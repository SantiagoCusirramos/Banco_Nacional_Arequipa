"""CR-INT-03: el resultado llega a SOL con su contrato, al menos una vez y sin duplicarse."""
import json
from datetime import timedelta

from fastapi.testclient import TestClient
from SOL.schemas import EvaluationResult

from EVALUACION.comun import utc_ahora
from EVALUACION.main import crear_app
from EVALUACION.tests.ayudas import (TOKEN_RESULTADOS, aprobada, cabeceras, construir_contexto, nuevo_sobre, recibir,
                                     registrar_situacion)


def _envios(api, **filtros):
    return api.get("/eva/v1/envios", params=filtros, headers=cabeceras("tok-analista")).json()["items"]


def test_entrega_el_resultado_con_el_contrato_de_sol(api, sol):
    sobre = nuevo_sobre()
    acuse = recibir(api, sobre).json()
    registrar_situacion(api, acuse["idEvaluacion"], "5000.00")
    assert api.contexto.despachador.ciclo() == 1
    peticion = sol.recibidos[0]
    cuerpo = json.loads(peticion.content)
    EvaluationResult.model_validate(cuerpo)          # el modelo estricto de SOL: sin campos de más
    assert peticion.url.path == "/sol/integrations/evaluation-results"
    assert peticion.headers["Authorization"] == f"Bearer {TOKEN_RESULTADOS}"
    assert peticion.headers["X-Idempotency-Key"] == cuerpo["idOperacion"]
    assert peticion.headers["X-Correlation-ID"] == cuerpo["idCorrelacion"] == sobre["idCorrelacion"]
    assert (cuerpo["idSolicitud"], cuerpo["versionSolicitud"], cuerpo["idEvaluacion"], cuerpo["ronda"]) == (
        sobre["idSolicitud"], 1, acuse["idEvaluacion"], acuse["ronda"])
    assert cuerpo["decision"] == "APROBADO"
    envio = _envios(api)[0]
    assert envio["estado"] == "ENTREGADO" and envio["intentos"] == 1
    # Ya entregado: otro ciclo no lo reenvía.
    assert api.contexto.despachador.ciclo() == 0 and len(sol.recibidos) == 1


def test_si_sol_no_responde_reintenta_con_espera_creciente(api, sol, monkeypatch):
    aprobada(api)
    sol.respuestas = [0, 503]                          # sin respuesta, luego error del servidor, luego 200
    despachador = api.contexto.despachador
    assert despachador.ciclo() == 0
    envio = _envios(api)[0]
    assert (envio["estado"], envio["intentos"]) == ("PENDIENTE", 1) and envio["ultimoError"].startswith("SIN_RESPUESTA")
    assert despachador.ciclo() == 0 and len(sol.recibidos) == 1     # todavía no toca
    inicio = utc_ahora()
    monkeypatch.setattr("EVALUACION.envios.utc_ahora", lambda: inicio + timedelta(seconds=11))
    assert despachador.ciclo() == 0
    assert _envios(api)[0]["ultimoError"] == "HTTP_503" and len(sol.recibidos) == 2
    monkeypatch.setattr("EVALUACION.envios.utc_ahora", lambda: inicio + timedelta(seconds=40))
    assert despachador.ciclo() == 1
    assert _envios(api)[0]["estado"] == "ENTREGADO" and len(sol.recibidos) == 3
    # El reintento conserva la operación: SOL lo reconoce como el mismo mensaje.
    assert len({p.headers["X-Idempotency-Key"] for p in sol.recibidos}) == 1


def test_un_409_de_sol_se_reintenta(api, sol):
    aprobada(api)
    sol.respuestas = [409]
    assert api.contexto.despachador.ciclo() == 0
    envio = _envios(api)[0]
    assert envio["estado"] == "PENDIENTE" and envio["ultimoError"].startswith("HTTP_409")


def test_una_credencial_rechazada_queda_en_error_hasta_reintentarla(api, sol):
    d = aprobada(api)
    sol.respuestas = [401]
    assert api.contexto.despachador.ciclo() == 0
    envio = _envios(api, estado="ERROR")[0]
    assert envio["ultimoError"] == "HTTP_401"
    assert api.contexto.despachador.ciclo() == 0 and len(sol.recibidos) == 1   # en ERROR no se reintenta solo
    ruta = f"/eva/v1/envios/{envio['idOperacion']}/reintento"
    assert api.post(ruta, headers=cabeceras("tok-auditor")).status_code == 403
    reintento = api.post(ruta, headers=cabeceras("tok-analista"))
    assert reintento.status_code == 200 and reintento.json()["estado"] == "PENDIENTE"
    assert api.contexto.despachador.ciclo() == 1
    otra_vez = api.post(ruta, headers=cabeceras("tok-analista"))
    assert otra_vez.status_code == 409 and otra_vez.json()["error"]["code"] == "ENVIO_NO_EN_ERROR"
    eventos = [h["evento"] for h in api.get(f"/eva/v1/evaluaciones/{d['idEvaluacion']}",
                                            headers=cabeceras("tok-analista")).json()["historial"]]
    assert eventos[-3:] == ["RESULTADO_CON_ERROR", "ENVIO_REINTENTADO", "RESULTADO_ENTREGADO"]


def test_mientras_sol_siga_simulado_los_resultados_esperan(base_de_datos, root, sol):
    contexto = construir_contexto(base_de_datos, sol, sol_url="", sol_token_resultados="")
    with TestClient(crear_app(contexto=contexto)) as api:
        api.contexto = contexto
        aprobada(api)
        assert contexto.despachador.ciclo() == 0 and sol.recibidos == []
        assert _envios(api)[0]["estado"] == "PENDIENTE"
        salud = api.get("/salud").json()
        assert salud["estado"] == "ok" and salud["resultadosASol"].startswith("pendiente")
        respuesta = api.get("/eva/v1/envios", headers=cabeceras("tok-analista")).json()
        assert respuesta["configurado"] is False
