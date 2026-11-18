"""Envía a Evaluación un expediente con el formato exacto de SOL, para demostraciones y pruebas.

En el producto SOL envía sus expedientes por el Bus. Este script arma, sin pasar por SOL, un sobre
CR-INT-02 con el propio código de SOL (su política y `SOL.finance.calendar`) y lo entrega como lo hace
SOL; sirve para probar Evaluación sola.

    python -m EVALUACION.scripts.enviar_expediente_demo --cliente CLI000000001 --documento 70000001 \
        --nombres Juan --paterno Perez --materno Quispe --monto 15000.00 --plazo 12

Variables: EVALUACION_URL (http://127.0.0.1:8015) y EVALUACION_TOKEN_SOL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import httpx

import SOL
from SOL.finance import calendar
from SOL.policy import load_policy

POLITICA = Path(SOL.__file__).resolve().parent / "config" / "politica_demo.json"
VERSION_CONTRATO = "CR-INT-02-PROPUESTA-v2"


def sobre_de_sol(*, id_cliente: str, numero_documento: str, nombres: str, apellido_paterno: str,
                 apellido_materno: str | None = None, monto: str = "15000.00", plazo_meses: int = 12,
                 destino: str = "Mejoras en la vivienda", fecha_base: date | None = None,
                 id_solicitud: str | None = None, version_solicitud: int = 1, id_operacion: str | None = None,
                 actor: str = "asesor.bna", simulado: bool = True) -> dict:
    """El sobre que SOL envía al pulsar «Guardar y enviar», con su calendario."""
    politica = load_policy(POLITICA)
    hoy = date.today()
    base = fecha_base or hoy
    cliente = {
        "id_cliente": id_cliente, "cod_tipo_documento": "DNI", "numero_documento": numero_documento,
        "nombres": nombres, "apellido_paterno": apellido_paterno, "apellido_materno": apellido_materno,
        "estado_cliente": "ACTIVO", "id_caso": str(uuid.uuid4()), "id_verificacion": str(uuid.uuid4()),
        "fecha_verificacion": hoy.isoformat(), "vigente_hasta": (hoy + timedelta(days=30)).isoformat(),
        "estado_habilitante": "HABILITADO", "version_contrato": "CR-INT-01-PROPUESTA-v2", "simulado": True,
    }
    condiciones = {
        "id_cliente": id_cliente, "monto_solicitado": format(Decimal(monto), ".2f"), "moneda": "PEN",
        "plazo_meses": plazo_meses, "destino_credito": destino, "fecha_base": base.isoformat(),
        "pago_doble": False, "garantias": [], "id_producto_credito": politica.producto_id,
    }
    expediente = {
        "cliente": cliente, "condiciones": condiciones, "fiadores": [],
        "politica": politica.model_dump(mode="json"),
        "calendario": calendar(Decimal(monto), politica.tea, plazo_meses, base, politica.dias_por_periodo),
    }
    return {
        "versionContrato": VERSION_CONTRATO, "idSolicitud": id_solicitud or str(uuid.uuid4()),
        "versionSolicitud": version_solicitud, "idOperacion": id_operacion or str(uuid.uuid4()),
        "idCorrelacion": str(uuid.uuid4()), "expediente": expediente, "simulado": simulado, "actorEnvio": actor,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Envía a Evaluación un expediente con el formato de SOL.")
    p.add_argument("--cliente", required=True, help="Código del cliente (cod_cliente de COREDB)")
    p.add_argument("--documento", required=True)
    p.add_argument("--nombres", required=True)
    p.add_argument("--paterno", required=True)
    p.add_argument("--materno")
    p.add_argument("--monto", default="15000.00")
    p.add_argument("--plazo", type=int, default=12)
    a = p.parse_args()
    token = os.environ.get("EVALUACION_TOKEN_SOL", "")
    if not token:
        print("Falta EVALUACION_TOKEN_SOL.", file=sys.stderr)
        return 1
    sobre = sobre_de_sol(id_cliente=a.cliente, numero_documento=a.documento, nombres=a.nombres,
                         apellido_paterno=a.paterno, apellido_materno=a.materno, monto=a.monto, plazo_meses=a.plazo)
    url = os.environ.get("EVALUACION_URL", "http://127.0.0.1:8015").rstrip("/")
    r = httpx.post(f"{url}/eva/applications", json=sobre, timeout=10, headers={
        "Authorization": f"Bearer {token}", "X-Idempotency-Key": sobre["idOperacion"],
        "X-Correlation-ID": sobre["idCorrelacion"]})
    print(r.status_code, json.dumps(r.json(), ensure_ascii=False, indent=2))
    return 0 if r.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
