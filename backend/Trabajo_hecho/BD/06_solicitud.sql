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
