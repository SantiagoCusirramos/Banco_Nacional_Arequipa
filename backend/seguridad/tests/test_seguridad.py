"""Seguridad sin base propia, contra un COREDB en memoria."""
import ast
import hashlib
import hmac
import uuid
from pathlib import Path

import pytest

from seguridad import auditoria
from seguridad.api import hmac_codigo
from seguridad.config import Config
from seguridad.tests.conftest import CLAVE, como

MODULO = Path(__file__).resolve().parents[1]


def _operacion(monto, **extra):
    return {"uuid_operacion": str(uuid.uuid4()), "num_cuenta": "CTA-1", "canal": "ATM", "monto": monto, **extra}


# --------------------------------------------------------------------- sin almacenamiento propio
def test_el_modulo_no_tiene_almacenamiento_propio():
    prohibidos = {"sqlite3", "shelve", "dbm", "sqlalchemy", "pymysql"}
    for archivo in MODULO.rglob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            nombres = ([a.name for a in nodo.names] if isinstance(nodo, ast.Import)
                       else [nodo.module or ""] if isinstance(nodo, ast.ImportFrom) else [])
            for nombre in nombres:
                assert nombre.split(".")[0] not in prohibidos, f"{archivo.name} importa {nombre}"
            if isinstance(nodo, ast.Call) and getattr(nodo.func, "id", None) == "open":
                pytest.fail(f"{archivo.name} abre archivos")


def test_la_configuracion_exige_clave_y_secreto():
    with pytest.raises(RuntimeError, match="SEGURIDAD_SECRET_KEY"):
        Config(clave="corta", servicio_secreto="s" * 40).validar()
    with pytest.raises(RuntimeError, match="SEGURIDAD_SECRET_KEY"):
        Config(clave="change_me" + "x" * 40, servicio_secreto="s" * 40).validar()
    with pytest.raises(RuntimeError, match="SEGURIDAD_COREDB_SECRETO") as exc:
        Config(clave="k" * 40, servicio_secreto="corto").validar()
    assert "corto" not in str(exc.value)


# --------------------------------------------------------------------- quién llama
def test_sin_correlacion_400(api):
    respuesta = api.get("/seguridad/estado", headers={"X-Correlation-ID": ""})
    assert respuesta.status_code == 400


def test_estado_publico(api):
    cuerpo = api.get("/seguridad/estado").json()
    assert cuerpo["base_propia"] is False and cuerpo["coredb_disponible"] is True


def test_login_es_el_de_coredb(api, coredb):
    respuesta = api.post("/seguridad/auth/login", json={"username": "ana", "password": "clave"})
    assert respuesta.status_code == 200 and respuesta.json()["access_token"] == "tok-ana"
    malo = api.post("/seguridad/auth/login", json={"username": "ana", "password": "otra"})
    assert malo.status_code == 401 and malo.json()["error"]["code"] == "CREDENCIALES_INVALIDAS"


def test_sin_token_401_y_sin_permiso_403(api):
    assert api.post("/seguridad/operaciones/evaluar", json=_operacion("10.00")).status_code == 401
    assert api.post("/seguridad/operaciones/evaluar", json=_operacion("10.00"),
                    headers=como("aud")).status_code == 403
    # El usuario de servicio no entra por las rutas del personal.
    assert api.get("/seguridad/auditoria", headers=como("svc-seguridad")).status_code == 403
    assert api.get("/seguridad/auth/me", headers=como("nadie")).status_code == 401


# --------------------------------------------------------------------- evaluación
def test_evaluacion_va_con_el_servicio_y_la_persona(api, coredb):
    respuesta = api.post("/seguridad/operaciones/evaluar", json=_operacion("100.00"), headers=como("ana"))
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["decision"] == "AUTORIZADA" and respuesta.json()["efecto_financiero"] is False
    pedido = next(p for p in coredb.peticiones if p.url.path == "/coredb/seguridad/evaluaciones")
    assert pedido.headers["Authorization"] == "Bearer tok-svc-seguridad"
    assert pedido.headers["X-Persona-Token"] == "tok-ana"
    assert pedido.headers["X-Correlation-ID"] == "pytest-seguridad"


def test_desafio_completo_sin_que_coredb_vea_el_codigo(api, coredb):
    operacion = _operacion("1300.00")
    primera = api.post("/seguridad/operaciones/evaluar", json=operacion, headers=como("ana")).json()
    assert primera["decision"] == "DESAFIO_REQUERIDO" and primera["vence_en_seg"] == 120
    codigo, id_desafio = primera["codigo_demo"], primera["id_desafio"]
    guardado = coredb.desafios[id_desafio]
    assert guardado["hmac_codigo"] == hmac_codigo(CLAVE, uuid.UUID(id_desafio), codigo)
    assert all(codigo not in p.content.decode() for p in coredb.peticiones if p.content)

    otro = "000000" if codigo != "000000" else "111111"
    mal = api.post("/seguridad/operaciones/evaluar", headers=como("ana"),
                   json={**operacion, "id_desafio": id_desafio, "codigo": otro}).json()
    assert mal["decision"] == "DESAFIO_RECHAZADO"
    bien = api.post("/seguridad/operaciones/evaluar", headers=como("ana"),
                    json={**operacion, "id_desafio": id_desafio, "codigo": codigo}).json()
    assert bien["decision"] == "AUTORIZADA"


def test_el_hmac_del_codigo_depende_de_la_clave():
    id_desafio = uuid.uuid4()
    esperado = hmac.new(CLAVE.encode(), f"desafio-v1:{id_desafio}:123456".encode(), hashlib.sha256).hexdigest()
    assert hmac_codigo(CLAVE, id_desafio, "123456") == esperado
    assert hmac_codigo("otra-clave-" + "x" * 30, id_desafio, "123456") != esperado


def test_desafio_y_codigo_van_juntos(api):
    respuesta = api.post("/seguridad/operaciones/evaluar", headers=como("ana"),
                         json=_operacion("10.00", id_desafio=str(uuid.uuid4())))
    assert respuesta.status_code == 422


def test_un_token_de_servicio_vencido_se_renueva_una_vez(api, coredb):
    api.post("/seguridad/operaciones/evaluar", json=_operacion("10.00"), headers=como("ana"))
    coredb.expirar_servicio = True
    respuesta = api.post("/seguridad/operaciones/evaluar", json=_operacion("10.00"), headers=como("ana"))
    assert respuesta.status_code == 200
    assert coredb.logins_servicio == 2


def test_coredb_caido_503(api, coredb):
    api.get("/seguridad/estado")
    coredb.caido = True
    respuesta = api.post("/seguridad/operaciones/evaluar", json=_operacion("10.00"), headers=como("ana"))
    assert respuesta.status_code == 503
    assert respuesta.json()["error"]["code"] == "COREDB_NO_DISPONIBLE"


# --------------------------------------------------------------------- bitácora
def test_sello_encadenado_y_verificacion(api, coredb):
    for i in range(3):
        coredb.evento(f"A{i}", monto=i)
    primero = api.post("/seguridad/auditoria/sellos", headers=como("aud")).json()
    assert primero["sellado"] is True
    assert primero["sello"]["hmac"] == auditoria.encadenar(CLAVE, auditoria.INICIO, coredb.eventos)
    coredb.evento("B0")
    segundo = api.post("/seguridad/auditoria/sellos", headers=como("aud")).json()["sello"]
    assert segundo["desde_evento"] == 3
    assert segundo["hmac"] == auditoria.encadenar(CLAVE, primero["sello"]["hmac"], coredb.eventos[3:])
    verificacion = api.get("/seguridad/auditoria/verificar", headers=como("aud")).json()
    assert verificacion["valida"] is True and verificacion["sellos_verificados"] == 2
    assert verificacion["eventos_sin_sellar"] == 0


def test_no_sella_eventos_recientes(api, coredb):
    coredb.evento("VIEJO")
    coredb.evento("NUEVO", segundos_atras=5)
    sello = api.post("/seguridad/auditoria/sellos", headers=como("aud")).json()["sello"]
    assert sello["hasta_evento"] == 1
    assert api.post("/seguridad/auditoria/sellos", headers=como("aud")).json()["sellado"] is False
    assert api.get("/seguridad/auditoria/verificar", headers=como("aud")).json()["eventos_sin_sellar"] == 1


@pytest.mark.parametrize("alterar, motivo", [
    (lambda c: c.eventos[1].update(actor="otro"), "un evento o el sello cambió"),
    (lambda c: c.eventos[1]["detalle"].update(monto=999), "un evento o el sello cambió"),
    (lambda c: c.eventos.pop(1), "faltan o sobran eventos en el tramo"),
    (lambda c: c.sellos[0].update(hmac="0" * 64), "un evento o el sello cambió"),
])
def test_la_verificacion_detecta_alteraciones(api, coredb, alterar, motivo):
    for i in range(3):
        coredb.evento(f"A{i}", monto=i)
    api.post("/seguridad/auditoria/sellos", headers=como("aud"))
    alterar(coredb)
    verificacion = api.get("/seguridad/auditoria/verificar", headers=como("aud")).json()
    assert verificacion["valida"] is False and verificacion["motivo"] == motivo


def test_vaciar_la_bitacora_se_detecta(api, coredb):
    coredb.evento("A")
    api.post("/seguridad/auditoria/sellos", headers=como("aud"))
    coredb.eventos.clear()
    assert api.get("/seguridad/auditoria/verificar", headers=como("aud")).json()["valida"] is False


def test_sellar_y_verificar_exigen_ver_auditoria(api):
    assert api.post("/seguridad/auditoria/sellos", headers=como("ana")).status_code == 403
    assert api.get("/seguridad/auditoria/verificar", headers=como("ana")).status_code == 403


def test_la_bitacora_se_lee_con_el_token_de_la_persona(api, coredb):
    coredb.evento("A")
    assert api.get("/seguridad/auditoria", headers=como("aud")).json()[0]["accion"] == "A"
    pedido = [p for p in coredb.peticiones if p.url.path == "/coredb/auditoria"][-1]
    assert pedido.headers["Authorization"] == "Bearer tok-aud" and "X-Persona-Token" not in pedido.headers


def test_sellado_periodico(ctx, coredb):
    import threading
    coredb.evento("A")
    from dataclasses import replace
    # Config es inmutable: otra con sellado cada 0.05 s.
    ctx.config = replace(ctx.config, sellado_seg=0.05)
    hilo = threading.Thread(target=ctx.sellar_periodicamente, daemon=True)
    hilo.start()
    for _ in range(100):
        if coredb.sellos:
            break
        threading.Event().wait(0.02)
    ctx.cerrar()
    hilo.join(timeout=2)
    assert coredb.sellos and coredb.sellos[0]["hasta_evento"] == 1


# --------------------------------------------------------------------- incidentes y tarjetas
def test_incidentes_con_sla(api, coredb):
    creado = api.post("/seguridad/incidentes", headers=como("ana"),
                      json={"prioridad": "P1", "titulo": "Intentos de acceso repetidos"})
    assert creado.status_code == 201
    incidente = creado.json()
    assert (incidente["estado"], incidente["sla_atencion_min"], incidente["sla_resolucion_min"]) == ("ABIERTO", 15, 120)
    avanzado = api.patch(f"/seguridad/incidentes/{incidente['id_incidente']}", headers=como("ana"),
                         json={"estado": "EN_PROGRESO"})
    assert avanzado.json()["estado"] == "EN_PROGRESO"
    pedido = coredb.peticiones[-1]
    assert pedido.method == "POST" and pedido.url.path.endswith("/estado")
    assert api.get("/seguridad/incidentes", headers=como("aud")).status_code == 200
    assert api.post("/seguridad/incidentes", headers=como("aud"),
                    json={"prioridad": "P1", "titulo": "Sin permiso para abrir"}).status_code == 403


def test_desbloqueo_por_una_persona_que_puede_bloquear(api, coredb):
    tarjeta = str(uuid.uuid4())
    respuesta = api.post(f"/seguridad/tarjetas/{tarjeta}/desbloqueo", headers=como("ana"),
                         json={"motivo": "Identidad confirmada"})
    assert respuesta.status_code == 200 and respuesta.json()["estado_tarjeta"] == "ACTIVA"
    assert coredb.peticiones[-1].headers["X-Persona-Token"] == "tok-ana"
    assert api.post(f"/seguridad/tarjetas/{tarjeta}/desbloqueo", headers=como("ase"),
                    json={"motivo": "Sin permiso"}).status_code == 403
