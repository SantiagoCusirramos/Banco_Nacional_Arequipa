import pytest

pytest.importorskip("COREDB.routers.tarjetas")
pytest.importorskip("COREDB.routers.autorizaciones")

from COREDB.routers.tarjetas import EstadoCambiar, TarjetaEmitir  # noqa: E402
from COREDB.routers.autorizaciones import ConfirmacionRegistrar  # noqa: E402

from TARJETAS.schemas.tarjetas import BloqueoIn, ConfirmacionIn, EmisionIn, EstadoIn  # noqa: E402
from TARJETAS.services import tarjetas as svc  # noqa: E402

ID = "7e570001-0000-4000-8000-000000000001"
AUT = "5a1f0c3e-0000-4000-8000-000000000001"


class Captura:
    def __init__(self):
        self.payload = None

    def emitir_tarjeta(self, payload, cid, authorization=None):
        self.payload = payload
        return {}

    def cambiar_estado(self, id_tarjeta, payload, cid, authorization=None):
        self.payload = payload
        return {}

    def confirmar_autorizacion(self, uuid_autorizacion, payload, cid, authorization=None):
        self.payload = payload
        return {}


def test_emision_cumple_esquema_de_coredb():
    c = Captura()
    svc.emitir(c, EmisionIn(cod_cliente="CLI1", num_cuenta="111"), "550e8400-e29b-41d4-a716-446655440000",
               "corr", "Bearer x")
    TarjetaEmitir(**c.payload)


def test_cambio_de_estado_cumple_esquema_de_coredb():
    c = Captura()
    svc.cambiar_estado(c, ID, EstadoIn(estado="RETENIDA", motivo="m"), "corr", "Bearer x")
    EstadoCambiar(**c.payload)


def test_bloqueo_cumple_esquema_de_coredb():
    c = Captura()
    svc.bloquear(c, ID, BloqueoIn(motivo="Robo reportado"), "corr", "Bearer x")
    EstadoCambiar(**c.payload)


def test_confirmar_autorizacion_cumple_esquema_de_coredb():
    import hashlib
    c = Captura()
    svc.confirmar_autorizacion(c, AUT, ConfirmacionIn(
        llave_idempotencia="550e8400-e29b-41d4-a716-446655440000",
        huella=hashlib.sha256(b"550e8400-e29b-41d4-a716-446655440000").hexdigest(),
        id_terminal="DEV-ATM-01"
    ), "corr", "Bearer x")
    ConfirmacionRegistrar(**c.payload)
