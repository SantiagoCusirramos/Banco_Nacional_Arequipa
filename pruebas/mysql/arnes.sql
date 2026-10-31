-- Arnés de pruebas de la base integrada (base prueba), MySQL 8.4.
-- Cada prueba abre una transacción, ejecuta sus sentencias (una lista JSON;
-- cada una se prepara y ejecuta por separado), comprueba el resultado y la
-- deshace con ROLLBACK, de modo que las pruebas no se afectan entre sí; el
-- veredicto se escribe después, en prueba.resultado.
-- Los procedimientos son SQL SECURITY INVOKER: las sentencias corren con los
-- privilegios de quien llama (bna_app_user o bna_admin_user), que es lo que
-- se prueba. La misma prueba puede registrarse con los dos usuarios; el
-- resultado de un ID es «pasa» solo si pasan todas sus filas.
-- Lo carga root después del DDL.
CREATE DATABASE prueba;

CREATE TABLE prueba.resultado (
    n           INT AUTO_INCREMENT PRIMARY KEY,
    id          VARCHAR(10) NOT NULL,
    usuario     VARCHAR(32) NOT NULL,
    grupo       VARCHAR(30) NOT NULL,
    referencia  VARCHAR(120) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    mecanismo   VARCHAR(30) NOT NULL,
    esperado    TEXT NOT NULL,
    obtenido    TEXT NOT NULL,
    ok          TINYINT(1)            -- NULL = N/A
);

DELIMITER //

-- Ejecuta cada sentencia de la lista JSON.
CREATE PROCEDURE prueba.ejecutar(IN p_sentencias JSON) SQL SECURITY INVOKER
BEGIN
    DECLARE i INT DEFAULT 0;
    WHILE i < JSON_LENGTH(p_sentencias) DO
        SET @prueba_sql = JSON_UNQUOTE(JSON_EXTRACT(p_sentencias, CONCAT('$[', i, ']')));
        PREPARE prueba_st FROM @prueba_sql;
        EXECUTE prueba_st;
        DEALLOCATE PREPARE prueba_st;
        SET i = i + 1;
    END WHILE;
END //

-- La operación debe rechazarse con un mensaje que cumpla p_patron.
-- El mensaje es el del primer error del área de diagnóstico apilada (no una
-- advertencia previa, como «No data»); el manejador la lee con GET STACKED
-- DIAGNOSTICS porque cualquier otra sentencia vacía el área actual.
CREATE PROCEDURE prueba.rechaza(IN p_id VARCHAR(10), IN p_grupo VARCHAR(30), IN p_ref VARCHAR(120),
                                IN p_desc VARCHAR(255), IN p_sentencias JSON, IN p_patron VARCHAR(255),
                                IN p_mecanismo VARCHAR(30)) SQL SECURITY INVOKER
BEGIN
    DECLARE v_msg, v_txt TEXT DEFAULT NULL;
    DECLARE v_n, v_i INT;
    DECLARE v_estado CHAR(5);
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET STACKED DIAGNOSTICS v_n = NUMBER;
            SET v_i = 1;
            WHILE v_i <= v_n AND v_msg IS NULL DO
                GET STACKED DIAGNOSTICS CONDITION v_i v_estado = RETURNED_SQLSTATE, v_txt = MESSAGE_TEXT;
                IF LEFT(v_estado, 2) NOT IN ('00', '01', '02') THEN
                    SET v_msg = v_txt;
                END IF;
                SET v_i = v_i + 1;
            END WHILE;
            SET v_msg = coalesce(v_msg, '(error sin mensaje)');
        END;
        START TRANSACTION;
        CALL prueba.ejecutar(p_sentencias);
    END;
    ROLLBACK;
    INSERT INTO prueba.resultado (id, usuario, grupo, referencia, descripcion, mecanismo, esperado, obtenido, ok)
    VALUES (p_id, SUBSTRING_INDEX(USER(), '@', 1), p_grupo, p_ref, p_desc, p_mecanismo,
            CONCAT('Rechazo: ', p_patron),
            IF(v_msg IS NULL, 'Aceptada sin error', CONCAT('Rechazo: ', v_msg)),
            v_msg IS NOT NULL AND REGEXP_LIKE(v_msg, p_patron, 'c'));
END //

-- La operación debe aceptarse y dejar el estado que describe p_cond (una
-- expresión o consulta escalar booleana); p_obtenido describe lo obtenido.
CREATE PROCEDURE prueba.verifica(IN p_id VARCHAR(10), IN p_grupo VARCHAR(30), IN p_ref VARCHAR(120),
                                 IN p_desc VARCHAR(255), IN p_sentencias JSON, IN p_cond TEXT,
                                 IN p_esperado TEXT, IN p_obtenido TEXT, IN p_mecanismo VARCHAR(30))
    SQL SECURITY INVOKER
BEGIN
    DECLARE v_err, v_txt TEXT DEFAULT NULL;
    DECLARE v_n, v_i INT;
    DECLARE v_estado CHAR(5);
    SET @prueba_ok = NULL, @prueba_obt = NULL;
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            GET STACKED DIAGNOSTICS v_n = NUMBER;
            SET v_i = 1;
            WHILE v_i <= v_n AND v_err IS NULL DO
                GET STACKED DIAGNOSTICS CONDITION v_i v_estado = RETURNED_SQLSTATE, v_txt = MESSAGE_TEXT;
                IF LEFT(v_estado, 2) NOT IN ('00', '01', '02') THEN
                    SET v_err = v_txt;
                END IF;
                SET v_i = v_i + 1;
            END WHILE;
            SET v_err = coalesce(v_err, '(error sin mensaje)');
        END;
        START TRANSACTION;
        CALL prueba.ejecutar(p_sentencias);
        CALL prueba.ejecutar(JSON_ARRAY(CONCAT('SELECT (', p_cond, ') INTO @prueba_ok'),
                                        CONCAT('SELECT (', p_obtenido, ') INTO @prueba_obt')));
    END;
    ROLLBACK;
    INSERT INTO prueba.resultado (id, usuario, grupo, referencia, descripcion, mecanismo, esperado, obtenido, ok)
    VALUES (p_id, SUBSTRING_INDEX(USER(), '@', 1), p_grupo, p_ref, p_desc, p_mecanismo, p_esperado,
            IF(v_err IS NOT NULL, CONCAT('Error: ', v_err), coalesce(@prueba_obt, '(sin dato)')),
            v_err IS NULL AND coalesce(@prueba_ok, 0) = 1);
END //

-- Falla que no tiene una prueba de ejecución con sentido.
CREATE PROCEDURE prueba.na(IN p_id VARCHAR(10), IN p_grupo VARCHAR(30), IN p_ref VARCHAR(120),
                           IN p_desc VARCHAR(255), IN p_razon TEXT) SQL SECURITY INVOKER
BEGIN
    INSERT INTO prueba.resultado (id, usuario, grupo, referencia, descripcion, mecanismo, esperado, obtenido, ok)
    VALUES (p_id, SUBSTRING_INDEX(USER(), '@', 1), p_grupo, p_ref, p_desc, 'N/A', '—', p_razon, NULL);
END //

-- Registra un movimiento con su asiento de partida doble cuadrado
-- (cuentas contables 1101 Caja y 2101 Depósitos de ahorro), por
-- core.registrar_asiento, como lo haría la aplicación. p_uuid permite
-- registrar el movimiento de una autorización con el identificador de su
-- operación. Debe llamarse dentro de una transacción (lo están las pruebas
-- y la carga de datos).
CREATE PROCEDURE prueba.movimiento(IN p_cuenta VARCHAR(20), IN p_tipo VARCHAR(25), IN p_monto DECIMAL(15,2),
                                   IN p_canal VARCHAR(5), IN p_moneda CHAR(3), IN p_uuid BINARY(16),
                                   OUT p_mov BINARY(16)) SQL SECURITY INVOKER
BEGIN
    DECLARE v_nat CHAR(1);
    DECLARE v_moneda CHAR(3);
    DECLARE v_asiento BINARY(16);
    SELECT naturaleza INTO v_nat FROM cuentas.tipo_operacion WHERE tipo_operacion = p_tipo;
    SELECT coalesce(p_moneda, moneda) INTO v_moneda FROM cuentas.cuenta_ahorro WHERE num_cuenta = p_cuenta;
    SET p_mov = coalesce(p_uuid, core.uuid_v4());
    CALL core.registrar_asiento(NULL, CONCAT('P-', HEX(RANDOM_BYTES(8))), CURRENT_DATE, CURRENT_DATE,
        CONCAT(p_tipo, ' ', p_cuenta), v_moneda, core.uuid_v4(), NULL,
        JSON_ARRAY(JSON_OBJECT('partida', IF(v_nat = 'C', 'DEBE', 'HABER'), 'importe', p_monto, 'cuenta', '1101'),
                   JSON_OBJECT('partida', IF(v_nat = 'C', 'HABER', 'DEBE'), 'importe', p_monto, 'cuenta', '2101')),
        v_asiento);
    INSERT INTO cuentas.movimiento (uuid_transaccion, tipo_operacion, monto, glosa, estado_transaccion,
                                    id_asiento, num_cuenta, id_canal)
    VALUES (p_mov, p_tipo, p_monto, 'Prueba', 'APROBADO', v_asiento, p_cuenta, p_canal);
END //

DELIMITER ;

-- Los dos usuarios de las pruebas, con sus roles.
CREATE USER 'bna_app_user'@'%' IDENTIFIED BY 'app' DEFAULT ROLE bna_app;
CREATE USER 'bna_admin_user'@'%' IDENTIFIED BY 'admin' DEFAULT ROLE bna_admin;
GRANT EXECUTE ON prueba.* TO 'bna_app_user'@'%', 'bna_admin_user'@'%';
GRANT INSERT ON prueba.resultado TO 'bna_app_user'@'%', 'bna_admin_user'@'%';
