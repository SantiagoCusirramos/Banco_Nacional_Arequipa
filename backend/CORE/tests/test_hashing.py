"""Hallazgos #3 y #9: bcrypt con migración desde SHA-256."""

import pytest
from sqlalchemy.exc import OperationalError

from CORE.exceptions import NotFoundError, ValidationError
from CORE.models import AuditoriaEvento, UsuarioSistema
from CORE.services import usuariossvc
from CORE.utils.hashing import (
    bcrypt_admite,
    hash_bcrypt,
    hash_sha256,
    verify_password,
    verify_sha256,
)

CLAVE = "clave-segura"


class FakeQuery:
    def __init__(self, resultado, ya_migrado=False):
        self.resultado = resultado
        self.ya_migrado = ya_migrado

    def filter(self, *_):
        return self

    def first(self):
        return self.resultado

    def update(self, valores, synchronize_session=None):
        if self.ya_migrado:
            return 0
        for columna, valor in valores.items():
            setattr(self.resultado, columna.key, valor)
        return 1


class FakeDb:
    def __init__(self, usuario=None, falla_commit=False, ya_migrado=False):
        self.usuario = usuario
        self.falla_commit = falla_commit
        self.ya_migrado = ya_migrado
        self.agregados = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, *_):
        return FakeQuery(self.usuario, self.ya_migrado)

    def get(self, *_):
        return None

    def add(self, objeto):
        self.agregados.append(objeto)

    def flush(self):
        pass

    def commit(self):
        if self.falla_commit:
            raise OperationalError("UPDATE", {}, Exception("sin conexión"))
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, _):
        pass

    def eventos(self):
        return [o for o in self.agregados if isinstance(o, AuditoriaEvento)]


def usuario_sha256(password=CLAVE, activo=True):
    return UsuarioSistema(
        id_usuario="u-1",
        username="ana",
        nombre="Ana",
        rol="ASESOR",
        hash_password=hash_sha256(password),
        algoritmo_hash="SHA256",
        version_hash="v1",
        activo=activo,
    )


class TestHashing:
    def test_hash_con_sal(self):
        h1, h2 = hash_bcrypt(CLAVE), hash_bcrypt(CLAVE)
        assert h1 != h2
        assert h1.startswith("$2b$")

    def test_verificar_con_hash_nulo_no_debe_explotar(self):
        assert verify_sha256(CLAVE, None) is False
        assert verify_sha256(CLAVE, "") is False
        assert verify_password(CLAVE, None, "BCRYPT") is False
        assert verify_password(CLAVE, None, "SHA256") is False

    def test_despacho_por_algoritmo(self):
        assert verify_password(CLAVE, hash_sha256(CLAVE), "SHA256")
        assert verify_password(CLAVE, hash_bcrypt(CLAVE), "BCRYPT")
        assert not verify_password("otra-clave", hash_sha256(CLAVE), "SHA256")
        assert not verify_password("otra-clave", hash_bcrypt(CLAVE), "BCRYPT")

    def test_algoritmo_desconocido_se_deniega(self):
        assert not verify_password(CLAVE, hash_sha256(CLAVE), "MD5")
        assert not verify_password(CLAVE, hash_sha256(CLAVE), None)

    def test_hash_malformado_se_deniega(self):
        assert not verify_password(CLAVE, "no-es-un-hash", "BCRYPT")

    @pytest.mark.parametrize("algoritmo", ["SHA256", "BCRYPT"])
    def test_hash_corrupto_no_ascii_se_deniega(self, algoritmo):
        assert not verify_password(CLAVE, "ñ" * 64, algoritmo)

    def test_surrogate_aislado_no_explota(self):
        password = "clave\ud800segura"
        assert not bcrypt_admite(password)
        assert not verify_password(password, hash_sha256(CLAVE), "SHA256")
        assert not verify_password(password, hash_bcrypt(CLAVE), "BCRYPT")

    def test_hash_cabe_en_char_64(self):
        assert len(hash_bcrypt(CLAVE)) <= 64

    def test_mas_de_72_bytes_no_se_truncan(self):
        base = "a" * 72
        assert not bcrypt_admite(base + "b")
        assert bcrypt_admite(base)
        assert not verify_password(base + "b", hash_bcrypt(base), "BCRYPT")
        with pytest.raises(ValueError):
            hash_bcrypt(base + "b")

    def test_72_bytes_se_cuentan_en_utf8(self):
        assert not bcrypt_admite("ñ" * 37)

    def test_caracter_nulo_no_se_admite(self):
        assert not bcrypt_admite("clave\x00segura")


class TestCrearUsuario:
    def test_usuario_nuevo_usa_bcrypt(self):
        db = FakeDb()
        usuario = usuariossvc.crear_usuario(
            db, username="ana", nombre="Ana", password=CLAVE, rol="ASESOR"
        )
        assert usuario.algoritmo_hash == "BCRYPT"
        assert usuario.version_hash == "v2"
        assert verify_password(CLAVE, usuario.hash_password, "BCRYPT")

    @pytest.mark.parametrize("password", ["a" * 73, "clave\x00segura", "clave\ud800segura"])
    def test_password_no_admitida_por_bcrypt_se_rechaza(self, password):
        with pytest.raises(ValidationError) as exc:
            usuariossvc.crear_usuario(
                FakeDb(), username="ana", nombre="Ana", password=password, rol="ASESOR"
            )
        assert exc.value.code == "PASSWORD_NO_ADMITIDA"


class TestAutenticar:
    @pytest.mark.parametrize("usuario", [None, usuario_sha256()])
    def test_surrogate_aislado_responde_422(self, usuario):
        with pytest.raises(ValidationError) as exc:
            usuariossvc.autenticar(FakeDb(usuario), username="ana", password="clave\ud800segura")
        assert exc.value.code == "PASSWORD_NO_ADMITIDA"
        assert exc.value.status_code == 422

    def test_hash_sha256_corrupto_es_login_fallido(self):
        usuario = usuario_sha256()
        usuario.hash_password = "ñ" * 64
        with pytest.raises(NotFoundError) as exc:
            usuariossvc.autenticar(FakeDb(usuario), username="ana", password=CLAVE)
        assert exc.value.code == "CREDENCIALES_INVALIDAS"


class TestMigracion:
    def test_sha256_migra_audita_y_confirma(self):
        usuario = usuario_sha256()
        db = FakeDb(usuario)
        resultado = usuariossvc.autenticar(db, username="ana", password=CLAVE)

        assert resultado is usuario
        assert usuario.algoritmo_hash == "BCRYPT"
        assert usuario.version_hash == "v2"
        assert verify_password(CLAVE, usuario.hash_password, "BCRYPT")
        assert db.commits == 1
        evento = db.eventos()[0]
        assert evento.accion == "MIGRAR_HASH_PASSWORD"
        assert usuario.hash_password not in str(evento.detalle)

    def test_fila_ya_migrada_por_otro_login_no_audita(self):
        usuario = usuario_sha256()
        db = FakeDb(usuario, ya_migrado=True)
        assert usuariossvc.autenticar(db, username="ana", password=CLAVE) is usuario
        assert db.eventos() == []

    def test_bcrypt_no_vuelve_a_migrar(self):
        usuario = usuario_sha256()
        usuario.hash_password = hash_bcrypt(CLAVE)
        usuario.algoritmo_hash = "BCRYPT"
        db = FakeDb(usuario)
        usuariossvc.autenticar(db, username="ana", password=CLAVE)
        assert db.commits == 0
        assert db.eventos() == []

    def test_password_incorrecta_no_migra(self):
        usuario = usuario_sha256()
        db = FakeDb(usuario)
        with pytest.raises(NotFoundError):
            usuariossvc.autenticar(db, username="ana", password="otra-clave")
        assert usuario.algoritmo_hash == "SHA256"
        assert db.commits == 0

    def test_usuario_inactivo_no_migra(self):
        usuario = usuario_sha256(activo=False)
        db = FakeDb(usuario)
        with pytest.raises(ValidationError):
            usuariossvc.autenticar(db, username="ana", password=CLAVE)
        assert usuario.algoritmo_hash == "SHA256"
        assert db.commits == 0

    @pytest.mark.parametrize("password", ["a" * 73, "clave\x00segura"])
    def test_password_legada_no_admitida_sigue_en_sha256(self, password):
        usuario = usuario_sha256(password)
        db = FakeDb(usuario)
        assert usuariossvc.autenticar(db, username="ana", password=password) is usuario
        assert usuario.algoritmo_hash == "SHA256"
        assert db.commits == 0

    def test_commit_fallido_igual_autentica(self):
        usuario = usuario_sha256()
        db = FakeDb(usuario, falla_commit=True)
        assert usuariossvc.autenticar(db, username="ana", password=CLAVE) is usuario
        assert db.rollbacks == 1
