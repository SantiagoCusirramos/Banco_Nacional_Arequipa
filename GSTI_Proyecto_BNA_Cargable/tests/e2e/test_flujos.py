"""Escenarios funcionales (numerados como en el enunciado). Requieren: scripts/cargar_datos_prueba.py ya ejecutado."""
import os
import random
import time
import uuid
from pathlib import Path

import pytest

from tests.e2e.conftest import HUELLAS

pytestmark = pytest.mark.e2e


def dni_nuevo() -> str:
    return "9" + "".join(random.choices("0123456789", k=7))


def datos_cliente(**c):
    base = dict(modulo_origen="AGENCIAS", tipo_documento="PASAPORTE", numero_documento="T" + uuid.uuid4().hex[:8].upper(),
                nombres="Prueba", apellidos="Automatica", fecha_nacimiento="1990-01-01", ingreso_mensual=1000,
                direccion="Calle de Prueba 123", correo="prueba@example.com", telefono="954123456")
    return {**base, **c}


def ultimas(sis, tabla, **filtros):
    filas = sis.panel.get(f"/panel/api/solicitudes-{tabla}?limite=200").json()
    return [f for f in filas if all(f.get(k) == v for k, v in filtros.items())]


# ---------------------------------------------------------------- 1-3 registro
def test_01_registrar_ciudadano_en_reniec(sis):
    dni = dni_nuevo()
    r = sis.reniec.post("/admin/api/ciudadanos", json=dict(numero_documento=dni, nombres="Rosa Maria", apellidos="Test Prueba", fecha_nacimiento="1993-02-03", genero="F"))
    assert r.status_code == 201
    assert any(c["numero_documento"] == dni for c in sis.reniec.get(f"/admin/api/ciudadanos?q={dni}").json()["ciudadanos"])
    assert sis.reniec.post("/admin/api/ciudadanos", json=dict(numero_documento=dni, nombres="X", apellidos="Y", fecha_nacimiento="1993-02-03", genero="F")).status_code == 409
    sis.reniec.delete(f"/admin/api/ciudadanos/{dni}")


def test_02_y_03_registrar_dni_valido_y_duplicado(sis):
    dni = dni_nuevo()
    sis.reniec.post("/admin/api/ciudadanos", json=dict(numero_documento=dni, nombres="Rosa Maria", apellidos="Test Prueba", fecha_nacimiento="1993-02-03", genero="F"))
    try:
        cuerpo = datos_cliente(tipo_documento="DNI", numero_documento=dni, nombres="ROSA MARÍA", apellidos="test prueba", fecha_nacimiento="1993-02-03")  # mayúsculas/tildes no importan
        http, r = sis.lab("registrar", cuerpo)
        assert http == 201 and r["correcto"] and isinstance(r["cliente_id"], int) and r["verificacion_reniec"] is True
        http, r = sis.lab("registrar", cuerpo)  # duplicado
        assert http == 409 and r == {"correcto": False, "codigo": "CLIENTE_DUPLICADO", "mensaje": "El cliente ya está registrado"}
        resultados = [f["resultado"] for f in ultimas(sis, "registro", numero_documento=dni)]
        assert "REGISTRADO" in resultados and "RECHAZADO_CLIENTE_DUPLICADO" in resultados
    finally:
        sis.reniec.delete(f"/admin/api/ciudadanos/{dni}")


def test_registro_dni_con_datos_distintos_a_reniec_se_rechaza(sis):
    http, r = sis.lab("registrar", datos_cliente(tipo_documento="DNI", numero_documento="70000002", nombres="María Elena", apellidos="Otro Apellido", fecha_nacimiento="1995-11-02"))
    assert http == 422 and r["codigo"] == "DATOS_NO_COINCIDEN"
    assert any(f["resultado"] == "RECHAZADO_DATOS_NO_COINCIDEN" for f in ultimas(sis, "registro", numero_documento="70000002"))


def test_registro_dni_inexistente_en_reniec(sis):
    http, r = sis.lab("registrar", datos_cliente(tipo_documento="DNI", numero_documento="70000099", fecha_nacimiento="1990-01-01"))
    assert http == 422 and r["codigo"] == "DNI_NO_ENCONTRADO"


def test_registro_pasaporte_y_ptp_sin_verificacion_reniec(sis):
    for tipo, numero in (("PASAPORTE", "P" + uuid.uuid4().hex[:8].upper()), ("PTP", "PTP" + uuid.uuid4().hex[:6].upper())):
        http, r = sis.lab("registrar", datos_cliente(tipo_documento=tipo, numero_documento=numero))
        assert http == 201 and r["verificacion_reniec"] is False and "sin verificación en reniec" in r["aviso"].lower()


@pytest.mark.parametrize("cambios", [
    dict(correo="no-es-correo"), dict(ingreso_mensual=-10), dict(fecha_nacimiento="31/12/1990"),
    dict(numero_documento=123456789), dict(telefono=954123456), dict(modulo_origen="OTRO"),
])
def test_registro_invalido_se_rechaza_y_se_audita(sis, cambios):
    cuerpo = datos_cliente(**cambios)
    http, r = sis.lab("registrar", cuerpo)
    assert http == 422 and r["codigo"] == "DATOS_INVALIDOS" and r["correcto"] is False
    if isinstance(cuerpo["numero_documento"], str) and cuerpo["modulo_origen"] == "AGENCIAS":
        assert any(f["resultado"] == "RECHAZADO_DATOS_INVALIDOS" for f in ultimas(sis, "registro", numero_documento=cuerpo["numero_documento"]))


# ---------------------------------------------------------------- 4-9 validación por documento
def test_04_dni_en_reniec_y_banco(sis):
    http, r = sis.lab("validar-documento", dict(modulo_origen="CUENTAS", tipo_documento="DNI", numero_documento="70000001", fecha_nacimiento="1990-05-14"))
    assert http == 200 and r["correcto"] and r["identidad"] == "DNI_VALIDO" and r["registrado_bna"] is True
    assert r["cliente"]["nombres"] == "Juan Carlos" and r["cliente"]["apellidos"] == "Pérez Quispe" and isinstance(r["cliente"]["id"], int)


def test_05_dni_solo_en_reniec(sis):
    http, r = sis.lab("validar-documento", dict(modulo_origen="CUENTAS", tipo_documento="DNI", numero_documento="70000003", fecha_nacimiento="1988-03-21"))
    assert http == 200 and r["identidad"] == "DNI_VALIDO" and r["registrado_bna"] is False and "cliente" not in r


def test_06_dni_inexistente(sis):
    http, r = sis.lab("validar-documento", dict(modulo_origen="CUENTAS", tipo_documento="DNI", numero_documento="70000099", fecha_nacimiento="1990-01-01"))
    assert http == 200 and r["identidad"] == "DNI_NO_ENCONTRADO" and "cliente" not in r


def test_07_dni_con_nacimiento_incorrecto_no_entrega_datos(sis):
    http, r = sis.lab("validar-documento", dict(modulo_origen="CUENTAS", tipo_documento="DNI", numero_documento="70000001", fecha_nacimiento="1991-05-14"))
    assert http == 200 and r["identidad"] == "DATOS_NO_COINCIDEN" and "cliente" not in r


def test_08_pasaporte_no_consultado_en_reniec(sis):
    http, r = sis.lab("validar-documento", dict(modulo_origen="TARJETAS", tipo_documento="PASAPORTE", numero_documento="AB123456", fecha_nacimiento="1985-07-09"))
    assert http == 200 and r["identidad"] == "PASAPORTE_NO_CONSULTADO" and r["registrado_bna"] is True
    assert r["cliente"] == {"id": r["cliente"]["id"]}  # nada de datos personales: el documento no fue verificado oficialmente
    assert "no verificado" in r["aviso"].lower()
    http, r = sis.lab("validar-documento", dict(modulo_origen="TARJETAS", tipo_documento="PASAPORTE", numero_documento="AB123456", fecha_nacimiento="1985-07-10"))
    assert r["registrado_bna"] is True and "cliente" not in r


def test_09_ptp_no_consultado_en_reniec(sis):
    http, r = sis.lab("validar-documento", dict(modulo_origen="TARJETAS", tipo_documento="PTP", numero_documento="PTP2024001", fecha_nacimiento="1992-01-30"))
    assert http == 200 and r["identidad"] == "PTP_NO_CONSULTADO" and r["registrado_bna"] is True


# ---------------------------------------------------------------- 13-15 huella
def test_13_14_15_huella(sis):
    # 13: la plantilla de 70000001 (huella A) ya está en RENIEC (script de datos de prueba)
    ids = {c["numero_documento"]: c for c in sis.reniec.get("/admin/api/ciudadanos?q=70000001").json()["ciudadanos"]}
    assert ids["70000001"]["tiene_huella"] is True

    misma = sis.plantilla("HUELLA", HUELLAS / "huella_A_variante.png")  # otra captura del MISMO dedo
    cuerpo = dict(modulo_origen="CAJERO_AUTOMATICO", tipo_documento="DNI", numero_documento="70000001", tipo_biometria="HUELLA",
                  formato="ISO_19794_2_2005", codificacion="base64", template=misma["template"])
    http, r = sis.lab("validar-biometria", cuerpo)
    assert http == 200 and r["coincide"] is True and r["registrado_bna"] is True and r["cliente"]["nombres"] == "Juan Carlos"  # 14

    otra = sis.plantilla("HUELLA", HUELLAS / "huella_B.png")  # OTRO dedo
    http, r = sis.lab("validar-biometria", {**cuerpo, "template": otra["template"]})
    assert http == 200 and r["correcto"] is True and r["coincide"] is False and "cliente" not in r and "registrado_bna" not in r  # 15


def test_biometria_resultados_de_borde(sis):
    huella = sis.plantilla("HUELLA", HUELLAS / "huella_A.png")["template"]
    base = dict(modulo_origen="BANCA_LINEA", tipo_documento="DNI", tipo_biometria="HUELLA", formato="ISO_19794_2_2005", codificacion="base64", template=huella)
    assert sis.lab("validar-biometria", {**base, "numero_documento": "70000003"})[1]["motivo"] == "SIN_PLANTILLA"
    assert sis.lab("validar-biometria", {**base, "numero_documento": "70000099"})[1]["motivo"] == "DNI_NO_ENCONTRADO"
    http, r = sis.lab("validar-biometria", {**base, "numero_documento": "70000001", "template": "AAAAAAAAAAAAAAAAAAAA"})
    assert http == 422 and r["codigo"] == "PLANTILLA_INVALIDA"  # error técnico, distinto de un "no coincide"
    http, r = sis.lab("validar-biometria", {**base, "tipo_documento": "PASAPORTE", "numero_documento": "AB123456"})
    assert http == 422 and r["codigo"] == "DATOS_INVALIDOS"  # biometría solo para DNI
    http, r = sis.lab("validar-biometria", {**base, "numero_documento": "70000001", "tipo_biometria": "FACIAL", "formato": "ARCFACE_EMBEDDING", "template": [0.1] * 10, "codificacion": None})
    assert http == 422 and r["codigo"] == "DATOS_INVALIDOS"


# ---------------------------------------------------------------- 10-12 rostro con fotos del propio usuario
ROSTROS = [os.getenv(v) for v in ("E2E_ROSTRO_A", "E2E_ROSTRO_A2", "E2E_ROSTRO_B")]


@pytest.mark.skipif(not all(ROSTROS), reason="Defina E2E_ROSTRO_A, E2E_ROSTRO_A2 (misma persona) y E2E_ROSTRO_B (otra persona) con rutas a imágenes de prueba")
def test_10_11_12_rostro(sis):
    dni = dni_nuevo()
    sis.reniec.post("/admin/api/ciudadanos", json=dict(numero_documento=dni, nombres="Rostro", apellidos="Prueba", fecha_nacimiento="1990-01-01", genero="F"))
    try:
        with open(ROSTROS[0], "rb") as f:
            r = sis.reniec.post(f"/admin/api/ciudadanos/{dni}/biometria/facial", files={"archivo": ("a.jpg", f)})
        assert r.status_code == 200 and r.json()["dimensiones"] == 512  # 10
        base = dict(modulo_origen="BANCA_LINEA", tipo_documento="DNI", numero_documento=dni, tipo_biometria="FACIAL", formato="ARCFACE_EMBEDDING")
        http, r = sis.lab("validar-biometria", {**base, "template": sis.plantilla("FACIAL", Path(ROSTROS[1]))["template"]})
        assert http == 200 and r["coincide"] is True  # 11
        http, r = sis.lab("validar-biometria", {**base, "template": sis.plantilla("FACIAL", Path(ROSTROS[2]))["template"]})
        assert http == 200 and r["coincide"] is False and "cliente" not in r  # 12
    finally:
        sis.reniec.delete(f"/admin/api/ciudadanos/{dni}")


# ---------------------------------------------------------------- 16-18 auditoría y módulo de origen
def test_16_17_18_solicitudes_y_modulo_origen(sis):
    sis.lab("validar-documento", dict(modulo_origen="BANCA_LINEA", tipo_documento="DNI", numero_documento="70000001", fecha_nacimiento="1990-05-14"))
    val = ultimas(sis, "validacion", modulo_origen="BANCA_LINEA", numero_documento="70000001", tipo_validacion="DOCUMENTO")
    assert val and val[0]["resultado"] == "DNI_VALIDO|REGISTRADO" and val[0]["fecha_solicitud"].endswith("Z")  # 17 y 18
    bio = ultimas(sis, "validacion", modulo_origen="CAJERO_AUTOMATICO", tipo_validacion="HUELLA")
    assert bio and bio[0]["resultado"] in ("COINCIDE|REGISTRADO", "NO_COINCIDE", "SIN_PLANTILLA", "DNI_NO_ENCONTRADO")
    reg = ultimas(sis, "registro", modulo_origen="AGENCIAS")
    assert reg  # 16
    ids = [f["id"] for f in sis.panel.get("/panel/api/solicitudes-validacion?limite=50&orden=recientes").json()]
    assert ids == sorted(ids, reverse=True)
    ids = [f["id"] for f in sis.panel.get("/panel/api/solicitudes-validacion?limite=50&orden=antiguas").json()]
    assert ids == sorted(ids)


# ---------------------------------------------------------------- seguridad y privacidad
def test_rutas_internas_exigen_credenciales(sis):
    assert sis.publico.post("/clientes/validar-documento", json={}).status_code == 401  # sin token de servicio
    assert sis.publico.post("/clientes/validar-documento", json={}, headers={"X-Service-Token": "incorrecto"}).status_code == 401
    assert sis.publico.get("/panel").status_code == 401  # panel con Basic
    import httpx

    assert httpx.get(f"{sis.reniec.base_url}/admin/api/ciudadanos").status_code == 401
    assert httpx.post(f"{sis.reniec.base_url}/interno/validar-dni", json={"numero_documento": "70000001", "fecha_nacimiento": "1990-05-14"}).status_code == 401


def test_la_consola_oculta_las_plantillas(sis):
    huella = sis.plantilla("HUELLA", HUELLAS / "huella_A.png")["template"]
    r = sis.panel.post("/panel/api/lab/validar-biometria", json=dict(modulo_origen="BANCA_LINEA", tipo_documento="DNI", numero_documento="70000001",
                                                                     tipo_biometria="HUELLA", formato="ISO_19794_2_2005", codificacion="base64", template=huella)).json()
    assert huella not in str(r) and "oculto" in r["peticion"]["template"] and "Base64" in r["peticion"]["template"]


def test_los_errores_no_son_html_ni_exponen_trazas(sis):
    r = sis.publico.get("/no-existe")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


# ---------------------------------------------------------------- 19 RENIEC detenido
@pytest.mark.reniec_caido
def test_19_reniec_caido_no_da_identidad_positiva(sis):
    http, r = sis.lab("validar-documento", dict(modulo_origen="BANCA_LINEA", tipo_documento="DNI", numero_documento="70000001", fecha_nacimiento="1990-05-14"))
    assert http == 503 and r["codigo"] == "RENIEC_NO_DISPONIBLE" and r["correcto"] is False
    assert "identidad" not in r and "cliente" not in r
    http, r = sis.lab("registrar", datos_cliente(tipo_documento="DNI", numero_documento="70000002", nombres="María Elena", apellidos="Mamani Condori", fecha_nacimiento="1995-11-02"))
    assert http == 503 and r["codigo"] == "RENIEC_NO_DISPONIBLE"
    http, r = sis.lab("validar-biometria", dict(modulo_origen="BANCA_LINEA", tipo_documento="DNI", numero_documento="70000001", tipo_biometria="HUELLA",
                                                formato="ISO_19794_2_2005", codificacion="base64", template="Rk1SAAAAAAAAAAAAAAAAAAAA"))
    assert http == 503 and r["codigo"] == "RENIEC_NO_DISPONIBLE" and "coincide" not in r
    # Los pasaportes no dependen de RENIEC: siguen funcionando
    http, r = sis.lab("validar-documento", dict(modulo_origen="BANCA_LINEA", tipo_documento="PASAPORTE", numero_documento="AB123456", fecha_nacimiento="1985-07-09"))
    assert http == 200 and r["identidad"] == "PASAPORTE_NO_CONSULTADO"
    time.sleep(0.5)
    assert any(f["resultado"] == "RENIEC_NO_DISPONIBLE" for f in ultimas(sis, "validacion", modulo_origen="BANCA_LINEA", tipo_documento="DNI"))  # la solicitud quedó registrada
