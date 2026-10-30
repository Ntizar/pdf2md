"""Extracción de datos estructurados de figuras: OCR y datos del gráfico con verificación determinista.

Dado el PNG recortado de una figura, qwen3.6 produce un JSON estructurado (tipo, series,
valores, texto OCR) y un verificador determinista decide si la extracción es fiable:
- donut/anillo: los valores deben sumar ~100% (o 1.0)
- barras/líneas: los valores deben ser positivos y no todos idénticos
- tabla: filas con el mismo número de celdas
Si falla tras los reintentos, la figura queda como imagen (fallback, nunca se pierde).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

PROMPT_EXTRACCION = """Analiza esta figura recortada de un PDF y devuelve SOLO un JSON válido con esta forma:
{
  "tipo": "barras" | "lineas" | "donut" | "tabla" | "diagrama" | "fotografia" | "otro",
  "titulo": "título si se lee, si no cadena vacía",
  "series": [{"nombre": "nombre de la serie", "valores": [{"etiqueta": "categoría/eje x", "valor": 12.5}]}],
  "texto": "todo el texto visible en la figura (OCR), línea a línea",
  "extraible": true | false
}
Reglas:
- "valor" SIEMPRE número (sin unidades, sin %, sin separadores de miles).
- Para donut/anillo: los valores de cada serie deben ser porcentajes que sumen ~100.
- Si es fotografía, mapa o puro decorativo: extraible=false, series=[], texto=lo que se lea.
- NO inventes: si no lees un valor, no lo pongas.
Solo el JSON."""


@dataclass
class Extraccion:
    tipo: str = "otro"
    titulo: str = ""
    series: list = field(default_factory=list)
    texto: str = ""
    extraible: bool = False
    verificada: bool = False
    errores: list = field(default_factory=list)


def _extraer_json(respuesta: str) -> dict | None:
    respuesta = respuesta.strip()
    m = re.search(r"\{.*\}", respuesta, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def verificar_extraccion(ext: dict) -> list[str]:
    """Devuelve la lista de errores deterministas; vacía = verificada."""
    errores: list[str] = []
    tipo = ext.get("tipo", "otro")
    series = ext.get("series", [])
    if tipo in ("donut", "anillo"):
        for s in series:
            valores = [v.get("valor") for v in s.get("valores", []) if isinstance(v.get("valor"), (int, float))]
            if not valores:
                errores.append("donut sin valores numéricos")
                continue
            total = sum(valores)
            if not (95 <= total <= 105):
                errores.append(f"donut «{s.get('nombre', '')}»: suma {total:g}, esperado ~100")
    elif tipo in ("barras", "lineas"):
        for s in series:
            valores = [v.get("valor") for v in s.get("valores", []) if isinstance(v.get("valor"), (int, float))]
            if valores and all(v == valores[0] for v in valores) and len(valores) > 2:
                errores.append(f"«{s.get('nombre', '')}»: todos los valores idénticos ({valores[0]}), sospechoso")
            if any((not isinstance(v, (int, float))) or v < 0 for v in valores):
                errores.append(f"«{s.get('nombre', '')}»: valores no numéricos o negativos")
    elif tipo == "tabla":
        anchos = {len(s.get("valores", [])) for s in series}
        if len(anchos) > 1:
            errores.append(f"tabla con filas de anchos distintos: {sorted(anchos)}")
    if ext.get("extraible") and not series and tipo not in ("fotografia", "diagrama", "otro"):
        errores.append("declara extraible pero no hay series")
    return errores


def extraer_figura(cliente, ruta_png: str | Path, max_pasadas: int = 3) -> Extraccion:
    """Extrae datos de un PNG de figura con reintentos verificados. Nunca lanza: si no verifica, fallback."""
    from .raster import a_base64

    b64 = a_base64(ruta_png)
    ext = Extraccion()
    for pasada in range(max_pasadas):
        prompt = PROMPT_EXTRACCION
        if ext.errores:
            prompt += "\n\nTu JSON anterior tuvo estos problemas verificables, corrígelos:\n" + "\n".join(f"- {e}" for e in ext.errores)
        respuesta = cliente.chatear(prompt, imagen_b64=b64, max_tokens=2500, response_json=True)
        datos = _extraer_json(respuesta)
        if datos is None:
            ext.errores = ["respuesta no es JSON válido"]
            continue
        errores = verificar_extraccion(datos)
        ext.errores = errores
        ext.tipo = datos.get("tipo", "otro")
        ext.titulo = datos.get("titulo", "")
        ext.series = datos.get("series", [])
        ext.texto = datos.get("texto", "")
        ext.extraible = bool(datos.get("extraible")) and not errores
        if not errores:
            ext.verificada = True
            break
    return ext


def bloque_markdown(ext: Extraccion, ruta_imagen_relativa: str) -> str:
    """Convierte una extracción verificada en bloque markdown: tabla de datos + OCR + imagen de respaldo."""
    lineas = [f"![Figura]({ruta_imagen_relativa})", ""]
    if ext.titulo:
        lineas += [f"**{ext.titulo}**", ""]
    for s in ext.series:
        if not s.get("valores"):
            continue
        lineas += [f"| {s.get('nombre', 'serie')} | valor |", "|---|---|"]
        for v in s["valores"]:
            valor = v.get("valor", "")
            lineas.append(f"| {v.get('etiqueta', '')} | {valor} |")
        lineas.append("")
    if ext.texto:
        texto = ext.texto.strip()
        if "\n" in texto:
            lineas += ["<details>", "<summary>Texto de la figura (OCR)</summary>", "", texto, "", "</details>", ""]
        elif texto:
            lineas += [f"*{texto}*", ""]
    return "\n".join(lineas).strip() + "\n"
