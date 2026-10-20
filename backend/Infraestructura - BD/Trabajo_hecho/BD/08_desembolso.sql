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
