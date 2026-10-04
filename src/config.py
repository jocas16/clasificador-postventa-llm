"""Configuracion central del proyecto (12-factor: todo por variables de entorno)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
for _p in (DATA_RAW, DATA_PROC, OUTPUTS):
    _p.mkdir(parents=True, exist_ok=True)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class Settings:
    provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "mock"))
    temperature: float = field(default_factory=lambda: float(_env("LLM_TEMPERATURE", "0.0")))
    max_tokens: int = field(default_factory=lambda: int(_env("LLM_MAX_TOKENS", "600")))
    max_workers: int = field(default_factory=lambda: int(_env("MAX_WORKERS", "4")))
    confidence_threshold: float = field(
        default_factory=lambda: float(_env("CONFIDENCE_THRESHOLD", "0.70"))
    )
    # Ollama
    ollama_base_url: str = field(default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "qwen2.5:3b")) #qwen2.5:7b-instruct
    # Groq
    groq_api_key: str = field(default_factory=lambda: _env("GROQ_API_KEY"))
    groq_model: str = field(default_factory=lambda: _env("GROQ_MODEL", "openai/gpt-oss-120b"))#llama-3.3-70b-versatile
    # OpenRouter
    openrouter_api_key: str = field(default_factory=lambda: _env("OPENROUTER_API_KEY"))
    openrouter_model: str = field(
        default_factory=lambda: _env("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    )


class Taxonomy:
    """Fuente unica de verdad de categorias, subcategorias y prioridades."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or ROOT / "config" / "taxonomy.yaml")
        self.raw: Dict[str, Any] = yaml.safe_load(self.path.read_text(encoding="utf-8"))

    @property
    def version(self) -> str:
        return str(self.raw.get("version", "v1.0"))

    @property
    def prioridades(self) -> List[str]:
        return list(self.raw.get("prioridades", ["ALTA", "MEDIA", "BAJA"]))

    @property
    def categorias(self) -> List[str]:
        return list(self.raw["categorias"].keys())

    def subcategorias(self, categoria: str) -> List[str]:
        cat = self.raw["categorias"].get(categoria, {})
        return [s["nombre"] for s in cat.get("subcategorias", [])]

    def es_valido(self, categoria: str, subcategoria: str) -> bool:
        return categoria in self.categorias and subcategoria in self.subcategorias(categoria)

    def prioridad_sugerida(self, categoria: str, subcategoria: str) -> str | None:
        for s in self.raw["categorias"].get(categoria, {}).get("subcategorias", []):
            if s["nombre"] == subcategoria:
                return s.get("prioridad_sugerida")
        return None

    def as_prompt_block(self) -> str:
        """Serializa la taxonomia en texto compacto para inyectarla en el prompt."""
        lineas = []
        for cat, body in self.raw["categorias"].items():
            subs = ", ".join(s["nombre"] for s in body.get("subcategorias", []))
            lineas.append(f"- {cat}: {body.get('descripcion','')}\n    subcategorias: [{subs}]")
        return "\n".join(lineas)


settings = Settings()
