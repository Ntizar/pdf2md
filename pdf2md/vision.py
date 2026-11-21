"""Cliente de visión OpenAI-compatible (NaN.builders por defecto).

Una sola función: `chatear(prompt, imagen_b64=None)` -> texto.
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
        self.key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.key:
            raise RuntimeError("Falta OPENAI_API_KEY: expórtala en el entorno o pásala como api_key.")
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
            "max_tokens": max_tokens,
        }
        if response_json:
            cuerpo["response_format"] = {"type": "json_object"}
        # reasoning_effort: qwen3.6 razona >120 s sin él; otros modelos pueden no
        # soportarlo (400 en gateways estrictos), así que solo va a quien lo admite
        esfuerzo = os.environ.get("OPENAI_REASONING_EFFORT")
        if esfuerzo is None and "qwen" in self.modelo.lower():
            esfuerzo = "minimal"
        if esfuerzo:
            cuerpo["reasoning_effort"] = esfuerzo
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
            except requests.HTTPError as e:
                ultimo_error = str(e)
                status = e.response.status_code if e.response is not None else None
                if status in (401, 403, 404):
                    break  # error permanente: reintentar no va a cambiar nada
            except Exception as e:  # noqa: BLE001 — reintentos ante red/API
                ultimo_error = str(e)
            if intento < self.reintentos - 1:
                time.sleep(2 ** intento)  # solo entre intentos, nunca tras el último
        raise RuntimeError(f"Visión falló tras {self.reintentos} intentos: {ultimo_error}")
