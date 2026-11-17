"""Laboratorio académico real HTTP CAP/COREDB/SOL/EVA. Secretos y fuentes fuera de Git."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request
import urllib.error
from prepare import prepare, HERE, REPO
from patch_eva import apply, apply_fixture


def envfile(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if line and not line.startswith('#'))


def write_env(path, values):
    path.write_text(''.join(f'{k}={v}\n' for k, v in values.items()))
    path.chmod(0o600)


def command(args, *, env=None, input=None):
    result = subprocess.run(args, env=env, input=input, capture_output=True, text=True)
    if result.returncode:
        # Docker output may contain secrets. Retain private diagnostics, never echo raw output.
        diagnostic=Path('/tmp/bna-integracion-private-last-error.log')
        diagnostic.write_text(result.stdout+'\n'+result.stderr)
        diagnostic.chmod(0o600)
        raise RuntimeError('Comando falló: '+args[0]+' (salida '+str(result.returncode)+'); diagnostico privado en /tmp/bna-integracion-private-last-error.log')
    return result.stdout


def compose(root, *args):
    control = envfile(root/'runtime/control.env')
    environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), **control}
    return command(['docker', 'compose', '--project-directory', str(HERE), '--env-file',
                    str(root/'runtime/control.env'), '-f', str(HERE/'compose.yaml'),
                    '-f', str(HERE/'compose.audit-sim.yaml'), '-f', str(root/'flow.json'),
                    '--profile', '*', *args], env=environment)


def setup(parent, port):
    root = prepare('final'+secrets.token_hex(4), parent)
    patch = apply(root/'sources/api/EVALUACION/envios.py')
    for name in ['flow_http.py', 'test_callback_ack.py', 'failure_http.py', 'test_ack_tcp.py']:
        (root/'sources/api/lab'/name).write_bytes((HERE/name).read_bytes())
    # Reuse original tests from pinned refs; no institutional SQL fixtures are executed.
    from prepare import git, CAP, EVA
    for ref, module in [(git('rev-parse', 'HEAD').decode().strip(), 'COREDB'), (CAP, 'CAPTACION'), (EVA, 'EVALUACION')]:
        for name in git('ls-tree', '-r', '--name-only', ref, 'backend/'+module+'/tests').decode().splitlines():
            if name.endswith('.py'):
                dest = root/'sources/api'/name.removeprefix('backend/')
                dest.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                dest.write_bytes(git('show', ref+':'+name))
    fixture_patch=apply_fixture(root/'sources/api/EVALUACION/tests/ayudas.py')
    for src in (REPO/'backend/SOL/tests').glob('*.py'):
        dest=root/'sources/api/SOL/tests'/src.name
        dest.parent.mkdir(exist_ok=True, mode=0o755)
        dest.write_bytes(src.read_bytes())
    for name in ['openapi.json']:
        (root/'sources/api/COREDB'/name).write_bytes(git('show', 'HEAD:backend/COREDB/'+name))
    for d in (root/'sources').rglob('*'):
        if d.is_dir(): d.chmod(0o755)
        elif d.is_file(): d.chmod(0o644)
    rt=root/'runtime'
    sol, cap, eva = [envfile(rt/(p+'.env')) for p in ['sol','cap','eva']]
    eva['EVALUACION_SOL_URL']='http://sol:8011'
    write_env(rt/'eva.env',eva)
    control=envfile(rt/'control.env')
    control.update(LAB_ALLOW_DDL='YES_ISOLATED_LAB', LAB_AUDIT_SIM_AUTHORIZATION='AUTHORIZED_ACADEMIC_ONLY')
    write_env(rt/'control.env', control)
    runner={**sol, **cap, **eva,
            'BNA_ADMIN_PASSWORD': envfile(rt/'coredb-init.env')['CORE_DB_ADMIN_INICIAL_PASSWORD'],
            'SOL_INITIAL_PASSWORD': envfile(rt/'sol-init.env')['SOL_INITIAL_PASSWORD']}
    write_env(rt/'runner.env',runner)
    services={'mysql-core':{'healthcheck':{'test':['CMD-SHELL',
        'MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "CALL core.verificar_configuracion()" >/dev/null 2>&1']}},
        'mysql-modulos':{'healthcheck':{'test':['CMD-SHELL',
        'MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT 1" >/dev/null 2>&1']}}}
    for i,name in enumerate(['coredb','captacion','sol','evaluacion']):
        internal={'coredb':8012,'captacion':8014,'sol':8011,'evaluacion':8015}[name]
        nets=['integration','web']+(['core-data'] if name=='coredb' else ['module-data'])
        services[name]={'ports':[f'127.0.0.1:{port+i}:{internal}'], 'networks':nets}
    services['flow-runner']={'image':f"bna-sol-cap-eva-lab-{control['LAB_RUN_ID']}/providers:lab",
        'env_file':[str(rt/'runner.env')], 'environment':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'/app'},
        'command':['python','lab/flow_http.py'], 'networks':['integration','module-data'],
        'read_only':True, 'tmpfs':['/tmp'], 'cap_drop':['ALL'], 'security_opt':['no-new-privileges:true']}
    (root/'flow.json').write_text(json.dumps({'services':services,'networks':{'web':{'internal':False}}},indent=2)+'\n')
    manifest=json.loads((root/'manifest.json').read_text())
    manifest['patches']=[patch,fixture_patch]
    manifest['files']=[{'path':str(p.relative_to(root)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                       for p in sorted((root/'sources').rglob('*')) if p.is_file()]
    manifest['ports']={name:port+i for i,name in enumerate(['coredb','captacion','sol','evaluacion'])}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return root


def verify(root):
    if root.is_symlink() or root==REPO or REPO in root.parents or root.stat().st_mode & 0o077:
        raise RuntimeError('Directorio externo inseguro.')
    m=json.loads((root/'manifest.json').read_text())
    for f in m['files']:
        p=root/f['path']
        if not p.resolve().is_relative_to(root) or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
            raise RuntimeError('Fuente alterada desde captura.')
    config=json.loads(compose(root,'config','--format','json'))
    project='bna-sol-cap-eva-lab-'+m['run_id']
    assert config['name']==project
    for name,s in config['services'].items():
        assert not any(s.get(k) for k in ['privileged','network_mode','container_name','devices','extra_hosts'])
        for v in s.get('volumes',[]): assert v['type']=='volume' and v['source']=='cap-secrets'
        if name.startswith('mysql-'): assert not s.get('ports') and 'web' not in s['networks']
        for p in s.get('ports',[]): assert p['host_ip']=='127.0.0.1'
        for key in ['MYSQL_ROOT_PASSWORD','AUX_DB_ROOT_PASSWORD']:
            if name in ['sol','captacion','evaluacion','coredb','flow-runner']: assert key not in s.get('environment',{})
    assert config['services']['evaluacion']['environment']['EVALUACION_SOL_URL']=='http://sol:8011'
    assert not config['volumes']['cap-secrets'].get('external')
    for net in config['networks'].values(): assert not net.get('external') and net['name'].startswith(project+'_')
    # Only local Docker daemon; reject a remote context before writes.
    if os.environ.get('DOCKER_HOST') and not os.environ['DOCKER_HOST'].startswith('unix://'):
        raise RuntimeError('Docker remoto no permitido.')
    context=command(['docker','context','show']).strip()
    info=json.loads(command(['docker','context','inspect',context]))[0]
    assert info['Endpoints']['docker']['Host'].startswith('unix://')
    return m


def frontend(root,manifest):
    """Copia saneada de frontend existente. Ninguna edición de UI ni dotenv."""
    import shutil
    dest=root/'sources/frontend'
    if not dest.exists():
        dest.mkdir(mode=0o755)
        for base,dirs,files in os.walk(REPO/'frontend'):
            dirs[:]=[d for d in dirs if d not in {'node_modules','.next','.git','coverage'} and not d.startswith('.')]
            relative=Path(base).relative_to(REPO/'frontend')
            target=dest/relative;target.mkdir(exist_ok=True,parents=True,mode=0o755)
            for name in files:
                if name.startswith('.env') or name.endswith(('.tsbuildinfo','.log')):continue
                src=Path(base)/name
                if src.is_symlink():raise RuntimeError('Symlink frontend inesperado.')
                shutil.copyfile(src,target/name);(target/name).chmod(0o644)
        (dest/'Dockerfile').write_bytes((HERE.parent/'demo/Dockerfile.frontend').read_bytes())
        (dest/'Dockerfile').chmod(0o644)
    port=manifest['ports']['coredb']+4
    flow=json.loads((root/'flow.json').read_text())
    flow['services']['frontend']={'image':'bna-sol-cap-eva-lab-'+manifest['run_id']+'/frontend:lab',
        'build':{'context':str(dest)},'environment':{'SOL_GATEWAY_URL':'http://sol:8011/sol',
        'SOL_PUBLIC_ORIGIN':f'http://127.0.0.1:{port}','NEXT_TELEMETRY_DISABLED':'1'},
        'ports':[f'127.0.0.1:{port}:3000'],'networks':['web'],'cap_drop':['ALL'],
        'security_opt':['no-new-privileges:true'],'healthcheck':{'test':['CMD','wget','-q','--spider','http://127.0.0.1:3000/'],
        'interval':'5s','timeout':'5s','retries':30},'restart':'no'}
    (root/'flow.json').write_text(json.dumps(flow,indent=2)+'\n')
    manifest['frontend_port']=port
    manifest['files']=[{'path':str(p.relative_to(root)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                       for p in sorted((root/'sources').rglob('*')) if p.is_file()]
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    verify(root)
    print('Construyendo Next.js original para laboratorio...',flush=True)
    compose(root,'build','frontend')
    compose(root,'up','-d','--no-deps','--wait','frontend')
    # Cookie session and REAL policy through existing Next proxy, without exposing tokens.
    import http.cookiejar
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    origin=f'http://127.0.0.1:{port}'
    password=envfile(root/'runtime/sol-init.env')['SOL_INITIAL_PASSWORD']
    req=urllib.request.Request(origin+'/api/solicitud-credito/auth/login',
        data=json.dumps({'username':'asesor.bna','password':password}).encode(),
        headers={'Content-Type':'application/json','Origin':origin})
    with opener.open(req,timeout=10) as response:
        result=json.load(response)
        assert 'token' not in result and 'httponly' in response.headers.get('set-cookie','').lower()
    with opener.open(origin+'/api/solicitud-credito/policy',timeout=10) as response:assert json.load(response)['integracion']=='REAL'
    with opener.open(origin+'/api/solicitud-credito/applications?limit=100',timeout=10) as response:
        assert json.load(response)['total']>=3
    print('Next.js REAL proxy/cookie HttpOnly/bandeja comprobados:',origin+'/solicitud-credito')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',choices=['up','test','status','stop','regressions','frontend','refresh-tools','eva-regressions','frontend-regressions','dependency-checks','verify-running'],default='up')
    parser.add_argument('--state',type=Path,default=Path('/tmp/bna-integracion-final-state.json'))
    parser.add_argument('--port',type=int,default=18120)
    parser.add_argument('--suite',default='',help='Suites de regresion separadas por coma; vacio=todas')
    args=parser.parse_args()
    os.umask(0o077)
    if args.state.is_symlink() or args.state.resolve().is_relative_to(REPO): raise RuntimeError('Estado debe ser externo y privado.')
    if args.state.exists():
        state=json.loads(args.state.read_text())
        root=Path(state['root'])
        if state.get('stopped') and args.action=='up':
            previous=str(root)
            port=json.loads((root/'manifest.json').read_text())['ports']['coredb']
            root=setup(Path('/tmp'),port)
            args.state.write_text(json.dumps({'root':str(root),'previous':previous}))
            args.state.chmod(0o600)
        elif state.get('stopped') and args.action not in {'status','stop'}:
            raise RuntimeError('Laboratorio detenido; ejecutar up para nueva instancia efimera.')
    else:
        if args.action!='up': raise RuntimeError('Primero ejecutar up.')
        if command(['git','branch','--show-current']).strip()!='feature/sol-integracion-cap-eva': raise RuntimeError('Rama incorrecta.')
        root=setup(Path('/tmp'), args.port)
        args.state.write_text(json.dumps({'root':str(root)}))
        args.state.chmod(0o600)
    manifest=verify(root)
    print('Laboratorio privado:',root,flush=True)
    if args.action=='stop':
        compose(root,'stop')
        args.state.write_text(json.dumps({'root':str(root),'stopped':True}))
        args.state.chmod(0o600)
        print('Detenido solo este proyecto; MySQL tmpfs pierde datos. El siguiente up crea una instancia limpia y conserva la captura anterior.'); return
    if args.action=='status':
        print(compose(root,'ps')); return
    if args.action=='verify-running':
        config=json.loads(compose(root,'config','--format','json'))
        ids=compose(root,'ps','--all','-q').split()
        inspected=json.loads(command(['docker','inspect',*ids]))
        checks=[]
        for container in inspected:
            assert container['Config']['Labels']['com.docker.compose.project']==config['name']
            service=container['Config']['Labels']['com.docker.compose.service']
            if service in ['mysql-core','mysql-modulos']:
                assert container['State']['Running'] and not container['HostConfig'].get('PortBindings')
                assert '/var/lib/mysql' in container['HostConfig']['Tmpfs']
                assert all('web' not in n for n in container['NetworkSettings']['Networks'])
            if service in ['coredb','captacion','sol','evaluacion','frontend']:
                assert container['State']['Running']
                assert all(p['HostIp']=='127.0.0.1' for ports in container['NetworkSettings']['Ports'].values() if ports for p in ports)
            checks.append({'service':service,'running':container['State']['Running']})
        private_values=set()
        import re
        for path in (root/'runtime').glob('*.env'):
            assert path.stat().st_mode & 0o077==0
            private_values.update(re.findall(r'[a-f0-9]{64}',path.read_text()))
        logs=compose(root,'logs','--no-color','--no-log-prefix','--tail','1000','coredb','captacion','sol','evaluacion','audit-lab')
        assert not any(secret in logs for secret in private_values)
        assert not re.search(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',logs)
        core_count=compose(root,'exec','-T','mysql-core','sh','-ec',
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT COUNT(*) FROM clientes.cliente"')
        assert int(core_count.strip())>=2
        report=json.loads((root/'evidence.json').read_text())
        report['runtime_verification']={'services':checks,'coredb_mysql_clients':int(core_count.strip()),
            'mysql_tmpfs_no_ports':True,'apis_loopback':True,'runtime_private':True,
            'logs_no_runtime_secrets_or_jwt':True}
        (root/'evidence.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(report['runtime_verification'],ensure_ascii=False));return
    if args.action=='dependency-checks':
        report=json.loads((root/'evidence.json').read_text())
        fault_env='LAB_RECOVERY_JSON='+json.dumps(report['recovery'])
        auth=json.loads(compose(root,'run','--rm','--no-deps','-T','-e',fault_env,'flow-runner','python','lab/failure_http.py','authorization'))
        compose(root,'stop','coredb')
        try:failure=json.loads(compose(root,'run','--rm','--no-deps','-T','-e',fault_env,'flow-runner','python','lab/failure_http.py','core-outage'))
        finally:compose(root,'up','-d','--no-deps','--wait','coredb')
        report['dependency_checks']=[auth,failure]
        (root/'evidence.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(report['dependency_checks'],ensure_ascii=False));return
    if args.action=='eva-regressions':
        secret=secrets.token_hex(32)
        write_env(root/'runtime/mysql-tests.env',{'MYSQL_ROOT_PASSWORD':secret,'MYSQL_ROOT_HOST':'%'})
        write_env(root/'runtime/eva-tests.env',{'EVALUACION_TEST_MYSQL':'mysql+pymysql://root:'+secret+'@mysql-tests:3306',
                  'SOL_INTEGRATION_MODE':'SIMULADO','PYTHONPATH':'/app','PYTHONDONTWRITEBYTECODE':'1'})
        flow=json.loads((root/'flow.json').read_text())
        flow['networks']['test-data']={'internal':True}
        flow['services']['mysql-tests']={'image':json.loads(compose(root,'config','--format','json'))['services']['mysql-modulos']['image'],
            'env_file':[str(root/'runtime/mysql-tests.env')],'networks':['test-data'],'tmpfs':['/var/lib/mysql','/var/run/mysqld'],
            'healthcheck':{'test':['CMD-SHELL','MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT 1" >/dev/null 2>&1'],
            'interval':'3s','timeout':'3s','retries':60},'restart':'no'}
        flow['services']['eva-tests']={'image':'bna-sol-cap-eva-lab-'+manifest['run_id']+'/providers:lab',
            'env_file':[str(root/'runtime/eva-tests.env')],'networks':['test-data'],'read_only':True,'tmpfs':['/tmp'],
            'command':['python','-m','pytest','-p','no:cacheprovider','-q','-o','addopts=','EVALUACION/tests']}
        (root/'flow.json').write_text(json.dumps(flow,indent=2)+'\n');verify(root)
        compose(root,'up','-d','--wait','mysql-tests')
        try:output=compose(root,'run','--rm','--no-deps','-T','eva-tests')
        finally:compose(root,'stop','mysql-tests')
        results=json.loads((root/'regressions.json').read_text()) if (root/'regressions.json').exists() else {}
        results['EVA_MySQL']={'exit':0,'output':output};(root/'regressions.json').write_text(json.dumps(results,indent=2))
        print(output[-2500:]);return
    if args.action=='frontend-regressions':
        dest=root/'sources/frontend'
        if not dest.exists():frontend(root,manifest)
        original=(HERE.parent/'demo/Dockerfile.frontend').read_text()
        tests=original.split('RUN npm run build')[0]+'''\nCMD ["sh", "-ec", "npm run lint && npx tsc --noEmit && npm test && npm run build"]\n'''
        (dest/'Dockerfile.regressions').write_text(tests);(dest/'Dockerfile.regressions').chmod(0o644)
        manifest['files']=[{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in sorted((root/'sources').rglob('*')) if p.is_file()]
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        image='bna-sol-cap-eva-lab-'+manifest['run_id']+'/frontend-tests:lab'
        command(['docker','build','-f',str(dest/'Dockerfile.regressions'),'-t',image,str(dest)])
        output=command(['docker','run','--rm','--network','none',image])
        results=json.loads((root/'regressions.json').read_text()) if (root/'regressions.json').exists() else {}
        results['frontend']={'exit':0,'output':output};(root/'regressions.json').write_text(json.dumps(results,indent=2))
        print(output[-3000:]);return
    if args.action=='refresh-tools':
        fixture=root/'sources/api/EVALUACION/tests/ayudas.py'
        if 'json={"recibido": estado == 200})' in fixture.read_text():
            manifest['patches'].append(apply_fixture(fixture))
        for name in ['flow_http.py','failure_http.py','test_callback_ack.py','test_ack_tcp.py']:
            dest=root/'sources/api/lab'/name
            dest.write_bytes((HERE/name).read_bytes());dest.chmod(0o644)
        manifest['files']=[{'path':str(p.relative_to(root)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in sorted((root/'sources').rglob('*')) if p.is_file()]
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        verify(root);compose(root,'build','captacion');print('Herramientas de pruebas actualizadas; aplicaciones originales preservadas.');return
    if args.action=='frontend':
        frontend(root,manifest);return
    if args.action=='regressions':
        results=json.loads((root/'regressions.json').read_text()) if (root/'regressions.json').exists() else {}
        suites={
            'SOL':['python','-m','pytest','-p','no:cacheprovider','-q','-o','addopts=','SOL/tests'],
            'COREDB':['python','-m','pytest','-p','no:cacheprovider','-q','-o','addopts=','COREDB/tests/test_unidad.py','COREDB/tests/test_autenticacion.py'],
            'CAP_SOL':['python','-m','pytest','-p','no:cacheprovider','-q','-o','addopts=','CAPTACION/tests/test_contrato_sol.py'],
            'CAP':['python','-m','pytest','-p','no:cacheprovider','-q','-o','addopts=','CAPTACION/tests'],
            'EVA_motor':['python','-m','pytest','-p','no:cacheprovider','-q','-o','addopts=','EVALUACION/tests/test_motor.py'],
            'EVA_ack_unit':['python','-m','pytest','-p','no:cacheprovider','-q','lab/test_callback_ack.py'],
            'EVA_ack_TCP':['python','-m','pytest','-p','no:cacheprovider','-q','lab/test_ack_tcp.py'],
        }
        for name,cmd in suites.items():
            if args.suite and name not in args.suite.split(','):continue
            if name in {'COREDB','CAP_SOL'}:
                output=command(['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp',
                    '-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/app',
                    'bna-sol-cap-eva-lab-'+manifest['run_id']+('/coredb:lab' if name=='COREDB' else '/sol:lab'),*cmd])
            else:
                output=compose(root,'run','--rm','--no-deps','-T','-e','SOL_INTEGRATION_MODE=SIMULADO','-e','SOL_WORKER_SECONDS=0',
                           '-e','PYTHONPATH=/app','flow-runner',*cmd)
            results[name]={'exit':0,'output':output}
            print(name,output[-1000:],flush=True)
            (root/'regressions.json').write_text(json.dumps(results,indent=2))
        return
    if args.action=='up':
        print('Construyendo aplicaciones originales y parche EVA aislado...',flush=True)
        for service in ['mysql-core','coredb','captacion','sol']:
            compose(root,'build',service)
        print('Inicializando únicamente MySQL efímeros propios y auditoría SIMULADA...',flush=True)
        compose(root,'up','-d','--wait','--wait-timeout','240','coredb','captacion','sol','evaluacion','audit-lab')
    print('Ejecutando REAL HTTP CAP→COREDB→CAP→SOL→EVA→SOL...',flush=True)
    evidence=compose(root,'run','--rm','--no-deps','-T','flow-runner')
    report=json.loads(evidence)
    (root/'evidence.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    assert report['status']=='passed'
    failure_env='LAB_RECOVERY_JSON='+json.dumps(report['recovery'])
    compose(root,'stop','evaluacion')
    try:
        failure=json.loads(compose(root,'run','--rm','--no-deps','-T','-e',failure_env,'flow-runner','python','lab/failure_http.py','outage'))
    finally:
        compose(root,'up','-d','--no-deps','--wait','evaluacion')
    recovery=json.loads(compose(root,'run','--rm','--no-deps','-T','-e',failure_env,'flow-runner','python','lab/failure_http.py','recovery'))
    report['fault_checks']=[failure,recovery]
    (root/'evidence.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    for name,port in manifest['ports'].items():
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/docs',timeout=10) as r: assert r.status==200
        print(f'Swagger {name}: http://127.0.0.1:{port}/docs')
    frontend(root,manifest)
    print(json.dumps({'status':report['status'],'checks':len(report['checks']),
                      'scenarios':report['scenarios'],'fault_checks':report['fault_checks']},ensure_ascii=False,indent=2))
    print('REAL HTTP y MySQL: COREDB/CAP/SOL/EVA. SIMULADO: verificadores CAP y auditoría académica.')
    print('Evidencia sin secretos:',root/'evidence.json')


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('ERROR:',str(exc) if isinstance(exc,(RuntimeError,AssertionError)) else type(exc).__name__,file=sys.stderr)
        sys.exit(1)
