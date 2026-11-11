"""Lecturas de consulta: movimientos de una cuenta, cuentas de un cliente y bitácora."""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app


@pytest.fixture
def cliente(autorizacion):
    return TestClient(app, raise_server_exceptions=False, headers=autorizacion)


def depositar(cliente, cuenta, monto="100.00", **extra):
    respuesta = cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": cuenta, "tipo": "DEPOSITO", "monto": monto, "glosa": "Depósito de prueba",
              "id_canal": "VEN", **extra},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["uuid_transaccion"]


# ── Movimientos ──────────────────────────────────────────────────────────────


def test_movimientos_de_una_cuenta_del_mas_reciente_al_mas_antiguo(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    primero = depositar(cliente, cuenta, "100.00")
    segundo = depositar(cliente, cuenta, "25.50")
    respuesta = cliente.get(f"/coredb/movimientos/cuenta/{cuenta}")
    assert respuesta.status_code == 200, respuesta.text
    lista = respuesta.json()
    assert [m["uuid_transaccion"] for m in lista] == [segundo, primero]
    assert lista[0] == {
        "uuid_transaccion": segundo, "num_cuenta": cuenta, "tipo_operacion": "DEPOSITO",
        "naturaleza": "C", "monto": "25.50", "moneda": "PEN", "glosa": "Depósito de prueba",
        "id_canal": "VEN", "estado_transaccion": "APROBADO", "fecha_hora": lista[0]["fecha_hora"],
    }
    assert lista[0]["fecha_hora"].endswith("Z")


def test_una_transferencia_se_lee_en_las_dos_cuentas(cliente, abrir_cuenta):
    origen, destino = abrir_cuenta(), abrir_cuenta()
    depositar(cliente, origen, "300.00")
    transferencia = cliente.post(
        "/coredb/movimientos/transferencias",
        json={"origen": origen, "destino": destino, "monto": "120.00", "glosa": "t", "id_canal": "VEN"},
    )
    assert transferencia.status_code == 201, transferencia.text
    ids = transferencia.json()
    del_origen = cliente.get(f"/coredb/movimientos/cuenta/{origen}").json()[0]
    del_destino = cliente.get(f"/coredb/movimientos/cuenta/{destino}").json()[0]
    assert (del_origen["uuid_transaccion"], del_origen["tipo_operacion"], del_origen["naturaleza"]) == (
        ids["uuid_debito"], "TRANSFERENCIA_ENVIADA", "D")
    assert (del_destino["uuid_transaccion"], del_destino["tipo_operacion"], del_destino["naturaleza"]) == (
        ids["uuid_abono"], "TRANSFERENCIA_RECIBIDA", "C")
    assert Decimal(del_origen["monto"]) == Decimal(del_destino["monto"]) == Decimal("120.00")


def test_limite_y_pagina_anterior(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    ids = [depositar(cliente, cuenta, f"{n}.00") for n in (1, 2, 3)]
    recientes = cliente.get(f"/coredb/movimientos/cuenta/{cuenta}", params={"limite": 2}).json()
    assert [m["uuid_transaccion"] for m in recientes] == [ids[2], ids[1]]
    anteriores = cliente.get(
        f"/coredb/movimientos/cuenta/{cuenta}",
        params={"limite": 2, "antes_de": recientes[-1]["fecha_hora"]},
    ).json()
    assert [m["uuid_transaccion"] for m in anteriores] == [ids[0]]
    for invalido in (0, 201):
        assert cliente.get(f"/coredb/movimientos/cuenta/{cuenta}", params={"limite": invalido}).status_code == 422


def test_un_movimiento_por_su_identificador(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    uuid_transaccion = depositar(cliente, cuenta)
    respuesta = cliente.get(f"/coredb/movimientos/{uuid_transaccion}")
    assert respuesta.status_code == 200, respuesta.text
    movimiento = respuesta.json()
    assert movimiento == cliente.get(f"/coredb/movimientos/cuenta/{cuenta}").json()[0]
    assert "id_asiento" not in movimiento


def test_movimiento_o_cuenta_inexistentes_404(cliente):
    inexistente = cliente.get(f"/coredb/movimientos/{uuid.uuid4()}")
    assert inexistente.status_code == 404
    assert inexistente.json()["error"]["code"] == "MOVIMIENTO_NO_ENCONTRADO"
    sin_cuenta = cliente.get("/coredb/movimientos/cuenta/NO-EXISTE")
    assert sin_cuenta.status_code == 404
    assert sin_cuenta.json()["error"]["code"] == "CUENTA_NO_ENCONTRADA"
    assert cliente.get("/coredb/movimientos/no-es-uuid").status_code == 422


def test_una_cuenta_sin_movimientos_devuelve_una_lista_vacia(cliente, abrir_cuenta):
    respuesta = cliente.get(f"/coredb/movimientos/cuenta/{abrir_cuenta()}")
    assert (respuesta.status_code, respuesta.json()) == (200, [])


def test_leer_movimientos_exige_ver_cuenta(abrir_cuenta, sesion_de, autorizacion):
    cuenta = abrir_cuenta()
    api = TestClient(app)
    assert api.get(f"/coredb/movimientos/cuenta/{cuenta}").status_code == 401
    asesor, _ = sesion_de("ASESOR")
    assert api.get(f"/coredb/movimientos/cuenta/{cuenta}", headers=asesor).status_code == 200
    servicio = api.post(
        "/coredb/usuarios/servicios", headers=autorizacion,
        json={"modulo": "CLIENTES", "username": "svc-" + uuid.uuid4().hex[:10], "nombre": "M"},
    ).json()
    login = api.post("/coredb/auth/login", json={"username": servicio["usuario"]["username"],
                                                 "password": servicio["secreto"]}).json()
    sin_permiso = {"Authorization": f"Bearer {login['access_token']}"}
    for ruta in (f"/coredb/movimientos/cuenta/{cuenta}", f"/coredb/movimientos/{uuid.uuid4()}",
                 "/coredb/cuentas?cod_cliente=C001"):
        respuesta = api.get(ruta, headers=sin_permiso)
        assert respuesta.status_code == 403, ruta
        assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


# ── Cuentas de un cliente ────────────────────────────────────────────────────


def test_cuentas_de_un_cliente_con_sus_titulares(cliente, abrir_cuenta):
    una, otra = abrir_cuenta(), abrir_cuenta("USD")
    respuesta = cliente.get("/coredb/cuentas", params={"cod_cliente": "C001"})
    assert respuesta.status_code == 200, respuesta.text
    por_numero = {c["num_cuenta"]: c for c in respuesta.json()}
    assert {una, otra} <= set(por_numero)
    assert por_numero[una]["titulares"] == ["C001"]
    assert (por_numero[una]["moneda"], por_numero[otra]["moneda"]) == ("PEN", "USD")
    assert list(por_numero) == sorted(por_numero)


def test_la_cuenta_incluye_a_todos_sus_titulares(cliente, datos_base):
    sufijo = uuid.uuid4().int % 10**16
    creada = cliente.post("/coredb/cuentas", json={
        "num_cuenta": f"CTA-{sufijo:016d}", "cci": f"{sufijo:020d}", "moneda": "PEN",
        "regimen": "MANCOMUNADA_INDISTINTA", "id_agencia": "AQP01", "titulares": ["C002", "C001"],
    })
    assert creada.status_code == 201, creada.text
    assert creada.json()["titulares"] == ["C001", "C002"]
    leida = cliente.get(f"/coredb/cuentas/{creada.json()['num_cuenta']}").json()
    assert leida["titulares"] == ["C001", "C002"]
    de_c002 = cliente.get("/coredb/cuentas", params={"cod_cliente": "C002"}).json()
    assert creada.json()["num_cuenta"] in {c["num_cuenta"] for c in de_c002}


def test_cuentas_de_un_cliente_inexistente_o_sin_indicarlo(cliente):
    inexistente = cliente.get("/coredb/cuentas", params={"cod_cliente": "CLI999999999"})
    assert inexistente.status_code == 404
    assert inexistente.json()["error"]["code"] == "CLIENTE_NO_ENCONTRADO"
    # No hay una ruta que liste todas las cuentas.
    assert cliente.get("/coredb/cuentas").status_code == 422


def test_un_cliente_sin_cuentas_devuelve_una_lista_vacia(cliente, autorizacion):
    registrado = cliente.post("/coredb/clientes", json={
        "tipo_documento": "DNI", "numero_documento": f"{uuid.uuid4().int % 10**8:08d}",
        "nombres": "Sin", "apellido_paterno": "Cuentas", "correo": f"s{uuid.uuid4().hex[:10]}@example.com",
        "celular": f"9{uuid.uuid4().int % 10**8:08d}", "version_contrato": "v1",
        "estado_habilitante": "OBSERVADO",
    })
    assert registrado.status_code == 201, registrado.text
    respuesta = cliente.get("/coredb/cuentas", params={"cod_cliente": registrado.json()["cod_cliente"]})
    assert (respuesta.status_code, respuesta.json()) == (200, [])


# ── Bitácora ─────────────────────────────────────────────────────────────────


def test_la_bitacora_muestra_el_evento_de_una_operacion(cliente, abrir_cuenta):
    cuenta, correlacion = abrir_cuenta(), str(uuid.uuid4())
    uuid_transaccion = depositar(cliente, cuenta, correlation_id=correlacion)
    respuesta = cliente.get("/coredb/auditoria", params={"correlation_id": correlacion})
    assert respuesta.status_code == 200, respuesta.text
    eventos = respuesta.json()
    assert len(eventos) == 1
    evento = eventos[0]
    assert set(evento) == {"id_evento", "modulo", "entidad", "id_entidad", "accion", "actor",
                           "correlation_id", "detalle", "fecha_hora"}
    assert (evento["modulo"], evento["entidad"], evento["id_entidad"], evento["accion"], evento["actor"]) == (
        "CUENTAS", "movimiento", uuid_transaccion, "DEPOSITO", "pruebas")
    assert evento["correlation_id"] == correlacion
    assert isinstance(evento["detalle"], dict)
    assert evento["fecha_hora"].endswith("Z")


def test_filtros_de_la_bitacora(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    depositar(cliente, cuenta)
    por_cuenta = cliente.get(
        "/coredb/auditoria", params={"entidad": "cuenta_ahorro", "id_entidad": cuenta}
    ).json()
    assert [(e["accion"], e["modulo"]) for e in por_cuenta] == [("ABRIR_CUENTA", "CUENTAS")]
    logins = cliente.get("/coredb/auditoria", params={"modulo": "CORE", "accion": "LOGIN", "limite": 5}).json()
    assert logins and all(e["accion"] == "LOGIN" and e["modulo"] == "CORE" for e in logins)
    assert cliente.get("/coredb/auditoria", params={"actor": "nadie-con-este-nombre"}).json() == []


def test_la_bitacora_va_del_evento_mas_reciente_al_mas_antiguo_y_se_pagina(cliente, abrir_cuenta):
    cuenta = abrir_cuenta()
    for _ in range(3):
        depositar(cliente, cuenta)
    pagina = cliente.get("/coredb/auditoria", params={"limite": 2}).json()
    ids = [e["id_evento"] for e in pagina]
    assert len(ids) == 2 and ids == sorted(ids, reverse=True)
    siguiente = cliente.get("/coredb/auditoria", params={"limite": 2, "antes_de_id": ids[-1]}).json()
    assert all(e["id_evento"] < ids[-1] for e in siguiente) and len(siguiente) == 2
    for invalido in (0, 201):
        assert cliente.get("/coredb/auditoria", params={"limite": invalido}).status_code == 422
    assert cliente.get("/coredb/auditoria", params={"correlation_id": "no-es-uuid"}).status_code == 422


def test_la_bitacora_exige_ver_auditoria(sesion_de):
    api = TestClient(app)
    assert api.get("/coredb/auditoria").status_code == 401
    auditor, _ = sesion_de("AUDITOR")
    assert api.get("/coredb/auditoria", headers=auditor, params={"limite": 1}).status_code == 200
    operador, _ = sesion_de("OPERADOR")
    respuesta = api.get("/coredb/auditoria", headers=operador)
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_la_bitacora_no_expone_datos_personales_del_registro(cliente):
    documento = f"{uuid.uuid4().int % 10**8:08d}"
    correo = f"b{uuid.uuid4().hex[:10]}@example.com"
    celular = f"9{uuid.uuid4().int % 10**8:08d}"
    registrado = cliente.post("/coredb/clientes", json={
        "tipo_documento": "DNI", "numero_documento": documento, "nombres": "Persona",
        "apellido_paterno": "Reservada", "correo": correo, "celular": celular,
        "version_contrato": "v1", "estado_habilitante": "OBSERVADO",
    })
    assert registrado.status_code == 201, registrado.text
    respuesta = cliente.get("/coredb/auditoria", params={"id_entidad": registrado.json()["cod_cliente"]})
    assert respuesta.status_code == 200 and len(respuesta.json()) == 1
    assert all(dato not in respuesta.text for dato in (documento, correo, celular))
