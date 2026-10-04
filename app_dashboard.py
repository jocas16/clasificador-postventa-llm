"""Dashboard operativo (Streamlit).  Ejecutar:  streamlit run app_dashboard.py"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import DATA_PROC
from src.evaluation import (calibracion_confianza, curva_automatizacion, errores_frecuentes,
                            matriz_confusion, metricas_nivel)

st.set_page_config(page_title="Tipificacion Post-Venta | LLM", layout="wide")
RUTA = DATA_PROC / "casos_clasificados_latest.csv"


@st.cache_data
def cargar(p: Path) -> pd.DataFrame:
    return pd.read_csv(p)


st.title("Tipificacion automatica de casos de post-venta")

if not RUTA.exists():
    st.warning("Primero ejecuta:  python scripts/run_pipeline.py --datos data/raw/casos_postventa.csv")
    st.stop()

df = cargar(RUTA)

with st.sidebar:
    st.header("Filtros")
    canales = st.multiselect("Canal", sorted(df["canal"].dropna().unique()))
    cats = st.multiselect("Categoria predicha", sorted(df["categoria"].dropna().unique()))
    umbral = st.slider("Umbral de confianza para automatizar", 0.0, 1.0, 0.70, 0.05)
    solo_revision = st.checkbox("Solo casos en revision humana")

f = df.copy()
if canales:
    f = f[f["canal"].isin(canales)]
if cats:
    f = f[f["categoria"].isin(cats)]
if solo_revision:
    f = f[f["confianza"] < umbral]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Casos", len(f))
c2.metric("Confianza media", f"{f['confianza'].mean():.2f}" if len(f) else "-")
c3.metric("Automatizables", f"{(f['confianza'] >= umbral).mean()*100:.1f}%" if len(f) else "-")
c4.metric("Prioridad ALTA", int((f["prioridad"] == "ALTA").sum()))
c5.metric("Latencia p95 (ms)", int(f["latencia_ms"].quantile(0.95)) if len(f) else 0)

t1, t2, t3, t4 = st.tabs(["Volumen", "Calidad del modelo", "Cola de revision", "Detalle"])

with t1:
    a, b = st.columns(2)
    a.subheader("Casos por categoria")
    a.bar_chart(f["categoria"].value_counts())
    b.subheader("Casos por prioridad")
    b.bar_chart(f["prioridad"].value_counts())
    st.subheader("Volumen por canal y categoria")
    st.dataframe(pd.crosstab(f["canal"], f["categoria"]), width=1200)

with t2:
    if "categoria_real" in f.columns:
        for nivel, (r, p) in {"Categoria": ("categoria_real", "categoria"),
                              "Subcategoria": ("subcategoria_real", "subcategoria"),
                              "Prioridad": ("prioridad_real", "prioridad")}.items():
            st.write(f"**{nivel}**", metricas_nivel(f, r, p))
        st.subheader("Errores mas frecuentes")
        st.dataframe(errores_frecuentes(f, "subcategoria_real", "subcategoria"), width=True)
        st.subheader("Calibracion de la confianza")
        st.dataframe(calibracion_confianza(f, "subcategoria_real", "subcategoria"), width=True)
        st.subheader("Curva de automatizacion")
        st.dataframe(curva_automatizacion(f, "subcategoria_real", "subcategoria"), width=True)
        st.subheader("Matriz de confusion (categoria)")
        st.dataframe(matriz_confusion(f, "categoria_real", "categoria"), width=True)
    else:
        st.info("El dataset no tiene etiquetas reales: solo metricas operativas.")

with t3:
    cola = f[f["confianza"] < umbral].sort_values("confianza")
    st.write(f"{len(cola)} casos requieren revision humana con umbral {umbral:.2f}")
    st.dataframe(cola[["id_caso", "canal", "texto_caso", "categoria", "subcategoria",
                       "prioridad", "confianza", "motivo_revision"]], width=True)

with t4:
    st.dataframe(f, width=True)
    st.download_button("Descargar CSV filtrado", f.to_csv(index=False).encode("utf-8-sig"),
                       "casos_filtrados.csv", "text/csv")
