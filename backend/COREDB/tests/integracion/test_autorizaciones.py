"""Autorizaciones y extornos de tarjeta contra la base (bd-v1.4)."""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app


@pytest.fixture
def cliente(autorizacion):
    return TestClient(app, raise_server_exceptions=False, headers=autorizacion)


@pytest.fixture
def tarjeta_activa(cliente, abrir_cuenta):
    """Una tarjeta ACTIVA sobre una cuenta nueva con 1000 de saldo: (id_tarjeta, num_cuenta)."""

    def _crear(saldo="1000.00"):
        num_cuenta = abrir_cuenta()
        deposito = cliente.post("/coredb/movimientos", json={
            "num_cuenta": num_cuenta, "tipo": "DEPOSITO", "monto": saldo, "glosa": "g", "id_canal": "VEN",
        })
        assert deposito.status_code == 201, deposito.text
        emitida = cliente.post("/coredb/tarjetas", json={
            "pan_token": uuid.uuid4().hex, "bin": "004499", "ultimos4": "1234",
            "fecha_emision": "2026-01-01", "fecha_vencimiento": "2030-01-01",
            "cod_cliente": "C001", "num_cuenta": num_cuenta,
        })
        assert emitida.status_code == 201, emitida.text
        id_tarjeta = emitida.json()["id_tarjeta"]
        activada = cliente.post(f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "ACTIVA"})
        assert activada.status_code == 200, activada.text
        return id_tarjeta, num_cuenta

    return _crear


def autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00", uuid_autorizacion=None, **canal):
    return cliente.post("/coredb/autorizaciones", json={
        "uuid_autorizacion": str(uuid_autorizacion or uuid.uuid4()),
        "id_tarjeta": id_tarjeta,
        "num_cuenta": num_cuenta,
        "tipo_operacion": "RETIRO",
        "monto": monto,
        **(canal or {"id_terminal": "DEV-ATM-01"}),
    })


def disponible(cliente, num_cuenta):
    return Decimal(cliente.get(f"/coredb/cuentas/{num_cuenta}").json()["saldo_disponible"])


def test_un_retiro_en_cajero_se_autoriza_y_retiene_el_saldo(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["estado_autorizacion"], cuerpo["codigo_respuesta"]) == ("AUTORIZADA", "00")
    assert cuerpo["id_terminal"] == "DEV-ATM-01" and cuerpo["id_canal"] is None
    assert disponible(cliente, num_cuenta) == Decimal("900.00")
    assert cliente.get(f"/coredb/autorizaciones/{cuerpo['uuid_autorizacion']}").json() == cuerpo


def test_repetir_el_uuid_no_retiene_dos_veces(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = uuid.uuid4()
    primera = autorizar(cliente, id_tarjeta, num_cuenta, uuid_autorizacion=llave)
    segunda = autorizar(cliente, id_tarjeta, num_cuenta, uuid_autorizacion=llave)
    assert segunda.status_code == 201
    assert segunda.json() == primera.json()
    assert disponible(cliente, num_cuenta) == Decimal("900.00")


def test_el_mismo_uuid_con_otro_monto_409(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = uuid.uuid4()
    autorizar(cliente, id_tarjeta, num_cuenta, uuid_autorizacion=llave)
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta, monto="200.00", uuid_autorizacion=llave)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "BNA-IDEMPOTENCIA"


@pytest.mark.parametrize(
    ("monto", "canal", "codigo"),
    [("5000.00", {"id_canal": "VEN"}, "51"), ("1600.00", {"id_terminal": "DEV-ATM-01"}, "61")],
    ids=["sin_saldo", "sobre_el_tope_del_cajero"],
)
def test_una_regla_que_no_se_cumple_queda_rechazada(cliente, tarjeta_activa, monto, canal, codigo):
    id_tarjeta, num_cuenta = tarjeta_activa(saldo="2000.00")
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta, monto=monto, **canal)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert (cuerpo["estado_autorizacion"], cuerpo["codigo_respuesta"]) == ("RECHAZADA", codigo)
    assert monto.split(".")[0] not in cuerpo["motivo_rechazo"]
    assert disponible(cliente, num_cuenta) == Decimal("2000.00")


def test_una_tarjeta_bloqueada_queda_rechazada_con_62(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    cliente.post(f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "BLOQUEADA"})
    assert autorizar(cliente, id_tarjeta, num_cuenta).json()["codigo_respuesta"] == "62"


def test_una_cuenta_que_la_tarjeta_no_opera_422(cliente, tarjeta_activa, abrir_cuenta):
    id_tarjeta, _ = tarjeta_activa()
    respuesta = autorizar(cliente, id_tarjeta, abrir_cuenta(), id_canal="VEN")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-TARJETA"


def test_canal_y_terminal_a_la_vez_422(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta, id_canal="ATM", id_terminal="DEV-ATM-01")
    assert respuesta.status_code == 422


def test_el_extorno_libera_el_saldo_y_se_puede_repetir(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = autorizar(cliente, id_tarjeta, num_cuenta).json()["uuid_autorizacion"]
    for _ in range(2):
        respuesta = cliente.post(f"/coredb/autorizaciones/{llave}/extorno", json={"motivo": "Sin efectivo"})
        assert respuesta.status_code == 200, respuesta.text
        assert (respuesta.json()["estado_autorizacion"], respuesta.json()["codigo_respuesta"]) == ("EXTORNADA", "EXT")
    assert disponible(cliente, num_cuenta) == Decimal("1000.00")


def test_extornar_lo_que_no_existe_404(cliente, datos_base):
    respuesta = cliente.post(f"/coredb/autorizaciones/{uuid.uuid4()}/extorno", json={"motivo": "x"})
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "BNA-AUTORIZACION"


def test_extornar_una_rechazada_409(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = autorizar(cliente, id_tarjeta, num_cuenta, monto="9999.00").json()["uuid_autorizacion"]
    respuesta = cliente.post(f"/coredb/autorizaciones/{llave}/extorno", json={"motivo": "x"})
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "BNA-EXTORNO"


def test_ver_una_autorizacion_que_no_existe_404(cliente, datos_base):
    assert cliente.get(f"/coredb/autorizaciones/{uuid.uuid4()}").status_code == 404


def test_un_auditor_no_autoriza(sesion_de, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    encabezados, _ = sesion_de("AUDITOR")
    respuesta = autorizar(TestClient(app, headers=encabezados), id_tarjeta, num_cuenta)
    assert respuesta.status_code == 403
