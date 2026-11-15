import os, unittest
from decimal import Decimal
from pydantic import ValidationError
from COBRANZA.main import ObligacionIn, PagoIn


def obligacion(**cambios):
    base = {"codCredito": "CR-0001", "idCliente": "CLI-0001", "idSolicitud": "SOL-0001",
            "montoAprobado": Decimal("1200.00"), "moneda": "PEN", "fechaDesembolso": "2026-10-05T10:00:00",
            "calendarioPagos": []}
    base.update(cambios)
    return base


def pago(**cambios):
    base = {"codCliente": "CLI-0001", "codCredito": "CR-0001", "montoPago": Decimal("150.00"),
            "cuentaOrigen": "AH-001-123456", "referenciaTransaccion": "OP-0001", "idCanal": "HB"}
    base.update(cambios)
    return base


class PruebasValidacionLongitud(unittest.TestCase):
    """Los Field(max_length=...) de COBRANZA/main.py deben coincidir con el esquema de BD,
    para que un dato demasiado largo se rechace con 422 (ValidationError) y no con un error de MySQL."""

    def test_codCredito_demasiado_largo_es_rechazado(self):
        with self.assertRaises(ValidationError):
            ObligacionIn(**obligacion(codCredito="X" * 21))

    def test_idCliente_demasiado_largo_es_rechazado(self):
        with self.assertRaises(ValidationError):
            ObligacionIn(**obligacion(idCliente="X" * 21))

    def test_idSolicitud_demasiado_largo_es_rechazado(self):
        with self.assertRaises(ValidationError):
            ObligacionIn(**obligacion(idSolicitud="X" * 21))

    def test_codCliente_demasiado_largo_es_rechazado(self):
        with self.assertRaises(ValidationError):
            PagoIn(**pago(codCliente="X" * 21))

    def test_pagoIn_codCredito_demasiado_largo_es_rechazado(self):
        with self.assertRaises(ValidationError):
            PagoIn(**pago(codCredito="X" * 21))

    def test_referenciaTransaccion_demasiado_larga_es_rechazada(self):
        with self.assertRaises(ValidationError):
            PagoIn(**pago(referenciaTransaccion="R" * 41))

    def test_idCanal_demasiado_largo_es_rechazado(self):
        with self.assertRaises(ValidationError):
            PagoIn(**pago(idCanal="X" * 11))

    def test_valores_en_el_limite_son_aceptados(self):
        ObligacionIn(**obligacion(codCredito="X" * 20, idCliente="X" * 20, idSolicitud="X" * 20))
        PagoIn(**pago(codCliente="X" * 20, codCredito="X" * 20,
                       referenciaTransaccion="R" * 40, idCanal="X" * 10))


if __name__ == "__main__":
    unittest.main()
