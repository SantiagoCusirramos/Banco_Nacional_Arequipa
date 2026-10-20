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
