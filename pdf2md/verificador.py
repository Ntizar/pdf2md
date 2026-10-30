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
    for k, fila in enumerate(tabla[2:], start=2):  # 0=cabecera, 1=separador
        celdas = _celdas(fila)
        if len(celdas) != n:
            inf.fallo(f"tabla fila {k}: {len(celdas)} celdas, esperadas {n}")
            continue
        filas.append(celdas)
    for col in range(n):
        valores = [f[col] for f in filas if f[col]]
        if len(valores) >= 3 and all(_es_numero(v) for v in valores):
            _verificar_suma(valores, inf, f"tabla col {col + 1}")


def _verificar_suma(valores: list[str], inf: InformeVerificacion, donde: str) -> None:
    nums = [float(v.strip().replace(".", "").replace(",", ".").replace("%", "").replace("€", "")) for v in valores]
    total = nums[-1]
    suma = sum(nums[:-1])
    if abs(suma - total) <= 0.01 * max(abs(total), 1):
        return
    # tolerancia: quizá no es fila de total; solo marcar si coincide con suma de un subconjunto inicial
    if abs(sum(nums[: len(nums) // 2]) - total) > 0.01 * max(abs(total), 1) and len(nums) > 3:
        inf.fallo(f"{donde}: columna numérica no cuadra (suma {suma:g} != último {total:g})")
