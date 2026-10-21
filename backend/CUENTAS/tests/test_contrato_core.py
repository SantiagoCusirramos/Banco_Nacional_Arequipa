import pytest

pytest.importorskip("CORE.schemas.movimientos")

from CORE.schemas.cuentas import CuentaCrear  # noqa: E402
from CORE.schemas.movimientos import MovimientoRegistrar, TransferenciaRegistrar  # noqa: E402

from CUENTAS.schemas.cuentas import AbrirCuentaIn, OperacionIn, TransferenciaIn  # noqa: E402
from CUENTAS.services import cuentas as svc  # noqa: E402


class Captura:
    def __init__(self):
        self.payload = None

    def crear_cuenta(self, payload, cid):
        self.payload = payload

    def registrar_movimiento(self, payload, key, cid):
        self.payload = payload

    def transferir(self, payload, key, cid):
        self.payload = payload


def test_apertura_cumple_esquema_de_core():
    c = Captura()
    datos = AbrirCuentaIn(id_cliente="c1", id_producto_ahorro="p1", id_agencia="a1")
    svc.abrir_cuenta(c, datos, "corr")
    CuentaCrear(**c.payload)


@pytest.mark.parametrize("tipo", ["DEPOSITO", "RETIRO"])
def test_movimiento_cumple_esquema_de_core(tipo):
    c = Captura()
    svc.operar(c, tipo, "111", OperacionIn(monto="10.50", id_canal="ATM"), "k1", "corr")
    MovimientoRegistrar(**c.payload)


def test_transferencia_cumple_esquema_de_core():
    c = Captura()
    datos = TransferenciaIn(monto="10", id_canal="HB", num_cuenta_destino="222")
    svc.transferir(c, "111", datos, "k1", "corr")
    TransferenciaRegistrar(**c.payload)
