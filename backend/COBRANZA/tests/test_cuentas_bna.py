"""CR-INT-07 contra CUENTAS del producto BNA, con un transporte HTTP simulado (sin red).

Comprueba lo que Cobranza envía a CUENTAS (ruta, cabeceras ITIL-01, monto como texto) y cómo
interpreta cada respuesta: cargo aplicado, rechazo de negocio, CUENTAS sin respuesta, token vencido
y la consulta posterior de un pago PENDIENTE, que nunca vuelve a cobrar (RN-COB-009)."""
import json
import os
import unittest
import uuid
from unittest import mock

import httpx

from COBRANZA import cuentas as C

CUENTAS = "http://cuentas:8001/api/v1/cuentas"
COREDB = "http://coredb:8012"


class FalsoBNA:
    """Hace de COREDB (login) y de CUENTAS (retiro y movimientos). Guarda cada petición."""

    def __init__(self, retiro=None, movimientos=None, tokens_vencidos=0):
        self.peticiones = []
        self.retiro = retiro or (lambda req: httpx.Response(201, json={
            "success": True, "data": {"uuid_transaccion": str(uuid.uuid4()), "replay": False}}))
        self.movimientos = movimientos if movimientos is not None else []
        self.tokens_vencidos = tokens_vencidos
        self.logins = 0

    def __call__(self, req: httpx.Request):
        self.peticiones.append(req)
        ruta = req.url.path
        if ruta == "/coredb/auth/login":
            self.logins += 1
            return httpx.Response(200, json={"access_token": f"tok-{self.logins}", "expires_in": 900})
        if self.tokens_vencidos > 0:
            self.tokens_vencidos -= 1
            return httpx.Response(401, json={"success": False, "error_code": "ERR-CTA-TOKEN-EXPIRADO"})
        if ruta.endswith("/retiro"):
            return self.retiro(req)
        if ruta.endswith("/movimientos"):
            return httpx.Response(200, json={"success": True, "data": self.movimientos})
        return httpx.Response(404, json={"success": False, "error_code": "ERR-NO-ENCONTRADO"})


def cliente(falso, usuario="svc-cobranza", secreto="secreto"):
    credencial = C.CredencialServicio(usuario=usuario, secreto=secreto)
    return C.CuentasBNA(CUENTAS, COREDB, credencial, canal="WEB", transporte=httpx.MockTransport(falso))


class TestCargo(unittest.TestCase):
    def test_cargo_aplicado_envia_cabeceras_itil_y_monto_como_texto(self):
        falso = FalsoBNA()
        estado, _ = cliente(falso).cargar("CR-0001", "AH-001-123456", 150, "PEN", "OP-0001")
        self.assertEqual(estado, "CONFIRMADO")
        login, retiro = falso.peticiones
        self.assertEqual(json.loads(login.content), {"username": "svc-cobranza", "password": "secreto"})
        self.assertEqual(retiro.url.path, "/api/v1/cuentas/retiro")
        self.assertEqual(retiro.headers["Authorization"], "Bearer tok-1")
        self.assertEqual(retiro.headers["X-Channel-ID"], "WEB")
        self.assertEqual(uuid.UUID(retiro.headers["X-Idempotency-Key"]).version, 4)
        self.assertIn("X-Request-Timestamp", retiro.headers)
        cuerpo = json.loads(retiro.content)
        self.assertEqual(cuerpo["num_cuenta"], "AH-001-123456")
        self.assertEqual(cuerpo["monto"], "150.00")
        self.assertIn("(ref. OP-0001)", cuerpo["glosa"])

    def test_la_misma_referencia_usa_siempre_la_misma_llave(self):
        self.assertEqual(C.idempotency_key_de("OP-0001"), C.idempotency_key_de("OP-0001"))
        self.assertNotEqual(C.idempotency_key_de("OP-0001"), C.idempotency_key_de("OP-0002"))

    def test_fondos_insuficientes_es_rechazo(self):
        falso = FalsoBNA(retiro=lambda req: httpx.Response(400, json={
            "success": False, "error_code": "ERR-CTA-FONDOS-INSUFICIENTES", "message": "Saldo insuficiente"}))
        estado, motivo = cliente(falso).cargar("CR-0001", "AH-1", 150, "PEN", "OP-0001")
        self.assertEqual(estado, "RECHAZADO")
        self.assertIn("ERR-CTA-FONDOS-INSUFICIENTES", motivo)

    def test_operacion_no_confirmada_queda_sin_respuesta(self):
        falso = FalsoBNA(retiro=lambda req: httpx.Response(504, json={
            "success": False, "error_code": "ERR-CTA-OPERACION-NO-CONFIRMADA"}))
        estado, _ = cliente(falso).cargar("CR-0001", "AH-1", 150, "PEN", "OP-0001")
        self.assertEqual(estado, "SIN_RESPUESTA")

    def test_cuentas_caido_queda_sin_respuesta(self):
        def caido(req):
            if req.url.path.endswith("/retiro"):
                raise httpx.ConnectError("sin conexion")
            return FalsoBNA()(req)
        estado, _ = cliente(caido).cargar("CR-0001", "AH-1", 150, "PEN", "OP-0001")
        self.assertEqual(estado, "SIN_RESPUESTA")

    def test_token_vencido_inicia_sesion_de_nuevo_con_la_misma_llave(self):
        falso = FalsoBNA(tokens_vencidos=1)
        estado, _ = cliente(falso).cargar("CR-0001", "AH-1", 150, "PEN", "OP-0001")
        self.assertEqual(estado, "CONFIRMADO")
        self.assertEqual(falso.logins, 2)
        retiros = [p for p in falso.peticiones if p.url.path.endswith("/retiro")]
        self.assertEqual(len({r.headers["X-Idempotency-Key"] for r in retiros}), 1)

    def test_sin_usuario_de_servicio_no_cobra(self):
        falso = FalsoBNA()
        estado, motivo = cliente(falso, usuario=None, secreto=None).cargar("CR-0001", "AH-1", 150, "PEN", "OP-1")
        self.assertEqual(estado, "RECHAZADO")
        self.assertIn("usuario de servicio", motivo)
        self.assertEqual(falso.peticiones, [])


class TestConsulta(unittest.TestCase):
    PAGO = {"cuentaOrigen": "AH-1", "montoPago": "150.00"}

    def test_encuentra_el_cargo_por_la_referencia(self):
        falso = FalsoBNA(movimientos=[
            {"uuid_transaccion": "u-1", "glosa": "Otro movimiento", "estado_transaccion": "APROBADO"},
            {"uuid_transaccion": "u-2", "glosa": "Pago de cuota del credito CR-1 (ref. OP-9)",
             "estado_transaccion": "APROBADO"}])
        estado, motivo = cliente(falso).consultar("OP-9", pago=self.PAGO)
        self.assertEqual(estado, "CONFIRMADO")
        self.assertIn("u-2", motivo)
        self.assertFalse(any(p.url.path.endswith("/retiro") for p in falso.peticiones))

    def test_cargo_extornado_es_rechazo(self):
        falso = FalsoBNA(movimientos=[
            {"uuid_transaccion": "u-2", "glosa": "Pago (ref. OP-9)", "estado_transaccion": "EXTORNADO"}])
        self.assertEqual(cliente(falso).consultar("OP-9", pago=self.PAGO)[0], "RECHAZADO")

    def test_sin_cargo_no_se_cobro(self):
        falso = FalsoBNA(movimientos=[])
        self.assertEqual(cliente(falso).consultar("OP-9", pago=self.PAGO)[0], "RECHAZADO")

    def test_sin_la_cuenta_del_pago_no_decide(self):
        self.assertEqual(cliente(FalsoBNA()).consultar("OP-9", pago={})[0], "SIN_RESPUESTA")


class TestSeleccion(unittest.TestCase):
    def test_modo_bna_usa_cuentas_real(self):
        entorno = {"CUENTAS_MODO": "BNA", "CUENTAS_URL": CUENTAS, "COREDB_URL": COREDB}
        with mock.patch.dict(os.environ, entorno, clear=False):
            self.assertIsInstance(C.crear_cliente_cuentas(), C.CuentasBNA)

    def test_credencial_desde_archivo(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"username": "svc-cobranza", "secreto": "s3"}, f)
        try:
            self.assertEqual(C.CredencialServicio(archivo=f.name).leer(), ("svc-cobranza", "s3"))
        finally:
            os.unlink(f.name)

    def test_sin_configuracion_es_simulado(self):
        with mock.patch.dict(os.environ, {"CUENTAS_MODO": "", "CUENTAS_URL": ""}, clear=False):
            self.assertIsInstance(C.crear_cliente_cuentas(), C.CuentasSimulado)


if __name__ == "__main__":
    unittest.main()
