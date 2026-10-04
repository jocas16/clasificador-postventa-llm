"""Ollama: LLM 100% local, sin costo y sin enviar datos del banco a internet."""
from __future__ import annotations

from typing import Dict, List

import requests

from .base import BaseLLMClient


class OllamaClient(BaseLLMClient):
    nombre = "ollama"

    def __init__(self, modelo: str, base_url: str = "http://localhost:11434", timeout: int = 120, **kw):
        super().__init__(modelo=modelo, **kw)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _call(self, mensajes: List[Dict[str, str]]) -> Dict:
        payload = {
            "model": self.modelo,
            "messages": mensajes,
            "stream": False,
            "format": "json",  # fuerza salida JSON valida
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return {
            "text": data["message"]["content"],
            "in": data.get("prompt_eval_count", 0),
            "out": data.get("eval_count", 0),
        }
