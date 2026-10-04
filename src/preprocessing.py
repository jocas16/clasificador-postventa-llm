"""Limpieza, validaciones y enmascarado de PII antes de enviar texto al LLM."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Dict, List, Tuple

import pandas as pd

COLUMNAS_MINIMAS = ["id_caso", "fecha", "canal", "texto_caso"]
LONGITUD_MINIMA = 10  # caracteres utiles

# --- Patrones de PII tipicos en banca (Peru) ---
PATRONES_PII: Dict[str, re.Pattern] = {
    "[TARJETA]": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "[CUENTA]": re.compile(r"\b\d{10,20}\b"),
    "[DNI]": re.compile(r"\b\d{8}\b"),
    "[EMAIL]": re.compile(r"\b[\w\.\-]+@[\w\-]+\.[a-zA-Z]{2,}\b"),
    "[TELEFONO]": re.compile(r"\b9\d{8}\b"),
}


def quitar_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_etiqueta(etiqueta: str | None) -> str:
    """Clave canonica para comparar etiquetas sin importar acentos/mayusculas/espacios."""
    if etiqueta is None or (isinstance(etiqueta, float) and pd.isna(etiqueta)):
        return ""
    return re.sub(r"\s+", " ", quitar_acentos(str(etiqueta)).lower().strip())


def enmascarar_pii(texto: str) -> str:
    out = texto
    for token, patron in PATRONES_PII.items():
        out = patron.sub(token, out)
    return out


def limpiar_texto(texto: str) -> str:
    texto = str(texto).replace("\u00a0", " ")
    texto = re.sub(r"https?://\S+", "[URL]", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def hash_texto(texto: str) -> str:
    return hashlib.sha1(normalizar_etiqueta(texto).encode("utf-8")).hexdigest()[:16]


def validar_esquema(df: pd.DataFrame) -> None:
    faltantes = [c for c in COLUMNAS_MINIMAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {faltantes}")


def preprocesar(df: pd.DataFrame, deduplicar: bool = True) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Devuelve (df_limpio, reporte). Los casos invalidos NO se envian al LLM."""
    validar_esquema(df)
    n0 = len(df)
    out = df.copy()

    out["texto_limpio"] = out["texto_caso"].fillna("").map(limpiar_texto)
    out["texto_llm"] = out["texto_limpio"].map(enmascarar_pii)
    out["hash_texto"] = out["texto_llm"].map(hash_texto)
    out["len_texto"] = out["texto_limpio"].str.len()

    out["valido"] = out["len_texto"] >= LONGITUD_MINIMA
    out.loc[~out["valido"], "motivo_invalido"] = "texto_insuficiente"

    dups_id = int(out["id_caso"].duplicated().sum())
    if dups_id:
        out = out.drop_duplicates(subset=["id_caso"], keep="first")

    dups_texto = 0
    if deduplicar:
        dups_texto = int(out["hash_texto"].duplicated().sum())
        out["es_duplicado_texto"] = out["hash_texto"].duplicated(keep="first")
    else:
        out["es_duplicado_texto"] = False

    reporte = {
        "filas_entrada": n0,
        "filas_salida": len(out),
        "ids_duplicados_eliminados": dups_id,
        "textos_duplicados_detectados": dups_texto,
        "invalidos": int((~out["valido"]).sum()),
    }
    return out.reset_index(drop=True), reporte
