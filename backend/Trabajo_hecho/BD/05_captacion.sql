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
