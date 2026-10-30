"""Tests de extracción de figuras: verificador determinista y bloque markdown (sin red)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pdf2md.extraccion import Extraccion, bloque_markdown, verificar_extraccion  # noqa: E402


class TestVerificador:
    def test_donut_que_suma_100_ok(self):
        ext = {"tipo": "donut", "series": [{"nombre": "s", "valores": [
            {"etiqueta": "a", "valor": 60}, {"etiqueta": "b", "valor": 40}]}], "extraible": True}
        assert verificar_extraccion(ext) == []

    def test_donut_circular_falla(self):
        ext = {"tipo": "donut", "series": [{"nombre": "s", "valores": [
            {"etiqueta": "a", "valor": 60}, {"etiqueta": "b", "valor": 70}]}], "extraible": True}
        errores = verificar_extraccion(ext)
        assert any("suma" in e for e in errores)

    def test_barras_identicas_falla(self):
        ext = {"tipo": "barras", "series": [{"nombre": "s", "valores": [
            {"etiqueta": str(i), "valor": 5} for i in range(4)]}], "extraible": True}
        assert any("idénticos" in e for e in verificar_extraccion(ext))

    def test_tabla_filas_dispareas_falla(self):
        ext = {"tipo": "tabla", "series": [
            {"nombre": "f1", "valores": [{"etiqueta": "a", "valor": 1}, {"etiqueta": "b", "valor": 2}]},
            {"nombre": "f2", "valores": [{"etiqueta": "a", "valor": 1}]}], "extraible": True}
        assert any("anchos" in e for e in verificar_extraccion(ext))

    def test_fotografia_sin_series_ok(self):
        ext = {"tipo": "fotografia", "series": [], "extraible": False, "texto": "estación de Avilés"}
        assert verificar_extraccion(ext) == []


class TestBloqueMarkdown:
    def test_bloque_con_tabla_y_ocr(self):
        ext = Extraccion(tipo="donut", titulo="Reparto modal", series=[
            {"nombre": "reparto", "valores": [{"etiqueta": "tren", "valor": 70}, {"etiqueta": "bus", "valor": 30}]}],
            texto="Figura 3. Reparto modal", extraible=True, verificada=True)
        md = bloque_markdown(ext, "figuras/pag001-fig1.png")
        assert "![Figura](figuras/pag001-fig1.png)" in md
        assert "| tren | 70 |" in md
        assert "*Figura 3. Reparto modal*" in md

    def test_bloque_sin_datos_solo_imagen(self):
        ext = Extraccion(tipo="fotografia", extraible=False)
        md = bloque_markdown(ext, "figuras/pag002-fig1.png")
        assert md.strip() == "![Figura](figuras/pag002-fig1.png)"
