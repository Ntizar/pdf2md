# pdf2md

**[ES]** Conversor de PDF a Markdown **determinista**: cada página se lee con un modelo de visión (VLM OpenAI-compatible, por defecto `qwen3.6`) y el resultado pasa un **verificador determinista** (tablas bien formadas, aritmética de columnas numéricas). Si no cuadra, otra pasada con el informe de errores como feedback. Los gráficos, diagramas y fotografías que no se pueden reconstruir como texto se **recortan del PDF como imagen** y se referencian desde el markdown. Nada se pierde.

**[EN]** Deterministic PDF → Markdown converter: each page is read by a vision model (any OpenAI-compatible VLM, `qwen3.6` by default) and the result goes through a **deterministic verifier** (well-formed tables, numeric-column arithmetic). If it doesn't add up, another pass runs with the error report as feedback. Charts, diagrams and photos that can't be reconstructed as text are **cropped from the PDF as images** and referenced from the markdown. Nothing gets lost.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Aurora](https://img.shields.io/badge/Design-Aurora%20v10-2563eb)](https://github.com/Ntizar/Aurora)

**[ES] Cómo funciona · [EN] How it works**

```
PDF ──▶ rasterizar (pypdfium2, cache por página)
    ──▶ leer con VLM ──▶ markdown
    ──▶ verificar (tablas + aritmética) ──┬─ ok ──▶ siguiente página
                                          └─ fallo ──▶ otra pasada con feedback (máx. 3)
    ──▶ [FIGURA: ...] ──▶ recorte real del PDF ──▶ figuras/pagNNN-figN.png
    ──▶ ensamblar documento.md  (+ .log.jsonl reanudable)
```

## Inicio rápido · Quick start

```bash
# [ES] Requiere Python 3.10+ y una API key OpenAI-compatible.
# [EN] Requires Python 3.10+ and an OpenAI-compatible API key.

git clone https://github.com/Ntizar/pdf2md
cd pdf2md
uv pip install -e .

export OPENAI_API_KEY="sk-..."
# [ES] Opcional: OPENAI_BASE_URL (por defecto https://api.nan.builders/v1) y OPENAI_MODEL (por defecto qwen3.6)
# [EN] Optional: OPENAI_BASE_URL (default https://api.nan.builders/v1) and OPENAI_MODEL (default qwen3.6)

pdf2md documento.pdf -o salida/
```

Resultado · Result:

```
salida/
├── documento.md        # [ES] el markdown final · [EN] the final markdown
├── figuras/            # [ES] recortes PNG · [EN] PNG crops
│   └── pag005-fig1.png
└── .log.jsonl          # [ES] log reanudable · [EN] resumable log
```

## Por qué determinista · Why deterministic

| [ES] Problema clásico | [EN] Classic problem | [ES] pdf2md | [EN] pdf2md |
|---|---|---|---|
| Tablas fantasma y columnas rotas · Ghost tables, broken columns | ✗ | Verificador determinista + reintentos con feedback · Deterministic verifier + retries with feedback |
| Gráficos convertidos en basura de texto · Charts turned into text garbage | ✗ | Recorte real del PDF como PNG · Real PDF crop as PNG |
| Un crash repite horas de llamadas · A crash repeats hours of calls | ✗ | Cache por página + log jsonl reanudable · Per-page cache + resumable jsonl log |
| El resultado «parece bien» y nadie lo comprueba · "Looks fine", nobody checks | ✗ | Verificación aritmética de columnas numéricas · Arithmetic check of numeric columns |


## Limitaciones · Limitations

- **[ES]** Tablas que cruzan de página no se fusionan todavía (en la hoja de ruta).
  **[EN]** Tables spanning pages are not merged yet (on the roadmap).
- **[ES]** El recorte de figuras localiza objetos nativos del PDF (imágenes y trazados grandes); en PDFs escaneados recorta la página completa.
  **[EN]** Figure crops locate native PDF objects (images and large paths); on scanned PDFs it crops the full page.
- **[ES]** El verificador de sumas es heurístico: solo marca columnas numéricas completas cuyo último valor no cuadra.
  **[EN]** The sum checker is heuristic: it only flags fully numeric columns whose last value doesn't add up.

## Licencia · License

MIT — © David Antizar

Hecho con ❤️ por David Antizar
