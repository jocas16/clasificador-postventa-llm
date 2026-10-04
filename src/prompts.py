"""Ingenieria de prompt: instrucciones + taxonomia + few-shot + salida JSON estricta."""
from __future__ import annotations

from .config import Taxonomy

SYSTEM_PROMPT = """Eres un analista senior de post-venta de un banco. Tu tarea es tipificar casos
de clientes segun una taxonomia oficial. Eres preciso, conservador y NUNCA inventas categorias.

Reglas:
1. Usa EXCLUSIVAMENTE las categorias y subcategorias de la taxonomia entregada, con su texto exacto.
2. La subcategoria debe pertenecer a la categoria elegida.
3. Prioridad: ALTA si hay riesgo de fraude, dinero no acreditado, duplicado o bloqueo total del
   servicio; MEDIA si afecta la operativa pero tiene solucion estandar; BAJA si es consulta,
   solicitud o gestion sin impacto economico inmediato.
4. Si el texto es ambiguo, insuficiente o no encaja, usa categoria "Otros" / "No clasificable"
   y una confianza baja.
5. La justificacion debe ser breve (maximo 25 palabras) y citar la evidencia del texto.
6. La confianza es un numero entre 0.0 y 1.0 que refleja tu certeza real. Se honesto: si dudas
   entre dos subcategorias, usa un valor menor a 0.7.
7. Responde UNICAMENTE con un objeto JSON valido, sin markdown, sin ```json, sin texto adicional.

Formato de salida obligatorio:
{"categoria": "...", "subcategoria": "...", "prioridad": "ALTA|MEDIA|BAJA", "justificacion": "...", "confianza": 0.0}
"""

FEW_SHOTS = [
    (
        "Canal: App\nTexto: Hice una transferencia y me la cobraron dos veces, necesito que me devuelvan el dinero.",
        '{"categoria": "Transferencias", "subcategoria": "Transferencia duplicada", "prioridad": "ALTA", '
        '"justificacion": "El cliente reporta doble cobro de una misma transferencia.", "confianza": 0.95}',
    ),
    (
        "Canal: Web\nTexto: Quiero saber si puedo adelantar cuotas de mi prestamo vehicular.",
        '{"categoria": "Préstamos", "subcategoria": "Pago anticipado", "prioridad": "BAJA", '
        '"justificacion": "Consulta sobre adelanto de cuotas, sin incidencia ni impacto economico.", "confianza": 0.92}',
    ),
    (
        "Canal: WhatsApp\nTexto: hola",
        '{"categoria": "Otros", "subcategoria": "No clasificable", "prioridad": "BAJA", '
        '"justificacion": "Texto sin informacion suficiente para tipificar.", "confianza": 0.30}',
    ),
]


def construir_system_prompt(tax: Taxonomy) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\nTAXONOMIA OFICIAL (version {tax.version}):\n{tax.as_prompt_block()}\n"
    )


def construir_user_prompt(canal: str, texto: str) -> str:
    return f"Canal: {canal}\nTexto: {texto}\n\nDevuelve solo el JSON."


def construir_mensajes(tax: Taxonomy, canal: str, texto: str, con_few_shot: bool = True):
    msgs = [{"role": "system", "content": construir_system_prompt(tax)}]
    if con_few_shot:
        for u, a in FEW_SHOTS:
            msgs.append({"role": "user", "content": u})
            msgs.append({"role": "assistant", "content": a})
    msgs.append({"role": "user", "content": construir_user_prompt(canal, texto)})
    return msgs
