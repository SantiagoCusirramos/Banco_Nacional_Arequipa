-- Segunda línea de las reglas protegidas por privilegio: las mismas pruebas
-- de pruebas.sql que bna_app no puede ejecutar por falta del privilegio, ahora
-- con bna_admin_user (rol bna_admin), que sí lo tiene. El trigger o la
-- restricción debe rechazar la operación. Un ID solo pasa si pasan sus filas
-- de los dos usuarios.
-- F15 está solo aquí: marcar_tarjetas_vencidas la ejecuta el evento diario,
-- no la aplicación.
-- F11c no está: bna_admin sí puede vaciar una bitácora con TRUNCATE
-- (brecha G03, en run_tests.sh).

CALL prueba.rechaza('M11', 'MySQL', 'Comprobación 11 (bug 7)', 'El saldo disponible no supera al contable',
  JSON_ARRAY("UPDATE cuentas.cuenta_ahorro SET saldo_disponible = 9000 WHERE num_cuenta = 'CTA-PEN-2'"),
  'ck_cuenta_ahorro_1', 'declarativo');

CALL prueba.rechaza('F07', 'Tarjetas', 'Historial (RN-SEG-002)', 'El estado de la tarjeta solo cambia registrando el historial',
  JSON_ARRAY("UPDATE tarjetas.tarjeta SET estado_tarjeta = 'BLOQUEADA' WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')"),
  'RN-SEG-002', 'trigger');

CALL prueba.rechaza('F11a', 'Tarjetas', 'trg_intento_bu (RN-SEG-002)', 'La bitácora de intentos no se modifica',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'ATM-AQP-001', 'EXITOSO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'))",
    "UPDATE tarjetas.intento_autenticacion SET resultado = 'FALLIDO'"),
  'ERR-TAR-009', 'trigger');
CALL prueba.rechaza('F11b', 'Tarjetas', 'trg_historial_bd (RN-SEG-002)', 'El historial de estados no se borra',
  JSON_ARRAY("DELETE FROM tarjetas.historial_estado_tarjeta"),
  'ERR-TAR-009', 'trigger');
CALL prueba.rechaza('F11d', 'Cobranza', 'Bitácora de auditoría', 'La auditoría no se modifica',
  JSON_ARRAY("UPDATE creditos.evento_auditoria SET resultado = 'ALTERADO'"),
  'BNA-SOLO-INSERCION', 'trigger');
CALL prueba.rechaza('F11e', 'CORE', 'Asientos inmutables', 'Un asiento no se modifica',
  JSON_ARRAY("UPDATE core.detalle_asiento SET importe = importe + 1"),
  'BNA-SOLO-INSERCION', 'trigger');
CALL prueba.rechaza('F11f', 'Solicitud', 'Historial de la solicitud', 'El historial de la solicitud no se borra',
  JSON_ARRAY("DELETE FROM creditos.historial_estado_solicitud"),
  'BNA-SOLO-INSERCION', 'trigger');

CALL prueba.rechaza('F12k', 'Tarjetas', 'Operación única (RN-BUS-002)', 'Una autorización solo se vincula al movimiento de su misma operación',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000006'), 'RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')",
    "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 100, 'ATM', NULL, NULL, @m)",
    "UPDATE tarjetas.autorizacion SET uuid_transaccion = @m WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000006')"),
  'ck_autorizacion_3', 'declarativo');

CALL prueba.rechaza('F13', 'Tarjetas', 'trg_autorizacion_bd (RN-ATM-003)', 'Una autorización no se borra; se extorna',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')",
    "DELETE FROM tarjetas.autorizacion"),
  'ERR-TAR-009', 'trigger');

CALL prueba.verifica('F15', 'Tarjetas', 'ev_marcar_tarjetas_vencidas (RN-TAR-003)', 'marcar_tarjetas_vencidas() vence las tarjetas cuya fecha pasó',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
     VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f4'), 'tok-f4', '455788', '4444', '2020-01-01', '2021-01-31', 'ACTIVA', 'C002')",
    "CALL tarjetas.marcar_tarjetas_vencidas(NULL, @n)"),
  "SELECT @n = 1
        AND (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f4')) = 'VENCIDA'
        AND (SELECT origen FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f4')
              ORDER BY id_historial DESC LIMIT 1) = 'SISTEMA'
        AND (SELECT STATUS = 'ENABLED' AND INTERVAL_VALUE = '1' AND INTERVAL_FIELD = 'DAY' FROM information_schema.EVENTS
              WHERE EVENT_SCHEMA = 'tarjetas' AND EVENT_NAME = 'ev_marcar_tarjetas_vencidas')",
  '1 tarjeta; VENCIDA por SISTEMA; evento diario ENABLED',
  "SELECT CONCAT(@n, ' tarjeta; ',
       (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f4')), ' por ',
       (SELECT origen FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f4')
         ORDER BY id_historial DESC LIMIT 1), '; evento ',
       (SELECT IF(INTERVAL_VALUE = '1' AND INTERVAL_FIELD = 'DAY', 'diario ', 'no diario ') FROM information_schema.EVENTS
         WHERE EVENT_SCHEMA = 'tarjetas' AND EVENT_NAME = 'ev_marcar_tarjetas_vencidas'),
       (SELECT STATUS FROM information_schema.EVENTS WHERE EVENT_SCHEMA = 'tarjetas' AND EVENT_NAME = 'ev_marcar_tarjetas_vencidas'))",
  'evento');

CALL prueba.rechaza('F20', 'Cobranza', 'Aplicación de pagos', 'Una aplicación de pago no se modifica',
  JSON_ARRAY("CALL creditos.aplicar_pago(UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), @a)",
    "UPDATE creditos.aplicacion_pago SET monto_aplicado = 1"),
  'BNA-SOLO-INSERCION|BNA-PAGO', 'trigger');

CALL prueba.rechaza('F23', 'Cuentas', 'Movimiento inmutable', 'El importe de un movimiento no se modifica',
  JSON_ARRAY("UPDATE cuentas.movimiento SET monto = 1 WHERE num_cuenta = 'CTA-PEN-2'"),
  'BNA-MOVIMIENTO', 'trigger');

CALL prueba.rechaza('F32', 'CORE', 'Bitácoras (decisión del informe)', 'El identificador de una bitácora lo asigna la base',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (id_intento, tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES (999, 'PIN_ATM', 'ATM-AQP-001', 'EXITOSO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'))"),
  'BNA-IDENTIDAD', 'trigger');

CALL prueba.rechaza('R8', 'Regresión', 'Pruebas negativas del DDL', 'Borrar una moneda en uso',
  JSON_ARRAY("DELETE FROM core.moneda WHERE cod_moneda = 'PEN'"),
  'foreign key constraint fails', 'declarativo');
