"""Acceso de clientes y rutas de la Billetera Digital, sin base (bd-v1.9)."""

import jwt
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from COREDB import permisos, tokens
from COREDB.auth import cliente_actual
from COREDB.errores import ErrorAutenticacion
from COREDB.main import app


PREFIJO = "/coredb/billetera"


def _dependencias(dependant):
    for dependencia in dependant.dependencies:
        yield dependencia.call
        yield from _dependencias(dependencia)

# Las que no actúan por un cliente: el acceso (que lo autentica) y las del personal del banco.
RUTAS_SIN_CLIENTE = {
    ("POST", f"{PREFIJO}/acceso"),
    ("POST", f"{PREFIJO}/afiliaciones"),
    ("POST", f"{PREFIJO}/comercios"),
}


def _rutas_billetera():
    for ruta in app.routes:
        if isinstance(ruta, APIRoute) and ruta.path.startswith(PREFIJO):
            for metodo in ruta.methods:
                yield metodo, ruta


def test_el_token_de_cliente_lleva_el_rol_cliente_y_su_codigo():
    token, vigencia = tokens.crear_token_cliente(cod_cliente="C001")
    claims = tokens.decodificar_cliente(token)
    assert claims["sub"] == "C001"
    assert claims["rol"] == "CLIENTE"
    assert vigencia > 0


def test_un_token_de_cliente_no_sirve_como_token_del_personal_ni_al_reves():
    token_cliente, _ = tokens.crear_token_cliente(cod_cliente="C001")
    with pytest.raises(ErrorAutenticacion):
        tokens.decodificar(token_cliente)
    import uuid

    token_personal, _ = tokens.crear_token(
        id_usuario=uuid.uuid4(), username="admin", rol="ADMINISTRADOR", modulo=None
    )
    with pytest.raises(ErrorAutenticacion):
        tokens.decodificar_cliente(token_personal)


def test_un_token_de_cliente_con_otra_firma_no_sirve():
    token, _ = tokens.crear_token_cliente(cod_cliente="C001")
    claims = jwt.decode(token, options={"verify_signature": False})
    falso = jwt.encode(claims, "otra-clave-de-al-menos-treinta-y-dos-caracteres", algorithm="HS256")
    with pytest.raises(ErrorAutenticacion):
        tokens.decodificar_cliente(falso)


def test_solo_el_modulo_billetera_opera_por_un_cliente():
    con_operar = {rol for rol, acciones in permisos.PERMISOS.items() if "OPERAR_BILLETERA" in acciones}
    # El administrador tiene todas las acciones; sin el token del cliente no actúa por él.
    assert con_operar == {"SERVICIO:BILLETERA", "ADMINISTRADOR"}
    assert permisos.PERMISOS["SERVICIO:BILLETERA"] == {"OPERAR_BILLETERA"}
    con_afiliar = {rol for rol, acciones in permisos.PERMISOS.items() if "AFILIAR_BILLETERA" in acciones}
    assert con_afiliar == {"ADMINISTRADOR", "ASESOR", "OPERADOR"}
    con_comercio = {rol for rol, acciones in permisos.PERMISOS.items() if "REGISTRAR_COMERCIO" in acciones}
    assert con_comercio == {"ADMINISTRADOR", "OPERADOR"}


def test_toda_ruta_de_la_billetera_actua_por_un_cliente_salvo_el_acceso_y_las_del_banco():
    rutas = list(_rutas_billetera())
    assert len(rutas) > len(RUTAS_SIN_CLIENTE)
    assert {(m, r.path) for m, r in rutas} >= RUTAS_SIN_CLIENTE
    for metodo, ruta in rutas:
        con_cliente = cliente_actual in set(_dependencias(ruta.dependant))
        assert con_cliente == ((metodo, ruta.path) not in RUTAS_SIN_CLIENTE), (metodo, ruta.path)


def test_el_celular_nunca_va_en_la_ruta_ni_en_la_consulta():
    # Las rutas y consultas quedan en los registros de acceso; el celular va en el cuerpo.
    for _, ruta in _rutas_billetera():
        nombres = {p.name for p in ruta.dependant.path_params + ruta.dependant.query_params}
        assert not {n for n in nombres if "celular" in n}, ruta.path


def test_las_operaciones_de_dinero_exigen_la_llave_de_idempotencia():
    exigida = {}
    for metodo, ruta in _rutas_billetera():
        for parametro in ruta.dependant.header_params:
            if parametro.alias == "X-Idempotency-Key":
                exigida[(metodo, ruta.path)] = parametro.required
    assert exigida == {
        ("POST", f"{PREFIJO}/transferencias"): True,
        ("POST", f"{PREFIJO}/qr/{{id_qr}}/pagos"): True,
        # Solo ACEPTAR mueve dinero: la ruta la exige para esa acción (422 LLAVE_REQUERIDA).
        ("POST", f"{PREFIJO}/solicitudes/{{id_solicitud}}/respuesta"): False,
    }


def test_sin_token_de_cliente_no_entra():
    respuesta = TestClient(app).get(f"{PREFIJO}/yo")
    assert respuesta.status_code == 401
