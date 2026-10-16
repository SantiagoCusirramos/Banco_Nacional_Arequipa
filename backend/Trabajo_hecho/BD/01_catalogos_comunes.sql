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
