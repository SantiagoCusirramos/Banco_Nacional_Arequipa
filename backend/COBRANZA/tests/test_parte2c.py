import os, unittest
from datetime import date, timedelta
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


class PruebasParte2C(unittest.TestCase):
    def setUp(self):
        self.db = conectar("sqlite:///:memory:")
        crear_esquema(self.db)
        self.cuentas = CuentasSimulado()
        S.activar_obligacion(self.db, obligacion())

    def n(self, tabla, where="1=1", params=()):
        return self.db.uno(f"SELECT COUNT(*) AS n FROM {tabla} WHERE {where}", params)["n"]

    # ---------------------------------------------------------- RF-COB-004
    def test_token_invalido_es_rechazado_y_no_crea_pago(self):
        seguridad = SeguridadSimulada()
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        self.assertEqual(e.exception.status, 401)
        self.assertEqual(e.exception.regla, "RF-COB-004")
        self.assertEqual(self.n("PAGO"), 0)

    def test_token_vacio_es_rechazado(self):
        seguridad = SeguridadSimulada()
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, seguridad, None)
        self.assertEqual(e.exception.regla, "RF-COB-004")

    def test_token_valido_permite_el_pago(self):
        seguridad = SeguridadSimulada()
        r = S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, seguridad, "TOKEN-VALIDO")
        self.assertEqual(r["estado"], "CONFIRMADO")

    def test_tres_rechazos_bloquean_los_pagos_del_cliente(self):
        seguridad = SeguridadSimulada(bloqueo_segundos=9999, limite_rechazos=3)
        for i in range(3):
            with self.assertRaises(S.ErrorNegocio):
                S.registrar_pago(self.db, pago(f"OP-{i}", "100.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        # el cuarto intento, aunque mande un token VALIDO, sigue bloqueado
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-4", "100.00"), self.cuentas, seguridad, "TOKEN-VALIDO")
        self.assertIn("bloqueado", e.exception.detalle.lower())
        self.assertEqual(self.n("PAGO"), 0)

    def test_limite_de_rechazos_es_configurable(self):
        seguridad = SeguridadSimulada(bloqueo_segundos=9999, limite_rechazos=1)
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        self.assertIn("bloqueado", e.exception.detalle.lower())

    def test_token_valido_reinicia_el_contador_de_rechazos(self):
        seguridad = SeguridadSimulada(bloqueo_segundos=9999, limite_rechazos=3)
        with self.assertRaises(S.ErrorNegocio):
            S.registrar_pago(self.db, pago("OP-1", "10.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        with self.assertRaises(S.ErrorNegocio):
            S.registrar_pago(self.db, pago("OP-2", "10.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        r = S.registrar_pago(self.db, pago("OP-3", "100.00"), self.cuentas, seguridad, "TOKEN-VALIDO")
        self.assertEqual(r["estado"], "CONFIRMADO")
        # dos rechazos mas no deberian bloquear, porque el token valido reinicio el contador
        with self.assertRaises(S.ErrorNegocio):
            S.registrar_pago(self.db, pago("OP-4", "10.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        with self.assertRaises(S.ErrorNegocio):
            S.registrar_pago(self.db, pago("OP-5", "10.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        r2 = S.registrar_pago(self.db, pago("OP-6", "10.00"), self.cuentas, seguridad, "TOKEN-VALIDO")
        self.assertEqual(r2["estado"], "CONFIRMADO")

    def test_rechazo_de_token_queda_en_auditoria(self):
        seguridad = SeguridadSimulada()
        with self.assertRaises(S.ErrorNegocio):
            S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, seguridad, "TOKEN-INVALIDO")
        eventos = [e for e in S.auditoria(self.db, "CLI-0001") if e["tipoEvento"] == "TOKEN_SEGURIDAD_RECHAZADO"]
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["resultado"], "RECHAZADO")

    # ---------------------------------------------------------- CR-INT-10: campo resultado
    def test_resultado_exitoso_por_defecto(self):
        seguridad = SeguridadSimulada()
        S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, seguridad, "TOKEN-VALIDO")
        tipos = {e["tipoEvento"]: e["resultado"] for e in S.auditoria(self.db, limite=100)}
        self.assertEqual(tipos["PAGO_APLICADO"], "EXITOSO")

    def test_resultado_rechazado_en_pago_rechazado_por_cuentas(self):
        seguridad = SeguridadSimulada()
        S.registrar_pago(self.db, pago("OP-1", "100.00", cuenta="SIN-FONDOS"), self.cuentas, seguridad, "TOKEN-VALIDO")
        tipos = {e["tipoEvento"]: e["resultado"] for e in S.auditoria(self.db, limite=100)}
        self.assertEqual(tipos["PAGO_RECHAZADO"], "RECHAZADO")

    # ---------------------------------------------------------- RN-CR-GEN-004: usuarioOperador = rol
    def test_usuario_operador_toma_el_rol_que_hizo_la_llamada(self):
        seguridad = SeguridadSimulada()
        S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas, seguridad, "TOKEN-VALIDO",
                          usuario="INTEGRACION_BUS")
        eventos = S.auditoria(self.db, limite=100)
        aplicados = [e for e in eventos if e["tipoEvento"] == "PAGO_APLICADO"]
        self.assertEqual(aplicados[0]["usuarioOperador"], "INTEGRACION_BUS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
