-- Ayudantes de las pruebas de captación de sql/bna_extension.sql (v1.7), MySQL 8.4.
-- Los carga root después de la extensión. Son SQL SECURITY INVOKER: corren con los
-- privilegios de quien llama (bna_api_user), así que también prueban los permisos de
-- la API. Cada uno lleva un expediente al estado que necesita la prueba:
--   cap_solicitante  el prospecto registrado (DNI p_doc)
--   cap_caso         su caso abierto (INICIADO)
--   cap_consentido   con los tres consentimientos requeridos aceptados
--   cap_listo        APROBADO: OTP del celular, RENIEC, listas, una central y el perfil
-- Los identificadores salen de p_n: solicitante 35000000-…-<p_n>, caso 35100000-…-<p_n>
-- y OTP 35200000-…-<p_n>. El celular es 95 y siete dígitos de p_n; el correo, p<p_n>@….
SET NAMES utf8mb4;

DELIMITER //

CREATE FUNCTION prueba.cap_id(p_prefijo CHAR(8), p_n INT) RETURNS BINARY(16) DETERMINISTIC
BEGIN
    RETURN UUID_TO_BIN(CONCAT(p_prefijo, '-0000-4000-8000-', LPAD(p_n, 12, '0')));
END //

CREATE PROCEDURE prueba.cap_solicitante(IN p_n INT, IN p_doc VARCHAR(12), OUT p_id BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    CALL clientes.registrar_solicitante_captacion(prueba.cap_id('35000000', p_n), 'DNI', p_doc, 'Prospecto',
        'Ficticio', NULL, CONCAT('95', LPAD(p_n, 7, '0')), CONCAT('p', p_n, '@example.com'), 'asesor.cap',
        UUID_TO_BIN(UUID()), p_id, @cap_duplicado);
END //

CREATE PROCEDURE prueba.cap_caso(IN p_n INT, IN p_doc VARCHAR(12), OUT p_caso BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    DECLARE v_sol BINARY(16);
    CALL prueba.cap_solicitante(p_n, p_doc, v_sol);
    SET p_caso = prueba.cap_id('35100000', p_n);
    CALL clientes.abrir_caso_captacion(p_caso, v_sol, 'AGENCIA', 'AQP01', 'Crédito personal', 'asesor.cap',
                                       UUID_TO_BIN(UUID()));
END //

CREATE PROCEDURE prueba.cap_consentido(IN p_n INT, IN p_doc VARCHAR(12), OUT p_caso BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    CALL prueba.cap_caso(p_n, p_doc, p_caso);
    CALL clientes.registrar_consentimientos_captacion(p_caso,
        JSON_ARRAY(JSON_OBJECT('tipo', 'TRATAMIENTO_DATOS', 'aceptado', TRUE, 'medio', 'DIGITAL'),
                   JSON_OBJECT('tipo', 'CONSULTA_BUROS', 'aceptado', TRUE, 'medio', 'DIGITAL'),
                   JSON_OBJECT('tipo', 'TERMINOS', 'aceptado', TRUE, 'medio', 'DIGITAL')),
        'v1', 'asesor.cap', UUID_TO_BIN(UUID()), @cap_estado);
END //

CREATE PROCEDURE prueba.cap_listo(IN p_n INT, IN p_doc VARCHAR(12), OUT p_caso BINARY(16))
    SQL SECURITY INVOKER
BEGIN
    CALL prueba.cap_consentido(p_n, p_doc, p_caso);
    CALL clientes.emitir_otp_captacion(prueba.cap_id('35200000', p_n), p_caso, 'SMS', REPEAT('a', 64), 'asesor.cap',
                                       UUID_TO_BIN(UUID()), @cap_expira);
    CALL clientes.verificar_otp_captacion(prueba.cap_id('35200000', p_n), p_caso, REPEAT('a', 64), 'asesor.cap',
                                          UUID_TO_BIN(UUID()), @cap_codigo, @cap_restantes, @cap_estado);
    CALL clientes.registrar_validacion_captacion(p_caso, 'RENIEC', 'APROBADO', 'SIMULADO', 'Identidad confirmada',
                                                 'asesor.cap', UUID_TO_BIN(UUID()), @cap_estado);
    CALL clientes.registrar_validacion_captacion(p_caso, 'LISTAS_NEGRAS', 'APROBADO', 'SIMULADO', 'Sin coincidencias',
                                                 'asesor.cap', UUID_TO_BIN(UUID()), @cap_estado);
    CALL clientes.registrar_consulta_riesgo_captacion(p_caso, 'SBS', 'NORMAL', 0, 0, 0, 'SIMULADO', 'asesor.cap',
                                                      UUID_TO_BIN(UUID()), @cap_estado);
    CALL clientes.registrar_perfil_captacion(p_caso, 820, 'BAJO', NULL, 'asesor.cap', UUID_TO_BIN(UUID()),
                                             @cap_estado);
END //

DELIMITER ;
