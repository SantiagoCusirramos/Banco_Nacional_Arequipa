"""Pruebas TCP entre aplicaciones originales. SQL limitado a bases propias del laboratorio."""
import json
import os
import secrets
import socket
import sys
import time
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from SOL.clock import business_today

BASE={'core':'http://coredb:8012','cap':'http://captacion:8014','sol':'http://sol:8011','eva':'http://evaluacion:8015'}


def main():
    rows, scenarios=[],[]
    client=httpx.Client(timeout=15,trust_env=False,follow_redirects=False)
    engines={}
    for name,prefix in [('sol','SOL'),('cap','CAP')]:
        assert os.environ[prefix+'_DB_HOST']=='mysql-modulos'
        db=os.environ[prefix+'_DB_NAME']
        assert db.startswith('bna_sol_mvp_final' if name=='sol' else 'bna_captacion_final')
        engines[name]=create_engine(URL.create('mysql+pymysql',username=os.environ[prefix+'_DB_USER'],
            password=os.environ[prefix+'_DB_PASSWORD'],host='mysql-modulos',database=db),hide_parameters=True)
    assert '@mysql-modulos:3306/bna_evaluacion_final' in os.environ['EVALUACION_DATABASE_URL']
    engines['eva']=create_engine(os.environ['EVALUACION_DATABASE_URL'],hide_parameters=True)
    def sql(name,query,**params):
        with engines[name].begin() as conn:
            result=conn.execute(text(query),params)
            return result.mappings().all() if result.returns_rows else []
    def check(label,condition):
        rows.append({'case':label,'passed':bool(condition)})
        assert condition,label
    def call(label,method,target,path,expected=200,headers=None,**kwargs):
        r=client.request(method,BASE[target]+path,headers=headers,**kwargs)
        rows.append({'case':label,'method':method,'service':target,'path':path.split('?')[0],
                     'http':r.status_code,'expected':expected,'passed':r.status_code==expected})
        if r.status_code!=expected: raise RuntimeError(label+': HTTP '+str(r.status_code))
        return r.json()
    def wait(label,func,predicate):
        end=time.monotonic()+100
        while time.monotonic()<end:
            result=func()
            if predicate(result):
                check(label,True); return result
            time.sleep(1)
        raise RuntimeError('Timeout: '+label)
    def token(value): return {'Authorization':'Bearer '+value}
    try:
        for host,port,path,target in [('coredb',8012,'/coredb/salud','core'),('captacion',8014,'/ready','cap'),
                                      ('sol',8011,'/ready','sol'),('evaluacion',8015,'/salud','eva')]:
            socket.getaddrinfo(host,port)
            call('salud '+host,'GET',target,path)
            spec=call('OpenAPI '+host,'GET',target,'/openapi.json')
            check('Swagger '+host,client.get(BASE[target]+'/docs').status_code==200 and bool(spec['paths']))
        admin=call('login COREDB','POST','core','/coredb/auth/login',json={'username':'admin-lab','password':os.environ['BNA_ADMIN_PASSWORD']})
        human=token(admin['access_token'])
        # Persona analista real creada por API COREDB, nunca rol inventado en headers.
        analyst_name='analista-'+secrets.token_hex(4)
        analyst_password=secrets.token_hex(20)
        call('crear analista autorizado','POST','core','/coredb/usuarios',201,headers=human,json={
            'username':analyst_name,'nombre':'Analista sintetico laboratorio','password':analyst_password,'rol':'ANALISTA'})
        analyst=token(call('login analista EVA','POST','core','/coredb/auth/login',json={
            'username':analyst_name,'password':analyst_password})['access_token'])
        advisor=token(call('login asesor SOL','POST','sol','/sol/auth/login',json={
            'username':'asesor.bna','password':os.environ['SOL_INITIAL_PASSWORD']})['token'])
        own=token(os.environ['CAP_SOL_TOKEN'])
        eva_token=token(os.environ['EVALUACION_TOKEN_SOL'])
        callback_token=token(os.environ['SOL_EVA_CALLBACK_TOKEN'])
        call('token incorrecto CAP','GET','cap','/cap/references',401,headers=token('invalid'))
        call('token incorrecto EVA','GET','eva','/eva/operations/unknown-lab',401,headers=own)
        call('COREDB sin token','GET','core','/coredb/auth/me',401)
        def capture():
            p='/api/v1/captacion'
            def cap(label,method,path,expected=200,**kw):
                return call(label,method,'cap',p+path,expected,headers=human,**kw)['data']
            doc=str(7100000+secrets.randbelow(800000))+'0'
            s=cap('CAP registrar solicitante','POST','/solicitantes',201,json={
                'tipo_documento':'DNI','numero_documento':doc,'nombres':'Persona Sintetica','apellido_paterno':'Laboratorio',
                'celular':'9'+doc,'correo':'lab'+secrets.token_hex(8)+'@example.invalid'})['solicitante']
            case=cap('CAP abrir caso','POST','/casos',201,json={'id_solicitante':s['id_solicitante'],'canal':'WEB'})
            path='/casos/'+case['id_caso']
            cap('CAP consentimientos','POST',path+'/consentimientos',201,json={'consentimientos':[
                {'tipo':t,'aceptado':True} for t in ['TRATAMIENTO_DATOS','CONSULTA_BUROS','TERMINOS']]})
            code=cap('CAP OTP externo SIMULADO','POST',path+'/otp',201,json={'canal':'SMS'})['codigo_simulado']
            cap('CAP verificar OTP','POST',path+'/otp/verificar',json={'canal':'SMS','codigo':code})
            cap('CAP identidad externa SIMULADA','POST',path+'/validaciones',201,json={'tipos':['RENIEC','LISTAS_NEGRAS','PEP']})
            cap('CAP central externa SIMULADA','POST',path+'/consultas-riesgo',201,json={'central':'SBS'})
            cap('CAP perfil','POST',path+'/perfil',201)
            case=cap('CAP habilitar via COREDB','POST',path+'/habilitar')
            ref=call('CAP referencia','GET','cap','/cap/references/'+case['cod_cliente'],headers=own)
            core=call('COREDB confirma cliente','GET','core','/coredb/clientes/'+ref['id_cliente'],headers=human)
            check('identidad COREDB CAP',core['cod_cliente']==ref['id_cliente'] and core['estado_cliente']=='ACTIVO')
            return ref,case['id_caso']
        ref,case_id=capture()
        found=call('SOL consulta CAP HTTP','GET','sol','/sol/clients',headers=advisor,params={'search':ref['id_cliente']})
        # CAP search accepts name/document, not guaranteed code. Re-query synthetic name.
        found=call('SOL busca nombre CAP HTTP','GET','sol','/sol/clients',headers=advisor,params={'search':'Persona Sintetica'})
        check('SOL encuentra referencia COREDB',any(r['id_cliente']==ref['id_cliente'] for r in found))
        payload={'id_cliente':ref['id_cliente'],'monto_solicitado':'15000.00','moneda':'PEN','plazo_meses':12,
                 'destino_credito':'Integracion academica sintetica','fecha_base':business_today().isoformat(),
                 'garantias':[{'tipo_garantia':'VEHICULAR','descripcion':'Vehiculo sintetico laboratorio','valor_tasacion':'20000.00'}],
                 'fiadores':[],'pago_doble':False}
        preview=call('SOL preview calendario','POST','sol','/sol/preview',headers=advisor,json=payload)
        check('calendario Decimal saldo final cero',Decimal(preview['calendario']['cuotas'][-1]['saldo_final'])==0)
        call('SOL cliente inexistente','POST','sol','/sol/preview',422,headers=advisor,json={**payload,'id_cliente':'NOEXISTE'})
        def application(decision,detail=None):
            if detail is None:
                detail=call('SOL crear BORRADOR '+decision,'POST','sol','/sol/applications',201,headers=advisor,json=payload)
                detail=call('SOL editar BORRADOR','PUT','sol','/sol/applications/'+detail['id'],headers=advisor,
                            json={**payload,'revision':detail['revision']})
            app=detail['id']; path='/sol/applications/'+app
            op=str(uuid4()); corr=str(uuid4())
            send_headers={**advisor,'X-Idempotency-Key':op,'X-Correlation-ID':corr}
            rev=detail['revision']
            call('SOL reserva durable202','POST','sol',path+'/send',202,headers=send_headers,json={'revision':rev})
            detail=wait('SOL acuse EVA confirmado',lambda:client.get(BASE['sol']+path,headers=advisor).json(),lambda d:d.get('estado')=='EN_EVALUACION')
            receipt=call('EVA consultar operacion','GET','eva','/eva/operations/'+op,headers=eva_token)
            check('acuse IDs exactos',receipt['idSolicitud']==app and receipt['versionSolicitud']==detail['version'] and receipt['idOperacion']==op)
            envelope=sql('sol','SELECT payload FROM mvp_sol_envio WHERE operation=:op',op=op)[0]['payload']
            if isinstance(envelope,str): envelope=json.loads(envelope)
            call('SOL reenvio misma clave','POST','sol',path+'/send',headers=send_headers,json={'revision':rev})
            call('EVA repeticion mismo sobre','POST','eva','/eva/applications',headers={**eva_token,'X-Idempotency-Key':op},json=envelope)
            call('EVA misma operacion otro contenido','POST','eva','/eva/applications',409,headers={**eva_token,'X-Idempotency-Key':op},json={**envelope,'actorEnvio':'otro-actor'})
            call('SOL editar version congelada','PUT','sol',path,409,headers=advisor,json={**payload,'revision':detail['revision']})
            evpath='/eva/v1/evaluaciones/'+receipt['idEvaluacion']
            ev=call('EVA expediente persistido','GET','eva',evpath,headers=analyst)
            check('EVA MySQL expediente unico',len(sql('eva','SELECT id_operacion FROM eva_expediente WHERE id_operacion=:op',op=op))==1)
            # 15000 / (0.35*4200*12) = 0.8503 → EN_REVISION, decisión explícita de analista.
            ev=call('EVA situacion financiera sintetica','POST','eva',evpath+'/situacion-financiera',headers=analyst,
                    json={'ingresoMensual':'4200.00','deudaMensual':'0.00','riesgo':'BUENO','verificada':True,'version':ev['version']})
            check('EVA exige decision analista',ev['estado']=='EN_REVISION')
            ev=call('EVA decision '+decision,'POST','eva',evpath+'/decision',headers=analyst,
                    json={'decision':decision,'observaciones':'Decision academica sintetica para verificar integracion HTTP.','version':ev['version']})
            desired={'APROBADO':'APROBADA','OBSERVADO':'OBSERVADA','RECHAZADO':'RECHAZADA'}[decision]
            detail=wait('Callback EVA SOL '+desired,lambda:client.get(BASE['sol']+path,headers=advisor).json(),lambda d:d.get('estado')==desired)
            ev=wait('EVA acuse semantico ENTREGADO',lambda:client.get(BASE['eva']+evpath,headers=analyst).json(),lambda d:(d.get('envioSol') or {}).get('estado')=='ENTREGADO')
            result=sql('eva','SELECT contenido FROM eva_envio WHERE id_evaluacion=:ev',ev=receipt['idEvaluacion'])[0]['contenido']
            if isinstance(result,str):result=json.loads(result)
            cb={**callback_token,'X-Idempotency-Key':result['idOperacion'],'X-Correlation-ID':result['idCorrelacion']}
            ack=call('Callback repetido HTTP','POST','sol','/sol/integrations/evaluation-results',headers=cb,json=result)
            check('Callback duplicado reconocido',ack.get('recibido') is True and ack.get('reintento_reconocido') is True)
            call('Callback misma operacion cuerpo distinto','POST','sol','/sol/integrations/evaluation-results',409,headers=cb,json={**result,'observaciones':'Otro contenido incompatible'})
            wrong={**result,'idOperacion':str(uuid4()),'versionSolicitud':999}
            call('Callback version erronea','POST','sol','/sol/integrations/evaluation-results',409,
                 headers={**cb,'X-Idempotency-Key':wrong['idOperacion']},json=wrong)
            call('Callback token incorrecto','POST','sol','/sol/integrations/evaluation-results',401,
                 headers={**cb,'Authorization':'Bearer incorrecto'},json=result)
            check('Outcome SQL unico',len(sql('sol','SELECT operation FROM mvp_sol_resultado WHERE operation=:op',op=result['idOperacion']))==1)
            state=sql('sol','SELECT state,current_version FROM mvp_sol_expediente WHERE id=:id',id=app)[0]
            check('MySQL SOL estado y version',state['state']==desired and state['current_version']==detail['version'])
            scenarios.append({'id_cliente':ref['id_cliente'],'id_caso':case_id,'idSolicitud':app,'versionSolicitud':detail['version'],
                'idOperacionEnvio':op,'idOperacionResultado':result['idOperacion'],'idCorrelacion':corr,
                'idEvaluacion':receipt['idEvaluacion'],'ronda':receipt['ronda'],'estado':desired,'acuse':receipt['acuse']})
            return detail
        approved=application('APROBADO')
        observed=application('OBSERVADO')
        frozen=observed['versiones'][0]
        revised=call('SOL nueva version subsanacion','POST','sol','/sol/applications/'+observed['id']+'/revise',headers=advisor,json={'revision':observed['revision']})
        check('v1 inmutable y v2 creada',revised['version']==2 and revised['versiones'][0]==frozen)
        application('APROBADO',revised)
        application('RECHAZADO')
        # Inyectar solamente fecha de caso sintético CAP propio para comprobar el límite de vigencia por HTTP real.
        sql('cap','UPDATE cap_caso SET vigente_hasta=:date WHERE id_caso=:id',date=business_today()-timedelta(days=1),id=case_id)
        try: call('SOL rechaza referencia vencida HTTP','POST','sol','/sol/preview',422,headers=advisor,json=payload)
        finally: sql('cap','UPDATE cap_caso SET vigente_hasta=:date WHERE id_caso=:id',date=ref['vigente_hasta'],id=case_id)
        call('CAP revocar por API','POST','cap','/api/v1/captacion/casos/'+case_id+'/estado',headers=human,
             json={'accion':'REVOCAR','motivo':'Prueba sintetica de referencia revocada'})
        call('SOL rechaza cliente no habilitado HTTP','POST','sol','/sol/preview',422,headers=advisor,json=payload)
        recovery_ref,_=capture()
        recovery=call('SOL borrador recuperacion EVA','POST','sol','/sol/applications',201,headers=advisor,
                      json={**payload,'id_cliente':recovery_ref['id_cliente']})
        check('Eventos y outbox SOL reales',bool(sql('sol','SELECT id FROM mvp_sol_evento WHERE application_id=:id',id=approved['id'])) and
              bool(sql('sol','SELECT id FROM mvp_sol_auditoria_pendiente LIMIT 1')))
        report={'status':'passed','transport':'REAL HTTP entre procesos independientes','simulated':['verificadores externos CAP','auditoria academica'],
                'scenarios':scenarios,'recovery':{'id':recovery['id'],'revision':recovery['revision'],'operation':str(uuid4())},'checks':rows,'persistence':{'cap':'MySQL8.4','sol':'MySQL8.4','eva':'MySQL8.4','coredb':'cliente consultado por API COREDB'}}
    except Exception as exc:
        report={'status':'failed','failure':str(exc) if isinstance(exc,(AssertionError,RuntimeError)) else type(exc).__name__,'scenarios':scenarios,'checks':rows}
    finally:
        client.close()
        for engine in engines.values():engine.dispose()
    print(json.dumps(report,ensure_ascii=False))
    return int(report['status']!='passed')


if __name__=='__main__': sys.exit(main())
