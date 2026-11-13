"""Las rutas de clientes, cuentas, movimientos, tarjetas, créditos y catálogos
exigen token y permiso, y toman el actor del token (issue #32).

Usan SQLite en memoria con solo usuario_sistema y auditoria_evento: basta para
el login. Los servicios de negocio se sustituyen donde hace falta ver con qué
actor se los llama.
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from CORE.api import montar_en
from CORE.config import get_settings
from CORE.dependencies import db_session, usuario_actual
from CORE.exceptions import ValidationError
from CORE.models import AuditoriaEvento, UsuarioSistema
from CORE.services import (
    clientessvc,
    creditossvc,
    cuentassvc,
    movimientos,
    rbac,
    tarjetassvc,
    usuariossvc,
)

CLAVE = "k" * 40
PASSWORD = "Clave-Segura-123"

# (método, ruta, acción del catálogo que exige)
RUTAS = [
    ("get", "/core/clientes", "VER_CLIENTE"),
    ("get", "/core/clientes/c-1", "VER_CLIENTE"),
    ("post", "/core/clientes", "CREAR_CLIENTE"),
    ("patch", "/core/clientes/c-1", "MODIFICAR_CLIENTE"),
    ("get", "/core/cuentas/cliente/c-1", "VER_CUENTA"),
    ("get", "/core/cuentas/n-1", "VER_CUENTA"),
    ("post", "/core/cuentas", "CREAR_CUENTA"),
    ("patch", "/core/cuentas/n-1", "MODIFICAR_CUENTA"),
    ("post", "/core/movimientos", "REGISTRAR_MOVIMIENTO"),
    ("post", "/core/movimientos/transferencias", "REGISTRAR_MOVIMIENTO"),
    ("get", "/core/tarjetas", "VER_TARJETA"),
    ("get", "/core/tarjetas/t-1", "VER_TARJETA"),
    ("post", "/core/tarjetas", "CREAR_TARJETA"),
    ("post", "/core/tarjetas/t-1/cambiar-estado", "BLOQUEAR_TARJETA"),
    ("post", "/core/creditos/solicitudes", "CREAR_SOLICITUD_CREDITO"),
    ("get", "/core/creditos/solicitudes/s-1", "VER_CREDITO"),
    ("post", "/core/creditos/solicitudes/s-1/evaluar", "EVALUAR_CREDITO"),
    ("post", "/core/creditos/solicitudes/s-1/decision", "APROBAR_CREDITO"),
    ("get", "/core/creditos/deuda", "CONSULTAR_DEUDA"),
    ("post", "/core/creditos/pagos", "REGISTRAR_PAGO"),
]

# Los catálogos no tienen acción en rbac.json: basta un token vigente.
CATALOGOS = [
    ("get", "/core/catalogos/agencias"),
    ("get", "/core/catalogos/productos-ahorro"),
]


@pytest.fixture(autouse=True)
def _entorno(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", CLAVE)
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def permisos(monkeypatch, tmp_path):
    """Copia de rbac.json que la prueba puede cambiar: fija las acciones de un rol."""
    copia = tmp_path / "rbac.json"
    copia.write_text(rbac.RBAC_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(rbac, "RBAC_FILE", copia)

    def fijar(rol, acciones):
        datos = json.loads(copia.read_text(encoding="utf-8"))
        datos["permisos"][rol] = sorted(acciones)
        copia.write_text(json.dumps(datos), encoding="utf-8")

    return fijar


# Los usuarios no cambian entre pruebas: se crean una vez por módulo (bcrypt es lento).
@pytest.fixture(scope="module")
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    UsuarioSistema.__table__.create(engine)
    AuditoriaEvento.__table__.create(engine)
    sesion = sessionmaker(bind=engine, expire_on_commit=False)()
    usuariossvc.crear_usuario(
        sesion, username="admin.t", nombre="Admin", password=PASSWORD, rol="ADMINISTRADOR"
    )
    usuariossvc.crear_usuario(
        sesion, username="oper.t", nombre="Oper", password=PASSWORD, rol="OPERADOR"
    )
    analista = usuariossvc.crear_usuario(
        sesion, username="anal.t", nombre="Anal", password=PASSWORD, rol="ANALISTA"
    )
    # crear_usuario comprueba el empleado en su tabla, que aquí no existe.
    analista.id_empleado = "emp-analista"
    sesion.commit()
    yield sesion
    sesion.close()


@pytest.fixture(scope="module")
def client(db):
    app = FastAPI()
    montar_en(app)
    app.dependency_overrides[db_session] = lambda: db
    return TestClient(app, raise_server_exceptions=False)


def _auth(client, username):
    r = client.post("/core/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ------------------------------------------------------------ token y permiso
def _depende_de_usuario_actual(dependant) -> bool:
    return any(
        d.call is usuario_actual or _depende_de_usuario_actual(d)
        for d in dependant.dependencies
    )


def test_toda_ruta_de_core_salvo_el_login_exige_token(client):
    sin_token = sorted(
        (sorted(r.methods), r.path)
        for r in client.app.routes
        if getattr(r, "path", "").startswith("/core/")
        and not _depende_de_usuario_actual(r.dependant)
    )
    assert sin_token == [(["POST"], "/core/auth/login")]


def test_la_lista_cubre_las_22_rutas(client):
    prefijos = ("clientes", "cuentas", "movimientos", "tarjetas", "creditos", "catalogos")
    montadas = [
        r for r in client.app.routes
        if getattr(r, "path", "").startswith(tuple(f"/core/{p}" for p in prefijos))
    ]
    assert len(montadas) == len(RUTAS) + len(CATALOGOS) == 22


@pytest.mark.parametrize("metodo,ruta", [r[:2] for r in RUTAS] + CATALOGOS)
def test_sin_token_responde_401(client, metodo, ruta):
    r = client.request(metodo, ruta, json={})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "TOKEN_REQUERIDO"


@pytest.mark.parametrize("metodo,ruta,accion", RUTAS)
def test_sin_la_accion_responde_403(client, permisos, metodo, ruta, accion):
    permisos("OPERADOR", set(rbac.ACCIONES_CORE) - {accion})
    r = client.request(metodo, ruta, json={}, headers=_auth(client, "oper.t"))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "PERMISO_DENEGADO"
    assert r.json()["error"]["details"] == {"accion": accion}


@pytest.mark.parametrize("metodo,ruta,accion", RUTAS)
def test_con_solo_esa_accion_pasa_el_control(client, permisos, metodo, ruta, accion):
    permisos("OPERADOR", {accion})
    r = client.request(metodo, ruta, json={}, headers=_auth(client, "oper.t"))
    # Sin las tablas de negocio la ruta falla después, pero ya no por acceso.
    assert r.status_code not in (401, 403)


@pytest.mark.parametrize("metodo,ruta", CATALOGOS)
def test_los_catalogos_solo_piden_un_token_vigente(client, permisos, metodo, ruta):
    permisos("OPERADOR", set())
    r = client.request(metodo, ruta, headers=_auth(client, "oper.t"))
    assert r.status_code not in (401, 403)


# ------------------------------------------------------------ actor del token
# (ruta, método, cuerpo válido, módulo del servicio, función que recibe el actor)
ESCRITURAS = [
    ("post", "/core/clientes",
     {"cod_tipo_documento": "DNI", "numero_documento": "12345678", "nombres": "Ana",
      "apellido_paterno": "Paz", "numero_celular": "987654321"},
     clientessvc, "crear_cliente"),
    ("patch", "/core/clientes/c-1", {"nombres": "Ana"}, clientessvc, "modificar_cliente"),
    ("post", "/core/cuentas",
     {"id_cliente": "c-1", "id_producto_ahorro": "p-1", "id_agencia": "a-1"},
     cuentassvc, "abrir_cuenta"),
    ("patch", "/core/cuentas/n-1", {"estado_cuenta": "BLOQUEADA"},
     cuentassvc, "modificar_cuenta"),
    ("post", "/core/movimientos",
     {"tipo_operacion": "DEPOSITO", "num_cuenta": "n-1", "monto": "10.00", "id_canal": "VEN"},
     movimientos, "registrar_movimiento"),
    ("post", "/core/movimientos/transferencias",
     {"num_cuenta_origen": "n-1", "num_cuenta_destino": "n-2", "monto": "10.00",
      "id_canal": "VEN"},
     movimientos, "transferir_cuentas"),
    ("post", "/core/tarjetas", {"id_cliente": "c-1", "num_cuenta": "n-1"},
     tarjetassvc, "emitir_tarjeta"),
    ("post", "/core/tarjetas/t-1/cambiar-estado",
     {"estado_nuevo": "BLOQUEADA", "motivo": "robo"},
     tarjetassvc, "cambiar_estado_tarjeta"),
    ("post", "/core/creditos/solicitudes",
     {"id_cliente": "c-1", "id_producto_credito": "pc-1", "monto_solicitado": "1000.00",
      "plazo_meses": 12, "destino_credito": "Consumo"},
     creditossvc, "crear_solicitud"),
    ("post", "/core/creditos/solicitudes/s-1/evaluar", {}, creditossvc, "evaluar_credito"),
    ("post", "/core/creditos/solicitudes/s-1/decision", {"decision": "APROBAR"},
     creditossvc, "aprobar_credito"),
    ("post", "/core/creditos/pagos",
     {"id_credito": "cr-1", "monto": "50.00", "id_canal_pago": "VEN", "num_operacion": "OP-1"},
     creditossvc, "registrar_pago"),
]


@pytest.fixture()
def espia(monkeypatch):
    """Sustituye una función de servicio: guarda con qué la llamaron y corta ahí."""
    llamadas = []

    def instalar(modulo, nombre):
        def sustituto(*args, **kwargs):
            llamadas.append(kwargs)
            raise ValidationError("CORTE_DE_PRUEBA", "El servicio no se ejecuta en esta prueba.")

        monkeypatch.setattr(modulo, nombre, sustituto)
        return llamadas

    return instalar


@pytest.mark.parametrize("metodo,ruta,cuerpo,modulo,funcion", ESCRITURAS)
def test_el_actor_sale_del_token_y_no_del_cuerpo(client, espia, metodo, ruta, cuerpo, modulo, funcion):
    llamadas = espia(modulo, funcion)
    r = client.request(
        metodo, ruta, json={**cuerpo, "actor": "suplantado"}, headers=_auth(client, "admin.t")
    )
    assert r.json()["error"]["code"] == "CORTE_DE_PRUEBA", r.text
    assert [ll["actor"] for ll in llamadas] == ["admin.t"]


def test_el_analista_de_una_decision_sale_del_token(client, espia):
    llamadas = espia(creditossvc, "aprobar_credito")
    client.post(
        "/core/creditos/solicitudes/s-1/decision",
        json={"decision": "APROBAR", "id_analista": "emp-ajeno"},
        headers=_auth(client, "anal.t"),
    )
    assert [(ll["actor"], ll["id_analista"]) for ll in llamadas] == [("anal.t", "emp-analista")]


def test_una_decision_de_un_usuario_sin_empleado_queda_sin_analista(client, espia):
    llamadas = espia(creditossvc, "aprobar_credito")
    client.post(
        "/core/creditos/solicitudes/s-1/decision",
        json={"decision": "APROBAR", "id_analista": "emp-ajeno"},
        headers=_auth(client, "admin.t"),
    )
    assert [(ll["actor"], ll["id_analista"]) for ll in llamadas] == [("admin.t", None)]
