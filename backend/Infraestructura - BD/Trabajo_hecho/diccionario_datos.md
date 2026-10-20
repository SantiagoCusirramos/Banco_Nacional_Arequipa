# Diccionario de Datos - Base de Datos BNA

Generado: 2026-10-15 | MySQL 8.0/8.4 | InnoDB | utf8mb4

Convencion: PK = clave primaria, FK = clave foranea, UQ = restriccion unica.
Los identificadores (`id_*`) son **UUID v7** almacenados como `CHAR(36)`
(ordenables por tiempo). La aplicacion genera los v7; la base los genera con
`fn_uuid_v7()` solo para las filas que crea ella misma (triggers/procedimientos).

## agencia
*Agencias del banco*

| Columna | Tipo | Clave |
|---|---|---|
| id_agencia | CHAR(36) | PK |
| nombre | VARCHAR(60) | UQ |
| direccion | VARCHAR(120) |  |
| activa | TINYINT(1) |  |

## empleado
*Asesores, analistas, operadores y cajeros*

| Columna | Tipo | Clave |
|---|---|---|
| id_empleado | CHAR(36) | PK |
| codigo_empleado | VARCHAR(20) | UQ |
| nombre_completo | VARCHAR(100) |  |
| cargo | ENUM('ASESOR_CREDITOS','ANALISTA_CREDITO','OPERADOR','CAJERO','ADMINISTRADOR') |  |
| id_agencia | CHAR(36) | FK->agencia |
| activo | TINYINT(1) |  |

## usuario_sistema
*Usuarios del sistema*

| Columna | Tipo | Clave |
|---|---|---|
| id_usuario | CHAR(36) | PK |
| username | VARCHAR(40) | UQ |
| nombre | VARCHAR(100) |  |
| rol | ENUM('ADMINISTRADOR','ASESOR','ANALISTA','OPERADOR','AUDITOR') |  |
| hash_password | CHAR(64) |  |
| algoritmo_hash | VARCHAR(20) |  |
| version_hash | VARCHAR(10) |  |
| id_empleado | CHAR(36) | FK->empleado |
| activo | TINYINT(1) |  |
| creado_en | DATETIME(3) |  |

## tipo_documento
*Catalogo de documentos de identidad*

| Columna | Tipo | Clave |
|---|---|---|
| cod_tipo_documento | VARCHAR(10) | PK |
| descripcion | VARCHAR(50) |  |

## moneda
*Catalogo de monedas*

| Columna | Tipo | Clave |
|---|---|---|
| cod_moneda | CHAR(3) | PK |
| nombre | VARCHAR(30) |  |
| simbolo | VARCHAR(5) |  |
| activa | TINYINT(1) |  |

## tipo_cambio
*Tipos de cambio por fecha*

| Columna | Tipo | Clave |
|---|---|---|
| id_tipo_cambio | CHAR(36) | PK |
| cod_moneda_origen | CHAR(3) | FK->moneda, UQ |
| cod_moneda_destino | CHAR(3) | FK->moneda, UQ |
| fecha | DATE | UQ |
| tasa | DECIMAL(12,6) |  |

## terminal
*Terminales y puntos de atencion*

| Columna | Tipo | Clave |
|---|---|---|
| id_terminal | CHAR(36) | PK |
| codigo | VARCHAR(30) | UQ |
| tipo | ENUM('ATM','AGENTE','POS','WEB','MOVIL') |  |
| ubicacion | VARCHAR(120) |  |
| id_agencia | CHAR(36) | FK->agencia |
| activa | TINYINT(1) |  |

## canal
*Catalogo de canales de atencion*

| Columna | Tipo | Clave |
|---|---|---|
| id_canal | VARCHAR(5) | PK |
| nombre | VARCHAR(40) | UQ |
| es_presencial | TINYINT(1) |  |
| validacion_requerida | ENUM('PIN_ATM','CLAVE_WEB','BIOMETRIA','TOKEN_PAGO') |  |
| requiere_token_matriz | TINYINT(1) |  |
| tipo_integracion | VARCHAR(30) |  |
| activo | TINYINT(1) |  |

## limite_canal
*Topes diarios acumulados por canal y moneda*

| Columna | Tipo | Clave |
|---|---|---|
| id_canal | VARCHAR(5) | PK, FK->canal |
| moneda | CHAR(3) | PK, FK->moneda |
| monto_maximo_diario | DECIMAL(15,2) |  |
| habilitado | TINYINT(1) |  |
| regla_negocio | VARCHAR(20) |  |

## producto_ahorro
*Productos de ahorro*

| Columna | Tipo | Clave |
|---|---|---|
| id_producto_ahorro | CHAR(36) | PK |
| nombre | VARCHAR(60) | UQ |
| moneda | CHAR(3) | FK->moneda, UQ |
| tasa_tea | DECIMAL(6,4) |  |
| activo | TINYINT(1) |  |

## producto_credito
*Productos de credito*

| Columna | Tipo | Clave |
|---|---|---|
| id_producto_credito | CHAR(36) | PK |
| nombre | VARCHAR(60) | UQ |
| tasa_tea | DECIMAL(6,4) |  |
| plazo_min_meses | INT |  |
| plazo_max_meses | INT |  |
| activo | TINYINT(1) |  |

## periodo_contable
*Periodos contables*

| Columna | Tipo | Clave |
|---|---|---|
| id_periodo | CHAR(36) | PK |
| anio | SMALLINT UNSIGNED | UQ |
| mes | TINYINT UNSIGNED | UQ |
| fecha_inicio | DATE |  |
| fecha_fin | DATE |  |
| estado | ENUM('ABIERTO','CERRADO') |  |

## plan_cuenta_contable
*Plan de cuentas contables*

| Columna | Tipo | Clave |
|---|---|---|
| cod_cuenta_contable | VARCHAR(20) | PK |
| nombre | VARCHAR(100) |  |
| naturaleza | ENUM('DEUDORA','ACREEDORA') |  |
| codigo_padre | VARCHAR(20) | FK->plan_cuenta_contable |
| activo | TINYINT(1) |  |

## asiento_contable
*Cabecera de asientos contables*

| Columna | Tipo | Clave |
|---|---|---|
| id_asiento | CHAR(36) | PK |
| id_periodo | CHAR(36) | FK->periodo_contable |
| fecha | DATETIME(3) |  |
| glosa | VARCHAR(200) |  |
| estado | ENUM('REGISTRADO','REVERTIDO') |  |
| id_asiento_rev | CHAR(36) | FK->asiento_contable |

## asiento_detalle
*Detalle de asientos con moneda base*

| Columna | Tipo | Clave |
|---|---|---|
| id_detalle | CHAR(36) | PK |
| id_asiento | CHAR(36) | FK->asiento_contable |
| cod_cuenta_contable | VARCHAR(20) | FK->plan_cuenta_contable |
| debe | DECIMAL(15,2) |  |
| haber | DECIMAL(15,2) |  |
| moneda | CHAR(3) | FK->moneda |
| tipo_cambio | DECIMAL(12,6) |  |
| importe_moneda_base | DECIMAL(15,2) |  |

## auditoria_evento
*Auditoria centralizada de toda la plataforma*

| Columna | Tipo | Clave |
|---|---|---|
| id_evento | CHAR(36) | PK |
| modulo | VARCHAR(20) |  |
| entidad | VARCHAR(40) |  |
| id_entidad | VARCHAR(40) |  |
| accion | VARCHAR(40) |  |
| actor | VARCHAR(40) |  |
| detalle | JSON |  |
| correlation_id | CHAR(36) |  |
| fecha_hora | DATETIME(3) |  |

## cliente
*Clientes del banco*

| Columna | Tipo | Clave |
|---|---|---|
| id_cliente | CHAR(36) | PK |
| cod_tipo_documento | VARCHAR(10) | FK->tipo_documento, UQ |
| numero_documento | VARCHAR(20) | UQ |
| nombres | VARCHAR(80) |  |
| apellido_paterno | VARCHAR(60) |  |
| apellido_materno | VARCHAR(60) |  |
| fecha_nacimiento | DATE |  |
| numero_celular | VARCHAR(15) |  |
| correo_electronico | VARCHAR(120) | UQ |
| estado_cliente | ENUM('ACTIVO','INACTIVO','BLOQUEADO','FALLECIDO') |  |
| fecha_registro | DATETIME(3) |  |

## biometria_cliente
*Plantillas biometricas cifradas del cliente*

| Columna | Tipo | Clave |
|---|---|---|
| id_biometria | CHAR(36) | PK |
| id_cliente | CHAR(36) | FK->cliente |
| tipo_biometria | ENUM('HUELLA','ROSTRO','VOZ','IRIS') |  |
| datos_biometricos | LONGBLOB |  |
| algoritmo_cifrado | VARCHAR(30) |  |
| version_cifrado | VARCHAR(10) |  |
| hash_datos | CHAR(64) |  |
| estado_activo | TINYINT(1) |  |
| fecha_registro | DATETIME(3) |  |

## cli_codigo_verificacion
*Codigos de verificacion OTP*

| Columna | Tipo | Clave |
|---|---|---|
| id_codigo | CHAR(36) | PK |
| id_cliente | CHAR(36) | FK->cliente |
| id_solicitante | CHAR(36) |  |
| destino | VARCHAR(120) |  |
| tipo_contacto | ENUM('SMS','EMAIL') |  |
| codigo_hmac | CHAR(64) |  |
| proposito | ENUM('ALTA_CLIENTE','RECUPERACION','TRANSACCION','CONSULTA') |  |
| intentos_fallidos | TINYINT UNSIGNED |  |
| estado | ENUM('PENDIENTE','USADO','EXPIRADO','BLOQUEADO') |  |
| fecha_creacion | DATETIME(3) |  |
| fecha_expiracion | DATETIME(3) |  |

## cli_auditoria_validacion
*Auditoria de validaciones de identidad*

| Columna | Tipo | Clave |
|---|---|---|
| id_validacion | CHAR(36) | PK |
| id_cliente | CHAR(36) | FK->cliente |
| tipo_validacion | ENUM('RENIEC','BIOMETRIA','OTP','LISTAS_NEGRAS','INTERNA') |  |
| resultado | ENUM('APROBADO','RECHAZADO','OBSERVADO') |  |
| detalle | VARCHAR(200) |  |
| correlation_id | CHAR(36) |  |
| fecha_evento | DATETIME(3) |  |

## cuenta_ahorro
*Cuentas de ahorro*

| Columna | Tipo | Clave |
|---|---|---|
| num_cuenta | VARCHAR(20) | PK |
| moneda | CHAR(3) | FK->moneda |
| regimen | ENUM('LIBRE','PROGRAMADO','INFANTIL','CTS','A_PLAZO') |  |
| saldo_contable | DECIMAL(15,2) |  |
| saldo_disponible | DECIMAL(15,2) |  |
| saldo_retenido | DECIMAL(15,2) |  |
| estado_cuenta | ENUM('ACTIVA','INACTIVA','BLOQUEADA','CERRADA','EMBARGO') |  |
| fecha_apertura | DATETIME(3) |  |
| id_agencia | CHAR(36) | FK->agencia |
| id_producto_ahorro | CHAR(36) | FK->producto_ahorro |

## cliente_cuenta
*Vinculacion cliente-cuenta*

| Columna | Tipo | Clave |
|---|---|---|
| num_cuenta | VARCHAR(20) | PK, FK->cuenta_ahorro |
| id_cliente | CHAR(36) | PK, FK->cliente |
| rol_titular | ENUM('TITULAR','MANCOMUNADO','APODERADO','TUTOR','BENEFICIARIO') |  |
| fecha_vinculacion | DATETIME(3) |  |

## cta_transaccion
*Historico de transacciones de cuentas*

| Columna | Tipo | Clave |
|---|---|---|
| id_transaccion | CHAR(36) | PK |
| uuid_transaccion | CHAR(36) | UQ |
| num_cuenta | VARCHAR(20) | FK->cuenta_ahorro |
| num_cuenta_contraparte | VARCHAR(20) |  |
| tipo_operacion | ENUM('DEPOSITO','RETIRO','TRANSFERENCIA','PAGO_SERVICIO','DEBITO_AUTOMATICO','NOTA_CREDITO','NOTA_DEBITO') |  |
| tipo_movimiento | CHAR(1) |  |
| monto | DECIMAL(15,2) |  |
| moneda | CHAR(3) |  |
| id_canal | VARCHAR(5) | FK->canal |
| id_terminal | CHAR(36) | FK->terminal |
| saldo_posterior | DECIMAL(15,2) |  |
| comision | DECIMAL(15,2) |  |
| itf | DECIMAL(15,2) |  |
| retencion | DECIMAL(15,2) |  |
| estado_transaccion | ENUM('APLICADA','RECHAZADA','ANULADA','PENDIENTE') |  |
| idempotency_key | VARCHAR(64) | UQ |
| fecha_valor | DATE |  |
| fecha_hora | DATETIME(3) |  |

## cta_retencion_saldo
*Retenciones de saldo por cuenta*

| Columna | Tipo | Clave |
|---|---|---|
| id_retencion | CHAR(36) | PK |
| num_cuenta | VARCHAR(20) | FK->cuenta_ahorro |
| monto | DECIMAL(15,2) |  |
| motivo | VARCHAR(120) |  |
| estado | ENUM('VIGENTE','LIBERADA','APLICADA') |  |
| fecha_inicio | DATETIME(3) |  |
| fecha_fin | DATETIME(3) |  |

## cta_control_tope_diario
*Control de topes diarios por cuenta y canal*

| Columna | Tipo | Clave |
|---|---|---|
| id_tope | CHAR(36) | PK |
| num_cuenta | VARCHAR(20) | FK->cuenta_ahorro, UQ |
| id_canal | VARCHAR(5) | FK->canal, UQ |
| fecha_corte | DATE | UQ |
| monto_acumulado | DECIMAL(15,2) |  |

## cta_interes_mensual
*Intereses mensuales de cuentas de ahorro*

| Columna | Tipo | Clave |
|---|---|---|
| id_interes | CHAR(36) | PK |
| num_cuenta | VARCHAR(20) | FK->cuenta_ahorro, UQ |
| anio | SMALLINT UNSIGNED | UQ |
| mes | TINYINT UNSIGNED | UQ |
| saldo_promedio | DECIMAL(15,2) |  |
| tasa_tea | DECIMAL(6,4) |  |
| tasa_trea | DECIMAL(6,4) |  |
| interes_calculado | DECIMAL(15,2) |  |
| estado | ENUM('CALCULADO','ABONADO','ANULADO') |  |
| fecha_proceso | DATETIME(3) |  |

## tar_tarjeta
*Tarjetas emitidas*

| Columna | Tipo | Clave |
|---|---|---|
| id_tarjeta | CHAR(36) | PK |
| pan_token | VARCHAR(64) | UQ |
| bin | CHAR(6) |  |
| ultimos4 | CHAR(4) |  |
| id_cliente | CHAR(36) | FK->cliente |
| tipo_tarjeta | ENUM('DEBITO','CREDITO','PREPAGO') |  |
| fecha_emision | DATE |  |
| fecha_vencimiento | DATE |  |
| estado | ENUM('ACTIVA','BLOQUEADA','VENCIDA','ANULADA') |  |
| fecha_creacion | DATETIME(3) |  |

## tar_tarjeta_cuenta
*Vinculacion tarjeta-cuenta*

| Columna | Tipo | Clave |
|---|---|---|
| id_tarjeta | CHAR(36) | PK, FK->tar_tarjeta |
| num_cuenta | VARCHAR(20) | PK, FK->cuenta_ahorro |
| es_principal | TINYINT(1) |  |
| habilitada_atm | TINYINT(1) |  |
| fecha_vinculacion | DATETIME(3) |  |

## tar_credencial
*Credenciales de tarjeta*

| Columna | Tipo | Clave |
|---|---|---|
| id_credencial | CHAR(36) | PK |
| id_tarjeta | CHAR(36) | FK->tar_tarjeta, UQ |
| tipo | ENUM('PIN_ATM','CLAVE_WEB','BIOMETRIA','TOKEN_PAGO','TOKEN_MATRIZ') | UQ |
| longitud | TINYINT UNSIGNED |  |
| hash_credencial | CHAR(64) |  |
| sal | CHAR(32) |  |
| algoritmo_hash | VARCHAR(20) |  |
| version_hash | VARCHAR(10) |  |
| numero_serie | VARCHAR(30) |  |
| intentos_fallidos | TINYINT UNSIGNED |  |
| bloqueada | TINYINT(1) |  |
| fecha_creacion | DATETIME(3) |  |
| fecha_ultimo_cambio | DATETIME(3) |  |

## tar_matriz_token
*Tarjetas matriz de coordenadas*

| Columna | Tipo | Clave |
|---|---|---|
| id_matriz | CHAR(36) | PK |
| id_credencial | CHAR(36) | FK->tar_credencial |
| fecha_emision | DATE |  |
| activa | TINYINT(1) |  |

## tar_matriz_coordenada
*Coordenadas de la tarjeta matriz*

| Columna | Tipo | Clave |
|---|---|---|
| id_coordenada | CHAR(36) | PK |
| id_matriz | CHAR(36) | FK->tar_matriz_token, UQ |
| fila | CHAR(1) | UQ |
| columna | TINYINT UNSIGNED | UQ |
| hash_valor | CHAR(64) |  |

## tar_token_pago
*Tokens de pago de un solo uso*

| Columna | Tipo | Clave |
|---|---|---|
| id_token | CHAR(36) | PK |
| id_credencial | CHAR(36) | FK->tar_credencial |
| valor_hash | CHAR(64) |  |
| fecha_expiracion | DATETIME(3) |  |
| usada | TINYINT(1) |  |

## tar_intento_autenticacion
*Intentos de autenticacion de tarjetas*

| Columna | Tipo | Clave |
|---|---|---|
| id_intento | CHAR(36) | PK |
| id_tarjeta | CHAR(36) | FK->tar_tarjeta |
| tipo_credencial | ENUM('PIN_ATM','CLAVE_WEB','BIOMETRIA','TOKEN_PAGO','TOKEN_MATRIZ') |  |
| coordenada_solicitada | CHAR(2) |  |
| id_canal | VARCHAR(5) | FK->canal |
| id_terminal | CHAR(36) | FK->terminal |
| resultado | ENUM('EXITOSO','FALLIDO') |  |
| motivo_rechazo | VARCHAR(120) |  |
| uuid_correlacion | CHAR(36) |  |
| fecha_hora | DATETIME(3) |  |

## tar_autorizacion
*Autorizaciones de operaciones con tarjeta*

| Columna | Tipo | Clave |
|---|---|---|
| uuid_transaccion | CHAR(36) | PK |
| id_tarjeta | CHAR(36) | FK->tar_tarjeta |
| num_cuenta | VARCHAR(20) | FK->cuenta_ahorro |
| id_canal | VARCHAR(5) | FK->canal |
| tipo_operacion | ENUM('COMPRA','RETIRO','TRANSFERENCIA','CONSULTA','PAGO') |  |
| monto | DECIMAL(15,2) |  |
| moneda | CHAR(3) |  |
| estado | ENUM('APROBADA','RECHAZADA','PENDIENTE') |  |
| codigo_respuesta | VARCHAR(10) |  |
| motivo_rechazo | VARCHAR(120) |  |
| nivel_riesgo | ENUM('BAJO','MEDIO','ALTO') |  |
| id_terminal | CHAR(36) | FK->terminal |
| num_asiento_core | VARCHAR(30) |  |
| fecha_hora | DATETIME(3) |  |
| fecha_actualizacion | DATETIME(3) |  |

## tar_historial_estado
*Historial de estados de tarjeta*

| Columna | Tipo | Clave |
|---|---|---|
| id_historial | CHAR(36) | PK |
| id_tarjeta | CHAR(36) | FK->tar_tarjeta |
| estado_anterior | ENUM('ACTIVA','BLOQUEADA','VENCIDA','ANULADA') |  |
| estado_nuevo | ENUM('ACTIVA','BLOQUEADA','VENCIDA','ANULADA') |  |
| motivo | VARCHAR(120) |  |
| origen | ENUM('CLIENTE','BANCO','SISTEMA','REGULADOR') |  |
| fecha_hora | DATETIME(3) |  |

## tar_evento_salida
*Eventos de salida (outbox) del modulo tarjetas*

| Columna | Tipo | Clave |
|---|---|---|
| id_evento | CHAR(36) | PK |
| tipo_evento | VARCHAR(40) |  |
| id_tarjeta | CHAR(36) | FK->tar_tarjeta |
| payload | JSON |  |
| estado | ENUM('PENDIENTE','PUBLICADO','ERROR') |  |
| fecha_creacion | DATETIME(3) |  |
| fecha_procesado | DATETIME(3) |  |

## cap_solicitante
*Solicitantes de captacion*

| Columna | Tipo | Clave |
|---|---|---|
| id_solicitante | CHAR(36) | PK |
| id_cliente | CHAR(36) | FK->cliente |
| cod_tipo_documento | VARCHAR(10) | FK->tipo_documento, UQ |
| numero_documento | VARCHAR(20) | UQ |
| nombres | VARCHAR(80) |  |
| apellidos | VARCHAR(80) |  |
| celular | VARCHAR(15) |  |
| correo | VARCHAR(120) |  |
| fecha_registro | DATETIME(3) |  |

## cap_perfil_riesgo
*Perfil de riesgo del solicitante*

| Columna | Tipo | Clave |
|---|---|---|
| id_perfil | CHAR(36) | PK |
| id_solicitante | CHAR(36) | FK->cap_solicitante |
| calificacion | ENUM('BAJO','MEDIO','ALTO','MUY_ALTO') |  |
| puntaje | SMALLINT UNSIGNED |  |
| observacion | VARCHAR(200) |  |
| fecha_calculo | DATETIME(3) |  |

## cap_caso
*Casos de captacion*

| Columna | Tipo | Clave |
|---|---|---|
| id_caso | CHAR(36) | PK |
| id_solicitante | CHAR(36) | FK->cap_solicitante |
| id_asesor | CHAR(36) | FK->empleado |
| id_agencia | CHAR(36) | FK->agencia |
| id_producto_credito | CHAR(36) | FK->producto_credito |
| canal_captacion | ENUM('AGENCIA','WEB','MOVIL','AGENTE','CAMPANA') |  |
| estado_caso | ENUM('INICIADO','EN_VALIDACION','OBSERVADO','APROBADO','RECHAZADO','DERIVADO') |  |
| id_solicitud | CHAR(36) |  |
| fecha_apertura | DATETIME(3) |  |
| fecha_cierre | DATETIME(3) |  |

## cap_consentimiento
*Consentimientos del solicitante*

| Columna | Tipo | Clave |
|---|---|---|
| id_consentimiento | CHAR(36) | PK |
| id_caso | CHAR(36) | FK->cap_caso |
| tipo_consentimiento | ENUM('TRATAMIENTO_DATOS','CONSULTA_BUROS','BIOMETRIA','TERMINOS') |  |
| aceptado | TINYINT(1) |  |
| medio | ENUM('DIGITAL','FISICO','BIOMETRICO') |  |
| fecha_otorgamiento | DATETIME(3) |  |

## cap_validacion_identidad
*Validaciones de identidad del caso*

| Columna | Tipo | Clave |
|---|---|---|
| id_validacion | CHAR(36) | PK |
| id_caso | CHAR(36) | FK->cap_caso |
| id_solicitante | CHAR(36) | FK->cap_solicitante |
| tipo_validacion | ENUM('RENIEC','BIOMETRIA','LISTAS_NEGRAS','PEP','INTERNA') |  |
| resultado | ENUM('APROBADO','RECHAZADO','OBSERVADO') |  |
| proveedor | VARCHAR(60) |  |
| detalle | VARCHAR(200) |  |
| fecha_validacion | DATETIME(3) |  |

## cap_consulta_riesgos
*Consultas a centrales de riesgo*

| Columna | Tipo | Clave |
|---|---|---|
| id_consulta | CHAR(36) | PK |
| id_caso | CHAR(36) | FK->cap_caso |
| id_solicitante | CHAR(36) | FK->cap_solicitante |
| central | ENUM('SBS','INFOCORP','SENTINEL','EQUIFAX','OTRA') |  |
| motivo | VARCHAR(120) |  |
| resultado | ENUM('NORMAL','CPP','DEFICIENTE','DUDOSO','PERDIDA') |  |
| fecha_consulta | DATETIME(3) |  |

## cap_reporte_riesgos
*Reportes de centrales de riesgo*

| Columna | Tipo | Clave |
|---|---|---|
| id_reporte | CHAR(36) | PK |
| id_consulta | CHAR(36) | FK->cap_consulta_riesgos |
| calificacion | ENUM('NORMAL','CPP','DEFICIENTE','DUDOSO','PERDIDA') |  |
| deuda_total | DECIMAL(15,2) |  |
| entidades | SMALLINT UNSIGNED |  |
| dias_mayor_mora | SMALLINT UNSIGNED |  |
| archivo_pdf | VARCHAR(200) |  |
| fecha_reporte | DATETIME(3) |  |

## cap_auditoria_consulta
*Auditoria de consultas a centrales de riesgo*

| Columna | Tipo | Clave |
|---|---|---|
| id_auditoria | CHAR(36) | PK |
| id_consulta | CHAR(36) | FK->cap_consulta_riesgos |
| id_usuario | CHAR(36) | FK->usuario_sistema |
| id_empleado | CHAR(36) | FK->empleado |
| accion | ENUM('CONSULTA','REENVIO','ANULACION') |  |
| correlation_id | CHAR(36) |  |
| fecha_hora | DATETIME(3) |  |

## sol_solicitud
*Solicitudes de credito*

| Columna | Tipo | Clave |
|---|---|---|
| id_solicitud | CHAR(36) | PK |
| id_cliente | CHAR(36) | FK->cliente |
| id_caso | CHAR(36) | FK->cap_caso |
| id_producto_credito | CHAR(36) | FK->producto_credito |
| id_asesor | CHAR(36) | FK->empleado |
| id_agencia | CHAR(36) | FK->agencia |
| monto_solicitado | DECIMAL(15,2) |  |
| moneda | CHAR(3) | FK->moneda |
| plazo_meses | INT |  |
| destino_credito | VARCHAR(120) |  |
| estado_solicitud | ENUM('REGISTRADA','EN_EVALUACION','APROBADA','RECHAZADA','DESEMBOLSADA','ANULADA') |  |
| fecha_registro | DATETIME(3) |  |

## sol_fiador
*Fiadores de la solicitud*

| Columna | Tipo | Clave |
|---|---|---|
| id_fiador | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud |
| id_cliente | CHAR(36) | FK->cliente |
| cod_tipo_documento | VARCHAR(10) | FK->tipo_documento |
| numero_documento | VARCHAR(20) |  |
| nombre_completo | VARCHAR(140) |  |
| telefono | VARCHAR(15) |  |
| ingreso_mensual | DECIMAL(15,2) |  |
| tipo_fiador | ENUM('PERSONAL','SOLIDARIO','MANCOMUNADO') |  |

## sol_garantia
*Garantias de la solicitud*

| Columna | Tipo | Clave |
|---|---|---|
| id_garantia | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud |
| tipo_garantia | ENUM('PERSONAL','HIPOTECARIA','VEHICULAR','MOBILIARIA','FONDOS','SIN_GARANTIA') |  |
| descripcion | VARCHAR(200) |  |
| valor_tasacion | DECIMAL(15,2) |  |
| entidad_registro | VARCHAR(100) |  |
| partida_registral | VARCHAR(40) |  |
| fecha_tasacion | DATE |  |

## sol_historial_estado
*Historial de estados de la solicitud*

| Columna | Tipo | Clave |
|---|---|---|
| id_historial | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud |
| estado_anterior | ENUM('REGISTRADA','EN_EVALUACION','APROBADA','RECHAZADA','DESEMBOLSADA','ANULADA') |  |
| estado_nuevo | ENUM('REGISTRADA','EN_EVALUACION','APROBADA','RECHAZADA','DESEMBOLSADA','ANULADA') |  |
| motivo | VARCHAR(200) |  |
| id_usuario | CHAR(36) | FK->usuario_sistema |
| fecha_hora | DATETIME(3) |  |

## sol_calendario_version
*Versiones del calendario de pagos*

| Columna | Tipo | Clave |
|---|---|---|
| id_calendario | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud, UQ |
| version | SMALLINT UNSIGNED | UQ |
| tasa_tea | DECIMAL(6,4) |  |
| numero_cuotas | INT |  |
| monto_financiado | DECIMAL(15,2) |  |
| estado | ENUM('SIMULADO','VIGENTE','REEMPLAZADO') |  |
| fecha_creacion | DATETIME(3) |  |

## sol_cuota_calendario
*Cuotas proyectadas del calendario*

| Columna | Tipo | Clave |
|---|---|---|
| id_cuota | CHAR(36) | PK |
| id_calendario | CHAR(36) | FK->sol_calendario_version, UQ |
| numero_cuota | INT | UQ |
| fecha_vencimiento | DATE |  |
| saldo_inicial | DECIMAL(15,2) |  |
| amortizacion | DECIMAL(15,2) |  |
| interes | DECIMAL(15,2) |  |
| cuota_total | DECIMAL(15,2) |  |
| saldo_final | DECIMAL(15,2) |  |

## eva_regla
*Reglas de evaluacion de credito*

| Columna | Tipo | Clave |
|---|---|---|
| id_regla | CHAR(36) | PK |
| nombre | VARCHAR(80) | UQ |
| descripcion | VARCHAR(200) |  |
| variable | VARCHAR(60) |  |
| operador | ENUM('MAYOR','MENOR','IGUAL','ENTRE','EXCLUYE') |  |
| valor_min | DECIMAL(15,4) |  |
| valor_max | DECIMAL(15,4) |  |
| resultado | ENUM('APROBAR','OBSERVAR','RECHAZAR') |  |
| peso | DECIMAL(5,2) |  |
| activa | TINYINT(1) |  |

## eva_situacion_financiera
*Situacion financiera del cliente*

| Columna | Tipo | Clave |
|---|---|---|
| id_situacion | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud |
| id_cliente | CHAR(36) | FK->cliente |
| ingresos_mensuales | DECIMAL(15,2) |  |
| egresos_mensuales | DECIMAL(15,2) |  |
| patrimonio | DECIMAL(15,2) |  |
| cuota_otros_creditos | DECIMAL(15,2) |  |
| ratio_capacidad | DECIMAL(9,4) |  |
| fecha_declaracion | DATETIME(3) |  |

## eva_evaluacion
*Evaluaciones automaticas de credito*

| Columna | Tipo | Clave |
|---|---|---|
| id_evaluacion | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud |
| puntaje | SMALLINT UNSIGNED |  |
| resultado | ENUM('APROBADO','OBSERVADO','RECHAZADO') |  |
| monto_maximo_sugerido | DECIMAL(15,2) |  |
| nivel_riesgo | ENUM('BAJO','MEDIO','ALTO','MUY_ALTO') |  |
| detalle_reglas | JSON |  |
| fecha_evaluacion | DATETIME(3) |  |

## eva_decision_analista
*Decision final del analista*

| Columna | Tipo | Clave |
|---|---|---|
| id_decision | CHAR(36) | PK |
| id_evaluacion | CHAR(36) | FK->eva_evaluacion |
| id_analista | CHAR(36) | FK->empleado |
| decision | ENUM('APROBAR','RECHAZAR','OBSERVAR','DERIVAR') |  |
| monto_aprobado | DECIMAL(15,2) |  |
| plazo_aprobado | INT |  |
| observacion | VARCHAR(300) |  |
| fecha_decision | DATETIME(3) |  |

## des_orden
*Ordenes de desembolso*

| Columna | Tipo | Clave |
|---|---|---|
| id_orden | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud |
| id_cliente | CHAR(36) | FK->cliente |
| num_cuenta | VARCHAR(20) | FK->cuenta_ahorro |
| id_agencia | CHAR(36) | FK->agencia |
| monto | DECIMAL(15,2) |  |
| moneda | CHAR(3) |  |
| tipo_desembolso | ENUM('EFECTIVO','ABONO_CUENTA','CHEQUE','TRANSFERENCIA') |  |
| estado_orden | ENUM('GENERADA','EN_VALIDACION','AUTORIZADA','ENTREGADA','RECHAZADA','REVERTIDA') |  |
| id_autorizador | CHAR(36) | FK->empleado |
| fecha_generacion | DATETIME(3) |  |
| fecha_entrega | DATETIME(3) |  |

## des_validacion
*Validaciones previas al desembolso*

| Columna | Tipo | Clave |
|---|---|---|
| id_validacion | CHAR(36) | PK |
| id_orden | CHAR(36) | FK->des_orden |
| tipo_validacion | ENUM('FIRMA','DOCUMENTOS','CUENTA_ACTIVA','BIOMETRIA','CONTRATO') |  |
| resultado | ENUM('APROBADO','RECHAZADO','OBSERVADO') |  |
| id_validador | CHAR(36) | FK->empleado |
| detalle | VARCHAR(200) |  |
| fecha_validacion | DATETIME(3) |  |

## des_evento_entrega
*Eventos de entrega del desembolso*

| Columna | Tipo | Clave |
|---|---|---|
| id_evento | CHAR(36) | PK |
| id_orden | CHAR(36) | FK->des_orden |
| tipo_evento | ENUM('INICIO','ENTREGA','REVERSION','FALLO') |  |
| num_operacion_core | VARCHAR(30) |  |
| id_terminal | CHAR(36) | FK->terminal |
| detalle | VARCHAR(200) |  |
| fecha_evento | DATETIME(3) |  |

## des_auditoria
*Auditoria del modulo desembolso*

| Columna | Tipo | Clave |
|---|---|---|
| id_auditoria | CHAR(36) | PK |
| id_orden | CHAR(36) | FK->des_orden |
| id_usuario | CHAR(36) | FK->usuario_sistema |
| accion | VARCHAR(40) |  |
| estado_anterior | VARCHAR(20) |  |
| estado_nuevo | VARCHAR(20) |  |
| detalle | VARCHAR(200) |  |
| correlation_id | CHAR(36) |  |
| fecha_hora | DATETIME(3) |  |

## des_solicitud_reversion
*Solicitudes de reversion de desembolso*

| Columna | Tipo | Clave |
|---|---|---|
| id_reversion | CHAR(36) | PK |
| id_orden | CHAR(36) | FK->des_orden |
| id_solicitante | CHAR(36) | FK->usuario_sistema |
| id_autorizador | CHAR(36) | FK->usuario_sistema |
| motivo | VARCHAR(200) |  |
| estado | ENUM('SOLICITADA','AUTORIZADA','RECHAZADA','APLICADA') |  |
| num_transaccion_reposicion | VARCHAR(36) |  |
| fecha_solicitud | DATETIME(3) |  |
| fecha_autorizacion | DATETIME(3) |  |

## canal_pago
*Catalogo de canales de pago*

| Columna | Tipo | Clave |
|---|---|---|
| id_canal_pago | CHAR(36) | PK |
| nombre | VARCHAR(40) | UQ |
| tipo | ENUM('VENTANILLA','AGENTE','ATM','BANCA_WEB','APP','DOMICILIACION','TRANSFERENCIA') |  |
| activo | TINYINT(1) |  |

## cob_credito
*Creditos en cobranza*

| Columna | Tipo | Clave |
|---|---|---|
| id_credito | CHAR(36) | PK |
| id_solicitud | CHAR(36) | FK->sol_solicitud |
| id_cliente | CHAR(36) | FK->cliente |
| num_cuenta_desembolso | VARCHAR(20) | FK->cuenta_ahorro |
| monto_aprobado | DECIMAL(15,2) |  |
| moneda | CHAR(3) | FK->moneda |
| tasa_tea | DECIMAL(6,4) |  |
| plazo_meses | INT |  |
| saldo_capital | DECIMAL(15,2) |  |
| estado_credito | ENUM('VIGENTE','VENCIDO','JUDICIAL','CASTIGADO','CANCELADO') |  |
| dias_mora | INT |  |
| fecha_desembolso | DATE |  |

## cob_cuota
*Cuotas del credito en cobranza*

| Columna | Tipo | Clave |
|---|---|---|
| id_cuota_credito | CHAR(36) | PK |
| id_credito | CHAR(36) | FK->cob_credito, UQ |
| numero_cuota | INT | UQ |
| fecha_vencimiento | DATE |  |
| capital | DECIMAL(15,2) |  |
| interes | DECIMAL(15,2) |  |
| seguro | DECIMAL(15,2) |  |
| cuota_total | DECIMAL(15,2) |  |
| saldo_capital | DECIMAL(15,2) |  |
| monto_pagado | DECIMAL(15,2) |  |
| estado_cuota | ENUM('PENDIENTE','PARCIAL','PAGADA','VENCIDA','CASTIGADA') |  |

## cob_pago
*Pagos recibidos*

| Columna | Tipo | Clave |
|---|---|---|
| id_pago | CHAR(36) | PK |
| id_credito | CHAR(36) | FK->cob_credito |
| id_canal_pago | CHAR(36) | FK->canal_pago |
| num_cuenta | VARCHAR(20) | FK->cuenta_ahorro |
| monto | DECIMAL(15,2) |  |
| moneda | CHAR(3) |  |
| num_operacion | VARCHAR(30) | UQ |
| id_cobrador | CHAR(36) | FK->empleado |
| estado_pago | ENUM('REGISTRADO','APLICADO','RECHAZADO','REVERSADO') |  |
| fecha_pago | DATETIME(3) |  |

## cob_aplicacion_pago
*Aplicacion del pago por componente*

| Columna | Tipo | Clave |
|---|---|---|
| id_aplicacion | CHAR(36) | PK |
| id_pago | CHAR(36) | FK->cob_pago |
| id_cuota_credito | CHAR(36) | FK->cob_cuota |
| aplica_capital | DECIMAL(15,2) |  |
| aplica_interes | DECIMAL(15,2) |  |
| aplica_seguro | DECIMAL(15,2) |  |
| aplica_mora | DECIMAL(15,2) |  |
| fecha_aplicacion | DATETIME(3) |  |

## cob_mora
*Mora de las cuotas*

| Columna | Tipo | Clave |
|---|---|---|
| id_mora | CHAR(36) | PK |
| id_cuota_credito | CHAR(36) | FK->cob_cuota, UQ |
| dias_atraso | INT |  |
| tasa_mora | DECIMAL(6,4) |  |
| interes_mora | DECIMAL(15,2) |  |
| estado_mora | ENUM('PENDIENTE','VIGENTE','PAGADA','CONDONADA') |  |
| vigente_flag | TINYINT | UQ |
| fecha_calculo | DATETIME(3) |  |

## cob_evento_auditoria
*Eventos de auditoria de cobranza*

| Columna | Tipo | Clave |
|---|---|---|
| id_evento | CHAR(36) | PK |
| id_credito | CHAR(36) | FK->cob_credito |
| tipo_evento | ENUM('PAGO','MORA','GESTION','CAMBIO_ESTADO','CASTIGO','CONDONACION') |  |
| descripcion | VARCHAR(200) |  |
| id_usuario | CHAR(36) | FK->usuario_sistema |
| canal | VARCHAR(20) |  |
| correlation_id | CHAR(36) |  |
| fecha_hora | DATETIME(3) |  |


