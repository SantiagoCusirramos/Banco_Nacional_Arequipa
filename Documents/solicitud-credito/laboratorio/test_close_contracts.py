"""Pure SOL/EVA contract and OpenAPI checks. No database, socket or live provider.
Run in the pinned lab image containing EVA #70; all envelopes/acks are unit fixtures.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError
from SOL.app import create_app
from SOL.integrations import evaluation_envelope, validate_receipt
from SOL.schemas import EvaluationResult
from SOL.settings import Settings
from EVALUACION.config import Config
from EVALUACION.contratos import SobreExpediente
from EVALUACION.envios import DespachadorResultados
from EVALUACION.scripts.enviar_expediente_demo import sobre_de_sol


def envelope(materno=None):
    # Existing EVA fixture builder uses SOL's unchanged policy/calendar. Never sent anywhere.
    example = sobre_de_sol(id_cliente='UNIT-CLIENT', numero_documento='70000000',
                           nombres='Unidad', apellido_paterno='Contrato', apellido_materno=materno)
    return evaluation_envelope(SimpleNamespace(id=example['idSolicitud']),
                               SimpleNamespace(number=example['versionSolicitud'], snapshot=example['expediente']),
                               example['idOperacion'], example['idCorrelacion'])


@pytest.mark.parametrize('materno', [None, '', 'Unidad'])
def test_sol_envelope_accepted_by_actual_eva_dto(materno):
    payload = envelope(materno)
    parsed = SobreExpediente.model_validate(payload)
    assert parsed.idOperacion == payload['idOperacion']
    assert parsed.expediente.cliente.apellido_materno == materno
    receipt = {key: payload[key] for key in ['idSolicitud', 'versionSolicitud', 'idOperacion']}
    receipt.update(idEvaluacion='UNIT-EVA', ronda=1, acuse='UNIT-ACK')
    assert validate_receipt(receipt, payload) == receipt


@pytest.mark.parametrize('decision', ['APROBADO', 'OBSERVADO', 'RECHAZADO'])
def test_callback_decisions_accepted_by_sol_dto(decision):
    payload = envelope()
    callback = {key: payload[key] for key in ['idSolicitud', 'versionSolicitud', 'idOperacion', 'idCorrelacion']}
    callback.update(idEvaluacion='UNIT-EVA', ronda=1, decision=decision, observaciones='Resultado unitario sintetico')
    assert EvaluationResult.model_validate(callback).decision == decision


def test_eva_rejects_string_version():
    payload = envelope()
    payload['versionSolicitud'] = '1'
    with pytest.raises(ValidationError):
        SobreExpediente.model_validate(payload)


def test_characterizes_eva_2xx_ack_weakness_without_sql():
    config = Config(database_url='sqlite://', sol_url='http://unit-sol.test',
                    sol_token_resultados='unit-resultados-'+'x'*32)
    dispatcher = DespachadorResultados(None, config, httpx.MockTransport(
        lambda request: httpx.Response(200, json={'recibido': False, 'incompatible': True})))
    dispatcher._terminar = Mock()  # capture intended state, never perform SQL
    row = SimpleNamespace(intentos=0, id_operacion='unit-operation', id_evaluacion='UNIT-EVA',
                          contenido=json.dumps({'idOperacion':'unit-operation','idCorrelacion':'unit-correlation'}))
    try:
        assert dispatcher._entregar(row) == 1
        assert dispatcher._terminar.call_args.args[2] == 'ENTREGADO'
    finally:
        dispatcher.cerrar()


@pytest.mark.parametrize('mode', ['SIMULADO', 'REAL'])
def test_openapi_routes_auth_and_responses_match_e06_except_optional_surname(mode):
    changes = {} if mode == 'SIMULADO' else dict(
        cap_base_url='http://unit-cap.test', cap_token='unit-cap-'+'a'*32,
        eva_base_url='http://unit-eva.test', eva_token='unit-eva-'+'e'*32,
        audit_base_url='http://unit-audit.test', audit_token='unit-audit-'+'s'*32,
        callback_token='unit-callback-'+'c'*32, cap_search_path='/cap/references',
        cap_reference_path='/cap/references/{idCliente}', eva_send_path='/eva/applications',
        eva_status_path='/eva/operations/{idOperacion}', audit_path='/security/events')
    app = create_app(Settings('sqlite://', mode=mode, worker_seconds=0, **changes))
    try:
        current = app.openapi()
        directory = Path(os.environ['SOL_CLOSE_REFERENCE_DIR'])
        previous = json.loads((directory/f'sol-openapi-e06-{mode.lower()}.json').read_text())
        expected = deepcopy(previous)
        client = expected['components']['schemas']['ClientResponse']
        client['required'].remove('apellido_materno')
        client['properties']['apellido_materno']['default'] = ''
        assert current == expected
    finally:
        app.state.integrations.close()
        app.state.engine.dispose()
