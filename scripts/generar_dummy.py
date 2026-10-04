"""Genera data dummy realista de casos de post-venta (con ruido: typos, textos vagos, PII)."""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

CANALES = ["App", "Web", "Call Center", "WhatsApp", "Agencia"]
PESOS_CANAL = [0.32, 0.2, 0.22, 0.16, 0.10]

PLANTILLAS = {
    ("Transferencias", "Transferencia duplicada", "ALTA"): [
        "Veo una transferencia duplicada en mi cuenta, me cobraron dos veces.",
        "Hice una sola transferencia pero aparece dos veces en mi estado de cuenta.",
        "Me descontaron el mismo monto dos veces por una transferencia.",
    ],
    ("Transferencias", "Transferencia no acreditada", "ALTA"): [
        "Transferi dinero y el destinatario no lo ha recibido.",
        "Mi transferencia no se acredito en la cuenta destino.",
    ],
    ("Transferencias", "Transferencia con datos errados", "MEDIA"): [
        "Transferi a una cuenta equivocada, digite mal el numero 00219348571234.",
        "Me equivoque de cuenta al transferir, necesito reversar.",
    ],
    ("Pagos", "Pago rechazado", "MEDIA"): [
        "Intente pagar pero la operacion fue rechazada.",
        "Mi pago fue declinado sin motivo aparente.",
    ],
    ("Pagos", "Pago demorado", "MEDIA"): [
        "El pago sigue pendiente y no se refleja en el sistema.",
        "Pague ayer y hasta ahora no se registra el pago.",
    ],
    ("Pagos", "Cobro no reconocido", "ALTA"): [
        "No reconozco un cargo en mi cuenta, hay un consumo que no hice.",
        "Aparece un cobro desconocido de S/ 350 en mi cuenta.",
    ],
    ("Tarjetas", "Tarjeta no recibida", "MEDIA"): [
        "Mi tarjeta debia llegar y todavia no la recibo.",
        "Solicite mi tarjeta hace tres semanas y aun no me llega.",
    ],
    ("Tarjetas", "Tarjeta bloqueada", "ALTA"): [
        "Mi tarjeta esta bloqueada y no puedo usarla.",
        "No puedo pagar, la tarjeta figura como bloqueada.",
    ],
    ("Tarjetas", "Consumo no reconocido", "ALTA"): [
        "Hay consumos con mi tarjeta que no reconozco, creo que la clonaron.",
        "Reporto un consumo no reconocido con mi tarjeta terminada en 4417.",
    ],
    ("Préstamos", "Problema con préstamo", "MEDIA"): [
        "Tengo un problema con mi credito, la cuota esta mal calculada.",
        "Mi cronograma de prestamo no coincide con lo pactado.",
    ],
    ("Préstamos", "Pago anticipado", "BAJA"): [
        "Quiero adelantar cuotas de mi prestamo.",
        "Deseo amortizar capital de mi credito personal.",
    ],
    ("Préstamos", "Refinanciamiento", "MEDIA"): [
        "Necesito reprogramar mi deuda, quiero refinanciar mi prestamo.",
        "Solicito refinanciamiento para reducir mi cuota mensual.",
    ],
    ("Cuenta", "Problema con cuenta", "MEDIA"): [
        "Tengo un problema con mi cuenta bancaria, aparece bloqueada.",
        "Mi saldo no coincide con mis movimientos.",
    ],
    ("Cuenta", "Actualización de datos", "BAJA"): [
        "Quiero actualizar mi telefono y correo registrados.",
        "Necesito cambiar mi direccion en el banco.",
    ],
    ("Cuenta", "Cierre de cuenta", "MEDIA"): [
        "Deseo cerrar mi cuenta de ahorros.",
        "Quiero cancelar cuenta que ya no uso.",
    ],
    ("Canales digitales", "Error en aplicación", "MEDIA"): [
        "La aplicacion se cierra cuando intento ingresar.",
        "El app no carga la pantalla de movimientos.",
    ],
    ("Canales digitales", "Acceso y clave", "MEDIA"): [
        "No puedo ingresar, mi clave digital no funciona.",
        "El token no me llega y no puedo acceder.",
    ],
    ("Comisiones", "Comisión no informada", "MEDIA"): [
        "Me cobraron una comision de mantenimiento que nadie me informo.",
        "Aparece una membresia que no acepte.",
    ],
    ("Comisiones", "Solicitud de devolución", "MEDIA"): [
        "Solicito la devolucion del cobro indebido.",
        "Pido el extorno del reembolso pendiente.",
    ],
    ("Otros", "No clasificable", "BAJA"): [
        "Hola", "Necesito ayuda por favor.", "Quisiera informacion.",
    ],
}

COLAS = ["", " Necesito ayuda.", " Es urgente para mi.", " No se que hacer.",
         " Esto ocurrio hoy.", " Por favor, necesito una solucion."]


def _typos(t: str, p: float, rng: random.Random) -> str:
    if rng.random() > p:
        return t
    palabras = t.split()
    if len(palabras) < 3:
        return t
    i = rng.randrange(len(palabras))
    w = palabras[i]
    if len(w) > 4:
        j = rng.randrange(1, len(w) - 1)
        palabras[i] = w[:j] + w[j + 1:]
    return " ".join(palabras)


def generar(n: int = 1000, seed: int = 42, pct_ambiguos: float = 0.06) -> pd.DataFrame:
    rng = random.Random(seed)
    claves = list(PLANTILLAS.keys())
    pesos = [1.0 if k[0] != "Otros" else pct_ambiguos * len(claves) for k in claves]
    filas = []
    inicio = date(2026, 1, 1)
    for i in range(1, n + 1):
        cat, sub, pri = rng.choices(claves, weights=pesos, k=1)[0]
        texto = rng.choice(PLANTILLAS[(cat, sub, pri)]) + rng.choice(COLAS)
        texto = _typos(texto, 0.18, rng)
        if rng.random() < 0.25:
            texto = texto.lower()
        filas.append({
            "id_caso": f"CASO_{i:05d}",
            "fecha": (inicio + timedelta(days=rng.randrange(0, 250))).isoformat(),
            "canal": rng.choices(CANALES, weights=PESOS_CANAL, k=1)[0],
            "texto_caso": texto,
            "categoria_real": cat,
            "subcategoria_real": sub,
            "prioridad_real": pri,
            "taxonomy_version": "v1.0",
        })
    return pd.DataFrame(filas).sample(frac=1, random_state=seed).reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--salida", default=str(Path(__file__).resolve().parents[1] / "data/raw/casos_postventa.csv"))
    a = ap.parse_args()
    df = generar(a.n, a.seed)
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.salida, index=False, encoding="utf-8-sig")
    print(f"{len(df)} casos generados en {a.salida}")
    print(df["categoria_real"].value_counts())
