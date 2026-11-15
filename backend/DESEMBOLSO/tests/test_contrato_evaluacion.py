"""CR-INT-04 de punta a punta con el módulo EVALUACION real (no el simulador).

Evaluación recibe un expediente con el formato exacto de SOL, lo aprueba, y el adaptador de Desembolso lo busca,
lo lee con el calendario de SOL y lo marca DESEMBOLSADA. Así se comprueba que los dos módulos hablan el mismo
contrato. Usa el mismo MySQL de pruebas, con una base propia para Evaluación.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

import httpx
import pymysql
import pytest
from sqlalchemy.engine import make_url

from DESEMBOLSO.config import Config
from DESEMBOLSO.integraciones.http import ClienteHttp, Latencias
from DESEMBOLSO.integraciones.modulos import Evaluacion
from DESEMBOLSO.tests.conftest import MYSQL, _servir
from EVALUACION import esquema as esquema_eva
from EVALUACION.auth import VerificadorCoreDb
from EVALUACION.config import Config as ConfigEva
from EVALUACION.main import Contexto, crear_app as crear_app_eva
from EVALUACION.scripts.enviar_expediente_demo import sobre_de_sol

BASE_EVA = "bna_evaluacion_contrato"
USUARIO_EVA = "evaluacion_contrato"
CLAVE_EVA = secrets.token_hex(16)
TOKEN_SOL = secrets.token_hex(24)
TOKEN_SERVICIO = "token-de-svc-desembolso"
TOKEN_ANALISTA = "token-de-analista"

PERFILES = {
    TOKEN_SERVICIO: {"username": "svc-desembolso", "rol": "SERVICIO", "modulo": "DESEMBOLSO",
                     "acciones": ["REGISTRAR_MOVIMIENTO", "VER_CUENTA"]},
    TOKEN_ANALISTA: {"username": "ana.analista", "rol": "ANALISTA", "modulo": None,
                     "acciones": ["APROBAR_CREDITO", "EVALUAR_CREDITO", "VER_CREDITO"]},
}


def _coredb(peticion: httpx.Request) -> httpx.Response:
    perfil = PERFILES.get(peticion.headers.get("Authorization", "").removeprefix("Bearer "))
    if perfil is None:
        return httpx.Response(401, json={"error": {"code": "TOKEN_INVALIDO", "message": "Token inválido."}})
    return httpx.Response(200, json={"id_usuario": "00000000-0000-4000-8000-000000000001", **perfil})


class SesionFija:
    """El token del usuario de servicio, como lo daría COREDB."""

    def con_token(self, enviar):
        return enviar(TOKEN_SERVICIO)


@pytest.fixture(scope="module")
def evaluacion_real():
    if not MYSQL:
        pytest.skip("Requiere DESEMBOLSO_TEST_MYSQL (scripts/pruebas_integracion.sh).")
    url = make_url(MYSQL)
    conexion = pymysql.connect(host=url.host or "127.0.0.1", port=url.port or 3306, user=url.username or "root",
                               password=url.password or "", autocommit=True, charset="utf8mb4")
    with conexion.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {BASE_EVA}")
        esquema_eva.instalar(cursor, BASE_EVA, USUARIO_EVA, CLAVE_EVA)
    config = ConfigEva(database_url=f"mysql+pymysql://{USUARIO_EVA}:{CLAVE_EVA}@{url.host}:{url.port or 3306}/{BASE_EVA}",
                       coredb_url="http://coredb.prueba", token_sol=TOKEN_SOL, envio_intervalo_seg=0)
    contexto = Contexto(config, verificador=VerificadorCoreDb(config.coredb_url, recordar_seg=0,
                                                              transporte=httpx.MockTransport(_coredb)))
    base_url, servidor = _servir(crear_app_eva(contexto=contexto))
    yield base_url
    servidor.should_exit = True
    with conexion.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {BASE_EVA}")
        cursor.execute(f"DROP USER IF EXISTS '{USUARIO_EVA}'@'%'")
    conexion.close()


def _aprobar_en_evaluacion(base_url: str, documento: str) -> dict:
    sobre = sobre_de_sol(id_cliente="CLI000000101", numero_documento=documento, nombres="Juan", apellido_paterno="Perez",
                         apellido_materno="Quispe", monto="15000.00", plazo_meses=12, simulado=False)
    with httpx.Client(base_url=base_url, timeout=10) as http:
        acuse = http.post("/eva/applications", json=sobre, headers={
            "Authorization": f"Bearer {TOKEN_SOL}", "X-Idempotency-Key": sobre["idOperacion"]}).json()
        analista = {"Authorization": f"Bearer {TOKEN_ANALISTA}"}
        version = http.get(f"/eva/v1/evaluaciones/{acuse['idEvaluacion']}", headers=analista).json()["version"]
        r = http.post(f"/eva/v1/evaluaciones/{acuse['idEvaluacion']}/situacion-financiera", headers=analista,
                      json={"ingresoMensual": "5000.00", "deudaMensual": "0.00", "riesgo": "BUENO",
                            "verificada": True, "version": version})
        assert r.status_code == 200 and r.json()["estado"] == "APROBADO", r.text
    return sobre


def test_desembolso_consume_la_aprobacion_de_evaluacion(evaluacion_real):
    sobre = _aprobar_en_evaluacion(evaluacion_real, "70000101")
    config = Config(_env_file=None, reintentos_consulta=0)
    adaptador = Evaluacion(ClienteHttp("Evaluacion", evaluacion_real, 5, Latencias()), SesionFija(), config)

    encontradas = adaptador.buscar(documento="70000101")
    assert len(encontradas) == 1
    a = adaptador.obtener(encontradas[0].aprobacion_id)
    assert a.habilitada and a.estado == "VIGENTE" and a.version == 1
    assert a.credito_id.startswith("CRE-") and len(a.credito_id) <= 20
    assert a.cliente_id == "CLI000000101" and a.cliente_documento == "70000101"
    assert a.solicitud_id == sobre["idSolicitud"]
    assert (a.importe, a.moneda, a.plazo_meses, a.tasa_tea) == (15000, "PEN", 12, "22.00")
    # El calendario es el de SOL, sin cambios: Desembolso lo enviará así a Cobranza.
    de_sol = sobre["expediente"]["calendario"]["cuotas"]
    assert [(c["numeroCuota"], c["fechaVencimiento"], c["cuotaTotal"]) for c in a.calendario] == \
           [(c["numero_cuota"], c["fecha_vencimiento"], c["cuota_total"]) for c in de_sol]
    assert adaptador.buscar(credito_id=a.credito_id)[0].aprobacion_id == a.aprobacion_id

    aviso = {"idAprobacion": a.aprobacion_id, "version": a.version, "codigoOrden": "DES-2026-000777",
             "fechaDesembolso": datetime.now(timezone.utc).isoformat()}
    acuse = adaptador.registrar_desembolso(aviso)
    assert acuse["confirmacion_id"] == f"{a.aprobacion_id}@v2"
    assert adaptador.registrar_desembolso(aviso) == acuse          # repetirlo no cambia nada
    marcada = adaptador.obtener(a.aprobacion_id)
    assert marcada.estado == "DESEMBOLSADA" and not marcada.habilitada


def test_evaluacion_rechaza_el_aviso_de_otra_orden(evaluacion_real):
    from DESEMBOLSO.core.errores import ErrorNegocio

    _aprobar_en_evaluacion(evaluacion_real, "70000102")
    adaptador = Evaluacion(ClienteHttp("Evaluacion", evaluacion_real, 5, Latencias()), SesionFija(),
                           Config(_env_file=None, reintentos_consulta=0))
    a = adaptador.buscar(documento="70000102")[0]
    ahora = datetime.now(timezone.utc).isoformat()
    adaptador.registrar_desembolso({"idAprobacion": a.aprobacion_id, "version": 1, "codigoOrden": "DES-A",
                                    "fechaDesembolso": ahora})
    with pytest.raises(ErrorNegocio) as error:
        adaptador.registrar_desembolso({"idAprobacion": a.aprobacion_id, "version": 1, "codigoOrden": "DES-B",
                                        "fechaDesembolso": ahora})
    assert error.value.codigo == "APROBACION_YA_DESEMBOLSADA" and error.value.detalle["permanente"] is True
