# pdf2md

**[ES]** Conversor de PDF a Markdown **determinista**, pensado para que lo consuman **LLMs y pipelines RAG**: cada página se lee con un modelo de visión (VLM OpenAI-compatible, por defecto `qwen3.6`) y el resultado pasa un **verificador determinista** (tablas bien formadas, aritmética de columnas numéricas). Si no cuadra, otra pasada con el informe de errores como feedback. Los gráficos, diagramas y fotografías se **recortan del PDF como imagen** y, cuando contienen datos, se **extraen como tabla markdown + OCR verificando** (donut que no suma 100 → reintento → fallback a imagen). Nada se pierde.

**[EN]** Deterministic **PDF → Markdown converter built for LLMs and RAG pipelines**: each page is read by a vision model (any OpenAI-compatible VLM, `qwen3.6` by default) and the result goes through a **deterministic verifier** (well-formed tables, numeric-column arithmetic). If it doesn't add up, another pass runs with the error report as feedback. Charts, diagrams and photos are **cropped from the PDF as images** and, when they carry data, **extracted as a markdown table + verified OCR** (a donut that doesn't sum to 100 → retry → image fallback). Nothing gets lost.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Aurora](https://img.shields.io/badge/Design-Aurora%20v10-2563eb)](https://github.com/Ntizar/Aurora)

**[ES] Cómo funciona · [EN] How it works**

```
PDF ──▶ rasterizar (pypdfium2, cache por página)
    ──▶ leer con VLM ──▶ markdown
    ──▶ verificar (tablas + aritmética) ──┬─ ok ──▶ siguiente página
                                          └─ fallo ──▶ otra pasada con feedback (máx. 3)
    ──▶ [FIGURA: ...] ──▶ recorte real del PDF ──▶ extracción de datos (JSON verificado:
         donut suma ~100, barras no idénticas, tabla filas iguales) ──▶ tabla MD + OCR + PNG
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

## Hecho para LLMs y RAG · Built for LLMs and RAG

**[ES]** Un LLM trabaja **mejor con el MD que con el PDF**, y no es una opinión:

- **Entrada texto directo vs. visión**: el PDF obliga a rasterizar cada página (~2k tokens de imagen + segundos de latencia). El MD entra como texto puro: ~4× menos tokens, respuesta inmediata.
- **Los números ya están verificados**: cada tabla pasó el verificador determinista (o lleva el PNG original al lado). Un RAG que cita cifras de este MD no está citando una posible alucinación del primer pase.
- **Chunking por estructura**: cortar por encabezados, tablas atómicas, figuras con su OCR en `<details>` — el MD conserva la semántica que el RAG necesita y el PDF no tiene.
- **Multimodal-ready**: las figuras no extraíbles quedan indexables por descripción/OCR y servibles como imagen al VLM cuando la pregunta lo pide.

**[ES] Cómo indexarlo en un RAG (ChromaDB, LangChain, LlamaIndex…):**

1. Chunking por encabezados markdown; cada tabla como chunk atómico.
2. Para tablas, indexa también una **serialización en frases** de cada fila ("La tasa de empleo objetivo para 2030 es 68%") — los embeddings recuperan frases mejor que celdas; sirve la tabla completa como contexto.
3. Indexa el OCR de las figuras con su ruta PNG como metadato para servir la imagen al modelo multimodal.
4. Re-ranking con el propio VLM sobre los top-k: si tu API es OpenAI-compatible (como NaN.builders), el re-ranker es el mismo modelo.

**[EN]** An LLM works **better with the MD than with the PDF**, and it's not an opinion:

- **Text input vs. vision**: PDF forces per-page rasterization (~2k image tokens + seconds of latency). MD enters as plain text: ~4× fewer tokens, instant responses.
- **Numbers are already verified**: every table passed the deterministic verifier (or carries the original PNG alongside). A RAG citing figures from this MD isn't citing a possible first-pass hallucination.
- **Structure-aware chunking**: split by headings, atomic tables, figures with OCR in `<details>` — the MD keeps the semantics RAG needs and PDFs lack.
- **Multimodal-ready**: non-extractable figures are indexable by description/OCR and servable as images to the VLM when the question calls for it.

**[EN] How to index it into a RAG (ChromaDB, LangChain, LlamaIndex…):**

1. Chunk by markdown headings; keep every table as an atomic chunk.
2. For tables, also index a **sentence serialization** of each row ("The 2030 employment-rate target is 68%") — embeddings retrieve sentences better than cells; serve the full table as context.
3. Index figure OCR with the PNG path as metadata so the multimodal model can be served the image.
4. Re-rank top-k with the same VLM: if your API is OpenAI-compatible (like NaN.builders), the re-ranker is the same model you already run.


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
