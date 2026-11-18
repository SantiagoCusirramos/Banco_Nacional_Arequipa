"""El expediente de captación de punta a punta, contra COREDB y la base integrada reales."""

import uuid

from CAPTACION.services.captacion import hoy_lima
from CAPTACION.tests.conftest import BASE, SOL, coredb, dni


def test_flujo_completo_registra_al_cliente_en_coredb_y_deja_la_referencia(client, flujo, asesor, admin):
    numero = dni()
    id_caso = flujo.hasta_aprobado(numero)
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "APROBADO" and caso["listo_para_habilitar"] is True, caso["faltantes"]
    assert caso["perfil"]["calificacion"] == "BAJO"
    assert [v["tipo"] for v in caso["validaciones"]] == ["CELULAR", "RENIEC", "LISTAS_NEGRAS", "PEP"]

    datos = flujo.habilitar(id_caso)
    assert datos["estado"] == "HABILITADO" and datos["cliente_nuevo"] is True
    cod = datos["cod_cliente"]
    assert cod.startswith("CLI")

    # En COREDB: el cliente ACTIVO y HABILITADO, con la verificación del celular.
    cliente = coredb("GET", f"/coredb/clientes/{cod}", admin, 200).json()
    assert cliente["numero_documento"] == numero and cliente["estado_cliente"] == "ACTIVO"
    assert cliente["estado_habilitante"] == "HABILITADO" and cliente["version_contrato"] == "v1"
    assert cliente["apellido_paterno"] == "Huamán" and cliente["apellido_materno"] == "Ccori"
    assert datos["id_verificacion_captacion"] == cliente["id_verificacion_captacion"]
    # La bitácora de la base: el asesor hizo cada paso y el usuario de servicio registró al cliente.
    eventos = coredb("GET", "/coredb/auditoria", admin, 200,
                     params={"entidad": "caso_captacion", "id_entidad": id_caso, "limite": 100}).json()
    actores = {e["accion"]: e["actor"] for e in eventos}
    assert actores["ABRIR_CASO"] == asesor[1] and actores["HABILITAR"] == asesor[1]
    assert actores["VINCULAR_CLIENTE"] == "svc-captacion"

    # Lo que consulta Solicitud de Crédito (CR-INT-01).
    r = client.get(f"/cap/references/{cod}", headers=SOL)
    assert r.status_code == 200, r.text
    ref = r.json()
    assert ref["id_cliente"] == cod and ref["id_caso"] == id_caso
    assert ref["estado_cliente"] == "ACTIVO" and ref["estado_habilitante"] == "HABILITADO"
    assert ref["fecha_verificacion"] == hoy_lima().isoformat()
    assert ref["vigente_hasta"] > ref["fecha_verificacion"]
    assert ref["id_verificacion"] == cliente["id_verificacion_captacion"]
    assert ref["simulado"] is True and ref["version_contrato"] == "CR-INT-01-PROPUESTA-v2"
    assert "celular" not in ref and "correo" not in ref  # SOL no recibe datos de contacto

    r = client.post("/cap/references/search", headers=SOL, json={"search": numero, "limit": 50})
    assert r.status_code == 200, r.text
    assert [x["id_cliente"] for x in r.json()] == [cod]
    # P-1: el documento nunca va en la consulta (quedaría en los registros de acceso).
    assert client.get("/cap/references", headers=SOL, params={"search": numero}).status_code in (404, 405)

    # El asesor ve la misma referencia desde el expediente.
    r = client.get(f"{BASE}/casos/{id_caso}/referencia", headers=asesor[0])
    assert r.json()["data"]["id_cliente"] == cod


def test_el_correo_tambien_se_verifica_y_queda_en_el_cliente(client, flujo, admin):
    id_caso = flujo.hasta_aprobado()
    flujo.otp(id_caso, "EMAIL")
    cod = flujo.habilitar(id_caso)["cod_cliente"]
    eventos = coredb("GET", "/coredb/auditoria", admin, 200,
                     params={"accion": "REGISTRAR_VALIDACION", "limite": 200}).json()
    tipos = sorted(e["detalle"]["tipo_validacion"] for e in eventos if e["detalle"].get("cod_cliente") == cod)
    assert tipos == ["CELULAR", "CORREO"]


def test_habilitar_reutiliza_al_cliente_activo_que_ya_existe(client, flujo, admin):
    numero = dni()
    cod = coredb("POST", "/coredb/clientes", admin, 201, json={
        "tipo_documento": "DNI", "numero_documento": numero, "nombres": "Rosa", "apellido_paterno": "Huamán",
        "correo": f"previa.{numero}@example.com", "celular": "9" + numero, "version_contrato": "v1",
        "estado_habilitante": "OBSERVADO"}).json()["cod_cliente"]
    coredb("POST", f"/coredb/clientes/{cod}/estado", admin, 200,
           json={"estado": "ACTIVO", "motivo": "Identidad confirmada antes (prueba)"})
    datos = flujo.habilitar(flujo.hasta_aprobado(numero))
    assert datos["cod_cliente"] == cod and datos["cliente_nuevo"] is False


def test_cliente_bloqueado_en_coredb_deja_el_caso_observado(client, flujo, asesor, admin):
    numero = dni()
    cod = coredb("POST", "/coredb/clientes", admin, 201, json={
        "tipo_documento": "DNI", "numero_documento": numero, "nombres": "Rosa", "apellido_paterno": "Huamán",
        "correo": f"bloq.{numero}@example.com", "celular": "9" + numero, "version_contrato": "v1",
        "estado_habilitante": "OBSERVADO"}).json()["cod_cliente"]
    coredb("POST", f"/coredb/clientes/{cod}/estado", admin, 200,
           json={"estado": "BLOQUEADO", "motivo": "Bloqueo de prueba"})
    id_caso = flujo.hasta_aprobado(numero)
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=asesor[0])
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-CAP-CLIENTE-NO-ACTIVO"
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "OBSERVADO" and caso["cod_cliente"] is None
    assert any("BLOQUEADO" in f for f in caso["faltantes"])


def test_habilitar_se_puede_repetir_sin_registrar_dos_veces(client, flujo, persona):
    id_caso = flujo.hasta_aprobado()
    primero = flujo.habilitar(id_caso)
    assert flujo.habilitar(id_caso) == primero
    numero = flujo.ver(id_caso)["solicitante"]["numero_documento"]
    operador, _ = persona("OPERADOR")  # tiene VALIDAR_IDENTIDAD
    verificacion = coredb("POST", "/coredb/clientes/validaciones/documento", operador["Authorization"][7:], 201, json={
        "tipo_documento": "DNI", "numero_documento": numero, "identidad_verificada": True}).json()
    assert verificacion["cliente"]["cod_cliente"] == primero["cod_cliente"]


def test_coredb_caido_responde_503(client, flujo, coredb_caido, asesor):
    r = client.get(f"{BASE}/casos", headers=asesor[0])
    assert r.status_code == 503 and r.json()["error_code"] == "ERR-CAP-COREDB-NO-DISPONIBLE"


def test_correo_ya_usado_por_otro_cliente(client, flujo, asesor, admin):
    numero = dni()
    correo = f"compartido.{numero}@example.com"
    coredb("POST", "/coredb/clientes", admin, 201, json={
        "tipo_documento": "DNI", "numero_documento": dni(), "nombres": "Otra", "apellido_paterno": "Persona",
        "correo": correo, "celular": "9" + numero, "version_contrato": "v1", "estado_habilitante": "OBSERVADO"})
    id_caso = flujo.hasta_aprobado(numero, correo=correo)
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=asesor[0])
    assert r.status_code == 409 and r.json()["error_code"] == "ERR-CAP-CORREO-DUPLICADO"
    assert flujo.ver(id_caso)["estado"] == "APROBADO"


def test_habilitar_sin_requisitos_lista_lo_que_falta(client, flujo, asesor):
    id_caso = flujo.caso(flujo.solicitante())
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=asesor[0])
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-CAP-CASO-NO-LISTO"
    faltantes = r.json()["details"]["faltantes"]
    assert any("OTP" in f for f in faltantes) and any("RENIEC" in f for f in faltantes)
    assert any("TERMINOS" in f for f in faltantes)


def test_lista_restrictiva_rechaza_el_caso_y_no_consulta_lo_demas(client, flujo, asesor):
    id_caso = flujo.caso(flujo.solicitante("99999999"))
    flujo.consentir(id_caso)
    creadas = flujo.validar(id_caso, ["RENIEC", "LISTAS_NEGRAS", "PEP"])
    assert [v["tipo"] for v in creadas] == ["RENIEC", "LISTAS_NEGRAS"]
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "RECHAZADO" and "LISTAS_NEGRAS" in caso["motivo_cierre"]
    r = client.post(f"{BASE}/casos/{id_caso}/otp", headers=asesor[0], json={"canal": "SMS"})
    assert r.status_code == 409 and r.json()["error_code"] == "ERR-CAP-CASO-CERRADO"


def test_pep_queda_observado_hasta_la_debida_diligencia(client, flujo, asesor):
    id_caso = flujo.caso(flujo.solicitante("88888880"))
    flujo.consentir(id_caso)
    flujo.otp(id_caso)
    flujo.validar(id_caso)
    flujo.riesgo(id_caso)
    assert flujo.ver(id_caso)["estado"] == "OBSERVADO"
    r = client.post(f"{BASE}/casos/{id_caso}/validaciones/manual", headers=asesor[0], json={
        "tipo": "PEP", "resultado": "APROBADO", "detalle": "Debida diligencia reforzada aprobada"})
    assert r.status_code == 201, r.text
    assert r.json()["data"]["proveedor"] == "MANUAL"
    # El perfil se calculó con el PEP observado: sigue vigente, el caso queda APROBADO.
    assert flujo.ver(id_caso)["estado"] == "APROBADO"


def test_riesgo_muy_alto_rechaza(client, flujo):
    id_caso = flujo.caso(flujo.solicitante(dni("9")))  # termina en 9: DUDOSO
    flujo.consentir(id_caso)
    perfil = flujo.riesgo(id_caso)
    assert perfil["calificacion"] == "MUY_ALTO"
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "RECHAZADO" and caso["motivo_cierre"] == "Perfil de riesgo MUY_ALTO"


def test_consulta_nueva_exige_recalcular_el_perfil(client, flujo, asesor):
    id_caso = flujo.hasta_aprobado()
    client.post(f"{BASE}/casos/{id_caso}/consultas-riesgo", headers=asesor[0], json={"central": "INFOCORP"})
    caso = flujo.ver(id_caso)
    assert caso["estado"] == "EN_VALIDACION"
    assert any("actualizado" in f for f in caso["faltantes"])


def test_reporte_manual_de_una_central(client, flujo, asesor):
    id_caso = flujo.caso(flujo.solicitante())
    flujo.consentir(id_caso)
    r = client.post(f"{BASE}/casos/{id_caso}/consultas-riesgo", headers=asesor[0], json={
        "central": "EQUIFAX", "reporte": {"calificacion": "CPP", "deuda_total": "1250.50", "entidades": 2,
                                          "dias_mora": 12}})
    assert r.status_code == 201, r.text
    assert r.json()["data"] | {"fecha": None} == {
        "central": "EQUIFAX", "calificacion": "CPP", "deuda_total": 1250.5, "entidades": 2, "dias_mora": 12,
        "fuente": "MANUAL", "fecha": None}


def test_consultar_centrales_exige_consentimiento(client, flujo, asesor):
    id_caso = flujo.caso(flujo.solicitante())
    r = client.post(f"{BASE}/casos/{id_caso}/consultas-riesgo", headers=asesor[0], json={})
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-CAP-CONSENTIMIENTO-REQUERIDO"


def test_otp_se_bloquea_al_tercer_intento(client, flujo, asesor):
    id_caso = flujo.caso(flujo.solicitante())
    flujo.consentir(id_caso)
    enviado = client.post(f"{BASE}/casos/{id_caso}/otp", headers=asesor[0], json={}).json()["data"]
    assert enviado["destino_enmascarado"].startswith("******")
    real = enviado["codigo_simulado"]
    malo = "000000" if real != "000000" else "111111"
    estados = [client.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=asesor[0],
                           json={"codigo": malo}).json()["data"] for _ in range(3)]
    assert [e["intentos_restantes"] for e in estados] == [2, 1, 0]
    assert estados[-1]["estado_codigo"] == "BLOQUEADO" and not estados[-1]["verificado"]
    r = client.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=asesor[0], json={"codigo": real})
    assert r.status_code == 404 and r.json()["error_code"] == "ERR-CAP-OTP-NO-ENCONTRADO"


def test_un_otp_nuevo_reemplaza_al_anterior(client, flujo, asesor):
    id_caso = flujo.caso(flujo.solicitante())
    flujo.consentir(id_caso)
    viejo = client.post(f"{BASE}/casos/{id_caso}/otp", headers=asesor[0], json={}).json()["data"]["codigo_simulado"]
    nuevo = client.post(f"{BASE}/casos/{id_caso}/otp", headers=asesor[0], json={}).json()["data"]["codigo_simulado"]
    if viejo != nuevo:
        r = client.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=asesor[0], json={"codigo": viejo})
        assert r.json()["data"]["verificado"] is False
    r = client.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=asesor[0], json={"codigo": nuevo})
    assert r.json()["data"]["verificado"] is True


def test_solicitante_duplicado_y_un_solo_caso_abierto(client, flujo, asesor):
    numero = dni()
    a = flujo.solicitante(numero)
    r = client.post(f"{BASE}/solicitantes", headers=asesor[0], json={
        "tipo_documento": "DNI", "numero_documento": numero, "nombres": "Otra", "apellido_paterno": "X",
        "celular": "958000000", "correo": "x@example.com"})
    assert r.status_code == 200 and r.json()["data"]["duplicado"] is True
    assert r.json()["data"]["solicitante"]["id_solicitante"] == a["id_solicitante"]
    id_caso = flujo.caso(a)
    r = client.post(f"{BASE}/casos", headers=asesor[0], json={"id_solicitante": a["id_solicitante"], "canal": "WEB"})
    assert r.status_code == 409 and r.json()["error_code"] == "ERR-CAP-CASO-ABIERTO"
    assert r.json()["details"] == {"id_caso": id_caso, "estado": "INICIADO"}
    r = client.post(f"{BASE}/solicitantes/busqueda", headers=asesor[0], json={"documento": numero})
    assert r.status_code == 200, r.text
    encontrados = r.json()["data"]
    assert client.get(f"{BASE}/solicitantes", headers=asesor[0], params={"documento": numero}).status_code == 405
    assert [s["id_solicitante"] for s in encontrados] == [a["id_solicitante"]]
    visto = client.get(f"{BASE}/solicitantes/{a['id_solicitante']}", headers=asesor[0]).json()["data"]
    assert visto == a


def test_reglas_del_documento_y_del_celular(client, asesor):
    base = {"nombres": "A", "apellido_paterno": "B", "celular": "958111222", "correo": "a@b.pe"}
    r = client.post(f"{BASE}/solicitantes", headers=asesor[0],
                    json={**base, "tipo_documento": "DNI", "numero_documento": "1234567"})
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-CAP-DOCUMENTO-INVALIDO"
    r = client.post(f"{BASE}/solicitantes", headers=asesor[0],
                    json={**base, "tipo_documento": "PTP", "numero_documento": "12345678A"})
    assert r.json()["error_code"] == "ERR-CAP-DOCUMENTO-INVALIDO"
    r = client.post(f"{BASE}/solicitantes", headers=asesor[0], json={
        **base, "tipo_documento": "DNI", "numero_documento": "12345678", "celular": "+51958111222"})
    assert r.status_code == 400 and r.json()["error_code"] == "ERR-VALIDACION-ESQUEMA"
    assert "958111222" not in r.text  # no se devuelven los valores recibidos


def test_permisos_del_personal(client, flujo, persona):
    r = client.get(f"{BASE}/casos")
    assert r.status_code == 401 and r.json()["error_code"] == "ERR-CAP-TOKEN-REQUERIDO"
    r = client.get(f"{BASE}/casos", headers={"Authorization": "Bearer otro"})
    assert r.status_code == 401
    auditor, _ = persona("AUDITOR")
    assert client.get(f"{BASE}/casos", headers=auditor).status_code == 200
    r = client.post(f"{BASE}/solicitantes", headers=auditor, json={
        "tipo_documento": "DNI", "numero_documento": "12345678", "nombres": "A", "apellido_paterno": "B",
        "celular": "958111222", "correo": "a@b.pe"})
    assert r.status_code == 403 and r.json()["error_code"] == "ERR-CAP-PERMISO-DENEGADO"


def test_revocar_la_habilitacion(client, flujo, asesor):
    id_caso = flujo.hasta_aprobado()
    cod = flujo.habilitar(id_caso)["cod_cliente"]
    r = client.post(f"{BASE}/casos/{id_caso}/estado", headers=asesor[0],
                    json={"accion": "REVOCAR", "motivo": "Documento reportado como extraviado"})
    assert r.status_code == 200 and r.json()["data"]["estado"] == "REVOCADO"
    ref = client.get(f"/cap/references/{cod}", headers=SOL).json()
    assert ref["estado_habilitante"] == "REVOCADO"


def test_observacion_manual_detiene_y_se_levanta(client, flujo, asesor):
    id_caso = flujo.hasta_aprobado()
    client.post(f"{BASE}/casos/{id_caso}/estado", headers=asesor[0], json={"accion": "OBSERVAR", "motivo": "Revisar firma"})
    assert flujo.ver(id_caso)["estado"] == "OBSERVADO"
    assert client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=asesor[0]).status_code == 400
    client.post(f"{BASE}/casos/{id_caso}/estado", headers=asesor[0],
                json={"accion": "LEVANTAR_OBSERVACION", "motivo": "Firma conforme"})
    assert flujo.ver(id_caso)["estado"] == "APROBADO"


def test_un_caso_inexistente_es_404(client, asesor):
    for ruta in (f"{BASE}/casos/{uuid.uuid4()}", f"{BASE}/casos/no-es-un-uuid"):
        r = client.get(ruta, headers=asesor[0])
        assert r.status_code == 404 and r.json()["error_code"] == "ERR-CAP-CASO-NO-ENCONTRADO"


def test_rutas_de_sol_exigen_su_token(client, asesor):
    assert client.post("/cap/references/search", json={}).status_code == 401
    assert client.post("/cap/references/search", headers=asesor[0], json={}).status_code == 401
    assert client.get("/cap/references/CLI999999999", headers=SOL).status_code == 404
    assert client.post("/cap/references/search", headers=SOL, json={"limit": 51}).status_code == 400
    assert client.post("/cap/references/search", headers=SOL, json={"search": "x" * 101}).status_code == 400


def test_referencia_con_coredb_caido_es_503(client, flujo, coredb_caido):
    assert client.get("/cap/references/CLI000000001", headers=SOL).status_code == 503
    assert client.post("/cap/references/search", headers=SOL, json={"search": "x"}).status_code == 503


def test_bandeja_de_casos(client, flujo, asesor):
    numero = dni()
    id_caso = flujo.caso(flujo.solicitante(numero))
    r = client.get(f"{BASE}/casos", headers=asesor[0], params={"estado": "INICIADO", "limite": 200})
    assert r.status_code == 200
    fila = next(c for c in r.json()["data"] if c["id_caso"] == id_caso)
    assert fila["solicitante"]["numero_documento"] == numero
    assert r.json()["success"] is True and r.json()["metadata"]["modulo_emisor"] == "CAPTACION"
