"""Sin COREDB ni base: configuración, cliente de COREDB, traducciones y salud."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from COBRANZA.comun import ErrorCob
from COBRANZA.config import Config
from COBRANZA.coredb import ClienteCoreDb
from COBRANZA.main import (Contexto, comprobante_legacy, credito_legacy, crear_app, monto_a_pagar_legacy,
                           pago_legacy, perfil_de)
from COBRANZA.scripts import tarea_diaria

SECRETO = "s" * 40
RAIZ = Path(__file__).resolve().parents[1]

DETALLE = {
    "codCredito": "CRE-1", "estado": "EN_MORA", "codCliente": "C001", "idSolicitud": "solicitud-1",
    "idOrden": "orden-1", "codigoOrden": "DES-1", "moneda": "PEN", "montoDesembolsado": "1200.00",
    "fechaDesembolso": "2026-01-05T10:00:00", "numeroCuotas": 3, "cuotasPagadas": 1, "cuotasVencidas": 1,
    "saldoPendiente": "750.00", "proximoVencimiento": "2026-03-05", "moraVigente": "12.50",
    "cuotas": [
        {"numeroCuota": 1, "fechaVencimiento": "2026-02-05", "capital": "400.00", "interes": "4.00",
         "otrosConceptos": "0.00", "cuotaTotal": "404.00", "saldoPendiente": "0.00", "estado": "PAGADA",
         "diasAtraso": 0, "moraVigente": "0.00"},
        {"numeroCuota": 2, "fechaVencimiento": "2026-03-05", "capital": "400.00", "interes": "4.00",
         "otrosConceptos": "0.00", "cuotaTotal": "404.00", "saldoPendiente": "400.00", "estado": "VENCIDA",
         "diasAtraso": 40, "moraVigente": "12.50"},
        {"numeroCuota": 3, "fechaVencimiento": "2026-04-05", "capital": "350.00", "interes": "3.50",
         "otrosConceptos": "0.00", "cuotaTotal": "353.50", "saldoPendiente": "350.00", "estado": "PENDIENTE",
         "diasAtraso": 0, "moraVigente": "0.00"},
    ],
    "eventos": [],
}

PAGO = {
    "idPago": "pago-1", "codCredito": "CRE-1", "referencia": "REF-1", "estado": "CONFIRMADO", "motivo": None,
    "monto": "400.00", "montoAplicado": "400.00", "numCuenta": "CTA-1", "canal": "VEN",
    "uuidTransaccion": "transaccion-1", "fecha": "2026-03-10T09:00:00",
    "aplicaciones": [{"numeroCuota": 2, "montoAplicado": "400.00"}],
    "estadoCredito": "AL_DIA", "saldoPendiente": "350.00",
}


def test_la_configuracion_exige_el_secreto_del_servicio_y_no_tiene_base():
    with pytest.raises(RuntimeError, match="COBRANZA_COREDB_SECRETO"):
        Config(servicio_secreto="corto").validar()
    Config(servicio_secreto=SECRETO).validar()
    assert not any("database" in campo or "cobranza" in campo or "evaluacion" in campo
                   for campo in Config.__dataclass_fields__)


def test_sin_base_propia_ni_llamadas_a_otros_modulos():
    """Cobranza solo habla con COREDB: no queda su base ni el cobro por CUENTAS."""
    for sobrante in ("db.py", "cuentas.py", "seguridad.py", "scripts/preparar_base.py",
                     "scripts/preparar_servicio.py"):
        assert not (RAIZ / sobrante).exists(), sobrante
    codigo = "\n".join(p.read_text(encoding="utf-8") for p in RAIZ.glob("*.py"))
    for otro in ("bna_cobranza", "/api/v1/cuentas/retiro", "X-API-Key", "X-Token-Seguridad", "sqlalchemy"):
        assert otro not in codigo, otro


def test_perfiles_por_rol():
    assert perfil_de("OPERADOR") == "OPERADOR"
    assert perfil_de("ADMINISTRADOR") == "SUPERVISOR"
    assert perfil_de("AUDITOR") == "AUDITOR"
    assert perfil_de("ANALISTA") == "CONSULTA"
    assert perfil_de("ASESOR") == "CONSULTA"


def test_el_credito_se_traduce_a_la_forma_de_la_pantalla():
    credito = credito_legacy(DETALLE)
    assert (credito["codCredito"], credito["idCliente"], credito["estadoCredito"]) == ("CRE-1", "C001", "EN_MORA")
    assert (credito["montoAprobado"], credito["saldoTotalPendiente"]) == ("1200.00", "750.00")
    assert [c["numeroCuota"] for c in credito["cuotas"]] == [1, 2, 3]
    vencida = credito["cuotas"][1]
    assert (vencida["idCuota"], vencida["estadoCuota"]) == ("CRE-1-2", "PENDIENTE")
    assert (vencida["montoCuota"], vencida["saldoPendiente"], vencida["moraPendiente"]) == (
        "404.00", "400.00", "12.50")
    assert vencida["totalAdeudado"] == "412.50"


def test_monto_a_pagar_no_cobra_la_mora():
    monto = monto_a_pagar_legacy(DETALLE)
    assert (monto["numeroCuota"], monto["idCuota"]) == (2, "CRE-1-2")
    assert (monto["saldoCapital"], monto["moraVigente"], monto["totalAPagar"]) == ("400.00", "12.50", "400.00")
    assert monto_a_pagar_legacy({**DETALLE, "cuotas": [DETALLE["cuotas"][0]]}) is None


def test_la_respuesta_de_pago_se_traduce_con_la_cuota_actualizada():
    resultado = pago_legacy(PAGO, DETALLE)
    assert (resultado["referenciaTransaccion"], resultado["estado"], resultado["idempotente"]) == (
        "REF-1", "CONFIRMADO", False)
    assert (resultado["montoPago"], resultado["idCanal"]) == ("400.00", "VEN")
    aplicacion = resultado["aplicacion"]
    assert (aplicacion["numeroCuota"], aplicacion["montoAplicadoCapital"]) == (2, "400.00")
    assert (aplicacion["montoAplicadoMora"], aplicacion["saldoPendienteCuota"]) == ("0.00", "400.00")
    assert aplicacion["estadoCuota"] == "VENCIDA"
    repetido = pago_legacy({**PAGO, "estado": "RECHAZADO", "motivo": "SALDO_INSUFICIENTE", "aplicaciones": []},
                           DETALLE, idempotente=True)
    assert (repetido["estado"], repetido["idempotente"], repetido["aplicacion"]) == ("RECHAZADO", True, None)
    assert repetido["motivo"] == "SALDO_INSUFICIENTE"


def test_la_respuesta_de_pago_trae_el_saldo_y_las_cuotas_del_credito():
    """El comprobante del Home Banking muestra lo que devuelve el servidor, nunca un valor por omisión."""
    resultado = pago_legacy(PAGO, DETALLE)
    assert (resultado["saldoCredito"], resultado["cuotasPendientes"], resultado["cuotasPagadas"]) == (
        "750.00", 2, [2])
    assert (resultado["numCuenta"], resultado["moneda"], resultado["montoAplicado"]) == ("CTA-1", "PEN", "400.00")
    assert resultado["uuidTransaccion"] == "transaccion-1"
    rechazado = pago_legacy({**PAGO, "estado": "RECHAZADO", "motivo": "SALDO_INSUFICIENTE", "aplicaciones": [],
                             "montoAplicado": "0.00", "uuidTransaccion": None}, DETALLE)
    assert (rechazado["cuotasPagadas"], rechazado["uuidTransaccion"], rechazado["montoAplicado"]) == ([], None, "0.00")


def test_el_comprobante_exige_un_pago_confirmado():
    comprobante = comprobante_legacy(PAGO, DETALLE)
    assert (comprobante["numeroOperacion"], comprobante["cuotaNumero"]) == ("REF-1", 2)
    assert (comprobante["montoPagado"], comprobante["montoAplicadoCapital"]) == ("400.00", "400.00")
    assert (comprobante["montoAplicadoMora"], comprobante["saldoRestanteCredito"]) == ("0.00", "750.00")
    with pytest.raises(ErrorCob) as e:
        comprobante_legacy({**PAGO, "estado": "RECHAZADO"}, DETALLE)
    assert (e.value.estado, e.value.codigo) == (409, "PAGO_NO_CONFIRMADO")


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
            return httpx.Response(404, json={"error": {"code": "CREDITO_NO_ENCONTRADO", "message": "No existe."}})
        if ruta == 500:
            return httpx.Response(500, text="falla")
        if ruta == 422:
            return httpx.Response(422, json={"detail": [{"loc": ["body", "x"], "msg": "x"}]})
        return httpx.Response(ruta, json={"ok": True})
    return manejar


def test_el_token_del_servicio_se_recuerda_y_se_renueva_si_coredb_lo_rechaza():
    registro = []
    cliente = ClienteCoreDb("http://coredb", "svc-cobranza", SECRETO,
                            transporte=httpx.MockTransport(_coredb_falso(registro)))
    assert cliente.como_servicio("GET", "/coredb/x") == (200, {"ok": True})
    assert cliente.como_servicio("GET", "/coredb/x") == (200, {"ok": True})
    assert [p.url.path for p in registro].count("/coredb/auth/login") == 1
    assert json.loads(registro[0].content) == {"username": "svc-cobranza", "password": SECRETO}
    registro.clear()
    cliente = ClienteCoreDb("http://coredb", "svc", SECRETO,
                            transporte=httpx.MockTransport(_coredb_falso(registro, ruta=401)))
    with pytest.raises(ErrorCob) as e:
        cliente.como_servicio("GET", "/coredb/x")
    assert e.value.estado == 401
    assert [p.url.path for p in registro] == ["/coredb/auth/login", "/coredb/x", "/coredb/auth/login", "/coredb/x"]


def test_errores_de_coredb():
    def cliente(**kw):
        return ClienteCoreDb("http://coredb", "svc", SECRETO, transporte=httpx.MockTransport(_coredb_falso([], **kw)))
    with pytest.raises(ErrorCob) as e:
        cliente(ruta=404).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo, e.value.mensaje) == (404, "CREDITO_NO_ENCONTRADO", "No existe.")
    with pytest.raises(ErrorCob) as e:
        cliente(ruta=500).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo) == (503, "COREDB_NO_DISPONIBLE")
    with pytest.raises(ErrorCob) as e:
        cliente(ruta=422).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo) == (422, "DATOS_RECHAZADOS_POR_COREDB")
    with pytest.raises(ErrorCob) as e:
        cliente(login=401).token_servicio()
    assert e.value.codigo == "SERVICIO_SIN_SESION" and SECRETO not in e.value.mensaje

    def caido(peticion):
        raise httpx.ConnectError("caído", request=peticion)
    sin_red = ClienteCoreDb("http://coredb", "svc", SECRETO, transporte=httpx.MockTransport(caido))
    with pytest.raises(ErrorCob) as e:
        sin_red.como_persona("tok", "GET", "/coredb/x")
    assert e.value.codigo == "COREDB_NO_DISPONIBLE"


def test_la_tarea_diaria_usa_el_usuario_de_servicio():
    registro = []

    def coredb(peticion):
        registro.append(peticion)
        if peticion.url.path == "/coredb/auth/login":
            return httpx.Response(200, json={"access_token": "tok-servicio", "expires_in": 1800})
        return httpx.Response(200, json={"fecha": "2026-11-17", "cuotasVencidas": 2, "creditosActualizados": 1})

    cliente = ClienteCoreDb("http://coredb", "svc-cobranza", SECRETO, transporte=httpx.MockTransport(coredb))
    resultado = tarea_diaria.ejecutar(cliente)
    assert resultado["cuotasVencidas"] == 2
    llamada = next(p for p in registro if p.url.path == "/coredb/creditos/vencimientos")
    assert llamada.headers["authorization"] == "Bearer tok-servicio"


def test_salud_falla_si_el_servicio_no_inicia_sesion():
    def coredb(peticion):
        if peticion.url.path == "/coredb/salud":
            return httpx.Response(200, json={"estado": "ok"})
        return httpx.Response(401, json={"error": {"code": "CREDENCIALES_INVALIDAS", "message": "x"}})
    ctx = Contexto(Config(servicio_secreto=SECRETO, coredb_url="http://coredb"), transporte_coredb=httpx.MockTransport(coredb))
    with TestClient(crear_app(contexto=ctx)) as api:
        r = api.get("/salud")
        assert r.status_code == 503 and r.json()["error"]["code"] == "SERVICIO_SIN_SESION"


def test_spec_publicada_al_dia():
    publicada = json.loads((RAIZ / "openapi.json").read_text(encoding="utf-8"))
    assert publicada == crear_app().openapi(), "Regenerar con: python -m COBRANZA.scripts.exporta_openapi"
