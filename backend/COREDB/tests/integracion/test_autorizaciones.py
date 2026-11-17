"""Autorizaciones, extornos y credenciales de tarjeta contra la base (bd-v1.5)."""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app


@pytest.fixture
def cliente(autorizacion):
    return TestClient(app, raise_server_exceptions=False, headers=autorizacion)


@pytest.fixture
def tarjeta_activa(cliente, abrir_cuenta):
    """Una tarjeta ACTIVA sobre una cuenta nueva con 1000 de saldo: (id_tarjeta, num_cuenta)."""

    def _crear(saldo="1000.00"):
        num_cuenta = abrir_cuenta()
        deposito = cliente.post("/coredb/movimientos", json={
            "num_cuenta": num_cuenta, "tipo": "DEPOSITO", "monto": saldo, "glosa": "g", "id_canal": "VEN",
        })
        assert deposito.status_code == 201, deposito.text
        emitida = cliente.post("/coredb/tarjetas", json={
            "pan_token": uuid.uuid4().hex, "bin": "004499", "ultimos4": "1234",
            "fecha_emision": "2026-01-01", "fecha_vencimiento": "2030-01-01",
            "cod_cliente": "C001", "num_cuenta": num_cuenta,
        })
        assert emitida.status_code == 201, emitida.text
        id_tarjeta = emitida.json()["id_tarjeta"]
        activada = cliente.post(f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "ACTIVA"})
        assert activada.status_code == 200, activada.text
        return id_tarjeta, num_cuenta

    return _crear


def autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00", uuid_autorizacion=None, **canal):
    return cliente.post("/coredb/autorizaciones", json={
        "uuid_autorizacion": str(uuid_autorizacion or uuid.uuid4()),
        "id_tarjeta": id_tarjeta,
        "num_cuenta": num_cuenta,
        "tipo_operacion": "RETIRO",
        "monto": monto,
        **(canal or {"id_terminal": "DEV-ATM-01"}),
    })


def disponible(cliente, num_cuenta):
    return Decimal(cliente.get(f"/coredb/cuentas/{num_cuenta}").json()["saldo_disponible"])


def test_un_retiro_en_cajero_se_autoriza_y_retiene_el_saldo(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["estado_autorizacion"], cuerpo["codigo_respuesta"]) == ("AUTORIZADA", "00")
    assert cuerpo["id_terminal"] == "DEV-ATM-01" and cuerpo["id_canal"] is None
    assert disponible(cliente, num_cuenta) == Decimal("900.00")
    assert cliente.get(f"/coredb/autorizaciones/{cuerpo['uuid_autorizacion']}").json() == cuerpo


def test_repetir_el_uuid_no_retiene_dos_veces(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = uuid.uuid4()
    primera = autorizar(cliente, id_tarjeta, num_cuenta, uuid_autorizacion=llave)
    segunda = autorizar(cliente, id_tarjeta, num_cuenta, uuid_autorizacion=llave)
    assert segunda.status_code == 201
    assert segunda.json() == primera.json()
    assert disponible(cliente, num_cuenta) == Decimal("900.00")


def test_el_mismo_uuid_con_otro_monto_409(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = uuid.uuid4()
    autorizar(cliente, id_tarjeta, num_cuenta, uuid_autorizacion=llave)
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta, monto="200.00", uuid_autorizacion=llave)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "BNA-IDEMPOTENCIA"


@pytest.mark.parametrize(
    ("monto", "canal", "codigo"),
    [("5000.00", {"id_canal": "VEN"}, "51"), ("1600.00", {"id_terminal": "DEV-ATM-01"}, "61")],
    ids=["sin_saldo", "sobre_el_tope_del_cajero"],
)
def test_una_regla_que_no_se_cumple_queda_rechazada(cliente, tarjeta_activa, monto, canal, codigo):
    id_tarjeta, num_cuenta = tarjeta_activa(saldo="2000.00")
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta, monto=monto, **canal)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert (cuerpo["estado_autorizacion"], cuerpo["codigo_respuesta"]) == ("RECHAZADA", codigo)
    assert monto.split(".")[0] not in cuerpo["motivo_rechazo"]
    assert disponible(cliente, num_cuenta) == Decimal("2000.00")


def test_una_tarjeta_bloqueada_queda_rechazada_con_62(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    cliente.post(f"/coredb/tarjetas/{id_tarjeta}/estado", json={"estado": "BLOQUEADA"})
    assert autorizar(cliente, id_tarjeta, num_cuenta).json()["codigo_respuesta"] == "62"


def test_una_cuenta_que_la_tarjeta_no_opera_422(cliente, tarjeta_activa, abrir_cuenta):
    id_tarjeta, _ = tarjeta_activa()
    respuesta = autorizar(cliente, id_tarjeta, abrir_cuenta(), id_canal="VEN")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-TARJETA"


def test_canal_y_terminal_a_la_vez_422(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    respuesta = autorizar(cliente, id_tarjeta, num_cuenta, id_canal="ATM", id_terminal="DEV-ATM-01")
    assert respuesta.status_code == 422


def test_el_extorno_libera_el_saldo_y_se_puede_repetir(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = autorizar(cliente, id_tarjeta, num_cuenta).json()["uuid_autorizacion"]
    for _ in range(2):
        respuesta = cliente.post(f"/coredb/autorizaciones/{llave}/extorno", json={"motivo": "Sin efectivo"})
        assert respuesta.status_code == 200, respuesta.text
        assert (respuesta.json()["estado_autorizacion"], respuesta.json()["codigo_respuesta"]) == ("EXTORNADA", "EXT")
    assert disponible(cliente, num_cuenta) == Decimal("1000.00")


def test_extornar_lo_que_no_existe_404(cliente, datos_base):
    respuesta = cliente.post(f"/coredb/autorizaciones/{uuid.uuid4()}/extorno", json={"motivo": "x"})
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "BNA-AUTORIZACION"


def test_extornar_una_rechazada_409(cliente, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    llave = autorizar(cliente, id_tarjeta, num_cuenta, monto="9999.00").json()["uuid_autorizacion"]
    respuesta = cliente.post(f"/coredb/autorizaciones/{llave}/extorno", json={"motivo": "x"})
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "BNA-EXTORNO"


def test_ver_una_autorizacion_que_no_existe_404(cliente, datos_base):
    assert cliente.get(f"/coredb/autorizaciones/{uuid.uuid4()}").status_code == 404


def registrar_pin(cliente, id_tarjeta, valor="4821", tipo="PIN_ATM"):
    return cliente.put(f"/coredb/tarjetas/{id_tarjeta}/credenciales/{tipo}", json={"valor": valor})


def validar(cliente, id_tarjeta, valor, tipo="PIN_ATM", **canal):
    return cliente.post(
        f"/coredb/tarjetas/{id_tarjeta}/credenciales/{tipo}/validacion",
        json={"valor": valor, **(canal or {"id_terminal": "DEV-ATM-01"})},
    )


def test_un_pin_registrado_se_valida(cliente, tarjeta_activa, consulta):
    id_tarjeta, _ = tarjeta_activa()
    assert registrar_pin(cliente, id_tarjeta).status_code == 204
    respuesta = validar(cliente, id_tarjeta, "4821")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"resultado": "EXITOSO", "intentos_restantes": 3}
    # La base guarda solo el hash con su sal.
    fila = consulta(
        "SELECT hash_credencial h, sal s FROM tarjetas.credencial WHERE id_tarjeta=UUID_TO_BIN(%s)", id_tarjeta
    )[0]
    assert "4821" not in fila["h"] + fila["s"]


def test_el_tercer_pin_equivocado_bloquea_la_tarjeta(cliente, tarjeta_activa):
    id_tarjeta, _ = tarjeta_activa()
    registrar_pin(cliente, id_tarjeta)
    restantes = [validar(cliente, id_tarjeta, "0000").json()["intentos_restantes"] for _ in range(3)]
    assert restantes == [2, 1, 0]
    assert cliente.get(f"/coredb/tarjetas/{id_tarjeta}").json()["estado_tarjeta"] == "BLOQUEADA"
    respuesta = validar(cliente, id_tarjeta, "4821")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "ERR-TAR-003"


def test_un_pin_de_otra_longitud_422_sin_repetirlo(cliente, tarjeta_activa):
    id_tarjeta, _ = tarjeta_activa()
    respuesta = registrar_pin(cliente, id_tarjeta, valor="482190")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-CREDENCIAL"
    assert "482190" not in respuesta.text


def test_la_clave_web_se_valida_por_home_banking(cliente, tarjeta_activa):
    id_tarjeta, _ = tarjeta_activa()
    assert registrar_pin(cliente, id_tarjeta, valor="615243", tipo="CLAVE_WEB").status_code == 204
    respuesta = validar(cliente, id_tarjeta, "615243", tipo="CLAVE_WEB", id_canal="HB")
    assert respuesta.json()["resultado"] == "EXITOSO"


def test_un_tipo_de_credencial_desconocido_422(cliente, tarjeta_activa):
    id_tarjeta, _ = tarjeta_activa()
    assert registrar_pin(cliente, id_tarjeta, tipo="BIOMETRIA").status_code == 422


def test_validar_sin_credencial_422(cliente, tarjeta_activa):
    id_tarjeta, _ = tarjeta_activa()
    respuesta = validar(cliente, id_tarjeta, "4821")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-CREDENCIAL"


def test_un_auditor_no_autoriza(sesion_de, tarjeta_activa):
    id_tarjeta, num_cuenta = tarjeta_activa()
    encabezados, _ = sesion_de("AUDITOR")
    respuesta = autorizar(TestClient(app, headers=encabezados), id_tarjeta, num_cuenta)
    assert respuesta.status_code == 403


# ── Confirmación de autorización ──────────────────────────────────────────────


def _huella(valor: str) -> str:
    """Genera una huella de 64 caracteres hex (SHA-256 del valor)."""
    import hashlib
    return hashlib.sha256(valor.encode()).hexdigest()


def test_confirmar_autorizacion_debita_una_sola_vez(cliente, tarjeta_activa):
    """Confirma una autorización AUTORIZADA: registra el movimiento y pasa a DISPENSADA."""
    id_tarjeta, num_cuenta = tarjeta_activa()
    # Autoriza un retiro de 100.00
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00")
    assert auth_resp.status_code == 201
    auth = auth_resp.json()
    uuid_autorizacion = auth["uuid_autorizacion"]
    assert (auth["estado_autorizacion"], auth["codigo_respuesta"]) == ("AUTORIZADA", "00")

    # Confirma con llave de idempotencia
    llave = str(uuid.uuid4())
    confirmacion = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert confirmacion.status_code == 200, confirmacion.text
    confirmada = confirmacion.json()
    assert confirmada["estado_autorizacion"] == "DISPENSADA"
    assert confirmada["uuid_transaccion"] == uuid_autorizacion
    # El saldo disponible bajó una vez (1000 - 100 = 900)
    assert disponible(cliente, num_cuenta) == Decimal("900.00")


def test_repetir_confirmacion_con_misma_llave_no_debita_dos_veces(cliente, tarjeta_activa):
    """Repetir la confirmación con la misma llave devuelve el mismo resultado sin segundo débito."""
    id_tarjeta, num_cuenta = tarjeta_activa()
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00")
    uuid_autorizacion = auth_resp.json()["uuid_autorizacion"]
    llave = str(uuid.uuid4())
    huella = _huella(llave)

    # Primera confirmación
    primera = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave, "huella": huella, "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert primera.status_code == 200
    assert disponible(cliente, num_cuenta) == Decimal("900.00")

    # Segunda confirmación con la misma llave
    segunda = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave, "huella": huella, "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert segunda.status_code == 200
    assert segunda.json() == primera.json()
    # El saldo no bajó dos veces
    assert disponible(cliente, num_cuenta) == Decimal("900.00")


def test_otra_llave_sobre_confirmada_409_o_422(cliente, tarjeta_activa):
    """Confirmar una ya DISPENSADA con otra llave falla (estado no vigente)."""
    id_tarjeta, num_cuenta = tarjeta_activa()
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00")
    uuid_autorizacion = auth_resp.json()["uuid_autorizacion"]
    llave1 = str(uuid.uuid4())
    llave2 = str(uuid.uuid4())

    # Primera confirmación
    cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave1, "huella": _huella(llave1), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    # Segunda con otra llave
    respuesta = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave2, "huella": _huella(llave2), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert respuesta.status_code in (409, 422), respuesta.text
    assert respuesta.json()["error"]["code"] in ("BNA-CONFIRMACION", "BNA-IDEMPOTENCIA")


def test_confirmar_extornada_409(cliente, tarjeta_activa):
    """Extornar una autorización y luego confirmarla falla."""
    id_tarjeta, num_cuenta = tarjeta_activa()
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00")
    uuid_autorizacion = auth_resp.json()["uuid_autorizacion"]

    # Extornar
    extorno = cliente.post(f"/coredb/autorizaciones/{uuid_autorizacion}/extorno", json={"motivo": "Sin efectivo"})
    assert extorno.status_code == 200
    assert extorno.json()["estado_autorizacion"] == "EXTORNADA"

    # Confirmar la extornada
    llave = str(uuid.uuid4())
    respuesta = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert respuesta.status_code in (409, 422), respuesta.text
    assert respuesta.json()["error"]["code"] == "BNA-CONFIRMACION"


def test_confirmar_inexistente_404(cliente, datos_base):
    """Confirmar una autorización que no existe devuelve 404."""
    llave = str(uuid.uuid4())
    respuesta = cliente.post(
        f"/coredb/autorizaciones/{uuid.uuid4()}/confirmacion",
        json={"llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "BNA-AUTORIZACION"


def test_confirmar_canal_no_coincide_409(cliente, tarjeta_activa):
    """Confirmar con un canal distinto al de la autorización falla."""
    id_tarjeta, num_cuenta = tarjeta_activa()
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00", id_canal="VEN")
    uuid_autorizacion = auth_resp.json()["uuid_autorizacion"]

    llave = str(uuid.uuid4())
    respuesta = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert respuesta.status_code in (409, 422), respuesta.text
    assert respuesta.json()["error"]["code"] == "BNA-CONFIRMACION"


def test_confirmar_terminal_no_coincide_409(cliente, tarjeta_activa):
    """Confirmar con una terminal distinta a la de la autorización falla."""
    id_tarjeta, num_cuenta = tarjeta_activa()
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00", id_terminal="DEV-ATM-01")
    uuid_autorizacion = auth_resp.json()["uuid_autorizacion"]

    llave = str(uuid.uuid4())
    respuesta = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM", "id_terminal": "OTRA-TERMINAL"},
    )
    assert respuesta.status_code in (409, 422), respuesta.text
    assert respuesta.json()["error"]["code"] == "BNA-CONFIRMACION"


def test_confirmar_sin_llave_idempotencia_422(cliente, tarjeta_activa):
    """La llave de idempotencia es obligatoria."""
    id_tarjeta, num_cuenta = tarjeta_activa()
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00")
    uuid_autorizacion = auth_resp.json()["uuid_autorizacion"]

    respuesta = cliente.post(
        f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
        json={"huella": _huella("x"), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
    )
    assert respuesta.status_code == 422


def test_confirmar_concurrencia_dos_llaves_distintas_un_solo_debito(cliente, tarjeta_activa, consulta):
    """Dos confirmaciones simultáneas con llaves distintas → una sola confirmación exitosa,
    las demás fallan porque la autorización ya cambió a DISPENSADA."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    id_tarjeta, num_cuenta = tarjeta_activa()
    auth_resp = autorizar(cliente, id_tarjeta, num_cuenta, monto="100.00")
    uuid_autorizacion = auth_resp.json()["uuid_autorizacion"]

    def confirmar(llave):
        return cliente.post(
            f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion",
            json={"llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM", "id_terminal": "DEV-ATM-01"},
        )

    barrera = threading.Barrier(8)
    llaves = [str(uuid.uuid4()) for _ in range(8)]

    def intento(_):
        barrera.wait()
        return confirmar(llaves[_])

    with ThreadPoolExecutor(8) as hilos:
        respuestas = list(hilos.map(intento, range(8)))

    # Una responde 200 (la primera), las otras 409/422 porque la autorización ya no está vigente
    exitosas = [r for r in respuestas if r.status_code == 200]
    fallidas = [r for r in respuestas if r.status_code in (409, 422)]
    assert len(exitosas) == 1
    assert len(fallidas) == 7
    for r in fallidas:
        assert r.json()["error"]["code"] == "BNA-CONFIRMACION"
    # Solo un movimiento en la cuenta
    movimientos = consulta(
        "SELECT COUNT(*) FROM cuentas.movimiento WHERE num_cuenta = %s AND tipo_operacion = 'RETIRO'",
        num_cuenta,
    )
    assert movimientos[0]["COUNT(*)"] == 1
    assert disponible(cliente, num_cuenta) == Decimal("900.00")
