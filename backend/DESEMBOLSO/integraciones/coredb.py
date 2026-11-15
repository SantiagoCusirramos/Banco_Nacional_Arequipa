"""COREDB: valida las sesiones del personal y da el token del usuario de servicio de Desembolso.

- VerificadorSesiones: `GET /coredb/auth/me` con el token de la persona. Recuerda el resultado unos
  segundos para no consultar a COREDB en cada petición; desactivar a alguien surte efecto al vencer.
- SesionServicio: `POST /coredb/auth/login` con svc-desembolso (rol SERVICIO, módulo DESEMBOLSO), como
  indica backend/COREDB/README.md: el secreto se lee del entorno o del archivo que deja desembolso-init,
  y ante un 401 se vuelve a iniciar sesión una vez.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable

import httpx

from ..config import Config
from ..core.errores import ErrorNegocio
from ..core.seguridad import Usuario, perfil_de
from .http import ClienteHttp


class VerificadorSesiones:
    MAXIMO_EN_MEMORIA = 2000

    def __init__(self, http: ClienteHttp, config: Config):
        self._http = http
        self._config = config
        self._memoria: dict[str, tuple[float, Usuario]] = {}
        self._candado = threading.Lock()

    def verificar(self, token: str) -> Usuario:
        clave = hashlib.sha256(token.encode()).hexdigest()
        ahora = time.monotonic()
        with self._candado:
            guardado = self._memoria.get(clave)
            if guardado and guardado[0] > ahora:
                return guardado[1]
        r = self._http.solicitar("GET", "/coredb/auth/me", cabeceras={"Authorization": f"Bearer {token}"})
        if r.status_code == 401:
            raise ErrorNegocio(401, "NO_AUTENTICADO", "La sesión no es válida o venció; inicie sesión otra vez")
        if r.status_code != 200:
            raise ErrorNegocio(503, "DEPENDENCIA_NO_DISPONIBLE", "COREDB no pudo validar la sesión",
                               {"modulo": "COREDB", "causa": f"HTTP_{r.status_code}"})
        datos = r.json()
        rol, permisos = perfil_de(str(datos.get("rol", "")))
        usuario = Usuario(id=str(datos["username"])[:40], nombre=str(datos["username"]), rol=rol, permisos=permisos,
                          agencia_id=self._config.agencia_id, agencia_nombre=self._config.agencia_nombre,
                          jti=clave[:16])
        with self._candado:
            if len(self._memoria) >= self.MAXIMO_EN_MEMORIA:
                self._memoria = {k: v for k, v in self._memoria.items() if v[0] > ahora}
            self._memoria[clave] = (ahora + self._config.sesion_cache_seg, usuario)
        return usuario


class SesionServicio:
    def __init__(self, http: ClienteHttp, config: Config):
        self._http = http
        self._config = config
        self._token: str | None = None
        self._vence = 0.0
        self._candado = threading.Lock()

    def _credencial(self) -> tuple[str, str]:
        if self._config.svc_secreto:
            return self._config.svc_usuario, self._config.svc_secreto
        archivo = self._config.svc_archivo
        if archivo and os.path.exists(archivo):
            # Se relee en cada inicio de sesión: desembolso-init lo renueva si el secreto dejó de servir.
            with open(archivo, encoding="utf-8") as f:
                datos = json.load(f)
            return datos.get("username") or self._config.svc_usuario, datos.get("secreto") or ""
        return self._config.svc_usuario, ""

    def token(self, renovar: bool = False) -> str:
        with self._candado:
            if self._token and not renovar and time.time() < self._vence - 60:
                return self._token
            usuario, secreto = self._credencial()
            if not secreto:
                raise ErrorNegocio(503, "CREDENCIAL_DE_SERVICIO",
                                   "Desembolso no tiene configurado su usuario de servicio de COREDB")
            r = self._http.solicitar("POST", "/coredb/auth/login", json={"username": usuario, "password": secreto})
            if r.status_code != 200:
                raise ErrorNegocio(503, "CREDENCIAL_DE_SERVICIO",
                                   f"COREDB rechazó el usuario de servicio de Desembolso (HTTP {r.status_code})")
            datos = r.json()
            self._token = datos["access_token"]
            self._vence = time.time() + float(datos.get("expires_in", 1800))
            return self._token

    def con_token(self, enviar: Callable[[str], httpx.Response]) -> httpx.Response:
        """Envía con el token vigente; ante un 401 inicia sesión otra vez y repite una sola vez."""
        r = enviar(self.token())
        if r.status_code == 401:
            r = enviar(self.token(renovar=True))
        return r
