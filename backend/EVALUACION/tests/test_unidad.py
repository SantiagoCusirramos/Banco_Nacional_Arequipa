"""Sin COREDB ni base: configuración, traducción del sobre de SOL, cliente de COREDB y CR-INT-03."""
import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from SOL.schemas import EvaluationResult

from EVALUACION.comun import ErrorEva
from EVALUACION.config import Config
from EVALUACION.contratos import SobreExpediente, expediente_coredb, validar_expediente
from EVALUACION.coredb import ClienteCoreDb
from EVALUACION.envios import id_operacion, resultado_para_sol
from EVALUACION.main import Contexto, crear_app
from EVALUACION.tests.ayudas import nuevo_sobre

SECRETO = "s" * 40


def test_la_configuracion_exige_el_secreto_del_servicio_y_no_tiene_base():
    with pytest.raises(RuntimeError, match="EVALUACION_COREDB_SECRETO"):
        Config(servicio_secreto="corto").validar()
    Config(servicio_secreto=SECRETO).validar()
    assert not any("database" in campo for campo in Config.__dataclass_fields__)
    with pytest.raises(RuntimeError, match="distintos"):
        Config(servicio_secreto=SECRETO, token_sol="t" * 32, sol_token_resultados="t" * 32).validar()


def test_el_sobre_de_sol_se_traduce_al_expediente_de_coredb():
    sobre = nuevo_sobre("C001")
    cuerpo = expediente_coredb(SobreExpediente.model_validate(sobre))
    exp = sobre["expediente"]
    assert cuerpo["idSolicitud"] == sobre["idSolicitud"] and cuerpo["codCliente"] == "C001"
    assert (cuerpo["montoSolicitado"], cuerpo["moneda"], cuerpo["plazoMeses"]) == ("15000.00", "PEN", 12)
    assert cuerpo["condicionPagoDoble"] is False and cuerpo["destino"] == exp["condiciones"]["destino_credito"]
    assert cuerpo["calendario"]["metodo"] == "FRANCES"
    assert cuerpo["calendario"]["tasa"] == format(float(exp["politica"]["tea"]), ".4f")
    assert len(cuerpo["calendario"]["cuotas"]) == 12
    primera, de_sol = cuerpo["calendario"]["cuotas"][0], exp["calendario"]["cuotas"][0]
    assert primera == {"numeroCuota": 1, "fechaVencimiento": de_sol["fecha_vencimiento"],
                       "saldoInicial": de_sol["saldo_inicial"], "amortizacion": de_sol["amortizacion"],
                       "interes": de_sol["interes"], "cuotaTotal": de_sol["cuota_total"],
                       "saldoFinal": de_sol["saldo_final"]}
    # Los datos personales del cliente no viajan a COREDB: ya los tiene por su cod_cliente.
    assert "Juan" not in json.dumps(cuerpo) and "70000001" not in json.dumps(cuerpo)


def test_validaciones_locales_del_sobre():
    sobre = nuevo_sobre("C001")
    sobre["expediente"]["condiciones"]["id_cliente"] = "C002"
    with pytest.raises(ErrorEva) as e:
        validar_expediente(SobreExpediente.model_validate(sobre))
    assert e.value.codigo == "EXPEDIENTE_INCONSISTENTE"
    with pytest.raises(ErrorEva) as e:
        validar_expediente(SobreExpediente.model_validate(nuevo_sobre("CAP-0001")))
    assert e.value.codigo == "CLIENTE_NO_HABILITADO"
    with pytest.raises(ValueError):
        SobreExpediente.model_validate({**nuevo_sobre("C001"), "idSolicitud": "SOL-1"})


def _coredb_falso(registro, *, login=200, ruta=200):
    def manejar(peticion):
        registro.append(peticion)
        if peticion.url.path == "/coredb/auth/login":
            if login != 200:
                return httpx.Response(login, json={"error": {"code": "CREDENCIALES_INVALIDAS", "message": "x"}})
            return httpx.Response(200, json={"access_token": f"tok-{len(registro)}", "expires_in": 1800})
        if ruta == 401:
            return httpx.Response(401, json={"error": {"code": "TOKEN_EXPIRADO", "message": "x"}})
        if ruta == 404:
            return httpx.Response(404, json={"error": {"code": "SOLICITUD_NO_ENCONTRADA", "message": "No existe."}})
        if ruta == 500:
            return httpx.Response(500, text="falla")
        return httpx.Response(ruta, json={"ok": True})
    return manejar


def test_el_token_del_servicio_se_recuerda_y_se_renueva_si_coredb_lo_rechaza():
    registro = []
    cliente = ClienteCoreDb("http://coredb", "svc-evaluacion", SECRETO,
                            transporte=httpx.MockTransport(_coredb_falso(registro)))
    assert cliente.como_servicio("GET", "/coredb/x") == (200, {"ok": True})
    assert cliente.como_servicio("GET", "/coredb/x") == (200, {"ok": True})
    assert [p.url.path for p in registro].count("/coredb/auth/login") == 1
    assert json.loads(registro[0].content) == {"username": "svc-evaluacion", "password": SECRETO}
    registro.clear()
    cliente = ClienteCoreDb("http://coredb", "svc", SECRETO,
                            transporte=httpx.MockTransport(_coredb_falso(registro, ruta=401)))
    with pytest.raises(ErrorEva) as e:
        cliente.como_servicio("GET", "/coredb/x")
    assert e.value.estado == 401
    assert [p.url.path for p in registro] == ["/coredb/auth/login", "/coredb/x", "/coredb/auth/login", "/coredb/x"]


def test_errores_de_coredb():
    def cliente(**kw):
        return ClienteCoreDb("http://coredb", "svc", SECRETO, transporte=httpx.MockTransport(_coredb_falso([], **kw)))
    with pytest.raises(ErrorEva) as e:
        cliente(ruta=404).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo, e.value.mensaje) == (404, "SOLICITUD_NO_ENCONTRADA", "No existe.")
    with pytest.raises(ErrorEva) as e:
        cliente(ruta=500).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo) == (503, "COREDB_NO_DISPONIBLE")
    with pytest.raises(ErrorEva) as e:
        cliente(login=401).token_servicio()
    assert e.value.codigo == "SERVICIO_SIN_SESION" and SECRETO not in e.value.mensaje

    def caido(peticion):
        raise httpx.ConnectError("caído", request=peticion)
    sin_red = ClienteCoreDb("http://coredb", "svc", SECRETO, transporte=httpx.MockTransport(caido))
    with pytest.raises(ErrorEva) as e:
        sin_red.como_persona("tok", "GET", "/coredb/x")
    assert e.value.codigo == "COREDB_NO_DISPONIBLE"


def test_salud_falla_si_el_servicio_no_inicia_sesion():
    def coredb(peticion):
        if peticion.url.path == "/coredb/salud":
            return httpx.Response(200, json={"estado": "ok"})
        return httpx.Response(401, json={"error": {"code": "CREDENCIALES_INVALIDAS", "message": "x"}})
    ctx = Contexto(Config(servicio_secreto=SECRETO, envio_intervalo_seg=0), transporte_coredb=httpx.MockTransport(coredb))
    with TestClient(crear_app(contexto=ctx)) as api:
        r = api.get("/salud")
        assert r.status_code == 503 and r.json()["error"]["code"] == "SERVICIO_SIN_SESION"


def _detalle(evaluaciones):
    return {"idSolicitud": str(uuid.uuid4()), "versionSolicitud": 2, "evaluaciones": evaluaciones}


def _evaluacion(**cambios):
    datos = {"idEvaluacion": str(uuid.uuid4()), "ronda": 2, "regla": "R-A", "resultadoRegla": "APROBADO",
             "decision": None, "comentario": None, "resultado": "APROBADO", "esUltima": True}
    return {**datos, **cambios}


def test_el_mensaje_cr_int_03_es_determinista_y_cumple_el_contrato_de_sol():
    ev = _evaluacion()
    d = _detalle([_evaluacion(ronda=1, esUltima=False, resultado="RECHAZADO"), ev])
    mensaje = resultado_para_sol(d)
    EvaluationResult.model_validate(mensaje)
    assert mensaje == resultado_para_sol(d)
    assert mensaje["idOperacion"] == id_operacion(ev["idEvaluacion"], "APROBADO") != id_operacion(ev["idEvaluacion"],
                                                                                                    "RECHAZADO")
    assert (mensaje["ronda"], mensaje["versionSolicitud"], mensaje["idEvaluacion"]) == (2, 2, ev["idEvaluacion"])


def test_observado_sin_decision_no_se_envia_t1():
    assert resultado_para_sol(_detalle([_evaluacion(resultadoRegla="OBSERVADO", resultado="OBSERVADO")])) is None
    assert resultado_para_sol(_detalle([])) is None
    decidido = _evaluacion(resultadoRegla="OBSERVADO", decision="RECHAZADO", resultado="RECHAZADO",
                           comentario="Ingresos sin sustento.")
    mensaje = resultado_para_sol(_detalle([decidido]))
    assert (mensaje["decision"], mensaje["observaciones"]) == ("RECHAZADO", "Ingresos sin sustento.")
