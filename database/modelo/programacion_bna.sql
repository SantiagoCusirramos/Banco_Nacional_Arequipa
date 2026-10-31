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
CREATE PROCEDURE core.fallar(IN p_mensaje TEXT)
    COMMENT 'Rechaza la operación con el mensaje dado (a lo sumo 128 caracteres).'
BEGIN
    DECLARE v_mensaje VARCHAR(128) DEFAULT LEFT(p_mensaje, 128);
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_mensaje;
END //

-- MySQL: DATETIME no guarda zona; las marcas de tiempo se guardan en UTC y
--   CONVERT_TZ devuelve NULL si el servidor no tiene cargadas las tablas de
--   zonas horarias, lo que dejaría sin efecto el tope diario: se rechaza.
CREATE FUNCTION core.fn_fecha_negocio(p_momento DATETIME(6))
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
CREATE FUNCTION core.uuid_v4()
RETURNS BINARY(16) NOT DETERMINISTIC NO SQL
    COMMENT 'UUID versión 4 en BINARY(16).'
BEGIN
    RETURN CONCAT(RANDOM_BYTES(6), CHAR(0x40 | (ASCII(RANDOM_BYTES(1)) & 0x0F)), RANDOM_BYTES(1),
                  CHAR(0x80 | (ASCII(RANDOM_BYTES(1)) & 0x3F)), RANDOM_BYTES(7));
END //

-- Comprueba la configuración de la que dependen las reglas. La llaman la
-- carga y las pruebas (L02); conviene llamarla al iniciar la aplicación.
CREATE PROCEDURE core.verificar_configuracion()
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
CREATE PROCEDURE core.rechazar_cambio(IN p_codigo VARCHAR(30), IN p_tabla VARCHAR(80), IN p_operacion VARCHAR(10))
    COMMENT 'Rechaza un UPDATE o DELETE sobre una tabla de solo inserción.'
BEGIN
    CALL core.fallar(CONCAT(p_codigo, ': ', p_tabla, ' es de solo inserción (', p_operacion, ' no permitido)'));
END //

CREATE TRIGGER core.tg_asiento_contable_solo_insercion_bu BEFORE UPDATE ON core.asiento_contable
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.asiento_contable', 'UPDATE') //
CREATE TRIGGER core.tg_asiento_contable_solo_insercion_bd BEFORE DELETE ON core.asiento_contable
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.asiento_contable', 'DELETE') //
CREATE TRIGGER core.tg_detalle_asiento_solo_insercion_bu BEFORE UPDATE ON core.detalle_asiento
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.detalle_asiento', 'UPDATE') //
CREATE TRIGGER core.tg_detalle_asiento_solo_insercion_bd BEFORE DELETE ON core.detalle_asiento
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'core.detalle_asiento', 'DELETE') //
CREATE TRIGGER tarjetas.tg_intento_solo_insercion_bu BEFORE UPDATE ON tarjetas.intento_autenticacion
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.intento_autenticacion', 'UPDATE') //
CREATE TRIGGER tarjetas.tg_intento_solo_insercion_bd BEFORE DELETE ON tarjetas.intento_autenticacion
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.intento_autenticacion', 'DELETE') //
CREATE TRIGGER tarjetas.tg_historial_tarjeta_solo_insercion_bu BEFORE UPDATE ON tarjetas.historial_estado_tarjeta
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.historial_estado_tarjeta', 'UPDATE') //
CREATE TRIGGER tarjetas.tg_historial_tarjeta_solo_insercion_bd BEFORE DELETE ON tarjetas.historial_estado_tarjeta
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.historial_estado_tarjeta', 'DELETE') //
CREATE TRIGGER tarjetas.tg_autorizacion_sin_borrado BEFORE DELETE ON tarjetas.autorizacion
FOR EACH ROW CALL core.rechazar_cambio('ERR-TAR-009', 'tarjetas.autorizacion', 'DELETE') //
CREATE TRIGGER creditos.tg_historial_solicitud_solo_insercion_bu BEFORE UPDATE ON creditos.historial_estado_solicitud
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'creditos.historial_estado_solicitud', 'UPDATE') //
CREATE TRIGGER creditos.tg_historial_solicitud_solo_insercion_bd BEFORE DELETE ON creditos.historial_estado_solicitud
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'creditos.historial_estado_solicitud', 'DELETE') //
CREATE TRIGGER creditos.tg_evento_auditoria_solo_insercion_bu BEFORE UPDATE ON creditos.evento_auditoria
FOR EACH ROW CALL core.rechazar_cambio('BNA-SOLO-INSERCION', 'creditos.evento_auditoria', 'UPDATE') //
CREATE TRIGGER creditos.tg_evento_auditoria_solo_insercion_bd BEFORE DELETE ON creditos.evento_auditoria
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
CREATE PROCEDURE core.registrar_asiento(
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
CREATE PROCEDURE core.consumo_sumar(IN p_cuenta VARCHAR(20), IN p_canal VARCHAR(5), IN p_fecha DATE,
                                    IN p_monto DECIMAL(15,2))
BEGIN
    INSERT INTO core.consumo_diario (num_cuenta, id_canal, fecha_corte, monto_acumulado)
    VALUES (p_cuenta, p_canal, p_fecha, GREATEST(p_monto, 0))
    ON DUPLICATE KEY UPDATE monto_acumulado = GREATEST(monto_acumulado + p_monto, 0);
END //

CREATE TRIGGER cuentas.tg_movimiento_validar BEFORE INSERT ON cuentas.movimiento
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

CREATE TRIGGER cuentas.tg_movimiento_aplicar_ai AFTER INSERT ON cuentas.movimiento
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
CREATE TRIGGER cuentas.tg_movimiento_aplicar_au AFTER UPDATE ON cuentas.movimiento
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
CREATE TRIGGER cuentas.tg_movimiento_inmutable_bu BEFORE UPDATE ON cuentas.movimiento
FOR EACH ROW BEGIN
    IF NOT (OLD.estado_transaccion = 'APROBADO' AND NEW.estado_transaccion = 'EXTORNADO')
       OR NOT (NEW.uuid_transaccion <=> OLD.uuid_transaccion AND NEW.tipo_operacion <=> OLD.tipo_operacion
               AND NEW.monto <=> OLD.monto AND NEW.glosa <=> OLD.glosa AND NEW.fecha_hora <=> OLD.fecha_hora
               AND NEW.id_asiento <=> OLD.id_asiento AND NEW.num_cuenta <=> OLD.num_cuenta
               AND NEW.id_canal <=> OLD.id_canal) THEN
        CALL core.fallar('BNA-MOVIMIENTO: solo se admite el paso de APROBADO a EXTORNADO');
    END IF;
END //
CREATE TRIGGER cuentas.tg_movimiento_inmutable_bd BEFORE DELETE ON cuentas.movimiento
FOR EACH ROW CALL core.fallar('BNA-MOVIMIENTO: un movimiento no se borra; se extorna') //

-- ---------------------------------------------------------------------
-- Tarjetas: emisión (trg_tarjeta_bi y trg_tarjeta_ai de Tarjetas).
--   * Solo se emite a un cliente ACTIVO (RF-TAR-005, ERR-TAR-001).
--   * La emisión queda en el historial y en la bandeja hacia SEGURIDAD
--     (RN-SEG-002).
-- ---------------------------------------------------------------------
CREATE TRIGGER tarjetas.tg_tarjeta_emitir BEFORE INSERT ON tarjetas.tarjeta
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

CREATE TRIGGER tarjetas.tg_tarjeta_emitida AFTER INSERT ON tarjetas.tarjeta
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
CREATE TRIGGER tarjetas.tg_tarjeta_estado_via_historial BEFORE UPDATE ON tarjetas.tarjeta
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
CREATE TRIGGER tarjetas.tg_historial_validar BEFORE INSERT ON tarjetas.historial_estado_tarjeta
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
CREATE TRIGGER tarjetas.tg_historial_aplicar AFTER INSERT ON tarjetas.historial_estado_tarjeta
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
CREATE TRIGGER tarjetas.tg_intento_contar AFTER INSERT ON tarjetas.intento_autenticacion
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
CREATE PROCEDURE tarjetas.validar_reglas_autorizacion(
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

CREATE TRIGGER tarjetas.tg_autorizacion_validar_bi BEFORE INSERT ON tarjetas.autorizacion
FOR EACH ROW BEGIN
    IF NEW.estado_autorizacion NOT IN ('INICIADA', 'AUTORIZADA', 'RECHAZADA') THEN
        CALL core.fallar(CONCAT('RN-ATM-007: una autorización nueva no puede estar ', NEW.estado_autorizacion));
    END IF;
    IF NEW.estado_autorizacion = 'AUTORIZADA' THEN
        CALL tarjetas.validar_reglas_autorizacion(NEW.id_tarjeta, NEW.num_cuenta, NEW.id_canal, NEW.id_terminal,
                                                  NEW.tipo_operacion, NEW.monto, NEW.fecha_hora);
    END IF;
END //

CREATE TRIGGER tarjetas.tg_autorizacion_validar_bu BEFORE UPDATE ON tarjetas.autorizacion
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
CREATE PROCEDURE tarjetas.autorizacion_comprometer(
    IN p_num_cuenta VARCHAR(20), IN p_id_canal VARCHAR(5), IN p_id_terminal VARCHAR(30),
    IN p_monto DECIMAL(15,2), IN p_momento DATETIME(6))
BEGIN
    DECLARE v_canal VARCHAR(5) DEFAULT coalesce(p_id_canal,
        (SELECT id_canal FROM core.terminal WHERE id_terminal = p_id_terminal));
    UPDATE cuentas.cuenta_ahorro SET saldo_disponible = saldo_disponible - p_monto WHERE num_cuenta = p_num_cuenta;
    CALL core.consumo_sumar(p_num_cuenta, v_canal, core.fn_fecha_negocio(p_momento), p_monto);
END //

CREATE TRIGGER tarjetas.tg_autorizacion_aplicar_ai AFTER INSERT ON tarjetas.autorizacion
FOR EACH ROW BEGIN
    IF NEW.estado_autorizacion = 'AUTORIZADA'
       AND (SELECT naturaleza FROM cuentas.tipo_operacion WHERE tipo_operacion = NEW.tipo_operacion) = 'D' THEN
        CALL tarjetas.autorizacion_comprometer(NEW.num_cuenta, NEW.id_canal, NEW.id_terminal, NEW.monto, NEW.fecha_hora);
    END IF;
END //

CREATE TRIGGER tarjetas.tg_autorizacion_aplicar_au AFTER UPDATE ON tarjetas.autorizacion
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
CREATE TRIGGER clientes.tg_cliente_estado_tarjetas AFTER UPDATE ON clientes.cliente
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
CREATE PROCEDURE tarjetas.bloquear_tarjeta(IN p_id_tarjeta BINARY(16), IN p_motivo VARCHAR(255),
                                           IN p_origen VARCHAR(20), OUT p_id_historial BIGINT)
    COMMENT 'Bloquea la tarjeta registrando el motivo y el origen en el historial.'
BEGIN
    INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
    VALUES ('BLOQUEADA', p_motivo, p_origen, p_id_tarjeta);
    SET p_id_historial = LAST_INSERT_ID();
END //

CREATE PROCEDURE tarjetas.marcar_tarjetas_vencidas(IN p_fecha DATE, OUT p_marcadas INT)
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

CREATE EVENT tarjetas.ev_marcar_tarjetas_vencidas
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
CREATE PROCEDURE creditos.validar_orden(IN p_id_orden BINARY(16), IN p_id_evaluacion BINARY(16),
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

CREATE TRIGGER creditos.tg_orden_validar_bi BEFORE INSERT ON creditos.orden_desembolso
FOR EACH ROW CALL creditos.validar_orden(NEW.id_orden, NEW.id_evaluacion, NEW.num_cuenta, NEW.importe, NEW.estado_orden) //
CREATE TRIGGER creditos.tg_orden_validar_bu BEFORE UPDATE ON creditos.orden_desembolso
FOR EACH ROW CALL creditos.validar_orden(NEW.id_orden, NEW.id_evaluacion, NEW.num_cuenta, NEW.importe, NEW.estado_orden) //

-- ---------------------------------------------------------------------
-- Cobranza: crédito (decisión I15 del informe).
--   * El crédito nace de una orden CONFIRMADA, y su calendario es OFICIAL y
--     pertenece a la solicitud de la evaluación de esa orden.
-- ---------------------------------------------------------------------
CREATE PROCEDURE creditos.validar_credito(IN p_id_orden BINARY(16), IN p_id_calendario BINARY(16))
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

CREATE TRIGGER creditos.tg_credito_validar_bi BEFORE INSERT ON creditos.credito
FOR EACH ROW CALL creditos.validar_credito(NEW.id_orden, NEW.id_calendario) //
CREATE TRIGGER creditos.tg_credito_validar_bu BEFORE UPDATE ON creditos.credito
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
CREATE TRIGGER creditos.tg_aplicacion_validar BEFORE INSERT ON creditos.aplicacion_pago
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
CREATE TRIGGER creditos.tg_aplicacion_aplicar AFTER INSERT ON creditos.aplicacion_pago
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

CREATE TRIGGER creditos.tg_aplicacion_solo_insercion_bu BEFORE UPDATE ON creditos.aplicacion_pago
FOR EACH ROW CALL core.rechazar_cambio('BNA-PAGO', 'creditos.aplicacion_pago', 'UPDATE') //
CREATE TRIGGER creditos.tg_aplicacion_solo_insercion_bd BEFORE DELETE ON creditos.aplicacion_pago
FOR EACH ROW CALL core.rechazar_cambio('BNA-PAGO', 'creditos.aplicacion_pago', 'DELETE') //

-- Aplica el saldo libre de un pago a las cuotas con saldo, de la más antigua
-- a la más reciente (Cobranza: un pago puede ser parcial o alcanzar para la
-- cuota siguiente). Devuelve el monto aplicado en esta llamada.
CREATE PROCEDURE creditos.aplicar_pago(IN p_id_pago BINARY(16), OUT p_aplicado DECIMAL(15,2))
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
CREATE VIEW tarjetas.v_tarjeta_resumen AS
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
CREATE VIEW tarjetas.v_consumo_diario AS
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
CREATE VIEW tarjetas.v_tope_restante_hoy AS
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
CREATE VIEW tarjetas.v_credenciales_en_riesgo AS
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
CREATE VIEW creditos.v_ordenes_inciertas AS
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
CREATE VIEW creditos.v_entregas_pendientes AS
SELECT ev.id_evento, ev.id_orden, o.codigo_orden, ev.tipo_evento, ev.estado_entrega,
       ev.intentos, ev.siguiente_intento, ev.ultimo_error, ev.creado_en
  FROM creditos.evento_entrega ev
  JOIN creditos.orden_desembolso o ON o.id_orden = ev.id_orden
 WHERE ev.estado_entrega IN ('PENDIENTE', 'ENVIADO', 'FALLIDO') AND ev.intentos > 2;

-- Base para cuadrar operaciones e importes por fecha y moneda contra el CORE:
-- importe de las órdenes confirmadas frente a lo abonado en las cuentas.
CREATE VIEW creditos.v_conciliacion_diaria AS
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
CREATE VIEW core.v_asientos_descuadrados AS
SELECT a.id_asiento, a.numero_asiento, a.fecha_contable,
       coalesce(sum(CASE WHEN d.tipo_partida = 'DEBE' THEN d.importe END), 0) AS debe,
       coalesce(sum(CASE WHEN d.tipo_partida = 'HABER' THEN d.importe END), 0) AS haber
  FROM core.asiento_contable a
  LEFT JOIN core.detalle_asiento d ON d.id_asiento = a.id_asiento
 GROUP BY a.id_asiento, a.numero_asiento, a.fecha_contable
HAVING count(CASE WHEN d.tipo_partida = 'DEBE' THEN 1 END) = 0
    OR count(CASE WHEN d.tipo_partida = 'HABER' THEN 1 END) = 0
    OR debe <> haber;
