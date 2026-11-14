"""Flujo por la API de Cobranza con CUENTAS del producto (transporte HTTP simulado, sin red):
CR-INT-06 activa el crédito, CR-INT-08 paga y CUENTAS debita; un pago sin confirmar se resuelve
después leyendo los movimientos de la cuenta, sin volver a cobrar (RF-COB-011, RN-COB-009)."""
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

import httpx
from fastapi.testclient import TestClient

from COBRANZA import cuentas as C
from COBRANZA import main

CLAVES = {"API_KEY_COBRANZA_LEER": "k-leer", "API_KEY_COBRANZA_EJECUTAR": "k-ejecutar",
          "API_KEY_INTEGRACION_BUS": "k-bus"}


class CuentasFalso:
    """COREDB (login) y CUENTAS (retiro y movimientos) en memoria."""

    def __init__(self):
        self.saldo = {"CTA-1": 500}
        self.movimientos = {"CTA-1": []}
        self.llaves = set()
        self.no_confirmar = False

    def __call__(self, req):
        ruta = req.url.path
        if ruta == "/coredb/auth/login":
            return httpx.Response(200, json={"access_token": "tok"})
        if ruta.endswith("/retiro"):
            import json
            cuerpo = json.loads(req.content)
            llave = req.headers["X-Idempotency-Key"]
            cuenta, monto = cuerpo["num_cuenta"], float(cuerpo["monto"])
            if llave not in self.llaves:
                if self.saldo.get(cuenta, 0) < monto:
                    return httpx.Response(400, json={"error_code": "ERR-CTA-FONDOS-INSUFICIENTES",
                                                     "message": "Saldo insuficiente"})
                self.llaves.add(llave)
                self.saldo[cuenta] -= monto
                self.movimientos[cuenta].insert(0, {"uuid_transaccion": llave, "glosa": cuerpo["glosa"],
                                                    "estado_transaccion": "APROBADO"})
            if self.no_confirmar:  # el cargo se hizo pero la respuesta no llegó (INC-01)
                return httpx.Response(504, json={"error_code": "ERR-CTA-OPERACION-NO-CONFIRMADA"})
            return httpx.Response(201, json={"data": {"uuid_transaccion": llave}})
        if ruta.endswith("/movimientos"):
            cuenta = ruta.split("/")[-2]
            return httpx.Response(200, json={"data": self.movimientos.get(cuenta, [])})
        return httpx.Response(404, json={})


class TestApiConCuentasBNA(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.entorno = mock.patch.dict(os.environ, {**CLAVES, "DATABASE_URL": f"sqlite:///{self.tmp.name}"})
        self.entorno.start()
        self.falso = CuentasFalso()
        credencial = C.CredencialServicio(usuario="svc-cobranza", secreto="s")
        bna = C.CuentasBNA("http://cuentas:8001/api/v1/cuentas", "http://coredb:8012", credencial,
                           transporte=httpx.MockTransport(self.falso))
        self.cuentas = mock.patch.object(main, "cuentas", bna)
        self.cuentas.start()
        self.api = TestClient(main.app)
        self.api.__enter__()
        hoy = date.today()
        r = self.api.post("/cr-int-06/obligaciones", headers={"X-API-Key": "k-bus"}, json={
            "codCredito": "CR-1", "idCliente": "CLI-1", "idSolicitud": "SOL-1", "montoAprobado": "300.00",
            "moneda": "PEN", "fechaDesembolso": f"{hoy}T09:00:00",
            "calendarioPagos": [{"numeroCuota": n, "fechaVencimiento": str(hoy + timedelta(days=30 * n)),
                                 "montoCuota": "150.00"} for n in (1, 2)]})
        self.assertEqual(r.status_code, 201, r.text)

    def tearDown(self):
        self.api.__exit__(None, None, None)
        self.cuentas.stop()
        self.entorno.stop()
        os.unlink(self.tmp.name)

    def pagar(self, cuenta, referencia):
        return self.api.post("/cr-int-08/pagos", headers={"X-API-Key": "k-bus", "X-Token-Seguridad": "ok"},
                             json={"codCliente": "CLI-1", "codCredito": "CR-1", "montoPago": "150.00",
                                   "cuentaOrigen": cuenta, "referenciaTransaccion": referencia}).json()

    def test_salud_informa_el_modo(self):
        self.assertEqual(self.api.get("/salud").json()["cuentas"], "bna")

    def test_pago_debitado_y_repetido_sin_cobrar_dos_veces(self):
        self.assertEqual(self.pagar("CTA-1", "OP-1")["estado"], "CONFIRMADO")
        self.assertTrue(self.pagar("CTA-1", "OP-1")["idempotente"])
        self.assertEqual(self.falso.saldo["CTA-1"], 350)

    def test_sin_fondos_no_cambia_la_cuota(self):
        pago = self.pagar("CTA-VACIA", "OP-2")
        self.assertEqual(pago["estado"], "RECHAZADO")
        self.assertIn("FONDOS-INSUFICIENTES", pago["motivo"])
        cuotas = self.api.get("/creditos/CR-1/cuotas", headers={"X-API-Key": "k-leer"}).json()
        self.assertEqual(cuotas[0]["estadoCuota"], "PENDIENTE")

    def test_pago_sin_confirmar_se_resuelve_leyendo_movimientos(self):
        self.falso.no_confirmar = True
        self.assertEqual(self.pagar("CTA-1", "OP-3")["estado"], "PENDIENTE")
        self.falso.no_confirmar = False
        r = self.api.post("/pagos/OP-3/resolver", headers={"X-API-Key": "k-ejecutar"}).json()
        self.assertEqual(r["estado"], "CONFIRMADO")
        self.assertEqual(self.falso.saldo["CTA-1"], 350)  # se cobró una sola vez


if __name__ == "__main__":
    unittest.main()
