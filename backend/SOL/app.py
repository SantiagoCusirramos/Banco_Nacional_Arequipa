"""API ejecutable del MVP: `python -m uvicorn SOL.app:app --port 8011`.

Arranca separada del CORE para no depender de sus tablas o modificar otros
módulos. /gateway/sol es el Bus SIMULADO del laboratorio: despacha al router
de SOL en el mismo proceso. No es el Bus corporativo ni una integración real.
"""

import secrets
import asyncio
import hashlib
from time import perf_counter
from sqlalchemy import delete, func, text
from .clock import business_today
from .integrations import Integrations, CLIENT_FIELDS
from .operations import maintenance, process_delivery, security_event
from .observability import Metrics, log, valid_id
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from .database import make_database
from .integrations import captacion_reference, evaluation_envelope
from .models import (
    Application,
    ClientReference,
    Delivery,
    LoginAttempt,
    LoginSession,
    Outcome,
    User,
    Version,
    now,
    AuditOutbox,
)
from .policy import load_policy
from .schemas import ApplicationInput, Login, ResultInput, RevisionInput, EvaluationResult, DisableUser
from .security import token_hash, verify_password, hash_password
from .service import (
    check_revision,
    current_version,
    detail,
    event,
    fingerprint,
    locked_application,
    prepare,
    summary,
    projected_detail,
    read_application,
)
from .settings import Settings


def create_app(settings=None, transport=None):
    settings = settings or Settings.from_env()
    settings.validate()
    engine, factory = make_database(settings)
    integrations = Integrations(settings, transport)
    metrics = Metrics()

    @asynccontextmanager
    async def lifespan(_):
        load_policy(settings.policy_path)
        stopped = asyncio.Event()

        async def worker():
            while not stopped.is_set():
                try:
                    await asyncio.to_thread(maintenance, factory, integrations)
                except Exception:
                    log("MANTENIMIENTO_NO_DISPONIBLE", str(uuid4()))
                try:
                    await asyncio.wait_for(stopped.wait(), timeout=settings.worker_seconds)
                except asyncio.TimeoutError:
                    pass
        task = asyncio.create_task(worker()) if settings.worker_seconds > 0 else None
        yield
        stopped.set()
        if task:
            await task
        integrations.close()
        engine.dispose()

    app = FastAPI(
        title="BNA · Solicitud de Crédito MVP", version="2.0.0", lifespan=lifespan
    )
    app.state.engine, app.state.factory, app.state.settings = engine, factory, settings

    app.state.integrations, app.state.metrics = integrations, metrics

    @app.middleware("http")
    async def request_trace(request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID")
        request.state.correlation = supplied if valid_id(supplied) else str(uuid4())
        key = request.headers.get("X-Idempotency-Key")
        operation = key if valid_id(key) else None
        start = perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Correlation-ID"] = request.state.correlation
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", "NO_ENCONTRADA")
            elapsed = (perf_counter() - start) * 1000
            metrics.observe(request.method + " " + route, elapsed, status)
            log("PETICION", request.state.correlation, operation, ruta=route,
                metodo=request.method, estado=status, duracion_ms=round(elapsed, 3))

    def db_session(request: Request):
        with factory() as db:
            db.info.update(integrations=integrations, integration_mode=settings.mode,
                           correlation=request.state.correlation, operation=request.headers.get("X-Idempotency-Key"))
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def authenticated(authorization: str | None = Header(None), db=Depends(db_session)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Inicia sesión para continuar.")
        session = db.get(LoginSession, token_hash(authorization[7:]))
        if not session or session.expires < now():
            raise HTTPException(401, "La sesión venció. Vuelve a ingresar.")
        user = db.get(User, session.user_id)
        if not user or not user.active:
            raise HTTPException(401, "La cuenta fue deshabilitada.")
        return user

    def role(*allowed):
        def check(user=Depends(authenticated)):
            if user.role not in allowed:
                raise HTTPException(403, "Tu perfil no puede realizar esta operación.")
            return user

        return check

    def policy():
        try:
            return load_policy(settings.policy_path)
        except Exception:
            raise HTTPException(
                503,
                "Política inválida: revisa el archivo y su versión antes de operar.",
            )

    def correlation(request: Request):
        return request.state.correlation

    @app.exception_handler(OperationalError)
    async def database_error(request, error):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "No se pudo acceder a MySQL. Revisa .env.sol y ejecuta la inicialización del laboratorio."
            },
        )

    @app.exception_handler(IntegrityError)
    async def conflict_error(request, error):
        return JSONResponse(
            status_code=409,
            content={
                "detail": "La operación ya existe o hubo un cambio concurrente. Recarga y revisa el expediente."
            },
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "modulo": "SOL", "integracion": settings.mode}

    @app.get("/ready")
    def ready():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return {"status": "ready", "base": "disponible"}
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready", "base": "no disponible"})

    router = APIRouter()

    @router.post("/auth/login")
    def login(payload: Login, request: Request, db=Depends(db_session)):
        db.execute(delete(LoginSession).where(LoginSession.expires <= now()))
        user = db.scalar(select(User).where(User.username == payload.username).with_for_update())
        # Hash de la cuenta también para intentos de usuarios inexistentes.
        subject = hashlib.sha256((user.username if user else payload.username.casefold()).encode()).hexdigest()[:60]
        attempt = db.get(LoginAttempt, subject)
        trace = correlation(request)
        if attempt and attempt.failures >= 5 and attempt.until > now():
            security_event(db, "cuenta:" + subject, "INTENTO_BLOQUEADO", trace)
            db.commit()
            raise HTTPException(429, "Demasiados intentos. Espera 5 minutos.")
        encoded = user.password_hash if user else dummy_hash
        valid = verify_password(payload.password, encoded)
        if not user or not user.active or not valid or (settings.mode == "REAL" and user.role == "EVALUADOR"):
            if not attempt:
                attempt = LoginAttempt(username=subject, failures=0, until=now())
                db.add(attempt)
            if attempt.until <= now():
                attempt.failures = 0
            attempt.failures += 1
            attempt.until = now() + timedelta(minutes=5)
            security_event(db, "cuenta:" + subject, "INGRESO_FALLIDO", trace)
            if attempt.failures == 5:
                security_event(db, "cuenta:" + subject, "BLOQUEO_TEMPORAL", trace)
            db.commit()  # El rechazo HTTP no debe revertir los eventos ni el bloqueo.
            raise HTTPException(401, "Usuario o contraseña incorrectos.")
        if attempt:
            db.delete(attempt)
        token = secrets.token_urlsafe(32)
        db.add(LoginSession(token_hash=token_hash(token), user_id=user.id,
                            expires=now() + timedelta(hours=settings.session_hours)))
        security_event(db, user.username, "INGRESO_EXITOSO", trace)
        return {"token": token, "usuario": user_data(user)}

    @router.get("/auth/me")
    def me(user=Depends(authenticated)):
        return user_data(user)

    @router.post("/auth/logout")
    def logout(
        request: Request,
        authorization: str = Header(),
        user=Depends(authenticated),
        db=Depends(db_session),
    ):
        db.delete(db.get(LoginSession, token_hash(authorization[7:])))
        security_event(db, user.username, "CIERRE_SESION", correlation(request))
        return {"ok": True}

    @router.get("/policy")
    def get_policy(user=Depends(authenticated)):
        return {**policy().model_dump(mode="json"), "integracion": settings.mode}

    @router.get("/clients")
    def clients(request: Request, search: str = Query("", max_length=80),
                user=Depends(authenticated), db=Depends(db_session)):
        if settings.mode == "REAL":
            records = integrations.clients(search, correlation(request))
        else:
            records = list(db.scalars(select(ClientReference).where(
                ClientReference.document.contains(search, autoescape=True)
                | ClientReference.snapshot["nombres"].as_string().contains(search, autoescape=True)
                | ClientReference.snapshot["apellido_paterno"].as_string().contains(search, autoescape=True)
            ).limit(50)))
            records = [row.snapshot for row in records]
        # Todos los roles reciben solo identidad y habilitación, nunca contacto/DOB.
        return [{k: r[k] for k in CLIENT_FIELDS if k in r} for r in records]

    @router.get("/applications")
    def applications(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                     user=Depends(authenticated), db=Depends(db_session)):
        total = db.scalar(select(func.count()).select_from(Application))
        counts = dict(db.execute(select(Application.state, func.count()).group_by(Application.state)).all())
        rows = db.execute(select(Application, Version).join(Version,
            (Version.application_id == Application.id) & (Version.number == Application.current_version)
        ).order_by(Application.updated.desc(), Application.id).offset(offset).limit(limit)).all()
        return {"items": [summary(db, a, v) for a, v in rows], "total": total,
                "limit": limit, "offset": offset, "estados": counts}

    @router.post("/admin/users/{username}/disable")
    def disable_user(username: str, payload: DisableUser, request: Request,
                     user=Depends(role("SUPERVISOR")), db=Depends(db_session)):
        target = db.scalar(select(User).where(User.username == username).with_for_update())
        if not target:
            raise HTTPException(404, "Usuario no encontrado.")
        if target.id == user.id:
            raise HTTPException(409, "No puedes deshabilitar tu propia cuenta.")
        target.active = False
        removed = db.execute(delete(LoginSession).where(LoginSession.user_id == target.id)).rowcount
        security_event(db, user.username, "BAJA_USUARIO", correlation(request), target.username)
        # Identificar el afectado en el evento, sin almacenar el motivo libre en logs.
        security_event(db, user.username, "SESIONES_REVOCADAS", correlation(request), target.username)
        return {"usuario": target.username, "activo": False, "sesiones_revocadas": removed}

    @router.get("/ops/metrics")
    def get_metrics(user=Depends(role("SUPERVISOR", "AUDITOR"))):
        return metrics.snapshot()

    @router.get("/ops/pending")
    def pending(user=Depends(role("SUPERVISOR", "AUDITOR")), db=Depends(db_session)):
        return {"envios": list(db.scalars(select(Delivery.operation).where(Delivery.status != "CONFIRMADO").limit(100))),
                "auditoria": [{"estado": status, "cantidad": count} for status, count in db.execute(
                    select(AuditOutbox.status, func.count()).group_by(AuditOutbox.status))]}

    @router.post("/preview")
    def preview(
        payload: ApplicationInput, user=Depends(role("ASESOR")), db=Depends(db_session)
    ):
        return prepare(db, payload, policy())

    @router.post("/applications", status_code=201)
    def create(
        payload: ApplicationInput,
        request: Request,
        user=Depends(role("ASESOR")),
        db=Depends(db_session),
    ):
        snapshot = prepare(db, payload, policy())
        identifier = str(uuid4())
        a = Application(
            id=identifier,
            code=f"SOL-{now():%y%m}-{identifier[:8].upper()}",
            client_id=payload.id_cliente,
            state="BORRADOR",
            current_version=1,
            revision=1,
        )
        db.add(a)
        db.flush()
        db.add(
            Version(
                id=str(uuid4()),
                application_id=a.id,
                number=1,
                frozen=False,
                snapshot=snapshot,
            )
        )
        event(db, a, user, "CREAR_BORRADOR", None, correlation(request))
        return projected_detail(db, a, user)

    @router.get("/applications/{identifier}")
    def get_application(
        identifier: str, user=Depends(authenticated), db=Depends(db_session)
    ):
        return projected_detail(db, read_application(db, identifier), user)

    @router.put("/applications/{identifier}")
    def edit(
        identifier: str,
        payload: ApplicationInput,
        request: Request,
        user=Depends(role("ASESOR")),
        db=Depends(db_session),
    ):
        a = locked_application(db, identifier)
        check_revision(a, payload.revision)
        v = current_version(db, a)
        if a.state != "BORRADOR" or v.frozen:
            raise HTTPException(
                409,
                "La versión enviada está congelada. Para subsanar crea una nueva versión.",
            )
        if payload.id_cliente != a.client_id:
            raise HTTPException(
                422, "El cliente de una solicitud existente no puede sustituirse."
            )
        v.snapshot = prepare(db, payload, policy())
        a.revision += 1
        event(db, a, user, "EDITAR_BORRADOR", a.state, correlation(request))
        return projected_detail(db, a, user)

    @router.post("/applications/{identifier}/send")
    def send(
        identifier: str,
        payload: RevisionInput,
        request: Request,
        operation: str = Header(
            ..., alias="X-Idempotency-Key", min_length=8, max_length=80
        ),
        user=Depends(role("ASESOR")),
        db=Depends(db_session),
    ):
        if not valid_id(operation):
            raise HTTPException(422, "Identificador de operación inválido.")
        a = locked_application(db, identifier)
        stamp = fingerprint({"id": identifier, "revision": payload.revision})
        previous = db.get(Delivery, operation)
        if previous:
            if getattr(previous, "mode", settings.mode) != settings.mode:
                raise HTTPException(409, "La operación pertenece a otro modo de integración.")
            if previous.fingerprint != stamp:
                raise HTTPException(409, "La clave de operación ya fue utilizada para otro envío.")
            if previous.status == "CONFIRMADO":
                return {**projected_detail(db, a, user), "reintento_reconocido": True}
        else:
            check_revision(a, payload.revision)
            v = current_version(db, a)
            existing = db.scalar(select(Delivery).where(Delivery.application_id == a.id, Delivery.version == v.number))
            if existing:
                raise HTTPException(409, {"mensaje": "Reintenta con la operación pendiente.", "idOperacion": existing.operation})
            if a.state != "BORRADOR" or v.frozen:
                raise HTTPException(409, "Esta versión ya fue enviada o no admite envío.")
            captacion_reference(db, a.client_id)
            if v.snapshot["politica"] != policy().model_dump(mode="json"):
                raise HTTPException(409, "La política cambió. Guarda el borrador para recalcular antes de enviar.")
            if v.snapshot["condiciones"]["fecha_base"] < business_today().isoformat():
                raise HTTPException(409, "Actualiza la fecha base y recalcula antes de enviar.")
            envelope = evaluation_envelope(a, v, operation, correlation(request), settings.mode)
            envelope["actorEnvio"] = user.username
            db.add(Delivery(operation=operation, application_id=a.id, version=v.number,
                            fingerprint=stamp, receipt="", payload=envelope, mode=settings.mode,
                            status="PENDIENTE"))
            v.frozen = True
        db.commit()  # Reserva durable antes del HTTP: no perderla por timeout/reinicio.
        confirmed = process_delivery(factory, integrations, operation) if settings.mode == "SIMULADO" else False
        db.expire_all()
        a = read_application(db, identifier)
        if not confirmed:
            # 202 expresa aceptación local pendiente, NO confirmación de Evaluación.
            return JSONResponse(status_code=202, content={**projected_detail(db, a, user),
                                "pendiente_envio": True, "idOperacion": operation})
        return projected_detail(db, a, user)

    @router.post("/applications/{identifier}/revise")
    def revise(
        identifier: str,
        payload: RevisionInput,
        request: Request,
        user=Depends(role("ASESOR")),
        db=Depends(db_session),
    ):
        a = locked_application(db, identifier)
        check_revision(a, payload.revision)
        if a.state != "OBSERVADA":
            raise HTTPException(
                409,
                "Solo una solicitud observada admite una nueva versión de subsanación.",
            )
        previous = current_version(db, a)
        a.current_version += 1
        a.revision += 1
        a.state = "BORRADOR"
        db.add(
            Version(
                id=str(uuid4()),
                application_id=a.id,
                number=a.current_version,
                frozen=False,
                snapshot=previous.snapshot,
            )
        )
        event(
            db, a, user, "CREAR_VERSION_SUBSANACION", "OBSERVADA", correlation(request)
        )
        return projected_detail(db, a, user)

    @router.post("/applications/{identifier}/demo-result")
    def result(
        identifier: str,
        payload: ResultInput,
        request: Request,
        operation: str = Header(
            ..., alias="X-Idempotency-Key", min_length=8, max_length=80
        ),
        user=Depends(role("EVALUADOR")),
        db=Depends(db_session),
    ):
        if settings.mode != "SIMULADO":
            raise HTTPException(403, "El retorno demo está deshabilitado en modo REAL.")
        a = locked_application(db, identifier)
        stamp = fingerprint({"id": identifier, **payload.model_dump(mode="json")})
        previous = db.get(Outcome, operation)
        if previous:
            if getattr(previous, "mode", settings.mode) != settings.mode:
                raise HTTPException(409, "La operación pertenece a otro modo de integración.")
            if previous.fingerprint != stamp:
                raise HTTPException(
                    409, "La clave del resultado corresponde a otro mensaje."
                )
            return {**projected_detail(db, a, user), "reintento_reconocido": True}
        if a.state != "EN_EVALUACION" or payload.version != a.current_version:
            raise HTTPException(
                409,
                "El resultado no corresponde a una versión enviada pendiente de decisión.",
            )
        db.add(
            Outcome(
                operation=operation,
                application_id=a.id,
                version=payload.version,
                decision=payload.decision,
                observations=payload.observaciones,
                fingerprint=stamp,
            )
        )
        a.state = {
            "APROBADO": "APROBADA",
            "OBSERVADO": "OBSERVADA",
            "RECHAZADO": "RECHAZADA",
        }[payload.decision]
        a.revision += 1
        event(
            db,
            a,
            user,
            "RECIBIR_CR_INT_03_SIMULADO",
            "EN_EVALUACION",
            correlation(request),
        )
        return projected_detail(db, a, user)

    @app.post("/sol/integrations/evaluation-results")
    def evaluation_result(payload: EvaluationResult, request: Request,
                          authorization: str | None = Header(None),
                          operation: str = Header(..., alias="X-Idempotency-Key"),
                          db=Depends(db_session)):
        if settings.mode != "REAL" or not settings.callback_token or not secrets.compare_digest(
                authorization or "", "Bearer " + settings.callback_token):
            raise HTTPException(401, "Servicio no autorizado.")
        if operation != payload.idOperacion or payload.idCorrelacion != correlation(request):
            raise HTTPException(422, "Identificadores de cuerpo y cabecera diferentes.")
        a = locked_application(db, payload.idSolicitud)
        stamp = fingerprint(payload.model_dump(mode="json"))
        previous = db.get(Outcome, operation)
        if previous:
            if getattr(previous, "mode", settings.mode) != settings.mode:
                raise HTTPException(409, "La operación pertenece a otro modo de integración.")
            if previous.fingerprint != stamp:
                raise HTTPException(409, "La clave del resultado corresponde a otro mensaje.")
            return {"recibido": True, "reintento_reconocido": True, "idOperacion": operation}
        delivery = db.scalar(select(Delivery).where(Delivery.application_id == a.id,
                                                   Delivery.version == payload.versionSolicitud))
        if (a.state != "EN_EVALUACION" or a.current_version != payload.versionSolicitud
                or not delivery or delivery.status != "CONFIRMADO" or delivery.mode != "REAL"
                or (delivery.evaluation_id, delivery.round) != (payload.idEvaluacion, payload.ronda)):
            raise HTTPException(409, "Resultado incompatible con evaluación, ronda o versión pendiente.")
        db.add(Outcome(operation=operation, application_id=a.id, version=payload.versionSolicitud,
                       decision=payload.decision, observations=payload.observaciones, fingerprint=stamp,
                       evaluation_id=payload.idEvaluacion, round=payload.ronda))
        a.state = {"APROBADO": "APROBADA", "OBSERVADO": "OBSERVADA", "RECHAZADO": "RECHAZADA"}[payload.decision]
        a.revision += 1
        from types import SimpleNamespace
        event(db, a, SimpleNamespace(username="servicio:EVA"), "RECIBIR_CR_INT_03",
              "EN_EVALUACION", correlation(request))
        return {"recibido": True, "idOperacion": operation, "estado": a.state}

    # Las dos rutas ejecutan el mismo módulo. La segunda es un despachador
    # local de pruebas, explícitamente rotulado, no un gateway institucional.
    app.include_router(router, prefix="/sol", tags=["SOL interno"])
    if settings.mode == "SIMULADO":
        app.include_router(router, prefix="/gateway/sol", tags=["Bus SIMULADO"])
    return app


def user_data(user):
    return {"username": user.username, "nombre": user.name, "rol": user.role}


dummy_hash = hash_password(secrets.token_urlsafe(24))
app = create_app()
