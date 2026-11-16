"""Independent COREDB/CAP/EVA TCP checks; run inside CAP with synthetic admin env.
Does not contact SOL or Auditoría. Never prints tokens, OTP, document or passwords.
"""
import json
import os
import secrets
import sys
import httpx
from fastapi import HTTPException
from SOL.integrations import validate_reference


def main():
    rows, ids = [], {}
    reference = {}
    client = httpx.Client(timeout=10, trust_env=False, follow_redirects=False)

    def call(label, method, base, path, *, expected=200, **kwargs):
        response = client.request(method, base+path, **kwargs)
        rows.append({'case': label, 'method': method, 'path': path, 'http': response.status_code,
                     'expected': expected, 'passed': response.status_code == expected})
        if response.status_code != expected:
            raise RuntimeError('HTTP status inesperado: '+label)
        return response.json()

    def data(label, method, path, expected=200, **kwargs):
        return call(label, method, cap, path, expected=expected, headers=human, **kwargs)['data']

    core, cap, eva = 'http://coredb:8012', 'http://captacion:8014', 'http://evaluacion:8015'
    try:
        for base, path, label in [(core, '/coredb/salud', 'COREDB health'),
                                  (cap, '/ready', 'CAP ready'), (eva, '/salud', 'EVA health')]:
            call(label, 'GET', base, path)
        login = call('COREDB login', 'POST', core, '/coredb/auth/login',
                     json={'username': 'admin-lab', 'password': os.environ['BNA_ADMIN_PASSWORD']})
        human = {'Authorization': 'Bearer '+login['access_token']}
        call('COREDB auth me', 'GET', core, '/coredb/auth/me', headers=human)
        call('COREDB sin autenticación', 'GET', core, '/coredb/auth/me', expected=401)
        prefix = '/api/v1/captacion'
        doc = str(71000000+secrets.randbelow(800000))[:-1]+'0'
        prospect = data('CAP solicitante sin materno', 'POST', prefix+'/solicitantes', 201, json={
            'tipo_documento': 'DNI', 'numero_documento': doc, 'nombres': 'Persona Sintetica',
            'apellido_paterno': 'Laboratorio', 'celular': '9'+doc, 'correo': 'ensayo'+secrets.token_hex(6)+'@example.invalid'})
        ids['id_solicitante'] = prospect['solicitante']['id_solicitante']
        assert prospect['solicitante']['apellido_materno'] is None
        case = data('CAP abrir caso WEB', 'POST', prefix+'/casos', 201,
                    json={'id_solicitante': ids['id_solicitante'], 'canal': 'WEB'})
        ids['id_caso'] = case['id_caso']
        path = prefix+'/casos/'+ids['id_caso']
        data('CAP consentimientos', 'POST', path+'/consentimientos', 201, json={'consentimientos': [
            {'tipo': t, 'aceptado': True} for t in ['TRATAMIENTO_DATOS', 'CONSULTA_BUROS', 'TERMINOS']]})
        otp = data('CAP enviar OTP simulado', 'POST', path+'/otp', 201, json={'canal': 'SMS'})
        code = otp['codigo_simulado']
        data('CAP verificar OTP', 'POST', path+'/otp/verificar', json={'canal': 'SMS', 'codigo': code})
        data('CAP validaciones simuladas', 'POST', path+'/validaciones', 201, json={'tipos': ['RENIEC', 'LISTAS_NEGRAS', 'PEP']})
        data('CAP central simulada sin reporte manual', 'POST', path+'/consultas-riesgo', 201, json={'central': 'SBS'})
        data('CAP perfil', 'POST', path+'/perfil', 201)
        data('CAP habilitar por COREDB HTTP', 'POST', path+'/habilitar')
        own = {'Authorization': 'Bearer '+os.environ['CAP_SOL_TOKEN']}
        refs = call('CAP buscar referencia', 'GET', cap, '/cap/references', headers=own, params={'search': doc})
        assert len(refs) == 1
        ids['id_cliente'] = refs[0]['id_cliente']
        reference = call('CAP detalle referencia', 'GET', cap, '/cap/references/'+ids['id_cliente'], headers=own)
        assert reference['id_caso'] == ids['id_caso']
        assert reference.get('apellido_materno') in (None, '')
        assert reference['estado_cliente'] == 'ACTIVO' and reference['estado_habilitante'] == 'HABILITADO'
        ids['id_verificacion'] = reference['id_verificacion']
        assert validate_reference(reference, ids['id_cliente'])['apellido_materno'] == ''
        call('CAP token incorrecto', 'GET', cap, '/cap/references', expected=401,
             headers={'Authorization': 'Bearer '+'invalid-lab-token-'*3})
        call('EVA credencial cruzada CAP', 'GET', eva, '/eva/operations/unknown-lab-operation', expected=401, headers=own)
        call('CAP id inexistente', 'GET', cap, '/cap/references/00000000-0000-0000-0000-000000000000', expected=404, headers=own)
        call('CAP JSON incompatible', 'POST', cap, prefix+'/solicitantes', expected=400, headers=human, json={'extra': 'invalid'})
        data('CAP revocar por API', 'POST', path+'/estado', json={'accion': 'REVOCAR', 'motivo': 'Ensayo sintetico de revocacion'})
        revoked = call('CAP referencia revocada explicita', 'GET', cap, '/cap/references/'+ids['id_cliente'], headers=own)
        assert revoked['estado_habilitante'] == 'REVOCADO'
        try:
            validate_reference(revoked, ids['id_cliente'])
        except HTTPException as exc:
            assert exc.status_code == 422
            rows.append({'case': 'Validador SOL rechaza referencia HTTP revocada', 'kind': 'local_contract_validation', 'status': 422, 'passed': True})
        else:
            raise AssertionError('SOL aceptó revocada')
        refs = call('CAP busqueda devuelve estado revocado', 'GET', cap, '/cap/references', headers=own, params={'search': doc})
        assert len(refs) == 1 and refs[0]['estado_habilitante'] == 'REVOCADO'
        result = {'status': 'passed', 'ids': ids, 'reference': {k: reference.get(k) for k in [
            'id_cliente', 'id_caso', 'id_verificacion', 'apellido_materno', 'estado_cliente',
            'estado_habilitante', 'fecha_verificacion', 'vigente_hasta', 'simulado']}, 'checks': rows}
    except Exception as exc:
        result = {'status': 'failed', 'failure_type': type(exc).__name__, 'ids': ids, 'checks': rows}
    finally:
        client.close()
    print(json.dumps(result, ensure_ascii=False))
    return int(result['status'] != 'passed')


if __name__ == '__main__':
    sys.exit(main())
