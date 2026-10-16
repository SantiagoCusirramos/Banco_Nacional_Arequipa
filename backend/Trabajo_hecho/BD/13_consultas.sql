-- =====================================================================
-- BNA - Script 13: Consultas documentadas y CRUD por modulo
-- Motor: MySQL 8.0 / 8.4  |  InnoDB  |  utf8mb4
-- Version: v1.0.0   Fecha: 2026-10-15
-- C01-C11: consultas del modulo Tarjetas.
-- CRUD: ejemplos por modulo (INSERT/SELECT/UPDATE/DELETE).
-- =====================================================================
USE bna;
SET NAMES utf8mb4;

-- =====================================================================
-- MODULO TARJETAS - C01..C11
-- =====================================================================

-- C01: Tarjetas activas de un cliente con sus cuentas asociadas
SELECT t.id_tarjeta, t.ultimos4, t.tipo_tarjeta, tc.num_cuenta, tc.es_principal
FROM tar_tarjeta t
JOIN tar_tarjeta_cuenta tc ON tc.id_tarjeta = t.id_tarjeta
WHERE t.id_cliente = '0198b000-0000-7009-8000-000000000001' AND t.estado = 'ACTIVA';

-- C02: Detalle de una tarjeta y sus credenciales
SELECT t.id_tarjeta, t.ultimos4, t.estado, cr.tipo, cr.bloqueada, cr.intentos_fallidos
FROM tar_tarjeta t
LEFT JOIN tar_credencial cr ON cr.id_tarjeta = t.id_tarjeta
WHERE t.id_tarjeta = '0198b000-0000-700f-8000-000000000001';

-- C03: Intentos de autenticacion fallidos del dia
SELECT id_intento, id_tarjeta, tipo_credencial, id_canal, motivo_rechazo, fecha_hora
FROM tar_intento_autenticacion
WHERE resultado = 'FALLIDO' AND DATE(fecha_hora) = CURRENT_DATE()
ORDER BY fecha_hora DESC;

-- C04: Autorizaciones aprobadas del dia por tarjeta
SELECT id_tarjeta, COUNT(*) AS operaciones, SUM(monto) AS monto_total
FROM tar_autorizacion
WHERE estado = 'APROBADA' AND DATE(fecha_hora) = CURRENT_DATE()
GROUP BY id_tarjeta;

-- C05: Consumo diario por tarjeta y canal (usa la vista)
SELECT * FROM v_consumo_diario WHERE fecha = CURRENT_DATE();

-- C06: Tope restante por canal (usa la vista)
SELECT * FROM v_tope_restante_hoy;

-- C07: Autorizaciones rechazadas y su motivo
SELECT uuid_transaccion, id_tarjeta, monto, motivo_rechazo, fecha_hora
FROM tar_autorizacion
WHERE estado = 'RECHAZADA'
ORDER BY fecha_hora DESC;

-- C08: Resumen de tarjetas por estado
SELECT estado, COUNT(*) AS cantidad
FROM tar_tarjeta
GROUP BY estado;

-- C09: Credenciales en riesgo (usa la vista)
SELECT * FROM v_credenciales_en_riesgo;

-- C10: Tarjetas proximas a vencer en 30 dias
SELECT id_tarjeta, ultimos4, id_cliente, fecha_vencimiento
FROM tar_tarjeta
WHERE estado = 'ACTIVA'
  AND fecha_vencimiento BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY);

-- C11: Historial de estados de una tarjeta
SELECT estado_anterior, estado_nuevo, motivo, origen, fecha_hora
FROM tar_historial_estado
WHERE id_tarjeta = '0198b000-0000-700f-8000-000000000001'
ORDER BY fecha_hora;

-- =====================================================================
-- CRUD - MODULO CLIENTES / KYC
-- =====================================================================
-- Alta de cliente
INSERT INTO cliente (id_cliente, cod_tipo_documento, numero_documento, nombres, apellido_paterno,
                     apellido_materno, fecha_nacimiento, numero_celular, correo_electronico)
VALUES ('0198b000-0000-7009-8000-000000000001','DNI','70000001','Juan','Perez','Quispe','1990-05-10','959000001','juan.perez@example.com');

-- Consulta de cliente por documento
SELECT * FROM cliente WHERE cod_tipo_documento='DNI' AND numero_documento='70000001';

-- Actualizacion de contacto
UPDATE cliente SET numero_celular='959000099' WHERE numero_documento='70000001';

-- Baja logica (cambio de estado)
UPDATE cliente SET estado_cliente='INACTIVO' WHERE numero_documento='70000001';

-- =====================================================================
-- CRUD - MODULO CUENTAS
-- =====================================================================
-- Apertura de cuenta
INSERT INTO cuenta_ahorro (num_cuenta, moneda, regimen, id_agencia, id_producto_ahorro)
VALUES ('0011000001','PEN','LIBRE','0198b000-0000-7001-8000-000000000001','0198b000-0000-7004-8000-000000000001');

-- Vincular titular
INSERT INTO cliente_cuenta (num_cuenta, id_cliente, rol_titular)
SELECT '0011000001', id_cliente, 'TITULAR' FROM cliente WHERE numero_documento='70000001';

-- Registrar deposito
INSERT INTO cta_transaccion (id_transaccion, uuid_transaccion, num_cuenta, tipo_operacion, tipo_movimiento,
                             monto, moneda, id_canal, saldo_posterior, fecha_valor)
VALUES ('0198b000-0000-700e-8000-000000000002','0198b000-0000-700e-8000-000000000001','0011000001','DEPOSITO','C',500.00,'PEN','VEN',500.00,CURRENT_DATE());

-- Consultar saldos
SELECT num_cuenta, saldo_contable, saldo_disponible, saldo_retenido
FROM cuenta_ahorro WHERE num_cuenta='0011000001';

-- Movimientos de la cuenta (usa la vista)
SELECT * FROM v_movimientos_cuenta WHERE num_cuenta='0011000001' ORDER BY fecha_hora DESC;

-- =====================================================================
-- CRUD - MODULO SOLICITUD
-- =====================================================================
INSERT INTO sol_solicitud (id_solicitud, id_cliente, id_producto_credito, monto_solicitado, moneda,
                           plazo_meses, destino_credito)
SELECT '0198b000-0000-700a-8000-000000000001', id_cliente, '0198b000-0000-7005-8000-000000000001', 10000.00, 'PEN', 24, 'Capital de trabajo'
FROM cliente WHERE numero_documento='70000001';

SELECT s.id_solicitud, s.monto_solicitado, s.estado_solicitud, p.nombre AS producto
FROM sol_solicitud s JOIN producto_credito p ON p.id_producto_credito = s.id_producto_credito;

-- =====================================================================
-- CRUD - MODULO EVALUACION
-- =====================================================================
INSERT INTO eva_evaluacion (id_evaluacion, id_solicitud, puntaje, resultado, monto_maximo_sugerido, nivel_riesgo)
VALUES ('0198b000-0000-7012-8000-000000000001', '0198b000-0000-700a-8000-000000000001', 820, 'APROBADO', 10000.00, 'BAJO');

SELECT e.id_evaluacion, e.puntaje, e.resultado, e.nivel_riesgo, d.decision, d.monto_aprobado
FROM eva_evaluacion e
LEFT JOIN eva_decision_analista d ON d.id_evaluacion = e.id_evaluacion;

-- =====================================================================
-- CRUD - MODULO DESEMBOLSO
-- =====================================================================
INSERT INTO des_orden (id_orden, id_solicitud, id_cliente, num_cuenta, id_agencia, monto, moneda, tipo_desembolso)
SELECT '0198b000-0000-7013-8000-000000000001', id_solicitud, id_cliente, '0011000001', '0198b000-0000-7001-8000-000000000001', 10000.00, 'PEN', 'ABONO_CUENTA'
FROM sol_solicitud WHERE id_solicitud = '0198b000-0000-700a-8000-000000000001';

SELECT * FROM des_v_ordenes_inciertas;
SELECT * FROM des_v_entregas_pendientes;
SELECT * FROM des_v_conciliacion_diaria;

-- =====================================================================
-- CRUD - MODULO COBRANZA
-- =====================================================================
-- Alta de credito en cobranza
INSERT INTO cob_credito (id_credito, id_solicitud, id_cliente, num_cuenta_desembolso, monto_aprobado,
                         moneda, tasa_tea, plazo_meses, saldo_capital, fecha_desembolso)
SELECT '0198b000-0000-700b-8000-000000000001', id_solicitud, id_cliente, '0011000001', 10000.00, 'PEN', 0.2200, 24, 10000.00, CURRENT_DATE()
FROM sol_solicitud WHERE id_solicitud = '0198b000-0000-700a-8000-000000000001';

-- Cuota del credito (necesaria para aplicar el pago)
INSERT INTO cob_cuota (id_cuota_credito, id_credito, numero_cuota, fecha_vencimiento, capital, interes,
                       seguro, cuota_total, saldo_capital, monto_pagado)
VALUES ('0198b000-0000-700c-8000-000000000001', '0198b000-0000-700b-8000-000000000001', 1, DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY), 300.00, 230.00,
        20.00, 550.00, 9700.00, 0.00);

-- Resumen de credito (usa la vista)
SELECT * FROM v_credito_resumen;

-- Registrar pago y aplicarlo por componente (procedimiento)
INSERT INTO cob_pago (id_pago, id_credito, id_canal_pago, monto, moneda, num_operacion)
VALUES ('0198b000-0000-700d-8000-000000000001', '0198b000-0000-700b-8000-000000000001', '0198b000-0000-7008-8000-000000000001', 550.00, 'PEN', 'OP-000001');
CALL sp_aplicar_pago('0198b000-0000-700d-8000-000000000001', '0198b000-0000-700c-8000-000000000001', 300.00, 230.00, 20.00, 0.00);
