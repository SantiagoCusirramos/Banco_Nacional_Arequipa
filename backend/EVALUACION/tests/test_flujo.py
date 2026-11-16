"""Expediente → evaluación → decisión contra COREDB y la base integrada reales.

El analista trabaja con su propio token de COREDB, que Evaluación reenvía: la regla la corre
COREDB (umbrales de `creditos.regla_evaluacion`) y el historial registra a la persona.
Con 15000.00 a 12 meses y riesgo BUENO: ingreso 5000.00 aprueba (71.43 %), 4000.00 queda
OBSERVADO (89.29 %) y 3000.00 rechaza (119.05 %).
"""
from EVALUACION.tests.ayudas import (analista_registrado, cabeceras, coredb, decidir, detalle, evaluar, nuevo_sobre,
                                     persona, recibir)


def _recibida(api, cliente):
    sobre = nuevo_sobre(cliente)
    acuse = recibir(api, sobre)
    assert acuse.status_code == 201, acuse.text
    return sobre["idSolicitud"], acuse.json()["idEvaluacion"]


def test_aprobada_por_la_regla(api, analista, cliente):
    token, username = analista
    id_solicitud, id_evaluacion = _recibida(api, cliente)
    r = evaluar(api, token, id_solicitud, "5000.00")
    assert r.status_code == 200, r.text
    resultado = r.json()
    assert (resultado["resultado"], resultado["estadoSolicitud"], resultado["regla"]) == ("APROBADO", "APROBADA", "R-A")
    assert resultado["idEvaluacion"] == id_evaluacion        # el id que SOL recibió en el acuse
    assert (resultado["score"], resultado["limite"], resultado["ratio"]) == (850, "21000.00", "0.7143")
    d = detalle(api, token, id_solicitud)
    assert d["estado"] == "APROBADA" and d["historial"][-1]["actor"] == username
    [evaluacion] = d["evaluaciones"]
    assert (evaluacion["ingresoMensual"], evaluacion["deudaMensual"]) == ("5000.00", "0.00")
    aprobaciones = api.get("/eva/v1/aprobaciones", params={"idSolicitud": id_solicitud}, headers=cabeceras(token))
    assert aprobaciones.status_code == 200
    [aprobacion] = aprobaciones.json()
    assert aprobacion["idEvaluacion"] == id_evaluacion and aprobacion["monto"] == "15000.00"


def test_rechazada_por_la_regla(api, analista, cliente):
    id_solicitud, _ = _recibida(api, cliente)
    r = evaluar(api, analista[0], id_solicitud, "3000.00")
    assert (r.json()["resultado"], r.json()["estadoSolicitud"]) == ("RECHAZADO", "RECHAZADA")
    assert api.get("/eva/v1/aprobaciones", params={"idSolicitud": id_solicitud},
                   headers=cabeceras(analista[0])).json() == []


def test_observada_la_decide_el_analista(api, analista, cliente):
    token, username = analista
    id_solicitud, id_evaluacion = _recibida(api, cliente)
    r = evaluar(api, token, id_solicitud, "4000.00")
    assert (r.json()["resultado"], r.json()["estadoSolicitud"]) == ("OBSERVADO", "EN_EVALUACION")
    decision = decidir(api, token, id_evaluacion, "APROBADO")
    assert decision.status_code == 200, decision.text
    assert decision.json()["estadoSolicitud"] == "APROBADA"
    d = detalle(api, token, id_solicitud)
    [evaluacion] = d["evaluaciones"]
    assert (evaluacion["resultadoRegla"], evaluacion["decision"], evaluacion["resultado"]) == (
        "OBSERVADO", "APROBADO", "APROBADO")
    assert evaluacion["comentario"] == "Sustento revisado con el cliente."
    assert d["historial"][-1]["actor"] == username
    # Una sola vez.
    otra = decidir(api, token, id_evaluacion, "RECHAZADO")
    assert otra.status_code == 422 and otra.json()["error"]["code"] == "EVALUACION_NO_ADMITIDA"


def test_observada_y_rechazada_por_el_analista(api, analista, cliente):
    id_solicitud, id_evaluacion = _recibida(api, cliente)
    evaluar(api, analista[0], id_solicitud, "4000.00")
    r = decidir(api, analista[0], id_evaluacion, "RECHAZADO", "Ingresos sin sustento suficiente.")
    assert r.status_code == 200 and r.json()["estadoSolicitud"] == "RECHAZADA"


def test_el_analista_no_observa_t1(api, analista, cliente):
    """Por omisión del equipo (T1) la decisión es APROBADO o RECHAZADO: no vuelve a SOL."""
    id_solicitud, id_evaluacion = _recibida(api, cliente)
    evaluar(api, analista[0], id_solicitud, "4000.00")
    r = decidir(api, analista[0], id_evaluacion, "OBSERVADO")
    assert r.status_code == 422
    assert detalle(api, analista[0], id_solicitud)["estado"] == "EN_EVALUACION"


def test_decidir_exige_un_analista_registrado(api, admin, cliente):
    token, _ = persona(admin, "ANALISTA")        # sin empleado ni registro como analista
    id_solicitud, id_evaluacion = _recibida(api, cliente)
    assert evaluar(api, token, id_solicitud, "4000.00").status_code == 200
    r = decidir(api, token, id_evaluacion, "APROBADO")
    assert r.status_code == 422 and r.json()["error"]["code"] == "ANALISTA_REQUERIDO"


def test_la_situacion_debe_estar_verificada(api, analista, cliente):
    id_solicitud, _ = _recibida(api, cliente)
    r = evaluar(api, analista[0], id_solicitud, "5000.00", verificada=False)
    assert r.status_code == 422 and r.json()["error"]["code"] == "SITUACION_NO_VERIFICADA"
    assert detalle(api, analista[0], id_solicitud)["evaluaciones"] == []


def test_una_ronda_se_evalua_una_vez(api, analista, cliente):
    id_solicitud, _ = _recibida(api, cliente)
    evaluar(api, analista[0], id_solicitud, "4000.00")
    r = evaluar(api, analista[0], id_solicitud, "5000.00")
    assert r.status_code == 422 and r.json()["error"]["code"] == "EVALUACION_NO_ADMITIDA"


def test_revocar_una_aprobacion(api, analista, cliente):
    token = analista[0]
    id_solicitud, _ = _recibida(api, cliente)
    evaluar(api, token, id_solicitud, "5000.00")
    r = api.post(f"/eva/v1/solicitudes/{id_solicitud}/revocacion", headers=cabeceras(token),
                 json={"motivo": "El cliente desistió del crédito."})
    assert r.status_code == 200, r.text
    assert r.json()["estadoSolicitud"] == "RECHAZADA"
    assert api.get("/eva/v1/aprobaciones", params={"idSolicitud": id_solicitud}, headers=cabeceras(token)).json() == []
    d = detalle(api, token, id_solicitud)
    assert d["historial"][-1]["motivo"] == "El cliente desistió del crédito."


def test_bandeja_catalogo_y_no_encontrada(api, analista, cliente):
    token = analista[0]
    id_solicitud, _ = _recibida(api, cliente)
    bandeja = api.get("/eva/v1/solicitudes", params={"codCliente": cliente}, headers=cabeceras(token))
    assert bandeja.status_code == 200
    assert [s["idSolicitud"] for s in bandeja.json()] == [id_solicitud]
    assert "nombres" not in bandeja.text and "70000001" not in bandeja.text   # sin datos personales
    catalogo = api.get("/eva/v1/catalogo", headers=cabeceras(token)).json()
    assert catalogo["vigenciaAprobacionDias"] == 30
    r = api.get("/eva/v1/solicitudes/00000000-0000-4000-8000-000000000000", headers=cabeceras(token))
    assert r.status_code == 404 and r.json()["error"]["code"] == "SOLICITUD_NO_ENCONTRADA"
    assert api.get("/eva/v1/solicitudes/no-es-un-uuid", headers=cabeceras(token)).status_code == 422


def test_dos_analistas_ven_lo_mismo(api, admin, analista, cliente):
    otro, _ = analista_registrado(admin)
    id_solicitud, _ = _recibida(api, cliente)
    evaluar(api, analista[0], id_solicitud, "5000.00")
    assert detalle(api, otro, id_solicitud)["estado"] == "APROBADA"
    assert coredb("GET", f"/coredb/creditos/solicitudes/{id_solicitud}", admin, 200).json()["estado"] == "APROBADA"
