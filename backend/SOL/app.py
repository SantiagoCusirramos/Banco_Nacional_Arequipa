"""API de Solicitud de Crédito: `uvicorn SOL.app:app --port 8011`.

Sin base propia. El borrador, la bandeja, el historial y la bitácora están en COREDB; las
referencias de clientes, en CAPTACION; el expediente va a EVALUACION. Todo por el Bus.
La persona entra con su usuario de COREDB y SOL reenvía su token en lo que hace ella.
"""

import hashlib
import logging
import os
import secrets
import threading
import time
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .clock import business_today
from .integrations import Integrations, IntegrationError, RemoteRejection, project_identity
from .observability import AccessLogPrivacy, Metrics, log, valid_id
from .policy import load_policy
from .schemas import (ApplicationInput, ApplicationPageResponse, ClientResponse, ClientSearch, DetailResponse,
                      EvaluationReceiptResponse, EvaluationResult, HealthResponse, Login, LoginResponse,
                      MetricsResponse, OkResponse, PolicyResponse, ReadyResponse, RevisionInput, SnapshotResponse,
                      UserResponse, http_errors)
from .service import (application_detail, draft_body, evaluation_envelope, prepare, snapshot_from_coredb, summary)
from .settings import Settings

# El rol de COREDB → el perfil de SOL. Los demás roles (y los usuarios de servicio) no usan SOL.
ROLES = {"ASESOR": "ASESOR", "ADMINISTRADOR": "SUPERVISOR", "AUDITOR": "AUDITOR"}
ESPACIO_EVENTOS = uuid5(NAMESPACE_URL, "https://bna.local/sol/eventos")
FINALES = {"APROBADO": ("APROBADA", "DESEMBOLSADA"), "RECHAZADO": ("RECHAZADA",)}


def create_app(settings=None, transport=None):
    settings = settings or Settings.from_env()
    settings.validate()
    integrations = Integrations(settings, transport)
    metrics = Metrics()
    sessions, sessions_lock = {}, threading.Lock()

    @asynccontextmanager
    async def lifespan(_):
        load_policy(settings.policy_path)
        access_logger = logging.getLogger("uvicorn.access")
        access_privacy = AccessLogPrivacy()
        access_logger.addFilter(access_privacy)
        try:
            yield
        finally:
            access_logger.removeFilter(access_privacy)
            integrations.close()

    app = FastAPI(title="BNA · Solicitud de Crédito", version="3.0.0", lifespan=lifespan)
    app.state.settings, app.state.integrations, app.state.metrics = settings, integrations, metrics

    @app.middleware("http")
    async def request_trace(request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID")
        request.state.correlation = supplied if valid_id(supplied) else str(uuid4())
        key = request.headers.get("X-Idempotency-Key")
        start, status = perf_counter(), 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Correlation-ID"] = request.state.correlation
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", "NO_ENCONTRADA")
            elapsed = (perf_counter() - start) * 1000
            metrics.observe(request.method + " " + route, elapsed, status)
            log("PETICION", request.state.correlation, key if valid_id(key) else None, ruta=route,
                metodo=request.method, estado=status, duracion_ms=round(elapsed, 3))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        issues = []
        for issue in error.errors():
            loc = list(issue["loc"])
            if issue["type"] == "extra_forbidden" and loc:
                loc[-1] = "campo_no_admitido"
            loc = [part if isinstance(part, int) else str(part).encode("utf-8", "backslashreplace").decode()
                   for part in loc]
            issues.append({"loc": loc, "msg": issue["type"], "type": issue["type"]})
        return JSONResponse(status_code=422, content={"detail": issues})

    @app.exception_handler(IntegrationError)
    async def unavailable(request, error):
        log("DEPENDENCIA_NO_DISPONIBLE", request.state.correlation, causa=error.code)
        return JSONResponse(status_code=503, content={"detail": "COREDB, Captación o Evaluación no respondieron. "
                                                                 "Intenta de nuevo."})

    @app.exception_handler(RemoteRejection)
    async def rejected(request, error):
        if error.status == 401:
            return JSONResponse(status_code=401, content={"detail": "La sesión venció. Vuelve a ingresar."})
        if error.status == 403:
            return JSONResponse(status_code=403, content={"detail": "Tu perfil no puede realizar esta operación."})
        if error.status == 404:
            return JSONResponse(status_code=404, content={"detail": "Solicitud no encontrada."})
        if error.code == "REVISION_DESACTUALIZADA":
            return JSONResponse(status_code=409, content={
                "detail": "La solicitud cambió en otra sesión. Recarga antes de continuar."})
        status = error.status if error.status in (409, 422) else 422
        # Los mensajes de COREDB no repiten documentos, cuentas ni montos.
        return JSONResponse(status_code=status, content={"detail": error.message or error.code})

    def correlation(request: Request):
        return request.state.correlation

    bearer = HTTPBearer(auto_error=False, scheme_name="COREDB")
    callback_bearer = HTTPBearer(auto_error=False, scheme_name="EVACallback")

    def profile(token, trace):
        """El perfil de una sesión de COREDB, recordado unos segundos para no preguntar en cada clic."""
        key = hashlib.sha256(token.encode()).hexdigest()
        with sessions_lock:
            cached = sessions.get(key)
            if cached and cached[1] > time.monotonic():
                return cached[0]
        try:
            _, data = integrations.coredb("GET", "/coredb/auth/me", token, trace)
        except RemoteRejection as exc:
            if exc.status == 401:
                raise HTTPException(401, "La sesión venció. Vuelve a ingresar.") from None
            raise
        rol = ROLES.get(data.get("rol"))
        if rol is None:
            raise HTTPException(403, "Tu perfil no usa Solicitud de Crédito.")
        user = {"username": data["username"], "nombre": data.get("nombre") or data["username"], "rol": rol,
                "token": token}
        with sessions_lock:
            sessions[key] = (user, time.monotonic() + settings.session_cache_seconds)
        return user

    def authenticated(request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
        if credentials is None:
            raise HTTPException(401, "Inicia sesión para continuar.")
        return profile(credentials.credentials, correlation(request))

    def role(*allowed):
        def check(user=Depends(authenticated)):
            if user["rol"] not in allowed:
                raise HTTPException(403, "Tu perfil no puede realizar esta operación.")
            return user
        return check

    def policy():
        try:
            return load_policy(settings.policy_path)
        except Exception:
            raise HTTPException(503, "Política inválida: revisa el archivo y su versión antes de operar.") from None

    def identities(trace):
        cache = {}

        def identity(identifier):
            if identifier not in cache:
                cache[identifier] = integrations.identity(identifier, trace)
            return cache[identifier]
        return identity

    def coredb_detail(identifier, token, trace):
        _, data = integrations.coredb("GET", f"/coredb/creditos/solicitudes/{identifier}", token, trace)
        return data

    def detail_for(identifier, user, trace):
        return application_detail(coredb_detail(identifier, user["token"], trace), identities(trace))

    def audit(action, actor, entity, trace, detail, event_key):
        event = {"idEvento": str(uuid5(ESPACIO_EVENTOS, f"{action}:{event_key}")), "accion": action,
                 "entidad": "solicitud_credito", "idEntidad": entity, "actor": actor, "detalle": detail}
        return integrations.audit(event, trace)

    @app.get("/health", response_model=HealthResponse)
    def health():
        return {"status": "ok", "modulo": "SOL", "integracion": "REAL"}

    @app.get("/ready", response_model=ReadyResponse, responses={503: {"model": ReadyResponse}})
    def ready(request: Request):
        if integrations.ready(correlation(request)):
            return {"status": "ready", "coredb": "disponible"}
        return JSONResponse(status_code=503, content={"status": "not_ready", "coredb": "no disponible"})

    router = APIRouter()

    @router.post("/auth/login", response_model=LoginResponse, responses=http_errors(401, 403, 422, 503))
    def login(payload: Login, request: Request):
        """El login de COREDB (con su bloqueo tras fallos seguidos). SOL no guarda usuarios."""
        try:
            data = integrations.login(payload.username, payload.password, correlation(request))
        except RemoteRejection:
            raise HTTPException(401, "Usuario o contraseña incorrectos.") from None
        rol = ROLES.get(data["usuario"]["rol"])
        if rol is None:
            raise HTTPException(403, "Tu perfil no usa Solicitud de Crédito.")
        return {"token": data["access_token"],
                "usuario": {"username": data["usuario"]["username"], "nombre": data["usuario"]["nombre"], "rol": rol}}

    @router.get("/auth/me", response_model=UserResponse, responses=http_errors(401, 403, 503))
    def me(user=Depends(authenticated)):
        return {k: user[k] for k in ("username", "nombre", "rol")}

    @router.post("/auth/logout", response_model=OkResponse, responses=http_errors(401, 503))
    def logout(credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
        # COREDB aún no revoca sesiones: el token vence solo. El frontend borra su cookie.
        if credentials is not None:
            with sessions_lock:
                sessions.pop(hashlib.sha256(credentials.credentials.encode()).hexdigest(), None)
        return {"ok": True}

    @router.get("/policy", response_model=PolicyResponse, responses=http_errors(401, 503))
    def get_policy(user=Depends(authenticated)):
        return {**policy().model_dump(mode="json"), "integracion": "REAL"}

    @router.get("/clients", response_model=list[ClientResponse], response_model_exclude_unset=True,
                responses=http_errors(401, 503))
    def clients(request: Request, user=Depends(authenticated)):
        return [project_identity(r) for r in integrations.clients("", correlation(request))]

    # P-1: buscar por documento es POST con el texto en el cuerpo; en la consulta quedaría en
    # los registros de acceso del Bus y de cada salto.
    @router.post("/clients/search", response_model=list[ClientResponse], response_model_exclude_unset=True,
                 responses=http_errors(401, 422, 503))
    def search_clients(request: Request, payload: ClientSearch, user=Depends(authenticated)):
        return [project_identity(r) for r in integrations.clients(payload.search, correlation(request))]

    @router.get("/applications", response_model=ApplicationPageResponse, responses=http_errors(401, 422, 503))
    def applications(request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                     user=Depends(authenticated)):
        trace = correlation(request)
        _, rows = integrations.coredb("GET", "/coredb/creditos/solicitudes", user["token"], trace,
                                      params={"borradores": "true", "limite": limit, "offset": offset})
        _, counts = integrations.coredb("GET", "/coredb/creditos/solicitudes/conteo", user["token"], trace)
        identity = identities(trace)
        return {"items": [summary(r, identity(r["codCliente"])) for r in rows], "total": counts["total"],
                "limit": limit, "offset": offset, "estados": counts["estados"]}

    @router.get("/ops/metrics", response_model=MetricsResponse, responses=http_errors(401, 403, 503))
    def get_metrics(user=Depends(role("SUPERVISOR", "AUDITOR"))):
        return metrics.snapshot()

    @router.post("/preview", response_model=SnapshotResponse, response_model_exclude_unset=True,
                 responses=http_errors(401, 403, 422, 503))
    def preview(payload: ApplicationInput, request: Request, user=Depends(role("ASESOR"))):
        return prepare(integrations, payload, policy(), correlation(request))

    @router.post("/applications", status_code=201, response_model=DetailResponse, response_model_exclude_unset=True,
                 responses=http_errors(401, 403, 409, 422, 503))
    def create(payload: ApplicationInput, request: Request, user=Depends(role("ASESOR"))):
        trace, current = correlation(request), policy()
        prepare(integrations, payload, current, trace)
        identifier = str(uuid4())
        integrations.coredb("POST", "/coredb/creditos/borradores", user["token"], trace,
                            payload={"idSolicitud": identifier, **draft_body(payload, current)})
        return detail_for(identifier, user, trace)

    @router.get("/applications/{identifier}", response_model=DetailResponse, response_model_exclude_unset=True,
                responses=http_errors(401, 404, 422, 503))
    def get_application(identifier: str, request: Request, user=Depends(authenticated)):
        return detail_for(identifier, user, correlation(request))

    @router.put("/applications/{identifier}", response_model=DetailResponse, response_model_exclude_unset=True,
                responses=http_errors(401, 403, 404, 409, 422, 503))
    def edit(identifier: str, payload: ApplicationInput, request: Request, user=Depends(role("ASESOR"))):
        trace, current = correlation(request), policy()
        if payload.revision is None:
            raise HTTPException(422, "Falta la revisión que se edita.")
        stored = coredb_detail(identifier, user["token"], trace)
        if stored["codCliente"] != payload.id_cliente:
            raise HTTPException(422, "El cliente de una solicitud existente no puede sustituirse.")
        if stored["estado"] != "REGISTRADA":
            raise HTTPException(409, "La versión enviada está congelada.")
        prepare(integrations, payload, current, trace)
        integrations.coredb("PUT", f"/coredb/creditos/borradores/{identifier}", user["token"], trace,
                            payload={"revision": payload.revision, **draft_body(payload, current)})
        return detail_for(identifier, user, trace)

    @router.post("/applications/{identifier}/send", response_model=DetailResponse, response_model_exclude_unset=True,
                 responses={**http_errors(401, 403, 404, 409, 422, 503),
                            202: {"model": DetailResponse, "description": "Evaluación no respondió; reintentar"}})
    def send(identifier: str, payload: RevisionInput, request: Request,
             operation: str = Header(..., alias="X-Idempotency-Key", min_length=8, max_length=80),
             user=Depends(role("ASESOR"))):
        if not valid_id(operation):
            raise HTTPException(422, "Identificador de operación inválido.")
        trace, current = correlation(request), policy()
        stored = coredb_detail(identifier, user["token"], trace)
        if not stored.get("expediente"):
            raise HTTPException(404, "Solicitud no encontrada.")
        if stored["estado"] != "REGISTRADA":
            if any(r["versionSolicitud"] == stored["versionSolicitud"] for r in stored["recepciones"]):
                return {**application_detail(stored, identities(trace)), "reintento_reconocido": True}
            raise HTTPException(409, "Esta versión ya fue enviada o no admite envío.")
        if payload.revision != stored["revision"]:
            raise HTTPException(409, "La solicitud cambió en otra sesión. Recarga antes de continuar.")
        if stored["expediente"]["politica"] != current.model_dump(mode="json"):
            raise HTTPException(409, "La política cambió. Guarda el borrador para recalcular antes de enviar.")
        if stored["expediente"]["fechaBase"] < business_today().isoformat():
            raise HTTPException(409, "Actualiza la fecha base y recalcula antes de enviar.")
        integrations.reference(stored["codCliente"], trace)
        data = snapshot_from_coredb(stored, identities(trace))
        envelope = evaluation_envelope(stored, data, trace, user["username"])
        try:
            receipt = integrations.deliver(envelope)
        except IntegrationError as exc:
            log("ENVIO_PENDIENTE", trace, envelope["idOperacion"], causa=exc.code)
            # 202: Evaluación no confirmó; reintentar manda el mismo sobre y COREDB no lo duplica.
            return JSONResponse(status_code=202, content={**application_detail(stored, identities(trace)),
                                                          "pendiente_envio": True,
                                                          "idOperacion": envelope["idOperacion"]})
        except RemoteRejection as exc:
            raise HTTPException(409 if exc.status == 409 else 422,
                                f"Evaluación rechazó el expediente ({exc.code}).") from None
        try:
            audit("ENVIAR_CR_INT_02", user["username"], identifier, trace,
                  {"version": envelope["versionSolicitud"], "ronda": receipt["ronda"],
                   "idEvaluacion": receipt["idEvaluacion"], "acuse": receipt["acuse"]}, envelope["idOperacion"])
        except IntegrationError as exc:
            # El expediente ya está en Evaluación; el envío queda en la bitácora de COREDB por
            # REGISTRAR_SOLICITUD. Solo falta el evento de SOL con la persona: queda en el registro.
            log("AUDITORIA_PENDIENTE", trace, envelope["idOperacion"], causa=exc.code)
        log("ENVIO_CONFIRMADO", trace, envelope["idOperacion"])
        return detail_for(identifier, user, trace)

    @app.post("/sol/integrations/evaluation-results", response_model=EvaluationReceiptResponse,
              response_model_exclude_unset=True, responses=http_errors(401, 404, 409, 422, 503))
    def evaluation_result(payload: EvaluationResult, request: Request,
                          credentials: HTTPAuthorizationCredentials | None = Security(callback_bearer),
                          operation: str = Header(..., alias="X-Idempotency-Key"),
                          trace: str = Header(..., alias="X-Correlation-ID", pattern=r"^[A-Za-z0-9._:-]{1,100}$")):
        """CR-INT-03. SOL no guarda el resultado: ya está en COREDB. Lo contrasta con COREDB y lo
        registra en la bitácora una sola vez por idOperacion."""
        if not secrets.compare_digest(credentials.credentials if credentials else "", settings.callback_token):
            raise HTTPException(401, "Servicio no autorizado.")
        if operation != payload.idOperacion or trace != payload.idCorrelacion or trace != correlation(request):
            raise HTTPException(422, "Identificadores de cuerpo y cabecera diferentes.")
        try:
            _, stored = integrations.coredb_service("GET", f"/coredb/creditos/solicitudes/{payload.idSolicitud}", trace)
        except RemoteRejection as exc:
            if exc.status == 404:
                raise HTTPException(404, "Solicitud no encontrada.") from None
            raise
        last = next((e for e in stored["evaluaciones"] if e.get("esUltima")), None)
        if (last is None or stored["versionSolicitud"] != payload.versionSolicitud
                or (last["idEvaluacion"], last["ronda"], last["resultado"])
                != (payload.idEvaluacion, payload.ronda, payload.decision)
                or stored["estado"] not in FINALES.get(payload.decision, ())):
            raise HTTPException(409, "Resultado incompatible con la evaluación, la ronda o la versión en COREDB.")
        _, repeated = audit("RECIBIR_CR_INT_03", "servicio:EVALUACION", payload.idSolicitud, trace,
                            {"version": payload.versionSolicitud, "ronda": payload.ronda,
                             "idEvaluacion": payload.idEvaluacion, "decision": payload.decision}, operation)
        if repeated:
            return {"recibido": True, "reintento_reconocido": True, "idOperacion": operation}
        return {"recibido": True, "idOperacion": operation, "estado": stored["estado"]}

    app.include_router(router, prefix="/sol", tags=["SOL"])
    return app


# uvicorn importa `SOL.app:app`; sin SOL_BUS_URL (las pruebas) se usa create_app con su configuración.
app = create_app() if os.getenv("SOL_BUS_URL") else None
