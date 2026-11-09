# MySQL 8.4 DDL of the final (normalized) schema.  Called from modelo_bna.py.
# The relational design (schemas, keys, CHECKs, catalogs, seeds) is the same
# as on the main (PostgreSQL) branch; only the physical layer differs: the
# logical types below are mapped by my_type(), and gen() writes MySQL.
# Every design decision taken while writing the DDL is marked "DECISIÓN" both
# here and, where it matters to the reader of the script, in the SQL output.
import os
import re

from modelo_bna import E, R, STAGES, CATALOGS

FIN = STAGES["fin"]

# ---------------------------------------------------------------------------
# Logical schemas.  DECISIÓN: one PostgreSQL database with the logical schemas
# of the CORE architecture; each table lives in the schema of the module that
# owns the data.  Channels, limits and daily consumption belong to CORE because
# CORE owns the daily limits (topes diarios).
# ---------------------------------------------------------------------------
SCHEMAS = {
    "core": ["AGENCIA", "CUENTA_CONTABLE", "ASIENTO_CONTABLE", "DETALLE_ASIENTO", "MONEDA",
             "MODULO", "CANAL", "CANAL_VALIDACION", "LIMITE_CANAL", "CONSUMO_DIARIO", "TERMINAL"],
    "clientes": ["CLIENTE", "BIOMETRIA_CLIENTE", "CODIGO_VERIFICACION", "VALIDACION_IDENTIDAD",
                 "VERIFICACION_CAPTACION", "TIPO_DOCUMENTO", "TIPO_BIOMETRIA", "TIPO_CONTACTO",
                 "TIPO_VALIDACION", "ESTADO_CLIENTE"],
    "cuentas": ["CUENTA_AHORRO", "MOVIMIENTO", "TITULARIDAD", "TIPO_OPERACION", "REGIMEN_CUENTA",
                "ESTADO_CUENTA"],
    "tarjetas": ["TARJETA", "BIN_TARJETA", "TARJETA_CUENTA", "CREDENCIAL", "TIPO_CREDENCIAL",
                 "MATRIZ_TOKEN", "MATRIZ_COORDENADA", "TOKEN_PAGO", "PASARELA_PAGO",
                 "INTENTO_AUTENTICACION", "AUTORIZACION", "CODIGO_RESPUESTA",
                 "HISTORIAL_ESTADO_TARJETA", "ESTADO_TARJETA", "ORIGEN_CAMBIO", "EVENTO_SALIDA",
                 "TIPO_EVENTO_SALIDA"],
    "creditos": ["SOLICITUD_CREDITO", "HISTORIAL_ESTADO_SOLICITUD", "ESTADO_SOLICITUD", "GARANTIA",
                 "TIPO_GARANTIA", "FIADOR", "FIADOR_SOLICITUD", "CALENDARIO_PAGO",
                 "METODO_AMORTIZACION", "CUOTA", "ESTADO_CUOTA", "SITUACION_FINANCIERA",
                 "EVALUACION", "REGLA_EVALUACION", "RESULTADO_CREDITICIO", "ANALISTA",
                 "DECISION_ANALISTA", "ORDEN_DESEMBOLSO", "ESTADO_ORDEN", "VALIDACION_DESEMBOLSO",
                 "TIPO_VALIDACION_DESEMBOLSO", "EVENTO_ENTREGA", "SOLICITUD_REVERSION", "CREDITO",
                 "ESTADO_CREDITO", "PAGO", "APLICACION_PAGO", "MORA", "EVENTO_AUDITORIA",
                 "ENTIDAD_AUDITADA"],
}
SCHEMA_OF = {t: s for s, ts in SCHEMAS.items() for t in ts}


def q(rel):
    return "%s.%s" % (SCHEMA_OF[rel], rel.lower())


# ---------------------------------------------------------------------------
# Types.  DECISIÓN (convenciones):
#   * identificadores de entidades de negocio: UUID generado por defecto
#     (la arquitectura del CORE fija UUID); bitácoras de solo inserción:
#     BIGINT GENERATED ALWAYS AS IDENTITY (orden de inserción, volumen);
#   * códigos legibles de negocio y de catálogo: VARCHAR del largo de la fuente;
#   * importes: NUMERIC(15,2) (nunca FLOAT); tasas y ratios: NUMERIC con 4 o 2
#     decimales; fechas de negocio: DATE; marcas de tiempo: TIMESTAMPTZ (UTC);
#   * hashes SHA-256: CHAR(64); sales: CHAR(32); plantillas biométricas: BYTEA;
#   * mensajes y detalles semiestructurados: JSONB.
# ---------------------------------------------------------------------------
IDENTITY = {"EVENTO_AUDITORIA.id_evento", "INTENTO_AUTENTICACION.id_intento",
            "HISTORIAL_ESTADO_TARJETA.id_historial", "HISTORIAL_ESTADO_SOLICITUD.id_historial",
            "EVENTO_SALIDA.id_evento", "VALIDACION_IDENTIDAD.id_validacion",
            "EVENTO_ENTREGA.id_evento"}

TYPES = {
    # códigos de negocio
    "id_agencia": "VARCHAR(10)", "codigo_contable": "VARCHAR(20)", "codigo_padre": "VARCHAR(20)",
    "numero_asiento": "VARCHAR(20)", "cod_cliente": "VARCHAR(12)", "num_cuenta": "VARCHAR(20)",
    "cci": "CHAR(20)", "id_canal": "VARCHAR(5)", "id_terminal": "VARCHAR(30)",
    "cod_credito": "VARCHAR(20)", "codigo_orden": "VARCHAR(24)", "bin": "CHAR(6)",
    "ultimos4": "CHAR(4)", "pan_token": "VARCHAR(32)", "numero_serie": "VARCHAR(20)",
    "valor_token": "VARCHAR(64)", "codigo_rn": "VARCHAR(20)", "codigo_empleado": "VARCHAR(20)",
    "id_regla": "VARCHAR(10)", "id_analista": "VARCHAR(10)",
    "id_persona_externa": "VARCHAR(36)", "id_verificacion": "VARCHAR(36)",
    "id_verificacion_captacion": "VARCHAR(36)", "referencia_transaccion": "VARCHAR(40)",
    "referencia_evidencia": "VARCHAR(100)", "confirmacion_id": "VARCHAR(60)",
    "autorizacion_id": "VARCHAR(60)", "solicitante_id": "VARCHAR(40)",
    "usuario_preparacion": "VARCHAR(40)", "usuario_confirmacion": "VARCHAR(40)",
    "actor": "VARCHAR(40)", "version_contrato": "VARCHAR(10)", "version_esquema": "VARCHAR(10)",
    # catálogos
    "cod_moneda": "CHAR(3)", "moneda": "CHAR(3)", "id_modulo": "SMALLINT",
    "id_modulo_destino": "SMALLINT", "id_modulo_proveedor": "SMALLINT", "modulo_emisor": "SMALLINT",
    "cod_tipo_documento": "VARCHAR(10)", "tipo_documento": "VARCHAR(10)",
    "cod_tipo_biometria": "VARCHAR(10)", "tipo_biometria": "VARCHAR(10)",
    "cod_tipo_contacto": "VARCHAR(10)", "tipo_contacto": "VARCHAR(10)",
    "cod_tipo_validacion": "VARCHAR(15)", "cod_regimen": "VARCHAR(25)", "regimen": "VARCHAR(25)",
    "cod_estado": "VARCHAR(25)", "estado_cliente": "VARCHAR(25)", "estado_cuenta": "VARCHAR(25)",
    "estado_tarjeta": "VARCHAR(25)", "estado_nuevo": "VARCHAR(25)", "estado_solicitud": "VARCHAR(25)",
    "estado_orden": "VARCHAR(25)", "estado_credito": "VARCHAR(25)", "estado_cuota": "VARCHAR(25)",
    "tipo_operacion": "VARCHAR(25)", "tipo_credencial": "VARCHAR(15)",
    "cod_respuesta": "VARCHAR(4)", "codigo_respuesta": "VARCHAR(4)", "cod_origen": "VARCHAR(20)",
    "origen": "VARCHAR(20)", "cod_tipo_garantia": "VARCHAR(20)", "tipo_garantia": "VARCHAR(20)",
    "cod_metodo": "VARCHAR(20)", "metodo_amortizacion": "VARCHAR(20)",
    "cod_resultado": "VARCHAR(12)", "accion": "VARCHAR(12)", "decision": "VARCHAR(12)",
    "id_pasarela": "VARCHAR(20)", "proveedor_pasarela": "VARCHAR(20)",
    # importes, tasas y contadores
    "importe": "NUMERIC(15,2)", "monto": "NUMERIC(15,2)", "monto_pago": "NUMERIC(15,2)",
    "monto_aplicado": "NUMERIC(15,2)", "monto_calculado": "NUMERIC(15,2)",
    "monto_solicitado": "NUMERIC(15,2)", "monto_maximo_diario": "NUMERIC(15,2)",
    "monto_acumulado": "NUMERIC(15,2)", "saldo_contable": "NUMERIC(15,2)",
    "saldo_disponible": "NUMERIC(15,2)", "capital": "NUMERIC(15,2)", "interes": "NUMERIC(15,2)",
    "otros_conceptos": "NUMERIC(15,2)", "saldo_capital": "NUMERIC(15,2)",
    "saldo_pendiente": "NUMERIC(15,2)", "valor_referencial": "NUMERIC(15,2)",
    "limite_aprobado": "NUMERIC(15,2)", "ingreso_mensual": "NUMERIC(15,2)",
    "deuda_reportada": "NUMERIC(15,2)", "tasa_aplicada": "NUMERIC(7,4)",
    "score_calculado": "NUMERIC(6,2)", "ratio_min": "NUMERIC(7,2)", "ratio_max": "NUMERIC(7,2)",
    "umbral_similitud": "NUMERIC(5,4)", "intentos_fallidos": "SMALLINT", "intentos": "SMALLINT",
    "max_intentos": "SMALLINT", "vigencia_minutos": "SMALLINT", "longitud": "SMALLINT",
    "longitud_min": "SMALLINT", "longitud_max": "SMALLINT", "decimales": "SMALLINT",
    "min_titulares": "SMALLINT", "plazo_meses": "SMALLINT", "numero_cuota": "SMALLINT",
    "nro_linea": "SMALLINT", "ronda": "SMALLINT", "version": "SMALLINT",
    "version_solicitud": "SMALLINT", "version_registro": "INTEGER", "columna": "SMALLINT",
    "coord_columna": "SMALLINT", "fila": "CHAR(1)", "coord_fila": "CHAR(1)",
    # fechas
    "fecha_vencimiento": "DATE", "fecha_emision": "DATE", "fecha_corte": "DATE",
    "fecha_contable": "DATE", "fecha_valor": "DATE", "fecha_expiracion": "TIMESTAMPTZ",
    # seguridad y datos opacos
    "hash_credencial": "CHAR(64)", "hash_valor": "CHAR(64)", "codigo_otp": "CHAR(64)",
    "request_hash": "CHAR(64)", "sal": "CHAR(32)", "datos_biometricos": "BYTEA",
    "carga_json": "JSONB", "payload": "JSONB", "detalle": "JSONB", "ip_origen": "INET",
    # textos
    "nombre": "VARCHAR(100)", "nombres": "VARCHAR(100)", "apellido_paterno": "VARCHAR(100)",
    "apellido_materno": "VARCHAR(100)", "correo": "VARCHAR(150)", "celular": "CHAR(9)",
    "numero_documento": "VARCHAR(12)", "calle": "VARCHAR(120)", "distrito": "VARCHAR(60)",
    "ciudad": "VARCHAR(60)", "glosa": "VARCHAR(200)", "descripcion": "VARCHAR(255)",
    "motivo": "VARCHAR(255)", "motivo_rechazo": "VARCHAR(255)", "comentario": "VARCHAR(500)",
    "condiciones_propuestas": "VARCHAR(300)", "observaciones": "VARCHAR(500)",
    "ultimo_error": "VARCHAR(255)", "endpoint": "VARCHAR(80)", "simbolo": "VARCHAR(4)",
    "regla_tope": "VARCHAR(20)", "tipo_integracion": "VARCHAR(30)",
    "resultado_verificacion": "VARCHAR(20)",
}
# Overrides by relation.attribute
TYPES_REL = {
    "VALIDACION_DESEMBOLSO.detalle": "VARCHAR(255)",
    "TIPO_OPERACION.naturaleza": "CHAR(1)",
    "TIPO_VALIDACION_DESEMBOLSO.tipo_validacion": "VARCHAR(15)",
    "VALIDACION_DESEMBOLSO.tipo_validacion": "VARCHAR(15)",
    "VALIDACION_IDENTIDAD.tipo_validacion": "VARCHAR(15)",
    "CANAL_VALIDACION.tipo_validacion": "VARCHAR(15)",
    "TIPO_EVENTO_SALIDA.tipo_evento": "VARCHAR(30)", "EVENTO_SALIDA.tipo_evento": "VARCHAR(30)",
    "EVENTO_ENTREGA.tipo_evento": "VARCHAR(60)",
    "EVENTO_AUDITORIA.accion": "VARCHAR(60)", "EVENTO_AUDITORIA.resultado": "VARCHAR(40)",
    "MODULO.nombre": "VARCHAR(40)", "CANAL.nombre": "VARCHAR(40)",
    "BIN_TARJETA.descripcion": "VARCHAR(100)",
    # DECISIÓN: id_entidad guarda UUID (orden, pago, calendario) o códigos
    #   (crédito), por eso es texto y no UUID.
    "ENTIDAD_AUDITADA.id_entidad": "VARCHAR(36)", "EVENTO_AUDITORIA.id_entidad": "VARCHAR(36)",
}


def col_type(rel, a):
    key = "%s.%s" % (rel, a["name"])
    if key in IDENTITY:
        return "BIGINT GENERATED ALWAYS AS IDENTITY"
    if key in TYPES_REL:
        return TYPES_REL[key]
    n = a["name"]
    if n in TYPES:
        return TYPES[n]
    if n.startswith(("id_", "uuid_")):
        return "UUID"
    if n.startswith(("es_", "permite_", "habilitad", "puede_")) or n in (
            "activo", "estado_activo", "firma_conjunta", "condicion_pago_doble"):
        return "BOOLEAN"
    if n.startswith(("fecha_", "creado_en", "actualizado_en", "vence_en", "siguiente_intento")):
        return "TIMESTAMPTZ"
    if n in ("correlation_id", "uuid_correlacion", "idempotency_key"):
        return "UUID"
    if n.startswith(("estado_", "tipo_", "resultado", "naturaleza", "nivel_")):
        return "VARCHAR(25)"
    raise KeyError("sin tipo: " + key)


# Base attributes that admit NULL (FK nullability comes from participation).
NULLABLE = {
    "CLIENTE.apellido_materno", "GARANTIA.descripcion", "HISTORIAL_ESTADO_TARJETA.motivo",
    "HISTORIAL_ESTADO_SOLICITUD.motivo", "INTENTO_AUTENTICACION.motivo_rechazo",
    "AUTORIZACION.motivo_rechazo", "AUTORIZACION.codigo_respuesta", "AUTORIZACION.nivel_riesgo",
    "ORDEN_DESEMBOLSO.motivo_rechazo", "ORDEN_DESEMBOLSO.usuario_confirmacion",
    "EVALUACION.condiciones_propuestas", "EVALUACION.observaciones",
    "VALIDACION_DESEMBOLSO.detalle", "VALIDACION_DESEMBOLSO.vence_en",
    "EVENTO_ENTREGA.siguiente_intento", "EVENTO_ENTREGA.confirmacion_id",
    "EVENTO_ENTREGA.ultimo_error", "SOLICITUD_REVERSION.autorizacion_id",
    "REGLA_EVALUACION.ratio_min", "REGLA_EVALUACION.ratio_max",
    "LIMITE_CANAL.monto_maximo_diario", "EVENTO_SALIDA.fecha_envio",
    "EVENTO_AUDITORIA.ip_origen", "EVENTO_AUDITORIA.detalle", "EVENTO_AUDITORIA.resultado",
    "INTENTO_AUTENTICACION.uuid_correlacion", "TIPO_CREDENCIAL.longitud",
    "TIPO_BIOMETRIA.umbral_similitud", "CUENTA_CONTABLE.codigo_padre",
}

DEFAULTS = {
    "saldo_contable": "0", "saldo_disponible": "0", "monto_acumulado": "0",
    "intentos_fallidos": "0", "intentos": "0", "otros_conceptos": "0",
    "version_solicitud": "1", "version_registro": "0", "condicion_pago_doble": "FALSE",
    "activo": "TRUE", "estado_activo": "TRUE", "habilitado": "TRUE",
    "es_principal": "FALSE", "habilitada_atm": "TRUE",
    "creado_en": "now()", "actualizado_en": "now()", "fecha_hora": "now()",
    "fecha_registro": "now()", "fecha_evento": "now()", "fecha_creacion": "now()",
    "fecha_calculo": "now()", "fecha_generacion": "now()", "fecha_evaluacion": "now()",
    "fecha_decision": "now()", "fecha_consulta": "now()", "fecha_apertura": "now()",
    "fecha_vinculacion": "now()", "fecha_actualizacion": "now()",
    "fecha_ultimo_cambio": "now()", "fecha_verificacion": "now()",
}

# Closed domains kept as CHECK (see the catalog section of the report).
ENUMS = {
    "AGENCIA.estado_agencia": ["ACTIVA", "INACTIVA"],
    "CUENTA_CONTABLE.naturaleza": ["DEUDORA", "ACREEDORA"],
    "DETALLE_ASIENTO.tipo_partida": ["DEBE", "HABER"],
    "TIPO_OPERACION.naturaleza": ["D", "C", "N"],
    "CODIGO_VERIFICACION.estado_codigo": ["PENDIENTE", "VALIDADO", "EXPIRADO", "BLOQUEADO"],
    "VALIDACION_IDENTIDAD.resultado": ["APROBADO", "RECHAZADO"],
    "VERIFICACION_CAPTACION.estado_habilitante": ["HABILITADO", "OBSERVADO"],
    "MOVIMIENTO.estado_transaccion": ["APROBADO", "EXTORNADO"],
    "BIN_TARJETA.tipo_tarjeta": ["FISICA", "VIRTUAL"],
    "MATRIZ_TOKEN.tipo_matriz": ["FISICA", "VIRTUAL"],
    "MATRIZ_TOKEN.estado_matriz": ["ACTIVA", "BLOQUEADA", "REEMPLAZADA"],
    "TOKEN_PAGO.estado_token": ["ACTIVO", "SUSPENDIDO", "REVOCADO"],
    "INTENTO_AUTENTICACION.resultado": ["EXITOSO", "FALLIDO"],
    "AUTORIZACION.estado_autorizacion": ["INICIADA", "AUTORIZADA", "RECHAZADA", "DISPENSADA",
                                         "EXTORNADA", "PENDIENTE_REVERSION"],
    "AUTORIZACION.nivel_riesgo": ["BAJO", "MEDIO", "ALTO"],
    "EVENTO_SALIDA.estado_envio": ["PENDIENTE", "ENVIADO", "ERROR"],
    "GARANTIA.estado_garantia": ["REGISTRADA", "EN_TASACION", "CONSTITUIDA", "LEVANTADA"],
    "CALENDARIO_PAGO.tipo_calendario": ["PRELIMINAR", "OFICIAL"],
    "CALENDARIO_PAGO.estado_calendario": ["VIGENTE", "HISTORICO", "DESCARTADO"],
    "VALIDACION_DESEMBOLSO.resultado": ["APROBADA", "RECHAZADA"],
    "EVENTO_ENTREGA.tipo_evento": ["desembolso.confirmado", "desembolso.revertido"],
    "EVENTO_ENTREGA.estado_entrega": ["PENDIENTE", "ENVIADO", "CONFIRMADO", "FALLIDO"],
    "SOLICITUD_REVERSION.estado_reversion": ["SOLICITADA", "AUTORIZADA", "CONFIRMADA", "RECHAZADA"],
    "PAGO.estado_confirmacion": ["PENDIENTE", "CONFIRMADO", "RECHAZADO"],
    "ENTIDAD_AUDITADA.tipo_entidad": ["ORDEN", "CREDITO", "PAGO", "CUOTA"],
}

CHECKS = {
    "CLIENTE": ["celular ~ '^9[0-9]{8}$'"],
    "CUENTA_AHORRO": ["saldo_disponible <= saldo_contable", "saldo_disponible >= 0"],
    "MOVIMIENTO": ["monto > 0"],
    "DETALLE_ASIENTO": ["importe > 0"],
    "CONSUMO_DIARIO": ["monto_acumulado >= 0"],
    "LIMITE_CANAL": ["monto_maximo_diario IS NULL OR monto_maximo_diario > 0"],
    "TARJETA": ["fecha_vencimiento > fecha_emision", "ultimos4 ~ '^[0-9]{4}$'"],
    "BIN_TARJETA": ["bin ~ '^[0-9]{6}$'"],
    "CREDENCIAL": ["tipo_credencial IN ('PIN_ATM', 'CLAVE_WEB')",
                   "intentos_fallidos BETWEEN 0 AND 3"],
    "MATRIZ_TOKEN": ["intentos_fallidos BETWEEN 0 AND 3"],
    "MATRIZ_COORDENADA": ["fila BETWEEN 'A' AND 'G'", "columna BETWEEN 0 AND 9"],
    "INTENTO_AUTENTICACION": [
        "coord_fila IS NULL OR coord_fila BETWEEN 'A' AND 'G'",
        "coord_columna IS NULL OR coord_columna BETWEEN 0 AND 9",
        "(coord_fila IS NULL) = (coord_columna IS NULL)",
        "(coord_fila IS NOT NULL) = (tipo_credencial = 'TOKEN_MATRIZ')",
        "num_nonnulls(id_terminal, id_canal) = 1"],
    # DECISIÓN: la autorización y su movimiento comparten el identificador de
    #   la operación (Tarjetas, RN-BUS-002); así el movimiento sabe que el tope
    #   y el saldo ya se comprometieron al autorizar.
    "AUTORIZACION": ["monto >= 0", "num_nonnulls(id_terminal, id_canal) = 1",
                     "uuid_transaccion IS NULL OR uuid_transaccion = uuid_autorizacion"],
    "SOLICITUD_CREDITO": ["monto_solicitado > 0", "plazo_meses > 0"],
    "GARANTIA": ["valor_referencial > 0"],
    "CALENDARIO_PAGO": ["tasa_aplicada >= 0"],
    "CUOTA": ["numero_cuota > 0", "capital >= 0", "interes >= 0", "otros_conceptos >= 0",
              "saldo_pendiente >= 0"],
    "EVALUACION": ["limite_aprobado >= 0"],
    "REGLA_EVALUACION": ["ratio_min IS NULL OR ratio_max IS NULL OR ratio_min < ratio_max"],
    "ORDEN_DESEMBOLSO": ["importe > 0"],
    "PAGO": ["monto_pago > 0"],
    "APLICACION_PAGO": ["monto_aplicado > 0"],
    "MORA": ["monto_calculado >= 0"],
    "EVENTO_AUDITORIA": ["numero_cuota IS NULL OR id_entidad IS NOT NULL"],
    "TIPO_DOCUMENTO": ["longitud_min <= longitud_max"],
    "REGIMEN_CUENTA": ["min_titulares >= 1"],
    "TIPO_CONTACTO": ["vigencia_minutos > 0", "max_intentos > 0"],
}

# Candidate keys besides the PK that do not come from UK attributes or 1:1 FKs.
EXTRA_UNIQUE = {
    "CALENDARIO_PAGO": [("id_solicitud", "version")],
    "EVALUACION": [("id_solicitud", "ronda")],
    "MORA": [("id_calendario", "numero_cuota", "fecha_calculo")],
    "MODULO": [("nombre",)],
    "TIPO_VALIDACION": [("endpoint",)],
    "CLIENTE": [("id_verificacion_captacion",)],
    "FIADOR_SOLICITUD": [("id_verificacion",)],
    "REGLA_EVALUACION": [("ratio_min", "ratio_max")],
}

# Partial unique indexes (business rules expressible as indexes).
PARTIAL = [
    ("ux_matriz_activa", "MATRIZ_TOKEN", "id_tarjeta", "estado_matriz = 'ACTIVA'",
     "una sola matriz ACTIVA por tarjeta (RN-TAR-002); reemplaza tarjeta_si_activa"),
    ("ux_orden_confirmada", "ORDEN_DESEMBOLSO", "id_evaluacion", "estado_orden = 'CONFIRMADA'",
     "una sola orden CONFIRMADA por aprobación; reemplaza credito_confirmado"),
    ("ux_tarjeta_principal", "TARJETA_CUENTA", "id_tarjeta", "es_principal",
     "una sola cuenta principal por tarjeta"),
    ("ux_biometria_vigente", "BIOMETRIA_CLIENTE", "cod_cliente, tipo_biometria", "estado_activo",
     "una sola plantilla vigente por cliente y tipo"),
]

# Composite FKs that are not relationships of the MER but rules of the sources.
EXTRA_FK = [
    ("AUTORIZACION", ("id_tarjeta", "num_cuenta"), "TARJETA_CUENTA",
     "la cuenta afectada debe estar vinculada a la tarjeta (trigger de TARJETAS)"),
]

# Rules that need data of other tables: implemented with triggers (listed).
# Query indexes for the ported views and the documented queries.  An FK
# index whose columns are a prefix of one of these is not created twice.
QUERY_INDEXES = [
    ("ix_movimiento_cuenta_fecha", "MOVIMIENTO", ("num_cuenta", "fecha_hora"), None,
     "estado de cuenta: movimientos de una cuenta por fecha"),
    ("ix_autorizacion_tarjeta_fecha", "AUTORIZACION", ("id_tarjeta", "fecha_hora"), None,
     "consumo diario por tarjeta (v_consumo_diario, Tarjetas)"),
    ("ix_intento_tarjeta_fecha", "INTENTO_AUTENTICACION", ("id_tarjeta", "fecha_hora"), None,
     "intentos de una tarjeta por fecha (Tarjetas, C08)"),
    ("ix_historial_tarjeta_fecha", "HISTORIAL_ESTADO_TARJETA", ("id_tarjeta", "fecha_hora"), None,
     "historial de una tarjeta (Tarjetas, C10)"),
    ("ix_orden_estado_fecha", "ORDEN_DESEMBOLSO", ("estado_orden", "actualizado_en"), None,
     "recuperación de órdenes inciertas por estado y fecha (Desembolso, idx_orden_estado)"),
    ("ix_evento_salida_pendiente", "EVENTO_SALIDA", ("fecha_registro",), "estado_envio = 'PENDIENTE'",
     "bandeja de salida hacia SEGURIDAD: solo los eventos por enviar"),
    ("ix_evento_entrega_pendiente", "EVENTO_ENTREGA", ("siguiente_intento",),
     "estado_entrega IN ('PENDIENTE', 'ENVIADO', 'FALLIDO')",
     "búsqueda de entregas pendientes hacia Cobranza (Desembolso)"),
    ("ix_evento_auditoria_correlacion", "EVENTO_AUDITORIA", ("correlation_id",), None,
     "reconstrucción de una operación completa desde la traza (Desembolso, idx_auditoria_correlation)"),
]

# Triggers, procedures, functions, views and the event: hand-written MySQL
# stored programs inlined in the DDL.
PROGRAMMING = os.path.join(os.path.dirname(os.path.abspath(__file__)), "programacion_bna.sql")


def uniques(rel):
    out = []
    cols = {a["name"] for a in FIN[rel]}
    if rel in E:
        for a in E[rel]["attrs"]:
            if a["key"] == "UK":
                names = [c for c, _ in a["comp"]] if a["comp"] else [a["name"]]
                if all(n in cols for n in names):
                    out.append(tuple(names))
    for r in R:
        if r["card"] == "1:1" and r["fk"] and r["fk"][0] == rel:
            names = tuple(fa for fa, _ in r["fk"][1])
            if all(n in cols for n in names):
                out.append(names)
    out += EXTRA_UNIQUE.get(rel, [])
    return out


def pk(rel):
    return [a["name"] for a in FIN[rel] if a["pk"]]


def fks(rel):
    """[(cols, target)] grouped as in the relational notation."""
    out, seen = [], set()
    for a in FIN[rel]:
        if not a["fk"]:
            continue
        if a["grp"]:
            if a["grp"] in seen:
                continue
            seen.add(a["grp"])
            out.append((tuple(x["name"] for x in FIN[rel] if x["grp"] == a["grp"]), a["fk"]))
        else:
            out.append(((a["name"],), a["fk"]))
    return out


def comment_text(rel):
    if rel in E:
        return re.sub(r"`", "", E[rel]["desc"])
    for t, cols, uses, crit, note in CATALOGS:
        if t == rel:
            return "Catálogo. " + re.sub(r"`", "", note)
    return {
        "TITULARIDAD": "Titulares de cada cuenta (relación N:M ES_TITULAR).",
        "TARJETA_CUENTA": "Cuentas que opera cada tarjeta (relación N:M VINCULA).",
        "FIADOR_SOLICITUD": "Fiadores que respaldan cada solicitud (relación N:M RESPALDA).",
        "APLICACION_PAGO": "Reparto de cada pago entre cuotas (relación N:M APLICA).",
        "CANAL_VALIDACION": "Credenciales que exige cada canal (atributo multivaluado).",
        "TIPO_CREDENCIAL": "Tipos de credencial y su longitud (2FN).",
        "VERIFICACION_CAPTACION": "Verificación de captación del cliente (3FN).",
        "TIPO_OPERACION": "Tipos de operación y su naturaleza D/C/N (3FN).",
        "BIN_TARJETA": "BIN emitidos por el BNA y el tipo de tarjeta que identifican (3FN).",
        "TERMINAL": "Terminales físicas (cajeros, agentes, ventanillas) y su canal (3FN).",
        "TIPO_VALIDACION_DESEMBOLSO": "Tipos de validación previa al desembolso y su proveedor (3FN).",
        "TIPO_EVENTO_SALIDA": "Tipos de evento hacia otros módulos y su destino (3FN).",
        "ENTIDAD_AUDITADA": "Registros auditables y su tipo (3FN).",
    }[rel]


def sql_str(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Seed data: only values documented by the sources (CORE loads parameters).
# ---------------------------------------------------------------------------
SEEDS = [
    ("MONEDA", ["cod_moneda", "nombre", "simbolo", "decimales"],
     [("PEN", "Sol", "S/", 2), ("USD", "Dólar estadounidense", "US$", 2)]),
    ("MODULO", ["id_modulo", "nombre"],
     [(1, "CORE"), (2, "CLIENTES"), (3, "CUENTAS"), (8, "BUS DE SERVICIOS"), (9, "SEGURIDAD"),
      (11, "SOLICITUD DE CREDITO"), (12, "EVALUACION"), (13, "DESEMBOLSO"), (14, "COBRANZA")]),
    ("TIPO_DOCUMENTO", ["cod_tipo_documento", "descripcion", "longitud_min", "longitud_max", "es_alfanumerico"],
     [("DNI", "Documento Nacional de Identidad", 8, 8, False),
      ("CE", "Carné de extranjería", 9, 12, True),
      ("PTP", "Permiso Temporal de Permanencia", 9, 9, False),
      ("PASAPORTE", "Pasaporte", 6, 12, True)]),
    ("TIPO_BIOMETRIA", ["cod_tipo_biometria", "descripcion", "umbral_similitud"],
     [("DACTILAR", "Huella dactilar", None), ("FACIAL", "Reconocimiento facial", None)]),
    ("TIPO_CONTACTO", ["cod_tipo_contacto", "descripcion", "vigencia_minutos", "max_intentos"],
     [("SMS", "Código enviado al celular", 5, 3), ("CORREO", "Código enviado al correo", 10, 3)]),
    ("TIPO_VALIDACION", ["cod_tipo_validacion", "descripcion", "endpoint"],
     [("DOCUMENTO", "Validación de documento", "/api/v1/kyc/validar-documento"),
      ("HUELLA", "Verificación dactilar", "/api/v1/kyc/validar-huella"),
      ("FACIAL", "Verificación facial", "/api/v1/kyc/validar-facial"),
      ("CELULAR", "Confirmación de celular", "/api/v1/kyc/celular/verificar-codigo"),
      ("CORREO", "Confirmación de correo", "/api/v1/kyc/correo/verificar-codigo")]),
    ("ESTADO_CLIENTE", ["cod_estado", "descripcion", "permite_operar"],
     [("ACTIVO", "Cliente activo", True), ("OBSERVADO", "Cliente observado", True),
      ("BLOQUEADO", "Cliente bloqueado", False), ("SUSPENDIDO", "Cliente suspendido", False),
      ("BAJA", "Cliente dado de baja", False)]),
    ("REGIMEN_CUENTA", ["cod_regimen", "descripcion", "min_titulares", "firma_conjunta"],
     [("INDIVIDUAL", "Un solo titular", 1, False),
      ("MANCOMUNADA_INDISTINTA", "Mancomunada (o): firma cualquier titular", 2, False),
      ("MANCOMUNADA_CONJUNTA", "Mancomunada (y): firman todos los titulares", 2, True)]),
    ("ESTADO_CUENTA", ["cod_estado", "descripcion", "permite_debito", "permite_credito"],
     [("ACTIVA", "Cuenta activa", True, True), ("BLOQUEADA", "Cuenta bloqueada", False, False),
      ("BLOQUEADA_PREVENTIVA", "Bloqueo por seguridad", False, True),
      ("CANCELADA", "Cuenta cancelada", False, False)]),
    ("TIPO_OPERACION", ["tipo_operacion", "naturaleza"],
     [("RETIRO", "D"), ("TRANSFERENCIA_ENVIADA", "D"), ("PAGO", "D"), ("FONDEO_BILLETERA", "D"),
      ("DEBITO_CUOTA", "D"), ("DEPOSITO", "C"), ("TRANSFERENCIA_RECIBIDA", "C"),
      ("DESEMBOLSO", "C"), ("ABONO_INTERES", "C"), ("EXTORNO", "C"), ("CONSULTA_SALDO", "N")]),
    ("CANAL", ["id_canal", "nombre", "es_presencial", "tipo_integracion", "activo", "regla_tope"],
     [("ATM", "Cajero automático", True, "BUS", True, "RN-TOP-001"),
      ("AGE", "Agente BNA", True, "BUS", True, "RN-TOP-001"),
      ("VEN", "Ventanilla", True, "BUS", True, "RN-TOP-001"),
      ("HB", "Home Banking", False, "BUS", True, "RN-TOP-001"),
      ("BD", "Billetera Digital", False, "BUS", True, "RN-BD-002")]),
    ("LIMITE_CANAL", ["id_canal", "moneda", "monto_maximo_diario", "habilitado"],
     [("ATM", "PEN", 1500, True), ("ATM", "USD", 500, True), ("VEN", "PEN", None, True),
      ("VEN", "USD", None, True), ("HB", "PEN", 10000, True), ("BD", "PEN", 500, True),
      ("BD", "USD", None, False)]),
    ("TIPO_CREDENCIAL", ["tipo_credencial", "longitud"],
     [("PIN_ATM", 4), ("CLAVE_WEB", 6), ("TOKEN_MATRIZ", None), ("BIOMETRIA", None),
      ("TOKEN_PAGO", None)]),
    ("CANAL_VALIDACION", ["id_canal", "tipo_validacion"],
     [("ATM", "PIN_ATM"), ("HB", "CLAVE_WEB"), ("HB", "TOKEN_MATRIZ"), ("BD", "TOKEN_PAGO"),
      ("VEN", "BIOMETRIA"), ("AGE", "BIOMETRIA")]),
    ("ESTADO_TARJETA", ["cod_estado", "descripcion", "es_operativa", "es_final"],
     [("PENDIENTE_ACTIVACION", "Emitida, sin activar", False, False),
      ("ACTIVA", "Operativa", True, False), ("BLOQUEADA", "Bloqueada", False, False),
      ("RETENIDA", "Retenida por el cajero", False, False), ("VENCIDA", "Vencida", False, False),
      ("CANCELADA", "Cancelada", False, True)]),
    ("ORIGEN_CAMBIO", ["cod_origen", "descripcion", "puede_desbloquear"],
     [("CLIENTE", "El propio cliente", False), ("SISTEMA", "Proceso automático", False),
      ("SEGURIDAD", "Módulo de seguridad", True), ("OPERADOR", "Operador de ventanilla", True),
      ("MODULO_CLIENTES", "Módulo de clientes", False)]),
    ("CODIGO_RESPUESTA", ["cod_respuesta", "descripcion", "es_aprobacion"],
     [("00", "Aprobada", True), ("54", "Tarjeta vencida", False), ("EXT", "Extorno", False)]),
    ("TIPO_EVENTO_SALIDA", ["tipo_evento", "descripcion", "id_modulo_destino"],
     [("EMISION_TARJETA", "Emisión de tarjeta", 9),
      ("CAMBIO_ESTADO_TARJETA", "Cambio de estado de tarjeta", 9),
      ("BLOQUEO_POR_INTENTOS", "Bloqueo por intentos fallidos", 9)]),
    ("ESTADO_SOLICITUD", ["cod_estado", "descripcion", "es_final"],
     [("REGISTRADA", "Registrada", False), ("EN_EVALUACION", "En evaluación", False),
      ("APROBADA", "Aprobada", False), ("RECHAZADA", "Rechazada", True),
      ("DESEMBOLSADA", "Desembolsada", True)]),
    ("TIPO_GARANTIA", ["cod_tipo_garantia", "descripcion"],
     [("HIPOTECARIA", "Hipoteca"), ("MOBILIARIA", "Garantía mobiliaria"), ("PRENDARIA", "Prenda")]),
    ("METODO_AMORTIZACION", ["cod_metodo", "descripcion"],
     [("FRANCES", "Cuota constante"), ("ALEMAN", "Amortización constante"),
      ("AMERICANO", "Capital al vencimiento")]),
    ("ESTADO_CUOTA", ["cod_estado", "descripcion"],
     [("PENDIENTE", "Pendiente"), ("PARCIAL", "Pagada parcialmente"), ("PAGADA", "Pagada"),
      ("VENCIDA", "Vencida")]),
    ("ESTADO_CREDITO", ["cod_estado", "descripcion"],
     [("AL_DIA", "Al día"), ("EN_MORA", "En mora"), ("CANCELADO", "Cancelado")]),
    ("RESULTADO_CREDITICIO", ["cod_resultado", "descripcion"],
     [("APROBADO", "Aprobado"), ("OBSERVADO", "Derivado a revisión manual"),
      ("RECHAZADO", "Rechazado")]),
    ("REGLA_EVALUACION", ["id_regla", "codigo_rn", "descripcion", "ratio_min", "ratio_max", "accion"],
     [("R-A", "RN-EVA-002-P.a", "Ratio monto/límite hasta 80 %", None, 80, "APROBADO"),
      ("R-B", "RN-EVA-002-P.b", "Ratio monto/límite entre 80 % y 100 %", 80, 100, "OBSERVADO"),
      ("R-C", "RN-EVA-002-P.c", "Ratio monto/límite mayor que 100 %", 100, None, "RECHAZADO")]),
    ("ESTADO_ORDEN", ["cod_estado", "descripcion", "es_final"],
     [("PREPARADA", "Preparada", False), ("VALIDADA", "Validada", False),
      ("EN_PROCESO", "Enviada al CORE", False), ("POR_VERIFICAR", "Respuesta del CORE perdida", False),
      ("CONFIRMADA", "Confirmada", False), ("RECHAZADA", "Rechazada", True),
      ("REVERTIDA", "Revertida", True)]),
    ("TIPO_VALIDACION_DESEMBOLSO", ["tipo_validacion", "descripcion", "id_modulo_proveedor"],
     [("IDENTIDAD", "Identidad del titular", 2), ("CUENTA", "Cuenta destino elegible", 3),
      ("AUTORIZACION", "Autorización de la operación", 9), ("ANTIFRAUDE", "Control antifraude", 9)]),
]


# ---------------------------------------------------------------------------
# Physical layer (MySQL 8.4).  DECISIÓN (correspondencia de tipos):
#   * UUID -> BINARY(16) en el orden de bytes del texto (UUID_TO_BIN sin
#     intercambio), con un CHECK de versión y variante: sin él, un texto corto
#     como 'c2' se rellena con ceros y se guarda. El valor por omisión es un
#     UUID versión 4 hecho con RANDOM_BYTES (no se porta fn_uuid_v7, que tenía
#     una falla en la línea base);
#   * TIMESTAMPTZ -> DATETIME(6) en UTC (TIMESTAMP termina en 2038); now() ->
#     UTC_TIMESTAMP(6), que no depende de la zona de la sesión;
#   * BOOLEAN -> TINYINT(1) con CHECK (0, 1): el BOOLEAN de MySQL acepta 5;
#   * INET -> VARCHAR(45) con CHECK IS_IPV4/IS_IPV6; JSONB -> JSON;
#     BYTEA -> LONGBLOB; NUMERIC -> DECIMAL;
#   * IDENTITY -> AUTO_INCREMENT, más un trigger que rechaza un valor explícito
#     (GENERATED ALWAYS lo rechaza en PostgreSQL; AUTO_INCREMENT lo acepta).
# ---------------------------------------------------------------------------
OWNER = "'bna_owner'@'%'"
SQL_MODE = ("STRICT_ALL_TABLES,ONLY_FULL_GROUP_BY,NO_ZERO_IN_DATE,NO_ZERO_DATE,"
            "ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION")
COLLATION = "utf8mb4_0900_as_cs"
UUID_V4 = ("(CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), "
           "CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7)))")


def my_type(t):
    if "IDENTITY" in t:
        return "BIGINT AUTO_INCREMENT"
    m = re.match(r"NUMERIC(\(.*\))$", t)
    if m:
        return "DECIMAL" + m.group(1)
    return {"UUID": "BINARY(16)", "TIMESTAMPTZ": "DATETIME(6)", "BOOLEAN": "TINYINT(1)",
            "JSONB": "JSON", "INET": "VARCHAR(45)", "BYTEA": "LONGBLOB"}.get(t, t)


def type_check(t, col):
    """CHECK que suple en MySQL lo que el tipo de PostgreSQL ya garantiza."""
    if t == "UUID":
        return ("(ASCII(SUBSTR(%s, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(%s, 9, 1)) & 0xC0) = 0x80"
                % (col, col))
    if t == "BOOLEAN":
        return "%s IN (0, 1)" % col
    if t == "INET":
        return "IS_IPV4(%s) OR IS_IPV6(%s)" % (col, col)
    return None


def my_check(c):
    c = re.sub(r"(\w+) ~ ('[^']*')", r"REGEXP_LIKE(\1, \2)", c)
    return re.sub(r"num_nonnulls\((\w+), (\w+)\) = 1", r"(\1 IS NOT NULL) + (\2 IS NOT NULL) = 1", c)


def my_default(d):
    return "(UTC_TIMESTAMP(6))" if d == "now()" else d


# Índices de consulta parciales: MySQL no admite WHERE en un índice; la
# columna de la condición pasa a encabezar el índice.
PARTIAL_QUERY_LEAD = {"ix_evento_salida_pendiente": "estado_envio",
                      "ix_evento_entrega_pendiente": "estado_entrega"}


def functional_unique(cols, where):
    cond = re.sub(r"^(es_principal|estado_activo)$", r"\1 = 1", where)
    return ", ".join("(CASE WHEN %s THEN %s END)" % (cond, c.strip()) for c in cols.split(","))


# ---------------------------------------------------------------------------
# Roles. DECISIÓN: tres cuentas o roles.
#   * bna_owner: cuenta bloqueada (no inicia sesión), dueña y DEFINER de los
#     triggers, procedimientos, vistas y del evento;
#   * bna_admin: DDL y DML sobre las cinco bases, sin privilegios de servidor;
#   * bna_app: la aplicación. Lee todo; inserta en las tablas de negocio (no
#     en catálogos, parámetros ni datos de referencia) salvo
#     los asientos (solo por core.registrar_asiento) y el consumo diario (lo
#     mantienen los triggers); actualiza solo las columnas que cambia una
#     operación de negocio; no borra, no trunca (TRUNCATE exige DROP) ni
#     altera nada.
# ---------------------------------------------------------------------------
APP_NO_INSERT = {"ASIENTO_CONTABLE", "DETALLE_ASIENTO", "CONSUMO_DIARIO"}
# Datos de referencia que mantiene bna_admin, como los catálogos y los
# parámetros sembrados.
REFERENCE = {"AGENCIA", "CUENTA_CONTABLE", "TERMINAL", "ANALISTA", "BIN_TARJETA", "PASARELA_PAGO"}
# Bitácoras de solo inserción: sin UPDATE para la aplicación.
APPEND_ONLY = {"ASIENTO_CONTABLE", "DETALLE_ASIENTO", "INTENTO_AUTENTICACION",
               "HISTORIAL_ESTADO_TARJETA", "HISTORIAL_ESTADO_SOLICITUD", "EVENTO_AUDITORIA",
               "APLICACION_PAGO"}
# Columnas que mantiene la base (triggers): la aplicación no las escribe.
DERIVED = {"CUENTA_AHORRO": {"saldo_contable", "saldo_disponible"},
           "CREDENCIAL": {"intentos_fallidos"}, "MATRIZ_TOKEN": {"intentos_fallidos"},
           "AUTORIZACION": {"uuid_transaccion", "fecha_actualizacion"},
           "TARJETA": {"estado_tarjeta"}, "CUOTA": {"saldo_pendiente", "estado_cuota"},
           "CREDITO": {"estado_credito"}}
# En la inserción, el estado de la tarjeta, la cuota y el crédito sí los da la
# aplicación (estado inicial).
DERIVED_ON_INSERT_OK = {"TARJETA": {"estado_tarjeta"}, "CUOTA": {"saldo_pendiente", "estado_cuota"},
                        "CREDITO": {"estado_credito"}}
# Tablas cuyas columnas actualizables se enumeran (el resto de la fila no
# cambia: lo impiden además sus triggers).
APP_UPDATE_ONLY = {"MOVIMIENTO": ["estado_transaccion"],
                   "AUTORIZACION": ["estado_autorizacion", "codigo_respuesta", "motivo_rechazo", "nivel_riesgo"]}
PROCEDURES_APP = ["core.registrar_asiento", "core.verificar_configuracion", "tarjetas.bloquear_tarjeta",
                  "creditos.aplicar_pago"]
PROCEDURES_ADMIN = ["tarjetas.marcar_tarjetas_vencidas"]


def grants(order):
    seeded = {rel for rel, _, _ in SEEDS} | {t for t, *_ in CATALOGS} | REFERENCE
    L = []
    w = L.append
    w("CREATE ROLE IF NOT EXISTS bna_app, bna_admin;")
    for s_ in SCHEMAS:
        w("GRANT ALL PRIVILEGES ON %s.* TO bna_admin;" % s_)
    for s_ in SCHEMAS:
        w("GRANT SELECT ON %s.* TO bna_app;" % s_)
    for rel in order:
        cols = [a["name"] for a in FIN[rel]]
        pkc = set(pk(rel))
        ident = {c for c in cols if "%s.%s" % (rel, c) in IDENTITY}
        if rel not in APP_NO_INSERT and rel not in seeded:
            excl = (DERIVED.get(rel, set()) - DERIVED_ON_INSERT_OK.get(rel, set())) | ident
            ins = [c for c in cols if c not in excl]
            if ins == cols:
                w("GRANT INSERT ON %s TO bna_app;" % q(rel))
            else:
                w("GRANT INSERT (%s) ON %s TO bna_app;" % (", ".join(ins), q(rel)))
        if rel in APPEND_ONLY or rel in seeded or rel in APP_NO_INSERT:
            continue
        upd = APP_UPDATE_ONLY.get(rel) or [c for c in cols if c not in pkc | ident | DERIVED.get(rel, set())]
        if upd:
            w("GRANT UPDATE (%s) ON %s TO bna_app;" % (", ".join(upd), q(rel)))
    for p in PROCEDURES_APP:
        w("GRANT EXECUTE ON PROCEDURE %s TO bna_app;" % p)
    w("GRANT EXECUTE ON FUNCTION core.uuid_v4 TO bna_app;")
    w("GRANT EXECUTE ON FUNCTION core.fn_fecha_negocio TO bna_app;")
    for p in PROCEDURES_APP + PROCEDURES_ADMIN:
        w("GRANT EXECUTE ON PROCEDURE %s TO bna_admin;" % p)
    return L


def identity_guards(order):
    """Triggers que rechazan un identificador explícito en las bitácoras."""
    L = ["DELIMITER //"]
    for rel in order:
        for a in FIN[rel]:
            if "%s.%s" % (rel, a["name"]) in IDENTITY:
                L.append("CREATE TRIGGER %s.tg_%s_identidad BEFORE INSERT ON %s\nFOR EACH ROW BEGIN\n"
                         "    IF NEW.%s <> 0 THEN\n"
                         "        CALL core.fallar(CONCAT('BNA-IDENTIDAD: %s.%s lo asigna la base (se recibió ', NEW.%s, ')'));\n"
                         "    END IF;\nEND //" % (SCHEMA_OF[rel], rel.lower(), q(rel), a["name"], q(rel), a["name"],
                                          a["name"]))
    L.append("DELIMITER ;")
    return L


def with_definer(sql):
    sql = re.sub(r"^CREATE (TRIGGER|PROCEDURE|FUNCTION|EVENT) ", r"CREATE DEFINER = %s \1 " % OWNER, sql, flags=re.M)
    return re.sub(r"^CREATE VIEW ", "CREATE DEFINER = %s SQL SECURITY DEFINER VIEW " % OWNER, sql, flags=re.M)


def my_str(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def gen(path):
    L = []
    w = L.append
    w("-- =====================================================================")
    w("-- Banco Nacional de Arequipa (BNA) - base de datos integrada del CORE")
    w("-- MySQL 8.4. Generado por modelo/modelo_bna.py desde el esquema")
    w("-- relacional normalizado (3FN) y con tablas de catálogo; el diseño es el")
    w("-- de la rama main (PostgreSQL) y solo cambia la capa física.")
    w("-- =====================================================================")
    w("-- DECISIÓN: MySQL 8.4, por decisión del equipo de infraestructura, en")
    w("--   contra de la recomendación del informe (sección «Selección del")
    w("--   sistema gestor de base de datos»).")
    w("-- DECISIÓN: una base (database) por cada esquema lógico de la rama main,")
    w("--   con los mismos nombres calificados; collation utf8mb4_0900_as_cs, que")
    w("--   distingue mayúsculas y tildes como PostgreSQL (con la de omisión,")
    w("--   CHECK (x IN ('ACTIVA')) aceptaría 'activa').")
    w("-- DECISIÓN: el modo SQL estricto se fija en la configuración del servidor")
    w("--   (conf/mysql/bna.cnf) y aquí, en la sesión de carga: cada trigger y")
    w("--   procedimiento se ejecuta siempre con el modo vigente al crearlo.")
    w("-- DECISIÓN: las claves foráneas se agregan al final con ALTER TABLE, después")
    w("--   de los índices, para que InnoDB use esos índices y no cree otros;")
    w("--   ON DELETE RESTRICT por omisión, porque los registros financieros no se")
    w("--   borran, se anulan o revierten.")
    w("")
    w("SET NAMES utf8mb4;")
    w("SET SESSION sql_mode = '%s';" % SQL_MODE)
    w("SET SESSION time_zone = '+00:00';")
    w("")
    for s_ in SCHEMAS:
        w("CREATE DATABASE IF NOT EXISTS %s CHARACTER SET utf8mb4 COLLATE %s;" % (s_, COLLATION))
    w("CREATE USER IF NOT EXISTS %s ACCOUNT LOCK;" % OWNER)
    for s_ in SCHEMAS:
        w("GRANT ALL PRIVILEGES ON %s.* TO %s;" % (s_, OWNER))
    w("")
    order = [t for s_ in SCHEMAS for t in SCHEMAS[s_]]
    missing = set(FIN) - set(order)
    assert not missing, missing
    names = set()
    for rel in order:
        attrs = FIN[rel]
        w("-- %s" % ("-" * 69))
        w("CREATE TABLE %s (" % q(rel))
        lines, tchecks = [], []
        for a in attrs:
            key = "%s.%s" % (rel, a["name"])
            lt = col_type(rel, a)
            t = my_type(lt)
            if lt == "UUID" and a["pk"] and not a["fk"] and len(pk(rel)) == 1:
                t += " DEFAULT " + UUID_V4
            null = a["null"] or key in NULLABLE
            d = DEFAULTS.get(a["name"]) if not a["pk"] else None
            line = "    %-27s %s" % (a["name"], t)
            if d and "IDENTITY" not in lt:
                line += " DEFAULT " + my_default(d)
            if not null and not a["pk"]:
                line += " NOT NULL"
            if key in ENUMS:
                line += "\n        CHECK (%s IN (%s))" % (a["name"], ", ".join(sql_str(v) for v in ENUMS[key]))
            lines.append(line)
            tc = type_check(lt, a["name"])
            if tc:
                tchecks.append(("ck_%s_%s" % (rel.lower(), a["name"]), tc))
        lines.append("    CONSTRAINT pk_%s PRIMARY KEY (%s)" % (rel.lower(), ", ".join(pk(rel))))
        for i, u in enumerate(uniques(rel), 1):
            lines.append("    CONSTRAINT uk_%s_%d UNIQUE (%s)" % (rel.lower(), i, ", ".join(u)))
        for i, c in enumerate(CHECKS.get(rel, []), 1):
            lines.append("    CONSTRAINT ck_%s_%d CHECK (%s)" % (rel.lower(), i, my_check(c)))
        for n, c in tchecks:
            lines.append("    CONSTRAINT %s CHECK (%s)" % (n, c))
        for ln in lines:
            m = re.match(r"\s+CONSTRAINT (\w+) (CHECK|UNIQUE)", ln)
            if m:
                assert len(m.group(1)) <= 64, m.group(1)
                assert (SCHEMA_OF[rel], m.group(1)) not in names, m.group(1)
                names.add((SCHEMA_OF[rel], m.group(1)))
        w(",\n".join(lines))
        w(") ENGINE = InnoDB COMMENT = %s;" % my_str(comment_text(rel)))
        w("")
    # indexes before foreign keys
    w("-- %s" % ("=" * 69))
    w("-- Índices")
    w("-- %s" % ("=" * 69))
    idx = []
    for rel in order:
        for cols, tgt in fks(rel):
            pkc = pk(rel)
            covered = (tuple(pkc[:len(cols)]) == cols
                       or any(tuple(u[:len(cols)]) == cols for u in uniques(rel))
                       or any(r == rel and where is None and tuple(c[:len(cols)]) == cols
                              for _, r, c, where, _ in QUERY_INDEXES))
            if not covered:
                idx.append((rel, cols))
    w("-- DECISIÓN: InnoDB exige un índice por clave foránea y lo crea si falta;")
    w("--   se crean aquí, con nombre, los mismos que en la rama main.")
    for rel, cols in idx:
        w("CREATE INDEX ix_%s_%s ON %s (%s);" % (rel.lower(), "_".join(cols), q(rel), ", ".join(cols)))
    w("-- DECISIÓN: MySQL no tiene índices parciales. La unicidad parcial se")
    w("--   expresa con un índice funcional sobre CASE WHEN condición THEN columna")
    w("--   END: fuera de la condición vale NULL, y los NULL no chocan entre sí.")
    for name, rel, cols, where, why in PARTIAL:
        w("-- DECISIÓN: %s." % why)
        w("CREATE UNIQUE INDEX %s ON %s (%s);" % (name, q(rel), functional_unique(cols, where)))
    w("-- DECISIÓN: índices de consulta para las vistas y las consultas documentadas;")
    w("--   en los dos que en la rama main son parciales, la columna de la")
    w("--   condición encabeza el índice.")
    for name, rel, cols, where, why in QUERY_INDEXES:
        w("-- %s%s." % (why[0].upper(), why[1:]))
        cols = ((PARTIAL_QUERY_LEAD[name],) if where else ()) + tuple(cols)
        w("CREATE INDEX %s ON %s (%s);" % (name, q(rel), ", ".join(cols)))
    w("")
    # foreign keys
    w("-- %s" % ("=" * 69))
    w("-- Claves foráneas")
    w("-- %s" % ("=" * 69))
    for rel in order:
        for i, (cols, tgt) in enumerate(fks(rel), 1):
            w("ALTER TABLE %s ADD CONSTRAINT fk_%s_%d FOREIGN KEY (%s)\n    REFERENCES %s (%s);"
              % (q(rel), rel.lower(), i, ", ".join(cols), q(tgt), ", ".join(pk(tgt))))
    for rel, cols, tgt, why in EXTRA_FK:
        w("-- DECISIÓN: %s." % why)
        w("ALTER TABLE %s ADD CONSTRAINT fk_%s_vinculo FOREIGN KEY (%s)\n    REFERENCES %s (%s);"
          % (q(rel), rel.lower(), ", ".join(cols), q(tgt), ", ".join(pk(tgt))))
    w("")
    w(PROG_BEGIN)
    with open(PROGRAMMING, encoding="utf-8") as f:
        w(with_definer(f.read().rstrip("\n")))
    w("")
    w("-- %s" % ("-" * 69))
    w("-- Bitácoras: el identificador lo asigna la base (en la rama main,")
    w("-- GENERATED ALWAYS AS IDENTITY rechaza un valor explícito).")
    w("-- %s" % ("-" * 69))
    w(with_definer("\n".join(identity_guards(order))))
    w("")
    w("-- %s" % ("=" * 69))
    w("-- Roles y privilegios")
    w("-- %s" % ("=" * 69))
    w("\n".join(grants(order)))
    w(PROG_END)
    w("")
    w("-- %s" % ("=" * 69))
    w("-- Datos iniciales: parámetros documentados por las fuentes")
    w("-- %s" % ("=" * 69))
    w("-- DECISIÓN: solo se cargan valores que figuran en los documentos de los")
    w("--   módulos; los números de módulo sin asignar se agregan después.")
    w("START TRANSACTION;")
    for rel, cols, rows in SEEDS:
        w("INSERT INTO %s (%s) VALUES" % (q(rel), ", ".join(cols)))
        w(",\n".join("    (%s)" % ", ".join(my_str(v) for v in r) for r in rows) + ";")
    w("COMMIT;")
    text = "\n".join(L) + "\n"
    assert "CASCADE" not in text.upper().replace("CASCADA", ""), "ON DELETE CASCADE no se usa"
    for m in re.finditer(r"core\.fallar\('([^']*)'\)", text):
        assert len(m.group(1)) <= 128, m.group(1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    # Capa programable tal como se carga (anexo del informe).
    prog = text[text.index(PROG_BEGIN):text.index(PROG_END) + len(PROG_END)]
    with open(os.path.join(os.path.dirname(path), "..", "informe", "mysql-programacion.sql"), "w",
              encoding="utf-8") as f:
        f.write(prog + "\n")
    return len(order)


PROG_BEGIN = "-- >>> capa programable (procedimientos, funciones, triggers, vistas, evento y roles)"
PROG_END = "-- <<< fin de la capa programable"


# ---------------------------------------------------------------------------
# Final verification table (report): candidate keys and the reasoning that
# each relation of the final schema is in 1FN, 2FN and 3FN.
# ---------------------------------------------------------------------------
NOTES = {
    "AGENCIA": "`distrito` no determina `ciudad`: hay distritos homónimos en distintas ciudades (Miraflores en Lima y en Arequipa).",
    "CUENTA_CONTABLE": "Se retiró `nivel` en 3FN; `naturaleza` no depende de `codigo_padre`, porque existen cuentas correctoras de naturaleza opuesta a la de su cuenta padre.",
    "ASIENTO_CONTABLE": "`numero_asiento` es clave candidata; `id_asiento_revertido` es única pero admite nulos, por lo que no es clave y no determina nada. `estado_asiento` se retiró por derivarse de otra fila.",
    "CLIENTE": "Cuatro claves candidatas más (documento, correo, celular y verificación); todo determinante es superclave.",
    "CODIGO_VERIFICACION": "`estado_codigo` no se deriva de `intentos_fallidos` ni de `fecha_expiracion`: VALIDADO, PENDIENTE y EXPIRADO dependen del momento y de la respuesta del cliente.",
    "CUENTA_AHORRO": "`cci` es clave candidata; aunque codifica la oficina y el número de cuenta, todo lo que determina lo determina como superclave.",
    "MOVIMIENTO": "`id_asiento` es clave candidata (relación 1:1 con el asiento).",
    "TARJETA": "Tras retirar `tipo_tarjeta` y `vencimiento_mm_aa`, ningún atributo no primo determina a otro.",
    "INTENTO_AUTENTICACION": "`id_canal` solo tiene valor cuando no hay terminal (restricción de arco exclusivo), de modo que no depende de `id_terminal`.",
    "AUTORIZACION": "Igual que el intento respecto de terminal y canal; `codigo_respuesta` no determina el estado (00 corresponde a AUTORIZADA y a DISPENSADA). `uuid_transaccion` es única pero admite nulos (las consultas no generan movimiento).",
    "CALENDARIO_PAGO": "(`id_solicitud`, `version`) es clave candidata.",
    "CUOTA": "`estado_cuota` depende de la fecha de consulta además de los saldos (VENCIDA), por lo que no hay dependencia funcional entre atributos.",
    "EVALUACION": "(`id_solicitud`, `ronda`) es clave candidata. `score_calculado` y `limite_aprobado` se registran como resultado del motor en esa ronda: el modelo de score es externo y versionado, así que `id_consulta` no los determina.",
    "REGLA_EVALUACION": "`codigo_rn` es clave candidata; el tramo (`ratio_min`, `ratio_max`) es único, pero un extremo puede ser nulo (tramos abiertos), por lo que no es clave. `accion` depende de la regla, no del tramo por separado.",
    "DECISION_ANALISTA": "`id_evaluacion` es clave candidata (relación 1:1).",
    "SOLICITUD_REVERSION": "`idempotency_key` es clave candidata; `uuid_transaccion_extorno` es única pero admite nulos (solo la reversión confirmada genera extorno).",
    "ORDEN_DESEMBOLSO": "`codigo_orden` e `idempotency_key` son claves candidatas; `request_hash` depende de la petición, identificada por la clave de idempotencia. `uuid_transaccion_abono` es única pero admite nulos (solo la orden confirmada abona).",
    "EVENTO_ENTREGA": "`version_esquema` no depende de `tipo_evento`: los eventos antiguos conservan la versión del contrato con la que se enviaron.",
    "CREDITO": "`id_orden` e `id_calendario` son claves candidatas (relaciones 1:1).",
    "MORA": "(`id_calendario`, `numero_cuota`, `fecha_calculo`) es clave candidata; `dias_atraso` se retiró en 3FN.",
    "EVENTO_AUDITORIA": "El tipo del registro auditado se obtiene de ENTIDAD_AUDITADA; `numero_cuota` solo tiene valor cuando el registro es una cuota y no depende de `id_entidad`, porque un calendario tiene varias cuotas.",
    "ENTIDAD_AUDITADA": "Un único atributo no primo: el tipo del registro auditado.",
    "TERMINAL": "`id_agencia` no determina `id_canal`: una agencia tiene ventanillas, agentes y cajeros.",
    "REGIMEN_CUENTA": "`firma_conjunta` y `min_titulares` no se determinan entre sí (la indistinta y la conjunta exigen dos titulares).",
    "TITULARIDAD": "Sin atributos no primos dependientes de parte de la clave tras retirar `rol_titular` en 2FN.",
    "LIMITE_CANAL": "Tras trasladar la regla a CANAL, el tope y la habilitación dependen del par canal--moneda.",
    "CREDENCIAL": "Tras extraer `longitud`, los atributos dependen del par tarjeta--tipo.",
}


def verification_rows():
    from modelo_bna import md, relname, ttb, NEW, MR_ORDER
    order = list(MR_ORDER) + [n for n in FIN if n not in MR_ORDER]
    rows = []
    for rel in order:
        nullable = {a["name"] for a in FIN[rel]
                    if a["null"] or "%s.%s" % (rel, a["name"]) in NULLABLE}
        ks = [pk(rel)] + [u for u in uniques(rel) if not set(u) & nullable]
        un = [u for u in uniques(rel) if set(u) & nullable]
        keys = "; ".join(ttb("(" + ", ".join(k) + ")") for k in ks)
        if un:
            keys += r"; \textit{únicas con nulos:} " + "; ".join(ttb("(" + ", ".join(u) + ")") for u in un)
        if rel in NOTES:
            note = md(NOTES[rel])
        elif NEW.get(rel) == "cat":
            note = "Catálogo: código como clave y atributos que describen solo a ese código."
        elif len(pk(rel)) > 1:
            note = "Clave compuesta; los atributos no primos dependen de toda la clave y no entre sí."
        else:
            note = "Clave simple; ningún atributo no primo determina a otro."
        rows.append(r"%s & %s & %s \\" % (relname(rel), keys, note))
    return "\n".join(rows) + "\n"
