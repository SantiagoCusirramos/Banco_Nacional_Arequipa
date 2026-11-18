"""CR-INT-03 sin estado propio: el resultado final llega a SOL con su contrato, y repetirlo manda el
mismo mensaje (SOL lo reconoce por su idOperacion). Un OBSERVADO no se envía (T1)."""
import json

from fastapi.testclient import TestClient
from SOL.schemas import EvaluationResult

from EVALUACION.envios import id_operacion
from EVALUACION.main import crear_app
from EVALUACION.tests.ayudas import (BUS_TOKEN, TOKEN_RESULTADOS, SolFalso, cabeceras, contexto, decidir, evaluar, nuevo_sobre,
                                     recibir)


def _de(sol, id_solicitud):
    return [json.loads(p.content) for p in sol.recibidos if json.loads(p.content)["idSolicitud"] == id_solicitud]


def test_entrega_el_resultado_con_el_contrato_de_sol(api, sol, analista, cliente):
    sobre = nuevo_sobre(cliente)
    acuse = recibir(api, sobre).json()
    evaluar(api, analista[0], sobre["idSolicitud"], "5000.00")
    assert api.contexto.despachador.ciclo() >= 1
    [cuerpo] = _de(sol, sobre["idSolicitud"])
    EvaluationResult.model_validate(cuerpo)          # el modelo estricto de SOL: sin campos de más
    peticion = next(p for p in sol.recibidos if json.loads(p.content) == cuerpo)
    assert peticion.url.path == "/sol/integrations/evaluation-results"
    assert peticion.headers["Authorization"] == f"Bearer {TOKEN_RESULTADOS}"
    # SOL se alcanza por el Bus: la entrega lleva la credencial de Evaluación ante el Bus.
    assert peticion.headers.get("X-Bus-Token", "") == BUS_TOKEN
    assert peticion.headers["X-Idempotency-Key"] == cuerpo["idOperacion"]
    assert peticion.headers["X-Correlation-ID"] == cuerpo["idCorrelacion"]
    assert (cuerpo["idSolicitud"], cuerpo["versionSolicitud"], cuerpo["idEvaluacion"], cuerpo["ronda"]) == (
        sobre["idSolicitud"], 1, acuse["idEvaluacion"], acuse["ronda"])
    assert cuerpo["decision"] == "APROBADO" and "R-A" in cuerpo["observaciones"]
    assert cuerpo["idOperacion"] == id_operacion(acuse["idEvaluacion"], "APROBADO")
    # Otro ciclo reenvía exactamente el mismo mensaje: SOL lo reconoce sin duplicarlo.
    api.contexto.despachador.ciclo()
    assert _de(sol, sobre["idSolicitud"]) == [cuerpo, cuerpo]


def test_observado_espera_al_analista_y_luego_se_envia_su_decision(api, sol, analista, cliente):
    sobre = nuevo_sobre(cliente)
    acuse = recibir(api, sobre).json()
    evaluar(api, analista[0], sobre["idSolicitud"], "4000.00")
    api.contexto.despachador.ciclo()
    assert _de(sol, sobre["idSolicitud"]) == []
    listado = api.get("/eva/v1/resultados-sol", headers=cabeceras(analista[0])).json()
    assert sobre["idSolicitud"] not in [m["idSolicitud"] for m in listado["items"]]
    decidir(api, analista[0], acuse["idEvaluacion"], "RECHAZADO", "Ingresos sin sustento suficiente.")
    api.contexto.despachador.ciclo()
    [cuerpo] = _de(sol, sobre["idSolicitud"])
    EvaluationResult.model_validate(cuerpo)
    assert (cuerpo["decision"], cuerpo["observaciones"]) == ("RECHAZADO", "Ingresos sin sustento suficiente.")


def test_si_sol_falla_se_reintenta_en_el_siguiente_ciclo(api, sol, analista, cliente):
    sobre = nuevo_sobre(cliente)
    recibir(api, sobre)
    evaluar(api, analista[0], sobre["idSolicitud"], "3000.00")
    sol.respuestas = [0] * 500                    # sin respuesta en todo este ciclo
    api.contexto.despachador.ciclo()
    sol.respuestas = []
    api.contexto.despachador.ciclo()
    enviados = _de(sol, sobre["idSolicitud"])
    assert len(enviados) == 2 and enviados[0] == enviados[1] and enviados[0]["decision"] == "RECHAZADO"


def test_sin_sol_configurado_no_envia(admin, analista, cliente):
    sol = SolFalso()
    ctx = contexto(sol, sol_url="", sol_token_resultados="")
    with TestClient(crear_app(contexto=ctx)) as api:
        sobre = nuevo_sobre(cliente)
        recibir(api, sobre)
        evaluar(api, analista[0], sobre["idSolicitud"], "5000.00")
        assert ctx.despachador.ciclo() == 0 and sol.recibidos == []
        assert api.get("/eva/v1/resultados-sol", headers=cabeceras(analista[0])).json()["configurado"] is False
        assert api.get("/salud").json()["resultadosASol"].startswith("pendiente")
