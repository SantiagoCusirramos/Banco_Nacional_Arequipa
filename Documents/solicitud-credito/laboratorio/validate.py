"""Static validation only. Docker is invoked exclusively as compose config (no daemon)."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def env_file(path):
    assert path.is_file() and not path.is_symlink(), 'Archivo externo ausente o enlace inesperado.'
    assert path.stat().st_mode & 0o077 == 0, 'Permisos de archivo externo demasiado abiertos.'
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if line and not line.startswith('#'))


def rendered(root, audit):
    control = env_file(root/'runtime/control.env')
    assert control['LAB_ROOT'] == str(root)
    assert re.fullmatch('[a-z0-9]{8,24}', control['LAB_RUN_ID'])
    # Do not inherit caller's Compose project, override URLs, proxies, or tokens.
    environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), **control}
    command = ['docker', 'compose', '--env-file', str(root/'runtime/control.env'),
               '--project-directory', str(HERE), '-f', str(HERE/'compose.yaml')]
    if audit:
        command += ['-f', str(HERE/'compose.audit-sim.yaml')]
    command += ['--profile', '*', 'config', '--format', 'json']
    result = subprocess.run(command, env=environment, capture_output=True, text=True)
    # Never print stderr/stdout on failure: Compose can interpolate credential values there.
    assert result.returncode == 0, 'Compose config falló; salida potencialmente sensible descartada.'
    return json.loads(result.stdout)


def validate(root):
    root = root.resolve()
    assert root != REPO and REPO not in root.parents
    assert root.stat().st_mode & 0o077 == 0
    manifest = json.loads((root/'manifest.json').read_text())
    assert manifest['branch'] == 'feature/sol-integracion-cap-eva'
    assert manifest['cap'] == '4ea5014bddb1a69289402f03b3fbc47c28cc9413'
    assert manifest['eva'] == '57b0e2a34fd55fb96fd6245acc06a86536d220f8'
    for name, digest in manifest['tooling'].items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest() == digest, 'Herramienta cambió desde captura.'
    paths = set()
    for record in manifest['files']:
        path = root/record['path']
        assert root in path.resolve().parents and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256'], 'Hash de fuente cambió.'
        paths.add(record['path'])
        if path.suffix == '.py':
            ast.parse(path.read_text(), filename=record['path'])
        assert path.suffix not in {'.db', '.sqlite', '.pyc'}
        assert not any(part.startswith('.env') for part in path.parts)
    for directory in [root/'sources', *(root/'sources').rglob('*')]:
        if directory.is_dir():
            assert directory.stat().st_mode & 0o777 == 0o755, 'Directorio fuente no transitable por usuario imagen.'
    actual = {str(p.relative_to(root)) for p in (root/'sources').rglob('*') if p.is_file()}
    assert actual == paths, 'Contextos contienen archivos fuera del manifiesto.'
    for module in ['COREDB', 'SOL', 'CAPTACION', 'EVALUACION']:
        assert any(p.startswith('sources/api/'+module+'/') for p in paths)
    assert not any('/CORE/' in p or '/CUENTAS/' in p or '/TARJETAS/' in p for p in paths)
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(), filename=path.name)
    for path in (root/'runtime').glob('*.env'):
        env_file(path)
    secrets = set()
    for path in (root/'runtime').glob('*.env'):
        for value in env_file(path).values():
            if re.fullmatch('[a-f0-9]{64}', value):
                secrets.add(value)
    # Exact-value scan of deliverables + copied source text; never display matching values.
    for path in list(HERE.rglob('*')) + [REPO/'Documents/solicitud-credito/sol-laboratorio-build.md']:
        if path.is_file():
            data = path.read_bytes()
            assert not any(secret.encode() in data for secret in secrets), 'Secreto externo copiado al repositorio.'
    for record in manifest['files']:
        data = (root/record['path']).read_bytes()
        assert not any(secret.encode() in data for secret in secrets), 'Secreto copiado al contexto.'
    expected = {'mysql-core', 'mysql-modulos', 'coredb', 'coredb-init', 'captacion', 'captacion-init',
                'sol', 'sol-bootstrap', 'sol-init', 'evaluacion', 'evaluacion-init', 'http-runner'}
    configs = [rendered(root, False), rendered(root, True)]
    for index, config in enumerate(configs):
        assert config['name'] == 'bna-sol-cap-eva-lab-'+manifest['run_id']
        assert set(config['services']) == expected | ({'audit-lab'} if index else set())
        assert set(config['networks']) == {'core-data', 'module-data', 'integration'}
        assert all(net.get('internal') and not net.get('external') and
                   net['name'].startswith(config['name']+'_') for net in config['networks'].values())
        assert set(config['volumes']) == {'cap-secrets'}
        volume = config['volumes']['cap-secrets']
        assert not volume.get('external') and volume['name'] == config['name']+'_cap-secrets'
        for name, service in config['services'].items():
            assert not any(service.get(key) for key in ['ports', 'container_name', 'network_mode',
                                                       'extra_hosts', 'privileged', 'devices', 'volumes_from'])
            assert not service.get('restart') or service['restart'] == 'no'
            assert set(service['networks']) <= set(config['networks'])
            assert service['image'].startswith(config['name']+'/') or name == 'mysql-modulos'
            if 'build' in service:
                assert Path(service['build']['context']).is_relative_to(root/'sources')
                assert (Path(service['build']['context'])/'Dockerfile').is_file()
            for volume in service.get('volumes', []):
                assert volume['type'] == 'volume' and volume['source'] == 'cap-secrets'
            environment = service.get('environment', {})
            if name.endswith('-init') or name in {'sol-bootstrap', 'mysql-core', 'mysql-modulos'}:
                assert environment['LAB_ALLOW_DDL'] == 'NO', 'Gates deben seguir cerrados en preparación.'
            if name in {'coredb', 'captacion', 'sol', 'evaluacion', 'http-runner', 'audit-lab'}:
                assert 'AUX_DB_ROOT_PASSWORD' not in environment and 'MYSQL_ROOT_PASSWORD' not in environment
            assert all(dep in config['services'] for dep in service.get('depends_on', {}))
        visited = set()
        def visit(name, pending):
            assert name not in pending, 'Ciclo de dependencias.'
            if name in visited:
                return
            for dep in config['services'][name].get('depends_on', {}):
                visit(dep, pending | {name})
            visited.add(name)
        for name in config['services']:
            visit(name, set())
        assert 'core-data' not in config['services']['sol']['networks']
        assert 'core-data' not in config['services']['captacion']['networks']
        assert 'core-data' not in config['services']['evaluacion']['networks']
        sol = config['services']['sol']['environment']
        cap = config['services']['captacion']['environment']
        eva = config['services']['evaluacion']['environment']
        assert sol['SOL_CAP_BASE_URL'] == 'http://captacion:8014'
        assert sol['SOL_EVA_BASE_URL'] == 'http://evaluacion:8015'
        assert sol['SOL_CAP_TOKEN'] == cap['CAP_SOL_TOKEN']
        assert sol['SOL_EVA_TOKEN'] == eva['EVALUACION_TOKEN_SOL']
        assert sol['SOL_EVA_CALLBACK_TOKEN'] == eva['EVALUACION_SOL_TOKEN_RESULTADOS']
        assert len({sol['SOL_CAP_TOKEN'], sol['SOL_EVA_TOKEN'], sol['SOL_EVA_CALLBACK_TOKEN']}) == 3
        assert sol['SOL_EVA_TOKEN'] not in cap.values() and sol['SOL_CAP_TOKEN'] not in eva.values()
        assert sol['SOL_INTEGRATION_MODE'] == 'REAL' and not sol['SOL_BUS_BASE_URL'] and not sol['SOL_BUS_TOKEN']
        assert sol['SOL_CAP_SEARCH_PATH'] == '/cap/references'
        assert sol['SOL_CAP_REFERENCE_PATH'] == '/cap/references/{idCliente}'
        assert sol['SOL_EVA_SEND_PATH'] == '/eva/applications'
        assert sol['SOL_EVA_STATUS_PATH'] == '/eva/operations/{idOperacion}'
        assert not eva['EVALUACION_SOL_URL'], 'Callback no debe activarse todavía.'
        assert urlparse(eva['EVALUACION_DATABASE_URL']).hostname == 'mysql-modulos'
        assert cap['CAP_DB_HOST'] == sol['SOL_DB_HOST'] == 'mysql-modulos'
        if index:
            audit = config['services']['audit-lab']
            assert audit['profiles'] == ['audit-sim']
            assert sol['SOL_AUDIT_TOKEN'] == audit['environment']['SOL_SIMULATOR_TOKEN']
            assert sol['SOL_AUDIT_TOKEN'] not in {sol['SOL_CAP_TOKEN'], sol['SOL_EVA_TOKEN'], sol['SOL_EVA_CALLBACK_TOKEN']}
            assert sol['SOL_AUDIT_PATH'] == '/security/events'
            assert sol['LAB_AUDIT_SIM_AUTHORIZATION'] == audit['environment']['LAB_AUDIT_SIM_AUTHORIZATION'] == 'NO'
        else:
            assert not sol['SOL_AUDIT_BASE_URL'] and not sol['SOL_AUDIT_TOKEN'] and not sol['SOL_AUDIT_PATH']
    print('OK: hashes/AST, permisos externos, secretos, Compose base y overlay, destinos, tokens, redes, recursos y gates cerrados.')
    print('Fuentes verificadas:', len(paths), '| Servicios base:', len(expected), '| Servicios con overlay:', len(expected)+1)
    print('Solo validación estática; no build, daemon Docker, SQL ni HTTP.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    try:
        validate(p.parse_args().root)
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        # Avoid echoing configuration values from third-party exception messages.
        print('VALIDACIÓN FALLIDA:', str(exc) if isinstance(exc, AssertionError) else type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
