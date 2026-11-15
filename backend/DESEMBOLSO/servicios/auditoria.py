"""Bitacora de solo insercion (des_auditoria) y eventos criticos hacia Seguridad (CR-INT-10)."""
from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from ..core.correlacion import correlation_id
from ..core.seguridad import Usuario
from ..integraciones.modulos import Seguridad
from ..persistencia.modelos import Auditoria

CRITICAS = {"CONFIRMAR", "REVERTIR", "ACCESO_DENEGADO", "RECUPERAR"}


class Auditor:
    def __init__(self, fabrica: sessionmaker[Session], seguridad: Seguridad):
        self._fabrica = fabrica
        self._seguridad = seguridad

    def registrar(self, sesion: Session, accion: str, resultado: str, *, actor: str, orden_id: str | None = None,
                  detalle: dict | None = None, ip: str | None = None) -> None:
        sesion.add(Auditoria(orden_id=orden_id, actor_id=actor[:40], accion=accion[:60], resultado=resultado[:40],
                             correlation_id=correlation_id(), ip=ip, detalle=detalle))
        if accion in CRITICAS:
            self._seguridad.publicar_evento({"modulo": "DESEMBOLSO", "accion": accion, "resultado": resultado,
                                             "actor": actor, "orden_id": orden_id, "correlation_id": correlation_id()})

    def denegado(self, usuario: Usuario, ruta: str, ip: str | None) -> None:
        """Registra un acceso denegado en su propia transaccion (la peticion termina en 403)."""
        with self._fabrica() as sesion, sesion.begin():
            self.registrar(sesion, "ACCESO_DENEGADO", "403", actor=usuario.id, ip=ip,
                           detalle={"ruta": ruta, "rol": usuario.rol})
