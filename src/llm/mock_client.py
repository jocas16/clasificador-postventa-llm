"""Cliente offline determinista: simula al LLM con reglas + ruido controlado.

Sirve para (a) desarrollar y correr tests sin red ni GPU, y (b) tener una BASELINE
contra la cual comparar al LLM real. Si el LLM no le gana a esto, no vale la pena.
"""
from __future__ import annotations

import json
import random
import re
from typing import Dict, List

from ..preprocessing import quitar_acentos
from .base import BaseLLMClient

REGLAS = [
    (r"duplicad|dos veces|doble", ("Transferencias", "Transferencia duplicada", "ALTA", 0.93)),
    (r"no (llego|se acredito)|no recibio el dinero", ("Transferencias", "Transferencia no acreditada", "ALTA", 0.9)),
    (r"transferenc", ("Transferencias", "Transferencia con datos errados", "MEDIA", 0.7)),
    (r"rechazad|declinad|no se proceso", ("Pagos", "Pago rechazado", "MEDIA", 0.9)),
    (r"pendiente|demor|no se refleja", ("Pagos", "Pago demorado", "MEDIA", 0.86)),
    (r"no reconozco|cargo desconocido", ("Pagos", "Cobro no reconocido", "ALTA", 0.85)),
    (r"no (la )?recibo|no me llega|aun no recibo", ("Tarjetas", "Tarjeta no recibida", "MEDIA", 0.88)),
    (r"tarjeta.{0,20}bloquead|bloquead.{0,20}tarjeta", ("Tarjetas", "Tarjeta bloqueada", "ALTA", 0.8)),
    (r"adelantar|prepago|amortizar", ("Préstamos", "Pago anticipado", "BAJA", 0.9)),
    (r"refinanc|reprogram", ("Préstamos", "Refinanciamiento", "MEDIA", 0.85)),
    (r"prestamo|credito|cuota", ("Préstamos", "Problema con préstamo", "MEDIA", 0.82)),
    (r"aplicacion se cierra|app|aplicacion|pantalla", ("Canales digitales", "Error en aplicación", "MEDIA", 0.84)),
    (r"clave|token|no puedo ingresar", ("Canales digitales", "Acceso y clave", "MEDIA", 0.83)),
    (r"comision|mantenimiento|membresia", ("Comisiones", "Comisión no informada", "MEDIA", 0.8)),
    (r"devolucion|reembolso|extorno", ("Comisiones", "Solicitud de devolución", "MEDIA", 0.78)),
    (r"cerrar (mi )?cuenta|cancelar cuenta", ("Cuenta", "Cierre de cuenta", "MEDIA", 0.86)),
    (r"actualizar|cambiar (mi )?(direccion|telefono|correo)", ("Cuenta", "Actualización de datos", "BAJA", 0.85)),
    (r"tarjeta", ("Tarjetas", "Consumo no reconocido", "ALTA", 0.65)),
    (r"cuenta", ("Cuenta", "Problema con cuenta", "MEDIA", 0.8)),
    (r"pago|pagar", ("Pagos", "Pago rechazado", "MEDIA", 0.6)),
]


class MockLLMClient(BaseLLMClient):
    nombre = "mock"

    def __init__(self, modelo: str = "mock-reglas-v1", ruido: float = 0.05, seed: int = 42, **kw):
        super().__init__(modelo=modelo, **kw)
        self.ruido = ruido
        self._rng = random.Random(seed)

    def _call(self, mensajes: List[Dict[str, str]]) -> Dict:
        contenido = mensajes[-1]["content"]
        # Solo se evalua el cuerpo del caso: el canal no debe contaminar las reglas.
        m = re.search(r"Texto:\s*(.*)", contenido, flags=re.DOTALL)
        texto = quitar_acentos((m.group(1) if m else contenido).lower())
        cat, sub, pri, conf = "Otros", "No clasificable", "BAJA", 0.35
        for patron, (c, s, p, k) in REGLAS:
            if re.search(patron, texto):
                cat, sub, pri, conf = c, s, p, k
                break
        if self._rng.random() < self.ruido:  # simula el error del modelo real
            cat, sub, pri, conf = "Otros", "No clasificable", "BAJA", 0.40
        payload = {
            "categoria": cat,
            "subcategoria": sub,
            "prioridad": pri,
            "justificacion": "Coincidencia lexica con senales de la taxonomia (baseline offline).",
            "confianza": round(conf + self._rng.uniform(-0.03, 0.03), 2),
        }
        return {"text": json.dumps(payload, ensure_ascii=False), "in": len(texto) // 4, "out": 60}
