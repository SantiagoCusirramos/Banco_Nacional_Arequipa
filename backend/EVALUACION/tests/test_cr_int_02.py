"""CR-INT-02: Evaluación recibe el expediente tal como lo envía SOL, lo registra en COREDB y le
devuelve el acuse que SOL valida.

El acuse se valida con `SOL.integrations.validate_receipt` y una prueba usa el propio cliente HTTP de
SOL (`Integrations.deliver`) contra un servidor real. Todo queda en COREDB: lo que se
comprueba allí se lee con el token del administrador.
"""
import copy
import uuid
from decimal import Decimal
from types import SimpleNamespace

from SOL.integrations import Integrations, validate_receipt

from EVALUACION.main import crear_app
from EVALUACION.tests.ayudas import (TOKEN_RESULTADOS, TOKEN_SOL, cabeceras, contexto, coredb, evaluar, nuevo_sobre,
                                     recibir, servidor)


def test_acuse_que_sol_acepta_y_expediente_en_coredb(api, admin, cliente):
    sobre = nuevo_sobre(cliente)
    r = recibir(api, sobre)
    assert r.status_code == 201, r.text
    acuse = r.json()
    assert validate_receipt(acuse, sobre) == acuse
    assert acuse["ronda"] == 1 and acuse["acuse"] == f"ACK-{acuse['idEvaluacion']}"
    uuid.UUID(acuse["idEvaluacion"])
    assert r.headers["X-Correlation-ID"] == sobre["idCorrelacion"]
    # En COREDB: la solicitud EN_EVALUACION con el calendario de SOL sin cambios (RN-SOL-006).
    detalle = coredb("GET", f"/coredb/creditos/solicitudes/{sobre['idSolicitud']}", admin, 200).json()
    assert detalle["estado"] == "EN_EVALUACION" and detalle["codCliente"] == cliente
    assert detalle["calendario"]["tipo"] == "PRELIMINAR"
    cuotas_sol = sobre["expediente"]["calendario"]["cuotas"]
    assert [(q["numeroCuota"], q["fechaVencimiento"], Decimal(q["cuotaTotal"]))
            for q in detalle["calendario"]["cuotas"]] == [
        (q["numero_cuota"], q["fecha_vencimiento"], Decimal(q["cuota_total"])) for q in cuotas_sol]
    # El historial lo registra el usuario de servicio de Evaluación.
    assert detalle["historial"][-1]["actor"] == "svc-evaluacion"


def test_repetir_el_envio_devuelve_el_mismo_acuse(api, cliente):
    sobre = nuevo_sobre(cliente)
    primero = recibir(api, sobre).json()
    repetido = recibir(api, sobre)
    assert repetido.status_code == 200 and repetido.json() == primero
    # Evaluación no guarda operaciones: la consulta dice "no recibido" y SOL reenvía sin duplicar.
    consultado = api.get(f"/eva/operations/{sobre['idOperacion']}", headers={"Authorization": f"Bearer {TOKEN_SOL}"})
    assert consultado.status_code == 404
    # Otra operación de SOL para la misma versión y el mismo contenido: el mismo acuse, con su operación.
    otra = dict(sobre, idOperacion=str(uuid.uuid4()))
    r = recibir(api, otra)
    assert r.status_code == 200 and r.json()["idEvaluacion"] == primero["idEvaluacion"]
    assert validate_receipt(r.json(), otra)


def test_la_misma_version_con_otro_contenido_se_rechaza(api, cliente):
    sobre = nuevo_sobre(cliente)
    recibir(api, sobre)
    otro = copy.deepcopy(sobre)
    otro["idOperacion"] = str(uuid.uuid4())
    otro["expediente"]["condiciones"]["destino_credito"] = "Capital de trabajo"
    r = recibir(api, otro)
    assert r.status_code == 409 and r.json()["error"]["code"] == "IDEMPOTENCIA_CONFLICTO"


def test_solo_entra_el_token_de_servicio_de_sol(api, admin, cliente):
    sobre = nuevo_sobre(cliente)
    assert api.post("/eva/applications", json=sobre).status_code == 401
    for token in (admin, "otro-token-de-al-menos-treinta-y-dos-caracteres"):
        r = recibir(api, sobre, token=token)
        assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALIDO"
    assert api.get(f"/eva/operations/{sobre['idOperacion']}", headers=cabeceras(admin)).status_code == 401
    assert coredb("GET", f"/coredb/creditos/solicitudes/{sobre['idSolicitud']}", admin).status_code == 404


def test_la_clave_de_idempotencia_debe_ser_la_operacion(api, cliente):
    sobre = nuevo_sobre(cliente)
    r = api.post("/eva/applications", json=sobre, headers={
        "Authorization": f"Bearer {TOKEN_SOL}", "X-Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 422 and r.json()["error"]["code"] == "CLAVE_DISTINTA"


def test_un_calendario_que_no_cuadra_no_llega_a_coredb(api, admin, cliente):
    sobre = nuevo_sobre(cliente)
    sobre["expediente"]["calendario"]["cuotas"][0]["amortizacion"] = "1.00"
    r = recibir(api, sobre)
    assert r.status_code == 422 and r.json()["error"]["code"] == "EXPEDIENTE_INCONSISTENTE"
    assert "no suma el monto solicitado" in r.json()["error"]["message"]
    assert coredb("GET", f"/coredb/creditos/solicitudes/{sobre['idSolicitud']}", admin).status_code == 404


def test_un_calendario_que_la_base_rechaza(api, cliente):
    """La base comprueba cada cuota: aquí la cuota no es amortización + interés."""
    sobre = nuevo_sobre(cliente)
    cuotas = sobre["expediente"]["calendario"]["cuotas"]
    cuotas[0]["interes"] = format(Decimal(cuotas[0]["interes"]) + Decimal("1.00"), ".2f")
    r = recibir(api, sobre)
    assert r.status_code == 422 and r.json()["error"]["code"] == "CALENDARIO_INVALIDO"


def test_un_sobre_incompleto_no_repite_los_datos_recibidos(api, cliente):
    sobre = nuevo_sobre(cliente)
    del sobre["expediente"]["calendario"]
    r = recibir(api, sobre)
    assert r.status_code == 422
    assert all("input" not in error for error in r.json()["detail"])
    assert cliente not in r.text


def test_un_cliente_que_no_es_del_core(api):
    for codigo in ("NOEXISTE1", "CAP-0001"):
        r = recibir(api, nuevo_sobre(codigo))
        assert r.status_code == 422 and r.json()["error"]["code"] == "CLIENTE_NO_HABILITADO", r.text


def test_version_nueva_solo_mientras_la_ronda_no_esta_evaluada(api, analista, cliente):
    sobre = nuevo_sobre(cliente)
    recibir(api, sobre)
    segunda = nuevo_sobre(cliente, id_solicitud=sobre["idSolicitud"], version_solicitud=2)
    r = recibir(api, segunda)
    assert r.status_code == 201 and r.json()["ronda"] == 2
    # Evaluada como OBSERVADO, la solicitud no admite otra versión: el caso es del analista (T1).
    assert evaluar(api, analista[0], sobre["idSolicitud"], "4000.00", version=2).json()["resultado"] == "OBSERVADO"
    tercera = nuevo_sobre(cliente, id_solicitud=sobre["idSolicitud"], version_solicitud=3)
    r = recibir(api, tercera)
    assert r.status_code == 422 and r.json()["error"]["code"] == "SOLICITUD_NO_ADMITIDA"


def test_entrega_con_el_cliente_http_de_sol(admin, sol, cliente):
    """SOL entrega con su `Integrations.deliver` y valida el acuse por HTTP; reenviar es seguro."""
    with servidor(crear_app(contexto=contexto(sol))) as url:
        ajustes = SimpleNamespace(eva_url=url, eva_token=TOKEN_SOL, bus_token="", http_timeout=2.5, max_retries=1)
        cliente_sol = Integrations(ajustes)
        try:
            base = nuevo_sobre(cliente)
            sobre = {"versionContrato": "CR-INT-02-PROPUESTA-v2", "idSolicitud": base["idSolicitud"],
                     "versionSolicitud": 1, "idOperacion": str(uuid.uuid4()), "idCorrelacion": str(uuid.uuid4()),
                     "expediente": base["expediente"], "simulado": False, "actorEnvio": "asesora"}
            acuse = cliente_sol.deliver(sobre)
            assert acuse["idSolicitud"] == base["idSolicitud"] and acuse["ronda"] == 1
            # Reenviar el mismo sobre: COREDB lo reconoce y devuelve el mismo acuse.
            assert cliente_sol.deliver(sobre) == acuse
        finally:
            cliente_sol.close()
    assert coredb("GET", f"/coredb/creditos/solicitudes/{base['idSolicitud']}", admin, 200).json()["ronda"] == 1
