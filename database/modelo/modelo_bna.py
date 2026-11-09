# Regenerate the LaTeX fragments of the data model after editing it:
#   cd modelo && python3 modelo_bna.py ../informe

# -*- coding: utf-8 -*-
"""Integrated BNA data model: single source for the LaTeX fragments.

Run:  python model.py <output-dir>
"""
import copy
import os
import re
import sys

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def A(name, desc, key="", comp=None, mv=False, der=False):
    """Attribute. key: PK | PP (partial) | UK. comp: list of (name, desc)."""
    return dict(name=name, desc=desc, key=key, comp=comp, mv=mv, der=der)


def esc(s):
    s = s.replace("\\", r"\textbackslash{}")
    for c in "&%$#_{}":
        s = s.replace(c, "\\" + c)
    s = s.replace("~", r"\textasciitilde{}")
    return s


def md(s):
    """Escape text and turn `code` into \\texttt{code}."""
    parts = re.split(r"`([^`]*)`", s)
    out = []
    for i, p in enumerate(parts):
        out.append(r"\texttt{%s}" % esc(p) if i % 2 else esc(p))
    return "".join(out)


def tt(s):
    return r"\texttt{%s}" % esc(s)


def ttb(s):
    """texttt that may break after underscores (for narrow cells)."""
    return r"\texttt{%s}" % esc(s).replace(r"\_", r"\_\allowbreak{}")


def relname(n):
    """CUENTA_AHORRO -> \\textsc{Cuenta\\_Ahorro}"""
    return r"\textsc{%s}" % esc("_".join(w.capitalize() for w in n.split("_")))


# ---------------------------------------------------------------------------
# Modules / sources
# ---------------------------------------------------------------------------
MODULES = [
    ("CORE", "Núcleo contable (CORE)"),
    ("CLI", "Clientes (KYC / biometría)"),
    ("CTA", "Cuentas de ahorro"),
    ("TAR", "Tarjetas y canales"),
    ("SOL", "Solicitud de crédito"),
    ("EVA", "Evaluación crediticia"),
    ("DES", "Desembolso"),
    ("COB", "Cobranza"),
    ("TRV", "Transversal (auditoría)"),
]

# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
E = {}
ORDER = []


def entity(name, module, kind, src, desc, attrs, owners=None):
    E[name] = dict(name=name, module=module, kind=kind, src=src, desc=desc,
                   attrs=attrs, owners=owners or [])
    ORDER.append(name)


# DECISIÓN: ningún módulo modela el núcleo contable; estas cuatro entidades se
#   derivan de la arquitectura del CORE (asientos de partida doble inmutables,
#   plan de cuentas, agencias) y sus atributos son los mínimos para ese rol.
# ---- CORE -----------------------------------------------------------------
entity("AGENCIA", "CORE", "fuerte", "CORE, CTA, DES",
       "Agencia física del BNA; las cuatro agencias iniciales de Arequipa.", [
           A("id_agencia", "Código de la agencia.", "PK"),
           A("nombre", "Nombre comercial de la agencia."),
           A("direccion", "Ubicación de la agencia.", comp=[
               ("calle", "Vía y número."),
               ("distrito", "Distrito."),
               ("ciudad", "Ciudad (Arequipa)."),
           ]),
           A("estado_agencia", "ACTIVA o INACTIVA."),
       ])

entity("CUENTA_CONTABLE", "CORE", "fuerte", "CORE, DES",
       "Cuenta del plan de cuentas sobre la que se registran los asientos.", [
           A("codigo_contable", "Código de la cuenta en el plan de cuentas.", "PK"),
           A("nombre", "Denominación de la cuenta contable."),
           A("naturaleza", "DEUDORA o ACREEDORA."),
           A("nivel", "Nivel jerárquico dentro del plan de cuentas."),
       ])

entity("ASIENTO_CONTABLE", "CORE", "fuerte", "CORE, CTA, TAR, DES",
       "Cabecera del asiento de partida doble; es inmutable y se corrige con un asiento de reversa.", [
           A("id_asiento", "Identificador UUID del asiento.", "PK"),
           A("numero_asiento", "Correlativo legible del asiento (antes `num_asiento_core`).", "UK"),
           A("fecha_contable", "Fecha en que se registra el asiento."),
           A("fecha_valor", "Fecha valor de la operación (p. ej., primer día del mes para intereses)."),
           A("glosa", "Descripción de la operación contabilizada."),
           A("moneda", "Moneda del asiento: PEN o USD."),
           A("estado_asiento", "REGISTRADO o REVERSADO."),
           A("correlation_id", "Identificador de correlación propagado por el Bus."),
       ])

entity("DETALLE_ASIENTO", "CORE", "débil", "CORE",
       "Línea de débito o crédito de un asiento; no existe ni se identifica sin su asiento.", [
           A("nro_linea", "Número de línea dentro del asiento.", "PP"),
           A("tipo_partida", "DEBE o HABER."),
           A("importe", "Importe de la línea; mayor que cero."),
       ], owners=[("ASIENTO_CONTABLE", "COMPONE")])

# ---- CLIENTES -------------------------------------------------------------
entity("CLIENTE", "CLI", "fuerte", "CLI, CTA, TAR, SOL, EVA, DES, COB",
       "Maestro único de la persona natural cliente del banco; reemplaza a `CLIENTE_REF`, `cliente_ref` y `CLIENTES`.", [
           A("cod_cliente", "Customer ID generado por CLIENTES y persistido en CORE.", "PK"),
           A("documento", "Documento de identidad; único por cliente.", "UK", comp=[
               ("tipo_documento", "DNI, CE, PASAPORTE o PTP."),
               ("numero_documento", "Número del documento."),
           ]),
           A("nombre_completo", "Nombre del titular.", comp=[
               ("nombres", "Nombres."),
               ("apellido_paterno", "Primer apellido."),
               ("apellido_materno", "Segundo apellido (opcional)."),
           ]),
           A("correo", "Correo electrónico único para notificaciones (RN-CLI-003).", "UK"),
           A("celular", "Celular único de 9 dígitos que inicia en 9 (RN-CLI-003).", "UK"),
           # DECISIÓN: dominio = unión de las listas de Clientes y Tarjetas.
           A("estado_cliente", "ACTIVO, OBSERVADO, BLOQUEADO, SUSPENDIDO o BAJA."),
           A("id_verificacion_captacion", "Código del proceso de verificación de captación (KYC / onboarding)."),
           A("fecha_verificacion", "Fecha y hora en que se completó la verificación de captación."),
           A("estado_habilitante", "HABILITADO u OBSERVADO para solicitar crédito (RN-CLI-001)."),
           A("version_contrato", "Versión del contrato marco vigente del cliente."),
       ])

entity("BIOMETRIA_CLIENTE", "CLI", "fuerte", "CLI, CTA",
       "Plantilla biométrica registrada del cliente, cifrada con AES-256.", [
           A("id_biometria", "Identificador del registro biométrico.", "PK"),
           A("tipo_biometria", "DACTILAR o FACIAL."),
           A("datos_biometricos", "Plantilla matemática cifrada (nunca la imagen)."),
           A("estado_activo", "Indica si la plantilla está vigente."),
       ])

entity("CODIGO_VERIFICACION", "CLI", "fuerte", "CLI",
       "Código OTP temporal enviado al celular o al correo del cliente.", [
           A("id_codigo", "Identificador del código.", "PK"),
           A("tipo_contacto", "Canal de envío: SMS o CORREO."),
           A("destino", "Número o correo al que se envió el código."),
           A("codigo_otp", "Código de seis dígitos (almacenado como hash)."),
           A("fecha_expiracion", "Fecha y hora de expiración del código."),
           A("estado_codigo", "PENDIENTE, VALIDADO, EXPIRADO o BLOQUEADO."),
           A("intentos_fallidos", "Intentos incorrectos acumulados; bloqueo al tercero (RF-CLI-005)."),
       ])

entity("VALIDACION_IDENTIDAD", "CLI", "fuerte", "CLI, DES",
       "Bitácora inmutable de cada intento de validación de identidad (antes `AUDITORIA_VALIDACION`).", [
           A("id_validacion", "Identificador del registro de auditoría.", "PK"),
           A("tipo_validacion", "DOCUMENTO, HUELLA, FACIAL, CELULAR o CORREO."),
           A("resultado", "APROBADO o RECHAZADO."),
           A("correlation_id", "Identificador de correlación de la petición (RNF-CLI-005)."),
           A("fecha_evento", "Fecha y hora de la validación."),
       ])

# ---- CUENTAS --------------------------------------------------------------
entity("CUENTA_AHORRO", "CTA", "fuerte", "CTA, TAR, DES, COB",
       "Cuenta de ahorros individual o mancomunada; reemplaza a `cuenta_ref` de TARJETAS.", [
           A("num_cuenta", "Número de la cuenta de ahorros.", "PK"),
           A("cci", "Código de cuenta interbancario generado en la apertura.", "UK"),
           A("moneda", "PEN o USD (RN-CTA-001)."),
           A("regimen", "INDIVIDUAL, MANCOMUNADA_INDISTINTA o MANCOMUNADA_CONJUNTA (RN-CTA-002)."),
           A("saldo_contable", "Saldo contabilizado; resulta de los movimientos.", der=True),
           A("saldo_disponible", "Saldo líquido: contable menos retenciones.", der=True),
           A("estado_cuenta", "ACTIVA, BLOQUEADA, BLOQUEADA_PREVENTIVA o CANCELADA."),
           A("fecha_apertura", "Fecha de creación de la cuenta."),
       ])

entity("MOVIMIENTO", "CTA", "fuerte", "CTA",
       "Débito o crédito aplicado a una cuenta (antes `TRANSACCIONES_HISTORICO`).", [
           A("uuid_transaccion", "Clave de idempotencia de la operación (RN-BUS-002).", "PK"),
           # DECISIÓN: los tipos distinguen el sentido (TRANSFERENCIA_ENVIADA/RECIBIDA).
           A("tipo_operacion", "RETIRO, DEPOSITO, TRANSFERENCIA_ENVIADA, DESEMBOLSO, ABONO_INTERES, EXTORNO, etc."),
           A("tipo_movimiento", "D (débito) o C (crédito)."),
           A("monto", "Importe del movimiento; siempre positivo."),
           A("glosa", "Concepto que se muestra al cliente (CUS-CTA-009)."),
           A("fecha_hora", "Fecha y hora de registro."),
           A("estado_transaccion", "APROBADO o EXTORNADO."),
       ])

# DECISIÓN: entidad débil con dos propietarias; se descarta el idTope de Cuentas.
entity("CONSUMO_DIARIO", "CTA", "débil", "CTA, TAR",
       "Acumulado de salidas de una cuenta por canal y jornada; base del tope diario (RN-TOP-001).", [
           A("fecha_corte", "Jornada de 24 horas con corte a las 00:00:00.", "PP"),
           A("monto_acumulado", "Suma de las salidas del día por el canal.", der=True),
       ], owners=[("CUENTA_AHORRO", "ACUMULA_CUENTA"), ("CANAL", "ACUMULA_CANAL")])

# ---- TARJETAS Y CANALES -----------------------------------------------------
entity("CANAL", "TAR", "fuerte", "TAR, CTA, COB, DES",
       "Canal de atención; unifica `canal` (TARJETAS), `CANAL_PAGO` (COBRANZA) e `idCanal` (CUENTAS).", [
           A("id_canal", "ATM, AGE (agente), VEN (ventanilla), HB (Home Banking) o BD (Billetera Digital).", "PK"),
           A("nombre", "Nombre del canal.", "UK"),
           A("es_presencial", "Indica si el cliente está físicamente presente."),
           # DECISIÓN: atributo de CANAL_PAGO (Cobranza) extendido a todos los canales.
           A("tipo_integracion", "Mecanismo de integración (Bus de Servicios u otro)."),
           A("activo", "Indica si el canal está operativo."),
           A("validacion_requerida", "Credenciales que exige el canal: PIN_ATM, CLAVE_WEB, BIOMETRIA, TOKEN_PAGO, TOKEN_MATRIZ.", mv=True),
       ])

entity("LIMITE_CANAL", "TAR", "débil", "TAR, CTA",
       "Tope diario de un canal en una moneda (RN-TOP-001).", [
           A("moneda", "PEN o USD.", "PP"),
           A("monto_maximo_diario", "Tope diario; nulo significa sin límite automático."),
           A("habilitado", "Falso si el canal no opera en esa moneda."),
           A("regla_negocio", "Código de la regla que define el tope."),
       ], owners=[("CANAL", "FIJA_TOPE")])

entity("TARJETA", "TAR", "fuerte", "TAR, CTA",
       "Tarjeta de débito física o virtual; no guarda el PAN completo (PCI-DSS).", [
           A("id_tarjeta", "Identificador interno de la tarjeta.", "PK"),
           A("pan_token", "Token que reemplaza al número completo.", "UK"),
           A("numero_visible", "Partes del PAN que pueden mostrarse.", comp=[
               ("bin", "Primeros seis dígitos."),
               ("ultimos4", "Últimos cuatro dígitos."),
           ]),
           A("tipo_tarjeta", "FISICA o VIRTUAL."),
           A("fecha_emision", "Fecha de emisión; no se modifica."),
           A("fecha_vencimiento", "Último día del mes de vencimiento."),
           A("vencimiento_mm_aa", "Vencimiento con formato MM/AA (RN-TAR-003).", der=True),
           A("estado_tarjeta", "PENDIENTE_ACTIVACION, ACTIVA, BLOQUEADA, RETENIDA, VENCIDA o CANCELADA."),
           A("motivo_estado", "Motivo del último cambio de estado."),
           A("origen_ultimo_cambio", "CLIENTE, SISTEMA, SEGURIDAD, OPERADOR o MODULO_CLIENTES."),
           A("fecha_ultimo_cambio", "Fecha y hora del último cambio de estado."),
       ])

entity("CREDENCIAL", "TAR", "débil", "TAR, CTA",
       "Clave de acceso de una tarjeta; se identifica por la tarjeta y su tipo.", [
           A("tipo_credencial", "PIN_ATM (4 dígitos) o CLAVE_WEB (6 dígitos).", "PP"),
           A("longitud", "4 para PIN_ATM y 6 para CLAVE_WEB (RN-TAR-001)."),
           A("hash_credencial", "SHA-256 de la sal más la clave."),
           A("sal", "Valor aleatorio combinado con la clave."),
           A("intentos_fallidos", "Fallos consecutivos, de 0 a 3 (RN-TAR-004)."),
           A("fecha_creacion", "Fecha de creación."),
           A("fecha_ultimo_cambio", "Fecha del último cambio de clave."),
       ], owners=[("TARJETA", "PROTEGE")])

entity("MATRIZ_TOKEN", "TAR", "fuerte", "TAR",
       "Tarjeta matriz de coordenadas A--G por 0--9 (RN-TAR-002).", [
           A("id_matriz", "Identificador de la matriz.", "PK"),
           A("numero_serie", "Número de serie impreso.", "UK"),
           A("tipo_matriz", "FISICA o VIRTUAL."),
           A("sal", "Sal usada para el hash de las 70 coordenadas."),
           A("estado_matriz", "ACTIVA, BLOQUEADA o REEMPLAZADA."),
           A("intentos_fallidos", "Coordenadas erradas consecutivas, de 0 a 3."),
           A("fecha_emision", "Fecha de entrega de la matriz."),
       ])

entity("MATRIZ_COORDENADA", "TAR", "débil", "TAR",
       "Cada una de las 70 celdas de una tarjeta matriz.", [
           A("coordenada", "Posición de la celda.", "PP", comp=[
               ("fila", "Letra de la A a la G."),
               ("columna", "Número del 0 al 9."),
           ]),
           A("hash_valor", "Hash del valor impreso en la celda."),
       ], owners=[("MATRIZ_TOKEN", "CONTIENE")])

entity("TOKEN_PAGO", "TAR", "fuerte", "TAR",
       "Token entregado a una pasarela externa para el fondeo de la Billetera Digital.", [
           A("id_token_pago", "Identificador del token.", "PK"),
           A("valor_token", "Token entregado a la pasarela.", "UK"),
           A("proveedor_pasarela", "Pasarela de pago externa."),
           A("estado_token", "ACTIVO, SUSPENDIDO o REVOCADO."),
           A("fecha_creacion", "Fecha de creación."),
           A("fecha_expiracion", "Fecha en que deja de ser válido."),
       ])

entity("INTENTO_AUTENTICACION", "TAR", "fuerte", "TAR",
       "Bitácora inmutable de cada intento de validar una credencial (RN-TAR-004).", [
           A("id_intento", "Identificador del intento.", "PK"),
           A("tipo_credencial", "PIN_ATM, CLAVE_WEB o TOKEN_MATRIZ."),
           A("coordenada_solicitada", "Coordenada pedida, p. ej. `D-4`; solo para TOKEN_MATRIZ."),
           A("id_terminal", "Cajero, agente o dirección IP de origen."),
           A("resultado", "EXITOSO o FALLIDO."),
           A("motivo_rechazo", "Motivo cuando el resultado es FALLIDO."),
           A("uuid_correlacion", "Identificador de correlación enviado por el Bus."),
           A("fecha_hora", "Fecha y hora con milisegundos."),
       ])

entity("AUTORIZACION", "TAR", "fuerte", "TAR",
       "Autorización que TARJETAS emite antes de que la operación se contabilice.", [
           A("uuid_autorizacion", "UUID de la operación (en la fuente, `uuid_transaccion`).", "PK"),
           A("tipo_operacion", "CONSULTA_SALDO, RETIRO, TRANSFERENCIA, PAGO o FONDEO_BILLETERA."),
           A("monto", "Importe; cero en consultas."),
           A("moneda", "PEN o USD."),
           A("estado_autorizacion", "INICIADA, AUTORIZADA, RECHAZADA, DISPENSADA, EXTORNADA o PENDIENTE_REVERSION."),
           A("codigo_respuesta", "Código devuelto al canal: 00, 54, EXT, etc."),
           A("motivo_rechazo", "Motivo de rechazo o extorno."),
           A("nivel_riesgo", "BAJO, MEDIO o ALTO según SEGURIDAD (RN-SEG-001)."),
           A("id_terminal", "Terminal o IP de origen."),
           A("fecha_hora", "Fecha y hora de la operación."),
           A("fecha_actualizacion", "Último cambio de estado."),
       ])

entity("HISTORIAL_ESTADO_TARJETA", "TAR", "fuerte", "TAR",
       "Historial inmutable de cambios de estado de cada tarjeta (RN-SEG-002).", [
           A("id_historial", "Identificador del registro.", "PK"),
           A("estado_anterior", "Estado previo; nulo en la emisión."),
           A("estado_nuevo", "Estado resultante."),
           A("motivo", "Motivo del cambio."),
           A("origen", "Quién originó el cambio."),
           A("fecha_hora", "Momento exacto del cambio."),
       ])

entity("EVENTO_SALIDA", "TAR", "fuerte", "TAR",
       "Bandeja de eventos que el Bus entrega al log centralizado de SEGURIDAD.", [
           A("id_evento", "Identificador del evento.", "PK"),
           A("modulo_destino", "Módulo receptor; por defecto SEGURIDAD."),
           A("tipo_evento", "EMISION_TARJETA, CAMBIO_ESTADO_TARJETA o BLOQUEO_POR_INTENTOS."),
           A("carga_json", "Datos del evento en JSON."),
           A("estado_envio", "PENDIENTE, ENVIADO o ERROR."),
           A("fecha_registro", "Momento en que se generó."),
           A("fecha_envio", "Momento en que el Bus lo entregó."),
       ])

# ---- SOLICITUD DE CRÉDITO ---------------------------------------------------
entity("SOLICITUD_CREDITO", "SOL", "fuerte", "SOL, EVA, DES, COB",
       "Solicitud de crédito; reemplaza la réplica `SOLICITUD_CREDITO` de EVALUACIÓN.", [
           A("id_solicitud", "Identificador de la solicitud.", "PK"),
           A("version_solicitud", "Versión; se incrementa en cada reformulación."),
           A("monto_solicitado", "Monto solicitado por el cliente."),
           A("moneda", "PEN o USD (RN-SOL-001)."),
           A("plazo_meses", "Plazo solicitado en meses."),
           A("condicion_pago_doble", "Indica si contempla condición de pago doble."),
           A("estado_solicitud", "REGISTRADA, EN_EVALUACION, APROBADA, RECHAZADA, etc."),
           A("fecha_creacion", "Fecha y hora de creación."),
       ])

entity("HISTORIAL_ESTADO_SOLICITUD", "SOL", "fuerte", "SOL",
       "Registro de cada cambio de estado de una solicitud.", [
           A("id_historial", "Identificador del registro.", "PK"),
           A("estado_anterior", "Estado previo; nulo en la creación."),
           A("estado_nuevo", "Estado posterior al cambio."),
           A("fecha_hora", "Momento del cambio."),
           A("actor", "Usuario, rol o sistema que ejecutó el cambio."),
           A("motivo", "Justificación registrada."),
       ])

entity("GARANTIA", "SOL", "fuerte", "SOL, EVA",
       "Bien o instrumento que respalda una solicitud (RN-SOL-007).", [
           A("id_garantia", "Identificador de la garantía.", "PK"),
           A("tipo_garantia", "HIPOTECARIA, MOBILIARIA, PRENDARIA, etc."),
           A("descripcion", "Descripción del bien o instrumento."),
           A("valor_referencial", "Valor estimado."),
           A("moneda", "Moneda del valor referencial."),
           A("estado_garantia", "REGISTRADA, EN_TASACION, CONSTITUIDA o LEVANTADA."),
       ])

entity("FIADOR", "SOL", "fuerte", "SOL, EVA",
       "Persona externa que respalda solicitudes de crédito (antes `FIADOR_REF`).", [
           A("id_fiador", "Identificador local del fiador.", "PK"),
           A("id_persona_externa", "Identificador en el sistema maestro de personas.", "UK"),
           A("documento", "Documento de identidad del fiador.", "UK", comp=[
               ("tipo_documento", "DNI, CE o PASAPORTE."),
               ("numero_documento", "Número del documento."),
           ]),
       ])

entity("CALENDARIO_PAGO", "SOL", "fuerte", "SOL, EVA, COB",
       "Versión del calendario de pagos de una solicitud: PRELIMINAR (simulación) u OFICIAL.", [
           A("id_calendario", "Identificador de la versión del calendario.", "PK"),
           A("version", "Correlativo de versión dentro de la solicitud."),
           A("tipo_calendario", "PRELIMINAR u OFICIAL (RN-CAL-001)."),
           A("metodo_amortizacion", "FRANCES, AMERICANO, ALEMAN, etc."),
           A("tasa_aplicada", "Tasa de interés aplicada."),
           A("fecha_generacion", "Fecha y hora de generación."),
           A("estado_calendario", "VIGENTE, HISTORICO o DESCARTADO."),
       ])

entity("CUOTA", "SOL", "débil", "SOL, COB",
       "Cuota del calendario; unifica la `CUOTA` de SOLICITUD con la de COBRANZA.", [
           A("numero_cuota", "Número correlativo de la cuota dentro del calendario.", "PP"),
           A("fecha_vencimiento", "Fecha de vencimiento programada."),
           A("capital", "Capital amortizado en la cuota."),
           A("interes", "Interés de la cuota."),
           A("otros_conceptos", "Seguros, comisiones, etc."),
           A("importe_total", "Capital más interés más otros conceptos.", der=True),
           A("saldo_capital", "Saldo de capital luego de aplicar la cuota."),
           A("saldo_pendiente", "Parte de la cuota aún no cubierta por pagos."),
           A("estado_cuota", "PENDIENTE, PARCIAL, PAGADA o VENCIDA."),
       ], owners=[("CALENDARIO_PAGO", "DETALLA")])

# ---- EVALUACIÓN -----------------------------------------------------------
entity("SITUACION_FINANCIERA", "EVA", "fuerte", "EVA",
       "Resultado de la verificación financiera del cliente, insumo del score.", [
           A("id_consulta", "Identificador de la consulta financiera.", "PK"),
           A("resultado_verificacion", "Resultado reportado por Captación de Clientes."),
           # DECISIÓN: el JSON de la fuente se reduce a sus dos datos nombrados.
           A("datos_financieros", "Datos usados para el score (antes un campo JSON).", comp=[
               ("ingreso_mensual", "Ingresos declarados o verificados."),
               ("deuda_reportada", "Deudas reportadas."),
           ]),
           A("fecha_consulta", "Fecha y hora de la consulta; determina su vigencia (RN-CAP-005)."),
       ])

entity("EVALUACION", "EVA", "fuerte", "EVA, SOL",
       "Evaluación crediticia de una solicitud; unifica `EVALUACION` y `RESULTADO_EVALUACION`.", [
           A("id_evaluacion", "Identificador de la evaluación.", "PK"),
           # DECISIÓN: ronda de RESULTADO_EVALUACION (Solicitud); evaluación 1:N (I5).
           A("ronda", "Número de ronda; permite reevaluaciones sucesivas."),
           A("fecha_evaluacion", "Fecha y hora de la evaluación automática."),
           A("score_calculado", "Score crediticio calculado."),
           A("limite_aprobado", "Límite máximo de crédito derivado del score."),
           A("ratio_monto_limite", "Monto solicitado entre límite aprobado, en porcentaje.", der=True),
           A("tipo_resultado", "AUTOMATICA o MANUAL."),
           A("resultado", "APROBADO, OBSERVADO o RECHAZADO."),
           A("condiciones_propuestas", "Condiciones propuestas para la aprobación."),
           A("observaciones", "Observaciones comunicadas a Solicitud de Crédito."),
       ])

entity("REGLA_EVALUACION", "EVA", "fuerte", "EVA",
       "Regla de decisión por tramo del ratio monto/límite (RN-EVA-002-P).", [
           A("id_regla", "Identificador de la regla.", "PK"),
           A("codigo_rn", "Código de la regla de negocio, p. ej. RN-EVA-002-P.a.", "UK"),
           A("descripcion", "Condición evaluada."),
           A("rango_ratio", "Tramo del ratio al que aplica la regla.", comp=[
               ("ratio_min", "Límite inferior; nulo si no aplica."),
               ("ratio_max", "Límite superior; nulo si no aplica."),
           ]),
           A("accion", "APROBADO, OBSERVADO o RECHAZADO."),
       ])

entity("ANALISTA", "EVA", "fuerte", "EVA",
       "Analista de crédito habilitado para la revisión manual.", [
           A("id_analista", "Identificador del analista.", "PK"),
           A("nombre", "Nombre completo."),
           A("codigo_empleado", "Código de empleado del BNA.", "UK"),
       ])

entity("DECISION_ANALISTA", "EVA", "fuerte", "EVA",
       "Decisión final de un analista sobre una evaluación OBSERVADA (RN-EVA-004).", [
           A("id_decision", "Identificador de la decisión.", "PK"),
           A("decision", "APROBADO o RECHAZADO."),
           A("comentario", "Justificación obligatoria."),
           A("fecha_decision", "Fecha y hora de la decisión."),
       ])

# ---- DESEMBOLSO -----------------------------------------------------------
entity("ORDEN_DESEMBOLSO", "DES", "fuerte", "DES",
       "Intención, ejecución y resultado de un desembolso (antes `des_orden`).", [
           A("id_orden", "UUID v4 de la orden.", "PK"),
           A("codigo_orden", "Correlativo legible DES-2026-000001.", "UK"),
           A("aprobacion_version", "Versión de la aprobación consumida."),
           A("importe", "Monto bruto a desembolsar; mayor que cero."),
           A("moneda", "PEN o USD."),
           A("estado_orden", "PREPARADA, VALIDADA, EN_PROCESO, POR_VERIFICAR, CONFIRMADA, RECHAZADA o REVERTIDA."),
           A("motivo_rechazo", "Motivo cuando el estado es RECHAZADA."),
           A("entrega_estado", "PENDIENTE o CONFIRMADA; entrega a Cobranza."),
           A("fecha_efectiva", "Fecha valor del desembolso según el CORE."),
           A("idempotency_key", "Clave de idempotencia enviada por el canal.", "UK"),
           A("request_hash", "SHA-256 del contenido de la solicitud."),
           A("usuario_preparacion", "Operador que prepara la orden."),
           A("usuario_confirmacion", "Operador que confirma la ejecución."),
           A("correlation_id", "Identificador de correlación del Bus."),
           A("version_registro", "Control de concurrencia optimista."),
           A("creado_en", "Marca de creación en UTC."),
           A("actualizado_en", "Marca de última modificación en UTC."),
       ])

entity("VALIDACION_DESEMBOLSO", "DES", "fuerte", "DES",
       "Evidencia de cada validación previa a la ejecución de la orden.", [
           A("id_validacion", "Identificador de la validación.", "PK"),
           A("tipo_validacion", "IDENTIDAD, CUENTA, AUTORIZACION o ANTIFRAUDE."),
           A("proveedor", "Módulo que emitió la validación."),
           A("referencia_evidencia", "Referencia opaca devuelta por el proveedor."),
           A("resultado", "APROBADA o RECHAZADA."),
           A("detalle", "Observación funcional sin datos sensibles."),
           A("vence_en", "Vigencia de la validación."),
           A("creado_en", "Momento de la validación."),
       ])

entity("EVENTO_ENTREGA", "DES", "fuerte", "DES",
       "Bandeja de salida hacia Cobranza con reintentos.", [
           A("id_evento", "Identificador del evento.", "PK"),
           A("tipo_evento", "desembolso.confirmado o desembolso.revertido."),
           A("version_esquema", "Versión del contrato del mensaje."),
           A("payload", "Mensaje publicado hacia Cobranza (JSON)."),
           A("estado_entrega", "PENDIENTE, ENVIADO, CONFIRMADO o FALLIDO."),
           A("intentos", "Intentos de entrega realizados."),
           A("siguiente_intento", "Momento del próximo reintento."),
           A("confirmacion_id", "Acuse de recibo de Cobranza."),
           A("ultimo_error", "Último error registrado."),
           A("creado_en", "Creación del evento."),
           A("actualizado_en", "Último cambio de estado."),
       ])

entity("SOLICITUD_REVERSION", "DES", "fuerte", "DES",
       "Solicitud de reversión de un desembolso; preparada pero sin uso en la Fase I.", [
           A("id_reversion", "Identificador de la solicitud.", "PK"),
           A("motivo", "Motivo declarado."),
           A("solicitante_id", "Usuario que solicita la reversión."),
           A("autorizacion_id", "Referencia de autorización de SEGURIDAD."),
           A("estado_reversion", "SOLICITADA, AUTORIZADA, CONFIRMADA o RECHAZADA."),
           A("idempotency_key", "Clave propia de la reversión.", "UK"),
           A("creado_en", "Creación de la solicitud."),
           A("actualizado_en", "Último cambio de estado."),
       ])

# ---- COBRANZA -------------------------------------------------------------
entity("CREDITO", "COB", "fuerte", "COB, DES",
       "Préstamo ya desembolsado que debe cobrarse (RF-COB-015).", [
           A("cod_credito", "Identificador del crédito.", "PK"),
           A("monto_aprobado", "Monto aprobado y confirmado en el desembolso."),
           A("moneda", "PEN o USD."),
           A("fecha_desembolso", "Fecha del desembolso confirmado."),
           A("estado_credito", "AL_DIA, EN_MORA, CANCELADO, etc. (catálogo pendiente)."),
       ])

entity("PAGO", "COB", "fuerte", "COB",
       "Evento de pago realizado por el cliente.", [
           A("id_pago", "Identificador del pago.", "PK"),
           A("fecha_hora", "Momento del registro."),
           A("monto_pago", "Monto pagado: parcial, exacto o mayor a la cuota."),
           A("referencia_transaccion", "Referencia de trazabilidad e idempotencia.", "UK"),
           A("estado_confirmacion", "Confirmación del módulo procesador."),
       ])

entity("MORA", "COB", "fuerte", "COB",
       "Cada cálculo de interés moratorio que el CORE realiza para una cuota atrasada.", [
           A("id_mora", "Identificador del cálculo.", "PK"),
           A("dias_atraso", "Días de atraso al momento del cálculo."),
           A("monto_calculado", "Interés moratorio devuelto por el CORE."),
           A("fecha_calculo", "Momento del cálculo."),
           A("vigente", "Verdadero solo para el cálculo más reciente de la cuota.", der=True),
       ])

# ---- TRANSVERSAL ----------------------------------------------------------
entity("EVENTO_AUDITORIA", "TRV", "fuerte", "DES, COB",
       "Bitácora de solo inserción; unifica `des_auditoria` y `EVENTO_AUDITORIA` de COBRANZA.", [
           A("id_evento", "Correlativo de la bitácora.", "PK"),
           A("modulo_emisor", "Módulo que generó el evento."),
           A("id_entidad", "Identificador del registro afectado (orden, crédito, cuota o pago)."),
           A("accion", "PREPARAR, VALIDAR, CONFIRMAR, CAMBIO_ESTADO, PAGO_APLICADO, etc."),
           A("resultado", "Resultado de la acción."),
           A("actor", "Usuario o servicio que ejecuta la acción."),
           A("correlation_id", "Correlación con la traza del Bus."),
           A("ip_origen", "Dirección de origen; admite IPv6."),
           A("detalle", "Datos enmascarados en JSON."),
           A("fecha_hora", "Marca con precisión de milisegundos."),
       ])

# ---------------------------------------------------------------------------
# Relationships
#   card is e1:e2.  part = (participation of e1, participation of e2).
#   fk: for 1:1 / 1:N -> (side entity, [(fk_attr, referenced_pk_attr)], note)
# ---------------------------------------------------------------------------
R = []


def rel(rid, name, e1, e2, card, p1, p2, attrs=None, ident=False, src="",
        roles=None, fk=None, nm=None, desc=""):
    R.append(dict(id=rid, name=name, e1=e1, e2=e2, card=card, p1=p1, p2=p2,
                  attrs=attrs or [], ident=ident, src=src, roles=roles,
                  fk=fk, nm=nm, desc=desc))


T, P = "T", "P"
# CORE
rel("R01", "COMPONE", "ASIENTO_CONTABLE", "DETALLE_ASIENTO", "1:N", T, T, ident=True,
    desc="Todo asiento tiene al menos dos líneas (partida doble).")
rel("R02", "AFECTA", "CUENTA_CONTABLE", "DETALLE_ASIENTO", "1:N", P, T,
    fk=("DETALLE_ASIENTO", [("codigo_contable", "codigo_contable")]),
    desc="Cada línea afecta a una cuenta del plan de cuentas.")
rel("R03", "AGRUPA", "CUENTA_CONTABLE", "CUENTA_CONTABLE", "1:N", P, P, roles=("padre", "hija"),
    fk=("CUENTA_CONTABLE", [("codigo_padre", "codigo_contable")]),
    desc="Jerarquía del plan de cuentas.")
rel("R04", "REVIERTE", "ASIENTO_CONTABLE", "ASIENTO_CONTABLE", "1:1", P, P, roles=("reversa", "original"),
    fk=("ASIENTO_CONTABLE", [("id_asiento_revertido", "id_asiento")]),
    desc="Un asiento de reversa anula exactamente a un asiento original.")
rel("R05", "CONTABILIZA", "MOVIMIENTO", "ASIENTO_CONTABLE", "1:1", T, P,
    fk=("MOVIMIENTO", [("id_asiento", "id_asiento")]),
    desc="Todo movimiento se registra en el ledger (RN-COR-002).")
# DECISIÓN: participación parcial de la cuenta (apertura digital sin agencia).
rel("R06", "APERTURA_EN", "AGENCIA", "CUENTA_AHORRO", "1:N", P, P,
    fk=("CUENTA_AHORRO", [("id_agencia", "id_agencia")]),
    desc="Agencia de origen; nula en aperturas digitales.")
# CLIENTES
rel("R07", "TIENE_BIOMETRIA", "CLIENTE", "BIOMETRIA_CLIENTE", "1:N", P, T,
    fk=("BIOMETRIA_CLIENTE", [("cod_cliente", "cod_cliente")]))
rel("R08", "RECIBE_CODIGO", "CLIENTE", "CODIGO_VERIFICACION", "1:N", P, T,
    fk=("CODIGO_VERIFICACION", [("cod_cliente", "cod_cliente")]),
    desc="El código se genera para el contacto registrado del cliente.")
rel("R09", "ES_VALIDADO", "CLIENTE", "VALIDACION_IDENTIDAD", "1:N", P, P,
    fk=("VALIDACION_IDENTIDAD", [("cod_cliente", "cod_cliente")]),
    desc="Nulo cuando el documento consultado no existe.")
# CUENTAS
rel("R10", "ES_TITULAR", "CLIENTE", "CUENTA_AHORRO", "N:M", P, T,
    attrs=["rol_titular", "fecha_vinculacion"], nm="TITULARIDAD",
    desc="Una mancomunada tiene dos o más titulares (RN-CTA-002).")
rel("R11", "REGISTRA", "CUENTA_AHORRO", "MOVIMIENTO", "1:N", P, T,
    fk=("MOVIMIENTO", [("num_cuenta", "num_cuenta")]))
# DECISIÓN: parcial; los movimientos batch (intereses, desembolso) no tienen canal.
rel("R12", "CANALIZA", "CANAL", "MOVIMIENTO", "1:N", P, P,
    fk=("MOVIMIENTO", [("id_canal", "id_canal")]),
    desc="Nulo en procesos batch (intereses).")
rel("R13", "ACUMULA_CUENTA", "CUENTA_AHORRO", "CONSUMO_DIARIO", "1:N", P, T, ident=True)
rel("R14", "ACUMULA_CANAL", "CANAL", "CONSUMO_DIARIO", "1:N", P, T, ident=True)
# TARJETAS
rel("R15", "FIJA_TOPE", "CANAL", "LIMITE_CANAL", "1:N", T, T, ident=True,
    desc="Un tope por canal y moneda.")
rel("R16", "POSEE", "CLIENTE", "TARJETA", "1:N", P, T,
    fk=("TARJETA", [("cod_cliente", "cod_cliente")]))
rel("R17", "VINCULA", "TARJETA", "CUENTA_AHORRO", "N:M", T, P,
    attrs=["es_principal", "habilitada_atm", "fecha_vinculacion"], nm="TARJETA_CUENTA",
    desc="Una tarjeta opera una o más cuentas (RN-ATM-005).")
rel("R18", "PROTEGE", "TARJETA", "CREDENCIAL", "1:N", P, T, ident=True,
    desc="Hasta dos credenciales por tarjeta.")
rel("R19", "ASIGNA_MATRIZ", "TARJETA", "MATRIZ_TOKEN", "1:N", P, T,
    fk=("MATRIZ_TOKEN", [("id_tarjeta", "id_tarjeta")]),
    desc="Solo una matriz ACTIVA por tarjeta.")
rel("R20", "CONTIENE", "MATRIZ_TOKEN", "MATRIZ_COORDENADA", "1:N", T, T, ident=True,
    desc="Exactamente 70 coordenadas por matriz.")
rel("R21", "TOKENIZA", "TARJETA", "TOKEN_PAGO", "1:N", P, T,
    fk=("TOKEN_PAGO", [("id_tarjeta", "id_tarjeta")]))
rel("R22", "INTENTA", "TARJETA", "INTENTO_AUTENTICACION", "1:N", P, T,
    fk=("INTENTO_AUTENTICACION", [("id_tarjeta", "id_tarjeta")]))
rel("R23", "RECIBE_INTENTO", "CANAL", "INTENTO_AUTENTICACION", "1:N", P, T,
    fk=("INTENTO_AUTENTICACION", [("id_canal", "id_canal")]))
rel("R24", "EMITE", "TARJETA", "AUTORIZACION", "1:N", P, T,
    fk=("AUTORIZACION", [("id_tarjeta", "id_tarjeta")]))
rel("R25", "AFECTA_CUENTA", "CUENTA_AHORRO", "AUTORIZACION", "1:N", P, T,
    fk=("AUTORIZACION", [("num_cuenta", "num_cuenta")]))
rel("R26", "ORIGINA_AUTORIZACION", "CANAL", "AUTORIZACION", "1:N", P, T,
    fk=("AUTORIZACION", [("id_canal", "id_canal")]))
# DECISIÓN: autorización y movimiento son hechos distintos enlazados 1:1.
rel("R27", "EJECUTA", "AUTORIZACION", "MOVIMIENTO", "1:1", P, P,
    fk=("AUTORIZACION", [("uuid_transaccion", "uuid_transaccion")]),
    desc="Reemplaza a `num_asiento_core`; las consultas no generan movimiento.")
rel("R28", "HISTORIZA", "TARJETA", "HISTORIAL_ESTADO_TARJETA", "1:N", T, T,
    fk=("HISTORIAL_ESTADO_TARJETA", [("id_tarjeta", "id_tarjeta")]),
    desc="La emisión ya genera la primera fila.")
rel("R29", "NOTIFICA", "TARJETA", "EVENTO_SALIDA", "1:N", T, T,
    fk=("EVENTO_SALIDA", [("id_tarjeta", "id_tarjeta")]))
# SOLICITUD
rel("R30", "SOLICITA", "CLIENTE", "SOLICITUD_CREDITO", "1:N", P, T,
    fk=("SOLICITUD_CREDITO", [("cod_cliente", "cod_cliente")]))
rel("R31", "TRAZA", "SOLICITUD_CREDITO", "HISTORIAL_ESTADO_SOLICITUD", "1:N", T, T,
    fk=("HISTORIAL_ESTADO_SOLICITUD", [("id_solicitud", "id_solicitud")]))
rel("R32", "GARANTIZA", "SOLICITUD_CREDITO", "GARANTIA", "1:N", P, T,
    fk=("GARANTIA", [("id_solicitud", "id_solicitud")]))
# DECISIÓN: N:M; un fiador puede respaldar varias solicitudes (I11).
rel("R33", "RESPALDA", "FIADOR", "SOLICITUD_CREDITO", "N:M", T, P,
    attrs=["id_verificacion"], nm="FIADOR_SOLICITUD",
    desc="Un mismo fiador puede respaldar varias solicitudes.")
rel("R34", "PROGRAMA", "SOLICITUD_CREDITO", "CALENDARIO_PAGO", "1:N", T, T,
    fk=("CALENDARIO_PAGO", [("id_solicitud", "id_solicitud")]),
    desc="Simulaciones preliminares y calendario oficial (RN-SOL-006).")
rel("R35", "DETALLA", "CALENDARIO_PAGO", "CUOTA", "1:N", T, T, ident=True)
# EVALUACIÓN
rel("R36", "REPORTA", "CLIENTE", "SITUACION_FINANCIERA", "1:N", P, T,
    fk=("SITUACION_FINANCIERA", [("cod_cliente", "cod_cliente")]))
rel("R37", "EVALUA", "SOLICITUD_CREDITO", "EVALUACION", "1:N", P, T,
    fk=("EVALUACION", [("id_solicitud", "id_solicitud")]),
    desc="Una evaluación por ronda.")
rel("R38", "SUSTENTA", "SITUACION_FINANCIERA", "EVALUACION", "1:N", P, T,
    fk=("EVALUACION", [("id_consulta", "id_consulta")]))
rel("R39", "APLICA_REGLA", "REGLA_EVALUACION", "EVALUACION", "1:N", P, T,
    fk=("EVALUACION", [("id_regla", "id_regla")]))
rel("R40", "ASIGNADA_A", "ANALISTA", "EVALUACION", "1:N", P, P,
    fk=("EVALUACION", [("id_analista", "id_analista")]),
    desc="Solo cuando el resultado es OBSERVADO.")
rel("R41", "RESUELVE", "EVALUACION", "DECISION_ANALISTA", "1:1", P, T,
    fk=("DECISION_ANALISTA", [("id_evaluacion", "id_evaluacion")]))
rel("R42", "DECIDE", "ANALISTA", "DECISION_ANALISTA", "1:N", P, T,
    fk=("DECISION_ANALISTA", [("id_analista", "id_analista")]))
# DESEMBOLSO
rel("R43", "APRUEBA", "EVALUACION", "ORDEN_DESEMBOLSO", "1:N", P, T,
    fk=("ORDEN_DESEMBOLSO", [("id_evaluacion", "id_evaluacion")]),
    desc="Antes `aprobacion_id`; varias órdenes por aprobación, solo una CONFIRMADA.")
rel("R44", "DESEMBOLSA", "SOLICITUD_CREDITO", "ORDEN_DESEMBOLSO", "1:N", P, T,
    fk=("ORDEN_DESEMBOLSO", [("id_solicitud", "id_solicitud")]),
    desc="Antes `credito_id`, referencia a Solicitud de Crédito (11).")
rel("R45", "BENEFICIA", "CLIENTE", "ORDEN_DESEMBOLSO", "1:N", P, T,
    fk=("ORDEN_DESEMBOLSO", [("cod_cliente", "cod_cliente")]),
    desc="Antes `cliente_id`, titular validado.")
rel("R46", "DESTINA", "CUENTA_AHORRO", "ORDEN_DESEMBOLSO", "1:N", P, T,
    fk=("ORDEN_DESEMBOLSO", [("num_cuenta", "num_cuenta")]))
rel("R47", "ORIGINA_ORDEN", "CANAL", "ORDEN_DESEMBOLSO", "1:N", P, T,
    fk=("ORDEN_DESEMBOLSO", [("id_canal", "id_canal")]))
rel("R48", "PREPARA", "AGENCIA", "ORDEN_DESEMBOLSO", "1:N", P, P,
    fk=("ORDEN_DESEMBOLSO", [("id_agencia", "id_agencia")]))
rel("R49", "VERIFICA", "ORDEN_DESEMBOLSO", "VALIDACION_DESEMBOLSO", "1:N", P, T,
    fk=("VALIDACION_DESEMBOLSO", [("id_orden", "id_orden")]))
rel("R50", "PUBLICA", "ORDEN_DESEMBOLSO", "EVENTO_ENTREGA", "1:N", P, T,
    fk=("EVENTO_ENTREGA", [("id_orden", "id_orden")]))
rel("R51", "PIDE_REVERSION", "ORDEN_DESEMBOLSO", "SOLICITUD_REVERSION", "1:N", P, T,
    fk=("SOLICITUD_REVERSION", [("id_orden", "id_orden")]))
rel("R52", "ABONA", "ORDEN_DESEMBOLSO", "MOVIMIENTO", "1:1", P, P,
    fk=("ORDEN_DESEMBOLSO", [("uuid_transaccion_abono", "uuid_transaccion")]),
    desc="Reemplaza a `core_operacion_id`; solo la orden CONFIRMADA abona.")
rel("R53", "EXTORNA", "SOLICITUD_REVERSION", "MOVIMIENTO", "1:1", P, P,
    fk=("SOLICITUD_REVERSION", [("uuid_transaccion_extorno", "uuid_transaccion")]),
    desc="Reemplaza a `core_reversion_id`.")
# COBRANZA
# DECISIÓN: el crédito nace de la orden de desembolso confirmada (RF-COB-015),
#   no directamente de la solicitud (I15).
rel("R54", "FORMALIZA", "ORDEN_DESEMBOLSO", "CREDITO", "1:1", P, T,
    fk=("CREDITO", [("id_orden", "id_orden")]),
    desc="Cobranza recibe el crédito activado por Desembolso (RF-COB-015).")
rel("R55", "ADEUDA", "CLIENTE", "CREDITO", "1:N", P, T,
    fk=("CREDITO", [("cod_cliente", "cod_cliente")]),
    desc="Antes `idCliente` en el `CREDITO` de COBRANZA.")
# DECISIÓN: enlaza el crédito con su calendario OFICIAL y VIGENTE (I7).
rel("R56", "SE_RIGE_POR", "CREDITO", "CALENDARIO_PAGO", "1:1", T, P,
    fk=("CREDITO", [("id_calendario", "id_calendario")]),
    desc="Calendario OFICIAL y VIGENTE del crédito.")
rel("R57", "RECIBE_PAGO", "CREDITO", "PAGO", "1:N", P, T,
    fk=("PAGO", [("cod_credito", "cod_credito")]))
rel("R58", "CANAL_DE_PAGO", "CANAL", "PAGO", "1:N", P, T,
    fk=("PAGO", [("id_canal", "id_canal")]))
rel("R59", "APLICA", "PAGO", "CUOTA", "N:M", T, P,
    attrs=["monto_aplicado"], nm="APLICACION_PAGO",
    desc="Pagos parciales o que cubren varias cuotas.")
rel("R60", "GENERA_MORA", "CUOTA", "MORA", "1:N", P, T,
    fk=("MORA", [("id_calendario", "id_calendario"), ("numero_cuota", "numero_cuota")]),
    desc="Una fila por cada recálculo del CORE.")

# ---------------------------------------------------------------------------
# Relational schema representation
#   attribute: dict(name, pk, fk=(target, group) or None, null)
# ---------------------------------------------------------------------------


def ra(name, pk=False, fk=None, grp=None, null=False):
    return dict(name=name, pk=pk, fk=fk, grp=grp, null=null)


def flat(attrs):
    out = []
    for a in attrs:
        if a["mv"]:
            continue
        if a["comp"]:
            for c, _ in a["comp"]:
                out.append(ra(c, pk=a["key"] in ("PK", "PP")))
        else:
            out.append(ra(a["name"], pk=a["key"] in ("PK", "PP")))
    return out


def pk_of(schema, name):
    return [x for x in schema[name] if x["pk"]]


SCHEMA = {}      # relation -> list of attrs
ORIGIN = {}      # relation -> list of steps
STEP = {k: [] for k in range(1, 8)}
STEP_FK = {3: [], 4: []}

# Step 1: strong entities
for n in ORDER:
    if E[n]["kind"] == "fuerte":
        SCHEMA[n] = flat(E[n]["attrs"])
        ORIGIN[n] = [1]
        STEP[1].append(n)

# Step 2: weak entities (owners must already exist; iterate until done)
weak = [n for n in ORDER if E[n]["kind"] == "débil"]
for n in weak:
    attrs = []
    for owner, _ in E[n]["owners"]:
        opks = pk_of(SCHEMA, owner)
        for k in opks:
            attrs.append(ra(k["name"], pk=True, fk=owner,
                            grp=owner + n if len(opks) > 1 else None))
    attrs += flat(E[n]["attrs"])
    SCHEMA[n] = attrs
    ORIGIN[n] = [2]
    STEP[2].append(n)
SNAP2 = copy.deepcopy(SCHEMA)

# Steps 3 and 4
for r in R:
    if r["card"] in ("1:1", "1:N") and not r["ident"]:
        side, pairs = r["fk"][0], r["fk"][1]
        other = r["e1"] if side == r["e2"] else r["e2"]
        if r["e1"] == r["e2"]:
            other = r["e1"]
        # nullability: participation of the side receiving the FK
        part = r["p2"] if side == r["e2"] else r["p1"]
        if r["e1"] == r["e2"]:
            part = P
        null = part == P
        grp = r["id"] if len(pairs) > 1 else None
        for fa, _ in pairs:
            SCHEMA[side].append(ra(fa, fk=other, grp=grp, null=null))
        step = 3 if r["card"] == "1:1" else 4
        if step not in ORIGIN[side]:
            ORIGIN[side].append(step)
        STEP_FK[step].append(dict(rel=r, side=side, other=other, pairs=pairs, null=null))

# Step 5: N:M
for r in R:
    if r["card"] == "N:M":
        attrs = []
        for e in (r["e1"], r["e2"]):
            pks = pk_of(SCHEMA, e)
            g = r["id"] + e if len(pks) > 1 else None
            for k in pks:
                attrs.append(ra(k["name"], pk=True, fk=e, grp=g))
        attrs += [ra(x) for x in r["attrs"]]
        SCHEMA[r["nm"]] = attrs
        ORIGIN[r["nm"]] = [5]
        STEP[5].append(r["nm"])

# Step 6: multivalued attributes
MV = []
for n in ORDER:
    for a in E[n]["attrs"]:
        if a["mv"]:
            rn = n + "_" + a["name"].upper().split("_")[0]
            rn = "CANAL_VALIDACION" if n == "CANAL" else rn
            attrs = [ra(k["name"], pk=True, fk=n) for k in pk_of(SCHEMA, n)]
            attrs.append(ra(a["name"].replace("validacion_requerida", "tipo_validacion"), pk=True))
            SCHEMA[rn] = attrs
            ORIGIN[rn] = [6]
            STEP[6].append(rn)
            MV.append((n, a, rn))

MR_ORDER = STEP[1] + STEP[2] + STEP[5] + STEP[6]
STAGES = {"mr": copy.deepcopy(SCHEMA)}

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
S = copy.deepcopy(SCHEMA)


def drop(rel_, *names):
    S[rel_] = [a for a in S[rel_] if a["name"] not in names]


def replace(rel_, old, new_attrs):
    i = [a["name"] for a in S[rel_]].index(old)
    S[rel_][i:i + 1] = new_attrs


def insert_after(rel_, after, new_attrs):
    i = [a["name"] for a in S[rel_]].index(after)
    S[rel_][i + 1:i + 1] = new_attrs


def set_fk(rel_, name, target):
    for a in S[rel_]:
        if a["name"] == name:
            a["fk"] = target


NEW = {}  # relation -> (stage, purpose)

# 1FN ----------------------------------------------------------------------
# coordenada_solicitada empaqueta fila y columna ("D-4").
replace("INTENTO_AUTENTICACION", "coordenada_solicitada",
        [ra("coord_fila", null=True), ra("coord_columna", null=True)])
# id_terminal mezcla dos dominios: código de terminal física e IP de origen.
for _r in ("INTENTO_AUTENTICACION", "AUTORIZACION"):
    replace(_r, "id_terminal", [ra("id_terminal", null=True), ra("ip_origen", null=True)])
# id_entidad mezcla identificadores de orden, crédito, pago y cuota.
# DECISIÓN: discriminante tipo_entidad; la cuota (clave compuesta) se
#   referencia con id_entidad = id_calendario más numero_cuota.
replace("EVENTO_AUDITORIA", "id_entidad", [
    ra("tipo_entidad", null=True), ra("id_entidad", null=True),
    ra("numero_cuota", null=True)])
STAGES["n1"] = copy.deepcopy(S)

# 2FN ----------------------------------------------------------------------
drop("CREDENCIAL", "longitud")                       # tipo_credencial -> longitud
S["TIPO_CREDENCIAL"] = [ra("tipo_credencial", pk=True), ra("longitud", null=True)]
set_fk("CREDENCIAL", "tipo_credencial", "TIPO_CREDENCIAL")
NEW["TIPO_CREDENCIAL"] = "2FN"
drop("LIMITE_CANAL", "regla_negocio")                # id_canal -> regla_negocio
insert_after("CANAL", "activo", [ra("regla_tope")])
drop("TITULARIDAD", "rol_titular")                   # num_cuenta -> rol_titular
STAGES["n2"] = copy.deepcopy(S)

# 3FN ----------------------------------------------------------------------
drop("CUENTA_CONTABLE", "nivel")                     # codigo_padre -> nivel
drop("CLIENTE", "fecha_verificacion", "estado_habilitante")
set_fk("CLIENTE", "id_verificacion_captacion", "VERIFICACION_CAPTACION")
S["VERIFICACION_CAPTACION"] = [ra("id_verificacion_captacion", pk=True),
                               ra("fecha_verificacion"), ra("estado_habilitante")]
NEW["VERIFICACION_CAPTACION"] = "3FN"
drop("CODIGO_VERIFICACION", "destino")               # (cliente, tipo) -> destino
drop("MOVIMIENTO", "tipo_movimiento")                # tipo_operacion -> tipo_movimiento
set_fk("MOVIMIENTO", "tipo_operacion", "TIPO_OPERACION")
S["TIPO_OPERACION"] = [ra("tipo_operacion", pk=True), ra("naturaleza")]
NEW["TIPO_OPERACION"] = "3FN"
drop("TARJETA", "vencimiento_mm_aa")                 # fecha_vencimiento -> mm/aa
drop("TARJETA", "tipo_tarjeta")                      # bin -> tipo_tarjeta
set_fk("TARJETA", "bin", "BIN_TARJETA")
S["BIN_TARJETA"] = [ra("bin", pk=True), ra("tipo_tarjeta"), ra("descripcion")]
NEW["BIN_TARJETA"] = "3FN"
for _r in ("INTENTO_AUTENTICACION", "AUTORIZACION"):  # id_terminal -> id_canal
    set_fk(_r, "id_terminal", "TERMINAL")
    for a in S[_r]:
        if a["name"] == "id_canal":
            a["null"] = True
S["TERMINAL"] = [ra("id_terminal", pk=True), ra("descripcion"), ra("activo"),
                 ra("id_canal", fk="CANAL"), ra("id_agencia", fk="AGENCIA", null=True)]
NEW["TERMINAL"] = "3FN"
drop("AUTORIZACION", "moneda")                       # num_cuenta -> moneda
drop("CUOTA", "importe_total")                       # capital+interes+otros
drop("EVALUACION", "ratio_monto_limite", "resultado", "tipo_resultado")
drop("ORDEN_DESEMBOLSO", "id_solicitud", "cod_cliente", "aprobacion_version", "moneda")
drop("VALIDACION_DESEMBOLSO", "proveedor")           # tipo_validacion -> proveedor
set_fk("VALIDACION_DESEMBOLSO", "tipo_validacion", "TIPO_VALIDACION_DESEMBOLSO")
S["TIPO_VALIDACION_DESEMBOLSO"] = [ra("tipo_validacion", pk=True), ra("descripcion"),
                                   ra("id_modulo_proveedor")]
NEW["TIPO_VALIDACION_DESEMBOLSO"] = "3FN"
drop("EVENTO_SALIDA", "modulo_destino")              # tipo_evento -> modulo_destino
set_fk("EVENTO_SALIDA", "tipo_evento", "TIPO_EVENTO_SALIDA")
S["TIPO_EVENTO_SALIDA"] = [ra("tipo_evento", pk=True), ra("descripcion"), ra("id_modulo_destino")]
NEW["TIPO_EVENTO_SALIDA"] = "3FN"
drop("MORA", "dias_atraso")                          # (cuota, fecha_calculo) -> dias
drop("EVENTO_AUDITORIA", "tipo_entidad")             # id_entidad -> tipo_entidad
set_fk("EVENTO_AUDITORIA", "id_entidad", "ENTIDAD_AUDITADA")
S["ENTIDAD_AUDITADA"] = [ra("id_entidad", pk=True), ra("tipo_entidad")]
NEW["ENTIDAD_AUDITADA"] = "3FN"
STAGES["n3"] = copy.deepcopy(S)

# Redundancia entre relaciones y entre filas (fuera de las formas normales)
drop("CREDITO", "cod_cliente", "moneda", "monto_aprobado", "fecha_desembolso")
drop("ORDEN_DESEMBOLSO", "fecha_efectiva", "entrega_estado")
drop("DECISION_ANALISTA", "id_analista")
drop("TARJETA", "motivo_estado", "origen_ultimo_cambio", "fecha_ultimo_cambio")
drop("HISTORIAL_ESTADO_TARJETA", "estado_anterior")
drop("HISTORIAL_ESTADO_SOLICITUD", "estado_anterior")
drop("MORA", "vigente")
drop("ASIENTO_CONTABLE", "estado_asiento")
STAGES["dep"] = copy.deepcopy(S)

# ---------------------------------------------------------------------------
# Catalog extraction after 3FN
#   (table, [(attr, flags)], [(relation, attribute)], criteria, note)
# ---------------------------------------------------------------------------
# DECISIÓN: las columnas adicionales de cada catálogo parametrizan reglas de
#   negocio de las fuentes (longitudes, intentos, umbrales, permisos).
CATALOGS = [
    ("MONEDA", ["cod_moneda", "nombre", "simbolo", "decimales"],
     [("CUENTA_AHORRO", "moneda"), ("LIMITE_CANAL", "moneda"), ("ASIENTO_CONTABLE", "moneda"),
      ("SOLICITUD_CREDITO", "moneda"), ("GARANTIA", "moneda")],
     "C1, C2", "Parámetro del CORE junto con los tipos de cambio; código ISO 4217."),
    ("TIPO_DOCUMENTO", ["cod_tipo_documento", "descripcion", "longitud_min", "longitud_max", "es_alfanumerico"],
     [("CLIENTE", "tipo_documento"), ("FIADOR", "tipo_documento")],
     "C1, C2", "DNI de 8 dígitos, PTP de 9, pasaporte alfanumérico de hasta 12 (RN-CLI-001)."),
    ("TIPO_BIOMETRIA", ["cod_tipo_biometria", "descripcion", "umbral_similitud"],
     [("BIOMETRIA_CLIENTE", "tipo_biometria")],
     "C2, C3", "El umbral de similitud es el punto abierto R-03 de CLIENTES."),
    ("TIPO_CONTACTO", ["cod_tipo_contacto", "descripcion", "vigencia_minutos", "max_intentos"],
     [("CODIGO_VERIFICACION", "tipo_contacto")],
     "C2", "Parametriza la expiración y el bloqueo al tercer intento (RF-CLI-005)."),
    ("TIPO_VALIDACION", ["cod_tipo_validacion", "descripcion", "endpoint"],
     [("VALIDACION_IDENTIDAD", "tipo_validacion")],
     "C2, C4", "Los cinco flujos de KYC y su endpoint `/api/v1/kyc/...`."),
    ("REGIMEN_CUENTA", ["cod_regimen", "descripcion", "min_titulares", "firma_conjunta"],
     [("CUENTA_AHORRO", "regimen")],
     "C2", "Indistinta (o) y conjunta (y) cambian la regla de autorización (RN-CTA-002)."),
    ("ESTADO_CUENTA", ["cod_estado", "descripcion", "permite_debito", "permite_credito"],
     [("CUENTA_AHORRO", "estado_cuenta")],
     "C2", "BLOQUEADA_PREVENTIVA impide débitos pero no abonos."),
    ("ESTADO_TARJETA", ["cod_estado", "descripcion", "es_operativa", "es_final"],
     [("TARJETA", "estado_tarjeta"), ("HISTORIAL_ESTADO_TARJETA", "estado_nuevo")],
     "C1, C2", "Sustituye el cálculo de `operativa` de la vista `v_tarjeta_resumen`."),
    ("ESTADO_CLIENTE", ["cod_estado", "descripcion", "permite_operar"],
     [("CLIENTE", "estado_cliente")],
     "C3", "Los módulos usan listas distintas (ACTIVO/BLOQUEADO/SUSPENDIDO frente a OBSERVADO/BAJA)."),
    ("ESTADO_SOLICITUD", ["cod_estado", "descripcion", "es_final"],
     [("SOLICITUD_CREDITO", "estado_solicitud"), ("HISTORIAL_ESTADO_SOLICITUD", "estado_nuevo")],
     "C1, C3", "Dominio usado por la solicitud y por su historial."),
    ("ESTADO_ORDEN", ["cod_estado", "descripcion", "es_final"],
     [("ORDEN_DESEMBOLSO", "estado_orden")],
     "C2", "Base para la tabla de transiciones válidas (figura 2 de DESEMBOLSO)."),
    ("ESTADO_CREDITO", ["cod_estado", "descripcion"],
     [("CREDITO", "estado_credito")],
     "C3", "Catálogo pendiente de aprobación según COBRANZA."),
    ("ESTADO_CUOTA", ["cod_estado", "descripcion"],
     [("CUOTA", "estado_cuota")],
     "C3", "Catálogo pendiente de aprobación según COBRANZA."),
    ("TIPO_OPERACION", None,
     [("AUTORIZACION", "tipo_operacion")],
     "C1", "Tabla creada en 3FN; ahora también la referencia AUTORIZACION."),
    ("TIPO_CREDENCIAL", None,
     [("INTENTO_AUTENTICACION", "tipo_credencial"), ("CANAL_VALIDACION", "tipo_validacion")],
     "C1", "Tabla creada en 2FN; se amplía con TOKEN_MATRIZ, BIOMETRIA y TOKEN_PAGO."),
    ("CODIGO_RESPUESTA", ["cod_respuesta", "descripcion", "es_aprobacion"],
     [("AUTORIZACION", "codigo_respuesta")],
     "C2, C4", "00 aprobado, 54 tarjeta vencida, EXT extorno."),
    ("ORIGEN_CAMBIO", ["cod_origen", "descripcion", "puede_desbloquear"],
     [("HISTORIAL_ESTADO_TARJETA", "origen")],
     "C2", "Solo OPERADOR y SEGURIDAD pueden desbloquear (RN-TAR-004)."),
    ("TIPO_GARANTIA", ["cod_tipo_garantia", "descripcion"],
     [("GARANTIA", "tipo_garantia")],
     "C3", "Lista abierta en la fuente (`p. ej.`)."),
    ("METODO_AMORTIZACION", ["cod_metodo", "descripcion"],
     [("CALENDARIO_PAGO", "metodo_amortizacion")],
     "C3", "Lista abierta en la fuente (`p. ej.`)."),
    ("RESULTADO_CREDITICIO", ["cod_resultado", "descripcion"],
     [("REGLA_EVALUACION", "accion"), ("DECISION_ANALISTA", "decision")],
     "C1", "APROBADO, OBSERVADO y RECHAZADO son el dominio oficial del Diccionario de Reglas."),
    ("MODULO", ["id_modulo", "nombre"],
     [("TIPO_EVENTO_SALIDA", "id_modulo_destino"), ("EVENTO_AUDITORIA", "modulo_emisor"),
      ("TIPO_VALIDACION_DESEMBOLSO", "id_modulo_proveedor")],
     "C1, C4", "Numeración oficial: CORE (1), CLIENTES (2), CUENTAS (3), ..., COBRANZA (14)."),
    ("PASARELA_PAGO", ["id_pasarela", "nombre"],
     [("TOKEN_PAGO", "proveedor_pasarela")],
     "C3", "Punto abierto R-05 sobre la propiedad de las pasarelas."),
]

for tbl, cols, uses, _, _ in CATALOGS:
    if cols:
        S[tbl] = [ra(cols[0], pk=True)] + [ra(c) for c in cols[1:]]
        NEW[tbl] = "cat"
    for r_, a_ in uses:
        set_fk(r_, a_, tbl)
STAGES["fin"] = copy.deepcopy(S)

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render(attrs, show_fk=True):
    parts, done = [], set()
    for a in attrs:
        if a["grp"] and show_fk and a["fk"]:
            if a["grp"] in done:
                continue
            members = [x for x in attrs if x["grp"] == a["grp"]]
            done.add(a["grp"])
            inner = ", ".join(
                (r"\underline{%s}" % tt(m["name"])) if m["pk"] else tt(m["name"])
                for m in members)
            parts.append(r"(%s)~\textsc{fk}~%s" % (inner, relname(a["fk"])))
            continue
        s = (r"\underline{%s}" % tt(a["name"])) if a["pk"] else tt(a["name"])
        if a["fk"] and show_fk:
            s += r"~\textsc{fk}~%s" % relname(a["fk"])
        parts.append(s)
    return ", ".join(parts)


def rel_line(name, attrs):
    return r"%s (%s)" % (relname(name), render(attrs))


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def gen(out):
    os.makedirs(out, exist_ok=True)
    hdr = "% Generated by model.py -- the integrated BNA data model.\n"

    # --- stage macros: \Rel{stage}{NAME}
    lines = [hdr]
    for st, sch in STAGES.items():
        for n, attrs in sch.items():
            lines.append(r"\expandafter\def\csname rel:%s:%s\endcsname{%s}" % (st, n, rel_line(n, attrs)))
    write(os.path.join(out, "rel-macros.tex"), "\n".join(lines) + "\n")

    # --- MER: entity summary
    rows = []
    for code, label in MODULES:
        ents = [n for n in ORDER if E[n]["module"] == code]
        if not ents:
            continue
        rows.append(r"\multicolumn{4}{l}{\textit{%s}} \\" % esc(label))
        for n in ents:
            e = E[n]
            if e["kind"] == "débil":
                own = "; ".join(r"%s (%s)" % (ttb(o), ttb(rr)) for o, rr in e["owners"])
                pp = [a for a in e["attrs"] if a["key"] == "PP"][0]
                pk = r"Propietario: %s. Clave parcial: %s" % (own, tt(pp["name"]))
            else:
                pk = r"Clave: %s" % tt([a for a in e["attrs"] if a["key"] == "PK"][0]["name"])
            rows.append(r"%s & %s & %s & %s \\" % (ttb(n), "Débil" if e["kind"] == "débil" else "Fuerte",
                                                   pk, esc(e["src"])))
    write(os.path.join(out, "mer-entidades.tex"), hdr + "\n".join(rows) + "\n")

    # --- MER: attributes per module
    for code, label in MODULES:
        ents = [n for n in ORDER if E[n]["module"] == code]
        rows = []
        for n in ents:
            e = E[n]
            if rows:
                # space, not \midrule: a page break can only fall before this
                # separator, and a rule there would double the repeated
                # header's rule at the top of the next page.
                rows.append(r"\addlinespace[0.6em]")
            kind = " (entidad débil)" if e["kind"] == "débil" else ""
            rows.append(r"\multicolumn{6}{@{}p{\linewidth}@{}}{\textbf{%s}%s --- %s} \\*" % (tt(n), kind, md(e["desc"])))
            for a in e["attrs"]:
                key = {"PK": "PK", "PP": "Parcial", "UK": "UK", "": ""}[a["key"]]
                name = ttb(a["name"])
                if a["mv"]:
                    name = r"\{%s\}" % name
                if a["der"]:
                    name = r"/%s" % name
                rows.append(r"%s & %s & %s & %s & %s & %s \\" % (
                    name, key, "C" if a["comp"] else "S", "MV" if a["mv"] else "M",
                    "D" if a["der"] else "A", md(a["desc"])))
                for c, d in a["comp"] or []:
                    rows.append(r"\quad$\llcorner$\,%s &  & S & M & A & %s \\" % (ttb(c), md(d)))
        write(os.path.join(out, "mer-atributos-%s.tex" % code.lower()), hdr + "\n".join(rows) + "\n")

    # --- MER: relationships
    rows = []
    for r in R:
        e1, e2 = ttb(r["e1"]), ttb(r["e2"])
        if r["roles"]:
            e1 += r" (%s)" % r["roles"][0]
            e2 += r" (%s)" % r["roles"][1]
        kind = "Ident." if r["ident"] else ("Recur." if r["e1"] == r["e2"] else "Reg.")
        note = []
        if r["attrs"]:
            note.append(r"Atributos: %s." % ", ".join(tt(x) for x in r["attrs"]))
        if r["desc"]:
            note.append(md(r["desc"]))
        rows.append(r"%s & %s & %s --- %s & %s & %s\,/\,%s & %s \\%s" % (
            r["id"], ttb(r["name"]), e1, e2, r["card"], r["p1"], r["p2"], kind, "*" if note else ""))
        if note:
            rows.append(r" & \multicolumn{5}{p{\dimexpr\linewidth-1.6cm\relax}}{\footnotesize\itshape %s} \\" % " ".join(note))
    write(os.path.join(out, "mer-relaciones.tex"), hdr + "\n".join(rows) + "\n")

    # --- Step 1 / 2 / 5 / 6 blocks
    for st in (1, 2, 5, 6):
        blocks = []
        for n in STEP[st]:
            if st == 1:
                attrs = flat(E[n]["attrs"])
            elif st == 2:
                attrs = SNAP2[n]
            else:
                attrs = SCHEMA[n]
            blocks.append(rel_line(n, attrs) + "\n")
        write(os.path.join(out, "paso%d.tex" % st), hdr + "\\begin{quote}\\raggedright\n" +
              "\n".join(blocks) + "\\end{quote}\n")

    # --- Step 3 / 4 tables
    for st in (3, 4):
        rows = []
        for x in STEP_FK[st]:
            r = x["rel"]
            fks = ", ".join(ttb(a) for a, _ in x["pairs"])
            ref = relname(x["other"])
            cons = "NULL" if x["null"] else "NOT NULL"
            if st == 3:
                cons += ", UNIQUE"
            rows.append(r"%s %s & %s & %s & %s & %s \\" % (r["id"], ttb(r["name"]), r["card"],
                                                          relname(x["side"]), r"%s $\rightarrow$ %s" % (fks, ref), cons))
        write(os.path.join(out, "paso%d.tex" % st), hdr + "\n".join(rows) + "\n")

    # --- Resulting MR (after step 7)
    stepname = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6"}
    rows = []
    for n in MR_ORDER:
        rows.append(r"%s & (%s) & %s \\" % (relname(n), render(SCHEMA[n]),
                                         ", ".join(stepname[s] for s in sorted(ORIGIN[n]))))
    write(os.path.join(out, "mr-resultante.tex"), hdr + "\n".join(rows) + "\n")

    # --- Catalog table
    rows = []
    for tbl, cols, uses, crit, note in CATALOGS:
        src = "; ".join(r"%s.%s" % (relname(r_), ttb(a_)) for r_, a_ in uses)
        tcols = ", ".join(ttb(c) for c in cols) if cols else r"\textit{(ya existe)}"
        rows.append(r"%s & %s & %s & %s & %s \\" % (relname(tbl), tcols, src, crit, md(note)))
    write(os.path.join(out, "catalogos.tex"), hdr + "\n".join(rows) + "\n")

    # --- Final schema
    fin = STAGES["fin"]
    order = [n for n in MR_ORDER] + [n for n in fin if n not in MR_ORDER]
    rows = []
    for n in order:
        tag = NEW.get(n, "")
        tag = {"2FN": "2FN", "3FN": "3FN", "cat": "Catálogo", "": ""}[tag]
        rows.append(r"%s & (%s) & %s \\" % (relname(n), render(fin[n]), tag))
    write(os.path.join(out, "esquema-final.tex"), hdr + "\n".join(rows) + "\n")

    # --- Stats
    stats = dict(
        entidades=len(E), fuertes=len(STEP[1]), debiles=len(STEP[2]), relaciones=len(R),
        r11=len([r for r in R if r["card"] == "1:1"]), r1n=len([r for r in R if r["card"] == "1:N"]),
        rnm=len([r for r in R if r["card"] == "N:M"]), ident=len([r for r in R if r["ident"]]),
        mr=len(MR_ORDER), fin=len(fin), catalogos=len([c for c in CATALOGS if c[1]]),
        paso3=len(STEP_FK[3]), paso4=len(STEP_FK[4]),
        attrs=sum(len(E[n]["attrs"]) for n in E),
        comp=sum(1 for n in E for a in E[n]["attrs"] if a["comp"]),
        mv=sum(1 for n in E for a in E[n]["attrs"] if a["mv"]),
        der=sum(1 for n in E for a in E[n]["attrs"] if a["der"]),
    )
    write(os.path.join(out, "stats.tex"), hdr + "\n".join(
        r"\expandafter\def\csname stat:%s\endcsname{%d}" % (k, v) for k, v in stats.items()) + "\n")
    return stats


if __name__ == "__main__":
    st = gen(sys.argv[1])
    import diagramas_mer  # noqa: E402  (imports this module by name)
    diagramas_mer.gen(sys.argv[1])
    import ddl_bna  # noqa: E402
    sql = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql", "bna_core.sql")
    ddl_bna.gen(sql)
    write(os.path.join(sys.argv[1], "verificacion-final.tex"),
          "% Generated by ddl_bna.py\n" + ddl_bna.verification_rows())
    txt = open(sql, encoding="utf-8").read()
    extra = dict(n3=len(STAGES["n3"]), tablas=txt.count("CREATE TABLE "),
                 fks=txt.count("FOREIGN KEY"), fkcompuestas=len(re.findall(r"FOREIGN KEY \([^)]*,[^)]*\)", txt)), indices=txt.count("CREATE INDEX ") + txt.count("CREATE UNIQUE INDEX "),
                 parciales=txt.count("CREATE UNIQUE INDEX "), semillas=txt.count("\nINSERT INTO "),
                 consultas=len(ddl_bna.QUERY_INDEXES),
                 triggers=txt.count("CREATE TRIGGER ") + txt.count("CREATE CONSTRAINT TRIGGER "),
                 funciones=txt.count("CREATE FUNCTION "), vistas=txt.count("CREATE VIEW "),
                 lineassql=txt.count("\n"))
    with open(os.path.join(sys.argv[1], "stats.tex"), "a", encoding="utf-8") as f:
        f.write("\n".join(r"\expandafter\def\csname stat:%s\endcsname{%d}" % kv for kv in extra.items()) + "\n")
    for k, v in st.items():
        print(k, v)
    # sanity: every FK target exists
    for n, attrs in STAGES["fin"].items():
        for a in attrs:
            if a["fk"] and a["fk"] not in STAGES["fin"]:
                print("MISSING FK TARGET", n, a)
