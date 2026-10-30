<div align="center">

# pdf2md

**[ES]** PDF a Markdown **determinista** por visión — verificador con reintentos y fallback a imagen recortada. Nada se pierde.
**[EN]** Deterministic **PDF → Markdown** via vision — verifier with retries and image fallback. Nothing gets lost.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg)](pyproject.toml)
[![Aurora](https://img.shields.io/badge/Design-Aurora%20v10-111111.svg)](https://github.com/Ntizar/Aurora)

**[ES] Lee la página entera como una imagen, verifica los números con reglas fijas, y reintenta hasta que cuadran — o te deja el gráfico original al lado.**

</div>

---

## ¿Qué hace? · What does it do?

**[ES]** Convierte cualquier PDF en Markdown limpio y **verificable**, pensado para LLMs y pipelines RAG:

1. **Rasteriza** cada página a PNG (pypdfium2, con caché en disco).
2. **La lee un modelo de visión** (cualquier VLM con API OpenAI-compatible, `qwen3.6` por defecto) que produce el markdown de la página: texto, tablas reales y un marcador `[FIGURA: ...]` donde había gráficos o fotos.
3. **Un verificador determinista comprueba el resultado sin IA**: tablas bien formadas y aritmética de columnas numéricas. Si algo no cuadra, el informe de errores se devuelve al modelo como feedback y reintenta (máx. 3 pasadas).
4. **Las figuras se recortan del PDF como PNG real** (objetos nativos, no capturas a ojo) y, si contienen datos, se extraen como tabla markdown + OCR con su propia verificación: un donut que no suma ~100 o unas barras todas idénticas → reintento → si se agota, la imagen queda en el documento igualmente.
5. **Ensambla todo** en `documento.md`, con las figuras PNG al lado y un log `.log.jsonl` **reanudable**: si el proceso muere a mitad de un PDF de 500 páginas, se retoma donde estaba.

**[EN]** Turns any PDF into clean, **verifiable** Markdown, built for LLMs and RAG pipelines:

1. **Rasterizes** each page to PNG (pypdfium2, disk-cached).
2. **A vision model reads it** (any OpenAI-compatible VLM, `qwen3.6` by default) producing the page's markdown: text, real tables and a `[FIGURA: ...]` marker where charts or photos were.
3. **A deterministic verifier checks the result without AI**: well-formed tables and numeric-column arithmetic. On mismatch, the error report goes back to the model as feedback (max. 3 passes).
4. **Figures are cropped from the PDF as real PNGs** (native objects, not eyeballed captures) and, when they carry data, extracted as a markdown table + OCR with its own checks: a donut not summing ~100 or all-identical bars → retry → if exhausted, the image still lands in the document.
5. **Assembles everything** into `documento.md`, with PNG figures alongside and a **resumable** `.log.jsonl`: if the process dies halfway through a 500-page PDF, it picks up where it left off.

## Cómo funciona · How it works

![Pipeline de pdf2md](assets/diagrama-light.svg#gh-light-mode-only)
![pdf2md pipeline](assets/diagrama-dark.svg#gh-dark-mode-only)

**[ES]** Dos bucles de verificación con feedback, uno por tablas y otro por figuras; los dos con fallback que garantiza que **nada se pierde**: el markdown siempre sale, verificado o con la evidencia original al lado.
**[EN]** Two verification loops with feedback, one for tables and one for figures; both with a fallback that guarantees **nothing gets lost**: the markdown always comes out, verified or with the original evidence next to it.

<details>
<summary><strong>[ES] Verificación de tablas: qué mira exactamente · [EN] Table checks: exactly what it looks at</strong></summary>

**[ES]**
- **Tablas fantasma**: filas con anchos distintos a la cabecera. Minoría → se toleran (celdas combinadas del original); mayoría → fallo.
- **Aritmética**: columnas completamente numéricas donde el último valor debería ser la suma de los anteriores (tolerancia 1 %). Excluye series temporales monótonas (objetivos 2030/2040/2050 no son sumas) salvo que haya un total declarado.
- El verificador es **código puro, sin IA**: mismo input, mismo veredicto. Lo que se marca, se puede reproducir.

**[EN]**
- **Ghost tables**: rows whose width differs from the header. A minority → tolerated (merged cells in the original); a majority → failure.
- **Arithmetic**: fully numeric columns where the last value should be the sum of the previous ones (1 % tolerance). Monotonic time series are excluded (2030/2040/2050 targets aren't sums) unless a declared total exists.
- The verifier is **pure code, no AI**: same input, same verdict. Every flag is reproducible.

</details>

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

### Ejemplo real · Real example

**[ES]** En [`ejemplos/`](ejemplos/) tienes 10 páginas del denso **«España 2050»** (cuadro de 50 indicadores, tablas anchas y gráficos vectoriales) junto a su conversión ya hecha: [`espana-2050-pag46-55.md`](ejemplos/espana-2050-pag46-55.md) con tablas verificadas, figuras recortadas y OCR.
**[EN]** [`ejemplos/`](ejemplos/) ships 10 pages of the dense **«España 2050»** report (50-indicator scoreboard, wide tables, vector charts) alongside its already-converted output: [`espana-2050-pag46-55.md`](ejemplos/espana-2050-pag46-55.md) with verified tables, cropped figures and OCR.

## Por qué determinista · Why deterministic

| [ES] Problema clásico · [EN] Classic problem | Otro conversor · Typical converter | pdf2md |
|---|---|---|
| Tablas fantasma y columnas rotas · Ghost tables, broken columns | ✗ | Verificador determinista + reintentos con feedback · Deterministic verifier + feedback retries |
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
