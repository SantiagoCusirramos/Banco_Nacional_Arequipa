"""Caída y recuperación de EVA real controladas por launcher fuera de contenedores."""
import json
import os
import sys
import time
import httpx
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL


def main():
    case=json.loads(os.environ['LAB_RECOVERY_JSON'])
    mode=sys.argv[1]
    engine=create_engine(URL.create('mysql+pymysql',username=os.environ['SOL_DB_USER'],password=os.environ['SOL_DB_PASSWORD'],
                                   host='mysql-modulos',database=os.environ['SOL_DB_NAME']),hide_parameters=True)
    assert os.environ['SOL_DB_NAME'].startswith('bna_sol_mvp_final')
    with httpx.Client(timeout=10,trust_env=False) as client:
        login=client.post('http://sol:8011/sol/auth/login',json={'username':'asesor.bna','password':os.environ['SOL_INITIAL_PASSWORD']})
        assert login.status_code==200
        headers={'Authorization':'Bearer '+login.json()['token'],'X-Idempotency-Key':case['operation']}
        url='http://sol:8011/sol/applications/'+case['id']
        if mode=='core-outage':
            detail=client.get(url,headers=headers).json()
            conditions=detail['versiones'][-1]['expediente']['condiciones']
            fields=['id_cliente','monto_solicitado','moneda','plazo_meses','destino_credito','fecha_base','pago_doble','garantias']
            payload={key:conditions[key] for key in fields if key in conditions}
            assert client.post('http://sol:8011/sol/preview',headers=headers,json=payload).status_code==503
            assert client.get('http://captacion:8014/ready').status_code==503
            result={'case':'Caida COREDB propagada CAP y SOL por HTTP503','passed':True,'sol_http':503,'cap_http':503}
        elif mode=='authorization':
            supervisor=client.post('http://sol:8011/sol/auth/login',json={'username':'supervisor.bna','password':os.environ['SOL_INITIAL_PASSWORD']})
            assert supervisor.status_code==200
            detail=client.get(url,headers=headers).json()
            conditions=detail['versiones'][-1]['expediente']['condiciones']
            fields=['id_cliente','monto_solicitado','moneda','plazo_meses','destino_credito','fecha_base','pago_doble','garantias']
            payload={key:conditions[key] for key in fields if key in conditions}
            assert client.post('http://sol:8011/sol/preview',headers={'Authorization':'Bearer '+supervisor.json()['token']},json=payload).status_code==403
            assert client.post('http://sol:8011/sol/integrations/evaluation-results',headers={
                'Authorization':'Bearer '+os.environ['SOL_EVA_CALLBACK_TOKEN'], 'X-Idempotency-Key':'invalid-json-op',
                'X-Correlation-ID':'invalid-json-corr'},json={}).status_code==422
            result={'case':'Autorizacion supervisor403 y callback esquema422 por HTTP real','passed':True,'forbidden':403,'invalid_callback':422}
        elif mode=='outage':
            try: client.get('http://evaluacion:8015/salud')
            except httpx.TransportError: pass
            else:raise AssertionError('EVA no esta detenida')
            r=client.post(url+'/send',headers=headers,json={'revision':case['revision']})
            assert r.status_code==202
            end=time.monotonic()+60
            while time.monotonic()<end:
                with engine.connect() as c:
                    row=c.execute(text('SELECT status,attempts,last_error FROM mvp_sol_envio WHERE operation=:op'),{'op':case['operation']}).mappings().one()
                if row['attempts']>=1 and row['last_error']:break
                time.sleep(1)
            assert row['status']=='PENDIENTE' and row['attempts']>=1 and row['last_error']
            result={'case':'EVA real detenida: reserva202 y reintento durable','passed':True,'attempts':row['attempts']}
        else:
            end=time.monotonic()+100
            while time.monotonic()<end:
                d=client.get(url,headers=headers).json()
                if d['estado']=='EN_EVALUACION':break
                time.sleep(1)
            assert d['estado']=='EN_EVALUACION'
            with engine.connect() as c:
                row=c.execute(text('SELECT status,attempts,evaluation_id FROM mvp_sol_envio WHERE operation=:op'),{'op':case['operation']}).mappings().one()
            assert row['status']=='CONFIRMADO' and row['attempts']>=2
            acuse=client.get('http://evaluacion:8015/eva/operations/'+case['operation'],headers={'Authorization':'Bearer '+os.environ['SOL_EVA_TOKEN']})
            assert acuse.status_code==200 and acuse.json()['idSolicitud']==case['id']
            result={'case':'EVA reiniciada: recuperacion con misma operacion','passed':True,'attempts':row['attempts'],
                    'idSolicitud':case['id'],'idOperacion':case['operation'],'idEvaluacion':row['evaluation_id']}
        print(json.dumps(result))
    engine.dispose()


if __name__=='__main__':main()
