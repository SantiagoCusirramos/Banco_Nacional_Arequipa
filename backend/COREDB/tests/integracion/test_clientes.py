"""Rutas de clientes (CONTRATO_CLIENTES.md) contra la base real."""

import random
import re
import uuid

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app

BIOMETRIA = {"plantilla", "huella", "facial", "biometria", "template"}


@pytest.fixture
def cliente():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def servicio(autorizacion):
    """Encabezados y nombre del usuario de servicio del módulo Clientes."""
    api = TestClient(app)
    creado = api.post(
        "/coredb/usuarios/servicios",
        json={"modulo": "CLIENTES", "username": "svc-" + uuid.uuid4().hex[:10], "nombre": "Clientes"},
        headers=autorizacion,
    )
    assert creado.status_code == 201, creado.text
    cuerpo = creado.json()
    login = api.post(
        "/coredb/auth/login",
        json={"username": cuerpo["usuario"]["username"], "password": cuerpo["secreto"]},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, cuerpo["usuario"]["username"]


def digitos(n):
    return "".join(random.choice("0123456789") for _ in range(n))


def datos(**cambios):
    cuerpo = {
        "tipo_documento": "DNI",
        "numero_documento": digitos(8),
        "nombres": "Prueba",
        "apellido_paterno": "Integración",
        "apellido_materno": "Segundo",
        "correo": f"c{uuid.uuid4().hex[:12]}@example.com",
        "celular": "9" + digitos(8),
        "version_contrato": "v1",
        "estado_habilitante": "HABILITADO",
    }
    cuerpo.update(cambios)
    return cuerpo


def registrar(cliente, encabezados, **cambios):
    return cliente.post("/coredb/clientes", json=datos(**cambios), headers=encabezados)


def registrado(cliente, servicio, **cambios):
    """Registra un cliente con el usuario de servicio y devuelve (datos enviados, respuesta)."""
    cuerpo = datos(**cambios)
    respuesta = cliente.post("/coredb/clientes", json=cuerpo, headers=servicio[0])
    assert respuesta.status_code == 201, respuesta.text
    return cuerpo, respuesta.json()


def sin_datos_personales(texto, cuerpo):
    return all(cuerpo[campo] not in texto for campo in ("numero_documento", "correo", "celular"))


# ── Registro ─────────────────────────────────────────────────────────────────


def test_el_servicio_registra_un_cliente_habilitado(cliente, servicio, consulta):
    correlacion = str(uuid.uuid4())
    cuerpo = datos()
    respuesta = cliente.post(
        "/coredb/clientes", json=cuerpo, headers={**servicio[0], "X-Correlation-ID": correlacion}
    )
    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()
    assert set(creado) == {"cod_cliente", "estado_cliente", "estado_habilitante", "id_verificacion_captacion"}
    assert re.fullmatch(r"CLI\d{9}", creado["cod_cliente"])
    assert (creado["estado_cliente"], creado["estado_habilitante"]) == ("ACTIVO", "HABILITADO")
    assert respuesta.headers["x-correlation-id"] == correlacion
    fila = consulta(
        "SELECT numero_documento d, correo c, celular t, estado_cliente e FROM clientes.cliente "
        "WHERE cod_cliente=%s", creado["cod_cliente"],
    )
    assert fila == [{"d": cuerpo["numero_documento"], "c": cuerpo["correo"], "t": cuerpo["celular"], "e": "ACTIVO"}]
    evento = consulta(
        "SELECT actor, BIN_TO_UUID(correlation_id) c FROM core.evento_auditoria "
        "WHERE accion='REGISTRAR_CLIENTE' AND id_entidad=%s", creado["cod_cliente"],
    )
    assert evento == [{"actor": servicio[1], "c": correlacion}]


def test_sin_correlacion_la_api_genera_una_y_la_devuelve(cliente, servicio, consulta):
    respuesta = registrar(cliente, servicio[0])
    assert respuesta.status_code == 201
    generada = respuesta.headers["x-correlation-id"]
    assert str(uuid.UUID(generada)) == generada
    evento = consulta(
        "SELECT BIN_TO_UUID(correlation_id) c FROM core.evento_auditoria WHERE id_entidad=%s",
        respuesta.json()["cod_cliente"],
    )
    assert evento == [{"c": generada}]


def test_observado_da_un_cliente_observado(cliente, servicio):
    _, creado = registrado(cliente, servicio, estado_habilitante="OBSERVADO")
    assert (creado["estado_cliente"], creado["estado_habilitante"]) == ("OBSERVADO", "OBSERVADO")


@pytest.mark.parametrize("rol", ["ASESOR", "ADMINISTRADOR"])
def test_una_persona_solo_registra_observado(cliente, sesion_de, rol):
    encabezados, _ = sesion_de(rol)
    rechazado = registrar(cliente, encabezados)
    assert rechazado.status_code == 403
    assert rechazado.json()["error"]["code"] == "HABILITACION_NO_PERMITIDA"
    aceptado = registrar(cliente, encabezados, estado_habilitante="OBSERVADO")
    assert aceptado.status_code == 201, aceptado.text
    assert aceptado.json()["estado_cliente"] == "OBSERVADO"


def test_registrar_exige_token_y_permiso(cliente, sesion_de):
    assert registrar(cliente, {}).status_code == 401
    encabezados, _ = sesion_de("OPERADOR")
    respuesta = registrar(cliente, encabezados, estado_habilitante="OBSERVADO")
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_cada_duplicado_tiene_su_codigo_y_no_repite_el_valor(cliente, servicio):
    original, _ = registrado(cliente, servicio)
    casos = [
        ("CLIENTE_DUPLICADO", {"numero_documento": original["numero_documento"]}),
        ("CORREO_DUPLICADO", {"correo": original["correo"].upper()}),
        ("CELULAR_DUPLICADO", {"celular": original["celular"]}),
    ]
    for codigo, cambio in casos:
        respuesta = registrar(cliente, servicio[0], **cambio)
        assert respuesta.status_code == 409, respuesta.text
        assert respuesta.json()["error"]["code"] == codigo
        assert sin_datos_personales(respuesta.text.lower(), original)


def test_celular_invalido_se_rechaza_antes_de_la_base(cliente, servicio, consulta):
    correlacion = str(uuid.uuid4())
    respuesta = cliente.post(
        "/coredb/clientes", json=datos(celular="812345678"),
        headers={**servicio[0], "X-Correlation-ID": correlacion},
    )
    assert respuesta.status_code == 422
    assert "812345678" not in respuesta.text
    assert consulta(
        "SELECT COUNT(*) n FROM core.evento_auditoria WHERE correlation_id=UUID_TO_BIN(%s)", correlacion
    ) == [{"n": 0}]


@pytest.mark.parametrize("tipo, numero, estado", [
    ("DNI", "1234567", 422),            # siete dígitos
    ("DNI", "1234567A", 422),           # letras en un DNI
    ("CE", "ab1234567", 201),           # se pasa a mayúsculas
    ("CE", "12345678", 422),            # ocho caracteres
    ("PTP", "123456789", 201),
    ("PTP", "PTP202400", 422),          # el PTP es de nueve dígitos
    ("PASAPORTE", "AB1234", 201),
    ("LIBRETA", "12345678", 422),       # tipo desconocido
])
def test_reglas_de_cada_tipo_de_documento(cliente, servicio, consulta, tipo, numero, estado):
    if estado == 201:  # un número nuevo en cada corrida
        numero = numero[:2] + digitos(len(numero) - 2) if tipo != "PTP" else digitos(9)
    respuesta = registrar(cliente, servicio[0], tipo_documento=tipo, numero_documento=numero)
    assert respuesta.status_code == estado, respuesta.text
    if estado == 422:
        assert respuesta.json()["error"]["code"] == "BNA-DOCUMENTO"
        assert numero not in respuesta.text
    else:
        guardado = consulta(
            "SELECT numero_documento d FROM clientes.cliente WHERE cod_cliente=%s",
            respuesta.json()["cod_cliente"],
        )
        assert guardado == [{"d": numero.upper()}]


@pytest.mark.parametrize("cambio", [
    {"version_contrato": ""},
    {"nombres": ""},
    {"apellido_paterno": ""},
    {"correo": "sin-arroba"},
    {"estado_habilitante": "APROBADO"},
    {"numero_documento": 70000001},      # los textos van como cadenas JSON
    {"apellidos": "Un solo campo"},      # campo desconocido
])
def test_cuerpo_invalido_422_sin_repetir_valores(cliente, servicio, cambio):
    respuesta = registrar(cliente, servicio[0], **cambio)
    assert respuesta.status_code == 422, respuesta.text
    for valor in cambio.values():
        if valor:
            assert str(valor) not in respuesta.text


def test_el_apellido_materno_es_opcional(cliente, servicio, consulta):
    _, creado = registrado(cliente, servicio, apellido_materno=None)
    assert consulta(
        "SELECT apellido_materno a FROM clientes.cliente WHERE cod_cliente=%s", creado["cod_cliente"]
    ) == [{"a": None}]


# ── Consulta ─────────────────────────────────────────────────────────────────


def test_consultar_un_cliente_sin_biometria(cliente, servicio, sesion_de):
    enviado, creado = registrado(cliente, servicio)
    auditor, _ = sesion_de("AUDITOR")
    respuesta = cliente.get(f"/coredb/clientes/{creado['cod_cliente']}", headers=auditor)
    assert respuesta.status_code == 200, respuesta.text
    vista = respuesta.json()
    assert set(vista) == {
        "cod_cliente", "tipo_documento", "numero_documento", "nombres", "apellido_paterno",
        "apellido_materno", "correo", "celular", "estado_cliente", "permite_operar",
        "version_contrato", "id_verificacion_captacion", "estado_habilitante", "fecha_verificacion",
    }
    assert not BIOMETRIA & set(vista)
    assert vista["numero_documento"] == enviado["numero_documento"]
    assert vista["permite_operar"] is True
    assert vista["fecha_verificacion"].endswith("Z")


def test_consultar_un_cliente_inexistente_404(cliente, autorizacion):
    respuesta = cliente.get("/coredb/clientes/CLI999999999", headers=autorizacion)
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "CLIENTE_NO_ENCONTRADO"


def test_consultar_exige_token(cliente):
    assert cliente.get("/coredb/clientes/DEV001").status_code == 401


# ── Verificación por documento ───────────────────────────────────────────────


def verificar(cliente, encabezados, cuerpo, verificada, motivo=None, **extra):
    return cliente.post(
        "/coredb/clientes/validaciones/documento",
        json={"tipo_documento": cuerpo["tipo_documento"], "numero_documento": cuerpo["numero_documento"],
              "identidad_verificada": verificada, "motivo": motivo},
        headers={**encabezados, **extra},
    )


def test_sin_identidad_verificada_cliente_y_no_cliente_responden_igual(cliente, servicio):
    existente, _ = registrado(cliente, servicio)
    de_cliente = verificar(cliente, servicio[0], existente, False, "RENIEC_NO_COINCIDE")
    de_nadie = verificar(cliente, servicio[0], datos(), False, "RENIEC_NO_COINCIDE")
    assert de_cliente.status_code == de_nadie.status_code == 201
    uno, otro = de_cliente.json(), de_nadie.json()
    assert uno.pop("id_validacion") != otro.pop("id_validacion")
    assert uno == otro == {"resultado": "RECHAZADO", "motivo": "IDENTIDAD_NO_VERIFICADA", "cliente": None}


def test_identidad_verificada_de_un_cliente_activo(cliente, servicio, consulta):
    existente, creado = registrado(cliente, servicio)
    correlacion = str(uuid.uuid4())
    respuesta = verificar(cliente, servicio[0], existente, True, **{"X-Correlation-ID": correlacion})
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("APROBADO", None)
    assert cuerpo["cliente"]["cod_cliente"] == creado["cod_cliente"]
    assert not BIOMETRIA & set(cuerpo["cliente"])
    fila = consulta(
        "SELECT tipo_validacion t, resultado r, cod_cliente c, BIN_TO_UUID(correlation_id) x "
        "FROM clientes.validacion_identidad WHERE id_validacion=%s", cuerpo["id_validacion"],
    )
    assert fila == [{"t": "DOCUMENTO", "r": "APROBADO", "c": creado["cod_cliente"], "x": correlacion}]


def test_identidad_verificada_de_quien_no_es_cliente(cliente, servicio):
    respuesta = verificar(cliente, servicio[0], datos(), True)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["cliente"]) == ("RECHAZADO", "NO_ES_CLIENTE", None)


def test_identidad_verificada_de_un_cliente_bloqueado(cliente, servicio):
    existente, creado = registrado(cliente, servicio)
    bloqueo = cliente.post(
        f"/coredb/clientes/{creado['cod_cliente']}/estado",
        json={"estado": "BLOQUEADO", "motivo": "Prueba"}, headers=servicio[0],
    )
    assert bloqueo.status_code == 200, bloqueo.text
    cuerpo = verificar(cliente, servicio[0], existente, True).json()
    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("RECHAZADO", "CLIENTE_NO_ACTIVO")
    assert cuerpo["cliente"]["estado_cliente"] == "BLOQUEADO"


def test_verificar_un_documento_exige_validar_identidad(cliente, sesion_de, autorizacion):
    for encabezados in (sesion_de("OPERADOR")[0], autorizacion):
        respuesta = verificar(cliente, encabezados, datos(), True)
        assert respuesta.status_code == 403
        assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"
    assert verificar(cliente, {}, datos(), True).status_code == 401


def test_verificar_un_documento_valida_el_cuerpo(cliente, servicio):
    url = "/coredb/clientes/validaciones/documento"
    sin_campo = cliente.post(url, json={"tipo_documento": "DNI", "numero_documento": "70000001"},
                             headers=servicio[0])
    assert sin_campo.status_code == 422
    largo = cliente.post(
        url, json={"tipo_documento": "DNI", "numero_documento": "7" * 13, "identidad_verificada": True},
        headers=servicio[0],
    )
    assert largo.status_code == 422


# ── Otras validaciones ───────────────────────────────────────────────────────


def test_registrar_la_validacion_de_una_huella(cliente, servicio, consulta):
    _, creado = registrado(cliente, servicio)
    correlacion = str(uuid.uuid4())
    respuesta = cliente.post(
        f"/coredb/clientes/{creado['cod_cliente']}/validaciones",
        json={"tipo_validacion": "HUELLA", "resultado": "RECHAZADO", "motivo": "SIMILITUD_BAJA"},
        headers={**servicio[0], "X-Correlation-ID": correlacion},
    )
    assert respuesta.status_code == 201, respuesta.text
    fila = consulta(
        "SELECT tipo_validacion t, resultado r, cod_cliente c, BIN_TO_UUID(correlation_id) x "
        "FROM clientes.validacion_identidad WHERE id_validacion=%s", respuesta.json()["id_validacion"],
    )
    assert fila == [{"t": "HUELLA", "r": "RECHAZADO", "c": creado["cod_cliente"], "x": correlacion}]


def test_la_validacion_de_documento_no_entra_por_esta_ruta(cliente, servicio):
    _, creado = registrado(cliente, servicio)
    for cuerpo in ({"tipo_validacion": "DOCUMENTO", "resultado": "APROBADO"},
                   {"tipo_validacion": "HUELLA", "resultado": "DUDOSO"},
                   {"tipo_validacion": "IRIS", "resultado": "APROBADO"}):
        respuesta = cliente.post(
            f"/coredb/clientes/{creado['cod_cliente']}/validaciones", json=cuerpo, headers=servicio[0]
        )
        assert respuesta.status_code == 422, respuesta.text


def test_validacion_de_un_cliente_inexistente_404(cliente, servicio):
    respuesta = cliente.post(
        "/coredb/clientes/CLI999999999/validaciones",
        json={"tipo_validacion": "FACIAL", "resultado": "APROBADO"}, headers=servicio[0],
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "CLIENTE_NO_ENCONTRADO"


# ── Cambio de estado ─────────────────────────────────────────────────────────


def cambiar(cliente, encabezados, cod_cliente, **cuerpo):
    return cliente.post(f"/coredb/clientes/{cod_cliente}/estado", json=cuerpo, headers=encabezados)


def test_bloquear_un_cliente_bloquea_sus_tarjetas(cliente, servicio, autorizacion, consulta):
    _, creado = registrado(cliente, servicio)
    cod = creado["cod_cliente"]
    sufijo = uuid.uuid4().int % 10**16
    cuenta = cliente.post("/coredb/cuentas", headers=autorizacion, json={
        "num_cuenta": f"CTA-{sufijo:016d}", "cci": f"{sufijo:020d}", "moneda": "PEN",
        "regimen": "INDIVIDUAL", "id_agencia": "AQP01", "titulares": [cod],
    })
    assert cuenta.status_code == 201, cuenta.text
    tarjeta = cliente.post("/coredb/tarjetas", headers=autorizacion, json={
        "pan_token": uuid.uuid4().hex, "bin": "004499", "ultimos4": "1234",
        "fecha_emision": "2026-01-01", "fecha_vencimiento": "2030-01-01",
        "cod_cliente": cod, "num_cuenta": cuenta.json()["num_cuenta"],
    })
    assert tarjeta.status_code == 201, tarjeta.text
    id_tarjeta = tarjeta.json()["id_tarjeta"]

    respuesta = cambiar(cliente, servicio[0], cod, estado="BLOQUEADO", motivo="Investigación de fraude")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["estado_anterior"], cuerpo["estado_cliente"], cuerpo["permite_operar"]) == (
        "ACTIVO", "BLOQUEADO", False)
    historial = consulta(
        "SELECT estado_nuevo e, origen o FROM tarjetas.historial_estado_tarjeta "
        "WHERE id_tarjeta=UUID_TO_BIN(%s) ORDER BY id_historial DESC LIMIT 1", id_tarjeta,
    )
    assert historial == [{"e": "BLOQUEADA", "o": "MODULO_CLIENTES"}]
    evento = consulta(
        "SELECT actor, JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.motivo')) m FROM core.evento_auditoria "
        "WHERE accion='CAMBIAR_ESTADO_CLIENTE' AND id_entidad=%s", cod,
    )
    assert evento == [{"actor": servicio[1], "m": "Investigación de fraude"}]

    # Reactivar al cliente no desbloquea la tarjeta: eso es de Seguridad.
    assert cambiar(cliente, servicio[0], cod, estado="ACTIVO", motivo="Cerrada").status_code == 200
    estado = cliente.get(f"/coredb/tarjetas/{id_tarjeta}", headers=autorizacion).json()["estado_tarjeta"]
    assert estado == "BLOQUEADA"


def test_el_cambio_de_estado_exige_un_motivo(cliente, servicio):
    _, creado = registrado(cliente, servicio)
    for cuerpo in ({"estado": "BLOQUEADO"}, {"estado": "BLOQUEADO", "motivo": ""},
                   {"estado": "BLOQUEADO", "motivo": "   "}):
        respuesta = cambiar(cliente, servicio[0], creado["cod_cliente"], **cuerpo)
        assert respuesta.status_code == 422, respuesta.text


def test_la_baja_es_final_y_solo_la_fija_una_persona(cliente, servicio, sesion_de):
    _, creado = registrado(cliente, servicio)
    cod = creado["cod_cliente"]
    del_servicio = cambiar(cliente, servicio[0], cod, estado="BAJA", motivo="Pedido del cliente")
    assert del_servicio.status_code == 403
    assert del_servicio.json()["error"]["code"] == "PERMISO_DENEGADO"
    asesor, _ = sesion_de("ASESOR")
    baja = cambiar(cliente, asesor, cod, estado="BAJA", motivo="Pedido del cliente")
    assert baja.status_code == 200, baja.text
    assert baja.json()["estado_cliente"] == "BAJA"
    despues = cambiar(cliente, asesor, cod, estado="ACTIVO", motivo="Arrepentido")
    assert despues.status_code == 422
    assert despues.json()["error"]["code"] == "BNA-ESTADO"


def test_el_mismo_estado_no_deja_un_evento(cliente, servicio, consulta):
    _, creado = registrado(cliente, servicio)
    respuesta = cambiar(cliente, servicio[0], creado["cod_cliente"], estado="ACTIVO", motivo="Sin cambio")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado_anterior"] == respuesta.json()["estado_cliente"] == "ACTIVO"
    assert consulta(
        "SELECT COUNT(*) n FROM core.evento_auditoria WHERE accion='CAMBIAR_ESTADO_CLIENTE' AND id_entidad=%s",
        creado["cod_cliente"],
    ) == [{"n": 0}]


def test_estado_desconocido_y_cliente_inexistente(cliente, servicio):
    _, creado = registrado(cliente, servicio)
    desconocido = cambiar(cliente, servicio[0], creado["cod_cliente"], estado="CONGELADO", motivo="x")
    assert desconocido.status_code == 422
    inexistente = cambiar(cliente, servicio[0], "CLI999999999", estado="BLOQUEADO", motivo="x")
    assert inexistente.status_code == 404
    assert inexistente.json()["error"]["code"] == "CLIENTE_NO_ENCONTRADO"


def test_cambiar_el_estado_exige_permiso(cliente, sesion_de):
    operador, _ = sesion_de("OPERADOR")
    assert cambiar(cliente, operador, "DEV001", estado="BLOQUEADO", motivo="x").status_code == 403
    assert cambiar(cliente, {}, "DEV001", estado="BLOQUEADO", motivo="x").status_code == 401


# ── Catálogos ────────────────────────────────────────────────────────────────


def test_catalogos_de_clientes(cliente, sesion_de):
    operador, _ = sesion_de("OPERADOR")
    respuesta = cliente.get("/coredb/catalogos/clientes", headers=operador)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    tipos = {t["codigo"]: t for t in cuerpo["tipos_documento"]}
    assert set(tipos) == {"DNI", "CE", "PTP", "PASAPORTE"}
    assert tipos["DNI"] == {"codigo": "DNI", "descripcion": tipos["DNI"]["descripcion"],
                            "longitud_min": 8, "longitud_max": 8, "es_alfanumerico": False}
    assert (tipos["PTP"]["longitud_min"], tipos["PTP"]["es_alfanumerico"]) == (9, False)
    estados = {e["codigo"]: e["permite_operar"] for e in cuerpo["estados_cliente"]}
    assert estados == {"ACTIVO": True, "OBSERVADO": True, "BLOQUEADO": False, "SUSPENDIDO": False, "BAJA": False}
    assert cliente.get("/coredb/catalogos/clientes").status_code == 401
