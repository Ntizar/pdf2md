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
        assert any("celdas" in e for e in inf.errores)

    def test_texto_plano_ok(self):
        assert verificar_markdown("Párrafo simple sin tablas.\n\nOtro párrafo.").ok


class TestFiguras:
    def test_patron_figura(self):
        from pdf2md.figuras import RE_FIGURA
        assert RE_FIGURA.findall("texto [FIGURA: gráfico de barras] más texto") == ["gráfico de barras"]
        assert RE_FIGURA.search("sin marcador") is None

    def test_recorte_pdf_real(self):
        import pypdfium2 as pdfium
        from pdf2md.figuras import recortar_figuras_pagina
        pdf = Path("/home/nan/Projects/CiafMD/pdfs/ES/IF-140109-190509-CIAF.pdf")
        if not pdf.exists():
            print("skip: PDF de prueba no disponible")
            return
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            figuras = recortar_figuras_pagina(pdf, 5, tmp)
            for f in figuras:
                assert f.exists() and f.stat().st_size > 500


class TestPipeline:
    def test_cache_reanudable(self, tmp_path):
        from pdf2md.pipeline import convertir_pagina

        class ClienteFalso:
            def __init__(self):
                self.llamadas = 0

            def chatear(self, prompt, imagen_b64=None, max_tokens=4000, response_json=False):
                self.llamadas += 1
                return "| A | B |\n|---|---|\n| 1 | 2 |"

        pdf = Path("/home/nan/Projects/CiafMD/pdfs/ES/IF-140109-190509-CIAF.pdf")
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

        pdf = Path("/home/nan/Projects/CiafMD/pdfs/ES/IF-140109-190509-CIAF.pdf")
        if not pdf.exists():
            print("skip: PDF de prueba no disponible")
            return
        cliente = ClienteRotoLuegoBien()
        md, meta = convertir_pagina(cliente, pdf, 0, tmp_path, max_pasadas=3)
        assert meta["pasadas"] == 2
        assert meta["verificado"]
        assert "problemas verificables" in cliente.prompts[1]
