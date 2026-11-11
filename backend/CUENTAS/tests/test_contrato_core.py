import pytest

pytest.importorskip("COREDB.routers.movimientos")

from COREDB.routers.cuentas import CuentaAbrir  # noqa: E402
from COREDB.routers.movimientos import MovimientoRegistrar, TransferenciaRegistrar  # noqa: E402

from CUENTAS.schemas.cuentas import AbrirCuentaIn, OperacionIn, TransferenciaIn  # noqa: E402
from CUENTAS.services import cuentas as svc  # noqa: E402

KEY = "550e8400-e29b-41d4-a716-446655440000"


class Captura:
    def __init__(self):
        self.payload = None

    def crear_cuenta(self, payload, cid, authorization=None):
        self.payload = payload
        return {}

    def registrar_movimiento(self, payload, key, cid, authorization=None):
        self.payload = payload
        return {"uuid_transaccion": "u1"}

    def transferir(self, payload, key, cid, authorization=None):
        self.payload = payload
        return {"uuid_debito": "d", "uuid_abono": "a"}


def test_apertura_cumple_esquema_de_coredb():
    c = Captura()
    datos = AbrirCuentaIn(num_cuenta="123", cci="0" * 20, id_cliente="c1", id_agencia="a1")
    svc.abrir_cuenta(c, datos, "corr", "Bearer x")
    CuentaAbrir(**c.payload)


@pytest.mark.parametrize("tipo", ["DEPOSITO", "RETIRO"])
def test_movimiento_cumple_esquema_de_coredb(tipo):
    c = Captura()
    svc.operar(c, tipo, OperacionIn(num_cuenta="111", monto="10.50"), "ATM", KEY, "corr", "Bearer x")
    MovimientoRegistrar(**c.payload)


def test_transferencia_cumple_esquema_de_coredb():
    c = Captura()
    datos = TransferenciaIn(num_cuenta_origen="111", num_cuenta_destino="222", monto="10")
    svc.transferir(c, datos, "HB", KEY, "corr", "Bearer x")
    TransferenciaRegistrar(**c.payload)
