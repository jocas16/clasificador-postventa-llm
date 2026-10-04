"""Contratos de datos del pipeline."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional


@dataclass
class Caso:
    id_caso: str
    fecha: str
    canal: str
    texto_caso: str
    categoria_real: Optional[str] = None
    subcategoria_real: Optional[str] = None
    prioridad_real: Optional[str] = None
    taxonomy_version: Optional[str] = None


@dataclass
class Clasificacion:
    id_caso: str
    categoria: str
    subcategoria: str
    prioridad: str
    justificacion: str
    confianza: float
    requiere_revision: bool = False
    motivo_revision: str = ""
    modelo: str = ""
    proveedor: str = ""
    latencia_ms: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    intentos: int = 1
    error: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("extra", None)
        return d


@dataclass
class LLMResponse:
    text: str
    latencia_ms: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    modelo: str = ""
    proveedor: str = ""
