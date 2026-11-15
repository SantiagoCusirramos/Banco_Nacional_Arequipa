"""Reglas de Evaluación sobre su base (MySQL).

Cada operación es una transacción. Los cambios de estado comparan la versión de la fila para no
pisar el trabajo de otro analista, y todo cambio queda en el historial con su actor y su
X-Correlation-ID. El calendario lo arma SOL (RN-SOL-006): aquí se copia sin cambios.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from . import motor
from .auth import DECIDIR, EVALUAR, Perfil
from .comun import ErrorEva, a_utc, correlacion_actual, dinero, enmascarar, iso, tasa, utc_ahora
from .config import Config
from .contratos import DecisionIn, DesembolsoIn, RevocacionIn, SituacionIn, SobreExpediente

FINALES = ("APROBADO", "OBSERVADO", "RECHAZADO")
CR_INT_03 = "CR-INT-03"


def huella(datos: dict) -> str:
    texto = json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(texto.encode()).hexdigest()


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, default=str)


def _leer_json(valor):
    return json.loads(valor) if isinstance(valor, (str, bytes, bytearray)) else valor


def _historial(c: Connection, evento: str, actor: str, *, evaluacion: str | None = None,
               aprobacion: str | None = None, detalle: dict | None = None) -> None:
    c.execute(text(
        "INSERT INTO eva_historial (fecha, evento, actor, id_evaluacion, id_aprobacion, id_correlacion, detalle) "
        "VALUES (:fecha, :evento, :actor, :evaluacion, :aprobacion, :correlacion, :detalle)"),
        {"fecha": utc_ahora(), "evento": evento, "actor": actor[:60], "evaluacion": evaluacion,
         "aprobacion": aprobacion, "correlacion": correlacion_actual(),
         "detalle": None if detalle is None else _json(detalle)})


def _codigo(c: Connection, tipo: str) -> str:
    """EVA-AAAA-NNNNNN, APR-... o CRE-...: el bloqueo de la fila ordena a los concurrentes."""
    anio = utc_ahora().year
    c.execute(text("INSERT INTO eva_correlativo (tipo, anio, ultimo) VALUES (:tipo, :anio, 1) "
                   "ON DUPLICATE KEY UPDATE ultimo = ultimo + 1"), {"tipo": tipo, "anio": anio})
    numero = c.execute(text("SELECT ultimo FROM eva_correlativo WHERE tipo = :tipo AND anio = :anio"),
                       {"tipo": tipo, "anio": anio}).scalar_one()
    return f"{tipo}-{anio}-{numero:06d}"


def _exigir_version(actual: int, enviada: int) -> None:
    if actual != enviada:
        raise ErrorEva(409, "VERSION_DESACTUALIZADA",
                       "El registro cambió mientras lo revisabas. Actualiza y vuelve a intentarlo.",
                       {"version": actual})


def _validar_expediente(sobre: SobreExpediente) -> None:
    """El calendario de SOL debe cuadrar con las condiciones antes de evaluarlo."""
    e = sobre.expediente
    cuotas = e.calendario.cuotas
    problemas = []
    if e.cliente.id_cliente != e.condiciones.id_cliente:
        problemas.append("El cliente del expediente no coincide con el de las condiciones.")
    if [c.numero_cuota for c in cuotas] != list(range(1, len(cuotas) + 1)):
        problemas.append("Las cuotas del calendario deben numerarse 1, 2, 3...")
    if len(cuotas) != e.condiciones.plazo_meses:
        problemas.append("El calendario no tiene una cuota por cada mes del plazo.")
    if sum((c.amortizacion for c in cuotas), Decimal(0)) != e.condiciones.monto_solicitado:
        problemas.append("La amortización del calendario no suma el monto solicitado.")
    if sum((c.cuota_total for c in cuotas), Decimal(0)) != e.calendario.total_pagar:
        problemas.append("Las cuotas del calendario no suman el total a pagar.")
    fechas = [c.fecha_vencimiento for c in cuotas]
    if fechas != sorted(set(fechas)):
        problemas.append("Los vencimientos del calendario deben ser crecientes.")
    if problemas:
        raise ErrorEva(422, "EXPEDIENTE_INCONSISTENTE", " ".join(problemas))


def _cuota_json(numero, vence, saldo_inicial, amortizacion, interes, total, saldo_final) -> dict:
    return {"numeroCuota": numero, "fechaVencimiento": vence.isoformat(), "saldoInicial": dinero(saldo_inicial),
            "amortizacion": dinero(amortizacion), "interes": dinero(interes), "cuotaTotal": dinero(total),
            "saldoFinal": dinero(saldo_final)}


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class Servicio:
    def __init__(self, engine: Engine, config: Config):
        self.engine = engine
        self.config = config

    # ------------------------------------------------------------------ CR-INT-02
    def recibir_expediente(self, sobre: SobreExpediente, crudo: dict) -> tuple[dict, bool]:
        """Devuelve (acuse, nuevo). Repetir el mismo sobre devuelve el mismo acuse."""
        _validar_expediente(sobre)
        firma = huella(crudo)
        try:
            with self.engine.begin() as c:
                previo = self._expediente_existente(c, sobre, firma)
                if previo is not None:
                    return previo, False
                return self._registrar_expediente(c, sobre, crudo, firma), True
        except IntegrityError:
            # Otra petición con la misma operación o la misma versión ganó la carrera.
            with self.engine.begin() as c:
                previo = self._expediente_existente(c, sobre, firma)
                if previo is not None:
                    return previo, False
            raise ErrorEva(409, "VERSION_YA_RECIBIDA", "Esa versión de la solicitud ya se recibió.") from None

    def acuse(self, id_operacion: str) -> dict | None:
        with self.engine.connect() as c:
            return self._acuse(c, id_operacion)

    @staticmethod
    def _acuse(c: Connection, id_operacion: str) -> dict | None:
        f = c.execute(text("SELECT id_solicitud, version_solicitud, id_operacion, id_evaluacion, ronda, acuse "
                           "FROM eva_evaluacion WHERE id_operacion = :op"), {"op": id_operacion}).first()
        if f is None:
            return None
        return {"idSolicitud": f.id_solicitud, "versionSolicitud": f.version_solicitud, "idOperacion": f.id_operacion,
                "idEvaluacion": f.id_evaluacion, "ronda": f.ronda, "acuse": f.acuse}

    def _expediente_existente(self, c: Connection, sobre: SobreExpediente, firma: str) -> dict | None:
        fila = c.execute(text("SELECT huella FROM eva_expediente WHERE id_operacion = :op"),
                         {"op": sobre.idOperacion}).first()
        if fila is not None:
            if fila.huella != firma:
                raise ErrorEva(409, "OPERACION_REUTILIZADA", "La operación ya se recibió con otro contenido.")
            return self._acuse(c, sobre.idOperacion)
        otra = c.execute(text("SELECT 1 FROM eva_expediente WHERE id_solicitud = :s AND version_solicitud = :v"),
                         {"s": sobre.idSolicitud, "v": sobre.versionSolicitud}).first()
        if otra is not None:
            raise ErrorEva(409, "VERSION_YA_RECIBIDA", "Esa versión de la solicitud ya se recibió con otra operación.")
        return None

    def _registrar_expediente(self, c: Connection, sobre: SobreExpediente, crudo: dict, firma: str) -> dict:
        previa = c.execute(text("SELECT estado, ronda, version_solicitud FROM eva_evaluacion "
                                "WHERE id_solicitud = :s ORDER BY ronda DESC LIMIT 1 FOR UPDATE"),
                           {"s": sobre.idSolicitud}).first()
        if previa is not None:
            if previa.estado in ("PENDIENTE", "EN_REVISION"):
                raise ErrorEva(409, "EVALUACION_EN_CURSO", "La versión anterior de la solicitud sigue en evaluación.")
            if previa.estado != "OBSERVADO":
                raise ErrorEva(409, "SOLICITUD_CON_RESULTADO", "La solicitud ya tiene un resultado final.")
            if sobre.versionSolicitud <= previa.version_solicitud:
                raise ErrorEva(409, "VERSION_ANTERIOR", "La versión recibida no es posterior a la ya evaluada.")
        ronda = previa.ronda + 1 if previa is not None else 1
        id_evaluacion = _codigo(c, "EVA")
        ahora = utc_ahora()
        e = sobre.expediente
        nombre = " ".join(p for p in (e.cliente.nombres, e.cliente.apellido_paterno, e.cliente.apellido_materno) if p)
        c.execute(text(
            "INSERT INTO eva_expediente (id_operacion, id_solicitud, version_solicitud, id_correlacion, "
            "version_contrato, actor_envio, simulado, huella, contenido, recibido_en) VALUES (:op, :s, :v, :corr, "
            ":contrato, :actor, :simulado, :huella, :contenido, :ahora)"),
            {"op": sobre.idOperacion, "s": sobre.idSolicitud, "v": sobre.versionSolicitud,
             "corr": sobre.idCorrelacion, "contrato": sobre.versionContrato, "actor": sobre.actorEnvio,
             "simulado": sobre.simulado, "huella": firma, "contenido": _json(crudo), "ahora": ahora})
        c.execute(text(
            "INSERT INTO eva_evaluacion (id_evaluacion, id_operacion, id_solicitud, version_solicitud, ronda, acuse, "
            "id_cliente, cliente_nombre, tipo_documento, numero_documento, producto, destino, monto_solicitado, "
            "moneda, plazo_meses, tasa_tea, estado, version, recibido_en, actualizado_en) VALUES (:id, :op, :s, :v, "
            ":ronda, :acuse, :cliente, :nombre, :tipo_doc, :doc, :producto, :destino, :monto, :moneda, :plazo, "
            ":tea, 'PENDIENTE', 1, :ahora, :ahora)"),
            {"id": id_evaluacion, "op": sobre.idOperacion, "s": sobre.idSolicitud, "v": sobre.versionSolicitud,
             "ronda": ronda, "acuse": f"ACK-{id_evaluacion}", "cliente": e.cliente.id_cliente, "nombre": nombre[:200],
             "tipo_doc": e.cliente.cod_tipo_documento, "doc": e.cliente.numero_documento,
             "producto": e.politica.producto_nombre, "destino": e.condiciones.destino_credito,
             "monto": e.condiciones.monto_solicitado, "moneda": e.condiciones.moneda,
             "plazo": e.condiciones.plazo_meses, "tea": e.politica.tea, "ahora": ahora})
        _historial(c, "EXPEDIENTE_RECIBIDO", f"SOL:{sobre.actorEnvio or 'servicio'}", evaluacion=id_evaluacion,
                   detalle={"idOperacion": sobre.idOperacion, "versionSolicitud": sobre.versionSolicitud,
                            "ronda": ronda, "simulado": sobre.simulado})
        return self._acuse(c, sobre.idOperacion)

    # ------------------------------------------------------------------ Analista
    @staticmethod
    def _evaluacion(c: Connection, id_evaluacion: str, bloquear: bool = False):
        sql = "SELECT * FROM eva_evaluacion WHERE id_evaluacion = :id" + (" FOR UPDATE" if bloquear else "")
        fila = c.execute(text(sql), {"id": id_evaluacion}).first()
        if fila is None:
            raise ErrorEva(404, "EVALUACION_NO_ENCONTRADA", "La evaluación no existe.")
        return fila

    @staticmethod
    def _actualizar_evaluacion(c: Connection, ev, **cambios) -> None:
        columnas = ", ".join(f"{columna} = :{columna}" for columna in cambios)
        r = c.execute(text(f"UPDATE eva_evaluacion SET {columnas}, version = version + 1, actualizado_en = :_ahora "
                           "WHERE id_evaluacion = :_id AND version = :_version"),
                      {**cambios, "_ahora": utc_ahora(), "_id": ev.id_evaluacion, "_version": ev.version})
        if r.rowcount != 1:
            raise ErrorEva(409, "VERSION_DESACTUALIZADA", "La evaluación cambió mientras la revisabas.")

    def registrar_situacion(self, id_evaluacion: str, datos: SituacionIn, perfil: Perfil) -> dict:
        with self.engine.begin() as c:
            ev = self._evaluacion(c, id_evaluacion, bloquear=True)
            if ev.estado != "PENDIENTE":
                raise ErrorEva(409, "EVALUACION_NO_PENDIENTE", "La situación financiera ya se registró en esta evaluación.")
            _exigir_version(ev.version, datos.version)
            if not datos.verificada:
                raise ErrorEva(422, "SITUACION_NO_VERIFICADA", "Se requiere la situación financiera verificada.")
            ahora = utc_ahora()
            c.execute(text(
                "INSERT INTO eva_situacion_financiera (id_evaluacion, id_cliente, ingreso_mensual, deuda_mensual, "
                "riesgo, verificada, registrado_por, registrado_en) VALUES (:ev, :cliente, :ingreso, :deuda, :riesgo, "
                ":verificada, :por, :ahora)"),
                {"ev": id_evaluacion, "cliente": ev.id_cliente, "ingreso": datos.ingresoMensual,
                 "deuda": datos.deudaMensual, "riesgo": datos.riesgo, "verificada": datos.verificada,
                 "por": perfil.usuario, "ahora": ahora})
            r = motor.evaluar(ev.monto_solicitado, ev.plazo_meses, datos.ingresoMensual, datos.deudaMensual,
                              datos.riesgo)
            estado = "EN_REVISION" if r.resultado == "OBSERVADO" else r.resultado
            final = estado in FINALES
            explicacion = None
            if final:
                accion = "Aprobado" if estado == "APROBADO" else "Rechazado"
                explicacion = f"{accion} por la regla {motor.REGLA}. {r.motivo}."
            self._actualizar_evaluacion(
                c, ev, estado=estado, resultado_motor=r.resultado, score=r.score, limite=r.limite, ratio=r.ratio,
                regla=motor.REGLA, motivo=explicacion, decidido_por="MOTOR" if final else None,
                decidido_en=ahora if final else None)
            _historial(c, "SITUACION_REGISTRADA", perfil.usuario, evaluacion=id_evaluacion,
                       detalle={"riesgo": datos.riesgo})
            _historial(c, "RESULTADO_MOTOR", "MOTOR", evaluacion=id_evaluacion,
                       detalle={"resultado": r.resultado, "limite": dinero(r.limite),
                                "ratio": None if r.ratio is None else str(r.ratio), "regla": motor.REGLA})
            if final:
                self._cerrar(c, id_evaluacion, estado, explicacion, actor="MOTOR")
        return self.detalle(id_evaluacion, perfil)

    def decidir(self, id_evaluacion: str, datos: DecisionIn, perfil: Perfil) -> dict:
        with self.engine.begin() as c:
            ev = self._evaluacion(c, id_evaluacion, bloquear=True)
            if ev.estado != "EN_REVISION":
                raise ErrorEva(409, "EVALUACION_NO_EN_REVISION", "Solo se decide una evaluación EN_REVISION.")
            _exigir_version(ev.version, datos.version)
            self._actualizar_evaluacion(c, ev, estado=datos.decision, motivo=datos.observaciones,
                                        decidido_por=perfil.usuario, decidido_en=utc_ahora())
            _historial(c, "DECISION_ANALISTA", perfil.usuario, evaluacion=id_evaluacion,
                       detalle={"decision": datos.decision})
            self._cerrar(c, id_evaluacion, datos.decision, datos.observaciones, actor=perfil.usuario)
        return self.detalle(id_evaluacion, perfil)

    def _cerrar(self, c: Connection, id_evaluacion: str, decision: str, observaciones: str, actor: str) -> None:
        """Resultado final: aprobación para Desembolso si corresponde y resultado para SOL."""
        ev = self._evaluacion(c, id_evaluacion)
        expediente = c.execute(text("SELECT id_correlacion, contenido FROM eva_expediente WHERE id_operacion = :op"),
                               {"op": ev.id_operacion}).one()
        if decision == "APROBADO":
            self._crear_aprobacion(c, ev, SobreExpediente.model_validate(_leer_json(expediente.contenido)), actor)
        id_operacion = str(uuid.uuid4())
        contenido = {"idSolicitud": ev.id_solicitud, "versionSolicitud": ev.version_solicitud,
                     "idEvaluacion": ev.id_evaluacion, "ronda": ev.ronda, "idOperacion": id_operacion,
                     "idCorrelacion": expediente.id_correlacion, "decision": decision,
                     "observaciones": observaciones}
        ahora = utc_ahora()
        c.execute(text(
            "INSERT INTO eva_envio (id_operacion, id_evaluacion, interfaz, contenido, estado, intentos, "
            "siguiente_intento, creado_en) VALUES (:op, :ev, :interfaz, :contenido, 'PENDIENTE', 0, :ahora, :ahora)"),
            {"op": id_operacion, "ev": id_evaluacion, "interfaz": CR_INT_03, "contenido": _json(contenido),
             "ahora": ahora})
        _historial(c, "RESULTADO_POR_ENTREGAR", actor, evaluacion=id_evaluacion,
                   detalle={"decision": decision, "idOperacion": id_operacion})

    def _crear_aprobacion(self, c: Connection, ev, sobre: SobreExpediente, actor: str) -> None:
        calendario, politica = sobre.expediente.calendario, sobre.expediente.politica
        id_aprobacion, cod_credito = _codigo(c, "APR"), _codigo(c, "CRE")
        ahora = utc_ahora()
        vigente_hasta = ahora + timedelta(days=self.config.vigencia_dias)
        c.execute(text(
            "INSERT INTO eva_aprobacion (id_aprobacion, id_evaluacion, id_solicitud, version_solicitud, cod_credito, "
            "id_cliente, cliente_nombre, tipo_documento, numero_documento, producto, monto_aprobado, moneda, "
            "plazo_meses, tasa_tea, calendario_estado, calendario_politica, cuota_referencial, intereses_totales, "
            "total_pagar, estado, version, vigente_hasta, aprobada_por, aprobada_en) VALUES (:id, :ev, :s, :v, :cod, "
            ":cliente, :nombre, :tipo_doc, :doc, :producto, :monto, :moneda, :plazo, :tea, :cal_estado, :politica, "
            ":cuota_ref, :intereses, :total, 'VIGENTE', 1, :vigente, :por, :ahora)"),
            {"id": id_aprobacion, "ev": ev.id_evaluacion, "s": ev.id_solicitud, "v": ev.version_solicitud,
             "cod": cod_credito, "cliente": ev.id_cliente, "nombre": ev.cliente_nombre, "tipo_doc": ev.tipo_documento,
             "doc": ev.numero_documento, "producto": ev.producto, "monto": ev.monto_solicitado, "moneda": ev.moneda,
             "plazo": ev.plazo_meses, "tea": ev.tasa_tea, "cal_estado": calendario.estado,
             "politica": politica.version, "cuota_ref": calendario.cuota_referencial,
             "intereses": calendario.intereses_totales, "total": calendario.total_pagar, "vigente": vigente_hasta,
             "por": actor, "ahora": ahora})
        c.execute(text(
            "INSERT INTO eva_cuota (id_aprobacion, numero_cuota, fecha_vencimiento, saldo_inicial, amortizacion, "
            "interes, cuota_total, saldo_final) VALUES (:apr, :numero, :vence, :saldo_inicial, :amortizacion, "
            ":interes, :total, :saldo_final)"),
            [{"apr": id_aprobacion, "numero": q.numero_cuota, "vence": q.fecha_vencimiento,
              "saldo_inicial": q.saldo_inicial, "amortizacion": q.amortizacion, "interes": q.interes,
              "total": q.cuota_total, "saldo_final": q.saldo_final} for q in calendario.cuotas])
        _historial(c, "APROBACION_CREADA", actor, evaluacion=ev.id_evaluacion, aprobacion=id_aprobacion,
                   detalle={"codCredito": cod_credito, "vigenteHasta": iso(vigente_hasta)})

    # ------------------------------------------------------------------ CR-INT-04
    @staticmethod
    def _aprobacion(c: Connection, id_aprobacion: str, bloquear: bool = False):
        sql = "SELECT * FROM eva_aprobacion WHERE id_aprobacion = :id" + (" FOR UPDATE" if bloquear else "")
        fila = c.execute(text(sql), {"id": id_aprobacion}).first()
        if fila is None:
            raise ErrorEva(404, "APROBACION_NO_ENCONTRADA", "Evaluación no registra esa aprobación.")
        return fila

    @staticmethod
    def _completo(perfil: Perfil) -> bool:
        """El documento completo solo para Desembolso y para quien evalúa; los demás lo ven enmascarado."""
        return perfil.es_servicio or perfil.puede(EVALUAR, DECIDIR)

    @staticmethod
    def _estado_efectivo(a) -> str:
        if a.estado == "VIGENTE" and a.vigente_hasta <= utc_ahora():
            return "VENCIDA"
        return a.estado

    def _aprobacion_json(self, c: Connection, a, completo: bool, con_cuotas: bool = True) -> dict:
        calendario = {"origen": "SOL", "estado": a.calendario_estado, "politica": a.calendario_politica,
                      "cuotaReferencial": dinero(a.cuota_referencial), "interesesTotales": dinero(a.intereses_totales),
                      "totalPagar": dinero(a.total_pagar), "numeroCuotas": a.plazo_meses}
        if con_cuotas:
            filas = c.execute(text("SELECT * FROM eva_cuota WHERE id_aprobacion = :id ORDER BY numero_cuota"),
                              {"id": a.id_aprobacion}).all()
            calendario["cuotas"] = [_cuota_json(q.numero_cuota, q.fecha_vencimiento, q.saldo_inicial, q.amortizacion,
                                                q.interes, q.cuota_total, q.saldo_final) for q in filas]
        return {
            "idAprobacion": a.id_aprobacion, "version": a.version, "idEvaluacion": a.id_evaluacion,
            "idSolicitud": a.id_solicitud, "versionSolicitud": a.version_solicitud, "codCredito": a.cod_credito,
            "idCliente": a.id_cliente, "clienteNombre": a.cliente_nombre, "tipoDocumento": a.tipo_documento,
            "numeroDocumento": a.numero_documento if completo else enmascarar(a.numero_documento),
            "producto": a.producto, "montoAprobado": dinero(a.monto_aprobado), "moneda": a.moneda,
            "plazoMeses": a.plazo_meses, "tasaTea": tasa(a.tasa_tea), "estado": self._estado_efectivo(a),
            "vigenteHasta": iso(a.vigente_hasta), "aprobadaPor": a.aprobada_por, "aprobadaEn": iso(a.aprobada_en),
            "calendario": calendario,
            "desembolso": None if a.codigo_orden is None else {
                "codigoOrden": a.codigo_orden, "fechaDesembolso": iso(a.fecha_desembolso),
                "registradoPor": a.desembolso_registrado_por},
            "revocacion": None if a.revocada_por is None else {
                "motivo": a.motivo_revocacion, "revocadaPor": a.revocada_por, "fecha": iso(a.cambiado_en)},
        }

    def buscar_aprobaciones(self, perfil: Perfil, numero_documento: str | None, cod_credito: str | None,
                            estado: str | None = None) -> list[dict]:
        condiciones, parametros = [], {}
        if numero_documento:
            condiciones.append("numero_documento = :documento")
            parametros["documento"] = numero_documento.strip()
        if cod_credito:
            condiciones.append("cod_credito = :credito")
            parametros["credito"] = cod_credito.strip()
        if not condiciones:
            raise ErrorEva(422, "FILTRO_REQUERIDO", "Indica el número de documento o el código del crédito.")
        with self.engine.connect() as c:
            filas = c.execute(text(f"SELECT * FROM eva_aprobacion WHERE {' AND '.join(condiciones)} "
                                   "ORDER BY aprobada_en DESC LIMIT 20"), parametros).all()
            items = [self._aprobacion_json(c, a, self._completo(perfil), con_cuotas=False) for a in filas]
        return [a for a in items if not estado or a["estado"] == estado]

    def obtener_aprobacion(self, id_aprobacion: str, perfil: Perfil) -> dict:
        with self.engine.connect() as c:
            return self._aprobacion_json(c, self._aprobacion(c, id_aprobacion), self._completo(perfil))

    def registrar_desembolso(self, id_aprobacion: str, datos: DesembolsoIn, perfil: Perfil) -> dict:
        """Marca DESEMBOLSADA. Repetir con la misma orden devuelve lo mismo, sin otro cambio."""
        fecha = a_utc(datos.fechaDesembolso)
        with self.engine.begin() as c:
            a = self._aprobacion(c, id_aprobacion, bloquear=True)
            if a.estado == "DESEMBOLSADA":
                if a.codigo_orden == datos.codigoOrden:
                    return self._aprobacion_json(c, a, completo=True)
                raise ErrorEva(409, "APROBACION_YA_DESEMBOLSADA", f"La aprobación ya se usó en la orden {a.codigo_orden}.")
            if a.estado == "REVOCADA":
                raise ErrorEva(409, "APROBACION_REVOCADA", "Evaluación revocó esta aprobación.")
            _exigir_version(a.version, datos.version)
            if fecha > utc_ahora() + timedelta(minutes=5):
                raise ErrorEva(422, "FECHA_FUTURA", "La fecha del desembolso no puede ser futura.")
            if fecha > a.vigente_hasta:
                raise ErrorEva(409, "APROBACION_VENCIDA", "El desembolso es posterior al vencimiento de la aprobación.")
            c.execute(text(
                "UPDATE eva_aprobacion SET estado = 'DESEMBOLSADA', version = version + 1, codigo_orden = :orden, "
                "fecha_desembolso = :fecha, desembolso_registrado_por = :por, cambiado_en = :ahora "
                "WHERE id_aprobacion = :id AND version = :version"),
                {"orden": datos.codigoOrden, "fecha": fecha, "por": perfil.usuario, "ahora": utc_ahora(),
                 "id": id_aprobacion, "version": a.version})
            _historial(c, "APROBACION_DESEMBOLSADA", perfil.usuario, evaluacion=a.id_evaluacion,
                       aprobacion=id_aprobacion, detalle={"codigoOrden": datos.codigoOrden, "fechaDesembolso": iso(fecha)})
            return self._aprobacion_json(c, self._aprobacion(c, id_aprobacion), completo=True)

    def revocar(self, id_aprobacion: str, datos: RevocacionIn, perfil: Perfil) -> dict:
        with self.engine.begin() as c:
            a = self._aprobacion(c, id_aprobacion, bloquear=True)
            if a.estado != "VIGENTE":
                raise ErrorEva(409, "APROBACION_NO_VIGENTE", f"La aprobación está {a.estado} y ya no se puede revocar.")
            if a.vigente_hasta <= utc_ahora():
                raise ErrorEva(409, "APROBACION_VENCIDA", "La aprobación ya venció.")
            _exigir_version(a.version, datos.version)
            c.execute(text(
                "UPDATE eva_aprobacion SET estado = 'REVOCADA', version = version + 1, revocada_por = :por, "
                "motivo_revocacion = :motivo, cambiado_en = :ahora WHERE id_aprobacion = :id AND version = :version"),
                {"por": perfil.usuario, "motivo": datos.motivo, "ahora": utc_ahora(), "id": id_aprobacion,
                 "version": a.version})
            _historial(c, "APROBACION_REVOCADA", perfil.usuario, evaluacion=a.id_evaluacion, aprobacion=id_aprobacion,
                       detalle={"motivo": datos.motivo})
            return self._aprobacion_json(c, self._aprobacion(c, id_aprobacion), self._completo(perfil))

    # ------------------------------------------------------------------ Consultas del personal
    def _evaluacion_json(self, ev, completo: bool) -> dict:
        return {
            "idEvaluacion": ev.id_evaluacion, "idSolicitud": ev.id_solicitud,
            "versionSolicitud": ev.version_solicitud, "ronda": ev.ronda, "estado": ev.estado, "version": ev.version,
            "cliente": {"idCliente": ev.id_cliente, "nombre": ev.cliente_nombre, "tipoDocumento": ev.tipo_documento,
                        "numeroDocumento": ev.numero_documento if completo else enmascarar(ev.numero_documento)},
            "producto": ev.producto, "destino": ev.destino, "montoSolicitado": dinero(ev.monto_solicitado),
            "moneda": ev.moneda, "plazoMeses": ev.plazo_meses, "tasaTea": tasa(ev.tasa_tea),
            "motor": None if ev.resultado_motor is None else {
                "resultado": ev.resultado_motor, "score": ev.score, "limite": dinero(ev.limite),
                "ratio": None if ev.ratio is None else str(ev.ratio), "regla": ev.regla},
            "motivo": ev.motivo, "decididoPor": ev.decidido_por, "decididoEn": iso(ev.decidido_en),
            "recibidoEn": iso(ev.recibido_en), "actualizadoEn": iso(ev.actualizado_en),
        }

    def listar_evaluaciones(self, perfil: Perfil, estado: str | None = None, buscar: str | None = None,
                            limite: int = 50) -> dict:
        condiciones, parametros = [], {"limite": limite}
        if estado:
            condiciones.append("estado = :estado")
            parametros["estado"] = estado
        if buscar and buscar.strip():
            texto = buscar.strip()
            condiciones.append("(id_evaluacion = :texto OR id_solicitud = :texto OR numero_documento = :texto "
                               "OR cliente_nombre LIKE :parecido)")
            parametros.update(texto=texto, parecido=f"%{_escapar_like(texto)}%")
        donde = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        with self.engine.connect() as c:
            filas = c.execute(text(f"SELECT * FROM eva_evaluacion {donde} ORDER BY recibido_en DESC, id_evaluacion DESC "
                                   "LIMIT :limite"), parametros).all()
            conteos = {f.estado: f.n for f in c.execute(text("SELECT estado, COUNT(*) AS n FROM eva_evaluacion "
                                                             "GROUP BY estado")).all()}
        return {"items": [self._evaluacion_json(f, completo=False) for f in filas], "conteos": conteos}

    def detalle(self, id_evaluacion: str, perfil: Perfil) -> dict:
        completo = self._completo(perfil)
        with self.engine.connect() as c:
            ev = self._evaluacion(c, id_evaluacion)
            exp = c.execute(text("SELECT * FROM eva_expediente WHERE id_operacion = :op"), {"op": ev.id_operacion}).one()
            sobre = _leer_json(exp.contenido)
            expediente = sobre.get("expediente", {})
            condiciones = expediente.get("condiciones", {})
            calendario = expediente.get("calendario", {})
            situacion = c.execute(text("SELECT * FROM eva_situacion_financiera WHERE id_evaluacion = :id"),
                                  {"id": id_evaluacion}).first()
            aprobacion = c.execute(text("SELECT * FROM eva_aprobacion WHERE id_evaluacion = :id"),
                                   {"id": id_evaluacion}).first()
            envio = c.execute(text("SELECT * FROM eva_envio WHERE id_evaluacion = :id"), {"id": id_evaluacion}).first()
            historial = c.execute(text(
                "SELECT * FROM eva_historial WHERE id_evaluacion = :id OR id_aprobacion = :apr ORDER BY id"),
                {"id": id_evaluacion, "apr": aprobacion.id_aprobacion if aprobacion else ""}).all()
            datos = self._evaluacion_json(ev, completo)
            datos["expediente"] = {
                "idOperacion": exp.id_operacion, "acuse": ev.acuse, "versionContrato": exp.version_contrato,
                "actorEnvio": exp.actor_envio, "simulado": bool(exp.simulado), "recibidoEn": iso(exp.recibido_en),
                "fechaBase": condiciones.get("fecha_base"),
                "garantias": [{"tipo": g.get("tipo_garantia"), "descripcion": g.get("descripcion"),
                               "valorTasacion": g.get("valor_tasacion")} for g in condiciones.get("garantias") or []],
                "fiadores": len(expediente.get("fiadores") or []),
                "politica": {"version": expediente.get("politica", {}).get("version"),
                             "estadoAprobacion": expediente.get("politica", {}).get("estado_aprobacion")},
                "calendario": {
                    "estado": calendario.get("estado"), "cuotaReferencial": calendario.get("cuota_referencial"),
                    "interesesTotales": calendario.get("intereses_totales"),
                    "totalPagar": calendario.get("total_pagar"),
                    "cuotas": [{"numeroCuota": q.get("numero_cuota"), "fechaVencimiento": q.get("fecha_vencimiento"),
                                "amortizacion": q.get("amortizacion"), "interes": q.get("interes"),
                                "cuotaTotal": q.get("cuota_total"), "saldoFinal": q.get("saldo_final")}
                               for q in calendario.get("cuotas") or []],
                },
            }
            datos["situacionFinanciera"] = None if situacion is None else {
                "ingresoMensual": dinero(situacion.ingreso_mensual), "deudaMensual": dinero(situacion.deuda_mensual),
                "riesgo": situacion.riesgo, "verificada": bool(situacion.verificada),
                "registradoPor": situacion.registrado_por, "registradoEn": iso(situacion.registrado_en)}
            datos["aprobacion"] = None if aprobacion is None else self._aprobacion_json(c, aprobacion, completo)
            datos["envioSol"] = None if envio is None else self._envio_json(envio)
            datos["historial"] = [self._historial_json(h) for h in historial]
        return datos

    @staticmethod
    def _envio_json(e) -> dict:
        contenido = _leer_json(e.contenido)
        return {"idOperacion": e.id_operacion, "idEvaluacion": e.id_evaluacion, "interfaz": e.interfaz,
                "decision": contenido.get("decision"), "estado": e.estado, "intentos": e.intentos,
                "siguienteIntento": iso(e.siguiente_intento), "ultimoError": e.ultimo_error,
                "creadoEn": iso(e.creado_en), "entregadoEn": iso(e.entregado_en)}

    @staticmethod
    def _historial_json(h) -> dict:
        return {"id": h.id, "fecha": iso(h.fecha), "evento": h.evento, "actor": h.actor,
                "idEvaluacion": h.id_evaluacion, "idAprobacion": h.id_aprobacion,
                "idCorrelacion": h.id_correlacion, "detalle": _leer_json(h.detalle) if h.detalle else None}

    def listar_envios(self, estado: str | None = None, limite: int = 50) -> list[dict]:
        donde, parametros = ("WHERE estado = :estado", {"estado": estado}) if estado else ("", {})
        with self.engine.connect() as c:
            filas = c.execute(text(f"SELECT * FROM eva_envio {donde} ORDER BY creado_en DESC LIMIT :limite"),
                              {**parametros, "limite": limite}).all()
        return [self._envio_json(f) for f in filas]

    def reintentar_envio(self, id_operacion: str, perfil: Perfil) -> dict:
        with self.engine.begin() as c:
            envio = c.execute(text("SELECT * FROM eva_envio WHERE id_operacion = :id FOR UPDATE"),
                              {"id": id_operacion}).first()
            if envio is None:
                raise ErrorEva(404, "ENVIO_NO_ENCONTRADO", "No existe ese envío.")
            if envio.estado != "ERROR":
                raise ErrorEva(409, "ENVIO_NO_EN_ERROR", "Solo se reintenta un envío en ERROR.")
            c.execute(text("UPDATE eva_envio SET estado = 'PENDIENTE', siguiente_intento = :ahora, ultimo_error = NULL "
                           "WHERE id_operacion = :id"), {"ahora": utc_ahora(), "id": id_operacion})
            _historial(c, "ENVIO_REINTENTADO", perfil.usuario, evaluacion=envio.id_evaluacion,
                       detalle={"idOperacion": id_operacion})
            return self._envio_json(c.execute(text("SELECT * FROM eva_envio WHERE id_operacion = :id"),
                                              {"id": id_operacion}).one())

    def historial(self, limite: int = 100) -> list[dict]:
        with self.engine.connect() as c:
            filas = c.execute(text("SELECT * FROM eva_historial ORDER BY id DESC LIMIT :limite"),
                              {"limite": limite}).all()
        return [self._historial_json(h) for h in filas]
