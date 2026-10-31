-- =====================================================================
-- Banco Nacional de Arequipa (BNA) - base de datos integrada del CORE
-- MySQL 8.4. Generado por modelo/modelo_bna.py desde el esquema
-- relacional normalizado (3FN) y con tablas de catálogo; el diseño es el
-- de la rama main (PostgreSQL) y solo cambia la capa física.
-- =====================================================================
-- DECISIÓN: MySQL 8.4, por decisión del equipo de infraestructura, en
--   contra de la recomendación del informe (sección «Selección del
--   sistema gestor de base de datos»).
-- DECISIÓN: una base (database) por cada esquema lógico de la rama main,
--   con los mismos nombres calificados; collation utf8mb4_0900_as_cs, que
--   distingue mayúsculas y tildes como PostgreSQL (con la de omisión,
--   CHECK (x IN ('ACTIVA')) aceptaría 'activa').
-- DECISIÓN: el modo SQL estricto se fija en la configuración del servidor
--   (conf/mysql/bna.cnf) y aquí, en la sesión de carga: cada trigger y
--   procedimiento se ejecuta siempre con el modo vigente al crearlo.
-- DECISIÓN: las claves foráneas se agregan al final con ALTER TABLE, después
--   de los índices, para que InnoDB use esos índices y no cree otros;
--   ON DELETE RESTRICT por omisión, porque los registros financieros no se
--   borran, se anulan o revierten.

SET NAMES utf8mb4;
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ONLY_FULL_GROUP_BY,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION time_zone = '+00:00';

CREATE DATABASE IF NOT EXISTS core CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
CREATE DATABASE IF NOT EXISTS clientes CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
CREATE DATABASE IF NOT EXISTS cuentas CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
CREATE DATABASE IF NOT EXISTS tarjetas CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
CREATE DATABASE IF NOT EXISTS creditos CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
CREATE USER IF NOT EXISTS 'bna_owner'@'%' ACCOUNT LOCK;
GRANT ALL PRIVILEGES ON core.* TO 'bna_owner'@'%';
GRANT ALL PRIVILEGES ON clientes.* TO 'bna_owner'@'%';
GRANT ALL PRIVILEGES ON cuentas.* TO 'bna_owner'@'%';
GRANT ALL PRIVILEGES ON tarjetas.* TO 'bna_owner'@'%';
GRANT ALL PRIVILEGES ON creditos.* TO 'bna_owner'@'%';

-- ---------------------------------------------------------------------
CREATE TABLE core.agencia (
    id_agencia                  VARCHAR(10),
    nombre                      VARCHAR(100) NOT NULL,
    calle                       VARCHAR(120) NOT NULL,
    distrito                    VARCHAR(60) NOT NULL,
    ciudad                      VARCHAR(60) NOT NULL,
    estado_agencia              VARCHAR(25) NOT NULL
        CHECK (estado_agencia IN ('ACTIVA', 'INACTIVA')),
    CONSTRAINT pk_agencia PRIMARY KEY (id_agencia)
) ENGINE = InnoDB COMMENT = 'Agencia física del BNA; las cuatro agencias iniciales de Arequipa.';

-- ---------------------------------------------------------------------
CREATE TABLE core.cuenta_contable (
    codigo_contable             VARCHAR(20),
    nombre                      VARCHAR(100) NOT NULL,
    naturaleza                  VARCHAR(25) NOT NULL
        CHECK (naturaleza IN ('DEUDORA', 'ACREEDORA')),
    codigo_padre                VARCHAR(20),
    CONSTRAINT pk_cuenta_contable PRIMARY KEY (codigo_contable)
) ENGINE = InnoDB COMMENT = 'Cuenta del plan de cuentas sobre la que se registran los asientos.';

-- ---------------------------------------------------------------------
CREATE TABLE core.asiento_contable (
    id_asiento                  BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    numero_asiento              VARCHAR(20) NOT NULL,
    fecha_contable              DATE NOT NULL,
    fecha_valor                 DATE NOT NULL,
    glosa                       VARCHAR(200) NOT NULL,
    moneda                      CHAR(3) NOT NULL,
    correlation_id              BINARY(16) NOT NULL,
    id_asiento_revertido        BINARY(16),
    CONSTRAINT pk_asiento_contable PRIMARY KEY (id_asiento),
    CONSTRAINT uk_asiento_contable_1 UNIQUE (numero_asiento),
    CONSTRAINT uk_asiento_contable_2 UNIQUE (id_asiento_revertido),
    CONSTRAINT ck_asiento_contable_id_asiento CHECK ((ASCII(SUBSTR(id_asiento, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_asiento, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_asiento_contable_correlation_id CHECK ((ASCII(SUBSTR(correlation_id, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(correlation_id, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_asiento_contable_id_asiento_revertido CHECK ((ASCII(SUBSTR(id_asiento_revertido, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_asiento_revertido, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Cabecera del asiento de partida doble; es inmutable y se corrige con un asiento de reversa.';

-- ---------------------------------------------------------------------
CREATE TABLE core.detalle_asiento (
    id_asiento                  BINARY(16),
    nro_linea                   SMALLINT,
    tipo_partida                VARCHAR(25) NOT NULL
        CHECK (tipo_partida IN ('DEBE', 'HABER')),
    importe                     DECIMAL(15,2) NOT NULL,
    codigo_contable             VARCHAR(20) NOT NULL,
    CONSTRAINT pk_detalle_asiento PRIMARY KEY (id_asiento, nro_linea),
    CONSTRAINT ck_detalle_asiento_1 CHECK (importe > 0),
    CONSTRAINT ck_detalle_asiento_id_asiento CHECK ((ASCII(SUBSTR(id_asiento, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_asiento, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Línea de débito o crédito de un asiento; no existe ni se identifica sin su asiento.';

-- ---------------------------------------------------------------------
CREATE TABLE core.moneda (
    cod_moneda                  CHAR(3),
    nombre                      VARCHAR(100) NOT NULL,
    simbolo                     VARCHAR(4) NOT NULL,
    decimales                   SMALLINT NOT NULL,
    CONSTRAINT pk_moneda PRIMARY KEY (cod_moneda)
) ENGINE = InnoDB COMMENT = 'Catálogo. Parámetro del CORE junto con los tipos de cambio; código ISO 4217.';

-- ---------------------------------------------------------------------
CREATE TABLE core.modulo (
    id_modulo                   SMALLINT,
    nombre                      VARCHAR(40) NOT NULL,
    CONSTRAINT pk_modulo PRIMARY KEY (id_modulo),
    CONSTRAINT uk_modulo_1 UNIQUE (nombre)
) ENGINE = InnoDB COMMENT = 'Catálogo. Numeración oficial: CORE (1), CLIENTES (2), CUENTAS (3), ..., COBRANZA (14).';

-- ---------------------------------------------------------------------
CREATE TABLE core.canal (
    id_canal                    VARCHAR(5),
    nombre                      VARCHAR(40) NOT NULL,
    es_presencial               TINYINT(1) NOT NULL,
    tipo_integracion            VARCHAR(30) NOT NULL,
    activo                      TINYINT(1) DEFAULT TRUE NOT NULL,
    regla_tope                  VARCHAR(20) NOT NULL,
    CONSTRAINT pk_canal PRIMARY KEY (id_canal),
    CONSTRAINT uk_canal_1 UNIQUE (nombre),
    CONSTRAINT ck_canal_es_presencial CHECK (es_presencial IN (0, 1)),
    CONSTRAINT ck_canal_activo CHECK (activo IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Canal de atención; unifica canal (TARJETAS), CANAL_PAGO (COBRANZA) e idCanal (CUENTAS).';

-- ---------------------------------------------------------------------
CREATE TABLE core.canal_validacion (
    id_canal                    VARCHAR(5),
    tipo_validacion             VARCHAR(15),
    CONSTRAINT pk_canal_validacion PRIMARY KEY (id_canal, tipo_validacion)
) ENGINE = InnoDB COMMENT = 'Credenciales que exige cada canal (atributo multivaluado).';

-- ---------------------------------------------------------------------
CREATE TABLE core.limite_canal (
    id_canal                    VARCHAR(5),
    moneda                      CHAR(3),
    monto_maximo_diario         DECIMAL(15,2),
    habilitado                  TINYINT(1) DEFAULT TRUE NOT NULL,
    CONSTRAINT pk_limite_canal PRIMARY KEY (id_canal, moneda),
    CONSTRAINT ck_limite_canal_1 CHECK (monto_maximo_diario IS NULL OR monto_maximo_diario > 0),
    CONSTRAINT ck_limite_canal_habilitado CHECK (habilitado IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Tope diario de un canal en una moneda (RN-TOP-001).';

-- ---------------------------------------------------------------------
CREATE TABLE core.consumo_diario (
    num_cuenta                  VARCHAR(20),
    id_canal                    VARCHAR(5),
    fecha_corte                 DATE,
    monto_acumulado             DECIMAL(15,2) DEFAULT 0 NOT NULL,
    CONSTRAINT pk_consumo_diario PRIMARY KEY (num_cuenta, id_canal, fecha_corte),
    CONSTRAINT ck_consumo_diario_1 CHECK (monto_acumulado >= 0)
) ENGINE = InnoDB COMMENT = 'Acumulado de salidas de una cuenta por canal y jornada; base del tope diario (RN-TOP-001).';

-- ---------------------------------------------------------------------
CREATE TABLE core.terminal (
    id_terminal                 VARCHAR(30),
    descripcion                 VARCHAR(255) NOT NULL,
    activo                      TINYINT(1) DEFAULT TRUE NOT NULL,
    id_canal                    VARCHAR(5) NOT NULL,
    id_agencia                  VARCHAR(10),
    CONSTRAINT pk_terminal PRIMARY KEY (id_terminal),
    CONSTRAINT ck_terminal_activo CHECK (activo IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Terminales físicas (cajeros, agentes, ventanillas) y su canal (3FN).';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.cliente (
    cod_cliente                 VARCHAR(12),
    tipo_documento              VARCHAR(10) NOT NULL,
    numero_documento            VARCHAR(12) NOT NULL,
    nombres                     VARCHAR(100) NOT NULL,
    apellido_paterno            VARCHAR(100) NOT NULL,
    apellido_materno            VARCHAR(100),
    correo                      VARCHAR(150) NOT NULL,
    celular                     CHAR(9) NOT NULL,
    estado_cliente              VARCHAR(25) NOT NULL,
    id_verificacion_captacion   VARCHAR(36) NOT NULL,
    version_contrato            VARCHAR(10) NOT NULL,
    CONSTRAINT pk_cliente PRIMARY KEY (cod_cliente),
    CONSTRAINT uk_cliente_1 UNIQUE (tipo_documento, numero_documento),
    CONSTRAINT uk_cliente_2 UNIQUE (correo),
    CONSTRAINT uk_cliente_3 UNIQUE (celular),
    CONSTRAINT uk_cliente_4 UNIQUE (id_verificacion_captacion),
    CONSTRAINT ck_cliente_1 CHECK (REGEXP_LIKE(celular, '^9[0-9]{8}$'))
) ENGINE = InnoDB COMMENT = 'Maestro único de la persona natural cliente del banco; reemplaza a CLIENTE_REF, cliente_ref y CLIENTES.';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.biometria_cliente (
    id_biometria                BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    tipo_biometria              VARCHAR(10) NOT NULL,
    datos_biometricos           LONGBLOB NOT NULL,
    estado_activo               TINYINT(1) DEFAULT TRUE NOT NULL,
    cod_cliente                 VARCHAR(12) NOT NULL,
    CONSTRAINT pk_biometria_cliente PRIMARY KEY (id_biometria),
    CONSTRAINT ck_biometria_cliente_id_biometria CHECK ((ASCII(SUBSTR(id_biometria, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_biometria, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_biometria_cliente_estado_activo CHECK (estado_activo IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Plantilla biométrica registrada del cliente, cifrada con AES-256.';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.codigo_verificacion (
    id_codigo                   BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    tipo_contacto               VARCHAR(10) NOT NULL,
    codigo_otp                  CHAR(64) NOT NULL,
    fecha_expiracion            DATETIME(6) NOT NULL,
    estado_codigo               VARCHAR(25) NOT NULL
        CHECK (estado_codigo IN ('PENDIENTE', 'VALIDADO', 'EXPIRADO', 'BLOQUEADO')),
    intentos_fallidos           SMALLINT DEFAULT 0 NOT NULL,
    cod_cliente                 VARCHAR(12) NOT NULL,
    CONSTRAINT pk_codigo_verificacion PRIMARY KEY (id_codigo),
    CONSTRAINT ck_codigo_verificacion_id_codigo CHECK ((ASCII(SUBSTR(id_codigo, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_codigo, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Código OTP temporal enviado al celular o al correo del cliente.';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.validacion_identidad (
    id_validacion               BIGINT AUTO_INCREMENT,
    tipo_validacion             VARCHAR(15) NOT NULL,
    resultado                   VARCHAR(25) NOT NULL
        CHECK (resultado IN ('APROBADO', 'RECHAZADO')),
    correlation_id              BINARY(16) NOT NULL,
    fecha_evento                DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    cod_cliente                 VARCHAR(12),
    CONSTRAINT pk_validacion_identidad PRIMARY KEY (id_validacion),
    CONSTRAINT ck_validacion_identidad_correlation_id CHECK ((ASCII(SUBSTR(correlation_id, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(correlation_id, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Bitácora inmutable de cada intento de validación de identidad (antes AUDITORIA_VALIDACION).';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.verificacion_captacion (
    id_verificacion_captacion   VARCHAR(36),
    fecha_verificacion          DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    estado_habilitante          VARCHAR(25) NOT NULL
        CHECK (estado_habilitante IN ('HABILITADO', 'OBSERVADO')),
    CONSTRAINT pk_verificacion_captacion PRIMARY KEY (id_verificacion_captacion)
) ENGINE = InnoDB COMMENT = 'Verificación de captación del cliente (3FN).';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.tipo_documento (
    cod_tipo_documento          VARCHAR(10),
    descripcion                 VARCHAR(255) NOT NULL,
    longitud_min                SMALLINT NOT NULL,
    longitud_max                SMALLINT NOT NULL,
    es_alfanumerico             TINYINT(1) NOT NULL,
    CONSTRAINT pk_tipo_documento PRIMARY KEY (cod_tipo_documento),
    CONSTRAINT ck_tipo_documento_1 CHECK (longitud_min <= longitud_max),
    CONSTRAINT ck_tipo_documento_es_alfanumerico CHECK (es_alfanumerico IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. DNI de 8 dígitos, PTP de 9, pasaporte alfanumérico de hasta 12 (RN-CLI-001).';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.tipo_biometria (
    cod_tipo_biometria          VARCHAR(10),
    descripcion                 VARCHAR(255) NOT NULL,
    umbral_similitud            DECIMAL(5,4),
    CONSTRAINT pk_tipo_biometria PRIMARY KEY (cod_tipo_biometria)
) ENGINE = InnoDB COMMENT = 'Catálogo. El umbral de similitud es el punto abierto R-03 de CLIENTES.';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.tipo_contacto (
    cod_tipo_contacto           VARCHAR(10),
    descripcion                 VARCHAR(255) NOT NULL,
    vigencia_minutos            SMALLINT NOT NULL,
    max_intentos                SMALLINT NOT NULL,
    CONSTRAINT pk_tipo_contacto PRIMARY KEY (cod_tipo_contacto),
    CONSTRAINT ck_tipo_contacto_1 CHECK (vigencia_minutos > 0),
    CONSTRAINT ck_tipo_contacto_2 CHECK (max_intentos > 0)
) ENGINE = InnoDB COMMENT = 'Catálogo. Parametriza la expiración y el bloqueo al tercer intento (RF-CLI-005).';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.tipo_validacion (
    cod_tipo_validacion         VARCHAR(15),
    descripcion                 VARCHAR(255) NOT NULL,
    endpoint                    VARCHAR(80) NOT NULL,
    CONSTRAINT pk_tipo_validacion PRIMARY KEY (cod_tipo_validacion),
    CONSTRAINT uk_tipo_validacion_1 UNIQUE (endpoint)
) ENGINE = InnoDB COMMENT = 'Catálogo. Los cinco flujos de KYC y su endpoint /api/v1/kyc/....';

-- ---------------------------------------------------------------------
CREATE TABLE clientes.estado_cliente (
    cod_estado                  VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    permite_operar              TINYINT(1) NOT NULL,
    CONSTRAINT pk_estado_cliente PRIMARY KEY (cod_estado),
    CONSTRAINT ck_estado_cliente_permite_operar CHECK (permite_operar IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. Los módulos usan listas distintas (ACTIVO/BLOQUEADO/SUSPENDIDO frente a OBSERVADO/BAJA).';

-- ---------------------------------------------------------------------
CREATE TABLE cuentas.cuenta_ahorro (
    num_cuenta                  VARCHAR(20),
    cci                         CHAR(20) NOT NULL,
    moneda                      CHAR(3) NOT NULL,
    regimen                     VARCHAR(25) NOT NULL,
    saldo_contable              DECIMAL(15,2) DEFAULT 0 NOT NULL,
    saldo_disponible            DECIMAL(15,2) DEFAULT 0 NOT NULL,
    estado_cuenta               VARCHAR(25) NOT NULL,
    fecha_apertura              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_agencia                  VARCHAR(10),
    CONSTRAINT pk_cuenta_ahorro PRIMARY KEY (num_cuenta),
    CONSTRAINT uk_cuenta_ahorro_1 UNIQUE (cci),
    CONSTRAINT ck_cuenta_ahorro_1 CHECK (saldo_disponible <= saldo_contable),
    CONSTRAINT ck_cuenta_ahorro_2 CHECK (saldo_disponible >= 0)
) ENGINE = InnoDB COMMENT = 'Cuenta de ahorros individual o mancomunada; reemplaza a cuenta_ref de TARJETAS.';

-- ---------------------------------------------------------------------
CREATE TABLE cuentas.movimiento (
    uuid_transaccion            BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    tipo_operacion              VARCHAR(25) NOT NULL,
    monto                       DECIMAL(15,2) NOT NULL,
    glosa                       VARCHAR(200) NOT NULL,
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    estado_transaccion          VARCHAR(25) NOT NULL
        CHECK (estado_transaccion IN ('APROBADO', 'EXTORNADO')),
    id_asiento                  BINARY(16) NOT NULL,
    num_cuenta                  VARCHAR(20) NOT NULL,
    id_canal                    VARCHAR(5),
    CONSTRAINT pk_movimiento PRIMARY KEY (uuid_transaccion),
    CONSTRAINT uk_movimiento_1 UNIQUE (id_asiento),
    CONSTRAINT ck_movimiento_1 CHECK (monto > 0),
    CONSTRAINT ck_movimiento_uuid_transaccion CHECK ((ASCII(SUBSTR(uuid_transaccion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(uuid_transaccion, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_movimiento_id_asiento CHECK ((ASCII(SUBSTR(id_asiento, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_asiento, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Débito o crédito aplicado a una cuenta (antes TRANSACCIONES_HISTORICO).';

-- ---------------------------------------------------------------------
CREATE TABLE cuentas.titularidad (
    cod_cliente                 VARCHAR(12),
    num_cuenta                  VARCHAR(20),
    fecha_vinculacion           DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_titularidad PRIMARY KEY (cod_cliente, num_cuenta)
) ENGINE = InnoDB COMMENT = 'Titulares de cada cuenta (relación N:M ES_TITULAR).';

-- ---------------------------------------------------------------------
CREATE TABLE cuentas.tipo_operacion (
    tipo_operacion              VARCHAR(25),
    naturaleza                  CHAR(1) NOT NULL
        CHECK (naturaleza IN ('D', 'C', 'N')),
    CONSTRAINT pk_tipo_operacion PRIMARY KEY (tipo_operacion)
) ENGINE = InnoDB COMMENT = 'Catálogo. Tabla creada en 3FN; ahora también la referencia AUTORIZACION.';

-- ---------------------------------------------------------------------
CREATE TABLE cuentas.regimen_cuenta (
    cod_regimen                 VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    min_titulares               SMALLINT NOT NULL,
    firma_conjunta              TINYINT(1) NOT NULL,
    CONSTRAINT pk_regimen_cuenta PRIMARY KEY (cod_regimen),
    CONSTRAINT ck_regimen_cuenta_1 CHECK (min_titulares >= 1),
    CONSTRAINT ck_regimen_cuenta_firma_conjunta CHECK (firma_conjunta IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. Indistinta (o) y conjunta (y) cambian la regla de autorización (RN-CTA-002).';

-- ---------------------------------------------------------------------
CREATE TABLE cuentas.estado_cuenta (
    cod_estado                  VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    permite_debito              TINYINT(1) NOT NULL,
    permite_credito             TINYINT(1) NOT NULL,
    CONSTRAINT pk_estado_cuenta PRIMARY KEY (cod_estado),
    CONSTRAINT ck_estado_cuenta_permite_debito CHECK (permite_debito IN (0, 1)),
    CONSTRAINT ck_estado_cuenta_permite_credito CHECK (permite_credito IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. BLOQUEADA_PREVENTIVA impide débitos pero no abonos.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.tarjeta (
    id_tarjeta                  BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    pan_token                   VARCHAR(32) NOT NULL,
    bin                         CHAR(6) NOT NULL,
    ultimos4                    CHAR(4) NOT NULL,
    fecha_emision               DATE NOT NULL,
    fecha_vencimiento           DATE NOT NULL,
    estado_tarjeta              VARCHAR(25) NOT NULL,
    cod_cliente                 VARCHAR(12) NOT NULL,
    CONSTRAINT pk_tarjeta PRIMARY KEY (id_tarjeta),
    CONSTRAINT uk_tarjeta_1 UNIQUE (pan_token),
    CONSTRAINT ck_tarjeta_1 CHECK (fecha_vencimiento > fecha_emision),
    CONSTRAINT ck_tarjeta_2 CHECK (REGEXP_LIKE(ultimos4, '^[0-9]{4}$')),
    CONSTRAINT ck_tarjeta_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Tarjeta de débito física o virtual; no guarda el PAN completo (PCI-DSS).';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.bin_tarjeta (
    bin                         CHAR(6),
    tipo_tarjeta                VARCHAR(25) NOT NULL
        CHECK (tipo_tarjeta IN ('FISICA', 'VIRTUAL')),
    descripcion                 VARCHAR(100) NOT NULL,
    CONSTRAINT pk_bin_tarjeta PRIMARY KEY (bin),
    CONSTRAINT ck_bin_tarjeta_1 CHECK (REGEXP_LIKE(bin, '^[0-9]{6}$'))
) ENGINE = InnoDB COMMENT = 'BIN emitidos por el BNA y el tipo de tarjeta que identifican (3FN).';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.tarjeta_cuenta (
    id_tarjeta                  BINARY(16),
    num_cuenta                  VARCHAR(20),
    es_principal                TINYINT(1) DEFAULT FALSE NOT NULL,
    habilitada_atm              TINYINT(1) DEFAULT TRUE NOT NULL,
    fecha_vinculacion           DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_tarjeta_cuenta PRIMARY KEY (id_tarjeta, num_cuenta),
    CONSTRAINT ck_tarjeta_cuenta_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_tarjeta_cuenta_es_principal CHECK (es_principal IN (0, 1)),
    CONSTRAINT ck_tarjeta_cuenta_habilitada_atm CHECK (habilitada_atm IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Cuentas que opera cada tarjeta (relación N:M VINCULA).';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.credencial (
    id_tarjeta                  BINARY(16),
    tipo_credencial             VARCHAR(15),
    hash_credencial             CHAR(64) NOT NULL,
    sal                         CHAR(32) NOT NULL,
    intentos_fallidos           SMALLINT DEFAULT 0 NOT NULL,
    fecha_creacion              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_ultimo_cambio         DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_credencial PRIMARY KEY (id_tarjeta, tipo_credencial),
    CONSTRAINT ck_credencial_1 CHECK (tipo_credencial IN ('PIN_ATM', 'CLAVE_WEB')),
    CONSTRAINT ck_credencial_2 CHECK (intentos_fallidos BETWEEN 0 AND 3),
    CONSTRAINT ck_credencial_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Clave de acceso de una tarjeta; se identifica por la tarjeta y su tipo.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.tipo_credencial (
    tipo_credencial             VARCHAR(15),
    longitud                    SMALLINT,
    CONSTRAINT pk_tipo_credencial PRIMARY KEY (tipo_credencial)
) ENGINE = InnoDB COMMENT = 'Catálogo. Tabla creada en 2FN; se amplía con TOKEN_MATRIZ, BIOMETRIA y TOKEN_PAGO.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.matriz_token (
    id_matriz                   BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    numero_serie                VARCHAR(20) NOT NULL,
    tipo_matriz                 VARCHAR(25) NOT NULL
        CHECK (tipo_matriz IN ('FISICA', 'VIRTUAL')),
    sal                         CHAR(32) NOT NULL,
    estado_matriz               VARCHAR(25) NOT NULL
        CHECK (estado_matriz IN ('ACTIVA', 'BLOQUEADA', 'REEMPLAZADA')),
    intentos_fallidos           SMALLINT DEFAULT 0 NOT NULL,
    fecha_emision               DATE NOT NULL,
    id_tarjeta                  BINARY(16) NOT NULL,
    CONSTRAINT pk_matriz_token PRIMARY KEY (id_matriz),
    CONSTRAINT uk_matriz_token_1 UNIQUE (numero_serie),
    CONSTRAINT ck_matriz_token_1 CHECK (intentos_fallidos BETWEEN 0 AND 3),
    CONSTRAINT ck_matriz_token_id_matriz CHECK ((ASCII(SUBSTR(id_matriz, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_matriz, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_matriz_token_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Tarjeta matriz de coordenadas A--G por 0--9 (RN-TAR-002).';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.matriz_coordenada (
    id_matriz                   BINARY(16),
    fila                        CHAR(1),
    columna                     SMALLINT,
    hash_valor                  CHAR(64) NOT NULL,
    CONSTRAINT pk_matriz_coordenada PRIMARY KEY (id_matriz, fila, columna),
    CONSTRAINT ck_matriz_coordenada_1 CHECK (fila BETWEEN 'A' AND 'G'),
    CONSTRAINT ck_matriz_coordenada_2 CHECK (columna BETWEEN 0 AND 9),
    CONSTRAINT ck_matriz_coordenada_id_matriz CHECK ((ASCII(SUBSTR(id_matriz, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_matriz, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Cada una de las 70 celdas de una tarjeta matriz.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.token_pago (
    id_token_pago               BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    valor_token                 VARCHAR(64) NOT NULL,
    proveedor_pasarela          VARCHAR(20) NOT NULL,
    estado_token                VARCHAR(25) NOT NULL
        CHECK (estado_token IN ('ACTIVO', 'SUSPENDIDO', 'REVOCADO')),
    fecha_creacion              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_expiracion            DATETIME(6) NOT NULL,
    id_tarjeta                  BINARY(16) NOT NULL,
    CONSTRAINT pk_token_pago PRIMARY KEY (id_token_pago),
    CONSTRAINT uk_token_pago_1 UNIQUE (valor_token),
    CONSTRAINT ck_token_pago_id_token_pago CHECK ((ASCII(SUBSTR(id_token_pago, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_token_pago, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_token_pago_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Token entregado a una pasarela externa para el fondeo de la Billetera Digital.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.pasarela_pago (
    id_pasarela                 VARCHAR(20),
    nombre                      VARCHAR(100) NOT NULL,
    CONSTRAINT pk_pasarela_pago PRIMARY KEY (id_pasarela)
) ENGINE = InnoDB COMMENT = 'Catálogo. Punto abierto R-05 sobre la propiedad de las pasarelas.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.intento_autenticacion (
    id_intento                  BIGINT AUTO_INCREMENT,
    tipo_credencial             VARCHAR(15) NOT NULL,
    coord_fila                  CHAR(1),
    coord_columna               SMALLINT,
    id_terminal                 VARCHAR(30),
    ip_origen                   VARCHAR(45),
    resultado                   VARCHAR(25) NOT NULL
        CHECK (resultado IN ('EXITOSO', 'FALLIDO')),
    motivo_rechazo              VARCHAR(255),
    uuid_correlacion            BINARY(16),
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_tarjeta                  BINARY(16) NOT NULL,
    id_canal                    VARCHAR(5),
    CONSTRAINT pk_intento_autenticacion PRIMARY KEY (id_intento),
    CONSTRAINT ck_intento_autenticacion_1 CHECK (coord_fila IS NULL OR coord_fila BETWEEN 'A' AND 'G'),
    CONSTRAINT ck_intento_autenticacion_2 CHECK (coord_columna IS NULL OR coord_columna BETWEEN 0 AND 9),
    CONSTRAINT ck_intento_autenticacion_3 CHECK ((coord_fila IS NULL) = (coord_columna IS NULL)),
    CONSTRAINT ck_intento_autenticacion_4 CHECK ((coord_fila IS NOT NULL) = (tipo_credencial = 'TOKEN_MATRIZ')),
    CONSTRAINT ck_intento_autenticacion_5 CHECK ((id_terminal IS NOT NULL) + (id_canal IS NOT NULL) = 1),
    CONSTRAINT ck_intento_autenticacion_ip_origen CHECK (IS_IPV4(ip_origen) OR IS_IPV6(ip_origen)),
    CONSTRAINT ck_intento_autenticacion_uuid_correlacion CHECK ((ASCII(SUBSTR(uuid_correlacion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(uuid_correlacion, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_intento_autenticacion_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Bitácora inmutable de cada intento de validar una credencial (RN-TAR-004).';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.autorizacion (
    uuid_autorizacion           BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    tipo_operacion              VARCHAR(25) NOT NULL,
    monto                       DECIMAL(15,2) NOT NULL,
    estado_autorizacion         VARCHAR(25) NOT NULL
        CHECK (estado_autorizacion IN ('INICIADA', 'AUTORIZADA', 'RECHAZADA', 'DISPENSADA', 'EXTORNADA', 'PENDIENTE_REVERSION')),
    codigo_respuesta            VARCHAR(4),
    motivo_rechazo              VARCHAR(255),
    nivel_riesgo                VARCHAR(25)
        CHECK (nivel_riesgo IN ('BAJO', 'MEDIO', 'ALTO')),
    id_terminal                 VARCHAR(30),
    ip_origen                   VARCHAR(45),
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_actualizacion         DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_tarjeta                  BINARY(16) NOT NULL,
    num_cuenta                  VARCHAR(20) NOT NULL,
    id_canal                    VARCHAR(5),
    uuid_transaccion            BINARY(16),
    CONSTRAINT pk_autorizacion PRIMARY KEY (uuid_autorizacion),
    CONSTRAINT uk_autorizacion_1 UNIQUE (uuid_transaccion),
    CONSTRAINT ck_autorizacion_1 CHECK (monto >= 0),
    CONSTRAINT ck_autorizacion_2 CHECK ((id_terminal IS NOT NULL) + (id_canal IS NOT NULL) = 1),
    CONSTRAINT ck_autorizacion_3 CHECK (uuid_transaccion IS NULL OR uuid_transaccion = uuid_autorizacion),
    CONSTRAINT ck_autorizacion_uuid_autorizacion CHECK ((ASCII(SUBSTR(uuid_autorizacion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(uuid_autorizacion, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_autorizacion_ip_origen CHECK (IS_IPV4(ip_origen) OR IS_IPV6(ip_origen)),
    CONSTRAINT ck_autorizacion_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_autorizacion_uuid_transaccion CHECK ((ASCII(SUBSTR(uuid_transaccion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(uuid_transaccion, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Autorización que TARJETAS emite antes de que la operación se contabilice.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.codigo_respuesta (
    cod_respuesta               VARCHAR(4),
    descripcion                 VARCHAR(255) NOT NULL,
    es_aprobacion               TINYINT(1) NOT NULL,
    CONSTRAINT pk_codigo_respuesta PRIMARY KEY (cod_respuesta),
    CONSTRAINT ck_codigo_respuesta_es_aprobacion CHECK (es_aprobacion IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. 00 aprobado, 54 tarjeta vencida, EXT extorno.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.historial_estado_tarjeta (
    id_historial                BIGINT AUTO_INCREMENT,
    estado_nuevo                VARCHAR(25) NOT NULL,
    motivo                      VARCHAR(255),
    origen                      VARCHAR(20) NOT NULL,
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_tarjeta                  BINARY(16) NOT NULL,
    CONSTRAINT pk_historial_estado_tarjeta PRIMARY KEY (id_historial),
    CONSTRAINT ck_historial_estado_tarjeta_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Historial inmutable de cambios de estado de cada tarjeta (RN-SEG-002).';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.estado_tarjeta (
    cod_estado                  VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    es_operativa                TINYINT(1) NOT NULL,
    es_final                    TINYINT(1) NOT NULL,
    CONSTRAINT pk_estado_tarjeta PRIMARY KEY (cod_estado),
    CONSTRAINT ck_estado_tarjeta_es_operativa CHECK (es_operativa IN (0, 1)),
    CONSTRAINT ck_estado_tarjeta_es_final CHECK (es_final IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. Sustituye el cálculo de operativa de la vista v_tarjeta_resumen.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.origen_cambio (
    cod_origen                  VARCHAR(20),
    descripcion                 VARCHAR(255) NOT NULL,
    puede_desbloquear           TINYINT(1) NOT NULL,
    CONSTRAINT pk_origen_cambio PRIMARY KEY (cod_origen),
    CONSTRAINT ck_origen_cambio_puede_desbloquear CHECK (puede_desbloquear IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. Solo OPERADOR y SEGURIDAD pueden desbloquear (RN-TAR-004).';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.evento_salida (
    id_evento                   BIGINT AUTO_INCREMENT,
    tipo_evento                 VARCHAR(30) NOT NULL,
    carga_json                  JSON NOT NULL,
    estado_envio                VARCHAR(25) NOT NULL
        CHECK (estado_envio IN ('PENDIENTE', 'ENVIADO', 'ERROR')),
    fecha_registro              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_envio                 DATETIME(6),
    id_tarjeta                  BINARY(16) NOT NULL,
    CONSTRAINT pk_evento_salida PRIMARY KEY (id_evento),
    CONSTRAINT ck_evento_salida_id_tarjeta CHECK ((ASCII(SUBSTR(id_tarjeta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_tarjeta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Bandeja de eventos que el Bus entrega al log centralizado de SEGURIDAD.';

-- ---------------------------------------------------------------------
CREATE TABLE tarjetas.tipo_evento_salida (
    tipo_evento                 VARCHAR(30),
    descripcion                 VARCHAR(255) NOT NULL,
    id_modulo_destino           SMALLINT NOT NULL,
    CONSTRAINT pk_tipo_evento_salida PRIMARY KEY (tipo_evento)
) ENGINE = InnoDB COMMENT = 'Tipos de evento hacia otros módulos y su destino (3FN).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.solicitud_credito (
    id_solicitud                BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    version_solicitud           SMALLINT DEFAULT 1 NOT NULL,
    monto_solicitado            DECIMAL(15,2) NOT NULL,
    moneda                      CHAR(3) NOT NULL,
    plazo_meses                 SMALLINT NOT NULL,
    condicion_pago_doble        TINYINT(1) DEFAULT FALSE NOT NULL,
    estado_solicitud            VARCHAR(25) NOT NULL,
    fecha_creacion              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    cod_cliente                 VARCHAR(12) NOT NULL,
    CONSTRAINT pk_solicitud_credito PRIMARY KEY (id_solicitud),
    CONSTRAINT ck_solicitud_credito_1 CHECK (monto_solicitado > 0),
    CONSTRAINT ck_solicitud_credito_2 CHECK (plazo_meses > 0),
    CONSTRAINT ck_solicitud_credito_id_solicitud CHECK ((ASCII(SUBSTR(id_solicitud, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_solicitud, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_solicitud_credito_condicion_pago_doble CHECK (condicion_pago_doble IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Solicitud de crédito; reemplaza la réplica SOLICITUD_CREDITO de EVALUACIÓN.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.historial_estado_solicitud (
    id_historial                BIGINT AUTO_INCREMENT,
    estado_nuevo                VARCHAR(25) NOT NULL,
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    actor                       VARCHAR(40) NOT NULL,
    motivo                      VARCHAR(255),
    id_solicitud                BINARY(16) NOT NULL,
    CONSTRAINT pk_historial_estado_solicitud PRIMARY KEY (id_historial),
    CONSTRAINT ck_historial_estado_solicitud_id_solicitud CHECK ((ASCII(SUBSTR(id_solicitud, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_solicitud, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Registro de cada cambio de estado de una solicitud.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.estado_solicitud (
    cod_estado                  VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    es_final                    TINYINT(1) NOT NULL,
    CONSTRAINT pk_estado_solicitud PRIMARY KEY (cod_estado),
    CONSTRAINT ck_estado_solicitud_es_final CHECK (es_final IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. Dominio usado por la solicitud y por su historial.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.garantia (
    id_garantia                 BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    tipo_garantia               VARCHAR(20) NOT NULL,
    descripcion                 VARCHAR(255),
    valor_referencial           DECIMAL(15,2) NOT NULL,
    moneda                      CHAR(3) NOT NULL,
    estado_garantia             VARCHAR(25) NOT NULL
        CHECK (estado_garantia IN ('REGISTRADA', 'EN_TASACION', 'CONSTITUIDA', 'LEVANTADA')),
    id_solicitud                BINARY(16) NOT NULL,
    CONSTRAINT pk_garantia PRIMARY KEY (id_garantia),
    CONSTRAINT ck_garantia_1 CHECK (valor_referencial > 0),
    CONSTRAINT ck_garantia_id_garantia CHECK ((ASCII(SUBSTR(id_garantia, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_garantia, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_garantia_id_solicitud CHECK ((ASCII(SUBSTR(id_solicitud, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_solicitud, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Bien o instrumento que respalda una solicitud (RN-SOL-007).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.tipo_garantia (
    cod_tipo_garantia           VARCHAR(20),
    descripcion                 VARCHAR(255) NOT NULL,
    CONSTRAINT pk_tipo_garantia PRIMARY KEY (cod_tipo_garantia)
) ENGINE = InnoDB COMMENT = 'Catálogo. Lista abierta en la fuente (p. ej.).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.fiador (
    id_fiador                   BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    id_persona_externa          VARCHAR(36) NOT NULL,
    tipo_documento              VARCHAR(10) NOT NULL,
    numero_documento            VARCHAR(12) NOT NULL,
    CONSTRAINT pk_fiador PRIMARY KEY (id_fiador),
    CONSTRAINT uk_fiador_1 UNIQUE (id_persona_externa),
    CONSTRAINT uk_fiador_2 UNIQUE (tipo_documento, numero_documento),
    CONSTRAINT ck_fiador_id_fiador CHECK ((ASCII(SUBSTR(id_fiador, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_fiador, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Persona externa que respalda solicitudes de crédito (antes FIADOR_REF).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.fiador_solicitud (
    id_fiador                   BINARY(16),
    id_solicitud                BINARY(16),
    id_verificacion             VARCHAR(36) NOT NULL,
    CONSTRAINT pk_fiador_solicitud PRIMARY KEY (id_fiador, id_solicitud),
    CONSTRAINT uk_fiador_solicitud_1 UNIQUE (id_verificacion),
    CONSTRAINT ck_fiador_solicitud_id_fiador CHECK ((ASCII(SUBSTR(id_fiador, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_fiador, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_fiador_solicitud_id_solicitud CHECK ((ASCII(SUBSTR(id_solicitud, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_solicitud, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Fiadores que respaldan cada solicitud (relación N:M RESPALDA).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.calendario_pago (
    id_calendario               BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    version                     SMALLINT NOT NULL,
    tipo_calendario             VARCHAR(25) NOT NULL
        CHECK (tipo_calendario IN ('PRELIMINAR', 'OFICIAL')),
    metodo_amortizacion         VARCHAR(20) NOT NULL,
    tasa_aplicada               DECIMAL(7,4) NOT NULL,
    fecha_generacion            DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    estado_calendario           VARCHAR(25) NOT NULL
        CHECK (estado_calendario IN ('VIGENTE', 'HISTORICO', 'DESCARTADO')),
    id_solicitud                BINARY(16) NOT NULL,
    CONSTRAINT pk_calendario_pago PRIMARY KEY (id_calendario),
    CONSTRAINT uk_calendario_pago_1 UNIQUE (id_solicitud, version),
    CONSTRAINT ck_calendario_pago_1 CHECK (tasa_aplicada >= 0),
    CONSTRAINT ck_calendario_pago_id_calendario CHECK ((ASCII(SUBSTR(id_calendario, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_calendario, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_calendario_pago_id_solicitud CHECK ((ASCII(SUBSTR(id_solicitud, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_solicitud, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Versión del calendario de pagos de una solicitud: PRELIMINAR (simulación) u OFICIAL.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.metodo_amortizacion (
    cod_metodo                  VARCHAR(20),
    descripcion                 VARCHAR(255) NOT NULL,
    CONSTRAINT pk_metodo_amortizacion PRIMARY KEY (cod_metodo)
) ENGINE = InnoDB COMMENT = 'Catálogo. Lista abierta en la fuente (p. ej.).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.cuota (
    id_calendario               BINARY(16),
    numero_cuota                SMALLINT,
    fecha_vencimiento           DATE NOT NULL,
    capital                     DECIMAL(15,2) NOT NULL,
    interes                     DECIMAL(15,2) NOT NULL,
    otros_conceptos             DECIMAL(15,2) DEFAULT 0 NOT NULL,
    saldo_capital               DECIMAL(15,2) NOT NULL,
    saldo_pendiente             DECIMAL(15,2) NOT NULL,
    estado_cuota                VARCHAR(25) NOT NULL,
    CONSTRAINT pk_cuota PRIMARY KEY (id_calendario, numero_cuota),
    CONSTRAINT ck_cuota_1 CHECK (numero_cuota > 0),
    CONSTRAINT ck_cuota_2 CHECK (capital >= 0),
    CONSTRAINT ck_cuota_3 CHECK (interes >= 0),
    CONSTRAINT ck_cuota_4 CHECK (otros_conceptos >= 0),
    CONSTRAINT ck_cuota_5 CHECK (saldo_pendiente >= 0),
    CONSTRAINT ck_cuota_id_calendario CHECK ((ASCII(SUBSTR(id_calendario, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_calendario, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Cuota del calendario; unifica la CUOTA de SOLICITUD con la de COBRANZA.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.estado_cuota (
    cod_estado                  VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    CONSTRAINT pk_estado_cuota PRIMARY KEY (cod_estado)
) ENGINE = InnoDB COMMENT = 'Catálogo. Catálogo pendiente de aprobación según COBRANZA.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.situacion_financiera (
    id_consulta                 BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    resultado_verificacion      VARCHAR(20) NOT NULL,
    ingreso_mensual             DECIMAL(15,2) NOT NULL,
    deuda_reportada             DECIMAL(15,2) NOT NULL,
    fecha_consulta              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    cod_cliente                 VARCHAR(12) NOT NULL,
    CONSTRAINT pk_situacion_financiera PRIMARY KEY (id_consulta),
    CONSTRAINT ck_situacion_financiera_id_consulta CHECK ((ASCII(SUBSTR(id_consulta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_consulta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Resultado de la verificación financiera del cliente, insumo del score.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.evaluacion (
    id_evaluacion               BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    ronda                       SMALLINT NOT NULL,
    fecha_evaluacion            DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    score_calculado             DECIMAL(6,2) NOT NULL,
    limite_aprobado             DECIMAL(15,2) NOT NULL,
    condiciones_propuestas      VARCHAR(300),
    observaciones               VARCHAR(500),
    id_solicitud                BINARY(16) NOT NULL,
    id_consulta                 BINARY(16) NOT NULL,
    id_regla                    VARCHAR(10) NOT NULL,
    id_analista                 VARCHAR(10),
    CONSTRAINT pk_evaluacion PRIMARY KEY (id_evaluacion),
    CONSTRAINT uk_evaluacion_1 UNIQUE (id_solicitud, ronda),
    CONSTRAINT ck_evaluacion_1 CHECK (limite_aprobado >= 0),
    CONSTRAINT ck_evaluacion_id_evaluacion CHECK ((ASCII(SUBSTR(id_evaluacion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_evaluacion, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_evaluacion_id_solicitud CHECK ((ASCII(SUBSTR(id_solicitud, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_solicitud, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_evaluacion_id_consulta CHECK ((ASCII(SUBSTR(id_consulta, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_consulta, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Evaluación crediticia de una solicitud; unifica EVALUACION y RESULTADO_EVALUACION.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.regla_evaluacion (
    id_regla                    VARCHAR(10),
    codigo_rn                   VARCHAR(20) NOT NULL,
    descripcion                 VARCHAR(255) NOT NULL,
    ratio_min                   DECIMAL(7,2),
    ratio_max                   DECIMAL(7,2),
    accion                      VARCHAR(12) NOT NULL,
    CONSTRAINT pk_regla_evaluacion PRIMARY KEY (id_regla),
    CONSTRAINT uk_regla_evaluacion_1 UNIQUE (codigo_rn),
    CONSTRAINT uk_regla_evaluacion_2 UNIQUE (ratio_min, ratio_max),
    CONSTRAINT ck_regla_evaluacion_1 CHECK (ratio_min IS NULL OR ratio_max IS NULL OR ratio_min < ratio_max)
) ENGINE = InnoDB COMMENT = 'Regla de decisión por tramo del ratio monto/límite (RN-EVA-002-P).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.resultado_crediticio (
    cod_resultado               VARCHAR(12),
    descripcion                 VARCHAR(255) NOT NULL,
    CONSTRAINT pk_resultado_crediticio PRIMARY KEY (cod_resultado)
) ENGINE = InnoDB COMMENT = 'Catálogo. APROBADO, OBSERVADO y RECHAZADO son el dominio oficial del Diccionario de Reglas.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.analista (
    id_analista                 VARCHAR(10),
    nombre                      VARCHAR(100) NOT NULL,
    codigo_empleado             VARCHAR(20) NOT NULL,
    CONSTRAINT pk_analista PRIMARY KEY (id_analista),
    CONSTRAINT uk_analista_1 UNIQUE (codigo_empleado)
) ENGINE = InnoDB COMMENT = 'Analista de crédito habilitado para la revisión manual.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.decision_analista (
    id_decision                 BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    decision                    VARCHAR(12) NOT NULL,
    comentario                  VARCHAR(500) NOT NULL,
    fecha_decision              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_evaluacion               BINARY(16) NOT NULL,
    CONSTRAINT pk_decision_analista PRIMARY KEY (id_decision),
    CONSTRAINT uk_decision_analista_1 UNIQUE (id_evaluacion),
    CONSTRAINT ck_decision_analista_id_decision CHECK ((ASCII(SUBSTR(id_decision, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_decision, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_decision_analista_id_evaluacion CHECK ((ASCII(SUBSTR(id_evaluacion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_evaluacion, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Decisión final de un analista sobre una evaluación OBSERVADA (RN-EVA-004).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.orden_desembolso (
    id_orden                    BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    codigo_orden                VARCHAR(24) NOT NULL,
    importe                     DECIMAL(15,2) NOT NULL,
    estado_orden                VARCHAR(25) NOT NULL,
    motivo_rechazo              VARCHAR(255),
    idempotency_key             BINARY(16) NOT NULL,
    request_hash                CHAR(64) NOT NULL,
    usuario_preparacion         VARCHAR(40) NOT NULL,
    usuario_confirmacion        VARCHAR(40),
    correlation_id              BINARY(16) NOT NULL,
    version_registro            INTEGER DEFAULT 0 NOT NULL,
    creado_en                   DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    actualizado_en              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_evaluacion               BINARY(16) NOT NULL,
    num_cuenta                  VARCHAR(20) NOT NULL,
    id_canal                    VARCHAR(5) NOT NULL,
    id_agencia                  VARCHAR(10),
    uuid_transaccion_abono      BINARY(16),
    CONSTRAINT pk_orden_desembolso PRIMARY KEY (id_orden),
    CONSTRAINT uk_orden_desembolso_1 UNIQUE (codigo_orden),
    CONSTRAINT uk_orden_desembolso_2 UNIQUE (idempotency_key),
    CONSTRAINT uk_orden_desembolso_3 UNIQUE (uuid_transaccion_abono),
    CONSTRAINT ck_orden_desembolso_1 CHECK (importe > 0),
    CONSTRAINT ck_orden_desembolso_id_orden CHECK ((ASCII(SUBSTR(id_orden, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_orden, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_orden_desembolso_idempotency_key CHECK ((ASCII(SUBSTR(idempotency_key, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(idempotency_key, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_orden_desembolso_correlation_id CHECK ((ASCII(SUBSTR(correlation_id, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(correlation_id, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_orden_desembolso_id_evaluacion CHECK ((ASCII(SUBSTR(id_evaluacion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_evaluacion, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_orden_desembolso_uuid_transaccion_abono CHECK ((ASCII(SUBSTR(uuid_transaccion_abono, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(uuid_transaccion_abono, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Intención, ejecución y resultado de un desembolso (antes des_orden).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.estado_orden (
    cod_estado                  VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    es_final                    TINYINT(1) NOT NULL,
    CONSTRAINT pk_estado_orden PRIMARY KEY (cod_estado),
    CONSTRAINT ck_estado_orden_es_final CHECK (es_final IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Catálogo. Base para la tabla de transiciones válidas (figura 2 de DESEMBOLSO).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.validacion_desembolso (
    id_validacion               BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    tipo_validacion             VARCHAR(15) NOT NULL,
    referencia_evidencia        VARCHAR(100) NOT NULL,
    resultado                   VARCHAR(25) NOT NULL
        CHECK (resultado IN ('APROBADA', 'RECHAZADA')),
    detalle                     VARCHAR(255),
    vence_en                    DATETIME(6),
    creado_en                   DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_orden                    BINARY(16) NOT NULL,
    CONSTRAINT pk_validacion_desembolso PRIMARY KEY (id_validacion),
    CONSTRAINT ck_validacion_desembolso_id_validacion CHECK ((ASCII(SUBSTR(id_validacion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_validacion, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_validacion_desembolso_id_orden CHECK ((ASCII(SUBSTR(id_orden, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_orden, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Evidencia de cada validación previa a la ejecución de la orden.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.tipo_validacion_desembolso (
    tipo_validacion             VARCHAR(15),
    descripcion                 VARCHAR(255) NOT NULL,
    id_modulo_proveedor         SMALLINT NOT NULL,
    CONSTRAINT pk_tipo_validacion_desembolso PRIMARY KEY (tipo_validacion)
) ENGINE = InnoDB COMMENT = 'Tipos de validación previa al desembolso y su proveedor (3FN).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.evento_entrega (
    id_evento                   BIGINT AUTO_INCREMENT,
    tipo_evento                 VARCHAR(60) NOT NULL
        CHECK (tipo_evento IN ('desembolso.confirmado', 'desembolso.revertido')),
    version_esquema             VARCHAR(10) NOT NULL,
    payload                     JSON NOT NULL,
    estado_entrega              VARCHAR(25) NOT NULL
        CHECK (estado_entrega IN ('PENDIENTE', 'ENVIADO', 'CONFIRMADO', 'FALLIDO')),
    intentos                    SMALLINT DEFAULT 0 NOT NULL,
    siguiente_intento           DATETIME(6),
    confirmacion_id             VARCHAR(60),
    ultimo_error                VARCHAR(255),
    creado_en                   DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    actualizado_en              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_orden                    BINARY(16) NOT NULL,
    CONSTRAINT pk_evento_entrega PRIMARY KEY (id_evento),
    CONSTRAINT ck_evento_entrega_id_orden CHECK ((ASCII(SUBSTR(id_orden, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_orden, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Bandeja de salida hacia Cobranza con reintentos.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.solicitud_reversion (
    id_reversion                BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    motivo                      VARCHAR(255) NOT NULL,
    solicitante_id              VARCHAR(40) NOT NULL,
    autorizacion_id             VARCHAR(60),
    estado_reversion            VARCHAR(25) NOT NULL
        CHECK (estado_reversion IN ('SOLICITADA', 'AUTORIZADA', 'CONFIRMADA', 'RECHAZADA')),
    idempotency_key             BINARY(16) NOT NULL,
    creado_en                   DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    actualizado_en              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_orden                    BINARY(16) NOT NULL,
    uuid_transaccion_extorno    BINARY(16),
    CONSTRAINT pk_solicitud_reversion PRIMARY KEY (id_reversion),
    CONSTRAINT uk_solicitud_reversion_1 UNIQUE (idempotency_key),
    CONSTRAINT uk_solicitud_reversion_2 UNIQUE (uuid_transaccion_extorno),
    CONSTRAINT ck_solicitud_reversion_id_reversion CHECK ((ASCII(SUBSTR(id_reversion, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_reversion, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_solicitud_reversion_idempotency_key CHECK ((ASCII(SUBSTR(idempotency_key, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(idempotency_key, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_solicitud_reversion_id_orden CHECK ((ASCII(SUBSTR(id_orden, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_orden, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_solicitud_reversion_uuid_transaccion_extorno CHECK ((ASCII(SUBSTR(uuid_transaccion_extorno, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(uuid_transaccion_extorno, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Solicitud de reversión de un desembolso; preparada pero sin uso en la Fase I.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.credito (
    cod_credito                 VARCHAR(20),
    estado_credito              VARCHAR(25) NOT NULL,
    id_orden                    BINARY(16) NOT NULL,
    id_calendario               BINARY(16) NOT NULL,
    CONSTRAINT pk_credito PRIMARY KEY (cod_credito),
    CONSTRAINT uk_credito_1 UNIQUE (id_orden),
    CONSTRAINT uk_credito_2 UNIQUE (id_calendario),
    CONSTRAINT ck_credito_id_orden CHECK ((ASCII(SUBSTR(id_orden, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_orden, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_credito_id_calendario CHECK ((ASCII(SUBSTR(id_calendario, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_calendario, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Préstamo ya desembolsado que debe cobrarse (RF-COB-015).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.estado_credito (
    cod_estado                  VARCHAR(25),
    descripcion                 VARCHAR(255) NOT NULL,
    CONSTRAINT pk_estado_credito PRIMARY KEY (cod_estado)
) ENGINE = InnoDB COMMENT = 'Catálogo. Catálogo pendiente de aprobación según COBRANZA.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.pago (
    id_pago                     BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    monto_pago                  DECIMAL(15,2) NOT NULL,
    referencia_transaccion      VARCHAR(40) NOT NULL,
    estado_confirmacion         VARCHAR(25) NOT NULL
        CHECK (estado_confirmacion IN ('PENDIENTE', 'CONFIRMADO', 'RECHAZADO')),
    cod_credito                 VARCHAR(20) NOT NULL,
    id_canal                    VARCHAR(5) NOT NULL,
    CONSTRAINT pk_pago PRIMARY KEY (id_pago),
    CONSTRAINT uk_pago_1 UNIQUE (referencia_transaccion),
    CONSTRAINT ck_pago_1 CHECK (monto_pago > 0),
    CONSTRAINT ck_pago_id_pago CHECK ((ASCII(SUBSTR(id_pago, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_pago, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Evento de pago realizado por el cliente.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.aplicacion_pago (
    id_pago                     BINARY(16),
    id_calendario               BINARY(16),
    numero_cuota                SMALLINT,
    monto_aplicado              DECIMAL(15,2) NOT NULL,
    CONSTRAINT pk_aplicacion_pago PRIMARY KEY (id_pago, id_calendario, numero_cuota),
    CONSTRAINT ck_aplicacion_pago_1 CHECK (monto_aplicado > 0),
    CONSTRAINT ck_aplicacion_pago_id_pago CHECK ((ASCII(SUBSTR(id_pago, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_pago, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_aplicacion_pago_id_calendario CHECK ((ASCII(SUBSTR(id_calendario, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_calendario, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Reparto de cada pago entre cuotas (relación N:M APLICA).';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.mora (
    id_mora                     BINARY(16) DEFAULT (CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1), CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7))),
    monto_calculado             DECIMAL(15,2) NOT NULL,
    fecha_calculo               DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    id_calendario               BINARY(16) NOT NULL,
    numero_cuota                SMALLINT NOT NULL,
    CONSTRAINT pk_mora PRIMARY KEY (id_mora),
    CONSTRAINT uk_mora_1 UNIQUE (id_calendario, numero_cuota, fecha_calculo),
    CONSTRAINT ck_mora_1 CHECK (monto_calculado >= 0),
    CONSTRAINT ck_mora_id_mora CHECK ((ASCII(SUBSTR(id_mora, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_mora, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_mora_id_calendario CHECK ((ASCII(SUBSTR(id_calendario, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(id_calendario, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Cada cálculo de interés moratorio que el CORE realiza para una cuota atrasada.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.evento_auditoria (
    id_evento                   BIGINT AUTO_INCREMENT,
    modulo_emisor               SMALLINT NOT NULL,
    id_entidad                  VARCHAR(36),
    numero_cuota                SMALLINT,
    accion                      VARCHAR(60) NOT NULL,
    resultado                   VARCHAR(40),
    actor                       VARCHAR(40) NOT NULL,
    correlation_id              BINARY(16) NOT NULL,
    ip_origen                   VARCHAR(45),
    detalle                     JSON,
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_evento_auditoria PRIMARY KEY (id_evento),
    CONSTRAINT ck_evento_auditoria_1 CHECK (numero_cuota IS NULL OR id_entidad IS NOT NULL),
    CONSTRAINT ck_evento_auditoria_correlation_id CHECK ((ASCII(SUBSTR(correlation_id, 7, 1)) >> 4) BETWEEN 1 AND 8 AND (ASCII(SUBSTR(correlation_id, 9, 1)) & 0xC0) = 0x80),
    CONSTRAINT ck_evento_auditoria_ip_origen CHECK (IS_IPV4(ip_origen) OR IS_IPV6(ip_origen))
) ENGINE = InnoDB COMMENT = 'Bitácora de solo inserción; unifica des_auditoria y EVENTO_AUDITORIA de COBRANZA.';

-- ---------------------------------------------------------------------
CREATE TABLE creditos.entidad_auditada (
    id_entidad                  VARCHAR(36),
    tipo_entidad                VARCHAR(25) NOT NULL
        CHECK (tipo_entidad IN ('ORDEN', 'CREDITO', 'PAGO', 'CUOTA')),
    CONSTRAINT pk_entidad_auditada PRIMARY KEY (id_entidad)
) ENGINE = InnoDB COMMENT = 'Registros auditables y su tipo (3FN).';

-- =====================================================================
-- Índices
-- =====================================================================
-- DECISIÓN: InnoDB exige un índice por clave foránea y lo crea si falta;
--   se crean aquí, con nombre, los mismos que en la rama main.
CREATE INDEX ix_cuenta_contable_codigo_padre ON core.cuenta_contable (codigo_padre);
CREATE INDEX ix_asiento_contable_moneda ON core.asiento_contable (moneda);
CREATE INDEX ix_detalle_asiento_codigo_contable ON core.detalle_asiento (codigo_contable);
CREATE INDEX ix_canal_validacion_tipo_validacion ON core.canal_validacion (tipo_validacion);
CREATE INDEX ix_limite_canal_moneda ON core.limite_canal (moneda);
CREATE INDEX ix_consumo_diario_id_canal ON core.consumo_diario (id_canal);
CREATE INDEX ix_terminal_id_canal ON core.terminal (id_canal);
CREATE INDEX ix_terminal_id_agencia ON core.terminal (id_agencia);
CREATE INDEX ix_cliente_estado_cliente ON clientes.cliente (estado_cliente);
CREATE INDEX ix_biometria_cliente_tipo_biometria ON clientes.biometria_cliente (tipo_biometria);
CREATE INDEX ix_biometria_cliente_cod_cliente ON clientes.biometria_cliente (cod_cliente);
CREATE INDEX ix_codigo_verificacion_tipo_contacto ON clientes.codigo_verificacion (tipo_contacto);
CREATE INDEX ix_codigo_verificacion_cod_cliente ON clientes.codigo_verificacion (cod_cliente);
CREATE INDEX ix_validacion_identidad_tipo_validacion ON clientes.validacion_identidad (tipo_validacion);
CREATE INDEX ix_validacion_identidad_cod_cliente ON clientes.validacion_identidad (cod_cliente);
CREATE INDEX ix_cuenta_ahorro_moneda ON cuentas.cuenta_ahorro (moneda);
CREATE INDEX ix_cuenta_ahorro_regimen ON cuentas.cuenta_ahorro (regimen);
CREATE INDEX ix_cuenta_ahorro_estado_cuenta ON cuentas.cuenta_ahorro (estado_cuenta);
CREATE INDEX ix_cuenta_ahorro_id_agencia ON cuentas.cuenta_ahorro (id_agencia);
CREATE INDEX ix_movimiento_tipo_operacion ON cuentas.movimiento (tipo_operacion);
CREATE INDEX ix_movimiento_id_canal ON cuentas.movimiento (id_canal);
CREATE INDEX ix_titularidad_num_cuenta ON cuentas.titularidad (num_cuenta);
CREATE INDEX ix_tarjeta_bin ON tarjetas.tarjeta (bin);
CREATE INDEX ix_tarjeta_estado_tarjeta ON tarjetas.tarjeta (estado_tarjeta);
CREATE INDEX ix_tarjeta_cod_cliente ON tarjetas.tarjeta (cod_cliente);
CREATE INDEX ix_tarjeta_cuenta_num_cuenta ON tarjetas.tarjeta_cuenta (num_cuenta);
CREATE INDEX ix_credencial_tipo_credencial ON tarjetas.credencial (tipo_credencial);
CREATE INDEX ix_matriz_token_id_tarjeta ON tarjetas.matriz_token (id_tarjeta);
CREATE INDEX ix_token_pago_proveedor_pasarela ON tarjetas.token_pago (proveedor_pasarela);
CREATE INDEX ix_token_pago_id_tarjeta ON tarjetas.token_pago (id_tarjeta);
CREATE INDEX ix_intento_autenticacion_tipo_credencial ON tarjetas.intento_autenticacion (tipo_credencial);
CREATE INDEX ix_intento_autenticacion_id_terminal ON tarjetas.intento_autenticacion (id_terminal);
CREATE INDEX ix_intento_autenticacion_id_canal ON tarjetas.intento_autenticacion (id_canal);
CREATE INDEX ix_autorizacion_tipo_operacion ON tarjetas.autorizacion (tipo_operacion);
CREATE INDEX ix_autorizacion_codigo_respuesta ON tarjetas.autorizacion (codigo_respuesta);
CREATE INDEX ix_autorizacion_id_terminal ON tarjetas.autorizacion (id_terminal);
CREATE INDEX ix_autorizacion_num_cuenta ON tarjetas.autorizacion (num_cuenta);
CREATE INDEX ix_autorizacion_id_canal ON tarjetas.autorizacion (id_canal);
CREATE INDEX ix_historial_estado_tarjeta_estado_nuevo ON tarjetas.historial_estado_tarjeta (estado_nuevo);
CREATE INDEX ix_historial_estado_tarjeta_origen ON tarjetas.historial_estado_tarjeta (origen);
CREATE INDEX ix_evento_salida_tipo_evento ON tarjetas.evento_salida (tipo_evento);
CREATE INDEX ix_evento_salida_id_tarjeta ON tarjetas.evento_salida (id_tarjeta);
CREATE INDEX ix_tipo_evento_salida_id_modulo_destino ON tarjetas.tipo_evento_salida (id_modulo_destino);
CREATE INDEX ix_solicitud_credito_moneda ON creditos.solicitud_credito (moneda);
CREATE INDEX ix_solicitud_credito_estado_solicitud ON creditos.solicitud_credito (estado_solicitud);
CREATE INDEX ix_solicitud_credito_cod_cliente ON creditos.solicitud_credito (cod_cliente);
CREATE INDEX ix_historial_estado_solicitud_estado_nuevo ON creditos.historial_estado_solicitud (estado_nuevo);
CREATE INDEX ix_historial_estado_solicitud_id_solicitud ON creditos.historial_estado_solicitud (id_solicitud);
CREATE INDEX ix_garantia_tipo_garantia ON creditos.garantia (tipo_garantia);
CREATE INDEX ix_garantia_moneda ON creditos.garantia (moneda);
CREATE INDEX ix_garantia_id_solicitud ON creditos.garantia (id_solicitud);
CREATE INDEX ix_fiador_solicitud_id_solicitud ON creditos.fiador_solicitud (id_solicitud);
CREATE INDEX ix_calendario_pago_metodo_amortizacion ON creditos.calendario_pago (metodo_amortizacion);
CREATE INDEX ix_cuota_estado_cuota ON creditos.cuota (estado_cuota);
CREATE INDEX ix_situacion_financiera_cod_cliente ON creditos.situacion_financiera (cod_cliente);
CREATE INDEX ix_evaluacion_id_consulta ON creditos.evaluacion (id_consulta);
CREATE INDEX ix_evaluacion_id_regla ON creditos.evaluacion (id_regla);
CREATE INDEX ix_evaluacion_id_analista ON creditos.evaluacion (id_analista);
CREATE INDEX ix_regla_evaluacion_accion ON creditos.regla_evaluacion (accion);
CREATE INDEX ix_decision_analista_decision ON creditos.decision_analista (decision);
CREATE INDEX ix_orden_desembolso_id_evaluacion ON creditos.orden_desembolso (id_evaluacion);
CREATE INDEX ix_orden_desembolso_num_cuenta ON creditos.orden_desembolso (num_cuenta);
CREATE INDEX ix_orden_desembolso_id_canal ON creditos.orden_desembolso (id_canal);
CREATE INDEX ix_orden_desembolso_id_agencia ON creditos.orden_desembolso (id_agencia);
CREATE INDEX ix_validacion_desembolso_tipo_validacion ON creditos.validacion_desembolso (tipo_validacion);
CREATE INDEX ix_validacion_desembolso_id_orden ON creditos.validacion_desembolso (id_orden);
CREATE INDEX ix_tipo_validacion_desembolso_id_modulo_proveedor ON creditos.tipo_validacion_desembolso (id_modulo_proveedor);
CREATE INDEX ix_evento_entrega_id_orden ON creditos.evento_entrega (id_orden);
CREATE INDEX ix_solicitud_reversion_id_orden ON creditos.solicitud_reversion (id_orden);
CREATE INDEX ix_credito_estado_credito ON creditos.credito (estado_credito);
CREATE INDEX ix_pago_cod_credito ON creditos.pago (cod_credito);
CREATE INDEX ix_pago_id_canal ON creditos.pago (id_canal);
CREATE INDEX ix_aplicacion_pago_id_calendario_numero_cuota ON creditos.aplicacion_pago (id_calendario, numero_cuota);
CREATE INDEX ix_evento_auditoria_modulo_emisor ON creditos.evento_auditoria (modulo_emisor);
CREATE INDEX ix_evento_auditoria_id_entidad ON creditos.evento_auditoria (id_entidad);
-- DECISIÓN: MySQL no tiene índices parciales. La unicidad parcial se
--   expresa con un índice funcional sobre CASE WHEN condición THEN columna
--   END: fuera de la condición vale NULL, y los NULL no chocan entre sí.
-- DECISIÓN: una sola matriz ACTIVA por tarjeta (RN-TAR-002); reemplaza tarjeta_si_activa.
CREATE UNIQUE INDEX ux_matriz_activa ON tarjetas.matriz_token ((CASE WHEN estado_matriz = 'ACTIVA' THEN id_tarjeta END));
-- DECISIÓN: una sola orden CONFIRMADA por aprobación; reemplaza credito_confirmado.
CREATE UNIQUE INDEX ux_orden_confirmada ON creditos.orden_desembolso ((CASE WHEN estado_orden = 'CONFIRMADA' THEN id_evaluacion END));
-- DECISIÓN: una sola cuenta principal por tarjeta.
CREATE UNIQUE INDEX ux_tarjeta_principal ON tarjetas.tarjeta_cuenta ((CASE WHEN es_principal = 1 THEN id_tarjeta END));
-- DECISIÓN: una sola plantilla vigente por cliente y tipo.
CREATE UNIQUE INDEX ux_biometria_vigente ON clientes.biometria_cliente ((CASE WHEN estado_activo = 1 THEN cod_cliente END), (CASE WHEN estado_activo = 1 THEN tipo_biometria END));
-- DECISIÓN: índices de consulta para las vistas y las consultas documentadas;
--   en los dos que en la rama main son parciales, la columna de la
--   condición encabeza el índice.
-- Estado de cuenta: movimientos de una cuenta por fecha.
CREATE INDEX ix_movimiento_cuenta_fecha ON cuentas.movimiento (num_cuenta, fecha_hora);
-- Consumo diario por tarjeta (v_consumo_diario, Tarjetas).
CREATE INDEX ix_autorizacion_tarjeta_fecha ON tarjetas.autorizacion (id_tarjeta, fecha_hora);
-- Intentos de una tarjeta por fecha (Tarjetas, C08).
CREATE INDEX ix_intento_tarjeta_fecha ON tarjetas.intento_autenticacion (id_tarjeta, fecha_hora);
-- Historial de una tarjeta (Tarjetas, C10).
CREATE INDEX ix_historial_tarjeta_fecha ON tarjetas.historial_estado_tarjeta (id_tarjeta, fecha_hora);
-- Recuperación de órdenes inciertas por estado y fecha (Desembolso, idx_orden_estado).
CREATE INDEX ix_orden_estado_fecha ON creditos.orden_desembolso (estado_orden, actualizado_en);
-- Bandeja de salida hacia SEGURIDAD: solo los eventos por enviar.
CREATE INDEX ix_evento_salida_pendiente ON tarjetas.evento_salida (estado_envio, fecha_registro);
-- Búsqueda de entregas pendientes hacia Cobranza (Desembolso).
CREATE INDEX ix_evento_entrega_pendiente ON creditos.evento_entrega (estado_entrega, siguiente_intento);
-- Reconstrucción de una operación completa desde la traza (Desembolso, idx_auditoria_correlation).
CREATE INDEX ix_evento_auditoria_correlacion ON creditos.evento_auditoria (correlation_id);

-- =====================================================================
-- Claves foráneas
-- =====================================================================
ALTER TABLE core.cuenta_contable ADD CONSTRAINT fk_cuenta_contable_1 FOREIGN KEY (codigo_padre)
    REFERENCES core.cuenta_contable (codigo_contable);
ALTER TABLE core.asiento_contable ADD CONSTRAINT fk_asiento_contable_1 FOREIGN KEY (moneda)
    REFERENCES core.moneda (cod_moneda);
ALTER TABLE core.asiento_contable ADD CONSTRAINT fk_asiento_contable_2 FOREIGN KEY (id_asiento_revertido)
    REFERENCES core.asiento_contable (id_asiento);
ALTER TABLE core.detalle_asiento ADD CONSTRAINT fk_detalle_asiento_1 FOREIGN KEY (id_asiento)
    REFERENCES core.asiento_contable (id_asiento);
ALTER TABLE core.detalle_asiento ADD CONSTRAINT fk_detalle_asiento_2 FOREIGN KEY (codigo_contable)
    REFERENCES core.cuenta_contable (codigo_contable);
ALTER TABLE core.canal_validacion ADD CONSTRAINT fk_canal_validacion_1 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE core.canal_validacion ADD CONSTRAINT fk_canal_validacion_2 FOREIGN KEY (tipo_validacion)
    REFERENCES tarjetas.tipo_credencial (tipo_credencial);
ALTER TABLE core.limite_canal ADD CONSTRAINT fk_limite_canal_1 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE core.limite_canal ADD CONSTRAINT fk_limite_canal_2 FOREIGN KEY (moneda)
    REFERENCES core.moneda (cod_moneda);
ALTER TABLE core.consumo_diario ADD CONSTRAINT fk_consumo_diario_1 FOREIGN KEY (num_cuenta)
    REFERENCES cuentas.cuenta_ahorro (num_cuenta);
ALTER TABLE core.consumo_diario ADD CONSTRAINT fk_consumo_diario_2 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE core.terminal ADD CONSTRAINT fk_terminal_1 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE core.terminal ADD CONSTRAINT fk_terminal_2 FOREIGN KEY (id_agencia)
    REFERENCES core.agencia (id_agencia);
ALTER TABLE clientes.cliente ADD CONSTRAINT fk_cliente_1 FOREIGN KEY (tipo_documento)
    REFERENCES clientes.tipo_documento (cod_tipo_documento);
ALTER TABLE clientes.cliente ADD CONSTRAINT fk_cliente_2 FOREIGN KEY (estado_cliente)
    REFERENCES clientes.estado_cliente (cod_estado);
ALTER TABLE clientes.cliente ADD CONSTRAINT fk_cliente_3 FOREIGN KEY (id_verificacion_captacion)
    REFERENCES clientes.verificacion_captacion (id_verificacion_captacion);
ALTER TABLE clientes.biometria_cliente ADD CONSTRAINT fk_biometria_cliente_1 FOREIGN KEY (tipo_biometria)
    REFERENCES clientes.tipo_biometria (cod_tipo_biometria);
ALTER TABLE clientes.biometria_cliente ADD CONSTRAINT fk_biometria_cliente_2 FOREIGN KEY (cod_cliente)
    REFERENCES clientes.cliente (cod_cliente);
ALTER TABLE clientes.codigo_verificacion ADD CONSTRAINT fk_codigo_verificacion_1 FOREIGN KEY (tipo_contacto)
    REFERENCES clientes.tipo_contacto (cod_tipo_contacto);
ALTER TABLE clientes.codigo_verificacion ADD CONSTRAINT fk_codigo_verificacion_2 FOREIGN KEY (cod_cliente)
    REFERENCES clientes.cliente (cod_cliente);
ALTER TABLE clientes.validacion_identidad ADD CONSTRAINT fk_validacion_identidad_1 FOREIGN KEY (tipo_validacion)
    REFERENCES clientes.tipo_validacion (cod_tipo_validacion);
ALTER TABLE clientes.validacion_identidad ADD CONSTRAINT fk_validacion_identidad_2 FOREIGN KEY (cod_cliente)
    REFERENCES clientes.cliente (cod_cliente);
ALTER TABLE cuentas.cuenta_ahorro ADD CONSTRAINT fk_cuenta_ahorro_1 FOREIGN KEY (moneda)
    REFERENCES core.moneda (cod_moneda);
ALTER TABLE cuentas.cuenta_ahorro ADD CONSTRAINT fk_cuenta_ahorro_2 FOREIGN KEY (regimen)
    REFERENCES cuentas.regimen_cuenta (cod_regimen);
ALTER TABLE cuentas.cuenta_ahorro ADD CONSTRAINT fk_cuenta_ahorro_3 FOREIGN KEY (estado_cuenta)
    REFERENCES cuentas.estado_cuenta (cod_estado);
ALTER TABLE cuentas.cuenta_ahorro ADD CONSTRAINT fk_cuenta_ahorro_4 FOREIGN KEY (id_agencia)
    REFERENCES core.agencia (id_agencia);
ALTER TABLE cuentas.movimiento ADD CONSTRAINT fk_movimiento_1 FOREIGN KEY (tipo_operacion)
    REFERENCES cuentas.tipo_operacion (tipo_operacion);
ALTER TABLE cuentas.movimiento ADD CONSTRAINT fk_movimiento_2 FOREIGN KEY (id_asiento)
    REFERENCES core.asiento_contable (id_asiento);
ALTER TABLE cuentas.movimiento ADD CONSTRAINT fk_movimiento_3 FOREIGN KEY (num_cuenta)
    REFERENCES cuentas.cuenta_ahorro (num_cuenta);
ALTER TABLE cuentas.movimiento ADD CONSTRAINT fk_movimiento_4 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE cuentas.titularidad ADD CONSTRAINT fk_titularidad_1 FOREIGN KEY (cod_cliente)
    REFERENCES clientes.cliente (cod_cliente);
ALTER TABLE cuentas.titularidad ADD CONSTRAINT fk_titularidad_2 FOREIGN KEY (num_cuenta)
    REFERENCES cuentas.cuenta_ahorro (num_cuenta);
ALTER TABLE tarjetas.tarjeta ADD CONSTRAINT fk_tarjeta_1 FOREIGN KEY (bin)
    REFERENCES tarjetas.bin_tarjeta (bin);
ALTER TABLE tarjetas.tarjeta ADD CONSTRAINT fk_tarjeta_2 FOREIGN KEY (estado_tarjeta)
    REFERENCES tarjetas.estado_tarjeta (cod_estado);
ALTER TABLE tarjetas.tarjeta ADD CONSTRAINT fk_tarjeta_3 FOREIGN KEY (cod_cliente)
    REFERENCES clientes.cliente (cod_cliente);
ALTER TABLE tarjetas.tarjeta_cuenta ADD CONSTRAINT fk_tarjeta_cuenta_1 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.tarjeta_cuenta ADD CONSTRAINT fk_tarjeta_cuenta_2 FOREIGN KEY (num_cuenta)
    REFERENCES cuentas.cuenta_ahorro (num_cuenta);
ALTER TABLE tarjetas.credencial ADD CONSTRAINT fk_credencial_1 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.credencial ADD CONSTRAINT fk_credencial_2 FOREIGN KEY (tipo_credencial)
    REFERENCES tarjetas.tipo_credencial (tipo_credencial);
ALTER TABLE tarjetas.matriz_token ADD CONSTRAINT fk_matriz_token_1 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.matriz_coordenada ADD CONSTRAINT fk_matriz_coordenada_1 FOREIGN KEY (id_matriz)
    REFERENCES tarjetas.matriz_token (id_matriz);
ALTER TABLE tarjetas.token_pago ADD CONSTRAINT fk_token_pago_1 FOREIGN KEY (proveedor_pasarela)
    REFERENCES tarjetas.pasarela_pago (id_pasarela);
ALTER TABLE tarjetas.token_pago ADD CONSTRAINT fk_token_pago_2 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.intento_autenticacion ADD CONSTRAINT fk_intento_autenticacion_1 FOREIGN KEY (tipo_credencial)
    REFERENCES tarjetas.tipo_credencial (tipo_credencial);
ALTER TABLE tarjetas.intento_autenticacion ADD CONSTRAINT fk_intento_autenticacion_2 FOREIGN KEY (id_terminal)
    REFERENCES core.terminal (id_terminal);
ALTER TABLE tarjetas.intento_autenticacion ADD CONSTRAINT fk_intento_autenticacion_3 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.intento_autenticacion ADD CONSTRAINT fk_intento_autenticacion_4 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_1 FOREIGN KEY (tipo_operacion)
    REFERENCES cuentas.tipo_operacion (tipo_operacion);
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_2 FOREIGN KEY (codigo_respuesta)
    REFERENCES tarjetas.codigo_respuesta (cod_respuesta);
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_3 FOREIGN KEY (id_terminal)
    REFERENCES core.terminal (id_terminal);
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_4 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_5 FOREIGN KEY (num_cuenta)
    REFERENCES cuentas.cuenta_ahorro (num_cuenta);
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_6 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_7 FOREIGN KEY (uuid_transaccion)
    REFERENCES cuentas.movimiento (uuid_transaccion);
ALTER TABLE tarjetas.historial_estado_tarjeta ADD CONSTRAINT fk_historial_estado_tarjeta_1 FOREIGN KEY (estado_nuevo)
    REFERENCES tarjetas.estado_tarjeta (cod_estado);
ALTER TABLE tarjetas.historial_estado_tarjeta ADD CONSTRAINT fk_historial_estado_tarjeta_2 FOREIGN KEY (origen)
    REFERENCES tarjetas.origen_cambio (cod_origen);
ALTER TABLE tarjetas.historial_estado_tarjeta ADD CONSTRAINT fk_historial_estado_tarjeta_3 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.evento_salida ADD CONSTRAINT fk_evento_salida_1 FOREIGN KEY (tipo_evento)
    REFERENCES tarjetas.tipo_evento_salida (tipo_evento);
ALTER TABLE tarjetas.evento_salida ADD CONSTRAINT fk_evento_salida_2 FOREIGN KEY (id_tarjeta)
    REFERENCES tarjetas.tarjeta (id_tarjeta);
ALTER TABLE tarjetas.tipo_evento_salida ADD CONSTRAINT fk_tipo_evento_salida_1 FOREIGN KEY (id_modulo_destino)
    REFERENCES core.modulo (id_modulo);
ALTER TABLE creditos.solicitud_credito ADD CONSTRAINT fk_solicitud_credito_1 FOREIGN KEY (moneda)
    REFERENCES core.moneda (cod_moneda);
ALTER TABLE creditos.solicitud_credito ADD CONSTRAINT fk_solicitud_credito_2 FOREIGN KEY (estado_solicitud)
    REFERENCES creditos.estado_solicitud (cod_estado);
ALTER TABLE creditos.solicitud_credito ADD CONSTRAINT fk_solicitud_credito_3 FOREIGN KEY (cod_cliente)
    REFERENCES clientes.cliente (cod_cliente);
ALTER TABLE creditos.historial_estado_solicitud ADD CONSTRAINT fk_historial_estado_solicitud_1 FOREIGN KEY (estado_nuevo)
    REFERENCES creditos.estado_solicitud (cod_estado);
ALTER TABLE creditos.historial_estado_solicitud ADD CONSTRAINT fk_historial_estado_solicitud_2 FOREIGN KEY (id_solicitud)
    REFERENCES creditos.solicitud_credito (id_solicitud);
ALTER TABLE creditos.garantia ADD CONSTRAINT fk_garantia_1 FOREIGN KEY (tipo_garantia)
    REFERENCES creditos.tipo_garantia (cod_tipo_garantia);
ALTER TABLE creditos.garantia ADD CONSTRAINT fk_garantia_2 FOREIGN KEY (moneda)
    REFERENCES core.moneda (cod_moneda);
ALTER TABLE creditos.garantia ADD CONSTRAINT fk_garantia_3 FOREIGN KEY (id_solicitud)
    REFERENCES creditos.solicitud_credito (id_solicitud);
ALTER TABLE creditos.fiador ADD CONSTRAINT fk_fiador_1 FOREIGN KEY (tipo_documento)
    REFERENCES clientes.tipo_documento (cod_tipo_documento);
ALTER TABLE creditos.fiador_solicitud ADD CONSTRAINT fk_fiador_solicitud_1 FOREIGN KEY (id_fiador)
    REFERENCES creditos.fiador (id_fiador);
ALTER TABLE creditos.fiador_solicitud ADD CONSTRAINT fk_fiador_solicitud_2 FOREIGN KEY (id_solicitud)
    REFERENCES creditos.solicitud_credito (id_solicitud);
ALTER TABLE creditos.calendario_pago ADD CONSTRAINT fk_calendario_pago_1 FOREIGN KEY (metodo_amortizacion)
    REFERENCES creditos.metodo_amortizacion (cod_metodo);
ALTER TABLE creditos.calendario_pago ADD CONSTRAINT fk_calendario_pago_2 FOREIGN KEY (id_solicitud)
    REFERENCES creditos.solicitud_credito (id_solicitud);
ALTER TABLE creditos.cuota ADD CONSTRAINT fk_cuota_1 FOREIGN KEY (id_calendario)
    REFERENCES creditos.calendario_pago (id_calendario);
ALTER TABLE creditos.cuota ADD CONSTRAINT fk_cuota_2 FOREIGN KEY (estado_cuota)
    REFERENCES creditos.estado_cuota (cod_estado);
ALTER TABLE creditos.situacion_financiera ADD CONSTRAINT fk_situacion_financiera_1 FOREIGN KEY (cod_cliente)
    REFERENCES clientes.cliente (cod_cliente);
ALTER TABLE creditos.evaluacion ADD CONSTRAINT fk_evaluacion_1 FOREIGN KEY (id_solicitud)
    REFERENCES creditos.solicitud_credito (id_solicitud);
ALTER TABLE creditos.evaluacion ADD CONSTRAINT fk_evaluacion_2 FOREIGN KEY (id_consulta)
    REFERENCES creditos.situacion_financiera (id_consulta);
ALTER TABLE creditos.evaluacion ADD CONSTRAINT fk_evaluacion_3 FOREIGN KEY (id_regla)
    REFERENCES creditos.regla_evaluacion (id_regla);
ALTER TABLE creditos.evaluacion ADD CONSTRAINT fk_evaluacion_4 FOREIGN KEY (id_analista)
    REFERENCES creditos.analista (id_analista);
ALTER TABLE creditos.regla_evaluacion ADD CONSTRAINT fk_regla_evaluacion_1 FOREIGN KEY (accion)
    REFERENCES creditos.resultado_crediticio (cod_resultado);
ALTER TABLE creditos.decision_analista ADD CONSTRAINT fk_decision_analista_1 FOREIGN KEY (decision)
    REFERENCES creditos.resultado_crediticio (cod_resultado);
ALTER TABLE creditos.decision_analista ADD CONSTRAINT fk_decision_analista_2 FOREIGN KEY (id_evaluacion)
    REFERENCES creditos.evaluacion (id_evaluacion);
ALTER TABLE creditos.orden_desembolso ADD CONSTRAINT fk_orden_desembolso_1 FOREIGN KEY (estado_orden)
    REFERENCES creditos.estado_orden (cod_estado);
ALTER TABLE creditos.orden_desembolso ADD CONSTRAINT fk_orden_desembolso_2 FOREIGN KEY (id_evaluacion)
    REFERENCES creditos.evaluacion (id_evaluacion);
ALTER TABLE creditos.orden_desembolso ADD CONSTRAINT fk_orden_desembolso_3 FOREIGN KEY (num_cuenta)
    REFERENCES cuentas.cuenta_ahorro (num_cuenta);
ALTER TABLE creditos.orden_desembolso ADD CONSTRAINT fk_orden_desembolso_4 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE creditos.orden_desembolso ADD CONSTRAINT fk_orden_desembolso_5 FOREIGN KEY (id_agencia)
    REFERENCES core.agencia (id_agencia);
ALTER TABLE creditos.orden_desembolso ADD CONSTRAINT fk_orden_desembolso_6 FOREIGN KEY (uuid_transaccion_abono)
    REFERENCES cuentas.movimiento (uuid_transaccion);
ALTER TABLE creditos.validacion_desembolso ADD CONSTRAINT fk_validacion_desembolso_1 FOREIGN KEY (tipo_validacion)
    REFERENCES creditos.tipo_validacion_desembolso (tipo_validacion);
ALTER TABLE creditos.validacion_desembolso ADD CONSTRAINT fk_validacion_desembolso_2 FOREIGN KEY (id_orden)
    REFERENCES creditos.orden_desembolso (id_orden);
ALTER TABLE creditos.tipo_validacion_desembolso ADD CONSTRAINT fk_tipo_validacion_desembolso_1 FOREIGN KEY (id_modulo_proveedor)
    REFERENCES core.modulo (id_modulo);
ALTER TABLE creditos.evento_entrega ADD CONSTRAINT fk_evento_entrega_1 FOREIGN KEY (id_orden)
    REFERENCES creditos.orden_desembolso (id_orden);
ALTER TABLE creditos.solicitud_reversion ADD CONSTRAINT fk_solicitud_reversion_1 FOREIGN KEY (id_orden)
    REFERENCES creditos.orden_desembolso (id_orden);
ALTER TABLE creditos.solicitud_reversion ADD CONSTRAINT fk_solicitud_reversion_2 FOREIGN KEY (uuid_transaccion_extorno)
    REFERENCES cuentas.movimiento (uuid_transaccion);
ALTER TABLE creditos.credito ADD CONSTRAINT fk_credito_1 FOREIGN KEY (estado_credito)
    REFERENCES creditos.estado_credito (cod_estado);
ALTER TABLE creditos.credito ADD CONSTRAINT fk_credito_2 FOREIGN KEY (id_orden)
    REFERENCES creditos.orden_desembolso (id_orden);
ALTER TABLE creditos.credito ADD CONSTRAINT fk_credito_3 FOREIGN KEY (id_calendario)
    REFERENCES creditos.calendario_pago (id_calendario);
ALTER TABLE creditos.pago ADD CONSTRAINT fk_pago_1 FOREIGN KEY (cod_credito)
    REFERENCES creditos.credito (cod_credito);
ALTER TABLE creditos.pago ADD CONSTRAINT fk_pago_2 FOREIGN KEY (id_canal)
    REFERENCES core.canal (id_canal);
ALTER TABLE creditos.aplicacion_pago ADD CONSTRAINT fk_aplicacion_pago_1 FOREIGN KEY (id_pago)
    REFERENCES creditos.pago (id_pago);
ALTER TABLE creditos.aplicacion_pago ADD CONSTRAINT fk_aplicacion_pago_2 FOREIGN KEY (id_calendario, numero_cuota)
    REFERENCES creditos.cuota (id_calendario, numero_cuota);
ALTER TABLE creditos.mora ADD CONSTRAINT fk_mora_1 FOREIGN KEY (id_calendario, numero_cuota)
    REFERENCES creditos.cuota (id_calendario, numero_cuota);
ALTER TABLE creditos.evento_auditoria ADD CONSTRAINT fk_evento_auditoria_1 FOREIGN KEY (modulo_emisor)
    REFERENCES core.modulo (id_modulo);
ALTER TABLE creditos.evento_auditoria ADD CONSTRAINT fk_evento_auditoria_2 FOREIGN KEY (id_entidad)
    REFERENCES creditos.entidad_auditada (id_entidad);
-- DECISIÓN: la cuenta afectada debe estar vinculada a la tarjeta (trigger de TARJETAS).
ALTER TABLE tarjetas.autorizacion ADD CONSTRAINT fk_autorizacion_vinculo FOREIGN KEY (id_tarjeta, num_cuenta)
    REFERENCES tarjetas.tarjeta_cuenta (id_tarjeta, num_cuenta);

-- >>> capa programable (procedimientos, funciones, triggers, vistas, evento y roles)
-- =====================================================================
-- Reglas, procedimientos, funciones, triggers y vistas (MySQL 8.4)
-- =====================================================================
-- Fuente: la regla de cada objeto se indica en su comentario; las de
--   Tarjetas y Desembolso conservan sus códigos (RN-*, ERR-TAR-*). Son las
--   mismas reglas de la rama main (PL/pgSQL); los comentarios «MySQL:»
--   explican dónde la implementación difiere.
-- DECISIÓN: los mensajes de error empiezan con la regla o el código de la
--   fuente (RN-*, ERR-TAR-*), o con un código BNA-* cuando la regla es una
--   decisión de este informe, para que la aplicación los traduzca sin leer
--   el texto.
-- DECISIÓN: el día de negocio se corta a las 00:00:00 de Arequipa
--   (America/Lima), como el tope diario de Tarjetas (RN-TOP-001).
-- MySQL: los triggers son por evento (INSERT, UPDATE o DELETE) y no
--   comparten una función: cada uno lleva su cuerpo. El generador agrega
--   DEFINER = bna_owner a cada objeto, que se ejecuta con los privilegios de
--   esa cuenta y no con los de quien lo invoca.

DELIMITER //

-- MySQL: MESSAGE_TEXT admite 128 caracteres y un texto más largo es otro
--   error (1648); todo rechazo pasa por aquí y se recorta.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.fallar(IN p_mensaje TEXT)
    COMMENT 'Rechaza la operación con el mensaje dado (a lo sumo 128 caracteres).'
BEGIN
    DECLARE v_mensaje VARCHAR(128) DEFAULT LEFT(p_mensaje, 128);
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_mensaje;
END //

-- MySQL: DATETIME no guarda zona; las marcas de tiempo se guardan en UTC y
--   CONVERT_TZ devuelve NULL si el servidor no tiene cargadas las tablas de
--   zonas horarias, lo que dejaría sin efecto el tope diario: se rechaza.
CREATE DEFINER = 'bna_owner'@'%' FUNCTION core.fn_fecha_negocio(p_momento DATETIME(6))
RETURNS DATE DETERMINISTIC CONTAINS SQL
    COMMENT 'Fecha de negocio (America/Lima) de una marca de tiempo en UTC.'
BEGIN
    DECLARE v_local DATETIME(6) DEFAULT CONVERT_TZ(p_momento, '+00:00', 'America/Lima');
    IF v_local IS NULL AND p_momento IS NOT NULL THEN
        CALL core.fallar('BNA-CONFIGURACION: el servidor no tiene las tablas de zonas horarias (America/Lima)');
    END IF;
    RETURN DATE(v_local);
END //

-- UUID versión 4 (aleatorio) para la aplicación y los procedimientos: MySQL
-- solo trae UUID() (versión 1, con la hora y la dirección del servidor).
-- Un valor por omisión de columna no puede llamar a una función almacenada,
-- por eso el DDL repite la misma expresión.
CREATE DEFINER = 'bna_owner'@'%' FUNCTION core.uuid_v4()
RETURNS BINARY(16) NOT DETERMINISTIC NO SQL
    COMMENT 'UUID versión 4 en BINARY(16).'
BEGIN
    RETURN CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1),
                  CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7));
END //

-- Comprueba la configuración de la que dependen las reglas. La llaman la
-- carga y las pruebas (L02); conviene llamarla al iniciar la aplicación.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.verificar_configuracion()
    COMMENT 'Rechaza si el servidor no tiene modo estricto, zona UTC, zonas horarias o el planificador de eventos.'
BEGIN
    IF FIND_IN_SET('STRICT_ALL_TABLES', @@GLOBAL.sql_mode) = 0 AND FIND_IN_SET('STRICT_TRANS_TABLES', @@GLOBAL.sql_mode) = 0 THEN
        CALL core.fallar(CONCAT('BNA-CONFIGURACION: el servidor no está en modo estricto (', @@GLOBAL.sql_mode, ')'));
    END IF;
    IF @@GLOBAL.time_zone <> '+00:00' THEN
        CALL core.fallar(CONCAT('BNA-CONFIGURACION: la zona del servidor es ', @@GLOBAL.time_zone, ', no +00:00'));
    END IF;
    IF CONVERT_TZ('2026-01-01 05:00:00', '+00:00', 'America/Lima') IS NULL THEN
        CALL core.fallar('BNA-CONFIGURACION: el servidor no tiene las tablas de zonas horarias');
    END IF;
    IF @@GLOBAL.event_scheduler <> 'ON' THEN
        CALL core.fallar('BNA-CONFIGURACION: el planificador de eventos está apagado (event_scheduler)');
    END IF;
    IF (SELECT DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = 'core') <> 'utf8mb4_0900_as_cs' THEN
        CALL core.fallar('BNA-CONFIGURACION: la base core no usa la collation utf8mb4_0900_as_cs');
    END IF;
    SELECT 'BNA-CONFIGURACION: correcta' AS resultado;
END //

-- ---------------------------------------------------------------------
-- Bitácoras e históricos de solo inserción.
-- Fuentes: CORE (asientos inmutables), Tarjetas (RN-SEG-002, RN-ATM-003),
--   Desembolso y Cobranza (bitácora de solo inserción).
-- MySQL: no hay triggers de TRUNCATE (en la rama main, un trigger por
--   sentencia lo rechaza). TRUNCATE exige el privilegio DROP, que bna_app no
--   tiene; bna_admin sí lo tiene y puede vaciar una bitácora (brecha G03).
--   La aplicación tampoco tiene UPDATE ni DELETE sobre estas tablas; los
--   triggers son la segunda línea, para las cuentas que sí los tienen.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.rechazar_cambio(IN p_codigo VARCHAR(30), IN p_tabla VARCHAR(80), IN p_operacion VARCHAR(10))
    COMMENT 'Rechaza un UPDATE o DELETE sobre una tabla de solo inserción.'
BEGIN
    CALL core.fallar(CONCAT(p_codigo, ': ', p_tabla, ' es de solo inserción (', p_operacion, ' no permitido)'));
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER core.tg_asiento_contable_solo_insercion_bu BEFORE UPDATE ON core.asiento_contable
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.asiento_contable', 'UPDATE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER core.tg_asiento_contable_solo_insercion_bd BEFORE DELETE ON core.asiento_contable
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.asiento_contable', 'DELETE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER core.tg_detalle_asiento_solo_insercion_bu BEFORE UPDATE ON core.detalle_asiento
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.detalle_asiento', 'UPDATE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER core.tg_detalle_asiento_solo_insercion_bd BEFORE DELETE ON core.detalle_asiento
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.detalle_asiento', 'DELETE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_intento_solo_insercion_bu BEFORE UPDATE ON tarjetas.intento_autenticacion
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.intento_autenticacion', 'UPDATE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_intento_solo_insercion_bd BEFORE DELETE ON tarjetas.intento_autenticacion
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.intento_autenticacion', 'DELETE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_historial_tarjeta_solo_insercion_bu BEFORE UPDATE ON tarjetas.historial_estado_tarjeta
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.historial_estado_tarjeta', 'UPDATE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_historial_tarjeta_solo_insercion_bd BEFORE DELETE ON tarjetas.historial_estado_tarjeta
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.historial_estado_tarjeta', 'DELETE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_autorizacion_sin_borrado BEFORE DELETE ON tarjetas.autorizacion
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.autorizacion', 'DELETE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_historial_solicitud_solo_insercion_bu BEFORE UPDATE ON creditos.historial_estado_solicitud
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'creditos.historial_estado_solicitud', 'UPDATE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_historial_solicitud_solo_insercion_bd BEFORE DELETE ON creditos.historial_estado_solicitud
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'creditos.historial_estado_solicitud', 'DELETE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_evento_auditoria_solo_insercion_bu BEFORE UPDATE ON creditos.evento_auditoria
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'creditos.evento_auditoria', 'UPDATE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_evento_auditoria_solo_insercion_bd BEFORE DELETE ON creditos.evento_auditoria
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'creditos.evento_auditoria', 'DELETE') //

-- ---------------------------------------------------------------------
-- Partida doble (CORE): un asiento tiene al menos una línea en el debe y
-- otra en el haber, y ambas sumas coinciden.
-- MySQL: no hay triggers diferidos hasta la confirmación (en la rama main,
--   un trigger de restricción diferido). El asiento se registra completo con
--   core.registrar_asiento, que valida las líneas antes de insertar nada;
--   bna_app no tiene INSERT sobre ASIENTO_CONTABLE ni DETALLE_ASIENTO, y como
--   son de solo inserción, nadie agrega líneas después. Una cuenta con INSERT
--   directo (bna_admin) puede saltarse el procedimiento (brecha G04);
--   core.v_asientos_descuadrados lo detecta.
-- MySQL: dentro de un procedimiento, cada sentencia que falla se deshace
--   sola, no la transacción. Si el llamador no tiene una transacción abierta,
--   el procedimiento abre la suya y la confirma o la deshace; si la tiene, usa
--   un punto de guardado. Así la cabecera nunca queda sin sus líneas. MySQL
--   no tiene @@in_transaction: RELEASE SAVEPOINT falla (1305) fuera de una
--   transacción, y eso basta para saberlo.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.registrar_asiento(
    IN p_id_asiento BINARY(16), IN p_numero VARCHAR(20), IN p_fecha_contable DATE, IN p_fecha_valor DATE,
    IN p_glosa VARCHAR(200), IN p_moneda CHAR(3), IN p_correlation_id BINARY(16),
    IN p_id_asiento_revertido BINARY(16), IN p_lineas JSON, OUT p_id BINARY(16))
    COMMENT 'Registra un asiento con todas sus líneas ([{partida, importe, cuenta}]) si cuadra.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_debe, v_haber DECIMAL(15,2);
    DECLARE v_nd, v_nh INT;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_asiento;
        RELEASE SAVEPOINT bna_asiento;
    END;
    SET p_id = coalesce(p_id_asiento, core.uuid_v4());
    SELECT coalesce(sum(CASE WHEN l.partida = 'DEBE' THEN l.importe END), 0),
           coalesce(sum(CASE WHEN l.partida = 'HABER' THEN l.importe END), 0),
           count(CASE WHEN l.partida = 'DEBE' THEN 1 END),
           count(CASE WHEN l.partida = 'HABER' THEN 1 END)
      INTO v_debe, v_haber, v_nd, v_nh
      FROM JSON_TABLE(coalesce(p_lineas, JSON_ARRAY()), '$[*]' COLUMNS (
               partida VARCHAR(25) PATH '$.partida', importe DECIMAL(15,2) PATH '$.importe')) l;
    IF v_nd = 0 OR v_nh = 0 OR v_debe <> v_haber THEN
        CALL core.fallar(CONCAT('BNA-PARTIDA-DOBLE: el asiento ', BIN_TO_UUID(p_id), ' no cuadra (debe ',
                                v_debe, ', haber ', v_haber, ')'));
    END IF;
    IF v_propia THEN
        START TRANSACTION;
    ELSE
        SAVEPOINT bna_asiento;
    END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN
                    ROLLBACK;
                ELSE
                    ROLLBACK TO SAVEPOINT bna_asiento;
                END IF;
            END;
            RESIGNAL;
        END;
        INSERT INTO core.asiento_contable (id_asiento, numero_asiento, fecha_contable, fecha_valor, glosa, moneda,
                                           correlation_id, id_asiento_revertido)
        VALUES (p_id, p_numero, p_fecha_contable, p_fecha_valor, p_glosa, p_moneda, p_correlation_id,
                p_id_asiento_revertido);
        INSERT INTO core.detalle_asiento (id_asiento, nro_linea, tipo_partida, importe, codigo_contable)
        SELECT p_id, l.n, l.partida, l.importe, l.cuenta
          FROM JSON_TABLE(p_lineas, '$[*]' COLUMNS (
                   n FOR ORDINALITY, partida VARCHAR(25) PATH '$.partida',
                   importe DECIMAL(15,2) PATH '$.importe', cuenta VARCHAR(20) PATH '$.cuenta')) l;
        IF v_propia THEN
            COMMIT;
        ELSE
            RELEASE SAVEPOINT bna_asiento;
        END IF;
    END;
END //

-- ---------------------------------------------------------------------
-- Movimientos de cuenta (Cuentas y CORE).
--   * La cuenta admite débitos o créditos según su estado (ESTADO_CUENTA).
--   * El asiento del movimiento está en la moneda de la cuenta.
--   * Un débito no supera el saldo disponible ni el tope diario del canal
--     (RN-TOP-001; BNA-CANAL sin fila para esa moneda, RN-BD-002 con la fila
--     deshabilitada).
--   * Los saldos y el consumo del día se actualizan en la misma transacción.
-- DECISIÓN: el tope y el saldo se comprometen una sola vez por operación.
--   Un débito con autorización de Tarjetas los compromete al autorizarse:
--   la autorización suma su monto a CONSUMO_DIARIO y lo descuenta del saldo
--   disponible. Su movimiento comparte el identificador de la operación
--   (uuid_transaccion = uuid_autorizacion, como en Tarjetas, RN-BUS-002),
--   solo descuenta el saldo contable y queda vinculado a la autorización. Un
--   débito sin autorización compromete ambos al registrarse.
-- DECISIÓN: toda operación que compromete el tope o el saldo bloquea antes
--   la fila de su cuenta (FOR UPDATE), de modo que dos operaciones
--   simultáneas sobre la misma cuenta se serializan.
-- MySQL: con REPEATABLE READ, una lectura sin bloqueo lee la instantánea de
--   la transacción, que puede ser anterior a lo que confirmó la operación por
--   la que se esperó. Por eso también el consumo del día se lee con
--   FOR UPDATE: una lectura con bloqueo lee siempre lo último confirmado.
-- DECISIÓN: sin fila en LIMITE_CANAL para el canal y la moneda, o con
--   habilitado = FALSE, el canal no opera en esa moneda; una fila con
--   monto nulo es un canal sin tope automático.
-- DECISIÓN: el movimiento es inmutable salvo el paso de APROBADO a
--   EXTORNADO; el extorno devuelve el consumo del día y el saldo se repone
--   con un movimiento EXTORNO.
-- ---------------------------------------------------------------------
-- Suma (o resta, con monto negativo) al consumo comprometido del día.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.consumo_sumar(IN p_cuenta VARCHAR(20), IN p_canal VARCHAR(5), IN p_fecha DATE,
                                    IN p_monto DECIMAL(15,2))
BEGIN
    INSERT INTO core.consumo_diario (num_cuenta, id_canal, fecha_corte, monto_acumulado)
    VALUES (p_cuenta, p_canal, p_fecha, GREATEST(p_monto, 0))
    ON DUPLICATE KEY UPDATE monto_acumulado = GREATEST(monto_acumulado + p_monto, 0);
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER cuentas.tg_movimiento_validar BEFORE INSERT ON cuentas.movimiento
FOR EACH ROW BEGIN
    DECLARE v_estado_cuenta VARCHAR(25);
    DECLARE v_moneda_cuenta, v_moneda CHAR(3);
    DECLARE v_disponible DECIMAL(15,2);
    DECLARE v_debito, v_credito BOOLEAN;
    DECLARE v_nat CHAR(1);
    DECLARE v_hay_limite BOOLEAN DEFAULT FALSE;
    DECLARE v_habilitado BOOLEAN;
    DECLARE v_tope, v_consumo DECIMAL(15,2);
    DECLARE v_hay_aut BOOLEAN DEFAULT FALSE;
    DECLARE v_aut_estado VARCHAR(25);
    DECLARE v_aut_trx BINARY(16);
    DECLARE v_aut_cuenta VARCHAR(20);
    DECLARE v_aut_monto DECIMAL(15,2);
    IF NEW.estado_transaccion <> 'APROBADO' THEN
        CALL core.fallar('BNA-MOVIMIENTO: un movimiento nuevo se registra APROBADO');
    END IF;
    -- Bloquea la cuenta: dos débitos simultáneos no pueden leer el mismo saldo.
    SELECT estado_cuenta, moneda, saldo_disponible INTO v_estado_cuenta, v_moneda_cuenta, v_disponible
      FROM cuentas.cuenta_ahorro WHERE num_cuenta = NEW.num_cuenta FOR UPDATE;
    SELECT permite_debito, permite_credito INTO v_debito, v_credito
      FROM cuentas.estado_cuenta WHERE cod_estado = v_estado_cuenta;
    SELECT naturaleza INTO v_nat FROM cuentas.tipo_operacion WHERE tipo_operacion = NEW.tipo_operacion;
    IF v_nat = 'N' THEN
        CALL core.fallar(CONCAT('BNA-MOVIMIENTO: ', NEW.tipo_operacion, ' no mueve saldo y no genera movimiento'));
    END IF;
    IF (v_nat = 'D' AND NOT v_debito) OR (v_nat = 'C' AND NOT v_credito) THEN
        CALL core.fallar(CONCAT('BNA-ESTADO-CUENTA: la cuenta ', NEW.num_cuenta, ' (estado ', v_estado_cuenta,
                                ') no admite ', IF(v_nat = 'D', 'débitos', 'créditos')));
    END IF;
    SELECT moneda INTO v_moneda FROM core.asiento_contable WHERE id_asiento = NEW.id_asiento;
    IF NOT (v_moneda <=> v_moneda_cuenta) THEN
        CALL core.fallar(CONCAT('BNA-MONEDA: el asiento está en ', coalesce(v_moneda, '(sin asiento)'),
                                ' y la cuenta ', NEW.num_cuenta, ' en ', v_moneda_cuenta));
    END IF;
    IF v_nat = 'D' THEN
        -- Movimiento de una autorización: el tope y el saldo disponible ya se
        -- comprometieron al autorizar.
        SELECT TRUE, estado_autorizacion, uuid_transaccion, num_cuenta, monto
          INTO v_hay_aut, v_aut_estado, v_aut_trx, v_aut_cuenta, v_aut_monto
          FROM tarjetas.autorizacion WHERE uuid_autorizacion = NEW.uuid_transaccion FOR UPDATE;
        IF v_hay_aut THEN
            IF v_aut_estado NOT IN ('AUTORIZADA', 'DISPENSADA') OR v_aut_trx IS NOT NULL
               OR v_aut_cuenta <> NEW.num_cuenta OR v_aut_monto <> NEW.monto THEN
                CALL core.fallar(CONCAT('BNA-MOVIMIENTO: el movimiento no corresponde a la autorización ',
                                        BIN_TO_UUID(NEW.uuid_transaccion), ' (', v_aut_estado, ')'));
            END IF;
        ELSE
            IF v_disponible < NEW.monto THEN
                CALL core.fallar(CONCAT('BNA-SALDO: saldo disponible insuficiente en ', NEW.num_cuenta,
                                        ' (', v_disponible, ' < ', NEW.monto, ')'));
            END IF;
            IF NEW.id_canal IS NOT NULL THEN
                SELECT TRUE, habilitado, monto_maximo_diario INTO v_hay_limite, v_habilitado, v_tope
                  FROM core.limite_canal WHERE id_canal = NEW.id_canal AND moneda = v_moneda_cuenta;
                -- Sin fila en core.limite_canal el canal no opera en esa moneda; «sin
                -- tope» es una fila con monto nulo (ventanilla, Tarjetas, tabla 4).
                IF NOT v_hay_limite THEN
                    CALL core.fallar(CONCAT('BNA-CANAL: el canal ', NEW.id_canal, ' no opera en ', v_moneda_cuenta));
                END IF;
                IF NOT v_habilitado THEN
                    CALL core.fallar(CONCAT('RN-BD-002: el canal ', NEW.id_canal, ' no opera en ', v_moneda_cuenta));
                END IF;
                IF v_tope IS NOT NULL THEN
                    SELECT coalesce(max(monto_acumulado), 0) INTO v_consumo FROM core.consumo_diario
                     WHERE num_cuenta = NEW.num_cuenta AND id_canal = NEW.id_canal
                       AND fecha_corte = core.fn_fecha_negocio(NEW.fecha_hora)
                       FOR UPDATE;
                    IF v_consumo + NEW.monto > v_tope THEN
                        CALL core.fallar(CONCAT('RN-TOP-001: tope diario de ', NEW.id_canal, ' excedido en ',
                                                NEW.num_cuenta, ' (consumido ', v_consumo, ', tope ', v_tope,
                                                ', solicitado ', NEW.monto, ')'));
                    END IF;
                END IF;
            END IF;
        END IF;
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER cuentas.tg_movimiento_aplicar_ai AFTER INSERT ON cuentas.movimiento
FOR EACH ROW BEGIN
    DECLARE v_nat CHAR(1);
    SELECT naturaleza INTO v_nat FROM cuentas.tipo_operacion WHERE tipo_operacion = NEW.tipo_operacion;
    IF v_nat = 'D' AND EXISTS (SELECT 1 FROM tarjetas.autorizacion WHERE uuid_autorizacion = NEW.uuid_transaccion) THEN
        -- Movimiento de una autorización: el disponible ya se descontó.
        UPDATE cuentas.cuenta_ahorro SET saldo_contable = saldo_contable - NEW.monto
         WHERE num_cuenta = NEW.num_cuenta;
        UPDATE tarjetas.autorizacion SET uuid_transaccion = NEW.uuid_transaccion
         WHERE uuid_autorizacion = NEW.uuid_transaccion;
    ELSE
        UPDATE cuentas.cuenta_ahorro
           SET saldo_contable   = saldo_contable   + IF(v_nat = 'D', -NEW.monto, NEW.monto),
               saldo_disponible = saldo_disponible + IF(v_nat = 'D', -NEW.monto, NEW.monto)
         WHERE num_cuenta = NEW.num_cuenta;
        IF v_nat = 'D' AND NEW.id_canal IS NOT NULL THEN
            CALL core.consumo_sumar(NEW.num_cuenta, NEW.id_canal, core.fn_fecha_negocio(NEW.fecha_hora), NEW.monto);
        END IF;
    END IF;
END //

-- Extorno: el monto deja de contar para el tope del día y el canal en que se
-- comprometió (Tarjetas, C07): los de su autorización, si la tiene, aunque
-- el movimiento se haya registrado otro día.
CREATE DEFINER = 'bna_owner'@'%' TRIGGER cuentas.tg_movimiento_aplicar_au AFTER UPDATE ON cuentas.movimiento
FOR EACH ROW BEGIN
    DECLARE v_nat CHAR(1);
    DECLARE v_hay_aut BOOLEAN DEFAULT FALSE;
    DECLARE v_canal VARCHAR(5);
    DECLARE v_momento DATETIME(6);
    IF NOT (NEW.estado_transaccion <=> OLD.estado_transaccion) THEN
        SELECT naturaleza INTO v_nat FROM cuentas.tipo_operacion WHERE tipo_operacion = NEW.tipo_operacion;
        IF v_nat = 'D' THEN
            SELECT TRUE, coalesce(a.id_canal, t.id_canal), a.fecha_hora INTO v_hay_aut, v_canal, v_momento
              FROM tarjetas.autorizacion a LEFT JOIN core.terminal t ON t.id_terminal = a.id_terminal
             WHERE a.uuid_autorizacion = NEW.uuid_transaccion;
            IF NOT v_hay_aut THEN
                SET v_canal = NEW.id_canal, v_momento = NEW.fecha_hora;
            END IF;
            IF v_canal IS NOT NULL THEN
                CALL core.consumo_sumar(NEW.num_cuenta, v_canal, core.fn_fecha_negocio(v_momento), -NEW.monto);
            END IF;
        END IF;
    END IF;
END //

-- MySQL: además, bna_app solo puede actualizar estado_transaccion.
CREATE DEFINER = 'bna_owner'@'%' TRIGGER cuentas.tg_movimiento_inmutable_bu BEFORE UPDATE ON cuentas.movimiento
FOR EACH ROW BEGIN
    IF NOT (OLD.estado_transaccion = 'APROBADO' AND NEW.estado_transaccion = 'EXTORNADO')
       OR NOT (NEW.uuid_transaccion <=> OLD.uuid_transaccion AND NEW.tipo_operacion <=> OLD.tipo_operacion
               AND NEW.monto <=> OLD.monto AND NEW.glosa <=> OLD.glosa AND NEW.fecha_hora <=> OLD.fecha_hora
               AND NEW.id_asiento <=> OLD.id_asiento AND NEW.num_cuenta <=> OLD.num_cuenta
               AND NEW.id_canal <=> OLD.id_canal) THEN
        CALL core.fallar('BNA-MOVIMIENTO: solo se admite el paso de APROBADO a EXTORNADO');
    END IF;
END //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER cuentas.tg_movimiento_inmutable_bd BEFORE DELETE ON cuentas.movimiento
FOR EACH ROW CALL core.fallar('BNA-MOVIMIENTO: un movimiento no se borra; se extorna') //

-- ---------------------------------------------------------------------
-- Tarjetas: emisión (trg_tarjeta_bi y trg_tarjeta_ai de Tarjetas).
--   * Solo se emite a un cliente ACTIVO (RF-TAR-005, ERR-TAR-001).
--   * La emisión queda en el historial y en la bandeja hacia SEGURIDAD
--     (RN-SEG-002).
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_tarjeta_emitir BEFORE INSERT ON tarjetas.tarjeta
FOR EACH ROW BEGIN
    DECLARE v_estado_cliente VARCHAR(25);
    SELECT estado_cliente INTO v_estado_cliente FROM clientes.cliente WHERE cod_cliente = NEW.cod_cliente;
    IF NOT (v_estado_cliente <=> 'ACTIVO') THEN
        CALL core.fallar(CONCAT('ERR-TAR-001: no se emite tarjeta al cliente ', NEW.cod_cliente, ' en estado ',
                                coalesce(v_estado_cliente, '(inexistente)')));
    END IF;
    IF NEW.estado_tarjeta NOT IN ('PENDIENTE_ACTIVACION', 'ACTIVA') THEN
        CALL core.fallar(CONCAT('ERR-TAR-002: una tarjeta se emite PENDIENTE_ACTIVACION o ACTIVA, no ', NEW.estado_tarjeta));
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_tarjeta_emitida AFTER INSERT ON tarjetas.tarjeta
FOR EACH ROW BEGIN
    INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
    VALUES (NEW.estado_tarjeta, 'Emisión de la tarjeta', 'SISTEMA', NEW.id_tarjeta);
    INSERT INTO tarjetas.evento_salida (tipo_evento, carga_json, estado_envio, id_tarjeta)
    VALUES ('EMISION_TARJETA',
            JSON_OBJECT('id_tarjeta', BIN_TO_UUID(NEW.id_tarjeta), 'cod_cliente', NEW.cod_cliente,
                        'bin', NEW.bin, 'ultimos4', NEW.ultimos4, 'estado', NEW.estado_tarjeta),
            'PENDIENTE', NEW.id_tarjeta);
END //

-- El estado solo cambia registrando el historial (trigger siguiente).
-- MySQL: la marca que deja el historial es una variable de sesión con el
--   identificador de la tarjeta (en la rama main, set_config local a la
--   transacción). bna_app no tiene UPDATE sobre estado_tarjeta: el trigger
--   es la segunda línea, para las cuentas que sí lo tienen.
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_tarjeta_estado_via_historial BEFORE UPDATE ON tarjetas.tarjeta
FOR EACH ROW BEGIN
    IF NOT (NEW.estado_tarjeta <=> OLD.estado_tarjeta) AND NOT (@bna_cambio_por_historial <=> NEW.id_tarjeta) THEN
        CALL core.fallar(CONCAT('RN-SEG-002: el estado de la tarjeta ', BIN_TO_UUID(OLD.id_tarjeta),
                                ' solo cambia registrando el historial'));
    END IF;
END //

-- ---------------------------------------------------------------------
-- Tarjetas: cambios de estado (trg_tarjeta_bu y trg_tarjeta_au de Tarjetas).
--   * La CANCELADA no cambia; la VENCIDA solo se cancela (RN-TAR-003,
--     ERR-TAR-002).
--   * El desbloqueo lo hace un origen autorizado: OPERADOR o SEGURIDAD
--     (RN-TAR-004, ERR-TAR-004); al desbloquear, los intentos vuelven a 0.
--   * Cada cambio se avisa a SEGURIDAD por la bandeja de salida (RN-SEG-002).
-- DECISIÓN: el primer registro del historial de una tarjeta es su emisión y
--   no se valida como transición.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_historial_validar BEFORE INSERT ON tarjetas.historial_estado_tarjeta
FOR EACH ROW BEGIN
    DECLARE v_actual VARCHAR(25);
    DECLARE v_final BOOLEAN;
    -- MySQL: el registro de emisión lo inserta el trigger de TARJETA, y una
    --   lectura FOR UPDATE de la tabla que se está insertando es el error
    --   1442; la fila ya está bloqueada por esa inserción, así que solo los
    --   cambios posteriores bloquean la tarjeta.
    IF NOT EXISTS (SELECT 1 FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = NEW.id_tarjeta) THEN
        SELECT estado_tarjeta INTO v_actual FROM tarjetas.tarjeta WHERE id_tarjeta = NEW.id_tarjeta;
        IF NOT (NEW.estado_nuevo <=> v_actual) THEN
            CALL core.fallar(CONCAT('RN-SEG-002: el primer registro del historial debe ser la emisión en estado ', v_actual));
        END IF;
    ELSE
        SELECT t.estado_tarjeta, e.es_final INTO v_actual, v_final
          FROM tarjetas.tarjeta t JOIN tarjetas.estado_tarjeta e ON e.cod_estado = t.estado_tarjeta
         WHERE t.id_tarjeta = NEW.id_tarjeta
           FOR UPDATE OF t;
        IF NEW.estado_nuevo = v_actual THEN
            CALL core.fallar(CONCAT('ERR-TAR-002: la tarjeta ', BIN_TO_UUID(NEW.id_tarjeta), ' ya está ', v_actual));
        END IF;
        IF v_final THEN
            CALL core.fallar(CONCAT('ERR-TAR-002: la tarjeta ', BIN_TO_UUID(NEW.id_tarjeta), ' está ', v_actual,
                                    ' y no cambia de estado'));
        END IF;
        IF v_actual = 'VENCIDA' AND NEW.estado_nuevo <> 'CANCELADA' THEN
            CALL core.fallar(CONCAT('ERR-TAR-002: una tarjeta VENCIDA solo se cancela (se pidió ', NEW.estado_nuevo, ')'));
        END IF;
        IF NEW.estado_nuevo = 'PENDIENTE_ACTIVACION' THEN
            CALL core.fallar('ERR-TAR-002: una tarjeta no vuelve a PENDIENTE_ACTIVACION');
        END IF;
        IF v_actual IN ('BLOQUEADA', 'RETENIDA') AND NEW.estado_nuevo = 'ACTIVA'
           AND NOT (SELECT puede_desbloquear FROM tarjetas.origen_cambio WHERE cod_origen = NEW.origen) THEN
            CALL core.fallar(CONCAT('ERR-TAR-004: el origen ', NEW.origen, ' no puede desbloquear la tarjeta ',
                                    BIN_TO_UUID(NEW.id_tarjeta)));
        END IF;
    END IF;
    SET @bna_estado_anterior_tarjeta = v_actual;
END //

-- MySQL: una variable de sesión no se deshace con la transacción; el
--   manejador la limpia si algo falla antes de terminar.
-- MySQL: el estado anterior es el que el trigger BEFORE leyó con bloqueo. Con
--   REPEATABLE READ, una lectura aquí vería la instantánea de la transacción y
--   podría no aplicar un cambio que el historial sí registra.
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_historial_aplicar AFTER INSERT ON tarjetas.historial_estado_tarjeta
FOR EACH ROW BEGIN
    DECLARE v_anterior VARCHAR(25);
    DECLARE v_tipo VARCHAR(30);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET @bna_cambio_por_historial = NULL;
        RESIGNAL;
    END;
    SET v_anterior = @bna_estado_anterior_tarjeta;
    SET @bna_estado_anterior_tarjeta = NULL;
    -- Registro de emisión: la tarjeta ya tiene ese estado.
    IF NOT (v_anterior <=> NEW.estado_nuevo) THEN
        SET @bna_cambio_por_historial = NEW.id_tarjeta;
        UPDATE tarjetas.tarjeta SET estado_tarjeta = NEW.estado_nuevo WHERE id_tarjeta = NEW.id_tarjeta;
        SET @bna_cambio_por_historial = NULL;
        IF v_anterior IN ('BLOQUEADA', 'RETENIDA') AND NEW.estado_nuevo = 'ACTIVA' THEN
            UPDATE tarjetas.credencial SET intentos_fallidos = 0 WHERE id_tarjeta = NEW.id_tarjeta;
            UPDATE tarjetas.matriz_token SET intentos_fallidos = 0
             WHERE id_tarjeta = NEW.id_tarjeta AND estado_matriz = 'ACTIVA';
        END IF;
        SET v_tipo = IF(@bna_bloqueo_por_intentos <=> NEW.id_tarjeta, 'BLOQUEO_POR_INTENTOS', 'CAMBIO_ESTADO_TARJETA');
        INSERT INTO tarjetas.evento_salida (tipo_evento, carga_json, estado_envio, id_tarjeta)
        VALUES (v_tipo,
                JSON_OBJECT('id_tarjeta', BIN_TO_UUID(NEW.id_tarjeta), 'estado_anterior', v_anterior,
                            'estado_nuevo', NEW.estado_nuevo, 'origen', NEW.origen,
                            'motivo', NEW.motivo, 'id_historial', NEW.id_historial),
                'PENDIENTE', NEW.id_tarjeta);
    END IF;
END //

-- ---------------------------------------------------------------------
-- Tarjetas: intentos de autenticación (trg_intento_ai de Tarjetas).
--   * Cada fallo suma un intento a la credencial o a la matriz activa; al
--     tercero consecutivo se bloquea la tarjeta (RN-TAR-004). Un intento
--     exitoso reinicia el contador.
-- MySQL: no hay UPDATE ... RETURNING; el contador se lee después de
--   actualizarlo. En un UPDATE de MySQL, cada asignación ve el valor que dejó
--   la anterior: por eso el estado de la matriz se asigna antes que el
--   contador.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_intento_contar AFTER INSERT ON tarjetas.intento_autenticacion
FOR EACH ROW BEGIN
    DECLARE v_intentos SMALLINT;
    DECLARE v_matriz BINARY(16);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET @bna_bloqueo_por_intentos = NULL;
        RESIGNAL;
    END;
    IF NEW.tipo_credencial IN ('PIN_ATM', 'CLAVE_WEB') THEN
        UPDATE tarjetas.credencial
           SET intentos_fallidos = IF(NEW.resultado = 'FALLIDO', LEAST(intentos_fallidos + 1, 3), 0)
         WHERE id_tarjeta = NEW.id_tarjeta AND tipo_credencial = NEW.tipo_credencial;
        SELECT intentos_fallidos INTO v_intentos FROM tarjetas.credencial
         WHERE id_tarjeta = NEW.id_tarjeta AND tipo_credencial = NEW.tipo_credencial;
    ELSEIF NEW.tipo_credencial = 'TOKEN_MATRIZ' THEN
        SELECT id_matriz INTO v_matriz FROM tarjetas.matriz_token
         WHERE id_tarjeta = NEW.id_tarjeta AND estado_matriz = 'ACTIVA' FOR UPDATE;
        UPDATE tarjetas.matriz_token
           SET estado_matriz = IF(NEW.resultado = 'FALLIDO' AND intentos_fallidos + 1 >= 3, 'BLOQUEADA', estado_matriz),
               intentos_fallidos = IF(NEW.resultado = 'FALLIDO', LEAST(intentos_fallidos + 1, 3), 0)
         WHERE id_matriz = v_matriz;
        SELECT intentos_fallidos INTO v_intentos FROM tarjetas.matriz_token WHERE id_matriz = v_matriz;
    END IF;
    IF NEW.resultado = 'FALLIDO' AND v_intentos >= 3
       AND (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = NEW.id_tarjeta) = 'ACTIVA' THEN
        SET @bna_bloqueo_por_intentos = NEW.id_tarjeta;
        INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
        VALUES ('BLOQUEADA', CONCAT('Tercer intento fallido de ', NEW.tipo_credencial), 'SISTEMA', NEW.id_tarjeta);
        SET @bna_bloqueo_por_intentos = NULL;
    END IF;
END //

-- ---------------------------------------------------------------------
-- Tarjetas: autorizaciones (trg_autorizacion_bi/bu y
-- sp_validar_reglas_autorizacion de Tarjetas).
--   * Para autorizar, la tarjeta está operativa y vigente (RN-TAR-003,
--     ERR-TAR-003), el canal y la terminal están activos, la cuenta admite
--     débitos y, en cajero, está habilitada y no es mancomunada conjunta
--     (RN-ATM-005, ERR-TAR-008).
--   * Un débito no supera el saldo ni el tope del día (RN-TOP-001,
--     ERR-TAR-007) y el canal opera en la moneda (RN-BD-002, ERR-TAR-006).
--   * La secuencia de estados está controlada (RN-ATM-007).
-- DECISIÓN: secuencia de estados: INICIADA -> AUTORIZADA | RECHAZADA;
--   AUTORIZADA -> DISPENSADA | PENDIENTE_REVERSION | EXTORNADA;
--   DISPENSADA -> PENDIENTE_REVERSION | EXTORNADA;
--   PENDIENTE_REVERSION -> EXTORNADA. RECHAZADA y EXTORNADA son finales.
-- DECISIÓN: las reglas se validan cada vez que la autorización llega a
--   AUTORIZADA, sea al insertarla o al actualizarla desde INICIADA, con la
--   cuenta bloqueada; en ese momento se compromete el tope y se retiene el
--   monto en el saldo disponible. Si se extorna antes de registrar su
--   movimiento, se liberan ambos.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.validar_reglas_autorizacion(
    IN p_id_tarjeta BINARY(16), IN p_num_cuenta VARCHAR(20), IN p_id_canal VARCHAR(5), IN p_id_terminal VARCHAR(30),
    IN p_tipo_operacion VARCHAR(25), IN p_monto DECIMAL(15,2), IN p_momento DATETIME(6))
BEGIN
    DECLARE v_estado_tarjeta VARCHAR(25);
    DECLARE v_vencimiento DATE;
    DECLARE v_operativa BOOLEAN;
    DECLARE v_canal VARCHAR(5);
    DECLARE v_estado_cuenta VARCHAR(25);
    DECLARE v_moneda CHAR(3);
    DECLARE v_regimen VARCHAR(25);
    DECLARE v_disponible DECIMAL(15,2);
    DECLARE v_nat CHAR(1);
    DECLARE v_hay_limite BOOLEAN DEFAULT FALSE;
    DECLARE v_habilitado BOOLEAN;
    DECLARE v_tope, v_consumo DECIMAL(15,2);
    SELECT estado_tarjeta, fecha_vencimiento INTO v_estado_tarjeta, v_vencimiento
      FROM tarjetas.tarjeta WHERE id_tarjeta = p_id_tarjeta;
    SELECT es_operativa INTO v_operativa FROM tarjetas.estado_tarjeta WHERE cod_estado = v_estado_tarjeta;
    IF NOT v_operativa THEN
        CALL core.fallar(CONCAT('ERR-TAR-003: la tarjeta ', BIN_TO_UUID(p_id_tarjeta), ' no es operativa (estado ',
                                v_estado_tarjeta, ')'));
    END IF;
    IF v_vencimiento < core.fn_fecha_negocio(p_momento) THEN
        CALL core.fallar(CONCAT('ERR-TAR-003: la tarjeta ', BIN_TO_UUID(p_id_tarjeta), ' venció el ', v_vencimiento));
    END IF;
    IF p_id_terminal IS NOT NULL THEN
        SELECT id_canal INTO v_canal FROM core.terminal WHERE id_terminal = p_id_terminal AND activo;
        IF v_canal IS NULL THEN
            CALL core.fallar(CONCAT('ERR-TAR-006: la terminal ', p_id_terminal, ' no está activa'));
        END IF;
    ELSE
        SET v_canal = p_id_canal;
    END IF;
    IF NOT (SELECT activo FROM core.canal WHERE id_canal = v_canal) THEN
        CALL core.fallar(CONCAT('ERR-TAR-006: el canal ', v_canal, ' no está activo'));
    END IF;
    -- Bloquea la cuenta antes de leer el saldo y el consumo comprometido.
    SELECT estado_cuenta, moneda, regimen, saldo_disponible INTO v_estado_cuenta, v_moneda, v_regimen, v_disponible
      FROM cuentas.cuenta_ahorro WHERE num_cuenta = p_num_cuenta FOR UPDATE;
    SELECT naturaleza INTO v_nat FROM cuentas.tipo_operacion WHERE tipo_operacion = p_tipo_operacion;
    IF v_canal = 'ATM' AND (
           NOT (SELECT habilitada_atm FROM tarjetas.tarjeta_cuenta
                 WHERE id_tarjeta = p_id_tarjeta AND num_cuenta = p_num_cuenta)
           OR (SELECT firma_conjunta FROM cuentas.regimen_cuenta WHERE cod_regimen = v_regimen)) THEN
        CALL core.fallar(CONCAT('ERR-TAR-008: la cuenta ', p_num_cuenta, ' no puede operarse en cajero (RN-ATM-005)'));
    END IF;
    IF v_nat = 'D' THEN
        IF NOT (SELECT permite_debito FROM cuentas.estado_cuenta WHERE cod_estado = v_estado_cuenta) THEN
            CALL core.fallar(CONCAT('BNA-ESTADO-CUENTA: la cuenta ', p_num_cuenta, ' (estado ', v_estado_cuenta,
                                    ') no admite débitos'));
        END IF;
        SELECT TRUE, habilitado, monto_maximo_diario INTO v_hay_limite, v_habilitado, v_tope
          FROM core.limite_canal WHERE id_canal = v_canal AND moneda = v_moneda;
        IF NOT v_hay_limite THEN
            CALL core.fallar(CONCAT('ERR-TAR-006: el canal ', v_canal, ' no opera en ', v_moneda));
        END IF;
        IF NOT v_habilitado THEN
            CALL core.fallar(CONCAT('ERR-TAR-006: el canal ', v_canal, ' no opera en ', v_moneda, ' (RN-BD-002)'));
        END IF;
        IF v_tope IS NOT NULL THEN
            SELECT coalesce(max(monto_acumulado), 0) INTO v_consumo FROM core.consumo_diario
             WHERE num_cuenta = p_num_cuenta AND id_canal = v_canal
               AND fecha_corte = core.fn_fecha_negocio(p_momento)
               FOR UPDATE;
            IF v_consumo + p_monto > v_tope THEN
                CALL core.fallar(CONCAT('ERR-TAR-007: tope diario excedido (RN-TOP-001); disponible hoy ',
                                        v_tope - v_consumo, ' ', v_moneda));
            END IF;
        END IF;
        IF v_disponible < p_monto THEN
            CALL core.fallar(CONCAT('BNA-SALDO: saldo disponible insuficiente en ', p_num_cuenta,
                                    ' (', v_disponible, ' < ', p_monto, ')'));
        END IF;
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_autorizacion_validar_bi BEFORE INSERT ON tarjetas.autorizacion
FOR EACH ROW BEGIN
    IF NEW.estado_autorizacion NOT IN ('INICIADA', 'AUTORIZADA', 'RECHAZADA') THEN
        CALL core.fallar(CONCAT('RN-ATM-007: una autorización nueva no puede estar ', NEW.estado_autorizacion));
    END IF;
    IF NEW.estado_autorizacion = 'AUTORIZADA' THEN
        CALL tarjetas.validar_reglas_autorizacion(NEW.id_tarjeta, NEW.num_cuenta, NEW.id_canal, NEW.id_terminal,
                                                  NEW.tipo_operacion, NEW.monto, NEW.fecha_hora);
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_autorizacion_validar_bu BEFORE UPDATE ON tarjetas.autorizacion
FOR EACH ROW BEGIN
    IF NOT (NEW.uuid_autorizacion <=> OLD.uuid_autorizacion AND NEW.tipo_operacion <=> OLD.tipo_operacion
            AND NEW.monto <=> OLD.monto AND NEW.id_tarjeta <=> OLD.id_tarjeta AND NEW.num_cuenta <=> OLD.num_cuenta
            AND NEW.id_canal <=> OLD.id_canal AND NEW.id_terminal <=> OLD.id_terminal
            AND NEW.ip_origen <=> OLD.ip_origen AND NEW.fecha_hora <=> OLD.fecha_hora) THEN
        CALL core.fallar('RN-ATM-007: los datos de la operación autorizada no se modifican');
    END IF;
    IF NOT (NEW.estado_autorizacion <=> OLD.estado_autorizacion) AND NOT (
           (OLD.estado_autorizacion = 'INICIADA' AND NEW.estado_autorizacion IN ('AUTORIZADA', 'RECHAZADA'))
        OR (OLD.estado_autorizacion = 'AUTORIZADA'
            AND NEW.estado_autorizacion IN ('DISPENSADA', 'PENDIENTE_REVERSION', 'EXTORNADA'))
        OR (OLD.estado_autorizacion = 'DISPENSADA'
            AND NEW.estado_autorizacion IN ('PENDIENTE_REVERSION', 'EXTORNADA'))
        OR (OLD.estado_autorizacion = 'PENDIENTE_REVERSION' AND NEW.estado_autorizacion = 'EXTORNADA')) THEN
        CALL core.fallar(CONCAT('RN-ATM-007: transición no permitida de ', OLD.estado_autorizacion, ' a ',
                                NEW.estado_autorizacion));
    END IF;
    SET NEW.fecha_actualizacion = UTC_TIMESTAMP(6);
    IF NEW.estado_autorizacion = 'AUTORIZADA' AND OLD.estado_autorizacion = 'INICIADA' THEN
        CALL tarjetas.validar_reglas_autorizacion(NEW.id_tarjeta, NEW.num_cuenta, NEW.id_canal, NEW.id_terminal,
                                                  NEW.tipo_operacion, NEW.monto, NEW.fecha_hora);
    END IF;
END //

-- Compromete el tope y retiene el saldo al autorizar; los libera si la
-- autorización se extorna antes de registrar su movimiento.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.autorizacion_comprometer(
    IN p_num_cuenta VARCHAR(20), IN p_id_canal VARCHAR(5), IN p_id_terminal VARCHAR(30),
    IN p_monto DECIMAL(15,2), IN p_momento DATETIME(6))
BEGIN
    DECLARE v_canal VARCHAR(5) DEFAULT coalesce(p_id_canal,
        (SELECT id_canal FROM core.terminal WHERE id_terminal = p_id_terminal));
    UPDATE cuentas.cuenta_ahorro SET saldo_disponible = saldo_disponible - p_monto WHERE num_cuenta = p_num_cuenta;
    CALL core.consumo_sumar(p_num_cuenta, v_canal, core.fn_fecha_negocio(p_momento), p_monto);
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_autorizacion_aplicar_ai AFTER INSERT ON tarjetas.autorizacion
FOR EACH ROW BEGIN
    IF NEW.estado_autorizacion = 'AUTORIZADA'
       AND (SELECT naturaleza FROM cuentas.tipo_operacion WHERE tipo_operacion = NEW.tipo_operacion) = 'D' THEN
        CALL tarjetas.autorizacion_comprometer(NEW.num_cuenta, NEW.id_canal, NEW.id_terminal, NEW.monto, NEW.fecha_hora);
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_autorizacion_aplicar_au AFTER UPDATE ON tarjetas.autorizacion
FOR EACH ROW BEGIN
    IF (SELECT naturaleza FROM cuentas.tipo_operacion WHERE tipo_operacion = NEW.tipo_operacion) = 'D' THEN
        IF NEW.estado_autorizacion = 'AUTORIZADA' AND OLD.estado_autorizacion = 'INICIADA' THEN
            CALL tarjetas.autorizacion_comprometer(NEW.num_cuenta, NEW.id_canal, NEW.id_terminal, NEW.monto,
                                                   NEW.fecha_hora);
        ELSEIF NEW.estado_autorizacion = 'EXTORNADA' AND OLD.estado_autorizacion <> 'EXTORNADA'
               AND NEW.uuid_transaccion IS NULL THEN
            CALL tarjetas.autorizacion_comprometer(NEW.num_cuenta, NEW.id_canal, NEW.id_terminal, -NEW.monto,
                                                   NEW.fecha_hora);
        END IF;
    END IF;
END //

-- ---------------------------------------------------------------------
-- Tarjetas: estado del cliente (trg_cliente_ref_au de Tarjetas, INT-T07).
--   * Si Clientes bloquea o suspende al cliente, se bloquean sus tarjetas
--     activas o por activar; si lo da de baja, se cancelan todas.
-- MySQL: un INSERT ... SELECT FROM tarjetas.tarjeta falla aquí (error 1442):
--   el trigger del historial actualiza TARJETA, que ya usa la sentencia que lo
--   invoca. Se recorre un cursor e inserta fila por fila.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' TRIGGER clientes.tg_cliente_estado_tarjetas AFTER UPDATE ON clientes.cliente
FOR EACH ROW BEGIN
    DECLARE v_cliente VARCHAR(12) DEFAULT NEW.cod_cliente;
    DECLARE v_estado VARCHAR(25) DEFAULT NEW.estado_cliente;
    DECLARE v_tarjeta BINARY(16);
    DECLARE v_fin BOOLEAN DEFAULT FALSE;
    DECLARE c_tarjetas CURSOR FOR
        SELECT t.id_tarjeta
          FROM tarjetas.tarjeta t JOIN tarjetas.estado_tarjeta e ON e.cod_estado = t.estado_tarjeta
         WHERE t.cod_cliente = v_cliente
           AND ((v_estado IN ('BLOQUEADO', 'SUSPENDIDO') AND t.estado_tarjeta IN ('ACTIVA', 'PENDIENTE_ACTIVACION'))
                OR (v_estado = 'BAJA' AND NOT e.es_final));
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fin = TRUE;
    IF NOT (NEW.estado_cliente <=> OLD.estado_cliente) AND v_estado IN ('BLOQUEADO', 'SUSPENDIDO', 'BAJA') THEN
        OPEN c_tarjetas;
        recorrer: LOOP
            FETCH c_tarjetas INTO v_tarjeta;
            IF v_fin THEN
                LEAVE recorrer;
            END IF;
            INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
            VALUES (IF(v_estado = 'BAJA', 'CANCELADA', 'BLOQUEADA'),
                    IF(v_estado = 'BAJA', 'Cliente dado de baja en Clientes', CONCAT('Cliente ', v_estado, ' en Clientes')),
                    'MODULO_CLIENTES', v_tarjeta);
        END LOOP;
        CLOSE c_tarjetas;
    END IF;
END //

-- ---------------------------------------------------------------------
-- Tarjetas: procedimientos de operación.
--   * bloquear_tarjeta: bloqueo con su motivo y origen (Tarjetas).
--   * marcar_tarjetas_vencidas: el procedimiento del evento programado
--     ev_marcar_tarjetas_vencidas de Tarjetas (RN-TAR-003).
-- MySQL: procedimientos con un parámetro OUT, no funciones con efectos.
-- DECISIÓN: MySQL tiene un planificador de eventos; como en Tarjetas, el
--   evento corre una vez al día, a las 00:05 de Arequipa (05:05 UTC).
--   core.verificar_configuracion rechaza si el planificador está apagado.
--   En una réplica los eventos quedan deshabilitados y deben habilitarse si
--   pasa a ser la principal.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.bloquear_tarjeta(IN p_id_tarjeta BINARY(16), IN p_motivo VARCHAR(255),
                                           IN p_origen VARCHAR(20), OUT p_id_historial BIGINT)
    COMMENT 'Bloquea la tarjeta registrando el motivo y el origen en el historial.'
BEGIN
    INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
    VALUES ('BLOQUEADA', p_motivo, p_origen, p_id_tarjeta);
    SET p_id_historial = LAST_INSERT_ID();
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.marcar_tarjetas_vencidas(IN p_fecha DATE, OUT p_marcadas INT)
    COMMENT 'Marca como VENCIDA cada tarjeta cuya fecha ya pasó (por omisión, hoy); lo llama el evento diario.'
BEGIN
    DECLARE v_fecha DATE DEFAULT coalesce(p_fecha, core.fn_fecha_negocio(UTC_TIMESTAMP(6)));
    DECLARE v_tarjeta BINARY(16);
    DECLARE v_fin BOOLEAN DEFAULT FALSE;
    DECLARE c_tarjetas CURSOR FOR
        SELECT id_tarjeta FROM tarjetas.tarjeta
         WHERE fecha_vencimiento < v_fecha AND estado_tarjeta NOT IN ('VENCIDA', 'CANCELADA');
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fin = TRUE;
    SET p_marcadas = 0;
    OPEN c_tarjetas;
    recorrer: LOOP
        FETCH c_tarjetas INTO v_tarjeta;
        IF v_fin THEN
            LEAVE recorrer;
        END IF;
        INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
        VALUES ('VENCIDA', 'Vencimiento de la tarjeta', 'SISTEMA', v_tarjeta);
        SET p_marcadas = p_marcadas + 1;
    END LOOP;
    CLOSE c_tarjetas;
END //

CREATE DEFINER = 'bna_owner'@'%' EVENT tarjetas.ev_marcar_tarjetas_vencidas
    ON SCHEDULE EVERY 1 DAY STARTS '2026-01-01 05:05:00'
    ON COMPLETION PRESERVE ENABLE
    COMMENT 'Una vez al día, 00:05 de Arequipa: marca las tarjetas vencidas (RN-TAR-003).'
    DO CALL tarjetas.marcar_tarjetas_vencidas(NULL, @bna_tarjetas_vencidas) //

-- ---------------------------------------------------------------------
-- Desembolso: orden (reglas de integración del modelo).
--   * La cuenta destino pertenece al cliente de la solicitud y tiene su
--     moneda; el importe no supera el límite aprobado en la evaluación.
--   * Una sola orden CONFIRMADA por solicitud, en todas sus rondas
--     (Desembolso: un desembolso confirmado por crédito).
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.validar_orden(IN p_id_orden BINARY(16), IN p_id_evaluacion BINARY(16),
                                        IN p_num_cuenta VARCHAR(20), IN p_importe DECIMAL(15,2),
                                        IN p_estado VARCHAR(25))
BEGIN
    DECLARE v_solicitud BINARY(16);
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_moneda_solicitud, v_moneda CHAR(3);
    DECLARE v_limite DECIMAL(15,2);
    SELECT s.id_solicitud, s.cod_cliente, s.moneda, e.limite_aprobado
      INTO v_solicitud, v_cliente, v_moneda_solicitud, v_limite
      FROM creditos.solicitud_credito s
      JOIN creditos.evaluacion e ON e.id_solicitud = s.id_solicitud
     WHERE e.id_evaluacion = p_id_evaluacion
       FOR UPDATE OF s;
    IF NOT EXISTS (SELECT 1 FROM cuentas.titularidad WHERE cod_cliente = v_cliente AND num_cuenta = p_num_cuenta) THEN
        CALL core.fallar(CONCAT('BNA-CUENTA-DESTINO: la cuenta ', p_num_cuenta, ' no pertenece al cliente ',
                                v_cliente, ' de la solicitud'));
    END IF;
    SELECT moneda INTO v_moneda FROM cuentas.cuenta_ahorro WHERE num_cuenta = p_num_cuenta;
    IF v_moneda <> v_moneda_solicitud THEN
        CALL core.fallar(CONCAT('BNA-CUENTA-DESTINO: la cuenta ', p_num_cuenta, ' está en ', v_moneda,
                                ' y la solicitud en ', v_moneda_solicitud));
    END IF;
    IF p_importe > v_limite THEN
        CALL core.fallar(CONCAT('BNA-IMPORTE: el importe ', p_importe, ' supera el límite aprobado ', v_limite));
    END IF;
    IF p_estado = 'CONFIRMADA' AND EXISTS (
           SELECT 1 FROM creditos.orden_desembolso o
             JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
            WHERE e.id_solicitud = v_solicitud
              AND o.estado_orden = 'CONFIRMADA' AND NOT (o.id_orden <=> p_id_orden)) THEN
        CALL core.fallar(CONCAT('BNA-ORDEN-UNICA: la solicitud ', BIN_TO_UUID(v_solicitud),
                                ' ya tiene una orden CONFIRMADA'));
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_orden_validar_bi BEFORE INSERT ON creditos.orden_desembolso
FOR EACH ROW CALL creditos.validar_orden(NEW.id_orden, NEW.id_evaluacion, NEW.num_cuenta, NEW.importe, NEW.estado_orden) //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_orden_validar_bu BEFORE UPDATE ON creditos.orden_desembolso
FOR EACH ROW CALL creditos.validar_orden(NEW.id_orden, NEW.id_evaluacion, NEW.num_cuenta, NEW.importe, NEW.estado_orden) //

-- ---------------------------------------------------------------------
-- Cobranza: crédito (decisión I15 del informe).
--   * El crédito nace de una orden CONFIRMADA, y su calendario es OFICIAL y
--     pertenece a la solicitud de la evaluación de esa orden.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.validar_credito(IN p_id_orden BINARY(16), IN p_id_calendario BINARY(16))
BEGIN
    DECLARE v_estado_orden VARCHAR(25);
    DECLARE v_sol_orden, v_sol_calendario BINARY(16);
    DECLARE v_tipo VARCHAR(25);
    SELECT o.estado_orden, e.id_solicitud INTO v_estado_orden, v_sol_orden
      FROM creditos.orden_desembolso o JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
     WHERE o.id_orden = p_id_orden;
    IF v_estado_orden <> 'CONFIRMADA' THEN
        CALL core.fallar(CONCAT('BNA-CREDITO: el crédito nace de una orden CONFIRMADA (la orden está ', v_estado_orden, ')'));
    END IF;
    SELECT id_solicitud, tipo_calendario INTO v_sol_calendario, v_tipo
      FROM creditos.calendario_pago WHERE id_calendario = p_id_calendario;
    IF v_sol_calendario <> v_sol_orden THEN
        CALL core.fallar(CONCAT('BNA-CREDITO: el calendario ', BIN_TO_UUID(p_id_calendario),
                                ' no pertenece a la solicitud de la orden'));
    END IF;
    IF v_tipo <> 'OFICIAL' THEN
        CALL core.fallar(CONCAT('BNA-CREDITO: el crédito usa el calendario OFICIAL, no el ', v_tipo));
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_credito_validar_bi BEFORE INSERT ON creditos.credito
FOR EACH ROW CALL creditos.validar_credito(NEW.id_orden, NEW.id_calendario) //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_credito_validar_bu BEFORE UPDATE ON creditos.credito
FOR EACH ROW BEGIN
    IF NOT (NEW.id_orden <=> OLD.id_orden AND NEW.id_calendario <=> OLD.id_calendario) THEN
        CALL creditos.validar_credito(NEW.id_orden, NEW.id_calendario);
    END IF;
END //

-- ---------------------------------------------------------------------
-- Cobranza: aplicación de pagos.
--   * Solo se aplica un pago CONFIRMADO, a cuotas del calendario de su
--     crédito, sin superar el saldo de la cuota ni el monto del pago.
--   * Aplicar actualiza el saldo pendiente y el estado de la cuota, y
--     cancela el crédito cuando todas sus cuotas quedan pagadas (Cobranza,
--     acciones de actualización).
-- DECISIÓN: la mora no se paga por APLICACION_PAGO: es el cálculo de CORE
--   guardado en MORA, de modo que pagarla no puede dar por pagada la cuota.
-- DECISIÓN: una aplicación no se modifica ni se borra; un error se corrige
--   con un nuevo pago o con su extorno en Cuentas.
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_aplicacion_validar BEFORE INSERT ON creditos.aplicacion_pago
FOR EACH ROW BEGIN
    DECLARE v_estado VARCHAR(25);
    DECLARE v_credito VARCHAR(20);
    DECLARE v_monto_pago, v_saldo, v_aplicado DECIMAL(15,2);
    DECLARE v_cal BINARY(16);
    SELECT estado_confirmacion, cod_credito, monto_pago INTO v_estado, v_credito, v_monto_pago
      FROM creditos.pago WHERE id_pago = NEW.id_pago FOR UPDATE;
    IF v_estado <> 'CONFIRMADO' THEN
        CALL core.fallar(CONCAT('BNA-PAGO: solo se aplica un pago CONFIRMADO (el pago está ', v_estado, ')'));
    END IF;
    SELECT id_calendario INTO v_cal FROM creditos.credito WHERE cod_credito = v_credito;
    IF NEW.id_calendario <> v_cal THEN
        CALL core.fallar(CONCAT('BNA-PAGO: la cuota no pertenece al calendario del crédito ', v_credito, ' del pago'));
    END IF;
    SELECT saldo_pendiente INTO v_saldo FROM creditos.cuota
     WHERE id_calendario = NEW.id_calendario AND numero_cuota = NEW.numero_cuota FOR UPDATE;
    IF NEW.monto_aplicado > v_saldo THEN
        CALL core.fallar(CONCAT('BNA-PAGO: se aplican ', NEW.monto_aplicado, ' a la cuota ', NEW.numero_cuota,
                                ', que solo debe ', v_saldo));
    END IF;
    SELECT coalesce(sum(monto_aplicado), 0) INTO v_aplicado FROM creditos.aplicacion_pago WHERE id_pago = NEW.id_pago;
    IF v_aplicado + NEW.monto_aplicado > v_monto_pago THEN
        CALL core.fallar(CONCAT('BNA-PAGO: se aplicarían ', v_aplicado + NEW.monto_aplicado, ' de un pago de ', v_monto_pago));
    END IF;
END //

-- MySQL: el estado se asigna antes que el saldo, porque cada asignación de
--   un UPDATE ve el valor que dejó la anterior.
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_aplicacion_aplicar AFTER INSERT ON creditos.aplicacion_pago
FOR EACH ROW BEGIN
    UPDATE creditos.cuota
       SET estado_cuota = CASE WHEN saldo_pendiente - NEW.monto_aplicado = 0 THEN 'PAGADA'
                               WHEN estado_cuota = 'VENCIDA' THEN 'VENCIDA'
                               ELSE 'PARCIAL' END,
           saldo_pendiente = saldo_pendiente - NEW.monto_aplicado
     WHERE id_calendario = NEW.id_calendario AND numero_cuota = NEW.numero_cuota;
    IF NOT EXISTS (SELECT 1 FROM creditos.cuota
                    WHERE id_calendario = NEW.id_calendario AND estado_cuota <> 'PAGADA') THEN
        UPDATE creditos.credito SET estado_credito = 'CANCELADO' WHERE id_calendario = NEW.id_calendario;
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_aplicacion_solo_insercion_bu BEFORE UPDATE ON creditos.aplicacion_pago
FOR EACH ROW CALL core.rechazar_cambio('BNA-PAGO', 'creditos.aplicacion_pago', 'UPDATE') //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_aplicacion_solo_insercion_bd BEFORE DELETE ON creditos.aplicacion_pago
FOR EACH ROW CALL core.rechazar_cambio('BNA-PAGO', 'creditos.aplicacion_pago', 'DELETE') //

-- Aplica el saldo libre de un pago a las cuotas con saldo, de la más antigua
-- a la más reciente (Cobranza: un pago puede ser parcial o alcanzar para la
-- cuota siguiente). Devuelve el monto aplicado en esta llamada.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.aplicar_pago(IN p_id_pago BINARY(16), OUT p_aplicado DECIMAL(15,2))
    COMMENT 'Reparte el saldo libre de un pago entre las cuotas pendientes, de la más antigua a la más reciente.'
BEGIN
    DECLARE v_credito VARCHAR(20);
    DECLARE v_monto_pago, v_libre, v_monto, v_saldo DECIMAL(15,2);
    DECLARE v_cal BINARY(16);
    DECLARE v_cuota SMALLINT;
    DECLARE v_fin BOOLEAN DEFAULT FALSE;
    DECLARE c_cuotas CURSOR FOR
        SELECT q.id_calendario, q.numero_cuota, q.saldo_pendiente
          FROM creditos.cuota q JOIN creditos.credito c ON c.id_calendario = q.id_calendario
         WHERE c.cod_credito = v_credito AND q.saldo_pendiente > 0
         ORDER BY q.numero_cuota;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fin = TRUE;
    SET p_aplicado = 0;
    SELECT cod_credito, monto_pago INTO v_credito, v_monto_pago FROM creditos.pago WHERE id_pago = p_id_pago;
    IF v_credito IS NULL THEN
        CALL core.fallar(CONCAT('BNA-PAGO: no existe el pago ', coalesce(BIN_TO_UUID(p_id_pago), 'NULL')));
    END IF;
    SET v_fin = FALSE;
    SELECT v_monto_pago - coalesce(sum(monto_aplicado), 0) INTO v_libre
      FROM creditos.aplicacion_pago WHERE id_pago = p_id_pago;
    OPEN c_cuotas;
    recorrer: LOOP
        FETCH c_cuotas INTO v_cal, v_cuota, v_saldo;
        IF v_fin OR v_libre <= 0 THEN
            LEAVE recorrer;
        END IF;
        SET v_monto = LEAST(v_libre, v_saldo);
        INSERT INTO creditos.aplicacion_pago (id_pago, id_calendario, numero_cuota, monto_aplicado)
        VALUES (p_id_pago, v_cal, v_cuota, v_monto);
        SET v_libre = v_libre - v_monto, p_aplicado = p_aplicado + v_monto;
    END LOOP;
    CLOSE c_cuotas;
END //

DELIMITER ;

-- ---------------------------------------------------------------------
-- Vistas de Tarjetas (Tabla 17 de Tarjetas).
-- ---------------------------------------------------------------------
-- Tarjetas con número enmascarado, titular, vencimiento MM/AA y si están
-- operativas (PCI-DSS: nunca se muestra el número completo).
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW tarjetas.v_tarjeta_resumen AS
SELECT t.id_tarjeta,
       CONCAT(SUBSTR(t.bin, 1, 4), ' ', SUBSTR(t.bin, 5, 2), '** **** ', t.ultimos4) AS numero_enmascarado,
       b.tipo_tarjeta,
       t.cod_cliente,
       CONCAT_WS(' ', c.nombres, c.apellido_paterno, c.apellido_materno) AS titular,
       DATE_FORMAT(t.fecha_vencimiento, '%m/%y') AS vencimiento_mm_aa,
       t.estado_tarjeta,
       e.es_operativa AND t.fecha_vencimiento >= core.fn_fecha_negocio(UTC_TIMESTAMP(6)) AS operativa
  FROM tarjetas.tarjeta t
  JOIN tarjetas.bin_tarjeta b ON b.bin = t.bin
  JOIN tarjetas.estado_tarjeta e ON e.cod_estado = t.estado_tarjeta
  JOIN clientes.cliente c ON c.cod_cliente = t.cod_cliente;

-- Monto consumido por tarjeta, canal, moneda y día (RN-TOP-001).
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW tarjetas.v_consumo_diario AS
SELECT a.id_tarjeta,
       coalesce(a.id_canal, te.id_canal) AS id_canal,
       cu.moneda,
       core.fn_fecha_negocio(a.fecha_hora) AS fecha,
       sum(a.monto) AS monto_consumido,
       count(*) AS operaciones
  FROM tarjetas.autorizacion a
  JOIN cuentas.cuenta_ahorro cu ON cu.num_cuenta = a.num_cuenta
  JOIN cuentas.tipo_operacion o ON o.tipo_operacion = a.tipo_operacion
  LEFT JOIN core.terminal te ON te.id_terminal = a.id_terminal
 WHERE a.estado_autorizacion IN ('AUTORIZADA', 'DISPENSADA') AND o.naturaleza = 'D'
 GROUP BY a.id_tarjeta, coalesce(a.id_canal, te.id_canal), cu.moneda, core.fn_fecha_negocio(a.fecha_hora);

-- Tope disponible del día por tarjeta y canal (RN-TOP-001). El consumo es el
-- de cada cuenta vinculada, porque el tope se controla por cuenta.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW tarjetas.v_tope_restante_hoy AS
SELECT tc.id_tarjeta,
       tc.num_cuenta,
       l.id_canal,
       l.moneda,
       l.monto_maximo_diario,
       coalesce(cd.monto_acumulado, 0) AS consumido_hoy,
       l.monto_maximo_diario - coalesce(cd.monto_acumulado, 0) AS disponible_hoy
  FROM tarjetas.tarjeta_cuenta tc
  JOIN cuentas.cuenta_ahorro cu ON cu.num_cuenta = tc.num_cuenta
  JOIN core.limite_canal l ON l.moneda = cu.moneda AND l.habilitado
  LEFT JOIN core.consumo_diario cd
         ON cd.num_cuenta = tc.num_cuenta AND cd.id_canal = l.id_canal
        AND cd.fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6));

-- Credenciales y matrices con intentos fallidos acumulados (RN-TAR-004).
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW tarjetas.v_credenciales_en_riesgo AS
SELECT cr.id_tarjeta, cr.tipo_credencial AS credencial, cr.intentos_fallidos,
       3 - cr.intentos_fallidos AS intentos_restantes, t.estado_tarjeta
  FROM tarjetas.credencial cr JOIN tarjetas.tarjeta t ON t.id_tarjeta = cr.id_tarjeta
 WHERE cr.intentos_fallidos > 0
UNION ALL
SELECT m.id_tarjeta, 'TOKEN_MATRIZ', m.intentos_fallidos, 3 - m.intentos_fallidos, t.estado_tarjeta
  FROM tarjetas.matriz_token m JOIN tarjetas.tarjeta t ON t.id_tarjeta = m.id_tarjeta
 WHERE m.intentos_fallidos > 0 AND m.estado_matriz <> 'REEMPLAZADA';

-- ---------------------------------------------------------------------
-- Vistas de apoyo operativo de Desembolso (sección 8 de Desembolso).
-- ---------------------------------------------------------------------
-- Órdenes cuyo resultado en el CORE es incierto; alimenta el proceso de
-- recuperación que consulta el resultado por la misma referencia.
-- MySQL: no hay tipo intervalo; el tiempo en el estado va en segundos.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_ordenes_inciertas AS
SELECT o.id_orden, o.codigo_orden, o.estado_orden, o.importe, s.moneda, o.num_cuenta,
       o.idempotency_key, o.correlation_id, o.actualizado_en,
       TIMESTAMPDIFF(SECOND, o.actualizado_en, UTC_TIMESTAMP(6)) AS segundos_en_estado
  FROM creditos.orden_desembolso o
  JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
  JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
 WHERE o.estado_orden IN ('EN_PROCESO', 'POR_VERIFICAR');

-- Entregas a Cobranza que superan la política de reintentos.
-- DECISIÓN: la política es de dos reintentos como máximo (documento de
--   tecnologías del proyecto), es decir, tres intentos.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_entregas_pendientes AS
SELECT ev.id_evento, ev.id_orden, o.codigo_orden, ev.tipo_evento, ev.estado_entrega,
       ev.intentos, ev.siguiente_intento, ev.ultimo_error, ev.creado_en
  FROM creditos.evento_entrega ev
  JOIN creditos.orden_desembolso o ON o.id_orden = ev.id_orden
 WHERE ev.estado_entrega IN ('PENDIENTE', 'ENVIADO', 'FALLIDO') AND ev.intentos > 2;

-- Base para cuadrar operaciones e importes por fecha y moneda contra el CORE:
-- importe de las órdenes confirmadas frente a lo abonado en las cuentas.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_conciliacion_diaria AS
SELECT core.fn_fecha_negocio(coalesce(m.fecha_hora, o.actualizado_en)) AS fecha,
       s.moneda,
       count(*) AS ordenes_confirmadas,
       sum(o.importe) AS importe_ordenes,
       coalesce(sum(CASE WHEN m.estado_transaccion = 'APROBADO' THEN m.monto END), 0) AS importe_abonado,
       count(CASE WHEN m.uuid_transaccion IS NULL THEN 1 END) AS ordenes_sin_abono
  FROM creditos.orden_desembolso o
  JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
  JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
  LEFT JOIN cuentas.movimiento m ON m.uuid_transaccion = o.uuid_transaccion_abono
 WHERE o.estado_orden = 'CONFIRMADA'
 GROUP BY core.fn_fecha_negocio(coalesce(m.fecha_hora, o.actualizado_en)), s.moneda;

-- ---------------------------------------------------------------------
-- Control de la partida doble (MySQL): asientos sin líneas en el debe o en
-- el haber, o con sumas distintas. Solo puede haberlos si una cuenta con
-- INSERT directo se saltó core.registrar_asiento (brecha G04).
-- ---------------------------------------------------------------------
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW core.v_asientos_descuadrados AS
SELECT a.id_asiento, a.numero_asiento, a.fecha_contable,
       coalesce(sum(CASE WHEN d.tipo_partida = 'DEBE' THEN d.importe END), 0) AS debe,
       coalesce(sum(CASE WHEN d.tipo_partida = 'HABER' THEN d.importe END), 0) AS haber
  FROM core.asiento_contable a
  LEFT JOIN core.detalle_asiento d ON d.id_asiento = a.id_asiento
 GROUP BY a.id_asiento, a.numero_asiento, a.fecha_contable
HAVING count(CASE WHEN d.tipo_partida = 'DEBE' THEN 1 END) = 0
    OR count(CASE WHEN d.tipo_partida = 'HABER' THEN 1 END) = 0
    OR debe <> haber;

-- ---------------------------------------------------------------------
-- Bitácoras: el identificador lo asigna la base (en la rama main,
-- GENERATED ALWAYS AS IDENTITY rechaza un valor explícito).
-- ---------------------------------------------------------------------
DELIMITER //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER clientes.tg_validacion_identidad_identidad BEFORE INSERT ON clientes.validacion_identidad
FOR EACH ROW BEGIN
    IF NEW.id_validacion <> 0 THEN
        CALL core.fallar(CONCAT('BNA-IDENTIDAD: clientes.validacion_identidad.id_validacion lo asigna la base (se recibió ', NEW.id_validacion, ')'));
    END IF;
END //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_intento_autenticacion_identidad BEFORE INSERT ON tarjetas.intento_autenticacion
FOR EACH ROW BEGIN
    IF NEW.id_intento <> 0 THEN
        CALL core.fallar(CONCAT('BNA-IDENTIDAD: tarjetas.intento_autenticacion.id_intento lo asigna la base (se recibió ', NEW.id_intento, ')'));
    END IF;
END //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_historial_estado_tarjeta_identidad BEFORE INSERT ON tarjetas.historial_estado_tarjeta
FOR EACH ROW BEGIN
    IF NEW.id_historial <> 0 THEN
        CALL core.fallar(CONCAT('BNA-IDENTIDAD: tarjetas.historial_estado_tarjeta.id_historial lo asigna la base (se recibió ', NEW.id_historial, ')'));
    END IF;
END //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER tarjetas.tg_evento_salida_identidad BEFORE INSERT ON tarjetas.evento_salida
FOR EACH ROW BEGIN
    IF NEW.id_evento <> 0 THEN
        CALL core.fallar(CONCAT('BNA-IDENTIDAD: tarjetas.evento_salida.id_evento lo asigna la base (se recibió ', NEW.id_evento, ')'));
    END IF;
END //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_historial_estado_solicitud_identidad BEFORE INSERT ON creditos.historial_estado_solicitud
FOR EACH ROW BEGIN
    IF NEW.id_historial <> 0 THEN
        CALL core.fallar(CONCAT('BNA-IDENTIDAD: creditos.historial_estado_solicitud.id_historial lo asigna la base (se recibió ', NEW.id_historial, ')'));
    END IF;
END //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_evento_entrega_identidad BEFORE INSERT ON creditos.evento_entrega
FOR EACH ROW BEGIN
    IF NEW.id_evento <> 0 THEN
        CALL core.fallar(CONCAT('BNA-IDENTIDAD: creditos.evento_entrega.id_evento lo asigna la base (se recibió ', NEW.id_evento, ')'));
    END IF;
END //
CREATE DEFINER = 'bna_owner'@'%' TRIGGER creditos.tg_evento_auditoria_identidad BEFORE INSERT ON creditos.evento_auditoria
FOR EACH ROW BEGIN
    IF NEW.id_evento <> 0 THEN
        CALL core.fallar(CONCAT('BNA-IDENTIDAD: creditos.evento_auditoria.id_evento lo asigna la base (se recibió ', NEW.id_evento, ')'));
    END IF;
END //
DELIMITER ;

-- =====================================================================
-- Roles y privilegios
-- =====================================================================
CREATE ROLE IF NOT EXISTS bna_app, bna_admin;
GRANT ALL PRIVILEGES ON core.* TO bna_admin;
GRANT ALL PRIVILEGES ON clientes.* TO bna_admin;
GRANT ALL PRIVILEGES ON cuentas.* TO bna_admin;
GRANT ALL PRIVILEGES ON tarjetas.* TO bna_admin;
GRANT ALL PRIVILEGES ON creditos.* TO bna_admin;
GRANT SELECT ON core.* TO bna_app;
GRANT SELECT ON clientes.* TO bna_app;
GRANT SELECT ON cuentas.* TO bna_app;
GRANT SELECT ON tarjetas.* TO bna_app;
GRANT SELECT ON creditos.* TO bna_app;
GRANT INSERT ON clientes.cliente TO bna_app;
GRANT UPDATE (tipo_documento, numero_documento, nombres, apellido_paterno, apellido_materno, correo, celular, estado_cliente, id_verificacion_captacion, version_contrato) ON clientes.cliente TO bna_app;
GRANT INSERT ON clientes.biometria_cliente TO bna_app;
GRANT UPDATE (tipo_biometria, datos_biometricos, estado_activo, cod_cliente) ON clientes.biometria_cliente TO bna_app;
GRANT INSERT ON clientes.codigo_verificacion TO bna_app;
GRANT UPDATE (tipo_contacto, codigo_otp, fecha_expiracion, estado_codigo, intentos_fallidos, cod_cliente) ON clientes.codigo_verificacion TO bna_app;
GRANT INSERT (tipo_validacion, resultado, correlation_id, fecha_evento, cod_cliente) ON clientes.validacion_identidad TO bna_app;
GRANT UPDATE (tipo_validacion, resultado, correlation_id, fecha_evento, cod_cliente) ON clientes.validacion_identidad TO bna_app;
GRANT INSERT ON clientes.verificacion_captacion TO bna_app;
GRANT UPDATE (fecha_verificacion, estado_habilitante) ON clientes.verificacion_captacion TO bna_app;
GRANT INSERT (num_cuenta, cci, moneda, regimen, estado_cuenta, fecha_apertura, id_agencia) ON cuentas.cuenta_ahorro TO bna_app;
GRANT UPDATE (cci, moneda, regimen, estado_cuenta, fecha_apertura, id_agencia) ON cuentas.cuenta_ahorro TO bna_app;
GRANT INSERT ON cuentas.movimiento TO bna_app;
GRANT UPDATE (estado_transaccion) ON cuentas.movimiento TO bna_app;
GRANT INSERT ON cuentas.titularidad TO bna_app;
GRANT UPDATE (fecha_vinculacion) ON cuentas.titularidad TO bna_app;
GRANT INSERT ON tarjetas.tarjeta TO bna_app;
GRANT UPDATE (pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, cod_cliente) ON tarjetas.tarjeta TO bna_app;
GRANT INSERT ON tarjetas.tarjeta_cuenta TO bna_app;
GRANT UPDATE (es_principal, habilitada_atm, fecha_vinculacion) ON tarjetas.tarjeta_cuenta TO bna_app;
GRANT INSERT (id_tarjeta, tipo_credencial, hash_credencial, sal, fecha_creacion, fecha_ultimo_cambio) ON tarjetas.credencial TO bna_app;
GRANT UPDATE (hash_credencial, sal, fecha_creacion, fecha_ultimo_cambio) ON tarjetas.credencial TO bna_app;
GRANT INSERT (id_matriz, numero_serie, tipo_matriz, sal, estado_matriz, fecha_emision, id_tarjeta) ON tarjetas.matriz_token TO bna_app;
GRANT UPDATE (numero_serie, tipo_matriz, sal, estado_matriz, fecha_emision, id_tarjeta) ON tarjetas.matriz_token TO bna_app;
GRANT INSERT ON tarjetas.matriz_coordenada TO bna_app;
GRANT UPDATE (hash_valor) ON tarjetas.matriz_coordenada TO bna_app;
GRANT INSERT ON tarjetas.token_pago TO bna_app;
GRANT UPDATE (valor_token, proveedor_pasarela, estado_token, fecha_creacion, fecha_expiracion, id_tarjeta) ON tarjetas.token_pago TO bna_app;
GRANT INSERT (tipo_credencial, coord_fila, coord_columna, id_terminal, ip_origen, resultado, motivo_rechazo, uuid_correlacion, fecha_hora, id_tarjeta, id_canal) ON tarjetas.intento_autenticacion TO bna_app;
GRANT INSERT (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, codigo_respuesta, motivo_rechazo, nivel_riesgo, id_terminal, ip_origen, fecha_hora, id_tarjeta, num_cuenta, id_canal) ON tarjetas.autorizacion TO bna_app;
GRANT UPDATE (estado_autorizacion, codigo_respuesta, motivo_rechazo, nivel_riesgo) ON tarjetas.autorizacion TO bna_app;
GRANT INSERT (estado_nuevo, motivo, origen, fecha_hora, id_tarjeta) ON tarjetas.historial_estado_tarjeta TO bna_app;
GRANT INSERT (tipo_evento, carga_json, estado_envio, fecha_registro, fecha_envio, id_tarjeta) ON tarjetas.evento_salida TO bna_app;
GRANT UPDATE (tipo_evento, carga_json, estado_envio, fecha_registro, fecha_envio, id_tarjeta) ON tarjetas.evento_salida TO bna_app;
GRANT INSERT ON creditos.solicitud_credito TO bna_app;
GRANT UPDATE (version_solicitud, monto_solicitado, moneda, plazo_meses, condicion_pago_doble, estado_solicitud, fecha_creacion, cod_cliente) ON creditos.solicitud_credito TO bna_app;
GRANT INSERT (estado_nuevo, fecha_hora, actor, motivo, id_solicitud) ON creditos.historial_estado_solicitud TO bna_app;
GRANT INSERT ON creditos.garantia TO bna_app;
GRANT UPDATE (tipo_garantia, descripcion, valor_referencial, moneda, estado_garantia, id_solicitud) ON creditos.garantia TO bna_app;
GRANT INSERT ON creditos.fiador TO bna_app;
GRANT UPDATE (id_persona_externa, tipo_documento, numero_documento) ON creditos.fiador TO bna_app;
GRANT INSERT ON creditos.fiador_solicitud TO bna_app;
GRANT UPDATE (id_verificacion) ON creditos.fiador_solicitud TO bna_app;
GRANT INSERT ON creditos.calendario_pago TO bna_app;
GRANT UPDATE (version, tipo_calendario, metodo_amortizacion, tasa_aplicada, fecha_generacion, estado_calendario, id_solicitud) ON creditos.calendario_pago TO bna_app;
GRANT INSERT ON creditos.cuota TO bna_app;
GRANT UPDATE (fecha_vencimiento, capital, interes, otros_conceptos, saldo_capital) ON creditos.cuota TO bna_app;
GRANT INSERT ON creditos.situacion_financiera TO bna_app;
GRANT UPDATE (resultado_verificacion, ingreso_mensual, deuda_reportada, fecha_consulta, cod_cliente) ON creditos.situacion_financiera TO bna_app;
GRANT INSERT ON creditos.evaluacion TO bna_app;
GRANT UPDATE (ronda, fecha_evaluacion, score_calculado, limite_aprobado, condiciones_propuestas, observaciones, id_solicitud, id_consulta, id_regla, id_analista) ON creditos.evaluacion TO bna_app;
GRANT INSERT ON creditos.decision_analista TO bna_app;
GRANT UPDATE (decision, comentario, fecha_decision, id_evaluacion) ON creditos.decision_analista TO bna_app;
GRANT INSERT ON creditos.orden_desembolso TO bna_app;
GRANT UPDATE (codigo_orden, importe, estado_orden, motivo_rechazo, idempotency_key, request_hash, usuario_preparacion, usuario_confirmacion, correlation_id, version_registro, creado_en, actualizado_en, id_evaluacion, num_cuenta, id_canal, id_agencia, uuid_transaccion_abono) ON creditos.orden_desembolso TO bna_app;
GRANT INSERT ON creditos.validacion_desembolso TO bna_app;
GRANT UPDATE (tipo_validacion, referencia_evidencia, resultado, detalle, vence_en, creado_en, id_orden) ON creditos.validacion_desembolso TO bna_app;
GRANT INSERT (tipo_evento, version_esquema, payload, estado_entrega, intentos, siguiente_intento, confirmacion_id, ultimo_error, creado_en, actualizado_en, id_orden) ON creditos.evento_entrega TO bna_app;
GRANT UPDATE (tipo_evento, version_esquema, payload, estado_entrega, intentos, siguiente_intento, confirmacion_id, ultimo_error, creado_en, actualizado_en, id_orden) ON creditos.evento_entrega TO bna_app;
GRANT INSERT ON creditos.solicitud_reversion TO bna_app;
GRANT UPDATE (motivo, solicitante_id, autorizacion_id, estado_reversion, idempotency_key, creado_en, actualizado_en, id_orden, uuid_transaccion_extorno) ON creditos.solicitud_reversion TO bna_app;
GRANT INSERT ON creditos.credito TO bna_app;
GRANT UPDATE (id_orden, id_calendario) ON creditos.credito TO bna_app;
GRANT INSERT ON creditos.pago TO bna_app;
GRANT UPDATE (fecha_hora, monto_pago, referencia_transaccion, estado_confirmacion, cod_credito, id_canal) ON creditos.pago TO bna_app;
GRANT INSERT ON creditos.aplicacion_pago TO bna_app;
GRANT INSERT ON creditos.mora TO bna_app;
GRANT UPDATE (monto_calculado, fecha_calculo, id_calendario, numero_cuota) ON creditos.mora TO bna_app;
GRANT INSERT (modulo_emisor, id_entidad, numero_cuota, accion, resultado, actor, correlation_id, ip_origen, detalle, fecha_hora) ON creditos.evento_auditoria TO bna_app;
GRANT INSERT ON creditos.entidad_auditada TO bna_app;
GRANT UPDATE (tipo_entidad) ON creditos.entidad_auditada TO bna_app;
GRANT EXECUTE ON PROCEDURE core.registrar_asiento TO bna_app;
GRANT EXECUTE ON PROCEDURE core.verificar_configuracion TO bna_app;
GRANT EXECUTE ON PROCEDURE tarjetas.bloquear_tarjeta TO bna_app;
GRANT EXECUTE ON PROCEDURE creditos.aplicar_pago TO bna_app;
GRANT EXECUTE ON FUNCTION core.uuid_v4 TO bna_app;
GRANT EXECUTE ON FUNCTION core.fn_fecha_negocio TO bna_app;
GRANT EXECUTE ON PROCEDURE core.registrar_asiento TO bna_admin;
GRANT EXECUTE ON PROCEDURE core.verificar_configuracion TO bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.bloquear_tarjeta TO bna_admin;
GRANT EXECUTE ON PROCEDURE creditos.aplicar_pago TO bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.marcar_tarjetas_vencidas TO bna_admin;
-- <<< fin de la capa programable

-- =====================================================================
-- Datos iniciales: parámetros documentados por las fuentes
-- =====================================================================
-- DECISIÓN: solo se cargan valores que figuran en los documentos de los
--   módulos; los números de módulo sin asignar se agregan después.
START TRANSACTION;
INSERT INTO core.moneda (cod_moneda, nombre, simbolo, decimales) VALUES
    ('PEN', 'Sol', 'S/', 2),
    ('USD', 'Dólar estadounidense', 'US$', 2);
INSERT INTO core.modulo (id_modulo, nombre) VALUES
    (1, 'CORE'),
    (2, 'CLIENTES'),
    (3, 'CUENTAS'),
    (8, 'BUS DE SERVICIOS'),
    (9, 'SEGURIDAD'),
    (11, 'SOLICITUD DE CREDITO'),
    (12, 'EVALUACION'),
    (13, 'DESEMBOLSO'),
    (14, 'COBRANZA');
INSERT INTO clientes.tipo_documento (cod_tipo_documento, descripcion, longitud_min, longitud_max, es_alfanumerico) VALUES
    ('DNI', 'Documento Nacional de Identidad', 8, 8, FALSE),
    ('CE', 'Carné de extranjería', 9, 12, TRUE),
    ('PTP', 'Permiso Temporal de Permanencia', 9, 9, FALSE),
    ('PASAPORTE', 'Pasaporte', 6, 12, TRUE);
INSERT INTO clientes.tipo_biometria (cod_tipo_biometria, descripcion, umbral_similitud) VALUES
    ('DACTILAR', 'Huella dactilar', NULL),
    ('FACIAL', 'Reconocimiento facial', NULL);
INSERT INTO clientes.tipo_contacto (cod_tipo_contacto, descripcion, vigencia_minutos, max_intentos) VALUES
    ('SMS', 'Código enviado al celular', 5, 3),
    ('CORREO', 'Código enviado al correo', 10, 3);
INSERT INTO clientes.tipo_validacion (cod_tipo_validacion, descripcion, endpoint) VALUES
    ('DOCUMENTO', 'Validación de documento', '/api/v1/kyc/validar-documento'),
    ('HUELLA', 'Verificación dactilar', '/api/v1/kyc/validar-huella'),
    ('FACIAL', 'Verificación facial', '/api/v1/kyc/validar-facial'),
    ('CELULAR', 'Confirmación de celular', '/api/v1/kyc/celular/verificar-codigo'),
    ('CORREO', 'Confirmación de correo', '/api/v1/kyc/correo/verificar-codigo');
INSERT INTO clientes.estado_cliente (cod_estado, descripcion, permite_operar) VALUES
    ('ACTIVO', 'Cliente activo', TRUE),
    ('OBSERVADO', 'Cliente observado', TRUE),
    ('BLOQUEADO', 'Cliente bloqueado', FALSE),
    ('SUSPENDIDO', 'Cliente suspendido', FALSE),
    ('BAJA', 'Cliente dado de baja', FALSE);
INSERT INTO cuentas.regimen_cuenta (cod_regimen, descripcion, min_titulares, firma_conjunta) VALUES
    ('INDIVIDUAL', 'Un solo titular', 1, FALSE),
    ('MANCOMUNADA_INDISTINTA', 'Mancomunada (o): firma cualquier titular', 2, FALSE),
    ('MANCOMUNADA_CONJUNTA', 'Mancomunada (y): firman todos los titulares', 2, TRUE);
INSERT INTO cuentas.estado_cuenta (cod_estado, descripcion, permite_debito, permite_credito) VALUES
    ('ACTIVA', 'Cuenta activa', TRUE, TRUE),
    ('BLOQUEADA', 'Cuenta bloqueada', FALSE, FALSE),
    ('BLOQUEADA_PREVENTIVA', 'Bloqueo por seguridad', FALSE, TRUE),
    ('CANCELADA', 'Cuenta cancelada', FALSE, FALSE);
INSERT INTO cuentas.tipo_operacion (tipo_operacion, naturaleza) VALUES
    ('RETIRO', 'D'),
    ('TRANSFERENCIA_ENVIADA', 'D'),
    ('PAGO', 'D'),
    ('FONDEO_BILLETERA', 'D'),
    ('DEBITO_CUOTA', 'D'),
    ('DEPOSITO', 'C'),
    ('TRANSFERENCIA_RECIBIDA', 'C'),
    ('DESEMBOLSO', 'C'),
    ('ABONO_INTERES', 'C'),
    ('EXTORNO', 'C'),
    ('CONSULTA_SALDO', 'N');
INSERT INTO core.canal (id_canal, nombre, es_presencial, tipo_integracion, activo, regla_tope) VALUES
    ('ATM', 'Cajero automático', TRUE, 'BUS', TRUE, 'RN-TOP-001'),
    ('AGE', 'Agente BNA', TRUE, 'BUS', TRUE, 'RN-TOP-001'),
    ('VEN', 'Ventanilla', TRUE, 'BUS', TRUE, 'RN-TOP-001'),
    ('HB', 'Home Banking', FALSE, 'BUS', TRUE, 'RN-TOP-001'),
    ('BD', 'Billetera Digital', FALSE, 'BUS', TRUE, 'RN-BD-002');
INSERT INTO core.limite_canal (id_canal, moneda, monto_maximo_diario, habilitado) VALUES
    ('ATM', 'PEN', 1500, TRUE),
    ('ATM', 'USD', 500, TRUE),
    ('VEN', 'PEN', NULL, TRUE),
    ('VEN', 'USD', NULL, TRUE),
    ('HB', 'PEN', 10000, TRUE),
    ('BD', 'PEN', 500, TRUE),
    ('BD', 'USD', NULL, FALSE);
INSERT INTO tarjetas.tipo_credencial (tipo_credencial, longitud) VALUES
    ('PIN_ATM', 4),
    ('CLAVE_WEB', 6),
    ('TOKEN_MATRIZ', NULL),
    ('BIOMETRIA', NULL),
    ('TOKEN_PAGO', NULL);
INSERT INTO core.canal_validacion (id_canal, tipo_validacion) VALUES
    ('ATM', 'PIN_ATM'),
    ('HB', 'CLAVE_WEB'),
    ('HB', 'TOKEN_MATRIZ'),
    ('BD', 'TOKEN_PAGO'),
    ('VEN', 'BIOMETRIA'),
    ('AGE', 'BIOMETRIA');
INSERT INTO tarjetas.estado_tarjeta (cod_estado, descripcion, es_operativa, es_final) VALUES
    ('PENDIENTE_ACTIVACION', 'Emitida, sin activar', FALSE, FALSE),
    ('ACTIVA', 'Operativa', TRUE, FALSE),
    ('BLOQUEADA', 'Bloqueada', FALSE, FALSE),
    ('RETENIDA', 'Retenida por el cajero', FALSE, FALSE),
    ('VENCIDA', 'Vencida', FALSE, FALSE),
    ('CANCELADA', 'Cancelada', FALSE, TRUE);
INSERT INTO tarjetas.origen_cambio (cod_origen, descripcion, puede_desbloquear) VALUES
    ('CLIENTE', 'El propio cliente', FALSE),
    ('SISTEMA', 'Proceso automático', FALSE),
    ('SEGURIDAD', 'Módulo de seguridad', TRUE),
    ('OPERADOR', 'Operador de ventanilla', TRUE),
    ('MODULO_CLIENTES', 'Módulo de clientes', FALSE);
INSERT INTO tarjetas.codigo_respuesta (cod_respuesta, descripcion, es_aprobacion) VALUES
    ('00', 'Aprobada', TRUE),
    ('54', 'Tarjeta vencida', FALSE),
    ('EXT', 'Extorno', FALSE);
INSERT INTO tarjetas.tipo_evento_salida (tipo_evento, descripcion, id_modulo_destino) VALUES
    ('EMISION_TARJETA', 'Emisión de tarjeta', 9),
    ('CAMBIO_ESTADO_TARJETA', 'Cambio de estado de tarjeta', 9),
    ('BLOQUEO_POR_INTENTOS', 'Bloqueo por intentos fallidos', 9);
INSERT INTO creditos.estado_solicitud (cod_estado, descripcion, es_final) VALUES
    ('REGISTRADA', 'Registrada', FALSE),
    ('EN_EVALUACION', 'En evaluación', FALSE),
    ('APROBADA', 'Aprobada', FALSE),
    ('RECHAZADA', 'Rechazada', TRUE),
    ('DESEMBOLSADA', 'Desembolsada', TRUE);
INSERT INTO creditos.tipo_garantia (cod_tipo_garantia, descripcion) VALUES
    ('HIPOTECARIA', 'Hipoteca'),
    ('MOBILIARIA', 'Garantía mobiliaria'),
    ('PRENDARIA', 'Prenda');
INSERT INTO creditos.metodo_amortizacion (cod_metodo, descripcion) VALUES
    ('FRANCES', 'Cuota constante'),
    ('ALEMAN', 'Amortización constante'),
    ('AMERICANO', 'Capital al vencimiento');
INSERT INTO creditos.estado_cuota (cod_estado, descripcion) VALUES
    ('PENDIENTE', 'Pendiente'),
    ('PARCIAL', 'Pagada parcialmente'),
    ('PAGADA', 'Pagada'),
    ('VENCIDA', 'Vencida');
INSERT INTO creditos.estado_credito (cod_estado, descripcion) VALUES
    ('AL_DIA', 'Al día'),
    ('EN_MORA', 'En mora'),
    ('CANCELADO', 'Cancelado');
INSERT INTO creditos.resultado_crediticio (cod_resultado, descripcion) VALUES
    ('APROBADO', 'Aprobado'),
    ('OBSERVADO', 'Derivado a revisión manual'),
    ('RECHAZADO', 'Rechazado');
INSERT INTO creditos.regla_evaluacion (id_regla, codigo_rn, descripcion, ratio_min, ratio_max, accion) VALUES
    ('R-A', 'RN-EVA-002-P.a', 'Ratio monto/límite hasta 80 %', NULL, 80, 'APROBADO'),
    ('R-B', 'RN-EVA-002-P.b', 'Ratio monto/límite entre 80 % y 100 %', 80, 100, 'OBSERVADO'),
    ('R-C', 'RN-EVA-002-P.c', 'Ratio monto/límite mayor que 100 %', 100, NULL, 'RECHAZADO');
INSERT INTO creditos.estado_orden (cod_estado, descripcion, es_final) VALUES
    ('PREPARADA', 'Preparada', FALSE),
    ('VALIDADA', 'Validada', FALSE),
    ('EN_PROCESO', 'Enviada al CORE', FALSE),
    ('POR_VERIFICAR', 'Respuesta del CORE perdida', FALSE),
    ('CONFIRMADA', 'Confirmada', FALSE),
    ('RECHAZADA', 'Rechazada', TRUE),
    ('REVERTIDA', 'Revertida', TRUE);
INSERT INTO creditos.tipo_validacion_desembolso (tipo_validacion, descripcion, id_modulo_proveedor) VALUES
    ('IDENTIDAD', 'Identidad del titular', 2),
    ('CUENTA', 'Cuenta destino elegible', 3),
    ('AUTORIZACION', 'Autorización de la operación', 9),
    ('ANTIFRAUDE', 'Control antifraude', 9);
COMMIT;
