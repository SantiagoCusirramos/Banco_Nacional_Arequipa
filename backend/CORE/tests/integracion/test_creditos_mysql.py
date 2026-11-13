"""Ciclo de crédito por HTTP contra un MySQL real con el esquema `bna` (issue #19).

SQLite no aplica los ENUM ni los NOT NULL de `06_solicitud.sql` y
`07_evaluacion.sql`, así que estos casos solo fallan aquí. Escribe en la BD:
solo corre con BNA_INTEGRACION_MYSQL=1 (ver "Pruebas de integración" en
CORE/README.md).
"""

import os
import uuid

import pymysql
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from CORE.api import montar_en
from CORE.config import get_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("BNA_INTEGRACION_MYSQL") != "1",
    reason="Requiere BNA_INTEGRACION_MYSQL=1 y una BD `bna` recién cargada.",
)

CLAVE = "clave-segura-1"
CLIENTE = "0198b000-0000-7009-8000-000000000001"
PRODUCTO = "0198b000-0000-7005-8000-000000000001"
ANALISTA = "0198b000-0000-7002-8000-000000000002"
SOLICITUD = {
    "id_cliente": CLIENTE,
    "id_producto_credito": PRODUCTO,
    "monto_solicitado": "5000.00",
    "moneda": "PEN",
    "plazo_meses": 12,
    "destino_credito": "Capital de trabajo",
}
SITUACION = {"situacion": {"ingresos_mensuales": "8000", "egresos_mensuales": "1000"}}


def sql(q, *a):
    ajustes = get_settings()
    with pymysql.connect(
        host=ajustes.db_host, port=ajustes.db_port, user=ajustes.db_user,
        password=ajustes.db_password, database=ajustes.db_name, autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    ) as c, c.cursor() as cur:
        cur.execute(q, a)
        return list(cur.fetchall())


def cliente_http(id_empleado):
    """Cliente con el token de un ADMINISTRADOR nuevo, con o sin empleado."""
    usuario = "c" + uuid.uuid4().hex[:12]
    sql(
        "insert into usuario_sistema (id_usuario,username,nombre,rol,hash_password,id_empleado,activo)"
        " values (%s,%s,'P','ADMINISTRADOR',SHA2(%s,256),%s,1)",
        str(uuid.uuid4()), usuario, CLAVE, id_empleado,
    )
    app = FastAPI()
    montar_en(app)
    http = TestClient(app, raise_server_exceptions=False)
    r = http.post("/core/auth/login", json={"username": usuario, "password": CLAVE})
    assert r.status_code == 200, r.text
    http.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return http


@pytest.fixture
def con_empleado():
    return cliente_http(ANALISTA)


@pytest.fixture
def sin_empleado():
    return cliente_http(None)


def evaluada(http):
    r = http.post("/core/creditos/solicitudes", json=SOLICITUD)
    assert r.status_code == 201, r.text
    id_solicitud = r.json()["id_solicitud"]
    r = http.post(f"/core/creditos/solicitudes/{id_solicitud}/evaluar", json=SITUACION)
    assert r.status_code == 201, r.text
    return id_solicitud


def decidir(http, id_solicitud, decision):
    return http.post(
        f"/core/creditos/solicitudes/{id_solicitud}/decision", json={"decision": decision}
    )


def estado(id_solicitud):
    return sql("select estado_solicitud e from sol_solicitud where id_solicitud=%s", id_solicitud)[0]["e"]


def decisiones(id_solicitud):
    return sql(
        "select d.decision, d.id_analista from eva_decision_analista d"
        " join eva_evaluacion e on e.id_evaluacion=d.id_evaluacion where e.id_solicitud=%s",
        id_solicitud,
    )


@pytest.mark.parametrize(
    "decision,esperado", [("APROBAR", "APROBADA"), ("RECHAZAR", "RECHAZADA"), ("DERIVAR", "EN_EVALUACION")]
)
def test_decision_admitida_guarda_el_empleado_del_token(con_empleado, decision, esperado):
    id_solicitud = evaluada(con_empleado)
    r = decidir(con_empleado, id_solicitud, decision)
    assert r.status_code == 200, r.text
    assert r.json()["estado_solicitud"] == esperado == estado(id_solicitud)
    assert decisiones(id_solicitud) == [{"decision": decision, "id_analista": ANALISTA}]


def test_observar_no_es_una_decision_del_analista(con_empleado):
    id_solicitud = evaluada(con_empleado)
    r = decidir(con_empleado, id_solicitud, "OBSERVAR")
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "DECISION_INVALIDO"
    assert estado(id_solicitud) == "EN_EVALUACION" and decisiones(id_solicitud) == []


@pytest.mark.parametrize("decision", ["APROBAR", "RECHAZAR", "DERIVAR"])
def test_decision_de_un_usuario_sin_empleado_responde_422(con_empleado, sin_empleado, decision):
    id_solicitud = evaluada(con_empleado)
    r = decidir(sin_empleado, id_solicitud, decision)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "ANALISTA_REQUERIDO"
    assert estado(id_solicitud) == "EN_EVALUACION" and decisiones(id_solicitud) == []


FIADOR = {"numero_documento": "70000002", "nombre_completo": "Rosa Quispe"}
GARANTIA = {"tipo_garantia": "VEHICULAR", "descripcion": "Auto 2020"}


def sin(d, campo):
    return {k: v for k, v in d.items() if k != campo}


@pytest.mark.parametrize("cuerpo,campo", [
    (sin(SOLICITUD, "destino_credito"), ["body", "destino_credito"]),
    ({**SOLICITUD, "destino_credito": None}, ["body", "destino_credito"]),
    ({**SOLICITUD, "fiadores": [sin(FIADOR, "numero_documento")]},
     ["body", "fiadores", 0, "numero_documento"]),
    ({**SOLICITUD, "garantias": [sin(GARANTIA, "descripcion")]},
     ["body", "garantias", 0, "descripcion"]),
], ids=["destino-ausente", "destino-nulo", "fiador-sin-documento", "garantia-sin-descripcion"])
def test_solicitud_sin_campo_obligatorio_responde_422(con_empleado, cuerpo, campo):
    antes = sql("select count(*) n from sol_solicitud")[0]["n"]
    r = con_empleado.post("/core/creditos/solicitudes", json=cuerpo)
    assert r.status_code == 422, r.text
    assert [e["loc"] for e in r.json()["detail"]] == [campo]
    assert sql("select count(*) n from sol_solicitud")[0]["n"] == antes


@pytest.mark.parametrize("monto", [None, "0"], ids=["ausente", "cero"])
def test_montos_de_fiador_y_garantia_toman_el_valor_por_omision_de_la_bd(con_empleado, monto):
    fiador, garantia = dict(FIADOR), dict(GARANTIA)
    if monto is not None:
        fiador["ingreso_mensual"] = garantia["valor_tasacion"] = monto
    r = con_empleado.post(
        "/core/creditos/solicitudes", json={**SOLICITUD, "fiadores": [fiador], "garantias": [garantia]}
    )
    assert r.status_code == 201, r.text
    id_solicitud = r.json()["id_solicitud"]
    assert sql("select ingreso_mensual m from sol_fiador where id_solicitud=%s", id_solicitud)[0]["m"] == 0
    assert sql("select valor_tasacion m from sol_garantia where id_solicitud=%s", id_solicitud)[0]["m"] == 0


def test_evaluar_sin_patrimonio_guarda_cero(con_empleado):
    id_solicitud = evaluada(con_empleado)
    assert sql(
        "select patrimonio p from eva_situacion_financiera where id_solicitud=%s", id_solicitud
    ) == [{"p": 0}]


def test_evaluacion_rechazada_guarda_monto_sugerido_cero(con_empleado):
    r = con_empleado.post("/core/creditos/solicitudes", json=SOLICITUD)
    assert r.status_code == 201, r.text
    id_solicitud = r.json()["id_solicitud"]
    r = con_empleado.post(
        f"/core/creditos/solicitudes/{id_solicitud}/evaluar", json={**SITUACION, "dias_mayor_mora": 200}
    )
    assert r.status_code == 201, r.text
    assert r.json()["resultado"] == "RECHAZADO"
    assert float(r.json()["monto_maximo_sugerido"]) == 0
