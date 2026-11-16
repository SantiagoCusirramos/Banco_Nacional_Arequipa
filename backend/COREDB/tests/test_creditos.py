"""Créditos sin base de datos: regla RN-EVA-002-P, permisos por ruta, errores y cuerpos."""

import uuid
from decimal import Decimal

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from COREDB import permisos
from COREDB.auth import actor_actual
from COREDB.auth_tipos import Actor
from COREDB.errores import ErrorCoreDb
from COREDB.main import app
from COREDB.services import creditos, regla_evaluacion

MONTO = Decimal("15000.00")


# ── RN-EVA-002-P, portada de backend/EVALUACION/motor.py (#70) ───────────────
# El resultado lo decide la base con los umbrales de creditos.regla_evaluacion; las
# fronteras 80 % / 100 % se prueban contra la base en integracion/test_creditos_evaluacion.py.


@pytest.mark.parametrize(("ingreso", "deuda", "riesgo", "limite", "ratio"), [
    ("5000.00", "0.00", "BUENO", "21000.00", "0.7143"),
    ("4000.00", "0.00", "BUENO", "16800.00", "0.8929"),
    ("3000.00", "0.00", "BUENO", "12600.00", "1.1905"),
    ("6000.00", "0.00", "REGULAR", "18900.00", "0.7937"),
    ("6000.00", "0.00", "ALTO", "10080.00", "1.4881"),
])
def test_limite_y_ratio_segun_capacidad_y_riesgo(ingreso, deuda, riesgo, limite, ratio):
    r = regla_evaluacion.calcular(MONTO, 12, Decimal(ingreso), Decimal(deuda), riesgo)
    assert (r.limite, r.ratio) == (Decimal(limite), Decimal(ratio))


def test_score_por_riesgo():
    assert {riesgo: regla_evaluacion.calcular(MONTO, 12, Decimal("5000"), Decimal("0"), riesgo).score
            for riesgo in ("BUENO", "REGULAR", "ALTO")} == {"BUENO": 850, "REGULAR": 650, "ALTO": 400}


@pytest.mark.parametrize(("ingreso", "deuda"), [("1000.00", "500.00"), ("5000.00", "1750.00")])
def test_sin_capacidad_el_limite_es_cero_y_no_hay_ratio(ingreso, deuda):
    r = regla_evaluacion.calcular(MONTO, 12, Decimal(ingreso), Decimal(deuda), "BUENO")
    assert (r.limite, r.ratio) == (Decimal("0.00"), None)


def test_limite_redondeado_al_centimo():
    # 35 % de 1000.01 = 350.0035; × 7 × 0.75 = 1837.518375 → 1837.52
    r = regla_evaluacion.calcular(Decimal("100"), 7, Decimal("1000.01"), Decimal("0"), "REGULAR")
    assert r.limite == Decimal("1837.52")


# ── Permisos ─────────────────────────────────────────────────────────────────

RUTAS_CREDITO = {
    ("POST", "/coredb/creditos/solicitudes"): "CREAR_SOLICITUD_CREDITO",
    ("GET", "/coredb/creditos/solicitudes"): "VER_CREDITO",
    ("GET", "/coredb/creditos/solicitudes/{id_solicitud}"): "VER_CREDITO",
    ("POST", "/coredb/creditos/solicitudes/{id_solicitud}/evaluaciones"): "EVALUAR_CREDITO",
    ("POST", "/coredb/creditos/evaluaciones/{id_evaluacion}/decision"): "APROBAR_CREDITO",
    ("POST", "/coredb/creditos/solicitudes/{id_solicitud}/revocacion"): "APROBAR_CREDITO",
    ("GET", "/coredb/creditos/aprobaciones"): "VER_CREDITO",
    ("POST", "/coredb/creditos/analistas"): "CREAR_USUARIO",
    ("POST", "/coredb/creditos/ordenes"): "DESEMBOLSAR_CREDITO",
    ("GET", "/coredb/creditos/ordenes"): "VER_CREDITO",
    ("GET", "/coredb/creditos/ordenes/{id_orden}"): "VER_CREDITO",
    ("PUT", "/coredb/creditos/ordenes/{id_orden}/cuenta"): "DESEMBOLSAR_CREDITO",
    ("POST", "/coredb/creditos/ordenes/{id_orden}/validaciones"): "DESEMBOLSAR_CREDITO",
    ("POST", "/coredb/creditos/ordenes/{id_orden}/confirmacion"): "DESEMBOLSAR_CREDITO",
    ("POST", "/coredb/creditos/ordenes/{id_orden}/rechazo"): "DESEMBOLSAR_CREDITO",
    ("GET", "/coredb/creditos/conciliacion/desembolsos"): "GENERAR_REPORTES",
}


def _dependencias(dependant):
    for dependencia in dependant.dependencies:
        yield dependencia.call
        yield from _dependencias(dependencia)


def _acciones_por_ruta():
    resultado = {}
    for ruta in app.routes:
        if isinstance(ruta, APIRoute) and ruta.path.startswith("/coredb/creditos"):
            acciones = {getattr(c, "accion", None) for c in _dependencias(ruta.dependant)} - {None}
            for metodo in ruta.methods:
                resultado[(metodo, ruta.path)] = acciones
    return resultado


def test_cada_ruta_de_creditos_exige_su_permiso():
    assert _acciones_por_ruta() == {ruta: {accion} for ruta, accion in RUTAS_CREDITO.items()}


def test_catalogo_de_creditos_solo_exige_sesion():
    ruta = next(r for r in app.routes if isinstance(r, APIRoute) and r.path == "/coredb/catalogos/creditos")
    llamadas = set(_dependencias(ruta.dependant))
    assert actor_actual in llamadas
    assert not {getattr(c, "accion", None) for c in llamadas} - {None}


def test_acciones_nuevas_de_coredb():
    assert {"DESEMBOLSAR_CREDITO", "REGISTRAR_MORA"} <= permisos.ACCIONES
    assert "DESEMBOLSAR_CREDITO" in permisos.PERMISOS["OPERADOR"]
    assert {"DESEMBOLSAR_CREDITO", "REGISTRAR_MORA"} <= permisos.PERMISOS["ADMINISTRADOR"]
    assert "REGISTRAR_MORA" not in permisos.PERMISOS["OPERADOR"]


def test_el_operador_verifica_la_identidad_para_desembolsar():
    # La evidencia IDENTIDAD de una orden es la verificación de documento en ventanilla.
    assert {permisos.VALIDAR_IDENTIDAD, "DESEMBOLSAR_CREDITO"} <= permisos.PERMISOS["OPERADOR"]
    assert "GENERAR_REPORTES" not in permisos.PERMISOS["OPERADOR"]


def test_usuarios_de_servicio_de_creditos():
    assert permisos.PERMISOS["SERVICIO:EVALUACION"] == {"CREAR_SOLICITUD_CREDITO", "VER_CREDITO"}
    assert permisos.PERMISOS["SERVICIO:DESEMBOLSO"] == {"VER_CREDITO", "VER_CUENTA"}
    assert permisos.PERMISOS["SERVICIO:COBRANZA"] == {"VER_CREDITO", "CONSULTAR_DEUDA", "REGISTRAR_MORA"}


def test_el_servicio_de_evaluacion_no_evalua_ni_decide():
    servicio = Actor(uuid.uuid4(), "svc-evaluacion", "SERVICIO", "EVALUACION")
    assert permisos.puede(servicio, "CREAR_SOLICITUD_CREDITO")
    assert not permisos.puede(servicio, "EVALUAR_CREDITO")
    assert not permisos.puede(servicio, "APROBAR_CREDITO")


# ── Errores de la base ───────────────────────────────────────────────────────

# Los códigos que lanzan registrar_solicitud, evaluar_solicitud, decidir_evaluacion,
# revocar_aprobacion y registrar_analista (database/sql/bna_extension.sql, sección 12).
CODIGOS_EVALUACION = {
    "BNA-SOLICITUD": "SOLICITUD_NO_ADMITIDA",
    "BNA-CLIENTE": "CLIENTE_NO_HABILITADO",
    "BNA-CALENDARIO": "CALENDARIO_INVALIDO",
    "BNA-IDEMPOTENCIA": "IDEMPOTENCIA_CONFLICTO",
    "BNA-EVALUACION": "EVALUACION_NO_ADMITIDA",
    "BNA-REGLA": "REGLA_NO_DISPONIBLE",
    "BNA-ANALISTA": "ANALISTA_REQUERIDO",
    "BNA-MOTIVO": "MOTIVO_REQUERIDO",
    "BNA-EMPLEADO": "EMPLEADO_NO_HABILITADO",
}


@pytest.mark.parametrize(("regla", "codigo"), CODIGOS_EVALUACION.items())
def test_cada_codigo_de_la_base_tiene_su_error(regla, codigo):
    traducido = creditos.traducir(ErrorCoreDb(regla, f"{regla}: algo sin valores"))
    assert traducido.code == codigo
    assert traducido.status_code == (409 if codigo == "IDEMPOTENCIA_CONFLICTO" else 422)
    assert regla not in traducido.message


# Los de preparar_orden, cambiar_cuenta_orden, registrar_validacion_orden, confirmar_orden y
# rechazar_orden, más los del disparador validar_orden y los de cuentas.validar_canal.
CODIGOS_DESEMBOLSO = {
    "BNA-APROBACION": "APROBACION_NO_VIGENTE",
    "BNA-ORDEN": "ORDEN_NO_ADMITIDA",
    "BNA-ORDEN-UNICA": "ORDEN_NO_ADMITIDA",
    "BNA-CUENTA-DESTINO": "CUENTA_NO_ELEGIBLE",
    "BNA-IMPORTE": "IMPORTE_NO_ADMITIDO",
    "BNA-VALIDACION": "VALIDACION_NO_ADMITIDA",
    "BNA-CANAL": "CANAL_NO_ADMITIDO",
    "BNA-NUMERACION": "NUMERACION_AGOTADA",
}


@pytest.mark.parametrize(("regla", "codigo"), CODIGOS_DESEMBOLSO.items())
def test_cada_codigo_del_desembolso_tiene_su_error(regla, codigo):
    traducido = creditos.traducir(ErrorCoreDb(regla, f"{regla}: algo sin valores"))
    assert (traducido.code, traducido.status_code) == (codigo, 422)
    assert regla not in traducido.message


@pytest.mark.parametrize("mensaje", [
    "BNA-CUENTA-DESTINO: la cuenta CTA-0000000000001234 no pertenece al cliente C001 de la solicitud",
    "BNA-IMPORTE: el importe 15000.00 supera el límite aprobado 12000.00",
    "BNA-ORDEN-UNICA: la solicitud 0b6f0000-0000-4000-8000-000000000001 ya tiene una orden CONFIRMADA",
    "BNA-CANAL: canal desconocido XYZ",
])
def test_los_mensajes_del_desembolso_no_repiten_valores(mensaje):
    traducido = creditos.traducir(ErrorCoreDb(mensaje.split(":")[0], mensaje))
    for valor in ("CTA-0000000000001234", "C001", "15000", "12000", "0b6f0000", "XYZ"):
        assert valor not in traducido.message


def test_un_analista_duplicado_es_409():
    error = ErrorCoreDb("REGISTRO_DUPLICADO", "x", 409)
    error.restriccion = "PRIMARY"
    assert creditos.traducir(error).code == "ANALISTA_DUPLICADO"


# ── Cuerpos ──────────────────────────────────────────────────────────────────


def _expediente(**cambios):
    cuerpo = {
        "idSolicitud": str(uuid.uuid4()),
        "versionSolicitud": 1,
        "codCliente": "C001",
        "montoSolicitado": "1000.00",
        "moneda": "PEN",
        "plazoMeses": 2,
        "calendario": {
            "metodo": "FRANCES",
            "tasa": "0.2200",
            "cuotas": [
                {"numeroCuota": 1, "fechaVencimiento": "2031-01-15", "saldoInicial": "1000.00",
                 "amortizacion": "500.00", "interes": "18.33", "cuotaTotal": "518.33", "saldoFinal": "500.00"},
                {"numeroCuota": 2, "fechaVencimiento": "2031-02-15", "saldoInicial": "500.00",
                 "amortizacion": "500.00", "interes": "9.17", "cuotaTotal": "509.17", "saldoFinal": "0.00"},
            ],
        },
    }
    cuerpo.update(cambios)
    return cuerpo


def _modelo(**cambios):
    from COREDB.routers.creditos_evaluacion import ExpedienteRegistrar

    return ExpedienteRegistrar.model_validate(_expediente(**cambios))


def test_el_expediente_usa_camel_case_y_rechaza_campos_desconocidos():
    from pydantic import ValidationError

    assert _modelo().id_solicitud
    with pytest.raises(ValidationError):
        _modelo(otro=1)
    with pytest.raises(ValidationError):
        _modelo(id_solicitud=str(uuid.uuid4()))


@pytest.mark.parametrize("cambio", [
    {"idSolicitud": "no-es-uuid"}, {"versionSolicitud": 0}, {"montoSolicitado": "0"},
    {"moneda": "pen"}, {"codCliente": "C 01"}, {"plazoMeses": 0},
])
def test_el_expediente_valida_sus_campos(cambio):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _modelo(**cambio)


def test_la_huella_no_depende_del_formato_de_los_numeros():
    id_solicitud = str(uuid.uuid4())
    a = _modelo(idSolicitud=id_solicitud)
    b = _modelo(idSolicitud=id_solicitud, montoSolicitado=1000,
                calendario={**_expediente()["calendario"], "tasa": 0.22})
    otro_destino = _modelo(idSolicitud=id_solicitud, destino="Capital de trabajo")
    assert creditos.huella_expediente(a) == creditos.huella_expediente(b)
    assert creditos.huella_expediente(a) != creditos.huella_expediente(otro_destino)


def _orden(**cambios):
    from COREDB.routers.creditos_desembolso import OrdenPreparar

    cuerpo = {"idEvaluacion": str(uuid.uuid4()), "numCuenta": "CTA-1"}
    cuerpo.update(cambios)
    return OrdenPreparar.model_validate(cuerpo)


def test_la_orden_usa_camel_case_y_ventanilla_por_omision():
    from pydantic import ValidationError

    orden = _orden()
    assert (orden.canal, orden.id_agencia) == ("VEN", None)
    for cambio in ({"otro": 1}, {"num_cuenta": "CTA-1"}, {"canal": "ATM"}, {"numCuenta": ""},
                   {"idEvaluacion": "no-es-uuid"}):
        with pytest.raises(ValidationError):
            _orden(**cambio)


def test_la_huella_de_la_orden_cambia_con_su_contenido():
    id_evaluacion = str(uuid.uuid4())
    base = creditos.huella_orden(_orden(idEvaluacion=id_evaluacion))
    assert base == creditos.huella_orden(_orden(idEvaluacion=id_evaluacion, canal="VEN"))
    assert base != creditos.huella_orden(_orden(idEvaluacion=id_evaluacion, numCuenta="CTA-2"))
    assert base != creditos.huella_orden(_orden(idEvaluacion=id_evaluacion, canal="HB"))
    assert base != creditos.huella_orden(_orden(idEvaluacion=id_evaluacion, idAgencia="AQP01"))


@pytest.mark.parametrize("cuerpo", [
    {"tipo": "CUENTA", "resultado": "APROBADA", "referenciaEvidencia": "1"},
    {"tipo": "IDENTIDAD", "resultado": "OBSERVADA", "referenciaEvidencia": "1"},
    {"tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": ""},
    {"tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": "1", "venceEn": "2030-01-01T00:00:00"},
])
def test_cuerpo_de_la_validacion(cuerpo):
    from pydantic import ValidationError

    from COREDB.routers.creditos_desembolso import ValidacionRegistrar

    with pytest.raises(ValidationError):
        ValidacionRegistrar.model_validate(cuerpo)


def test_sin_token_401_en_creditos():
    respuesta = TestClient(app).get("/coredb/creditos/solicitudes")
    assert respuesta.status_code == 401
