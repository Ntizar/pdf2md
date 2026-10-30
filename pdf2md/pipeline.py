"""Pipeline principal: PDF -> markdown determinista con pasadas de verificación y fallback a imagen."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .figuras import RE_FIGURA, recortar_figuras_pagina
from .raster import a_base64, num_paginas, rasterizar_pagina
from .verificador import verificar_markdown

PROMPT_LECTURA = """Convierte esta página a markdown limpio y coherente. Reglas:
- IGNORA logos, marcas de agua, cabeceras repetidas y pies de página.
- Tablas como tablas markdown reales con cabeceras correctas y datos exactos.
- Títulos con #/##/### según jerarquía visual real.
- Si hay gráficos, diagramas, mapas o fotografías, emite EXACTAMENTE un marcador [FIGURA: descripción breve] en su posición. No intentes reconstruir el gráfico como texto.
- Conserva fechas, números y datos exactos. NO inventes contenido; si algo es ilegible escribe [ilegible].
Responde SOLO el markdown, sin bloque de código."""


def _extraer_bloque(md: str) -> str:
    m = re.search(r"```(?:markdown)?\n(.*)```", md, re.S)
    return m.group(1).strip() if m else md.strip()


def convertir_pagina(cliente, ruta_pdf: str | Path, indice: int, dir_cache: Path,
                     max_pasadas: int = 3) -> tuple[str, dict]:
    """Convierte una página. Devuelve (markdown, metadatos). Determinista: reintenta hasta verificar o agotar."""
    png = rasterizar_pagina(ruta_pdf, indice, dir_cache)
    b64 = a_base64(png)
    md_final = ""
    meta: dict = {"pagina": indice + 1, "pasadas": 0, "verificado": False, "figuras": 0}
    for pasada in range(max_pasadas):
        meta["pasadas"] += 1
        prompt = PROMPT_LECTURA
        if pasada > 0:
            prompt += f"\n\nTu respuesta anterior tuvo estos problemas verificables, corrígelos:\n" + "\n".join(f"- {e}" for e in meta["errores"])
        md = _extraer_bloque(cliente.chatear(prompt, imagen_b64=b64))
        inf = verificar_markdown(md)
        meta["errores"] = inf.errores
        if inf.ok or not inf.errores:
            md_final = md
            meta["verificado"] = True
            break
        md_final = md  # nos quedamos con la última pasada si nunca verifica
    meta["figuras"] = len(RE_FIGURA.findall(md_final))
    return md_final, meta


def convertir_pdf(cliente, ruta_pdf: str | Path, dir_salida: str | Path, dir_cache: Path | None = None,
                  max_pasadas: int = 3, log_ruta: str | Path | None = None) -> Path:
    """Convierte un PDF completo. Cache/jsonl reanudable: las páginas ya registradas como ok no se repiten."""
    ruta_pdf = Path(ruta_pdf)
    salida = Path(dir_salida)
    salida.mkdir(parents=True, exist_ok=True)
    cache = Path(dir_cache) if dir_cache else salida / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    log = Path(log_ruta) if log_ruta else salida / ".log.jsonl"
    hechas: dict[int, dict] = {}
    if log.exists():
        for linea in log.read_text().splitlines():
            try:
                reg = json.loads(linea)
                if reg.get("ok"):
                    hechas[reg["pagina"]] = reg
            except json.JSONDecodeError:
                continue
    total = num_paginas(ruta_pdf)
    paginas_md: dict[int, str] = {}
    with log.open("a") as flog:
        for indice in range(total):
            pag = indice + 1
            if pag in hechas:
                paginas_md[indice] = hechas[pag]["md"]
                continue
            md, meta = convertir_pagina(cliente, ruta_pdf, indice, cache, max_pasadas)
            # figuras detectadas -> recorte real
            if meta["figuras"]:
                figuras = recortar_figuras_pagina(ruta_pdf, indice, salida / "figuras")
                for k, fig in enumerate(figuras, start=1):
                    nombre = f"figuras/{fig.name}"
                    if f"[FIGURA:" in md:
                        md = re.sub(r"\[FIGURA:[^\]]+\]", f"![Figura]({nombre})", md, count=1)
                    else:
                        md += f"\n\n![Figura]({nombre})\n"
            paginas_md[indice] = md
            flog.write(json.dumps({"pagina": pag, "ok": True, "md": md, **meta}) + "\n")
            flog.flush()
    partes = [paginas_md[i] for i in sorted(paginas_md)]
    doc_md = "\n\n".join(partes) + "\n"
    destino = salida / f"{ruta_pdf.stem}.md"
    destino.write_text(doc_md)
    return destino
