"""Cliente de visión OpenAI-compatible (NaN.builders por defecto).

Una sola función: `chatear(mensaje, imagen_png=None)` -> texto.
El modelo y la base URL se leen de variables de entorno (OPENAI_MODEL, OPENAI_BASE_URL, OPENAI_API_KEY).
"""

from __future__ import annotations

import os
import time

import requests

USER_AGENT = "Mozilla/5.0 (pdf2md)"


def _base() -> str:
    base = os.environ.get("OPENAI_BASE_URL", "https://api.nan.builders/v1")
    if not base.rstrip("/").endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    return base


def _modelo() -> str:
    return os.environ.get("OPENAI_MODEL", "qwen3.6")


class ClienteVision:
    """Cliente mínimo. `reasoning_effort=minimal` evita que qwen3.6 razone >120 s."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, modelo: str | None = None,
                 timeout: int = 180, reintentos: int = 3):
        self.key = api_key or os.environ["OPENAI_API_KEY"]
        self.base = (base_url or _base()).rstrip("/")
        self.modelo = modelo or _modelo()
        self.timeout = timeout
        self.reintentos = reintentos

    def chatear(self, prompt: str, imagen_b64: str | None = None, max_tokens: int = 4000,
                response_json: bool = False) -> str:
        contenido: list[dict] = []
        if imagen_b64:
            contenido.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{imagen_b64}"}})
        contenido.append({"type": "text", "text": prompt})
        cuerpo: dict = {
            "model": self.modelo,
            "messages": [{"role": "user", "content": contenido}],
            "reasoning_effort": "minimal",
            "max_tokens": max_tokens,
        }
        if response_json:
            cuerpo["response_format"] = {"type": "json_object"}
        ultimo_error = ""
        for intento in range(self.reintentos):
            try:
                r = requests.post(
                    f"{self.base}/chat/completions",
                    headers={"Authorization": f"Bearer {self.key}", "User-Agent": USER_AGENT},
                    json=cuerpo, timeout=self.timeout,
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:  # noqa: BLE001 — reintentos ante red/API
                ultimo_error = str(e)
                time.sleep(2 ** intento)
        raise RuntimeError(f"Visión falló tras {self.reintentos} intentos: {ultimo_error}")
