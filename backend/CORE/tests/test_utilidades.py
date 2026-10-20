from decimal import Decimal

from CORE.utils.hashing import hash_sha256, verify_sha256
from CORE.utils.ids import new_uuid7
from CORE.utils.money import D, convertir


def test_hash_sha256_es_hex_de_64():
    h = hash_sha256("secreto123")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_verify_sha256():
    h = hash_sha256("clave")
    assert verify_sha256("clave", h)
    assert not verify_sha256("otra", h)


def test_uuid7_version():
    u1, u2 = new_uuid7(), new_uuid7()
    assert u1 != u2
    # UUID v7: el nibble de versión (posición 14) es 7
    assert u1[14] == "7"


def test_convertir_aplica_tasa():
    assert convertir(Decimal("100"), Decimal("3.75")) == Decimal("375.00")
    assert convertir(Decimal("10.005"), Decimal("1")) == Decimal("10.01")


def test_d_normaliza():
    assert D("10.5") == Decimal("10.5")
    assert D(Decimal("1")) == Decimal("1")
