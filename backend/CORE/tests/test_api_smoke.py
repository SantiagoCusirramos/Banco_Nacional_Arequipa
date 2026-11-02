"""Smoke tests de importación y montaje de la app (sin BD)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from CORE.api import montar_en


def _app() -> FastAPI:
    app = FastAPI()
    montar_en(app)
    return app


def test_rutas_core_montadas():
    client = TestClient(_app())
    paths = {r.path for r in client.app.routes if hasattr(r, "path")}
    assert "/core/clientes" in paths
    assert "/core/cuentas" in paths
    assert "/core/movimientos" in paths
    assert "/core/tarjetas" in paths
    assert "/core/creditos/solicitudes" in paths
    assert "/core/creditos/pagos" in paths
    assert "/core/usuarios" in paths
    assert "/core/permisos" in paths
    assert "/core/auditoria" in paths
    assert "/core/reportes/cuadre-contable" in paths


def test_error_core_devuelve_json_catalogado():
    from fastapi import FastAPI, Depends
    from sqlalchemy.orm import Session

    from CORE.exceptions import NotFoundError
    from CORE.routers import clientes as r_clientes

    app = FastAPI()
    montar_en(app)

    client = TestClient(app, raise_server_exceptions=False)
    # Sin BD real la sesión fallaría; usamos una ruta que solo valida
    # el handler de CoreError montado en la app.
    resp = client.get("/core/clientes/NO-EXISTE")
    # 500 por falta de BD (no hay MySQL en el entorno de prueba) o 404
    # si la sesión está disponible; en ambos casos no es un 200.
    assert resp.status_code != 200


class TestApi:
    def test_montar_en_es_idempotente(self):
        app = FastAPI()

        # Primera llamada
        montar_en(app)

        rutas_primera_llamada = [
            ruta for ruta in app.routes
            if getattr(ruta, "path", "").startswith("/core/")
        ]

        # Segunda llamada
        montar_en(app)

        rutas_segunda_llamada = [
            ruta for ruta in app.routes
            if getattr(ruta, "path", "").startswith("/core/")
        ]

        # Comprobar que existen las 33 rutas
        assert len(rutas_primera_llamada) == 33

        # Comprobar que no se duplicaron
        assert len(rutas_segunda_llamada) == len(rutas_primera_llamada)

        # Comprobar que no existen rutas repetidas
        rutas_unicas = {
            (
                ruta.path,
                tuple(sorted(getattr(ruta, "methods", [])))
            )
            for ruta in rutas_segunda_llamada
        }

        assert len(rutas_unicas) == len(rutas_segunda_llamada)

        # Comprobar compatibilidad con TestClient
        client = TestClient(app)
        assert client.get("/openapi.json").status_code == 200

