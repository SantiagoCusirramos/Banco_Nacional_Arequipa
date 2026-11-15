"""RF-10 / CU-07: reversion (extorno). Politica pendiente (PC-05): deshabilitada por defecto."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ..config import Config
from ..core.errores import DependenciaNoDisponible, ErrorNegocio
from ..core.ids import uuid7
from ..core.seguridad import SUPERVISOR, Usuario
from ..core.tiempo import ahora_lima
from ..dominio.estados import Estado
from ..integraciones.modulos import Modulos
from ..persistencia.modelos import EventoEntrega, Orden, SolicitudReversion
from ..persistencia.repositorio import es_duplicado, transitar
from .auditoria import Auditor
from .ordenes import ServicioOrdenes, _correlacion, payload_evento, reversion_salida, utc_ahora


class ServicioReversiones:
    def __init__(self, config: Config, fabrica: sessionmaker[Session], modulos: Modulos, auditor: Auditor,
                 ordenes: ServicioOrdenes):
        self.config, self.Sesion, self.m, self.auditor, self.ordenes = config, fabrica, modulos, auditor, ordenes

    def _exigir_habilitada(self) -> None:
        if not self.config.reversion_habilitada:
            raise ErrorNegocio(409, "REVERSION_DESHABILITADA",
                               "La política de reversión aún no está aprobada por el Comité de Créditos (PC-05)")
        if not self.m.cuentas.admite_reversion:
            raise ErrorNegocio(409, "REVERSION_NO_DISPONIBLE",
                               "CUENTAS no ofrece extorno: la reversión requiere un cambio en el CORE (RFC)")

    def solicitar(self, usuario: Usuario, orden_id: str, motivo: str, origen: str, clave: str) -> dict:
        self._exigir_habilitada()
        try:
            with self.Sesion() as s, s.begin():
                previa = s.scalars(select(SolicitudReversion).where(SolicitudReversion.idempotency_key == clave)).first()
                if previa:
                    if previa.orden_id != orden_id:
                        raise ErrorNegocio(409, "IDEMPOTENCIA_CONFLICTO", "La clave ya se usó para otra orden")
                    return reversion_salida(previa)
                orden = self.ordenes._obtener(s, orden_id, bloquear=True)
                if orden.estado != Estado.CONFIRMADA:
                    raise ErrorNegocio(409, "ESTADO_INVALIDO", "Solo se revierte un desembolso CONFIRMADO",
                                       {"estado": orden.estado})
                if orden.fecha_efectiva < ahora_lima() - timedelta(hours=self.config.reversion_plazo_horas):
                    raise ErrorNegocio(422, "PLAZO_VENCIDO",
                                       f"La reversión solo procede dentro de {self.config.reversion_plazo_horas} h")
                r = SolicitudReversion(id=uuid7(), orden_id=orden_id, motivo=motivo[:255], origen=origen,
                                       solicitante_id=usuario.id, estado="SOLICITADA", idempotency_key=clave,
                                       correlation_id=_correlacion())
                s.add(r)
                s.flush()
                self.auditor.registrar(s, "REVERTIR", "SOLICITADA", actor=usuario.id, orden_id=orden_id,
                                       detalle={"motivo": motivo, "origen": origen})
                return reversion_salida(r)
        except IntegrityError as exc:
            if es_duplicado(exc, "uk_reversion_activa"):
                raise ErrorNegocio(409, "REVERSION_EXISTENTE", "La orden ya tiene una reversión en curso o confirmada") from exc
            raise

    def decidir(self, usuario: Usuario, reversion_id: str, aprobar: bool, motivo: str | None) -> dict:
        self._exigir_habilitada()
        if usuario.rol != SUPERVISOR:
            raise ErrorNegocio(403, "PERMISO_DENEGADO", "Solo un supervisor decide sobre una reversión")
        with self.Sesion() as s, s.begin():
            r = s.get(SolicitudReversion, reversion_id, with_for_update=True)
            if r is None:
                raise ErrorNegocio(404, "REVERSION_NO_ENCONTRADA", "No existe la solicitud de reversión")
            if r.estado != "SOLICITADA":
                raise ErrorNegocio(409, "ESTADO_INVALIDO", f"La solicitud está {r.estado}")
            if r.solicitante_id == usuario.id:
                raise ErrorNegocio(409, "AUTORIZADOR_INVALIDO", "Quien autoriza debe ser distinto de quien solicita (RT-08)")
            if not aprobar:
                r.estado, r.autorizador_id = "RECHAZADA", usuario.id
                r.motivo_rechazo = (motivo or "Rechazada por el supervisor")[:255]
                self.auditor.registrar(s, "REVERTIR", "RECHAZADA_POR_SUPERVISOR", actor=usuario.id, orden_id=r.orden_id)
                return reversion_salida(r)
            r.estado, r.autorizador_id, r.autorizacion_id = "EN_PROCESO", usuario.id, f"coredb:{usuario.jti}"[:60]
            self.auditor.registrar(s, "REVERTIR", "AUTORIZADA", actor=usuario.id, orden_id=r.orden_id)
            orden = self.ordenes._obtener(s, r.orden_id)
            cuerpo = {"reversion_id": r.id, "orden_id": orden.id, "operacion_original_id": orden.operacion_financiera_id,
                      "motivo": r.motivo, "autorizacion": r.autorizacion_id}
            clave = r.idempotency_key
        try:
            respuesta = self.m.cuentas.revertir(cuerpo, clave)
        except DependenciaNoDisponible:
            with self.Sesion() as s, s.begin():
                s.execute(update(SolicitudReversion).where(SolicitudReversion.id == reversion_id,
                                                           SolicitudReversion.estado == "EN_PROCESO")
                          .values(estado="POR_VERIFICAR"))
            return self._salida(reversion_id)
        with self.Sesion() as s, s.begin():
            self._aplicar(s, reversion_id, respuesta, usuario.id)
        return self._salida(reversion_id)

    def _aplicar(self, s: Session, reversion_id: str, respuesta: dict, actor: str) -> None:
        r = s.get(SolicitudReversion, reversion_id, with_for_update=True)
        if r.estado not in ("EN_PROCESO", "POR_VERIFICAR"):
            return
        if respuesta.get("estado") == "CONFIRMADO":
            r.estado, r.reversion_financiera_id = "CONFIRMADA", respuesta.get("operacion_id")
            transitar(s, r.orden_id, {Estado.CONFIRMADA}, Estado.REVERTIDA, entrega_estado="PENDIENTE")
            orden = self.ordenes._obtener(s, r.orden_id)
            evento_id = uuid7()
            payload = payload_evento(orden, evento_id, "desembolso.revertido")
            payload["reversion_financiera_id"] = r.reversion_financiera_id
            s.add(EventoEntrega(id=evento_id, orden_id=orden.id, tipo="desembolso.revertido", version_esquema="v1",
                                payload=payload, estado="PENDIENTE", intentos=0, siguiente_intento=utc_ahora()))
            self.auditor.registrar(s, "REVERTIR", "CONFIRMADA", actor=actor, orden_id=r.orden_id,
                                   detalle={"operacion": r.reversion_financiera_id})
        elif respuesta.get("estado") == "RECHAZADO":
            r.estado, r.motivo_rechazo = "RECHAZADA", str(respuesta.get("motivo") or "Cuentas rechazó la reversión")[:255]
            self.auditor.registrar(s, "REVERTIR", "RECHAZADA_POR_CUENTAS", actor=actor, orden_id=r.orden_id)

    def recuperar(self, actor: str) -> int:
        with self.Sesion() as s:
            pendientes = s.scalars(select(SolicitudReversion).where(
                SolicitudReversion.estado.in_(["EN_PROCESO", "POR_VERIFICAR"]))).all()
            datos = [(r.id, r.idempotency_key) for r in pendientes]
        resueltas = 0
        for reversion_id, clave in datos:
            try:
                respuesta = self.m.cuentas.consultar_reversion(clave)
            except ErrorNegocio:
                continue
            if respuesta.get("estado") in ("CONFIRMADO", "RECHAZADO"):
                with self.Sesion() as s, s.begin():
                    self._aplicar(s, reversion_id, respuesta, actor)
                resueltas += 1
        return resueltas

    def listar(self, estado: str | None) -> list[dict]:
        with self.Sesion() as s:
            consulta = select(SolicitudReversion, Orden.codigo_orden).join(Orden, Orden.id == SolicitudReversion.orden_id)
            if estado:
                consulta = consulta.where(SolicitudReversion.estado == estado)
            filas = s.execute(consulta.order_by(SolicitudReversion.creado_en.desc()).limit(100)).all()
            return [reversion_salida(r) | {"codigo_orden": codigo} for r, codigo in filas]

    def _salida(self, reversion_id: str) -> dict:
        with self.Sesion() as s:
            return reversion_salida(s.get(SolicitudReversion, reversion_id))
