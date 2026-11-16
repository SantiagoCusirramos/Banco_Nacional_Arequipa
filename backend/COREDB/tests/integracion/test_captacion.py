"""Captación: el expediente del prospecto (clientes.*_captacion, bd-v1.7-mysql), contra la base real."""

import hashlib
import random
import uuid

import pytest
from creditos_apoyo import sesion_servicio
from fastapi.testclient import TestClient

from COREDB.main import app

RUTA = "/coredb/captacion"
CONSENTIMIENTOS = [{"tipo": t, "aceptado": True, "medio": "DIGITAL"}
                   for t in ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")]


@pytest.fixture
def api():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def asesor(sesion_de):
    encabezados, usuario = sesion_de("ASESOR")
    return encabezados, usuario["username"]


def dni():
    return "6" + "".join(random.choices("0123456789", k=7))


def hmac_de(texto):
    return hashlib.sha256(texto.encode()).hexdigest()


def solicitante(api, encabezados, documento=None, **cambios):
    documento = documento or dni()
    cuerpo = {"tipo_documento": "DNI", "numero_documento": documento, "nombres": "Rosa",
              "apellido_paterno": "Prospecto", "apellido_materno": None,
              "celular": "9" + "".join(random.choices("0123456789", k=8)),
              "correo": f"rosa.{documento}@example.com", **cambios}
    return api.post(f"{RUTA}/solicitantes", json=cuerpo, headers=encabezados)


def caso(api, encabezados, documento=None):
    id_solicitante = solicitante(api, encabezados, documento).json()["solicitante"]["id_solicitante"]
    respuesta = api.post(f"{RUTA}/casos", json={"id_solicitante": id_solicitante, "canal": "AGENCIA",
                                                "id_agencia": "AQP01"}, headers=encabezados)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id_caso"]


def escribir(api, encabezados, id_caso, ruta, cuerpo, esperado=201):
    respuesta = api.post(f"{RUTA}/casos/{id_caso}/{ruta}", json=cuerpo, headers=encabezados)
    assert respuesta.status_code == esperado, respuesta.text
    return respuesta.json()


def otp_verificado(api, encabezados, id_caso):
    id_otp = str(uuid.uuid4())
    escribir(api, encabezados, id_caso, "otps", {"id_otp": id_otp, "canal": "SMS", "codigo_hmac": hmac_de(id_otp)})
    return escribir(api, encabezados, id_caso, f"otps/{id_otp}/verificacion", {"codigo_hmac": hmac_de(id_otp)}, 200)


def listo(api, encabezados, documento=None):
    """Un caso APROBADO: consentimientos, OTP del celular, RENIEC, listas, una central y el perfil."""
    id_caso = caso(api, encabezados, documento)
    escribir(api, encabezados, id_caso, "consentimientos", {"consentimientos": CONSENTIMIENTOS, "version_terminos": "v1"})
    otp_verificado(api, encabezados, id_caso)
    for tipo in ("RENIEC", "LISTAS_NEGRAS"):
        escribir(api, encabezados, id_caso, "validaciones",
                 {"tipo": tipo, "resultado": "APROBADO", "proveedor": "SIMULADO", "detalle": "Sin observaciones"})
    escribir(api, encabezados, id_caso, "consultas-riesgo", {"central": "SBS", "calificacion": "NORMAL", "deuda_total": "0",
                                                             "entidades": 0, "dias_mora": 0, "fuente": "SIMULADO"})
    expediente = escribir(api, encabezados, id_caso, "perfil", {"puntaje": 820, "calificacion": "BAJO"})
    assert expediente["estado"] == "APROBADO", expediente
    return id_caso


def error(respuesta, estado, codigo):
    assert respuesta.status_code == estado, respuesta.text
    assert respuesta.json()["error"]["code"] == codigo, respuesta.text


# ── Solicitantes ────────────────────────────────────────────────────────────


def test_registra_un_solicitante_y_el_mismo_documento_devuelve_el_mismo(api, asesor, consulta):
    encabezados, usuario = asesor
    documento = dni()
    primero = solicitante(api, encabezados, documento, correo=f"Rosa.{documento}@Example.com")
    assert primero.status_code == 201, primero.text
    cuerpo = primero.json()
    assert cuerpo["duplicado"] is False
    assert cuerpo["solicitante"]["correo"] == f"rosa.{documento}@example.com"
    assert cuerpo["solicitante"]["creado_por"] == usuario and cuerpo["solicitante"]["cod_cliente"] is None
    otra_vez = solicitante(api, encabezados, documento, nombres="Otro")
    assert otra_vez.status_code == 200, otra_vez.text
    assert otra_vez.json()["duplicado"] is True
    assert otra_vez.json()["solicitante"] == cuerpo["solicitante"]
    eventos = consulta("SELECT accion, actor, detalle FROM core.evento_auditoria WHERE id_entidad = %s ORDER BY id_evento",
                       cuerpo["solicitante"]["id_solicitante"])
    assert [e["accion"] for e in eventos] == ["REGISTRAR_SOLICITANTE", "REGISTRAR_SOLICITANTE_DUPLICADO"]
    assert all(e["actor"] == usuario and documento not in e["detalle"] for e in eventos)


def test_un_documento_que_no_cumple_su_formato_se_rechaza(api, asesor):
    error(solicitante(api, asesor[0], "7100A12"), 422, "DOCUMENTO_INVALIDO")


def test_solo_quien_crea_clientes_trabaja_un_expediente(api, sesion_de, asesor):
    operador, _ = sesion_de("OPERADOR")
    error(solicitante(api, operador), 403, "PERMISO_DENEGADO")
    auditor, _ = sesion_de("AUDITOR")
    id_caso = caso(api, asesor[0])
    assert api.get(f"{RUTA}/casos/{id_caso}", headers=auditor).status_code == 200
    error(api.post(f"{RUTA}/casos/{id_caso}/estado", json={"accion": "RECHAZAR", "motivo": "Prueba"}, headers=auditor),
          403, "PERMISO_DENEGADO")


def test_busca_solicitantes_por_texto_y_con_cliente(api, asesor, autorizacion):
    encabezados, _ = asesor
    documento = dni()
    nombre = "Zoila" + uuid.uuid4().hex[:6]
    creado = solicitante(api, encabezados, documento, nombres=nombre).json()["solicitante"]
    por_texto = api.get(f"{RUTA}/solicitantes", params={"texto": nombre.lower()}, headers=encabezados).json()
    assert [s["id_solicitante"] for s in por_texto] == [creado["id_solicitante"]]
    por_documento = api.get(f"{RUTA}/solicitantes", params={"documento": documento[2:]}, headers=encabezados).json()
    assert creado["id_solicitante"] in [s["id_solicitante"] for s in por_documento]
    con_cliente = api.get(f"{RUTA}/solicitantes", params={"texto": nombre, "con_cliente": True},
                          headers=encabezados).json()
    assert con_cliente == []
    visto = api.get(f"{RUTA}/solicitantes/{creado['id_solicitante']}", headers=encabezados)
    assert visto.status_code == 200 and visto.json() == creado
    error(api.get(f"{RUTA}/solicitantes/{uuid.uuid4()}", headers=encabezados), 404, "SOLICITANTE_NO_ENCONTRADO")


# ── Casos ───────────────────────────────────────────────────────────────────


def test_abre_un_caso_iniciado_y_no_admite_dos_abiertos(api, asesor):
    encabezados, usuario = asesor
    id_solicitante = solicitante(api, encabezados).json()["solicitante"]["id_solicitante"]
    abierto = api.post(f"{RUTA}/casos", json={"id_solicitante": id_solicitante, "canal": "WEB",
                                              "producto_interes": "Crédito personal"}, headers=encabezados)
    assert abierto.status_code == 201, abierto.text
    cuerpo = abierto.json()
    assert cuerpo["estado"] == "INICIADO" and cuerpo["creado_por"] == usuario and cuerpo["id_agencia"] is None
    assert "Verificación OTP del celular" in cuerpo["faltantes"] and cuerpo["cod_cliente"] is None
    error(api.post(f"{RUTA}/casos", json={"id_solicitante": id_solicitante, "canal": "WEB"}, headers=encabezados),
          409, "CASO_ABIERTO")
    error(api.post(f"{RUTA}/casos", json={"id_solicitante": str(uuid.uuid4()), "canal": "WEB"}, headers=encabezados),
          404, "SOLICITANTE_NO_ENCONTRADO")
    otro = solicitante(api, encabezados).json()["solicitante"]["id_solicitante"]
    error(api.post(f"{RUTA}/casos", json={"id_solicitante": otro, "canal": "WEB", "id_agencia": "NOEXISTE"},
                   headers=encabezados), 422, "AGENCIA_NO_ENCONTRADA")


def test_un_caso_inexistente_es_404(api, asesor):
    encabezados, _ = asesor
    falso = uuid.uuid4()
    error(api.get(f"{RUTA}/casos/{falso}", headers=encabezados), 404, "CASO_NO_ENCONTRADO")
    error(api.post(f"{RUTA}/casos/{falso}/consentimientos", json={"consentimientos": CONSENTIMIENTOS,
                                                                    "version_terminos": "v1"}, headers=encabezados),
          404, "CASO_NO_ENCONTRADO")


def test_expediente_completo_hasta_aprobado(api, asesor):
    encabezados, usuario = asesor
    id_caso = listo(api, encabezados)
    expediente = api.get(f"{RUTA}/casos/{id_caso}", headers=encabezados)
    assert expediente.status_code == 200, expediente.text
    cuerpo = expediente.json()
    assert cuerpo["estado"] == "APROBADO" and cuerpo["faltantes"] == [] and cuerpo["listo_para_habilitar"] is True
    assert [c["tipo"] for c in cuerpo["consentimientos"]] == ["TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS"]
    assert {c["tipo"]: c["version"] for c in cuerpo["consentimientos"]}["TERMINOS"] == "v1"
    assert [(v["tipo"], v["resultado"]) for v in cuerpo["validaciones"]] == [
        ("CELULAR", "APROBADO"), ("RENIEC", "APROBADO"), ("LISTAS_NEGRAS", "APROBADO")]
    assert cuerpo["otps"][0]["estado"] == "USADO" and "codigo_hmac" not in expediente.text
    assert cuerpo["consultas"][0]["deuda_total"] == "0.00"
    assert cuerpo["perfil"]["puntaje"] == 820 and cuerpo["perfil"]["vigente"] is True
    assert cuerpo["solicitante"]["id_solicitante"] == cuerpo["id_solicitante"]
    assert all(v["registrado_por"] == usuario for v in cuerpo["validaciones"])


def test_otp_errado_tres_veces_queda_bloqueado(api, asesor):
    encabezados, _ = asesor
    id_caso = caso(api, encabezados)
    escribir(api, encabezados, id_caso, "consentimientos", {"consentimientos": CONSENTIMIENTOS, "version_terminos": "v1"})
    id_otp = str(uuid.uuid4())
    emitido = escribir(api, encabezados, id_caso, "otps", {"id_otp": id_otp, "canal": "SMS", "codigo_hmac": hmac_de("a")})
    assert emitido["estado"] == "PENDIENTE" and emitido["id_otp"] == id_otp
    restantes = [escribir(api, encabezados, id_caso, f"otps/{id_otp}/verificacion", {"codigo_hmac": hmac_de("b")}, 200)
                 for _ in range(3)]
    assert [(r["estado_codigo"], r["intentos_restantes"]) for r in restantes] == [
        ("PENDIENTE", 2), ("PENDIENTE", 1), ("BLOQUEADO", 0)]
    error(api.post(f"{RUTA}/casos/{id_caso}/otps/{id_otp}/verificacion", json={"codigo_hmac": hmac_de("a")},
                   headers=encabezados), 404, "OTP_NO_ENCONTRADO")


def test_sin_consentimiento_no_hay_otp_ni_central(api, asesor):
    encabezados, _ = asesor
    id_caso = caso(api, encabezados)
    error(api.post(f"{RUTA}/casos/{id_caso}/otps", json={"id_otp": str(uuid.uuid4()), "canal": "SMS",
                                                         "codigo_hmac": hmac_de("a")}, headers=encabezados),
          422, "CONSENTIMIENTO_REQUERIDO")
    error(api.post(f"{RUTA}/casos/{id_caso}/consultas-riesgo",
                   json={"central": "SBS", "calificacion": "NORMAL", "deuda_total": "0", "entidades": 0,
                         "dias_mora": 0, "fuente": "MANUAL"}, headers=encabezados),
          422, "CONSENTIMIENTO_REQUERIDO")
    error(api.post(f"{RUTA}/casos/{id_caso}/perfil", json={"puntaje": 500, "calificacion": "MEDIO"},
                   headers=encabezados), 422, "SIN_CONSULTA")


def test_una_validacion_rechazada_cierra_el_caso(api, asesor):
    encabezados, _ = asesor
    id_caso = caso(api, encabezados)
    escribir(api, encabezados, id_caso, "consentimientos", {"consentimientos": CONSENTIMIENTOS, "version_terminos": "v1"})
    cerrado = escribir(api, encabezados, id_caso, "validaciones",
                       {"tipo": "LISTAS_NEGRAS", "resultado": "RECHAZADO", "proveedor": "SIMULADO"})
    assert cerrado["estado"] == "RECHAZADO" and cerrado["motivo_cierre"] == "Validación rechazada: LISTAS_NEGRAS"
    assert cerrado["faltantes"] == [] and cerrado["listo_para_habilitar"] is False
    error(api.post(f"{RUTA}/casos/{id_caso}/validaciones",
                   json={"tipo": "PEP", "resultado": "APROBADO", "proveedor": "MANUAL"}, headers=encabezados),
          409, "CASO_CERRADO")


def test_observar_levantar_y_revocar(api, asesor):
    encabezados, _ = asesor
    id_caso = listo(api, encabezados)
    observado = escribir(api, encabezados, id_caso, "estado", {"accion": "OBSERVAR", "motivo": "Falta sustento"}, 200)
    assert observado["estado"] == "OBSERVADO" and observado["observacion"] == "Falta sustento"
    assert "Observación del asesor: Falta sustento" in observado["faltantes"]
    levantado = escribir(api, encabezados, id_caso, "estado",
                         {"accion": "LEVANTAR_OBSERVACION", "motivo": "Sustento recibido"}, 200)
    assert levantado["estado"] == "APROBADO"
    error(api.post(f"{RUTA}/casos/{id_caso}/estado", json={"accion": "REVOCAR", "motivo": "Fraude"},
                   headers=encabezados), 409, "ESTADO_INVALIDO")


def test_ligar_exige_un_caso_listo_y_el_mismo_documento(api, asesor):
    encabezados, _ = asesor
    id_caso = caso(api, encabezados)
    error(api.post(f"{RUTA}/casos/{id_caso}/cliente", json={"cod_cliente": "C001", "cliente_nuevo": False},
                   headers=encabezados), 422, "CASO_NO_LISTO")
    aprobado = listo(api, encabezados)
    error(api.post(f"{RUTA}/casos/{aprobado}/habilitacion", json={"vigencia_dias": 30}, headers=encabezados),
          422, "CASO_NO_LISTO")
    error(api.post(f"{RUTA}/casos/{aprobado}/cliente", json={"cod_cliente": "C001", "cliente_nuevo": False},
                   headers=encabezados), 422, "CLIENTE_NO_COINCIDE")
    error(api.post(f"{RUTA}/casos/{aprobado}/cliente", json={"cod_cliente": "CLI999999999", "cliente_nuevo": False},
                   headers=encabezados), 404, "CLIENTE_NO_ENCONTRADO")


def test_habilita_con_un_cliente_nuevo_que_registra_el_modulo_clientes(api, asesor, autorizacion, consulta):
    """El cliente HABILITADO lo registra el usuario de servicio de CLIENTES (R-01); el asesor habilita."""
    encabezados, usuario = asesor
    servicio, _ = sesion_servicio(autorizacion, "CLIENTES")
    documento = dni()
    id_caso = listo(api, encabezados, documento)
    datos = api.get(f"{RUTA}/casos/{id_caso}", headers=servicio).json()["solicitante"]
    registrado = api.post("/coredb/clientes", headers=servicio, json={
        "tipo_documento": "DNI", "numero_documento": documento, "nombres": datos["nombres"],
        "apellido_paterno": datos["apellido_paterno"], "correo": datos["correo"], "celular": datos["celular"],
        "version_contrato": "v1", "estado_habilitante": "HABILITADO"})
    assert registrado.status_code == 201, registrado.text
    cod_cliente = registrado.json()["cod_cliente"]
    ligado = escribir(api, servicio, id_caso, "cliente", {"cod_cliente": cod_cliente, "cliente_nuevo": True}, 200)
    assert ligado["cod_cliente"] == cod_cliente and ligado["estado"] == "APROBADO"
    assert escribir(api, servicio, id_caso, "cliente", {"cod_cliente": cod_cliente, "cliente_nuevo": True}, 200) == ligado
    habilitado = escribir(api, encabezados, id_caso, "habilitacion", {"vigencia_dias": 30}, 200)
    assert habilitado["estado"] == "HABILITADO" and habilitado["cliente_nuevo"] is True
    assert habilitado["estado_cliente"] == "ACTIVO"
    assert habilitado["id_verificacion_captacion"] == registrado.json()["id_verificacion_captacion"]
    assert habilitado["fecha_verificacion"] and habilitado["vigente_hasta"] > habilitado["fecha_verificacion"]
    assert habilitado["solicitante"]["cod_cliente"] == cod_cliente
    assert escribir(api, encabezados, id_caso, "habilitacion", {"vigencia_dias": 60}, 200) == habilitado
    validaciones = consulta("SELECT tipo_validacion, resultado FROM clientes.validacion_identidad WHERE cod_cliente = %s",
                            cod_cliente)
    assert validaciones == [{"tipo_validacion": "CELULAR", "resultado": "APROBADO"}]
    eventos = consulta("SELECT accion, actor FROM core.evento_auditoria WHERE id_entidad = %s "
                       "AND accion IN ('VINCULAR_CLIENTE', 'HABILITAR') ORDER BY id_evento", id_caso)
    assert [(e["accion"], e["actor"]) for e in eventos] == [("VINCULAR_CLIENTE", servicio_usuario(consulta, eventos)),
                                                            ("HABILITAR", usuario)]
    por_cliente = api.get(f"{RUTA}/casos", params={"cod_cliente": cod_cliente}, headers=servicio).json()
    assert [c["id_caso"] for c in por_cliente] == [id_caso] and por_cliente[0]["solicitante"]["numero_documento"] == documento
    con_cliente = api.get(f"{RUTA}/solicitantes", params={"texto": documento, "con_cliente": True}, headers=servicio).json()
    assert [s["cod_cliente"] for s in con_cliente] == [cod_cliente]
    revocado = escribir(api, encabezados, id_caso, "estado", {"accion": "REVOCAR", "motivo": "Documento adulterado"}, 200)
    assert revocado["estado"] == "REVOCADO" and revocado["cod_cliente"] == cod_cliente


def servicio_usuario(consulta, eventos):
    """El actor del vínculo es el usuario de servicio, cualquiera sea su nombre."""
    actor = eventos[0]["actor"]
    assert actor.startswith("svc-")
    return actor


def test_bandeja_por_estado(api, asesor):
    encabezados, _ = asesor
    id_caso = caso(api, encabezados)
    iniciados = api.get(f"{RUTA}/casos", params={"estado": "INICIADO", "limite": 200}, headers=encabezados)
    assert iniciados.status_code == 200, iniciados.text
    assert id_caso in [c["id_caso"] for c in iniciados.json()]
    assert all(c["estado"] == "INICIADO" for c in iniciados.json())
    assert api.get(f"{RUTA}/casos", params={"estado": "OTRO"}, headers=encabezados).status_code == 422


def test_un_deadlock_se_reintenta(api, asesor, fallar_una_vez):
    from COREDB.services import captacion

    intentos = fallar_una_vez(captacion, 1213)
    respuesta = solicitante(api, asesor[0])
    assert respuesta.status_code == 201, respuesta.text
    assert intentos == ["clientes.registrar_solicitante_captacion"] * 2
