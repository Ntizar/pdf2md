"""Verificación determinista del markdown producido: tablas bien formadas y aritmética de columnas numéricas."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RE_FILA = re.compile(r"^\s*\|(.+)\|\s*$")
RE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


@dataclass
class InformeVerificacion:
    ok: bool = True
    errores: list[str] = field(default_factory=list)

    def fallo(self, msg: str) -> None:
        self.ok = False
        self.errores.append(msg)


def verificar_markdown(md: str) -> InformeVerificacion:
    inf = InformeVerificacion()
    lineas = md.splitlines()
    i = 0
    while i < len(lineas):
        if RE_FILA.match(lineas[i]) and i + 1 < len(lineas) and RE_SEP.match(lineas[i + 1]):
            tabla = [lineas[i]]
            j = i + 1
            while j < len(lineas) and RE_FILA.match(lineas[j]):
                tabla.append(lineas[j])
                j += 1
            _verificar_tabla(tabla, inf)
            i = j
        else:
            i += 1
    return inf


def _celdas(fila: str) -> list[str]:
    m = RE_FILA.match(fila)
    if not m:
        return []
    return [c.strip() for c in m.group(1).split("|")]


def _es_numero(txt: str) -> bool:
    t = txt.strip().replace(".", "").replace(",", ".").replace("%", "").replace("€", "").strip()
    t = t.lstrip("+-")
    return bool(re.fullmatch(r"\d+(\.\d+)?", t)) if t else False


def _verificar_tabla(tabla: list[str], inf: InformeVerificacion) -> None:
    cab = _celdas(tabla[0])
    n = len(cab)
    filas: list[list[str]] = []
    irregulares = 0
    for k, fila in enumerate(tabla[2:], start=2):  # 0=cabecera, 1=separador
        celdas = _celdas(fila)
        if len(celdas) != n:
            irregulares += 1
            continue  # fila irregular: se ignora, no es fallo si son minoría (celdas combinadas del original)
        filas.append(celdas)
    if irregulares and (len(filas) <= 2 or irregulares > len(filas) // 2):
        inf.fallo(f"tabla irregular: {irregulares} filas de {len(filas) + irregulares} con ancho distinto a {n}")
    for col in range(n):
        valores = [f[col] for f in filas if f[col]]
        if len(valores) >= 3 and all(_es_numero(v) for v in valores):
            _verificar_suma(valores, inf, f"tabla col {col + 1}", tabla)


def _verificar_suma(valores: list[str], inf: InformeVerificacion, donde: str,
                    tabla: list[str] | None = None) -> None:
    nums = [float(v.strip().replace(".", "").replace(",", ".").replace("%", "").replace("€", "")) for v in valores]
    total = nums[-1]
    suma = sum(nums[:-1])
    if abs(suma - total) <= 0.01 * max(abs(total), 1):
        return
    # Columna de series temporales u objetivos (2030, 2040, 2050...): valores crecientes
    # monótonos NO son una suma; no marcar. Salvo que la fila final sea un total declarado
    # (celda de texto con «total») y no cuadre.
    cabecera_total = any(
        _celdas(f) and "total" in _celdas(f)[0].lower()
        for f in tabla[2:]
    )
    monotona = all(b >= a for a, b in zip(nums, nums[1:])) or all(b <= a for a, b in zip(nums, nums[1:]))
    if monotona and not cabecera_total:
        return
    # porcentajes sueltos de un cuadro de indicadores (objetivos, no composición): no suman 100
    if all(v.strip().endswith("%") for v in valores):
        return
    # mezcla de % y números puros (cuadro de indicadores heterogéneo): no es sumable
    con_porciento = sum(1 for v in valores if v.strip().endswith("%"))
    if 0 < con_porciento < len(valores):
        return
    # Solo marcar si hay fila de total declarada (no cuadra) o el último valor excede
    # claramente la suma de los anteriores (patrón de total mal leído).
    if cabecera_total or (total > suma and total <= suma * 1.5 and len(nums) >= 3):
        inf.fallo(f"{donde}: columna numérica no cuadra (suma {suma:g} != último {total:g})")
