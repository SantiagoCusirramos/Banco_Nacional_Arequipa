"""Pruebas de los Hallazgos #10 (deadlock en transferencias) y #11
(idempotencia) del Informe de Errores BNA.

No requieren MySQL: se usan dobles de prueba (fakes) para la sesión y las
filas. La prueba de transferencias cruzadas A->B / B->A simula los
candados de fila de InnoDB con `threading.Lock` y demuestra que:
  - el orden anterior (origen y luego destino) produce espera circular;
  - el orden nuevo (num_cuenta ascendente) no la produce.
La verificación definitiva sigue siendo una prueba de integración con
MySQL real y dos conexiones concurrentes.
"""

import threading
from decimal import Decimal
from types import SimpleNamespace

import pymysql
import pytest
from sqlalchemy.exc import OperationalError

from CORE.exceptions import ConcurrencyError, IdempotencyConflictError, ValidationError
from CORE.services import movimientos as mov

# ── Dobles de prueba ──────────────────────────────────────────────────


class DeadlockSimulado(Exception):
    pass


class CandadosFila:
    """Simula los candados de fila (FOR UPDATE) de InnoDB."""

    def __init__(self, cuentas, espera_max=1.0):
        self.locks = {c: threading.Lock() for c in cuentas}
        self.espera_max = espera_max
        self.barrera = threading.Barrier(2)

    def adquirir(self, num, retenidos):
        if not self.locks[num].acquire(timeout=self.espera_max):
            raise DeadlockSimulado(f"espera circular esperando {num}")
        retenidos.append(num)
        if len(retenidos) == 1:
            # Fuerza el peor caso: ambos hilos toman su primer candado
            # "a la vez" antes de pedir el segundo.
            try:
                self.barrera.wait(timeout=0.3)
            except threading.BrokenBarrierError:
                pass


class FakeQuery:
    def __init__(self, sesion):
        self.sesion = sesion
        self.num = None

    def filter(self, expr):
        self.num = expr.right.value
        return self

    def with_for_update(self):
        return self

    def first(self):
        self.sesion.orden_bloqueo.append(self.num)
        if self.sesion.candados is not None:
            self.sesion.candados.adquirir(self.num, self.sesion.retenidos)
        return SimpleNamespace(num_cuenta=self.num)


class FakeSesion:
    def __init__(self, candados=None):
        self.candados = candados
        self.orden_bloqueo = []
        self.retenidos = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, _modelo):
        return FakeQuery(self)

    def commit(self):
        self.commits += 1
        self._liberar()

    def rollback(self):
        self.rollbacks += 1
        self._liberar()

    def _liberar(self):
        if self.candados:
            for num in reversed(self.retenidos):
                self.candados.locks[num].release()
        self.retenidos.clear()


def _error_deadlock():
    orig = pymysql.err.OperationalError(
        1213, "Deadlock found when trying to get lock; try restarting transaction"
    )
    return OperationalError("SELECT ... FOR UPDATE", {}, orig)


def _bloqueo_antiguo(db, origen, destino):
    """Réplica del comportamiento anterior: origen primero, luego destino."""
    for num in (origen, destino):
        db.query(mov.CuentaAhorro).filter(
            mov.CuentaAhorro.num_cuenta == num
        ).with_for_update().first()


def _correr_cruzadas(funcion_bloqueo):
    """Lanza A->B y B->A en paralelo; devuelve los errores de cada hilo."""
    candados = CandadosFila(["A-001", "B-002"])
    errores = []

    def transferir(origen, destino):
        db = FakeSesion(candados)
        try:
            funcion_bloqueo(db, origen, destino)
            db.commit()
        except DeadlockSimulado as exc:
            errores.append(exc)
            db.rollback()

    hilos = [
        threading.Thread(target=transferir, args=("A-001", "B-002")),
        threading.Thread(target=transferir, args=("B-002", "A-001")),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=5)
    return errores


# ── Hallazgo #10: orden de bloqueo y reintentos ───────────────────────


class TestOrdenBloqueo:
    def test_bloquea_en_orden_ascendente_sin_importar_origen(self):
        db = FakeSesion()
        mov._bloquear_cuentas_en_orden(db, "200", "100")
        assert db.orden_bloqueo == ["100", "200"]

        db = FakeSesion()
        mov._bloquear_cuentas_en_orden(db, "100", "200")
        assert db.orden_bloqueo == ["100", "200"]

    def test_orden_antiguo_produce_espera_circular(self):
        errores = _correr_cruzadas(_bloqueo_antiguo)
        assert errores, "el orden origen->destino debería generar deadlock"

    def test_orden_nuevo_no_produce_espera_circular(self):
        errores = _correr_cruzadas(mov._bloquear_cuentas_en_orden)
        assert errores == []


class TestReintentosDeadlock:
    @pytest.fixture(autouse=True)
    def _sin_espera(self, monkeypatch):
        monkeypatch.setattr(mov.time, "sleep", lambda _s: None)

    def test_detecta_deadlock_mysql(self):
        assert mov._es_deadlock(_error_deadlock())
        otro = OperationalError("x", {}, pymysql.err.OperationalError(2006, "gone away"))
        assert not mov._es_deadlock(otro)

    def test_reintenta_y_luego_confirma(self):
        db = FakeSesion()
        llamadas = {"n": 0}

        def operacion():
            llamadas["n"] += 1
            if llamadas["n"] < 3:
                raise _error_deadlock()
            return "ok"

        assert mov._con_reintentos_deadlock(db, operacion, nombre="prueba") == "ok"
        assert llamadas["n"] == 3
        assert db.rollbacks == 2 and db.commits == 1

    def test_agota_reintentos_y_responde_503(self):
        db = FakeSesion()

        def operacion():
            raise _error_deadlock()

        with pytest.raises(ConcurrencyError) as exc:
            mov._con_reintentos_deadlock(db, operacion, nombre="transferencia")
        assert exc.value.status_code == 503
        assert db.rollbacks == mov.MAX_INTENTOS_DEADLOCK

    def test_error_que_no_es_deadlock_no_se_reintenta(self):
        db = FakeSesion()
        llamadas = {"n": 0}
        error = OperationalError("x", {}, pymysql.err.OperationalError(2006, "gone"))

        def operacion():
            llamadas["n"] += 1
            raise error

        with pytest.raises(OperationalError):
            mov._con_reintentos_deadlock(db, operacion, nombre="prueba")
        assert llamadas["n"] == 1

    def test_transferir_reintenta_ante_deadlock(self, monkeypatch):
        db = FakeSesion()
        llamadas = {"n": 0}

        def falso_ejecutar(_db, **_kw):
            llamadas["n"] += 1
            if llamadas["n"] == 1:
                raise _error_deadlock()
            return "resultado"

        monkeypatch.setattr(mov, "_ejecutar_transferencia", falso_ejecutar)
        res = mov.transferir_cuentas(
            db, num_cuenta_origen="A", num_cuenta_destino="B",
            monto=Decimal("10"), id_canal="WEB",
        )
        assert res == "resultado"
        assert llamadas["n"] == 2 and db.commits == 1


# ── Hallazgo #11: idempotencia ────────────────────────────────────────


def _tx(**kw):
    base = dict(
        id_transaccion="tx-" + kw.get("idempotency_key", "x"),
        uuid_transaccion="u",
        num_cuenta_contraparte=None,
        moneda="PEN",
        id_canal="WEB",
        monto=Decimal("100.00"),
        saldo_posterior=Decimal("0.00"),
        fecha_hora=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _transferencia_guardada(key="K1"):
    """Las dos patas, con la DESTINO primero (mismo fecha_hora)."""
    destino = _tx(
        idempotency_key=key + "#C", num_cuenta="B", num_cuenta_contraparte="A",
        tipo_operacion="TRANSFERENCIA", tipo_movimiento="C",
        saldo_posterior=Decimal("600.00"),
    )
    origen = _tx(
        idempotency_key=key, num_cuenta="A", num_cuenta_contraparte="B",
        tipo_operacion="TRANSFERENCIA", tipo_movimiento="D",
        saldo_posterior=Decimal("400.00"),
    )
    return [destino, origen]


@pytest.fixture
def sin_auditoria(monkeypatch):
    monkeypatch.setattr(mov, "_evento_registro", lambda _db, _id: {})


class TestIdempotencia:
    def test_replay_transferencia_no_intercambia_patas(self, monkeypatch, sin_auditoria):
        monkeypatch.setattr(
            mov, "_buscar_por_idempotencia", lambda _db, _k: _transferencia_guardada()
        )
        res = mov.transferir_cuentas(
            None, num_cuenta_origen="A", num_cuenta_destino="B",
            monto=Decimal("100"), moneda="PEN", id_canal="WEB",
            idempotency_key="K1",
        )
        assert res.replay
        assert res.origen.num_cuenta == "A" and res.origen.tipo_movimiento == "D"
        assert res.destino.num_cuenta == "B" and res.destino.tipo_movimiento == "C"

    def test_misma_llave_otro_monto_da_409(self, monkeypatch, sin_auditoria):
        monkeypatch.setattr(
            mov, "_buscar_por_idempotencia", lambda _db, _k: _transferencia_guardada()
        )
        with pytest.raises(IdempotencyConflictError) as exc:
            mov.transferir_cuentas(
                None, num_cuenta_origen="A", num_cuenta_destino="B",
                monto=Decimal("999"), moneda="PEN", id_canal="WEB",
                idempotency_key="K1",
            )
        assert exc.value.status_code == 409
        assert "monto" in exc.value.details["diferencias"]

    def test_misma_llave_otro_destino_da_409(self, monkeypatch, sin_auditoria):
        monkeypatch.setattr(
            mov, "_buscar_por_idempotencia", lambda _db, _k: _transferencia_guardada()
        )
        with pytest.raises(IdempotencyConflictError) as exc:
            mov.transferir_cuentas(
                None, num_cuenta_origen="A", num_cuenta_destino="C",
                monto=Decimal("100"), moneda="PEN", id_canal="WEB",
                idempotency_key="K1",
            )
        assert "num_cuenta_contraparte" in exc.value.details["diferencias"]

    def test_llave_de_deposito_no_sirve_para_transferencia(self, monkeypatch, sin_auditoria):
        deposito = _tx(
            idempotency_key="K2", num_cuenta="A", tipo_operacion="DEPOSITO",
            tipo_movimiento="C",
        )
        monkeypatch.setattr(mov, "_buscar_por_idempotencia", lambda _db, _k: [deposito])
        with pytest.raises(IdempotencyConflictError) as exc:
            mov.transferir_cuentas(
                None, num_cuenta_origen="A", num_cuenta_destino="B",
                monto=Decimal("100"), moneda="PEN", id_canal="WEB",
                idempotency_key="K2",
            )
        assert "tipo_operacion" in exc.value.details["diferencias"]

    def test_llave_de_transferencia_no_sirve_para_deposito(self, monkeypatch, sin_auditoria):
        monkeypatch.setattr(
            mov, "_buscar_por_idempotencia", lambda _db, _k: _transferencia_guardada()
        )
        with pytest.raises(IdempotencyConflictError):
            mov.registrar_movimiento(
                None, tipo_operacion="DEPOSITO", num_cuenta="A",
                monto=Decimal("100"), moneda="PEN", id_canal="WEB",
                idempotency_key="K1",
            )

    def test_deposito_vs_retiro_misma_llave_da_409(self, monkeypatch, sin_auditoria):
        deposito = _tx(
            idempotency_key="K3", num_cuenta="A", tipo_operacion="DEPOSITO",
            tipo_movimiento="C",
        )
        monkeypatch.setattr(mov, "_buscar_por_idempotencia", lambda _db, _k: [deposito])
        with pytest.raises(IdempotencyConflictError):
            mov.registrar_movimiento(
                None, tipo_operacion="RETIRO", num_cuenta="A",
                monto=Decimal("100"), moneda="PEN", id_canal="WEB",
                idempotency_key="K3",
            )

    def test_replay_deposito_identico(self, monkeypatch, sin_auditoria):
        deposito = _tx(
            idempotency_key="K4", num_cuenta="A", tipo_operacion="DEPOSITO",
            tipo_movimiento="C",
        )
        monkeypatch.setattr(mov, "_buscar_por_idempotencia", lambda _db, _k: [deposito])
        res = mov.registrar_movimiento(
            None, tipo_operacion="DEPOSITO", num_cuenta="A",
            monto=Decimal("100.00"), moneda="PEN", id_canal="WEB",
            idempotency_key="K4",
        )
        assert res.replay and res.id_transaccion == deposito.id_transaccion

    def test_usa_hash_guardado_en_auditoria(self, monkeypatch):
        deposito = _tx(
            idempotency_key="K5", num_cuenta="A", tipo_operacion="DEPOSITO",
            tipo_movimiento="C",
        )
        monkeypatch.setattr(mov, "_buscar_por_idempotencia", lambda _db, _k: [deposito])
        monkeypatch.setattr(
            mov, "_evento_registro", lambda _db, _id: {"hash_peticion": "otro-hash"}
        )
        with pytest.raises(IdempotencyConflictError):
            mov.registrar_movimiento(
                None, tipo_operacion="DEPOSITO", num_cuenta="A",
                monto=Decimal("100"), moneda="PEN", id_canal="WEB",
                idempotency_key="K5",
            )

    def test_sufijo_reservado_rechazado(self):
        with pytest.raises(ValidationError):
            mov.registrar_movimiento(
                None, tipo_operacion="DEPOSITO", num_cuenta="A",
                monto=Decimal("1"), moneda="PEN", id_canal="WEB",
                idempotency_key="abc#C",
            )

    def test_llave_transferencia_demasiado_larga(self):
        with pytest.raises(ValidationError):
            mov.transferir_cuentas(
                None, num_cuenta_origen="A", num_cuenta_destino="B",
                monto=Decimal("1"), moneda="PEN", id_canal="WEB",
                idempotency_key="x" * 63,
            )

    def test_huella_normaliza_monto(self):
        p1 = mov._parametros_criticos(
            tipo_operacion="DEPOSITO", num_cuenta="A", num_cuenta_contraparte=None,
            monto=Decimal("100"), moneda="PEN", id_canal="WEB",
        )
        p2 = dict(p1, monto=str(mov.D(Decimal("100.00"))))
        assert mov._huella(p1) == mov._huella(p2)
