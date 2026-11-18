"""Billetera Digital contra la base (bd-v1.9): acceso de clientes con rol CLIENTE y su
credencial, y las rutas /coredb/billetera/* sobre los procedimientos billetera.*."""

import random
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app

B = "/coredb/billetera"


@pytest.fixture
def api():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def servicio_billetera(autorizacion):
    """El usuario de servicio del módulo BILLETERA (Chaski), con sesión."""
    cliente = TestClient(app)
    username = "svc-bd-" + uuid.uuid4().hex[:8]
    creado = cliente.post("/coredb/usuarios/servicios", headers=autorizacion,
                          json={"modulo": "BILLETERA", "username": username, "nombre": "Billetera"})
    assert creado.status_code == 201, creado.text
    login = cliente.post("/coredb/auth/login",
                         json={"username": username, "password": creado.json()["secreto"]})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def billetera(api, autorizacion, admin, abrir_cuenta, datos_base):
    """Un cliente ACTIVO nuevo con una cuenta en soles (saldo inicial) afiliado por el banco."""

    def _crear(saldo="300.00", pin="246810", nombres="Rosa Elena", apellido="Quispe"):
        cod = "W" + uuid.uuid4().hex[:11].upper()
        celular = "9" + "".join(random.choice("0123456789") for _ in range(8))
        with admin.cursor() as cursor:
            cursor.execute("INSERT INTO clientes.verificacion_captacion (id_verificacion_captacion, "
                           "estado_habilitante) VALUES (%s, 'HABILITADO')", (f"VC-{cod}",))
            cursor.execute(
                "INSERT INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, "
                "apellido_paterno, correo, celular, estado_cliente, id_verificacion_captacion, "
                "version_contrato) VALUES (%s, 'DNI', %s, %s, %s, %s, %s, 'ACTIVO', %s, 'v1')",
                (cod, f"{random.randrange(10**7, 10**8)}", nombres, apellido, f"{cod.lower()}@example.com",
                 celular, f"VC-{cod}"),
            )
        num_cuenta = abrir_cuenta(titular=cod)
        deposito = api.post("/coredb/movimientos", headers=autorizacion, json={
            "num_cuenta": num_cuenta, "tipo": "DEPOSITO", "monto": saldo, "glosa": "g", "id_canal": "VEN"})
        assert deposito.status_code == 201, deposito.text
        afiliada = api.post(f"{B}/afiliaciones", headers=autorizacion,
                            json={"cod_cliente": cod, "num_cuenta": num_cuenta, "pin": pin})
        assert afiliada.status_code == 201, afiliada.text
        return {"cod": cod, "celular": celular, "pin": pin, "num_cuenta": num_cuenta}

    return _crear


@pytest.fixture
def sesion(api, servicio_billetera):
    """Encabezados de Chaski actuando por el cliente: su token de servicio y el del cliente."""

    def _sesion(datos):
        acceso = api.post(f"{B}/acceso", headers=servicio_billetera,
                          json={"celular": datos["celular"], "pin": datos["pin"]})
        assert acceso.status_code == 200, acceso.text
        return {**servicio_billetera, "X-Cliente-Token": acceso.json()["access_token"]}

    return _sesion


def saldo(api, encabezados):
    respuesta = api.get(f"{B}/yo", headers=encabezados)
    assert respuesta.status_code == 200, respuesta.text
    return Decimal(respuesta.json()["saldo_disponible"])


def llave():
    return {"X-Idempotency-Key": str(uuid.uuid4())}


# --- Afiliación y acceso -------------------------------------------------------------

def test_el_banco_afilia_y_el_cliente_entra_con_celular_y_pin(api, billetera, sesion, servicio_billetera):
    datos = billetera(nombres="Rosa Elena")
    acceso = api.post(f"{B}/acceso", headers=servicio_billetera,
                      json={"celular": datos["celular"], "pin": datos["pin"]})
    assert acceso.status_code == 200, acceso.text
    cuerpo = acceso.json()
    assert cuerpo["token_type"] == "bearer" and cuerpo["expires_in"] > 0
    assert cuerpo["cliente"] == {"cod_cliente": datos["cod"], "nombre_corto": "Rosa Q."}
    yo = api.get(f"{B}/yo", headers={**servicio_billetera, "X-Cliente-Token": cuerpo["access_token"]})
    assert yo.status_code == 200, yo.text
    perfil = yo.json()
    assert perfil["num_cuenta"] == datos["num_cuenta"]
    assert Decimal(perfil["saldo_disponible"]) == Decimal("300.00")
    assert Decimal(perfil["tope_diario"]) == Decimal("500.00")
    assert Decimal(perfil["disponible_hoy"]) == Decimal("500.00")
    assert "celular" not in perfil


def test_pin_equivocado_y_celular_desconocido_responden_lo_mismo(api, billetera, servicio_billetera):
    datos = billetera()
    equivocado = api.post(f"{B}/acceso", headers=servicio_billetera,
                          json={"celular": datos["celular"], "pin": "000000"})
    desconocido = api.post(f"{B}/acceso", headers=servicio_billetera,
                           json={"celular": "900000001", "pin": "000000"})
    assert equivocado.status_code == desconocido.status_code == 401
    assert equivocado.json() == desconocido.json()
    assert equivocado.json()["error"]["code"] == "CREDENCIALES_INVALIDAS"


def test_al_tercer_pin_equivocado_se_bloquea_y_corta_la_sesion_abierta(api, billetera, sesion, servicio_billetera):
    datos = billetera()
    abierta = sesion(datos)
    for pin in ("000000", "000001", "000002"):
        api.post(f"{B}/acceso", headers=servicio_billetera, json={"celular": datos["celular"], "pin": pin})
    bloqueada = api.post(f"{B}/acceso", headers=servicio_billetera,
                         json={"celular": datos["celular"], "pin": datos["pin"]})
    assert bloqueada.status_code == 403
    assert bloqueada.json()["error"]["code"] == "BILLETERA_BLOQUEADA"
    assert api.get(f"{B}/yo", headers=abierta).status_code == 401
    # El banco la reactiva afiliándola otra vez (cambio de PIN).
    otra_vez = api.post(f"{B}/afiliaciones", headers={"Authorization": abierta["Authorization"]},
                        json={"cod_cliente": datos["cod"], "num_cuenta": datos["num_cuenta"], "pin": "135790"})
    assert otra_vez.status_code == 403  # el servicio no afilia


def test_reafiliar_desbloquea(api, billetera, autorizacion, servicio_billetera):
    datos = billetera()
    for pin in ("000000", "000001", "000002"):
        api.post(f"{B}/acceso", headers=servicio_billetera, json={"celular": datos["celular"], "pin": pin})
    reafiliada = api.post(f"{B}/afiliaciones", headers=autorizacion,
                          json={"cod_cliente": datos["cod"], "num_cuenta": datos["num_cuenta"], "pin": "135790"})
    assert reafiliada.status_code == 201, reafiliada.text
    assert reafiliada.json()["nueva"] is False
    acceso = api.post(f"{B}/acceso", headers=servicio_billetera,
                      json={"celular": datos["celular"], "pin": "135790"})
    assert acceso.status_code == 200, acceso.text


def test_la_afiliacion_respeta_las_reglas_de_la_base(api, autorizacion, abrir_cuenta, datos_base):
    cuenta_ajena = abrir_cuenta(titular="C002")
    respuesta = api.post(f"{B}/afiliaciones", headers=autorizacion,
                         json={"cod_cliente": "C001", "num_cuenta": cuenta_ajena, "pin": "123456"})
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-BILLETERA-TITULAR"
    corto = api.post(f"{B}/afiliaciones", headers=autorizacion,
                     json={"cod_cliente": "C001", "num_cuenta": cuenta_ajena, "pin": "12345"})
    assert corto.status_code == 422


def test_sin_token_de_cliente_o_con_otro_modulo_no_se_opera(api, autorizacion, sesion_de, billetera, sesion):
    datos = billetera()
    sin_cliente = api.get(f"{B}/yo", headers=autorizacion)
    assert sin_cliente.status_code == 401
    assert sin_cliente.json()["error"]["code"] == "CLIENTE_TOKEN_REQUERIDO"
    asesor, _ = sesion_de("ASESOR")
    acceso = api.post(f"{B}/acceso", headers=asesor, json={"celular": datos["celular"], "pin": datos["pin"]})
    assert acceso.status_code == 403
    assert acceso.json()["error"]["code"] == "PERMISO_DENEGADO"
    # El token del cliente no sirve como token del personal.
    encabezados = sesion(datos)
    como_personal = api.get("/coredb/catalogos/monedas",
                            headers={"Authorization": f"Bearer {encabezados['X-Cliente-Token']}"})
    assert como_personal.status_code == 401


# --- Envíos -------------------------------------------------------------------------

def test_un_envio_por_celular_mueve_el_dinero_una_vez_aunque_se_repita(api, billetera, sesion):
    ana, luis = billetera(nombres="Ana", apellido="Diaz"), billetera(nombres="Luis", apellido="Rojas")
    s_ana, s_luis = sesion(ana), sesion(luis)
    clave = llave()
    cuerpo = {"celular_destino": luis["celular"], "monto": "45.50", "referencia": "Almuerzo"}
    primero = api.post(f"{B}/transferencias", headers={**s_ana, **clave}, json=cuerpo)
    assert primero.status_code == 201, primero.text
    operacion = primero.json()
    assert operacion["repetido"] is False
    assert operacion["tipo"] == "P2P" and Decimal(operacion["monto"]) == Decimal("45.50")
    assert operacion["nombre_destino"] == "Luis R."
    repetido = api.post(f"{B}/transferencias", headers={**s_ana, **clave}, json=cuerpo)
    assert repetido.status_code == 201, repetido.text
    assert repetido.json()["repetido"] is True
    assert repetido.json()["id_operacion"] == operacion["id_operacion"]
    assert saldo(api, s_ana) == Decimal("254.50")
    assert saldo(api, s_luis) == Decimal("345.50")
    otro_monto = api.post(f"{B}/transferencias", headers={**s_ana, **clave}, json={**cuerpo, "monto": "1.00"})
    assert otro_monto.status_code == 409
    assert otro_monto.json()["error"]["code"] == "BNA-IDEMPOTENCIA"


def test_el_envio_exige_llave_y_un_destino_con_billetera(api, billetera, sesion):
    ana = billetera()
    s_ana = sesion(ana)
    sin_llave = api.post(f"{B}/transferencias", headers=s_ana,
                         json={"celular_destino": "959000002", "monto": "1.00"})
    assert sin_llave.status_code == 422
    sin_billetera = api.post(f"{B}/transferencias", headers={**s_ana, **llave()},
                             json={"celular_destino": "959000002", "monto": "1.00"})
    assert sin_billetera.status_code == 404
    assert sin_billetera.json()["error"]["code"] == "BNA-BILLETERA-DESTINO"
    assert "959000002" not in sin_billetera.text


def test_buscar_un_contacto_devuelve_solo_su_nombre_corto(api, billetera, sesion):
    ana, luis = billetera(), billetera(nombres="Luis Alberto", apellido="Rojas")
    s_ana = sesion(ana)
    hallado = api.post(f"{B}/contactos", headers=s_ana, json={"celular": luis["celular"]})
    assert hallado.status_code == 200, hallado.text
    assert hallado.json() == {"nombre": "Luis R."}
    propio = api.post(f"{B}/contactos", headers=s_ana, json={"celular": ana["celular"]})
    assert propio.status_code == 404


def test_dos_envios_simultaneos_con_la_misma_llave_debitan_una_vez(api, billetera, sesion):
    ana, luis = billetera(), billetera()
    s_ana = sesion(ana)
    encabezados = {**s_ana, **llave()}
    cuerpo = {"celular_destino": luis["celular"], "monto": "20.00"}

    def enviar(_):
        return TestClient(app, raise_server_exceptions=False).post(
            f"{B}/transferencias", headers=encabezados, json=cuerpo)

    with ThreadPoolExecutor(2) as hilos:
        respuestas = list(hilos.map(enviar, range(2)))
    assert [r.status_code for r in respuestas] == [201, 201], [r.text for r in respuestas]
    assert {r.json()["id_operacion"] for r in respuestas} == {respuestas[0].json()["id_operacion"]}
    assert sorted(r.json()["repetido"] for r in respuestas) == [False, True]
    assert saldo(api, s_ana) == Decimal("280.00")


# --- QR -----------------------------------------------------------------------------

def test_un_qr_dinamico_se_paga_una_sola_vez(api, billetera, sesion):
    vendedor, comprador = billetera(nombres="Marta", apellido="Lopez"), billetera()
    s_vendedor, s_comprador = sesion(vendedor), sesion(comprador)
    creado = api.post(f"{B}/qr", headers=s_vendedor, json={"monto": "30.00"})
    assert creado.status_code == 201, creado.text
    qr = creado.json()
    assert qr["tipo"] == "DINAMICO" and qr["estado"] == "ACTIVO"
    visto = api.get(f"{B}/qr/{qr['id_qr']}", headers=s_comprador)
    assert visto.status_code == 200, visto.text
    assert visto.json()["beneficiario"] == "Marta L."
    assert "num_cuenta" not in visto.json() and "cod_cliente" not in visto.json()
    pagado = api.post(f"{B}/qr/{qr['id_qr']}/pagos", headers={**s_comprador, **llave()}, json={})
    assert pagado.status_code == 201, pagado.text
    assert pagado.json()["tipo"] == "QR" and Decimal(pagado.json()["monto"]) == Decimal("30.00")
    otra_vez = api.post(f"{B}/qr/{qr['id_qr']}/pagos", headers={**s_comprador, **llave()}, json={})
    assert otra_vez.status_code == 409
    assert otra_vez.json()["error"]["code"] == "BNA-QR-NO-VIGENTE"
    assert saldo(api, s_comprador) == Decimal("270.00")
    assert saldo(api, s_vendedor) == Decimal("330.00")


def test_dos_pagos_simultaneos_de_un_qr_dinamico_con_llaves_distintas_cobran_una_vez(api, billetera, sesion):
    vendedor, comprador = billetera(), billetera()
    s_vendedor, s_comprador = sesion(vendedor), sesion(comprador)
    qr = api.post(f"{B}/qr", headers=s_vendedor, json={"monto": "25.00"}).json()

    def pagar(_):
        return TestClient(app, raise_server_exceptions=False).post(
            f"{B}/qr/{qr['id_qr']}/pagos", headers={**s_comprador, **llave()}, json={})

    with ThreadPoolExecutor(2) as hilos:
        respuestas = list(hilos.map(pagar, range(2)))
    assert sorted(r.status_code for r in respuestas) == [201, 409], [r.text for r in respuestas]
    assert saldo(api, s_comprador) == Decimal("275.00")


def test_un_comercio_cobra_con_su_qr_estatico(api, autorizacion, billetera, sesion, abrir_cuenta):
    cuenta = abrir_cuenta(titular="C002")
    ruc = "20" + "".join(random.choice("0123456789") for _ in range(9))
    comercio = api.post(f"{B}/comercios", headers=autorizacion,
                        json={"ruc": ruc, "razon_social": "Bodega Ficticia", "num_cuenta": cuenta})
    assert comercio.status_code == 201, comercio.text
    id_qr = comercio.json()["id_qr"]
    comprador = billetera()
    s_comprador = sesion(comprador)
    listado = api.get(f"{B}/comercios", headers=s_comprador)
    assert listado.status_code == 200
    assert {"razon_social": "Bodega Ficticia", "id_qr": id_qr} in [
        {k: c[k] for k in ("razon_social", "id_qr")} for c in listado.json()]
    sin_monto = api.post(f"{B}/qr/{id_qr}/pagos", headers={**s_comprador, **llave()}, json={})
    assert sin_monto.status_code == 422
    pagado = api.post(f"{B}/qr/{id_qr}/pagos", headers={**s_comprador, **llave()}, json={"monto": "12.50"})
    assert pagado.status_code == 201, pagado.text
    assert pagado.json()["nombre_destino"] == "Bodega Ficticia"
    duplicado = api.post(f"{B}/comercios", headers=autorizacion,
                         json={"ruc": ruc, "razon_social": "Otra", "num_cuenta": cuenta})
    assert duplicado.status_code == 409


# --- Solicitudes de cobro y avisos --------------------------------------------------

def test_una_solicitud_aceptada_paga_y_avisa(api, billetera, sesion):
    pide, paga = billetera(nombres="Carla", apellido="Vega"), billetera(nombres="Pedro", apellido="Salas")
    s_pide, s_paga = sesion(pide), sesion(paga)
    creada = api.post(f"{B}/solicitudes", headers=s_pide,
                      json={"celular": paga["celular"], "monto": "40.00", "concepto": "Entradas"})
    assert creada.status_code == 201, creada.text
    id_solicitud = creada.json()["id_solicitud"]
    recibidas = api.get(f"{B}/solicitudes", headers=s_paga).json()["recibidas"]
    assert [s["id_solicitud"] for s in recibidas] == [id_solicitud]
    assert recibidas[0]["nombre_solicitante"] == "Carla V." and recibidas[0]["estado"] == "PENDIENTE"
    sin_llave = api.post(f"{B}/solicitudes/{id_solicitud}/respuesta", headers=s_paga, json={"accion": "ACEPTAR"})
    assert sin_llave.status_code == 422
    aceptada = api.post(f"{B}/solicitudes/{id_solicitud}/respuesta", headers={**s_paga, **llave()},
                        json={"accion": "ACEPTAR"})
    assert aceptada.status_code == 200, aceptada.text
    assert aceptada.json()["estado"] == "PAGADA"
    assert aceptada.json()["operacion"]["tipo"] == "SOLICITUD"
    assert saldo(api, s_paga) == Decimal("260.00")
    assert saldo(api, s_pide) == Decimal("340.00")
    avisos = api.get(f"{B}/notificaciones", headers=s_pide).json()
    assert any("Pedro S." in a["mensaje"] for a in avisos)
    leidas = api.post(f"{B}/notificaciones/leidas", headers=s_pide)
    assert leidas.status_code == 200 and leidas.json()["marcadas"] >= 1
    assert all(a["leida"] for a in api.get(f"{B}/notificaciones", headers=s_pide).json())


def test_solo_el_pagador_responde_y_una_rechazada_no_se_acepta(api, billetera, sesion):
    pide, paga = billetera(), billetera()
    s_pide, s_paga = sesion(pide), sesion(paga)
    id_solicitud = api.post(f"{B}/solicitudes", headers=s_pide,
                            json={"celular": paga["celular"], "monto": "5.00"}).json()["id_solicitud"]
    ajena = api.post(f"{B}/solicitudes/{id_solicitud}/respuesta", headers={**s_pide, **llave()},
                     json={"accion": "ACEPTAR"})
    assert ajena.status_code == 403
    rechazada = api.post(f"{B}/solicitudes/{id_solicitud}/respuesta", headers=s_paga, json={"accion": "RECHAZAR"})
    assert rechazada.status_code == 200 and rechazada.json()["estado"] == "RECHAZADA"
    tarde = api.post(f"{B}/solicitudes/{id_solicitud}/respuesta", headers={**s_paga, **llave()},
                     json={"accion": "ACEPTAR"})
    assert tarde.status_code == 409


def test_movimientos_y_operaciones_son_solo_los_del_cliente(api, billetera, sesion):
    ana, luis = billetera(), billetera()
    s_ana, s_luis = sesion(ana), sesion(luis)
    api.post(f"{B}/transferencias", headers={**s_ana, **llave()},
             json={"celular_destino": luis["celular"], "monto": "10.00"})
    movimientos = api.get(f"{B}/movimientos", headers=s_ana).json()
    assert movimientos and {m["num_cuenta"] for m in movimientos} == {ana["num_cuenta"]}
    assert movimientos[0]["id_canal"] == "BD"
    operaciones = api.get(f"{B}/operaciones", headers=s_luis).json()
    assert len(operaciones) == 1 and operaciones[0]["sentido"] == "RECIBIDA"


def test_la_bitacora_y_los_avisos_no_guardan_el_celular(api, billetera, sesion, servicio_billetera, consulta):
    ana, luis = billetera(), billetera()
    s_ana = sesion(ana)
    api.post(f"{B}/acceso", headers=servicio_billetera, json={"celular": ana["celular"], "pin": "999999"})
    api.post(f"{B}/transferencias", headers={**s_ana, **llave()},
             json={"celular_destino": luis["celular"], "monto": "3.00"})
    api.post(f"{B}/solicitudes", headers=s_ana, json={"celular": luis["celular"], "monto": "2.00"})
    avisos = api.get(f"{B}/notificaciones", headers=s_ana).text + api.get(
        f"{B}/notificaciones", headers=sesion(luis)).text
    for celular in (ana["celular"], luis["celular"]):
        assert consulta("SELECT COUNT(*) AS n FROM core.evento_auditoria WHERE detalle LIKE %s OR id_entidad = %s",
                        f"%{celular}%", celular)[0]["n"] == 0
        assert consulta("SELECT COUNT(*) AS n FROM cuentas.movimiento WHERE glosa LIKE %s",
                        f"%{celular}%")[0]["n"] == 0
        assert celular not in avisos


def test_el_pin_se_confirma_antes_de_operar_y_cuenta_los_intentos(api, billetera, sesion, servicio_billetera):
    datos = billetera()
    encabezados = sesion(datos)
    correcto = api.post(f"{B}/pin/verificacion", headers=encabezados, json={"pin": datos["pin"]})
    assert correcto.status_code == 200, correcto.text
    assert correcto.json() == {"valido": True}
    for _ in range(2):
        equivocado = api.post(f"{B}/pin/verificacion", headers=encabezados, json={"pin": "000000"})
        assert equivocado.status_code == 401
        assert equivocado.json()["error"]["code"] == "PIN_INCORRECTO"
    tercero = api.post(f"{B}/pin/verificacion", headers=encabezados, json={"pin": "000000"})
    assert tercero.status_code == 401
    # Al tercer PIN equivocado la billetera queda bloqueada y la sesión se corta.
    assert api.get(f"{B}/yo", headers=encabezados).status_code == 401
    acceso = api.post(f"{B}/acceso", headers=servicio_billetera,
                      json={"celular": datos["celular"], "pin": datos["pin"]})
    assert acceso.json()["error"]["code"] == "BILLETERA_BLOQUEADA"
