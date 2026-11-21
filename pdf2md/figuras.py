"""Recorte de figuras del PDF a partir de marcadores [FIGURA: ...] del modelo.

Estrategia: localizar en la página los objetos gráficos nativos del PDF
(imágenes incrustadas y trazados vectoriales grandes) con pypdfium2 y recortarlos.
Si la localización falla, se recorta la página entera como garantía de que no se pierde nada.
"""

from __future__ import annotations

import re
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
from PIL import Image as PILImage

from .raster import rasterizar_pagina

RE_FIGURA = re.compile(r"\[FIGURA:\s*([^\]]+)\]")


def recortar_figuras_pagina(ruta_pdf: str | Path, indice: int, dir_figuras: str | Path,
                            escala: float = 2.0, relleno: int = 8,
                            dir_cache: str | Path | None = None) -> list[Path]:
    """Recorta los objetos gráficos nativos de la página (imágenes y trazados densos).

    Devuelve la lista de PNG escritos, en orden de lectura.
    """
    dir_out = Path(dir_figuras)
    dir_out.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(ruta_pdf))
    pagina = doc[indice]
    w_pts, h_pts = pagina.get_size()
    candidatos: list[tuple[str, tuple[float, float, float, float]]] = []
    try:
        for obj in pagina.get_objects(max_depth=16):
            if obj.type == pdfium_raw.FPDF_PAGEOBJ_IMAGE:
                candidatos.append(("IMG", _ampliar(obj.get_bounds(), relleno)))
            elif obj.type == pdfium_raw.FPDF_PAGEOBJ_PATH and _area(obj.get_bounds()) > 20000:
                # trazados vectoriales grandes (fondos de gráficos, diagramas)
                candidatos.append(("PATH", _ampliar(obj.get_bounds(), relleno)))
    finally:
        doc.close()

    # descartar decorativos: trazados que cubren ≥80 % de la página (fondos, marcos)
    area_pagina = w_pts * h_pts
    candidatos = [c for c in candidatos if not (c[0] == "PATH" and _area(c[1]) >= 0.8 * area_pagina)]

    # fusionar cajas solapadas (un gráfico suele ser varios trazados), en orden de lectura
    cajas = _fusionar([b for _, b in candidatos])
    if not cajas:
        # la localización no encontró nada: página entera como garantía (nada se pierde)
        cajas = [(0.0, 0.0, w_pts, h_pts)]
    resultados: list[Path] = []
    for i, caja in enumerate(cajas):
        destino = dir_out / f"pag{indice + 1:03d}-fig{i + 1}.png"
        _recortar_png(ruta_pdf, indice, caja, destino, escala, dir_cache=dir_cache)
        resultados.append(destino)
    return resultados


def _area(bounds) -> float:
    l, b, r, t = bounds
    return max(0.0, (r - l)) * max(0.0, (t - b))


def _ampliar(bounds, margen: float):
    l, b, r, t = bounds
    return (l - margen, b - margen, r + margen, t + margen)


def _fusionar(cajas: list[tuple[float, float, float, float]]) -> list[tuple[float, float, float, float]]:
    cajas = sorted(cajas, key=lambda c: (-c[3], c[0]))  # orden de lectura: arriba→abajo, izquierda→derecha
    fusion: list[list[float]] = []
    for l, b, r, t in cajas:
        if fusion and l <= fusion[-1][2] and b <= fusion[-1][3] + 4 and r >= fusion[-1][0] and t >= fusion[-1][1] - 4:
            f = fusion[-1]
            f[0] = min(f[0], l); f[1] = min(f[1], b); f[2] = max(f[2], r); f[3] = max(f[3], t)
        else:
            fusion.append([l, b, r, t])
    return [tuple(f) for f in fusion]


def _recortar_png(ruta_pdf: str | Path, indice: int, caja_pts, destino: Path, escala: float,
                  dir_cache: str | Path | None = None) -> None:
    alto_pts: float
    if dir_cache:
        # reutiliza el render ya cacheado por el pipeline (antes re-rasterizaba por cada recorte)
        img = PILImage.open(rasterizar_pagina(ruta_pdf, indice, dir_cache, escala))
        alto_pts = img.height / escala
    else:
        doc = pdfium.PdfDocument(str(ruta_pdf))
        try:
            pagina = doc[indice]
            img = pagina.render(scale=escala).to_pil()
            alto_pts = pagina.get_height()
        finally:
            doc.close()
    l, b, r, t = caja_pts
    # pypdfium2 origen abajo-izquierda; PIL origen arriba-izquierda
    x0 = max(0, int(l * escala)); x1 = min(img.width, int(r * escala))
    y0 = max(0, int((alto_pts - t) * escala)); y1 = min(img.height, int((alto_pts - b) * escala))
    if x1 <= x0 or y1 <= y0:  # caja degenerada: página entera
        img.save(destino)
        return
    img.crop((x0, y0, x1, y1)).save(destino)
