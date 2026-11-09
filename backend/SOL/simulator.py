"""Bus + CAP/EVA/Seguridad SINTÉTICOS, solo para practicar el transporte HTTP.

No es un Bus institucional. Sus datos están en memoria y desaparecen al parar.
Arranque: definir SOL_SIMULATOR_TOKEN (32+ caracteres) y usar uvicorn
SOL.simulator:app --host 127.0.0.1 --port 8020. No publicar en Internet.
"""
import os
import secrets
from datetime import timedelta
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from .clock import business_today


def create_simulator(token):
    if len(token) < 32:
        raise ValueError("Define SOL_SIMULATOR_TOKEN con al menos 32 caracteres.")
    def authorized(authorization: str = Header()):
        if not secrets.compare_digest(authorization, "Bearer " + token):
            raise HTTPException(401, "Servicio no autorizado.")
    app = FastAPI(title="SIMULADOR HTTP CAP/EVA/AUD — no institucional", dependencies=[Depends(authorized)])
    app.state.deliveries, app.state.events = {}, {}

    def reference(index):
        today = business_today()
        return {"id_cliente": f"0198b000-0000-7009-8000-{index:012d}",
                "cod_tipo_documento": "DNI", "numero_documento": f"7000000{index}",
                "nombres": "Cliente sintético", "apellido_paterno": f"Prueba {index}", "apellido_materno": "Laboratorio",
                "estado_cliente": "ACTIVO", "id_caso": f"CASO-DEMO-{index}",
                "id_verificacion": f"VER-DEMO-{index}", "fecha_verificacion": (today-timedelta(days=5)).isoformat(),
                "vigente_hasta": (today+timedelta(days=-1 if index == 3 else 30)).isoformat(),
                "estado_habilitante": "OBSERVADO" if index == 2 else "HABILITADO",
                "version_contrato": "CR-INT-01-PROPUESTA-v2", "simulado": True}

    @app.get("/cap/references")
    def search(search: str = "", limit: int = Query(50, ge=1, le=50)):
        return [r for r in [reference(i) for i in range(1, 4)] if search.lower() in (r["numero_documento"] + " " + r["nombres"]).lower()][:limit]

    @app.get("/cap/references/{identifier}")
    def client(identifier: str):
        for i in range(1, 4):
            if reference(i)["id_cliente"] == identifier:
                return reference(i)
        raise HTTPException(404, "Referencia sintética no encontrada.")

    @app.get("/eva/operations/{operation}")
    def status(operation: str):
        if operation not in app.state.deliveries:
            raise HTTPException(404, "Operación no recibida.")
        return app.state.deliveries[operation]["receipt"]

    @app.post("/eva/applications")
    def deliver(payload: dict, operation: str = Header(alias="X-Idempotency-Key")):
        if operation != payload.get("idOperacion"):
            raise HTTPException(422, "Clave diferente.")
        if operation in app.state.deliveries:
            if app.state.deliveries[operation]["payload"] != payload:
                raise HTTPException(409, "Operación con contenido diferente.")
            return app.state.deliveries[operation]["receipt"]
        receipt = {key: payload[key] for key in ["idSolicitud", "versionSolicitud", "idOperacion"]}
        receipt.update(idEvaluacion="EVA-SIM-" + payload["idSolicitud"], ronda=payload["versionSolicitud"],
                       acuse="ACK-SIM-" + operation[:20])
        app.state.deliveries[operation] = {"payload": payload, "receipt": receipt}
        return receipt

    @app.post("/security/events")
    def audit(payload: dict, operation: str = Header(alias="X-Idempotency-Key")):
        if operation != payload.get("idEvento"):
            raise HTTPException(422, "Clave diferente.")
        if operation in app.state.events and app.state.events[operation] != payload:
            raise HTTPException(409, "Evento con contenido diferente.")
        app.state.events[operation] = payload
        return {"idEvento": operation, "confirmado": True, "acuse": "AUD-SIM-" + operation}

    return app


app = create_simulator(os.getenv("SOL_SIMULATOR_TOKEN", ""))
