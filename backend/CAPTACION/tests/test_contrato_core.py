"""Lo que CAPTACION envía a COREDB cumple los esquemas reales de COREDB, y lo que lee de
sus respuestas existe en ellas. Solo la imagen de COREDB tiene sus dependencias: en las
demás estas pruebas se omiten (como test_contrato_core.py de CUENTAS y TARJETAS)."""

import pytest

pytest.importorskip("COREDB.routers.clientes")

from COREDB.routers.clientes import (  # noqa: E402
    ClienteRegistrado, ClienteRegistrar, ClienteRespuesta, DocumentoVerificado, DocumentoVerificar,
    ValidacionRegistrar,
)

from CAPTACION.tests.conftest import ASESOR, BASE  # noqa: E402


def _cuerpos(coredb_falso, ruta_fin):
    return [c["json"] for c in coredb_falso.llamadas if c["metodo"] == "POST" and c["ruta"].endswith(ruta_fin)]


def test_lo_que_captacion_envia_cumple_los_esquemas_de_coredb(client, flujo, coredb_falso):
    id_caso = flujo.hasta_aprobado("45679001", materno=None)
    flujo.otp(id_caso, "EMAIL")
    assert client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR).status_code == 200

    (verificar,) = _cuerpos(coredb_falso, "/validaciones/documento")
    DocumentoVerificar(**verificar)
    (alta,) = _cuerpos(coredb_falso, "/coredb/clientes")
    modelo = ClienteRegistrar(**alta)  # strict, extra="forbid": un campo de más o de otro tipo falla
    assert modelo.estado_habilitante == "HABILITADO" and modelo.apellido_materno is None
    validaciones = [c for c in coredb_falso.llamadas if c["ruta"].endswith("/validaciones")
                    and "/documento" not in c["ruta"]]
    assert {ValidacionRegistrar(**c["json"]).tipo_validacion for c in validaciones} == {"CELULAR", "CORREO"}


def test_lo_que_captacion_lee_existe_en_las_respuestas_de_coredb():
    # Campos que lee services/captacion.py de cada respuesta de COREDB.
    assert {"cod_cliente"} <= ClienteRegistrado.model_fields.keys()
    assert {"resultado", "motivo", "cliente"} <= DocumentoVerificado.model_fields.keys()
    assert {"cod_cliente", "estado_cliente", "id_verificacion_captacion", "tipo_documento", "numero_documento",
            "nombres", "apellido_paterno", "apellido_materno"} <= ClienteRespuesta.model_fields.keys()
