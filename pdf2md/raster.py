"""Rasterizado de páginas PDF a PNG con pypdfium2, con cache en disco."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pypdfium2 as pdfium


def rasterizar_pagina(ruta_pdf: str | Path, indice: int, cache_dir: str | Path, escala: float = 2.0) -> Path:
    """Devuelve la ruta del PNG de la página `indice` (0-based), generándolo si no está en cache."""
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    clave = hashlib.sha1(f"{Path(ruta_pdf).resolve()}:{indice}:{escala}".encode()).hexdigest()[:16]
    destino = cache / f"pag-{indice:04d}-{clave}.png"
    if destino.exists():
        return destino
    doc = pdfium.PdfDocument(str(ruta_pdf))
    try:
        img = doc[indice].render(scale=escala).to_pil()
    finally:
        doc.close()
    img.save(destino)
    return destino


def a_base64(ruta_png: str | Path) -> str:
    return base64.b64encode(Path(ruta_png).read_bytes()).decode()


def num_paginas(ruta_pdf: str | Path) -> int:
    doc = pdfium.PdfDocument(str(ruta_pdf))
    try:
        return len(doc)
    finally:
        doc.close()
