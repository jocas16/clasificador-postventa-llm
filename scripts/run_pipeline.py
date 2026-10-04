"""CLI del proyecto.

Ejemplos:
    python scripts/run_pipeline.py --datos data/raw/casos_postventa.csv --provider mock
    python scripts/run_pipeline.py --datos data/raw/casos_postventa.csv --provider ollama --muestra 100
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Settings  # noqa: E402
from src.pipeline import ejecutar_pipeline  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Clasificador LLM de casos de post-venta")
    ap.add_argument("--datos", required=True)
    ap.add_argument("--provider", default=None, help="mock | ollama | groq | openrouter")
    ap.add_argument("--muestra", type=int, default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--umbral", type=float, default=None)
    ap.add_argument("--log", default="INFO")
    a = ap.parse_args()

    logging.basicConfig(level=a.log, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    s = Settings()
    if a.provider:
        s.provider = a.provider
    if a.workers:
        s.max_workers = a.workers
    if a.umbral is not None:
        s.confidence_threshold = a.umbral

    r = ejecutar_pipeline(a.datos, s=s, muestra=a.muestra)

    print("\n=== METRICAS OPERATIVAS ===")
    print(json.dumps(r["operativo"], indent=2, ensure_ascii=False))
    print("\n=== CALIDAD ===")
    print(json.dumps(r["evaluacion"].get("resumen", {}), indent=2, ensure_ascii=False))
    print("\n=== TOP ERRORES (subcategoria) ===")
    print(r["evaluacion"].get("errores_top", "").to_string(index=False))
    print("\n=== CURVA DE AUTOMATIZACION ===")
    print(r["evaluacion"].get("automatizacion", "").to_string(index=False))


if __name__ == "__main__":
    main()
