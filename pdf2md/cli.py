"""CLI de pdf2md: convertir un PDF a markdown determinista con fallback a imagen.

Uso:
    pdf2md entrada.pdf -o salida/ [--pasadas 3]

Requiere OPENAI_API_KEY (y opcionalmente OPENAI_BASE_URL y OPENAI_MODEL).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .pipeline import convertir_pdf
from .vision import ClienteVision


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pdf2md", description="PDF a Markdown determinista por visión")
    ap.add_argument("pdf", help="ruta del PDF de entrada")
    ap.add_argument("-o", "--salida", default=None, help="directorio de salida (por defecto: <pdf>_md)")
    ap.add_argument("--pasadas", type=int, default=3, help="máximo de pasadas de verificación por página")
    args = ap.parse_args(argv)

    if "OPENAI_API_KEY" not in os.environ:
        print("Error: exporta OPENAI_API_KEY (API OpenAI-compatible; por defecto NaN.builders).", file=sys.stderr)
        return 2
    salida = Path(args.salida) if args.salida else Path(str(args.pdf) + "_md")
    cliente = ClienteVision()
    destino = convertir_pdf(cliente, args.pdf, salida, max_pasadas=args.pasadas)
    print(f"Listo: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
