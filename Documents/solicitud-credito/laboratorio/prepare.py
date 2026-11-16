"""Capture pinned sources and synthetic secrets outside Git. Never invokes Docker or SQL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CAP = '4ea5014bddb1a69289402f03b3fbc47c28cc9413'
EVA = '57b0e2a34fd55fb96fd6245acc06a86536d220f8'
BRANCH = 'feature/sol-integracion-cap-eva'
SQL_FILES = ['sql/bna_core.sql', 'sql/bna_extension.sql', 'sql/bna_datos_dev.sql',
             'conf/mysql/bna.cnf', 'conf/mysql/crear_usuarios.sh']


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


def safe_file(path):
    return (not any(p.startswith('.') or p in {'__pycache__', 'tests', 'node_modules'}
                    for p in path.parts) and path.suffix == '.py')


def prepare(run_id, parent):
    if git('branch', '--show-current').decode().strip() != BRANCH:
        raise ValueError('Rama incorrecta; no se cambió de rama.')
    if not re.fullmatch('[a-z0-9]{8,24}', run_id):
        raise ValueError('run-id: 8–24 caracteres alfanuméricos minúsculos.')
    for ref, expected in [('origin/pr-cap-74', CAP), ('origin/pr-eva-70', EVA)]:
        if git('rev-parse', ref).decode().strip() != expected:
            raise ValueError('Referencia PR cambió: revisar auditoría antes de capturar.')
    parent = parent.resolve()
    if parent == REPO or REPO in parent.parents:
        raise ValueError('Destino de fuentes y secretos debe estar fuera del repositorio.')
    os.umask(0o077)
    root = Path(tempfile.mkdtemp(prefix='bna-sol-lab-'+run_id+'-', dir=parent))
    head = git('rev-parse', 'HEAD').decode().strip()
    records = []

    def write(relative, data, origin):
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        dest.chmod(0o644)  # sources only; runtime secrets are written separately
        records.append({'path': relative, 'source': origin,
                        'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})

    def export_py(ref, module):
        paths = git('ls-tree', '-r', '--name-only', ref, 'backend/'+module).decode().splitlines()
        for name in paths:
            if safe_file(Path(name)):
                write('sources/api/'+name.removeprefix('backend/'),
                      git('show', ref+':'+name), ref+':'+name)

    export_py(head, 'COREDB')
    export_py(CAP, 'CAPTACION')
    export_py(EVA, 'EVALUACION')
    # Workspace SOL is deliberately NOT exported from HEAD: includes uncommitted adapters.
    for src in sorted((REPO/'backend/SOL').rglob('*')):
        rel = src.relative_to(REPO/'backend')
        if src.is_symlink():
            raise ValueError('Enlace simbólico inesperado en SOL: captura detenida.')
        if src.is_file() and (safe_file(rel) or rel.as_posix() == 'SOL/config/politica_demo.json'):
            write('sources/api/'+rel.as_posix(), src.read_bytes(), 'workspace:backend/'+rel.as_posix())
    for filename, ref in [('requirements-sol.txt', head), ('requirements-coredb.txt', head),
                          ('requirements.txt', EVA)]:
        write('sources/api/'+filename, git('show', ref+':backend/'+filename), ref+':backend/'+filename)
    # Distinguish workspace requirements from historical HEAD if they changed.
    for filename in ['requirements-sol.txt']:
        write('sources/api/'+filename, (REPO/'backend'/filename).read_bytes(), 'workspace:backend/'+filename)
    # Remove superseded record (same destination), keeping its actual final content only.
    records = list({r['path']: r for r in records}.values())
    for name in SQL_FILES:
        write('sources/core/'+name, git('show', head+':database/'+name), head+':database/'+name)
    for name in ['Dockerfile.api', 'guard.py', 'bootstrap_sol.py', 'http_probe.py']:
        target = 'Dockerfile' if name == 'Dockerfile.api' else 'lab/'+name
        write('sources/api/'+target, (HERE/name).read_bytes(), 'laboratorio/'+name)
    write('sources/core/Dockerfile', (HERE/'Dockerfile.core').read_bytes(), 'laboratorio/Dockerfile.core')
    for context in ['api', 'core']:
        write('sources/'+context+'/.dockerignore', b'**/.env*\n**/__pycache__\n**/*.pyc\n**/*.db\n**/*.sqlite*\n', 'laboratorio:exclusions')
    # COPY preserves directory modes; the non-root image user must traverse source dirs.
    for directory in [root/'sources', *(root/'sources').rglob('*')]:
        if directory.is_dir():
            directory.chmod(0o755)
    manifest = {'task': 'SOL-LAB-BUILD', 'head': head, 'branch': BRANCH,
                'cap': CAP, 'eva': EVA, 'run_id': run_id,
                'workspace_status': git('status', '--porcelain', '--', 'backend/SOL', 'backend/requirements-sol.txt').decode().splitlines(),
                'files': sorted(records, key=lambda r: r['path']),
                'tooling': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(HERE.iterdir())
                            if p.suffix in {'.py', '.yaml'} or p.name.startswith('Dockerfile.')}}
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    runtime = root/'runtime'
    runtime.mkdir(mode=0o700)
    values = {name: secrets.token_hex(32) for name in [
        'root_core', 'root_modules', 'app', 'admin_sql', 'security_sql', 'jwt',
        'admin_human', 'cap_db', 'sol_db', 'eva_db', 'otp', 'cap_token', 'eva_token',
        'callback', 'audit', 'sol_initial']}

    def env(name, content):
        path = runtime/(name+'.env')
        path.write_text(''.join(f'{k}={v}\n' for k, v in content.items()))
        path.chmod(0o600)

    core = {'CORE_DB_HOST': 'mysql-core', 'CORE_DB_PORT': '3306', 'CORE_DB_APP_USER': 'bna_app_user',
            'CORE_DB_APP_PASSWORD': values['app'], 'CORE_DB_JWT_CLAVE': values['jwt']}
    cap = {'CAP_DB_HOST': 'mysql-modulos', 'CAP_DB_PORT': '3306', 'CAP_DB_USER': 'cap_lab',
           'CAP_DB_NAME': 'bna_captacion_'+run_id, 'CAP_DB_PASSWORD': values['cap_db'],
           'CORE_BASE_URL': 'http://coredb:8012', 'CAP_CORE_USUARIO': 'svc-cap-lab',
           'CAP_CORE_SECRETO_ARCHIVO': '/datos/coredb_secreto', 'CAP_SOL_TOKEN': values['cap_token'],
           'CAP_OTP_CLAVE': values['otp'], 'CAP_OTP_SIMULADO': 'true'}
    sol = {'SOL_DB_HOST': 'mysql-modulos', 'SOL_DB_PORT': '3306', 'SOL_DB_USER': 'sol_lab',
           'SOL_DB_NAME': 'bna_sol_mvp_'+run_id, 'SOL_DB_PASSWORD': values['sol_db'],
           'SOL_INTEGRATION_MODE': 'REAL', 'SOL_CAP_BASE_URL': 'http://captacion:8014',
           'SOL_CAP_TOKEN': values['cap_token'], 'SOL_CAP_SEARCH_PATH': '/cap/references',
           'SOL_CAP_REFERENCE_PATH': '/cap/references/{idCliente}',
           'SOL_EVA_BASE_URL': 'http://evaluacion:8015', 'SOL_EVA_TOKEN': values['eva_token'],
           'SOL_EVA_SEND_PATH': '/eva/applications', 'SOL_EVA_STATUS_PATH': '/eva/operations/{idOperacion}',
           'SOL_EVA_CALLBACK_TOKEN': values['callback'], 'SOL_BUS_BASE_URL': '', 'SOL_BUS_TOKEN': '',
           'SOL_AUDIT_BASE_URL': '', 'SOL_AUDIT_TOKEN': '', 'SOL_AUDIT_PATH': '',
           'SOL_HTTP_TIMEOUT_SECONDS': '0.6', 'SOL_REQUEST_BUDGET_SECONDS': '2.4',
           'SOL_HTTP_MAX_RETRIES': '2', 'SOL_WORKER_SECONDS': '5'}
    eva = {'EVALUACION_DATABASE_URL': 'mysql+pymysql://eva_lab:'+values['eva_db']+'@mysql-modulos:3306/bna_evaluacion_'+run_id+'?charset=utf8mb4',
           'COREDB_URL': 'http://coredb:8012', 'EVALUACION_TOKEN_SOL': values['eva_token'],
           'EVALUACION_SOL_TOKEN_RESULTADOS': values['callback'],
           'EVALUACION_SOL_URL': '', 'EVALUACION_ENVIO_INTERVALO_SEG': '5'}
    env('mysql-core', {'MYSQL_ROOT_PASSWORD': values['root_core'], 'CORE_DB_APP_PASSWORD': values['app'],
                      'CORE_DB_ADMIN_PASSWORD': values['admin_sql'], 'CORE_DB_SEGURIDAD_PASSWORD': values['security_sql']})
    env('mysql-modulos', {'MYSQL_ROOT_PASSWORD': values['root_modules'], 'MYSQL_ROOT_HOST': '%'})
    env('coredb', core)
    env('coredb-init', dict(core, CORE_DB_ADMIN_INICIAL_PASSWORD=values['admin_human']))
    env('cap', cap)
    env('cap-init', dict(cap, AUX_DB_ROOT_PASSWORD=values['root_modules'], BNA_ADMIN_USUARIO='admin-lab',
                         BNA_ADMIN_PASSWORD=values['admin_human']))
    env('sol', sol)
    env('sol-init', dict(sol, SOL_INITIAL_PASSWORD=values['sol_initial']))
    env('sol-bootstrap', {k: v for k, v in sol.items() if k.startswith('SOL_DB_')} |
        {'AUX_DB_ROOT_PASSWORD': values['root_modules']})
    env('eva', eva)
    env('eva-init', {'EVALUACION_DB_HOST': 'mysql-modulos', 'EVALUACION_DB_PORT': '3306',
                     'EVALUACION_DB_USER': 'eva_lab', 'EVALUACION_DB_NAME': 'bna_evaluacion_'+run_id,
                     'EVALUACION_DB_PASSWORD': values['eva_db'], 'AUX_DB_ROOT_PASSWORD': values['root_modules']})
    env('audit-server', {'SOL_SIMULATOR_TOKEN': values['audit']})
    env('audit-client', {'SOL_AUDIT_TOKEN': values['audit']})
    # Compose interpolation file contains paths and nonsecret gates only; not exported to shell.
    env('control', {'LAB_ROOT': str(root), 'LAB_RUN_ID': run_id, 'LAB_ALLOW_DDL': 'NO',
                    'LAB_DATOS_DEV': '0', 'LAB_AUDIT_SIM_AUTHORIZATION': 'NO'})
    # No secret values, hashes of secrets, or env contents in the manifest or stdout.
    return root


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id', required=True)
    p.add_argument('--parent', type=Path, default=Path(tempfile.gettempdir()))
    a = p.parse_args()
    print(prepare(a.run_id, a.parent))  # private directory path only
