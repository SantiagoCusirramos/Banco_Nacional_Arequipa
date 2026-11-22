"""Insertar la tarjeta con el documento y los 4 últimos dígitos (hallazgos B4 y C7 de la prueba
«solo con el mouse»): el cajero pedía el UUID de la tarjeta, que solo aparece en la ficha de
Tarjetas, y mostraba «•••• B080» (el final del UUID) en vez de los dígitos de la tarjeta.

El cajero busca con el token del operador que lo abrió: el cliente por su documento exacto
(COREDB, POST con el documento en el cuerpo) y sus tarjetas (TARJETAS). Si no coincide, el mismo
error genérico, sin decir si el documento existe. El PIN sigue siendo el que autoriza.
"""
from pathlib import Path

import httpx

AUTH = {"Authorization": "Bearer token-del-operador"}
ID = "7e570001-0000-4000-8000-000000000001"
OTRA = "7e570001-0000-4000-8000-000000000002"
BUSQUEDA = "/bus/coredb/coredb/captacion/solicitantes/busqueda"


def solicitante(documento="45871236", cod="CLI000000001"):
    return {"id_solicitante": "s-1", "tipo_documento": "DNI", "numero_documento": documento, "nombres": "CARMEN",
            "apellido_paterno": "QUISPE", "apellido_materno": None, "celular": "987123456", "correo": "c@x.pe",
            "cod_cliente": cod, "creado_por": "asesora", "fecha_registro": "2026-11-22T10:00:00Z"}


def tarjeta(id_tarjeta=ID, ultimos4="3886", estado="ACTIVA"):
    return {"id_tarjeta": id_tarjeta, "bin": "004499", "ultimos4": ultimos4, "fecha_emision": "2026-11-22",
            "fecha_vencimiento": "2030-11-30", "estado_tarjeta": estado, "cod_cliente": "CLI000000001",
            "num_cuenta": "24233417472693"}


def test_identifica_la_tarjeta_por_documento_y_ultimos_4(client, core):
    core.respuesta = [httpx.Response(200, json=[solicitante("458712360"), solicitante()]),
                      httpx.Response(200, json=[tarjeta(OTRA, "1111"), tarjeta()])]
    r = client.post("/api/identificar-tarjeta", json={"documento": "45871236", "ultimos4": "3886"}, headers=AUTH)
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"id_tarjeta": ID, "ultimos4": "3886"}
    busqueda, tarjetas = core.llamadas
    assert busqueda["metodo"] == "POST" and busqueda["ruta"] == BUSQUEDA
    assert busqueda["json"]["documento"] == "45871236" and busqueda["json"]["con_cliente"] is True
    assert busqueda["query"] == {}  # el documento nunca va en la URL
    assert busqueda["headers"]["authorization"] == "Bearer token-del-operador"
    assert tarjetas["ruta"] == "/bus/tarjetas/api/v1/tarjetas/cliente/CLI000000001"


def test_solo_cuenta_el_documento_exacto(client, core):
    # La búsqueda de COREDB es por parte del documento: 458712360 no es 45871236.
    core.respuesta = [httpx.Response(200, json=[solicitante("458712360")])]
    r = client.post("/api/identificar-tarjeta", json={"documento": "45871236", "ultimos4": "3886"}, headers=AUTH)
    assert r.status_code == 404
    assert r.json()["error_code"] == "ERR-ATM-TARJETA-NO-RECONOCIDA"


def test_mismo_error_si_el_documento_existe_pero_los_digitos_no(client, core):
    core.respuesta = [httpx.Response(200, json=[solicitante()]), httpx.Response(200, json=[tarjeta()])]
    r1 = client.post("/api/identificar-tarjeta", json={"documento": "45871236", "ultimos4": "0000"}, headers=AUTH)
    core.llamadas.clear()
    core.respuesta = [httpx.Response(200, json=[])]
    r2 = client.post("/api/identificar-tarjeta", json={"documento": "11111111", "ultimos4": "3886"}, headers=AUTH)
    assert r1.status_code == r2.status_code == 404
    assert (r1.json()["error_code"], r1.json()["message"]) == (r2.json()["error_code"], r2.json()["message"])


def test_prefiere_la_tarjeta_activa_si_hay_dos_con_los_mismos_digitos(client, core):
    core.respuesta = [httpx.Response(200, json=[solicitante()]),
                      httpx.Response(200, json=[tarjeta(OTRA, "3886", "CANCELADA"), tarjeta(ID, "3886", "ACTIVA")])]
    r = client.post("/api/identificar-tarjeta", json={"documento": "45871236", "ultimos4": "3886"}, headers=AUTH)
    assert r.json()["data"]["id_tarjeta"] == ID


def test_sin_operador_no_busca(client, core):
    r = client.post("/api/identificar-tarjeta", json={"documento": "45871236", "ultimos4": "3886"})
    assert r.status_code == 401
    assert core.llamadas == []


def test_valida_el_formato(client, core):
    for cuerpo in ({"documento": "4587", "ultimos4": "3886"}, {"documento": "45871236", "ultimos4": "38a6"},
                   {"documento": "45871236"}, {"documento": "45871236", "ultimos4": "3886", "pin": "1234"}):
        assert client.post("/api/identificar-tarjeta", json=cuerpo, headers=AUTH).status_code in (400, 422), cuerpo
    assert core.llamadas == []


def test_la_pantalla_pide_documento_y_ultimos_4_y_muestra_los_digitos_reales():
    html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    assert "UUID que da TARJETAS" not in html
    assert 'aria-label="Documento de identidad"' in html
    assert 'aria-label="Últimos 4 dígitos de la tarjeta"' in html
    assert "/api/identificar-tarjeta" in html
    # «•••• B080» venía del final del UUID: los dígitos salen de la respuesta.
    assert "const ultimos = id => (id || '----').slice(-4);" not in html
