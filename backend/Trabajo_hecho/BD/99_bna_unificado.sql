-- =====================================================================
-- BNA - BASE DE DATOS UNIFICADA (TODO EN UNO)
-- Generado: 2026-10-15  |  MySQL 8.0/8.4  |  InnoDB  |  utf8mb4
-- Ejecutar: source 99_bna_unificado.sql   (desde MySQL Shell)
-- NOTA: elimina y recrea la base bna para una carga limpia.
-- IDs: UUID v7 (CHAR(36)) en todas las claves primarias y foraneas.
-- =====================================================================
-- >>> INICIO 01_catalogos_comunes.sql
-- =====================================================================
-- BANCO NACIONAL DE AREQUIPA (BNA) - BASE DE DATOS UNIFICADA
-- Script 01: Catalagos comunes y compartidos
-- Modulo: CORE / COMPARTIDO
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4 / utf8mb4_0900_ai_ci
-- Version: v1.0.0   Fecha: 2026-10-15
-- Correcciones aplicadas: enums con valores, ENGINE/CHARSET, DEFAULT
--   CURRENT_TIMESTAMP(3) sin comillas, sin indices UNIQUE duplicados.
-- IDs: todas las claves primarias y foraneas son UUID v7 en CHAR(36)
--   (ordenables por tiempo). La aplicacion genera los v7; ver fn_uuid_v7()
--   en 12_triggers_eventos.sql para las filas creadas por la base.
-- =====================================================================
-- IMPORTANTE: se elimina la base previa para garantizar una carga limpia
-- desde cero (evita "Table already exists" con esquemas antiguos).
DROP DATABASE IF EXISTS bna;
CREATE DATABASE bna
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE bna;

SET NAMES utf8mb4;
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION';

-- ---------------------------------------------------------------------
-- agencia: agencias fisicas del banco (cuatro iniciales en Arequipa)
-- ---------------------------------------------------------------------
CREATE TABLE agencia (
  id_agencia   CHAR(36)        NOT NULL COMMENT 'Identificador de la agencia',
  nombre       VARCHAR(60)     NOT NULL COMMENT 'Nombre de la agencia',
  direccion    VARCHAR(120)    NOT NULL COMMENT 'Direccion de la agencia',
  activa       TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si la agencia esta operativa',
  PRIMARY KEY (id_agencia),
  UNIQUE KEY uk_agencia_nombre (nombre)
) ENGINE=InnoDB COMMENT='Agencias del banco';

-- ---------------------------------------------------------------------
-- empleado: asesores, analistas, operadores y cajeros
-- ---------------------------------------------------------------------
CREATE TABLE empleado (
  id_empleado     CHAR(36)        NOT NULL COMMENT 'Identificador del empleado',
  codigo_empleado VARCHAR(20)     NOT NULL COMMENT 'Codigo de empleado dentro del BNA',
  nombre_completo VARCHAR(100)    NOT NULL COMMENT 'Nombres y apellidos del empleado',
  cargo           ENUM('ASESOR_CREDITOS','ANALISTA_CREDITO','OPERADOR','CAJERO','ADMINISTRADOR')
                  NOT NULL COMMENT 'Cargo o rol operativo',
  id_agencia      CHAR(36)        NULL COMMENT 'Agencia donde labora',
  activo          TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si el empleado esta habilitado',
  PRIMARY KEY (id_empleado),
  UNIQUE KEY uk_empleado_codigo (codigo_empleado),
  CONSTRAINT fk_empleado_agencia FOREIGN KEY (id_agencia) REFERENCES agencia (id_agencia)
) ENGINE=InnoDB COMMENT='Asesores, analistas, operadores y cajeros';

-- ---------------------------------------------------------------------
-- usuario_sistema: usuarios de aplicacion (mejora: tabla faltante)
-- ---------------------------------------------------------------------
CREATE TABLE usuario_sistema (
  id_usuario    CHAR(36)        NOT NULL COMMENT 'Identificador del usuario',
  username      VARCHAR(40)     NOT NULL COMMENT 'Nombre de usuario de la plataforma',
  nombre        VARCHAR(100)    NOT NULL COMMENT 'Nombre completo',
  rol           ENUM('ADMINISTRADOR','ASESOR','ANALISTA','OPERADOR','AUDITOR')
                NOT NULL COMMENT 'Rol de acceso',
  hash_password CHAR(64)        NOT NULL COMMENT 'SHA-256/HMAC del password',
  algoritmo_hash VARCHAR(20)    NOT NULL DEFAULT 'SHA256' COMMENT 'Algoritmo de hash del password',
  version_hash  VARCHAR(10)     NOT NULL DEFAULT 'v1' COMMENT 'Version del algoritmo de hash',
  id_empleado   CHAR(36)        NULL COMMENT 'Empleado asociado, si aplica',
  activo        TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si el usuario esta habilitado',
  creado_en     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de alta',
  PRIMARY KEY (id_usuario),
  UNIQUE KEY uk_usuario_username (username),
  CONSTRAINT fk_usuario_empleado FOREIGN KEY (id_empleado) REFERENCES empleado (id_empleado)
) ENGINE=InnoDB COMMENT='Usuarios del sistema';

-- ---------------------------------------------------------------------
-- tipo_documento: catalogo de documentos de identidad admitidos
-- ---------------------------------------------------------------------
CREATE TABLE tipo_documento (
  cod_tipo_documento VARCHAR(10) NOT NULL COMMENT 'Codigo: DNI, CE, PASAPORTE, PTP',
  descripcion        VARCHAR(50) NOT NULL COMMENT 'Nombre del documento',
  PRIMARY KEY (cod_tipo_documento)
) ENGINE=InnoDB COMMENT='Catalogo de documentos de identidad';

-- ---------------------------------------------------------------------
-- moneda: catalogo de monedas ISO-4217 (mejora: tabla faltante)
-- ---------------------------------------------------------------------
CREATE TABLE moneda (
  cod_moneda CHAR(3)     NOT NULL COMMENT 'Codigo ISO-4217: PEN, USD',
  nombre     VARCHAR(30) NOT NULL COMMENT 'Nombre de la moneda',
  simbolo    VARCHAR(5)  NOT NULL COMMENT 'Simbolo de la moneda',
  activa     TINYINT(1)  NOT NULL DEFAULT 1 COMMENT '1 si la moneda esta habilitada',
  PRIMARY KEY (cod_moneda),
  CONSTRAINT ck_moneda_codigo CHECK (cod_moneda IN ('PEN','USD'))
) ENGINE=InnoDB COMMENT='Catalogo de monedas';

-- ---------------------------------------------------------------------
-- tipo_cambio: tipo de cambio por fecha (mejora: contabilidad multimoneda)
-- ---------------------------------------------------------------------
CREATE TABLE tipo_cambio (
  id_tipo_cambio     CHAR(36)        NOT NULL COMMENT 'Identificador del tipo de cambio',
  cod_moneda_origen  CHAR(3)         NOT NULL COMMENT 'Moneda origen',
  cod_moneda_destino CHAR(3)         NOT NULL COMMENT 'Moneda destino (base)',
  fecha              DATE            NOT NULL COMMENT 'Fecha de vigencia',
  tasa               DECIMAL(12,6)   NOT NULL COMMENT 'Factor de conversion',
  PRIMARY KEY (id_tipo_cambio),
  UNIQUE KEY uk_tc_monedas_fecha (cod_moneda_origen, cod_moneda_destino, fecha),
  CONSTRAINT fk_tc_origen  FOREIGN KEY (cod_moneda_origen)  REFERENCES moneda (cod_moneda),
  CONSTRAINT fk_tc_destino FOREIGN KEY (cod_moneda_destino) REFERENCES moneda (cod_moneda),
  CONSTRAINT ck_tc_tasa CHECK (tasa > 0)
) ENGINE=InnoDB COMMENT='Tipos de cambio por fecha';

-- ---------------------------------------------------------------------
-- terminal: cajeros, agentes y puntos de atencion (mejora: tabla faltante)
-- ---------------------------------------------------------------------
CREATE TABLE terminal (
  id_terminal CHAR(36)        NOT NULL COMMENT 'Identificador de la terminal',
  codigo      VARCHAR(30)     NOT NULL COMMENT 'Codigo o IP de la terminal',
  tipo        ENUM('ATM','AGENTE','POS','WEB','MOVIL') NOT NULL COMMENT 'Tipo de terminal',
  ubicacion   VARCHAR(120)    NULL COMMENT 'Ubicacion fisica',
  id_agencia  CHAR(36)        NULL COMMENT 'Agencia donde opera',
  activa      TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si la terminal esta operativa',
  PRIMARY KEY (id_terminal),
  UNIQUE KEY uk_terminal_codigo (codigo),
  CONSTRAINT fk_terminal_agencia FOREIGN KEY (id_agencia) REFERENCES agencia (id_agencia)
) ENGINE=InnoDB COMMENT='Terminales y puntos de atencion';

-- ---------------------------------------------------------------------
-- canal: canales de atencion desde los que se opera
-- ---------------------------------------------------------------------
CREATE TABLE canal (
  id_canal              VARCHAR(5)  NOT NULL COMMENT 'ATM, AGE, VEN, HB o BD',
  nombre                VARCHAR(40) NOT NULL COMMENT 'Nombre del canal',
  es_presencial         TINYINT(1)  NOT NULL COMMENT '1 si el cliente esta fisicamente presente',
  validacion_requerida  ENUM('PIN_ATM','CLAVE_WEB','BIOMETRIA','TOKEN_PAGO') NOT NULL
                        COMMENT 'Credencial que exige el canal',
  requiere_token_matriz TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '1 si exige coordenada de tarjeta matriz',
  tipo_integracion      VARCHAR(30) NOT NULL DEFAULT 'BUS_SERVICIOS' COMMENT 'Mecanismo de integracion',
  activo                TINYINT(1)  NOT NULL DEFAULT 1 COMMENT '1 si el canal esta operativo',
  PRIMARY KEY (id_canal),
  UNIQUE KEY uk_canal_nombre (nombre)
) ENGINE=InnoDB COMMENT='Catalogo de canales de atencion';

-- ---------------------------------------------------------------------
-- limite_canal: topes diarios por canal y moneda
-- ---------------------------------------------------------------------
CREATE TABLE limite_canal (
  id_canal              VARCHAR(5)    NOT NULL COMMENT 'Canal al que aplica el tope',
  moneda                CHAR(3)       NOT NULL COMMENT 'Moneda del tope',
  monto_maximo_diario   DECIMAL(15,2) NULL COMMENT 'Tope diario (NULL = sin limite)',
  habilitado            TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '1 si el canal opera en esa moneda',
  regla_negocio         VARCHAR(40)   NOT NULL COMMENT 'Codigo de la regla que define el tope',
  PRIMARY KEY (id_canal, moneda),
  CONSTRAINT fk_limite_canal FOREIGN KEY (id_canal) REFERENCES canal (id_canal),
  CONSTRAINT fk_limite_moneda FOREIGN KEY (moneda) REFERENCES moneda (cod_moneda)
) ENGINE=InnoDB COMMENT='Topes diarios acumulados por canal y moneda';

-- ---------------------------------------------------------------------
-- producto_ahorro (mejora: tabla faltante)
-- ---------------------------------------------------------------------
CREATE TABLE producto_ahorro (
  id_producto_ahorro CHAR(36)        NOT NULL COMMENT 'Identificador del producto',
  nombre             VARCHAR(60)     NOT NULL COMMENT 'Nombre del producto de ahorro',
  moneda             CHAR(3)         NOT NULL COMMENT 'Moneda del producto',
  tasa_tea           DECIMAL(6,4)    NOT NULL DEFAULT 0 COMMENT 'Tasa efectiva anual',
  activo             TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si el producto esta vigente',
  PRIMARY KEY (id_producto_ahorro),
  UNIQUE KEY uk_producto_ahorro_nombre (nombre, moneda),
  CONSTRAINT fk_prod_ahorro_moneda FOREIGN KEY (moneda) REFERENCES moneda (cod_moneda)
) ENGINE=InnoDB COMMENT='Productos de ahorro';

-- ---------------------------------------------------------------------
-- producto_credito (mejora: tabla faltante)
-- ---------------------------------------------------------------------
CREATE TABLE producto_credito (
  id_producto_credito CHAR(36)        NOT NULL COMMENT 'Identificador del producto de credito',
  nombre              VARCHAR(60)     NOT NULL COMMENT 'Nombre del producto de credito',
  tasa_tea            DECIMAL(6,4)    NOT NULL COMMENT 'Tasa efectiva anual',
  plazo_min_meses     INT             NOT NULL DEFAULT 1 COMMENT 'Plazo minimo en meses',
  plazo_max_meses     INT             NOT NULL DEFAULT 60 COMMENT 'Plazo maximo en meses',
  activo              TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si el producto esta vigente',
  PRIMARY KEY (id_producto_credito),
  UNIQUE KEY uk_producto_credito_nombre (nombre),
  CONSTRAINT ck_prod_credito_plazo CHECK (plazo_min_meses <= plazo_max_meses)
) ENGINE=InnoDB COMMENT='Productos de credito';

-- ---------------------------------------------------------------------
-- periodo_contable (mejora: periodos contables)
-- ---------------------------------------------------------------------
CREATE TABLE periodo_contable (
  id_periodo   CHAR(36)        NOT NULL COMMENT 'Identificador del periodo',
  anio         SMALLINT UNSIGNED NOT NULL COMMENT 'Anio contable',
  mes          TINYINT UNSIGNED  NOT NULL COMMENT 'Mes contable (1-12)',
  fecha_inicio DATE              NOT NULL COMMENT 'Primer dia del periodo',
  fecha_fin    DATE              NOT NULL COMMENT 'Ultimo dia del periodo',
  estado       ENUM('ABIERTO','CERRADO') NOT NULL DEFAULT 'ABIERTO' COMMENT 'Estado del periodo',
  PRIMARY KEY (id_periodo),
  UNIQUE KEY uk_periodo_anio_mes (anio, mes),
  CONSTRAINT ck_periodo_mes CHECK (mes BETWEEN 1 AND 12)
) ENGINE=InnoDB COMMENT='Periodos contables';

-- ---------------------------------------------------------------------
-- plan_cuenta_contable: plan de cuentas (partida doble)
-- ---------------------------------------------------------------------
CREATE TABLE plan_cuenta_contable (
  cod_cuenta_contable VARCHAR(20)  NOT NULL COMMENT 'Codigo contable',
  nombre              VARCHAR(100) NOT NULL COMMENT 'Nombre de la cuenta',
  naturaleza          ENUM('DEUDORA','ACREEDORA') NOT NULL COMMENT 'Naturaleza contable',
  codigo_padre        VARCHAR(20)  NULL COMMENT 'Cuenta padre en la jerarquia',
  activo              TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '1 si la cuenta esta vigente',
  PRIMARY KEY (cod_cuenta_contable),
  CONSTRAINT fk_plan_padre FOREIGN KEY (codigo_padre) REFERENCES plan_cuenta_contable (cod_cuenta_contable)
) ENGINE=InnoDB COMMENT='Plan de cuentas contables';

-- ---------------------------------------------------------------------
-- asiento_contable: cabecera de asiento (partida doble)
-- ---------------------------------------------------------------------
CREATE TABLE asiento_contable (
  id_asiento      CHAR(36)        NOT NULL COMMENT 'Identificador del asiento',
  id_periodo      CHAR(36)        NOT NULL COMMENT 'Periodo contable',
  fecha           DATETIME(3)     NOT NULL COMMENT 'Fecha y hora del asiento',
  glosa           VARCHAR(200)    NOT NULL COMMENT 'Descripcion del asiento',
  estado          ENUM('REGISTRADO','REVERTIDO') NOT NULL DEFAULT 'REGISTRADO' COMMENT 'Estado del asiento',
  id_asiento_rev  CHAR(36)        NULL COMMENT 'Asiento que revierte, si aplica',
  PRIMARY KEY (id_asiento),
  CONSTRAINT fk_asiento_periodo FOREIGN KEY (id_periodo) REFERENCES periodo_contable (id_periodo),
  CONSTRAINT fk_asiento_reversion FOREIGN KEY (id_asiento_rev) REFERENCES asiento_contable (id_asiento)
) ENGINE=InnoDB COMMENT='Cabecera de asientos contables';

-- ---------------------------------------------------------------------
-- asiento_detalle: detalle del asiento con moneda y tipo de cambio
-- Mejora: tipo de cambio e importe en moneda base.
-- ---------------------------------------------------------------------
CREATE TABLE asiento_detalle (
  id_detalle          CHAR(36)        NOT NULL COMMENT 'Identificador del detalle',
  id_asiento          CHAR(36)        NOT NULL COMMENT 'Asiento al que pertenece',
  cod_cuenta_contable VARCHAR(20)     NOT NULL COMMENT 'Cuenta contable afectada',
  debe                DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Importe en el debe',
  haber               DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Importe en el haber',
  moneda              CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda del movimiento',
  tipo_cambio         DECIMAL(12,6)   NOT NULL DEFAULT 1 COMMENT 'Tipo de cambio aplicado',
  importe_moneda_base DECIMAL(15,2)   NOT NULL COMMENT 'Importe convertido a moneda base',
  PRIMARY KEY (id_detalle),
  CONSTRAINT fk_detalle_asiento FOREIGN KEY (id_asiento) REFERENCES asiento_contable (id_asiento),
  CONSTRAINT fk_detalle_cuenta  FOREIGN KEY (cod_cuenta_contable) REFERENCES plan_cuenta_contable (cod_cuenta_contable),
  CONSTRAINT fk_detalle_moneda  FOREIGN KEY (moneda) REFERENCES moneda (cod_moneda),
  CONSTRAINT ck_detalle_montos CHECK (debe >= 0 AND haber >= 0)
) ENGINE=InnoDB COMMENT='Detalle de asientos con moneda base';

-- ---------------------------------------------------------------------
-- auditoria_evento: auditoria centralizada (mejora del feedback)
-- ---------------------------------------------------------------------
CREATE TABLE auditoria_evento (
  id_evento      CHAR(36)        NOT NULL COMMENT 'Clave primaria UUID v7',
  modulo         VARCHAR(20)     NOT NULL COMMENT 'Modulo: CLI, CTA, TAR, CAP, SOL, EVA, DES, COB',
  entidad        VARCHAR(40)     NOT NULL COMMENT 'Tabla afectada',
  id_entidad     VARCHAR(40)     NOT NULL COMMENT 'Identificador del registro afectado',
  accion         VARCHAR(40)     NOT NULL COMMENT 'Accion realizada',
  actor          VARCHAR(40)     NOT NULL COMMENT 'Usuario, empleado o sistema',
  detalle        JSON            NULL COMMENT 'Estado anterior/nuevo y motivo, sin datos sensibles',
  correlation_id CHAR(36)        NULL COMMENT 'Identificador de correlacion del Bus',
  fecha_hora     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora con milisegundos',
  PRIMARY KEY (id_evento),
  KEY idx_auditoria_entidad (entidad, id_entidad),
  KEY idx_auditoria_correlation (correlation_id),
  KEY idx_auditoria_fecha (fecha_hora)
) ENGINE=InnoDB COMMENT='Auditoria centralizada de toda la plataforma';

-- <<< FIN 01_catalogos_comunes.sql

-- >>> INICIO 02_clientes_kyc.sql
-- =====================================================================
-- BNA - Script 02: Modulo Clientes / KYC
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Mejoras: biometria cifrada (algoritmo/version), codigo de verificacion
--   con HMAC + proposito + vigencia, auditoria de validacion con correlation_id.
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- cliente: cliente persona natural del banco
-- ---------------------------------------------------------------------
CREATE TABLE cliente (
  id_cliente         CHAR(36)        NOT NULL COMMENT 'Identificador interno del cliente',
  cod_tipo_documento VARCHAR(10)     NOT NULL COMMENT 'Tipo de documento de identidad',
  numero_documento   VARCHAR(20)     NOT NULL COMMENT 'Numero de documento',
  nombres            VARCHAR(80)     NOT NULL COMMENT 'Nombres',
  apellido_paterno   VARCHAR(60)     NOT NULL COMMENT 'Apellido paterno',
  apellido_materno   VARCHAR(60)     NULL COMMENT 'Apellido materno',
  fecha_nacimiento   DATE            NULL COMMENT 'Fecha de nacimiento',
  numero_celular     VARCHAR(15)     NOT NULL COMMENT 'Celular de contacto',
  correo_electronico VARCHAR(120)    NULL COMMENT 'Correo electronico',
  estado_cliente     ENUM('ACTIVO','INACTIVO','BLOQUEADO','FALLECIDO') NOT NULL DEFAULT 'ACTIVO'
                     COMMENT 'Estado del cliente',
  fecha_registro     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de alta',
  PRIMARY KEY (id_cliente),
  UNIQUE KEY uk_cliente_doc (cod_tipo_documento, numero_documento),
  UNIQUE KEY uk_cliente_correo (correo_electronico),
  CONSTRAINT fk_cliente_tipodoc FOREIGN KEY (cod_tipo_documento) REFERENCES tipo_documento (cod_tipo_documento)
) ENGINE=InnoDB COMMENT='Clientes del banco';

-- ---------------------------------------------------------------------
-- biometria_cliente: plantillas biometricas cifradas (mejora de seguridad)
-- ---------------------------------------------------------------------
CREATE TABLE biometria_cliente (
  id_biometria       CHAR(36)        NOT NULL COMMENT 'Identificador de la biometria',
  id_cliente          CHAR(36)        NOT NULL COMMENT 'Cliente asociado',
  tipo_biometria      ENUM('HUELLA','ROSTRO','VOZ','IRIS') NOT NULL COMMENT 'Tipo de biometria',
  datos_biometricos   LONGBLOB        NOT NULL COMMENT 'Plantilla cifrada',
  algoritmo_cifrado   VARCHAR(30)     NOT NULL COMMENT 'Algoritmo de cifrado (AES-256, etc.)',
  version_cifrado     VARCHAR(10)     NOT NULL COMMENT 'Version del esquema de cifrado',
  hash_datos          CHAR(64)        NOT NULL COMMENT 'Hash de integridad de la plantilla',
  estado_activo       TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si la plantilla esta vigente',
  fecha_registro      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de registro',
  PRIMARY KEY (id_biometria),
  KEY idx_biometria_cliente (id_cliente, estado_activo),
  CONSTRAINT fk_biometria_cliente FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente),
  CONSTRAINT ck_biometria_cifrado CHECK (algoritmo_cifrado IN ('AES-256-GCM','AES-256-CBC'))
) ENGINE=InnoDB COMMENT='Plantillas biometricas cifradas del cliente';

-- ---------------------------------------------------------------------
-- cli_codigo_verificacion: OTP por SMS/correo con HMAC y proposito
-- Mejora: no se guarda el codigo en claro, se guarda HMAC; vigencia y proposito.
-- ---------------------------------------------------------------------
CREATE TABLE cli_codigo_verificacion (
  id_codigo        CHAR(36)        NOT NULL COMMENT 'Identificador del codigo',
  id_cliente       CHAR(36)        NULL COMMENT 'Cliente destino (NULL si es solicitante no cliente)',
  id_solicitante   CHAR(36)        NULL COMMENT 'Solicitante de captacion (si no es cliente)',
  destino          VARCHAR(120)    NOT NULL COMMENT 'Celular o correo destino',
  tipo_contacto    ENUM('SMS','EMAIL') NOT NULL COMMENT 'Medio de envio',
  codigo_hmac      CHAR(64)        NOT NULL COMMENT 'HMAC-SHA256 del codigo OTP',
  proposito        ENUM('ALTA_CLIENTE','RECUPERACION','TRANSACCION','CONSULTA') NOT NULL
                   COMMENT 'Proposito del codigo',
  intentos_fallidos TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Intentos fallidos',
  estado           ENUM('PENDIENTE','USADO','EXPIRADO','BLOQUEADO') NOT NULL DEFAULT 'PENDIENTE'
                   COMMENT 'Estado del codigo',
  fecha_creacion   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de generacion',
  fecha_expiracion DATETIME(3)     NOT NULL COMMENT 'Fecha de expiracion',
  PRIMARY KEY (id_codigo),
  KEY idx_codigo_cliente (id_cliente, estado),
  CONSTRAINT fk_codigo_cliente FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
) ENGINE=InnoDB COMMENT='Codigos de verificacion OTP';

-- ---------------------------------------------------------------------
-- cli_auditoria_validacion: trazabilidad de validaciones de identidad
-- ---------------------------------------------------------------------
CREATE TABLE cli_auditoria_validacion (
  id_validacion  CHAR(36)        NOT NULL COMMENT 'Identificador de la validacion',
  id_cliente     CHAR(36)        NULL COMMENT 'Cliente validado',
  tipo_validacion ENUM('RENIEC','BIOMETRIA','OTP','LISTAS_NEGRAS','INTERNA') NOT NULL
                  COMMENT 'Tipo de validacion realizada',
  resultado      ENUM('APROBADO','RECHAZADO','OBSERVADO') NOT NULL COMMENT 'Resultado',
  detalle        VARCHAR(200)    NULL COMMENT 'Detalle o motivo del resultado',
  correlation_id CHAR(36)        NULL COMMENT 'Identificador de correlacion del Bus',
  fecha_evento   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora del evento',
  PRIMARY KEY (id_validacion),
  KEY idx_valida_cliente (id_cliente, tipo_validacion),
  CONSTRAINT fk_valida_cliente FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
) ENGINE=InnoDB COMMENT='Auditoria de validaciones de identidad';

-- <<< FIN 02_clientes_kyc.sql

-- >>> INICIO 03_cuentas.sql
-- =====================================================================
-- BNA - Script 03: Modulo Cuentas
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Mejoras: transaccion con contraparte/saldo posterior/fecha valor/comision/
--   ITF/retencion e idempotencia; tabla de retenciones; tasa TEA/TREA;
--   indices de consulta.
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- cuenta_ahorro: cuenta de ahorro del cliente
-- ---------------------------------------------------------------------
CREATE TABLE cuenta_ahorro (
  num_cuenta         VARCHAR(20)     NOT NULL COMMENT 'Numero de cuenta',
  moneda             CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda de la cuenta',
  regimen            ENUM('LIBRE','PROGRAMADO','INFANTIL','CTS','A_PLAZO') NOT NULL
                     COMMENT 'Regimen de la cuenta',
  saldo_contable     DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Saldo contable',
  saldo_disponible   DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Saldo disponible para operar',
  saldo_retenido     DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Saldo retenido',
  estado_cuenta      ENUM('ACTIVA','INACTIVA','BLOQUEADA','CERRADA','EMBARGO') NOT NULL DEFAULT 'ACTIVA'
                     COMMENT 'Estado de la cuenta',
  fecha_apertura     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de apertura',
  id_agencia         CHAR(36)        NOT NULL COMMENT 'Agencia de apertura',
  id_producto_ahorro CHAR(36)        NOT NULL COMMENT 'Producto de ahorro',
  PRIMARY KEY (num_cuenta),
  KEY idx_cuenta_cliente_estado (estado_cuenta),
  CONSTRAINT fk_cuenta_agencia  FOREIGN KEY (id_agencia) REFERENCES agencia (id_agencia),
  CONSTRAINT fk_cuenta_producto FOREIGN KEY (id_producto_ahorro) REFERENCES producto_ahorro (id_producto_ahorro),
  CONSTRAINT fk_cuenta_moneda   FOREIGN KEY (moneda) REFERENCES moneda (cod_moneda),
  CONSTRAINT ck_cuenta_saldos CHECK (saldo_disponible >= 0 AND saldo_retenido >= 0)
) ENGINE=InnoDB COMMENT='Cuentas de ahorro';

-- ---------------------------------------------------------------------
-- cliente_cuenta: titulares y mancomunados de una cuenta
-- ---------------------------------------------------------------------
CREATE TABLE cliente_cuenta (
  num_cuenta       VARCHAR(20)     NOT NULL COMMENT 'Numero de cuenta',
  id_cliente       CHAR(36)        NOT NULL COMMENT 'Cliente titular',
  rol_titular      ENUM('TITULAR','MANCOMUNADO','APODERADO','TUTOR','BENEFICIARIO') NOT NULL
                   COMMENT 'Rol del cliente en la cuenta',
  fecha_vinculacion DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de vinculacion',
  PRIMARY KEY (num_cuenta, id_cliente),
  CONSTRAINT fk_cc_cuenta  FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT fk_cc_cliente FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
) ENGINE=InnoDB COMMENT='Vinculacion cliente-cuenta';

-- ---------------------------------------------------------------------
-- cta_transaccion: movimientos de cuenta (mejorada)
-- ---------------------------------------------------------------------
CREATE TABLE cta_transaccion (
  id_transaccion      CHAR(36)        NOT NULL COMMENT 'Identificador interno',
  uuid_transaccion    CHAR(36)        NOT NULL COMMENT 'Identificador unico de la operacion',
  num_cuenta          VARCHAR(20)     NOT NULL COMMENT 'Cuenta afectada',
  num_cuenta_contraparte VARCHAR(20)  NULL COMMENT 'Cuenta de la contraparte, si aplica',
  tipo_operacion      ENUM('DEPOSITO','RETIRO','TRANSFERENCIA','PAGO_SERVICIO','DEBITO_AUTOMATICO','NOTA_CREDITO','NOTA_DEBITO')
                      NOT NULL COMMENT 'Tipo de operacion',
  tipo_movimiento     CHAR(1)         NOT NULL COMMENT 'D = debito, C = credito',
  monto               DECIMAL(15,2)   NOT NULL COMMENT 'Importe de la operacion',
  moneda              CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda de la operacion',
  id_canal            VARCHAR(5)      NOT NULL COMMENT 'Canal de origen',
  id_terminal         CHAR(36)        NULL COMMENT 'Terminal de origen',
  saldo_posterior     DECIMAL(15,2)   NOT NULL COMMENT 'Saldo disponible despues de la operacion',
  comision            DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Comision cobrada',
  itf                 DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Impuesto a las transacciones financieras',
  retencion           DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Retencion aplicada',
  estado_transaccion  ENUM('APLICADA','RECHAZADA','ANULADA','PENDIENTE') NOT NULL DEFAULT 'APLICADA'
                      COMMENT 'Estado de la transaccion',
  idempotency_key     VARCHAR(64)     NULL COMMENT 'Llave de idempotencia para reintentos',
  fecha_valor         DATE            NOT NULL COMMENT 'Fecha valor contable',
  fecha_hora          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora de la operacion',
  PRIMARY KEY (id_transaccion),
  UNIQUE KEY uk_transaccion_uuid (uuid_transaccion),
  UNIQUE KEY uk_transaccion_idem (idempotency_key),
  KEY idx_transaccion_cuenta_fecha (num_cuenta, fecha_hora),
  KEY idx_transaccion_canal_fecha (id_canal, fecha_valor),
  CONSTRAINT fk_transaccion_cuenta  FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT fk_transaccion_canal   FOREIGN KEY (id_canal) REFERENCES canal (id_canal),
  CONSTRAINT fk_transaccion_terminal FOREIGN KEY (id_terminal) REFERENCES terminal (id_terminal),
  CONSTRAINT ck_transaccion_mov CHECK (tipo_movimiento IN ('D','C')),
  CONSTRAINT ck_transaccion_monto CHECK (monto > 0)
) ENGINE=InnoDB COMMENT='Historico de transacciones de cuentas';

-- ---------------------------------------------------------------------
-- cta_retencion_saldo: retenciones de saldo (mejora: tabla faltante)
-- ---------------------------------------------------------------------
CREATE TABLE cta_retencion_saldo (
  id_retencion CHAR(36)        NOT NULL COMMENT 'Identificador de la retencion',
  num_cuenta   VARCHAR(20)     NOT NULL COMMENT 'Cuenta afectada',
  monto        DECIMAL(15,2)   NOT NULL COMMENT 'Monto retenido',
  motivo       VARCHAR(120)    NOT NULL COMMENT 'Motivo de la retencion',
  estado       ENUM('VIGENTE','LIBERADA','APLICADA') NOT NULL DEFAULT 'VIGENTE' COMMENT 'Estado',
  fecha_inicio DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Inicio de la retencion',
  fecha_fin    DATETIME(3)     NULL COMMENT 'Fin de la retencion',
  PRIMARY KEY (id_retencion),
  KEY idx_retencion_cuenta (num_cuenta, estado),
  CONSTRAINT fk_retencion_cuenta FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT ck_retencion_monto CHECK (monto > 0)
) ENGINE=InnoDB COMMENT='Retenciones de saldo por cuenta';

-- ---------------------------------------------------------------------
-- cta_control_tope_diario: acumulado diario por cuenta y canal
-- ---------------------------------------------------------------------
CREATE TABLE cta_control_tope_diario (
  id_tope          CHAR(36)        NOT NULL COMMENT 'Identificador del control',
  num_cuenta       VARCHAR(20)     NOT NULL COMMENT 'Cuenta controlada',
  id_canal         VARCHAR(5)      NOT NULL COMMENT 'Canal del tope',
  fecha_corte      DATE            NOT NULL COMMENT 'Dia del control',
  monto_acumulado  DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Monto acumulado del dia',
  PRIMARY KEY (id_tope),
  UNIQUE KEY uk_tope_cuenta_canal_dia (num_cuenta, id_canal, fecha_corte),
  CONSTRAINT fk_tope_cuenta FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT fk_tope_canal  FOREIGN KEY (id_canal) REFERENCES canal (id_canal)
) ENGINE=InnoDB COMMENT='Control de topes diarios por cuenta y canal';

-- ---------------------------------------------------------------------
-- cta_interes_mensual: calculo mensual de intereses (mejora TEA/TREA)
-- ---------------------------------------------------------------------
CREATE TABLE cta_interes_mensual (
  id_interes       CHAR(36)        NOT NULL COMMENT 'Identificador del calculo',
  num_cuenta       VARCHAR(20)     NOT NULL COMMENT 'Cuenta',
  anio             SMALLINT UNSIGNED NOT NULL COMMENT 'Anio del periodo',
  mes              TINYINT UNSIGNED  NOT NULL COMMENT 'Mes del periodo',
  saldo_promedio   DECIMAL(15,2)   NOT NULL COMMENT 'Saldo promedio del periodo',
  tasa_tea         DECIMAL(6,4)    NOT NULL COMMENT 'Tasa efectiva anual',
  tasa_trea        DECIMAL(6,4)    NOT NULL COMMENT 'Tasa de rendimiento efectivo anual (TREA)',
  interes_calculado DECIMAL(15,2)  NOT NULL COMMENT 'Interes calculado',
  estado           ENUM('CALCULADO','ABONADO','ANULADO') NOT NULL DEFAULT 'CALCULADO' COMMENT 'Estado',
  fecha_proceso    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de proceso',
  PRIMARY KEY (id_interes),
  UNIQUE KEY uk_interes_cuenta_periodo (num_cuenta, anio, mes),
  CONSTRAINT fk_interes_cuenta FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT ck_interes_mes CHECK (mes BETWEEN 1 AND 12)
) ENGINE=InnoDB COMMENT='Intereses mensuales de cuentas de ahorro';

-- <<< FIN 03_cuentas.sql

-- >>> INICIO 04_tarjetas.sql
-- =====================================================================
-- BNA - Script 04: Modulo Tarjetas
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Mejoras: PAN tokenizado; credenciales con algoritmo/version de hash;
--   intento de autenticacion con coordenada validada por CHECK; historial
--   de estado inmutable; evento de salida (patron outbox).
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- tar_tarjeta: tarjeta emitida al cliente (PAN tokenizado)
-- ---------------------------------------------------------------------
CREATE TABLE tar_tarjeta (
  id_tarjeta        CHAR(36)        NOT NULL COMMENT 'Identificador de la tarjeta',
  pan_token         VARCHAR(64)     NOT NULL COMMENT 'Token del PAN (nunca el PAN en claro)',
  bin               CHAR(6)         NOT NULL COMMENT 'Bank Identification Number',
  ultimos4          CHAR(4)         NOT NULL COMMENT 'Ultimos 4 digitos',
  id_cliente        CHAR(36)        NOT NULL COMMENT 'Cliente titular',
  tipo_tarjeta      ENUM('DEBITO','CREDITO','PREPAGO') NOT NULL COMMENT 'Tipo de tarjeta',
  fecha_emision     DATE            NOT NULL COMMENT 'Fecha de emision',
  fecha_vencimiento DATE            NOT NULL COMMENT 'Fecha de vencimiento',
  estado            ENUM('ACTIVA','BLOQUEADA','VENCIDA','ANULADA') NOT NULL DEFAULT 'ACTIVA'
                    COMMENT 'Estado de la tarjeta',
  fecha_creacion    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de alta',
  PRIMARY KEY (id_tarjeta),
  UNIQUE KEY uk_tarjeta_pan (pan_token),
  KEY idx_tarjeta_cliente (id_cliente, estado),
  CONSTRAINT fk_tarjeta_cliente FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
) ENGINE=InnoDB COMMENT='Tarjetas emitidas';

-- ---------------------------------------------------------------------
-- tar_tarjeta_cuenta: tarjetas asociadas a cuentas
-- ---------------------------------------------------------------------
CREATE TABLE tar_tarjeta_cuenta (
  id_tarjeta      CHAR(36)        NOT NULL COMMENT 'Tarjeta',
  num_cuenta      VARCHAR(20)     NOT NULL COMMENT 'Cuenta asociada',
  es_principal    TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 si es la cuenta principal',
  habilitada_atm  TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si opera en cajeros',
  fecha_vinculacion DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de vinculacion',
  PRIMARY KEY (id_tarjeta, num_cuenta),
  CONSTRAINT fk_tc_tarjeta FOREIGN KEY (id_tarjeta) REFERENCES tar_tarjeta (id_tarjeta),
  CONSTRAINT fk_tc_cuenta  FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta)
) ENGINE=InnoDB COMMENT='Vinculacion tarjeta-cuenta';

-- ---------------------------------------------------------------------
-- tar_credencial: credenciales de la tarjeta (PIN, clave web, token, matriz)
-- ---------------------------------------------------------------------
CREATE TABLE tar_credencial (
  id_credencial   CHAR(36)        NOT NULL COMMENT 'Identificador de la credencial',
  id_tarjeta      CHAR(36)        NOT NULL COMMENT 'Tarjeta asociada',
  tipo            ENUM('PIN_ATM','CLAVE_WEB','BIOMETRIA','TOKEN_PAGO','TOKEN_MATRIZ') NOT NULL
                  COMMENT 'Tipo de credencial',
  longitud        TINYINT UNSIGNED NOT NULL COMMENT 'Longitud de la credencial',
  hash_credencial CHAR(64)        NOT NULL COMMENT 'HMAC/SHA-256 de la credencial',
  sal             CHAR(32)        NOT NULL COMMENT 'Sal usada en el hash',
  algoritmo_hash  VARCHAR(20)     NOT NULL DEFAULT 'PBKDF2' COMMENT 'Algoritmo de hash',
  version_hash    VARCHAR(10)     NOT NULL DEFAULT 'v1' COMMENT 'Version del algoritmo',
  numero_serie    VARCHAR(30)     NULL COMMENT 'Numero de serie del dispositivo (si aplica)',
  intentos_fallidos TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Intentos fallidos',
  bloqueada       TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 si la credencial esta bloqueada',
  fecha_creacion  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de alta',
  fecha_ultimo_cambio DATETIME(3) NULL COMMENT 'Ultima actualizacion',
  PRIMARY KEY (id_credencial),
  UNIQUE KEY uk_credencial_tipo (id_tarjeta, tipo),
  CONSTRAINT fk_credencial_tarjeta FOREIGN KEY (id_tarjeta) REFERENCES tar_tarjeta (id_tarjeta)
) ENGINE=InnoDB COMMENT='Credenciales de tarjeta';

-- ---------------------------------------------------------------------
-- tar_matriz_token: tarjeta matriz de coordenadas (token fisico)
-- ---------------------------------------------------------------------
CREATE TABLE tar_matriz_token (
  id_matriz     CHAR(36)        NOT NULL COMMENT 'Identificador de la matriz',
  id_credencial CHAR(36)        NOT NULL COMMENT 'Credencial tipo TOKEN_MATRIZ',
  fecha_emision DATE            NOT NULL COMMENT 'Fecha de emision',
  activa        TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si la matriz esta activa',
  PRIMARY KEY (id_matriz),
  CONSTRAINT fk_matriz_credencial FOREIGN KEY (id_credencial) REFERENCES tar_credencial (id_credencial)
) ENGINE=InnoDB COMMENT='Tarjetas matriz de coordenadas';

-- ---------------------------------------------------------------------
-- tar_matriz_coordenada: valores por coordenada de la matriz
-- ---------------------------------------------------------------------
CREATE TABLE tar_matriz_coordenada (
  id_coordenada CHAR(36)        NOT NULL COMMENT 'Identificador de la coordenada',
  id_matriz     CHAR(36)        NOT NULL COMMENT 'Matriz a la que pertenece',
  fila          CHAR(1)         NOT NULL COMMENT 'Fila (A-H)',
  columna       TINYINT UNSIGNED NOT NULL COMMENT 'Columna (1-8)',
  hash_valor    CHAR(64)        NOT NULL COMMENT 'HMAC del valor de la coordenada',
  PRIMARY KEY (id_coordenada),
  UNIQUE KEY uk_coordenada_matriz (id_matriz, fila, columna),
  CONSTRAINT fk_coordenada_matriz FOREIGN KEY (id_matriz) REFERENCES tar_matriz_token (id_matriz),
  CONSTRAINT ck_coordenada_fila CHECK (fila BETWEEN 'A' AND 'H'),
  CONSTRAINT ck_coordenada_col CHECK (columna BETWEEN 1 AND 8)
) ENGINE=InnoDB COMMENT='Coordenadas de la tarjeta matriz';

-- ---------------------------------------------------------------------
-- tar_token_pago: tokens de pago de un solo uso
-- ---------------------------------------------------------------------
CREATE TABLE tar_token_pago (
  id_token      CHAR(36)        NOT NULL COMMENT 'Identificador del token',
  id_credencial CHAR(36)        NOT NULL COMMENT 'Credencial tipo TOKEN_PAGO',
  valor_hash    CHAR(64)        NOT NULL COMMENT 'Hash del token de pago',
  fecha_expiracion DATETIME(3)  NOT NULL COMMENT 'Expiracion del token',
  usada         TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 si ya fue usada',
  PRIMARY KEY (id_token),
  CONSTRAINT fk_token_credencial FOREIGN KEY (id_credencial) REFERENCES tar_credencial (id_credencial)
) ENGINE=InnoDB COMMENT='Tokens de pago de un solo uso';

-- ---------------------------------------------------------------------
-- tar_intento_autenticacion: registro de cada intento de autenticacion
-- ---------------------------------------------------------------------
CREATE TABLE tar_intento_autenticacion (
  id_intento           CHAR(36)        NOT NULL COMMENT 'Identificador del intento',
  id_tarjeta           CHAR(36)        NOT NULL COMMENT 'Tarjeta usada',
  tipo_credencial      ENUM('PIN_ATM','CLAVE_WEB','BIOMETRIA','TOKEN_PAGO','TOKEN_MATRIZ') NOT NULL
                       COMMENT 'Credencial evaluada',
  coordenada_solicitada CHAR(2)       NULL COMMENT 'Coordenada pedida, ej. C4 (solo matriz)',
  id_canal             VARCHAR(5)     NOT NULL COMMENT 'Canal del intento',
  id_terminal          CHAR(36)        NULL COMMENT 'Terminal del intento',
  resultado            ENUM('EXITOSO','FALLIDO') NOT NULL COMMENT 'Resultado del intento',
  motivo_rechazo       VARCHAR(120)   NULL COMMENT 'Motivo del rechazo',
  uuid_correlacion     CHAR(36)       NULL COMMENT 'Correlacion con la autorizacion',
  fecha_hora           DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora',
  PRIMARY KEY (id_intento),
  KEY idx_intento_tarjeta (id_tarjeta, fecha_hora),
  CONSTRAINT fk_intento_tarjeta  FOREIGN KEY (id_tarjeta) REFERENCES tar_tarjeta (id_tarjeta),
  CONSTRAINT fk_intento_canal    FOREIGN KEY (id_canal) REFERENCES canal (id_canal),
  CONSTRAINT fk_intento_terminal FOREIGN KEY (id_terminal) REFERENCES terminal (id_terminal),
  CONSTRAINT ck_intento_coord CHECK (coordenada_solicitada IS NULL OR CHAR_LENGTH(coordenada_solicitada) = 2)
) ENGINE=InnoDB COMMENT='Intentos de autenticacion de tarjetas';

-- ---------------------------------------------------------------------
-- tar_autorizacion: autorizacion de una operacion con tarjeta
-- ---------------------------------------------------------------------
CREATE TABLE tar_autorizacion (
  uuid_transaccion   CHAR(36)        NOT NULL COMMENT 'Identificador unico de la operacion',
  id_tarjeta         CHAR(36)        NOT NULL COMMENT 'Tarjeta',
  num_cuenta         VARCHAR(20)     NOT NULL COMMENT 'Cuenta afectada',
  id_canal           VARCHAR(5)      NOT NULL COMMENT 'Canal de la operacion',
  tipo_operacion     ENUM('COMPRA','RETIRO','TRANSFERENCIA','CONSULTA','PAGO') NOT NULL
                     COMMENT 'Tipo de operacion',
  monto              DECIMAL(15,2)   NOT NULL COMMENT 'Importe solicitado',
  moneda             CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda',
  estado             ENUM('APROBADA','RECHAZADA','PENDIENTE') NOT NULL DEFAULT 'PENDIENTE'
                     COMMENT 'Estado de la autorizacion',
  codigo_respuesta   VARCHAR(10)     NULL COMMENT 'Codigo de respuesta',
  motivo_rechazo     VARCHAR(120)    NULL COMMENT 'Motivo de rechazo',
  nivel_riesgo       ENUM('BAJO','MEDIO','ALTO') NULL COMMENT 'Nivel de riesgo evaluado',
  id_terminal        CHAR(36)        NULL COMMENT 'Terminal de la operacion',
  num_asiento_core   VARCHAR(30)     NULL COMMENT 'Referencia del asiento en el core',
  fecha_hora         DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora',
  fecha_actualizacion DATETIME(3)    NULL COMMENT 'Ultima actualizacion',
  PRIMARY KEY (uuid_transaccion),
  KEY idx_autoriz_tarjeta (id_tarjeta, fecha_hora),
  CONSTRAINT fk_autoriz_tarjeta  FOREIGN KEY (id_tarjeta) REFERENCES tar_tarjeta (id_tarjeta),
  CONSTRAINT fk_autoriz_cuenta   FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT fk_autoriz_canal    FOREIGN KEY (id_canal) REFERENCES canal (id_canal),
  CONSTRAINT fk_autoriz_terminal FOREIGN KEY (id_terminal) REFERENCES terminal (id_terminal),
  CONSTRAINT ck_autoriz_monto CHECK (monto > 0)
) ENGINE=InnoDB COMMENT='Autorizaciones de operaciones con tarjeta';

-- ---------------------------------------------------------------------
-- tar_historial_estado: historial inmutable de cambios de estado
-- ---------------------------------------------------------------------
CREATE TABLE tar_historial_estado (
  id_historial   CHAR(36)        NOT NULL COMMENT 'Identificador del cambio',
  id_tarjeta     CHAR(36)        NOT NULL COMMENT 'Tarjeta',
  estado_anterior ENUM('ACTIVA','BLOQUEADA','VENCIDA','ANULADA') NOT NULL COMMENT 'Estado anterior',
  estado_nuevo   ENUM('ACTIVA','BLOQUEADA','VENCIDA','ANULADA') NOT NULL COMMENT 'Estado nuevo',
  motivo         VARCHAR(120)    NOT NULL COMMENT 'Motivo del cambio',
  origen         ENUM('CLIENTE','BANCO','SISTEMA','REGULADOR') NOT NULL COMMENT 'Origen del cambio',
  fecha_hora     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora',
  PRIMARY KEY (id_historial),
  KEY idx_historial_tarjeta (id_tarjeta, fecha_hora),
  CONSTRAINT fk_historial_tarjeta FOREIGN KEY (id_tarjeta) REFERENCES tar_tarjeta (id_tarjeta)
) ENGINE=InnoDB COMMENT='Historial de estados de tarjeta';

-- ---------------------------------------------------------------------
-- tar_evento_salida: patron outbox para eventos hacia otros sistemas
-- ---------------------------------------------------------------------
CREATE TABLE tar_evento_salida (
  id_evento      CHAR(36)        NOT NULL COMMENT 'Identificador del evento',
  tipo_evento    VARCHAR(40)     NOT NULL COMMENT 'Tipo de evento publicado',
  id_tarjeta     CHAR(36)        NULL COMMENT 'Tarjeta relacionada',
  payload        JSON            NOT NULL COMMENT 'Carga util del evento',
  estado         ENUM('PENDIENTE','PUBLICADO','ERROR') NOT NULL DEFAULT 'PENDIENTE' COMMENT 'Estado',
  fecha_creacion DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de creacion',
  fecha_procesado DATETIME(3)    NULL COMMENT 'Fecha de publicacion',
  PRIMARY KEY (id_evento),
  KEY idx_evento_estado (estado, fecha_creacion),
  CONSTRAINT fk_evento_tarjeta FOREIGN KEY (id_tarjeta) REFERENCES tar_tarjeta (id_tarjeta)
) ENGINE=InnoDB COMMENT='Eventos de salida (outbox) del modulo tarjetas';

-- <<< FIN 04_tarjetas.sql

-- >>> INICIO 05_captacion.sql
-- =====================================================================
-- BNA - Script 05: Modulo Captacion de Clientes
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Basado en Entregable-1-GSTI (TOGAF): Agencia, Asesor, Solicitante,
--   Caso, Consentimiento, Validacion de Identidad, Consulta/Reporte de
--   riesgos, Perfil del solicitante. Mejora: id_solicitante para KYC de
--   no clientes y auditoria de consultas.
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- cap_solicitante: persona que inicia la captacion (puede no ser cliente)
-- ---------------------------------------------------------------------
CREATE TABLE cap_solicitante (
  id_solicitante     CHAR(36)        NOT NULL COMMENT 'Identificador del solicitante',
  id_cliente         CHAR(36)        NULL COMMENT 'Cliente ya existente, si aplica',
  cod_tipo_documento VARCHAR(10)     NOT NULL COMMENT 'Tipo de documento',
  numero_documento   VARCHAR(20)     NOT NULL COMMENT 'Numero de documento',
  nombres            VARCHAR(80)     NOT NULL COMMENT 'Nombres',
  apellidos          VARCHAR(80)     NOT NULL COMMENT 'Apellidos',
  celular            VARCHAR(15)     NOT NULL COMMENT 'Celular de contacto',
  correo             VARCHAR(120)    NULL COMMENT 'Correo de contacto',
  fecha_registro     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de registro',
  PRIMARY KEY (id_solicitante),
  UNIQUE KEY uk_solicitante_doc (cod_tipo_documento, numero_documento),
  CONSTRAINT fk_solicitante_cliente FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente),
  CONSTRAINT fk_solicitante_tipodoc FOREIGN KEY (cod_tipo_documento) REFERENCES tipo_documento (cod_tipo_documento)
) ENGINE=InnoDB COMMENT='Solicitantes de captacion';

-- ---------------------------------------------------------------------
-- cap_perfil_riesgo: perfil de riesgo calculado del solicitante
-- ---------------------------------------------------------------------
CREATE TABLE cap_perfil_riesgo (
  id_perfil       CHAR(36)        NOT NULL COMMENT 'Identificador del perfil',
  id_solicitante  CHAR(36)        NOT NULL COMMENT 'Solicitante evaluado',
  calificacion    ENUM('BAJO','MEDIO','ALTO','MUY_ALTO') NOT NULL COMMENT 'Calificacion de riesgo',
  puntaje         SMALLINT UNSIGNED NOT NULL COMMENT 'Puntaje calculado (0-1000)',
  observacion     VARCHAR(200)    NULL COMMENT 'Observaciones',
  fecha_calculo   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha del calculo',
  PRIMARY KEY (id_perfil),
  KEY idx_perfil_solicitante (id_solicitante, fecha_calculo),
  CONSTRAINT fk_perfil_solicitante FOREIGN KEY (id_solicitante) REFERENCES cap_solicitante (id_solicitante),
  CONSTRAINT ck_perfil_puntaje CHECK (puntaje <= 1000)
) ENGINE=InnoDB COMMENT='Perfil de riesgo del solicitante';

-- ---------------------------------------------------------------------
-- cap_caso: caso de captacion (expediente)
-- ---------------------------------------------------------------------
CREATE TABLE cap_caso (
  id_caso          CHAR(36)        NOT NULL COMMENT 'Identificador del caso',
  id_solicitante   CHAR(36)        NOT NULL COMMENT 'Solicitante',
  id_asesor        CHAR(36)        NULL COMMENT 'Asesor que atiende el caso',
  id_agencia       CHAR(36)        NULL COMMENT 'Agencia del caso',
  id_producto_credito CHAR(36)        NULL COMMENT 'Producto de interes',
  canal_captacion  ENUM('AGENCIA','WEB','MOVIL','AGENTE','CAMPANA') NOT NULL COMMENT 'Canal de captacion',
  estado_caso      ENUM('INICIADO','EN_VALIDACION','OBSERVADO','APROBADO','RECHAZADO','DERIVADO')
                   NOT NULL DEFAULT 'INICIADO' COMMENT 'Estado del caso',
  id_solicitud     CHAR(36)        NULL COMMENT 'Solicitud de credito generada (referencia logica)',
  fecha_apertura   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de apertura',
  fecha_cierre     DATETIME(3)     NULL COMMENT 'Fecha de cierre',
  PRIMARY KEY (id_caso),
  KEY idx_caso_solicitante (id_solicitante, estado_caso),
  CONSTRAINT fk_caso_solicitante FOREIGN KEY (id_solicitante) REFERENCES cap_solicitante (id_solicitante),
  CONSTRAINT fk_caso_asesor      FOREIGN KEY (id_asesor) REFERENCES empleado (id_empleado),
  CONSTRAINT fk_caso_agencia     FOREIGN KEY (id_agencia) REFERENCES agencia (id_agencia),
  CONSTRAINT fk_caso_producto    FOREIGN KEY (id_producto_credito) REFERENCES producto_credito (id_producto_credito)
) ENGINE=InnoDB COMMENT='Casos de captacion';

-- ---------------------------------------------------------------------
-- cap_consentimiento: consentimientos informados del solicitante
-- ---------------------------------------------------------------------
CREATE TABLE cap_consentimiento (
  id_consentimiento CHAR(36)        NOT NULL COMMENT 'Identificador del consentimiento',
  id_caso           CHAR(36)        NOT NULL COMMENT 'Caso asociado',
  tipo_consentimiento ENUM('TRATAMIENTO_DATOS','CONSULTA_BUROS','BIOMETRIA','TERMINOS') NOT NULL
                      COMMENT 'Tipo de consentimiento',
  aceptado          TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 si fue aceptado',
  medio             ENUM('DIGITAL','FISICO','BIOMETRICO') NOT NULL COMMENT 'Medio de otorgamiento',
  fecha_otorgamiento DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de otorgamiento',
  PRIMARY KEY (id_consentimiento),
  CONSTRAINT fk_consentimiento_caso FOREIGN KEY (id_caso) REFERENCES cap_caso (id_caso)
) ENGINE=InnoDB COMMENT='Consentimientos del solicitante';

-- ---------------------------------------------------------------------
-- cap_validacion_identidad: resultados de validacion de identidad
-- ---------------------------------------------------------------------
CREATE TABLE cap_validacion_identidad (
  id_validacion   CHAR(36)        NOT NULL COMMENT 'Identificador de la validacion',
  id_caso         CHAR(36)        NOT NULL COMMENT 'Caso asociado',
  id_solicitante  CHAR(36)        NOT NULL COMMENT 'Solicitante validado',
  tipo_validacion ENUM('RENIEC','BIOMETRIA','LISTAS_NEGRAS','PEP','INTERNA') NOT NULL
                  COMMENT 'Tipo de validacion',
  resultado       ENUM('APROBADO','RECHAZADO','OBSERVADO') NOT NULL COMMENT 'Resultado',
  proveedor       VARCHAR(60)     NULL COMMENT 'Proveedor externo',
  detalle         VARCHAR(200)    NULL COMMENT 'Detalle del resultado',
  fecha_validacion DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de validacion',
  PRIMARY KEY (id_validacion),
  KEY idx_valida_caso (id_caso, tipo_validacion),
  CONSTRAINT fk_ci_caso        FOREIGN KEY (id_caso) REFERENCES cap_caso (id_caso),
  CONSTRAINT fk_ci_solicitante FOREIGN KEY (id_solicitante) REFERENCES cap_solicitante (id_solicitante)
) ENGINE=InnoDB COMMENT='Validaciones de identidad del caso';

-- ---------------------------------------------------------------------
-- cap_consulta_riesgos: consultas a centrales de riesgo
-- ---------------------------------------------------------------------
CREATE TABLE cap_consulta_riesgos (
  id_consulta     CHAR(36)        NOT NULL COMMENT 'Identificador de la consulta',
  id_caso         CHAR(36)        NOT NULL COMMENT 'Caso asociado',
  id_solicitante  CHAR(36)        NOT NULL COMMENT 'Solicitante consultado',
  central         ENUM('SBS','INFOCORP','SENTINEL','EQUIFAX','OTRA') NOT NULL COMMENT 'Central consultada',
  motivo          VARCHAR(120)    NOT NULL COMMENT 'Motivo de la consulta',
  resultado       ENUM('NORMAL','CPP','DEFICIENTE','DUDOSO','PERDIDA') NULL COMMENT 'Calificacion obtenida',
  fecha_consulta  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de la consulta',
  PRIMARY KEY (id_consulta),
  KEY idx_consulta_caso (id_caso, central),
  CONSTRAINT fk_consulta_caso        FOREIGN KEY (id_caso) REFERENCES cap_caso (id_caso),
  CONSTRAINT fk_consulta_solicitante FOREIGN KEY (id_solicitante) REFERENCES cap_solicitante (id_solicitante)
) ENGINE=InnoDB COMMENT='Consultas a centrales de riesgo';

-- ---------------------------------------------------------------------
-- cap_reporte_riesgos: reporte detallado obtenido de la central
-- ---------------------------------------------------------------------
CREATE TABLE cap_reporte_riesgos (
  id_reporte      CHAR(36)        NOT NULL COMMENT 'Identificador del reporte',
  id_consulta     CHAR(36)        NOT NULL COMMENT 'Consulta asociada',
  calificacion    ENUM('NORMAL','CPP','DEFICIENTE','DUDOSO','PERDIDA') NOT NULL COMMENT 'Calificacion vigente',
  deuda_total     DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Deuda total reportada',
  entidades       SMALLINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Numero de entidades reportantes',
  dias_mayor_mora SMALLINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Dias de mayor mora',
  archivo_pdf     VARCHAR(200)    NULL COMMENT 'Ruta del reporte PDF almacenado',
  fecha_reporte   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha del reporte',
  PRIMARY KEY (id_reporte),
  CONSTRAINT fk_reporte_consulta FOREIGN KEY (id_consulta) REFERENCES cap_consulta_riesgos (id_consulta)
) ENGINE=InnoDB COMMENT='Reportes de centrales de riesgo';

-- ---------------------------------------------------------------------
-- cap_auditoria_consulta: trazabilidad de consultas a centrales
-- ---------------------------------------------------------------------
CREATE TABLE cap_auditoria_consulta (
  id_auditoria    CHAR(36)        NOT NULL COMMENT 'Identificador de la auditoria',
  id_consulta     CHAR(36)        NOT NULL COMMENT 'Consulta auditada',
  id_usuario      CHAR(36)        NULL COMMENT 'Usuario solicitante',
  id_empleado     CHAR(36)        NULL COMMENT 'Empleado solicitante',
  accion          ENUM('CONSULTA','REENVIO','ANULACION') NOT NULL COMMENT 'Accion realizada',
  correlation_id  CHAR(36)        NULL COMMENT 'Correlacion del Bus',
  fecha_hora      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora',
  PRIMARY KEY (id_auditoria),
  KEY idx_auc_consulta (id_consulta),
  CONSTRAINT fk_auc_consulta FOREIGN KEY (id_consulta) REFERENCES cap_consulta_riesgos (id_consulta),
  CONSTRAINT fk_auc_usuario  FOREIGN KEY (id_usuario) REFERENCES usuario_sistema (id_usuario),
  CONSTRAINT fk_auc_empleado FOREIGN KEY (id_empleado) REFERENCES empleado (id_empleado)
) ENGINE=InnoDB COMMENT='Auditoria de consultas a centrales de riesgo';

-- <<< FIN 05_captacion.sql

-- >>> INICIO 06_solicitud.sql
-- =====================================================================
-- BNA - Script 06: Modulo Solicitud de Credito
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Basado en el diccionario de Solicitud de Credito: SOLICITUD,
--   FIADOR, GARANTIA, HISTORIAL_ESTADO, CALENDARIO_VERSION, CUOTA.
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- sol_solicitud: solicitud de credito
-- ---------------------------------------------------------------------
CREATE TABLE sol_solicitud (
  id_solicitud        CHAR(36)        NOT NULL COMMENT 'Identificador de la solicitud',
  id_cliente          CHAR(36)        NOT NULL COMMENT 'Cliente solicitante',
  id_caso             CHAR(36)        NULL COMMENT 'Caso de captacion origen',
  id_producto_credito CHAR(36)        NOT NULL COMMENT 'Producto solicitado',
  id_asesor           CHAR(36)        NULL COMMENT 'Asesor de la solicitud',
  id_agencia          CHAR(36)        NULL COMMENT 'Agencia de origen',
  monto_solicitado    DECIMAL(15,2)   NOT NULL COMMENT 'Monto solicitado',
  moneda              CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda del credito',
  plazo_meses         INT             NOT NULL COMMENT 'Plazo en meses',
  destino_credito     VARCHAR(120)    NOT NULL COMMENT 'Destino del credito',
  estado_solicitud    ENUM('REGISTRADA','EN_EVALUACION','APROBADA','RECHAZADA','DESEMBOLSADA','ANULADA')
                      NOT NULL DEFAULT 'REGISTRADA' COMMENT 'Estado de la solicitud',
  fecha_registro      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de registro',
  PRIMARY KEY (id_solicitud),
  KEY idx_sol_cliente (id_cliente, estado_solicitud),
  CONSTRAINT fk_sol_cliente  FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente),
  CONSTRAINT fk_sol_caso     FOREIGN KEY (id_caso) REFERENCES cap_caso (id_caso),
  CONSTRAINT fk_sol_producto FOREIGN KEY (id_producto_credito) REFERENCES producto_credito (id_producto_credito),
  CONSTRAINT fk_sol_asesor   FOREIGN KEY (id_asesor) REFERENCES empleado (id_empleado),
  CONSTRAINT fk_sol_agencia  FOREIGN KEY (id_agencia) REFERENCES agencia (id_agencia),
  CONSTRAINT fk_sol_moneda   FOREIGN KEY (moneda) REFERENCES moneda (cod_moneda),
  CONSTRAINT ck_sol_monto CHECK (monto_solicitado > 0 AND plazo_meses > 0)
) ENGINE=InnoDB COMMENT='Solicitudes de credito';

-- ---------------------------------------------------------------------
-- sol_fiador: fiadores del credito
-- ---------------------------------------------------------------------
CREATE TABLE sol_fiador (
  id_fiador          CHAR(36)        NOT NULL COMMENT 'Identificador del fiador',
  id_solicitud       CHAR(36)        NOT NULL COMMENT 'Solicitud',
  id_cliente         CHAR(36)        NULL COMMENT 'Cliente fiador, si existe',
  cod_tipo_documento VARCHAR(10)     NULL COMMENT 'Tipo de documento del fiador',
  numero_documento   VARCHAR(20)     NOT NULL COMMENT 'Documento del fiador',
  nombre_completo    VARCHAR(140)    NOT NULL COMMENT 'Nombre completo',
  telefono           VARCHAR(15)     NULL COMMENT 'Telefono',
  ingreso_mensual    DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Ingreso mensual declarado',
  tipo_fiador        ENUM('PERSONAL','SOLIDARIO','MANCOMUNADO') NOT NULL DEFAULT 'PERSONAL'
                     COMMENT 'Tipo de fianza',
  PRIMARY KEY (id_fiador),
  KEY idx_fiador_solicitud (id_solicitud),
  CONSTRAINT fk_fiador_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT fk_fiador_cliente   FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente),
  CONSTRAINT fk_fiador_tipodoc   FOREIGN KEY (cod_tipo_documento) REFERENCES tipo_documento (cod_tipo_documento)
) ENGINE=InnoDB COMMENT='Fiadores de la solicitud';

-- ---------------------------------------------------------------------
-- sol_garantia: garantias presentadas
-- ---------------------------------------------------------------------
CREATE TABLE sol_garantia (
  id_garantia     CHAR(36)        NOT NULL COMMENT 'Identificador de la garantia',
  id_solicitud    CHAR(36)        NOT NULL COMMENT 'Solicitud',
  tipo_garantia   ENUM('PERSONAL','HIPOTECARIA','VEHICULAR','MOBILIARIA','FONDOS','SIN_GARANTIA')
                  NOT NULL COMMENT 'Tipo de garantia',
  descripcion     VARCHAR(200)    NOT NULL COMMENT 'Descripcion de la garantia',
  valor_tasacion  DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Valor de tasacion',
  entidad_registro VARCHAR(100)   NULL COMMENT 'Registro (SUNARP, etc.)',
  partida_registral VARCHAR(40)   NULL COMMENT 'Partida registral',
  fecha_tasacion  DATE            NULL COMMENT 'Fecha de tasacion',
  PRIMARY KEY (id_garantia),
  KEY idx_garantia_solicitud (id_solicitud),
  CONSTRAINT fk_garantia_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT ck_garantia_valor CHECK (valor_tasacion >= 0)
) ENGINE=InnoDB COMMENT='Garantias de la solicitud';

-- ---------------------------------------------------------------------
-- sol_historial_estado: historial de cambios de estado de la solicitud
-- ---------------------------------------------------------------------
CREATE TABLE sol_historial_estado (
  id_historial    CHAR(36)        NOT NULL COMMENT 'Identificador del cambio',
  id_solicitud    CHAR(36)        NOT NULL COMMENT 'Solicitud',
  estado_anterior ENUM('REGISTRADA','EN_EVALUACION','APROBADA','RECHAZADA','DESEMBOLSADA','ANULADA') NULL
                  COMMENT 'Estado anterior',
  estado_nuevo    ENUM('REGISTRADA','EN_EVALUACION','APROBADA','RECHAZADA','DESEMBOLSADA','ANULADA') NOT NULL
                  COMMENT 'Estado nuevo',
  motivo          VARCHAR(200)    NULL COMMENT 'Motivo del cambio',
  id_usuario      CHAR(36)        NULL COMMENT 'Usuario que realizo el cambio',
  fecha_hora      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora',
  PRIMARY KEY (id_historial),
  KEY idx_solhist_solicitud (id_solicitud, fecha_hora),
  CONSTRAINT fk_solhist_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT fk_solhist_usuario   FOREIGN KEY (id_usuario) REFERENCES usuario_sistema (id_usuario)
) ENGINE=InnoDB COMMENT='Historial de estados de la solicitud';

-- ---------------------------------------------------------------------
-- sol_calendario_version: versiones del calendario de pagos
-- ---------------------------------------------------------------------
CREATE TABLE sol_calendario_version (
  id_calendario   CHAR(36)        NOT NULL COMMENT 'Identificador del calendario',
  id_solicitud    CHAR(36)        NOT NULL COMMENT 'Solicitud',
  version         SMALLINT UNSIGNED NOT NULL COMMENT 'Numero de version',
  tasa_tea        DECIMAL(6,4)    NOT NULL COMMENT 'Tasa efectiva anual aplicada',
  numero_cuotas   INT             NOT NULL COMMENT 'Numero de cuotas',
  monto_financiado DECIMAL(15,2)  NOT NULL COMMENT 'Monto financiado',
  estado          ENUM('SIMULADO','VIGENTE','REEMPLAZADO') NOT NULL DEFAULT 'SIMULADO' COMMENT 'Estado de la version',
  fecha_creacion  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de creacion',
  PRIMARY KEY (id_calendario),
  UNIQUE KEY uk_calendario_solicitud_version (id_solicitud, version),
  CONSTRAINT fk_calendario_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT ck_calendario_monto CHECK (monto_financiado > 0 AND numero_cuotas > 0)
) ENGINE=InnoDB COMMENT='Versiones del calendario de pagos';

-- ---------------------------------------------------------------------
-- sol_cuota_calendario: cuotas proyectadas del calendario
-- ---------------------------------------------------------------------
CREATE TABLE sol_cuota_calendario (
  id_cuota        CHAR(36)        NOT NULL COMMENT 'Identificador de la cuota',
  id_calendario   CHAR(36)        NOT NULL COMMENT 'Calendario al que pertenece',
  numero_cuota    INT             NOT NULL COMMENT 'Numero de cuota',
  fecha_vencimiento DATE          NOT NULL COMMENT 'Fecha de vencimiento',
  saldo_inicial   DECIMAL(15,2)   NOT NULL COMMENT 'Saldo inicial',
  amortizacion    DECIMAL(15,2)   NOT NULL COMMENT 'Amortizacion de capital',
  interes         DECIMAL(15,2)   NOT NULL COMMENT 'Interes de la cuota',
  cuota_total     DECIMAL(15,2)   NOT NULL COMMENT 'Cuota total a pagar',
  saldo_final     DECIMAL(15,2)   NOT NULL COMMENT 'Saldo final',
  PRIMARY KEY (id_cuota),
  UNIQUE KEY uk_cuota_calendario (id_calendario, numero_cuota),
  CONSTRAINT fk_cuota_calendario FOREIGN KEY (id_calendario) REFERENCES sol_calendario_version (id_calendario),
  CONSTRAINT ck_cuota_montos CHECK (amortizacion >= 0 AND interes >= 0)
) ENGINE=InnoDB COMMENT='Cuotas proyectadas del calendario';

-- <<< FIN 06_solicitud.sql

-- >>> INICIO 07_evaluacion.sql
-- =====================================================================
-- BNA - Script 07: Modulo Evaluacion de Credito
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Basado en el modelo relacional: SITUACION_FINANCIERA_CLIENTE,
--   REGLA_EVALUACION, EVALUACION y DECISION_ANALISTA (el analista usa
--   la tabla compartida empleado).
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- eva_regla: reglas de evaluacion (catalogo)
-- ---------------------------------------------------------------------
CREATE TABLE eva_regla (
  id_regla        CHAR(36)        NOT NULL COMMENT 'Identificador de la regla',
  nombre          VARCHAR(80)     NOT NULL COMMENT 'Nombre de la regla',
  descripcion     VARCHAR(200)    NOT NULL COMMENT 'Descripcion de la regla',
  variable        VARCHAR(60)     NOT NULL COMMENT 'Variable evaluada (ratio, mora, etc.)',
  operador        ENUM('MAYOR','MENOR','IGUAL','ENTRE','EXCLUYE') NOT NULL COMMENT 'Operador de comparacion',
  valor_min       DECIMAL(15,4)   NULL COMMENT 'Valor minimo del rango',
  valor_max       DECIMAL(15,4)   NULL COMMENT 'Valor maximo del rango',
  resultado       ENUM('APROBAR','OBSERVAR','RECHAZAR') NOT NULL COMMENT 'Resultado si la regla se cumple',
  peso            DECIMAL(5,2)    NOT NULL DEFAULT 1 COMMENT 'Peso de la regla en el puntaje',
  activa          TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si la regla esta vigente',
  PRIMARY KEY (id_regla),
  UNIQUE KEY uk_regla_nombre (nombre)
) ENGINE=InnoDB COMMENT='Reglas de evaluacion de credito';

-- ---------------------------------------------------------------------
-- eva_situacion_financiera: situacion financiera declarada del cliente
-- ---------------------------------------------------------------------
CREATE TABLE eva_situacion_financiera (
  id_situacion      CHAR(36)        NOT NULL COMMENT 'Identificador de la situacion',
  id_solicitud      CHAR(36)        NOT NULL COMMENT 'Solicitud evaluada',
  id_cliente        CHAR(36)        NOT NULL COMMENT 'Cliente',
  ingresos_mensuales DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT 'Ingresos mensuales netos',
  egresos_mensuales  DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT 'Egresos mensuales',
  patrimonio         DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT 'Patrimonio declarado',
  cuota_otros_creditos DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT 'Cuotas de otros creditos',
  ratio_capacidad    DECIMAL(9,4)  NULL COMMENT 'Ratio de capacidad de pago',
  fecha_declaracion  DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de declaracion',
  PRIMARY KEY (id_situacion),
  KEY idx_situacion_cliente (id_cliente),
  CONSTRAINT fk_situacion_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT fk_situacion_cliente   FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
) ENGINE=InnoDB COMMENT='Situacion financiera del cliente';

-- ---------------------------------------------------------------------
-- eva_evaluacion: resultado de la evaluacion automatica
-- ---------------------------------------------------------------------
CREATE TABLE eva_evaluacion (
  id_evaluacion   CHAR(36)        NOT NULL COMMENT 'Identificador de la evaluacion',
  id_solicitud    CHAR(36)        NOT NULL COMMENT 'Solicitud evaluada',
  puntaje         SMALLINT UNSIGNED NOT NULL COMMENT 'Puntaje total obtenido',
  resultado       ENUM('APROBADO','OBSERVADO','RECHAZADO') NOT NULL COMMENT 'Resultado de la evaluacion',
  monto_maximo_sugerido DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT 'Monto maximo sugerido',
  nivel_riesgo    ENUM('BAJO','MEDIO','ALTO','MUY_ALTO') NOT NULL COMMENT 'Nivel de riesgo',
  detalle_reglas  JSON            NULL COMMENT 'Detalle del cumplimiento de cada regla',
  fecha_evaluacion DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de evaluacion',
  PRIMARY KEY (id_evaluacion),
  KEY idx_eval_solicitud (id_solicitud, fecha_evaluacion),
  CONSTRAINT fk_eval_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT ck_eval_puntaje CHECK (puntaje <= 1000)
) ENGINE=InnoDB COMMENT='Evaluaciones automaticas de credito';

-- ---------------------------------------------------------------------
-- eva_decision_analista: decision final del analista
-- ---------------------------------------------------------------------
CREATE TABLE eva_decision_analista (
  id_decision     CHAR(36)        NOT NULL COMMENT 'Identificador de la decision',
  id_evaluacion   CHAR(36)        NOT NULL COMMENT 'Evaluacion asociada',
  id_analista     CHAR(36)        NOT NULL COMMENT 'Analista que decide',
  decision        ENUM('APROBAR','RECHAZAR','OBSERVAR','DERIVAR') NOT NULL COMMENT 'Decision',
  monto_aprobado  DECIMAL(15,2)   NULL COMMENT 'Monto aprobado',
  plazo_aprobado  INT             NULL COMMENT 'Plazo aprobado en meses',
  observacion     VARCHAR(300)    NULL COMMENT 'Sustento de la decision',
  fecha_decision  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de decision',
  PRIMARY KEY (id_decision),
  KEY idx_decision_evaluacion (id_evaluacion),
  CONSTRAINT fk_decision_eval     FOREIGN KEY (id_evaluacion) REFERENCES eva_evaluacion (id_evaluacion),
  CONSTRAINT fk_decision_analista FOREIGN KEY (id_analista) REFERENCES empleado (id_empleado)
) ENGINE=InnoDB COMMENT='Decision final del analista';

-- <<< FIN 07_evaluacion.sql

-- >>> INICIO 08_desembolso.sql
-- =====================================================================
-- BNA - Script 08: Modulo Desembolso
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Basado en el Modelo Referencial: ORDEN, VALIDACION, EVENTO_ENTREGA,
--   AUDITORIA y SOLICITUD_REVERSION. Mejora: la reversion exige un
--   autorizador distinto y deja transaccion de reposicion.
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- des_orden: orden de desembolso
-- ---------------------------------------------------------------------
CREATE TABLE des_orden (
  id_orden        CHAR(36)        NOT NULL COMMENT 'Identificador de la orden',
  id_solicitud    CHAR(36)        NOT NULL COMMENT 'Solicitud aprobada',
  id_cliente      CHAR(36)        NOT NULL COMMENT 'Cliente beneficiario',
  num_cuenta      VARCHAR(20)     NOT NULL COMMENT 'Cuenta destino del desembolso',
  id_agencia      CHAR(36)        NULL COMMENT 'Agencia donde se ejecuta',
  monto           DECIMAL(15,2)   NOT NULL COMMENT 'Monto del desembolso',
  moneda          CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda',
  tipo_desembolso ENUM('EFECTIVO','ABONO_CUENTA','CHEQUE','TRANSFERENCIA') NOT NULL COMMENT 'Forma de entrega',
  estado_orden    ENUM('GENERADA','EN_VALIDACION','AUTORIZADA','ENTREGADA','RECHAZADA','REVERTIDA')
                  NOT NULL DEFAULT 'GENERADA' COMMENT 'Estado de la orden',
  id_autorizador  CHAR(36)        NULL COMMENT 'Empleado que autoriza',
  fecha_generacion DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de generacion',
  fecha_entrega   DATETIME(3)     NULL COMMENT 'Fecha de entrega',
  PRIMARY KEY (id_orden),
  KEY idx_orden_solicitud (id_solicitud, estado_orden),
  CONSTRAINT fk_orden_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT fk_orden_cliente   FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente),
  CONSTRAINT fk_orden_cuenta    FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT fk_orden_agencia   FOREIGN KEY (id_agencia) REFERENCES agencia (id_agencia),
  CONSTRAINT fk_orden_autoriz   FOREIGN KEY (id_autorizador) REFERENCES empleado (id_empleado),
  CONSTRAINT ck_orden_monto CHECK (monto > 0)
) ENGINE=InnoDB COMMENT='Ordenes de desembolso';

-- ---------------------------------------------------------------------
-- des_validacion: validaciones previas al desembolso
-- ---------------------------------------------------------------------
CREATE TABLE des_validacion (
  id_validacion   CHAR(36)        NOT NULL COMMENT 'Identificador de la validacion',
  id_orden        CHAR(36)        NOT NULL COMMENT 'Orden validada',
  tipo_validacion ENUM('FIRMA','DOCUMENTOS','CUENTA_ACTIVA','BIOMETRIA','CONTRATO') NOT NULL
                  COMMENT 'Tipo de validacion',
  resultado       ENUM('APROBADO','RECHAZADO','OBSERVADO') NOT NULL COMMENT 'Resultado',
  id_validador    CHAR(36)        NULL COMMENT 'Empleado validador',
  detalle         VARCHAR(200)    NULL COMMENT 'Detalle',
  fecha_validacion DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de validacion',
  PRIMARY KEY (id_validacion),
  KEY idx_desval_orden (id_orden, tipo_validacion),
  CONSTRAINT fk_desval_orden   FOREIGN KEY (id_orden) REFERENCES des_orden (id_orden),
  CONSTRAINT fk_desval_validador FOREIGN KEY (id_validador) REFERENCES empleado (id_empleado)
) ENGINE=InnoDB COMMENT='Validaciones previas al desembolso';

-- ---------------------------------------------------------------------
-- des_evento_entrega: bitacora de la entrega del dinero
-- ---------------------------------------------------------------------
CREATE TABLE des_evento_entrega (
  id_evento       CHAR(36)        NOT NULL COMMENT 'Identificador del evento',
  id_orden        CHAR(36)        NOT NULL COMMENT 'Orden entregada',
  tipo_evento     ENUM('INICIO','ENTREGA','REVERSION','FALLO') NOT NULL COMMENT 'Tipo de evento',
  num_operacion_core VARCHAR(30)  NULL COMMENT 'Numero de operacion en el core',
  id_terminal     CHAR(36)        NULL COMMENT 'Terminal usada',
  detalle         VARCHAR(200)    NULL COMMENT 'Detalle del evento',
  fecha_evento    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha del evento',
  PRIMARY KEY (id_evento),
  KEY idx_desevento_orden (id_orden, fecha_evento),
  CONSTRAINT fk_desevento_orden    FOREIGN KEY (id_orden) REFERENCES des_orden (id_orden),
  CONSTRAINT fk_desevento_terminal FOREIGN KEY (id_terminal) REFERENCES terminal (id_terminal)
) ENGINE=InnoDB COMMENT='Eventos de entrega del desembolso';

-- ---------------------------------------------------------------------
-- des_auditoria: auditoria de acciones sobre la orden
-- ---------------------------------------------------------------------
CREATE TABLE des_auditoria (
  id_auditoria    CHAR(36)        NOT NULL COMMENT 'Identificador de la auditoria',
  id_orden        CHAR(36)        NOT NULL COMMENT 'Orden auditada',
  id_usuario      CHAR(36)        NULL COMMENT 'Usuario actor',
  accion          VARCHAR(40)     NOT NULL COMMENT 'Accion realizada',
  estado_anterior VARCHAR(20)     NULL COMMENT 'Estado anterior',
  estado_nuevo    VARCHAR(20)     NULL COMMENT 'Estado nuevo',
  detalle         VARCHAR(200)    NULL COMMENT 'Detalle, sin datos sensibles',
  correlation_id  CHAR(36)        NULL COMMENT 'Correlacion del Bus',
  fecha_hora      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora',
  PRIMARY KEY (id_auditoria),
  KEY idx_desaud_orden (id_orden, fecha_hora),
  CONSTRAINT fk_desaud_orden   FOREIGN KEY (id_orden) REFERENCES des_orden (id_orden),
  CONSTRAINT fk_desaud_usuario FOREIGN KEY (id_usuario) REFERENCES usuario_sistema (id_usuario)
) ENGINE=InnoDB COMMENT='Auditoria del modulo desembolso';

-- ---------------------------------------------------------------------
-- des_solicitud_reversion: solicitudes de reversion (mejora: autorizador
-- distinto y transaccion de reposicion)
-- ---------------------------------------------------------------------
CREATE TABLE des_solicitud_reversion (
  id_reversion    CHAR(36)        NOT NULL COMMENT 'Identificador de la reversion',
  id_orden        CHAR(36)        NOT NULL COMMENT 'Orden a revertir',
  id_solicitante  CHAR(36)        NOT NULL COMMENT 'Usuario que solicita la reversion',
  id_autorizador  CHAR(36)        NULL COMMENT 'Usuario que autoriza (distinto del solicitante)',
  motivo          VARCHAR(200)    NOT NULL COMMENT 'Motivo de la reversion',
  estado          ENUM('SOLICITADA','AUTORIZADA','RECHAZADA','APLICADA') NOT NULL DEFAULT 'SOLICITADA'
                  COMMENT 'Estado de la reversion',
  num_transaccion_reposicion VARCHAR(36) NULL COMMENT 'Transaccion de reposicion generada',
  fecha_solicitud DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de solicitud',
  fecha_autorizacion DATETIME(3)  NULL COMMENT 'Fecha de autorizacion',
  PRIMARY KEY (id_reversion),
  KEY idx_rev_orden (id_orden),
  CONSTRAINT fk_rev_orden        FOREIGN KEY (id_orden) REFERENCES des_orden (id_orden),
  CONSTRAINT fk_rev_solicitante  FOREIGN KEY (id_solicitante) REFERENCES usuario_sistema (id_usuario),
  CONSTRAINT fk_rev_autorizador  FOREIGN KEY (id_autorizador) REFERENCES usuario_sistema (id_usuario),
  CONSTRAINT ck_rev_autorizador_distinto CHECK (id_autorizador IS NULL OR id_autorizador <> id_solicitante)
) ENGINE=InnoDB COMMENT='Solicitudes de reversion de desembolso';

-- <<< FIN 08_desembolso.sql

-- >>> INICIO 09_cobranza.sql
-- =====================================================================
-- BNA - Script 09: Modulo Cobranza
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Basado en el diccionario de Cobranza: CREDITO, CUOTA, PAGO, CANAL_PAGO,
--   APLICACION_PAGO, MORA, EVENTO_AUDITORIA. Mejora: la aplicacion del
--   pago separa capital/interes/seguro/mora y la mora se controla con
--   columna generada + UNIQUE para tener una sola vigente por cuota.
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- canal_pago: catalogo de canales de pago
-- ---------------------------------------------------------------------
CREATE TABLE canal_pago (
  id_canal_pago CHAR(36)        NOT NULL COMMENT 'Identificador del canal de pago',
  nombre        VARCHAR(40)     NOT NULL COMMENT 'Nombre del canal de pago',
  tipo          ENUM('VENTANILLA','AGENTE','ATM','BANCA_WEB','APP','DOMICILIACION','TRANSFERENCIA')
                NOT NULL COMMENT 'Tipo de canal',
  activo        TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 si esta operativo',
  PRIMARY KEY (id_canal_pago),
  UNIQUE KEY uk_canal_pago_nombre (nombre)
) ENGINE=InnoDB COMMENT='Catalogo de canales de pago';

-- ---------------------------------------------------------------------
-- cob_credito: credito desembolsado en fase de cobranza
-- ---------------------------------------------------------------------
CREATE TABLE cob_credito (
  id_credito      CHAR(36)        NOT NULL COMMENT 'Identificador del credito',
  id_solicitud    CHAR(36)        NOT NULL COMMENT 'Solicitud origen',
  id_cliente      CHAR(36)        NOT NULL COMMENT 'Cliente deudor',
  num_cuenta_desembolso VARCHAR(20) NOT NULL COMMENT 'Cuenta de desembolso',
  monto_aprobado  DECIMAL(15,2)   NOT NULL COMMENT 'Monto aprobado',
  moneda          CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda',
  tasa_tea        DECIMAL(6,4)    NOT NULL COMMENT 'Tasa efectiva anual',
  plazo_meses     INT             NOT NULL COMMENT 'Plazo en meses',
  saldo_capital   DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Saldo de capital pendiente',
  estado_credito  ENUM('VIGENTE','VENCIDO','JUDICIAL','CASTIGADO','CANCELADO') NOT NULL DEFAULT 'VIGENTE'
                  COMMENT 'Estado del credito',
  dias_mora       INT             NOT NULL DEFAULT 0 COMMENT 'Dias de mora acumulados',
  fecha_desembolso DATE           NOT NULL COMMENT 'Fecha de desembolso',
  PRIMARY KEY (id_credito),
  KEY idx_credito_cliente (id_cliente, estado_credito),
  CONSTRAINT fk_credito_solicitud FOREIGN KEY (id_solicitud) REFERENCES sol_solicitud (id_solicitud),
  CONSTRAINT fk_credito_cliente   FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente),
  CONSTRAINT fk_credito_cuenta    FOREIGN KEY (num_cuenta_desembolso) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT fk_credito_moneda    FOREIGN KEY (moneda) REFERENCES moneda (cod_moneda),
  CONSTRAINT ck_credito_monto CHECK (monto_aprobado > 0 AND dias_mora >= 0)
) ENGINE=InnoDB COMMENT='Creditos en cobranza';

-- ---------------------------------------------------------------------
-- cob_cuota: cuotas del credito (cartera vigente)
-- ---------------------------------------------------------------------
CREATE TABLE cob_cuota (
  id_cuota_credito CHAR(36)        NOT NULL COMMENT 'Identificador de la cuota',
  id_credito      CHAR(36)        NOT NULL COMMENT 'Credito',
  numero_cuota    INT             NOT NULL COMMENT 'Numero de cuota',
  fecha_vencimiento DATE          NOT NULL COMMENT 'Fecha de vencimiento',
  capital         DECIMAL(15,2)   NOT NULL COMMENT 'Capital de la cuota',
  interes         DECIMAL(15,2)   NOT NULL COMMENT 'Interes de la cuota',
  seguro          DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Seguro desgravamen',
  cuota_total     DECIMAL(15,2)   NOT NULL COMMENT 'Total de la cuota',
  saldo_capital   DECIMAL(15,2)   NOT NULL COMMENT 'Saldo de capital luego de pagar',
  monto_pagado    DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Monto efectivamente pagado',
  estado_cuota    ENUM('PENDIENTE','PARCIAL','PAGADA','VENCIDA','CASTIGADA') NOT NULL DEFAULT 'PENDIENTE'
                  COMMENT 'Estado de la cuota',
  PRIMARY KEY (id_cuota_credito),
  UNIQUE KEY uk_cuota_credito_num (id_credito, numero_cuota),
  CONSTRAINT fk_cuota_credito FOREIGN KEY (id_credito) REFERENCES cob_credito (id_credito),
  CONSTRAINT ck_cuota_pagado CHECK (monto_pagado >= 0)
) ENGINE=InnoDB COMMENT='Cuotas del credito en cobranza';

-- ---------------------------------------------------------------------
-- cob_pago: pago recibido
-- ---------------------------------------------------------------------
CREATE TABLE cob_pago (
  id_pago         CHAR(36)        NOT NULL COMMENT 'Identificador del pago',
  id_credito      CHAR(36)        NOT NULL COMMENT 'Credito pagado',
  id_canal_pago   CHAR(36)        NOT NULL COMMENT 'Canal de pago',
  num_cuenta      VARCHAR(20)     NULL COMMENT 'Cuenta usada para el pago, si aplica',
  monto           DECIMAL(15,2)   NOT NULL COMMENT 'Monto pagado',
  moneda          CHAR(3)         NOT NULL DEFAULT 'PEN' COMMENT 'Moneda',
  num_operacion   VARCHAR(30)     NOT NULL COMMENT 'Numero de operacion/recibo',
  id_cobrador     CHAR(36)        NULL COMMENT 'Empleado o cobrador que registra',
  estado_pago     ENUM('REGISTRADO','APLICADO','RECHAZADO','REVERSADO') NOT NULL DEFAULT 'REGISTRADO'
                  COMMENT 'Estado del pago',
  fecha_pago      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha del pago',
  PRIMARY KEY (id_pago),
  UNIQUE KEY uk_pago_operacion (num_operacion),
  KEY idx_pago_credito (id_credito, fecha_pago),
  CONSTRAINT fk_pago_credito  FOREIGN KEY (id_credito) REFERENCES cob_credito (id_credito),
  CONSTRAINT fk_pago_canal    FOREIGN KEY (id_canal_pago) REFERENCES canal_pago (id_canal_pago),
  CONSTRAINT fk_pago_cuenta   FOREIGN KEY (num_cuenta) REFERENCES cuenta_ahorro (num_cuenta),
  CONSTRAINT fk_pago_cobrador FOREIGN KEY (id_cobrador) REFERENCES empleado (id_empleado),
  CONSTRAINT ck_pago_monto CHECK (monto > 0)
) ENGINE=InnoDB COMMENT='Pagos recibidos';

-- ---------------------------------------------------------------------
-- cob_aplicacion_pago: distribucion del pago por componente
-- ---------------------------------------------------------------------
CREATE TABLE cob_aplicacion_pago (
  id_aplicacion   CHAR(36)        NOT NULL COMMENT 'Identificador de la aplicacion',
  id_pago         CHAR(36)        NOT NULL COMMENT 'Pago aplicado',
  id_cuota_credito CHAR(36)        NOT NULL COMMENT 'Cuota afectada',
  aplica_capital  DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Aplicado a capital',
  aplica_interes  DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Aplicado a interes',
  aplica_seguro   DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Aplicado a seguro',
  aplica_mora     DECIMAL(15,2)   NOT NULL DEFAULT 0 COMMENT 'Aplicado a mora',
  fecha_aplicacion DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de aplicacion',
  PRIMARY KEY (id_aplicacion),
  KEY idx_aplic_pago (id_pago),
  CONSTRAINT fk_aplic_pago   FOREIGN KEY (id_pago) REFERENCES cob_pago (id_pago),
  CONSTRAINT fk_aplic_cuota  FOREIGN KEY (id_cuota_credito) REFERENCES cob_cuota (id_cuota_credito),
  CONSTRAINT ck_aplic_montos CHECK (aplica_capital >= 0 AND aplica_interes >= 0 AND aplica_seguro >= 0 AND aplica_mora >= 0)
) ENGINE=InnoDB COMMENT='Aplicacion del pago por componente';

-- ---------------------------------------------------------------------
-- cob_mora: mora generada por cuota (una sola vigente por cuota)
-- ---------------------------------------------------------------------
CREATE TABLE cob_mora (
  id_mora         CHAR(36)        NOT NULL COMMENT 'Identificador de la mora',
  id_cuota_credito CHAR(36)        NOT NULL COMMENT 'Cuota en mora',
  dias_atraso     INT             NOT NULL COMMENT 'Dias de atraso',
  tasa_mora       DECIMAL(6,4)    NOT NULL COMMENT 'Tasa de mora aplicada',
  interes_mora    DECIMAL(15,2)   NOT NULL COMMENT 'Interes moratorio calculado',
  estado_mora     ENUM('PENDIENTE','VIGENTE','PAGADA','CONDONADA') NOT NULL DEFAULT 'PENDIENTE'
                  COMMENT 'Estado de la mora',
  vigente_flag    TINYINT GENERATED ALWAYS AS
                  (CASE WHEN estado_mora IN ('PENDIENTE','VIGENTE') THEN 1 ELSE NULL END) STORED
                  COMMENT 'Columna generada para garantizar una mora vigente por cuota',
  fecha_calculo   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha de calculo',
  PRIMARY KEY (id_mora),
  UNIQUE KEY uk_mora_cuota_vigente (id_cuota_credito, vigente_flag),
  CONSTRAINT fk_mora_cuota FOREIGN KEY (id_cuota_credito) REFERENCES cob_cuota (id_cuota_credito),
  CONSTRAINT ck_mora_dias CHECK (dias_atraso >= 0)
) ENGINE=InnoDB COMMENT='Mora de las cuotas';

-- ---------------------------------------------------------------------
-- cob_evento_auditoria: eventos de cobranza y auditoria
-- ---------------------------------------------------------------------
CREATE TABLE cob_evento_auditoria (
  id_evento       CHAR(36)        NOT NULL COMMENT 'Identificador del evento',
  id_credito      CHAR(36)        NOT NULL COMMENT 'Credito afectado',
  tipo_evento     ENUM('PAGO','MORA','GESTION','CAMBIO_ESTADO','CASTIGO','CONDONACION') NOT NULL
                  COMMENT 'Tipo de evento',
  descripcion     VARCHAR(200)    NOT NULL COMMENT 'Descripcion del evento',
  id_usuario      CHAR(36)        NULL COMMENT 'Usuario actor',
  canal           VARCHAR(20)     NULL COMMENT 'Canal o medio de gestion',
  correlation_id  CHAR(36)        NULL COMMENT 'Correlacion del Bus',
  fecha_hora      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Fecha y hora',
  PRIMARY KEY (id_evento),
  KEY idx_cobevento_credito (id_credito, fecha_hora),
  CONSTRAINT fk_cobevento_credito FOREIGN KEY (id_credito) REFERENCES cob_credito (id_credito),
  CONSTRAINT fk_cobevento_usuario FOREIGN KEY (id_usuario) REFERENCES usuario_sistema (id_usuario)
) ENGINE=InnoDB COMMENT='Eventos de auditoria de cobranza';

-- <<< FIN 09_cobranza.sql

-- >>> INICIO 10_seed_catalogos.sql
-- =====================================================================
-- BNA - Script 10: Carga de catalogos (seed)
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- IDs: UUID v7 (CHAR(36)) fijos, para que la carga siga siendo idempotente.
-- Uso: idempotente (INSERT IGNORE / ON DUPLICATE KEY UPDATE).
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- Agencias (4 iniciales en Arequipa)
INSERT IGNORE INTO agencia (id_agencia, nombre, direccion, activa) VALUES
 ('0198b000-0000-7001-8000-000000000001','Agencia Arequipa Centro','Calle Mercaderes 120, Arequipa',1),
 ('0198b000-0000-7001-8000-000000000002','Agencia Cayma','Av. Ejercito 505, Cayma, Arequipa',1),
 ('0198b000-0000-7001-8000-000000000003','Agencia Yanahuara','Av. Bolognesi 210, Yanahuara, Arequipa',1),
 ('0198b000-0000-7001-8000-000000000004','Agencia Paucarpata','Av. Goyeneche 850, Paucarpata, Arequipa',1);

-- Tipos de documento
INSERT IGNORE INTO tipo_documento (cod_tipo_documento, descripcion) VALUES
 ('DNI','Documento Nacional de Identidad'),
 ('CE','Carnet de Extranjeria'),
 ('PASAPORTE','Pasaporte'),
 ('PTP','Permiso Temporal de Permanencia'),
 ('RUC','Registro Unico de Contribuyentes');

-- Monedas
INSERT IGNORE INTO moneda (cod_moneda, nombre, simbolo, activa) VALUES
 ('PEN','Sol Peruano','S/',1),
 ('USD','Dolar Estadounidense','$',1);

-- Tipo de cambio de ejemplo
INSERT IGNORE INTO tipo_cambio (id_tipo_cambio, cod_moneda_origen, cod_moneda_destino, fecha, tasa) VALUES
 ('0198b000-0000-7011-8000-000000000001','USD','PEN','2026-10-15',3.750000),
 ('0198b000-0000-7011-8000-000000000002','PEN','USD','2026-10-15',0.266667);

-- Canales de atencion
INSERT IGNORE INTO canal (id_canal, nombre, es_presencial, validacion_requerida, requiere_token_matriz, tipo_integracion, activo) VALUES
 ('ATM','Cajero Automatico',1,'PIN_ATM',0,'BUS_SERVICIOS',1),
 ('AGE','Agente / Ventanilla',1,'PIN_ATM',0,'BUS_SERVICIOS',1),
 ('VEN','Ventanilla',1,'PIN_ATM',0,'BUS_SERVICIOS',1),
 ('HB','Home Banking',0,'CLAVE_WEB',0,'API_REST',1),
 ('BD','Banca por Dispositivo',0,'TOKEN_PAGO',1,'API_REST',1);

-- Topes por canal y moneda (NULL = sin limite)
INSERT IGNORE INTO limite_canal (id_canal, moneda, monto_maximo_diario, habilitado, regla_negocio) VALUES
 ('ATM','PEN',700.00,1,'TOPE_ATM_PEN'),
 ('AGE','PEN',5000.00,1,'TOPE_AGENTE_PEN'),
 ('VEN','PEN',NULL,1,'TOPE_VENTANILLA_PEN'),
 ('HB','PEN',2000.00,1,'TOPE_HB_PEN'),
 ('BD','USD',1500.00,1,'TOPE_BANCADIGITAL_USD');

-- Productos de ahorro
INSERT IGNORE INTO producto_ahorro (id_producto_ahorro, nombre, moneda, tasa_tea, activo) VALUES
 ('0198b000-0000-7004-8000-000000000001','Ahorro Libre',          'PEN',0.0100,1),
 ('0198b000-0000-7004-8000-000000000002','Ahorro Programado',     'PEN',0.0350,1),
 ('0198b000-0000-7004-8000-000000000003','Ahorro Infantil',       'PEN',0.0150,1),
 ('0198b000-0000-7004-8000-000000000004','Ahorro CTS',            'PEN',0.0400,1),
 ('0198b000-0000-7004-8000-000000000005','Ahorro a Plazo Fijo',   'PEN',0.0550,1),
 ('0198b000-0000-7004-8000-000000000006','Ahorro Libre Dolares',  'USD',0.0050,1);

-- Productos de credito
INSERT IGNORE INTO producto_credito (id_producto_credito, nombre, tasa_tea, plazo_min_meses, plazo_max_meses, activo) VALUES
 ('0198b000-0000-7005-8000-000000000001','Credito Personal',        0.2200,6,60,1),
 ('0198b000-0000-7005-8000-000000000002','Credito Microempresa',    0.2800,6,48,1),
 ('0198b000-0000-7005-8000-000000000003','Credito Hipotecario',     0.1050,60,300,1),
 ('0198b000-0000-7005-8000-000000000004','Credito Vehicular',       0.1500,12,72,1);

-- Periodos contables 2026
INSERT IGNORE INTO periodo_contable (id_periodo, anio, mes, fecha_inicio, fecha_fin, estado) VALUES
 ('0198b000-0000-7010-8000-000000000001',2026,1,'2026-01-01','2026-01-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000002',2026,2,'2026-02-01','2026-02-28','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000003',2026,3,'2026-03-01','2026-03-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000004',2026,4,'2026-04-01','2026-04-30','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000005',2026,5,'2026-05-01','2026-05-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000006',2026,6,'2026-06-01','2026-06-30','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000007',2026,7,'2026-07-01','2026-07-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000008',2026,8,'2026-08-01','2026-08-31','ABIERTO'),
 ('0198b000-0000-7010-8000-000000000009',2026,9,'2026-09-01','2026-09-30','ABIERTO'),
 ('0198b000-0000-7010-8000-00000000000a',2026,10,'2026-10-01','2026-10-31','ABIERTO'),
 ('0198b000-0000-7010-8000-00000000000b',2026,11,'2026-11-01','2026-11-30','ABIERTO'),
 ('0198b000-0000-7010-8000-00000000000c',2026,12,'2026-12-01','2026-12-31','ABIERTO');

-- Plan de cuentas contables (extracto)
INSERT IGNORE INTO plan_cuenta_contable (cod_cuenta_contable, nombre, naturaleza, codigo_padre, activo) VALUES
 ('1','ACTIVO','DEUDORA',NULL,1),
 ('2','PASIVO','ACREEDORA',NULL,1),
 ('3','PATRIMONIO','ACREEDORA',NULL,1),
 ('4','INGRESOS','ACREEDORA',NULL,1),
 ('5','GASTOS','DEUDORA',NULL,1),
 ('1101','Caja','DEUDORA','1',1),
 ('1102','Fondos en Banco Central','DEUDORA','1',1),
 ('1103','Cuentas por Cobrar','DEUDORA','1',1),
 ('2101','Depositos de Ahorro','ACREEDORA','2',1),
 ('2102','Depositos a Plazo','ACREEDORA','2',1),
 ('2103','Obligaciones con el Publico','ACREEDORA','2',1),
 ('4101','Ingresos por Intereses','ACREEDORA','4',1),
 ('4102','Ingresos por Comisiones','ACREEDORA','4',1),
 ('4103','Ingresos por Mora','ACREEDORA','4',1),
 ('5101','Gastos por Intereses','DEUDORA','5',1),
 ('5102','Gastos Operativos','DEUDORA','5',1),
 ('5103','Provision Custodia','DEUDORA','5',1);

-- Reglas de evaluacion (tramos del informe)
INSERT IGNORE INTO eva_regla (id_regla, nombre, descripcion, variable, operador, valor_min, valor_max, resultado, peso, activa) VALUES
 ('0198b000-0000-7007-8000-000000000001','RATIO_SALUDABLE','Ratio cuota/ingreso hasta 80%','ratio_capacidad','ENTRE',0,0.80,'APROBAR',1.00,1),
 ('0198b000-0000-7007-8000-000000000002','RATIO_LIMITE','Ratio cuota/ingreso hasta 100%','ratio_capacidad','ENTRE',0.80,1.00,'OBSERVAR',1.00,1),
 ('0198b000-0000-7007-8000-000000000003','RATIO_INSUFICIENTE','Ratio cuota/ingreso mayor a 100%','ratio_capacidad','MAYOR',1.00,NULL,'RECHAZAR',1.00,1),
 ('0198b000-0000-7007-8000-000000000004','MORA_RECIENTE','Dias de mayor mora en central','dias_mayor_mora','MAYOR',30,NULL,'OBSERVAR',0.50,1),
 ('0198b000-0000-7007-8000-000000000005','MORA_GRAVE','Dias de mayor mora mayor a 120','dias_mayor_mora','MAYOR',120,NULL,'RECHAZAR',1.00,1);

-- Canales de pago
INSERT IGNORE INTO canal_pago (id_canal_pago, nombre, tipo, activo) VALUES
 ('0198b000-0000-7008-8000-000000000001','Ventanilla Agencia','VENTANILLA',1),
 ('0198b000-0000-7008-8000-000000000002','Agente BNA','AGENTE',1),
 ('0198b000-0000-7008-8000-000000000003','Cajero Automatico','ATM',1),
 ('0198b000-0000-7008-8000-000000000004','Banca por Internet','BANCA_WEB',1),
 ('0198b000-0000-7008-8000-000000000005','App Movil','APP',1),
 ('0198b000-0000-7008-8000-000000000006','Domiciliacion','DOMICILIACION',1),
 ('0198b000-0000-7008-8000-000000000007','Transferencia Interbancaria','TRANSFERENCIA',1);

-- Empleados de ejemplo
INSERT IGNORE INTO empleado (id_empleado, codigo_empleado, nombre_completo, cargo, id_agencia, activo) VALUES
 ('0198b000-0000-7002-8000-000000000001','BNA-0001','Asesor Demo Arequipa','ASESOR_CREDITOS','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7002-8000-000000000002','BNA-0002','Analista Demo Arequipa','ANALISTA_CREDITO','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7002-8000-000000000003','BNA-0003','Operador Demo Arequipa','OPERADOR','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7002-8000-000000000004','BNA-0004','Cajero Demo Arequipa','CAJERO','0198b000-0000-7001-8000-000000000001',1);

-- Usuarios del sistema de ejemplo
INSERT IGNORE INTO usuario_sistema (id_usuario, username, nombre, rol, hash_password, id_empleado, activo) VALUES
 ('0198b000-0000-7003-8000-000000000001','admin.bna','Administrador BNA','ADMINISTRADOR',SHA2('admin123',256),'0198b000-0000-7002-8000-000000000001',1),
 ('0198b000-0000-7003-8000-000000000002','asesor.bna','Asesor Demo','ASESOR',SHA2('asesor123',256),'0198b000-0000-7002-8000-000000000001',1),
 ('0198b000-0000-7003-8000-000000000003','analista.bna','Analista Demo','ANALISTA',SHA2('analista123',256),'0198b000-0000-7002-8000-000000000002',1),
 ('0198b000-0000-7003-8000-000000000004','operador.bna','Operador Demo','OPERADOR',SHA2('operador123',256),'0198b000-0000-7002-8000-000000000003',1),
 ('0198b000-0000-7003-8000-000000000005','auditor.bna','Auditor Demo','AUDITOR',SHA2('auditor123',256),NULL,1);

-- Terminales de ejemplo
INSERT IGNORE INTO terminal (id_terminal, codigo, tipo, ubicacion, id_agencia, activa) VALUES
 ('0198b000-0000-7006-8000-000000000001','ATM-ARQ-001','ATM','Agencia Arequipa Centro','0198b000-0000-7001-8000-000000000001',1),
 ('0198b000-0000-7006-8000-000000000002','ATM-ARQ-002','ATM','Agencia Cayma','0198b000-0000-7001-8000-000000000002',1),
 ('0198b000-0000-7006-8000-000000000003','POS-ARQ-001','POS','Agencia Yanahuara','0198b000-0000-7001-8000-000000000003',1),
 ('0198b000-0000-7006-8000-000000000004','WEB-BNA-001','WEB','Plataforma web',NULL,1),
 ('0198b000-0000-7006-8000-000000000005','MOV-BNA-001','MOVIL','Aplicacion movil',NULL,1);

-- <<< FIN 10_seed_catalogos.sql

-- >>> INICIO 11_vistas.sql
-- =====================================================================
-- BNA - Script 11: Vistas
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- v_tarjeta_resumen: resumen de tarjetas con cliente y cuentas
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_tarjeta_resumen AS
SELECT t.id_tarjeta,
       t.ultimos4,
       t.tipo_tarjeta,
       t.estado,
       t.fecha_vencimiento,
       c.id_cliente,
       CONCAT_WS(' ', c.nombres, c.apellido_paterno, c.apellido_materno) AS cliente,
       COUNT(tc.num_cuenta) AS cuentas_asociadas
FROM tar_tarjeta t
JOIN cliente c ON c.id_cliente = t.id_cliente
LEFT JOIN tar_tarjeta_cuenta tc ON tc.id_tarjeta = t.id_tarjeta
GROUP BY t.id_tarjeta, t.ultimos4, t.tipo_tarjeta, t.estado, t.fecha_vencimiento,
         c.id_cliente, c.nombres, c.apellido_paterno, c.apellido_materno;

-- ---------------------------------------------------------------------
-- v_consumo_diario: monto aprobado por tarjeta y dia
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_consumo_diario AS
SELECT a.id_tarjeta,
       DATE(a.fecha_hora) AS fecha,
       a.id_canal,
       SUM(a.monto)       AS monto_consumido
FROM tar_autorizacion a
WHERE a.estado = 'APROBADA'
GROUP BY a.id_tarjeta, DATE(a.fecha_hora), a.id_canal;

-- ---------------------------------------------------------------------
-- v_tope_restante_hoy: tope restante por canal segun consumo del dia
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_tope_restante_hoy AS
SELECT lc.id_canal,
       lc.moneda,
       lc.monto_maximo_diario,
       COALESCE(cd.monto_consumido, 0) AS consumido_hoy,
       CASE
         WHEN lc.monto_maximo_diario IS NULL THEN NULL
         ELSE GREATEST(lc.monto_maximo_diario - COALESCE(cd.monto_consumido, 0), 0)
       END AS tope_restante
FROM limite_canal lc
LEFT JOIN (
   SELECT a.id_canal, SUM(a.monto) AS monto_consumido
   FROM tar_autorizacion a
   WHERE a.estado = 'APROBADA' AND DATE(a.fecha_hora) = CURRENT_DATE()
   GROUP BY a.id_canal
) cd ON cd.id_canal = lc.id_canal
WHERE lc.habilitado = 1;

-- ---------------------------------------------------------------------
-- v_credenciales_en_riesgo: credenciales bloqueadas o con reintentos
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_credenciales_en_riesgo AS
SELECT cr.id_credencial,
       cr.id_tarjeta,
       cr.tipo,
       cr.intentos_fallidos,
       cr.bloqueada,
       cr.fecha_ultimo_cambio
FROM tar_credencial cr
WHERE cr.bloqueada = 1 OR cr.intentos_fallidos >= 2;

-- ---------------------------------------------------------------------
-- des_v_ordenes_inciertas: ordenes sin entrega ni reversion
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW des_v_ordenes_inciertas AS
SELECT o.id_orden,
       o.id_solicitud,
       o.monto,
       o.moneda,
       o.estado_orden,
       o.fecha_generacion
FROM des_orden o
LEFT JOIN des_evento_entrega e
       ON e.id_orden = o.id_orden AND e.tipo_evento IN ('ENTREGA','REVERSION')
WHERE e.id_evento IS NULL
  AND o.estado_orden IN ('GENERADA','EN_VALIDACION','AUTORIZADA');

-- ---------------------------------------------------------------------
-- des_v_entregas_pendientes: ordenes autorizadas por entregar
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW des_v_entregas_pendientes AS
SELECT o.id_orden,
       o.id_solicitud,
       o.id_cliente,
       o.num_cuenta,
       o.monto,
       o.moneda,
       o.tipo_desembolso,
       o.fecha_generacion
FROM des_orden o
WHERE o.estado_orden = 'AUTORIZADA';

-- ---------------------------------------------------------------------
-- des_v_conciliacion_diaria: desembolsos entregados por dia
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW des_v_conciliacion_diaria AS
SELECT DATE(o.fecha_entrega) AS fecha,
       o.moneda,
       COUNT(*)              AS cantidad_ordenes,
       SUM(o.monto)          AS monto_total
FROM des_orden o
WHERE o.estado_orden = 'ENTREGADA'
GROUP BY DATE(o.fecha_entrega), o.moneda;

-- ---------------------------------------------------------------------
-- v_credito_resumen: resumen de credito con cliente y saldo
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_credito_resumen AS
SELECT cr.id_credito,
       cr.estado_credito,
       cr.moneda,
       cr.monto_aprobado,
       cr.saldo_capital,
       cr.dias_mora,
       CONCAT_WS(' ', c.nombres, c.apellido_paterno, c.apellido_materno) AS cliente,
       (SELECT COUNT(*) FROM cob_cuota q WHERE q.id_credito = cr.id_credito) AS total_cuotas,
       (SELECT COUNT(*) FROM cob_cuota q WHERE q.id_credito = cr.id_credito AND q.estado_cuota = 'PAGADA') AS cuotas_pagadas
FROM cob_credito cr
JOIN cliente c ON c.id_cliente = cr.id_cliente;

-- ---------------------------------------------------------------------
-- v_movimientos_cuenta: movimientos de cuenta con saldo
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_movimientos_cuenta AS
SELECT t.id_transaccion,
       t.uuid_transaccion,
       t.num_cuenta,
       t.tipo_operacion,
       t.tipo_movimiento,
       t.monto,
       t.moneda,
       t.saldo_posterior,
       t.comision,
       t.itf,
       t.estado_transaccion,
       t.fecha_valor,
       t.fecha_hora,
       cn.nombre AS canal
FROM cta_transaccion t
LEFT JOIN canal cn ON cn.id_canal = t.id_canal;

-- <<< FIN 11_vistas.sql

-- >>> INICIO 12_triggers_eventos.sql
-- =====================================================================
-- BNA - Script 12: Triggers, Evento y Procedimientos
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Mejoras: bloqueo al 3.er intento fallido, historial de estado inmutable,
--   control de topes diarios, vencimiento automatico de tarjetas y
--   aplicacion de pagos por componente.
-- IDs: UUID v7 (CHAR(36)). La aplicacion genera los v7; para las filas que
--   genera la propia base se usa la funcion fn_uuid_v7().
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

DELIMITER $$

-- ---------------------------------------------------------------------
-- fn_uuid_v7: genera un UUID version 7 (time-ordered) en MySQL 8.0/8.4.
-- 48 bits de timestamp en milisegundos + 4 bits de version (7) + 2 bits de
-- variante + 74 bits aleatorios. Se usa solo para filas creadas por la base
-- (triggers/procedimientos); la aplicacion genera sus propios v7.
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_uuid_v7 $$
CREATE FUNCTION fn_uuid_v7()
RETURNS CHAR(36)
NO SQL
BEGIN
  DECLARE v_ms    CHAR(12);
  DECLARE v_rand  CHAR(32);
  DECLARE v_hex   CHAR(32);

  SET v_ms = LPAD(HEX(
               FLOOR(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3)) * 1000)
               + FLOOR(MICROSECOND(CURRENT_TIMESTAMP(3)) / 1000)), 12, '0');
  SET v_rand = LPAD(HEX(RANDOM_BYTES(16)), 32, '0');
  SET v_hex = CONCAT(
                LEFT(v_ms, 12),
                '7',
                SUBSTRING(v_rand, 1, 3),
                SUBSTRING('89ab', 1 + FLOOR(RAND() * 4), 1),
                SUBSTRING(v_rand, 5, 15));

  RETURN CONCAT(LEFT(v_hex, 8), '-', SUBSTRING(v_hex, 9, 4), '-',
                SUBSTRING(v_hex, 13, 4), '-', SUBSTRING(v_hex, 17, 4), '-',
                RIGHT(v_hex, 12));
END $$

-- ---------------------------------------------------------------------
-- Historial inicial al crear la tarjeta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_tarjeta_hist_ins $$
CREATE TRIGGER trg_tarjeta_hist_ins
AFTER INSERT ON tar_tarjeta
FOR EACH ROW
BEGIN
  INSERT INTO tar_historial_estado (id_historial, id_tarjeta, estado_anterior, estado_nuevo, motivo, origen)
  VALUES (fn_uuid_v7(), NEW.id_tarjeta, NEW.estado, NEW.estado, 'Alta de tarjeta', 'SISTEMA');
END $$

-- ---------------------------------------------------------------------
-- Historial al cambiar el estado de la tarjeta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_tarjeta_hist_upd $$
CREATE TRIGGER trg_tarjeta_hist_upd
AFTER UPDATE ON tar_tarjeta
FOR EACH ROW
BEGIN
  IF NEW.estado <> OLD.estado THEN
    INSERT INTO tar_historial_estado (id_historial, id_tarjeta, estado_anterior, estado_nuevo, motivo, origen)
    VALUES (fn_uuid_v7(), NEW.id_tarjeta, OLD.estado, NEW.estado, 'Cambio de estado', 'SISTEMA');
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Inmutabilidad del historial de estados (no UPDATE ni DELETE)
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_historial_no_update $$
CREATE TRIGGER trg_historial_no_update
BEFORE UPDATE ON tar_historial_estado
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El historial de estados es inmutable';
END $$

DROP TRIGGER IF EXISTS trg_historial_no_delete $$
CREATE TRIGGER trg_historial_no_delete
BEFORE DELETE ON tar_historial_estado
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El historial de estados es inmutable';
END $$

-- ---------------------------------------------------------------------
-- Control de intentos fallidos: bloqueo de credencial y tarjeta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_intento_fallido $$
CREATE TRIGGER trg_intento_fallido
AFTER INSERT ON tar_intento_autenticacion
FOR EACH ROW
BEGIN
  IF NEW.resultado = 'FALLIDO' THEN
    UPDATE tar_credencial
       SET intentos_fallidos = intentos_fallidos + 1
     WHERE id_tarjeta = NEW.id_tarjeta
       AND tipo = NEW.tipo_credencial;

    IF (SELECT intentos_fallidos FROM tar_credencial
         WHERE id_tarjeta = NEW.id_tarjeta AND tipo = NEW.tipo_credencial) >= 3 THEN
      UPDATE tar_credencial
         SET bloqueada = 1
       WHERE id_tarjeta = NEW.id_tarjeta AND tipo = NEW.tipo_credencial;

      UPDATE tar_tarjeta
         SET estado = 'BLOQUEADA'
       WHERE id_tarjeta = NEW.id_tarjeta AND estado = 'ACTIVA';
    END IF;
  ELSE
    UPDATE tar_credencial
       SET intentos_fallidos = 0
     WHERE id_tarjeta = NEW.id_tarjeta
       AND tipo = NEW.tipo_credencial;
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Control de tope diario por autorizaciones aprobadas
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_autorizacion_tope $$
CREATE TRIGGER trg_autorizacion_tope
AFTER INSERT ON tar_autorizacion
FOR EACH ROW
BEGIN
  IF NEW.estado = 'APROBADA' THEN
    INSERT INTO cta_control_tope_diario (id_tope, num_cuenta, id_canal, fecha_corte, monto_acumulado)
    VALUES (fn_uuid_v7(), NEW.num_cuenta, NEW.id_canal, DATE(NEW.fecha_hora), NEW.monto)
    ON DUPLICATE KEY UPDATE monto_acumulado = monto_acumulado + NEW.monto;
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Control de tope diario por transacciones de cuenta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_transaccion_tope $$
CREATE TRIGGER trg_transaccion_tope
AFTER INSERT ON cta_transaccion
FOR EACH ROW
BEGIN
  IF NEW.estado_transaccion = 'APLICADA' AND NEW.tipo_movimiento = 'D' THEN
    INSERT INTO cta_control_tope_diario (id_tope, num_cuenta, id_canal, fecha_corte, monto_acumulado)
    VALUES (fn_uuid_v7(), NEW.num_cuenta, NEW.id_canal, NEW.fecha_valor, NEW.monto)
    ON DUPLICATE KEY UPDATE monto_acumulado = monto_acumulado + NEW.monto;
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Procedimiento: bloquear tarjeta
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_bloquear_tarjeta $$
CREATE PROCEDURE sp_bloquear_tarjeta(
  IN p_id_tarjeta CHAR(36),
  IN p_motivo     VARCHAR(120),
  IN p_origen     VARCHAR(20)
)
BEGIN
  UPDATE tar_tarjeta
     SET estado = 'BLOQUEADA'
   WHERE id_tarjeta = p_id_tarjeta AND estado = 'ACTIVA';
END $$

-- ---------------------------------------------------------------------
-- Procedimiento: aplicar pago por componente y actualizar la cuota
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_aplicar_pago $$
CREATE PROCEDURE sp_aplicar_pago(
  IN p_id_pago          CHAR(36),
  IN p_id_cuota_credito CHAR(36),
  IN p_capital          DECIMAL(15,2),
  IN p_interes          DECIMAL(15,2),
  IN p_seguro           DECIMAL(15,2),
  IN p_mora             DECIMAL(15,2)
)
BEGIN
  DECLARE v_total  DECIMAL(15,2);
  DECLARE v_cuota  DECIMAL(15,2);
  DECLARE v_pagado DECIMAL(15,2);

  SET v_total = p_capital + p_interes + p_seguro + p_mora;

  INSERT INTO cob_aplicacion_pago
    (id_aplicacion, id_pago, id_cuota_credito, aplica_capital, aplica_interes, aplica_seguro, aplica_mora)
  VALUES
    (fn_uuid_v7(), p_id_pago, p_id_cuota_credito, p_capital, p_interes, p_seguro, p_mora);

  SELECT cuota_total, monto_pagado INTO v_cuota, v_pagado
    FROM cob_cuota WHERE id_cuota_credito = p_id_cuota_credito;

  SET v_pagado = v_pagado + v_total;

  UPDATE cob_cuota
     SET monto_pagado = v_pagado,
         estado_cuota = CASE WHEN v_pagado >= v_cuota THEN 'PAGADA'
                             WHEN v_pagado > 0 THEN 'PARCIAL'
                             ELSE estado_cuota END
   WHERE id_cuota_credito = p_id_cuota_credito;

  UPDATE cob_pago SET estado_pago = 'APLICADO' WHERE id_pago = p_id_pago;
END $$

-- ---------------------------------------------------------------------
-- Evento: vencimiento automatico de tarjetas (diario)
-- ---------------------------------------------------------------------
DROP EVENT IF EXISTS ev_expirar_tarjetas $$
CREATE EVENT ev_expirar_tarjetas
ON SCHEDULE EVERY 1 DAY
STARTS (TIMESTAMP(CURRENT_DATE) + INTERVAL 1 DAY)
DO
BEGIN
  UPDATE tar_tarjeta
     SET estado = 'VENCIDA'
   WHERE estado = 'ACTIVA'
     AND fecha_vencimiento < CURRENT_DATE();
END $$

DELIMITER ;

-- <<< FIN 12_triggers_eventos.sql

-- >>> INICIO 13_consultas.sql
-- =====================================================================
-- BNA - Script 13: Consultas documentadas y CRUD por modulo
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- C01-C11: consultas del modulo Tarjetas.
-- CRUD: ejemplos por modulo (INSERT/SELECT/UPDATE/DELETE).
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- =====================================================================
-- MODULO TARJETAS - C01..C11
-- =====================================================================

-- C01: Tarjetas activas de un cliente con sus cuentas asociadas
SELECT t.id_tarjeta, t.ultimos4, t.tipo_tarjeta, tc.num_cuenta, tc.es_principal
FROM tar_tarjeta t
JOIN tar_tarjeta_cuenta tc ON tc.id_tarjeta = t.id_tarjeta
WHERE t.id_cliente = '0198b000-0000-7009-8000-000000000001' AND t.estado = 'ACTIVA';

-- C02: Detalle de una tarjeta y sus credenciales
SELECT t.id_tarjeta, t.ultimos4, t.estado, cr.tipo, cr.bloqueada, cr.intentos_fallidos
FROM tar_tarjeta t
LEFT JOIN tar_credencial cr ON cr.id_tarjeta = t.id_tarjeta
WHERE t.id_tarjeta = '0198b000-0000-700f-8000-000000000001';

-- C03: Intentos de autenticacion fallidos del dia
SELECT id_intento, id_tarjeta, tipo_credencial, id_canal, motivo_rechazo, fecha_hora
FROM tar_intento_autenticacion
WHERE resultado = 'FALLIDO' AND DATE(fecha_hora) = CURRENT_DATE()
ORDER BY fecha_hora DESC;

-- C04: Autorizaciones aprobadas del dia por tarjeta
SELECT id_tarjeta, COUNT(*) AS operaciones, SUM(monto) AS monto_total
FROM tar_autorizacion
WHERE estado = 'APROBADA' AND DATE(fecha_hora) = CURRENT_DATE()
GROUP BY id_tarjeta;

-- C05: Consumo diario por tarjeta y canal (usa la vista)
SELECT * FROM v_consumo_diario WHERE fecha = CURRENT_DATE();

-- C06: Tope restante por canal (usa la vista)
SELECT * FROM v_tope_restante_hoy;

-- C07: Autorizaciones rechazadas y su motivo
SELECT uuid_transaccion, id_tarjeta, monto, motivo_rechazo, fecha_hora
FROM tar_autorizacion
WHERE estado = 'RECHAZADA'
ORDER BY fecha_hora DESC;

-- C08: Resumen de tarjetas por estado
SELECT estado, COUNT(*) AS cantidad
FROM tar_tarjeta
GROUP BY estado;

-- C09: Credenciales en riesgo (usa la vista)
SELECT * FROM v_credenciales_en_riesgo;

-- C10: Tarjetas proximas a vencer en 30 dias
SELECT id_tarjeta, ultimos4, id_cliente, fecha_vencimiento
FROM tar_tarjeta
WHERE estado = 'ACTIVA'
  AND fecha_vencimiento BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY);

-- C11: Historial de estados de una tarjeta
SELECT estado_anterior, estado_nuevo, motivo, origen, fecha_hora
FROM tar_historial_estado
WHERE id_tarjeta = '0198b000-0000-700f-8000-000000000001'
ORDER BY fecha_hora;

-- =====================================================================
-- CRUD - MODULO CLIENTES / KYC
-- =====================================================================
-- Alta de cliente
INSERT INTO cliente (id_cliente, cod_tipo_documento, numero_documento, nombres, apellido_paterno,
                     apellido_materno, fecha_nacimiento, numero_celular, correo_electronico)
VALUES ('0198b000-0000-7009-8000-000000000001','DNI','70000001','Juan','Perez','Quispe','1990-05-10','959000001','juan.perez@example.com');

-- Consulta de cliente por documento
SELECT * FROM cliente WHERE cod_tipo_documento='DNI' AND numero_documento='70000001';

-- Actualizacion de contacto
UPDATE cliente SET numero_celular='959000099' WHERE numero_documento='70000001';

-- Baja logica (cambio de estado)
UPDATE cliente SET estado_cliente='INACTIVO' WHERE numero_documento='70000001';

-- =====================================================================
-- CRUD - MODULO CUENTAS
-- =====================================================================
-- Apertura de cuenta
INSERT INTO cuenta_ahorro (num_cuenta, moneda, regimen, id_agencia, id_producto_ahorro)
VALUES ('0011000001','PEN','LIBRE','0198b000-0000-7001-8000-000000000001','0198b000-0000-7004-8000-000000000001');

-- Vincular titular
INSERT INTO cliente_cuenta (num_cuenta, id_cliente, rol_titular)
SELECT '0011000001', id_cliente, 'TITULAR' FROM cliente WHERE numero_documento='70000001';

-- Registrar deposito
INSERT INTO cta_transaccion (id_transaccion, uuid_transaccion, num_cuenta, tipo_operacion, tipo_movimiento,
                             monto, moneda, id_canal, saldo_posterior, fecha_valor)
VALUES ('0198b000-0000-700e-8000-000000000002','0198b000-0000-700e-8000-000000000001','0011000001','DEPOSITO','C',500.00,'PEN','VEN',500.00,CURRENT_DATE());

-- Consultar saldos
SELECT num_cuenta, saldo_contable, saldo_disponible, saldo_retenido
FROM cuenta_ahorro WHERE num_cuenta='0011000001';

-- Movimientos de la cuenta (usa la vista)
SELECT * FROM v_movimientos_cuenta WHERE num_cuenta='0011000001' ORDER BY fecha_hora DESC;

-- =====================================================================
-- CRUD - MODULO SOLICITUD
-- =====================================================================
INSERT INTO sol_solicitud (id_solicitud, id_cliente, id_producto_credito, monto_solicitado, moneda,
                           plazo_meses, destino_credito)
SELECT '0198b000-0000-700a-8000-000000000001', id_cliente, '0198b000-0000-7005-8000-000000000001', 10000.00, 'PEN', 24, 'Capital de trabajo'
FROM cliente WHERE numero_documento='70000001';

SELECT s.id_solicitud, s.monto_solicitado, s.estado_solicitud, p.nombre AS producto
FROM sol_solicitud s JOIN producto_credito p ON p.id_producto_credito = s.id_producto_credito;

-- =====================================================================
-- CRUD - MODULO EVALUACION
-- =====================================================================
INSERT INTO eva_evaluacion (id_evaluacion, id_solicitud, puntaje, resultado, monto_maximo_sugerido, nivel_riesgo)
VALUES ('0198b000-0000-7012-8000-000000000001', '0198b000-0000-700a-8000-000000000001', 820, 'APROBADO', 10000.00, 'BAJO');

SELECT e.id_evaluacion, e.puntaje, e.resultado, e.nivel_riesgo, d.decision, d.monto_aprobado
FROM eva_evaluacion e
LEFT JOIN eva_decision_analista d ON d.id_evaluacion = e.id_evaluacion;

-- =====================================================================
-- CRUD - MODULO DESEMBOLSO
-- =====================================================================
INSERT INTO des_orden (id_orden, id_solicitud, id_cliente, num_cuenta, id_agencia, monto, moneda, tipo_desembolso)
SELECT '0198b000-0000-7013-8000-000000000001', id_solicitud, id_cliente, '0011000001', '0198b000-0000-7001-8000-000000000001', 10000.00, 'PEN', 'ABONO_CUENTA'
FROM sol_solicitud WHERE id_solicitud = '0198b000-0000-700a-8000-000000000001';

SELECT * FROM des_v_ordenes_inciertas;
SELECT * FROM des_v_entregas_pendientes;
SELECT * FROM des_v_conciliacion_diaria;

-- =====================================================================
-- CRUD - MODULO COBRANZA
-- =====================================================================
-- Alta de credito en cobranza
INSERT INTO cob_credito (id_credito, id_solicitud, id_cliente, num_cuenta_desembolso, monto_aprobado,
                         moneda, tasa_tea, plazo_meses, saldo_capital, fecha_desembolso)
SELECT '0198b000-0000-700b-8000-000000000001', id_solicitud, id_cliente, '0011000001', 10000.00, 'PEN', 0.2200, 24, 10000.00, CURRENT_DATE()
FROM sol_solicitud WHERE id_solicitud = '0198b000-0000-700a-8000-000000000001';

-- Cuota del credito (necesaria para aplicar el pago)
INSERT INTO cob_cuota (id_cuota_credito, id_credito, numero_cuota, fecha_vencimiento, capital, interes,
                       seguro, cuota_total, saldo_capital, monto_pagado)
VALUES ('0198b000-0000-700c-8000-000000000001', '0198b000-0000-700b-8000-000000000001', 1, DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY), 300.00, 230.00,
        20.00, 550.00, 9700.00, 0.00);

-- Resumen de credito (usa la vista)
SELECT * FROM v_credito_resumen;

-- Registrar pago y aplicarlo por componente (procedimiento)
INSERT INTO cob_pago (id_pago, id_credito, id_canal_pago, monto, moneda, num_operacion)
VALUES ('0198b000-0000-700d-8000-000000000001', '0198b000-0000-700b-8000-000000000001', '0198b000-0000-7008-8000-000000000001', 550.00, 'PEN', 'OP-000001');
CALL sp_aplicar_pago('0198b000-0000-700d-8000-000000000001', '0198b000-0000-700c-8000-000000000001', 300.00, 230.00, 20.00, 0.00);

-- <<< FIN 13_consultas.sql

