-- Ayudantes de las pruebas de la Billetera Digital de sql/bna_extension.sql (v1.9),
-- MySQL 8.4. Los carga root después de la extensión. Son SQL SECURITY INVOKER: corren
-- con los privilegios de quien llama (bna_api_user).
--   bd_afiliar  afilia a C001 (CTA-PEN-1, PIN 123456) y a C002 (CTA-PEN-2, PIN 654321)
--   bd_saldos   guarda en @bd_s1 y @bd_s2 el saldo contable de CTA-PEN-1 y CTA-PEN-2
SET NAMES utf8mb4;

DELIMITER //

CREATE PROCEDURE prueba.bd_afiliar() SQL SECURITY INVOKER
BEGIN
    CALL billetera.afiliar('C001', 'CTA-PEN-1', '123456', 'asesor.bd', UUID_TO_BIN(UUID()), @bd_nueva);
    CALL billetera.afiliar('C002', 'CTA-PEN-2', '654321', 'asesor.bd', UUID_TO_BIN(UUID()), @bd_nueva);
END //

CREATE PROCEDURE prueba.bd_saldos() SQL SECURITY INVOKER
BEGIN
    SELECT saldo_contable INTO @bd_s1 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1';
    SELECT saldo_contable INTO @bd_s2 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2';
END //

DELIMITER ;
