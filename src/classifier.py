"""Orquestador de clasificacion: llamada al LLM, parseo robusto, validacion y guardarrailes."""
from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import pandas as pd

from .config import Settings, Taxonomy, settings as default_settings
from .llm.base import BaseLLMClient
from .preprocessing import normalizar_etiqueta
from .prompts import construir_mensajes
from .schemas import Clasificacion

log = logging.getLogger(__name__)

FALLBACK = ("Otros", "No clasificable", "BAJA")


def extraer_json(texto: str) -> Optional[Dict[str, Any]]:
    """Parseo defensivo: el modelo puede devolver ```json, texto previo o comillas raras."""
    if not texto:
        return None
    t = texto.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)  # primer objeto JSON del texto
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


class Clasificador:
    def __init__(self, client: BaseLLMClient, tax: Taxonomy, s: Settings | None = None,
                 usar_cache: bool = True):
        self.client = client
        self.tax = tax
        self.s = s or default_settings
        self.usar_cache = usar_cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        # mapas canonicos para tolerar acentos/mayusculas del modelo
        self._map_cat = {normalizar_etiqueta(c): c for c in tax.categorias}
        self._map_sub = {
            normalizar_etiqueta(s_): (c, s_) for c in tax.categorias for s_ in tax.subcategorias(c)
        }

    # ------------------------------------------------------------------ #
    def _canonizar(self, cat: str, sub: str) -> tuple[str, str, str]:
        """Devuelve (categoria, subcategoria, motivo_correccion)."""
        cat_c = self._map_cat.get(normalizar_etiqueta(cat))
        par = self._map_sub.get(normalizar_etiqueta(sub))
        if cat_c and par and par[0] == cat_c:
            return cat_c, par[1], ""
        if par:  # subcategoria valida pero categoria mal puesta -> se corrige por jerarquia
            return par[0], par[1], "categoria_corregida_por_subcategoria"
        if cat_c:
            return cat_c, FALLBACK[1], "subcategoria_invalida"
        return FALLBACK[0], FALLBACK[1], "etiqueta_fuera_de_taxonomia"

    def clasificar_uno(self, id_caso: str, canal: str, texto: str, reintentos: int = 2) -> Clasificacion:
        clave = f"{canal}||{texto}"
        if self.usar_cache and clave in self._cache:
            c = Clasificacion(**{**self._cache[clave], "id_caso": id_caso})
            c.extra["cache_hit"] = True
            return c

        mensajes = construir_mensajes(self.tax, canal, texto)
        ultimo_error = ""
        for intento in range(1, reintentos + 2):
            try:
                resp = self.client.chat(mensajes)
                data = extraer_json(resp.text)
                if data is None:
                    raise ValueError("respuesta_no_json")

                cat, sub, motivo = self._canonizar(
                    str(data.get("categoria", "")), str(data.get("subcategoria", ""))
                )
                pri = str(data.get("prioridad", "")).upper().strip()
                if pri not in self.tax.prioridades:
                    pri = self.tax.prioridad_sugerida(cat, sub) or "MEDIA"
                    motivo = (motivo + "|prioridad_invalida").strip("|")
                try:
                    conf = float(data.get("confianza", 0.0))
                except (TypeError, ValueError):
                    conf = 0.0
                conf = min(max(conf, 0.0), 1.0)

                revision = bool(motivo) or conf < self.s.confidence_threshold
                if not motivo and revision:
                    motivo = "confianza_bajo_umbral"

                c = Clasificacion(
                    id_caso=id_caso, categoria=cat, subcategoria=sub, prioridad=pri,
                    justificacion=str(data.get("justificacion", ""))[:300],
                    confianza=round(conf, 3), requiere_revision=revision, motivo_revision=motivo,
                    modelo=resp.modelo, proveedor=resp.proveedor, latencia_ms=resp.latencia_ms,
                    tokens_entrada=resp.tokens_entrada, tokens_salida=resp.tokens_salida,
                    intentos=intento,
                )
                if self.usar_cache:
                    d = c.to_dict(); d.pop("id_caso")
                    self._cache[clave] = d
                return c
            except Exception as e:  # red, rate limit, JSON invalido
                ultimo_error = f"{type(e).__name__}: {e}"
                log.warning("Caso %s intento %s fallo: %s", id_caso, intento, ultimo_error)
                time.sleep(min(2 ** intento, 8))  # backoff exponencial

        return Clasificacion(
            id_caso=id_caso, categoria=FALLBACK[0], subcategoria=FALLBACK[1], prioridad=FALLBACK[2],
            justificacion="No se pudo obtener respuesta valida del modelo.", confianza=0.0,
            requiere_revision=True, motivo_revision="error_llm", modelo=self.client.modelo,
            proveedor=self.client.nombre, intentos=reintentos + 1, error=ultimo_error,
        )

    # ------------------------------------------------------------------ #
    def clasificar_lote(self, df: pd.DataFrame, col_texto: str = "texto_llm",
                        max_workers: int | None = None) -> pd.DataFrame:
        """Clasifica solo las filas validas; las invalidas van directo a revision humana."""
        workers = max_workers or self.s.max_workers
        validos = df[df.get("valido", True)]
        invalidos = df[~df.get("valido", True)]

        filas: List[Clasificacion] = []
        if len(validos):
            args = list(zip(validos["id_caso"], validos["canal"], validos[col_texto]))
            if workers > 1:
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    filas = list(ex.map(lambda a: self.clasificar_uno(*a), args))
            else:
                filas = [self.clasificar_uno(*a) for a in args]

        for _, r in invalidos.iterrows():
            filas.append(Clasificacion(
                id_caso=r["id_caso"], categoria=FALLBACK[0], subcategoria=FALLBACK[1],
                prioridad=FALLBACK[2], justificacion="Texto insuficiente para tipificar.",
                confianza=0.0, requiere_revision=True, motivo_revision="texto_insuficiente",
                modelo=self.client.modelo, proveedor=self.client.nombre,
            ))
        return pd.DataFrame([c.to_dict() for c in filas])
