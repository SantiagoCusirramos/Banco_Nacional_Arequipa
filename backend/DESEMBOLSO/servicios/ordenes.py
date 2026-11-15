"""Casos de uso de la orden de desembolso (CU-01 a CU-04)."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ..config import Config
from ..core.dinero import formatear
from ..core.enmascarar import enmascarar
from ..core.errores import DependenciaNoDisponible, ErrorNegocio
from ..core.ids import uuid7
from ..core.seguridad import AUDITOR, EJECUTAR, LEER, SUPERVISOR, Usuario
from ..core.tiempo import LIMA, ahora_lima, desde_iso, hoy_lima
from ..dominio.estados import (CON_RESULTADO_FINANCIERO, EDITABLES, INCIERTOS, REQUERIDAS_PARA_VALIDAR, Estado,
                               TipoValidacion)
from ..integraciones.modulos import Aprobacion, Modulos
from ..persistencia.modelos import Auditoria, EventoEntrega, Orden, SolicitudReversion, Validacion
from ..persistencia.repositorio import (credito_en_ejecucion, es_duplicado, fecha_lima, orden_por_clave,
                                        siguiente_codigo, transitar)
from .auditoria import Auditor

log = logging.getLogger("desembolso.ordenes")

APROBADA, RECHAZADA = "APROBADA", "RECHAZADA"
# Sin módulo Clientes en el producto, la identidad la verifica el operador con el documento original.
METODOS_IDENTIDAD = ("VERIFICACION_PRESENCIAL",)
TIPO_COBRANZA = "desembolso.confirmado"       # obligación para Cobranza (CR-INT-06)
TIPO_EVALUACION = "aprobacion.desembolsada"   # aviso a Evaluación (CR-INT-04)


def utc_ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def huella(contenido: dict) -> str:
    return hashlib.sha256(json.dumps(contenido, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ServicioOrdenes:
    def __init__(self, config: Config, fabrica: sessionmaker[Session], modulos: Modulos, auditor: Auditor):
        self.config = config
        self.Sesion = fabrica
        self.m = modulos
        self.auditor = auditor
        self._cache_aprobaciones: dict[str, tuple[float, Aprobacion]] = {}

    # ------------------------------------------------------------------ utilidades
    @staticmethod
    def _obtener(s: Session, orden_id: str, bloquear: bool = False) -> Orden:
        consulta = select(Orden).where(Orden.id == orden_id).execution_options(populate_existing=True)
        if bloquear:
            consulta = consulta.with_for_update()
        orden = s.scalars(consulta).first()
        if orden is None:
            raise ErrorNegocio(404, "ORDEN_NO_ENCONTRADA", "No existe la orden de desembolso")
        return orden

    @staticmethod
    def _exigir_editable(orden: Orden) -> None:
        if orden.estado not in EDITABLES:
            raise ErrorNegocio(409, "ESTADO_INVALIDO", f"La orden está {orden.estado} y ya no admite cambios",
                               {"estado": orden.estado})

    @staticmethod
    def _exigir_version(orden: Orden, version: int) -> None:
        if orden.version != version:
            raise ErrorNegocio(409, "VERSION_CONFLICTO", "La orden cambió desde que se mostró; actualice la pantalla",
                               {"version_actual": orden.version})

    @staticmethod
    def _ultimas_validaciones(s: Session, orden_id: str) -> dict[str, Validacion]:
        ultimas: dict[str, Validacion] = {}
        for v in s.scalars(select(Validacion).where(Validacion.orden_id == orden_id)
                           .order_by(Validacion.creado_en, Validacion.id)):
            ultimas[v.tipo] = v
        return ultimas

    @staticmethod
    def _vigente(v: Validacion | None) -> bool:
        return v is not None and v.resultado == APROBADA and (v.vence_en is None or v.vence_en >= ahora_lima())

    def _guardar_cambios(self, s: Session, orden: Orden, **cambios) -> None:
        """Aplica cambios y recalcula PREPARADA/VALIDADA segun las validaciones vigentes."""
        cuenta = cambios.get("cuenta_id", orden.cuenta_id)
        ultimas = self._ultimas_validaciones(s, orden.id)
        completo = bool(cuenta) and all(self._vigente(ultimas.get(t)) for t in REQUERIDAS_PARA_VALIDAR)
        estado = orden.estado
        if estado == Estado.PREPARADA and completo:
            estado = Estado.VALIDADA
        elif estado == Estado.VALIDADA and not completo:
            estado = Estado.PREPARADA
        s.execute(update(Orden).where(Orden.id == orden.id)
                  .values(estado=estado, version=Orden.version + 1, **cambios)
                  .execution_options(synchronize_session=False))

    def aprobacion(self, aprobacion_id: str, cache_seg: float = 60) -> Aprobacion | None:
        """Datos de la aprobacion para mostrar (cache corto); nunca se usa para ejecutar."""
        en_cache = self._cache_aprobaciones.get(aprobacion_id)
        if en_cache and time.monotonic() - en_cache[0] < cache_seg:
            return en_cache[1]
        try:
            a = self.m.evaluacion.obtener(aprobacion_id)
        except ErrorNegocio:
            return en_cache[1] if en_cache else None
        if a:
            self._cache_aprobaciones[aprobacion_id] = (time.monotonic(), a)
        return a

    # ------------------------------------------------------------------ CU-01
    def creditos_habilitados(self, usuario: Usuario, documento: str | None, credito_id: str | None) -> list[dict]:
        if not documento and not credito_id:
            raise ErrorNegocio(422, "VALIDACION_ENTRADA", "Indique el documento del cliente o el código del crédito")
        aprobaciones = self.m.evaluacion.buscar(documento=documento, credito_id=credito_id)
        resultado = []
        with self.Sesion() as s, s.begin():
            for a in aprobaciones:
                self._cache_aprobaciones[a.aprobacion_id] = (time.monotonic(), a)
                en_ejecucion = credito_en_ejecucion(s, a.credito_id)
                borrador = s.scalars(select(Orden).where(Orden.credito_id == a.credito_id,
                                                         Orden.estado.in_(list(EDITABLES)))
                                     .order_by(Orden.creado_en.desc())).first()
                existente = en_ejecucion or borrador
                motivo = None
                if a.estado != "VIGENTE":
                    motivo = f"La aprobación está {a.estado}"
                elif not a.habilitada:
                    motivo = "La aprobación perdió vigencia"
                elif en_ejecucion:
                    motivo = f"El crédito ya tiene un desembolso {en_ejecucion.estado}"
                resultado.append({
                    **_aprobacion_salida(a),
                    "habilitada": a.habilitada and not en_ejecucion,
                    "motivo": motivo,
                    "orden_existente": {"id": existente.id, "codigo_orden": existente.codigo_orden,
                                        "estado": existente.estado} if existente else None,
                })
            self.auditor.registrar(s, "CONSULTAR", f"{len(resultado)}_RESULTADOS", actor=usuario.id,
                                   detalle={"documento": enmascarar(documento), "credito_id": credito_id})
        return resultado

    # ------------------------------------------------------------------ RF-01 / RF-04
    def preparar(self, usuario: Usuario, aprobacion_id: str, clave: str) -> tuple[str, bool]:
        firma = huella({"aprobacion_id": aprobacion_id})
        with self.Sesion() as s:
            existente = orden_por_clave(s, clave)
            if existente:
                return self._repeticion(existente, firma)
        a = self.m.evaluacion.obtener(aprobacion_id)
        if a is None:
            raise ErrorNegocio(404, "APROBACION_NO_ENCONTRADA", "Evaluación no registra esa aprobación")
        if not a.habilitada:
            raise ErrorNegocio(422, "APROBACION_NO_HABILITADA",
                               f"La aprobación no está habilitada para desembolso ({a.estado})",
                               {"estado": a.estado, "vigente_hasta": _iso(a.vigente_hasta)})
        problema = self._problema_calendario(a.calendario)
        if problema:
            raise ErrorNegocio(422, "CALENDARIO_NO_UTILIZABLE", problema)
        try:
            with self.Sesion() as s, s.begin():
                previa = credito_en_ejecucion(s, a.credito_id)
                if previa:
                    raise ErrorNegocio(409, "CREDITO_CON_DESEMBOLSO",
                                       f"El crédito ya tiene la orden {previa.codigo_orden} en estado {previa.estado}",
                                       {"orden_id": previa.id, "estado": previa.estado})
                orden = Orden(
                    id=uuid7(), codigo_orden=siguiente_codigo(s, ahora_lima().year), aprobacion_id=a.aprobacion_id,
                    aprobacion_version=a.version, credito_id=a.credito_id, cliente_id=a.cliente_id,
                    importe=a.importe, moneda=a.moneda, estado=Estado.PREPARADA, entrega_estado="PENDIENTE",
                    idempotency_key=clave, request_hash=firma, canal="AGENCIA", agencia_id=usuario.agencia_id,
                    usuario_preparacion=usuario.id, correlation_id=_correlacion(), version=0,
                    solicitud_id=a.solicitud_id, calendario_pagos=list(a.calendario))
                s.add(orden)
                s.flush()
                s.add(Validacion(id=uuid7(), orden_id=orden.id, tipo=TipoValidacion.APROBACION, fase="PREPARACION",
                                 proveedor="EVALUACION", referencia_evidencia=f"{a.aprobacion_id}@v{a.version}",
                                 resultado=APROBADA, detalle=f"Aprobación {a.estado} · {a.producto}",
                                 vence_en=a.vigente_hasta))
                self.auditor.registrar(s, "PREPARAR", "OK", actor=usuario.id, orden_id=orden.id,
                                       detalle={"codigo": orden.codigo_orden, "credito_id": a.credito_id,
                                                "importe": formatear(a.importe), "moneda": a.moneda})
                return orden.id, False
        except IntegrityError as exc:
            if es_duplicado(exc, "uk_orden_idempotency"):
                with self.Sesion() as s:
                    return self._repeticion(orden_por_clave(s, clave), firma)
            raise

    @staticmethod
    def _repeticion(orden: Orden, firma: str) -> tuple[str, bool]:
        if orden.request_hash != firma:
            raise ErrorNegocio(409, "IDEMPOTENCIA_CONFLICTO", "La clave de idempotencia ya se usó con otro contenido",
                               {"orden_id": orden.id})
        return orden.id, True

    def _problema_calendario(self, calendario) -> str | None:
        """El calendario lo arma Solicitud (RN-SOL-006) y pasa sin cambios a Cobranza; aquí solo se verifica
        que exista y que su primera cuota no venza antes del desembolso (Cobranza la marcaría en mora)."""
        if not calendario:
            return "La aprobación no trae el calendario de pagos de Solicitud"
        if self.config.validar_calendario:
            primera = min(str(c.get("fechaVencimiento")) for c in calendario)
            if primera <= hoy_lima().isoformat():
                return (f"La primera cuota del calendario de Solicitud vence el {primera}, antes del desembolso; "
                        "Solicitud debe recalcularlo")
        return None

    # ------------------------------------------------------------------ RF-02
    def validar_identidad(self, usuario: Usuario, orden_id: str, metodo: str, numero_documento: str) -> None:
        """Verificación presencial: el operador ve el documento original y registra su número, que se compara
        con el del titular según Evaluación. El módulo Clientes no está en el producto (sin biometría)."""
        with self.Sesion() as s:
            orden = self._obtener(s, orden_id)
            self._exigir_editable(orden)
            aprobacion_id = orden.aprobacion_id
        a = self.m.evaluacion.obtener(aprobacion_id)
        if a is None:
            raise ErrorNegocio(404, "APROBACION_NO_ENCONTRADA", "Evaluación no registra esa aprobación")
        aprobada = numero_documento.strip().upper() == a.cliente_documento.strip().upper()
        vence = ahora_lima() + timedelta(minutes=self.config.validacion_vigencia_min)
        referencia = f"PRESENCIAL:{usuario.id}:{uuid7()[-12:]}"
        detalle = ("Documento original verificado: coincide con el titular del crédito" if aprobada
                   else "El documento presentado no corresponde al titular del crédito")
        with self.Sesion() as s, s.begin():
            orden = self._obtener(s, orden_id, bloquear=True)
            self._exigir_editable(orden)
            s.add(Validacion(id=uuid7(), orden_id=orden_id, tipo=TipoValidacion.IDENTIDAD, fase="PREPARACION",
                             proveedor="AGENCIA", referencia_evidencia=referencia[:100],
                             resultado=APROBADA if aprobada else RECHAZADA, detalle=detalle, vence_en=vence))
            s.flush()
            self._guardar_cambios(s, orden)
            self.auditor.registrar(s, "VALIDAR", f"IDENTIDAD_{'APROBADA' if aprobada else 'RECHAZADA'}",
                                   actor=usuario.id, orden_id=orden_id,
                                   detalle={"metodo": metodo, "documento": enmascarar(numero_documento),
                                            "referencia": referencia})
        if not aprobada:
            raise ErrorNegocio(422, "IDENTIDAD_RECHAZADA", "La validación de identidad del titular fue rechazada",
                               {"detalle": detalle})

    # ------------------------------------------------------------------ RF-03
    def cuentas_elegibles(self, usuario: Usuario, orden_id: str) -> list[dict]:
        with self.Sesion() as s:
            orden = self._obtener(s, orden_id)
            self._exigir_editable(orden)
            cliente_id, moneda = orden.cliente_id, orden.moneda
        return self.m.cuentas.elegibles(cliente_id, moneda)

    def seleccionar_cuenta(self, usuario: Usuario, orden_id: str, cuenta_id: str, version: int) -> None:
        with self.Sesion() as s:
            orden = self._obtener(s, orden_id)
            self._exigir_editable(orden)
            self._exigir_version(orden, version)
            cliente_id, moneda = orden.cliente_id, orden.moneda
        r = self.m.cuentas.elegibilidad(cuenta_id, cliente_id, moneda)
        elegible, motivo = bool(r.get("elegible")), r.get("motivo")
        with self.Sesion() as s, s.begin():
            orden = self._obtener(s, orden_id, bloquear=True)
            self._exigir_editable(orden)
            self._exigir_version(orden, version)
            texto = "Cuenta de ahorros individual habilitada" if elegible else f"No elegible: {motivo}"
            s.add(Validacion(id=uuid7(), orden_id=orden_id, tipo=TipoValidacion.CUENTA, fase="PREPARACION",
                             proveedor="CUENTAS", referencia_evidencia=str(r.get("referencia") or cuenta_id)[:100],
                             resultado=APROBADA if elegible else RECHAZADA,
                             detalle=f"{r.get('numero_enmascarado') or ''} · {texto}"[:255]))
            s.flush()
            self._guardar_cambios(s, orden, cuenta_id=cuenta_id if elegible else None)
            self.auditor.registrar(s, "VALIDAR", f"CUENTA_{'APROBADA' if elegible else 'RECHAZADA'}",
                                   actor=usuario.id, orden_id=orden_id,
                                   detalle={"cuenta": r.get("numero_enmascarado"), "motivo": motivo})
        if not elegible:
            if motivo == "MONEDA_DISTINTA":
                raise ErrorNegocio(422, "MONEDA_DISTINTA",
                                   "La cuenta está en otra moneda; el escenario base no admite conversión", {"motivo": motivo})
            raise ErrorNegocio(422, "CUENTA_NO_ELEGIBLE", "La cuenta destino no está habilitada para recibir el desembolso",
                               {"motivo": motivo})

    # ------------------------------------------------------------------ RF-05 / RF-06
    def confirmar(self, usuario: Usuario, orden_id: str, clave: str, version: int) -> None:
        with self.Sesion() as s:
            orden = self._obtener(s, orden_id)
            if orden.idempotency_key != clave:
                raise ErrorNegocio(409, "IDEMPOTENCIA_CONFLICTO", "La clave de idempotencia no corresponde a esta orden")
            if orden.estado in (Estado.EN_PROCESO, Estado.POR_VERIFICAR, Estado.CONFIRMADA, Estado.REVERTIDA) or (
                    orden.estado == Estado.RECHAZADA and orden.usuario_confirmacion):
                return  # repeticion: se devuelve el resultado existente sin ejecutar de nuevo
            if orden.estado != Estado.VALIDADA:
                raise ErrorNegocio(422, "VALIDACIONES_INCOMPLETAS", "Complete la validación de identidad y de la cuenta",
                                   {"estado": orden.estado})
            self._exigir_version(orden, version)
            identidad = self._ultimas_validaciones(s, orden_id).get(TipoValidacion.IDENTIDAD)
            datos = {c: getattr(orden, c) for c in ("id", "codigo_orden", "aprobacion_id", "aprobacion_version", "credito_id",
                                                   "cliente_id", "cuenta_id", "importe", "moneda", "idempotency_key",
                                                   "calendario_pagos")}
        if not self._vigente(identidad):
            with self.Sesion() as s, s.begin():
                transitar(s, orden_id, {Estado.VALIDADA}, Estado.PREPARADA)
                self.auditor.registrar(s, "CONFIRMAR", "VALIDACION_VENCIDA", actor=usuario.id, orden_id=orden_id)
            raise ErrorNegocio(422, "VALIDACION_VENCIDA", "La validación de identidad venció; valide nuevamente al titular")

        revalidaciones = self._revalidar(datos, usuario)
        fallidas = [v for v in revalidaciones if v["resultado"] == RECHAZADA]
        try:
            with self.Sesion() as s, s.begin():
                for v in revalidaciones:
                    s.add(Validacion(id=uuid7(), orden_id=orden_id, fase="EJECUCION", **v))
                if fallidas:
                    motivo = "; ".join(f"{v['tipo']}: {v['detalle']}" for v in fallidas)[:255]
                    if not transitar(s, orden_id, {Estado.VALIDADA}, Estado.RECHAZADA, motivo_rechazo=motivo,
                                     usuario_confirmacion=usuario.id):
                        raise ErrorNegocio(409, "VERSION_CONFLICTO", "La orden cambió durante la confirmación")
                    self.auditor.registrar(s, "CONFIRMAR", "REVALIDACION_FALLIDA", actor=usuario.id, orden_id=orden_id,
                                           detalle={"motivo": motivo})
                else:
                    resultado = s.execute(
                        update(Orden).where(Orden.id == orden_id, Orden.estado == Estado.VALIDADA, Orden.version == version)
                        .values(estado=Estado.EN_PROCESO, usuario_confirmacion=usuario.id, version=Orden.version + 1)
                        .execution_options(synchronize_session=False))
                    if resultado.rowcount != 1:
                        actual = self._obtener(s, orden_id)
                        if actual.estado in INCIERTOS | CON_RESULTADO_FINANCIERO:
                            return  # otra peticion con la misma clave ya inicio la ejecucion
                        raise ErrorNegocio(409, "VERSION_CONFLICTO", "La orden cambió durante la confirmación")
                    self.auditor.registrar(s, "CONFIRMAR", "EN_PROCESO", actor=usuario.id, orden_id=orden_id,
                                           detalle={"importe": formatear(datos["importe"]), "moneda": datos["moneda"],
                                                    "cuenta": "****" + str(datos["cuenta_id"])[-4:]})
        except IntegrityError as exc:
            if not es_duplicado(exc, "uk_orden_credito_en_ejecucion"):
                raise
            with self.Sesion() as s, s.begin():
                transitar(s, orden_id, {Estado.VALIDADA}, Estado.RECHAZADA, usuario_confirmacion=usuario.id,
                          motivo_rechazo="CREDITO_CON_DESEMBOLSO: el crédito ya tiene otra orden en ejecución o confirmada")
                self.auditor.registrar(s, "CONFIRMAR", "CREDITO_CON_DESEMBOLSO", actor=usuario.id, orden_id=orden_id)
            raise ErrorNegocio(409, "CREDITO_CON_DESEMBOLSO",
                               "El crédito ya tiene otra orden en ejecución o confirmada (RN-05)") from exc
        if fallidas:
            raise ErrorNegocio(422, "REVALIDACION_FALLIDA", "Las condiciones cambiaron; la orden se rechazó sin abonar",
                               {"validaciones": [{"tipo": v["tipo"], "detalle": v["detalle"]} for v in fallidas]})

        # Intencion durable registrada: se solicita el abono una sola vez (RN-07).
        try:
            respuesta = self.m.cuentas.abonar(datos)
        except DependenciaNoDisponible as exc:
            with self.Sesion() as s, s.begin():
                transitar(s, orden_id, {Estado.EN_PROCESO}, Estado.POR_VERIFICAR)
                self.auditor.registrar(s, "CONFIRMAR", "POR_VERIFICAR", actor=usuario.id, orden_id=orden_id,
                                       detalle={"causa": exc.detalle.get("causa") if exc.detalle else None})
            return
        with self.Sesion() as s, s.begin():
            self.aplicar_resultado(s, orden_id, respuesta, actor=usuario.id)

    def _revalidar(self, d: dict, usuario: Usuario) -> list[dict]:
        """Revalidacion en la frontera de ejecucion (RN-06)."""
        resultados = []
        a = self.m.evaluacion.obtener(d["aprobacion_id"])
        if a is None or not a.habilitada:
            detalle = f"La aprobación ya no está habilitada ({a.estado if a else 'INEXISTENTE'})"
        elif a.version != d["aprobacion_version"]:
            detalle = f"La aprobación cambió de versión (v{d['aprobacion_version']} → v{a.version})"
        elif a.importe != d["importe"] or a.moneda != d["moneda"]:
            detalle = "El importe o la moneda aprobados cambiaron"
        else:
            detalle = self._problema_calendario(d["calendario_pagos"])
        resultados.append({"tipo": TipoValidacion.APROBACION, "proveedor": "EVALUACION",
                           "referencia_evidencia": f"{d['aprobacion_id']}@v{a.version if a else '?'}",
                           "resultado": RECHAZADA if detalle else APROBADA,
                           "detalle": detalle or "Aprobación vigente y sin cambios",
                           "vence_en": a.vigente_hasta if a else None})
        e = self.m.cuentas.elegibilidad(d["cuenta_id"], d["cliente_id"], d["moneda"])
        resultados.append({"tipo": TipoValidacion.CUENTA, "proveedor": "CUENTAS",
                           "referencia_evidencia": str(e.get("referencia") or d["cuenta_id"])[:100],
                           "resultado": APROBADA if e.get("elegible") else RECHAZADA,
                           "detalle": f"{e.get('numero_enmascarado') or ''} · "
                                      f"{'Cuenta elegible' if e.get('elegible') else 'No elegible: ' + str(e.get('motivo'))}",
                           "vence_en": None})
        resultados.append({"tipo": TipoValidacion.AUTORIZACION, "proveedor": "COREDB",
                           "referencia_evidencia": f"coredb:{usuario.jti}"[:100], "resultado": APROBADA,
                           "detalle": f"Permiso {EJECUTAR} · rol {usuario.rol}", "vence_en": None})
        if self.config.antifraude_habilitado:
            af = self.m.seguridad.antifraude({"orden_id": d["id"], "cliente_id": d["cliente_id"],
                                              "cuenta_id": d["cuenta_id"], "importe": formatear(d["importe"]),
                                              "moneda": d["moneda"], "operador": usuario.id, "canal": "AGENCIA"})
            permitido = af.get("decision") == "PERMITIR"
            resultados.append({"tipo": TipoValidacion.ANTIFRAUDE, "proveedor": "SEGURIDAD",
                               "referencia_evidencia": str(af.get("referencia", ""))[:100],
                               "resultado": APROBADA if permitido else RECHAZADA,
                               "detalle": "Sin alertas de fraude" if permitido else (af.get("motivo") or "Operación denegada"),
                               "vence_en": None})
        return resultados

    def aplicar_resultado(self, s: Session, orden_id: str, r: dict, actor: str) -> str:
        """Aplica la respuesta de Cuentas a una orden EN_PROCESO o POR_VERIFICAR. Devuelve el estado final."""
        if r.get("estado") == "CONFIRMADO":
            fecha = desde_iso(r.get("fecha_efectiva")) or ahora_lima()
            if transitar(s, orden_id, set(INCIERTOS), Estado.CONFIRMADA,
                         operacion_financiera_id=r["operacion_id"], fecha_efectiva=fecha):
                orden = self._obtener(s, orden_id)
                # En la misma transacción: la obligación para Cobranza y el aviso a Evaluación (outbox).
                for tipo, payload in ((TIPO_COBRANZA, obligacion_cobranza(orden)),
                                      (TIPO_EVALUACION, aviso_evaluacion(orden))):
                    s.add(EventoEntrega(id=uuid7(), orden_id=orden_id, tipo=tipo, version_esquema="v1",
                                        payload=payload, estado="PENDIENTE", intentos=0,
                                        siguiente_intento=utc_ahora()))
                self.auditor.registrar(s, "CONFIRMAR", "CONFIRMADA", actor=actor, orden_id=orden_id,
                                       detalle={"operacion": r["operacion_id"]})
            return Estado.CONFIRMADA
        if r.get("estado") == "RECHAZADO":
            motivo = f"{r.get('codigo') or 'RECHAZADO'}: {r.get('motivo') or 'Cuentas rechazó el abono'}"[:255]
            if transitar(s, orden_id, set(INCIERTOS), Estado.RECHAZADA, motivo_rechazo=motivo):
                self.auditor.registrar(s, "CONFIRMAR", "RECHAZADA", actor=actor, orden_id=orden_id, detalle={"motivo": motivo})
            return Estado.RECHAZADA
        raise ErrorNegocio(502, "RESPUESTA_INESPERADA", "Cuentas devolvió un estado desconocido", {"respuesta": r})

    # ------------------------------------------------------------------ RF-06 / CU-04
    def resolver_incierta(self, orden_id: str, actor: str, rechazar_no_encontrado: bool) -> str:
        """Busca el abono de la orden en CUENTAS y aplica el resultado. Nunca reenvía el abono."""
        with self.Sesion() as s:
            orden = self._obtener(s, orden_id)
            if orden.estado not in INCIERTOS:
                return orden.estado
            consulta = {"cuenta_id": orden.cuenta_id, "codigo_orden": orden.codigo_orden}
            estado = orden.estado
        try:
            r = self.m.cuentas.consultar_abono(consulta)
        except DependenciaNoDisponible:
            if estado == Estado.EN_PROCESO:
                with self.Sesion() as s, s.begin():
                    transitar(s, orden_id, {Estado.EN_PROCESO}, Estado.POR_VERIFICAR)
            raise
        with self.Sesion() as s, s.begin():
            if r.get("estado") in ("CONFIRMADO", "RECHAZADO"):
                final = self.aplicar_resultado(s, orden_id, r, actor=actor)
                self.auditor.registrar(s, "RECUPERAR", final, actor=actor, orden_id=orden_id)
                return final
            if rechazar_no_encontrado and r.get("estado") == "NO_ENCONTRADO":
                motivo = "ABONO_NO_REGISTRADO: Cuentas no registró el abono dentro de la ventana de gracia"
                if transitar(s, orden_id, set(INCIERTOS), Estado.RECHAZADA, motivo_rechazo=motivo):
                    self.auditor.registrar(s, "RECUPERAR", "RECHAZADA", actor=actor, orden_id=orden_id,
                                           detalle={"motivo": motivo})
                return Estado.RECHAZADA
            if estado == Estado.EN_PROCESO:
                transitar(s, orden_id, {Estado.EN_PROCESO}, Estado.POR_VERIFICAR)
            return Estado.POR_VERIFICAR

    def verificar(self, usuario: Usuario, orden_id: str) -> str:
        return self.resolver_incierta(orden_id, actor=usuario.id, rechazar_no_encontrado=False)

    # ------------------------------------------------------------------ RF-08
    def detalle(self, usuario: Usuario, orden_id: str) -> dict:
        with self.Sesion() as s:
            o = self._obtener(s, orden_id)
            ultimas = self._ultimas_validaciones(s, orden_id)
            reversiones = s.scalars(select(SolicitudReversion).where(SolicitudReversion.orden_id == orden_id)
                                    .order_by(SolicitudReversion.creado_en)).all()
            datos = _orden_salida(o)
            datos["validaciones"] = [_validacion_salida(v) for v in o.validaciones]
            datos["eventos"] = [_evento_salida(e) for e in o.eventos]
            datos["reversiones"] = [reversion_salida(r) for r in reversiones]
            cuenta = ultimas.get(TipoValidacion.CUENTA)
            datos["cuenta_enmascarada"] = (cuenta.detalle or "").split(" · ")[0] or None if cuenta and o.cuenta_id else None
            identidad = ultimas.get(TipoValidacion.IDENTIDAD)
            datos["identidad"] = {"resultado": "VENCIDA" if identidad and identidad.resultado == APROBADA and not self._vigente(identidad)
                                  else identidad.resultado, "vence_en": _iso(identidad.vence_en),
                                  "detalle": identidad.detalle} if identidad else None
            activa = any(r.estado != "RECHAZADA" for r in reversiones)
        a = self.aprobacion(o.aprobacion_id)
        datos["aprobacion"] = _aprobacion_salida(a) if a else None
        datos["solicitud_id"] = o.solicitud_id
        datos["calendario"] = o.calendario_pagos or []
        datos["acciones"] = self._acciones(usuario, o.estado, activa)
        return datos

    def _acciones(self, usuario: Usuario, estado: str, reversion_activa: bool) -> list[str]:
        acciones = []
        if estado in EDITABLES and usuario.tiene(EJECUTAR):
            acciones += ["VALIDAR_IDENTIDAD", "SELECCIONAR_CUENTA"]
        if estado == Estado.VALIDADA and usuario.tiene(EJECUTAR):
            acciones.append("CONFIRMAR")
        if estado in INCIERTOS and usuario.tiene(LEER):
            acciones.append("VERIFICAR")
        if estado in CON_RESULTADO_FINANCIERO and usuario.tiene(LEER):
            acciones.append("CONSTANCIA")
        if (estado == Estado.CONFIRMADA and usuario.tiene(EJECUTAR) and self.config.reversion_habilitada
                and not reversion_activa):
            acciones.append("SOLICITAR_REVERSION")
        if usuario.rol in (SUPERVISOR, AUDITOR):
            acciones.append("VER_AUDITORIA")
        return acciones

    def listar(self, texto: str | None, estado: str | None, desde: str | None, hasta: str | None,
               pagina: int, tamano: int) -> dict:
        with self.Sesion() as s:
            filtros = []
            if texto:
                patron = f"%{texto.strip()}%"
                filtros.append(or_(Orden.codigo_orden.like(patron), Orden.credito_id.like(patron),
                                   Orden.cliente_id.like(patron), Orden.aprobacion_id.like(patron)))
            if estado:
                filtros.append(Orden.estado == estado)
            if desde:
                filtros.append(fecha_lima(Orden.creado_en) >= desde)
            if hasta:
                filtros.append(fecha_lima(Orden.creado_en) <= hasta)
            total = s.scalar(select(func.count()).select_from(Orden).where(*filtros))
            filas = s.scalars(select(Orden).where(*filtros).order_by(Orden.creado_en.desc())
                              .offset((pagina - 1) * tamano).limit(tamano)).all()
            return {"items": [_orden_salida(o) for o in filas], "total": total, "pagina": pagina, "tamano": tamano}

    def constancia(self, usuario: Usuario, orden_id: str) -> dict:
        datos = self.detalle(usuario, orden_id)
        if datos["estado"] not in CON_RESULTADO_FINANCIERO:
            raise ErrorNegocio(409, "ESTADO_INVALIDO", "La constancia solo se emite con confirmación financiera",
                               {"estado": datos["estado"]})
        with self.Sesion() as s, s.begin():
            self.auditor.registrar(s, "CONSULTAR", "CONSTANCIA", actor=usuario.id, orden_id=orden_id)
        a = datos.get("aprobacion") or {}
        return {
            "codigo_orden": datos["codigo_orden"], "estado": datos["estado"],
            "operacion_financiera_id": datos["operacion_financiera_id"], "fecha_efectiva": datos["fecha_efectiva"],
            "credito_id": datos["credito_id"], "aprobacion_id": datos["aprobacion_id"],
            "producto": a.get("producto"), "plazo_meses": a.get("plazo_meses"), "tasa_tea": a.get("tasa_tea"),
            "cliente_nombre": a.get("cliente_nombre"), "cliente_documento": a.get("cliente_documento"),
            "cuenta_enmascarada": datos["cuenta_enmascarada"], "importe": datos["importe"], "moneda": datos["moneda"],
            "agencia": usuario.agencia_nombre if usuario.agencia_id == datos["agencia_id"] else datos["agencia_id"],
            "usuario_preparacion": datos["usuario_preparacion"], "usuario_confirmacion": datos["usuario_confirmacion"],
            "entrega_estado": datos["entrega_estado"], "correlation_id": datos["correlation_id"],
            "emitida_en": _iso(ahora_lima()), "emitida_por": usuario.id,
        }

    def auditoria(self, orden_id: str) -> list[dict]:
        with self.Sesion() as s:
            self._obtener(s, orden_id)
            filas = s.scalars(select(Auditoria).where(Auditoria.orden_id == orden_id).order_by(Auditoria.id)).all()
            return [{"id": a.id, "actor_id": a.actor_id, "accion": a.accion, "resultado": a.resultado,
                     "correlation_id": a.correlation_id, "detalle": a.detalle, "creado_en": _iso_utc(a.creado_en)} for a in filas]


# ---------------------------------------------------------------------- funciones de apoyo
def _correlacion() -> str:
    from ..core.correlacion import correlation_id
    return correlation_id()


def _iso(fecha: datetime | None) -> str | None:
    """Fecha de negocio (hora de Lima, sin zona en la base) con su zona: -05:00."""
    return fecha.replace(tzinfo=LIMA).isoformat() if fecha else None


def _iso_utc(fecha: datetime | None) -> str | None:
    """Marca técnica (TIMESTAMP en UTC, la zona de la sesión con MySQL) con su zona."""
    return fecha.replace(tzinfo=timezone.utc).isoformat() if fecha else None


def _fecha_lima(fecha: datetime | None) -> str | None:
    """Fecha de negocio de la orden (hora de Lima, sin zona) con su zona explícita: -05:00."""
    return _iso(fecha)


def obligacion_cobranza(o: Orden) -> dict:
    """CR-INT-06 tal como lo recibe Cobranza (ObligacionIn). El calendario es el de Solicitud, sin cambios:
    solo se usan los nombres de campo de Cobranza; montoCuota es la cuota total (capital + interés)."""
    return {"codCredito": o.credito_id, "idCliente": o.cliente_id, "idSolicitud": o.solicitud_id,
            "montoAprobado": formatear(o.importe), "moneda": o.moneda, "fechaDesembolso": _fecha_lima(o.fecha_efectiva),
            "calendarioPagos": [{"numeroCuota": c["numeroCuota"], "fechaVencimiento": c["fechaVencimiento"],
                                 "montoCuota": c["cuotaTotal"]} for c in (o.calendario_pagos or [])]}


def aviso_evaluacion(o: Orden) -> dict:
    """CR-INT-04: Evaluación marca la aprobación DESEMBOLSADA con la orden y la fecha del abono."""
    return {"idAprobacion": o.aprobacion_id, "version": o.aprobacion_version, "codigoOrden": o.codigo_orden,
            "fechaDesembolso": _fecha_lima(o.fecha_efectiva)}


def payload_evento(o: Orden, evento_id: str, tipo: str) -> dict:
    return {"evento_id": evento_id, "tipo": tipo, "version_esquema": "v1", "orden_id": o.id,
            "codigo_orden": o.codigo_orden, "credito_id": o.credito_id, "aprobacion_id": o.aprobacion_id,
            "aprobacion_version": o.aprobacion_version, "cliente_id": o.cliente_id, "cuenta_id": o.cuenta_id,
            "operacion_financiera_id": o.operacion_financiera_id, "importe": formatear(o.importe), "moneda": o.moneda,
            "fecha_efectiva": _iso(o.fecha_efectiva)}


def _aprobacion_salida(a: Aprobacion) -> dict:
    return {"aprobacion_id": a.aprobacion_id, "version": a.version, "credito_id": a.credito_id,
            "cliente_id": a.cliente_id, "cliente_nombre": a.cliente_nombre,
            "cliente_documento": enmascarar(a.cliente_documento), "producto": a.producto,
            "importe": formatear(a.importe), "moneda": a.moneda, "plazo_meses": a.plazo_meses,
            "tasa_tea": a.tasa_tea, "estado": a.estado, "vigente_hasta": _iso(a.vigente_hasta)}


def _orden_salida(o: Orden) -> dict:
    return {"id": o.id, "codigo_orden": o.codigo_orden, "estado": o.estado, "entrega_estado": o.entrega_estado,
            "motivo_rechazo": o.motivo_rechazo, "aprobacion_id": o.aprobacion_id,
            "aprobacion_version": o.aprobacion_version, "credito_id": o.credito_id, "cliente_id": o.cliente_id,
            "cuenta_id": o.cuenta_id, "importe": formatear(o.importe), "moneda": o.moneda,
            "operacion_financiera_id": o.operacion_financiera_id, "fecha_efectiva": _iso(o.fecha_efectiva),
            "idempotency_key": o.idempotency_key, "canal": o.canal, "agencia_id": o.agencia_id,
            "usuario_preparacion": o.usuario_preparacion, "usuario_confirmacion": o.usuario_confirmacion,
            "correlation_id": o.correlation_id, "version": o.version,
            "creado_en": _iso_utc(o.creado_en), "actualizado_en": _iso_utc(o.actualizado_en)}


def _validacion_salida(v: Validacion) -> dict:
    return {"id": v.id, "tipo": v.tipo, "fase": v.fase, "proveedor": v.proveedor,
            "referencia_evidencia": v.referencia_evidencia, "resultado": v.resultado, "detalle": v.detalle,
            "vence_en": _iso(v.vence_en), "creado_en": _iso_utc(v.creado_en)}


def _evento_salida(e: EventoEntrega) -> dict:
    return {"id": e.id, "tipo": e.tipo, "estado": e.estado, "intentos": e.intentos,
            "siguiente_intento": _iso_utc(e.siguiente_intento), "confirmacion_id": e.confirmacion_id,
            "ultimo_error": e.ultimo_error, "creado_en": _iso_utc(e.creado_en)}


def reversion_salida(r: SolicitudReversion) -> dict:
    return {"id": r.id, "orden_id": r.orden_id, "motivo": r.motivo, "origen": r.origen, "estado": r.estado,
            "solicitante_id": r.solicitante_id, "autorizador_id": r.autorizador_id,
            "motivo_rechazo": r.motivo_rechazo, "reversion_financiera_id": r.reversion_financiera_id,
            "creado_en": _iso_utc(r.creado_en), "actualizado_en": _iso_utc(r.actualizado_en)}
