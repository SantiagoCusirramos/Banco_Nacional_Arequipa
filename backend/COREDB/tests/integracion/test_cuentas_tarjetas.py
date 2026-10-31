import os
import uuid
from decimal import Decimal

import pymysql
import pytest
from fastapi.testclient import TestClient

from COREDB.main import app


@pytest.fixture
def cliente():
    return TestClient(app, raise_server_exceptions=False)


def emitir(cliente, cuenta, cod_cliente="C001"):
    return cliente.post(
        "/coredb/tarjetas",
        json={
            "pan_token": uuid.uuid4().hex,
            "bin": "004499",
            "ultimos4": "1234",
            "fecha_emision": "2026-01-01",
            "fecha_vencimiento": "2030-01-01",
            "cod_cliente": cod_cliente,
            "num_cuenta": cuenta,
        },
    )


def abrir(cliente, regimen="INDIVIDUAL", titulares=("C001",), moneda="PEN", sufijo=None):
    sufijo = sufijo or uuid.uuid4().int % 10**16
    return cliente.post(
        "/coredb/cuentas",
        json={
            "num_cuenta": f"CTA-{sufijo:016d}",
            "cci": f"{sufijo:020d}",
            "moneda": moneda,
            "regimen": regimen,
            "id_agencia": "AQP01",
            "titulares": list(titulares),
        },
    )


def test_deposito_en_una_base_nueva_con_datos_de_desarrollo(cliente):
    cuenta = abrir(cliente, titulares=("DEV001",))
    assert cuenta.status_code == 201, cuenta.text
    num_cuenta = cuenta.json()["num_cuenta"]
    deposito = cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": num_cuenta, "tipo": "DEPOSITO", "monto": "100.00", "glosa": "g",
              "id_canal": "VEN"},
    )
    assert deposito.status_code == 201, deposito.text
    assert Decimal(cliente.get(f"/coredb/cuentas/{num_cuenta}").json()["saldo_contable"]) == 100


def test_abrir_y_leer_cuenta(cliente, datos_base):
    creada = abrir(cliente)
    assert creada.status_code == 201
    leida = cliente.get(f"/coredb/cuentas/{creada.json()['num_cuenta']}").json()
    assert leida["estado_cuenta"] == "ACTIVA"
    assert Decimal(leida["saldo_contable"]) == 0


def test_mancomunada_con_un_titular_422(cliente, datos_base):
    respuesta = abrir(cliente, regimen="MANCOMUNADA_CONJUNTA")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-REGIMEN"


def test_regimen_de_la_api_antigua_no_se_acepta(cliente, datos_base):
    assert abrir(cliente, regimen="LIBRE").status_code == 422


def test_titular_inexistente_no_deja_cuenta(cliente, datos_base, consulta):
    sufijo = uuid.uuid4().int % 10**16
    respuesta = abrir(cliente, titulares=("NOEXISTE",), sufijo=sufijo)
    assert respuesta.status_code == 422
    assert not consulta(
        "SELECT 1 FROM cuentas.cuenta_ahorro WHERE num_cuenta=%s", f"CTA-{sufijo:016d}"
    )


def test_cuenta_inexistente_404(cliente, datos_base):
    assert cliente.get("/coredb/cuentas/NO-EXISTE").status_code == 404


def test_emitir_y_cambiar_estado_por_historial(cliente, abrir_cuenta, consulta):
    tarjeta = emitir(cliente, abrir_cuenta())
    assert tarjeta.status_code == 201
    assert tarjeta.json()["estado_tarjeta"] == "PENDIENTE_ACTIVACION"
    assert "pan_token" not in tarjeta.text
    id_tarjeta = tarjeta.json()["id_tarjeta"]
    activa = cliente.post(
        f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "ACTIVA"}
    )
    assert activa.json()["estado_tarjeta"] == "ACTIVA"
    historial = consulta(
        "SELECT estado_nuevo e FROM tarjetas.historial_estado_tarjeta "
        "WHERE id_tarjeta=UUID_TO_BIN(%s) ORDER BY id_historial",
        id_tarjeta,
    )
    assert [h["e"] for h in historial] == ["PENDIENTE_ACTIVACION", "ACTIVA"]


def test_valores_con_equivalente_exacto_se_traducen(cliente, abrir_cuenta):
    id_tarjeta = emitir(cliente, abrir_cuenta()).json()["id_tarjeta"]
    cliente.post(
        f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "ACTIVA"}
    )
    respuesta = cliente.post(
        f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "ANULADA"}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado_tarjeta"] == "CANCELADA"


def test_estado_sin_equivalente_422(cliente, abrir_cuenta):
    id_tarjeta = emitir(cliente, abrir_cuenta()).json()["id_tarjeta"]
    respuesta = cliente.post(
        f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "EMBARGO"}
    )
    assert respuesta.status_code == 422


def test_catalogos_leen(cliente, datos_base, consulta):
    consulta("INSERT IGNORE INTO core.tipo_cambio VALUES ('USD', 'PEN', '2026-01-01', 3.75)")
    monedas = cliente.get("/coredb/catalogos/monedas").json()
    assert {"PEN", "USD"} <= {m["cod_moneda"] for m in monedas}
    assert cliente.get("/coredb/catalogos/agencias").json()[0]["id_agencia"] == "AQP01"
    assert Decimal(cliente.get("/coredb/catalogos/tipos-cambio").json()[0]["tasa"]) == Decimal("3.75")
    assert cliente.get("/coredb/catalogos/productos-ahorro").status_code == 200
    assert cliente.get("/coredb/catalogos/productos-credito").status_code == 200


def test_acentos_llegan_exactos(cliente, abrir_cuenta, consulta):
    """La base corre con los archivos de docker-compose.coredb.yml. Ningún catálogo de la
    API lee las semillas de la extensión: de ella llega el mensaje, y sus datos se leen
    con la cuenta de administración."""
    monedas = cliente.get("/coredb/catalogos/monedas").json()
    assert {m["cod_moneda"]: m["nombre"] for m in monedas}["USD"] == "Dólar estadounidense"
    respuesta = cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": abrir_cuenta(), "tipo": "RETIRO", "monto": "1.00", "glosa": "g",
              "id_canal": "ATM"},
    )
    assert respuesta.json()["error"]["message"] == (
        "BNA-CANAL: un débito por ATM exige una autorización de tarjeta"
    )
    assert consulta(
        "SELECT nombre FROM core.cuenta_contable WHERE codigo_contable = '2101'"
    ) == [{"nombre": "Depósitos de ahorro"}]
    assert consulta("SELECT descripcion FROM tarjetas.bin_tarjeta WHERE bin = '004499'") == [
        {"descripcion": "Débito BNA física"}
    ]


def test_desbloqueo_pendiente_de_un_cliente_de_seguridad(cliente, abrir_cuenta, consulta):
    id_tarjeta = emitir(cliente, abrir_cuenta()).json()["id_tarjeta"]
    url = f"/coredb/tarjetas/{id_tarjeta}/estado"
    cliente.post(url, json={"estado": "ACTIVA"})
    cliente.post(url, json={"estado": "BLOQUEADA"})
    respuesta = cliente.post(url, json={"estado": "ACTIVA"})
    assert respuesta.status_code == 403
    error = respuesta.json()["error"]
    assert error["code"] == "BNA-DESBLOQUEO"
    assert "pendiente de un cliente de Seguridad" in error["message"]
    assert consulta(
        "SELECT estado_tarjeta e FROM tarjetas.tarjeta WHERE id_tarjeta=UUID_TO_BIN(%s)", id_tarjeta
    ) == [{"e": "BLOQUEADA"}]


def test_el_origen_no_viene_del_cliente(cliente, abrir_cuenta, consulta):
    id_tarjeta = emitir(cliente, abrir_cuenta()).json()["id_tarjeta"]
    url = f"/coredb/tarjetas/{id_tarjeta}/estado"
    for origen in ("SEGURIDAD", "SISTEMA", "CLIENTE"):
        assert cliente.post(url, json={"estado": "ACTIVA", "origen": origen}).status_code == 422
    assert cliente.post(url, json={"estado": "ACTIVA"}).status_code == 200
    assert consulta(
        "SELECT origen FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta=UUID_TO_BIN(%s)",
        id_tarjeta,
    )[-1] == {"origen": "OPERADOR"}


@pytest.mark.parametrize("codigo", [1213, 1205])
def test_abrir_cuenta_se_reintenta(cliente, datos_base, fallar_una_vez, codigo):
    from COREDB.routers import cuentas

    intentos = fallar_una_vez(cuentas, codigo)
    assert abrir(cliente).status_code == 201
    assert len(intentos) == 2


@pytest.mark.parametrize("codigo", [1213, 1205])
def test_emitir_tarjeta_se_reintenta(cliente, abrir_cuenta, fallar_una_vez, codigo):
    from COREDB.routers import tarjetas

    cuenta = abrir_cuenta()
    intentos = fallar_una_vez(tarjetas, codigo)
    assert emitir(cliente, cuenta).status_code == 201
    assert len(intentos) == 2


@pytest.mark.parametrize("codigo", [1213, 1205])
def test_cambiar_estado_se_reintenta(cliente, abrir_cuenta, fallar_una_vez, codigo):
    from COREDB.routers import tarjetas

    id_tarjeta = emitir(cliente, abrir_cuenta()).json()["id_tarjeta"]
    intentos = fallar_una_vez(tarjetas, codigo)
    respuesta = cliente.post(f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "ACTIVA"})
    assert respuesta.status_code == 200
    assert len(intentos) == 2


@pytest.mark.parametrize(
    "tabla",
    [
        "tarjetas.tarjeta", "tarjetas.credencial", "tarjetas.matriz_token", "tarjetas.matriz_coordenada",
        "tarjetas.token_pago", "clientes.biometria_cliente", "clientes.codigo_verificacion",
    ],
)
def test_la_api_no_lee_datos_sensibles(tabla):
    conexion = pymysql.connect(
        host=os.environ.get("CORE_DB_HOST", "127.0.0.1"),
        port=int(os.environ["CORE_DB_PORT"]),
        user="bna_app_user",
        password=os.environ["CORE_DB_APP_PASSWORD"],
    )
    with conexion, conexion.cursor() as cursor, pytest.raises(pymysql.err.OperationalError) as error:
        cursor.execute(f"SELECT 1 FROM {tabla} LIMIT 1")
    assert error.value.args[0] == 1142


def test_tarjeta_sobre_cuenta_ajena_422(cliente, abrir_cuenta):
    respuesta = emitir(cliente, abrir_cuenta(), cod_cliente="C002")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-TARJETA"


def test_individual_con_dos_titulares_422(cliente, datos_base):
    respuesta = abrir(cliente, titulares=("C001", "C002"))
    assert respuesta.json()["error"]["code"] == "BNA-REGIMEN"


def test_titular_repetido_422(cliente, datos_base):
    respuesta = abrir(cliente, regimen="MANCOMUNADA_CONJUNTA", titulares=("C001", "C001"))
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-REGIMEN"


def test_titular_que_no_puede_operar_422(cliente, datos_base, consulta):
    consulta("UPDATE clientes.cliente SET estado_cliente='BAJA' WHERE cod_cliente='C002'")
    try:
        respuesta = abrir(cliente, titulares=("C002",))
    finally:
        consulta("UPDATE clientes.cliente SET estado_cliente='ACTIVO' WHERE cod_cliente='C002'")
    assert respuesta.status_code == 422


def desbloquear(id_tarjeta):
    """Como lo haría el módulo de Seguridad, con su propio usuario."""
    conexion = pymysql.connect(
        host=os.environ.get("CORE_DB_HOST", "127.0.0.1"),
        port=int(os.environ["CORE_DB_PORT"]),
        user="bna_seguridad_user",
        password=os.environ["CORE_DB_SEGURIDAD_PASSWORD"],
        autocommit=True,
    )
    with conexion, conexion.cursor() as cursor:
        cursor.execute(
            "CALL tarjetas.desbloquear_tarjeta(UUID_TO_BIN(%s), 'y', 'pruebas', @h)",
            (str(id_tarjeta),),
        )


def test_bloqueo_concurrente_se_aplica_o_falla(cliente, abrir_cuenta, consulta):
    """La sesión 1 fija su instantánea antes de que otra desbloquee la tarjeta."""
    from COREDB.database import get_session_factory
    from COREDB.models import Tarjeta
    from COREDB.routers import tarjetas as modulo

    id_tarjeta = uuid.UUID(emitir(cliente, abrir_cuenta()).json()["id_tarjeta"])

    def cambiar(estado):
        return cliente.post(f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": estado})

    cambiar("ACTIVA")
    cambiar("BLOQUEADA")
    with get_session_factory()() as db:
        assert db.get(Tarjeta, id_tarjeta).estado_tarjeta == "BLOQUEADA"
        desbloquear(id_tarjeta)
        modulo.aplicar_cambio_estado(db, id_tarjeta, "BLOQUEADA", "robo", "CLIENTE", "pruebas")
    fila = consulta(
        "SELECT estado_tarjeta e FROM tarjetas.tarjeta WHERE id_tarjeta=UUID_TO_BIN(%s)", str(id_tarjeta)
    )
    assert fila == [{"e": "BLOQUEADA"}]
    assert consulta(
        "SELECT 1 FROM tarjetas.evento_salida WHERE id_tarjeta=UUID_TO_BIN(%s) "
        "AND carga_json->>'$.motivo'='robo'",
        str(id_tarjeta),
    )
