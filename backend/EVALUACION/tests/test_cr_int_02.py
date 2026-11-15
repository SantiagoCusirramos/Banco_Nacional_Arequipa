"""CR-INT-02: Evaluación recibe el expediente tal como lo envía SOL y le devuelve el acuse que SOL valida.

El acuse se valida con `SOL.integrations.validate_receipt` y una prueba usa el propio cliente HTTP de SOL
(`Integrations.deliver`, modo REAL) contra un servidor real, como ocurriría en el producto.
"""
import copy
import uuid
from types import SimpleNamespace

from SOL.integrations import Integrations, evaluation_envelope, validate_receipt
from SOL.settings import Settings

from EVALUACION.main import crear_app
from EVALUACION.tests.ayudas import (TOKEN_RESULTADOS, TOKEN_SOL, cabeceras, construir_contexto, nuevo_sobre, recibir,
                                     registrar_situacion, servidor)


def _consultar(api, id_operacion, token=TOKEN_SOL):
    return api.get(f"/eva/operations/{id_operacion}", headers={"Authorization": f"Bearer {token}"})


def test_acuse_que_sol_acepta(api):
    sobre = nuevo_sobre()
    r = recibir(api, sobre)
    assert r.status_code == 201, r.text
    acuse = r.json()
    assert validate_receipt(acuse, sobre) == acuse
    assert acuse["ronda"] == 1
    assert acuse["idEvaluacion"].startswith("EVA-") and acuse["acuse"] == f"ACK-{acuse['idEvaluacion']}"
    assert r.headers["X-Correlation-ID"] == sobre["idCorrelacion"]


def test_repetir_el_envio_devuelve_el_mismo_acuse(api):
    sobre = nuevo_sobre()
    primero = recibir(api, sobre).json()
    repetido = recibir(api, sobre)
    assert repetido.status_code == 200 and repetido.json() == primero
    consultado = _consultar(api, sobre["idOperacion"])
    assert consultado.status_code == 200 and consultado.json() == primero
    # Un GET 404 significa "no recibido" para SOL.
    assert _consultar(api, str(uuid.uuid4())).status_code == 404
    bandeja = api.get("/eva/v1/evaluaciones", headers=cabeceras("tok-analista")).json()
    assert bandeja["conteos"] == {"PENDIENTE": 1}


def test_la_misma_operacion_con_otro_contenido_se_rechaza(api):
    sobre = nuevo_sobre()
    recibir(api, sobre)
    otro = copy.deepcopy(sobre)
    otro["expediente"]["condiciones"]["destino_credito"] = "Capital de trabajo"
    r = recibir(api, otro)
    assert r.status_code == 409 and r.json()["error"]["code"] == "OPERACION_REUTILIZADA"


def test_otra_operacion_para_la_misma_version_se_rechaza(api):
    sobre = nuevo_sobre()
    recibir(api, sobre)
    r = recibir(api, nuevo_sobre(id_solicitud=sobre["idSolicitud"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_YA_RECIBIDA"


def test_solo_entra_el_token_de_servicio_de_sol(api):
    sobre = nuevo_sobre()
    sin_token = api.post("/eva/applications", json=sobre)
    assert sin_token.status_code == 401
    for token in ("tok-analista", "otro-token-de-al-menos-treinta-y-dos-caracteres"):
        r = recibir(api, sobre, token=token)
        assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALIDO"
    assert _consultar(api, sobre["idOperacion"], token="tok-analista").status_code == 401


def test_la_clave_de_idempotencia_debe_ser_la_operacion(api):
    sobre = nuevo_sobre()
    r = api.post("/eva/applications", json=sobre, headers={
        "Authorization": f"Bearer {TOKEN_SOL}", "X-Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 422 and r.json()["error"]["code"] == "CLAVE_DISTINTA"


def test_un_calendario_que_no_cuadra_se_rechaza(api):
    sobre = nuevo_sobre()
    sobre["expediente"]["calendario"]["cuotas"][0]["amortizacion"] = "1.00"
    r = recibir(api, sobre)
    assert r.status_code == 422 and r.json()["error"]["code"] == "EXPEDIENTE_INCONSISTENTE"
    assert "no suma el monto solicitado" in r.json()["error"]["message"]


def test_un_sobre_incompleto_no_repite_los_datos_recibidos(api):
    sobre = nuevo_sobre()
    del sobre["expediente"]["calendario"]
    r = recibir(api, sobre)
    assert r.status_code == 422
    assert all("input" not in error for error in r.json()["detail"])
    assert "70000001" not in r.text


def test_una_version_nueva_solo_despues_de_observar(api):
    sobre = nuevo_sobre()
    acuse = recibir(api, sobre).json()
    registrar_situacion(api, acuse["idEvaluacion"], "4000.00")          # zona gris: EN_REVISION
    segunda = nuevo_sobre(id_solicitud=sobre["idSolicitud"], version_solicitud=2)
    r = recibir(api, segunda)
    assert r.status_code == 409 and r.json()["error"]["code"] == "EVALUACION_EN_CURSO"
    version = api.get(f"/eva/v1/evaluaciones/{acuse['idEvaluacion']}", headers=cabeceras("tok-analista")).json()["version"]
    observada = api.post(f"/eva/v1/evaluaciones/{acuse['idEvaluacion']}/decision", headers=cabeceras("tok-analista"),
                         json={"decision": "OBSERVADO", "observaciones": "Precisar el destino declarado.",
                               "version": version})
    assert observada.status_code == 200, observada.text
    r = recibir(api, segunda)
    assert r.status_code == 201 and r.json()["ronda"] == 2
    # La versión anterior ya no puede llegar de nuevo como ronda nueva.
    tercera_vieja = nuevo_sobre(id_solicitud=sobre["idSolicitud"], version_solicitud=1)
    assert recibir(api, tercera_vieja).status_code == 409


def test_entrega_con_el_cliente_http_de_sol(base_de_datos, root, sol):
    """SOL en modo REAL: su `Integrations.deliver` consulta, envía y valida el acuse por HTTP."""
    contexto = construir_contexto(base_de_datos, sol)
    with servidor(crear_app(contexto=contexto)) as url:
        ajustes = Settings(database_url="sqlite://", mode="REAL", bus_base_url=url, bus_token=TOKEN_SOL,
                           callback_token=TOKEN_RESULTADOS, cap_search_path="/cap/referencias",
                           cap_reference_path="/cap/referencias/{idCliente}", eva_send_path="/eva/applications",
                           eva_status_path="/eva/operations/{idOperacion}", audit_path="/seguridad/eventos",
                           http_timeout=2.5, request_budget=2.9, worker_seconds=0)
        ajustes.validate()
        cliente_sol = Integrations(ajustes)
        try:
            base = nuevo_sobre()
            sobre = evaluation_envelope(SimpleNamespace(id=base["idSolicitud"]),
                                        SimpleNamespace(number=1, snapshot=base["expediente"]),
                                        str(uuid.uuid4()), str(uuid.uuid4()), "REAL")
            sobre["actorEnvio"] = "asesor.bna"
            acuse = cliente_sol.deliver(sobre)
            assert acuse["idSolicitud"] == base["idSolicitud"] and acuse["ronda"] == 1
            # SOL consulta antes de cada POST: la segunda vez encuentra el acuse y no reenvía.
            assert cliente_sol.deliver(sobre) == acuse
        finally:
            cliente_sol.close()
