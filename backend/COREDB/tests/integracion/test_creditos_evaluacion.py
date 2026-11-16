"""Créditos, área de evaluación (CONTRATO_CREDITOS.md §3) contra la base real."""

import uuid
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app

CENTIMO = Decimal("0.01")
BASE = "/coredb/creditos"


@pytest.fixture
def api():
    return TestClient(app, raise_server_exceptions=False)


def _sesion_servicio(autorizacion, modulo):
    api = TestClient(app)
    creado = api.post(
        "/coredb/usuarios/servicios",
        json={"modulo": modulo, "username": "svc-" + uuid.uuid4().hex[:10], "nombre": modulo.title()},
        headers=autorizacion,
    )
    assert creado.status_code == 201, creado.text
    cuerpo = creado.json()
    login = api.post("/coredb/auth/login",
                     json={"username": cuerpo["usuario"]["username"], "password": cuerpo["secreto"]})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, cuerpo["usuario"]["username"]


@pytest.fixture(scope="module")
def servicio(autorizacion, datos_base):
    """Encabezados y nombre del usuario de servicio del módulo Evaluación."""
    return _sesion_servicio(autorizacion, "EVALUACION")


@pytest.fixture(scope="module")
def cliente_bloqueado(admin, datos_base):
    with admin.cursor() as cursor:
        cursor.execute("INSERT IGNORE INTO clientes.verificacion_captacion (id_verificacion_captacion, "
                       "estado_habilitante) VALUES ('VC-CR-3', 'HABILITADO')")
        cursor.execute(
            "INSERT IGNORE INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, "
            "apellido_paterno, correo, celular, estado_cliente, id_verificacion_captacion, version_contrato) "
            "VALUES ('CCR03', 'DNI', '70000903', 'Rosa', 'Quispe', 'rq@example.com', '959000903', 'BLOQUEADO', "
            "'VC-CR-3', 'v1')")
    return "CCR03"


def _empleado(admin, cargo="ANALISTA"):
    codigo = "E" + uuid.uuid4().hex[:10].upper()
    id_empleado = uuid.uuid4()
    with admin.cursor() as cursor:
        cursor.execute(
            "INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo) "
            "VALUES (%s, %s, 'Analista de pruebas', %s)", (id_empleado.bytes, codigo, cargo))
    return id_empleado


def _usuario_con_empleado(autorizacion, rol, id_empleado):
    api = TestClient(app)
    username, password = "u" + uuid.uuid4().hex[:12], "clave-de-un-usuario-1"
    creado = api.post("/coredb/usuarios", headers=autorizacion, json={
        "username": username, "nombre": "N", "password": password, "rol": rol,
        "id_empleado": str(id_empleado)})
    assert creado.status_code == 201, creado.text
    login = api.post("/coredb/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture(scope="module")
def analista(autorizacion, admin, datos_base):
    """Sesión de un ANALISTA ligado a un empleado registrado como analista de crédito."""
    id_empleado = _empleado(admin)
    registrado = TestClient(app).post(f"{BASE}/analistas", json={"idEmpleado": str(id_empleado)},
                                      headers=autorizacion)
    assert registrado.status_code == 201, registrado.text
    return _usuario_con_empleado(autorizacion, "ANALISTA", id_empleado)


@pytest.fixture(scope="module")
def analista_sin_registro(autorizacion, admin, datos_base):
    return _usuario_con_empleado(autorizacion, "ANALISTA", _empleado(admin))


def calendario(monto, plazo, inicio=None):
    """Un calendario coherente: amortización constante y 1 % de interés mensual."""
    inicio = inicio or date.today() + timedelta(days=40)
    monto = Decimal(monto)
    amortizacion = (monto / plazo).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    saldo, cuotas = monto, []
    for n in range(1, plazo + 1):
        capital = saldo if n == plazo else amortizacion
        interes = (saldo * Decimal("0.01")).quantize(CENTIMO, rounding=ROUND_HALF_UP)
        cuotas.append({
            "numeroCuota": n, "fechaVencimiento": (inicio + timedelta(days=30 * (n - 1))).isoformat(),
            "saldoInicial": str(saldo), "amortizacion": str(capital), "interes": str(interes),
            "cuotaTotal": str(capital + interes), "saldoFinal": str(saldo - capital),
        })
        saldo -= capital
    return {"metodo": "FRANCES", "tasa": "0.1200", "cuotas": cuotas}


def expediente(monto="15000.00", plazo=12, version=1, id_solicitud=None, cod_cliente="C001", **cambios):
    cuerpo = {
        "idSolicitud": id_solicitud or str(uuid.uuid4()), "versionSolicitud": version,
        "codCliente": cod_cliente, "montoSolicitado": monto, "moneda": "PEN", "plazoMeses": plazo,
        "calendario": calendario(monto, plazo),
    }
    cuerpo.update(cambios)
    return cuerpo


def registrar(api, servicio, **datos):
    cuerpo = expediente(**datos)
    respuesta = api.post(f"{BASE}/solicitudes", json=cuerpo, headers=servicio[0])
    assert respuesta.status_code == 201, respuesta.text
    return cuerpo, respuesta.json()


def evaluar(api, encabezados, id_solicitud, ingreso, deuda="0.00", riesgo="BUENO", version=1, verificada=True):
    return api.post(f"{BASE}/solicitudes/{id_solicitud}/evaluaciones", headers=encabezados, json={
        "versionSolicitud": version, "ingresoMensual": ingreso, "deudaMensual": deuda, "riesgo": riesgo,
        "verificada": verificada})


def evaluada(api, servicio, analista, ingreso, monto="15000.00", **datos):
    cuerpo, recibo = registrar(api, servicio, monto=monto, **datos)
    respuesta = evaluar(api, analista, cuerpo["idSolicitud"], ingreso)
    assert respuesta.status_code == 200, respuesta.text
    return cuerpo["idSolicitud"], respuesta.json()


# ── Expediente (CR-INT-02) ──────────────────────────────────────────────────


def test_registra_el_expediente_y_entrega_el_acuse(api, servicio, consulta):
    correlacion = str(uuid.uuid4())
    cuerpo = expediente()
    respuesta = api.post(f"{BASE}/solicitudes", json=cuerpo,
                         headers={**servicio[0], "X-Correlation-ID": correlacion})
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.headers["X-Correlation-ID"] == correlacion
    recibo = respuesta.json()
    (esperado,) = consulta("SELECT BIN_TO_UUID(creditos.fn_id_evaluacion(UUID_TO_BIN(%s), 1)) AS id",
                           cuerpo["idSolicitud"])
    assert recibo == {"idSolicitud": cuerpo["idSolicitud"], "versionSolicitud": 1, "ronda": 1,
                      "idEvaluacion": esperado["id"], "estado": "EN_EVALUACION"}
    (evento,) = consulta(
        "SELECT actor, BIN_TO_UUID(correlation_id) AS correlacion FROM core.evento_auditoria "
        "WHERE accion = 'REGISTRAR_SOLICITUD' AND id_entidad = %s", cuerpo["idSolicitud"])
    assert evento == {"actor": servicio[1], "correlacion": correlacion}


def test_el_mismo_expediente_devuelve_el_mismo_acuse_y_otro_contenido_es_409(api, servicio, consulta):
    cuerpo, recibo = registrar(api, servicio)
    repetido = api.post(f"{BASE}/solicitudes", json=cuerpo, headers=servicio[0])
    assert repetido.status_code == 200
    assert repetido.json() == recibo
    otro = api.post(f"{BASE}/solicitudes", json={**cuerpo, "destino": "Otro destino"}, headers=servicio[0])
    assert otro.status_code == 409
    assert otro.json()["error"]["code"] == "IDEMPOTENCIA_CONFLICTO"
    (fila,) = consulta("SELECT count(*) AS n FROM creditos.recepcion_solicitud WHERE id_solicitud = UUID_TO_BIN(%s)",
                       cuerpo["idSolicitud"])
    assert fila["n"] == 1


def test_una_version_nueva_abre_otra_ronda(api, servicio, consulta):
    cuerpo, primero = registrar(api, servicio)
    segunda = expediente(monto="12000.00", version=2, id_solicitud=cuerpo["idSolicitud"])
    respuesta = api.post(f"{BASE}/solicitudes", json=segunda, headers=servicio[0])
    assert respuesta.status_code == 201, respuesta.text
    assert (respuesta.json()["ronda"], respuesta.json()["versionSolicitud"]) == (2, 2)
    assert respuesta.json()["idEvaluacion"] != primero["idEvaluacion"]
    estados = consulta("SELECT version, estado_calendario FROM creditos.calendario_pago "
                       "WHERE id_solicitud = UUID_TO_BIN(%s) ORDER BY version", cuerpo["idSolicitud"])
    assert [(f["version"], f["estado_calendario"]) for f in estados] == [(1, "HISTORICO"), (2, "VIGENTE")]


@pytest.mark.parametrize("cliente", ["NOEXISTE", "bloqueado"])
def test_cliente_que_no_puede_operar(api, servicio, cliente_bloqueado, cliente):
    cod = cliente_bloqueado if cliente == "bloqueado" else cliente
    respuesta = api.post(f"{BASE}/solicitudes", json=expediente(cod_cliente=cod), headers=servicio[0])
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "CLIENTE_NO_HABILITADO"
    assert cod not in respuesta.text


def test_calendario_incoherente(api, servicio):
    cuerpo = expediente()
    cuerpo["calendario"]["cuotas"][0]["interes"] = "999.99"
    respuesta = api.post(f"{BASE}/solicitudes", json=cuerpo, headers=servicio[0])
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "CALENDARIO_INVALIDO"
    assert "999" not in respuesta.text


def test_permisos_del_expediente(api, servicio, analista):
    assert api.post(f"{BASE}/solicitudes", json=expediente()).status_code == 401
    respuesta = api.post(f"{BASE}/solicitudes", json=expediente(), headers=analista)
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_reintenta_el_registro_tras_un_deadlock(api, servicio, fallar_una_vez, consulta):
    from COREDB.services import creditos

    intentos = fallar_una_vez(creditos, 1213)
    cuerpo = expediente()
    respuesta = api.post(f"{BASE}/solicitudes", json=cuerpo, headers=servicio[0])
    assert respuesta.status_code == 201, respuesta.text
    assert intentos.count("creditos.registrar_solicitud") == 2


# ── Bandeja y detalle ───────────────────────────────────────────────────────


def test_bandeja_y_detalle(api, servicio, analista):
    cuerpo, recibo = registrar(api, servicio, cod_cliente="C002", plazo=3, monto="900.00")
    bandeja = api.get(f"{BASE}/solicitudes", params={"estado": "EN_EVALUACION", "codCliente": "C002"},
                      headers=analista)
    assert bandeja.status_code == 200, bandeja.text
    fila = next(s for s in bandeja.json() if s["idSolicitud"] == cuerpo["idSolicitud"])
    assert {k: fila[k] for k in ("codCliente", "estado", "ronda", "numeroCuotas", "montoSolicitado")} == {
        "codCliente": "C002", "estado": "EN_EVALUACION", "ronda": 1, "numeroCuotas": 3,
        "montoSolicitado": "900.00"}
    assert all(s["codCliente"] == "C002" and s["estado"] == "EN_EVALUACION" for s in bandeja.json())

    detalle = api.get(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}", headers=servicio[0])
    assert detalle.status_code == 200, detalle.text
    datos = detalle.json()
    assert [c["numeroCuota"] for c in datos["calendario"]["cuotas"]] == [1, 2, 3]
    assert datos["calendario"]["cuotas"][0]["cuotaTotal"] == cuerpo["calendario"]["cuotas"][0]["cuotaTotal"]
    assert datos["calendario"]["tipo"] == "PRELIMINAR"
    assert datos["evaluaciones"] == []
    assert [h["estado"] for h in datos["historial"]] == ["EN_EVALUACION"]


def test_detalle_de_una_solicitud_inexistente(api, analista):
    respuesta = api.get(f"{BASE}/solicitudes/{uuid.uuid4()}", headers=analista)
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "SOLICITUD_NO_ENCONTRADA"


def test_bandeja_rechaza_estado_desconocido(api, analista):
    assert api.get(f"{BASE}/solicitudes", params={"estado": "OTRO"}, headers=analista).status_code == 422


# ── Evaluación (RN-EVA-002-P) ───────────────────────────────────────────────


@pytest.mark.parametrize(("ingreso", "riesgo", "resultado", "regla", "estado", "limite"), [
    ("5000.00", "BUENO", "APROBADO", "R-A", "APROBADA", "21000.00"),
    ("4000.00", "BUENO", "OBSERVADO", "R-B", "EN_EVALUACION", "16800.00"),
    ("3000.00", "BUENO", "RECHAZADO", "R-C", "RECHAZADA", "12600.00"),
    ("6000.00", "REGULAR", "APROBADO", "R-A", "APROBADA", "18900.00"),
    ("6000.00", "ALTO", "RECHAZADO", "R-C", "RECHAZADA", "10080.00"),
])
def test_los_tres_tramos_de_la_regla(api, servicio, analista, ingreso, riesgo, resultado, regla, estado, limite):
    cuerpo, recibo = registrar(api, servicio)
    respuesta = evaluar(api, analista, cuerpo["idSolicitud"], ingreso, riesgo=riesgo)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert (datos["resultado"], datos["regla"], datos["estadoSolicitud"], datos["limite"]) == (
        resultado, regla, estado, limite)
    assert datos["idEvaluacion"] == recibo["idEvaluacion"]
    detalle = api.get(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}", headers=analista).json()
    assert detalle["estado"] == estado
    assert detalle["evaluaciones"][0]["resultado"] == resultado


@pytest.mark.parametrize(("monto", "resultado"), [
    ("15000.00", "APROBADO"), ("15000.01", "OBSERVADO"), ("18750.00", "OBSERVADO"), ("18750.01", "RECHAZADO"),
])
def test_fronteras_de_la_regla_con_los_umbrales_de_la_base(api, servicio, analista, monto, resultado):
    # Ingreso 10000.00 y deuda 1937.50: capacidad 1562.50 y límite 18750.00 a 12 meses (test_motor.py de #70).
    cuerpo, _ = registrar(api, servicio, monto=monto)
    respuesta = evaluar(api, analista, cuerpo["idSolicitud"], "10000.00", deuda="1937.50")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resultado"] == resultado


def test_sin_capacidad_rechaza_con_la_regla_c(api, servicio, analista):
    cuerpo, _ = registrar(api, servicio)
    datos = evaluar(api, analista, cuerpo["idSolicitud"], "1000.00", deuda="500.00").json()
    assert (datos["resultado"], datos["regla"], datos["limite"], datos["ratio"], datos["score"]) == (
        "RECHAZADO", "R-C", "0.00", None, 850)


def test_situacion_no_verificada(api, servicio, analista, consulta):
    cuerpo, _ = registrar(api, servicio)
    respuesta = evaluar(api, analista, cuerpo["idSolicitud"], "5000.00", verificada=False)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "SITUACION_NO_VERIFICADA"
    (fila,) = consulta("SELECT count(*) AS n FROM creditos.evaluacion WHERE id_solicitud = UUID_TO_BIN(%s)",
                       cuerpo["idSolicitud"])
    assert fila["n"] == 0


def test_una_ronda_se_evalua_una_vez_y_despues_no_admite_versiones(api, servicio, analista):
    id_solicitud, _ = evaluada(api, servicio, analista, "4000.00")
    otra = evaluar(api, analista, id_solicitud, "5000.00")
    assert otra.status_code == 422
    assert otra.json()["error"]["code"] == "EVALUACION_NO_ADMITIDA"
    version = api.post(f"{BASE}/solicitudes", json=expediente(version=2, id_solicitud=id_solicitud),
                       headers=servicio[0])
    assert version.status_code == 422
    assert version.json()["error"]["code"] == "SOLICITUD_NO_ADMITIDA"


def test_evaluar_una_version_que_no_es_la_vigente(api, servicio, analista):
    cuerpo, _ = registrar(api, servicio)
    respuesta = evaluar(api, analista, cuerpo["idSolicitud"], "5000.00", version=2)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "SOLICITUD_NO_ADMITIDA"


def test_evaluar_una_solicitud_inexistente_y_permisos(api, servicio, analista):
    respuesta = evaluar(api, analista, uuid.uuid4(), "5000.00")
    assert respuesta.status_code == 404
    cuerpo, _ = registrar(api, servicio)
    assert evaluar(api, servicio[0], cuerpo["idSolicitud"], "5000.00").status_code == 403


def test_la_evaluacion_registra_al_analista_como_actor(api, servicio, analista, consulta):
    id_solicitud, datos = evaluada(api, servicio, analista, "5000.00")
    (evento,) = consulta("SELECT actor FROM core.evento_auditoria WHERE accion = 'EVALUAR_SOLICITUD' "
                         "AND id_entidad = %s", datos["idEvaluacion"])
    assert evento["actor"].startswith("u")


# ── Decisión del analista ───────────────────────────────────────────────────


def decidir(api, encabezados, id_evaluacion, decision="APROBADO", comentario="Ingresos verificados en planilla"):
    return api.post(f"{BASE}/evaluaciones/{id_evaluacion}/decision", headers=encabezados,
                    json={"decision": decision, "comentario": comentario})


def test_el_analista_decide_una_evaluacion_observada_una_vez(api, servicio, analista):
    id_solicitud, datos = evaluada(api, servicio, analista, "4000.00")
    respuesta = decidir(api, analista, datos["idEvaluacion"])
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"idEvaluacion": datos["idEvaluacion"], "idSolicitud": id_solicitud,
                                "decision": "APROBADO", "estadoSolicitud": "APROBADA"}
    otra = decidir(api, analista, datos["idEvaluacion"], decision="RECHAZADO")
    assert otra.status_code == 422
    assert otra.json()["error"]["code"] == "EVALUACION_NO_ADMITIDA"
    detalle = api.get(f"{BASE}/solicitudes/{id_solicitud}", headers=analista).json()
    evaluacion = detalle["evaluaciones"][0]
    assert (evaluacion["decision"], evaluacion["resultado"], evaluacion["idAnalista"][:2]) == (
        "APROBADO", "APROBADO", "AN")


def test_decidir_rechazado(api, servicio, analista):
    _, datos = evaluada(api, servicio, analista, "4000.00")
    assert decidir(api, analista, datos["idEvaluacion"], "RECHAZADO").json()["estadoSolicitud"] == "RECHAZADA"


def test_sin_analista_registrado(api, servicio, analista, analista_sin_registro):
    _, datos = evaluada(api, servicio, analista, "4000.00")
    respuesta = decidir(api, analista_sin_registro, datos["idEvaluacion"])
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "ANALISTA_REQUERIDO"


def test_solo_se_decide_una_evaluacion_observada(api, servicio, analista):
    _, datos = evaluada(api, servicio, analista, "5000.00")
    respuesta = decidir(api, analista, datos["idEvaluacion"])
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "EVALUACION_NO_ADMITIDA"


@pytest.mark.parametrize("cuerpo", [
    {"decision": "OBSERVADO", "comentario": "Falta una boleta de pago"},
    {"decision": "APROBADO", "comentario": "corto"},
    {"decision": "APROBADO", "comentario": "Comentario válido", "otro": 1},
])
def test_cuerpo_de_la_decision(api, analista, cuerpo):
    respuesta = api.post(f"{BASE}/evaluaciones/{uuid.uuid4()}/decision", headers=analista, json=cuerpo)
    assert respuesta.status_code == 422


def test_decidir_una_evaluacion_inexistente_y_permisos(api, servicio, analista, sesion_de):
    respuesta = decidir(api, analista, uuid.uuid4())
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "EVALUACION_NO_ENCONTRADA"
    asesor, _ = sesion_de("ASESOR")
    assert decidir(api, asesor, uuid.uuid4()).status_code == 403


# ── Aprobaciones y revocación ───────────────────────────────────────────────


def test_aprobaciones_vigentes(api, servicio, analista):
    id_solicitud, datos = evaluada(api, servicio, analista, "5000.00", cod_cliente="C002")
    respuesta = api.get(f"{BASE}/aprobaciones", params={"idSolicitud": id_solicitud}, headers=servicio[0])
    assert respuesta.status_code == 200, respuesta.text
    (aprobacion,) = respuesta.json()
    assert {k: aprobacion[k] for k in ("idEvaluacion", "codCliente", "monto", "moneda", "plazoMeses", "ronda")} == {
        "idEvaluacion": datos["idEvaluacion"], "codCliente": "C002", "monto": "15000.00", "moneda": "PEN",
        "plazoMeses": 12, "ronda": 1}
    fecha = datetime.fromisoformat(aprobacion["fechaAprobacion"])
    assert datetime.fromisoformat(aprobacion["vigenteHasta"]) - fecha == timedelta(days=30)
    por_cliente = api.get(f"{BASE}/aprobaciones", params={"codCliente": "C002"}, headers=servicio[0]).json()
    assert id_solicitud in {a["idSolicitud"] for a in por_cliente}
    assert all(a["codCliente"] == "C002" for a in por_cliente)


def test_revocar_una_aprobacion(api, servicio, analista, consulta):
    id_solicitud, _ = evaluada(api, servicio, analista, "5000.00")
    respuesta = api.post(f"{BASE}/solicitudes/{id_solicitud}/revocacion", headers=analista,
                         json={"motivo": "Documentación adulterada"})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"idSolicitud": id_solicitud, "estadoSolicitud": "RECHAZADA"}
    aprobaciones = api.get(f"{BASE}/aprobaciones", params={"idSolicitud": id_solicitud}, headers=analista).json()
    assert aprobaciones == []
    historial = api.get(f"{BASE}/solicitudes/{id_solicitud}", headers=analista).json()["historial"]
    assert historial[-1]["estado"] == "RECHAZADA"
    assert historial[-1]["motivo"] == "Documentación adulterada"


def test_solo_se_revoca_una_aprobada(api, servicio, analista):
    cuerpo, _ = registrar(api, servicio)
    respuesta = api.post(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}/revocacion", headers=analista,
                         json={"motivo": "Sin motivo real"})
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "SOLICITUD_NO_ADMITIDA"
    inexistente = api.post(f"{BASE}/solicitudes/{uuid.uuid4()}/revocacion", headers=analista,
                           json={"motivo": "Sin motivo real"})
    assert inexistente.status_code == 404


# ── Analistas y catálogo ────────────────────────────────────────────────────


def test_registrar_analistas(api, autorizacion, admin, analista):
    id_empleado = _empleado(admin)
    primero = api.post(f"{BASE}/analistas", json={"idEmpleado": str(id_empleado)}, headers=autorizacion)
    assert primero.status_code == 201, primero.text
    assert primero.json()["idAnalista"].startswith("AN")
    duplicado = api.post(f"{BASE}/analistas", json={"idEmpleado": str(id_empleado)}, headers=autorizacion)
    assert duplicado.status_code == 409
    assert duplicado.json()["error"]["code"] == "ANALISTA_DUPLICADO"
    otro = api.post(f"{BASE}/analistas", json={"idEmpleado": str(uuid.uuid4())}, headers=autorizacion)
    assert otro.status_code == 422
    assert otro.json()["error"]["code"] == "EMPLEADO_NO_HABILITADO"
    assert api.post(f"{BASE}/analistas", json={"idEmpleado": str(id_empleado)}, headers=analista).status_code == 403


def test_catalogo_de_creditos(api, analista):
    respuesta = api.get("/coredb/catalogos/creditos", headers=analista)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    reglas = {r["idRegla"]: r for r in datos["reglas"]}
    assert reglas["R-A"]["ratioMax"] == "80.00" and reglas["R-B"]["resultado"] == "OBSERVADO"
    assert datos["vigenciaAprobacionDias"] == 30
    assert {"EN_EVALUACION", "APROBADA", "DESEMBOLSADA"} <= {e["codigo"] for e in datos["estadosSolicitud"]}
    assert datos["canalesDesembolso"] == ["VEN", "HB"]
