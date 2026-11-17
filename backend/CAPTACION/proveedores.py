"""Proveedores externos de la captación: RENIEC, listas restrictivas, PEP, biometría y
centrales de riesgo. Ninguno está contratado todavía, así que aquí hay un simulador
determinista; cuando exista el servicio real se reemplaza esta clase y nada más.

Documentos de prueba:
- 99999999: aparece en listas restrictivas (RECHAZADO).
- 88888880: es persona expuesta políticamente (OBSERVADO).
- Centrales: el último dígito del documento fija la calificación
  (0 a 6 NORMAL, 7 CPP, 8 DEFICIENTE, 9 DUDOSO).
"""

from decimal import Decimal

NOMBRE = "SIMULADO"
LISTA_RESTRICTIVA = {"99999999"}
PEP = {"88888880"}


def validar(tipo: str, tipo_documento: str, numero_documento: str) -> tuple[str, str]:
    """Devuelve (resultado, detalle)."""
    if tipo == "RENIEC":
        if tipo_documento != "DNI":
            return "OBSERVADO", "Documento no DNI: requiere verificación presencial en Migraciones"
        return "APROBADO", "Identidad confirmada en RENIEC"
    if tipo == "LISTAS_NEGRAS":
        if numero_documento in LISTA_RESTRICTIVA:
            return "RECHAZADO", "Documento registrado en listas restrictivas"
        return "APROBADO", "Sin coincidencias en listas restrictivas"
    if tipo == "PEP":
        if numero_documento in PEP:
            return "OBSERVADO", "Persona expuesta políticamente: debida diligencia reforzada"
        return "APROBADO", "No es persona expuesta políticamente"
    if tipo == "BIOMETRIA":
        return "APROBADO", "Coincidencia biométrica confirmada"
    raise ValueError(f"Tipo de validación no soportado: {tipo}")


def consultar_central(numero_documento: str) -> dict:
    digitos = "".join(c for c in numero_documento if c.isdigit()) or "0"
    n = int(digitos)
    ultimo = n % 10
    calificacion = ("NORMAL" if ultimo <= 6 else "CPP" if ultimo == 7
                    else "DEFICIENTE" if ultimo == 8 else "DUDOSO")
    return {
        "calificacion": calificacion,
        "deuda_total": Decimal((n % 7) * 1500).quantize(Decimal("0.01")),
        "entidades": n % 4,
        "dias_mora": {"NORMAL": 0, "CPP": 15, "DEFICIENTE": 45, "DUDOSO": 90}[calificacion],
    }


# ── Perfil de riesgo ──────────────────────────────────────────────────────
PENALIDAD_SBS = {"NORMAL": 0, "CPP": 250, "DEFICIENTE": 450, "DUDOSO": 650, "PERDIDA": 850}


def puntaje(reportes: list[dict], observadas: list[str]) -> tuple[int, str, str]:
    """Puntaje de 0 a 1000 (más alto, menos riesgo), calificación y observación.

    reportes: dicts con calificacion, deuda_total, entidades y dias_mora.
    observadas: tipos de validación cuyo último resultado es OBSERVADO.
    """
    if not reportes:
        raise ValueError("Se necesita al menos una consulta a centrales")
    peor = max(reportes, key=lambda r: PENALIDAD_SBS[r["calificacion"]])
    deuda = sum((Decimal(r["deuda_total"]) for r in reportes), Decimal("0")) / len(reportes)
    valor = 1000 - PENALIDAD_SBS[peor["calificacion"]]
    valor -= min(200, int(deuda / 100))
    valor -= min(150, max(0, int(peor["entidades"]) - 3) * 50)
    valor -= min(200, int(peor["dias_mora"]) * 2)
    notas = [f"Peor calificación {peor['calificacion']}"]
    for tipo in observadas:
        valor -= 100 if tipo == "PEP" else 50
        notas.append(f"{tipo} observado")
    valor = max(0, min(1000, valor))
    if peor["calificacion"] in ("DUDOSO", "PERDIDA") or valor < 350:
        calificacion = "MUY_ALTO"
    elif valor < 550:
        calificacion = "ALTO"
    elif valor < 750:
        calificacion = "MEDIO"
    else:
        calificacion = "BAJO"
    return valor, calificacion, "; ".join(notas)[:200]
