-- =====================================================================
-- BNA - Script 12: Triggers, Evento y Procedimientos
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- Mejoras: bloqueo al 3.er intento fallido, historial de estado inmutable,
--   control de topes diarios, vencimiento automatico de tarjetas y
--   aplicacion de pagos por componente.
-- IDs: UUID v7 (CHAR(36)). La aplicacion genera los v7; para las filas que
--   genera la propia base se usa la funcion fn_uuid_v7().
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

DELIMITER $$

-- ---------------------------------------------------------------------
-- fn_uuid_v7: genera un UUID version 7 (time-ordered) en MySQL 8.0/8.4.
-- 48 bits de timestamp en milisegundos + 4 bits de version (7) + 2 bits de
-- variante + 74 bits aleatorios. Se usa solo para filas creadas por la base
-- (triggers/procedimientos); la aplicacion genera sus propios v7.
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_uuid_v7 $$
CREATE FUNCTION fn_uuid_v7()
RETURNS CHAR(36)
NO SQL
BEGIN
  DECLARE v_ms    CHAR(12);
  DECLARE v_rand  CHAR(32);
  DECLARE v_hex   CHAR(32);

  SET v_ms = LPAD(HEX(
               FLOOR(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3)) * 1000)
               + FLOOR(MICROSECOND(CURRENT_TIMESTAMP(3)) / 1000)), 12, '0');
  SET v_rand = LPAD(HEX(RANDOM_BYTES(16)), 32, '0');
  SET v_hex = CONCAT(
                LEFT(v_ms, 12),
                '7',
                SUBSTRING(v_rand, 1, 3),
                SUBSTRING('89ab', 1 + FLOOR(RAND() * 4), 1),
                SUBSTRING(v_rand, 5, 15));

  RETURN CONCAT(LEFT(v_hex, 8), '-', SUBSTRING(v_hex, 9, 4), '-',
                SUBSTRING(v_hex, 13, 4), '-', SUBSTRING(v_hex, 17, 4), '-',
                RIGHT(v_hex, 12));
END $$

-- ---------------------------------------------------------------------
-- Historial inicial al crear la tarjeta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_tarjeta_hist_ins $$
CREATE TRIGGER trg_tarjeta_hist_ins
AFTER INSERT ON tar_tarjeta
FOR EACH ROW
BEGIN
  INSERT INTO tar_historial_estado (id_historial, id_tarjeta, estado_anterior, estado_nuevo, motivo, origen)
  VALUES (fn_uuid_v7(), NEW.id_tarjeta, NEW.estado, NEW.estado, 'Alta de tarjeta', 'SISTEMA');
END $$

-- ---------------------------------------------------------------------
-- Historial al cambiar el estado de la tarjeta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_tarjeta_hist_upd $$
CREATE TRIGGER trg_tarjeta_hist_upd
AFTER UPDATE ON tar_tarjeta
FOR EACH ROW
BEGIN
  IF NEW.estado <> OLD.estado THEN
    INSERT INTO tar_historial_estado (id_historial, id_tarjeta, estado_anterior, estado_nuevo, motivo, origen)
    VALUES (fn_uuid_v7(), NEW.id_tarjeta, OLD.estado, NEW.estado, 'Cambio de estado', 'SISTEMA');
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Inmutabilidad del historial de estados (no UPDATE ni DELETE)
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_historial_no_update $$
CREATE TRIGGER trg_historial_no_update
BEFORE UPDATE ON tar_historial_estado
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El historial de estados es inmutable';
END $$

DROP TRIGGER IF EXISTS trg_historial_no_delete $$
CREATE TRIGGER trg_historial_no_delete
BEFORE DELETE ON tar_historial_estado
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El historial de estados es inmutable';
END $$

-- ---------------------------------------------------------------------
-- Control de intentos fallidos: bloqueo de credencial y tarjeta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_intento_fallido $$
CREATE TRIGGER trg_intento_fallido
AFTER INSERT ON tar_intento_autenticacion
FOR EACH ROW
BEGIN
  IF NEW.resultado = 'FALLIDO' THEN
    UPDATE tar_credencial
       SET intentos_fallidos = intentos_fallidos + 1
     WHERE id_tarjeta = NEW.id_tarjeta
       AND tipo = NEW.tipo_credencial;

    IF (SELECT intentos_fallidos FROM tar_credencial
         WHERE id_tarjeta = NEW.id_tarjeta AND tipo = NEW.tipo_credencial) >= 3 THEN
      UPDATE tar_credencial
         SET bloqueada = 1
       WHERE id_tarjeta = NEW.id_tarjeta AND tipo = NEW.tipo_credencial;

      UPDATE tar_tarjeta
         SET estado = 'BLOQUEADA'
       WHERE id_tarjeta = NEW.id_tarjeta AND estado = 'ACTIVA';
    END IF;
  ELSE
    UPDATE tar_credencial
       SET intentos_fallidos = 0
     WHERE id_tarjeta = NEW.id_tarjeta
       AND tipo = NEW.tipo_credencial;
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Control de tope diario por autorizaciones aprobadas
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_autorizacion_tope $$
CREATE TRIGGER trg_autorizacion_tope
AFTER INSERT ON tar_autorizacion
FOR EACH ROW
BEGIN
  IF NEW.estado = 'APROBADA' THEN
    INSERT INTO cta_control_tope_diario (id_tope, num_cuenta, id_canal, fecha_corte, monto_acumulado)
    VALUES (fn_uuid_v7(), NEW.num_cuenta, NEW.id_canal, DATE(NEW.fecha_hora), NEW.monto)
    ON DUPLICATE KEY UPDATE monto_acumulado = monto_acumulado + NEW.monto;
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Control de tope diario por transacciones de cuenta
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_transaccion_tope $$
CREATE TRIGGER trg_transaccion_tope
AFTER INSERT ON cta_transaccion
FOR EACH ROW
BEGIN
  IF NEW.estado_transaccion = 'APLICADA' AND NEW.tipo_movimiento = 'D' THEN
    INSERT INTO cta_control_tope_diario (id_tope, num_cuenta, id_canal, fecha_corte, monto_acumulado)
    VALUES (fn_uuid_v7(), NEW.num_cuenta, NEW.id_canal, NEW.fecha_valor, NEW.monto)
    ON DUPLICATE KEY UPDATE monto_acumulado = monto_acumulado + NEW.monto;
  END IF;
END $$

-- ---------------------------------------------------------------------
-- Procedimiento: bloquear tarjeta
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_bloquear_tarjeta $$
CREATE PROCEDURE sp_bloquear_tarjeta(
  IN p_id_tarjeta CHAR(36),
  IN p_motivo     VARCHAR(120),
  IN p_origen     VARCHAR(20)
)
BEGIN
  UPDATE tar_tarjeta
     SET estado = 'BLOQUEADA'
   WHERE id_tarjeta = p_id_tarjeta AND estado = 'ACTIVA';
END $$

-- ---------------------------------------------------------------------
-- Procedimiento: aplicar pago por componente y actualizar la cuota
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_aplicar_pago $$
CREATE PROCEDURE sp_aplicar_pago(
  IN p_id_pago          CHAR(36),
  IN p_id_cuota_credito CHAR(36),
  IN p_capital          DECIMAL(15,2),
  IN p_interes          DECIMAL(15,2),
  IN p_seguro           DECIMAL(15,2),
  IN p_mora             DECIMAL(15,2)
)
BEGIN
  DECLARE v_total  DECIMAL(15,2);
  DECLARE v_cuota  DECIMAL(15,2);
  DECLARE v_pagado DECIMAL(15,2);

  SET v_total = p_capital + p_interes + p_seguro + p_mora;

  INSERT INTO cob_aplicacion_pago
    (id_aplicacion, id_pago, id_cuota_credito, aplica_capital, aplica_interes, aplica_seguro, aplica_mora)
  VALUES
    (fn_uuid_v7(), p_id_pago, p_id_cuota_credito, p_capital, p_interes, p_seguro, p_mora);

  SELECT cuota_total, monto_pagado INTO v_cuota, v_pagado
    FROM cob_cuota WHERE id_cuota_credito = p_id_cuota_credito;

  SET v_pagado = v_pagado + v_total;

  UPDATE cob_cuota
     SET monto_pagado = v_pagado,
         estado_cuota = CASE WHEN v_pagado >= v_cuota THEN 'PAGADA'
                             WHEN v_pagado > 0 THEN 'PARCIAL'
                             ELSE estado_cuota END
   WHERE id_cuota_credito = p_id_cuota_credito;

  UPDATE cob_pago SET estado_pago = 'APLICADO' WHERE id_pago = p_id_pago;
END $$

-- ---------------------------------------------------------------------
-- Evento: vencimiento automatico de tarjetas (diario)
-- ---------------------------------------------------------------------
DROP EVENT IF EXISTS ev_expirar_tarjetas $$
CREATE EVENT ev_expirar_tarjetas
ON SCHEDULE EVERY 1 DAY
STARTS (TIMESTAMP(CURRENT_DATE) + INTERVAL 1 DAY)
DO
BEGIN
  UPDATE tar_tarjeta
     SET estado = 'VENCIDA'
   WHERE estado = 'ACTIVA'
     AND fecha_vencimiento < CURRENT_DATE();
END $$

DELIMITER ;
