"""COREDB en memoria con las rutas de clientes que usa CAPTACION.

Responde con la forma de CONTRATO_CLIENTES.md. test_contrato_core.py comprueba, en la
imagen de COREDB, que lo que CAPTACION envía cumple sus esquemas reales.
"""

import json

import httpx

TOKEN_SERVICIO = "tok-servicio"
PERFILES = {
    "tok-asesor": {"id_usuario": "u1", "username": "asesor.demo", "rol": "ASESOR", "modulo": None,
                   "acciones": ["CREAR_CLIENTE", "VER_CLIENTE", "MODIFICAR_CLIENTE", "VALIDAR_IDENTIDAD"]},
    "tok-auditor": {"id_usuario": "u2", "username": "auditor.demo", "rol": "AUDITOR", "modulo": None,
                    "acciones": ["VER_CLIENTE", "VER_AUDITORIA"]},
    TOKEN_SERVICIO: {"id_usuario": "u3", "username": "svc-captacion", "rol": "SERVICIO", "modulo": "CLIENTES",
                     "acciones": ["CREAR_CLIENTE", "VER_CLIENTE", "MODIFICAR_CLIENTE", "VALIDAR_IDENTIDAD"]},
}


def _error(estado: int, codigo: str) -> httpx.Response:
    return httpx.Response(estado, json={"error": {"code": codigo, "message": codigo}})


class CoreDbFalso:
    def __init__(self):
        self.clientes: dict[str, dict] = {}   # cod_cliente -> vista
        self.llamadas: list[dict] = []
        self.caido = False
        self.fallar_en: str | None = None     # ruta que responde 503 una vez
        self._n = 0

    def agregar_cliente(self, numero: str, estado: str = "ACTIVO", tipo: str = "DNI") -> str:
        self._n += 1
        cod = f"CLI{self._n:09d}"
        self.clientes[cod] = {
            "cod_cliente": cod, "tipo_documento": tipo, "numero_documento": numero, "nombres": "Existente",
            "apellido_paterno": "Cliente", "apellido_materno": "Previo", "correo": f"{numero}@prev.pe",
            "celular": f"9{self._n:08d}", "estado_cliente": estado, "permite_operar": estado == "ACTIVO",
            "version_contrato": "v1", "id_verificacion_captacion": f"ver-{self._n}",
            "estado_habilitante": "HABILITADO", "fecha_verificacion": "2026-11-02T15:04:05.000000Z",
        }
        return cod

    def rutas(self, metodo: str) -> list[str]:
        return [c["ruta"] for c in self.llamadas if c["metodo"] == metodo]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(request.content) if request.content else None
        ruta = request.url.path
        self.llamadas.append({"metodo": request.method, "ruta": ruta, "json": cuerpo,
                              "auth": request.headers.get("authorization"),
                              "correlacion": request.headers.get("x-correlation-id")})
        if self.caido:
            raise httpx.ConnectError("COREDB caído")
        if self.fallar_en and ruta.startswith(self.fallar_en):
            self.fallar_en = None
            return httpx.Response(503, json={"error": {"code": "CONFLICTO_CONCURRENCIA", "message": "x"}})
        if ruta == "/coredb/salud":
            return httpx.Response(200, json={"estado": "ok"})
        if ruta == "/coredb/auth/login":
            if cuerpo == {"username": "svc-captacion", "password": "secreto-de-prueba"}:
                return httpx.Response(200, json={"access_token": TOKEN_SERVICIO, "token_type": "bearer",
                                                 "expires_in": 1800, "usuario": PERFILES[TOKEN_SERVICIO]})
            return _error(401, "CREDENCIALES_INVALIDAS")
        token = (request.headers.get("authorization") or "").removeprefix("Bearer ")
        if token not in PERFILES:
            return _error(401, "TOKEN_INVALIDO")
        if ruta == "/coredb/auth/me":
            return httpx.Response(200, json=PERFILES[token])
        if token != TOKEN_SERVICIO:
            return _error(403, "PERMISO_DENEGADO")  # CAPTACION solo escribe con su usuario de servicio

        if ruta == "/coredb/clientes/validaciones/documento":
            cliente = next((c for c in self.clientes.values()
                            if c["tipo_documento"] == cuerpo["tipo_documento"]
                            and c["numero_documento"] == cuerpo["numero_documento"]), None)
            if cliente is None:
                return httpx.Response(201, json={"id_validacion": 1, "resultado": "RECHAZADO",
                                                 "motivo": "NO_ES_CLIENTE", "cliente": None})
            if cliente["estado_cliente"] != "ACTIVO":
                return httpx.Response(201, json={"id_validacion": 1, "resultado": "RECHAZADO",
                                                 "motivo": "CLIENTE_NO_ACTIVO", "cliente": cliente})
            return httpx.Response(201, json={"id_validacion": 1, "resultado": "APROBADO", "motivo": None,
                                             "cliente": cliente})
        if ruta == "/coredb/clientes" and request.method == "POST":
            if any(c["correo"] == cuerpo["correo"] for c in self.clientes.values()):
                return _error(409, "CORREO_DUPLICADO")
            if any(c["numero_documento"] == cuerpo["numero_documento"] for c in self.clientes.values()):
                return _error(409, "CLIENTE_DUPLICADO")
            self._n += 1
            cod = f"CLI{self._n:09d}"
            self.clientes[cod] = {
                "cod_cliente": cod, **{k: cuerpo[k] for k in (
                    "tipo_documento", "numero_documento", "nombres", "apellido_paterno", "apellido_materno",
                    "correo", "celular", "version_contrato", "estado_habilitante")},
                "estado_cliente": "ACTIVO" if cuerpo["estado_habilitante"] == "HABILITADO" else "OBSERVADO",
                "permite_operar": True, "id_verificacion_captacion": f"ver-{self._n}",
                "fecha_verificacion": "2026-11-15T15:04:05.000000Z",
            }
            c = self.clientes[cod]
            return httpx.Response(201, json={"cod_cliente": cod, "estado_cliente": c["estado_cliente"],
                                             "estado_habilitante": c["estado_habilitante"],
                                             "id_verificacion_captacion": c["id_verificacion_captacion"]})
        partes = ruta.split("/")
        if len(partes) >= 4 and partes[2] == "clientes":
            cod = partes[3]
            if cod not in self.clientes:
                return _error(404, "CLIENTE_NO_ENCONTRADO")
            if len(partes) == 5 and partes[4] == "validaciones":
                return httpx.Response(201, json={"id_validacion": 2})
            if len(partes) == 4 and request.method == "GET":
                return httpx.Response(200, json=self.clientes[cod])
        return _error(404, "RUTA_DESCONOCIDA")
