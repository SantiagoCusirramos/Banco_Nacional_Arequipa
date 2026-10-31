"""Arranque con y sin configuración válida. No requieren MySQL."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from CORE.config import Settings, get_settings, verificar_configuracion
from CUENTAS.config import Settings as SettingsCuentas

BACKEND = Path(__file__).resolve().parents[2]
EJEMPLO = (BACKEND / ".env.example").read_text(encoding="utf-8")
VALIDA = "x" * 32


def variable_del_ejemplo(nombre):
    linea = next(l for l in EJEMPLO.splitlines() if l.startswith(f"{nombre}="))
    return linea.split("=", 1)[1].split("#")[0].strip()


@pytest.fixture(autouse=True)
def _sin_env_local(monkeypatch, tmp_path):
    """Sale de backend/ para que un .env local no cambie el resultado."""
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_sin_clave_explica_que_hacer(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError) as e:
        verificar_configuracion()
    for texto in ("SECRET_KEY", "backend/.env.example", "secrets.token_urlsafe(48)"):
        assert texto in str(e.value)


@pytest.mark.parametrize("clave", ["", "corta", "y" * 31, "change_me_super_secret_key_32_chars_minimum"])
def test_clave_invalida_explica_que_hacer_sin_repetirla(monkeypatch, clave):
    monkeypatch.setenv("SECRET_KEY", clave)
    with pytest.raises(RuntimeError) as e:
        verificar_configuracion()
    assert "SECRET_KEY" in str(e.value)
    assert not clave or clave not in str(e.value)


def test_clave_valida_pasa(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", VALIDA)
    verificar_configuracion()


def test_el_valor_de_env_example_no_sirve(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", variable_del_ejemplo("SECRET_KEY"))
    with pytest.raises(RuntimeError):
        verificar_configuracion()


def test_la_app_no_arranca_sin_clave(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        with TestClient(main.app):
            pass


def test_la_app_arranca_con_clave(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", VALIDA)
    with TestClient(main.app) as cliente:
        assert cliente.get("/health").status_code == 200


def test_env_example_declara_lo_que_lee_el_codigo():
    leidas = set(Settings.model_fields) | set(SettingsCuentas.model_fields)
    faltan = {n.upper() for n in leidas if f"{n.upper()}=" not in EJEMPLO}
    assert not faltan


def test_env_example_usa_la_base_del_esquema():
    assert variable_del_ejemplo("DB_NAME") == "bna"
