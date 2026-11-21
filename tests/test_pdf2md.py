"""Tests de pdf2md: verificador, figuras y pipeline (sin red)."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pdf2md.verificador import verificar_markdown  # noqa: E402


class TestVerificador:
    def test_tabla_bien_formada_ok(self):
        md = """| Concepto | Importe |
|---|---|
| Vía única | 100 |
| Electrificación | 50 |
"""
        inf = verificar_markdown(md)
        assert inf.ok, inf.errores

    def test_tabla_fantasma_detectada(self):
        md = """|  | CIAF | |
|---|---|---|
| fila rota | solo 2 |
"""
        inf = verificar_markdown(md)
        assert not inf.ok
        assert any("irregular" in e or "celdas" in e for e in inf.errores)

    def test_texto_plano_ok(self):
        assert verificar_markdown("Párrafo simple sin tablas.\n\nOtro párrafo.").ok

    def test_serie_temporal_no_es_suma(self):
        # columnas de objetivos 2030/2040/2050 son series, no sumas: no deben fallar
        md = """| Indicador | 2030 | 2040 | 2050 |
|---|---|---|---|
| Pobreza | 16,1 | 12,7 | 9,2 |
"""
        assert verificar_markdown(md).ok

    def test_total_declarado_mal_sumado_detectado(self):
        md = """| Concepto | Euros |
|---|---|
| A | 100 |
| B | 200 |
| C | 250 |
| Total | 400 |
"""
        inf = verificar_markdown(md)
        assert not inf.ok
        assert any("no cuadra" in e for e in inf.errores)

    def test_total_declarado_bien_sumado_ok(self):
        md = """| Concepto | Euros |
|---|---|
| A | 100 |
| B | 200 |
| Total | 300 |
"""
        assert verificar_markdown(md).ok

    def test_serie_monotona_con_totalmente_ok(self):
        # «totalmente» en una celda de datos no es un total declarado
        md = """| Nota | serie |
|---|---|
| totalmente nuevo | 5 |
| b | 10 |
| c | 20 |
"""
        assert verificar_markdown(md).ok

    def test_decimales_mezclados_ok(self):
        md = """| Concepto | Euros |
|---|---|
| A | 1,5 |
| B | 2.5 |
| Total | 4.0 |
"""
        assert verificar_markdown(md).ok

    def test_miles_espanol_ok(self):
        md = """| Concepto | Euros |
|---|---|
| A | 1.234,56 |
| B | 765,44 |
| Total | 2.000 |
"""
        assert verificar_markdown(md).ok


class TestFiguras:
    def test_patron_figura(self):
        from pdf2md.figuras import RE_FIGURA
        assert RE_FIGURA.findall("texto [FIGURA: gráfico de barras] más texto") == ["gráfico de barras"]
        assert RE_FIGURA.search("sin marcador") is None

    def test_recorte_pdf_real(self):
        import pypdfium2 as pdfium
        from pdf2md.figuras import recortar_figuras_pagina
        pdf = Path(__file__).resolve().parents[1] / "ejemplos" / "espana-2050-pag46-55.pdf"
        if not pdf.exists():
            print("skip: PDF de prueba no disponible")
            return
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            figuras = recortar_figuras_pagina(pdf, 5, tmp)
            for f in figuras:
                assert f.exists() and f.stat().st_size > 500

    def test_orden_lectura_topdown(self):
        from pdf2md.figuras import _fusionar
        arriba = (100.0, 300.0, 200.0, 340.0)
        abajo = (100.0, 100.0, 200.0, 140.0)
        assert _fusionar([arriba, abajo])[0] == arriba


class TestPipeline:
    def test_cache_reanudable(self, tmp_path):
        from pdf2md.pipeline import convertir_pagina

        class ClienteFalso:
            def __init__(self):
                self.llamadas = 0

            def chatear(self, prompt, imagen_b64=None, max_tokens=4000, response_json=False):
                self.llamadas += 1
                return "| A | B |\n|---|---|\n| 1 | 2 |"

        pdf = Path(__file__).resolve().parents[1] / "ejemplos" / "espana-2050-pag46-55.pdf"
        if not pdf.exists():
            print("skip: PDF de prueba no disponible")
            return
        cliente = ClienteFalso()
        md, meta = convertir_pagina(cliente, pdf, 0, tmp_path, max_pasadas=2)
        assert "| A | B |" in md
        assert meta["verificado"]
        assert cliente.llamadas == 1

    def test_reintento_con_feedback(self, tmp_path):
        from pdf2md.pipeline import convertir_pagina

        class ClienteRotoLuegoBien:
            def __init__(self):
                self.prompts = []

            def chatear(self, prompt, imagen_b64=None, max_tokens=4000, response_json=False):
                self.prompts.append(prompt)
                if len(self.prompts) == 1:
                    return "| A | B |\n|---|---|\n| 1 |"  # tabla rota
                return "| A | B |\n|---|---|\n| 1 | 2 |"

        pdf = Path(__file__).resolve().parents[1] / "ejemplos" / "espana-2050-pag46-55.pdf"
        if not pdf.exists():
            print("skip: PDF de prueba no disponible")
            return
        cliente = ClienteRotoLuegoBien()
        md, meta = convertir_pagina(cliente, pdf, 0, tmp_path, max_pasadas=3)
        assert meta["pasadas"] == 2
        assert meta["verificado"]
        assert "problemas verificables" in cliente.prompts[1]

    def test_sustitucion_figura_con_barras(self):
        from pdf2md.pipeline import _sustituir_figura
        out = _sustituir_figura("x [FIGURA: a] y", "OCR \\1 con barra")
        assert out == "x OCR \\1 con barra y"

    def test_log_no_contamina_entre_pdfs(self, tmp_path):
        from PIL import Image
        from pdf2md.pipeline import convertir_pdf

        class ClienteFalso:
            def __init__(self, texto):
                self.texto = texto
                self.llamadas = 0

            def chatear(self, prompt, imagen_b64=None, max_tokens=4000, response_json=False):
                self.llamadas += 1
                return f"| {self.texto} | B |\n|---|---|\n| 1 | 2 |"

        pdf = Path(__file__).resolve().parents[1] / "ejemplos" / "espana-2050-pag46-55.pdf"
        if not pdf.exists():
            print("skip: PDF de prueba no disponible")
            return
        mini = tmp_path / "mini.pdf"
        Image.new("RGB", (10, 20), "white").save(mini)
        c1 = ClienteFalso("PRIMERA")
        convertir_pdf(c1, pdf, tmp_path)
        c2 = ClienteFalso("SEGUNDA")
        destino = convertir_pdf(c2, mini, tmp_path)
        # el mini tiene 1 página: se convierte de verdad, no se reutiliza el otro PDF
        assert c2.llamadas == 1
        assert "SEGUNDA" in destino.read_text()

    def test_cache_distingue_ficheros(self, tmp_path):
        from PIL import Image
        from pdf2md.raster import rasterizar_pagina
        pdf = Path(__file__).resolve().parents[1] / "ejemplos" / "espana-2050-pag46-55.pdf"
        if not pdf.exists():
            print("skip: PDF de prueba no disponible")
            return
        mini = tmp_path / "mini.pdf"
        Image.new("RGB", (10, 20), "white").save(mini)
        p1 = rasterizar_pagina(pdf, 0, tmp_path)
        p2 = rasterizar_pagina(mini, 0, tmp_path)
        assert p1 != p2
        assert p1.stat().st_size != p2.stat().st_size
