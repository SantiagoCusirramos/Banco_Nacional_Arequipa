"""Reglas que cuida la base, aunque alguien salte la API: triggers y permisos mínimos."""
import pymysql
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from EVALUACION.tests.ayudas import aprobada, cabeceras


def _rechaza(root, sql, mensaje):
    with root.cursor() as cursor, pytest.raises(pymysql.MySQLError) as error:
        cursor.execute(sql)
    assert mensaje in str(error.value)


def test_el_historial_solo_crece(api, root):
    aprobada(api)
    _rechaza(root, "UPDATE eva_historial SET actor = 'otro'", "EVA-HISTORIAL")
    _rechaza(root, "DELETE FROM eva_historial", "EVA-HISTORIAL")


def test_lo_recibido_de_sol_y_el_calendario_no_cambian(api, root):
    aprobada(api)
    _rechaza(root, "UPDATE eva_expediente SET actor_envio = 'otro'", "EVA-EXPEDIENTE")
    _rechaza(root, "UPDATE eva_cuota SET cuota_total = 1 WHERE numero_cuota = 1", "EVA-CALENDARIO")
    _rechaza(root, "DELETE FROM eva_cuota", "EVA-CALENDARIO")
    _rechaza(root, "UPDATE eva_situacion_financiera SET riesgo = 'ALTO'", "EVA-SITUACION")


def test_las_condiciones_aprobadas_no_cambian(api, root):
    aprobada(api)
    _rechaza(root, "UPDATE eva_aprobacion SET monto_aprobado = 99999.00", "EVA-APROBACION")
    _rechaza(root, "UPDATE eva_aprobacion SET vigente_hasta = vigente_hasta + INTERVAL 1 YEAR", "EVA-APROBACION")
    _rechaza(root, "UPDATE eva_aprobacion SET estado = 'REVOCADA'", "aumenta la versión")


def test_los_estados_finales_no_se_reabren(api, root):
    d = aprobada(api)
    with root.cursor() as cursor:
        cursor.execute("UPDATE eva_aprobacion SET estado = 'REVOCADA', version = version + 1")
    _rechaza(root, "UPDATE eva_aprobacion SET estado = 'VIGENTE', version = version + 1", "estados finales")
    _rechaza(root, f"UPDATE eva_evaluacion SET motivo = 'otro' WHERE id_evaluacion = '{d['idEvaluacion']}'",
             "evaluación decidida")


def test_una_evaluacion_no_salta_estados(api, root):
    from EVALUACION.tests.ayudas import nuevo_sobre, recibir
    acuse = recibir(api, nuevo_sobre()).json()
    _rechaza(root, f"UPDATE eva_evaluacion SET estado = 'OBSERVADO' WHERE id_evaluacion = '{acuse['idEvaluacion']}'",
             "transición de estado")
    _rechaza(root, f"UPDATE eva_evaluacion SET monto_solicitado = 1 WHERE id_evaluacion = '{acuse['idEvaluacion']}'",
             "datos recibidos de SOL")


@pytest.mark.parametrize("sql", [
    "DELETE FROM eva_evaluacion",
    "DELETE FROM eva_aprobacion",
    "DELETE FROM eva_envio",
    "UPDATE eva_historial SET actor = 'otro'",
    "UPDATE eva_expediente SET actor_envio = 'otro'",
    "UPDATE eva_cuota SET cuota_total = 1",
])
def test_el_usuario_de_la_aplicacion_tiene_permisos_minimos(api, sql):
    aprobada(api)
    with pytest.raises(DBAPIError) as error, api.contexto.engine.begin() as c:
        c.execute(text(sql))
    assert error.value.orig.args[0] == 1142   # comando denegado al usuario


def test_la_salud_comprueba_la_base(api):
    r = api.get("/salud")
    assert r.status_code == 200 and r.json()["estado"] == "ok"
    assert api.get("/eva/v1/evaluaciones", headers=cabeceras("tok-analista")).status_code == 200
