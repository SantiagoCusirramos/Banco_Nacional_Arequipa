#!/usr/bin/env python3
"""One-command, localhost-only SOL presentation. No shared Compose or REAL providers."""
import argparse
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def run(command, *, capture=False, env=None):
    result = subprocess.run(command, env=env, capture_output=capture, text=True)
    if result.returncode:
        # Captured Compose config/inspect can contain passwords. Never echo it.
        raise RuntimeError('Comando fallido: '+command[0]+' (salida '+str(result.returncode)+').')
    return result.stdout if capture else ''


def write_private(path, values):
    path.write_text(''.join(f'{key}={value}\n' for key, value in values.items()))
    path.chmod(0o600)


def capture_sources(state):
    context = Path(tempfile.mkdtemp(prefix='fuentes-', dir=state))
    backend, frontend = context/'backend', context/'frontend'
    backend.mkdir(); frontend.mkdir()
    for source in (REPO/'backend/SOL').rglob('*'):
        relative = source.relative_to(REPO/'backend')
        if source.is_symlink():
            raise RuntimeError('Enlace simbolico inesperado en SOL.')
        if source.is_file() and 'tests' not in relative.parts and '__pycache__' not in relative.parts:
            if source.suffix == '.py' or relative.as_posix() == 'SOL/config/politica_demo.json':
                target = backend/relative;target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes());target.chmod(0o644)
    for source, target in [(REPO/'backend/requirements-sol.txt', backend/'requirements-sol.txt'),
                           (HERE/'Dockerfile.backend', backend/'Dockerfile'), (HERE/'seed_demo.py', backend/'seed_demo.py'),
                           (HERE/'Dockerfile.frontend', frontend/'Dockerfile')]:
        shutil.copyfile(source, target); target.chmod(0o644)
    paths = run(['git', '-C', str(REPO), 'ls-files', '-z', '--', 'frontend'], capture=True).split('\0')
    for name in paths:
        if not name:
            continue
        source = REPO/name
        if source.is_symlink():
            raise RuntimeError('Enlace simbolico inesperado en frontend.')
        if any(part.startswith('.env') or part in {'node_modules', '.next', '__pycache__'} for part in Path(name).parts):
            continue
        if not source.is_file():
            raise RuntimeError('Falta fuente frontend registrada en Git.')
        target = context/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes());target.chmod(0o644)
    for directory in [context, *context.rglob('*')]:
        if directory.is_dir():
            directory.chmod(0o755)
    manifest = {str(p.relative_to(context)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(context.rglob('*')) if p.is_file()}
    (context/'manifest.json').write_text(json.dumps(manifest, indent=2))
    return context


def settings(state, port=None, api_port=None):
    path = state/'settings.json'
    identifier = hashlib.sha256((str(REPO)+'|'+str(state)).encode()).hexdigest()[:10]
    if path.exists():
        cfg = json.loads(path.read_text())
        if cfg.get('id') != identifier or cfg.get('project') != 'bna-sol-demo-'+identifier:
            raise RuntimeError('El estado no pertenece a este workspace/instancia demo.')
        if (port is not None and port != cfg['port']) or (api_port is not None and api_port != cfg['api_port']):
            raise RuntimeError('Puertos ya fijados para esta demo. Usa otro --state-dir para otra instancia.')
        return cfg
    port, api_port = port or 13017, api_port or 18017
    if not (1024 <= port <= 65535 and 1024 <= api_port <= 65535 and port != api_port):
        raise RuntimeError('Elige dos puertos distintos entre1024 y65535.')
    password = getpass.getpass('Clave para las cuatro cuentas DEMO (minimo12 caracteres): ') if sys.stdin.isatty() else secrets.token_urlsafe(24)
    if not 12 <= len(password) <= 128 or any(c in password for c in '\n\r\x00'):
        raise RuntimeError('Clave demasiado corta o con caracteres no permitidos.')
    db_password = secrets.token_hex(32)
    root_password = secrets.token_hex(32)
    cfg = {'id': identifier, 'project': 'bna-sol-demo-'+identifier, 'port': port, 'api_port': api_port}
    write_private(state/'mysql.env', {'MYSQL_ROOT_PASSWORD': root_password, 'MYSQL_DATABASE': 'bna_sol_mvp_demo',
                                     'MYSQL_USER': 'sol_demo', 'MYSQL_PASSWORD': db_password})
    write_private(state/'app.env', {'SOL_DB_PASSWORD': db_password})
    write_private(state/'init.env', {'SOL_DB_PASSWORD': db_password})
    (state/'login.key').write_text(password);(state/'login.key').chmod(0o600)
    access = state/'acceso.txt'
    access.write_text('DEMO SOL — solo datos sinteticos\nUsuarios: asesor.bna, supervisor.bna, auditor.bna, evaluador.demo\nClave: '+password+'\n')
    access.chmod(0o600)
    path.write_text(json.dumps(cfg));path.chmod(0o600)
    return cfg


def validate(config, cfg, context):
    assert config['name'] == cfg['project']
    assert set(config['services']) == {'mysql', 'init', 'sol', 'frontend', 'scenarios'}
    assert set(config['networks']) == {'demo', 'edge'} and config['networks']['demo']['internal']
    assert not config['networks']['edge'].get('internal', False)
    assert set(config['services']['mysql']['networks']) == {'demo'}
    assert set(config['services']['frontend']['networks']) == {'edge'}
    assert not config.get('volumes')
    for name, service in config['services'].items():
        assert service['labels']['bna.sol.demo'] == cfg['id']
        assert not any(service.get(k) for k in ['container_name', 'network_mode', 'privileged', 'volumes', 'extra_hosts'])
        if name != 'mysql':
            assert service['image'].startswith(cfg['project']+'/')
            assert Path(service['build']['context']).is_relative_to(context)
            assert service.get('read_only')
        for port in service.get('ports', []):
            assert port['host_ip'] == '127.0.0.1'
        if name not in {'sol', 'frontend'}:
            assert not service.get('ports')
    for name in ['init', 'sol']:
        values = config['services'][name]['environment']
        assert values['SOL_INTEGRATION_MODE'] == 'SIMULADO'
        assert values['SOL_DB_HOST'] == 'mysql' and values['SOL_DB_NAME'] == 'bna_sol_mvp_demo'
        assert values['SOL_DB_USER'] == 'sol_demo'
    assert 'SOL_INITIAL_PASSWORD' not in config['services']['sol']['environment']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', nargs='?', choices=['up', 'check', 'status', 'stop'], default='up')
    p.add_argument('--port', type=int)
    p.add_argument('--api-port', type=int)
    default_id = hashlib.sha256(str(REPO).encode()).hexdigest()[:10]
    p.add_argument('--state-dir', type=Path, default=Path(tempfile.gettempdir())/('bna-sol-demo-'+str(os.getuid())+'-'+default_id))
    args = p.parse_args()
    state = args.state_dir.resolve()
    if state == REPO or REPO in state.parents or args.state_dir.is_symlink():
        raise RuntimeError('Estado/secretos deben estar fuera del repositorio y sin enlaces.')
    if state.exists() and (state.stat().st_uid != os.getuid() or state.stat().st_mode & 0o077):
        raise RuntimeError('El directorio de estado debe ser propio y tener permisos0700.')
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.umask(0o077)
    with (state/'launcher.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not shutil.which('docker'):
            raise RuntimeError('Instala Docker con el plugin docker compose.')
        endpoint = os.environ.get('DOCKER_HOST') or run(['docker', 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'], capture=True).strip()
        if not endpoint.startswith('unix://'):
            raise RuntimeError('Solo se permite un daemon Docker local unix:// para esta demo.')
        cfg = settings(state, args.port, args.api_port)
        if args.action in {'up', 'check'}:
            context = capture_sources(state)
            cfg['context'] = str(context)
            (state/'settings.json').write_text(json.dumps(cfg))
        elif not cfg.get('context'):
            print('La demo todavia no fue preparada.');return
        context = Path(cfg['context'])
        controls = {'DEMO_ID': cfg['id'], 'DEMO_PROJECT': cfg['project'], 'DEMO_STATE': str(state),
                    'DEMO_CONTEXT': str(context), 'DEMO_PORT': str(cfg['port']), 'DEMO_API_PORT': str(cfg['api_port'])}
        write_private(state/'control.env', controls)
        env = dict(os.environ);env.update(controls)
        env['DEMO_LOGIN_PASSWORD'] = (state/'login.key').read_text()
        compose = ['docker', 'compose', '--env-file', str(state/'control.env'), '-p', cfg['project'], '-f', str(HERE/'compose.yaml')]
        config = json.loads(run(compose+['--profile', 'prepare', 'config', '--format', 'json'], capture=True, env=env))
        validate(config, cfg, context)
        assert config['services']['init']['environment']['SOL_INITIAL_PASSWORD'] == env['DEMO_LOGIN_PASSWORD']
        # Refuse collisions with another project/owner, even if its names resemble this demo.
        ids = run(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project='+cfg['project']], capture=True).split()
        existing = json.loads(run(['docker', 'inspect', *ids], capture=True)) if ids else []
        assert all(c['Config']['Labels'].get('bna.sol.demo') == cfg['id'] for c in existing), 'Colision de propietario.'
        for network, internal in [('demo', True), ('edge', False)]:
            networks = run(['docker', 'network', 'ls', '-q', '--filter', 'name=^'+cfg['project']+'_'+network+'$'], capture=True).split()
            if networks:
                net = json.loads(run(['docker', 'network', 'inspect', *networks], capture=True))
                assert all(n['Internal'] == internal and n['Labels'].get('bna.sol.demo') == cfg['id'] for n in net)
        if args.action == 'check':
            print('Configuracion aislada correcta; SIMULADO; sin servicios iniciados.');return
        if args.action == 'status':
            run(compose+['ps', '-a'], env=env);return
        if args.action == 'stop':
            run(compose+['stop'], env=env)
            print('Solo demo detenida. MySQL tmpfs: los datos sinteticos se pierden; no se eliminaron volumenes.');return
        for service, port in [('frontend', cfg['port']), ('sol', cfg['api_port'])]:
            owned = any(c['Config']['Labels'].get('com.docker.compose.service') == service and c['State']['Running'] for c in existing)
            if not owned:
                with socket.socket() as sock:
                    try:
                        sock.bind(('127.0.0.1', port))
                    except OSError:
                        raise RuntimeError('Puerto ocupado: '+str(port)+'. Usa otro --port/--api-port y --state-dir.') from None
        print('Preparando DEMO SIMULADA SOL. La primera construccion necesita Internet.', flush=True)
        run(compose+['up', '-d', '--build', '--wait', '--wait-timeout', '240', 'mysql', 'sol', 'frontend'], env=env)
        # Health inside Docker does not prove published localhost ports work.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for url in ['http://127.0.0.1:'+str(cfg['port'])+'/solicitud-credito',
                    'http://127.0.0.1:'+str(cfg['api_port'])+'/ready']:
            with opener.open(url, timeout=10) as response:
                assert response.status == 200, 'Puerto local no accesible.'
        # Seed once per live MySQL instance. Re-launching never restores over user edits.
        containers = run(compose+['ps', '-q', 'mysql'], capture=True, env=env).split()
        stamp = run(['docker', 'inspect', '--format', '{{.Id}} {{.State.StartedAt}}', *containers], capture=True).strip()
        marker = state/'ready.json'
        previous = json.loads(marker.read_text()) if marker.exists() else {}
        if previous.get('mysql_instance') != stamp:
            run(compose+['run', '--rm', '--no-deps', 'scenarios'], env=env)
            marker.write_text(json.dumps({'mysql_instance': stamp}));marker.chmod(0o600)
        else:
            print('Demo existente conservada; no se duplican ni restauran los expedientes.')
        print('\nDemo: http://127.0.0.1:'+str(cfg['port'])+'/solicitud-credito')
        print('Swagger: http://127.0.0.1:'+str(cfg['api_port'])+'/docs')
        print('Acceso: asesor.bna. Otros perfiles: supervisor.bna, auditor.bna, evaluador.demo.')
        print('Clave privada guardada en: '+str(state/'acceso.txt')+' (no se imprime).')
        print('SIMULADO: no es una integracion CAP/EVA/Seguridad institucional.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, AssertionError, OSError, ValueError) as exc:
        print('Demo no iniciada/completada: '+str(exc), file=sys.stderr)
        sys.exit(1)
