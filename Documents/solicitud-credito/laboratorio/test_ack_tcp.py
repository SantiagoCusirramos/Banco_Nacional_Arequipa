"""Fallos de acuse por TCP a proceso HTTP de prueba; complementa aplicaciones reales."""
import json
import time
from multiprocessing import Process, Pipe
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
import unittest
from EVALUACION.config import Config
from EVALUACION.envios import DespachadorResultados


def serve(pipe,status,body):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length','0')))
            if status==0:time.sleep(0.3)
            self.send_response(status or 200);self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=HTTPServer(('127.0.0.1',0),Handler)
    pipe.send(server.server_port);server.serve_forever()


class AckTCP(unittest.TestCase):
    def run_case(self,status,body,expected):
        parent,child=Pipe()
        process=Process(target=serve,args=(child,status,body));process.start()
        port=parent.recv()
        dispatcher=DespachadorResultados(None,Config(database_url='unused',sol_url=f'http://127.0.0.1:{port}',sol_token_resultados='a'*40,timeout_seg=0.05 if status==0 else 3))
        events=[]
        dispatcher._terminar=lambda row,n,state,error:events.append(state)
        dispatcher._reprogramar=lambda row,n,error:events.append('PENDIENTE')
        try:
            dispatcher._entregar(SimpleNamespace(contenido=json.dumps({'idOperacion':'op-tcp-test','idCorrelacion':'corr-synthetic'}),intentos=0,id_operacion='op-tcp-test'))
            self.assertEqual(events,[expected])
        finally:
            dispatcher.cerrar();process.terminate();process.join(5);parent.close();child.close()
    def test_valid_tcp(self):self.run_case(200,b'{"recibido":true,"idOperacion":"op-tcp-test"}','ENTREGADO')
    def test_false_tcp(self):self.run_case(200,b'{"recibido":false,"idOperacion":"op-tcp-test"}','ERROR')
    def test_wrong_id_tcp(self):self.run_case(200,b'{"recibido":true,"idOperacion":"wrong"}','ERROR')
    def test_invalid_json_tcp(self):self.run_case(200,b'bad-json','ERROR')
    def test_401_tcp(self):self.run_case(401,b'{}','ERROR')
    def test_409_tcp(self):self.run_case(409,b'{}','PENDIENTE')
    def test_timeout_tcp(self):self.run_case(0,b'{}','PENDIENTE')


if __name__=='__main__':unittest.main()
