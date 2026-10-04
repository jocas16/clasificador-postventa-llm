"""Fabrica de clientes: cambiar de proveedor = cambiar una variable de entorno."""
from __future__ import annotations

from ..config import Settings, settings as default_settings
from .base import BaseLLMClient
from .mock_client import MockLLMClient
from .ollama_client import OllamaClient
from .openai_compat_client import OpenAICompatClient


def get_llm_client(s: Settings | None = None) -> BaseLLMClient:
    s = s or default_settings
    comun = {"temperature": s.temperature, "max_tokens": s.max_tokens}
    p = s.provider.lower()

    if p == "mock":
        return MockLLMClient(**comun)
    if p == "ollama":
        return OllamaClient(modelo=s.ollama_model, base_url=s.ollama_base_url, **comun)
    if p == "groq":
        return OpenAICompatClient(
            modelo=s.groq_model, api_key=s.groq_api_key,
            base_url="https://api.groq.com/openai/v1", nombre="groq", **comun)
    if p == "openrouter":
        return OpenAICompatClient(
            modelo=s.openrouter_model, api_key=s.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1", nombre="openrouter", json_mode=False, **comun)
    raise ValueError(f"Proveedor no soportado: {s.provider}")
