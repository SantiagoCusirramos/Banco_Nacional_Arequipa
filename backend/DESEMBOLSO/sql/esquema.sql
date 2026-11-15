-- =====================================================================
-- BNA - Modulo 13 Desembolso (Linea de Creditos): esquema de bna_desembolso
-- Motor: MySQL 8.4  |  InnoDB  |  utf8mb4 / utf8mb4_0900_ai_ci
-- Version: v3.0.0   Fecha: 2026-11-15
-- Base propia del modulo en db-aux, como SOL y Cobranza: no toca la base
-- integrada del CORE. Lo aplica scripts/preparar_base.py (desembolso-init)
-- en cada arranque: es idempotente y no borra datos.
-- Cambios respecto de database/sql/08_desembolso.sql (repo del modulo):
--   * Sin USE: la base la elige quien ejecuta el script.
--   * CREATE TABLE IF NOT EXISTS y DROP TRIGGER IF EXISTS: se puede repetir.
--   * des_orden guarda solicitud_id y el calendario de Solicitud recibido con
--     la aprobacion (CR-INT-04); va sin cambios a Cobranza (CR-INT-06).
--   * des_evento_entrega tambien lleva el aviso a Evaluacion
--     (aprobacion.desembolsada).
-- Sin llaves foraneas hacia otros modulos (PA-04): los ids externos son
-- referencias logicas que se verifican en cada modulo.
-- =====================================================================
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- des_orden: intencion, ejecucion y resultado del desembolso
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS des_orden (
  id                      CHAR(36)        NOT NULL COMMENT 'UUID v7 generado por la aplicacion',
  codigo_orden            VARCHAR(24)     NOT NULL COMMENT 'Correlativo legible DES-AAAA-NNNNNN',
  aprobacion_id           VARCHAR(36)     NOT NULL COMMENT 'Ref. logica a Evaluacion (12), CR-INT-04',
  aprobacion_version      INT UNSIGNED    NOT NULL DEFAULT 1 COMMENT 'Version de la aprobacion consumida',
  credito_id              VARCHAR(36)     NOT NULL COMMENT 'Ref. logica a Solicitud de Credito (11)',
  cliente_id              VARCHAR(36)     NOT NULL COMMENT 'Ref. logica a Clientes (2)',
  cuenta_id               VARCHAR(36)     NULL COMMENT 'Cuenta destino, ref. logica a Cuentas (3); se fija al validar la cuenta',
  importe                 DECIMAL(15,2)   NOT NULL COMMENT 'Monto bruto a desembolsar; se toma de la aprobacion (RN-04)',
  moneda                  CHAR(3)         NOT NULL COMMENT 'ISO 4217: PEN o USD',
  estado                  ENUM('PREPARADA','VALIDADA','EN_PROCESO','POR_VERIFICAR','CONFIRMADA','RECHAZADA','REVERTIDA')
                          NOT NULL DEFAULT 'PREPARADA' COMMENT 'Estado financiero de la orden',
  motivo_rechazo          VARCHAR(255)    NULL COMMENT 'Motivo cuando el estado es RECHAZADA',
  entrega_estado          ENUM('PENDIENTE','CONFIRMADA') NOT NULL DEFAULT 'PENDIENTE'
                          COMMENT 'Entrega a Cobranza, independiente del estado financiero (RN-08)',
  operacion_financiera_id VARCHAR(40)     NULL COMMENT 'Operacion financiera devuelta por Cuentas/CORE (CR-INT-05)',
  fecha_efectiva          DATETIME        NULL COMMENT 'Fecha valor del abono segun Cuentas/CORE',
  idempotency_key         CHAR(36)        NOT NULL COMMENT 'Clave X-Idempotency-Key de la operacion de negocio',
  request_hash            CHAR(64)        NOT NULL COMMENT 'SHA-256 del contenido canonico de la solicitud de preparacion',
  canal                   ENUM('AGENCIA','HOME_BANKING') NOT NULL DEFAULT 'AGENCIA' COMMENT 'Canal de origen; HOME_BANKING fuera del escenario base',
  agencia_id              VARCHAR(36)     NULL COMMENT 'Agencia donde se prepara la orden',
  usuario_preparacion     VARCHAR(40)     NOT NULL COMMENT 'Operador que prepara la orden',
  usuario_confirmacion    VARCHAR(40)     NULL COMMENT 'Operador que confirma la ejecucion',
  correlation_id          CHAR(36)        NOT NULL COMMENT 'X-Correlation-ID propagado por el Bus',
  version                 INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT 'Control de concurrencia optimista',
  solicitud_id            VARCHAR(36)     NULL COMMENT 'idSolicitud de Solicitud (11), recibido con la aprobacion',
  calendario_pagos        JSON            NULL COMMENT 'Calendario de Solicitud (RN-SOL-006) recibido con la aprobacion; va sin cambios a Cobranza',
  credito_en_ejecucion    VARCHAR(36) GENERATED ALWAYS AS (
                            CASE WHEN estado IN ('EN_PROCESO','POR_VERIFICAR','CONFIRMADA','REVERTIDA')
                                 THEN credito_id ELSE NULL END) STORED
                          COMMENT 'Igual a credito_id solo desde que la orden llega a Cuentas; UNIQUE impone RN-05',
  creado_en               TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Creacion (UTC)',
  actualizado_en          TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)
                          COMMENT 'Ultima modificacion (UTC)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_orden_codigo (codigo_orden),
  UNIQUE KEY uk_orden_idempotency (idempotency_key),
  UNIQUE KEY uk_orden_credito_en_ejecucion (credito_en_ejecucion),
  KEY idx_orden_estado (estado, actualizado_en),
  KEY idx_orden_entrega (entrega_estado, estado),
  KEY idx_orden_credito (credito_id),
  KEY idx_orden_cliente (cliente_id),
  KEY idx_orden_fecha_efectiva (fecha_efectiva, moneda),
  CONSTRAINT ck_orden_importe CHECK (importe > 0),
  CONSTRAINT ck_orden_moneda CHECK (moneda IN ('PEN','USD')),
  CONSTRAINT ck_orden_cuenta CHECK (estado = 'PREPARADA' OR estado = 'RECHAZADA' OR cuenta_id IS NOT NULL),
  CONSTRAINT ck_orden_confirmada CHECK (estado NOT IN ('CONFIRMADA','REVERTIDA')
                                        OR (operacion_financiera_id IS NOT NULL AND fecha_efectiva IS NOT NULL)),
  CONSTRAINT ck_orden_rechazada CHECK (estado <> 'RECHAZADA' OR motivo_rechazo IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Ordenes de desembolso del modulo 13';

-- ---------------------------------------------------------------------
-- des_validacion: evidencia de cada validacion previa a la ejecucion.
-- No almacena biometria: solo la referencia opaca del proveedor.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS des_validacion (
  id                    CHAR(36)        NOT NULL COMMENT 'UUID v7 de la validacion',
  orden_id              CHAR(36)        NOT NULL COMMENT 'Orden a la que pertenece',
  tipo                  ENUM('APROBACION','IDENTIDAD','CUENTA','AUTORIZACION','ANTIFRAUDE') NOT NULL
                        COMMENT 'APROBACION=Evaluacion, IDENTIDAD=Clientes, CUENTA=Cuentas, AUTORIZACION/ANTIFRAUDE=Seguridad',
  fase                  ENUM('PREPARACION','EJECUCION') NOT NULL DEFAULT 'PREPARACION'
                        COMMENT 'EJECUCION = revalidacion en la frontera de ejecucion (RN-06)',
  proveedor             VARCHAR(40)     NOT NULL COMMENT 'Modulo que emitio la validacion',
  referencia_evidencia  VARCHAR(100)    NOT NULL COMMENT 'Referencia opaca devuelta por el proveedor',
  resultado             ENUM('APROBADA','RECHAZADA') NOT NULL,
  detalle               VARCHAR(255)    NULL COMMENT 'Observacion funcional, sin datos sensibles',
  vence_en              DATETIME        NULL COMMENT 'Vigencia informada por el proveedor',
  creado_en             TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Momento de la validacion (UTC)',
  PRIMARY KEY (id),
  KEY idx_validacion_orden (orden_id, tipo, creado_en),
  CONSTRAINT fk_validacion_orden FOREIGN KEY (orden_id) REFERENCES des_orden (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Validaciones previas al desembolso';

-- ---------------------------------------------------------------------
-- des_evento_entrega: bandeja de salida (outbox) hacia Cobranza y Evaluacion.
-- Entrega al menos una vez; el id del evento es la clave de deduplicacion.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS des_evento_entrega (
  id                CHAR(36)          NOT NULL COMMENT 'UUID v7 del evento (eventoId para Cobranza)',
  orden_id          CHAR(36)          NOT NULL COMMENT 'Orden que origino el evento',
  tipo              VARCHAR(60)       NOT NULL COMMENT 'desembolso.confirmado (Cobranza) | aprobacion.desembolsada (Evaluacion) | desembolso.revertido',
  version_esquema   VARCHAR(10)       NOT NULL DEFAULT 'v1' COMMENT 'Version del contrato del mensaje',
  payload           JSON              NOT NULL COMMENT 'Mensaje para Cobranza (CR-INT-06) o Evaluacion (CR-INT-04)',
  estado            ENUM('PENDIENTE','ENVIADO','CONFIRMADO','FALLIDO') NOT NULL DEFAULT 'PENDIENTE',
  intentos          SMALLINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Intentos de entrega realizados',
  siguiente_intento DATETIME          NULL COMMENT 'Proximo reintento (UTC)',
  confirmacion_id   VARCHAR(60)       NULL COMMENT 'Acuse de recibo del modulo destino',
  ultimo_error      VARCHAR(255)      NULL COMMENT 'Ultimo error de entrega',
  creado_en         TIMESTAMP(3)      NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  actualizado_en    TIMESTAMP(3)      NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_evento_orden_tipo (orden_id, tipo),
  KEY idx_evento_pendientes (estado, siguiente_intento),
  CONSTRAINT fk_evento_orden FOREIGN KEY (orden_id) REFERENCES des_orden (id),
  CONSTRAINT ck_evento_tipo CHECK (tipo IN ('desembolso.confirmado','aprobacion.desembolsada','desembolso.revertido'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Outbox de entregas a Cobranza y avisos a Evaluacion';

-- ---------------------------------------------------------------------
-- des_auditoria: bitacora de solo insercion. El usuario de aplicacion
-- recibe solo INSERT y SELECT; los triggers bloquean UPDATE y DELETE.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS des_auditoria (
  id              BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT COMMENT 'Correlativo interno de la bitacora',
  orden_id        CHAR(36)          NULL COMMENT 'Orden afectada, si aplica (sin FK: puede registrar intentos sobre ids inexistentes)',
  actor_id        VARCHAR(40)       NOT NULL COMMENT 'Usuario o servicio que ejecuta la accion',
  accion          VARCHAR(60)       NOT NULL COMMENT 'PREPARAR, VALIDAR, CONFIRMAR, CONSULTAR, ENTREGAR, RECUPERAR, CONCILIAR, REVERTIR, ACCESO_DENEGADO',
  resultado       VARCHAR(40)       NOT NULL COMMENT 'Resultado de la accion registrada',
  correlation_id  CHAR(36)          NOT NULL COMMENT 'Correlacion con la traza del Bus',
  ip              VARCHAR(45)       NULL COMMENT 'Direccion de origen (admite IPv6)',
  detalle         JSON              NULL COMMENT 'Datos enmascarados, sin secretos ni cuentas completas',
  creado_en       TIMESTAMP(3)      NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Marca con milisegundos (UTC)',
  PRIMARY KEY (id),
  KEY idx_auditoria_correlation (correlation_id),
  KEY idx_auditoria_orden (orden_id, creado_en),
  KEY idx_auditoria_actor (actor_id, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bitacora de solo insercion del modulo desembolso';

-- ---------------------------------------------------------------------
-- des_solicitud_reversion: reversiones (extornos). La politica esta
-- PENDIENTE (PC-05 / OBS-DES-07): la aplicacion la deshabilita por defecto.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS des_solicitud_reversion (
  id                      CHAR(36)      NOT NULL COMMENT 'UUID v7 de la solicitud',
  orden_id                CHAR(36)      NOT NULL COMMENT 'Orden cuyo desembolso se desea revertir',
  motivo                  VARCHAR(255)  NOT NULL COMMENT 'Motivo declarado por el solicitante',
  origen                  ENUM('SOLICITUD_SERVICIO','INCIDENTE') NOT NULL DEFAULT 'SOLICITUD_SERVICIO'
                          COMMENT 'AC-44: decision de negocio o falla tecnica',
  solicitante_id          VARCHAR(40)   NOT NULL COMMENT 'Usuario que solicita la reversion',
  autorizador_id          VARCHAR(40)   NULL COMMENT 'Supervisor que autoriza; distinto del solicitante',
  autorizacion_id         VARCHAR(60)   NULL COMMENT 'Referencia de autorizacion de Seguridad (9)',
  estado                  ENUM('SOLICITADA','AUTORIZADA','EN_PROCESO','POR_VERIFICAR','CONFIRMADA','RECHAZADA')
                          NOT NULL DEFAULT 'SOLICITADA',
  motivo_rechazo          VARCHAR(255)  NULL,
  idempotency_key         CHAR(36)      NOT NULL COMMENT 'Clave propia de la reversion',
  reversion_financiera_id VARCHAR(40)   NULL COMMENT 'Operacion de reversion registrada por Cuentas/CORE',
  correlation_id          CHAR(36)      NOT NULL,
  orden_reversion_activa  CHAR(36) GENERATED ALWAYS AS (
                            CASE WHEN estado <> 'RECHAZADA' THEN orden_id ELSE NULL END) STORED
                          COMMENT 'Una sola reversion activa o confirmada por orden',
  creado_en               TIMESTAMP(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  actualizado_en          TIMESTAMP(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_reversion_idempotency (idempotency_key),
  UNIQUE KEY uk_reversion_activa (orden_reversion_activa),
  KEY idx_reversion_estado (estado, actualizado_en),
  CONSTRAINT fk_reversion_orden FOREIGN KEY (orden_id) REFERENCES des_orden (id),
  CONSTRAINT ck_reversion_autorizador CHECK (autorizador_id IS NULL OR autorizador_id <> solicitante_id),
  CONSTRAINT ck_reversion_rechazada CHECK (estado <> 'RECHAZADA' OR motivo_rechazo IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Solicitudes de reversion de desembolso';

-- ---------------------------------------------------------------------
-- des_correlativo: generador del codigo legible DES-AAAA-NNNNNN.
-- La aplicacion incrementa con SELECT ... FOR UPDATE en la misma
-- transaccion que inserta la orden.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS des_correlativo (
  anio            SMALLINT UNSIGNED NOT NULL COMMENT 'Anio del correlativo',
  ultimo_numero   INT UNSIGNED      NOT NULL DEFAULT 0 COMMENT 'Ultimo numero emitido',
  PRIMARY KEY (anio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Correlativo anual de ordenes de desembolso';

-- ---------------------------------------------------------------------
-- Triggers de integridad del modulo
-- ---------------------------------------------------------------------
DELIMITER $$

-- Maquina de estados de des_orden y datos financieros inmutables.
DROP TRIGGER IF EXISTS trg_des_orden_bu$$
CREATE TRIGGER trg_des_orden_bu BEFORE UPDATE ON des_orden
FOR EACH ROW
BEGIN
  IF NEW.estado <> OLD.estado AND NOT (
       (OLD.estado = 'PREPARADA'     AND NEW.estado IN ('VALIDADA','RECHAZADA'))
    OR (OLD.estado = 'VALIDADA'      AND NEW.estado IN ('PREPARADA','EN_PROCESO','RECHAZADA'))
    OR (OLD.estado = 'EN_PROCESO'    AND NEW.estado IN ('CONFIRMADA','RECHAZADA','POR_VERIFICAR'))
    OR (OLD.estado = 'POR_VERIFICAR' AND NEW.estado IN ('CONFIRMADA','RECHAZADA'))
    OR (OLD.estado = 'CONFIRMADA'    AND NEW.estado = 'REVERTIDA')
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'des_orden: transicion de estado no permitida';
  END IF;

  IF OLD.estado IN ('EN_PROCESO','POR_VERIFICAR','CONFIRMADA','REVERTIDA') AND (
       NEW.importe <> OLD.importe
    OR NEW.moneda <> OLD.moneda
    OR NOT (NEW.cuenta_id <=> OLD.cuenta_id)
    OR NEW.credito_id <> OLD.credito_id
    OR NEW.aprobacion_id <> OLD.aprobacion_id
    OR NEW.idempotency_key <> OLD.idempotency_key
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'des_orden: datos financieros inmutables tras iniciar la ejecucion';
  END IF;

  IF OLD.operacion_financiera_id IS NOT NULL
     AND NOT (NEW.operacion_financiera_id <=> OLD.operacion_financiera_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'des_orden: la operacion financiera no puede modificarse';
  END IF;

  IF NOT (NEW.calendario_pagos <=> OLD.calendario_pagos) OR NOT (NEW.solicitud_id <=> OLD.solicitud_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'des_orden: el calendario de Solicitud no se modifica';
  END IF;
END$$

-- Bitacora de solo insercion.
DROP TRIGGER IF EXISTS trg_des_auditoria_bu$$
CREATE TRIGGER trg_des_auditoria_bu BEFORE UPDATE ON des_auditoria
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'des_auditoria es de solo insercion';
END$$

DROP TRIGGER IF EXISTS trg_des_auditoria_bd$$
CREATE TRIGGER trg_des_auditoria_bd BEFORE DELETE ON des_auditoria
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'des_auditoria es de solo insercion';
END$$

DELIMITER ;

-- ---------------------------------------------------------------------
-- Vistas de apoyo operativo
-- ---------------------------------------------------------------------

-- Ordenes con resultado financiero incierto: alimentan la recuperacion.
CREATE OR REPLACE VIEW des_v_ordenes_inciertas AS
SELECT o.id,
       o.codigo_orden,
       o.credito_id,
       o.importe,
       o.moneda,
       o.estado,
       o.idempotency_key,
       o.correlation_id,
       o.actualizado_en,
       TIMESTAMPDIFF(SECOND, o.actualizado_en, CURRENT_TIMESTAMP(3)) AS segundos_en_estado
FROM des_orden o
WHERE o.estado IN ('EN_PROCESO','POR_VERIFICAR');

-- Entregas a Cobranza y avisos a Evaluacion no confirmados (monitoreo y alertas).
CREATE OR REPLACE VIEW des_v_entregas_pendientes AS
SELECT e.id AS evento_id,
       e.orden_id,
       o.codigo_orden,
       o.credito_id,
       e.tipo,
       e.estado,
       e.intentos,
       e.siguiente_intento,
       e.ultimo_error,
       e.creado_en,
       TIMESTAMPDIFF(MINUTE, e.creado_en, CURRENT_TIMESTAMP(3)) AS antiguedad_min
FROM des_evento_entrega e
JOIN des_orden o ON o.id = e.orden_id
WHERE e.estado IN ('PENDIENTE','ENVIADO','FALLIDO');

-- Base para cuadrar operaciones e importes por fecha y moneda contra Cuentas/CORE.
CREATE OR REPLACE VIEW des_v_conciliacion_diaria AS
SELECT DATE(o.fecha_efectiva)                         AS fecha,
       o.moneda,
       COUNT(*)                                       AS cantidad_ordenes,
       SUM(o.importe)                                 AS importe_total,
       SUM(o.estado = 'REVERTIDA')                    AS cantidad_revertidas,
       SUM(o.entrega_estado = 'CONFIRMADA')           AS entregas_confirmadas,
       SUM(o.entrega_estado = 'PENDIENTE')            AS entregas_pendientes
FROM des_orden o
WHERE o.estado IN ('CONFIRMADA','REVERTIDA')
GROUP BY DATE(o.fecha_efectiva), o.moneda;
