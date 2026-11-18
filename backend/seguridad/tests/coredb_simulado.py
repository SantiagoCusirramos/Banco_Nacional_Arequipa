"""COREDB en memoria para las pruebas unitarias: lo justo de sus contratos de Seguridad
(bd-v1.13). Las pruebas de integración usan el COREDB real (scripts/pruebas_integracion.sh)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx

SECRETO_SERVICIO = "s" * 40
ACCIONES = {
    "ADMINISTRADOR": {"REGISTRAR_MOVIMIENTO", "VER_AUDITORIA", "GESTIONAR_INCIDENTES", "BLOQUEAR_TARJETA"},
    "OPERADOR": {"REGISTRAR_MOVIMIENTO", "GESTIONAR_INCIDENTES", "BLOQUEAR_TARJETA"},
    "AUDITOR": {"VER_AUDITORIA"},
    "ASESOR": {"VER_CLIENTE"},
    "SERVICIO": {"OPERAR_SEGURIDAD", "VER_AUDITORIA"},
}


def _hora(segundos_atras: float = 3600) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=segundos_atras)).isoformat().replace("+00:00", "Z")


class CoreDbSimulado:
    def __init__(self):
        self.usuarios = {"svc-seguridad": (SECRETO_SERVICIO, "SERVICIO"), "ana": ("clave", "OPERADOR"),
                         "aud": ("clave", "AUDITOR"), "ase": ("clave", "ASESOR"), "adm": ("clave", "ADMINISTRADOR")}
        self.peticiones: list[httpx.Request] = []
        self.eventos: list[dict] = []
        self.sellos: list[dict] = []
        self.desafios: dict[str, dict] = {}
        self.decisiones: dict[str, dict] = {}
        self.incidentes: dict[str, dict] = {}
        self.expirar_servicio = False
        self.caido = False
        self.logins_servicio = 0

    # ------------------------------------------------------------------ utilidades
    def evento(self, accion: str, segundos_atras: float = 3600, **detalle) -> dict:
        evento = {"id_evento": len(self.eventos) + 1, "modulo": "CORE", "entidad": "x", "id_entidad": "1",
                  "accion": accion, "actor": "pruebas", "correlation_id": None, "detalle": detalle or None,
                  "fecha_hora": _hora(segundos_atras)}
        self.eventos.append(evento)
        return evento

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._atender)

    @staticmethod
    def _json(estado: int, cuerpo) -> httpx.Response:
        return httpx.Response(estado, json=cuerpo)

    def _error(self, estado: int, codigo: str) -> httpx.Response:
        return self._json(estado, {"error": {"code": codigo, "message": codigo}})

    def _quien(self, valor: str | None) -> tuple[str, str] | None:
        if not valor or not valor.startswith("tok-"):
            return None
        usuario = valor.removeprefix("tok-")
        return (usuario, self.usuarios[usuario][1]) if usuario in self.usuarios else None

    def _bearer(self, pedido: httpx.Request) -> tuple[str, str] | None:
        return self._quien(pedido.headers.get("Authorization", "").removeprefix("Bearer "))

    # ------------------------------------------------------------------ rutas
    def _atender(self, pedido: httpx.Request) -> httpx.Response:
        if self.caido:
            raise httpx.ConnectError("COREDB caído", request=pedido)
        self.peticiones.append(pedido)
        ruta, metodo = pedido.url.path, pedido.method
        cuerpo = json.loads(pedido.content) if pedido.content else {}
        if ruta == "/coredb/salud":
            return self._json(200, {"estado": "ok"})
        if ruta == "/coredb/auth/login":
            guardado = self.usuarios.get(cuerpo.get("username"))
            if not guardado or guardado[0] != cuerpo.get("password"):
                return self._error(401, "CREDENCIALES_INVALIDAS")
            if cuerpo["username"] == "svc-seguridad":
                self.logins_servicio += 1
            return self._json(200, {"access_token": f"tok-{cuerpo['username']}", "token_type": "bearer",
                                    "expires_in": 1800})
        quien = self._bearer(pedido)
        if quien is None:
            return self._error(401, "TOKEN_REQUERIDO")
        if ruta == "/coredb/auth/me":
            return self._json(200, {"username": quien[0], "rol": quien[1], "acciones": sorted(ACCIONES[quien[1]])})
        if ruta.startswith("/coredb/auditoria"):
            return self._auditoria(pedido, ruta, metodo, cuerpo, quien)
        # Las demás: solo el servicio de Seguridad, por una persona.
        if quien[1] != "SERVICIO":
            return self._error(403, "PERMISO_DENEGADO")
        if self.expirar_servicio:
            self.expirar_servicio = False
            return self._error(401, "TOKEN_EXPIRADO")
        persona = self._quien(pedido.headers.get("X-Persona-Token"))
        if persona is None:
            return self._error(401, "PERSONA_TOKEN_REQUERIDO")
        if ruta == "/coredb/seguridad/evaluaciones":
            return self._evaluar(cuerpo, persona[0])
        if ruta == "/coredb/seguridad/desafios":
            self.desafios[cuerpo["id_desafio"]] = {**cuerpo, "actor": persona[0], "fallos": 0, "usado": False}
            return self._json(201, {"id_desafio": cuerpo["id_desafio"], "vence_en": _hora(-120)})
        if ruta == "/coredb/seguridad/incidentes":
            if metodo == "GET":
                return self._json(200, list(self.incidentes.values()))
            incidente = {"id_incidente": str(uuid.uuid4()), **cuerpo, "estado": "ABIERTO", "resolucion": None,
                         "abierto_por": persona[0]}
            self.incidentes[incidente["id_incidente"]] = incidente
            return self._json(201, incidente)
        if ruta.startswith("/coredb/seguridad/incidentes/") and ruta.endswith("/estado"):
            incidente = self.incidentes[ruta.split("/")[4]]
            incidente.update(estado=cuerpo["estado"], resolucion=cuerpo.get("resolucion", incidente["resolucion"]))
            return self._json(200, incidente)
        if ruta.endswith("/desbloqueo"):
            return self._json(200, {"id_tarjeta": ruta.split("/")[3], "estado_tarjeta": "ACTIVA"})
        return self._error(404, "RUTA")

    def _auditoria(self, pedido, ruta, metodo, cuerpo, quien) -> httpx.Response:
        if ruta == "/coredb/auditoria/sellos" and metodo == "POST":
            desde = self.sellos[-1]["hasta_evento"] if self.sellos else 0
            n = sum(1 for e in self.eventos if desde < e["id_evento"] <= cuerpo["hasta_evento"])
            if cuerpo["hasta_evento"] <= desde or n != cuerpo["eventos"]:
                return self._error(409, "BNA-SELLO")
            sello = {"id_sello": len(self.sellos) + 1, "desde_evento": desde, **cuerpo, "actor": quien[0],
                     "fecha_hora": _hora(0)}
            self.sellos.append(sello)
            return self._json(201, sello)
        parametros = pedido.url.params
        if ruta == "/coredb/auditoria/sellos":
            despues = int(parametros.get("despues_de_id", 0))
            return self._json(200, [s for s in self.sellos if s["id_sello"] > despues])
        limite = int(parametros.get("limite", 50))
        if "despues_de_id" in parametros:
            despues = int(parametros["despues_de_id"])
            return self._json(200, [e for e in self.eventos if e["id_evento"] > despues][:limite])
        return self._json(200, list(reversed(self.eventos))[:limite])

    def _evaluar(self, cuerpo: dict, actor: str) -> httpx.Response:
        monto, tope = float(cuerpo["monto"]), 1500.0
        guardada = self.decisiones.get(cuerpo["uuid_operacion"])
        if guardada:
            return self._json(200, {**guardada, "repetida": True})
        base = {"uuid_operacion": cuerpo["uuid_operacion"], "tope": "1500.00", "consumido": "0.00",
                "motivo": None, "repetida": False}
        if monto > tope:
            decision = {**base, "decision": "RECHAZADA", "motivo": "TOPE"}
        elif monto > tope * 0.8:
            if "id_desafio" not in cuerpo:
                return self._json(200, {**base, "decision": "DESAFIO_REQUERIDO"})
            desafio = self.desafios.get(cuerpo["id_desafio"])
            if (not desafio or desafio["usado"] or desafio["fallos"] >= 3
                    or desafio["hmac_codigo"] != cuerpo["hmac_codigo"]):
                if desafio:
                    desafio["fallos"] += 1
                return self._json(200, {**base, "decision": "DESAFIO_RECHAZADO"})
            desafio["usado"] = True
            decision = {**base, "decision": "AUTORIZADA"}
        else:
            decision = {**base, "decision": "AUTORIZADA"}
        self.decisiones[cuerpo["uuid_operacion"]] = decision
        return self._json(200, decision)
