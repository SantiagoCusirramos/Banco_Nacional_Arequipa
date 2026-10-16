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
