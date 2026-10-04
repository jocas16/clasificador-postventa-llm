"""Interfaz comun para cualquier proveedor de LLM (patron Strategy)."""
from __future__ import annotations

import abc
import time
from typing import Dict, List

from ..schemas import LLMResponse


class BaseLLMClient(abc.ABC):
    nombre = "base"

    def __init__(self, modelo: str, temperature: float = 0.0, max_tokens: int = 300):
        self.modelo = modelo
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abc.abstractmethod
    def _call(self, mensajes: List[Dict[str, str]]) -> Dict:
        """Debe devolver {'text': str, 'in': int, 'out': int}."""

    def chat(self, mensajes: List[Dict[str, str]]) -> LLMResponse:
        t0 = time.perf_counter()
        raw = self._call(mensajes)
        return LLMResponse(
            text=raw["text"],
            latencia_ms=int((time.perf_counter() - t0) * 1000),
            tokens_entrada=raw.get("in", 0),
            tokens_salida=raw.get("out", 0),
            modelo=self.modelo,
            proveedor=self.nombre,
        )
