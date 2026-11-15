"""Doble de prueba de los módulos con los que habla Desembolso, con sus contratos reales:

- COREDB: POST /coredb/auth/login y GET /coredb/auth/me, con el mapa real de COREDB/permisos.py.
- Evaluación (backend/EVALUACION): CR-INT-04 bajo /eva/v1/aprobaciones, con el calendario de SOL.
- CUENTAS (backend/CUENTAS): /api/v1/cuentas con su sobre ITIL-02, depósito idempotente y movimientos.
- Cobranza (PR #68): POST /cr-int-06/obligaciones con X-API-Key; repetir el codCredito responde 409 RN-COB-001.

/_sim permite inyectar fallas (respuesta perdida, rechazo, caídas) para probar el módulo. Todo en memoria.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import secrets
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from COREDB import permisos
from DESEMBOLSO.tests import datos

LIMA = timezone(timedelta(hours=-5))
CENTIMO = Decimal("0.01")

app = FastAPI(title="Simulador de COREDB, Evaluación, CUENTAS y Cobranza")
_candado = threading.Lock()
_tokens: dict[str, str] = {}   # token -> usuario; sobrevive a /_sim/reiniciar

ESCENARIO_BASE: dict[str, Any] = {
    "cuentas_abono": "NORMAL",       # NORMAL | TIMEOUT_REGISTRADO | TIMEOUT_NO_REGISTRADO | RECHAZO | ERROR
    "demora_timeout_seg": 5.0,
    "cuentas_caida": False,
    "evaluacion_caida": False,
    "cobranza_caida": False,
    "cobranza_fallos": 0,            # las próximas N obligaciones responden 503
    "cobranza_limite_ids": 36,       # largo máximo de idSolicitud e idCliente que acepta Cobranza
}
estado: dict[str, Any] = {}


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _dinero(valor: Decimal) -> str:
    return format(valor.quantize(CENTIMO, rounding=ROUND_HALF_UP), "f")


def _calendario(importe: Decimal, plazo: int, inicio: date) -> dict:
    """Calendario como el de SOL: cuotas cada 30 días, amortización pareja y 1 % mensual sobre el saldo."""
    saldo, cuotas = importe, []
    amortizacion = (importe / plazo).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    for n in range(1, plazo + 1):
        capital = saldo if n == plazo else amortizacion
        interes = (saldo * Decimal("0.01")).quantize(CENTIMO, rounding=ROUND_HALF_UP)
        cuotas.append({"numeroCuota": n, "fechaVencimiento": (inicio + timedelta(days=30 * n)).isoformat(),
                       "saldoInicial": _dinero(saldo), "amortizacion": _dinero(capital), "interes": _dinero(interes),
                       "cuotaTotal": _dinero(capital + interes), "saldoFinal": _dinero(saldo - capital)})
        saldo -= capital
    total = sum((Decimal(c["cuotaTotal"]) for c in cuotas), Decimal(0))
    return {"origen": "SOL", "estado": "PRELIMINAR", "politica": "SOL-DEMO-2026-01", "numeroCuotas": plazo,
            "cuotaReferencial": cuotas[0]["cuotaTotal"], "interesesTotales": _dinero(total - importe),
            "totalPagar": _dinero(total), "cuotas": cuotas}


def _aprobacion(a: dict) -> dict:
    cliente = datos.CLIENTES[a["cliente"]]
    numero = a["id"][-4:]
    return {
        "idAprobacion": a["id"], "version": 1, "idEvaluacion": f"EVA-2026-00{numero}",
        "idSolicitud": f"0198b000-0000-7000-8000-00000000{numero}", "versionSolicitud": 1, "codCredito": a["credito"],
        "idCliente": a["cliente"], "clienteNombre": cliente["nombre"], "tipoDocumento": "DNI",
        "numeroDocumento": cliente["documento"], "producto": a["producto"], "montoAprobado": _dinero(a["importe"]),
        "moneda": a["moneda"], "plazoMeses": a["plazo"], "tasaTea": a["tea"], "estado": a["estado"],
        "vigenteHasta": (datetime.now(timezone.utc) + timedelta(days=a["dias"])).isoformat(),
        "aprobadaPor": "ana.analista", "aprobadaEn": datetime.now(timezone.utc).isoformat(),
        "calendario": _calendario(a["importe"], a["plazo"], datetime.now(LIMA).date()),
        "desembolso": None, "revocacion": None,
    }


def _reiniciar() -> None:
    with _candado:
        estado.clear()
        estado.update({
            "escenario": dict(ESCENARIO_BASE),
            "aprobaciones": {a["id"]: _aprobacion(a) for a in datos.APROBACIONES},
            "cuentas": {num: {"num_cuenta": num, "cci": f"002{num}000"[:20], "moneda": moneda, "regimen": regimen,
                              "estado_cuenta": estado_cuenta, "saldo_contable": "500.00", "saldo_disponible": "500.00",
                              "id_agencia": "AG001", "titulares": [cliente], "comportamiento": comportamiento}
                        for num, cliente, moneda, estado_cuenta, regimen, comportamiento in datos.CUENTAS},
            "movimientos": [],
            "llaves": {},              # X-Idempotency-Key -> (huella, uuid_transaccion)
            "intentos_abono": 0,
            "ya_demorados": set(),     # cuentas cuyo primer depósito ya "perdió" la respuesta
            "obligaciones": {},        # codCredito -> obligación recibida
            "activaciones": {},        # codCredito -> veces que se intentó activar
            "avisos_evaluacion": [],
        })


_reiniciar()


def _error_cuentas(estado_http: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=estado_http, content={"success": False, "status_code": estado_http,
                                                          "error_code": codigo, "message": mensaje, "details": {}})


def _usuario(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return _tokens.get(authorization[7:])


def _acciones(usuario: str) -> frozenset[str]:
    u = datos.USUARIOS[usuario]
    clave = f"SERVICIO:{u['modulo']}" if u["rol"] == "SERVICIO" else u["rol"]
    return permisos.PERMISOS.get(clave, frozenset())


# ---------------------------------------------------------------------- control
@app.post("/_sim/escenarios")
def cambiar_escenarios(cambios: dict[str, Any]):
    with _candado:
        desconocidas = set(cambios) - set(ESCENARIO_BASE)
        if desconocidas:
            return JSONResponse(status_code=400, content={"desconocidas": sorted(desconocidas)})
        estado["escenario"].update(cambios)
        return estado["escenario"]


@app.post("/_sim/reiniciar")
def reiniciar():
    _reiniciar()
    return {"ok": True}


@app.post("/_sim/aprobaciones/{aprobacion_id}")
def cambiar_aprobacion(aprobacion_id: str, cambios: dict[str, Any]):
    with _candado:
        a = estado["aprobaciones"][aprobacion_id]
        a.update(cambios)
        return a


@app.get("/_sim/estado")
def ver_estado():
    with _candado:
        return {"intentos_abono": estado["intentos_abono"], "movimientos": list(estado["movimientos"]),
                "obligaciones": copy.deepcopy(estado["obligaciones"]), "activaciones": dict(estado["activaciones"]),
                "avisos_evaluacion": list(estado["avisos_evaluacion"]),
                "aprobaciones": {k: v["estado"] for k, v in estado["aprobaciones"].items()}}


# ---------------------------------------------------------------------- COREDB
@app.get("/coredb/salud")
def salud_coredb():
    return {"estado": "ok"}


@app.post("/coredb/auth/login")
def login(cuerpo: dict[str, Any]):
    usuario, clave = cuerpo.get("username", ""), cuerpo.get("password", "")
    esperada = datos.SECRETO_SERVICIO if usuario == "svc-desembolso" else datos.CONTRASENA
    if usuario not in datos.USUARIOS or clave != esperada:
        return JSONResponse(status_code=401, content={"error": {"code": "CREDENCIALES_INVALIDAS",
                                                                "message": "Usuario o contraseña incorrectos."}})
    token = secrets.token_urlsafe(24)
    _tokens[token] = usuario
    u = datos.USUARIOS[usuario]
    return {"access_token": token, "token_type": "bearer", "expires_in": 1800,
            "usuario": {"id_usuario": str(uuid.uuid4()), "username": usuario, "nombre": usuario, "rol": u["rol"],
                        "modulo": u["modulo"], "activo": True, "creado_en": _ahora_utc().isoformat()}}


@app.get("/coredb/auth/me")
def me(authorization: str | None = Header(default=None)):
    usuario = _usuario(authorization)
    if usuario is None:
        return JSONResponse(status_code=401, content={"error": {"code": "TOKEN_INVALIDO", "message": "Token inválido."}})
    u = datos.USUARIOS[usuario]
    return {"id_usuario": str(uuid.uuid5(uuid.NAMESPACE_URL, usuario)), "username": usuario, "rol": u["rol"],
            "modulo": u["modulo"], "acciones": sorted(_acciones(usuario))}


# ---------------------------------------------------------------------- Evaluación (CR-INT-04)
def _servicio_desembolso(authorization: str | None) -> JSONResponse | None:
    usuario = _usuario(authorization)
    if usuario is None:
        return JSONResponse(status_code=401, content={"error": {"code": "SESION_INVALIDA", "message": "Sin sesión."}})
    if usuario != "svc-desembolso":
        return JSONResponse(status_code=403, content={"error": {"code": "PERMISO_DENEGADO", "message": "Solo Desembolso."}})
    if estado["escenario"]["evaluacion_caida"]:
        return JSONResponse(status_code=503, content={"error": {"code": "NO_DISPONIBLE", "message": "Caída simulada."}})
    return None


def _efectiva(a: dict) -> dict:
    vencida = a["estado"] == "VIGENTE" and datetime.fromisoformat(a["vigenteHasta"]) <= datetime.now(timezone.utc)
    return {**a, "estado": "VENCIDA" if vencida else a["estado"]}


@app.get("/eva/v1/aprobaciones")
def buscar_aprobaciones(numeroDocumento: str | None = None, codCredito: str | None = None,
                        authorization: str | None = Header(default=None)):
    if (error := _servicio_desembolso(authorization)) is not None:
        return error
    items = []
    for a in estado["aprobaciones"].values():
        if (numeroDocumento and a["numeroDocumento"] != numeroDocumento) or (codCredito and a["codCredito"] != codCredito):
            continue
        sin_cuotas = {k: v for k, v in a["calendario"].items() if k != "cuotas"}
        items.append({**_efectiva(a), "calendario": sin_cuotas})
    return {"items": items}


@app.get("/eva/v1/aprobaciones/{aprobacion_id}")
def obtener_aprobacion(aprobacion_id: str, authorization: str | None = Header(default=None)):
    if (error := _servicio_desembolso(authorization)) is not None:
        return error
    a = estado["aprobaciones"].get(aprobacion_id)
    if a is None:
        return JSONResponse(status_code=404, content={"error": {"code": "APROBACION_NO_ENCONTRADA",
                                                                "message": "Evaluación no registra esa aprobación."}})
    return _efectiva(a)


@app.post("/eva/v1/aprobaciones/{aprobacion_id}/desembolso")
def registrar_desembolso(aprobacion_id: str, cuerpo: dict[str, Any], authorization: str | None = Header(default=None)):
    if (error := _servicio_desembolso(authorization)) is not None:
        return error
    with _candado:
        a = estado["aprobaciones"][aprobacion_id]
        estado["avisos_evaluacion"].append({"idAprobacion": aprobacion_id, **cuerpo})
        if a["estado"] == "DESEMBOLSADA":
            if a["desembolso"]["codigoOrden"] == cuerpo["codigoOrden"]:
                return a
            return JSONResponse(status_code=409, content={"error": {"code": "APROBACION_YA_DESEMBOLSADA",
                                                                    "message": "Ya se usó en otra orden."}})
        if a["estado"] != "VIGENTE" or a["version"] != cuerpo["version"]:
            return JSONResponse(status_code=409, content={"error": {"code": "APROBACION_NO_VIGENTE",
                                                                    "message": "Aprobación revocada o con otra versión."}})
        a.update(estado="DESEMBOLSADA", version=a["version"] + 1,
                 desembolso={"codigoOrden": cuerpo["codigoOrden"], "fechaDesembolso": cuerpo["fechaDesembolso"],
                             "registradoPor": "svc-desembolso"})
        return a


# ---------------------------------------------------------------------- CUENTAS (CR-INT-05)
def _cuentas(authorization: str | None, accion: str) -> JSONResponse | None:
    if estado["escenario"]["cuentas_caida"]:
        return _error_cuentas(503, "ERR-COR-NO-DISPONIBLE", "COREDB no disponible (simulado)")
    usuario = _usuario(authorization)
    if usuario is None:
        return _error_cuentas(401, "ERR-CTA-TOKEN-INVALIDO", "Token inválido")
    if accion not in _acciones(usuario):
        return _error_cuentas(403, "ERR-CTA-PERMISO-DENEGADO", f"El rol no puede ejecutar {accion}")
    return None


def _publica(c: dict) -> dict:
    return {k: v for k, v in c.items() if k != "comportamiento"}


@app.get("/api/v1/cuentas/consolidada/{id_cliente}")
def consolidada(id_cliente: str, authorization: str | None = Header(default=None)):
    if (error := _cuentas(authorization, "VER_CUENTA")) is not None:
        return error
    if id_cliente not in datos.CLIENTES:
        return _error_cuentas(404, "ERR-CLI-NO-ENCONTRADO", "Cliente no encontrado")
    return {"success": True, "data": [_publica(c) for c in estado["cuentas"].values() if id_cliente in c["titulares"]]}


@app.get("/api/v1/cuentas/movimiento/{uuid_transaccion}")
def ver_movimiento(uuid_transaccion: str, authorization: str | None = Header(default=None)):
    if (error := _cuentas(authorization, "VER_CUENTA")) is not None:
        return error
    m = next((m for m in estado["movimientos"] if m["uuid_transaccion"] == uuid_transaccion), None)
    if m is None:
        return _error_cuentas(404, "ERR-COR-MOVIMIENTO_NO_ENCONTRADO", "El movimiento no existe")
    return {"success": True, "data": m}


@app.get("/api/v1/cuentas/{num_cuenta}/movimientos")
def movimientos(num_cuenta: str, authorization: str | None = Header(default=None)):
    if (error := _cuentas(authorization, "VER_CUENTA")) is not None:
        return error
    if num_cuenta not in estado["cuentas"]:
        return _error_cuentas(404, "ERR-CTA-NO-ENCONTRADA", "Cuenta no encontrada")
    propios = [m for m in reversed(estado["movimientos"]) if m["num_cuenta"] == num_cuenta]
    return {"success": True, "data": propios[:50]}


@app.get("/api/v1/cuentas/{num_cuenta}")
def ver_cuenta(num_cuenta: str, authorization: str | None = Header(default=None)):
    if (error := _cuentas(authorization, "VER_CUENTA")) is not None:
        return error
    c = estado["cuentas"].get(num_cuenta)
    if c is None:
        return _error_cuentas(404, "ERR-CTA-NO-ENCONTRADA", "Cuenta no encontrada")
    return {"success": True, "data": _publica(c)}


@app.post("/api/v1/cuentas/deposito", status_code=201)
async def depositar(cuerpo: dict[str, Any], authorization: str | None = Header(default=None),
                    x_idempotency_key: str | None = Header(default=None), x_channel_id: str | None = Header(default=None),
                    x_request_timestamp: str | None = Header(default=None)):
    with _candado:
        estado["intentos_abono"] += 1
        if (error := _cuentas(authorization, "REGISTRAR_MOVIMIENTO")) is not None:
            return error
        try:
            if uuid.UUID(x_idempotency_key or "").version != 4:
                raise ValueError
        except ValueError:
            return _error_cuentas(400, "ERR-CTA-HEADER-INVALIDO", "X-Idempotency-Key debe ser un UUIDv4")
        if x_channel_id not in ("ATM", "AGE", "VEN", "WEB", "MOB") or not x_request_timestamp:
            return _error_cuentas(400, "ERR-CTA-HEADER-INVALIDO", "Cabeceras de operación inválidas")
        huella = hashlib.sha256(json.dumps(cuerpo, sort_keys=True).encode()).hexdigest()
        previa = estado["llaves"].get(x_idempotency_key)
        if previa:
            if previa[0] != huella:
                return _error_cuentas(409, "ERR-COR-IDEMPOTENCY-KEY-REUTILIZADA", "Llave reutilizada con otros datos")
            return {"success": True, "data": {"uuid_transaccion": previa[1], "replay": True}}
        cuenta = estado["cuentas"].get(cuerpo.get("num_cuenta"))
        if cuenta is None:
            return _error_cuentas(404, "ERR-CTA-NO-ENCONTRADA", "Cuenta no encontrada")
        comportamiento = estado["escenario"]["cuentas_abono"]
        if comportamiento == "NORMAL":
            comportamiento = cuenta.get("comportamiento") or "NORMAL"
            if comportamiento == "TIMEOUT_REGISTRADO" and cuenta["num_cuenta"] in estado["ya_demorados"]:
                comportamiento = "NORMAL"
        if comportamiento == "RECHAZO" or cuenta["estado_cuenta"] == "BLOQUEADA":
            return _error_cuentas(403, "ERR-CTA-BLOQUEADA", "La cuenta tiene una retención judicial vigente")
        if comportamiento == "ERROR":
            return _error_cuentas(500, "ERR-INTERNO-SERVIDOR", "Falla interna simulada")
        demora = estado["escenario"]["demora_timeout_seg"]
        uuid_transaccion = None
        if comportamiento != "TIMEOUT_NO_REGISTRADO":
            uuid_transaccion = str(uuid.uuid4())
            estado["llaves"][x_idempotency_key] = (huella, uuid_transaccion)
            estado["movimientos"].append({
                "uuid_transaccion": uuid_transaccion, "num_cuenta": cuenta["num_cuenta"], "tipo_operacion": "DEPOSITO",
                "naturaleza": "C", "monto": format(Decimal(str(cuerpo["monto"])), ".2f"), "moneda": cuenta["moneda"],
                "glosa": cuerpo.get("glosa", ""), "id_canal": x_channel_id, "estado_transaccion": "PROCESADO",
                "fecha_hora": _ahora_utc().isoformat()})
        if comportamiento.startswith("TIMEOUT"):
            estado["ya_demorados"].add(cuenta["num_cuenta"])
    if comportamiento.startswith("TIMEOUT"):
        await asyncio.sleep(demora)
        if comportamiento == "TIMEOUT_NO_REGISTRADO":
            return _error_cuentas(504, "ERR-CTA-OPERACION-NO-CONFIRMADA", "COREDB no confirmó la operación")
    return {"success": True, "data": {"uuid_transaccion": uuid_transaccion, "replay": False}}


# ---------------------------------------------------------------------- Cobranza (CR-INT-06)
@app.post("/cr-int-06/obligaciones", status_code=201)
def activar_obligacion(cuerpo: dict[str, Any], request: Request, x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        return JSONResponse(status_code=401, content={"detalle": "Falta la clave X-API-Key", "regla": "AUTENTICACION"})
    if x_api_key != datos.CLAVE_COBRANZA:
        return JSONResponse(status_code=401, content={"detalle": "X-API-Key invalida", "regla": "AUTENTICACION"})
    with _candado:
        escenario = estado["escenario"]
        if escenario["cobranza_caida"]:
            return JSONResponse(status_code=503, content={"detalle": "Cobranza no disponible (simulado)"})
        if escenario["cobranza_fallos"] > 0:
            escenario["cobranza_fallos"] -= 1
            return JSONResponse(status_code=503, content={"detalle": "Falla transitoria (simulada)"})
        limite = escenario["cobranza_limite_ids"]
        largos = [c for c, maximo in (("codCredito", 20), ("idCliente", limite), ("idSolicitud", limite))
                  if len(str(cuerpo.get(c) or "")) > maximo]
        faltan = [c for c in ("codCredito", "idCliente", "idSolicitud", "montoAprobado", "fechaDesembolso",
                              "calendarioPagos") if not cuerpo.get(c)]
        if largos or faltan:
            return JSONResponse(status_code=422, content={"detail": [
                {"loc": ["body", c], "msg": "String should have at most characters" if c in largos else "Field required",
                 "type": "string_too_long" if c in largos else "missing"} for c in largos + faltan]})
        codigo = cuerpo["codCredito"]
        if codigo in estado["obligaciones"]:
            return JSONResponse(status_code=409, content={"detalle": "El credito ya fue activado en Cobranza",
                                                          "regla": "RN-COB-001"})
        estado["activaciones"][codigo] = estado["activaciones"].get(codigo, 0) + 1
        estado["obligaciones"][codigo] = copy.deepcopy(cuerpo)
        return {"codCredito": codigo, "estadoCredito": "AL_DIA", "cuotas": cuerpo["calendarioPagos"]}
