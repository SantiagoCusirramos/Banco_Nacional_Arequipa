"""Quién entra a las rutas del personal: COREDB valida el token y Evaluación lo reenvía."""
import pytest

from EVALUACION.tests.ayudas import (SERVICIO_SECRETO, SERVICIO_USUARIO, cabeceras, evaluar, login, nuevo_sobre,
                                     persona, recibir)

RUTAS_LECTURA = ["/eva/v1/solicitudes", "/eva/v1/aprobaciones", "/eva/v1/catalogo", "/eva/v1/resultados-sol"]


def test_sin_token_o_con_token_invalido(api):
    for ruta in RUTAS_LECTURA:
        r = api.get(ruta)
        assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_REQUERIDO"
    r = api.get("/eva/v1/solicitudes", headers=cabeceras("token-que-no-firmo-coredb"))
    assert r.status_code == 401 and r.json()["error"]["code"] == "SESION_INVALIDA"


def test_el_usuario_de_servicio_no_entra_a_las_rutas_del_personal(api):
    token = login(SERVICIO_USUARIO, SERVICIO_SECRETO)
    for ruta in RUTAS_LECTURA:
        r = api.get(ruta, headers=cabeceras(token))
        assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO"


@pytest.mark.parametrize("rol", ["AUDITOR", "OPERADOR", "ASESOR"])
def test_lectura_sin_evaluar(api, admin, cliente, rol):
    token, _ = persona(admin, rol)
    sobre = nuevo_sobre(cliente)
    recibir(api, sobre)
    assert api.get(f"/eva/v1/solicitudes/{sobre['idSolicitud']}", headers=cabeceras(token)).status_code == 200
    r = evaluar(api, token, sobre["idSolicitud"], "5000.00")
    assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO"
    r = api.post(f"/eva/v1/solicitudes/{sobre['idSolicitud']}/revocacion", headers=cabeceras(token),
                 json={"motivo": "Motivo de una revocación."})
    assert r.status_code == 403


def test_campos_desconocidos_se_rechazan(api, analista, cliente):
    sobre = nuevo_sobre(cliente)
    recibir(api, sobre)
    r = api.post(f"/eva/v1/solicitudes/{sobre['idSolicitud']}/evaluaciones", headers=cabeceras(analista[0]),
                 json={"versionSolicitud": 1, "ingresoMensual": "5000.00", "deudaMensual": "0.00",
                       "riesgo": "BUENO", "verificada": True, "score": 999})
    assert r.status_code == 422
