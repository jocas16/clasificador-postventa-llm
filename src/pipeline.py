"""Pipeline end-to-end: carga -> preprocesamiento -> LLM -> evaluacion -> artefactos."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

from .classifier import Clasificador
from .config import DATA_PROC, OUTPUTS, Settings, Taxonomy, settings as default_settings
from .evaluation import evaluar_todo
from .llm.factory import get_llm_client
from .preprocessing import preprocesar

log = logging.getLogger(__name__)
COLS_REALES = ["categoria_real", "subcategoria_real", "prioridad_real"]


def cargar_casos(ruta: str | Path) -> pd.DataFrame:
    ruta = Path(ruta)
    if ruta.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(ruta)
    return pd.read_csv(ruta)


def ejecutar_pipeline(ruta_datos: str | Path, s: Settings | None = None,
                      muestra: int | None = None, guardar: bool = True) -> Dict:
    s = s or default_settings
    tax = Taxonomy()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    df = cargar_casos(ruta_datos)
    if muestra:
        df = df.head(muestra).copy()
    log.info("Casos cargados: %s", len(df))

    df_prep, reporte_prep = preprocesar(df)
    log.info("Preprocesamiento: %s", reporte_prep)

    cliente = get_llm_client(s)
    clf = Clasificador(cliente, tax, s)
    preds = clf.clasificar_lote(df_prep)

    cols_base = ["id_caso", "fecha", "canal", "texto_caso", "texto_limpio", "valido"]
    cols_base += [c for c in COLS_REALES if c in df_prep.columns]
    final = df_prep[cols_base].merge(preds, on="id_caso", how="left")
    final["acierto_categoria"] = None
    if "categoria_real" in final.columns:
        from .preprocessing import normalizar_etiqueta as _n
        final["acierto_categoria"] = (
            final["categoria_real"].map(_n) == final["categoria"].map(_n))
        final["acierto_subcategoria"] = (
            final["subcategoria_real"].map(_n) == final["subcategoria"].map(_n))

    evalr = evaluar_todo(final) if "categoria_real" in final.columns else {}

    operativo = {
        "casos": int(len(final)),
        "proveedor": cliente.nombre,
        "modelo": cliente.modelo,
        "latencia_media_ms": int(final["latencia_ms"].mean()) if len(final) else 0,
        "latencia_p95_ms": int(final["latencia_ms"].quantile(0.95)) if len(final) else 0,
        "tokens_totales": int(final[["tokens_entrada", "tokens_salida"]].sum().sum()),
        "pct_revision_humana": round(final["requiere_revision"].mean() * 100, 2),
        "pct_errores_llm": round((final["error"].fillna("") != "").mean() * 100, 2),
        "confianza_media": round(final["confianza"].mean(), 3),
        "preprocesamiento": reporte_prep,
    }

    if guardar:
        final.to_csv(DATA_PROC / f"casos_clasificados_{ts}.csv", index=False, encoding="utf-8-sig")
        for nombre, obj in evalr.items():
            if isinstance(obj, pd.DataFrame):
                obj.to_csv(OUTPUTS / f"{nombre}_{ts}.csv", index=bool(nombre.startswith("matriz")),
                           encoding="utf-8-sig")
        (OUTPUTS / f"metricas_{ts}.json").write_text(
            json.dumps({"operativo": operativo, "calidad": evalr.get("resumen", {})},
                       indent=2, ensure_ascii=False), encoding="utf-8")
        # copia estable para el dashboard
        final.to_csv(DATA_PROC / "casos_clasificados_latest.csv", index=False, encoding="utf-8-sig")

    return {"resultados": final, "evaluacion": evalr, "operativo": operativo, "timestamp": ts}
