-- =====================================================================
-- BNA - Script 11: Vistas
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- v_tarjeta_resumen: resumen de tarjetas con cliente y cuentas
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_tarjeta_resumen AS
SELECT t.id_tarjeta,
       t.ultimos4,
       t.tipo_tarjeta,
       t.estado,
       t.fecha_vencimiento,
       c.id_cliente,
       CONCAT_WS(' ', c.nombres, c.apellido_paterno, c.apellido_materno) AS cliente,
       COUNT(tc.num_cuenta) AS cuentas_asociadas
FROM tar_tarjeta t
JOIN cliente c ON c.id_cliente = t.id_cliente
LEFT JOIN tar_tarjeta_cuenta tc ON tc.id_tarjeta = t.id_tarjeta
GROUP BY t.id_tarjeta, t.ultimos4, t.tipo_tarjeta, t.estado, t.fecha_vencimiento,
         c.id_cliente, c.nombres, c.apellido_paterno, c.apellido_materno;

-- ---------------------------------------------------------------------
-- v_consumo_diario: monto aprobado por tarjeta y dia
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_consumo_diario AS
SELECT a.id_tarjeta,
       DATE(a.fecha_hora) AS fecha,
       a.id_canal,
       SUM(a.monto)       AS monto_consumido
FROM tar_autorizacion a
WHERE a.estado = 'APROBADA'
GROUP BY a.id_tarjeta, DATE(a.fecha_hora), a.id_canal;

-- ---------------------------------------------------------------------
-- v_tope_restante_hoy: tope restante por canal segun consumo del dia
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_tope_restante_hoy AS
SELECT lc.id_canal,
       lc.moneda,
       lc.monto_maximo_diario,
       COALESCE(cd.monto_consumido, 0) AS consumido_hoy,
       CASE
         WHEN lc.monto_maximo_diario IS NULL THEN NULL
         ELSE GREATEST(lc.monto_maximo_diario - COALESCE(cd.monto_consumido, 0), 0)
       END AS tope_restante
FROM limite_canal lc
LEFT JOIN (
   SELECT a.id_canal, SUM(a.monto) AS monto_consumido
   FROM tar_autorizacion a
   WHERE a.estado = 'APROBADA' AND DATE(a.fecha_hora) = CURRENT_DATE()
   GROUP BY a.id_canal
) cd ON cd.id_canal = lc.id_canal
WHERE lc.habilitado = 1;

-- ---------------------------------------------------------------------
-- v_credenciales_en_riesgo: credenciales bloqueadas o con reintentos
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_credenciales_en_riesgo AS
SELECT cr.id_credencial,
       cr.id_tarjeta,
       cr.tipo,
       cr.intentos_fallidos,
       cr.bloqueada,
       cr.fecha_ultimo_cambio
FROM tar_credencial cr
WHERE cr.bloqueada = 1 OR cr.intentos_fallidos >= 2;

-- ---------------------------------------------------------------------
-- des_v_ordenes_inciertas: ordenes sin entrega ni reversion
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW des_v_ordenes_inciertas AS
SELECT o.id_orden,
       o.id_solicitud,
       o.monto,
       o.moneda,
       o.estado_orden,
       o.fecha_generacion
FROM des_orden o
LEFT JOIN des_evento_entrega e
       ON e.id_orden = o.id_orden AND e.tipo_evento IN ('ENTREGA','REVERSION')
WHERE e.id_evento IS NULL
  AND o.estado_orden IN ('GENERADA','EN_VALIDACION','AUTORIZADA');

-- ---------------------------------------------------------------------
-- des_v_entregas_pendientes: ordenes autorizadas por entregar
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW des_v_entregas_pendientes AS
SELECT o.id_orden,
       o.id_solicitud,
       o.id_cliente,
       o.num_cuenta,
       o.monto,
       o.moneda,
       o.tipo_desembolso,
       o.fecha_generacion
FROM des_orden o
WHERE o.estado_orden = 'AUTORIZADA';

-- ---------------------------------------------------------------------
-- des_v_conciliacion_diaria: desembolsos entregados por dia
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW des_v_conciliacion_diaria AS
SELECT DATE(o.fecha_entrega) AS fecha,
       o.moneda,
       COUNT(*)              AS cantidad_ordenes,
       SUM(o.monto)          AS monto_total
FROM des_orden o
WHERE o.estado_orden = 'ENTREGADA'
GROUP BY DATE(o.fecha_entrega), o.moneda;

-- ---------------------------------------------------------------------
-- v_credito_resumen: resumen de credito con cliente y saldo
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_credito_resumen AS
SELECT cr.id_credito,
       cr.estado_credito,
       cr.moneda,
       cr.monto_aprobado,
       cr.saldo_capital,
       cr.dias_mora,
       CONCAT_WS(' ', c.nombres, c.apellido_paterno, c.apellido_materno) AS cliente,
       (SELECT COUNT(*) FROM cob_cuota q WHERE q.id_credito = cr.id_credito) AS total_cuotas,
       (SELECT COUNT(*) FROM cob_cuota q WHERE q.id_credito = cr.id_credito AND q.estado_cuota = 'PAGADA') AS cuotas_pagadas
FROM cob_credito cr
JOIN cliente c ON c.id_cliente = cr.id_cliente;

-- ---------------------------------------------------------------------
-- v_movimientos_cuenta: movimientos de cuenta con saldo
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_movimientos_cuenta AS
SELECT t.id_transaccion,
       t.uuid_transaccion,
       t.num_cuenta,
       t.tipo_operacion,
       t.tipo_movimiento,
       t.monto,
       t.moneda,
       t.saldo_posterior,
       t.comision,
       t.itf,
       t.estado_transaccion,
       t.fecha_valor,
       t.fecha_hora,
       cn.nombre AS canal
FROM cta_transaccion t
LEFT JOIN canal cn ON cn.id_canal = t.id_canal;
