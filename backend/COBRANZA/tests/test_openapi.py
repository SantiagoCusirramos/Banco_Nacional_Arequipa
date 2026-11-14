"""RNF-23: la especificación publicada en backend/COBRANZA/openapi.json es la de la API actual.
Si falla, regenerarla desde backend/: python -m COBRANZA.scripts.exporta_openapi"""
import unittest

from COBRANZA.scripts.exporta_openapi import ARCHIVO, especificacion


class TestOpenAPI(unittest.TestCase):
    def test_openapi_publicado_al_dia(self):
        self.assertEqual(ARCHIVO.read_text(encoding="utf-8"), especificacion())


if __name__ == "__main__":
    unittest.main()
