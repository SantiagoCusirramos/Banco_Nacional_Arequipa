import pytest

pytest.importorskip("COREDB.routers.tarjetas")

from COREDB.routers.tarjetas import EstadoCambiar, TarjetaEmitir  # noqa: E402

from TARJETAS.schemas.tarjetas import BloqueoIn, EmisionIn, EstadoIn  # noqa: E402
from TARJETAS.services import tarjetas as svc  # noqa: E402

ID = "7e570001-0000-4000-8000-000000000001"


class Captura:
    def __init__(self):
        self.payload = None

    def emitir_tarjeta(self, payload, cid, authorization=None):
        self.payload = payload
        return {}

    def cambiar_estado(self, id_tarjeta, payload, cid, authorization=None):
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
