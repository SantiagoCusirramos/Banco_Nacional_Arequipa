"""Pruebas unitarias complementarias del parche, nunca se presentan como E2E."""
import json
from types import SimpleNamespace
import unittest
import httpx
from EVALUACION.config import Config
from EVALUACION.envios import DespachadorResultados


class CallbackAck(unittest.TestCase):
    def exercise(self,status=200,body=None,raw=None,timeout=False):
        def respond(req):
            if timeout:raise httpx.ReadTimeout('synthetic',request=req)
            return httpx.Response(status,json=body) if raw is None else httpx.Response(status,content=raw)
        cfg=Config(database_url='mysql+pymysql://unused',sol_url='http://sol:8011',sol_token_resultados='a'*40)
        dispatcher=DespachadorResultados(None,cfg,httpx.MockTransport(respond))
        events=[]
        dispatcher._terminar=lambda row,n,state,error:events.append((state,error))
        dispatcher._reprogramar=lambda row,n,error:events.append(('PENDIENTE',error))
        try:result=dispatcher._entregar(SimpleNamespace(contenido=json.dumps({'idOperacion':'op-synthetic','idCorrelacion':'corr-synthetic'}),intentos=0,id_operacion='op-synthetic'))
        finally:dispatcher.cerrar()
        return result,events
    def test_valid(self):self.assertEqual(self.exercise(body={'recibido':True,'idOperacion':'op-synthetic'}),(1,[('ENTREGADO',None)]))
    def test_false(self):self.assertEqual(self.exercise(body={'recibido':False,'idOperacion':'op-synthetic'})[1][0][0],'ERROR')
    def test_wrong_id(self):self.assertEqual(self.exercise(body={'recibido':True,'idOperacion':'other'})[1][0][0],'ERROR')
    def test_invalid_json(self):self.assertEqual(self.exercise(raw=b'not-json')[1][0],('ERROR','ACUSE_SOL_INVALIDO'))
    def test_401(self):self.assertEqual(self.exercise(401,body={})[1][0],('ERROR','HTTP_401'))
    def test_409(self):self.assertEqual(self.exercise(409,body={})[1][0][0],'PENDIENTE')
    def test_timeout(self):self.assertEqual(self.exercise(timeout=True)[1][0][0],'PENDIENTE')
    def test_202_not_receipt(self):self.assertEqual(self.exercise(202,body={'recibido':True,'idOperacion':'op-synthetic'})[1][0][0],'ERROR')
    def test_non_bool(self):self.assertEqual(self.exercise(body={'recibido':1,'idOperacion':'op-synthetic'})[1][0][0],'ERROR')


if __name__=='__main__':unittest.main()
