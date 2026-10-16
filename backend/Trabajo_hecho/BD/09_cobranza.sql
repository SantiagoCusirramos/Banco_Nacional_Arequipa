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
