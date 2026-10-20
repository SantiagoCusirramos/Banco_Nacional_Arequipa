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
