import os, unittest
from datetime import date, timedelta
from decimal import Decimal
from COBRANZA import servicio as S
from COBRANZA.db import conectar, crear_esquema
from COBRANZA.cuentas import CuentasSimulado
from COBRANZA.seguridad import SeguridadSimulada

HOY = date.today()


def obligacion(cod="CR-0001", cliente="CLI-0001"):
    return {"codCredito": cod, "idCliente": cliente, "idSolicitud": "SOL-0001", "montoAprobado": "400.00",
            "moneda": "PEN", "fechaDesembolso": "2026-10-05T10:00:00",
            "calendarioPagos": [{"numeroCuota": 1, "fechaVencimiento": (HOY + timedelta(days=30)).isoformat(),
                                  "montoCuota": "400.00"}]}


def pago(ref, monto, cuenta="AH-001", cod="CR-0001", cliente="CLI-0001"):
    return {"codCliente": cliente, "codCredito": cod, "montoPago": monto, "cuentaOrigen": cuenta,
            "referenciaTransaccion": ref, "idCanal": "HB"}


class PruebasParte2B(unittest.TestCase):
    def setUp(self):
        self.db = conectar("sqlite:///:memory:")
        crear_esquema(self.db)
        self.cuentas = CuentasSimulado()
        self.seguridad = SeguridadSimulada()

    # ---------------------------------------------------------- RF-COB-011 / INC-01
    def test_pagos_pendientes_lista_con_antiguedad(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_pago(self.db, pago("OP-1", "100.00", cuenta="SIN-RESPUESTA"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        pend = S.pagos_pendientes(self.db)
        self.assertEqual(len(pend), 1)
        self.assertEqual(pend[0]["referenciaTransaccion"], "OP-1")
        self.assertGreaterEqual(pend[0]["antiguedadHoras"], 0)

    def test_resolver_pago_confirmado_lo_aplica(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_pago(self.db, pago("OP-1", "100.00", cuenta="SIN-RESPUESTA"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        r = S.resolver_pago(self.db, "OP-1", self.cuentas)  # consultar() por defecto: CONFIRMADO
        self.assertEqual(r["estado"], "CONFIRMADO")
        self.assertEqual(r["aplicacion"]["estadoCuota"], "PARCIAL")
        self.assertEqual(r["aplicacion"]["saldoPendienteCuota"], Decimal("300.00"))
        self.assertEqual(S.pagos_pendientes(self.db), [])

    def test_resolver_pago_rechazado_al_consultar(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_pago(self.db, pago("OP-1-RECHAZA", "100.00", cuenta="SIN-RESPUESTA"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        r = S.resolver_pago(self.db, "OP-1-RECHAZA", self.cuentas)
        self.assertEqual(r["estado"], "RECHAZADO")
        self.assertIsNone(r["aplicacion"])

    def test_resolver_pago_sigue_sin_respuesta(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_pago(self.db, pago("OP-1-SIGUESIN", "100.00", cuenta="SIN-RESPUESTA"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        r = S.resolver_pago(self.db, "OP-1-SIGUESIN", self.cuentas)
        self.assertEqual(r["estado"], "PENDIENTE")
        self.assertEqual(len(S.pagos_pendientes(self.db)), 1)

    def test_resolver_pago_no_pendiente_es_rechazado(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")  # ya CONFIRMADO
        with self.assertRaises(S.ErrorNegocio) as e:
            S.resolver_pago(self.db, "OP-1", self.cuentas)
        self.assertEqual(e.exception.status, 409)
        self.assertEqual(e.exception.regla, "RN-COB-009")

    def test_resolver_pago_nunca_reintenta_el_cargo(self):
        class CuentasSinCargar(CuentasSimulado):
            def cargar(self, *a, **k):
                raise AssertionError("resolver_pago no debe reintentar el cargo (RN-COB-009)")

        S.activar_obligacion(self.db, obligacion())
        S.registrar_pago(self.db, pago("OP-1", "100.00", cuenta="SIN-RESPUESTA"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        r = S.resolver_pago(self.db, "OP-1", CuentasSinCargar())
        self.assertEqual(r["estado"], "CONFIRMADO")

    def test_resolver_pago_requiere_revision_si_la_cuota_cambio(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_pago(self.db, pago("OP-PEND", "400.00", cuenta="SIN-RESPUESTA"), self.cuentas, self.seguridad, "TOKEN-VALIDO")  # no toca la cuota
        S.registrar_pago(self.db, pago("OP-OTRO", "100.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")  # confirma: saldo baja a 300
        r = S.resolver_pago(self.db, "OP-PEND", self.cuentas)  # 400 > 300 adeudado ahora
        self.assertEqual(r["estado"], "REQUIERE_REVISION")
        tipos = {e["tipoEvento"] for e in S.auditoria(self.db)}
        self.assertIn("PAGO_REQUIERE_REVISION", tipos)

    # ---------------------------------------------------------- RF-COB-018
    def test_conciliacion_cobrado_aplicado_y_detalle(self):
        S.activar_obligacion(self.db, obligacion(cod="CR-A"))
        S.activar_obligacion(self.db, obligacion(cod="CR-B"))
        S.registrar_pago(self.db, pago("OP-OK", "100.00", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")  # CONFIRMADO
        S.registrar_pago(self.db, pago("OP-PEND", "50.00", cuenta="SIN-RESPUESTA", cod="CR-B"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        S.registrar_pago(self.db, pago("OP-MAL", "10.00", cuenta="SIN-FONDOS", cod="CR-B"), self.cuentas, self.seguridad, "TOKEN-VALIDO")

        c = S.conciliacion(self.db)
        self.assertEqual(c["totalCobrado"], Decimal("100.00"))
        self.assertEqual(c["totalAplicado"], Decimal("100.00"))
        self.assertEqual(c["diferencia"], Decimal("0.00"))
        self.assertEqual(c["cantidadPagosCobrados"], 1)
        self.assertEqual(len(c["pagosPendientes"]), 1)
        self.assertEqual(len(c["pagosRechazados"]), 1)
        self.assertEqual(len(c["pagosRequierenRevision"]), 0)
        tipos = {e["tipoEvento"] for e in S.auditoria(self.db)}
        self.assertIn("CONCILIACION_EJECUTADA", tipos)

    def test_conciliacion_refleja_requiere_revision_como_diferencia(self):
        S.activar_obligacion(self.db, obligacion(cod="CR-A"))
        S.registrar_pago(self.db, pago("OP-PEND", "400.00", cuenta="SIN-RESPUESTA", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        S.registrar_pago(self.db, pago("OP-OTRO", "100.00", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        S.resolver_pago(self.db, "OP-PEND", self.cuentas)  # 400 > 300 -> REQUIERE_REVISION

        c = S.conciliacion(self.db)
        self.assertEqual(c["totalCobrado"], Decimal("500.00"))
        self.assertEqual(c["totalAplicado"], Decimal("100.00"))
        self.assertEqual(c["diferencia"], Decimal("400.00"))
        self.assertEqual(len(c["pagosRequierenRevision"]), 1)

    # ---------------------------------------------------------- I-05
    def test_metricas_tasa_de_fallas_y_pendientes(self):
        S.activar_obligacion(self.db, obligacion(cod="CR-A"))
        S.registrar_pago(self.db, pago("OP-OK", "100.00", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        S.registrar_pago(self.db, pago("OP-MAL", "10.00", cuenta="SIN-FONDOS", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        S.registrar_pago(self.db, pago("OP-PEND", "10.00", cuenta="SIN-RESPUESTA", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        m = S.metricas(self.db)
        self.assertEqual(m["intentosValidos"], 3)
        self.assertEqual(m["pagosFallidos"], 2)
        self.assertEqual(m["tasaFallasOperacion"], round(2 / 3, 4))
        self.assertEqual(m["pagosPendientes"], 1)
        self.assertIsNone(m["tiempoRespuestaPagosP95Ms"])  # eso lo mide el middleware de main.py

    def test_metricas_duplicado_no_cuenta_como_intento_nuevo(self):
        S.activar_obligacion(self.db, obligacion(cod="CR-A"))
        S.registrar_pago(self.db, pago("OP-1", "100.00", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        S.registrar_pago(self.db, pago("OP-1", "100.00", cod="CR-A"), self.cuentas, self.seguridad, "TOKEN-VALIDO")  # idempotente
        self.assertEqual(S.metricas(self.db)["intentosValidos"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
