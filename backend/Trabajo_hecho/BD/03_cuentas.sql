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
