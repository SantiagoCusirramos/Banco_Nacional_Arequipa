-- Ayudantes y datos de las pruebas de créditos de sql/bna_extension.sql (v1.4), MySQL 8.4.
-- Los carga root después de la extensión. Los procedimientos son SQL SECURITY INVOKER:
-- corren con los privilegios de quien llama (bna_api_user), así que también prueban
-- los permisos de la API. Cada uno arma un paso del flujo de crédito para que las
-- pruebas lleguen al estado que necesitan:
--   cr_calendario  el calendario de SOL en JSON (cuotas de 10.00 de interés)
--   cr_solicitud   el expediente de SOL registrado (una versión)
--   cr_aprobada    la solicitud evaluada con la regla R-A (APROBADA)
--   cr_orden       la orden PREPARADA sobre una cuenta
--   cr_validada    la orden VALIDADA (identidad verificada en ventanilla)
--   cr_credito     el desembolso confirmado: devuelve el código del crédito
SET NAMES utf8mb4;

-- Una cuenta más de C001 (PEN, individual, sin saldo), empleados y usuarios para el
-- analista, y la numeración de órdenes por encima de las de datos.sql
-- (DES-2026-000001 a 000003).
INSERT INTO cuentas.cuenta_ahorro (num_cuenta, cci, moneda, regimen, estado_cuenta, id_agencia) VALUES
    ('CR-PEN-1B', '00219100000000000104', 'PEN', 'INDIVIDUAL', 'ACTIVA', 'AQP01');
INSERT INTO cuentas.titularidad (cod_cliente, num_cuenta) VALUES ('C001', 'CR-PEN-1B');
INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo, id_agencia, activo) VALUES
    (UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'EMP-AN-1', 'Analista Ficticio', 'ANALISTA', 'AQP01', TRUE),
    (UUID_TO_BIN('31000000-0000-4000-8000-000000000002'), 'EMP-OP-1', 'Operador Ficticio', 'OPERADOR', 'AQP01', TRUE),
    (UUID_TO_BIN('31000000-0000-4000-8000-000000000003'), 'EMP-IN-1', 'Exempleado Ficticio', 'ANALISTA', 'AQP01', FALSE);
INSERT INTO core.usuario_sistema (id_usuario, username, nombre, rol, hash_password, algoritmo_hash, version_hash,
                                  id_empleado) VALUES
    (UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', 'Analista Ficticio', 'ANALISTA', 'h',
     'BCRYPT', 'v2', UUID_TO_BIN('31000000-0000-4000-8000-000000000001')),
    (UUID_TO_BIN('32000000-0000-4000-8000-000000000002'), 'operador.cr', 'Operador Ficticio', 'OPERADOR', 'h',
     'BCRYPT', 'v2', UUID_TO_BIN('31000000-0000-4000-8000-000000000002'));
SET @cr_sql = IF((SELECT COUNT(*) FROM information_schema.tables
                   WHERE table_schema = 'creditos' AND table_name = 'numerador_orden') = 1,
                 'ALTER TABLE creditos.numerador_orden AUTO_INCREMENT = 1000', 'DO 0');
PREPARE cr_st FROM @cr_sql;
EXECUTE cr_st;
DEALLOCATE PREPARE cr_st;

DELIMITER //

-- p_n cuotas mensuales desde p_primera: amortización pareja (la última ajusta) e
-- interés de 10.00 por cuota.
CREATE PROCEDURE prueba.cr_calendario(IN p_monto DECIMAL(15,2), IN p_n INT, IN p_primera DATE, OUT p_cuotas JSON)
    SQL SECURITY INVOKER
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_saldo, v_amort DECIMAL(15,2);
    SET p_cuotas = JSON_ARRAY(), v_saldo = p_monto;
    WHILE i <= p_n DO
        SET v_amort = IF(i = p_n, v_saldo, ROUND(p_monto / p_n, 2));
        SET p_cuotas = JSON_ARRAY_APPEND(p_cuotas, '$', JSON_OBJECT(
            'numero_cuota', i, 'fecha_vencimiento', DATE_FORMAT(DATE_ADD(p_primera, INTERVAL i - 1 MONTH), '%Y-%m-%d'),
            'saldo_inicial', v_saldo, 'amortizacion', v_amort, 'interes', 10.00, 'cuota_total', v_amort + 10.00,
            'saldo_final', v_saldo - v_amort));
        SET v_saldo = v_saldo - v_amort, i = i + 1;
    END WHILE;
END //

-- p_primera nula: la primera cuota vence en 30 días.
CREATE PROCEDURE prueba.cr_solicitud(IN p_id CHAR(36), IN p_cliente VARCHAR(12), IN p_monto DECIMAL(15,2),
                                     IN p_n INT, IN p_version SMALLINT, IN p_primera DATE,
                                     OUT p_ronda SMALLINT, OUT p_eval BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    DECLARE v_cuotas JSON;
    CALL prueba.cr_calendario(p_monto, p_n, coalesce(p_primera, CURRENT_DATE + INTERVAL 30 DAY), v_cuotas);
    CALL creditos.registrar_solicitud(UUID_TO_BIN(p_id), p_version, p_cliente, p_monto, 'PEN', p_n, FALSE, 'FRANCES',
                                      0.2200, v_cuotas, SHA2(CONCAT(p_id, '/', p_version, '/', p_monto, '/', p_n), 256),
                                      'pruebas', UUID_TO_BIN(UUID()), p_ronda, p_eval, @cr_repetido);
END //

CREATE PROCEDURE prueba.cr_aprobada(IN p_id CHAR(36), IN p_cliente VARCHAR(12), IN p_monto DECIMAL(15,2),
                                    IN p_n INT, IN p_primera DATE, OUT p_eval BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    DECLARE v_ronda SMALLINT;
    CALL prueba.cr_solicitud(p_id, p_cliente, p_monto, p_n, 1, p_primera, v_ronda, p_eval);
    CALL creditos.evaluar_solicitud(UUID_TO_BIN(p_id), 1, 20000, 0, 850, p_monto * 10, 'pruebas', UUID_TO_BIN(UUID()),
                                    p_eval, @cr_resultado, @cr_regla);
END //

CREATE PROCEDURE prueba.cr_orden(IN p_id CHAR(36), IN p_cliente VARCHAR(12), IN p_cuenta VARCHAR(20),
                                 IN p_monto DECIMAL(15,2), IN p_n INT, OUT p_orden BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    DECLARE v_eval BINARY(16);
    CALL prueba.cr_aprobada(p_id, p_cliente, p_monto, p_n, NULL, v_eval);
    CALL creditos.preparar_orden(v_eval, p_cuenta, 'VEN', 'AQP01', UUID_TO_BIN(UUID()), SHA2(p_id, 256), 'operador.cr',
                                 UUID_TO_BIN(UUID()), p_orden, @cr_codigo, @cr_repetido);
END //

-- p_doc: el DNI del cliente, que se verifica en ventanilla.
CREATE PROCEDURE prueba.cr_validada(IN p_id CHAR(36), IN p_cliente VARCHAR(12), IN p_doc VARCHAR(12),
                                    IN p_cuenta VARCHAR(20), IN p_monto DECIMAL(15,2), IN p_n INT,
                                    OUT p_orden BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    DECLARE v_validacion BIGINT;
    CALL prueba.cr_orden(p_id, p_cliente, p_cuenta, p_monto, p_n, p_orden);
    CALL clientes.verificar_documento('DNI', p_doc, TRUE, 'Desembolso', UUID_TO_BIN(UUID()), 'operador.cr',
                                      v_validacion, @cr_res, @cr_mot, @cr_cli);
    CALL creditos.registrar_validacion_orden(p_orden, 'IDENTIDAD', 'APROBADA', CAST(v_validacion AS CHAR), NULL, NULL,
                                             'operador.cr', UUID_TO_BIN(UUID()), @cr_estado);
END //

CREATE PROCEDURE prueba.cr_credito(IN p_id CHAR(36), IN p_cliente VARCHAR(12), IN p_doc VARCHAR(12),
                                   IN p_cuenta VARCHAR(20), IN p_monto DECIMAL(15,2), IN p_n INT,
                                   OUT p_cod VARCHAR(20))
    SQL SECURITY INVOKER
BEGIN
    DECLARE v_orden BINARY(16);
    CALL prueba.cr_validada(p_id, p_cliente, p_doc, p_cuenta, p_monto, p_n, v_orden);
    CALL creditos.confirmar_orden(v_orden, 'operador.cr', UUID_TO_BIN(UUID()), p_cod, @cr_abono, @cr_repetido);
END //

DELIMITER ;
