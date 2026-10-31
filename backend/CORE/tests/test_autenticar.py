"""Contrato de autenticar(): estados, errores uniformes y tiempo de respuesta."""

import pytest

from CORE.exceptions import NotFoundError, ValidationError
from CORE.services import usuariossvc
from CORE.tests.test_hashing import CLAVE, FakeDb, usuario_sha256
from CORE.utils import hashing
from CORE.utils.hashing import hash_bcrypt


def usuario_bcrypt(activo=True):
    usuario = usuario_sha256(activo=activo)
    usuario.hash_password = hash_bcrypt(CLAVE)
    usuario.algoritmo_hash = "BCRYPT"
    usuario.version_hash = "v2"
    return usuario


@pytest.fixture
def simulaciones(monkeypatch):
    llamadas = []
    monkeypatch.setattr(hashing, "simular_verificacion", lambda: llamadas.append(1))
    monkeypatch.setattr(usuariossvc, "simular_verificacion", hashing.simular_verificacion)
    return llamadas


def error_de(db, password=CLAVE):
    with pytest.raises((NotFoundError, ValidationError)) as exc:
        usuariossvc.autenticar(db, username="ana", password=password)
    return exc.value


def test_retorna_usuario_con_campos_del_contrato():
    usuario = usuario_bcrypt()
    resultado = usuariossvc.autenticar(FakeDb(usuario), username="ana", password=CLAVE)
    assert resultado is usuario
    assert (resultado.id_usuario, resultado.username, resultado.rol, resultado.activo) == (
        "u-1", "ana", "ASESOR", True,
    )


def test_usuario_inexistente_y_clave_incorrecta_responden_igual():
    inexistente = error_de(FakeDb(None))
    incorrecta = error_de(FakeDb(usuario_bcrypt()), password="otra-clave")
    assert inexistente.code == incorrecta.code == "CREDENCIALES_INVALIDAS"
    assert inexistente.message == incorrecta.message
    assert inexistente.status_code == incorrecta.status_code


def test_usuario_inexistente_gasta_una_verificacion(simulaciones):
    error_de(FakeDb(None))
    assert simulaciones == [1]


def test_usuario_sha256_con_clave_incorrecta_gasta_una_verificacion(simulaciones):
    error_de(FakeDb(usuario_sha256()), password="otra-clave")
    assert simulaciones == [1]


def test_password_demasiado_larga_gasta_una_verificacion(simulaciones):
    error_de(FakeDb(usuario_bcrypt()), password="a" * 73)
    assert simulaciones == [1]


@pytest.mark.parametrize(
    "hash_almacenado", [None, "", "no-es-un-hash", "$2b$12$corto", "ñ" * 60]
)
def test_hash_bcrypt_nulo_o_malformado_gasta_una_verificacion(simulaciones, hash_almacenado):
    usuario = usuario_bcrypt()
    usuario.hash_password = hash_almacenado
    assert error_de(FakeDb(usuario)).code == "CREDENCIALES_INVALIDAS"
    assert simulaciones == [1]


def test_usuario_bcrypt_no_simula(simulaciones):
    error_de(FakeDb(usuario_bcrypt()), password="otra-clave")
    assert simulaciones == []


def test_simular_verificacion_usa_bcrypt_real():
    hashing.simular_verificacion()


def test_inactivo_con_clave_correcta():
    assert error_de(FakeDb(usuario_bcrypt(activo=False))).code == "USUARIO_INACTIVO"


def test_inactivo_con_clave_incorrecta_no_revela_el_estado():
    error = error_de(FakeDb(usuario_bcrypt(activo=False)), password="otra-clave")
    assert error.code == "CREDENCIALES_INVALIDAS"
