import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pymysql
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from COREDB.database import get_session_factory, llamar
from COREDB.main import app
from COREDB.services import movimientos


@pytest.fixture
def cliente():
    return TestClient(app, raise_server_exceptions=False)


def deposito(cliente, cuenta, monto="100.00", **extra):
    return cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": cuenta, "tipo": "DEPOSITO", "monto": monto, "glosa": "g",
              "id_canal": "VEN", **extra},
    )


def transferencia(cliente, origen, destino, monto="10.00", **extra):
    return cliente.post(
        "/coredb/movimientos/transferencias",
        json={"origen": origen, "destino": destino, "monto": monto, "glosa": "g",
              "id_canal": "VEN", **extra},
    )


def saldo(consulta, cuenta):
    return consulta(
        "SELECT saldo_contable s FROM cuentas.cuenta_ahorro WHERE num_cuenta=%s", cuenta
    )[0]["s"]


def test_deposito_actualiza_saldo_y_audita(cliente, abrir_cuenta, consulta):
    cuenta = abrir_cuenta()
    respuesta = deposito(cliente, cuenta)
    assert respuesta.status_code == 201
    assert saldo(consulta, cuenta) == Decimal("100.00")
    assert consulta(
        "SELECT 1 FROM core.evento_auditoria WHERE accion='DEPOSITO' AND id_entidad=%s",
        respuesta.json()["uuid_transaccion"],
    )


def test_replay_devuelve_la_misma_operacion(cliente, abrir_cuenta, consulta):
    cuenta, llave = abrir_cuenta(), uuid.uuid4().hex
    primero = deposito(cliente, cuenta, idempotency_key=llave).json()
    segundo = deposito(cliente, cuenta, idempotency_key=llave).json()
    assert segundo["uuid_transaccion"] == primero["uuid_transaccion"]
    assert (primero["repetido"], segundo["repetido"]) == (False, True)
    assert saldo(consulta, cuenta) == Decimal("100.00")


def test_llave_con_otros_parametros_409(cliente, abrir_cuenta):
    cuenta, llave = abrir_cuenta(), uuid.uuid4().hex
    deposito(cliente, cuenta, idempotency_key=llave)
    respuesta = deposito(cliente, cuenta, monto="200.00", idempotency_key=llave)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "BNA-IDEMPOTENCIA"


def test_misma_llave_concurrente_aplica_una_vez(cliente, abrir_cuenta, consulta):
    cuenta, llave = abrir_cuenta(), uuid.uuid4().hex
    with ThreadPoolExecutor(8) as hilos:
        respuestas = list(
            hilos.map(lambda _: deposito(cliente, cuenta, idempotency_key=llave), range(8))
        )
    assert {r.status_code for r in respuestas} == {201}
    assert len({r.json()["uuid_transaccion"] for r in respuestas}) == 1
    assert sum(not r.json()["repetido"] for r in respuestas) == 1
    assert saldo(consulta, cuenta) == Decimal("100.00")


def test_saldo_insuficiente_422_sin_rastro(cliente, abrir_cuenta, consulta):
    cuenta, llave = abrir_cuenta(), uuid.uuid4().hex
    respuesta = cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": cuenta, "tipo": "RETIRO", "monto": "1.00", "glosa": "g",
              "id_canal": "VEN", "idempotency_key": llave},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-SALDO"
    assert not consulta("SELECT 1 FROM cuentas.idempotencia_movimiento WHERE llave=%s", llave)


def test_cuenta_inexistente_404(cliente, datos_base):
    assert deposito(cliente, "NO-EXISTE").status_code == 404


def test_monto_con_tres_decimales_422(cliente, abrir_cuenta):
    assert deposito(cliente, abrir_cuenta(), monto="1.001").status_code == 422


def test_transferencia_un_asiento_por_tramo(cliente, abrir_cuenta, consulta):
    origen, destino = abrir_cuenta(), abrir_cuenta()
    deposito(cliente, origen)
    datos = transferencia(cliente, origen, destino, "30.00").json()
    assert saldo(consulta, origen) == Decimal("70.00")
    assert saldo(consulta, destino) == Decimal("30.00")
    asientos = consulta(
        "SELECT DISTINCT id_asiento FROM cuentas.movimiento WHERE uuid_transaccion IN "
        "(UUID_TO_BIN(%s), UUID_TO_BIN(%s))",
        datos["uuid_debito"], datos["uuid_abono"],
    )
    assert len(asientos) == 2


def test_transferencia_entre_monedas_422(cliente, abrir_cuenta):
    respuesta = transferencia(cliente, abrir_cuenta("PEN"), abrir_cuenta("USD"))
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-MONEDA"


def test_transferencias_opuestas_conservan_el_total(cliente, abrir_cuenta, consulta):
    a, b = abrir_cuenta(), abrir_cuenta()
    deposito(cliente, a, "1000.00")
    deposito(cliente, b, "1000.00")
    pares = [(a, b), (b, a)] * 20
    with ThreadPoolExecutor(8) as hilos:
        respuestas = list(hilos.map(lambda p: transferencia(cliente, *p, "7.00"), pares))
    assert {r.status_code for r in respuestas} == {201}
    assert saldo(consulta, a) + saldo(consulta, b) == Decimal("2000.00")
    assert saldo(consulta, a) == Decimal("1000.00")
    descuadre = consulta("SELECT COUNT(*) n FROM core.v_asientos_descuadrados")
    assert descuadre == [{"n": 0}]


def test_retiros_simultaneos_no_sobregiran(cliente, abrir_cuenta, consulta):
    cuenta = abrir_cuenta()
    deposito(cliente, cuenta, "100.00")
    barrera = threading.Barrier(8)

    def retiro(_):
        barrera.wait()
        return cliente.post(
            "/coredb/movimientos",
            json={"num_cuenta": cuenta, "tipo": "RETIRO", "monto": "30.00", "glosa": "g",
                  "id_canal": "VEN"},
        )

    with ThreadPoolExecutor(8) as hilos:
        codigos = sorted(r.status_code for r in hilos.map(retiro, range(8)))
    assert codigos == [201] * 3 + [422] * 5
    assert saldo(consulta, cuenta) == Decimal("10.00")


def test_periodo_cerrado_y_sin_periodo(cliente, abrir_cuenta, consulta, admin):
    cuenta = abrir_cuenta()
    actualizar = "UPDATE core.periodo_contable SET estado=%s"
    try:
        consulta(actualizar, "CERRADO")
        respuesta = deposito(cliente, cuenta)
        assert respuesta.json()["error"]["code"] == "BNA-PERIODO"
    finally:
        consulta(actualizar, "ABIERTO")
    filas = consulta("SELECT * FROM core.periodo_contable")
    consulta("DELETE FROM core.periodo_contable")
    try:
        respuesta = deposito(cliente, cuenta)
        assert respuesta.json()["error"]["code"] == "PERIODO_CONTABLE_NO_ENCONTRADO"
    finally:
        for f in filas:
            consulta(
                "INSERT INTO core.periodo_contable VALUES (%s, %s, %s, %s, %s)",
                f["anio"], f["mes"], f["fecha_inicio"], f["fecha_fin"], f["estado"],
            )


def retiro(cliente, cuenta, monto="1.00", **extra):
    return cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": cuenta, "tipo": "RETIRO", "monto": monto, "glosa": "g", **extra},
    )


def huellas(consulta, llave):
    return consulta("SELECT 1 FROM cuentas.idempotencia_movimiento WHERE llave=%s", llave)


def test_retiro_sin_canal_422(cliente, abrir_cuenta):
    respuesta = retiro(cliente, abrir_cuenta())
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"] == ["body", "id_canal"]


def test_transferencia_sin_canal_422(cliente, abrir_cuenta):
    origen, destino = abrir_cuenta(), abrir_cuenta()
    deposito(cliente, origen)
    respuesta = cliente.post(
        "/coredb/movimientos/transferencias",
        json={"origen": origen, "destino": destino, "monto": "1.00", "glosa": "g"},
    )
    assert respuesta.status_code == 422


def test_tope_diario_del_canal(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    deposito(cliente, cuenta, "20000.00")
    respuesta = retiro(cliente, cuenta, "11000.00", id_canal="HB")
    assert respuesta.json()["error"]["code"] == "RN-TOP-001"


def test_retiro_por_atm_exige_autorizacion(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    deposito(cliente, cuenta)
    respuesta = retiro(cliente, cuenta, id_canal="ATM")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-CANAL"


def test_saldo_que_desborda_422(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    deposito(cliente, cuenta, "9999999999999.99")
    assert deposito(cliente, cuenta, "9999999999999.99").status_code == 422


def test_saldo_insuficiente_no_revela_el_saldo(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    deposito(cliente, cuenta, "123.45")
    respuesta = retiro(cliente, cuenta, "500.00", id_canal="VEN")
    assert respuesta.json()["error"]["code"] == "BNA-SALDO"
    assert "123.45" not in respuesta.text


def test_transferencia_a_cuenta_bloqueada_no_deja_rastro(cliente, abrir_cuenta, consulta):
    origen, destino, llave = abrir_cuenta(), abrir_cuenta(), uuid.uuid4().hex
    deposito(cliente, origen, "1000.00")
    consulta("UPDATE cuentas.cuenta_ahorro SET estado_cuenta='BLOQUEADA' WHERE num_cuenta=%s", destino)
    antes = consulta("SELECT COUNT(*) n FROM core.asiento_contable")
    respuesta = transferencia(cliente, origen, destino, "300.00", idempotency_key=llave)
    assert respuesta.json()["error"]["code"] == "BNA-ESTADO-CUENTA"
    assert saldo(consulta, origen) == Decimal("1000.00")
    assert not huellas(consulta, llave)
    assert consulta("SELECT COUNT(*) n FROM core.asiento_contable") == antes
    assert not consulta(
        "SELECT 1 FROM core.evento_auditoria WHERE accion='TRANSFERENCIA' AND detalle->>'$.origen'=%s",
        origen,
    )
    consulta("UPDATE cuentas.cuenta_ahorro SET estado_cuenta='ACTIVA' WHERE num_cuenta=%s", destino)
    reintento = transferencia(cliente, origen, destino, "300.00", idempotency_key=llave)
    assert reintento.status_code == 201
    assert reintento.json()["repetido"] is False
    assert saldo(consulta, origen) == Decimal("700.00")


def test_transferencia_sin_fondos(cliente, abrir_cuenta, consulta):
    origen, destino = abrir_cuenta(), abrir_cuenta()
    assert transferencia(cliente, origen, destino).json()["error"]["code"] == "BNA-SALDO"
    assert saldo(consulta, destino) == 0


def test_replay_de_transferencia(cliente, abrir_cuenta, consulta):
    origen, destino, llave = abrir_cuenta(), abrir_cuenta(), uuid.uuid4().hex
    deposito(cliente, origen)
    primero = transferencia(cliente, origen, destino, idempotency_key=llave).json()
    segundo = transferencia(cliente, origen, destino, idempotency_key=llave).json()
    assert segundo == {**primero, "repetido": True}
    assert saldo(consulta, origen) == Decimal("90.00")
    otra = transferencia(cliente, origen, destino, "20.00", idempotency_key=llave)
    assert otra.status_code == 409


def test_transferencia_misma_llave_concurrente(cliente, abrir_cuenta, consulta):
    origen, destino, llave = abrir_cuenta(), abrir_cuenta(), uuid.uuid4().hex
    deposito(cliente, origen)
    with ThreadPoolExecutor(8) as hilos:
        respuestas = list(
            hilos.map(lambda _: transferencia(cliente, origen, destino, idempotency_key=llave), range(8))
        )
    assert {r.status_code for r in respuestas} == {201}
    assert sum(not r.json()["repetido"] for r in respuestas) == 1
    assert saldo(consulta, origen) == Decimal("90.00")


def test_llave_de_deposito_no_sirve_para_transferencia(cliente, abrir_cuenta):
    cuenta, otra, llave = abrir_cuenta(), abrir_cuenta(), uuid.uuid4().hex
    deposito(cliente, cuenta, idempotency_key=llave)
    assert transferencia(cliente, cuenta, otra, idempotency_key=llave).status_code == 409


def test_glosa_distinta_con_la_misma_llave_409(cliente, abrir_cuenta):
    cuenta, llave = abrir_cuenta(), uuid.uuid4().hex
    deposito(cliente, cuenta, idempotency_key=llave)
    respuesta = cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": cuenta, "tipo": "DEPOSITO", "monto": "100.00", "glosa": "otra",
              "id_canal": "VEN", "idempotency_key": llave},
    )
    assert respuesta.status_code == 409


def test_replay_sin_periodo_devuelve_la_operacion(cliente, abrir_cuenta, consulta):
    cuenta, llave = abrir_cuenta(), uuid.uuid4().hex
    primero = deposito(cliente, cuenta, idempotency_key=llave).json()
    filas = consulta("SELECT * FROM core.periodo_contable")
    consulta("DELETE FROM core.periodo_contable")
    try:
        segundo = deposito(cliente, cuenta, idempotency_key=llave)
    finally:
        for f in filas:
            consulta(
                "INSERT INTO core.periodo_contable VALUES (%s, %s, %s, %s, %s)",
                f["anio"], f["mes"], f["fecha_inicio"], f["fecha_fin"], f["estado"],
            )
    assert segundo.status_code == 201
    assert segundo.json()["uuid_transaccion"] == primero["uuid_transaccion"]


def _llamar_deposito(cuenta, llave, resultados, barrera):
    with get_session_factory()() as db:
        barrera.wait()
        try:
            llamar(
                db, "cuentas.registrar_movimiento",
                cuenta, "DEPOSITO", Decimal("1.00"), "g", "VEN", uuid.uuid4(), llave, "a" * 64,
                "pruebas",
                salidas=2,
            )
            db.commit()
            resultados.append("ok")
        except DBAPIError as exc:
            resultados.append(exc.orig.args[0])


def test_misma_llave_sin_deadlocks(abrir_cuenta, consulta):
    cuenta, resultados = abrir_cuenta(), []
    for _ in range(5):
        llave, barrera = uuid.uuid4().hex, threading.Barrier(16)
        hilos = [
            threading.Thread(target=_llamar_deposito, args=(cuenta, llave, resultados, barrera))
            for _ in range(16)
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()
    assert resultados == ["ok"] * 80
    assert saldo(consulta, cuenta) == Decimal("5.00")


def test_deadlock_dentro_del_procedimiento_conserva_1213(abrir_cuenta):
    """El manejador no debe ocultar el deadlock, o el reintento dejaría de funcionar."""
    a, b = abrir_cuenta(), abrir_cuenta()
    errores, listo = [], threading.Barrier(2)

    def sesion(primera, segunda):
        with get_session_factory()() as db:
            try:
                for cuenta in (primera, segunda):
                    llamar(
                        db, "cuentas.registrar_movimiento",
                        cuenta, "DEPOSITO", Decimal("1.00"), "g", "VEN", uuid.uuid4(), None, None,
                        "pruebas",
                        salidas=2,
                    )
                    if cuenta == primera:
                        listo.wait()
                db.commit()
            except DBAPIError as exc:
                errores.append(exc.orig.args[0])
                db.rollback()

    hilos = [threading.Thread(target=sesion, args=p) for p in ((a, b), (b, a))]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert errores == [1213]


@pytest.mark.parametrize("codigo", [1213, 1205])
def test_deposito_se_reintenta(cliente, abrir_cuenta, consulta, fallar_una_vez, codigo):
    cuenta = abrir_cuenta()
    intentos = fallar_una_vez(movimientos, codigo)
    assert deposito(cliente, cuenta).status_code == 201
    assert len(intentos) == 2
    assert saldo(consulta, cuenta) == Decimal("100.00")


@pytest.mark.parametrize("codigo", [1213, 1205])
def test_transferencia_se_reintenta(cliente, abrir_cuenta, consulta, fallar_una_vez, codigo):
    origen, destino = abrir_cuenta(), abrir_cuenta()
    deposito(cliente, origen)
    intentos = fallar_una_vez(movimientos, codigo)
    assert transferencia(cliente, origen, destino).status_code == 201
    assert len(intentos) == 2
    assert saldo(consulta, destino) == Decimal("10.00")


def _ciclo_en_el_asiento(llave, peticion, respuestas):
    """W, con más trabajo para no ser la víctima, bloquea la moneda; la API reserva la
    llave y espera esa moneda en el asiento; W pide la misma llave y cierra el ciclo."""
    w = pymysql.connect(
        host=os.environ.get("CORE_DB_HOST", "127.0.0.1"),
        port=int(os.environ["CORE_DB_PORT"]),
        user="bna_admin_user",
        password=os.environ["CORE_DB_ADMIN_PASSWORD"],
    )
    with w, w.cursor() as cursor:
        cursor.execute(
            "INSERT INTO core.tipo_cambio WITH RECURSIVE n (i) AS "
            "(SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 500) "
            "SELECT 'USD', 'PEN', '2000-01-01' + INTERVAL i DAY, 1 FROM n"
        )
        cursor.execute("SELECT cod_moneda FROM core.moneda WHERE cod_moneda = 'PEN' FOR UPDATE")
        hilo = threading.Thread(target=lambda: respuestas.append(peticion()))
        hilo.start()
        time.sleep(1)
        cursor.execute(
            "INSERT INTO cuentas.idempotencia_movimiento (llave, huella) VALUES (%s, %s)",
            (llave, "w" * 64),
        )
        w.rollback()
    hilo.join()


@pytest.fixture
def intentos_reales(monkeypatch):
    intentos = []

    def contar(db, *args, **kwargs):
        intentos.append(args[0])
        return llamar(db, *args, **kwargs)

    monkeypatch.setattr(movimientos, "llamar", contar)
    return intentos


def test_deadlock_en_registrar_asiento_llega_a_la_api_y_se_reintenta(
    cliente, abrir_cuenta, consulta, intentos_reales
):
    cuenta, llave, respuestas = abrir_cuenta(), uuid.uuid4().hex, []
    _ciclo_en_el_asiento(
        llave, lambda: deposito(cliente, cuenta, idempotency_key=llave), respuestas
    )
    assert respuestas[0].status_code == 201, respuestas[0].text
    assert len(intentos_reales) == 2
    assert saldo(consulta, cuenta) == Decimal("100.00")


def test_deadlock_en_una_transferencia_llega_a_la_api_y_se_reintenta(
    cliente, abrir_cuenta, consulta, intentos_reales
):
    """La API siempre llama dentro de una transacción: sin la guarda de 1305 de
    registrar_transferencia, el cliente recibiría 500 en vez de un reintento."""
    origen, destino, llave, respuestas = abrir_cuenta(), abrir_cuenta(), uuid.uuid4().hex, []
    deposito(cliente, origen)
    intentos_reales.clear()
    _ciclo_en_el_asiento(
        llave, lambda: transferencia(cliente, origen, destino, idempotency_key=llave), respuestas
    )
    assert respuestas[0].status_code == 201, respuestas[0].text
    assert len(intentos_reales) == 2
    assert saldo(consulta, origen) == Decimal("90.00")
    assert saldo(consulta, destino) == Decimal("10.00")


@pytest.mark.parametrize("operacion", ["deposito", "transferencia"])
def test_llave_sin_operacion_registrada_409(
    cliente, abrir_cuenta, consulta, monkeypatch, operacion
):
    origen, destino, llave = abrir_cuenta(), abrir_cuenta(), uuid.uuid4().hex
    monkeypatch.setattr(movimientos, "_huella", lambda **_: "a" * 64)
    consulta(
        "INSERT INTO cuentas.idempotencia_movimiento (llave, huella) VALUES (%s, %s)",
        llave, "a" * 64,
    )
    if operacion == "deposito":
        respuesta = deposito(cliente, origen, idempotency_key=llave)
    else:
        respuesta = transferencia(cliente, origen, destino, idempotency_key=llave)
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["error"]["code"] == "BNA-IDEMPOTENCIA"


@pytest.mark.parametrize(
    "canal,moneda,esperado",
    [("VEN", "PEN", 201), ("AGE", "PEN", 422), ("HB", "USD", 422), ("AGE", "USD", 422),
     ("VEN", "USD", 201), ("BD", "USD", 422)],
)
def test_retiro_por_canal_y_moneda(cliente, abrir_cuenta, canal, moneda, esperado):
    cuenta = abrir_cuenta(moneda)
    deposito(cliente, cuenta, monto="20000.00")
    respuesta = retiro(cliente, cuenta, "2000.00" if moneda == "PEN" else "1000.00", id_canal=canal)
    assert respuesta.status_code == esperado, respuesta.text
    if esperado == 422:
        codigo = "RN-BD-002" if canal == "BD" else "BNA-CANAL"
        assert respuesta.json()["error"]["code"] == codigo


@pytest.mark.parametrize("canal,esperado", [("VEN", 201), ("AGE", 422)])
def test_transferencia_grande_por_canal(cliente, abrir_cuenta, canal, esperado):
    origen, destino = abrir_cuenta(), abrir_cuenta()
    deposito(cliente, origen, monto="20000.00")
    respuesta = transferencia(cliente, origen, destino, monto="15000.00", id_canal=canal)
    assert respuesta.status_code == esperado, respuesta.text


def test_canal_inactivo_422(cliente, abrir_cuenta, admin):
    cuenta = abrir_cuenta()
    with admin.cursor() as cursor:
        cursor.execute("UPDATE core.canal SET activo = FALSE WHERE id_canal = 'BD'")
    try:
        respuesta = deposito(cliente, cuenta, id_canal="BD")
    finally:
        with admin.cursor() as cursor:
            cursor.execute("UPDATE core.canal SET activo = TRUE WHERE id_canal = 'BD'")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-CANAL"
