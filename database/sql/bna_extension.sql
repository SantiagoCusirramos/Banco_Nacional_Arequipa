-- Sin esto, el cliente del contenedor lee este archivo como latin1.
SET NAMES utf8mb4;

-- =====================================================================
-- Extensiones de integración de la rama mysql (MySQL 8.4)
-- =====================================================================
-- Lo que la API de integración necesita y el modelo normalizado no tiene.
-- Se carga después de sql/bna_core.sql. Queda fuera del modelo: no está en
-- modelo_bna.py, ni en el MER, ni en la rama main, y es una divergencia
-- deliberada de la versión MySQL.
-- DECISIÓN: nadie escribe directamente en estas tablas con bna_app ni bna_api; se
--   hace por los procedimientos de este archivo, que corren como bna_owner.
-- DECISIÓN: la API se conecta con el rol bna_api, que lee solo las tablas que usa y
--   ejecuta los procedimientos; no lee credenciales de tarjeta ni datos biométricos.
--   Ninguna cuenta desplegada tiene bna_app, que conserva sus permisos para los módulos
--   que aún no tienen procedimientos y para las pruebas de la matriz.
-- DECISIÓN: desbloquear una tarjeta solo es posible con el rol bna_seguridad:
--   desbloquear_tarjeta siempre registra SEGURIDAD, y cambiar_estado_tarjeta rechaza
--   todo desbloqueo y el origen SEGURIDAD. Los demás orígenes de cambiar_estado_tarjeta
--   los declara quien llama. bna_admin conserva el privilegio porque tiene ALL sobre
--   tarjetas.*, y bna_app puede escribir el historial directamente: la restricción
--   cubre a bna_api y a bna_seguridad.
-- DECISIÓN: el tope de cada canal y moneda es una fila de core.limite_canal, y sin
--   fila el débito se rechaza. Ventanilla: fila con monto nulo, «sin límite automático»
--   (Tarjetas, tabla 4). Sin fuente, y por tanto sin fila: AGE en PEN y USD, HB en USD.
-- DECISIÓN: cada procedimiento público es atómico aunque se llame sin una
--   transacción, y registra su propio evento de auditoría, de modo que la
--   operación y el evento se confirman o se deshacen juntos.
-- DECISIÓN: los catálogos de la API que no tienen equivalente exacto no se
--   agregan a la base (core.equivalencia_catalogo solo guarda los exactos).
-- DECISIÓN (v1.1): un módulo se autentica en la API con un usuario de servicio (rol
--   SERVICIO y su módulo), que se crea, renueva y revoca por procedimientos; los
--   permisos de cada rol los decide la API.
-- DECISIÓN (v1.1): bna_api no lee clientes.*: consulta, registra y cambia clientes solo
--   por los procedimientos de la sección 10, que se conceden solo a bna_api. Sus
--   mensajes de error no repiten documentos, correos ni celulares.
-- DECISIÓN (v1.1): la consulta por documento no revela si alguien es cliente mientras
--   quien llama no declare la identidad verificada; cada consulta queda en
--   clientes.validacion_identidad y en la bitácora, con quien la hizo.

-- ---------------------------------------------------------------------
-- 1. Usuarios y empleados
-- ---------------------------------------------------------------------
CREATE TABLE core.empleado (
    id_empleado     BINARY(16) NOT NULL,
    codigo_empleado VARCHAR(20) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    cargo           VARCHAR(30) NOT NULL,
    id_agencia      VARCHAR(10),
    activo          TINYINT(1) DEFAULT TRUE NOT NULL,
    CONSTRAINT pk_empleado PRIMARY KEY (id_empleado),
    CONSTRAINT uk_empleado_1 UNIQUE (codigo_empleado),
    CONSTRAINT fk_empleado_agencia FOREIGN KEY (id_agencia) REFERENCES core.agencia (id_agencia),
    CONSTRAINT ck_empleado_activo CHECK (activo IN (0, 1)),
    CONSTRAINT ck_empleado_id CHECK ((ASCII(SUBSTR(id_empleado, 7, 1)) >> 4) BETWEEN 1 AND 8
                                    AND (ASCII(SUBSTR(id_empleado, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: empleados del banco.';

CREATE TABLE core.usuario_sistema (
    id_usuario     BINARY(16) NOT NULL,
    username       VARCHAR(40) NOT NULL,
    nombre         VARCHAR(100) NOT NULL,
    rol            VARCHAR(15) NOT NULL,
    hash_password  VARCHAR(255) NOT NULL,
    algoritmo_hash VARCHAR(20) NOT NULL,
    version_hash   VARCHAR(10) NOT NULL,
    id_empleado    BINARY(16),
    activo         TINYINT(1) DEFAULT TRUE NOT NULL,
    creado_en      DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    -- Solo de los usuarios de servicio: el módulo que se autentica con este usuario.
    modulo         VARCHAR(40),
    CONSTRAINT pk_usuario_sistema PRIMARY KEY (id_usuario),
    CONSTRAINT uk_usuario_sistema_1 UNIQUE (username),
    CONSTRAINT fk_usuario_empleado FOREIGN KEY (id_empleado) REFERENCES core.empleado (id_empleado),
    CONSTRAINT fk_usuario_modulo FOREIGN KEY (modulo) REFERENCES core.modulo (nombre),
    CONSTRAINT ck_usuario_rol CHECK (rol IN ('ADMINISTRADOR', 'ASESOR', 'ANALISTA', 'OPERADOR', 'AUDITOR', 'SERVICIO')),
    CONSTRAINT ck_usuario_servicio CHECK ((rol = 'SERVICIO') = (modulo IS NOT NULL)),
    CONSTRAINT ck_usuario_activo CHECK (activo IN (0, 1)),
    CONSTRAINT ck_usuario_id CHECK ((ASCII(SUBSTR(id_usuario, 7, 1)) >> 4) BETWEEN 1 AND 8
                                    AND (ASCII(SUBSTR(id_usuario, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: usuarios; VARCHAR(255) admite bcrypt y Argon2.';

-- ---------------------------------------------------------------------
-- 2. Productos
-- ---------------------------------------------------------------------
CREATE TABLE core.producto_ahorro (
    id_producto_ahorro BINARY(16) NOT NULL,
    nombre             VARCHAR(60) NOT NULL,
    moneda             CHAR(3) NOT NULL,
    tasa_tea           DECIMAL(6,4) DEFAULT 0 NOT NULL,
    activo             TINYINT(1) DEFAULT TRUE NOT NULL,
    CONSTRAINT pk_producto_ahorro PRIMARY KEY (id_producto_ahorro),
    CONSTRAINT fk_producto_ahorro_moneda FOREIGN KEY (moneda) REFERENCES core.moneda (cod_moneda),
    CONSTRAINT ck_producto_ahorro_tea CHECK (tasa_tea >= 0),
    CONSTRAINT ck_producto_ahorro_id CHECK ((ASCII(SUBSTR(id_producto_ahorro, 7, 1)) >> 4) BETWEEN 1 AND 8
                                    AND (ASCII(SUBSTR(id_producto_ahorro, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: catálogo de productos de ahorro.';

CREATE TABLE core.producto_credito (
    id_producto_credito BINARY(16) NOT NULL,
    nombre              VARCHAR(60) NOT NULL,
    tasa_tea            DECIMAL(6,4) NOT NULL,
    plazo_min_meses     SMALLINT DEFAULT 1 NOT NULL,
    plazo_max_meses     SMALLINT DEFAULT 60 NOT NULL,
    activo              TINYINT(1) DEFAULT TRUE NOT NULL,
    CONSTRAINT pk_producto_credito PRIMARY KEY (id_producto_credito),
    CONSTRAINT ck_producto_credito_tea CHECK (tasa_tea >= 0),
    CONSTRAINT ck_producto_credito_plazo CHECK (plazo_min_meses BETWEEN 1 AND plazo_max_meses),
    CONSTRAINT ck_producto_credito_id CHECK ((ASCII(SUBSTR(id_producto_credito, 7, 1)) >> 4) BETWEEN 1 AND 8
                                    AND (ASCII(SUBSTR(id_producto_credito, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: catálogo de productos de crédito.';

-- ---------------------------------------------------------------------
-- 3. Tipos de cambio
-- ---------------------------------------------------------------------
CREATE TABLE core.tipo_cambio (
    cod_moneda_origen  CHAR(3) NOT NULL,
    cod_moneda_destino CHAR(3) NOT NULL,
    fecha              DATE NOT NULL,
    tasa               DECIMAL(12,6) NOT NULL,
    CONSTRAINT pk_tipo_cambio PRIMARY KEY (cod_moneda_origen, cod_moneda_destino, fecha),
    CONSTRAINT fk_tipo_cambio_origen FOREIGN KEY (cod_moneda_origen) REFERENCES core.moneda (cod_moneda),
    CONSTRAINT fk_tipo_cambio_destino FOREIGN KEY (cod_moneda_destino) REFERENCES core.moneda (cod_moneda),
    CONSTRAINT ck_tipo_cambio_tasa CHECK (tasa > 0),
    CONSTRAINT ck_tipo_cambio_monedas CHECK (cod_moneda_origen <> cod_moneda_destino)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: tipo de cambio diario, lo mantiene bna_admin.';

-- ---------------------------------------------------------------------
-- 4. Periodos contables
-- ---------------------------------------------------------------------
-- DECISIÓN: la base solo rechaza un periodo CERRADO. Una fecha sin periodo se
--   acepta en la base, para no exigir periodos a quien no los usa; la API
--   rechaza ese caso.
CREATE TABLE core.periodo_contable (
    anio         SMALLINT NOT NULL,
    mes          TINYINT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin    DATE NOT NULL,
    estado       VARCHAR(10) DEFAULT 'ABIERTO' NOT NULL,
    CONSTRAINT pk_periodo_contable PRIMARY KEY (anio, mes),
    CONSTRAINT ck_periodo_mes CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT ck_periodo_fechas CHECK (fecha_inicio <= fecha_fin),
    CONSTRAINT ck_periodo_estado CHECK (estado IN ('ABIERTO', 'CERRADO'))
) ENGINE = InnoDB COMMENT = 'Extensión de integración: periodos contables, los mantiene bna_admin.';

-- ---------------------------------------------------------------------
-- 5. Idempotencia de movimientos
-- ---------------------------------------------------------------------
CREATE TABLE cuentas.idempotencia_movimiento (
    llave              VARCHAR(64) NOT NULL,
    huella             CHAR(64) NOT NULL,
    uuid_transaccion   BINARY(16),
    uuid_abono         BINARY(16),
    creado_en          DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_idempotencia_movimiento PRIMARY KEY (llave),
    CONSTRAINT fk_idempotencia_movimiento FOREIGN KEY (uuid_transaccion)
        REFERENCES cuentas.movimiento (uuid_transaccion),
    CONSTRAINT fk_idempotencia_abono FOREIGN KEY (uuid_abono)
        REFERENCES cuentas.movimiento (uuid_transaccion)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: llave de idempotencia y huella de la petición.';

-- ---------------------------------------------------------------------
-- 6. Auditoría general del CORE
-- ---------------------------------------------------------------------
CREATE TABLE core.evento_auditoria (
    id_evento      BIGINT AUTO_INCREMENT,
    id_modulo      SMALLINT NOT NULL,
    entidad        VARCHAR(40) NOT NULL,
    id_entidad     VARCHAR(40) NOT NULL,
    accion         VARCHAR(60) NOT NULL,
    actor          VARCHAR(40) NOT NULL,
    correlation_id BINARY(16),
    detalle        JSON,
    fecha_hora     DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_evento_auditoria_core PRIMARY KEY (id_evento),
    CONSTRAINT fk_evento_auditoria_modulo FOREIGN KEY (id_modulo) REFERENCES core.modulo (id_modulo),
    CONSTRAINT ck_evento_auditoria_core_correlation CHECK ((ASCII(SUBSTR(correlation_id, 7, 1)) >> 4) BETWEEN 1 AND 8
                                    AND (ASCII(SUBSTR(correlation_id, 9, 1)) & 0xC0) = 0x80)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: bitácora general de solo inserción.';

-- ---------------------------------------------------------------------
-- 7. Valores de catálogo
-- ---------------------------------------------------------------------
CREATE TABLE core.equivalencia_catalogo (
    catalogo  VARCHAR(30) NOT NULL,
    valor_api VARCHAR(30) NOT NULL,
    valor_bd  VARCHAR(30) NOT NULL,
    CONSTRAINT pk_equivalencia_catalogo PRIMARY KEY (catalogo, valor_api)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: valores de la API con equivalente exacto.';

INSERT INTO core.equivalencia_catalogo (catalogo, valor_api, valor_bd) VALUES
    ('estado_tarjeta', 'ANULADA', 'CANCELADA'),
    ('origen_cambio', 'BANCO', 'OPERADOR');

-- Cuentas contables de los asientos de cuentas.aplicar_movimiento.
INSERT INTO core.cuenta_contable VALUES
    ('1101', 'Caja', 'DEUDORA', NULL), ('2101', 'Depósitos de ahorro', 'ACREEDORA', NULL) AS nueva
ON DUPLICATE KEY UPDATE codigo_contable = nueva.codigo_contable;

-- Códigos de respuesta de una autorización rechazada (v1.5), los de ISO 8583.
INSERT INTO tarjetas.codigo_respuesta (cod_respuesta, descripcion, es_aprobacion) VALUES
    ('51', 'Fondos insuficientes', FALSE),
    ('57', 'Operación no permitida para la tarjeta o la cuenta', FALSE),
    ('61', 'Excede el tope diario', FALSE),
    ('62', 'Tarjeta restringida', FALSE);

-- ---------------------------------------------------------------------
-- 8. Procedimientos y reglas
-- ---------------------------------------------------------------------
-- Los procedimientos públicos siguen el patrón de core.registrar_asiento: sin una
-- transacción abierta abren la suya; dentro de una usan un savepoint. Si algo
-- falla no queda nada de la operación, tampoco la llave de idempotencia.
DELIMITER //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER core.tg_asiento_periodo_abierto BEFORE INSERT ON core.asiento_contable
FOR EACH ROW BEGIN
    IF EXISTS (SELECT 1 FROM core.periodo_contable
                WHERE NEW.fecha_contable BETWEEN fecha_inicio AND fecha_fin AND estado = 'CERRADO') THEN
        CALL core.fallar(CONCAT('BNA-PERIODO: el periodo de ', NEW.fecha_contable, ' está cerrado'));
    END IF;
END //

-- bna_admin aún puede vaciar esta bitácora con TRUNCATE: es la brecha G03.
CREATE DEFINER = 'bna_owner'@'%' TRIGGER core.tg_evento_auditoria_solo_insercion_bu
BEFORE UPDATE ON core.evento_auditoria
FOR EACH ROW BEGIN CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.evento_auditoria', 'UPDATE'); END //

CREATE DEFINER = 'bna_owner'@'%' TRIGGER core.tg_evento_auditoria_solo_insercion_bd
BEFORE DELETE ON core.evento_auditoria
FOR EACH ROW BEGIN CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.evento_auditoria', 'DELETE'); END //

-- Interno: nadie más lo ejecuta, para que no se puedan fabricar eventos.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.registrar_evento(
    IN p_modulo VARCHAR(100), IN p_entidad VARCHAR(40), IN p_id_entidad VARCHAR(40), IN p_accion VARCHAR(60),
    IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), IN p_detalle JSON)
    COMMENT 'Registra un evento en la bitácora general.'
BEGIN
    DECLARE v_id SMALLINT;
    SELECT id_modulo INTO v_id FROM core.modulo WHERE nombre = p_modulo;
    IF v_id IS NULL THEN
        CALL core.fallar(CONCAT('BNA-AUDITORIA: módulo desconocido ', coalesce(p_modulo, '(nulo)')));
    END IF;
    INSERT INTO core.evento_auditoria (id_modulo, entidad, id_entidad, accion, actor, correlation_id, detalle)
    VALUES (v_id, p_entidad, p_id_entidad, p_accion, p_actor, p_correlation_id, p_detalle);
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.crear_usuario(
    IN p_id BINARY(16), IN p_username VARCHAR(40), IN p_nombre VARCHAR(100), IN p_rol VARCHAR(15),
    IN p_hash VARCHAR(255), IN p_algoritmo VARCHAR(20), IN p_version VARCHAR(10),
    IN p_id_empleado BINARY(16), IN p_activo BOOLEAN, IN p_actor VARCHAR(40))
    COMMENT 'Crea un usuario del sistema.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        INSERT INTO core.usuario_sistema (id_usuario, username, nombre, rol, hash_password, algoritmo_hash,
                                          version_hash, id_empleado, activo)
        VALUES (p_id, p_username, p_nombre, p_rol, p_hash, p_algoritmo, p_version, p_id_empleado, p_activo);
        CALL core.registrar_evento('CORE', 'usuario_sistema', BIN_TO_UUID(p_id), 'CREAR_USUARIO', p_actor, NULL,
                                   JSON_OBJECT('username', p_username, 'rol', p_rol));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.asignar_rol(
    IN p_id BINARY(16), IN p_rol VARCHAR(15), IN p_actor VARCHAR(40), OUT p_filas INT)
    COMMENT 'Cambia el rol de un usuario.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_anterior VARCHAR(15);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT rol INTO v_anterior FROM core.usuario_sistema WHERE id_usuario = p_id FOR UPDATE;
        UPDATE core.usuario_sistema SET rol = p_rol WHERE id_usuario = p_id;
        SET p_filas = ROW_COUNT();
        IF p_filas = 1 THEN
            CALL core.registrar_evento('CORE', 'usuario_sistema', BIN_TO_UUID(p_id), 'ASIGNAR_ROLES', p_actor, NULL,
                                       JSON_OBJECT('rol_anterior', v_anterior, 'rol_nuevo', p_rol));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Con logins simultáneos solo uno actualiza la fila y deja el evento.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.migrar_hash_usuario(
    IN p_id BINARY(16), IN p_algoritmo_anterior VARCHAR(20), IN p_hash VARCHAR(255),
    IN p_algoritmo VARCHAR(20), IN p_version VARCHAR(10), IN p_actor VARCHAR(40), OUT p_filas INT)
    COMMENT 'Migra el hash de un usuario si sigue en el algoritmo anterior.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        UPDATE core.usuario_sistema
           SET hash_password = p_hash, algoritmo_hash = p_algoritmo, version_hash = p_version
         WHERE id_usuario = p_id AND algoritmo_hash = p_algoritmo_anterior;
        SET p_filas = ROW_COUNT();
        IF p_filas = 1 THEN
            CALL core.registrar_evento('CORE', 'usuario_sistema', BIN_TO_UUID(p_id), 'MIGRAR_HASH_PASSWORD',
                                       p_actor, NULL,
                                       JSON_OBJECT('algoritmo_anterior', p_algoritmo_anterior,
                                                   'algoritmo_nuevo', p_algoritmo));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Reserva la llave antes de operar: una petición simultánea con la misma llave
-- espera en el índice único hasta que la primera confirme o deshaga. FOR SHARE lee lo
-- último confirmado sin pedir un bloqueo exclusivo, que entre varias peticiones en
-- espera produciría deadlocks.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE cuentas.reservar_llave(
    IN p_llave VARCHAR(64), IN p_huella CHAR(64), OUT p_repetido BOOLEAN,
    OUT p_uuid BINARY(16), OUT p_abono BINARY(16))
    COMMENT 'Reserva una llave de idempotencia o devuelve la operación que ya la usó.'
BEGIN
    DECLARE v_duplicada BOOLEAN DEFAULT FALSE;
    DECLARE v_huella CHAR(64);
    DECLARE CONTINUE HANDLER FOR 1062 SET v_duplicada = TRUE;
    SET p_repetido = FALSE;
    IF p_llave IS NOT NULL THEN
        INSERT INTO cuentas.idempotencia_movimiento (llave, huella) VALUES (p_llave, p_huella);
        IF v_duplicada THEN
            SELECT huella, uuid_transaccion, uuid_abono INTO v_huella, p_uuid, p_abono
              FROM cuentas.idempotencia_movimiento WHERE llave = p_llave FOR SHARE;
            IF NOT (v_huella <=> p_huella) THEN
                CALL core.fallar(CONCAT('BNA-IDEMPOTENCIA: la llave ', p_llave, ' se usó con otros parámetros'));
            END IF;
            IF p_uuid IS NULL THEN
                CALL core.fallar(CONCAT('BNA-IDEMPOTENCIA: la llave ', p_llave, ' no tiene una operación registrada'));
            END IF;
            SET p_repetido = TRUE;
        END IF;
    END IF;
END //

-- El canal es obligatorio: el tope diario de core depende de él. Un débito por ATM
-- pasa por la autorización de Tarjetas, que aplica sus propias reglas (RN-ATM-005).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE cuentas.validar_canal(IN p_canal VARCHAR(5), IN p_debito BOOLEAN)
    COMMENT 'Valida el canal de un movimiento.'
BEGIN
    DECLARE v_activo BOOLEAN;
    IF p_canal IS NULL THEN
        CALL core.fallar('BNA-CANAL: el canal es obligatorio');
    END IF;
    SELECT activo INTO v_activo FROM core.canal WHERE id_canal = p_canal;
    IF v_activo IS NULL THEN
        CALL core.fallar(CONCAT('BNA-CANAL: canal desconocido ', p_canal));
    END IF;
    IF NOT v_activo THEN
        CALL core.fallar(CONCAT('BNA-CANAL: el canal ', p_canal, ' no está activo'));
    END IF;
    IF p_debito AND p_canal = 'ATM' THEN
        CALL core.fallar('BNA-CANAL: un débito por ATM exige una autorización de tarjeta');
    END IF;
END //

-- Interno. Un movimiento con su asiento de partida doble (1101 Caja, 2101
-- Depósitos). Los triggers de cuentas.movimiento validan saldo, estado y tope.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE cuentas.aplicar_movimiento(
    IN p_cuenta VARCHAR(20), IN p_tipo VARCHAR(25), IN p_monto DECIMAL(15,2), IN p_glosa VARCHAR(200),
    IN p_canal VARCHAR(5), IN p_correlation_id BINARY(16), OUT p_uuid BINARY(16))
    COMMENT 'Registra un movimiento y su asiento.'
BEGIN
    DECLARE v_nat CHAR(1);
    DECLARE v_moneda CHAR(3);
    DECLARE v_asiento BINARY(16);
    DECLARE v_fecha DATE DEFAULT core.fn_fecha_negocio(UTC_TIMESTAMP(6));
    SELECT naturaleza INTO v_nat FROM cuentas.tipo_operacion WHERE tipo_operacion = p_tipo;
    SELECT moneda INTO v_moneda FROM cuentas.cuenta_ahorro WHERE num_cuenta = p_cuenta;
    IF v_moneda IS NULL THEN
        CALL core.fallar(CONCAT('BNA-CUENTA: no existe la cuenta ', coalesce(p_cuenta, '(nula)')));
    END IF;
    CALL core.registrar_asiento(NULL, CONCAT('A-', HEX(RANDOM_BYTES(8))), v_fecha, v_fecha, p_glosa, v_moneda,
        p_correlation_id, NULL,
        JSON_ARRAY(JSON_OBJECT('partida', IF(v_nat = 'C', 'DEBE', 'HABER'), 'importe', p_monto, 'cuenta', '1101'),
                   JSON_OBJECT('partida', IF(v_nat = 'C', 'HABER', 'DEBE'), 'importe', p_monto, 'cuenta', '2101')),
        v_asiento);
    SET p_uuid = core.uuid_v4();
    INSERT INTO cuentas.movimiento (uuid_transaccion, tipo_operacion, monto, glosa, estado_transaccion,
                                    id_asiento, num_cuenta, id_canal)
    VALUES (p_uuid, p_tipo, p_monto, p_glosa, 'APROBADO', v_asiento, p_cuenta, p_canal);
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE cuentas.registrar_movimiento(
    IN p_cuenta VARCHAR(20), IN p_tipo VARCHAR(25), IN p_monto DECIMAL(15,2), IN p_glosa VARCHAR(200),
    IN p_canal VARCHAR(5), IN p_correlation_id BINARY(16), IN p_llave VARCHAR(64), IN p_huella CHAR(64),
    IN p_actor VARCHAR(40), OUT p_uuid BINARY(16), OUT p_repetido BOOLEAN)
    COMMENT 'Depósito o retiro idempotente.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_abono BINARY(16);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_tipo IS NULL OR p_tipo NOT IN ('DEPOSITO', 'RETIRO') THEN
            CALL core.fallar(CONCAT('BNA-MOVIMIENTO: solo se admite DEPOSITO o RETIRO, no ', coalesce(p_tipo, '(nulo)')));
        END IF;
        CALL cuentas.validar_canal(p_canal, p_tipo = 'RETIRO');
        CALL cuentas.reservar_llave(p_llave, p_huella, p_repetido, p_uuid, v_abono);
        IF NOT p_repetido THEN
            CALL cuentas.aplicar_movimiento(p_cuenta, p_tipo, p_monto, p_glosa, p_canal, p_correlation_id, p_uuid);
            IF p_llave IS NOT NULL THEN
                UPDATE cuentas.idempotencia_movimiento SET uuid_transaccion = p_uuid WHERE llave = p_llave;
            END IF;
            CALL core.registrar_evento('CUENTAS', 'movimiento', BIN_TO_UUID(p_uuid), p_tipo, p_actor, p_correlation_id,
                                       JSON_OBJECT('num_cuenta', p_cuenta, 'monto', p_monto, 'canal', p_canal));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Bloquea las dos cuentas en orden de num_cuenta, para que dos transferencias
-- opuestas no se bloqueen entre sí. Cada tramo lleva su propio asiento
-- (uk_movimiento_1).
-- DECISIÓN: entre monedas distintas se rechaza hasta que se defina la regla de
--   conversión.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE cuentas.registrar_transferencia(
    IN p_origen VARCHAR(20), IN p_destino VARCHAR(20), IN p_monto DECIMAL(15,2), IN p_glosa VARCHAR(200),
    IN p_canal VARCHAR(5), IN p_correlation_id BINARY(16), IN p_llave VARCHAR(64), IN p_huella CHAR(64),
    IN p_actor VARCHAR(40), OUT p_debito BINARY(16), OUT p_abono BINARY(16), OUT p_repetido BOOLEAN)
    COMMENT 'Transferencia idempotente entre dos cuentas de la misma moneda.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_moneda_1, v_moneda_2 CHAR(3);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_origen IS NULL OR p_destino IS NULL THEN
            CALL core.fallar('BNA-CUENTA: la transferencia exige cuenta de origen y de destino');
        END IF;
        IF p_origen = p_destino THEN
            CALL core.fallar('BNA-TRANSFERENCIA: la cuenta de origen y la de destino son la misma');
        END IF;
        CALL cuentas.validar_canal(p_canal, TRUE);
        CALL cuentas.reservar_llave(p_llave, p_huella, p_repetido, p_debito, p_abono);
        IF NOT p_repetido THEN
            SELECT moneda INTO v_moneda_1 FROM cuentas.cuenta_ahorro
             WHERE num_cuenta = LEAST(p_origen, p_destino) FOR UPDATE;
            SELECT moneda INTO v_moneda_2 FROM cuentas.cuenta_ahorro
             WHERE num_cuenta = GREATEST(p_origen, p_destino) FOR UPDATE;
            IF v_moneda_1 IS NULL OR v_moneda_2 IS NULL THEN
                CALL core.fallar(CONCAT('BNA-CUENTA: no existe ', p_origen, ' o ', p_destino));
            END IF;
            IF v_moneda_1 <> v_moneda_2 THEN
                CALL core.fallar('BNA-MONEDA: transferencia entre monedas distintas');
            END IF;
            CALL cuentas.aplicar_movimiento(p_origen, 'TRANSFERENCIA_ENVIADA', p_monto, p_glosa, p_canal,
                                            p_correlation_id, p_debito);
            CALL cuentas.aplicar_movimiento(p_destino, 'TRANSFERENCIA_RECIBIDA', p_monto, p_glosa, p_canal,
                                            p_correlation_id, p_abono);
            IF p_llave IS NOT NULL THEN
                UPDATE cuentas.idempotencia_movimiento SET uuid_transaccion = p_debito, uuid_abono = p_abono
                 WHERE llave = p_llave;
            END IF;
            CALL core.registrar_evento('CUENTAS', 'movimiento', BIN_TO_UUID(p_debito), 'TRANSFERENCIA', p_actor,
                                       p_correlation_id,
                                       JSON_OBJECT('origen', p_origen, 'destino', p_destino, 'monto', p_monto,
                                                   'canal', p_canal, 'uuid_abono', BIN_TO_UUID(p_abono)));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE cuentas.abrir_cuenta(
    IN p_num_cuenta VARCHAR(20), IN p_cci CHAR(20), IN p_moneda CHAR(3), IN p_regimen VARCHAR(25),
    IN p_id_agencia VARCHAR(10), IN p_titulares JSON, IN p_actor VARCHAR(40))
    COMMENT 'Abre una cuenta con sus titulares ["C001", ...].'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_minimo SMALLINT;
    DECLARE v_n, v_distintos, v_aptos INT;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT min_titulares INTO v_minimo FROM cuentas.regimen_cuenta WHERE cod_regimen = p_regimen;
        IF v_minimo IS NULL THEN
            CALL core.fallar(CONCAT('BNA-REGIMEN: régimen desconocido ', coalesce(p_regimen, '(nulo)')));
        END IF;
        IF p_titulares IS NULL OR JSON_TYPE(p_titulares) <> 'ARRAY' THEN
            CALL core.fallar('BNA-REGIMEN: los titulares deben ser una lista');
        END IF;
        SELECT COUNT(*), COUNT(DISTINCT t.cod_cliente), COUNT(e.cod_estado)
          INTO v_n, v_distintos, v_aptos
          FROM JSON_TABLE(p_titulares, '$[*]' COLUMNS (
                   cod_cliente VARCHAR(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs PATH '$')) AS t
          LEFT JOIN clientes.cliente c ON c.cod_cliente = t.cod_cliente
          LEFT JOIN clientes.estado_cliente e ON e.cod_estado = c.estado_cliente AND e.permite_operar;
        IF v_distintos <> v_n THEN
            CALL core.fallar('BNA-REGIMEN: un titular está repetido');
        END IF;
        IF v_n < v_minimo THEN
            CALL core.fallar(CONCAT('BNA-REGIMEN: el régimen ', p_regimen, ' exige ', v_minimo, ' titulares'));
        END IF;
        IF p_regimen = 'INDIVIDUAL' AND v_n > 1 THEN
            CALL core.fallar('BNA-REGIMEN: una cuenta INDIVIDUAL tiene un solo titular');
        END IF;
        IF v_aptos <> v_n THEN
            CALL core.fallar('BNA-TITULAR: un titular no existe o no puede operar');
        END IF;
        INSERT INTO cuentas.cuenta_ahorro (num_cuenta, cci, moneda, regimen, estado_cuenta, id_agencia)
        VALUES (p_num_cuenta, p_cci, p_moneda, p_regimen, 'ACTIVA', p_id_agencia);
        INSERT INTO cuentas.titularidad (cod_cliente, num_cuenta)
        SELECT t.cod_cliente, p_num_cuenta
          FROM JSON_TABLE(p_titulares, '$[*]' COLUMNS (cod_cliente VARCHAR(12) PATH '$')) AS t;
        CALL core.registrar_evento('CUENTAS', 'cuenta_ahorro', p_num_cuenta, 'ABRIR_CUENTA', p_actor, NULL,
                                   JSON_OBJECT('regimen', p_regimen, 'titulares', p_titulares));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.emitir_tarjeta(
    IN p_id BINARY(16), IN p_pan_token VARCHAR(32), IN p_bin CHAR(6), IN p_ultimos4 CHAR(4),
    IN p_emision DATE, IN p_vencimiento DATE, IN p_cod_cliente VARCHAR(12), IN p_num_cuenta VARCHAR(20),
    IN p_actor VARCHAR(40))
    COMMENT 'Emite una tarjeta PENDIENTE_ACTIVACION vinculada a una cuenta de su titular.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF NOT EXISTS (SELECT 1 FROM cuentas.titularidad
                        WHERE cod_cliente = p_cod_cliente AND num_cuenta = p_num_cuenta) THEN
            CALL core.fallar('BNA-TARJETA: el cliente no es titular de la cuenta');
        END IF;
        SELECT estado_cuenta INTO v_estado FROM cuentas.cuenta_ahorro WHERE num_cuenta = p_num_cuenta;
        IF v_estado = 'CANCELADA' THEN
            CALL core.fallar('BNA-TARJETA: la cuenta está cancelada');
        END IF;
        INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento,
                                      estado_tarjeta, cod_cliente)
        VALUES (p_id, p_pan_token, p_bin, p_ultimos4, p_emision, p_vencimiento, 'PENDIENTE_ACTIVACION', p_cod_cliente);
        INSERT INTO tarjetas.tarjeta_cuenta (id_tarjeta, num_cuenta, es_principal) VALUES (p_id, p_num_cuenta, TRUE);
        CALL core.registrar_evento('CORE', 'tarjeta', BIN_TO_UUID(p_id), 'EMITIR_TARJETA', p_actor, NULL,
                                   JSON_OBJECT('cod_cliente', p_cod_cliente, 'num_cuenta', p_num_cuenta));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.cambiar_estado_tarjeta(
    IN p_id BINARY(16), IN p_estado VARCHAR(25), IN p_motivo VARCHAR(255), IN p_origen VARCHAR(20),
    IN p_actor VARCHAR(40), OUT p_id_historial BIGINT)
    COMMENT 'Cambia el estado de una tarjeta por su historial.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_anterior VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT estado_tarjeta INTO v_anterior FROM tarjetas.tarjeta WHERE id_tarjeta = p_id FOR UPDATE;
        IF v_anterior IS NULL THEN
            CALL core.fallar('BNA-TARJETA: la tarjeta no existe');
        END IF;
        IF v_anterior IN ('BLOQUEADA', 'RETENIDA') AND p_estado = 'ACTIVA' THEN
            CALL core.fallar('BNA-DESBLOQUEO: el desbloqueo solo lo hace el módulo de Seguridad');
        END IF;
        IF p_origen = 'SEGURIDAD' THEN
            CALL core.fallar('BNA-ORIGEN: el origen SEGURIDAD solo lo registra el módulo de Seguridad');
        END IF;
        INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
        VALUES (p_estado, p_motivo, p_origen, p_id);
        SET p_id_historial = LAST_INSERT_ID();
        CALL core.registrar_evento('CORE', 'tarjeta', BIN_TO_UUID(p_id), 'CAMBIAR_ESTADO_TARJETA', p_actor, NULL,
                                   JSON_OBJECT('estado_anterior', v_anterior, 'estado_nuevo', p_estado,
                                               'origen', p_origen, 'id_historial', p_id_historial));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.desbloquear_tarjeta(
    IN p_id BINARY(16), IN p_motivo VARCHAR(255), IN p_actor VARCHAR(40), OUT p_id_historial BIGINT)
    COMMENT 'Desbloquea una tarjeta BLOQUEADA o RETENIDA, con origen SEGURIDAD.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_anterior VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT estado_tarjeta INTO v_anterior FROM tarjetas.tarjeta WHERE id_tarjeta = p_id FOR UPDATE;
        IF v_anterior IS NULL OR v_anterior NOT IN ('BLOQUEADA', 'RETENIDA') THEN
            CALL core.fallar('BNA-DESBLOQUEO: la tarjeta no está bloqueada');
        END IF;
        INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
        VALUES ('ACTIVA', p_motivo, 'SEGURIDAD', p_id);
        SET p_id_historial = LAST_INSERT_ID();
        CALL core.registrar_evento('CORE', 'tarjeta', BIN_TO_UUID(p_id), 'DESBLOQUEAR_TARJETA', p_actor, NULL,
                                   JSON_OBJECT('estado_anterior', v_anterior, 'id_historial', p_id_historial));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Autorización de una operación con tarjeta (v1.5). Las reglas son las de
-- tg_autorizacion_validar_bi: este procedimiento solo es la entrada de la API.
-- DECISIÓN (v1.5): el uuid lo genera quien llama (RN-BUS-002). Repetirlo con los mismos
--   datos devuelve el resultado ya registrado sin tocar el saldo ni el tope; con otros
--   datos falla con BNA-IDEMPOTENCIA.
-- DECISIÓN (v1.5): una regla de negocio que no se cumple no es un error de la llamada:
--   queda la autorización RECHAZADA, con su código de respuesta y un motivo sin montos
--   ni saldos, como evidencia del intento. Los demás errores se propagan.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.autorizar_operacion(
    IN p_uuid BINARY(16), IN p_id_tarjeta BINARY(16), IN p_num_cuenta VARCHAR(20), IN p_id_canal VARCHAR(5),
    IN p_id_terminal VARCHAR(30), IN p_tipo_operacion VARCHAR(25), IN p_monto DECIMAL(15,2),
    IN p_ip_origen VARCHAR(45), IN p_actor VARCHAR(40), OUT p_estado VARCHAR(25), OUT p_codigo VARCHAR(4))
    COMMENT 'Autoriza una operación con tarjeta o registra su rechazo.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_existe BOOLEAN DEFAULT FALSE;
    DECLARE v_mismos BOOLEAN;
    DECLARE v_regla VARCHAR(30);
    DECLARE v_motivo VARCHAR(255);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT TRUE, estado_autorizacion, codigo_respuesta,
               id_tarjeta <=> p_id_tarjeta AND num_cuenta <=> p_num_cuenta AND id_canal <=> p_id_canal
               AND id_terminal <=> p_id_terminal AND tipo_operacion <=> p_tipo_operacion AND monto <=> p_monto
          INTO v_existe, p_estado, p_codigo, v_mismos
          FROM tarjetas.autorizacion WHERE uuid_autorizacion = p_uuid FOR UPDATE;
        IF v_existe AND NOT v_mismos THEN
            CALL core.fallar(CONCAT('BNA-IDEMPOTENCIA: la autorización ', BIN_TO_UUID(p_uuid),
                                    ' se registró con otros datos'));
        END IF;
        IF NOT v_existe THEN
            IF p_monto IS NULL OR p_monto <= 0 THEN
                CALL core.fallar('BNA-MONTO: el monto debe ser mayor que cero');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM tarjetas.tarjeta WHERE id_tarjeta = p_id_tarjeta) THEN
                CALL core.fallar('BNA-TARJETA: la tarjeta no existe');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM tarjetas.tarjeta_cuenta
                            WHERE id_tarjeta = p_id_tarjeta AND num_cuenta = p_num_cuenta) THEN
                CALL core.fallar('BNA-TARJETA: la tarjeta no opera esa cuenta');
            END IF;
            BEGIN
                -- Las reglas de tg_autorizacion_validar_bi fallan con SIGNAL 45000. Los
                -- códigos de respuesta son los de ISO 8583 (sección 7).
                DECLARE EXIT HANDLER FOR SQLSTATE '45000'
                BEGIN
                    GET STACKED DIAGNOSTICS CONDITION 1 v_motivo = MESSAGE_TEXT;
                    SET v_regla = SUBSTRING_INDEX(v_motivo, ':', 1);
                    SET p_codigo = CASE
                        WHEN v_regla = 'ERR-TAR-003' AND v_motivo LIKE '%venció%' THEN '54'
                        WHEN v_regla = 'ERR-TAR-003' THEN '62'
                        WHEN v_regla = 'ERR-TAR-007' THEN '61'
                        WHEN v_regla = 'BNA-SALDO' THEN '51'
                        WHEN v_regla IN ('ERR-TAR-006', 'ERR-TAR-008', 'BNA-ESTADO-CUENTA') THEN '57'
                    END;
                    IF p_codigo IS NULL THEN
                        RESIGNAL;
                    END IF;
                    SET v_motivo = CASE v_regla
                        WHEN 'ERR-TAR-003' THEN 'ERR-TAR-003: la tarjeta no está operativa o venció'
                        WHEN 'ERR-TAR-006' THEN 'ERR-TAR-006: el canal o la terminal no opera'
                        WHEN 'ERR-TAR-007' THEN 'ERR-TAR-007: tope diario excedido (RN-TOP-001)'
                        WHEN 'ERR-TAR-008' THEN 'ERR-TAR-008: la cuenta no puede operarse en cajero (RN-ATM-005)'
                        WHEN 'BNA-SALDO' THEN 'BNA-SALDO: saldo disponible insuficiente'
                        ELSE 'BNA-ESTADO-CUENTA: la cuenta no admite débitos'
                    END;
                    INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion,
                                                       codigo_respuesta, motivo_rechazo, id_terminal, ip_origen,
                                                       id_tarjeta, num_cuenta, id_canal)
                    VALUES (p_uuid, p_tipo_operacion, p_monto, 'RECHAZADA', p_codigo, v_motivo, p_id_terminal,
                            p_ip_origen, p_id_tarjeta, p_num_cuenta, p_id_canal);
                    SET p_estado = 'RECHAZADA';
                END;
                INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion,
                                                   codigo_respuesta, id_terminal, ip_origen, id_tarjeta, num_cuenta,
                                                   id_canal)
                VALUES (p_uuid, p_tipo_operacion, p_monto, 'AUTORIZADA', '00', p_id_terminal, p_ip_origen,
                        p_id_tarjeta, p_num_cuenta, p_id_canal);
                SET p_estado = 'AUTORIZADA', p_codigo = '00';
            END;
            CALL core.registrar_evento('CORE', 'autorizacion', BIN_TO_UUID(p_uuid), 'AUTORIZAR_OPERACION', p_actor,
                                       NULL, JSON_OBJECT('id_tarjeta', BIN_TO_UUID(p_id_tarjeta),
                                                         'num_cuenta', p_num_cuenta, 'estado', p_estado,
                                                         'codigo_respuesta', p_codigo));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- DECISIÓN (v1.5): el extorno por la API es el de una autorización sin movimiento: los
--   triggers liberan el tope y el saldo retenido (RN-ATM-003). Si la operación ya se
--   contabilizó, se revierte con su movimiento inverso, que no es de este procedimiento.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.extornar_autorizacion(
    IN p_uuid BINARY(16), IN p_motivo VARCHAR(255), IN p_actor VARCHAR(40), OUT p_estado VARCHAR(25))
    COMMENT 'Extorna una autorización que aún no tiene movimiento.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_anterior VARCHAR(25);
    DECLARE v_trx BINARY(16);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT estado_autorizacion, uuid_transaccion INTO v_anterior, v_trx
          FROM tarjetas.autorizacion WHERE uuid_autorizacion = p_uuid FOR UPDATE;
        IF v_anterior IS NULL THEN
            CALL core.fallar('BNA-AUTORIZACION: la autorización no existe');
        END IF;
        IF v_anterior <> 'EXTORNADA' THEN
            IF v_anterior = 'RECHAZADA' THEN
                CALL core.fallar('BNA-EXTORNO: una autorización rechazada no se extorna');
            END IF;
            IF v_trx IS NOT NULL THEN
                CALL core.fallar('BNA-EXTORNO: la operación ya tiene su movimiento');
            END IF;
            UPDATE tarjetas.autorizacion SET estado_autorizacion = 'EXTORNADA', codigo_respuesta = 'EXT'
             WHERE uuid_autorizacion = p_uuid;
            CALL core.registrar_evento('CORE', 'autorizacion', BIN_TO_UUID(p_uuid), 'EXTORNAR_AUTORIZACION', p_actor,
                                       NULL, JSON_OBJECT('estado_anterior', v_anterior, 'motivo', p_motivo));
        END IF;
        SET p_estado = 'EXTORNADA';
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Confirmación de autorización (v1.8): convierte una autorización retenida en el débito
-- real al dispensar el cajero. Solo autorizaciones AUTORIZADA o DISPENSADA sin movimiento
-- (uuid_transaccion IS NULL). Usa la llave de idempotencia para que repetir la
-- confirmación no debite dos veces. El movimiento lleva el mismo uuid que la
-- autorización (RN-BUS-002) y se registra con cuentas.aplicar_movimiento (el
-- procedimiento interno que usa la base), no con INSERT directo.
-- DECISIÓN (v1.8): el estado final de la autorización es DISPENSADA, que es la
--   transición válida desde AUTORIZADA según tg_autorizacion_validar_bu. La
--   retención se libera porque el movimiento descuenta saldo_contable y el
--   disponible ya se descontó al autorizar; tras confirmar, ambos coinciden.
-- DECISIÓN (v1.8): después de confirmar, extornar_autorizacion falla porque la
--   autorización ya tiene su movimiento (uuid_transaccion NOT NULL).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.confirmar_autorizacion(
    IN p_uuid_autorizacion BINARY(16), IN p_llave_idempotencia VARCHAR(64), IN p_huella CHAR(64),
    IN p_actor VARCHAR(40), IN p_id_canal VARCHAR(5), IN p_id_terminal VARCHAR(30),
    OUT p_uuid_transaccion BINARY(16), OUT p_estado VARCHAR(25))
    COMMENT 'Confirma una autorización retenida: registra el movimiento real y pasa a DISPENSADA.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_anterior VARCHAR(25);
    DECLARE v_tipo_operacion VARCHAR(25);
    DECLARE v_monto DECIMAL(15,2);
    DECLARE v_num_cuenta VARCHAR(20);
    DECLARE v_id_canal VARCHAR(5);
    DECLARE v_id_terminal VARCHAR(30);
    DECLARE v_fecha_hora DATETIME(6);
    DECLARE v_trx BINARY(16);
    DECLARE v_repetido BOOLEAN DEFAULT FALSE;
    DECLARE v_abono BINARY(16);
    DECLARE v_glosa VARCHAR(200);
    DECLARE v_correlation_id BINARY(16);
    DECLARE v_asiento BINARY(16);
    DECLARE v_nat CHAR(1);
    DECLARE v_moneda CHAR(3);
    DECLARE v_aut_canal VARCHAR(5);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    bna_confirmar: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        -- Bloquea la fila de la autorización para serializar confirmaciones concurrentes.
        SELECT estado_autorizacion, tipo_operacion, monto, num_cuenta, id_canal, id_terminal,
               fecha_hora, uuid_transaccion
          INTO v_anterior, v_tipo_operacion, v_monto, v_num_cuenta, v_id_canal, v_id_terminal,
               v_fecha_hora, v_trx
          FROM tarjetas.autorizacion WHERE uuid_autorizacion = p_uuid_autorizacion FOR UPDATE;
        IF v_anterior IS NULL THEN
            CALL core.fallar('BNA-AUTORIZACION: la autorización no existe');
        END IF;
        -- Reserva la llave de idempotencia primero: si es repetida, devolvemos el
        -- resultado existente sin validar el estado (idempotencia).
        CALL cuentas.reservar_llave(p_llave_idempotencia, p_huella, v_repetido, p_uuid_transaccion, v_abono);
        IF v_repetido THEN
            -- La llave ya se usó: verificamos que el movimiento existente pertenezca
            -- a esta autorización y devolvemos el mismo resultado.
            IF p_uuid_transaccion IS NULL OR NOT EXISTS (
                SELECT 1 FROM tarjetas.autorizacion
                WHERE uuid_autorizacion = p_uuid_autorizacion AND uuid_transaccion = p_uuid_transaccion
            ) THEN
                CALL core.fallar('BNA-IDEMPOTENCIA: la llave se usó en otra operación');
            END IF;
            SET p_estado = 'DISPENSADA';
            IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
            LEAVE bna_confirmar;
        END IF;
        -- Solo se confirma una autorización vigente (AUTORIZADA o DISPENSADA) sin movimiento.
        IF v_anterior NOT IN ('AUTORIZADA', 'DISPENSADA') OR v_trx IS NOT NULL THEN
            CALL core.fallar('BNA-CONFIRMACION: la autorización no está en estado vigente');
        END IF;
        -- v1.11: una retención que pasó el plazo ya no se confirma, aunque el evento aún
        -- no la haya liberado (sección 16).
        IF v_anterior = 'AUTORIZADA'
           AND v_fecha_hora < UTC_TIMESTAMP(6) - INTERVAL tarjetas.fn_minutos_retencion() MINUTE THEN
            CALL core.fallar('BNA-CONFIRMACION: la retención venció');
        END IF;
        -- Valida que el canal/terminal coincida con la autorización (seguridad).
        -- La autorización tiene either id_canal OR id_terminal (CHECK constraint).
        -- Aceptamos si el canal proporcionado coincide con el de la autorización
        -- (derivado de la terminal si la autorización usó terminal).
        IF p_id_canal IS NOT NULL THEN
            SELECT coalesce(v_id_canal, (SELECT id_canal FROM core.terminal WHERE id_terminal = v_id_terminal)) INTO v_aut_canal;
            IF NOT (p_id_canal <=> v_aut_canal) THEN
                CALL core.fallar('BNA-CONFIRMACION: el canal no coincide con la autorización');
            END IF;
        END IF;
        IF p_id_terminal IS NOT NULL AND NOT (p_id_terminal <=> v_id_terminal) THEN
            CALL core.fallar('BNA-CONFIRMACION: la terminal no coincide con la autorización');
        END IF;
        -- Genera correlation_id y glosa para el movimiento.
        SET v_correlation_id = core.uuid_v4();
        SET v_glosa = CONCAT('Confirmación ', BIN_TO_UUID(p_uuid_autorizacion));
        -- Registra el movimiento con el MISMO uuid que la autorización (RN-BUS-002).
        -- Usamos cuentas.aplicar_movimiento (interno) para poder fijar el uuid.
        -- La fecha contable usa la fecha de negocio ACTUAL (como cuentas.aplicar_movimiento),
        -- no la de la autorización.
        SELECT naturaleza INTO v_nat FROM cuentas.tipo_operacion WHERE tipo_operacion = v_tipo_operacion;
        SELECT moneda INTO v_moneda FROM cuentas.cuenta_ahorro WHERE num_cuenta = v_num_cuenta;
        CALL core.registrar_asiento(NULL, CONCAT('A-', HEX(RANDOM_BYTES(8))), core.fn_fecha_negocio(UTC_TIMESTAMP(6)), core.fn_fecha_negocio(UTC_TIMESTAMP(6)),
                                    v_glosa, v_moneda, v_correlation_id, NULL,
                                    JSON_ARRAY(JSON_OBJECT('partida', IF(v_nat = 'C', 'DEBE', 'HABER'), 'importe', v_monto, 'cuenta', '1101'),
                                               JSON_OBJECT('partida', IF(v_nat = 'C', 'HABER', 'DEBE'), 'importe', v_monto, 'cuenta', '2101')),
                                    v_asiento);
        SET p_uuid_transaccion = p_uuid_autorizacion;
        INSERT INTO cuentas.movimiento (uuid_transaccion, tipo_operacion, monto, glosa, estado_transaccion,
                                        id_asiento, num_cuenta, id_canal)
        VALUES (p_uuid_transaccion, v_tipo_operacion, v_monto, v_glosa, 'APROBADO', v_asiento, v_num_cuenta,
                coalesce(v_id_canal, (SELECT id_canal FROM core.terminal WHERE id_terminal = v_id_terminal)));
        -- Actualiza la autorización: estado DISPENSADA y referencia al movimiento.
        UPDATE tarjetas.autorizacion
           SET estado_autorizacion = 'DISPENSADA', uuid_transaccion = p_uuid_transaccion, fecha_actualizacion = UTC_TIMESTAMP(6)
         WHERE uuid_autorizacion = p_uuid_autorizacion;
        -- El trigger tg_movimiento_aplicar_ai descuenta saldo_contable y el trigger
        -- tg_autorizacion_aplicar_au (por el cambio a DISPENSADA) no vuelve a comprometer
        -- porque uuid_transaccion ya no es NULL.
        IF p_llave_idempotencia IS NOT NULL THEN
            UPDATE cuentas.idempotencia_movimiento SET uuid_transaccion = p_uuid_transaccion WHERE llave = p_llave_idempotencia;
        END IF;
        CALL core.registrar_evento('CORE', 'autorizacion', BIN_TO_UUID(p_uuid_autorizacion), 'CONFIRMAR_AUTORIZACION', p_actor,
                                   v_correlation_id, JSON_OBJECT('estado_anterior', v_anterior, 'tipo_operacion', v_tipo_operacion,
                                                                 'monto', v_monto, 'num_cuenta', v_num_cuenta));
        SET p_estado = 'DISPENSADA';
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Credenciales de tarjeta (v1.5): PIN_ATM y CLAVE_WEB. La matriz de coordenadas queda
-- para cuando haya un procedimiento que la emita.
-- DECISIÓN (v1.5): el hash es SHA2(CONCAT(sal, valor), 256), con una sal aleatoria de 16
--   bytes por credencial, y se calcula aquí para que la API no lea la tabla. Un PIN de 4
--   dígitos se descubre por fuerza bruta desde su hash: lo protege que solo bna_owner
--   lea tarjetas.credencial y el bloqueo al tercer intento (RN-TAR-004).
-- DECISIÓN (v1.5): el valor llega como parámetro; no se registra en la bitácora ni en
--   el mensaje de ningún error.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.formato_credencial(IN p_tipo VARCHAR(15), IN p_valor VARCHAR(64))
    COMMENT 'Interno. Rechaza un tipo de credencial no admitido o un valor de otra longitud (RN-TAR-001).'
BEGIN
    DECLARE v_longitud SMALLINT;
    IF p_tipo NOT IN ('PIN_ATM', 'CLAVE_WEB') THEN
        CALL core.fallar(CONCAT('BNA-CREDENCIAL: tipo de credencial no admitido ', coalesce(p_tipo, '(nulo)')));
    END IF;
    SELECT longitud INTO v_longitud FROM tarjetas.tipo_credencial WHERE tipo_credencial = p_tipo;
    IF NOT coalesce(REGEXP_LIKE(p_valor, CONCAT('^[0-9]{', v_longitud, '}$')), FALSE) THEN
        CALL core.fallar(CONCAT('BNA-CREDENCIAL: ', p_tipo, ' debe tener ', v_longitud, ' dígitos'));
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.registrar_credencial(
    IN p_id_tarjeta BINARY(16), IN p_tipo VARCHAR(15), IN p_valor VARCHAR(64), IN p_actor VARCHAR(40))
    COMMENT 'Asigna o cambia el PIN o la clave web de una tarjeta y reinicia sus intentos.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_sal CHAR(32);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL tarjetas.formato_credencial(p_tipo, p_valor);
        SELECT estado_tarjeta INTO v_estado FROM tarjetas.tarjeta WHERE id_tarjeta = p_id_tarjeta FOR UPDATE;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-TARJETA: la tarjeta no existe');
        END IF;
        IF v_estado IN ('CANCELADA', 'VENCIDA') THEN
            CALL core.fallar(CONCAT('BNA-TARJETA: la tarjeta está ', v_estado));
        END IF;
        SET v_sal = HEX(RANDOM_BYTES(16));
        INSERT INTO tarjetas.credencial (id_tarjeta, tipo_credencial, hash_credencial, sal)
        VALUES (p_id_tarjeta, p_tipo, SHA2(CONCAT(v_sal, p_valor), 256), v_sal) AS nueva
        ON DUPLICATE KEY UPDATE hash_credencial = nueva.hash_credencial, sal = nueva.sal, intentos_fallidos = 0,
                                fecha_ultimo_cambio = UTC_TIMESTAMP(6);
        CALL core.registrar_evento('CORE', 'credencial', BIN_TO_UUID(p_id_tarjeta), 'REGISTRAR_CREDENCIAL', p_actor,
                                   NULL, JSON_OBJECT('tipo_credencial', p_tipo));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Un valor equivocado no es un error: queda el intento FALLIDO y tg_intento_contar
-- bloquea la tarjeta al tercero (RN-TAR-004). Una tarjeta no operativa se rechaza
-- sin registrar el intento.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.validar_credencial(
    IN p_id_tarjeta BINARY(16), IN p_tipo VARCHAR(15), IN p_valor VARCHAR(64), IN p_id_canal VARCHAR(5),
    IN p_id_terminal VARCHAR(30), IN p_ip_origen VARCHAR(45), IN p_correlacion BINARY(16), IN p_actor VARCHAR(40),
    OUT p_resultado VARCHAR(25), OUT p_intentos_restantes SMALLINT)
    COMMENT 'Valida el PIN o la clave web de una tarjeta y registra el intento.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_hash CHAR(64);
    DECLARE v_sal CHAR(32);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL tarjetas.formato_credencial(p_tipo, p_valor);
        SELECT estado_tarjeta INTO v_estado FROM tarjetas.tarjeta WHERE id_tarjeta = p_id_tarjeta FOR UPDATE;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-TARJETA: la tarjeta no existe');
        END IF;
        IF NOT (SELECT es_operativa FROM tarjetas.estado_tarjeta WHERE cod_estado = v_estado) THEN
            CALL core.fallar(CONCAT('ERR-TAR-003: la tarjeta no es operativa (estado ', v_estado, ')'));
        END IF;
        SELECT hash_credencial, sal INTO v_hash, v_sal FROM tarjetas.credencial
         WHERE id_tarjeta = p_id_tarjeta AND tipo_credencial = p_tipo FOR UPDATE;
        IF v_hash IS NULL THEN
            CALL core.fallar(CONCAT('BNA-CREDENCIAL: la tarjeta no tiene ', p_tipo));
        END IF;
        SET p_resultado = IF(SHA2(CONCAT(v_sal, p_valor), 256) = v_hash, 'EXITOSO', 'FALLIDO');
        INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, ip_origen, resultado, motivo_rechazo,
                                                    uuid_correlacion, id_tarjeta, id_canal)
        VALUES (p_tipo, p_id_terminal, p_ip_origen, p_resultado,
                IF(p_resultado = 'FALLIDO', 'Credencial incorrecta', NULL), p_correlacion, p_id_tarjeta, p_id_canal);
        SELECT 3 - intentos_fallidos INTO p_intentos_restantes FROM tarjetas.credencial
         WHERE id_tarjeta = p_id_tarjeta AND tipo_credencial = p_tipo;
        CALL core.registrar_evento('CORE', 'credencial', BIN_TO_UUID(p_id_tarjeta), 'VALIDAR_CREDENCIAL', p_actor,
                                   p_correlacion, JSON_OBJECT('tipo_credencial', p_tipo, 'resultado', p_resultado,
                                                              'intentos_restantes', p_intentos_restantes));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

DELIMITER ;

-- ---------------------------------------------------------------------
-- 9. Lecturas de la API
-- ---------------------------------------------------------------------
-- La tarjeta sin pan_token: la API no necesita el token (PCI-DSS). num_cuenta es la
-- cuenta principal (a lo sumo una, por ux_tarjeta_principal), NULL si no tiene: la API la
-- compara al repetir una emisión con la misma llave de idempotencia.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW tarjetas.v_tarjeta_api AS
SELECT t.id_tarjeta, t.bin, t.ultimos4, t.fecha_emision, t.fecha_vencimiento, t.estado_tarjeta, t.cod_cliente,
       tc.num_cuenta
  FROM tarjetas.tarjeta t
  LEFT JOIN tarjetas.tarjeta_cuenta tc ON tc.id_tarjeta = t.id_tarjeta AND tc.es_principal = 1;

-- La autorización sin la IP de origen ni el nivel de riesgo (v1.5).
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW tarjetas.v_autorizacion_api AS
SELECT uuid_autorizacion, id_tarjeta, num_cuenta, id_canal, id_terminal, tipo_operacion, monto, estado_autorizacion,
       codigo_respuesta, motivo_rechazo, uuid_transaccion, fecha_hora, fecha_actualizacion
  FROM tarjetas.autorizacion;

CREATE ROLE IF NOT EXISTS bna_api, bna_seguridad;
GRANT EXECUTE ON PROCEDURE tarjetas.desbloquear_tarjeta TO bna_seguridad;
-- Solo lo que lee COREDB; un endpoint nuevo agrega aquí lo que necesite. El hash de
-- usuario_sistema lo exige la autenticación.
GRANT SELECT ON core.usuario_sistema TO bna_api;
GRANT SELECT ON core.moneda TO bna_api;
GRANT SELECT ON core.agencia TO bna_api;
GRANT SELECT ON core.producto_ahorro TO bna_api;
GRANT SELECT ON core.producto_credito TO bna_api;
GRANT SELECT ON core.tipo_cambio TO bna_api;
GRANT SELECT ON core.equivalencia_catalogo TO bna_api;
GRANT SELECT ON core.periodo_contable TO bna_api;
GRANT SELECT ON cuentas.cuenta_ahorro TO bna_api;
GRANT SELECT ON cuentas.idempotencia_movimiento TO bna_api;
GRANT SELECT ON tarjetas.v_tarjeta_api TO bna_api;
GRANT SELECT ON tarjetas.v_autorizacion_api TO bna_api;
GRANT EXECUTE ON PROCEDURE core.verificar_configuracion TO bna_api;
GRANT EXECUTE ON FUNCTION core.fn_fecha_negocio TO bna_api;
GRANT EXECUTE ON PROCEDURE core.crear_usuario TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE core.asignar_rol TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE core.migrar_hash_usuario TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE cuentas.registrar_movimiento TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE cuentas.registrar_transferencia TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE cuentas.abrir_cuenta TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.emitir_tarjeta TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.cambiar_estado_tarjeta TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.autorizar_operacion TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.extornar_autorizacion TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.confirmar_autorizacion TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.registrar_credencial TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.validar_credencial TO bna_api, bna_app, bna_admin;

-- ---------------------------------------------------------------------
-- 10. Usuarios de servicio y clientes (v1.1)
-- ---------------------------------------------------------------------
-- Lo que necesitan la autenticación de COREDB y el módulo Clientes. Los procedimientos
-- siguen el patrón de la sección 8 y se conceden solo a bna_api; bna_admin los ejecuta
-- por su privilegio sobre core.* y clientes.*.

-- Numeración de cod_cliente: CLI y nueve dígitos. Una operación deshecha deja un hueco.
CREATE TABLE clientes.numerador_cliente (
    numero    BIGINT AUTO_INCREMENT,
    creado_en DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_numerador_cliente PRIMARY KEY (numero)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: numeración de cod_cliente.';

DELIMITER //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.crear_usuario_servicio(
    IN p_id BINARY(16), IN p_username VARCHAR(40), IN p_nombre VARCHAR(100), IN p_modulo VARCHAR(40),
    IN p_hash VARCHAR(255), IN p_algoritmo VARCHAR(20), IN p_version VARCHAR(10), IN p_actor VARCHAR(40))
    COMMENT 'Crea el usuario de servicio con el que un módulo se autentica.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        INSERT INTO core.usuario_sistema (id_usuario, username, nombre, rol, hash_password, algoritmo_hash,
                                          version_hash, activo, modulo)
        VALUES (p_id, p_username, p_nombre, 'SERVICIO', p_hash, p_algoritmo, p_version, TRUE, p_modulo);
        CALL core.registrar_evento('CORE', 'usuario_sistema', BIN_TO_UUID(p_id), 'CREAR_USUARIO_SERVICIO', p_actor,
                                   NULL, JSON_OBJECT('username', p_username, 'modulo', p_modulo));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Solo usuarios de servicio: la contraseña de una persona no se cambia por esta vía.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.renovar_credencial(
    IN p_id BINARY(16), IN p_hash VARCHAR(255), IN p_algoritmo VARCHAR(20), IN p_version VARCHAR(10),
    IN p_actor VARCHAR(40), OUT p_filas INT)
    COMMENT 'Reemplaza la credencial de un usuario de servicio.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_rol VARCHAR(15);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT rol INTO v_rol FROM core.usuario_sistema WHERE id_usuario = p_id FOR UPDATE;
        IF v_rol IS NULL THEN
            CALL core.fallar('BNA-USUARIO: el usuario no existe');
        END IF;
        IF v_rol <> 'SERVICIO' THEN
            CALL core.fallar('BNA-USUARIO-SERVICIO: solo se renueva la credencial de un usuario de servicio');
        END IF;
        UPDATE core.usuario_sistema
           SET hash_password = p_hash, algoritmo_hash = p_algoritmo, version_hash = p_version
         WHERE id_usuario = p_id;
        SET p_filas = ROW_COUNT();
        CALL core.registrar_evento('CORE', 'usuario_sistema', BIN_TO_UUID(p_id), 'RENOVAR_CREDENCIAL', p_actor, NULL,
                                   JSON_OBJECT('algoritmo', p_algoritmo));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Revoca o restituye el acceso. Pedir el estado que ya tiene no cambia nada (p_filas = 0).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.cambiar_estado_usuario(
    IN p_id BINARY(16), IN p_activo BOOLEAN, IN p_actor VARCHAR(40), OUT p_filas INT)
    COMMENT 'Activa o desactiva un usuario.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_activo BOOLEAN;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_activo IS NULL THEN
            CALL core.fallar('BNA-USUARIO-ESTADO: falta el estado');
        END IF;
        SELECT activo INTO v_activo FROM core.usuario_sistema WHERE id_usuario = p_id FOR UPDATE;
        IF v_activo IS NULL THEN
            CALL core.fallar('BNA-USUARIO: el usuario no existe');
        END IF;
        SET p_filas = 0;
        IF v_activo <> p_activo THEN
            UPDATE core.usuario_sistema SET activo = p_activo WHERE id_usuario = p_id;
            SET p_filas = ROW_COUNT();
            CALL core.registrar_evento('CORE', 'usuario_sistema', BIN_TO_UUID(p_id),
                                       IF(p_activo, 'ACTIVAR_USUARIO', 'DESACTIVAR_USUARIO'), p_actor, NULL, NULL);
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- El actor es el propio usuario, leído de su fila: quien llama no puede atribuir un
-- login a otro nombre. Los intentos fallidos no se registran (como en CORE).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.registrar_login(IN p_id BINARY(16), IN p_correlation_id BINARY(16))
    COMMENT 'Registra un inicio de sesión exitoso.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_username VARCHAR(40);
    DECLARE v_rol VARCHAR(15);
    DECLARE v_modulo VARCHAR(40);
    DECLARE v_activo BOOLEAN;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT username, rol, modulo, activo INTO v_username, v_rol, v_modulo, v_activo
          FROM core.usuario_sistema WHERE id_usuario = p_id;
        IF v_username IS NULL OR NOT v_activo THEN
            CALL core.fallar('BNA-USUARIO: el usuario no existe o no está activo');
        END IF;
        CALL core.registrar_evento('CORE', 'usuario_sistema', BIN_TO_UUID(p_id), 'LOGIN', v_username, p_correlation_id,
                                   JSON_OBJECT('rol', v_rol, 'modulo', v_modulo));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Interno: la vista del cliente que devuelven los procedimientos. Sin biometría.
CREATE DEFINER = 'bna_owner'@'%' FUNCTION clientes.fn_cliente_json(p_cod_cliente VARCHAR(12)) RETURNS JSON
    READS SQL DATA
    COMMENT 'El cliente como objeto JSON, o NULL si no existe.'
BEGIN
    DECLARE v_cliente JSON;
    SELECT JSON_OBJECT(
               'cod_cliente', c.cod_cliente, 'tipo_documento', c.tipo_documento,
               'numero_documento', c.numero_documento, 'nombres', c.nombres,
               'apellido_paterno', c.apellido_paterno, 'apellido_materno', c.apellido_materno,
               'correo', c.correo, 'celular', c.celular, 'estado_cliente', c.estado_cliente,
               'permite_operar', CAST(IF(e.permite_operar, 'true', 'false') AS JSON),
               'version_contrato', c.version_contrato,
               'id_verificacion_captacion', c.id_verificacion_captacion,
               'estado_habilitante', v.estado_habilitante,
               'fecha_verificacion', DATE_FORMAT(v.fecha_verificacion, '%Y-%m-%dT%H:%i:%s.%fZ'))
      INTO v_cliente
      FROM clientes.cliente c
      JOIN clientes.estado_cliente e ON e.cod_estado = c.estado_cliente
      JOIN clientes.verificacion_captacion v ON v.id_verificacion_captacion = c.id_verificacion_captacion
     WHERE c.cod_cliente = p_cod_cliente;
    RETURN v_cliente;
END //

-- La base valida el documento con clientes.tipo_documento y genera cod_cliente. El
-- estado inicial sale del resultado de la verificación de captación: HABILITADO da
-- ACTIVO y OBSERVADO da OBSERVADO. Quién puede registrar HABILITADO lo decide la API.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.registrar_cliente(
    IN p_tipo_documento VARCHAR(10), IN p_numero_documento VARCHAR(12), IN p_nombres VARCHAR(100),
    IN p_apellido_paterno VARCHAR(100), IN p_apellido_materno VARCHAR(100), IN p_correo VARCHAR(150),
    IN p_celular CHAR(9), IN p_version_contrato VARCHAR(10), IN p_estado_habilitante VARCHAR(25),
    IN p_correlation_id BINARY(16), IN p_actor VARCHAR(40), OUT p_cod_cliente VARCHAR(12))
    COMMENT 'Registra un cliente con su verificación de captación.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_min, v_max SMALLINT;
    DECLARE v_alfanumerico BOOLEAN;
    DECLARE v_numero BIGINT;
    DECLARE v_captacion VARCHAR(36);
    DECLARE v_correo VARCHAR(150) DEFAULT LOWER(TRIM(p_correo));
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT longitud_min, longitud_max, es_alfanumerico INTO v_min, v_max, v_alfanumerico
          FROM clientes.tipo_documento WHERE cod_tipo_documento = p_tipo_documento;
        IF v_min IS NULL THEN
            CALL core.fallar('BNA-DOCUMENTO: tipo de documento desconocido');
        END IF;
        IF p_numero_documento IS NULL OR CHAR_LENGTH(p_numero_documento) NOT BETWEEN v_min AND v_max
           OR NOT REGEXP_LIKE(p_numero_documento, IF(v_alfanumerico, '^[A-Z0-9]+$', '^[0-9]+$'), 'c') THEN
            CALL core.fallar('BNA-DOCUMENTO: el número no cumple el formato de su tipo de documento');
        END IF;
        IF coalesce(TRIM(p_nombres), '') = '' OR coalesce(TRIM(p_apellido_paterno), '') = ''
           OR coalesce(TRIM(p_version_contrato), '') = '' THEN
            CALL core.fallar('BNA-DATOS-CLIENTE: faltan los nombres, el apellido paterno o la versión del contrato');
        END IF;
        IF v_correo IS NULL OR NOT REGEXP_LIKE(v_correo, '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$') THEN
            CALL core.fallar('BNA-DATOS-CLIENTE: el correo no es válido');
        END IF;
        IF p_estado_habilitante IS NULL OR p_estado_habilitante NOT IN ('HABILITADO', 'OBSERVADO') THEN
            CALL core.fallar('BNA-DATOS-CLIENTE: el estado habilitante es HABILITADO u OBSERVADO');
        END IF;
        IF p_correlation_id IS NULL THEN
            CALL core.fallar('BNA-DATOS-CLIENTE: falta el correlation_id');
        END IF;
        INSERT INTO clientes.numerador_cliente () VALUES ();
        SET v_numero = LAST_INSERT_ID();
        IF v_numero > 999999999 THEN
            CALL core.fallar('BNA-NUMERACION: se agotó la numeración de clientes');
        END IF;
        SET p_cod_cliente = CONCAT('CLI', LPAD(v_numero, 9, '0'));
        SET v_captacion = BIN_TO_UUID(core.uuid_v4());
        INSERT INTO clientes.verificacion_captacion (id_verificacion_captacion, estado_habilitante)
        VALUES (v_captacion, p_estado_habilitante);
        INSERT INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, apellido_paterno,
                                      apellido_materno, correo, celular, estado_cliente, id_verificacion_captacion,
                                      version_contrato)
        VALUES (p_cod_cliente, p_tipo_documento, p_numero_documento, TRIM(p_nombres), TRIM(p_apellido_paterno),
                NULLIF(TRIM(p_apellido_materno), ''), v_correo, p_celular,
                IF(p_estado_habilitante = 'HABILITADO', 'ACTIVO', 'OBSERVADO'), v_captacion, TRIM(p_version_contrato));
        CALL core.registrar_evento('CLIENTES', 'cliente', p_cod_cliente, 'REGISTRAR_CLIENTE', p_actor, p_correlation_id,
                                   JSON_OBJECT('tipo_documento', p_tipo_documento,
                                               'estado_habilitante', p_estado_habilitante,
                                               'version_contrato', TRIM(p_version_contrato)));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Consulta por código: quien lo conoce ya sabe que es cliente. Sin auditoría, como las
-- demás lecturas de la API.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.consultar_cliente(IN p_cod_cliente VARCHAR(12), OUT p_cliente JSON)
    READS SQL DATA
    COMMENT 'Devuelve el cliente en JSON, o NULL si no existe.'
BEGIN
    SET p_cliente = clientes.fn_cliente_json(p_cod_cliente);
END //

-- Consulta por documento (RF-CLI-001). Sin identidad verificada, la respuesta es la
-- misma para un cliente y para quien no lo es; con identidad verificada, aprueba solo
-- a un cliente ACTIVO. Siempre deja la validación y su evento.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.verificar_documento(
    IN p_tipo_documento VARCHAR(10), IN p_numero_documento VARCHAR(12), IN p_identidad_verificada BOOLEAN,
    IN p_motivo VARCHAR(60), IN p_correlation_id BINARY(16), IN p_actor VARCHAR(40),
    OUT p_id_validacion BIGINT, OUT p_resultado VARCHAR(25), OUT p_motivo_core VARCHAR(60), OUT p_cliente JSON)
    COMMENT 'Verifica un documento y registra la validación.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_cod VARCHAR(12);
    DECLARE v_estado VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_identidad_verificada IS NULL THEN
            CALL core.fallar('BNA-VALIDACION: falta indicar si la identidad se verificó');
        END IF;
        IF p_correlation_id IS NULL THEN
            CALL core.fallar('BNA-VALIDACION: falta el correlation_id');
        END IF;
        SELECT cod_cliente, estado_cliente INTO v_cod, v_estado
          FROM clientes.cliente WHERE tipo_documento = p_tipo_documento AND numero_documento = p_numero_documento;
        SET p_cliente = NULL, p_motivo_core = NULL, p_resultado = 'RECHAZADO';
        IF NOT p_identidad_verificada THEN
            SET p_motivo_core = 'IDENTIDAD_NO_VERIFICADA';
        ELSEIF v_cod IS NULL THEN
            SET p_motivo_core = 'NO_ES_CLIENTE';
        ELSEIF v_estado <> 'ACTIVO' THEN
            SET p_motivo_core = 'CLIENTE_NO_ACTIVO', p_cliente = clientes.fn_cliente_json(v_cod);
        ELSE
            SET p_resultado = 'APROBADO', p_cliente = clientes.fn_cliente_json(v_cod);
        END IF;
        INSERT INTO clientes.validacion_identidad (tipo_validacion, resultado, correlation_id, cod_cliente)
        VALUES ('DOCUMENTO', p_resultado, p_correlation_id, v_cod);
        SET p_id_validacion = LAST_INSERT_ID();
        CALL core.registrar_evento('CLIENTES', 'validacion_identidad', p_id_validacion, 'VALIDAR_DOCUMENTO', p_actor,
                                   p_correlation_id,
                                   JSON_OBJECT('tipo_documento', p_tipo_documento, 'cod_cliente', v_cod,
                                               'identidad_verificada', p_identidad_verificada IS TRUE,
                                               'resultado', p_resultado, 'motivo_llamador', p_motivo,
                                               'motivo_core', p_motivo_core));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Los veredictos de huella, rostro, celular y correo que produce Clientes. El de
-- documento pasa por verificar_documento.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.registrar_validacion(
    IN p_cod_cliente VARCHAR(12), IN p_tipo_validacion VARCHAR(15), IN p_resultado VARCHAR(25),
    IN p_motivo VARCHAR(60), IN p_correlation_id BINARY(16), IN p_actor VARCHAR(40), OUT p_id_validacion BIGINT)
    COMMENT 'Registra una validación de identidad de un cliente.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_tipo_validacion = 'DOCUMENTO' THEN
            CALL core.fallar('BNA-VALIDACION: la validación de documento se hace con verificar_documento');
        END IF;
        IF p_resultado IS NULL OR p_resultado NOT IN ('APROBADO', 'RECHAZADO') THEN
            CALL core.fallar('BNA-VALIDACION: el resultado es APROBADO o RECHAZADO');
        END IF;
        IF p_correlation_id IS NULL THEN
            CALL core.fallar('BNA-VALIDACION: falta el correlation_id');
        END IF;
        IF NOT EXISTS (SELECT 1 FROM clientes.cliente WHERE cod_cliente = p_cod_cliente) THEN
            CALL core.fallar('BNA-CLIENTE: el cliente no existe');
        END IF;
        INSERT INTO clientes.validacion_identidad (tipo_validacion, resultado, correlation_id, cod_cliente)
        VALUES (p_tipo_validacion, p_resultado, p_correlation_id, p_cod_cliente);
        SET p_id_validacion = LAST_INSERT_ID();
        CALL core.registrar_evento('CLIENTES', 'validacion_identidad', p_id_validacion, 'REGISTRAR_VALIDACION', p_actor,
                                   p_correlation_id,
                                   JSON_OBJECT('cod_cliente', p_cod_cliente, 'tipo_validacion', p_tipo_validacion,
                                               'resultado', p_resultado, 'motivo', p_motivo));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- El motivo es obligatorio y queda en la bitácora. BAJA es final; pedir el estado que ya
-- tiene no cambia nada. tg_cliente_estado_tarjetas bloquea o cancela sus tarjetas, y
-- reactivar al cliente no las desbloquea (eso es de Seguridad). Qué estados puede fijar
-- cada actor lo decide la API.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.cambiar_estado_cliente(
    IN p_cod_cliente VARCHAR(12), IN p_estado VARCHAR(25), IN p_motivo VARCHAR(255), IN p_actor VARCHAR(40),
    OUT p_anterior VARCHAR(25))
    COMMENT 'Cambia el estado de un cliente.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF coalesce(TRIM(p_motivo), '') = '' THEN
            CALL core.fallar('BNA-MOTIVO: el cambio de estado exige un motivo');
        END IF;
        IF NOT EXISTS (SELECT 1 FROM clientes.estado_cliente WHERE cod_estado = p_estado) THEN
            CALL core.fallar('BNA-ESTADO: estado de cliente desconocido');
        END IF;
        SET p_anterior = NULL;
        SELECT estado_cliente INTO p_anterior FROM clientes.cliente WHERE cod_cliente = p_cod_cliente FOR UPDATE;
        IF p_anterior IS NULL THEN
            CALL core.fallar('BNA-CLIENTE: el cliente no existe');
        END IF;
        IF p_anterior <> p_estado THEN
            IF p_anterior = 'BAJA' THEN
                CALL core.fallar('BNA-ESTADO: un cliente dado de baja no cambia de estado');
            END IF;
            UPDATE clientes.cliente SET estado_cliente = p_estado WHERE cod_cliente = p_cod_cliente;
            CALL core.registrar_evento('CLIENTES', 'cliente', p_cod_cliente, 'CAMBIAR_ESTADO_CLIENTE', p_actor, NULL,
                                       JSON_OBJECT('estado_anterior', p_anterior, 'estado_nuevo', p_estado,
                                                   'motivo', TRIM(p_motivo)));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Los catálogos que la API publica y usa para validar antes de llamar.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.catalogos_cliente(OUT p_catalogos JSON)
    READS SQL DATA
    COMMENT 'Tipos de documento y estados de cliente, en JSON.'
BEGIN
    SET p_catalogos = JSON_OBJECT(
        'tipos_documento', (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                                       'codigo', cod_tipo_documento, 'descripcion', descripcion,
                                       'longitud_min', longitud_min, 'longitud_max', longitud_max,
                                       'es_alfanumerico', CAST(IF(es_alfanumerico, 'true', 'false') AS JSON)))
                              FROM clientes.tipo_documento),
        'estados_cliente', (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                                       'codigo', cod_estado, 'descripcion', descripcion,
                                       'permite_operar', CAST(IF(permite_operar, 'true', 'false') AS JSON)))
                              FROM clientes.estado_cliente));
END //

DELIMITER ;

GRANT EXECUTE ON PROCEDURE core.crear_usuario_servicio TO bna_api;
GRANT EXECUTE ON PROCEDURE core.renovar_credencial TO bna_api;
GRANT EXECUTE ON PROCEDURE core.cambiar_estado_usuario TO bna_api;
GRANT EXECUTE ON PROCEDURE core.registrar_login TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.registrar_cliente TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.consultar_cliente TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.verificar_documento TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.registrar_validacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.cambiar_estado_cliente TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.catalogos_cliente TO bna_api;

-- ---------------------------------------------------------------------
-- 11. Lecturas de consulta de la API (v1.2)
-- ---------------------------------------------------------------------
-- Lo que COREDB necesita para listar los movimientos de una cuenta, las cuentas de un
-- cliente y la bitácora. bna_api sigue sin leer cuentas.movimiento ni
-- core.evento_auditoria: lee estas vistas, que corren como bna_owner.

-- El movimiento sin su asiento contable, con la naturaleza de la operación
-- (D débito, C crédito) y la moneda de la cuenta.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW cuentas.v_movimiento_api AS
SELECT m.uuid_transaccion, m.num_cuenta, m.tipo_operacion, o.naturaleza, m.monto, c.moneda,
       m.glosa, m.id_canal, m.estado_transaccion, m.fecha_hora
  FROM cuentas.movimiento m
  JOIN cuentas.tipo_operacion o ON o.tipo_operacion = m.tipo_operacion
  JOIN cuentas.cuenta_ahorro c ON c.num_cuenta = m.num_cuenta;

-- La bitácora general con el nombre del módulo. Los procedimientos no guardan datos
-- personales en el detalle de un evento.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW core.v_evento_auditoria_api AS
SELECT e.id_evento, mo.nombre AS modulo, e.entidad, e.id_entidad, e.accion, e.actor,
       e.correlation_id, e.detalle, e.fecha_hora
  FROM core.evento_auditoria e
  JOIN core.modulo mo ON mo.id_modulo = e.id_modulo;

GRANT SELECT ON cuentas.v_movimiento_api TO bna_api;
GRANT SELECT ON core.v_evento_auditoria_api TO bna_api;
-- Qué cuentas tiene un cliente: solo los dos códigos y la fecha de vinculación.
GRANT SELECT ON cuentas.titularidad TO bna_api;

-- ---------------------------------------------------------------------
-- 12. Créditos (v1.4)
-- ---------------------------------------------------------------------
-- Lo que COREDB necesita para la línea de créditos: el expediente de SOL, la evaluación,
-- la decisión del analista, el desembolso y el cobro de cuotas, sobre las tablas
-- creditos.* del modelo. Los procedimientos siguen el patrón de la sección 8 y se conceden
-- solo a bna_api; bna_admin los ejecuta por su privilegio sobre creditos.*. bna_api no lee
-- ninguna tabla de creditos: lee las vistas de esta sección.
-- DECISIÓN (v1.4): el dinero se mueve dentro del procedimiento de crédito. Confirmar una
--   orden registra el movimiento DESEMBOLSO, la orden CONFIRMADA, el crédito con su
--   calendario OFICIAL y la solicitud DESEMBOLSADA en una sola transacción; pagar una
--   cuota registra el movimiento DEBITO_CUOTA, el pago y su aplicación. Por eso los
--   estados EN_PROCESO y POR_VERIFICAR de la orden y PENDIENTE del pago no se usan, ni
--   evento_entrega (las llamadas CR-INT-04 a CR-INT-07 entre módulos desaparecen).
-- DECISIÓN (v1.4): el id de la evaluación de una ronda es determinista
--   (creditos.fn_id_evaluacion), porque el acuse a SOL lo necesita al recibir el
--   expediente, antes de que exista la evaluación.
-- DECISIÓN (v1.4): los umbrales de RN-EVA-002-P salen de creditos.regla_evaluacion; la
--   fórmula del límite la calcula COREDB. El analista decide APROBADO o RECHAZADO
--   (diccionario de Evaluación). Una aprobación vence a los 30 días
--   (creditos.fn_dias_vigencia_aprobacion).
-- DECISIÓN (v1.4): la cuenta del desembolso es de ahorros, ACTIVA, INDIVIDUAL, del titular y
--   en la moneda del crédito (como el módulo Desembolso); la que paga una cuota es del
--   titular y en su moneda. El canal del desembolso es VEN o HB.
-- DECISIÓN (v1.4): un débito rechazado por saldo, estado de la cuenta o tope deja el pago
--   RECHAZADO con el código de la regla y sin movimiento. La mora se registra y se muestra,
--   pero no se cobra (el modelo no la paga por aplicacion_pago).
-- DECISIÓN (v1.4): los mensajes de error de esta sección no llevan cifras ni valores de
--   entrada (cuentas, documentos, cod_cliente), porque la API puede devolverlos.

-- Numeración de codigo_orden (DES-AAAA-NNNNNN) y cod_credito (CRE-AAAA-NNNNNN). Una
-- operación deshecha deja un hueco.
CREATE TABLE creditos.numerador_orden (
    numero    BIGINT AUTO_INCREMENT,
    creado_en DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_numerador_orden PRIMARY KEY (numero)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: numeración de codigo_orden.';

CREATE TABLE creditos.numerador_credito (
    numero    BIGINT AUTO_INCREMENT,
    creado_en DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_numerador_credito PRIMARY KEY (numero)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: numeración de cod_credito.';

-- Cada versión del expediente recibida: su ronda y la huella del contenido, que hace
-- idempotente el reenvío de SOL.
CREATE TABLE creditos.recepcion_solicitud (
    id_solicitud      BINARY(16) NOT NULL,
    version_solicitud SMALLINT NOT NULL,
    ronda             SMALLINT NOT NULL,
    huella            CHAR(64) NOT NULL,
    recibida_en       DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_recepcion_solicitud PRIMARY KEY (id_solicitud, version_solicitud),
    CONSTRAINT uk_recepcion_solicitud_ronda UNIQUE (id_solicitud, ronda),
    CONSTRAINT fk_recepcion_solicitud FOREIGN KEY (id_solicitud) REFERENCES creditos.solicitud_credito (id_solicitud),
    CONSTRAINT ck_recepcion_solicitud_ronda CHECK (ronda > 0)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: versiones del expediente de SOL recibidas.';

-- La cuenta y el movimiento de cada pago, o el código de la regla que lo rechazó.
CREATE TABLE creditos.cobro_pago (
    id_pago          BINARY(16) NOT NULL,
    num_cuenta       VARCHAR(20) NOT NULL,
    huella           CHAR(64) NOT NULL,
    uuid_transaccion BINARY(16),
    motivo_rechazo   VARCHAR(40),
    CONSTRAINT pk_cobro_pago PRIMARY KEY (id_pago),
    CONSTRAINT uk_cobro_pago_movimiento UNIQUE (uuid_transaccion),
    CONSTRAINT fk_cobro_pago FOREIGN KEY (id_pago) REFERENCES creditos.pago (id_pago),
    CONSTRAINT fk_cobro_pago_cuenta FOREIGN KEY (num_cuenta) REFERENCES cuentas.cuenta_ahorro (num_cuenta),
    CONSTRAINT fk_cobro_pago_movimiento FOREIGN KEY (uuid_transaccion) REFERENCES cuentas.movimiento (uuid_transaccion),
    CONSTRAINT ck_cobro_pago_resultado CHECK ((uuid_transaccion IS NULL) <> (motivo_rechazo IS NULL))
) ENGINE = InnoDB COMMENT = 'Extensión de integración: débito o motivo de rechazo de cada pago.';

DELIMITER //

CREATE DEFINER = 'bna_owner'@'%' FUNCTION creditos.fn_dias_vigencia_aprobacion() RETURNS SMALLINT
    DETERMINISTIC NO SQL
    COMMENT 'Días de vigencia de una aprobación de crédito.'
BEGIN
    RETURN 30;
END //

-- UUID versión 8 a partir de SHA-256 de la solicitud y la ronda.
CREATE DEFINER = 'bna_owner'@'%' FUNCTION creditos.fn_id_evaluacion(p_id_solicitud BINARY(16), p_ronda SMALLINT)
    RETURNS BINARY(16) DETERMINISTIC NO SQL
    COMMENT 'Id determinista de la evaluación de una ronda.'
BEGIN
    DECLARE v_h VARBINARY(32) DEFAULT UNHEX(SHA2(CONCAT('bna-evaluacion:', HEX(p_id_solicitud), ':', p_ronda), 256));
    RETURN CONCAT(SUBSTR(v_h, 1, 6), CHAR(0x80 | (ASCII(SUBSTR(v_h, 7, 1)) & 0x0F)), SUBSTR(v_h, 8, 1),
                  CHAR(0x80 | (ASCII(SUBSTR(v_h, 9, 1)) & 0x3F)), SUBSTR(v_h, 10, 7));
END //

-- Interno: un evento en la bitácora de créditos (ORDEN, CREDITO, PAGO, CUOTA).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.registrar_evento_credito(
    IN p_tipo VARCHAR(25), IN p_id_entidad VARCHAR(36), IN p_numero_cuota SMALLINT, IN p_accion VARCHAR(60),
    IN p_resultado VARCHAR(40), IN p_modulo SMALLINT, IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    IN p_detalle JSON)
    COMMENT 'Registra un evento en creditos.evento_auditoria.'
BEGIN
    IF p_correlation_id IS NULL THEN
        CALL core.fallar('BNA-CORRELACION: falta el correlation_id');
    END IF;
    INSERT INTO creditos.entidad_auditada (id_entidad, tipo_entidad) VALUES (p_id_entidad, p_tipo)
        ON DUPLICATE KEY UPDATE tipo_entidad = tipo_entidad;
    INSERT INTO creditos.evento_auditoria (modulo_emisor, id_entidad, numero_cuota, accion, resultado, actor,
                                           correlation_id, detalle)
    VALUES (p_modulo, p_id_entidad, p_numero_cuota, p_accion, p_resultado, p_actor, p_correlation_id, p_detalle);
END //

-- Interno: la aprobación de una evaluación sigue vigente y admite un desembolso. Bloquea
-- la solicitud, de modo que las órdenes de una solicitud se preparan y confirman de a una.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.verificar_aprobacion(
    IN p_id_evaluacion BINARY(16), OUT p_id_solicitud BINARY(16), OUT p_cod_cliente VARCHAR(12),
    OUT p_monto DECIMAL(15,2), OUT p_moneda CHAR(3))
    COMMENT 'Comprueba que la evaluación sea una aprobación vigente sin desembolso.'
BEGIN
    DECLARE v_ronda, v_ultima SMALLINT;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_accion, v_decision VARCHAR(12);
    DECLARE v_fecha DATETIME(6);
    DECLARE v_primera DATE;
    SET p_id_solicitud = NULL;
    SELECT id_solicitud, ronda INTO p_id_solicitud, v_ronda FROM creditos.evaluacion WHERE id_evaluacion = p_id_evaluacion;
    IF p_id_solicitud IS NULL THEN
        CALL core.fallar('BNA-APROBACION: la evaluación no existe');
    END IF;
    SELECT estado_solicitud, cod_cliente, monto_solicitado, moneda INTO v_estado, p_cod_cliente, p_monto, p_moneda
      FROM creditos.solicitud_credito WHERE id_solicitud = p_id_solicitud FOR UPDATE;
    SELECT r.accion, d.decision, coalesce(d.fecha_decision, e.fecha_evaluacion) INTO v_accion, v_decision, v_fecha
      FROM creditos.evaluacion e
      JOIN creditos.regla_evaluacion r ON r.id_regla = e.id_regla
      LEFT JOIN creditos.decision_analista d ON d.id_evaluacion = e.id_evaluacion
     WHERE e.id_evaluacion = p_id_evaluacion FOR SHARE;
    SELECT max(ronda) INTO v_ultima FROM creditos.evaluacion WHERE id_solicitud = p_id_solicitud;
    IF v_estado <> 'APROBADA' OR v_ronda <> v_ultima OR NOT (v_accion = 'APROBADO' OR v_decision <=> 'APROBADO')
       OR EXISTS (SELECT 1 FROM creditos.orden_desembolso o JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
                   WHERE e.id_solicitud = p_id_solicitud AND o.estado_orden = 'CONFIRMADA') THEN
        CALL core.fallar('BNA-APROBACION: la solicitud no tiene una aprobación vigente sin desembolso');
    END IF;
    IF v_fecha + INTERVAL creditos.fn_dias_vigencia_aprobacion() DAY < UTC_TIMESTAMP(6) THEN
        CALL core.fallar('BNA-APROBACION: la aprobación venció');
    END IF;
    SELECT min(q.fecha_vencimiento) INTO v_primera
      FROM creditos.cuota q JOIN creditos.calendario_pago c ON c.id_calendario = q.id_calendario
     WHERE c.id_solicitud = p_id_solicitud AND c.tipo_calendario = 'PRELIMINAR' AND c.estado_calendario = 'VIGENTE';
    IF v_primera IS NULL OR v_primera <= core.fn_fecha_negocio(UTC_TIMESTAMP(6)) THEN
        CALL core.fallar('BNA-CALENDARIO: la primera cuota del calendario ya venció o falta el calendario');
    END IF;
END //

-- Interno: la cuenta admite el desembolso.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.validar_cuenta_desembolso(
    IN p_num_cuenta VARCHAR(20), IN p_cod_cliente VARCHAR(12), IN p_moneda CHAR(3))
    COMMENT 'Comprueba que la cuenta sea elegible para el desembolso.'
BEGIN
    IF NOT EXISTS (SELECT 1 FROM cuentas.cuenta_ahorro c
                     JOIN cuentas.titularidad t ON t.num_cuenta = c.num_cuenta AND t.cod_cliente = p_cod_cliente
                    WHERE c.num_cuenta = p_num_cuenta AND c.estado_cuenta = 'ACTIVA' AND c.regimen = 'INDIVIDUAL'
                      AND c.moneda = p_moneda) THEN
        CALL core.fallar('BNA-CUENTA-DESTINO: la cuenta debe ser de ahorros, activa, individual, del cliente y en la moneda del crédito');
    END IF;
END //

-- Interno: agrega una validación de la orden, siempre posterior a las anteriores.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.agregar_validacion(
    IN p_id_orden BINARY(16), IN p_tipo VARCHAR(15), IN p_resultado VARCHAR(25), IN p_evidencia VARCHAR(100),
    IN p_detalle VARCHAR(255), IN p_vence DATETIME(6))
    COMMENT 'Registra una validación previa al desembolso.'
BEGIN
    DECLARE v_momento DATETIME(6);
    SELECT GREATEST(UTC_TIMESTAMP(6), coalesce(max(creado_en) + INTERVAL 1 MICROSECOND, UTC_TIMESTAMP(6)))
      INTO v_momento FROM creditos.validacion_desembolso WHERE id_orden = p_id_orden;
    INSERT INTO creditos.validacion_desembolso (id_validacion, tipo_validacion, referencia_evidencia, resultado, detalle,
                                                vence_en, creado_en, id_orden)
    VALUES (core.uuid_v4(), p_tipo, p_evidencia, p_resultado, p_detalle, p_vence, v_momento, p_id_orden);
END //

-- Interno: con la última IDENTIDAD y la última CUENTA aprobadas (y vigentes) y ninguna
-- última validación rechazada, la orden queda VALIDADA; si no, PREPARADA.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.recalcular_orden(IN p_id_orden BINARY(16), OUT p_estado VARCHAR(25))
    COMMENT 'Deriva PREPARADA o VALIDADA de las validaciones de la orden.'
BEGIN
    DECLARE v_actual VARCHAR(25);
    DECLARE v_aprobadas, v_rechazadas INT;
    SELECT estado_orden INTO v_actual FROM creditos.orden_desembolso WHERE id_orden = p_id_orden;
    SELECT coalesce(sum(tipo_validacion IN ('IDENTIDAD', 'CUENTA') AND resultado = 'APROBADA'
                        AND (vence_en IS NULL OR vence_en > UTC_TIMESTAMP(6))), 0),
           coalesce(sum(resultado = 'RECHAZADA'), 0)
      INTO v_aprobadas, v_rechazadas
      FROM (SELECT tipo_validacion, resultado, vence_en,
                   ROW_NUMBER() OVER (PARTITION BY tipo_validacion ORDER BY creado_en DESC) AS n
              FROM creditos.validacion_desembolso WHERE id_orden = p_id_orden) v
     WHERE n = 1;
    SET p_estado = IF(v_aprobadas = 2 AND v_rechazadas = 0, 'VALIDADA', 'PREPARADA');
    IF p_estado <> v_actual THEN
        UPDATE creditos.orden_desembolso
           SET estado_orden = p_estado, actualizado_en = UTC_TIMESTAMP(6), version_registro = version_registro + 1
         WHERE id_orden = p_id_orden;
    END IF;
END //

-- Interno: un crédito con alguna cuota VENCIDA está EN_MORA; si no, AL_DIA. CANCELADO no cambia.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.recalcular_credito(IN p_cod_credito VARCHAR(20), OUT p_estado VARCHAR(25))
    COMMENT 'Recalcula AL_DIA o EN_MORA de un crédito.'
BEGIN
    DECLARE v_actual VARCHAR(25);
    DECLARE v_cal BINARY(16);
    SELECT estado_credito, id_calendario INTO v_actual, v_cal FROM creditos.credito WHERE cod_credito = p_cod_credito FOR UPDATE;
    SET p_estado = v_actual;
    IF v_actual <> 'CANCELADO' THEN
        SET p_estado = IF(EXISTS (SELECT 1 FROM creditos.cuota WHERE id_calendario = v_cal AND estado_cuota = 'VENCIDA'),
                          'EN_MORA', 'AL_DIA');
        IF p_estado <> v_actual THEN
            UPDATE creditos.credito SET estado_credito = p_estado WHERE cod_credito = p_cod_credito;
        END IF;
    END IF;
END //

-- El expediente de SOL (CR-INT-02). Una solicitud nueva queda EN_EVALUACION con su
-- calendario PRELIMINAR; una versión nueva, mientras la ronda vigente no esté evaluada, abre
-- otra ronda con otro calendario y deja el anterior HISTORICO. La misma versión con la
-- misma huella devuelve lo mismo (p_repetido); con otra huella se rechaza. p_cuotas:
-- [{numero_cuota, fecha_vencimiento, saldo_inicial, amortizacion, interes, cuota_total,
-- saldo_final}], tal como lo calcula SOL; la base comprueba que sea coherente.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.registrar_solicitud(
    IN p_id_solicitud BINARY(16), IN p_version SMALLINT, IN p_cod_cliente VARCHAR(12), IN p_monto DECIMAL(15,2),
    IN p_moneda CHAR(3), IN p_plazo SMALLINT, IN p_pago_doble BOOLEAN, IN p_metodo VARCHAR(20), IN p_tasa DECIMAL(7,4),
    IN p_cuotas JSON, IN p_huella CHAR(64), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_ronda SMALLINT, OUT p_id_evaluacion BINARY(16), OUT p_repetido BOOLEAN)
    COMMENT 'Registra una versión del expediente de SOL con su calendario PRELIMINAR.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_version SMALLINT;
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_huella CHAR(64);
    DECLARE v_ronda SMALLINT;
    DECLARE v_opera BOOLEAN;
    DECLARE v_n, v_malas INT;
    DECLARE v_saldo_final DECIMAL(15,2);
    DECLARE v_cal BINARY(16);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SET p_repetido = FALSE;
        IF p_id_solicitud IS NULL OR p_version IS NULL OR p_version < 1 OR p_huella IS NULL THEN
            CALL core.fallar('BNA-SOLICITUD: faltan el id, la versión o la huella del expediente');
        END IF;
        SELECT estado_solicitud, version_solicitud, cod_cliente INTO v_estado, v_version, v_cliente
          FROM creditos.solicitud_credito WHERE id_solicitud = p_id_solicitud FOR UPDATE;
        IF v_estado IS NOT NULL THEN
            SELECT ronda, huella INTO v_ronda, v_huella FROM creditos.recepcion_solicitud
             WHERE id_solicitud = p_id_solicitud AND version_solicitud = p_version FOR SHARE;
            IF v_huella IS NOT NULL THEN
                IF v_huella <> p_huella THEN
                    CALL core.fallar('BNA-IDEMPOTENCIA: esta versión del expediente ya se recibió con otro contenido');
                END IF;
                SET p_repetido = TRUE, p_ronda = v_ronda;
            END IF;
        END IF;
        IF NOT p_repetido THEN
            SELECT e.permite_operar INTO v_opera FROM clientes.cliente c
              JOIN clientes.estado_cliente e ON e.cod_estado = c.estado_cliente
             WHERE c.cod_cliente = p_cod_cliente;
            IF NOT (v_opera <=> TRUE) THEN
                CALL core.fallar('BNA-CLIENTE: el cliente no existe o no puede operar');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM core.moneda WHERE cod_moneda = p_moneda) THEN
                CALL core.fallar('BNA-SOLICITUD: moneda desconocida');
            END IF;
            IF p_monto IS NULL OR p_monto <= 0 OR p_plazo IS NULL OR p_plazo <= 0 THEN
                CALL core.fallar('BNA-SOLICITUD: el monto y el plazo deben ser positivos');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM creditos.metodo_amortizacion WHERE cod_metodo = p_metodo)
               OR p_tasa IS NULL OR p_tasa < 0 THEN
                CALL core.fallar('BNA-CALENDARIO: método de amortización desconocido o tasa no válida');
            END IF;
            SELECT COUNT(*),
                   coalesce(sum(numero_cuota IS NULL OR fecha_vencimiento IS NULL OR saldo_inicial IS NULL
                                OR amortizacion IS NULL OR interes IS NULL OR cuota_total IS NULL OR saldo_final IS NULL
                                OR amortizacion < 0 OR interes < 0 OR saldo_final < 0
                                OR cuota_total <> amortizacion + interes OR saldo_final <> saldo_inicial - amortizacion
                                OR numero_cuota <> n OR (n = 1 AND saldo_inicial <> p_monto)
                                OR (n > 1 AND (fecha_vencimiento <= fecha_anterior OR saldo_inicial <> saldo_anterior))), 0),
                   max(CASE WHEN n = total THEN saldo_final END)
              INTO v_n, v_malas, v_saldo_final
              FROM (SELECT j.*, ROW_NUMBER() OVER w AS n, COUNT(*) OVER () AS total,
                           LAG(j.fecha_vencimiento) OVER w AS fecha_anterior, LAG(j.saldo_final) OVER w AS saldo_anterior
                      FROM JSON_TABLE(IF(JSON_TYPE(p_cuotas) = 'ARRAY', p_cuotas, JSON_ARRAY()), '$[*]' COLUMNS (
                               numero_cuota INT PATH '$.numero_cuota',
                               fecha_vencimiento DATE PATH '$.fecha_vencimiento',
                               saldo_inicial DECIMAL(15,2) PATH '$.saldo_inicial',
                               amortizacion DECIMAL(15,2) PATH '$.amortizacion',
                               interes DECIMAL(15,2) PATH '$.interes',
                               cuota_total DECIMAL(15,2) PATH '$.cuota_total',
                               saldo_final DECIMAL(15,2) PATH '$.saldo_final')) j
                    WINDOW w AS (ORDER BY j.numero_cuota)) c;
            IF v_n = 0 OR v_n <> p_plazo OR v_malas > 0 OR NOT (v_saldo_final <=> 0.00) THEN
                CALL core.fallar('BNA-CALENDARIO: el calendario no es coherente con el monto, el plazo o sus propias cuotas');
            END IF;
            IF v_estado IS NULL THEN
                INSERT INTO creditos.solicitud_credito (id_solicitud, version_solicitud, monto_solicitado, moneda, plazo_meses,
                                                        condicion_pago_doble, estado_solicitud, cod_cliente)
                VALUES (p_id_solicitud, p_version, p_monto, p_moneda, p_plazo, coalesce(p_pago_doble, FALSE),
                        'EN_EVALUACION', p_cod_cliente);
                SET p_ronda = 1;
            ELSE
                IF v_cliente <> p_cod_cliente THEN
                    CALL core.fallar('BNA-SOLICITUD: el expediente pertenece a otro cliente');
                END IF;
                IF v_estado <> 'EN_EVALUACION' THEN
                    CALL core.fallar('BNA-SOLICITUD: la solicitud ya no admite versiones nuevas');
                END IF;
                IF p_version <= v_version THEN
                    CALL core.fallar('BNA-SOLICITUD: la versión no es posterior a la vigente');
                END IF;
                SELECT max(ronda) INTO v_ronda FROM creditos.recepcion_solicitud WHERE id_solicitud = p_id_solicitud;
                IF v_ronda IS NULL OR EXISTS (SELECT 1 FROM creditos.evaluacion
                                               WHERE id_solicitud = p_id_solicitud AND ronda = v_ronda) THEN
                    CALL core.fallar('BNA-SOLICITUD: la ronda vigente ya se evaluó');
                END IF;
                UPDATE creditos.solicitud_credito
                   SET version_solicitud = p_version, monto_solicitado = p_monto, moneda = p_moneda, plazo_meses = p_plazo,
                       condicion_pago_doble = coalesce(p_pago_doble, FALSE)
                 WHERE id_solicitud = p_id_solicitud;
                UPDATE creditos.calendario_pago SET estado_calendario = 'HISTORICO'
                 WHERE id_solicitud = p_id_solicitud AND estado_calendario = 'VIGENTE';
                SET p_ronda = v_ronda + 1;
            END IF;
            SET v_cal = core.uuid_v4();
            INSERT INTO creditos.calendario_pago (id_calendario, version, tipo_calendario, metodo_amortizacion, tasa_aplicada,
                                                  estado_calendario, id_solicitud)
            VALUES (v_cal, p_ronda, 'PRELIMINAR', p_metodo, p_tasa, 'VIGENTE', p_id_solicitud);
            INSERT INTO creditos.cuota (id_calendario, numero_cuota, fecha_vencimiento, capital, interes, otros_conceptos,
                                        saldo_capital, saldo_pendiente, estado_cuota)
            SELECT v_cal, j.numero_cuota, j.fecha_vencimiento, j.amortizacion, j.interes, 0, j.saldo_final, j.cuota_total,
                   'PENDIENTE'
              FROM JSON_TABLE(p_cuotas, '$[*]' COLUMNS (
                       numero_cuota INT PATH '$.numero_cuota',
                       fecha_vencimiento DATE PATH '$.fecha_vencimiento',
                       amortizacion DECIMAL(15,2) PATH '$.amortizacion',
                       interes DECIMAL(15,2) PATH '$.interes',
                       cuota_total DECIMAL(15,2) PATH '$.cuota_total',
                       saldo_final DECIMAL(15,2) PATH '$.saldo_final')) j;
            INSERT INTO creditos.recepcion_solicitud (id_solicitud, version_solicitud, ronda, huella)
            VALUES (p_id_solicitud, p_version, p_ronda, p_huella);
            INSERT INTO creditos.historial_estado_solicitud (estado_nuevo, actor, motivo, id_solicitud)
            VALUES ('EN_EVALUACION', p_actor, CONCAT('Versión ', p_version, ' recibida en la ronda ', p_ronda), p_id_solicitud);
            CALL core.registrar_evento('EVALUACION', 'solicitud_credito', BIN_TO_UUID(p_id_solicitud), 'REGISTRAR_SOLICITUD',
                                       p_actor, p_correlation_id,
                                       JSON_OBJECT('version', p_version, 'ronda', p_ronda, 'cod_cliente', p_cod_cliente,
                                                   'monto', p_monto, 'moneda', p_moneda, 'plazo_meses', p_plazo));
        END IF;
        SET p_id_evaluacion = creditos.fn_id_evaluacion(p_id_solicitud, p_ronda);
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- La evaluación de la ronda vigente (RN-EVA-002-P). COREDB calcula el score y el límite; la
-- base elige la regla por el ratio monto / límite con los umbrales de regla_evaluacion.
-- R-A deja la solicitud APROBADA, R-C RECHAZADA y R-B la deja EN_EVALUACION para el analista.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.evaluar_solicitud(
    IN p_id_solicitud BINARY(16), IN p_version SMALLINT, IN p_ingreso DECIMAL(15,2), IN p_deuda DECIMAL(15,2),
    IN p_score DECIMAL(6,2), IN p_limite DECIMAL(15,2), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_id_evaluacion BINARY(16), OUT p_resultado VARCHAR(12), OUT p_regla VARCHAR(10))
    COMMENT 'Evalúa la ronda vigente de una solicitud.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado, v_nuevo VARCHAR(25);
    DECLARE v_version, v_ronda SMALLINT;
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_monto DECIMAL(15,2);
    DECLARE v_consulta BINARY(16);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT estado_solicitud, version_solicitud, cod_cliente, monto_solicitado
          INTO v_estado, v_version, v_cliente, v_monto
          FROM creditos.solicitud_credito WHERE id_solicitud = p_id_solicitud FOR UPDATE;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-SOLICITUD: la solicitud no existe');
        END IF;
        IF v_estado <> 'EN_EVALUACION' THEN
            CALL core.fallar('BNA-SOLICITUD: la solicitud no está en evaluación');
        END IF;
        IF NOT (p_version <=> v_version) THEN
            CALL core.fallar('BNA-SOLICITUD: la versión evaluada no es la vigente');
        END IF;
        SELECT max(ronda) INTO v_ronda FROM creditos.recepcion_solicitud WHERE id_solicitud = p_id_solicitud;
        IF v_ronda IS NULL THEN
            CALL core.fallar('BNA-SOLICITUD: la solicitud no llegó por el expediente de SOL');
        END IF;
        IF EXISTS (SELECT 1 FROM creditos.evaluacion WHERE id_solicitud = p_id_solicitud AND ronda = v_ronda) THEN
            CALL core.fallar('BNA-EVALUACION: la ronda vigente ya se evaluó');
        END IF;
        IF p_ingreso IS NULL OR p_ingreso < 0 OR p_deuda IS NULL OR p_deuda < 0 OR p_limite IS NULL OR p_limite < 0
           OR p_score IS NULL THEN
            CALL core.fallar('BNA-EVALUACION: faltan datos de la evaluación o hay valores negativos');
        END IF;
        SET p_regla = NULL, p_id_evaluacion = creditos.fn_id_evaluacion(p_id_solicitud, v_ronda);
        IF p_limite = 0 THEN
            SELECT id_regla, accion INTO p_regla, p_resultado FROM creditos.regla_evaluacion
             WHERE ratio_max IS NULL AND ratio_min IS NOT NULL;
        ELSE
            SELECT id_regla, accion INTO p_regla, p_resultado FROM creditos.regla_evaluacion
             WHERE (ratio_min IS NULL OR v_monto * 100 > ratio_min * p_limite)
               AND (ratio_max IS NULL OR v_monto * 100 <= ratio_max * p_limite);
        END IF;
        IF p_regla IS NULL THEN
            CALL core.fallar('BNA-REGLA: ninguna regla de evaluación cubre el ratio');
        END IF;
        SET v_consulta = core.uuid_v4();
        INSERT INTO creditos.situacion_financiera (id_consulta, resultado_verificacion, ingreso_mensual, deuda_reportada,
                                                   cod_cliente)
        VALUES (v_consulta, 'VERIFICADO', p_ingreso, p_deuda, v_cliente);
        INSERT INTO creditos.evaluacion (id_evaluacion, ronda, score_calculado, limite_aprobado, id_solicitud, id_consulta,
                                         id_regla)
        VALUES (p_id_evaluacion, v_ronda, p_score, p_limite, p_id_solicitud, v_consulta, p_regla);
        IF p_resultado IN ('APROBADO', 'RECHAZADO') THEN
            SET v_nuevo = IF(p_resultado = 'APROBADO', 'APROBADA', 'RECHAZADA');
            UPDATE creditos.solicitud_credito SET estado_solicitud = v_nuevo WHERE id_solicitud = p_id_solicitud;
            INSERT INTO creditos.historial_estado_solicitud (estado_nuevo, actor, motivo, id_solicitud)
            VALUES (v_nuevo, p_actor, CONCAT('Regla ', p_regla), p_id_solicitud);
        END IF;
        CALL core.registrar_evento('EVALUACION', 'evaluacion', BIN_TO_UUID(p_id_evaluacion), 'EVALUAR_SOLICITUD', p_actor,
                                   p_correlation_id,
                                   JSON_OBJECT('id_solicitud', BIN_TO_UUID(p_id_solicitud), 'ronda', v_ronda,
                                               'regla', p_regla, 'resultado', p_resultado, 'score', p_score,
                                               'limite', p_limite));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- El analista decide una evaluación R-B de la ronda vigente, una sola vez (RN-EVA-004).
-- p_id_usuario es el usuario del token: debe estar ligado a un empleado activo registrado
-- como analista.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.decidir_evaluacion(
    IN p_id_evaluacion BINARY(16), IN p_decision VARCHAR(12), IN p_comentario VARCHAR(500), IN p_id_usuario BINARY(16),
    IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), OUT p_estado VARCHAR(25))
    COMMENT 'Registra la decisión del analista sobre una evaluación derivada.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_comentario VARCHAR(500) DEFAULT TRIM(p_comentario);
    DECLARE v_sol BINARY(16);
    DECLARE v_ronda SMALLINT;
    DECLARE v_accion VARCHAR(12);
    DECLARE v_estado VARCHAR(25);
    DECLARE v_analista VARCHAR(10);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_decision IS NULL OR p_decision NOT IN ('APROBADO', 'RECHAZADO') THEN
            CALL core.fallar('BNA-EVALUACION: la decisión es APROBADO o RECHAZADO');
        END IF;
        IF v_comentario IS NULL OR CHAR_LENGTH(v_comentario) < 10 THEN
            CALL core.fallar('BNA-MOTIVO: el comentario de la decisión es demasiado corto');
        END IF;
        SELECT e.id_solicitud, e.ronda, r.accion INTO v_sol, v_ronda, v_accion
          FROM creditos.evaluacion e JOIN creditos.regla_evaluacion r ON r.id_regla = e.id_regla
         WHERE e.id_evaluacion = p_id_evaluacion;
        IF v_sol IS NULL THEN
            CALL core.fallar('BNA-EVALUACION: la evaluación no existe');
        END IF;
        SELECT estado_solicitud INTO v_estado FROM creditos.solicitud_credito WHERE id_solicitud = v_sol FOR UPDATE;
        IF EXISTS (SELECT 1 FROM creditos.decision_analista WHERE id_evaluacion = p_id_evaluacion FOR SHARE) THEN
            CALL core.fallar('BNA-EVALUACION: la evaluación ya tiene una decisión');
        END IF;
        IF v_accion <> 'OBSERVADO' THEN
            CALL core.fallar('BNA-EVALUACION: solo se decide una evaluación derivada al analista');
        END IF;
        IF v_estado <> 'EN_EVALUACION'
           OR v_ronda <> (SELECT max(ronda) FROM creditos.evaluacion WHERE id_solicitud = v_sol) THEN
            CALL core.fallar('BNA-EVALUACION: la evaluación no es la vigente de la solicitud');
        END IF;
        SELECT a.id_analista INTO v_analista
          FROM core.usuario_sistema u
          JOIN core.empleado e ON e.id_empleado = u.id_empleado AND e.activo
          JOIN creditos.analista a ON a.codigo_empleado = e.codigo_empleado
         WHERE u.id_usuario = p_id_usuario AND u.activo;
        IF v_analista IS NULL THEN
            CALL core.fallar('BNA-ANALISTA: el usuario no es un analista registrado y activo');
        END IF;
        INSERT INTO creditos.decision_analista (id_decision, decision, comentario, id_evaluacion)
        VALUES (core.uuid_v4(), p_decision, v_comentario, p_id_evaluacion);
        UPDATE creditos.evaluacion SET id_analista = v_analista WHERE id_evaluacion = p_id_evaluacion;
        SET p_estado = IF(p_decision = 'APROBADO', 'APROBADA', 'RECHAZADA');
        UPDATE creditos.solicitud_credito SET estado_solicitud = p_estado WHERE id_solicitud = v_sol;
        INSERT INTO creditos.historial_estado_solicitud (estado_nuevo, actor, motivo, id_solicitud)
        VALUES (p_estado, p_actor, LEFT(v_comentario, 255), v_sol);
        CALL core.registrar_evento('EVALUACION', 'evaluacion', BIN_TO_UUID(p_id_evaluacion), 'DECIDIR_EVALUACION', p_actor,
                                   p_correlation_id,
                                   JSON_OBJECT('id_solicitud', BIN_TO_UUID(v_sol), 'decision', p_decision,
                                               'id_analista', v_analista));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Revoca una aprobación sin desembolso: la solicitud queda RECHAZADA con el motivo y sus
-- órdenes abiertas, RECHAZADA.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.revocar_aprobacion(
    IN p_id_solicitud BINARY(16), IN p_motivo VARCHAR(255), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16))
    COMMENT 'Revoca una aprobación antes del desembolso.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_ordenes JSON;
    DECLARE v_orden VARCHAR(36);
    DECLARE v_fin BOOLEAN DEFAULT FALSE;
    DECLARE c_ordenes CURSOR FOR
        SELECT j.id FROM JSON_TABLE(coalesce(v_ordenes, JSON_ARRAY()), '$[*]' COLUMNS (id VARCHAR(36) PATH '$')) j;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fin = TRUE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF coalesce(TRIM(p_motivo), '') = '' THEN
            CALL core.fallar('BNA-MOTIVO: revocar una aprobación exige un motivo');
        END IF;
        SELECT estado_solicitud INTO v_estado FROM creditos.solicitud_credito WHERE id_solicitud = p_id_solicitud FOR UPDATE;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-SOLICITUD: la solicitud no existe');
        END IF;
        IF v_estado <> 'APROBADA' OR EXISTS (
               SELECT 1 FROM creditos.orden_desembolso o JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
                WHERE e.id_solicitud = p_id_solicitud AND o.estado_orden = 'CONFIRMADA') THEN
            CALL core.fallar('BNA-SOLICITUD: solo se revoca una solicitud aprobada y no desembolsada');
        END IF;
        SELECT JSON_ARRAYAGG(BIN_TO_UUID(o.id_orden)) INTO v_ordenes
          FROM creditos.orden_desembolso o JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
         WHERE e.id_solicitud = p_id_solicitud AND o.estado_orden IN ('PREPARADA', 'VALIDADA') FOR UPDATE OF o;
        UPDATE creditos.orden_desembolso o JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
           SET o.estado_orden = 'RECHAZADA', o.motivo_rechazo = 'Aprobación revocada',
               o.actualizado_en = UTC_TIMESTAMP(6), o.version_registro = o.version_registro + 1
         WHERE e.id_solicitud = p_id_solicitud AND o.estado_orden IN ('PREPARADA', 'VALIDADA');
        UPDATE creditos.solicitud_credito SET estado_solicitud = 'RECHAZADA' WHERE id_solicitud = p_id_solicitud;
        INSERT INTO creditos.historial_estado_solicitud (estado_nuevo, actor, motivo, id_solicitud)
        VALUES ('RECHAZADA', p_actor, TRIM(p_motivo), p_id_solicitud);
        SET v_fin = FALSE;
        OPEN c_ordenes;
        recorrer: LOOP
            FETCH c_ordenes INTO v_orden;
            IF v_fin THEN
                LEAVE recorrer;
            END IF;
            CALL creditos.registrar_evento_credito('ORDEN', v_orden, NULL, 'RECHAZAR_ORDEN', 'RECHAZADA', 13, p_actor,
                                                   p_correlation_id, JSON_OBJECT('motivo', 'Aprobación revocada'));
        END LOOP;
        CLOSE c_ordenes;
        CALL core.registrar_evento('EVALUACION', 'solicitud_credito', BIN_TO_UUID(p_id_solicitud), 'REVOCAR_APROBACION',
                                   p_actor, p_correlation_id,
                                   JSON_OBJECT('motivo', TRIM(p_motivo), 'ordenes_rechazadas', coalesce(v_ordenes, JSON_ARRAY())));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Un administrador registra a un empleado activo como analista de crédito.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.registrar_analista(
    IN p_id_empleado BINARY(16), IN p_actor VARCHAR(40), OUT p_id_analista VARCHAR(10))
    COMMENT 'Registra un analista de crédito a partir de un empleado activo.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_codigo VARCHAR(20);
    DECLARE v_nombre VARCHAR(100);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT codigo_empleado, nombre_completo INTO v_codigo, v_nombre
          FROM core.empleado WHERE id_empleado = p_id_empleado AND activo;
        IF v_codigo IS NULL THEN
            CALL core.fallar('BNA-EMPLEADO: el empleado no existe o no está activo');
        END IF;
        SET p_id_analista = CONCAT('AN', UPPER(LEFT(SHA2(v_codigo, 256), 8)));
        INSERT INTO creditos.analista (id_analista, nombre, codigo_empleado) VALUES (p_id_analista, v_nombre, v_codigo);
        CALL core.registrar_evento('EVALUACION', 'analista', p_id_analista, 'REGISTRAR_ANALISTA', p_actor, NULL,
                                   JSON_OBJECT('codigo_empleado', v_codigo));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Prepara la orden de desembolso de una aprobación vigente, con la cuenta elegida. El
-- importe es el monto solicitado. La misma llave con la misma huella devuelve la misma
-- orden; con otra huella se rechaza. Una aprobación tiene a lo sumo una orden abierta.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.preparar_orden(
    IN p_id_evaluacion BINARY(16), IN p_num_cuenta VARCHAR(20), IN p_canal VARCHAR(5), IN p_id_agencia VARCHAR(10),
    IN p_llave BINARY(16), IN p_huella CHAR(64), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_id_orden BINARY(16), OUT p_codigo VARCHAR(24), OUT p_repetido BOOLEAN)
    COMMENT 'Prepara la orden de desembolso de una aprobación.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_huella CHAR(64);
    DECLARE v_sol BINARY(16);
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_monto DECIMAL(15,2);
    DECLARE v_moneda CHAR(3);
    DECLARE v_numero BIGINT;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SET p_repetido = FALSE, p_id_orden = NULL, p_codigo = NULL;
        IF p_llave IS NULL OR p_huella IS NULL OR p_correlation_id IS NULL THEN
            CALL core.fallar('BNA-IDEMPOTENCIA: faltan la llave, la huella o el correlation_id');
        END IF;
        SELECT id_orden, codigo_orden, request_hash INTO p_id_orden, p_codigo, v_huella
          FROM creditos.orden_desembolso WHERE idempotency_key = p_llave FOR SHARE;
        IF p_id_orden IS NOT NULL THEN
            IF v_huella <> p_huella THEN
                CALL core.fallar('BNA-IDEMPOTENCIA: la llave ya se usó con otros datos');
            END IF;
            SET p_repetido = TRUE;
        ELSE
            IF p_canal IS NULL OR p_canal NOT IN ('VEN', 'HB') THEN
                CALL core.fallar('BNA-CANAL: el desembolso es por ventanilla o Home Banking');
            END IF;
            CALL creditos.verificar_aprobacion(p_id_evaluacion, v_sol, v_cliente, v_monto, v_moneda);
            IF EXISTS (SELECT 1 FROM creditos.orden_desembolso o JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
                        WHERE e.id_solicitud = v_sol AND o.estado_orden IN ('PREPARADA', 'VALIDADA', 'EN_PROCESO', 'POR_VERIFICAR')) THEN
                CALL core.fallar('BNA-ORDEN: la aprobación ya tiene una orden abierta');
            END IF;
            CALL creditos.validar_cuenta_desembolso(p_num_cuenta, v_cliente, v_moneda);
            INSERT INTO creditos.numerador_orden () VALUES ();
            SET v_numero = LAST_INSERT_ID();
            IF v_numero > 999999 THEN
                CALL core.fallar('BNA-NUMERACION: se agotó la numeración de órdenes');
            END IF;
            SET p_codigo = CONCAT('DES-', YEAR(core.fn_fecha_negocio(UTC_TIMESTAMP(6))), '-', LPAD(v_numero, 6, '0'));
            SET p_id_orden = core.uuid_v4();
            INSERT INTO creditos.orden_desembolso (id_orden, codigo_orden, importe, estado_orden, idempotency_key,
                                                   request_hash, usuario_preparacion, correlation_id, id_evaluacion,
                                                   num_cuenta, id_canal, id_agencia)
            VALUES (p_id_orden, p_codigo, v_monto, 'PREPARADA', p_llave, p_huella, p_actor, p_correlation_id,
                    p_id_evaluacion, p_num_cuenta, p_canal, p_id_agencia);
            CALL creditos.agregar_validacion(p_id_orden, 'CUENTA', 'APROBADA', CONCAT('Cuenta terminada en ', RIGHT(p_num_cuenta, 4)),
                                             'De ahorros, activa, individual, del titular y en la moneda del crédito', NULL);
            CALL creditos.registrar_evento_credito('ORDEN', BIN_TO_UUID(p_id_orden), NULL, 'PREPARAR_ORDEN', 'PREPARADA', 13,
                                                   p_actor, p_correlation_id,
                                                   JSON_OBJECT('codigo_orden', p_codigo, 'id_evaluacion', BIN_TO_UUID(p_id_evaluacion),
                                                               'importe', v_monto, 'canal', p_canal));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Cambia la cuenta de una orden PREPARADA o VALIDADA; deja una validación CUENTA nueva.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.cambiar_cuenta_orden(
    IN p_id_orden BINARY(16), IN p_num_cuenta VARCHAR(20), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_estado VARCHAR(25))
    COMMENT 'Cambia la cuenta destino de una orden abierta.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_moneda CHAR(3);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT o.estado_orden, s.cod_cliente, s.moneda INTO v_estado, v_cliente, v_moneda
          FROM creditos.orden_desembolso o
          JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
          JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
         WHERE o.id_orden = p_id_orden FOR UPDATE OF o;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-ORDEN: la orden no existe');
        END IF;
        IF v_estado NOT IN ('PREPARADA', 'VALIDADA') THEN
            CALL core.fallar('BNA-ORDEN: la orden ya no admite cambios');
        END IF;
        CALL creditos.validar_cuenta_desembolso(p_num_cuenta, v_cliente, v_moneda);
        UPDATE creditos.orden_desembolso
           SET num_cuenta = p_num_cuenta, actualizado_en = UTC_TIMESTAMP(6), version_registro = version_registro + 1
         WHERE id_orden = p_id_orden;
        CALL creditos.agregar_validacion(p_id_orden, 'CUENTA', 'APROBADA', CONCAT('Cuenta terminada en ', RIGHT(p_num_cuenta, 4)),
                                         'De ahorros, activa, individual, del titular y en la moneda del crédito', NULL);
        CALL creditos.recalcular_orden(p_id_orden, p_estado);
        CALL creditos.registrar_evento_credito('ORDEN', BIN_TO_UUID(p_id_orden), NULL, 'CAMBIAR_CUENTA', p_estado, 13,
                                               p_actor, p_correlation_id,
                                               JSON_OBJECT('cuenta', CONCAT('terminada en ', RIGHT(p_num_cuenta, 4))));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Una validación previa al desembolso. IDENTIDAD aprobada exige como evidencia el
-- id_validacion de una verificación de identidad APROBADA hoy para el titular
-- (clientes.verificar_documento). La validación CUENTA la registra la base.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.registrar_validacion_orden(
    IN p_id_orden BINARY(16), IN p_tipo VARCHAR(15), IN p_resultado VARCHAR(25), IN p_evidencia VARCHAR(100),
    IN p_detalle VARCHAR(255), IN p_vence DATETIME(6), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_estado VARCHAR(25))
    COMMENT 'Registra una validación de la orden y recalcula su estado.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_cliente VARCHAR(12);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_tipo IS NULL OR p_tipo NOT IN ('IDENTIDAD', 'AUTORIZACION', 'ANTIFRAUDE') THEN
            CALL core.fallar('BNA-VALIDACION: el tipo es IDENTIDAD, AUTORIZACION o ANTIFRAUDE');
        END IF;
        IF p_resultado IS NULL OR p_resultado NOT IN ('APROBADA', 'RECHAZADA') THEN
            CALL core.fallar('BNA-VALIDACION: el resultado es APROBADA o RECHAZADA');
        END IF;
        IF coalesce(TRIM(p_evidencia), '') = '' THEN
            CALL core.fallar('BNA-VALIDACION: falta la referencia de la evidencia');
        END IF;
        SELECT o.estado_orden, s.cod_cliente INTO v_estado, v_cliente
          FROM creditos.orden_desembolso o
          JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
          JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
         WHERE o.id_orden = p_id_orden FOR UPDATE OF o;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-ORDEN: la orden no existe');
        END IF;
        IF v_estado NOT IN ('PREPARADA', 'VALIDADA') THEN
            CALL core.fallar('BNA-ORDEN: la orden ya no admite validaciones');
        END IF;
        IF p_tipo = 'IDENTIDAD' AND p_resultado = 'APROBADA'
           AND (NOT REGEXP_LIKE(TRIM(p_evidencia), '^[0-9]{1,18}$')
                OR NOT EXISTS (SELECT 1 FROM clientes.validacion_identidad
                                WHERE id_validacion = CAST(TRIM(p_evidencia) AS UNSIGNED) AND resultado = 'APROBADO'
                                  AND cod_cliente = v_cliente
                                  AND core.fn_fecha_negocio(fecha_evento) = core.fn_fecha_negocio(UTC_TIMESTAMP(6)))) THEN
            CALL core.fallar('BNA-VALIDACION: la evidencia no es una verificación de identidad aprobada hoy para el titular');
        END IF;
        CALL creditos.agregar_validacion(p_id_orden, p_tipo, p_resultado, TRIM(p_evidencia), p_detalle, p_vence);
        CALL creditos.recalcular_orden(p_id_orden, p_estado);
        CALL creditos.registrar_evento_credito('ORDEN', BIN_TO_UUID(p_id_orden), NULL, 'VALIDAR_ORDEN', p_resultado, 13,
                                               p_actor, p_correlation_id,
                                               JSON_OBJECT('tipo', p_tipo, 'estado_orden', p_estado));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Confirma una orden VALIDADA en una sola operación: revalida la aprobación, la cuenta y la
-- identidad (verificada hoy), registra el movimiento DESEMBOLSO, deja la orden CONFIRMADA,
-- crea el calendario OFICIAL (copia exacta del PRELIMINAR vigente, RN-SOL-006) y el
-- crédito AL_DIA, y deja la solicitud DESEMBOLSADA. Confirmar otra vez una orden
-- CONFIRMADA devuelve el mismo crédito y el mismo abono (p_repetido).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.confirmar_orden(
    IN p_id_orden BINARY(16), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_cod_credito VARCHAR(20), OUT p_uuid_abono BINARY(16), OUT p_repetido BOOLEAN)
    COMMENT 'Confirma el desembolso: abono, crédito y calendario oficial.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_eval, v_sol, v_abono, v_prel, v_oficial BINARY(16);
    DECLARE v_cuenta VARCHAR(20);
    DECLARE v_importe, v_monto DECIMAL(15,2);
    DECLARE v_canal VARCHAR(5);
    DECLARE v_codigo VARCHAR(24);
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_moneda CHAR(3);
    DECLARE v_validada VARCHAR(25);
    DECLARE v_metodo VARCHAR(20);
    DECLARE v_tasa DECIMAL(7,4);
    DECLARE v_version SMALLINT;
    DECLARE v_numero BIGINT;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SET p_repetido = FALSE, p_cod_credito = NULL, p_uuid_abono = NULL;
        SELECT estado_orden, id_evaluacion, num_cuenta, importe, id_canal, codigo_orden, uuid_transaccion_abono
          INTO v_estado, v_eval, v_cuenta, v_importe, v_canal, v_codigo, v_abono
          FROM creditos.orden_desembolso WHERE id_orden = p_id_orden FOR UPDATE;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-ORDEN: la orden no existe');
        END IF;
        IF v_estado = 'CONFIRMADA' THEN
            SELECT cod_credito INTO p_cod_credito FROM creditos.credito WHERE id_orden = p_id_orden FOR SHARE;
            SET p_uuid_abono = v_abono, p_repetido = TRUE;
        ELSE
            IF v_estado <> 'VALIDADA' THEN
                CALL core.fallar('BNA-ORDEN: la orden no está validada');
            END IF;
            IF p_correlation_id IS NULL THEN
                CALL core.fallar('BNA-CORRELACION: falta el correlation_id');
            END IF;
            CALL creditos.verificar_aprobacion(v_eval, v_sol, v_cliente, v_monto, v_moneda);
            CALL creditos.validar_cuenta_desembolso(v_cuenta, v_cliente, v_moneda);
            CALL creditos.recalcular_orden(p_id_orden, v_validada);
            IF v_validada <> 'VALIDADA' OR NOT EXISTS (
                   SELECT 1 FROM (SELECT resultado, creado_en,
                                         ROW_NUMBER() OVER (ORDER BY creado_en DESC) AS n
                                    FROM creditos.validacion_desembolso
                                   WHERE id_orden = p_id_orden AND tipo_validacion = 'IDENTIDAD') v
                    WHERE n = 1 AND resultado = 'APROBADA'
                      AND core.fn_fecha_negocio(creado_en) = core.fn_fecha_negocio(UTC_TIMESTAMP(6))) THEN
                CALL core.fallar('BNA-VALIDACION: la identidad del titular debe verificarse el mismo día del desembolso');
            END IF;
            CALL cuentas.validar_canal(v_canal, FALSE);
            CALL cuentas.aplicar_movimiento(v_cuenta, 'DESEMBOLSO', v_importe, CONCAT('Desembolso ', v_codigo), v_canal,
                                            p_correlation_id, p_uuid_abono);
            UPDATE creditos.orden_desembolso
               SET estado_orden = 'CONFIRMADA', uuid_transaccion_abono = p_uuid_abono, usuario_confirmacion = p_actor,
                   actualizado_en = UTC_TIMESTAMP(6), version_registro = version_registro + 1
             WHERE id_orden = p_id_orden;
            SELECT id_calendario, metodo_amortizacion, tasa_aplicada INTO v_prel, v_metodo, v_tasa
              FROM creditos.calendario_pago
             WHERE id_solicitud = v_sol AND tipo_calendario = 'PRELIMINAR' AND estado_calendario = 'VIGENTE' FOR UPDATE;
            SELECT max(version) + 1 INTO v_version FROM creditos.calendario_pago WHERE id_solicitud = v_sol;
            SET v_oficial = core.uuid_v4();
            UPDATE creditos.calendario_pago SET estado_calendario = 'HISTORICO' WHERE id_calendario = v_prel;
            INSERT INTO creditos.calendario_pago (id_calendario, version, tipo_calendario, metodo_amortizacion, tasa_aplicada,
                                                  estado_calendario, id_solicitud)
            VALUES (v_oficial, v_version, 'OFICIAL', v_metodo, v_tasa, 'VIGENTE', v_sol);
            INSERT INTO creditos.cuota (id_calendario, numero_cuota, fecha_vencimiento, capital, interes, otros_conceptos,
                                        saldo_capital, saldo_pendiente, estado_cuota)
            SELECT v_oficial, numero_cuota, fecha_vencimiento, capital, interes, otros_conceptos, saldo_capital,
                   capital + interes + otros_conceptos, 'PENDIENTE'
              FROM creditos.cuota WHERE id_calendario = v_prel;
            INSERT INTO creditos.numerador_credito () VALUES ();
            SET v_numero = LAST_INSERT_ID();
            IF v_numero > 999999 THEN
                CALL core.fallar('BNA-NUMERACION: se agotó la numeración de créditos');
            END IF;
            SET p_cod_credito = CONCAT('CRE-', YEAR(core.fn_fecha_negocio(UTC_TIMESTAMP(6))), '-', LPAD(v_numero, 6, '0'));
            INSERT INTO creditos.credito (cod_credito, estado_credito, id_orden, id_calendario)
            VALUES (p_cod_credito, 'AL_DIA', p_id_orden, v_oficial);
            UPDATE creditos.solicitud_credito SET estado_solicitud = 'DESEMBOLSADA' WHERE id_solicitud = v_sol;
            INSERT INTO creditos.historial_estado_solicitud (estado_nuevo, actor, motivo, id_solicitud)
            VALUES ('DESEMBOLSADA', p_actor, CONCAT('Orden ', v_codigo, ', crédito ', p_cod_credito), v_sol);
            CALL core.registrar_evento('CUENTAS', 'movimiento', BIN_TO_UUID(p_uuid_abono), 'DESEMBOLSO', p_actor,
                                       p_correlation_id,
                                       JSON_OBJECT('num_cuenta', v_cuenta, 'monto', v_importe, 'canal', v_canal,
                                                   'codigo_orden', v_codigo));
            CALL creditos.registrar_evento_credito('ORDEN', BIN_TO_UUID(p_id_orden), NULL, 'CONFIRMAR_ORDEN', 'CONFIRMADA', 13,
                                                   p_actor, p_correlation_id,
                                                   JSON_OBJECT('codigo_orden', v_codigo, 'cod_credito', p_cod_credito,
                                                               'uuid_abono', BIN_TO_UUID(p_uuid_abono), 'importe', v_importe));
            CALL creditos.registrar_evento_credito('CREDITO', p_cod_credito, NULL, 'CREAR_CREDITO', 'AL_DIA', 13,
                                                   p_actor, p_correlation_id,
                                                   JSON_OBJECT('codigo_orden', v_codigo, 'id_calendario', BIN_TO_UUID(v_oficial)));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Rechaza una orden PREPARADA o VALIDADA con su motivo. La aprobación sigue vigente.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.rechazar_orden(
    IN p_id_orden BINARY(16), IN p_motivo VARCHAR(255), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16))
    COMMENT 'Rechaza una orden de desembolso abierta.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF coalesce(TRIM(p_motivo), '') = '' THEN
            CALL core.fallar('BNA-MOTIVO: rechazar una orden exige un motivo');
        END IF;
        SELECT estado_orden INTO v_estado FROM creditos.orden_desembolso WHERE id_orden = p_id_orden FOR UPDATE;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-ORDEN: la orden no existe');
        END IF;
        IF v_estado NOT IN ('PREPARADA', 'VALIDADA') THEN
            CALL core.fallar('BNA-ORDEN: la orden ya no admite cambios');
        END IF;
        UPDATE creditos.orden_desembolso
           SET estado_orden = 'RECHAZADA', motivo_rechazo = TRIM(p_motivo), actualizado_en = UTC_TIMESTAMP(6),
               version_registro = version_registro + 1
         WHERE id_orden = p_id_orden;
        CALL creditos.registrar_evento_credito('ORDEN', BIN_TO_UUID(p_id_orden), NULL, 'RECHAZAR_ORDEN', 'RECHAZADA', 13,
                                               p_actor, p_correlation_id, JSON_OBJECT('motivo', TRIM(p_motivo)));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Pago de cuotas en una sola operación: debita la cuenta del titular (movimiento
-- DEBITO_CUOTA) y aplica el pago de la cuota más antigua a la más reciente
-- (creditos.aplicar_pago). Un débito rechazado por saldo, estado de la cuenta o tope deja
-- el pago RECHAZADO con el código de la regla (p_motivo) y sin movimiento. La referencia es
-- la llave: repetirla con la misma huella devuelve el mismo pago (p_repetido).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.registrar_pago_cuota(
    IN p_cod_credito VARCHAR(20), IN p_num_cuenta VARCHAR(20), IN p_monto DECIMAL(15,2), IN p_referencia VARCHAR(40),
    IN p_canal VARCHAR(5), IN p_huella CHAR(64), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_id_pago BINARY(16), OUT p_estado VARCHAR(25), OUT p_aplicado DECIMAL(15,2), OUT p_motivo VARCHAR(40),
    OUT p_repetido BOOLEAN)
    COMMENT 'Cobra un pago de cuotas: débito y aplicación.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(25);
    DECLARE v_cal, v_pago, v_movimiento BINARY(16);
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_moneda CHAR(3);
    DECLARE v_credito_pago VARCHAR(20);
    DECLARE v_huella CHAR(64);
    DECLARE v_deuda DECIMAL(15,2);
    DECLARE v_errno INT;
    DECLARE v_mensaje TEXT;
    DECLARE v_estado_credito VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SET p_repetido = FALSE, p_id_pago = NULL, p_estado = NULL, p_aplicado = 0, p_motivo = NULL;
        IF coalesce(TRIM(p_referencia), '') = '' OR p_huella IS NULL THEN
            CALL core.fallar('BNA-IDEMPOTENCIA: el pago exige una referencia y su huella');
        END IF;
        SELECT c.estado_credito, c.id_calendario, s.cod_cliente, s.moneda INTO v_estado, v_cal, v_cliente, v_moneda
          FROM creditos.credito c
          JOIN creditos.orden_desembolso o ON o.id_orden = c.id_orden
          JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
          JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
         WHERE c.cod_credito = p_cod_credito FOR UPDATE OF c;
        IF v_estado IS NULL THEN
            CALL core.fallar('BNA-CREDITO: el crédito no existe');
        END IF;
        SELECT p.id_pago, p.estado_confirmacion, p.cod_credito, cp.huella, cp.motivo_rechazo
          INTO v_pago, p_estado, v_credito_pago, v_huella, p_motivo
          FROM creditos.pago p LEFT JOIN creditos.cobro_pago cp ON cp.id_pago = p.id_pago
         WHERE p.referencia_transaccion = p_referencia FOR SHARE;
        IF v_pago IS NOT NULL THEN
            IF NOT (v_huella <=> p_huella) OR v_credito_pago <> p_cod_credito THEN
                CALL core.fallar('BNA-IDEMPOTENCIA: la referencia ya se usó con otros datos');
            END IF;
            SELECT coalesce(sum(monto_aplicado), 0) INTO p_aplicado FROM creditos.aplicacion_pago WHERE id_pago = v_pago;
            SET p_id_pago = v_pago, p_repetido = TRUE;
        ELSE
            IF v_estado = 'CANCELADO' THEN
                CALL core.fallar('BNA-CREDITO: el crédito está cancelado');
            END IF;
            IF p_monto IS NULL OR p_monto <= 0 THEN
                CALL core.fallar('BNA-PAGO: el monto debe ser positivo');
            END IF;
            SELECT coalesce(sum(saldo_pendiente), 0) INTO v_deuda FROM creditos.cuota WHERE id_calendario = v_cal;
            IF p_monto > v_deuda THEN
                CALL core.fallar('BNA-PAGO: el monto supera la deuda pendiente del crédito');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM cuentas.titularidad t JOIN cuentas.cuenta_ahorro a ON a.num_cuenta = t.num_cuenta
                            WHERE t.num_cuenta = p_num_cuenta AND t.cod_cliente = v_cliente AND a.moneda = v_moneda) THEN
                CALL core.fallar('BNA-CUENTA-ORIGEN: la cuenta no es del titular del crédito o no está en su moneda');
            END IF;
            IF p_correlation_id IS NULL THEN
                CALL core.fallar('BNA-CORRELACION: falta el correlation_id');
            END IF;
            CALL cuentas.validar_canal(p_canal, TRUE);
            SET p_id_pago = core.uuid_v4();
            -- El débito con su propio savepoint: un rechazo de la cuenta deja el pago
            -- RECHAZADO; cualquier otro error (y un deadlock) sigue hacia quien llama.
            BEGIN
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    GET STACKED DIAGNOSTICS CONDITION 1 v_errno = MYSQL_ERRNO, v_mensaje = MESSAGE_TEXT;
                    IF v_errno = 1644 AND SUBSTRING_INDEX(v_mensaje, ':', 1)
                                          IN ('BNA-SALDO', 'BNA-ESTADO-CUENTA', 'RN-TOP-001', 'RN-BD-002', 'BNA-CANAL') THEN
                        ROLLBACK TO SAVEPOINT bna_cobro;
                        SET p_motivo = SUBSTRING_INDEX(v_mensaje, ':', 1), v_movimiento = NULL;
                    ELSE
                        RESIGNAL;
                    END IF;
                END;
                SAVEPOINT bna_cobro;
                CALL cuentas.aplicar_movimiento(p_num_cuenta, 'DEBITO_CUOTA', p_monto,
                                                CONCAT('Cuota ', p_cod_credito, ' ref. ', p_referencia), p_canal,
                                                p_correlation_id, v_movimiento);
                RELEASE SAVEPOINT bna_cobro;
            END;
            SET p_estado = IF(p_motivo IS NULL, 'CONFIRMADO', 'RECHAZADO');
            INSERT INTO creditos.pago (id_pago, monto_pago, referencia_transaccion, estado_confirmacion, cod_credito, id_canal)
            VALUES (p_id_pago, p_monto, p_referencia, p_estado, p_cod_credito, p_canal);
            INSERT INTO creditos.cobro_pago (id_pago, num_cuenta, huella, uuid_transaccion, motivo_rechazo)
            VALUES (p_id_pago, p_num_cuenta, p_huella, v_movimiento, p_motivo);
            IF p_estado = 'CONFIRMADO' THEN
                CALL creditos.aplicar_pago(p_id_pago, p_aplicado);
                CALL creditos.recalcular_credito(p_cod_credito, v_estado_credito);
                CALL core.registrar_evento('CUENTAS', 'movimiento', BIN_TO_UUID(v_movimiento), 'DEBITO_CUOTA', p_actor,
                                           p_correlation_id,
                                           JSON_OBJECT('num_cuenta', p_num_cuenta, 'monto', p_monto, 'canal', p_canal,
                                                       'cod_credito', p_cod_credito));
            END IF;
            CALL creditos.registrar_evento_credito('PAGO', BIN_TO_UUID(p_id_pago), NULL, 'REGISTRAR_PAGO', p_estado, 14,
                                                   p_actor, p_correlation_id,
                                                   JSON_OBJECT('cod_credito', p_cod_credito, 'referencia', p_referencia,
                                                               'monto', p_monto, 'aplicado', p_aplicado, 'canal', p_canal,
                                                               'motivo', p_motivo));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Registra un cálculo de mora de una cuota vencida con saldo. Ninguna fuente define la
-- fórmula: la calcula quien llama y la base la guarda; la vigente es la última.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.registrar_mora(
    IN p_cod_credito VARCHAR(20), IN p_numero_cuota SMALLINT, IN p_monto DECIMAL(15,2), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_id_mora BINARY(16))
    COMMENT 'Registra un cálculo de mora de una cuota.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_cal BINARY(16);
    DECLARE v_vencimiento DATE;
    DECLARE v_saldo DECIMAL(15,2);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_monto IS NULL OR p_monto < 0 THEN
            CALL core.fallar('BNA-MORA: el monto de la mora falta o es negativo');
        END IF;
        SELECT id_calendario INTO v_cal FROM creditos.credito WHERE cod_credito = p_cod_credito FOR SHARE;
        IF v_cal IS NULL THEN
            CALL core.fallar('BNA-CREDITO: el crédito no existe');
        END IF;
        SELECT fecha_vencimiento, saldo_pendiente INTO v_vencimiento, v_saldo
          FROM creditos.cuota WHERE id_calendario = v_cal AND numero_cuota = p_numero_cuota;
        IF v_vencimiento IS NULL OR v_saldo = 0 OR v_vencimiento >= core.fn_fecha_negocio(UTC_TIMESTAMP(6)) THEN
            CALL core.fallar('BNA-CUOTA: la cuota no existe, no tiene saldo o aún no vence');
        END IF;
        SET p_id_mora = core.uuid_v4();
        INSERT INTO creditos.mora (id_mora, monto_calculado, fecha_calculo, id_calendario, numero_cuota)
        VALUES (p_id_mora, p_monto, UTC_TIMESTAMP(6), v_cal, p_numero_cuota);
        CALL creditos.registrar_evento_credito('CUOTA', CONCAT(p_cod_credito, ':', p_numero_cuota), p_numero_cuota,
                                               'REGISTRAR_MORA', NULL, 14, p_actor, p_correlation_id,
                                               JSON_OBJECT('monto', p_monto,
                                                           'dias_atraso', DATEDIFF(core.fn_fecha_negocio(UTC_TIMESTAMP(6)), v_vencimiento)));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Las cuotas PENDIENTE o PARCIAL vencidas antes de p_fecha (hoy si es nula) pasan a
-- VENCIDA, y cada crédito no cancelado queda EN_MORA si tiene una cuota VENCIDA o AL_DIA si
-- no. Solo los cambios dejan eventos. La corre el evento diario
-- creditos.ev_actualizar_vencimientos.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.actualizar_vencimientos(
    IN p_fecha DATE, IN p_actor VARCHAR(40), OUT p_cuotas INT, OUT p_creditos INT)
    COMMENT 'Marca las cuotas vencidas y recalcula el estado de los créditos.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_fecha DATE DEFAULT coalesce(p_fecha, core.fn_fecha_negocio(UTC_TIMESTAMP(6)));
    DECLARE v_correlacion BINARY(16) DEFAULT core.uuid_v4();
    DECLARE v_cuotas, v_creditos JSON;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_actor IS NULL THEN
            CALL core.fallar('BNA-ACTOR: falta el actor');
        END IF;
        SELECT JSON_ARRAYAGG(JSON_OBJECT('cod', c.cod_credito, 'n', q.numero_cuota)) INTO v_cuotas
          FROM creditos.cuota q JOIN creditos.credito c ON c.id_calendario = q.id_calendario
         WHERE c.estado_credito <> 'CANCELADO' AND q.estado_cuota IN ('PENDIENTE', 'PARCIAL')
           AND q.fecha_vencimiento < v_fecha
           FOR UPDATE OF q;
        UPDATE creditos.cuota q JOIN creditos.credito c ON c.id_calendario = q.id_calendario
           SET q.estado_cuota = 'VENCIDA'
         WHERE c.estado_credito <> 'CANCELADO' AND q.estado_cuota IN ('PENDIENTE', 'PARCIAL')
           AND q.fecha_vencimiento < v_fecha;
        SET p_cuotas = ROW_COUNT();
        SELECT JSON_ARRAYAGG(JSON_OBJECT('cod', x.cod_credito, 'estado', x.nuevo)) INTO v_creditos
          FROM (SELECT c.cod_credito, c.estado_credito,
                       IF(EXISTS (SELECT 1 FROM creditos.cuota q
                                   WHERE q.id_calendario = c.id_calendario AND q.estado_cuota = 'VENCIDA'),
                          'EN_MORA', 'AL_DIA') AS nuevo
                  FROM creditos.credito c WHERE c.estado_credito <> 'CANCELADO') x
         WHERE x.nuevo <> x.estado_credito;
        UPDATE creditos.credito c
          JOIN JSON_TABLE(coalesce(v_creditos, JSON_ARRAY()), '$[*]' COLUMNS (
                   cod VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs PATH '$.cod',
                   estado VARCHAR(25) PATH '$.estado')) j ON j.cod = c.cod_credito
           SET c.estado_credito = j.estado;
        SET p_creditos = ROW_COUNT();
        INSERT INTO creditos.entidad_auditada (id_entidad, tipo_entidad)
        SELECT CONCAT(j.cod, ':', j.n), 'CUOTA'
          FROM JSON_TABLE(coalesce(v_cuotas, JSON_ARRAY()), '$[*]' COLUMNS (
                   cod VARCHAR(20) PATH '$.cod', n SMALLINT PATH '$.n')) j
        ON DUPLICATE KEY UPDATE tipo_entidad = creditos.entidad_auditada.tipo_entidad;
        INSERT INTO creditos.evento_auditoria (modulo_emisor, id_entidad, numero_cuota, accion, resultado, actor,
                                               correlation_id, detalle)
        SELECT 14, CONCAT(j.cod, ':', j.n), j.n, 'VENCER_CUOTA', 'VENCIDA', p_actor, v_correlacion,
               JSON_OBJECT('fecha', v_fecha)
          FROM JSON_TABLE(coalesce(v_cuotas, JSON_ARRAY()), '$[*]' COLUMNS (
                   cod VARCHAR(20) PATH '$.cod', n SMALLINT PATH '$.n')) j;
        INSERT INTO creditos.entidad_auditada (id_entidad, tipo_entidad)
        SELECT j.cod, 'CREDITO'
          FROM JSON_TABLE(coalesce(v_creditos, JSON_ARRAY()), '$[*]' COLUMNS (cod VARCHAR(20) PATH '$.cod')) j
        ON DUPLICATE KEY UPDATE tipo_entidad = creditos.entidad_auditada.tipo_entidad;
        INSERT INTO creditos.evento_auditoria (modulo_emisor, id_entidad, accion, resultado, actor, correlation_id, detalle)
        SELECT 14, j.cod, 'ACTUALIZAR_ESTADO', j.estado, p_actor, v_correlacion, JSON_OBJECT('fecha', v_fecha)
          FROM JSON_TABLE(coalesce(v_creditos, JSON_ARRAY()), '$[*]' COLUMNS (
                   cod VARCHAR(20) PATH '$.cod', estado VARCHAR(25) PATH '$.estado')) j;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

-- Los catálogos que la API publica y usa para validar antes de llamar.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE creditos.catalogos_credito(OUT p_catalogos JSON)
    READS SQL DATA
    COMMENT 'Catálogos de la línea de créditos, en JSON.'
BEGIN
    SET p_catalogos = JSON_OBJECT(
        'estados_solicitud', (SELECT CAST(CONCAT('[', GROUP_CONCAT(JSON_OBJECT(
                                  'codigo', cod_estado, 'descripcion', descripcion,
                                  'es_final', CAST(IF(es_final, 'true', 'false') AS JSON)) ORDER BY cod_estado), ']') AS JSON)
                                FROM creditos.estado_solicitud),
        'reglas', (SELECT CAST(CONCAT('[', GROUP_CONCAT(JSON_OBJECT(
                       'id_regla', id_regla, 'codigo_rn', codigo_rn, 'descripcion', descripcion,
                       'ratio_min', ratio_min, 'ratio_max', ratio_max, 'resultado', accion) ORDER BY id_regla), ']') AS JSON)
                     FROM creditos.regla_evaluacion),
        'metodos_amortizacion', (SELECT CAST(CONCAT('[', GROUP_CONCAT(JSON_OBJECT(
                                     'codigo', cod_metodo, 'descripcion', descripcion) ORDER BY cod_metodo), ']') AS JSON)
                                   FROM creditos.metodo_amortizacion),
        'tipos_validacion', (SELECT CAST(CONCAT('[', GROUP_CONCAT(JSON_OBJECT(
                                 'codigo', tipo_validacion, 'descripcion', descripcion) ORDER BY tipo_validacion), ']') AS JSON)
                               FROM creditos.tipo_validacion_desembolso),
        'estados_orden', (SELECT CAST(CONCAT('[', GROUP_CONCAT(JSON_OBJECT(
                              'codigo', cod_estado, 'descripcion', descripcion,
                              'es_final', CAST(IF(es_final, 'true', 'false') AS JSON)) ORDER BY cod_estado), ']') AS JSON)
                            FROM creditos.estado_orden),
        'estados_cuota', (SELECT CAST(CONCAT('[', GROUP_CONCAT(JSON_OBJECT(
                              'codigo', cod_estado, 'descripcion', descripcion) ORDER BY cod_estado), ']') AS JSON)
                            FROM creditos.estado_cuota),
        'estados_credito', (SELECT CAST(CONCAT('[', GROUP_CONCAT(JSON_OBJECT(
                                'codigo', cod_estado, 'descripcion', descripcion) ORDER BY cod_estado), ']') AS JSON)
                              FROM creditos.estado_credito),
        'canales_desembolso', JSON_ARRAY('VEN', 'HB'),
        'vigencia_aprobacion_dias', creditos.fn_dias_vigencia_aprobacion());
END //

CREATE DEFINER = 'bna_owner'@'%' EVENT creditos.ev_actualizar_vencimientos
    ON SCHEDULE EVERY 1 DAY STARTS '2026-01-01 05:10:00'
    ON COMPLETION PRESERVE ENABLE
    COMMENT 'Una vez al día, 00:10 de Arequipa: marca las cuotas vencidas y recalcula los créditos.'
    DO CALL creditos.actualizar_vencimientos(NULL, 'SISTEMA', @bna_cuotas_vencidas, @bna_creditos_actualizados) //

DELIMITER ;

-- Lecturas de créditos para bna_api, sin nombres, documentos ni contactos del cliente.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_solicitud_api AS
SELECT s.id_solicitud, s.version_solicitud,
       (SELECT max(r.ronda) FROM creditos.recepcion_solicitud r WHERE r.id_solicitud = s.id_solicitud) AS ronda,
       s.cod_cliente, s.monto_solicitado, s.moneda, s.plazo_meses, s.condicion_pago_doble, s.estado_solicitud,
       s.fecha_creacion, c.id_calendario, c.tipo_calendario, c.metodo_amortizacion, c.tasa_aplicada,
       (SELECT count(*) FROM creditos.cuota q WHERE q.id_calendario = c.id_calendario) AS numero_cuotas,
       (SELECT sum(q.capital + q.interes + q.otros_conceptos) FROM creditos.cuota q
         WHERE q.id_calendario = c.id_calendario) AS total_cuotas,
       (SELECT min(q.fecha_vencimiento) FROM creditos.cuota q WHERE q.id_calendario = c.id_calendario) AS primer_vencimiento
  FROM creditos.solicitud_credito s
  LEFT JOIN creditos.calendario_pago c ON c.id_solicitud = s.id_solicitud AND c.estado_calendario = 'VIGENTE';

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_calendario_api AS
SELECT c.id_solicitud, c.id_calendario, c.version, c.tipo_calendario, c.estado_calendario, c.metodo_amortizacion,
       c.tasa_aplicada, q.numero_cuota, q.fecha_vencimiento, q.capital, q.interes, q.otros_conceptos, q.saldo_capital,
       q.capital + q.interes + q.otros_conceptos AS cuota_total, q.saldo_pendiente, q.estado_cuota
  FROM creditos.calendario_pago c
  JOIN creditos.cuota q ON q.id_calendario = c.id_calendario;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_historial_solicitud_api AS
SELECT id_historial, id_solicitud, estado_nuevo, fecha_hora, actor, motivo
  FROM creditos.historial_estado_solicitud;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_evaluacion_api AS
SELECT e.id_evaluacion, e.id_solicitud, e.ronda, e.fecha_evaluacion, e.score_calculado, e.limite_aprobado, e.id_regla,
       r.accion AS resultado_regla, f.ingreso_mensual, f.deuda_reportada, f.resultado_verificacion,
       d.decision, d.comentario, d.fecha_decision, e.id_analista, coalesce(d.decision, r.accion) AS resultado,
       e.ronda = (SELECT max(e2.ronda) FROM creditos.evaluacion e2 WHERE e2.id_solicitud = e.id_solicitud) AS es_ultima
  FROM creditos.evaluacion e
  JOIN creditos.regla_evaluacion r ON r.id_regla = e.id_regla
  JOIN creditos.situacion_financiera f ON f.id_consulta = e.id_consulta
  LEFT JOIN creditos.decision_analista d ON d.id_evaluacion = e.id_evaluacion;

-- Las aprobaciones que todavía admiten un desembolso: la última ronda, aprobada por la
-- regla o por el analista, vigente y sin orden confirmada.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_aprobacion_api AS
SELECT e.id_evaluacion, s.id_solicitud, s.cod_cliente, e.ronda, s.monto_solicitado AS monto, s.moneda, s.plazo_meses,
       e.limite_aprobado, coalesce(d.fecha_decision, e.fecha_evaluacion) AS fecha_aprobacion,
       coalesce(d.fecha_decision, e.fecha_evaluacion) + INTERVAL creditos.fn_dias_vigencia_aprobacion() DAY AS vigente_hasta,
       c.id_calendario
  FROM creditos.solicitud_credito s
  JOIN creditos.evaluacion e ON e.id_solicitud = s.id_solicitud
  JOIN creditos.regla_evaluacion r ON r.id_regla = e.id_regla
  LEFT JOIN creditos.decision_analista d ON d.id_evaluacion = e.id_evaluacion
  LEFT JOIN creditos.calendario_pago c
         ON c.id_solicitud = s.id_solicitud AND c.tipo_calendario = 'PRELIMINAR' AND c.estado_calendario = 'VIGENTE'
 WHERE s.estado_solicitud = 'APROBADA'
   AND e.ronda = (SELECT max(e2.ronda) FROM creditos.evaluacion e2 WHERE e2.id_solicitud = s.id_solicitud)
   AND (r.accion = 'APROBADO' OR d.decision = 'APROBADO')
   AND coalesce(d.fecha_decision, e.fecha_evaluacion) + INTERVAL creditos.fn_dias_vigencia_aprobacion() DAY >= UTC_TIMESTAMP(6)
   AND NOT EXISTS (SELECT 1 FROM creditos.orden_desembolso o JOIN creditos.evaluacion e3 ON e3.id_evaluacion = o.id_evaluacion
                    WHERE e3.id_solicitud = s.id_solicitud AND o.estado_orden = 'CONFIRMADA');

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_orden_api AS
SELECT o.id_orden, o.codigo_orden, o.estado_orden, o.motivo_rechazo, o.importe, s.moneda, o.num_cuenta, o.id_canal,
       o.id_agencia, o.id_evaluacion, s.id_solicitud, s.cod_cliente, o.usuario_preparacion, o.usuario_confirmacion,
       o.uuid_transaccion_abono, c.cod_credito, o.creado_en, o.actualizado_en
  FROM creditos.orden_desembolso o
  JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
  JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
  LEFT JOIN creditos.credito c ON c.id_orden = o.id_orden;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_validacion_orden_api AS
SELECT id_validacion, id_orden, tipo_validacion, resultado, referencia_evidencia, detalle, vence_en, creado_en
  FROM creditos.validacion_desembolso;

-- La mora vigente de una cuota es el último cálculo; el crédito suma la de sus cuotas con saldo.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_credito_api AS
SELECT c.cod_credito, c.estado_credito, s.cod_cliente, s.id_solicitud, o.id_orden, o.codigo_orden, s.moneda,
       o.importe AS monto_desembolsado, coalesce(m.fecha_hora, o.actualizado_en) AS fecha_desembolso, c.id_calendario,
       q.numero_cuotas, q.cuotas_pagadas, q.cuotas_vencidas, q.saldo_pendiente, q.proximo_vencimiento,
       coalesce(mv.mora_vigente, 0) AS mora_vigente
  FROM creditos.credito c
  JOIN creditos.orden_desembolso o ON o.id_orden = c.id_orden
  JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
  JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
  LEFT JOIN cuentas.movimiento m ON m.uuid_transaccion = o.uuid_transaccion_abono
  JOIN (SELECT id_calendario, count(*) AS numero_cuotas, sum(estado_cuota = 'PAGADA') AS cuotas_pagadas,
               sum(estado_cuota = 'VENCIDA') AS cuotas_vencidas, sum(saldo_pendiente) AS saldo_pendiente,
               min(CASE WHEN saldo_pendiente > 0 THEN fecha_vencimiento END) AS proximo_vencimiento
          FROM creditos.cuota GROUP BY id_calendario) q ON q.id_calendario = c.id_calendario
  LEFT JOIN (SELECT x.id_calendario, sum(x.monto_calculado) AS mora_vigente
               FROM (SELECT mo.id_calendario, mo.numero_cuota, mo.monto_calculado,
                            ROW_NUMBER() OVER (PARTITION BY mo.id_calendario, mo.numero_cuota
                                               ORDER BY mo.fecha_calculo DESC) AS n
                       FROM creditos.mora mo) x
               JOIN creditos.cuota qq ON qq.id_calendario = x.id_calendario AND qq.numero_cuota = x.numero_cuota
              WHERE x.n = 1 AND qq.saldo_pendiente > 0
              GROUP BY x.id_calendario) mv ON mv.id_calendario = c.id_calendario;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_cuota_api AS
SELECT c.cod_credito, q.numero_cuota, q.fecha_vencimiento, q.capital, q.interes, q.otros_conceptos,
       q.capital + q.interes + q.otros_conceptos AS cuota_total, q.saldo_pendiente, q.estado_cuota,
       IF(q.saldo_pendiente > 0, GREATEST(0, DATEDIFF(core.fn_fecha_negocio(UTC_TIMESTAMP(6)), q.fecha_vencimiento)), 0)
           AS dias_atraso,
       coalesce(mv.monto_calculado, 0) AS mora_vigente
  FROM creditos.credito c
  JOIN creditos.cuota q ON q.id_calendario = c.id_calendario
  LEFT JOIN (SELECT x.id_calendario, x.numero_cuota, x.monto_calculado
               FROM (SELECT mo.id_calendario, mo.numero_cuota, mo.monto_calculado,
                            ROW_NUMBER() OVER (PARTITION BY mo.id_calendario, mo.numero_cuota
                                               ORDER BY mo.fecha_calculo DESC) AS n
                       FROM creditos.mora mo) x
              WHERE x.n = 1) mv ON mv.id_calendario = q.id_calendario AND mv.numero_cuota = q.numero_cuota;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_pago_api AS
SELECT p.id_pago, p.referencia_transaccion AS referencia, p.cod_credito, p.fecha_hora, p.monto_pago,
       p.estado_confirmacion, p.id_canal, cp.num_cuenta, cp.uuid_transaccion, cp.motivo_rechazo,
       coalesce(a.monto_aplicado, 0) AS monto_aplicado, coalesce(a.aplicaciones, JSON_ARRAY()) AS aplicaciones
  FROM creditos.pago p
  LEFT JOIN creditos.cobro_pago cp ON cp.id_pago = p.id_pago
  LEFT JOIN (SELECT id_pago, sum(monto_aplicado) AS monto_aplicado,
                    JSON_ARRAYAGG(JSON_OBJECT('numero_cuota', numero_cuota, 'monto_aplicado', monto_aplicado)) AS aplicaciones
               FROM creditos.aplicacion_pago GROUP BY id_pago) a ON a.id_pago = p.id_pago;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_mora_api AS
SELECT m.id_mora, c.cod_credito, m.numero_cuota, m.monto_calculado, m.fecha_calculo,
       GREATEST(0, DATEDIFF(core.fn_fecha_negocio(m.fecha_calculo), q.fecha_vencimiento)) AS dias_atraso,
       m.fecha_calculo = (SELECT max(m2.fecha_calculo) FROM creditos.mora m2
                           WHERE m2.id_calendario = m.id_calendario AND m2.numero_cuota = m.numero_cuota) AS vigente
  FROM creditos.mora m
  JOIN creditos.cuota q ON q.id_calendario = m.id_calendario AND q.numero_cuota = m.numero_cuota
  JOIN creditos.credito c ON c.id_calendario = m.id_calendario;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_evento_credito_api AS
SELECT ev.id_evento, mo.nombre AS modulo, ea.tipo_entidad, ev.id_entidad, ev.numero_cuota, ev.accion, ev.resultado,
       ev.actor, ev.correlation_id, ev.detalle, ev.fecha_hora
  FROM creditos.evento_auditoria ev
  JOIN core.modulo mo ON mo.id_modulo = ev.modulo_emisor
  LEFT JOIN creditos.entidad_auditada ea ON ea.id_entidad = ev.id_entidad;

-- Lo cobrado (movimientos DEBITO_CUOTA) frente a lo aplicado a cuotas, por día de negocio,
-- canal y moneda.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW creditos.v_conciliacion_cobranza AS
SELECT core.fn_fecha_negocio(p.fecha_hora) AS fecha, p.id_canal, s.moneda,
       count(CASE WHEN p.estado_confirmacion = 'CONFIRMADO' THEN 1 END) AS pagos_confirmados,
       coalesce(sum(CASE WHEN p.estado_confirmacion = 'CONFIRMADO' THEN mv.monto END), 0) AS importe_cobrado,
       coalesce(sum(a.aplicado), 0) AS importe_aplicado,
       count(CASE WHEN p.estado_confirmacion = 'RECHAZADO' THEN 1 END) AS pagos_rechazados
  FROM creditos.pago p
  JOIN creditos.credito c ON c.cod_credito = p.cod_credito
  JOIN creditos.orden_desembolso o ON o.id_orden = c.id_orden
  JOIN creditos.evaluacion e ON e.id_evaluacion = o.id_evaluacion
  JOIN creditos.solicitud_credito s ON s.id_solicitud = e.id_solicitud
  LEFT JOIN creditos.cobro_pago cp ON cp.id_pago = p.id_pago
  LEFT JOIN cuentas.movimiento mv ON mv.uuid_transaccion = cp.uuid_transaccion
  LEFT JOIN (SELECT id_pago, sum(monto_aplicado) AS aplicado FROM creditos.aplicacion_pago GROUP BY id_pago) a
         ON a.id_pago = p.id_pago
 GROUP BY core.fn_fecha_negocio(p.fecha_hora), p.id_canal, s.moneda;

GRANT EXECUTE ON FUNCTION creditos.fn_id_evaluacion TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.registrar_solicitud TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.evaluar_solicitud TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.decidir_evaluacion TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.revocar_aprobacion TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.registrar_analista TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.preparar_orden TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.cambiar_cuenta_orden TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.registrar_validacion_orden TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.confirmar_orden TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.rechazar_orden TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.registrar_pago_cuota TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.registrar_mora TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.actualizar_vencimientos TO bna_api;
GRANT EXECUTE ON PROCEDURE creditos.catalogos_credito TO bna_api;
GRANT SELECT ON creditos.v_solicitud_api TO bna_api;
GRANT SELECT ON creditos.v_calendario_api TO bna_api;
GRANT SELECT ON creditos.v_historial_solicitud_api TO bna_api;
GRANT SELECT ON creditos.v_evaluacion_api TO bna_api;
GRANT SELECT ON creditos.v_aprobacion_api TO bna_api;
GRANT SELECT ON creditos.v_orden_api TO bna_api;
GRANT SELECT ON creditos.v_validacion_orden_api TO bna_api;
GRANT SELECT ON creditos.v_credito_api TO bna_api;
GRANT SELECT ON creditos.v_cuota_api TO bna_api;
GRANT SELECT ON creditos.v_pago_api TO bna_api;
GRANT SELECT ON creditos.v_mora_api TO bna_api;
GRANT SELECT ON creditos.v_evento_credito_api TO bna_api;
GRANT SELECT ON creditos.v_conciliacion_cobranza TO bna_api;
GRANT SELECT ON creditos.v_conciliacion_diaria TO bna_api;

-- ---------------------------------------------------------------------
-- 13. Empleados (v1.6)
-- ---------------------------------------------------------------------
-- Un administrador registra empleados por la API, sin el administrador de la base, y los
-- liga a su usuario: así un ANALISTA puede quedar registrado (creditos.registrar_analista)
-- y decidir. Sigue el patrón de la sección 8 y se concede solo a bna_api; bna_admin lo
-- ejecuta por su privilegio sobre core.*. El evento guarda el código y el cargo, no el
-- nombre; los mensajes de error no repiten ningún valor de entrada.

DELIMITER //

-- p_id_usuario es opcional: una persona activa o no, sin empleado. El empleado nace activo.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE core.registrar_empleado(
    IN p_id BINARY(16), IN p_codigo VARCHAR(20), IN p_nombre VARCHAR(100), IN p_cargo VARCHAR(30),
    IN p_id_agencia VARCHAR(10), IN p_id_usuario BINARY(16), IN p_actor VARCHAR(40))
    COMMENT 'Registra un empleado y, si se indica, lo liga a un usuario del sistema.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_codigo VARCHAR(20) DEFAULT TRIM(p_codigo);
    DECLARE v_nombre VARCHAR(100) DEFAULT TRIM(p_nombre);
    DECLARE v_cargo VARCHAR(30) DEFAULT UPPER(TRIM(p_cargo));
    DECLARE v_rol VARCHAR(15);
    DECLARE v_empleado BINARY(16);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF coalesce(v_codigo, '') = '' OR coalesce(v_nombre, '') = '' OR coalesce(v_cargo, '') = '' THEN
            CALL core.fallar('BNA-EMPLEADO-DATOS: faltan el código, el nombre o el cargo');
        END IF;
        IF p_id_agencia IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM core.agencia WHERE id_agencia = p_id_agencia) THEN
            CALL core.fallar('BNA-AGENCIA: la agencia no existe');
        END IF;
        IF EXISTS (SELECT 1 FROM core.empleado WHERE codigo_empleado = v_codigo FOR SHARE) THEN
            CALL core.fallar('BNA-EMPLEADO-DUPLICADO: el código de empleado ya existe');
        END IF;
        IF p_id_usuario IS NOT NULL THEN
            SELECT rol, id_empleado INTO v_rol, v_empleado
              FROM core.usuario_sistema WHERE id_usuario = p_id_usuario FOR UPDATE;
            IF v_rol IS NULL THEN
                CALL core.fallar('BNA-USUARIO: el usuario no existe');
            END IF;
            IF v_rol = 'SERVICIO' THEN
                CALL core.fallar('BNA-USUARIO-EMPLEADO: un usuario de servicio no se liga a un empleado');
            END IF;
            IF v_empleado IS NOT NULL THEN
                CALL core.fallar('BNA-USUARIO-EMPLEADO: el usuario ya está ligado a un empleado');
            END IF;
        END IF;
        INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo, id_agencia, activo)
        VALUES (p_id, v_codigo, v_nombre, v_cargo, p_id_agencia, TRUE);
        IF p_id_usuario IS NOT NULL THEN
            UPDATE core.usuario_sistema SET id_empleado = p_id WHERE id_usuario = p_id_usuario;
        END IF;
        CALL core.registrar_evento('CORE', 'empleado', BIN_TO_UUID(p_id), 'REGISTRAR_EMPLEADO', p_actor, NULL,
                                   JSON_OBJECT('codigo_empleado', v_codigo, 'cargo', v_cargo,
                                               'id_usuario', IF(p_id_usuario IS NULL, NULL, BIN_TO_UUID(p_id_usuario))));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

DELIMITER ;

GRANT EXECUTE ON PROCEDURE core.registrar_empleado TO bna_api;

-- ---------------------------------------------------------------------
-- 14. Captación (v1.7)
-- ---------------------------------------------------------------------
-- El expediente del prospecto, que todavía no es cliente: quién pidió, qué consintió,
-- cómo se verificó su identidad, qué dijeron las centrales y si quedó habilitado. Son
-- tablas de extensión del esquema clientes; el modelo normalizado no cambia. Solo se
-- ligan a él por el cliente que resulta (clientes.cliente), la agencia y, a través del
-- cliente, su verificación de captación. Los proveedores (RENIEC, listas, PEP,
-- centrales, SMS) y el puntaje son del módulo CAPTACION: la base guarda lo que
-- responden y aplica las reglas del expediente (consentimientos exigidos, OTP con
-- vencimiento e intentos de clientes.tipo_contacto, un caso abierto por solicitante,
-- estado recalculado tras cada paso). El hash del OTP lo calcula CAPTACION con su clave;
-- la base solo lo compara y ninguna vista lo expone. El estado sigue
-- INICIADO → EN_VALIDACION → APROBADO → HABILITADO, con OBSERVADO mientras algo quede por
-- resolver y RECHAZADO o REVOCADO como finales. Los eventos van al módulo CLIENTES
-- (core.modulo no tiene CAPTACION: punto R-01) sin documento, nombres ni contactos. Sigue
-- el patrón de la sección 8 y se concede solo a bna_api.

CREATE TABLE clientes.solicitante_captacion (
    id_solicitante     BINARY(16),
    tipo_documento     VARCHAR(10) NOT NULL,
    numero_documento   VARCHAR(12) NOT NULL,
    nombres            VARCHAR(100) NOT NULL,
    apellido_paterno   VARCHAR(100) NOT NULL,
    apellido_materno   VARCHAR(100),
    celular            CHAR(9) NOT NULL,
    correo             VARCHAR(150) NOT NULL,
    cod_cliente        VARCHAR(12),
    creado_por         VARCHAR(40) NOT NULL,
    fecha_registro     DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_solicitante_captacion PRIMARY KEY (id_solicitante),
    CONSTRAINT uk_solicitante_captacion_1 UNIQUE (tipo_documento, numero_documento),
    CONSTRAINT fk_solicitante_captacion_1 FOREIGN KEY (tipo_documento) REFERENCES clientes.tipo_documento (cod_tipo_documento),
    CONSTRAINT fk_solicitante_captacion_2 FOREIGN KEY (cod_cliente) REFERENCES clientes.cliente (cod_cliente),
    CONSTRAINT ck_solicitante_captacion_1 CHECK (REGEXP_LIKE(celular, '^9[0-9]{8}$'))
) ENGINE = InnoDB COMMENT = 'Extensión de integración: el prospecto de captación, antes de ser cliente.';

CREATE TABLE clientes.caso_captacion (
    id_caso            BINARY(16),
    id_solicitante     BINARY(16) NOT NULL,
    canal              VARCHAR(10) NOT NULL
        CHECK (canal IN ('AGENCIA', 'WEB', 'MOVIL', 'AGENTE', 'CAMPANA')),
    id_agencia         VARCHAR(10),
    producto_interes   VARCHAR(60),
    estado             VARCHAR(15) NOT NULL
        CHECK (estado IN ('INICIADO', 'EN_VALIDACION', 'OBSERVADO', 'APROBADO', 'HABILITADO', 'RECHAZADO', 'REVOCADO')),
    observacion        VARCHAR(255),
    motivo_cierre      VARCHAR(255),
    cod_cliente        VARCHAR(12),
    cliente_nuevo      TINYINT(1),
    fecha_verificacion DATE,
    vigente_hasta      DATE,
    creado_por         VARCHAR(40) NOT NULL,
    fecha_apertura     DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_cierre       DATETIME(6),
    -- Un solo caso abierto por solicitante: la columna vale NULL en un caso cerrado.
    solicitante_abierto BINARY(16) AS (IF(estado IN ('INICIADO', 'EN_VALIDACION', 'OBSERVADO', 'APROBADO'), id_solicitante, NULL)) STORED,
    CONSTRAINT pk_caso_captacion PRIMARY KEY (id_caso),
    CONSTRAINT uk_caso_captacion_1 UNIQUE (solicitante_abierto),
    CONSTRAINT fk_caso_captacion_1 FOREIGN KEY (id_solicitante) REFERENCES clientes.solicitante_captacion (id_solicitante),
    CONSTRAINT fk_caso_captacion_2 FOREIGN KEY (id_agencia) REFERENCES core.agencia (id_agencia),
    CONSTRAINT fk_caso_captacion_3 FOREIGN KEY (cod_cliente) REFERENCES clientes.cliente (cod_cliente),
    CONSTRAINT ck_caso_captacion_1 CHECK (cliente_nuevo IN (0, 1)),
    CONSTRAINT ck_caso_captacion_2 CHECK (estado <> 'HABILITADO' OR (cod_cliente IS NOT NULL AND vigente_hasta > fecha_verificacion))
) ENGINE = InnoDB COMMENT = 'Extensión de integración: el caso de captación de un solicitante y su habilitación.';
CREATE INDEX ix_caso_captacion_1 ON clientes.caso_captacion (estado, fecha_apertura);

CREATE TABLE clientes.consentimiento_captacion (
    id_consentimiento  BIGINT AUTO_INCREMENT,
    id_caso            BINARY(16) NOT NULL,
    tipo               VARCHAR(20) NOT NULL
        CHECK (tipo IN ('TRATAMIENTO_DATOS', 'CONSULTA_BUROS', 'TERMINOS', 'BIOMETRIA')),
    aceptado           TINYINT(1) NOT NULL,
    medio              VARCHAR(12) NOT NULL
        CHECK (medio IN ('DIGITAL', 'FISICO', 'BIOMETRICO')),
    version            VARCHAR(10),
    registrado_por     VARCHAR(40) NOT NULL,
    fecha              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_consentimiento_captacion PRIMARY KEY (id_consentimiento),
    CONSTRAINT fk_consentimiento_captacion_1 FOREIGN KEY (id_caso) REFERENCES clientes.caso_captacion (id_caso),
    CONSTRAINT ck_consentimiento_captacion_1 CHECK (aceptado IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Extensión de integración: consentimientos del solicitante; vale el último de cada tipo.';

CREATE TABLE clientes.otp_captacion (
    id_otp             BINARY(16),
    id_caso            BINARY(16) NOT NULL,
    canal              VARCHAR(5) NOT NULL CHECK (canal IN ('SMS', 'EMAIL')),
    codigo_hmac        CHAR(64) NOT NULL,
    intentos_fallidos  SMALLINT DEFAULT 0 NOT NULL,
    estado             VARCHAR(10) NOT NULL
        CHECK (estado IN ('PENDIENTE', 'USADO', 'EXPIRADO', 'BLOQUEADO')),
    fecha_emision      DATETIME(6) NOT NULL,
    fecha_expiracion   DATETIME(6) NOT NULL,
    CONSTRAINT pk_otp_captacion PRIMARY KEY (id_otp),
    CONSTRAINT fk_otp_captacion_1 FOREIGN KEY (id_caso) REFERENCES clientes.caso_captacion (id_caso),
    CONSTRAINT ck_otp_captacion_1 CHECK (fecha_expiracion > fecha_emision)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: código OTP del solicitante (HMAC calculado por CAPTACION).';

CREATE TABLE clientes.validacion_captacion (
    id_validacion      BIGINT AUTO_INCREMENT,
    id_caso            BINARY(16) NOT NULL,
    tipo               VARCHAR(15) NOT NULL
        CHECK (tipo IN ('RENIEC', 'LISTAS_NEGRAS', 'PEP', 'BIOMETRIA', 'CELULAR', 'CORREO')),
    resultado          VARCHAR(10) NOT NULL CHECK (resultado IN ('APROBADO', 'OBSERVADO', 'RECHAZADO')),
    proveedor          VARCHAR(40) NOT NULL,
    detalle            VARCHAR(200),
    registrado_por     VARCHAR(40) NOT NULL,
    fecha              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_validacion_captacion PRIMARY KEY (id_validacion),
    CONSTRAINT fk_validacion_captacion_1 FOREIGN KEY (id_caso) REFERENCES clientes.caso_captacion (id_caso)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: verificaciones del solicitante; vale la última de cada tipo.';

CREATE TABLE clientes.consulta_riesgo_captacion (
    id_consulta        BIGINT AUTO_INCREMENT,
    id_caso            BINARY(16) NOT NULL,
    central            VARCHAR(10) NOT NULL CHECK (central IN ('SBS', 'INFOCORP', 'SENTINEL', 'EQUIFAX')),
    calificacion       VARCHAR(12) NOT NULL
        CHECK (calificacion IN ('NORMAL', 'CPP', 'DEFICIENTE', 'DUDOSO', 'PERDIDA')),
    deuda_total        DECIMAL(15,2) NOT NULL CHECK (deuda_total >= 0),
    entidades          SMALLINT NOT NULL CHECK (entidades BETWEEN 0 AND 99),
    dias_mora          SMALLINT NOT NULL CHECK (dias_mora BETWEEN 0 AND 9999),
    fuente             VARCHAR(12) NOT NULL CHECK (fuente IN ('SIMULADO', 'MANUAL')),
    registrado_por     VARCHAR(40) NOT NULL,
    fecha              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_consulta_riesgo_captacion PRIMARY KEY (id_consulta),
    CONSTRAINT fk_consulta_riesgo_captacion_1 FOREIGN KEY (id_caso) REFERENCES clientes.caso_captacion (id_caso)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: respuestas de las centrales de riesgo para el solicitante.';

CREATE TABLE clientes.perfil_riesgo_captacion (
    id_perfil          BIGINT AUTO_INCREMENT,
    id_caso            BINARY(16) NOT NULL,
    puntaje            SMALLINT NOT NULL CHECK (puntaje BETWEEN 0 AND 1000),
    calificacion       VARCHAR(10) NOT NULL CHECK (calificacion IN ('BAJO', 'MEDIO', 'ALTO', 'MUY_ALTO')),
    observacion        VARCHAR(200),
    -- La última consulta que conocía el perfil: una consulta posterior lo deja desactualizado.
    id_consulta_base   BIGINT NOT NULL,
    registrado_por     VARCHAR(40) NOT NULL,
    fecha              DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_perfil_riesgo_captacion PRIMARY KEY (id_perfil),
    CONSTRAINT fk_perfil_riesgo_captacion_1 FOREIGN KEY (id_caso) REFERENCES clientes.caso_captacion (id_caso),
    CONSTRAINT fk_perfil_riesgo_captacion_2 FOREIGN KEY (id_consulta_base) REFERENCES clientes.consulta_riesgo_captacion (id_consulta)
) ENGINE = InnoDB COMMENT = 'Extensión de integración: perfil de riesgo del solicitante (0 a 1000), calculado por CAPTACION.';

DELIMITER //

-- La última validación de un tipo (la más reciente reemplaza a las anteriores).
CREATE DEFINER = 'bna_owner'@'%' FUNCTION clientes.fn_validacion_captacion(p_id_caso BINARY(16), p_tipo VARCHAR(15))
    RETURNS VARCHAR(10) READS SQL DATA
    COMMENT 'Resultado de la última validación de ese tipo, o NULL.'
BEGIN
    RETURN (SELECT resultado FROM clientes.validacion_captacion
             WHERE id_caso = p_id_caso AND tipo = p_tipo ORDER BY id_validacion DESC LIMIT 1);
END //

-- Los tipos cuya última validación tiene ese resultado, en orden alfabético.
CREATE DEFINER = 'bna_owner'@'%' FUNCTION clientes.fn_validaciones_captacion(p_id_caso BINARY(16), p_resultado VARCHAR(10))
    RETURNS VARCHAR(100) READS SQL DATA
    COMMENT 'Tipos separados por coma, o NULL.'
BEGIN
    RETURN (SELECT GROUP_CONCAT(v.tipo ORDER BY v.tipo SEPARATOR ', ')
              FROM clientes.validacion_captacion v
             WHERE v.id_caso = p_id_caso AND v.resultado = p_resultado
               AND v.id_validacion = (SELECT MAX(w.id_validacion) FROM clientes.validacion_captacion w
                                       WHERE w.id_caso = v.id_caso AND w.tipo = v.tipo));
END //

CREATE DEFINER = 'bna_owner'@'%' FUNCTION clientes.fn_consentido_captacion(p_id_caso BINARY(16), p_tipo VARCHAR(20))
    RETURNS BOOLEAN READS SQL DATA
    COMMENT 'Si el último consentimiento de ese tipo está aceptado.'
BEGIN
    RETURN coalesce((SELECT aceptado = 1 FROM clientes.consentimiento_captacion
                      WHERE id_caso = p_id_caso AND tipo = p_tipo ORDER BY id_consentimiento DESC LIMIT 1), FALSE);
END //

-- Lo que falta para habilitar un caso abierto; vacío si está listo o cerrado. Los
-- textos son los que muestra la pantalla del asesor.
CREATE DEFINER = 'bna_owner'@'%' FUNCTION clientes.fn_faltantes_captacion(p_id_caso BINARY(16))
    RETURNS JSON READS SQL DATA
    COMMENT 'Arreglo JSON con lo que falta para habilitar el caso.'
BEGIN
    DECLARE v_f JSON DEFAULT JSON_ARRAY();
    DECLARE v_estado VARCHAR(15);
    DECLARE v_observacion VARCHAR(255);
    DECLARE v_lista VARCHAR(100);
    DECLARE v_resultado VARCHAR(10);
    DECLARE v_perfil, v_base BIGINT;
    DECLARE v_calificacion VARCHAR(10);
    SELECT estado, observacion INTO v_estado, v_observacion FROM clientes.caso_captacion WHERE id_caso = p_id_caso;
    IF v_estado IS NULL THEN
        RETURN NULL;
    END IF;
    IF v_estado IN ('HABILITADO', 'RECHAZADO', 'REVOCADO') THEN
        RETURN v_f;
    END IF;
    IF NOT clientes.fn_consentido_captacion(p_id_caso, 'TRATAMIENTO_DATOS') THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Consentimiento TRATAMIENTO_DATOS aceptado');
    END IF;
    IF NOT clientes.fn_consentido_captacion(p_id_caso, 'CONSULTA_BUROS') THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Consentimiento CONSULTA_BUROS aceptado');
    END IF;
    IF NOT clientes.fn_consentido_captacion(p_id_caso, 'TERMINOS') THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Consentimiento TERMINOS aceptado');
    END IF;
    -- Los resultados pasan por una variable: la colación de la base decide la comparación.
    SET v_resultado = clientes.fn_validacion_captacion(p_id_caso, 'CELULAR');
    IF NOT (v_resultado <=> 'APROBADO') THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Verificación OTP del celular');
    END IF;
    SET v_resultado = clientes.fn_validacion_captacion(p_id_caso, 'RENIEC');
    IF NOT (v_resultado <=> 'APROBADO') THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Validación RENIEC aprobada');
    END IF;
    SET v_resultado = clientes.fn_validacion_captacion(p_id_caso, 'LISTAS_NEGRAS');
    IF NOT (v_resultado <=> 'APROBADO') THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Validación LISTAS_NEGRAS aprobada');
    END IF;
    SET v_lista = clientes.fn_validaciones_captacion(p_id_caso, 'RECHAZADO');
    IF v_lista IS NOT NULL THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', CONCAT('Validaciones rechazadas: ', v_lista));
    END IF;
    SET v_lista = clientes.fn_validaciones_captacion(p_id_caso, 'OBSERVADO');
    IF v_lista IS NOT NULL THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', CONCAT('Validaciones observadas: ', v_lista,
                                                     ' (registre una validación manual)'));
    END IF;
    IF v_observacion IS NOT NULL THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', CONCAT('Observación del asesor: ', v_observacion));
    END IF;
    SELECT id_perfil, id_consulta_base, calificacion INTO v_perfil, v_base, v_calificacion
      FROM clientes.perfil_riesgo_captacion WHERE id_caso = p_id_caso ORDER BY id_perfil DESC LIMIT 1;
    IF v_perfil IS NULL THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Perfil de riesgo calculado');
    ELSEIF EXISTS (SELECT 1 FROM clientes.consulta_riesgo_captacion WHERE id_caso = p_id_caso AND id_consulta > v_base) THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Perfil de riesgo actualizado con la última consulta');
    ELSEIF v_calificacion = 'MUY_ALTO' THEN
        SET v_f = JSON_ARRAY_APPEND(v_f, '$', 'Perfil de riesgo MUY_ALTO');
    END IF;
    RETURN v_f;
END //

-- Bloquea el caso y devuelve su estado. Con p_abierto, rechaza un caso cerrado. Lo
-- llaman los procedimientos de esta sección dentro de su savepoint.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.bloquear_caso_captacion(
    IN p_id_caso BINARY(16), IN p_abierto BOOLEAN, OUT p_estado VARCHAR(15))
    COMMENT 'Bloquea el caso de captación y devuelve su estado.'
BEGIN
    SET p_estado = NULL;
    SELECT estado INTO p_estado FROM clientes.caso_captacion WHERE id_caso = p_id_caso FOR UPDATE;
    IF p_estado IS NULL THEN
        CALL core.fallar('BNA-CASO: el caso no existe');
    END IF;
    IF p_abierto AND p_estado IN ('HABILITADO', 'RECHAZADO', 'REVOCADO') THEN
        CALL core.fallar('BNA-CASO-CERRADO: el caso ya no admite cambios');
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.exigir_consentimiento_captacion(
    IN p_id_caso BINARY(16), IN p_tipo VARCHAR(20))
    COMMENT 'Rechaza la operación si el último consentimiento de ese tipo no está aceptado.'
BEGIN
    IF NOT clientes.fn_consentido_captacion(p_id_caso, p_tipo) THEN
        CALL core.fallar(CONCAT('BNA-CONSENTIMIENTO-REQUERIDO: falta el consentimiento ', p_tipo));
    END IF;
END //

-- El estado tras cada paso. Una validación rechazada o un perfil MUY_ALTO cierran el
-- caso como RECHAZADO; una observación (del asesor o de una validación) lo deja
-- OBSERVADO; sin faltantes queda APROBADO. HABILITADO, RECHAZADO y REVOCADO no cambian.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.recalcular_caso_captacion(IN p_id_caso BINARY(16), OUT p_estado VARCHAR(15))
    COMMENT 'Recalcula y guarda el estado del caso de captación.'
BEGIN
    DECLARE v_observacion VARCHAR(255);
    DECLARE v_rechazadas VARCHAR(100);
    DECLARE v_calificacion VARCHAR(10);
    SELECT estado, observacion INTO p_estado, v_observacion FROM clientes.caso_captacion WHERE id_caso = p_id_caso;
    IF p_estado NOT IN ('HABILITADO', 'RECHAZADO', 'REVOCADO') THEN
        SET v_rechazadas = clientes.fn_validaciones_captacion(p_id_caso, 'RECHAZADO');
        SELECT calificacion INTO v_calificacion FROM clientes.perfil_riesgo_captacion
         WHERE id_caso = p_id_caso ORDER BY id_perfil DESC LIMIT 1;
        IF v_rechazadas IS NOT NULL OR v_calificacion <=> 'MUY_ALTO' THEN
            SET p_estado = 'RECHAZADO';
            UPDATE clientes.caso_captacion
               SET estado = p_estado, fecha_cierre = UTC_TIMESTAMP(6),
                   motivo_cierre = IF(v_rechazadas IS NOT NULL, CONCAT('Validación rechazada: ', v_rechazadas),
                                      'Perfil de riesgo MUY_ALTO')
             WHERE id_caso = p_id_caso;
        ELSE
            IF v_observacion IS NOT NULL OR clientes.fn_validaciones_captacion(p_id_caso, 'OBSERVADO') IS NOT NULL THEN
                SET p_estado = 'OBSERVADO';
            ELSEIF JSON_LENGTH(clientes.fn_faltantes_captacion(p_id_caso)) = 0 THEN
                SET p_estado = 'APROBADO';
            ELSEIF EXISTS (SELECT 1 FROM clientes.validacion_captacion WHERE id_caso = p_id_caso)
                OR EXISTS (SELECT 1 FROM clientes.consentimiento_captacion WHERE id_caso = p_id_caso)
                OR EXISTS (SELECT 1 FROM clientes.consulta_riesgo_captacion WHERE id_caso = p_id_caso) THEN
                SET p_estado = 'EN_VALIDACION';
            ELSE
                SET p_estado = 'INICIADO';
            END IF;
            UPDATE clientes.caso_captacion SET estado = p_estado WHERE id_caso = p_id_caso;
        END IF;
    END IF;
END //

-- Un documento repetido devuelve el mismo solicitante (p_duplicado) y no cambia sus datos.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.registrar_solicitante_captacion(
    IN p_id BINARY(16), IN p_tipo_documento VARCHAR(10), IN p_numero_documento VARCHAR(12), IN p_nombres VARCHAR(100),
    IN p_apellido_paterno VARCHAR(100), IN p_apellido_materno VARCHAR(100), IN p_celular CHAR(9), IN p_correo VARCHAR(150),
    IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), OUT p_id_solicitante BINARY(16), OUT p_duplicado BOOLEAN)
    COMMENT 'Registra al prospecto de captación, o devuelve el que ya tiene ese documento.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_min, v_max SMALLINT;
    DECLARE v_alfanumerico BOOLEAN;
    DECLARE v_numero VARCHAR(12) DEFAULT UPPER(TRIM(p_numero_documento));
    DECLARE v_correo VARCHAR(150) DEFAULT LOWER(TRIM(p_correo));
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT longitud_min, longitud_max, es_alfanumerico INTO v_min, v_max, v_alfanumerico
          FROM clientes.tipo_documento WHERE cod_tipo_documento = p_tipo_documento;
        IF v_min IS NULL THEN
            CALL core.fallar('BNA-DOCUMENTO: tipo de documento desconocido');
        END IF;
        IF v_numero IS NULL OR CHAR_LENGTH(v_numero) NOT BETWEEN v_min AND v_max
           OR NOT REGEXP_LIKE(v_numero, IF(v_alfanumerico, '^[A-Z0-9]+$', '^[0-9]+$'), 'c') THEN
            CALL core.fallar('BNA-DOCUMENTO: el número no cumple el formato de su tipo de documento');
        END IF;
        SET p_id_solicitante = NULL, p_duplicado = FALSE;
        SELECT id_solicitante INTO p_id_solicitante FROM clientes.solicitante_captacion
         WHERE tipo_documento = p_tipo_documento AND numero_documento = v_numero FOR UPDATE;
        IF p_id_solicitante IS NOT NULL THEN
            SET p_duplicado = TRUE;
            CALL core.registrar_evento('CLIENTES', 'solicitante_captacion', BIN_TO_UUID(p_id_solicitante),
                                       'REGISTRAR_SOLICITANTE_DUPLICADO', p_actor, p_correlation_id,
                                       JSON_OBJECT('tipo_documento', p_tipo_documento));
            LEAVE proc_cuerpo;
        END IF;
        IF p_id IS NULL THEN
            CALL core.fallar('BNA-SOLICITANTE-DATOS: falta el identificador');
        END IF;
        IF coalesce(TRIM(p_nombres), '') = '' OR coalesce(TRIM(p_apellido_paterno), '') = '' THEN
            CALL core.fallar('BNA-SOLICITANTE-DATOS: faltan los nombres o el apellido paterno');
        END IF;
        IF p_celular IS NULL OR NOT REGEXP_LIKE(p_celular, '^9[0-9]{8}$') THEN
            CALL core.fallar('BNA-SOLICITANTE-DATOS: el celular no es válido');
        END IF;
        IF v_correo IS NULL OR NOT REGEXP_LIKE(v_correo, '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$') THEN
            CALL core.fallar('BNA-SOLICITANTE-DATOS: el correo no es válido');
        END IF;
        INSERT INTO clientes.solicitante_captacion (id_solicitante, tipo_documento, numero_documento, nombres, apellido_paterno,
                                                    apellido_materno, celular, correo, creado_por)
        VALUES (p_id, p_tipo_documento, v_numero, TRIM(p_nombres), TRIM(p_apellido_paterno),
                NULLIF(TRIM(p_apellido_materno), ''), p_celular, v_correo, p_actor);
        SET p_id_solicitante = p_id;
        CALL core.registrar_evento('CLIENTES', 'solicitante_captacion', BIN_TO_UUID(p_id), 'REGISTRAR_SOLICITANTE', p_actor,
                                   p_correlation_id, JSON_OBJECT('tipo_documento', p_tipo_documento));
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.abrir_caso_captacion(
    IN p_id BINARY(16), IN p_id_solicitante BINARY(16), IN p_canal VARCHAR(10), IN p_id_agencia VARCHAR(10),
    IN p_producto_interes VARCHAR(60), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16))
    COMMENT 'Abre el caso de captación de un solicitante.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_existe BINARY(16);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        SELECT id_solicitante INTO v_existe FROM clientes.solicitante_captacion WHERE id_solicitante = p_id_solicitante FOR UPDATE;
        IF v_existe IS NULL THEN
            CALL core.fallar('BNA-SOLICITANTE: el solicitante no existe');
        END IF;
        IF p_id IS NULL THEN
            CALL core.fallar('BNA-CASO-DATOS: falta el identificador');
        END IF;
        IF p_canal IS NULL OR p_canal NOT IN ('AGENCIA', 'WEB', 'MOVIL', 'AGENTE', 'CAMPANA') THEN
            CALL core.fallar('BNA-CASO-DATOS: el canal no es válido');
        END IF;
        IF p_id_agencia IS NOT NULL AND NOT EXISTS (SELECT 1 FROM core.agencia WHERE id_agencia = p_id_agencia) THEN
            CALL core.fallar('BNA-AGENCIA: la agencia no existe');
        END IF;
        IF EXISTS (SELECT 1 FROM clientes.caso_captacion WHERE id_solicitante = p_id_solicitante AND estado IN ('INICIADO', 'EN_VALIDACION', 'OBSERVADO', 'APROBADO')) THEN
            CALL core.fallar('BNA-CASO-ABIERTO: el solicitante ya tiene un caso abierto');
        END IF;
        INSERT INTO clientes.caso_captacion (id_caso, id_solicitante, canal, id_agencia, producto_interes, estado, creado_por)
        VALUES (p_id, p_id_solicitante, p_canal, p_id_agencia, NULLIF(TRIM(p_producto_interes), ''), 'INICIADO', p_actor);
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id), 'ABRIR_CASO', p_actor, p_correlation_id,
                                   JSON_OBJECT('id_solicitante', BIN_TO_UUID(p_id_solicitante), 'canal', p_canal));
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- Vale el último consentimiento de cada tipo; la versión se guarda solo en TERMINOS.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.registrar_consentimientos_captacion(
    IN p_id_caso BINARY(16), IN p_consentimientos JSON, IN p_version_terminos VARCHAR(10), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_estado VARCHAR(15))
    COMMENT 'Registra de uno a cuatro consentimientos del solicitante.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    DECLARE v_malos INT;
    DECLARE v_version VARCHAR(10) DEFAULT NULLIF(TRIM(p_version_terminos), '');
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, TRUE, v_estado);
        IF p_consentimientos IS NULL OR JSON_TYPE(p_consentimientos) <> 'ARRAY' OR JSON_LENGTH(p_consentimientos) NOT BETWEEN 1 AND 4 THEN
            CALL core.fallar('BNA-CONSENTIMIENTO-DATOS: tipo, aceptación o medio no válidos');
        END IF;
        SELECT COUNT(*) INTO v_malos
          FROM JSON_TABLE(p_consentimientos, '$[*]' COLUMNS (tipo VARCHAR(30) PATH '$.tipo', aceptado JSON PATH '$.aceptado',
                                                            medio VARCHAR(20) PATH '$.medio')) j
         WHERE j.tipo IS NULL OR j.tipo NOT IN ('TRATAMIENTO_DATOS', 'CONSULTA_BUROS', 'TERMINOS', 'BIOMETRIA')
            OR j.aceptado IS NULL OR JSON_TYPE(j.aceptado) <> 'BOOLEAN'
            OR j.medio IS NULL OR j.medio NOT IN ('DIGITAL', 'FISICO', 'BIOMETRICO');
        IF v_malos > 0 THEN
            CALL core.fallar('BNA-CONSENTIMIENTO-DATOS: tipo, aceptación o medio no válidos');
        END IF;
        IF v_version IS NULL AND JSON_CONTAINS(JSON_EXTRACT(p_consentimientos, '$[*].tipo'), '"TERMINOS"') THEN
            CALL core.fallar('BNA-CONSENTIMIENTO-DATOS: falta la versión de los términos');
        END IF;
        INSERT INTO clientes.consentimiento_captacion (id_caso, tipo, aceptado, medio, version, registrado_por)
        SELECT p_id_caso, j.tipo, JSON_UNQUOTE(j.aceptado) = 'true', j.medio, IF(j.tipo = 'TERMINOS', v_version, NULL), p_actor
          FROM JSON_TABLE(p_consentimientos, '$[*]' COLUMNS (n FOR ORDINALITY, tipo VARCHAR(30) PATH '$.tipo',
                                                            aceptado JSON PATH '$.aceptado', medio VARCHAR(20) PATH '$.medio')) j
         ORDER BY j.n;
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'REGISTRAR_CONSENTIMIENTOS', p_actor, p_correlation_id,
                                   (SELECT JSON_OBJECTAGG(j.tipo, j.aceptado)
                                      FROM JSON_TABLE(p_consentimientos, '$[*]' COLUMNS (tipo VARCHAR(30) PATH '$.tipo',
                                                      aceptado JSON PATH '$.aceptado')) j));
        CALL clientes.recalcular_caso_captacion(p_id_caso, p_estado);
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- El vencimiento sale de clientes.tipo_contacto (SMS o CORREO).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.emitir_otp_captacion(
    IN p_id_otp BINARY(16), IN p_id_caso BINARY(16), IN p_canal VARCHAR(5), IN p_codigo_hmac CHAR(64),
    IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), OUT p_expira DATETIME(6))
    COMMENT 'Guarda un OTP nuevo del solicitante y vence el pendiente anterior del mismo canal.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    DECLARE v_minutos SMALLINT;
    DECLARE v_ahora DATETIME(6) DEFAULT UTC_TIMESTAMP(6);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, TRUE, v_estado);
        IF p_id_otp IS NULL OR p_canal IS NULL OR p_canal NOT IN ('SMS', 'EMAIL') THEN
            CALL core.fallar('BNA-OTP-DATOS: el canal no es válido');
        END IF;
        IF p_codigo_hmac IS NULL OR NOT REGEXP_LIKE(p_codigo_hmac, '^[0-9a-f]{64}$', 'c') THEN
            CALL core.fallar('BNA-OTP-DATOS: el código no es válido');
        END IF;
        CALL clientes.exigir_consentimiento_captacion(p_id_caso, 'TRATAMIENTO_DATOS');
        SELECT vigencia_minutos INTO v_minutos FROM clientes.tipo_contacto
         WHERE cod_tipo_contacto = IF(p_canal = 'SMS', 'SMS', 'CORREO');
        UPDATE clientes.otp_captacion SET estado = 'EXPIRADO'
         WHERE id_caso = p_id_caso AND canal = p_canal AND estado = 'PENDIENTE';
        SET p_expira = v_ahora + INTERVAL v_minutos MINUTE;
        INSERT INTO clientes.otp_captacion (id_otp, id_caso, canal, codigo_hmac, estado, fecha_emision, fecha_expiracion)
        VALUES (p_id_otp, p_id_caso, p_canal, p_codigo_hmac, 'PENDIENTE', v_ahora, p_expira);
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'ENVIAR_OTP', p_actor, p_correlation_id,
                                   JSON_OBJECT('canal', p_canal, 'id_otp', BIN_TO_UUID(p_id_otp)));
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- El código errado suma un intento y el último (max_intentos de clientes.tipo_contacto)
-- lo bloquea; vencido, queda EXPIRADO. Esos dos casos no son errores: se confirman y el
-- llamador recibe el estado del código. El correcto registra la verificación del canal.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.verificar_otp_captacion(
    IN p_id_otp BINARY(16), IN p_id_caso BINARY(16), IN p_codigo_hmac CHAR(64), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_estado_codigo VARCHAR(10), OUT p_intentos_restantes SMALLINT,
    OUT p_estado VARCHAR(15))
    COMMENT 'Compara el hash del código con el OTP pendiente y cuenta los intentos.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    DECLARE v_canal VARCHAR(5);
    DECLARE v_hmac CHAR(64);
    DECLARE v_intentos, v_max SMALLINT;
    DECLARE v_expira DATETIME(6);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, TRUE, v_estado);
        SET p_estado = v_estado, p_estado_codigo = NULL;
        SELECT canal, codigo_hmac, intentos_fallidos, estado, fecha_expiracion
          INTO v_canal, v_hmac, v_intentos, p_estado_codigo, v_expira
          FROM clientes.otp_captacion WHERE id_otp = p_id_otp AND id_caso = p_id_caso FOR UPDATE;
        IF NOT (p_estado_codigo <=> 'PENDIENTE') THEN
            CALL core.fallar('BNA-OTP: no hay un código pendiente');
        END IF;
        SELECT max_intentos INTO v_max FROM clientes.tipo_contacto
         WHERE cod_tipo_contacto = IF(v_canal = 'SMS', 'SMS', 'CORREO');
        IF UTC_TIMESTAMP(6) > v_expira THEN
            SET p_estado_codigo = 'EXPIRADO', p_intentos_restantes = 0;
            UPDATE clientes.otp_captacion SET estado = p_estado_codigo WHERE id_otp = p_id_otp;
            CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'VERIFICAR_OTP', p_actor, p_correlation_id,
                                   JSON_OBJECT('canal', v_canal, 'resultado', 'EXPIRADO'));
        ELSEIF p_codigo_hmac <=> v_hmac THEN
            SET p_estado_codigo = 'USADO', p_intentos_restantes = v_max - v_intentos;
            UPDATE clientes.otp_captacion SET estado = p_estado_codigo WHERE id_otp = p_id_otp;
            INSERT INTO clientes.validacion_captacion (id_caso, tipo, resultado, proveedor, detalle, registrado_por)
            VALUES (p_id_caso, IF(v_canal = 'SMS', 'CELULAR', 'CORREO'), 'APROBADO', CONCAT('OTP-', v_canal),
                    'Código verificado', p_actor);
            CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'VERIFICAR_OTP', p_actor, p_correlation_id,
                                   JSON_OBJECT('canal', v_canal, 'resultado', 'OK'));
            CALL clientes.recalcular_caso_captacion(p_id_caso, p_estado);
        ELSE
            SET v_intentos = v_intentos + 1;
            SET p_estado_codigo = IF(v_intentos >= v_max, 'BLOQUEADO', 'PENDIENTE'),
                p_intentos_restantes = GREATEST(v_max - v_intentos, 0);
            UPDATE clientes.otp_captacion SET intentos_fallidos = v_intentos, estado = p_estado_codigo WHERE id_otp = p_id_otp;
            CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'VERIFICAR_OTP', p_actor, p_correlation_id,
                                   JSON_OBJECT('canal', v_canal, 'resultado', 'FALLIDO', 'intentos', v_intentos));
        END IF;
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- RENIEC, listas restrictivas, PEP o biometría, del proveedor o de una revisión manual
-- (proveedor MANUAL), que reemplaza al resultado anterior del mismo tipo. El celular y
-- el correo se verifican solo con verificar_otp_captacion.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.registrar_validacion_captacion(
    IN p_id_caso BINARY(16), IN p_tipo VARCHAR(15), IN p_resultado VARCHAR(10), IN p_proveedor VARCHAR(40),
    IN p_detalle VARCHAR(200), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), OUT p_estado VARCHAR(15))
    COMMENT 'Registra una verificación de identidad del solicitante.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, TRUE, v_estado);
        IF p_tipo IS NULL OR p_tipo NOT IN ('RENIEC', 'LISTAS_NEGRAS', 'PEP', 'BIOMETRIA')
           OR p_resultado IS NULL OR p_resultado NOT IN ('APROBADO', 'OBSERVADO', 'RECHAZADO') THEN
            CALL core.fallar('BNA-VALIDACION-CAPTACION: tipo o resultado no válidos');
        END IF;
        IF coalesce(TRIM(p_proveedor), '') = '' THEN
            CALL core.fallar('BNA-VALIDACION-CAPTACION: falta el proveedor');
        END IF;
        CALL clientes.exigir_consentimiento_captacion(p_id_caso, 'TRATAMIENTO_DATOS');
        IF p_tipo = 'BIOMETRIA' THEN
            CALL clientes.exigir_consentimiento_captacion(p_id_caso, 'BIOMETRIA');
        END IF;
        INSERT INTO clientes.validacion_captacion (id_caso, tipo, resultado, proveedor, detalle, registrado_por)
        VALUES (p_id_caso, p_tipo, p_resultado, TRIM(p_proveedor), NULLIF(TRIM(p_detalle), ''), p_actor);
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'REGISTRAR_VALIDACION', p_actor, p_correlation_id,
                                   JSON_OBJECT('tipo', p_tipo, 'resultado', p_resultado, 'proveedor', TRIM(p_proveedor)));
        CALL clientes.recalcular_caso_captacion(p_id_caso, p_estado);
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.registrar_consulta_riesgo_captacion(
    IN p_id_caso BINARY(16), IN p_central VARCHAR(10), IN p_calificacion VARCHAR(12), IN p_deuda_total DECIMAL(15,2),
    IN p_entidades SMALLINT, IN p_dias_mora SMALLINT, IN p_fuente VARCHAR(12), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_estado VARCHAR(15))
    COMMENT 'Registra la respuesta de una central de riesgo para el solicitante.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, TRUE, v_estado);
        IF p_central IS NULL OR p_central NOT IN ('SBS', 'INFOCORP', 'SENTINEL', 'EQUIFAX')
           OR p_calificacion IS NULL OR p_calificacion NOT IN ('NORMAL', 'CPP', 'DEFICIENTE', 'DUDOSO', 'PERDIDA')
           OR p_fuente IS NULL OR p_fuente NOT IN ('SIMULADO', 'MANUAL')
           OR NOT (p_deuda_total >= 0) OR NOT (p_entidades BETWEEN 0 AND 99) OR NOT (p_dias_mora BETWEEN 0 AND 9999)
           OR p_deuda_total IS NULL OR p_entidades IS NULL OR p_dias_mora IS NULL THEN
            CALL core.fallar('BNA-RIESGO-DATOS: central, calificación o montos no válidos');
        END IF;
        CALL clientes.exigir_consentimiento_captacion(p_id_caso, 'CONSULTA_BUROS');
        INSERT INTO clientes.consulta_riesgo_captacion (id_caso, central, calificacion, deuda_total, entidades, dias_mora, fuente,
                                                        registrado_por)
        VALUES (p_id_caso, p_central, p_calificacion, p_deuda_total, p_entidades, p_dias_mora, p_fuente, p_actor);
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'CONSULTAR_CENTRAL', p_actor, p_correlation_id,
                                   JSON_OBJECT('central', p_central, 'calificacion', p_calificacion, 'fuente', p_fuente));
        CALL clientes.recalcular_caso_captacion(p_id_caso, p_estado);
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- Un perfil MUY_ALTO rechaza el caso.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.registrar_perfil_captacion(
    IN p_id_caso BINARY(16), IN p_puntaje SMALLINT, IN p_calificacion VARCHAR(10), IN p_observacion VARCHAR(200),
    IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), OUT p_estado VARCHAR(15))
    COMMENT 'Registra el perfil de riesgo del solicitante calculado por CAPTACION.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    DECLARE v_base BIGINT;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, TRUE, v_estado);
        IF p_puntaje IS NULL OR p_puntaje NOT BETWEEN 0 AND 1000
           OR p_calificacion IS NULL OR p_calificacion NOT IN ('BAJO', 'MEDIO', 'ALTO', 'MUY_ALTO') THEN
            CALL core.fallar('BNA-RIESGO-DATOS: puntaje o calificación no válidos');
        END IF;
        SELECT MAX(id_consulta) INTO v_base FROM clientes.consulta_riesgo_captacion WHERE id_caso = p_id_caso;
        IF v_base IS NULL THEN
            CALL core.fallar('BNA-SIN-CONSULTA: consulte al menos una central de riesgo');
        END IF;
        INSERT INTO clientes.perfil_riesgo_captacion (id_caso, puntaje, calificacion, observacion, id_consulta_base, registrado_por)
        VALUES (p_id_caso, p_puntaje, p_calificacion, NULLIF(TRIM(p_observacion), ''), v_base, p_actor);
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'CALCULAR_PERFIL', p_actor, p_correlation_id,
                                   JSON_OBJECT('puntaje', p_puntaje, 'calificacion', p_calificacion));
        CALL clientes.recalcular_caso_captacion(p_id_caso, p_estado);
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- Revocar retira una habilitación vigente; lo demás exige un caso abierto. La
-- observación del asesor detiene el caso hasta que se levante.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.cambiar_estado_caso_captacion(
    IN p_id_caso BINARY(16), IN p_accion VARCHAR(25), IN p_motivo VARCHAR(255), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_estado VARCHAR(15))
    COMMENT 'Observa, levanta la observación, rechaza o revoca un caso de captación.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    DECLARE v_motivo VARCHAR(255) DEFAULT TRIM(p_motivo);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_accion IS NULL OR p_accion NOT IN ('OBSERVAR', 'LEVANTAR_OBSERVACION', 'RECHAZAR', 'REVOCAR') THEN
            CALL core.fallar('BNA-CASO-DATOS: la acción no es válida');
        END IF;
        IF CHAR_LENGTH(coalesce(v_motivo, '')) < 3 THEN
            CALL core.fallar('BNA-CASO-DATOS: falta el motivo');
        END IF;
        CALL clientes.bloquear_caso_captacion(p_id_caso, p_accion <> 'REVOCAR', v_estado);
        IF p_accion = 'REVOCAR' THEN
            IF v_estado <> 'HABILITADO' THEN
                CALL core.fallar('BNA-CASO-ESTADO: solo se revoca un caso HABILITADO');
            END IF;
            UPDATE clientes.caso_captacion SET estado = 'REVOCADO', motivo_cierre = v_motivo WHERE id_caso = p_id_caso;
        ELSEIF p_accion = 'OBSERVAR' THEN
            UPDATE clientes.caso_captacion SET observacion = v_motivo WHERE id_caso = p_id_caso;
        ELSEIF p_accion = 'LEVANTAR_OBSERVACION' THEN
            UPDATE clientes.caso_captacion SET observacion = NULL WHERE id_caso = p_id_caso;
        ELSE
            UPDATE clientes.caso_captacion SET estado = 'RECHAZADO', motivo_cierre = v_motivo, fecha_cierre = UTC_TIMESTAMP(6)
             WHERE id_caso = p_id_caso;
        END IF;
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), p_accion, p_actor, p_correlation_id,
                                   JSON_OBJECT('motivo', v_motivo));
        CALL clientes.recalcular_caso_captacion(p_id_caso, p_estado);
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- El cliente lo registra (o lo encuentra) quien verificó la identidad, por
-- clientes.registrar_cliente o verificar_documento; aquí solo se liga. Ligarlo de nuevo
-- al mismo cliente no hace nada, así un reintento no falla.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.vincular_cliente_captacion(
    IN p_id_caso BINARY(16), IN p_cod_cliente VARCHAR(12), IN p_cliente_nuevo BOOLEAN, IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16))
    COMMENT 'Liga al caso APROBADO el cliente ACTIVO que tiene el documento del solicitante.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    DECLARE v_actual VARCHAR(12);
    DECLARE v_solicitante BINARY(16);
    DECLARE v_tipo_sol, v_tipo_cli VARCHAR(10);
    DECLARE v_num_sol, v_num_cli VARCHAR(12);
    DECLARE v_estado_cli VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, TRUE, v_estado);
        SELECT c.cod_cliente, c.id_solicitante, s.tipo_documento, s.numero_documento
          INTO v_actual, v_solicitante, v_tipo_sol, v_num_sol
          FROM clientes.caso_captacion c
          JOIN clientes.solicitante_captacion s ON s.id_solicitante = c.id_solicitante
         WHERE c.id_caso = p_id_caso;
        IF v_actual IS NOT NULL THEN
            IF v_actual <=> p_cod_cliente THEN
                LEAVE proc_cuerpo;
            END IF;
            CALL core.fallar('BNA-CASO-CLIENTE: el caso ya tiene otro cliente');
        END IF;
        IF v_estado <> 'APROBADO' OR JSON_LENGTH(clientes.fn_faltantes_captacion(p_id_caso)) > 0 THEN
            CALL core.fallar('BNA-CASO-NO-LISTO: el caso no cumple los requisitos para habilitarse');
        END IF;
        IF p_cliente_nuevo IS NULL THEN
            CALL core.fallar('BNA-CASO-DATOS: falta indicar si el cliente es nuevo');
        END IF;
        SELECT tipo_documento, numero_documento, estado_cliente INTO v_tipo_cli, v_num_cli, v_estado_cli
          FROM clientes.cliente WHERE cod_cliente = p_cod_cliente FOR SHARE;
        IF v_tipo_cli IS NULL THEN
            CALL core.fallar('BNA-CLIENTE: el cliente no existe');
        END IF;
        IF NOT (v_tipo_cli <=> v_tipo_sol AND v_num_cli <=> v_num_sol) THEN
            CALL core.fallar('BNA-CLIENTE-DOCUMENTO: el cliente no tiene el documento del solicitante');
        END IF;
        IF v_estado_cli <> 'ACTIVO' THEN
            CALL core.fallar('BNA-CLIENTE-NO-ACTIVO: el cliente no está ACTIVO');
        END IF;
        UPDATE clientes.caso_captacion SET cod_cliente = p_cod_cliente, cliente_nuevo = p_cliente_nuevo WHERE id_caso = p_id_caso;
        UPDATE clientes.solicitante_captacion SET cod_cliente = p_cod_cliente WHERE id_solicitante = v_solicitante;
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'VINCULAR_CLIENTE', p_actor, p_correlation_id,
                                   JSON_OBJECT('cod_cliente', p_cod_cliente, 'cliente_nuevo', p_cliente_nuevo IS TRUE));
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

-- La referencia queda vigente p_vigencia_dias desde la fecha de negocio de hoy (Lima).
-- Habilitar un caso ya HABILITADO no cambia nada.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE clientes.habilitar_caso_captacion(
    IN p_id_caso BINARY(16), IN p_vigencia_dias SMALLINT, IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_estado VARCHAR(15))
    COMMENT 'Habilita el caso con su cliente y deja en el cliente las verificaciones de contacto.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado VARCHAR(15);
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_estado_cli VARCHAR(25);
    DECLARE v_fecha DATE;
    DECLARE v_tipo VARCHAR(15);
    DECLARE v_resultado VARCHAR(10);
    DECLARE v_id BIGINT;
    DECLARE v_i TINYINT DEFAULT 1;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    proc_cuerpo: BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        CALL clientes.bloquear_caso_captacion(p_id_caso, FALSE, v_estado);
        SET p_estado = v_estado;
        IF v_estado = 'HABILITADO' THEN
            LEAVE proc_cuerpo;
        END IF;
        IF v_estado IN ('HABILITADO', 'RECHAZADO', 'REVOCADO') THEN
            CALL core.fallar('BNA-CASO-CERRADO: el caso ya no admite cambios');
        END IF;
        IF p_vigencia_dias IS NULL OR p_vigencia_dias NOT BETWEEN 1 AND 365 THEN
            CALL core.fallar('BNA-CASO-DATOS: la vigencia va de 1 a 365 días');
        END IF;
        IF p_correlation_id IS NULL THEN
            CALL core.fallar('BNA-CASO-DATOS: falta el correlation_id');
        END IF;
        IF v_estado <> 'APROBADO' OR JSON_LENGTH(clientes.fn_faltantes_captacion(p_id_caso)) > 0 THEN
            CALL core.fallar('BNA-CASO-NO-LISTO: el caso no cumple los requisitos para habilitarse');
        END IF;
        SELECT cod_cliente INTO v_cliente FROM clientes.caso_captacion WHERE id_caso = p_id_caso;
        IF v_cliente IS NULL THEN
            CALL core.fallar('BNA-CASO-NO-LISTO: el caso no tiene un cliente ligado');
        END IF;
        SELECT estado_cliente INTO v_estado_cli FROM clientes.cliente WHERE cod_cliente = v_cliente FOR SHARE;
        IF v_estado_cli <> 'ACTIVO' THEN
            CALL core.fallar('BNA-CLIENTE-NO-ACTIVO: el cliente no está ACTIVO');
        END IF;
        -- Las verificaciones de contacto aprobadas por OTP quedan también en el cliente, como
        -- las registraría clientes.registrar_validacion (aquí, sin anidar su savepoint).
        WHILE v_i <= 2 DO
            SET v_tipo = ELT(v_i, 'CELULAR', 'CORREO'), v_i = v_i + 1;
            SET v_resultado = clientes.fn_validacion_captacion(p_id_caso, v_tipo);
            IF v_resultado <=> 'APROBADO' THEN
                INSERT INTO clientes.validacion_identidad (tipo_validacion, resultado, correlation_id, cod_cliente)
                VALUES (v_tipo, 'APROBADO', p_correlation_id, v_cliente);
                SET v_id = LAST_INSERT_ID();
                CALL core.registrar_evento('CLIENTES', 'validacion_identidad', v_id, 'REGISTRAR_VALIDACION', p_actor,
                                           p_correlation_id,
                                           JSON_OBJECT('cod_cliente', v_cliente, 'tipo_validacion', v_tipo, 'resultado', 'APROBADO',
                                                       'motivo', CONCAT('OTP CAPTACION ', LEFT(BIN_TO_UUID(p_id_caso), 8))));
            END IF;
        END WHILE;
        SET v_fecha = core.fn_fecha_negocio(UTC_TIMESTAMP(6)), p_estado = 'HABILITADO';
        UPDATE clientes.caso_captacion
           SET estado = p_estado, fecha_verificacion = v_fecha, vigente_hasta = v_fecha + INTERVAL p_vigencia_dias DAY,
               fecha_cierre = UTC_TIMESTAMP(6)
         WHERE id_caso = p_id_caso;
        CALL core.registrar_evento('CLIENTES', 'caso_captacion', BIN_TO_UUID(p_id_caso), 'HABILITAR', p_actor, p_correlation_id,
                                   JSON_OBJECT('cod_cliente', v_cliente, 'vigente_hasta', DATE_FORMAT(v_fecha + INTERVAL p_vigencia_dias DAY, '%Y-%m-%d')));
    END;
    IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
END //

DELIMITER ;

-- Lecturas de la API. Sin el hash del OTP; el caso trae del cliente su verificación de
-- captación y su estado vigente, y lo que falta para habilitarlo.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW clientes.v_solicitante_captacion_api AS
SELECT BIN_TO_UUID(s.id_solicitante) AS id_solicitante, s.tipo_documento, s.numero_documento, s.nombres,
       s.apellido_paterno, s.apellido_materno, s.celular, s.correo, s.cod_cliente, s.creado_por, s.fecha_registro
  FROM clientes.solicitante_captacion s;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW clientes.v_caso_captacion_api AS
SELECT BIN_TO_UUID(c.id_caso) AS id_caso, BIN_TO_UUID(c.id_solicitante) AS id_solicitante, c.canal, c.id_agencia,
       c.producto_interes, c.estado, c.observacion, c.motivo_cierre, c.cod_cliente, c.cliente_nuevo,
       cl.id_verificacion_captacion, cl.estado_cliente, c.fecha_verificacion, c.vigente_hasta, c.creado_por,
       c.fecha_apertura, c.fecha_cierre, clientes.fn_faltantes_captacion(c.id_caso) AS faltantes
  FROM clientes.caso_captacion c
  LEFT JOIN clientes.cliente cl ON cl.cod_cliente = c.cod_cliente;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW clientes.v_consentimiento_captacion_api AS
SELECT id_consentimiento, BIN_TO_UUID(id_caso) AS id_caso, tipo, aceptado, medio, version, registrado_por, fecha
  FROM clientes.consentimiento_captacion;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW clientes.v_otp_captacion_api AS
SELECT BIN_TO_UUID(id_otp) AS id_otp, BIN_TO_UUID(id_caso) AS id_caso, canal, estado, intentos_fallidos,
       fecha_emision, fecha_expiracion
  FROM clientes.otp_captacion;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW clientes.v_validacion_captacion_api AS
SELECT id_validacion, BIN_TO_UUID(id_caso) AS id_caso, tipo, resultado, proveedor, detalle, registrado_por, fecha
  FROM clientes.validacion_captacion;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW clientes.v_consulta_riesgo_captacion_api AS
SELECT id_consulta, BIN_TO_UUID(id_caso) AS id_caso, central, calificacion, deuda_total, entidades, dias_mora, fuente,
       registrado_por, fecha
  FROM clientes.consulta_riesgo_captacion;

-- vigente: ninguna consulta posterior al perfil.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW clientes.v_perfil_riesgo_captacion_api AS
SELECT p.id_perfil, BIN_TO_UUID(p.id_caso) AS id_caso, p.puntaje, p.calificacion, p.observacion, p.registrado_por,
       p.fecha,
       NOT EXISTS (SELECT 1 FROM clientes.consulta_riesgo_captacion q
                    WHERE q.id_caso = p.id_caso AND q.id_consulta > p.id_consulta_base) AS vigente
  FROM clientes.perfil_riesgo_captacion p;

GRANT EXECUTE ON PROCEDURE clientes.registrar_solicitante_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.abrir_caso_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.registrar_consentimientos_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.emitir_otp_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.verificar_otp_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.registrar_validacion_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.registrar_consulta_riesgo_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.registrar_perfil_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.cambiar_estado_caso_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.vincular_cliente_captacion TO bna_api;
GRANT EXECUTE ON PROCEDURE clientes.habilitar_caso_captacion TO bna_api;
GRANT SELECT ON clientes.v_solicitante_captacion_api TO bna_api;
GRANT SELECT ON clientes.v_caso_captacion_api TO bna_api;
GRANT SELECT ON clientes.v_consentimiento_captacion_api TO bna_api;
GRANT SELECT ON clientes.v_otp_captacion_api TO bna_api;
GRANT SELECT ON clientes.v_validacion_captacion_api TO bna_api;
GRANT SELECT ON clientes.v_consulta_riesgo_captacion_api TO bna_api;
GRANT SELECT ON clientes.v_perfil_riesgo_captacion_api TO bna_api;

-- ---------------------------------------------------------------------
-- 15. Billetera Digital (v1.9)
-- ---------------------------------------------------------------------
-- La Billetera Digital «Chaski» (canal BD) sobre las cuentas del núcleo: no tiene
-- saldo propio. Su cuenta es una cuenta de ahorro en soles del cliente, y cada envío,
-- pago con QR o cobro aceptado es una cuenta.registrar_transferencia con canal BD, su
-- asiento y el tope diario del canal (core.limite_canal, RN-BD-002).
-- DECISIÓN (v1.9): el esquema billetera guarda solo lo propio de la billetera: la
--   afiliación (PIN de 6 dígitos y cuenta), comercios, códigos QR, solicitudes de
--   cobro, operaciones y notificaciones. Tienda, promociones, cupones, recargas y pago
--   de servicios quedan fuera hasta que el equipo los defina.
-- DECISIÓN (v1.9): la billetera no crea clientes (punto R-01). Se afilia un cliente
--   ACTIVO que ya existe, con una cuenta individual en soles de la que es titular. El
--   celular del cliente es el de clientes.cliente, que registró el módulo Clientes.
-- DECISIÓN (v1.9): el PIN se guarda como SHA2(CONCAT(sal, pin), 256) con sal aleatoria,
--   como las credenciales de tarjeta (v1.5); bna_api no lee la tabla. Al tercer intento
--   fallido la afiliación queda BLOQUEADA; una nueva afiliación (cambio de PIN) la
--   reactiva.
-- DECISIÓN (v1.9): ni la bitácora, ni las notificaciones, ni la glosa de los
--   movimientos, ni los mensajes de error guardan el celular ni el PIN. Identifican al
--   cliente por su código y muestran su nombre corto («Ana D.»).
-- DECISIÓN (v1.9): cada operación de dinero exige una llave de idempotencia y la
--   reserva antes de bloquear nada, en su misma transacción: una petición repetida
--   espera a la primera y devuelve la misma operación. Después llama a
--   cuentas.registrar_transferencia sin llave. Los procedimientos usan el savepoint
--   bna_billetera, distinto del bna_op de registrar_transferencia, para que este no
--   reemplace al suyo cuando se los llama dentro de una transacción.
-- DECISIÓN (v1.9): una solicitud de cobro vence a las 48 horas (Chaski, CUS-BD-002
--   FA-02); las vistas la muestran VENCIDA sin que nadie la actualice.
CREATE DATABASE IF NOT EXISTS billetera CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
GRANT ALL PRIVILEGES ON billetera.* TO 'bna_owner'@'%';
-- v1.10: como sobre los demás esquemas (bna_core.sql).
GRANT ALL PRIVILEGES ON billetera.* TO bna_admin;

-- El modelo deja libre el id 10 entre SEGURIDAD y SOLICITUD DE CREDITO.
INSERT INTO core.modulo (id_modulo, nombre) VALUES (10, 'BILLETERA') AS nueva
ON DUPLICATE KEY UPDATE nombre = nueva.nombre;

CREATE TABLE billetera.afiliacion (
    cod_cliente                 VARCHAR(12),
    num_cuenta                  VARCHAR(20) NOT NULL,
    hash_pin                    CHAR(64) NOT NULL,
    sal                         CHAR(32) NOT NULL,
    intentos_fallidos           SMALLINT DEFAULT 0 NOT NULL,
    estado                      VARCHAR(15) DEFAULT 'ACTIVA' NOT NULL,
    fecha_afiliacion            DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_ultimo_cambio         DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_afiliacion PRIMARY KEY (cod_cliente),
    CONSTRAINT uk_afiliacion_cuenta UNIQUE (num_cuenta),
    CONSTRAINT fk_afiliacion_cliente FOREIGN KEY (cod_cliente) REFERENCES clientes.cliente (cod_cliente),
    CONSTRAINT fk_afiliacion_cuenta FOREIGN KEY (num_cuenta) REFERENCES cuentas.cuenta_ahorro (num_cuenta),
    CONSTRAINT ck_afiliacion_intentos CHECK (intentos_fallidos BETWEEN 0 AND 3),
    CONSTRAINT ck_afiliacion_estado CHECK (estado IN ('ACTIVA', 'BLOQUEADA'))
) ENGINE = InnoDB COMMENT = 'Extensión v1.9: cliente afiliado a la Billetera Digital, su PIN y su cuenta.';

CREATE TABLE billetera.comercio (
    id_comercio                 BINARY(16),
    ruc                         CHAR(11) NOT NULL,
    razon_social                VARCHAR(150) NOT NULL,
    num_cuenta                  VARCHAR(20) NOT NULL,
    estado                      VARCHAR(15) DEFAULT 'ACTIVO' NOT NULL,
    fecha_afiliacion            DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_comercio PRIMARY KEY (id_comercio),
    CONSTRAINT uk_comercio_ruc UNIQUE (ruc),
    CONSTRAINT fk_comercio_cuenta FOREIGN KEY (num_cuenta) REFERENCES cuentas.cuenta_ahorro (num_cuenta),
    CONSTRAINT ck_comercio_ruc CHECK (REGEXP_LIKE(ruc, '^(10|15|17|20)[0-9]{9}$')),
    CONSTRAINT ck_comercio_estado CHECK (estado IN ('ACTIVO', 'INACTIVO'))
) ENGINE = InnoDB COMMENT = 'Extensión v1.9: comercio afiliado que cobra con QR en su cuenta.';

CREATE TABLE billetera.codigo_qr (
    id_qr                       BINARY(16),
    tipo                        VARCHAR(10) NOT NULL,
    num_cuenta                  VARCHAR(20) NOT NULL,
    cod_cliente                 VARCHAR(12),
    id_comercio                 BINARY(16),
    monto                       DECIMAL(15,2),
    estado                      VARCHAR(10) DEFAULT 'ACTIVO' NOT NULL,
    fecha_generacion            DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_expiracion            DATETIME(6),
    CONSTRAINT pk_codigo_qr PRIMARY KEY (id_qr),
    CONSTRAINT fk_codigo_qr_cuenta FOREIGN KEY (num_cuenta) REFERENCES cuentas.cuenta_ahorro (num_cuenta),
    CONSTRAINT fk_codigo_qr_cliente FOREIGN KEY (cod_cliente) REFERENCES billetera.afiliacion (cod_cliente),
    CONSTRAINT fk_codigo_qr_comercio FOREIGN KEY (id_comercio) REFERENCES billetera.comercio (id_comercio),
    CONSTRAINT ck_codigo_qr_tipo CHECK (tipo IN ('ESTATICO', 'DINAMICO')),
    CONSTRAINT ck_codigo_qr_estado CHECK (estado IN ('ACTIVO', 'PAGADO', 'ANULADO')),
    CONSTRAINT ck_codigo_qr_dueno CHECK ((cod_cliente IS NULL) <> (id_comercio IS NULL)),
    CONSTRAINT ck_codigo_qr_monto CHECK ((tipo = 'ESTATICO' AND monto IS NULL AND fecha_expiracion IS NULL)
                                      OR (tipo = 'DINAMICO' AND monto > 0 AND fecha_expiracion IS NOT NULL))
) ENGINE = InnoDB COMMENT = 'Extensión v1.9: QR estático (monto libre) o dinámico (monto fijo, un solo pago, vence).';

CREATE TABLE billetera.solicitud_cobro (
    id_solicitud                BINARY(16),
    cod_solicitante             VARCHAR(12) NOT NULL,
    cod_pagador                 VARCHAR(12) NOT NULL,
    monto                       DECIMAL(15,2) NOT NULL,
    concepto                    VARCHAR(100),
    estado                      VARCHAR(15) DEFAULT 'PENDIENTE' NOT NULL,
    fecha_solicitud             DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    fecha_vencimiento           DATETIME(6) NOT NULL,
    fecha_respuesta             DATETIME(6),
    CONSTRAINT pk_solicitud_cobro PRIMARY KEY (id_solicitud),
    CONSTRAINT fk_solicitud_cobro_solicitante FOREIGN KEY (cod_solicitante) REFERENCES billetera.afiliacion (cod_cliente),
    CONSTRAINT fk_solicitud_cobro_pagador FOREIGN KEY (cod_pagador) REFERENCES billetera.afiliacion (cod_cliente),
    CONSTRAINT ck_solicitud_cobro_monto CHECK (monto > 0),
    CONSTRAINT ck_solicitud_cobro_partes CHECK (cod_solicitante <> cod_pagador),
    CONSTRAINT ck_solicitud_cobro_estado CHECK (estado IN ('PENDIENTE', 'PAGADA', 'RECHAZADA', 'CANCELADA'))
) ENGINE = InnoDB COMMENT = 'Extensión v1.9: un cliente pide dinero a otro; si la acepta, se transfiere.';

CREATE TABLE billetera.operacion (
    id_operacion                BINARY(16),
    tipo                        VARCHAR(10) NOT NULL,
    cod_cliente_origen          VARCHAR(12) NOT NULL,
    cod_cliente_destino         VARCHAR(12),
    id_comercio                 BINARY(16),
    num_cuenta_origen           VARCHAR(20) NOT NULL,
    num_cuenta_destino          VARCHAR(20) NOT NULL,
    monto                       DECIMAL(15,2) NOT NULL,
    referencia                  VARCHAR(100),
    id_qr                       BINARY(16),
    id_solicitud                BINARY(16),
    uuid_debito                 BINARY(16) NOT NULL,
    uuid_abono                  BINARY(16) NOT NULL,
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_operacion PRIMARY KEY (id_operacion),
    CONSTRAINT uk_operacion_debito UNIQUE (uuid_debito),
    CONSTRAINT uk_operacion_abono UNIQUE (uuid_abono),
    CONSTRAINT uk_operacion_solicitud UNIQUE (id_solicitud),
    CONSTRAINT fk_operacion_origen FOREIGN KEY (cod_cliente_origen) REFERENCES billetera.afiliacion (cod_cliente),
    CONSTRAINT fk_operacion_destino FOREIGN KEY (cod_cliente_destino) REFERENCES billetera.afiliacion (cod_cliente),
    CONSTRAINT fk_operacion_comercio FOREIGN KEY (id_comercio) REFERENCES billetera.comercio (id_comercio),
    CONSTRAINT fk_operacion_qr FOREIGN KEY (id_qr) REFERENCES billetera.codigo_qr (id_qr),
    CONSTRAINT fk_operacion_solicitud FOREIGN KEY (id_solicitud) REFERENCES billetera.solicitud_cobro (id_solicitud),
    CONSTRAINT fk_operacion_debito FOREIGN KEY (uuid_debito) REFERENCES cuentas.movimiento (uuid_transaccion),
    CONSTRAINT fk_operacion_abono FOREIGN KEY (uuid_abono) REFERENCES cuentas.movimiento (uuid_transaccion),
    CONSTRAINT ck_operacion_tipo CHECK (tipo IN ('P2P', 'QR', 'SOLICITUD')),
    CONSTRAINT ck_operacion_monto CHECK (monto > 0),
    CONSTRAINT ck_operacion_qr CHECK ((tipo = 'QR') = (id_qr IS NOT NULL)),
    CONSTRAINT ck_operacion_solicitud CHECK ((tipo = 'SOLICITUD') = (id_solicitud IS NOT NULL)),
    CONSTRAINT ck_operacion_destino CHECK ((cod_cliente_destino IS NULL) <> (id_comercio IS NULL))
) ENGINE = InnoDB COMMENT = 'Extensión v1.9: cada envío, pago con QR o cobro pagado, con sus dos movimientos.';

CREATE TABLE billetera.notificacion (
    id_notificacion             BIGINT AUTO_INCREMENT,
    cod_cliente                 VARCHAR(12) NOT NULL,
    tipo                        VARCHAR(30) NOT NULL,
    mensaje                     VARCHAR(200) NOT NULL,
    leida                       TINYINT(1) DEFAULT 0 NOT NULL,
    id_operacion                BINARY(16),
    id_solicitud                BINARY(16),
    fecha_hora                  DATETIME(6) DEFAULT (UTC_TIMESTAMP(6)) NOT NULL,
    CONSTRAINT pk_notificacion PRIMARY KEY (id_notificacion),
    CONSTRAINT fk_notificacion_cliente FOREIGN KEY (cod_cliente) REFERENCES billetera.afiliacion (cod_cliente),
    CONSTRAINT fk_notificacion_operacion FOREIGN KEY (id_operacion) REFERENCES billetera.operacion (id_operacion),
    CONSTRAINT fk_notificacion_solicitud FOREIGN KEY (id_solicitud) REFERENCES billetera.solicitud_cobro (id_solicitud),
    CONSTRAINT ck_notificacion_leida CHECK (leida IN (0, 1))
) ENGINE = InnoDB COMMENT = 'Extensión v1.9: avisos de la billetera para el cliente.';

CREATE INDEX ix_codigo_qr_cliente ON billetera.codigo_qr (cod_cliente, tipo, estado);
CREATE INDEX ix_operacion_destino ON billetera.operacion (cod_cliente_destino, fecha_hora);
CREATE INDEX ix_operacion_origen ON billetera.operacion (cod_cliente_origen, fecha_hora);
CREATE INDEX ix_solicitud_cobro_pagador ON billetera.solicitud_cobro (cod_pagador, estado);
CREATE INDEX ix_notificacion_cliente ON billetera.notificacion (cod_cliente, leida);

DELIMITER //

-- «Ana D.»: el nombre que la billetera muestra de otro cliente.
CREATE DEFINER = 'bna_owner'@'%' FUNCTION billetera.fn_nombre_corto(p_cod_cliente VARCHAR(12))
    RETURNS VARCHAR(80) READS SQL DATA
    COMMENT 'Interno. Primer nombre e inicial del apellido paterno.'
BEGIN
    DECLARE v_nombre VARCHAR(80);
    SELECT CONCAT(SUBSTRING_INDEX(TRIM(nombres), ' ', 1), ' ', LEFT(apellido_paterno, 1), '.') INTO v_nombre
      FROM clientes.cliente WHERE cod_cliente = p_cod_cliente;
    RETURN v_nombre;
END //

CREATE DEFINER = 'bna_owner'@'%' FUNCTION billetera.fn_soles(p_monto DECIMAL(15,2))
    RETURNS VARCHAR(30) DETERMINISTIC
    COMMENT 'Interno. «S/ 12.50».'
BEGIN
    RETURN CONCAT('S/ ', FORMAT(p_monto, 2, 'en_US'));
END //

-- Interno. La cuenta de la billetera de un cliente que puede operar; si no, falla.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.cuenta_activa(IN p_cod_cliente VARCHAR(12), OUT p_num_cuenta VARCHAR(20))
    COMMENT 'Interno. Exige una afiliación ACTIVA de un cliente que puede operar.'
BEGIN
    DECLARE v_estado VARCHAR(15);
    DECLARE v_opera BOOLEAN;
    SELECT a.num_cuenta, a.estado, e.permite_operar INTO p_num_cuenta, v_estado, v_opera
      FROM billetera.afiliacion a
      JOIN clientes.cliente c ON c.cod_cliente = a.cod_cliente
      JOIN clientes.estado_cliente e ON e.cod_estado = c.estado_cliente
     WHERE a.cod_cliente = p_cod_cliente;
    IF p_num_cuenta IS NULL OR v_estado <> 'ACTIVA' OR NOT v_opera THEN
        CALL core.fallar('BNA-BILLETERA: el cliente no tiene una billetera activa');
    END IF;
END //

-- Interno. El cliente con billetera de un celular, que puede recibir; si no, falla.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.destino_por_celular(
    IN p_celular VARCHAR(20), OUT p_cod_cliente VARCHAR(12), OUT p_num_cuenta VARCHAR(20))
    COMMENT 'Interno. Busca la billetera de un celular sin repetirlo en el error.'
BEGIN
    DECLARE v_opera BOOLEAN;
    SELECT a.cod_cliente, a.num_cuenta, e.permite_operar INTO p_cod_cliente, p_num_cuenta, v_opera
      FROM clientes.cliente c
      JOIN clientes.estado_cliente e ON e.cod_estado = c.estado_cliente
      JOIN billetera.afiliacion a ON a.cod_cliente = c.cod_cliente
     WHERE c.celular = p_celular;
    IF p_cod_cliente IS NULL OR NOT v_opera THEN
        CALL core.fallar('BNA-BILLETERA-DESTINO: el celular no tiene una billetera que pueda recibir');
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.exigir_llave(IN p_llave VARCHAR(64), IN p_huella CHAR(64))
    COMMENT 'Interno. Una operación de dinero exige llave y huella.'
BEGIN
    IF p_llave IS NULL OR p_huella IS NULL THEN
        CALL core.fallar('BNA-IDEMPOTENCIA: la llave de idempotencia es obligatoria');
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.notificar(
    IN p_cod_cliente VARCHAR(12), IN p_tipo VARCHAR(30), IN p_mensaje VARCHAR(200), IN p_id_operacion BINARY(16),
    IN p_id_solicitud BINARY(16))
    COMMENT 'Interno. Agrega un aviso para el cliente.'
BEGIN
    INSERT INTO billetera.notificacion (cod_cliente, tipo, mensaje, id_operacion, id_solicitud)
    VALUES (p_cod_cliente, p_tipo, p_mensaje, p_id_operacion, p_id_solicitud);
END //

-- Afilia a un cliente o cambia su PIN y su cuenta; reinicia los intentos y reactiva una
-- afiliación BLOQUEADA.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.afiliar(
    IN p_cod_cliente VARCHAR(12), IN p_num_cuenta VARCHAR(20), IN p_pin VARCHAR(64), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_nueva BOOLEAN)
    COMMENT 'Afilia un cliente ACTIVO a la Billetera Digital con su cuenta y su PIN.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_estado_cliente, v_estado_cuenta, v_regimen VARCHAR(25);
    DECLARE v_moneda CHAR(3);
    DECLARE v_conjunta BOOLEAN;
    DECLARE v_otro VARCHAR(12);
    DECLARE v_sal CHAR(32);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        IF NOT coalesce(REGEXP_LIKE(p_pin, '^[0-9]{6}$'), FALSE) THEN
            CALL core.fallar('BNA-BILLETERA-PIN: el PIN debe tener 6 dígitos');
        END IF;
        SELECT estado_cliente INTO v_estado_cliente FROM clientes.cliente WHERE cod_cliente = p_cod_cliente FOR SHARE;
        IF v_estado_cliente IS NULL THEN
            CALL core.fallar('BNA-CLIENTE: el cliente no existe');
        END IF;
        IF v_estado_cliente <> 'ACTIVO' THEN
            CALL core.fallar('BNA-CLIENTE-NO-ACTIVO: el cliente no está ACTIVO');
        END IF;
        SELECT c.moneda, c.estado_cuenta, c.regimen, r.firma_conjunta
          INTO v_moneda, v_estado_cuenta, v_regimen, v_conjunta
          FROM cuentas.cuenta_ahorro c JOIN cuentas.regimen_cuenta r ON r.cod_regimen = c.regimen
         WHERE c.num_cuenta = p_num_cuenta FOR SHARE;
        IF v_moneda IS NULL THEN
            CALL core.fallar('BNA-CUENTA: la cuenta no existe');
        END IF;
        IF NOT EXISTS (SELECT 1 FROM cuentas.titularidad WHERE cod_cliente = p_cod_cliente AND num_cuenta = p_num_cuenta) THEN
            CALL core.fallar('BNA-BILLETERA-TITULAR: el cliente no es titular de la cuenta');
        END IF;
        IF v_moneda <> 'PEN' THEN
            CALL core.fallar('BNA-BILLETERA-MONEDA: la billetera opera solo en soles (RN-BD-002)');
        END IF;
        IF v_conjunta OR v_estado_cuenta <> 'ACTIVA' THEN
            CALL core.fallar('BNA-BILLETERA-CUENTA: la cuenta debe estar ACTIVA y no exigir firma conjunta');
        END IF;
        SELECT cod_cliente INTO v_otro FROM billetera.afiliacion WHERE num_cuenta = p_num_cuenta FOR UPDATE;
        IF v_otro IS NOT NULL AND v_otro <> p_cod_cliente THEN
            CALL core.fallar('BNA-BILLETERA-CUENTA: la cuenta ya es de otra billetera');
        END IF;
        SELECT COUNT(*) = 0 INTO p_nueva FROM billetera.afiliacion WHERE cod_cliente = p_cod_cliente FOR UPDATE;
        -- Con otra cuenta, sus QR anteriores dejan de cobrar en la cuenta vieja.
        UPDATE billetera.codigo_qr SET estado = 'ANULADO'
         WHERE cod_cliente = p_cod_cliente AND estado = 'ACTIVO' AND num_cuenta <> p_num_cuenta;
        SET v_sal = HEX(RANDOM_BYTES(16));
        INSERT INTO billetera.afiliacion (cod_cliente, num_cuenta, hash_pin, sal)
        VALUES (p_cod_cliente, p_num_cuenta, SHA2(CONCAT(v_sal, p_pin), 256), v_sal) AS nueva
        ON DUPLICATE KEY UPDATE num_cuenta = nueva.num_cuenta, hash_pin = nueva.hash_pin, sal = nueva.sal,
                                intentos_fallidos = 0, estado = 'ACTIVA', fecha_ultimo_cambio = UTC_TIMESTAMP(6);
        CALL core.registrar_evento('BILLETERA', 'afiliacion', p_cod_cliente, IF(p_nueva, 'AFILIAR', 'CAMBIAR_PIN'),
                                   p_actor, p_correlation_id, JSON_OBJECT('num_cuenta', p_num_cuenta));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

-- Un PIN equivocado no es un error: cuenta el intento y, al tercero, bloquea. Resultados:
-- EXITOSO, FALLIDO, BLOQUEADA, NO_AFILIADO (el celular no tiene billetera) y
-- CLIENTE_NO_OPERA. Solo EXITOSO devuelve el cliente.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.validar_acceso(
    IN p_celular VARCHAR(20), IN p_pin VARCHAR(64), IN p_correlation_id BINARY(16),
    OUT p_cod_cliente VARCHAR(12), OUT p_resultado VARCHAR(20), OUT p_intentos_restantes SMALLINT)
    COMMENT 'Valida el celular y el PIN de la billetera y registra el intento.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_opera BOOLEAN;
    DECLARE v_hash CHAR(64);
    DECLARE v_sal CHAR(32);
    DECLARE v_estado VARCHAR(15);
    DECLARE v_intentos SMALLINT;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        SET p_cod_cliente = NULL, p_intentos_restantes = 0;
        SELECT c.cod_cliente, e.permite_operar INTO v_cliente, v_opera
          FROM clientes.cliente c JOIN clientes.estado_cliente e ON e.cod_estado = c.estado_cliente
         WHERE c.celular = p_celular;
        IF v_cliente IS NOT NULL THEN
            SELECT hash_pin, sal, estado, intentos_fallidos INTO v_hash, v_sal, v_estado, v_intentos
              FROM billetera.afiliacion WHERE cod_cliente = v_cliente FOR UPDATE;
        END IF;
        IF v_hash IS NULL THEN
            SET p_resultado = 'NO_AFILIADO';
        ELSE
            IF v_estado = 'BLOQUEADA' THEN
                SET p_resultado = 'BLOQUEADA';
            ELSEIF NOT v_opera THEN
                SET p_resultado = 'CLIENTE_NO_OPERA';
            ELSEIF SHA2(CONCAT(v_sal, coalesce(p_pin, '')), 256) = v_hash THEN
                SET p_resultado = 'EXITOSO', p_cod_cliente = v_cliente, v_intentos = 0;
                UPDATE billetera.afiliacion SET intentos_fallidos = 0 WHERE cod_cliente = v_cliente;
            ELSE
                SET p_resultado = 'FALLIDO', v_intentos = LEAST(v_intentos + 1, 3);
                UPDATE billetera.afiliacion
                   SET intentos_fallidos = v_intentos, estado = IF(v_intentos >= 3, 'BLOQUEADA', estado)
                 WHERE cod_cliente = v_cliente;
            END IF;
            SET p_intentos_restantes = 3 - v_intentos;
            CALL core.registrar_evento('BILLETERA', 'afiliacion', v_cliente, 'VALIDAR_ACCESO', CONCAT('cliente:', v_cliente),
                                       p_correlation_id, JSON_OBJECT('resultado', p_resultado,
                                                                     'intentos_restantes', p_intentos_restantes));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

-- El nombre corto del dueño de un celular con billetera, o NULL (sin billetera o propio).
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.buscar_contacto(
    IN p_cod_cliente VARCHAR(12), IN p_celular VARCHAR(20), OUT p_nombre VARCHAR(80))
    COMMENT 'Nombre corto del destinatario de un envío; no devuelve su código ni sus datos.'
BEGIN
    DECLARE v_cliente VARCHAR(12);
    DECLARE v_opera BOOLEAN;
    SET p_nombre = NULL;
    SELECT a.cod_cliente, e.permite_operar INTO v_cliente, v_opera
      FROM clientes.cliente c
      JOIN clientes.estado_cliente e ON e.cod_estado = c.estado_cliente
      JOIN billetera.afiliacion a ON a.cod_cliente = c.cod_cliente
     WHERE c.celular = p_celular;
    IF v_cliente IS NOT NULL AND v_opera AND v_cliente <> p_cod_cliente THEN
        SET p_nombre = billetera.fn_nombre_corto(v_cliente);
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.registrar_comercio(
    IN p_ruc CHAR(11), IN p_razon_social VARCHAR(150), IN p_num_cuenta VARCHAR(20), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_id_comercio BINARY(16), OUT p_id_qr BINARY(16))
    COMMENT 'Afilia un comercio con su cuenta de abono y le genera su QR estático.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_moneda CHAR(3);
    DECLARE v_estado_cuenta VARCHAR(25);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        IF NOT coalesce(REGEXP_LIKE(p_ruc, '^(10|15|17|20)[0-9]{9}$'), FALSE) THEN
            CALL core.fallar('BNA-COMERCIO-RUC: el RUC debe tener 11 dígitos');
        END IF;
        IF coalesce(TRIM(p_razon_social), '') = '' THEN
            CALL core.fallar('BNA-COMERCIO: la razón social es obligatoria');
        END IF;
        SELECT moneda, estado_cuenta INTO v_moneda, v_estado_cuenta FROM cuentas.cuenta_ahorro
         WHERE num_cuenta = p_num_cuenta FOR SHARE;
        IF v_moneda IS NULL THEN
            CALL core.fallar('BNA-CUENTA: la cuenta no existe');
        END IF;
        IF v_moneda <> 'PEN' OR v_estado_cuenta <> 'ACTIVA' THEN
            CALL core.fallar('BNA-BILLETERA-CUENTA: la cuenta de abono debe estar ACTIVA y en soles');
        END IF;
        IF EXISTS (SELECT 1 FROM billetera.comercio WHERE ruc = p_ruc FOR UPDATE) THEN
            CALL core.fallar('BNA-COMERCIO-DUPLICADO: el RUC ya está afiliado');
        END IF;
        SET p_id_comercio = core.uuid_v4(), p_id_qr = core.uuid_v4();
        INSERT INTO billetera.comercio (id_comercio, ruc, razon_social, num_cuenta)
        VALUES (p_id_comercio, p_ruc, TRIM(p_razon_social), p_num_cuenta);
        INSERT INTO billetera.codigo_qr (id_qr, tipo, num_cuenta, id_comercio)
        VALUES (p_id_qr, 'ESTATICO', p_num_cuenta, p_id_comercio);
        CALL core.registrar_evento('BILLETERA', 'comercio', BIN_TO_UUID(p_id_comercio), 'REGISTRAR_COMERCIO', p_actor,
                                   p_correlation_id, JSON_OBJECT('ruc', p_ruc, 'num_cuenta', p_num_cuenta,
                                                                 'id_qr', BIN_TO_UUID(p_id_qr)));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

-- Sin monto: el QR estático del cliente (el mismo cada vez). Con monto: uno dinámico que
-- vence en p_minutos (1 a 60, 15 por omisión) y se paga una sola vez.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.crear_qr(
    IN p_cod_cliente VARCHAR(12), IN p_monto DECIMAL(15,2), IN p_minutos SMALLINT, IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_id_qr BINARY(16), OUT p_nuevo BOOLEAN)
    COMMENT 'Genera el QR de cobro de un cliente.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_cuenta VARCHAR(20);
    DECLARE v_minutos SMALLINT DEFAULT coalesce(p_minutos, 15);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        CALL billetera.cuenta_activa(p_cod_cliente, v_cuenta);
        -- Serializa la creación del QR estático de un mismo cliente.
        SELECT num_cuenta INTO v_cuenta FROM billetera.afiliacion WHERE cod_cliente = p_cod_cliente FOR UPDATE;
        SET p_nuevo = TRUE, p_id_qr = NULL;
        IF p_monto IS NULL THEN
            SELECT id_qr INTO p_id_qr FROM billetera.codigo_qr
             WHERE cod_cliente = p_cod_cliente AND tipo = 'ESTATICO' AND estado = 'ACTIVO' AND num_cuenta = v_cuenta
             LIMIT 1;
            IF p_id_qr IS NOT NULL THEN
                SET p_nuevo = FALSE;
            ELSE
                SET p_id_qr = core.uuid_v4();
                INSERT INTO billetera.codigo_qr (id_qr, tipo, num_cuenta, cod_cliente)
                VALUES (p_id_qr, 'ESTATICO', v_cuenta, p_cod_cliente);
            END IF;
        ELSE
            IF p_monto <= 0 THEN
                CALL core.fallar('BNA-BILLETERA-MONTO: el monto debe ser mayor que cero');
            END IF;
            IF v_minutos NOT BETWEEN 1 AND 60 THEN
                CALL core.fallar('BNA-QR: la vigencia de un QR dinámico va de 1 a 60 minutos');
            END IF;
            SET p_id_qr = core.uuid_v4();
            INSERT INTO billetera.codigo_qr (id_qr, tipo, num_cuenta, cod_cliente, monto, fecha_expiracion)
            VALUES (p_id_qr, 'DINAMICO', v_cuenta, p_cod_cliente, p_monto, UTC_TIMESTAMP(6) + INTERVAL v_minutos MINUTE);
        END IF;
        IF p_nuevo THEN
            CALL core.registrar_evento('BILLETERA', 'codigo_qr', BIN_TO_UUID(p_id_qr), 'CREAR_QR', p_actor, p_correlation_id,
                                       JSON_OBJECT('cod_cliente', p_cod_cliente, 'monto', p_monto));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

-- Interno. Mueve el dinero y registra la operación; quien llama ya reservó la llave.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.ejecutar_operacion(
    IN p_tipo VARCHAR(10), IN p_origen VARCHAR(12), IN p_cuenta_origen VARCHAR(20), IN p_destino VARCHAR(12),
    IN p_id_comercio BINARY(16), IN p_cuenta_destino VARCHAR(20), IN p_monto DECIMAL(15,2), IN p_referencia VARCHAR(100),
    IN p_id_qr BINARY(16), IN p_id_solicitud BINARY(16), IN p_llave VARCHAR(64), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_id_operacion BINARY(16), OUT p_uuid_debito BINARY(16))
    COMMENT 'Interno. Transferencia por canal BD, operación, llave y avisos.'
BEGIN
    DECLARE v_abono BINARY(16);
    DECLARE v_repetido BOOLEAN;
    DECLARE v_nombre_origen VARCHAR(80) DEFAULT billetera.fn_nombre_corto(p_origen);
    DECLARE v_nombre_destino VARCHAR(150);
    DECLARE v_correlacion BINARY(16) DEFAULT coalesce(p_correlation_id, core.uuid_v4());
    IF p_monto IS NULL OR p_monto <= 0 THEN
        CALL core.fallar('BNA-BILLETERA-MONTO: el monto debe ser mayor que cero');
    END IF;
    IF p_cuenta_origen = p_cuenta_destino THEN
        CALL core.fallar('BNA-BILLETERA-PROPIA: el origen y el destino son la misma billetera');
    END IF;
    IF p_id_comercio IS NOT NULL THEN
        SELECT razon_social INTO v_nombre_destino FROM billetera.comercio WHERE id_comercio = p_id_comercio;
    ELSE
        SET v_nombre_destino = billetera.fn_nombre_corto(p_destino);
    END IF;
    CALL cuentas.registrar_transferencia(p_cuenta_origen, p_cuenta_destino, p_monto,
                                         LEFT(CONCAT('Billetera ', p_tipo, ': ', v_nombre_origen, ' a ', v_nombre_destino), 200),
                                         'BD', v_correlacion, NULL, NULL, p_actor, p_uuid_debito, v_abono, v_repetido);
    SET p_id_operacion = core.uuid_v4();
    INSERT INTO billetera.operacion (id_operacion, tipo, cod_cliente_origen, cod_cliente_destino, id_comercio,
                                     num_cuenta_origen, num_cuenta_destino, monto, referencia, id_qr, id_solicitud,
                                     uuid_debito, uuid_abono)
    VALUES (p_id_operacion, p_tipo, p_origen, p_destino, p_id_comercio, p_cuenta_origen, p_cuenta_destino, p_monto,
            NULLIF(TRIM(p_referencia), ''), p_id_qr, p_id_solicitud, p_uuid_debito, v_abono);
    UPDATE cuentas.idempotencia_movimiento SET uuid_transaccion = p_uuid_debito, uuid_abono = v_abono
     WHERE llave = p_llave;
    CALL billetera.notificar(p_origen, CONCAT(p_tipo, '_ENVIADO'),
                             CONCAT('Enviaste ', billetera.fn_soles(p_monto), ' a ', v_nombre_destino), p_id_operacion,
                             p_id_solicitud);
    IF p_destino IS NOT NULL THEN
        CALL billetera.notificar(p_destino, CONCAT(p_tipo, '_RECIBIDO'),
                                 CONCAT(v_nombre_origen, ' te envió ', billetera.fn_soles(p_monto)), p_id_operacion,
                                 p_id_solicitud);
    END IF;
    CALL core.registrar_evento('BILLETERA', 'operacion', BIN_TO_UUID(p_id_operacion), CONCAT('OPERACION_', p_tipo),
                               p_actor, v_correlacion,
                               JSON_OBJECT('cod_cliente_origen', p_origen, 'cod_cliente_destino', p_destino,
                                           'id_comercio', BIN_TO_UUID(p_id_comercio), 'monto', p_monto,
                                           'id_qr', BIN_TO_UUID(p_id_qr), 'id_solicitud', BIN_TO_UUID(p_id_solicitud),
                                           'uuid_debito', BIN_TO_UUID(p_uuid_debito)));
END //

-- Interno. Con la llave ya usada, la operación que la usó si es la misma; si no, falla.
-- v1.10: lectura con bloqueo (FOR SHARE). Quien llama pudo leer antes en su transacción
-- (la API lee la afiliación del cliente), y con REPEATABLE READ una lectura sin bloqueo vería
-- esa instantánea, anterior a la operación que confirmó la petición por la que se esperó.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.operacion_repetida(
    IN p_debito BINARY(16), IN p_tipo VARCHAR(10), IN p_origen VARCHAR(12), IN p_id_qr BINARY(16),
    IN p_id_solicitud BINARY(16), OUT p_id_operacion BINARY(16))
    COMMENT 'Interno. Devuelve la operación de una llave repetida.'
BEGIN
    SET p_id_operacion = NULL;
    SELECT id_operacion INTO p_id_operacion FROM billetera.operacion
     WHERE uuid_debito = p_debito AND tipo = p_tipo AND cod_cliente_origen = p_origen
       AND (p_id_qr IS NULL OR id_qr = p_id_qr) AND (p_id_solicitud IS NULL OR id_solicitud = p_id_solicitud)
       FOR SHARE;
    IF p_id_operacion IS NULL THEN
        CALL core.fallar('BNA-IDEMPOTENCIA: la llave se usó en otra operación');
    END IF;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.transferir(
    IN p_cod_cliente VARCHAR(12), IN p_celular_destino VARCHAR(20), IN p_monto DECIMAL(15,2),
    IN p_referencia VARCHAR(100), IN p_llave VARCHAR(64), IN p_huella CHAR(64), IN p_actor VARCHAR(40),
    IN p_correlation_id BINARY(16), OUT p_id_operacion BINARY(16), OUT p_uuid_debito BINARY(16),
    OUT p_repetido BOOLEAN)
    COMMENT 'Envío de dinero a otra billetera por su celular (P2P), idempotente.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_abono BINARY(16);
    DECLARE v_cuenta, v_cuenta_destino VARCHAR(20);
    DECLARE v_destino VARCHAR(12);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        CALL billetera.exigir_llave(p_llave, p_huella);
        CALL cuentas.reservar_llave(p_llave, p_huella, p_repetido, p_uuid_debito, v_abono);
        IF p_repetido THEN
            CALL billetera.operacion_repetida(p_uuid_debito, 'P2P', p_cod_cliente, NULL, NULL, p_id_operacion);
        ELSE
            CALL billetera.cuenta_activa(p_cod_cliente, v_cuenta);
            CALL billetera.destino_por_celular(p_celular_destino, v_destino, v_cuenta_destino);
            IF v_destino = p_cod_cliente THEN
                CALL core.fallar('BNA-BILLETERA-PROPIA: el origen y el destino son la misma billetera');
            END IF;
            CALL billetera.ejecutar_operacion('P2P', p_cod_cliente, v_cuenta, v_destino, NULL, v_cuenta_destino, p_monto,
                                              p_referencia, NULL, NULL, p_llave, p_actor, p_correlation_id,
                                              p_id_operacion, p_uuid_debito);
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

-- Un QR dinámico cobra su monto (si p_monto llega, debe ser el mismo) y queda PAGADO; uno
-- estático cobra p_monto. El QR se bloquea después de reservar la llave: un pago repetido
-- espera al primero y devuelve su operación en vez de encontrar el QR ya pagado.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.pagar_qr(
    IN p_cod_cliente VARCHAR(12), IN p_id_qr BINARY(16), IN p_monto DECIMAL(15,2), IN p_llave VARCHAR(64),
    IN p_huella CHAR(64), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16),
    OUT p_id_operacion BINARY(16), OUT p_uuid_debito BINARY(16), OUT p_repetido BOOLEAN)
    COMMENT 'Pago con QR a otra billetera o a un comercio, idempotente.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_abono BINARY(16);
    DECLARE v_cuenta VARCHAR(20);
    DECLARE v_tipo, v_estado VARCHAR(10);
    DECLARE v_cuenta_qr VARCHAR(20);
    DECLARE v_dueno VARCHAR(12);
    DECLARE v_comercio BINARY(16);
    DECLARE v_monto_qr, v_monto DECIMAL(15,2);
    DECLARE v_expira DATETIME(6);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        CALL billetera.exigir_llave(p_llave, p_huella);
        CALL cuentas.reservar_llave(p_llave, p_huella, p_repetido, p_uuid_debito, v_abono);
        IF p_repetido THEN
            CALL billetera.operacion_repetida(p_uuid_debito, 'QR', p_cod_cliente, p_id_qr, NULL, p_id_operacion);
        ELSE
            CALL billetera.cuenta_activa(p_cod_cliente, v_cuenta);
            SELECT q.tipo, q.estado, q.num_cuenta, q.cod_cliente, q.id_comercio, q.monto, q.fecha_expiracion
              INTO v_tipo, v_estado, v_cuenta_qr, v_dueno, v_comercio, v_monto_qr, v_expira
              FROM billetera.codigo_qr q WHERE q.id_qr = p_id_qr FOR UPDATE;
            IF v_tipo IS NULL THEN
                CALL core.fallar('BNA-QR: el código QR no existe');
            END IF;
            IF v_estado <> 'ACTIVO' OR v_expira < UTC_TIMESTAMP(6)
               OR (v_comercio IS NOT NULL AND (SELECT estado FROM billetera.comercio WHERE id_comercio = v_comercio) <> 'ACTIVO')
               OR (v_dueno IS NOT NULL AND (SELECT estado FROM billetera.afiliacion WHERE cod_cliente = v_dueno) <> 'ACTIVA') THEN
                CALL core.fallar('BNA-QR-NO-VIGENTE: el código QR ya no está vigente');
            END IF;
            IF v_dueno = p_cod_cliente OR v_cuenta_qr = v_cuenta THEN
                CALL core.fallar('BNA-QR-PROPIO: no se puede pagar un código QR propio');
            END IF;
            IF v_tipo = 'DINAMICO' THEN
                IF p_monto IS NOT NULL AND p_monto <> v_monto_qr THEN
                    CALL core.fallar('BNA-QR-MONTO: el monto no es el del código QR');
                END IF;
                SET v_monto = v_monto_qr;
                UPDATE billetera.codigo_qr SET estado = 'PAGADO' WHERE id_qr = p_id_qr;
            ELSE
                SET v_monto = p_monto;
            END IF;
            CALL billetera.ejecutar_operacion('QR', p_cod_cliente, v_cuenta, v_dueno, v_comercio, v_cuenta_qr, v_monto,
                                              NULL, p_id_qr, NULL, p_llave, p_actor, p_correlation_id,
                                              p_id_operacion, p_uuid_debito);
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.crear_solicitud(
    IN p_cod_cliente VARCHAR(12), IN p_celular_pagador VARCHAR(20), IN p_monto DECIMAL(15,2),
    IN p_concepto VARCHAR(100), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), OUT p_id_solicitud BINARY(16))
    COMMENT 'Pide dinero a otra billetera por su celular; vence a las 48 horas.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_cuenta, v_cuenta_pagador VARCHAR(20);
    DECLARE v_pagador VARCHAR(12);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        CALL billetera.cuenta_activa(p_cod_cliente, v_cuenta);
        CALL billetera.destino_por_celular(p_celular_pagador, v_pagador, v_cuenta_pagador);
        IF v_pagador = p_cod_cliente THEN
            CALL core.fallar('BNA-BILLETERA-PROPIA: el origen y el destino son la misma billetera');
        END IF;
        IF p_monto IS NULL OR p_monto <= 0 THEN
            CALL core.fallar('BNA-BILLETERA-MONTO: el monto debe ser mayor que cero');
        END IF;
        SET p_id_solicitud = core.uuid_v4();
        INSERT INTO billetera.solicitud_cobro (id_solicitud, cod_solicitante, cod_pagador, monto, concepto, fecha_vencimiento)
        VALUES (p_id_solicitud, p_cod_cliente, v_pagador, p_monto, NULLIF(TRIM(p_concepto), ''),
                UTC_TIMESTAMP(6) + INTERVAL 48 HOUR);
        CALL billetera.notificar(v_pagador, 'SOLICITUD_RECIBIDA',
                                 CONCAT(billetera.fn_nombre_corto(p_cod_cliente), ' te pide ', billetera.fn_soles(p_monto)),
                                 NULL, p_id_solicitud);
        CALL core.registrar_evento('BILLETERA', 'solicitud_cobro', BIN_TO_UUID(p_id_solicitud), 'CREAR_SOLICITUD', p_actor,
                                   p_correlation_id, JSON_OBJECT('cod_solicitante', p_cod_cliente, 'cod_pagador', v_pagador,
                                                                 'monto', p_monto));
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

-- ACEPTAR (paga; exige llave) o RECHAZAR, solo el pagador; CANCELAR, solo quien la pidió.
CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.responder_solicitud(
    IN p_cod_cliente VARCHAR(12), IN p_id_solicitud BINARY(16), IN p_accion VARCHAR(10), IN p_llave VARCHAR(64),
    IN p_huella CHAR(64), IN p_actor VARCHAR(40), IN p_correlation_id BINARY(16), OUT p_estado VARCHAR(15),
    OUT p_id_operacion BINARY(16), OUT p_uuid_debito BINARY(16), OUT p_repetido BOOLEAN)
    COMMENT 'Acepta, rechaza o cancela una solicitud de cobro.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_abono BINARY(16);
    DECLARE v_solicitante, v_pagador VARCHAR(12);
    DECLARE v_estado VARCHAR(15);
    DECLARE v_monto DECIMAL(15,2);
    DECLARE v_concepto VARCHAR(100);
    DECLARE v_vence DATETIME(6);
    DECLARE v_cuenta, v_cuenta_solicitante VARCHAR(20);
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_billetera;
        RELEASE SAVEPOINT bna_billetera;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_billetera; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_billetera; END IF;
            END;
            RESIGNAL;
        END;
        IF p_accion IS NULL OR p_accion NOT IN ('ACEPTAR', 'RECHAZAR', 'CANCELAR') THEN
            CALL core.fallar('BNA-SOLICITUD-ACCION: la acción debe ser ACEPTAR, RECHAZAR o CANCELAR');
        END IF;
        SET p_repetido = FALSE, p_id_operacion = NULL, p_uuid_debito = NULL;
        IF p_accion = 'ACEPTAR' THEN
            CALL billetera.exigir_llave(p_llave, p_huella);
            CALL cuentas.reservar_llave(p_llave, p_huella, p_repetido, p_uuid_debito, v_abono);
        END IF;
        IF p_repetido THEN
            CALL billetera.operacion_repetida(p_uuid_debito, 'SOLICITUD', p_cod_cliente, NULL, p_id_solicitud,
                                              p_id_operacion);
            SET p_estado = 'PAGADA';
        ELSE
            SELECT cod_solicitante, cod_pagador, estado, monto, concepto, fecha_vencimiento
              INTO v_solicitante, v_pagador, v_estado, v_monto, v_concepto, v_vence
              FROM billetera.solicitud_cobro WHERE id_solicitud = p_id_solicitud FOR UPDATE;
            IF v_estado IS NULL THEN
                CALL core.fallar('BNA-SOLICITUD: la solicitud no existe');
            END IF;
            IF (p_accion = 'CANCELAR' AND p_cod_cliente <> v_solicitante)
               OR (p_accion <> 'CANCELAR' AND p_cod_cliente <> v_pagador) THEN
                CALL core.fallar('BNA-SOLICITUD-PERMISO: el cliente no puede responder esta solicitud');
            END IF;
            IF v_estado <> 'PENDIENTE' OR v_vence < UTC_TIMESTAMP(6) THEN
                CALL core.fallar('BNA-SOLICITUD-NO-PENDIENTE: la solicitud ya no está pendiente');
            END IF;
            SET p_estado = CASE p_accion WHEN 'ACEPTAR' THEN 'PAGADA' WHEN 'RECHAZAR' THEN 'RECHAZADA' ELSE 'CANCELADA' END;
            IF p_accion = 'ACEPTAR' THEN
                CALL billetera.cuenta_activa(v_pagador, v_cuenta);
                SELECT num_cuenta INTO v_cuenta_solicitante FROM billetera.afiliacion WHERE cod_cliente = v_solicitante;
                CALL billetera.ejecutar_operacion('SOLICITUD', v_pagador, v_cuenta, v_solicitante, NULL,
                                                  v_cuenta_solicitante, v_monto, v_concepto, NULL, p_id_solicitud,
                                                  p_llave, p_actor, p_correlation_id, p_id_operacion, p_uuid_debito);
            ELSEIF p_accion = 'RECHAZAR' THEN
                CALL billetera.notificar(v_solicitante, 'SOLICITUD_RECHAZADA',
                                         CONCAT(billetera.fn_nombre_corto(v_pagador), ' rechazó tu solicitud de ',
                                                billetera.fn_soles(v_monto)), NULL, p_id_solicitud);
            END IF;
            UPDATE billetera.solicitud_cobro SET estado = p_estado, fecha_respuesta = UTC_TIMESTAMP(6)
             WHERE id_solicitud = p_id_solicitud;
            CALL core.registrar_evento('BILLETERA', 'solicitud_cobro', BIN_TO_UUID(p_id_solicitud),
                                       CONCAT('SOLICITUD_', p_estado), p_actor, p_correlation_id,
                                       JSON_OBJECT('cod_cliente', p_cod_cliente, 'monto', v_monto,
                                                   'id_operacion', BIN_TO_UUID(p_id_operacion)));
        END IF;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_billetera; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE billetera.marcar_notificaciones_leidas(
    IN p_cod_cliente VARCHAR(12), OUT p_filas INT)
    COMMENT 'Marca como leídos los avisos de un cliente.'
BEGIN
    UPDATE billetera.notificacion SET leida = 1 WHERE cod_cliente = p_cod_cliente AND leida = 0;
    SET p_filas = ROW_COUNT();
END //

DELIMITER ;

-- Lecturas de la API: sin el hash ni la sal del PIN, sin celulares ni documentos. Los
-- estados vencidos se calculan al leer.
CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW billetera.v_afiliacion_api AS
SELECT a.cod_cliente, billetera.fn_nombre_corto(a.cod_cliente) AS nombre_corto, a.num_cuenta, a.estado,
       a.intentos_fallidos, a.fecha_afiliacion, a.fecha_ultimo_cambio, c.saldo_disponible,
       l.monto_maximo_diario AS tope_diario,
       coalesce((SELECT d.monto_acumulado FROM core.consumo_diario d
                  WHERE d.num_cuenta = a.num_cuenta AND d.id_canal = 'BD'
                    AND d.fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6))), 0) AS consumido_hoy
  FROM billetera.afiliacion a
  JOIN cuentas.cuenta_ahorro c ON c.num_cuenta = a.num_cuenta
  LEFT JOIN core.limite_canal l ON l.id_canal = 'BD' AND l.moneda = c.moneda;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW billetera.v_comercio_api AS
SELECT BIN_TO_UUID(m.id_comercio) AS id_comercio, m.ruc, m.razon_social, m.num_cuenta, m.estado, m.fecha_afiliacion,
       (SELECT BIN_TO_UUID(q.id_qr) FROM billetera.codigo_qr q
         WHERE q.id_comercio = m.id_comercio AND q.tipo = 'ESTATICO' AND q.estado = 'ACTIVO' LIMIT 1) AS id_qr
  FROM billetera.comercio m;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW billetera.v_qr_api AS
SELECT BIN_TO_UUID(q.id_qr) AS id_qr, q.tipo, q.monto,
       CASE WHEN q.estado = 'ACTIVO' AND q.fecha_expiracion < UTC_TIMESTAMP(6) THEN 'VENCIDO' ELSE q.estado END AS estado,
       q.cod_cliente, BIN_TO_UUID(q.id_comercio) AS id_comercio, q.num_cuenta,
       coalesce(m.razon_social, billetera.fn_nombre_corto(q.cod_cliente)) AS beneficiario,
       q.fecha_generacion, q.fecha_expiracion
  FROM billetera.codigo_qr q
  LEFT JOIN billetera.comercio m ON m.id_comercio = q.id_comercio;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW billetera.v_operacion_api AS
SELECT BIN_TO_UUID(o.id_operacion) AS id_operacion, o.tipo, o.cod_cliente_origen, o.cod_cliente_destino,
       BIN_TO_UUID(o.id_comercio) AS id_comercio, billetera.fn_nombre_corto(o.cod_cliente_origen) AS nombre_origen,
       coalesce(m.razon_social, billetera.fn_nombre_corto(o.cod_cliente_destino)) AS nombre_destino,
       o.num_cuenta_origen, o.num_cuenta_destino, o.monto, o.referencia, BIN_TO_UUID(o.id_qr) AS id_qr,
       BIN_TO_UUID(o.id_solicitud) AS id_solicitud, BIN_TO_UUID(o.uuid_debito) AS uuid_debito,
       BIN_TO_UUID(o.uuid_abono) AS uuid_abono, o.fecha_hora
  FROM billetera.operacion o
  LEFT JOIN billetera.comercio m ON m.id_comercio = o.id_comercio;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW billetera.v_solicitud_api AS
SELECT BIN_TO_UUID(s.id_solicitud) AS id_solicitud, s.cod_solicitante, s.cod_pagador,
       billetera.fn_nombre_corto(s.cod_solicitante) AS nombre_solicitante,
       billetera.fn_nombre_corto(s.cod_pagador) AS nombre_pagador, s.monto, s.concepto,
       CASE WHEN s.estado = 'PENDIENTE' AND s.fecha_vencimiento < UTC_TIMESTAMP(6) THEN 'VENCIDA' ELSE s.estado END AS estado,
       s.fecha_solicitud, s.fecha_vencimiento, s.fecha_respuesta
  FROM billetera.solicitud_cobro s;

CREATE DEFINER = 'bna_owner'@'%' SQL SECURITY DEFINER VIEW billetera.v_notificacion_api AS
SELECT id_notificacion, cod_cliente, tipo, mensaje, leida, BIN_TO_UUID(id_operacion) AS id_operacion,
       BIN_TO_UUID(id_solicitud) AS id_solicitud, fecha_hora
  FROM billetera.notificacion;

GRANT EXECUTE ON PROCEDURE billetera.afiliar TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.validar_acceso TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.buscar_contacto TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.registrar_comercio TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.crear_qr TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.transferir TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.pagar_qr TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.crear_solicitud TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.responder_solicitud TO bna_api;
GRANT EXECUTE ON PROCEDURE billetera.marcar_notificaciones_leidas TO bna_api;
GRANT SELECT ON billetera.v_afiliacion_api TO bna_api;
GRANT SELECT ON billetera.v_comercio_api TO bna_api;
GRANT SELECT ON billetera.v_qr_api TO bna_api;
GRANT SELECT ON billetera.v_operacion_api TO bna_api;
GRANT SELECT ON billetera.v_solicitud_api TO bna_api;
GRANT SELECT ON billetera.v_notificacion_api TO bna_api;

-- ---------------------------------------------------------------------
-- 16. Retenciones de tarjeta con caducidad (v1.11)
-- ---------------------------------------------------------------------
-- Una autorización AUTORIZADA retiene el saldo disponible y el tope del día hasta que se
-- confirma (v1.8) o se extorna. Si el cajero cae entre autorizar y confirmar, nadie la
-- extorna y el saldo queda retenido sin plazo. Desde v1.11 se libera sola.
-- DECISIÓN (v1.11): el plazo por omisión es de 15 minutos (tarjetas.fn_minutos_retencion),
--   como el QR dinámico de la billetera. Es un valor provisional: el plazo lo decide el
--   equipo (pregunta abierta en el issue #34). Cambiarlo es cambiar esa función.
-- DECISIÓN (v1.11): tarjetas.liberar_retenciones_vencidas extorna, como
--   extornar_autorizacion, las AUTORIZADA sin movimiento cuya hora pasó el plazo; los
--   triggers devuelven el disponible y el tope del día en que se comprometieron. Las
--   DISPENSADA (el cajero ya entregó el efectivo) no se tocan. Quien llama puede dar un
--   plazo menor, de 1 a 1440 minutos (un operador que sabe que el cajero cayó). El evento
--   tarjetas.ev_liberar_retenciones lo llama cada minuto con el plazo por omisión.
-- DECISIÓN (v1.11): la liberación lee con FOR UPDATE SKIP LOCKED: una autorización que una
--   confirmación tiene bloqueada se salta y la confirmación gana; si la liberación la
--   bloquea primero, la confirmación espera y falla porque ya no está vigente. Una
--   confirmación de una retención vencida falla aunque aún no se haya liberado.
CREATE INDEX ix_autorizacion_estado_fecha ON tarjetas.autorizacion (estado_autorizacion, fecha_hora);

DELIMITER //

CREATE DEFINER = 'bna_owner'@'%' FUNCTION tarjetas.fn_minutos_retencion() RETURNS SMALLINT
    DETERMINISTIC NO SQL
    COMMENT 'Minutos que una autorización sin confirmar retiene el saldo (pregunta #34).'
BEGIN
    RETURN 15;
END //

CREATE DEFINER = 'bna_owner'@'%' PROCEDURE tarjetas.liberar_retenciones_vencidas(
    IN p_minutos SMALLINT, IN p_actor VARCHAR(40), OUT p_liberadas INT)
    COMMENT 'Extorna las autorizaciones sin confirmar que pasaron el plazo de retención.'
BEGIN
    DECLARE v_propia BOOLEAN DEFAULT FALSE;
    DECLARE v_minutos SMALLINT DEFAULT coalesce(p_minutos, tarjetas.fn_minutos_retencion());
    DECLARE v_limite DATETIME(6);
    DECLARE v_uuid BINARY(16);
    DECLARE v_fin BOOLEAN DEFAULT FALSE;
    DECLARE v_correlacion BINARY(16) DEFAULT core.uuid_v4();
    DECLARE c_vencidas CURSOR FOR
        SELECT uuid_autorizacion FROM tarjetas.autorizacion
         WHERE estado_autorizacion = 'AUTORIZADA' AND uuid_transaccion IS NULL AND fecha_hora < v_limite
         ORDER BY fecha_hora
           FOR UPDATE SKIP LOCKED;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fin = TRUE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1305 SET v_propia = TRUE;
        SAVEPOINT bna_op;
        RELEASE SAVEPOINT bna_op;
    END;
    IF v_propia THEN START TRANSACTION; ELSE SAVEPOINT bna_op; END IF;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            -- Un deadlock ya revirtió toda la transacción y el savepoint no existe.
            -- RESIGNAL queda fuera del alcance de este manejador, o se descartaría.
            BEGIN
                DECLARE CONTINUE HANDLER FOR 1305 BEGIN END;
                IF v_propia THEN ROLLBACK; ELSE ROLLBACK TO SAVEPOINT bna_op; END IF;
            END;
            RESIGNAL;
        END;
        IF p_actor IS NULL THEN
            CALL core.fallar('BNA-ACTOR: falta el actor');
        END IF;
        IF v_minutos IS NULL OR v_minutos < 1 OR v_minutos > 1440 THEN
            CALL core.fallar('BNA-PLAZO: el plazo de una retención es de 1 a 1440 minutos');
        END IF;
        SET v_limite = UTC_TIMESTAMP(6) - INTERVAL v_minutos MINUTE;
        SET p_liberadas = 0;
        OPEN c_vencidas;
        liberar: LOOP
            FETCH c_vencidas INTO v_uuid;
            IF v_fin THEN
                LEAVE liberar;
            END IF;
            UPDATE tarjetas.autorizacion
               SET estado_autorizacion = 'EXTORNADA', codigo_respuesta = 'EXT',
                   motivo_rechazo = 'BNA-RETENCION: venció sin confirmarse'
             WHERE uuid_autorizacion = v_uuid;
            CALL core.registrar_evento('CORE', 'autorizacion', BIN_TO_UUID(v_uuid), 'LIBERAR_RETENCION', p_actor,
                                       v_correlacion, JSON_OBJECT('estado_anterior', 'AUTORIZADA',
                                                                  'plazo_minutos', v_minutos));
            SET p_liberadas = p_liberadas + 1;
        END LOOP;
        CLOSE c_vencidas;
        IF v_propia THEN COMMIT; ELSE RELEASE SAVEPOINT bna_op; END IF;
    END;
END //

CREATE DEFINER = 'bna_owner'@'%' EVENT tarjetas.ev_liberar_retenciones
    ON SCHEDULE EVERY 1 MINUTE STARTS '2026-01-01 00:00:00'
    ON COMPLETION PRESERVE ENABLE
    COMMENT 'Cada minuto: extorna las autorizaciones sin confirmar que pasaron el plazo de retención.'
    DO CALL tarjetas.liberar_retenciones_vencidas(NULL, 'SISTEMA', @bna_retenciones_liberadas) //

DELIMITER ;

GRANT EXECUTE ON FUNCTION tarjetas.fn_minutos_retencion TO bna_api, bna_app, bna_admin;
GRANT EXECUTE ON PROCEDURE tarjetas.liberar_retenciones_vencidas TO bna_api, bna_app, bna_admin;
