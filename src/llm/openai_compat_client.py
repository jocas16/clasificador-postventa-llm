"""Cliente generico para APIs compatibles con OpenAI: Groq, OpenRouter, Together, etc.

Ambos tienen capa gratuita; solo cambian base_url, modelo y api_key.
"""
from __future__ import annotations

from typing import Dict, List

import requests

from .base import BaseLLMClient


class OpenAICompatClient(BaseLLMClient):
    def __init__(self, modelo: str, api_key: str, base_url: str, nombre: str = "openai_compat",
                 json_mode: bool = True, timeout: int = 90, **kw):
        super().__init__(modelo=modelo, **kw)
        if not api_key:
            raise ValueError(f"Falta API key para el proveedor '{nombre}'. Revisa tu .env")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.nombre = nombre
        self.json_mode = json_mode
        self.timeout = timeout

    def _call(self, mensajes: List[Dict[str, str]]) -> Dict:
        payload = {
            "model": self.modelo,
            "messages": mensajes,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage", {})
        return {
            "text": data["choices"][0]["message"]["content"],
            "in": usage.get("prompt_tokens", 0),
            "out": usage.get("completion_tokens", 0),
        }
