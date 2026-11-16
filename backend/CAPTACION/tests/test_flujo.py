"""El expediente de captación de punta a punta, con COREDB en memoria."""

from CAPTACION.services.captacion import hoy_lima
from CAPTACION.tests.conftest import ASESOR, AUDITOR, BASE, SOL


def test_flujo_completo_registra_al_cliente_en_coredb_y_deja_la_referencia(client, flujo, coredb_falso):
    id_caso = flujo.hasta_aprobado("45678901")
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "APROBADO" and caso["listo_para_habilitar"] is True, caso["faltantes"]
    assert caso["perfil"]["calificacion"] == "BAJO"

    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 200, r.text
    datos = r.json()["data"]
    assert datos["estado"] == "HABILITADO" and datos["cliente_nuevo"] is True
    cod = datos["cod_cliente"]
    assert cod.startswith("CLI")

    # En COREDB: alta HABILITADA con el usuario de servicio y la verificación del celular.
    alta = next(c for c in coredb_falso.llamadas if c["ruta"] == "/coredb/clientes")
    assert alta["auth"] == "Bearer tok-servicio"
    assert alta["json"]["estado_habilitante"] == "HABILITADO"
    assert alta["json"]["apellido_paterno"] == "Huamán" and alta["json"]["apellido_materno"] == "Ccori"
    assert alta["json"]["version_contrato"] == "v1"
    validacion = next(c for c in coredb_falso.llamadas if c["ruta"] == f"/coredb/clientes/{cod}/validaciones")
    assert validacion["json"]["tipo_validacion"] == "CELULAR"
    assert all(c["correlacion"] for c in coredb_falso.llamadas if c["ruta"] != "/coredb/auth/login")

    # Lo que consulta Solicitud de Crédito (CR-INT-01).
    r = client.get(f"/cap/references/{cod}", headers=SOL)
    assert r.status_code == 200, r.text
    ref = r.json()
    assert ref["id_cliente"] == cod and ref["id_caso"] == id_caso
    assert ref["estado_cliente"] == "ACTIVO" and ref["estado_habilitante"] == "HABILITADO"
    assert ref["fecha_verificacion"] == hoy_lima().isoformat()
    assert ref["vigente_hasta"] > ref["fecha_verificacion"]
    assert ref["id_verificacion"].startswith("ver-")
    assert ref["simulado"] is True and ref["version_contrato"] == "CR-INT-01-PROPUESTA-v2"
    assert "celular" not in ref and "correo" not in ref  # SOL no recibe datos de contacto

    r = client.get("/cap/references", headers=SOL, params={"search": "4567", "limit": 50})
    assert [x["id_cliente"] for x in r.json()] == [cod]

    # El asesor ve la misma referencia desde el expediente.
    r = client.get(f"{BASE}/casos/{id_caso}/referencia", headers=ASESOR)
    assert r.json()["data"]["id_cliente"] == cod


def test_habilitar_reutiliza_al_cliente_activo_que_ya_existe(client, flujo, coredb_falso):
    cod = coredb_falso.agregar_cliente("45670002")
    id_caso = flujo.hasta_aprobado("45670002")
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["cod_cliente"] == cod and r.json()["data"]["cliente_nuevo"] is False
    assert "/coredb/clientes" not in coredb_falso.rutas("POST")


def test_cliente_bloqueado_en_coredb_deja_el_caso_observado(client, flujo, coredb_falso):
    coredb_falso.agregar_cliente("45670003", estado="BLOQUEADO")
    id_caso = flujo.hasta_aprobado("45670003")
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-CAP-CLIENTE-NO-ACTIVO"
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "OBSERVADO"
    assert any("BLOQUEADO" in f for f in caso["faltantes"])


def test_habilitar_se_puede_repetir_sin_registrar_dos_veces(client, flujo, coredb_falso):
    id_caso = flujo.hasta_aprobado("45670004")
    coredb_falso.fallar_en = "/coredb/clientes/CLI"  # cae después del alta
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 503
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 200, r.text
    assert coredb_falso.rutas("POST").count("/coredb/clientes") == 1
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 200 and coredb_falso.rutas("POST").count("/coredb/clientes") == 1


def test_coredb_caido_responde_503(client, flujo, coredb_falso):
    id_caso = flujo.hasta_aprobado("45670005")
    coredb_falso.caido = True
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 503 and r.json()["error_code"] == "ERR-CAP-COREDB-NO-DISPONIBLE"


def test_correo_ya_usado_por_otro_cliente(client, flujo, coredb_falso):
    coredb_falso.agregar_cliente("11111111")
    id_caso = flujo.hasta_aprobado("45670006", correo="11111111@prev.pe")
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 409 and r.json()["error_code"] == "ERR-CAP-CORREO-DUPLICADO"


def test_habilitar_sin_requisitos_lista_lo_que_falta(client, flujo):
    id_caso = flujo.caso(flujo.solicitante("45670007"))
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-CAP-CASO-NO-LISTO"
    faltantes = r.json()["details"]["faltantes"]
    assert any("OTP" in f for f in faltantes) and any("RENIEC" in f for f in faltantes)
    assert any("TERMINOS" in f for f in faltantes)


def test_lista_restrictiva_rechaza_el_caso(client, flujo):
    sol = flujo.solicitante("99999999")
    id_caso = flujo.caso(sol)
    flujo.consentir(id_caso)
    flujo.validar(id_caso, ["LISTAS_NEGRAS"])
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "RECHAZADO" and "LISTAS_NEGRAS" in caso["motivo_cierre"]
    r = client.post(f"{BASE}/casos/{id_caso}/otp", headers=ASESOR, json={"canal": "SMS"})
    assert r.status_code == 409 and r.json()["error_code"] == "ERR-CAP-CASO-CERRADO"


def test_pep_queda_observado_hasta_la_debida_diligencia(client, flujo):
    sol = flujo.solicitante("88888880")
    id_caso = flujo.caso(sol)
    flujo.consentir(id_caso)
    flujo.otp(id_caso)
    flujo.validar(id_caso)
    flujo.riesgo(id_caso)
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "OBSERVADO"
    r = client.post(f"{BASE}/casos/{id_caso}/validaciones/manual", headers=ASESOR, json={
        "tipo": "PEP", "resultado": "APROBADO", "detalle": "Debida diligencia reforzada aprobada"})
    assert r.status_code == 201, r.text
    assert flujo.ver(id_caso)["estado"] == "APROBADO"


def test_riesgo_muy_alto_rechaza(client, flujo):
    sol = flujo.solicitante("45670009")  # termina en 9: DUDOSO
    id_caso = flujo.caso(sol)
    flujo.consentir(id_caso)
    perfil = flujo.riesgo(id_caso)
    assert perfil["calificacion"] == "MUY_ALTO"
    assert flujo.ver(id_caso)["estado"] == "RECHAZADO"


def test_consulta_nueva_exige_recalcular_el_perfil(client, flujo):
    id_caso = flujo.hasta_aprobado("45670010")
    client.post(f"{BASE}/casos/{id_caso}/consultas-riesgo", headers=ASESOR, json={"central": "INFOCORP"})
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "EN_VALIDACION"
    assert any("actualizado" in f for f in caso["faltantes"])


def test_consultar_centrales_exige_consentimiento(client, flujo):
    id_caso = flujo.caso(flujo.solicitante("45670011"))
    r = client.post(f"{BASE}/casos/{id_caso}/consultas-riesgo", headers=ASESOR, json={})
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-CAP-CONSENTIMIENTO-REQUERIDO"


def test_otp_se_bloquea_al_tercer_intento(client, flujo):
    id_caso = flujo.caso(flujo.solicitante("45670012"))
    flujo.consentir(id_caso)
    real = client.post(f"{BASE}/casos/{id_caso}/otp", headers=ASESOR, json={}).json()["data"]["codigo_simulado"]
    malo = "000000" if real != "000000" else "111111"
    estados = [client.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=ASESOR,
                           json={"codigo": malo}).json()["data"] for _ in range(3)]
    assert estados[-1]["estado_codigo"] == "BLOQUEADO"
    r = client.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=ASESOR, json={"codigo": real})
    assert r.status_code == 404


def test_solicitante_duplicado_y_un_solo_caso_abierto(client, flujo):
    a = flujo.solicitante("45670013")
    r = client.post(f"{BASE}/solicitantes", headers=ASESOR, json={
        "tipo_documento": "DNI", "numero_documento": "45670013", "nombres": "Otra", "apellido_paterno": "X",
        "celular": "958000000", "correo": "x@example.com"})
    assert r.status_code == 200 and r.json()["data"]["duplicado"] is True
    assert r.json()["data"]["solicitante"]["id_solicitante"] == a["id_solicitante"]
    flujo.caso(a)
    r = client.post(f"{BASE}/casos", headers=ASESOR, json={"id_solicitante": a["id_solicitante"], "canal": "WEB"})
    assert r.status_code == 409 and r.json()["error_code"] == "ERR-CAP-CASO-ABIERTO"


def test_reglas_del_documento_y_del_celular(client):
    base = {"nombres": "A", "apellido_paterno": "B", "celular": "958111222", "correo": "a@b.pe"}
    r = client.post(f"{BASE}/solicitantes", headers=ASESOR,
                    json={**base, "tipo_documento": "DNI", "numero_documento": "1234567"})
    assert r.status_code == 400
    r = client.post(f"{BASE}/solicitantes", headers=ASESOR,
                    json={**base, "tipo_documento": "PTP", "numero_documento": "12345678A"})
    assert r.json()["error_code"] == "ERR-CAP-DOCUMENTO-INVALIDO"
    r = client.post(f"{BASE}/solicitantes", headers=ASESOR, json={
        **base, "tipo_documento": "DNI", "numero_documento": "12345678", "celular": "+51958111222"})
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-VALIDACION-ESQUEMA"
    assert "958111222" not in r.text  # no se devuelven los valores recibidos


def test_permisos_del_personal(client, flujo):
    r = client.get(f"{BASE}/casos")
    assert r.status_code == 401 and r.json()["error_code"] == "ERR-CAP-TOKEN-REQUERIDO"
    r = client.get(f"{BASE}/casos", headers={"Authorization": "Bearer otro"})
    assert r.status_code == 401
    assert client.get(f"{BASE}/casos", headers=AUDITOR).status_code == 200
    r = client.post(f"{BASE}/solicitantes", headers=AUDITOR, json={
        "tipo_documento": "DNI", "numero_documento": "12345678", "nombres": "A", "apellido_paterno": "B",
        "celular": "958111222", "correo": "a@b.pe"})
    assert r.status_code == 403 and r.json()["error_code"] == "ERR-CAP-PERMISO-DENEGADO"


def test_revocar_la_habilitacion(client, flujo):
    id_caso = flujo.hasta_aprobado("45670014")
    cod = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR).json()["data"]["cod_cliente"]
    r = client.post(f"{BASE}/casos/{id_caso}/estado", headers=ASESOR,
                    json={"accion": "REVOCAR", "motivo": "Documento reportado como extraviado"})
    assert r.status_code == 200 and r.json()["data"]["estado"] == "REVOCADO"
    ref = client.get(f"/cap/references/{cod}", headers=SOL).json()
    assert ref["estado_habilitante"] == "REVOCADO"


def test_observacion_manual_detiene_y_se_levanta(client, flujo):
    id_caso = flujo.hasta_aprobado("45670015")
    client.post(f"{BASE}/casos/{id_caso}/estado", headers=ASESOR, json={"accion": "OBSERVAR", "motivo": "Revisar firma"})
    assert flujo.ver(id_caso)["estado"] == "OBSERVADO"
    assert client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR).status_code == 400
    client.post(f"{BASE}/casos/{id_caso}/estado", headers=ASESOR,
                json={"accion": "LEVANTAR_OBSERVACION", "motivo": "Firma conforme"})
    assert flujo.ver(id_caso)["estado"] == "APROBADO"


def test_rutas_de_sol_exigen_su_token(client, flujo):
    assert client.get("/cap/references").status_code == 401
    assert client.get("/cap/references", headers=ASESOR).status_code == 401
    assert client.get("/cap/references/CLI999999999", headers=SOL).status_code == 404
    assert client.get("/cap/references", headers=SOL, params={"limit": 51}).status_code == 400


def test_referencia_con_coredb_caido_es_503(client, flujo, coredb_falso):
    id_caso = flujo.hasta_aprobado("45670016")
    cod = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR).json()["data"]["cod_cliente"]
    coredb_falso.caido = True
    assert client.get(f"/cap/references/{cod}", headers=SOL).status_code == 503


def test_bandeja_de_casos(client, flujo):
    flujo.caso(flujo.solicitante("45670017"))
    r = client.get(f"{BASE}/casos", headers=ASESOR, params={"estado": "INICIADO"})
    assert r.status_code == 200
    assert r.json()["data"][0]["solicitante"]["numero_documento"] == "45670017"
    assert r.json()["success"] is True and r.json()["metadata"]["modulo_emisor"] == "CAPTACION"
