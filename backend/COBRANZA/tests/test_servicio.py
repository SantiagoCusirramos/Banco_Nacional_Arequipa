import os, unittest
from datetime import date, timedelta
from decimal import Decimal
from COBRANZA import servicio as S
from COBRANZA.db import conectar, crear_esquema
from COBRANZA.cuentas import CuentasSimulado
from COBRANZA.seguridad import SeguridadSimulada

HOY = date.today()


def _dias(n):
    """Fecha relativa a hoy (ISO), para que las cuotas de prueba no queden vencidas con el paso
    del tiempo real: siempre se calculan al correr la prueba, no quedan fijas en el pasado."""
    return (HOY + timedelta(days=n)).isoformat()


def obligacion(cod="CR-0001", cliente="CLI-0001"):
    return {"codCredito": cod, "idCliente": cliente, "idSolicitud": "SOL-0001", "montoAprobado": "1200.00",
            "moneda": "PEN", "fechaDesembolso": "2026-10-05T10:00:00",
            "calendarioPagos": [
                {"numeroCuota": 1, "fechaVencimiento": _dias(30), "montoCuota": "400.00"},
                {"numeroCuota": 2, "fechaVencimiento": _dias(60), "montoCuota": "400.00"},
                {"numeroCuota": 3, "fechaVencimiento": _dias(90), "montoCuota": "400.00"}]}


def pago(ref, monto, cuenta="AH-001", cod="CR-0001", cliente="CLI-0001"):
    return {"codCliente": cliente, "codCredito": cod, "montoPago": monto, "cuentaOrigen": cuenta,
            "referenciaTransaccion": ref, "idCanal": "HB"}


class PruebasCobranza(unittest.TestCase):
    def setUp(self):
        self.db = conectar("sqlite:///:memory:")
        crear_esquema(self.db)
        self.cuentas = CuentasSimulado()
        self.seguridad = SeguridadSimulada()
        S.activar_obligacion(self.db, obligacion())

    def n(self, tabla, where="1=1", params=()):
        return self.db.uno(f"SELECT COUNT(*) AS n FROM {tabla} WHERE {where}", params)["n"]

    def test_activacion_crea_credito_y_cuotas(self):
        c = S.obtener_credito(self.db, "CR-0001")
        self.assertEqual(c["estadoCredito"], "AL_DIA")  # RF-COB-007: ninguna cuota vencida al activar
        self.assertEqual(len(c["cuotas"]), 3)
        self.assertEqual(c["saldoTotalPendiente"], Decimal("1200.00"))

    def test_activacion_duplicada_es_rechazada(self):
        with self.assertRaises(S.ErrorNegocio) as e:
            S.activar_obligacion(self.db, obligacion())
        self.assertEqual(e.exception.status, 409)

    def test_pago_parcial_deja_cuota_parcial(self):
        r = S.registrar_pago(self.db, pago("OP-1", "150.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(r["estado"], "CONFIRMADO")
        self.assertEqual(r["aplicacion"]["estadoCuota"], "PARCIAL")
        self.assertEqual(r["aplicacion"]["saldoPendienteCuota"], Decimal("250.00"))

    def test_pago_completo_cierra_cuota_y_pasa_a_la_siguiente(self):
        S.registrar_pago(self.db, pago("OP-1", "150.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        r2 = S.registrar_pago(self.db, pago("OP-2", "250.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(r2["aplicacion"]["estadoCuota"], "PAGADA")
        r3 = S.registrar_pago(self.db, pago("OP-3", "100.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(r3["aplicacion"]["numeroCuota"], 2)

    def test_idempotencia_no_duplica_el_pago(self):
        r1 = S.registrar_pago(self.db, pago("OP-1", "150.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        r2 = S.registrar_pago(self.db, pago("OP-1", "150.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertTrue(r2["idempotente"])
        self.assertEqual(r1["idPago"], r2["idPago"])
        self.assertEqual(self.n("PAGO"), 1)
        self.assertEqual(self.n("APLICACION_PAGO"), 1)
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["cuotas"][0]["saldoPendiente"], Decimal("250.00"))

    def test_excedente_se_rechaza_hasta_definicion_del_comite(self):
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-1", "9999.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(e.exception.regla, "RN-COB-011")
        self.assertEqual(self.n("PAGO"), 0)

    def test_cuentas_rechaza_y_la_cuota_no_cambia(self):
        r = S.registrar_pago(self.db, pago("OP-1", "100.00", cuenta="SIN-FONDOS"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(r["estado"], "RECHAZADO")
        self.assertIsNone(r["aplicacion"])
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["cuotas"][0]["saldoPendiente"], Decimal("400.00"))
        self.assertEqual(self.n("APLICACION_PAGO"), 0)
        with self.assertRaises(S.ErrorNegocio):
            S.comprobante(self.db, "OP-1")

    def test_cuentas_sin_respuesta_deja_pago_pendiente(self):
        r = S.registrar_pago(self.db, pago("OP-1", "100.00", cuenta="SIN-RESPUESTA"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(r["estado"], "PENDIENTE")
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["cuotas"][0]["estadoCuota"], "PENDIENTE")

    def test_validaciones_de_credito_y_cliente(self):
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-1", "10.00", cod="NO-EXISTE"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(e.exception.status, 404)
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-2", "10.00", cliente="OTRO"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(e.exception.status, 403)

    def test_canal_no_confirmado_es_rechazado(self):
        d = pago("OP-1", "10.00"); d["idCanal"] = "ATM"
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, d, self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(e.exception.regla, "RN-COB-002")

    def test_mora_se_refleja_y_el_recalculo_conserva_historial(self):
        # La mora se guarda separada del capital (CUOTA.moraPendiente); un recalculo reemplaza el valor vigente.
        # La cuota 2 vence a los 60 dias; fecha_referencia simula que ya paso esa fecha (RN-COB-010).
        ref = _dias(65)
        S.registrar_mora(self.db, "CR-0001", 2, 5, "12.50", fecha_referencia=ref)
        c = S.obtener_credito(self.db, "CR-0001")["cuotas"][1]
        self.assertEqual(c["saldoPendiente"], Decimal("400.00"))
        self.assertEqual(c["moraPendiente"], Decimal("12.50"))
        self.assertEqual(c["totalAdeudado"], Decimal("412.50"))
        S.registrar_mora(self.db, "CR-0001", 2, 8, "20.00", fecha_referencia=ref)
        c = S.obtener_credito(self.db, "CR-0001")["cuotas"][1]
        self.assertEqual(c["saldoPendiente"], Decimal("400.00"))
        self.assertEqual(c["moraPendiente"], Decimal("20.00"))
        h = S.historial_mora(self.db, "CR-0001", 2)
        self.assertEqual(len(h), 2)
        self.assertEqual(sum(1 for x in h if x["vigente"]), 1)

    def test_credito_se_cancela_al_pagar_todo(self):
        for i, m in enumerate(("400.00", "400.00", "400.00"), 1):
            S.registrar_pago(self.db, pago(f"OP-{i}", m), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["estadoCredito"], "CANCELADO")
        with self.assertRaises(S.ErrorNegocio):
            S.registrar_pago(self.db, pago("OP-9", "10.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")

    def test_comprobante_y_auditoria(self):
        S.registrar_pago(self.db, pago("OP-1", "150.00"), self.cuentas, self.seguridad, "TOKEN-VALIDO")
        c = S.comprobante(self.db, "OP-1")
        self.assertEqual(c["saldoRestanteCredito"], Decimal("1050.00"))
        tipos = {e["tipoEvento"] for e in S.auditoria(self.db)}
        self.assertTrue({"OBLIGACION_ACTIVADA", "PAGO_REGISTRADO", "PAGO_APLICADO", "CUOTA_PARCIAL"} <= tipos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
