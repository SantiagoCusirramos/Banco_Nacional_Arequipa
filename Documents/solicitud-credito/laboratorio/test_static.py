"""Negative checks for the static validator; no containers, SQL or HTTP."""
import contextlib
import copy
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import validate


class IsolationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        cls.base = validate.rendered(ROOT, False)
        cls.audit = validate.rendered(ROOT, True)

    def rejected(self, mutate):
        base, audit = copy.deepcopy(self.base), copy.deepcopy(self.audit)
        mutate(base)
        with patch.object(validate, 'rendered', side_effect=[base, audit]):
            with self.assertRaises(AssertionError), contextlib.redirect_stdout(io.StringIO()):
                validate.validate(self.root)

    def test_mysql_published_port(self):
        self.rejected(lambda c: c['services']['mysql-core'].update(ports=[{'published': 3306}]))

    def test_external_network(self):
        self.rejected(lambda c: c['networks']['integration'].update(internal=False))

    def test_crossed_token(self):
        self.rejected(lambda c: c['services']['captacion']['environment'].update(
            CAP_SOL_TOKEN=c['services']['sol']['environment']['SOL_EVA_TOKEN']))

    def test_root_credential_in_api(self):
        self.rejected(lambda c: c['services']['sol']['environment'].update(AUX_DB_ROOT_PASSWORD='forbidden'))

    def test_external_volume(self):
        self.rejected(lambda c: c['volumes']['cap-secrets'].update(external=True))

    def test_dependency_cycle(self):
        self.rejected(lambda c: c['services']['coredb-init'].update(depends_on={'captacion': {'condition': 'service_healthy'}}))

    def test_audit_activated_in_base(self):
        self.rejected(lambda c: c['services']['sol']['environment'].update(SOL_AUDIT_BASE_URL='http://audit-lab:8020'))

    def test_callback_activated(self):
        self.rejected(lambda c: c['services']['evaluacion']['environment'].update(EVALUACION_SOL_URL='http://sol:8011'))

    def test_ddl_gate_open(self):
        self.rejected(lambda c: c['services']['mysql-core']['environment'].update(LAB_ALLOW_DDL='YES_ISOLATED_LAB'))


if __name__ == '__main__':
    ROOT = Path(sys.argv.pop(1)).resolve()
    unittest.main()
