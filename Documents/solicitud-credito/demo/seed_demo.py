"""Synthetic presentation cases through existing SOL APIs and the Next proxy only."""
import os
import time
from uuid import uuid4
import httpx
from SOL.clock import business_today

SCENARIOS = [('Borrador', None), ('En evaluacion', 'PENDING'), ('Observada', 'OBSERVADO'),
             ('Aprobada', 'APROBADO'), ('Rechazada', 'RECHAZADO'), ('Subsanacion v2', 'REVISE')]


def main():
    origin = os.environ['DEMO_ORIGIN']
    with httpx.Client(base_url='http://frontend:3000/api/solicitud-credito/',
                      headers={'Origin': origin}, timeout=15, trust_env=False) as c:
        def request(method, path, expected=200, **kwargs):
            response = c.request(method, path, **kwargs)
            if response.status_code != expected:
                raise RuntimeError(f'Demo HTTP {method} {path.split("/")[0]}: {response.status_code}')
            if path == 'auth/login':
                assert 'httponly' in response.headers.get('set-cookie', '').lower()
            return response.json()

        def login(user):
            result = request('POST', 'auth/login', json={'username': user, 'password': os.environ['DEMO_LOGIN_PASSWORD']})
            assert 'token' not in result, 'Proxy no debe exponer token al navegador'
            assert c.cookies.get('bna_sol_session')

        def pending(path):
            for _ in range(60):
                result = request('GET', path)
                if result['estado'] == 'EN_EVALUACION':
                    return result
                time.sleep(0.5)
            raise RuntimeError('La entrega SIMULADA no finalizo a tiempo.')

        login('asesor.bna')
        assert request('GET', 'policy')['integracion'] == 'SIMULADO'
        # Existing titles make retries resume without cloning presentation cases.
        existing = {}
        for row in request('GET', 'applications?limit=100')['items']:
            detail = request('GET', 'applications/'+row['id'])
            title = detail['versiones'][-1]['expediente']['condiciones']['destino_credito']
            existing[title] = detail
        for name, result in SCENARIOS:
            title = 'DEMO SOL - '+name
            login('asesor.bna')
            payload = {'id_cliente': '0198b000-0000-7009-8000-000000000001',
                       'monto_solicitado': '15000.00', 'moneda': 'PEN', 'plazo_meses': 12,
                       'fecha_base': business_today().isoformat(), 'destino_credito': title,
                       'garantias': [{'tipo_garantia': 'VEHICULAR', 'descripcion': 'Vehiculo sintetico de demostracion', 'valor_tasacion': '12000.00'}],
                       'fiadores': ['0198b000-0000-7009-8000-000000000002']}
            detail = existing.get(title)
            if detail is None:
                preview = request('POST', 'preview', json=payload)
                assert preview['calendario']['cuotas'][-1]['saldo_final'] == '0.00'
                detail = request('POST', 'applications', 201, json=payload)
            path = 'applications/'+detail['id']
            desired = {'PENDING': 'EN_EVALUACION', 'OBSERVADO': 'OBSERVADA',
                       'APROBADO': 'APROBADA', 'RECHAZADO': 'RECHAZADA', 'REVISE': 'BORRADOR'}.get(result, 'BORRADOR')
            if detail['estado'] == desired and (result != 'REVISE' or detail['version'] == 2):
                continue
            if result:
                if detail['estado'] == 'BORRADOR':
                    # SIMULADO accepts immediately (200); REAL queues with 202.
                    request('POST', path+'/send', 200, json={'revision': detail['revision']},
                            headers={'X-Idempotency-Key': str(uuid4())})
                    detail = pending(path)
                elif detail['estado'] in {'LISTA_ENVIO', 'PENDIENTE_ENVIO'}:
                    detail = pending(path)
                if result != 'PENDING':
                    if detail['estado'] == 'EN_EVALUACION':
                        login('evaluador.demo')
                        decision = 'OBSERVADO' if result == 'REVISE' else result
                        detail = request('POST', path+'/demo-result', json={'version': detail['version'], 'decision': decision,
                            'observaciones': 'Resultado SIMULADO de presentacion; sin validez institucional.'},
                            headers={'X-Idempotency-Key': str(uuid4())})
                    if result == 'REVISE' and detail['estado'] == 'OBSERVADA':
                        frozen = detail['versiones'][0]
                        login('asesor.bna')
                        detail = request('POST', path+'/revise', json={'revision': detail['revision']})
                        assert detail['version'] == 2 and detail['versiones'][0] == frozen
            assert detail['estado'] == desired
            print('Escenario preparado:', name)
        login('asesor.bna')
        page = request('GET', 'applications?limit=100')
        assert page['total'] >= 6
        request('POST', 'auth/logout')
    print('DEMO SIMULADA lista: frontend, cookie HttpOnly, calendario y seis escenarios comprobados.')


if __name__ == '__main__':
    main()
