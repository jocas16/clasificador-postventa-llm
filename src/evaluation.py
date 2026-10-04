"""Evaluacion: accuracy, F1 macro/ponderado, reporte por clase, matriz de confusion,
calibracion de confianza y simulacion de automatizacion por umbral."""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, classification_report, cohen_kappa_score,
                             confusion_matrix, f1_score)

from .preprocessing import normalizar_etiqueta


def _alinear(df: pd.DataFrame, col_real: str, col_pred: str) -> pd.DataFrame:
    d = df.dropna(subset=[col_real]).copy()
    d["_y"] = d[col_real].map(normalizar_etiqueta)
    d["_p"] = d[col_pred].map(normalizar_etiqueta)
    return d[(d["_y"] != "") & (d["_p"] != "")]


def metricas_nivel(df: pd.DataFrame, col_real: str, col_pred: str) -> Dict[str, float]:
    d = _alinear(df, col_real, col_pred)
    if d.empty:
        return {}
    y, p = d["_y"], d["_p"]
    return {
        "n": int(len(d)),
        "accuracy": round(accuracy_score(y, p), 4),
        "f1_macro": round(f1_score(y, p, average="macro", zero_division=0), 4),
        "f1_weighted": round(f1_score(y, p, average="weighted", zero_division=0), 4),
        "kappa": round(cohen_kappa_score(y, p), 4),
    }


def reporte_por_clase(df: pd.DataFrame, col_real: str, col_pred: str) -> pd.DataFrame:
    d = _alinear(df, col_real, col_pred)
    rep = classification_report(d["_y"], d["_p"], output_dict=True, zero_division=0)
    out = pd.DataFrame(rep).T.reset_index().rename(columns={"index": "clase"})
    return out.round(4)


def matriz_confusion(df: pd.DataFrame, col_real: str, col_pred: str) -> pd.DataFrame:
    d = _alinear(df, col_real, col_pred)
    etiquetas = sorted(set(d["_y"]) | set(d["_p"]))
    m = confusion_matrix(d["_y"], d["_p"], labels=etiquetas)
    return pd.DataFrame(m, index=[f"real::{e}" for e in etiquetas],
                        columns=[f"pred::{e}" for e in etiquetas])


def errores_frecuentes(df: pd.DataFrame, col_real: str, col_pred: str, top: int = 15) -> pd.DataFrame:
    d = _alinear(df, col_real, col_pred)
    err = d[d["_y"] != d["_p"]]
    if err.empty:
        return pd.DataFrame(columns=["real", "predicho", "casos"])
    g = (err.groupby([col_real, col_pred]).size().reset_index(name="casos")
         .sort_values("casos", ascending=False).head(top))
    return g.rename(columns={col_real: "real", col_pred: "predicho"})


def calibracion_confianza(df: pd.DataFrame, col_real: str, col_pred: str,
                          bins: List[float] | None = None) -> pd.DataFrame:
    """Un modelo bien calibrado acierta ~90% cuando dice 0.9. Aqui se verifica."""
    d = _alinear(df, col_real, col_pred).copy()
    d["acierto"] = (d["_y"] == d["_p"]).astype(int)
    bins = bins or [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    d["bucket"] = pd.cut(d["confianza"], bins=bins, right=False)
    g = d.groupby("bucket", observed=True).agg(
        casos=("acierto", "size"), accuracy=("acierto", "mean"),
        confianza_media=("confianza", "mean")).reset_index()
    g["bucket"] = g["bucket"].astype(str)
    g["gap_calibracion"] = (g["confianza_media"] - g["accuracy"]).round(4)
    return g.round(4)


def curva_automatizacion(df: pd.DataFrame, col_real: str, col_pred: str,
                         umbrales: List[float] | None = None) -> pd.DataFrame:
    """Trade-off del negocio: cuanto se automatiza vs con que precision, por umbral."""
    d = _alinear(df, col_real, col_pred).copy()
    d["acierto"] = (d["_y"] == d["_p"]).astype(int)
    filas = []
    for u in (umbrales or [0.5, 0.6, 0.7, 0.8, 0.9]):
        auto = d[d["confianza"] >= u]
        filas.append({
            "umbral": u,
            "pct_automatizado": round(len(auto) / len(d) * 100, 2) if len(d) else 0,
            "accuracy_automatizado": round(auto["acierto"].mean(), 4) if len(auto) else np.nan,
            "casos_a_revision_humana": int(len(d) - len(auto)),
        })
    return pd.DataFrame(filas)


def evaluar_todo(df: pd.DataFrame) -> Dict[str, pd.DataFrame | Dict]:
    """df debe traer las columnas reales y las predichas ya unidas."""
    res: Dict[str, pd.DataFrame | Dict] = {}
    res["resumen"] = {
        "categoria": metricas_nivel(df, "categoria_real", "categoria"),
        "subcategoria": metricas_nivel(df, "subcategoria_real", "subcategoria"),
        "prioridad": metricas_nivel(df, "prioridad_real", "prioridad"),
    }
    res["reporte_categoria"] = reporte_por_clase(df, "categoria_real", "categoria")
    res["reporte_subcategoria"] = reporte_por_clase(df, "subcategoria_real", "subcategoria")
    res["matriz_categoria"] = matriz_confusion(df, "categoria_real", "categoria")
    res["errores_top"] = errores_frecuentes(df, "subcategoria_real", "subcategoria")
    res["calibracion"] = calibracion_confianza(df, "subcategoria_real", "subcategoria")
    res["automatizacion"] = curva_automatizacion(df, "subcategoria_real", "subcategoria")
    return res
