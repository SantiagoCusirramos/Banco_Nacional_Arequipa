"""Static launcher guards; no build, service, SQL or HTTP."""
import contextlib
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sol_demo_launcher', HERE/'demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class DemoGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = STATE
        cls.cfg = json.loads((STATE/'settings.json').read_text())
        cls.context = Path(cls.cfg['context'])
        controls = dict(line.split('=', 1) for line in (STATE/'control.env').read_text().splitlines())
        env = dict(os.environ);env.update(controls);env['DEMO_LOGIN_PASSWORD']=(STATE/'login.key').read_text()
        command = ['docker','compose','--env-file',str(STATE/'control.env'),'-p',cls.cfg['project'],
                   '-f',str(HERE/'compose.yaml'),'--profile','prepare','config','--format','json']
        cls.config = json.loads(demo.run(command, capture=True, env=env))

    def reject(self, mutate):
        config = deepcopy(self.config);mutate(config)
        with self.assertRaises(AssertionError):
            demo.validate(config, self.cfg, self.context)

    def test_valid_config(self):
        demo.validate(self.config, self.cfg, self.context)

    def test_no_public_port(self):
        self.reject(lambda c:c['services']['frontend']['ports'][0].update(host_ip='0.0.0.0'))

    def test_no_mysql_port(self):
        self.reject(lambda c:c['services']['mysql'].update(ports=[{'host_ip':'127.0.0.1'}]))

    def test_database_stays_internal(self):
        self.reject(lambda c:c['networks']['demo'].update(internal=False))

    def test_database_not_on_edge(self):
        self.reject(lambda c:c['services']['mysql']['networks'].update(edge={}))

    def test_no_real_mode(self):
        self.reject(lambda c:c['services']['sol']['environment'].update(SOL_INTEGRATION_MODE='REAL'))

    def test_no_external_database(self):
        self.reject(lambda c:c['services']['sol']['environment'].update(SOL_DB_HOST='external'))

    def test_no_external_mounts(self):
        self.reject(lambda c:c['services']['sol'].update(volumes=[{'source':'external'}]))

    def test_no_foreign_owner(self):
        self.reject(lambda c:c['services']['sol']['labels'].update({'bna.sol.demo':'foreign'}))

    def test_no_password_in_api(self):
        self.reject(lambda c:c['services']['sol']['environment'].update(SOL_INITIAL_PASSWORD='not-allowed'))

    def test_private_credentials(self):
        self.assertEqual(STATE.stat().st_mode & 0o777,0o700)
        for name in ['app.env','mysql.env','init.env','login.key','acceso.txt']:
            self.assertEqual((STATE/name).stat().st_mode & 0o777,0o600)

    def test_sources_exclude_env_and_databases(self):
        for p in self.context.rglob('*'):
            self.assertFalse(any(part.startswith('.env') or part in {'node_modules','.next','__pycache__'} for part in p.relative_to(self.context).parts))
            self.assertNotIn(p.suffix,{'.db','.sqlite','.pyc'})
            if p.is_dir():self.assertEqual(p.stat().st_mode & 0o777,0o755)

    def test_complex_password_stays_out_of_envfiles(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)
            chosen="Demo-unidad-$#'\\-2026"
            with patch.object(sys.stdin,'isatty',return_value=True),patch.object(demo.getpass,'getpass',return_value=chosen):
                cfg=demo.settings(state)
            self.assertTrue((state/'login.key').read_text()==chosen)
            self.assertNotIn('SOL_INITIAL_PASSWORD',(state/'init.env').read_text())
            with patch.object(demo.getpass,'getpass',side_effect=AssertionError('No volver a pedir clave')):
                self.assertEqual(demo.settings(state),cfg)
            cfg['project']='bna'
            (state/'settings.json').write_text(json.dumps(cfg))
            with self.assertRaises(RuntimeError):demo.settings(state)


if __name__ == '__main__':
    STATE=Path(sys.argv.pop(1)).resolve()
    unittest.main()
