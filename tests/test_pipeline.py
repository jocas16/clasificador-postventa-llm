import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.classifier import Clasificador, extraer_json
from src.config import Settings, Taxonomy
from src.llm.mock_client import MockLLMClient
from src.preprocessing import enmascarar_pii, normalizar_etiqueta, preprocesar


def test_extraer_json_con_markdown():
    assert extraer_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extraer_json_con_preambulo():
    assert extraer_json('Claro, aqui tienes: {"a": 1} espero ayude') == {"a": 1}


def test_extraer_json_invalido():
    assert extraer_json("no soy json") is None


def test_normalizar_etiqueta_ignora_acentos():
    assert normalizar_etiqueta("Préstamos") == normalizar_etiqueta("prestamos")


def test_enmascarar_pii():
    t = enmascarar_pii("mi tarjeta 4532015112830366 y correo juan@mail.com")
    assert "4532015112830366" not in t and "juan@mail.com" not in t


def test_preprocesar_marca_invalidos():
    df = pd.DataFrame({"id_caso": ["A", "B"], "fecha": ["2026-01-01"] * 2,
                       "canal": ["App"] * 2, "texto_caso": ["hola", "Mi tarjeta no llega aun"]})
    out, rep = preprocesar(df)
    assert rep["invalidos"] == 1 and out.loc[out.id_caso == "B", "valido"].item()


def test_clasificador_devuelve_etiqueta_valida():
    tax = Taxonomy()
    clf = Clasificador(MockLLMClient(), tax, Settings())
    c = clf.clasificar_uno("A1", "App", "Veo una transferencia duplicada en mi cuenta")
    assert tax.es_valido(c.categoria, c.subcategoria)
    assert c.prioridad in tax.prioridades and 0 <= c.confianza <= 1


def test_guardarrail_categoria_fuera_de_taxonomia():
    tax = Taxonomy()
    clf = Clasificador(MockLLMClient(), tax, Settings())
    cat, sub, motivo = clf._canonizar("Fraude Interno", "Algo inventado")
    assert (cat, sub) == ("Otros", "No clasificable") and motivo


def test_correccion_por_jerarquia():
    tax = Taxonomy()
    clf = Clasificador(MockLLMClient(), tax, Settings())
    cat, sub, motivo = clf._canonizar("Pagos", "Transferencia duplicada")
    assert cat == "Transferencias" and motivo == "categoria_corregida_por_subcategoria"
