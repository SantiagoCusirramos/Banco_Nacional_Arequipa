"""Datos sintéticos del simulador de pruebas. Ningún dato corresponde a personas reales."""
from decimal import Decimal

CLIENTES = {
    "CLI-0001": {"nombre": "Ana Lucía Quispe Mamani", "documento": "70000001"},
    "CLI-0002": {"nombre": "Luis Alberto Huamán Condori", "documento": "70000002"},
    "CLI-0003": {"nombre": "Rosa Elena Ccama Apaza", "documento": "70000003"},
    "CLI-0004": {"nombre": "Jorge Luis Puma Vilca", "documento": "70000004"},
    "CLI-0005": {"nombre": "María Fernanda Choque Torres", "documento": "70000005"},
    "CLI-0006": {"nombre": "Pedro Pablo Mamani Ríos", "documento": "70000006"},
    "CLI-0007": {"nombre": "Carmen Rosa Flores Sucasaire", "documento": "70000007"},
    "CLI-0008": {"nombre": "Víctor Hugo Zapana Larico", "documento": "70000008"},
}

# Como las publica Evaluación (CR-INT-04). La tasa es una fracción; los ids de solicitud son UUID de SOL.
APROBACIONES = [
    {"id": "APR-2026-0001", "credito": "CRE-2026-0001", "cliente": "CLI-0001", "producto": "Crédito Personal",
     "importe": Decimal("10000.00"), "moneda": "PEN", "plazo": 24, "tea": "0.2200", "estado": "VIGENTE", "dias": 25},
    {"id": "APR-2026-0002", "credito": "CRE-2026-0002", "cliente": "CLI-0002", "producto": "Crédito Vehicular",
     "importe": Decimal("5000.00"), "moneda": "USD", "plazo": 36, "tea": "0.1450", "estado": "VIGENTE", "dias": 20},
    {"id": "APR-2026-0003", "credito": "CRE-2026-0003", "cliente": "CLI-0003", "producto": "Crédito Personal",
     "importe": Decimal("3500.00"), "moneda": "PEN", "plazo": 12, "tea": "0.2800", "estado": "VIGENTE", "dias": -3},
    {"id": "APR-2026-0004", "credito": "CRE-2026-0004", "cliente": "CLI-0004", "producto": "Crédito MYPE",
     "importe": Decimal("15000.00"), "moneda": "PEN", "plazo": 18, "tea": "0.2450", "estado": "REVOCADA", "dias": 10},
    {"id": "APR-2026-0005", "credito": "CRE-2026-0005", "cliente": "CLI-0005", "producto": "Crédito MYPE",
     "importe": Decimal("25000.00"), "moneda": "PEN", "plazo": 36, "tea": "0.2100", "estado": "VIGENTE", "dias": 28},
    {"id": "APR-2026-0006", "credito": "CRE-2026-0006", "cliente": "CLI-0006", "producto": "Crédito Personal",
     "importe": Decimal("8000.00"), "moneda": "PEN", "plazo": 24, "tea": "0.2300", "estado": "VIGENTE", "dias": 15},
    {"id": "APR-2026-0007", "credito": "CRE-2026-0007", "cliente": "CLI-0007", "producto": "Crédito Personal",
     "importe": Decimal("6000.00"), "moneda": "PEN", "plazo": 12, "tea": "0.2600", "estado": "VIGENTE", "dias": 18},
    {"id": "APR-2026-0008", "credito": "CRE-2026-0008", "cliente": "CLI-0008", "producto": "Crédito Personal",
     "importe": Decimal("12000.00"), "moneda": "PEN", "plazo": 30, "tea": "0.2150", "estado": "VIGENTE", "dias": 22},
]

# Como las devuelve CUENTAS (CuentaOut). `comportamiento`: cómo responde COREDB al depósito.
CUENTAS = [
    ("21500012344521", "CLI-0001", "PEN", "ACTIVA", "INDIVIDUAL", None),
    ("21500087657730", "CLI-0001", "USD", "ACTIVA", "INDIVIDUAL", None),
    ("21500011119812", "CLI-0001", "PEN", "BLOQUEADA", "INDIVIDUAL", None),
    ("21500033336019", "CLI-0001", "PEN", "ACTIVA", "MANCOMUNADA_INDISTINTA", None),
    ("21500055558841", "CLI-0002", "USD", "ACTIVA", "INDIVIDUAL", None),
    ("21500066663307", "CLI-0002", "PEN", "ACTIVA", "INDIVIDUAL", None),
    ("21500077771145", "CLI-0003", "PEN", "ACTIVA", "INDIVIDUAL", None),
    ("21500088882290", "CLI-0004", "PEN", "ACTIVA", "INDIVIDUAL", None),
    ("21500099995563", "CLI-0005", "PEN", "ACTIVA", "INDIVIDUAL", "TIMEOUT_REGISTRADO"),
    ("21500010106678", "CLI-0006", "PEN", "ACTIVA", "INDIVIDUAL", "RECHAZO"),
    ("21500011117734", "CLI-0007", "PEN", "ACTIVA", "INDIVIDUAL", None),
    ("21500012128856", "CLI-0008", "PEN", "ACTIVA", "INDIVIDUAL", None),
    ("21500013134402", "CLI-0008", "PEN", "ACTIVA", "INDIVIDUAL", None),
]

# Usuarios de COREDB (contraseña de desarrollo). El de servicio entra con su secreto.
CONTRASENA = "Demo2026!"
USUARIOS = {
    "operador1": {"rol": "OPERADOR", "modulo": None},
    "operador2": {"rol": "OPERADOR", "modulo": None},
    "supervisor1": {"rol": "ADMINISTRADOR", "modulo": None},
    "supervisor2": {"rol": "ADMINISTRADOR", "modulo": None},
    "auditor1": {"rol": "AUDITOR", "modulo": None},
    "asesor1": {"rol": "ASESOR", "modulo": None},
    "svc-desembolso": {"rol": "SERVICIO", "modulo": "DESEMBOLSO"},
}
SECRETO_SERVICIO = "secreto-de-prueba-svc-desembolso"
CLAVE_COBRANZA = "clave-integracion-de-prueba"
