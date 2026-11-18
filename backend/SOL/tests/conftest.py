"""SOL sin base propia: un Bus falso en memoria con COREDB, CAPTACION y EVALUACION.

El falso sigue los contratos que SOL usa (CONTRATO_CREDITOS.md §3.1 y §8, CR-INT-01 de
CAPTACION, CR-INT-02 de EVALUACION). Las reglas de la base (revisión, huella, estados) las
prueban bna-core-db y COREDB; aquí basta con que el falso responda como ellos.
"""

import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from SOL.app import create_app  # noqa: E402
from SOL.clock import business_today  # noqa: E402
from SOL.settings import ROOT, Settings  # noqa: E402

BUS = "http://bus.test/bus"
CLIENT = "CLI000000001"
GUARANTOR = "CLI000000002"
PASSWORD = "clave-de-la-asesora-1"
TOKENS = {
    "bus_token": "bus-sintetico-" + "b" * 32, "coredb_secreto": "svc-sintetico-" + "s" * 32,
    "cap_token": "cap-sintetico-" + "c" * 32, "eva_token": "eva-sintetico-" + "e" * 32,
    "callback_token": "callback-sintetico-" + "k" * 32,
}
USERS = {"asesora": ("ASESOR", "Valeria Asesora"), "admin": ("ADMINISTRADOR", "Administración"),
         "auditor": ("AUDITOR", "Auditoría"), "analista": ("ANALISTA", "Analista"),
         "svc-sol": ("SERVICIO", "SOL")}


def now():
    return datetime.now(timezone.utc).isoformat()


def reference(identifier, index=1, **changes):
    today = business_today()
    data = {"id_cliente": identifier, "cod_tipo_documento": "DNI", "numero_documento": f"7000000{index}",
            "nombres": "Persona", "apellido_paterno": f"Sintética {index}", "apellido_materno": "Prueba",
            "estado_cliente": "ACTIVO", "id_caso": f"caso-{index}", "id_verificacion": f"ver-{index}",
            "fecha_verificacion": today.isoformat(), "vigente_hasta": (today + timedelta(days=30)).isoformat(),
            "estado_habilitante": "HABILITADO", "version_contrato": "CR-INT-01-PROPUESTA-v2", "simulado": True,
            "numero_celular": "959000001"}
    data.update(changes)
    return data


class FakeBus:
    def __init__(self):
        self.references = {CLIENT: reference(CLIENT, 1), GUARANTOR: reference(GUARANTOR, 2)}
        self.requests = []
        self.solicitudes = {}
        self.events = {}
        self.eva_down = False
        self.audit_down = False
        self.cap_down = False

    # ------------------------------------------------------------------ utilidades
    @staticmethod
    def reply(status, body):
        return httpx.Response(status, json=body)

    @staticmethod
    def error(status, code, message=""):
        return httpx.Response(status, json={"error": {"code": code, "message": message}})

    def user_of(self, request):
        token = request.headers.get("Authorization", "")[len("Bearer "):]
        username = token[len("tok-"):] if token.startswith("tok-") else None
        return username if username in USERS else None

    def evaluate(self, identifier, decision, rule="R-A", comment=None):
        s = self.solicitudes[identifier]
        evaluation = {"idEvaluacion": s["recepciones"][-1]["idEvaluacion"], "ronda": s["recepciones"][-1]["ronda"],
                      "fechaEvaluacion": now(), "regla": rule, "resultado": decision, "comentario": comment,
                      "fechaDecision": now() if comment else None, "esUltima": True}
        s["evaluaciones"] = [evaluation]
        s["estado"] = {"APROBADO": "APROBADA", "RECHAZADO": "RECHAZADA"}[decision]
        s["historial"].append({"estado": s["estado"], "fechaHora": now(), "actor": "analista", "motivo": None})
        return evaluation

    # ------------------------------------------------------------------ despacho
    def __call__(self, request):
        assert request.headers.get("X-Bus-Token") == TOKENS["bus_token"], "Falta la credencial de SOL ante el Bus"
        path = request.url.path
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, path, dict(request.headers), body))
        if path.startswith("/bus/coredb"):
            return self.coredb(request, path[len("/bus/coredb"):], body)
        if path.startswith("/bus/captacion"):
            return self.captacion(request, path[len("/bus/captacion"):], body)
        if path.startswith("/bus/evaluacion"):
            return self.evaluacion(request, path[len("/bus/evaluacion"):], body)
        return self.error(404, "RUTA")

    def captacion(self, request, path, body):
        assert request.headers["Authorization"] == "Bearer " + TOKENS["cap_token"]
        if self.cap_down:
            return self.reply(503, {"detail": "caído"})
        if path == "/cap/references/search":
            text = body["search"].lower()
            return self.reply(200, [r for r in self.references.values()
                                    if text in (r["numero_documento"] + " " + r["nombres"]).lower()])
        identifier = path.rsplit("/", 1)[-1]
        if identifier in self.references:
            return self.reply(200, self.references[identifier])
        return self.reply(404, {"detail": "no"})

    def evaluacion(self, request, path, body):
        assert request.headers["Authorization"] == "Bearer " + TOKENS["eva_token"]
        assert path == "/eva/applications"
        assert request.headers["X-Idempotency-Key"] == body["idOperacion"]
        if self.eva_down:
            return self.reply(503, {"detail": "caído"})
        s = self.solicitudes.get(body["idSolicitud"])
        if s is None:
            return self.error(422, "SOLICITUD_NO_ADMITIDA")
        cond = body["expediente"]["condiciones"]
        if (cond["monto_solicitado"], cond["plazo_meses"]) != (s["montoSolicitado"], s["plazoMeses"]):
            return self.error(422, "SOLICITUD_NO_ADMITIDA")
        id_evaluacion = "eva-" + body["idSolicitud"][:8]
        status = 200
        if s["estado"] == "REGISTRADA":
            status = 201
            s["estado"] = "EN_EVALUACION"
            s["recepciones"] = [{"versionSolicitud": 1, "ronda": 1, "idEvaluacion": id_evaluacion,
                                 "recibidaEn": now()}]
            s["historial"].append({"estado": "EN_EVALUACION", "fechaHora": now(), "actor": "svc-evaluacion",
                                   "motivo": None})
            s["calendario"] = {"tipo": "PRELIMINAR", "cuotas": [
                {"numeroCuota": c["numero_cuota"], "fechaVencimiento": c["fecha_vencimiento"],
                 "capital": c["amortizacion"], "interes": c["interes"], "cuotaTotal": c["cuota_total"],
                 "saldoCapital": c["saldo_final"]} for c in body["expediente"]["calendario"]["cuotas"]]}
        return self.reply(status, {"idSolicitud": body["idSolicitud"], "versionSolicitud": 1,
                                   "idOperacion": body["idOperacion"], "idEvaluacion": id_evaluacion, "ronda": 1,
                                   "acuse": f"ACK-{id_evaluacion}"})

    def coredb(self, request, path, body):
        method = request.method
        if path == "/coredb/salud":
            return self.reply(200, {"status": "ok"})
        if path == "/coredb/auth/login":
            username = body["username"]
            expected = TOKENS["coredb_secreto"] if username == "svc-sol" else PASSWORD
            if username not in USERS or body["password"] != expected:
                return self.error(401, "CREDENCIALES_INVALIDAS")
            rol, nombre = USERS[username]
            return self.reply(200, {"access_token": "tok-" + username, "token_type": "bearer", "expires_in": 1800,
                                    "usuario": {"username": username, "nombre": nombre, "rol": rol}})
        user = self.user_of(request)
        if user is None:
            return self.error(401, "TOKEN_INVALIDO")
        rol = USERS[user][0]
        if path == "/coredb/auth/me":
            return self.reply(200, {"username": user, "rol": rol, "acciones": []})
        if path == "/coredb/auditoria/eventos":
            if user != "svc-sol":
                return self.error(403, "PERMISO_DENEGADO")
            if self.audit_down:
                return self.reply(503, {"detail": "caído"})
            previous = self.events.get(body["idEvento"])
            if previous and previous != body:
                return self.error(409, "IDEMPOTENCIA_CONFLICTO")
            self.events[body["idEvento"]] = body
            return self.reply(200 if previous else 201, {"idEvento": body["idEvento"], "idRegistro": 7,
                                                         "acuse": "AUD-7", "confirmado": True})
        if path == "/coredb/creditos/borradores" and method == "POST":
            if rol not in ("ASESOR", "ADMINISTRADOR"):
                return self.error(403, "PERMISO_DENEGADO")
            return self.save(None, body, user)
        if path.startswith("/coredb/creditos/borradores/") and method == "PUT":
            return self.save(path.rsplit("/", 1)[-1], body, user)
        if path == "/coredb/creditos/solicitudes/conteo":
            counts = {}
            for s in self.solicitudes.values():
                counts[s["estado"]] = counts.get(s["estado"], 0) + 1
            return self.reply(200, {"total": sum(counts.values()), "estados": counts})
        if path == "/coredb/creditos/solicitudes":
            query = parse_qs(request.url.query.decode())
            assert query.get("borradores") == ["true"]
            rows = list(reversed(list(self.solicitudes.values())))
            offset, limit = int(query["offset"][0]), int(query["limite"][0])
            return self.reply(200, [self.row(s) for s in rows[offset:offset + limit]])
        if path.startswith("/coredb/creditos/solicitudes/"):
            s = self.solicitudes.get(path.rsplit("/", 1)[-1])
            return self.reply(200, deepcopy(s)) if s else self.error(404, "SOLICITUD_NO_ENCONTRADA")
        return self.error(404, "RUTA")

    @staticmethod
    def row(s):
        return {k: s[k] for k in ("idSolicitud", "versionSolicitud", "codCliente", "montoSolicitado", "moneda",
                                  "plazoMeses", "estado", "fechaCreacion", "codigo", "revision")}

    def save(self, identifier, body, user):
        if identifier is None:
            identifier = body["idSolicitud"]
            if identifier in self.solicitudes:
                return self.error(409, "IDEMPOTENCIA_CONFLICTO")
            revision = 1
        else:
            s = self.solicitudes.get(identifier)
            if s is None:
                return self.error(404, "SOLICITUD_NO_ENCONTRADA")
            if s["estado"] != "REGISTRADA":
                return self.error(422, "SOLICITUD_NO_ADMITIDA", "La solicitud ya se envió a evaluación.")
            if body["revision"] != s["revision"]:
                return self.error(409, "REVISION_DESACTUALIZADA", "La solicitud cambió en otra sesión.")
            revision = s["revision"] + 1
        previous = self.solicitudes.get(identifier, {})
        self.solicitudes[identifier] = {
            "idSolicitud": identifier, "versionSolicitud": 1, "codCliente": body["codCliente"],
            "montoSolicitado": body["montoSolicitado"], "moneda": body["moneda"], "plazoMeses": body["plazoMeses"],
            "condicionPagoDoble": body["condicionPagoDoble"], "estado": "REGISTRADA",
            "fechaCreacion": previous.get("fechaCreacion", now()), "codigo": "SOL-2611-" + identifier[:8].upper(),
            "revision": revision, "calendario": None, "evaluaciones": [], "recepciones": [],
            "historial": previous.get("historial", []) + [
                {"estado": "REGISTRADA", "fechaHora": now(), "actor": user, "motivo": None}],
            "expediente": {"codigo": "SOL-2611-" + identifier[:8].upper(), "revision": revision,
                           "destino": body["destino"], "fechaBase": body["fechaBase"], "politica": body["politica"],
                           "creadoPor": user, "actualizadoEn": now()},
            "garantias": [{"tipo": g["tipo"], "descripcion": g["descripcion"], "valor": g["valor"],
                           "moneda": body["moneda"], "estado": "REGISTRADA"} for g in body["garantias"]],
            "fiadores": [{"codCliente": f, "idVerificacion": "ver"} for f in body["fiadores"]],
        }
        return self.reply(201 if revision == 1 else 200, {"idSolicitud": identifier, "codigo": "SOL-2611-X",
                                                          "revision": revision, "estado": "REGISTRADA"})


def settings(tmp_path=None, **changes):
    policy = ROOT / "config" / "politica_demo.json"
    if tmp_path is not None:
        policy = tmp_path / "politica.json"
        policy.write_text((ROOT / "config" / "politica_demo.json").read_text(), encoding="utf-8")
    values = dict(bus_url=BUS, coredb_usuario="svc-sol", policy_path=policy, session_cache_seconds=0, **TOKENS)
    values.update(changes)
    return Settings(**values)


@pytest.fixture
def bus():
    return FakeBus()


@pytest.fixture
def lab(tmp_path, bus):
    app = create_app(settings(tmp_path), transport=httpx.MockTransport(bus))
    with TestClient(app) as client:
        yield client, app


def auth(client, username="asesora"):
    response = client.post("/sol/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["token"]}


def form(**changes):
    data = {"id_cliente": CLIENT, "monto_solicitado": "5000.00", "moneda": "PEN", "plazo_meses": 12,
            "destino_credito": "Capital de trabajo", "fecha_base": business_today().isoformat(),
            "pago_doble": False, "garantias": [], "fiadores": []}
    data.update(changes)
    return data
