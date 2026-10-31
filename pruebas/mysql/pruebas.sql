-- Pruebas de la base integrada en MySQL 8.4. Requiere arnes.sql y datos.sql.
-- Las ejecuta bna_app_user (rol bna_app), como la aplicación. Tienen los
-- mismos ID que las de la rama main (pruebas/postgres/pruebas.sql):
--   M  equivalentes de las 25 fallas reproducidas en la base unificada para
--      MySQL (bna_mysql_repro); el número es el de esa comprobación.
--   F  objetos portados o implementados (triggers, procedimientos, vistas,
--      índices).
--   R  pruebas negativas originales del informe (regresión).
-- El último argumento es el mecanismo que hace cumplir la regla en MySQL:
-- declarativo, trigger, procedimiento o privilegio. Las reglas protegidas
-- por privilegio se prueban otra vez con bna_admin_user (pruebas_admin.sql),
-- que tiene el privilegio y debe toparse con el trigger o la restricción.
-- Las pruebas que necesitan una confirmación real, dos sesiones o cambiar
-- la sesión (M20b, M20c, C01 a C03, G01 a G05) las ejecuta run_tests.sh.
-- Cada sentencia va entre comillas dobles dentro de JSON_ARRAY.

-- =====================================================================
-- M: fallas de la base unificada para MySQL
-- =====================================================================
CALL prueba.na('M01', 'MySQL', 'Comprobación 1 (bug 1)', 'El script de carga encuentra el archivo SQL',
  'N/A — prevenido por diseño: no hay script de carga con rutas; el DDL es un único archivo (sql/bna_core.sql) que se carga directamente, y su carga se prueba en L01.');

CALL prueba.verifica('M04', 'MySQL', 'Comprobación 4 (bug 3)', 'Un depósito actualiza el saldo de la cuenta',
  JSON_ARRAY("CALL prueba.movimiento('CTA-PEN-2', 'DEPOSITO', 500, 'VEN', NULL, NULL, @m)"),
  "SELECT saldo_contable = 5500 AND saldo_disponible = 5500 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2'",
  'saldo 5000.00 -> 5500.00',
  "SELECT CONCAT('saldo 5000.00 -> ', saldo_contable) FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2'",
  'trigger');

CALL prueba.verifica('M05', 'MySQL', 'Comprobación 5 (bug 4)', 'Pagar reduce la deuda del crédito',
  JSON_ARRAY("CALL creditos.aplicar_pago(UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), @a)"),
  "SELECT sum(saldo_pendiente) = 7200 FROM creditos.cuota WHERE id_calendario = UUID_TO_BIN('d0000000-0000-4000-8000-000000000001')",
  'deuda 10300.00 -> 7200.00',
  "SELECT CONCAT('deuda 10300.00 -> ', sum(saldo_pendiente)) FROM creditos.cuota WHERE id_calendario = UUID_TO_BIN('d0000000-0000-4000-8000-000000000001')",
  'trigger');

CALL prueba.na('M06', 'MySQL', 'Comprobación 6 (bug 2)', 'fn_uuid_v7() guarda la hora correcta',
  'N/A — no aplica: la función no se porta; los UUID son de versión 4 (core.uuid_v4() y el valor por omisión, hechos con RANDOM_BYTES), sin marca de tiempo.');
CALL prueba.na('M07', 'MySQL', 'Comprobación 7 (bug 2)', 'Los UUID v7 se ordenan por fecha de creación',
  'N/A — no aplica: por la misma razón que M06; el orden de las bitácoras lo da su identificador AUTO_INCREMENT y su marca de tiempo.');

CALL prueba.rechaza('M08', 'MySQL', 'Comprobación 8 (bug 7)', 'Un identificador debe ser un UUID válido',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
     VALUES ('c2', 'tok-x', '455788', '1111', '2026-01-01', '2030-01-01', 'ACTIVA', 'C002')"),
  'ck_tarjeta_id_tarjeta', 'declarativo');

CALL prueba.rechaza('M09a', 'MySQL', 'Comprobación 9 (bug 7)', 'La orden no abona en la cuenta de otro cliente',
  JSON_ARRAY("INSERT INTO creditos.orden_desembolso (codigo_orden, importe, estado_orden, idempotency_key, request_hash, usuario_preparacion,
       correlation_id, id_evaluacion, num_cuenta, id_canal)
     VALUES ('DES-T-1', 1000, 'PREPARADA', core.uuid_v4(), REPEAT('x', 64), 'u', core.uuid_v4(),
       UUID_TO_BIN('c0000000-0000-4000-8000-000000000002'), 'CTA-PEN-1', 'VEN')"),
  'BNA-CUENTA-DESTINO.*no pertenece', 'trigger');
CALL prueba.rechaza('M09b', 'MySQL', 'Comprobación 9 (bug 7)', 'La orden no abona en una cuenta de otra moneda',
  JSON_ARRAY("INSERT INTO creditos.orden_desembolso (codigo_orden, importe, estado_orden, idempotency_key, request_hash, usuario_preparacion,
       correlation_id, id_evaluacion, num_cuenta, id_canal)
     VALUES ('DES-T-2', 1000, 'PREPARADA', core.uuid_v4(), REPEAT('x', 64), 'u', core.uuid_v4(),
       UUID_TO_BIN('c0000000-0000-4000-8000-000000000001'), 'CTA-USD-1', 'VEN')"),
  'BNA-CUENTA-DESTINO.*USD', 'trigger');
CALL prueba.rechaza('M09c', 'MySQL', 'Comprobación 9 (bug 7)', 'La orden no supera el límite aprobado',
  JSON_ARRAY("INSERT INTO creditos.orden_desembolso (codigo_orden, importe, estado_orden, idempotency_key, request_hash, usuario_preparacion,
       correlation_id, id_evaluacion, num_cuenta, id_canal)
     VALUES ('DES-T-3', 99999, 'PREPARADA', core.uuid_v4(), REPEAT('x', 64), 'u', core.uuid_v4(),
       UUID_TO_BIN('c0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1', 'VEN')"),
  'BNA-IMPORTE', 'trigger');

CALL prueba.rechaza('M10a', 'MySQL', 'Comprobación 10 (bug 7)', 'Un retiro no deja el saldo en negativo',
  JSON_ARRAY("CALL prueba.movimiento('CTA-PEN-2', 'RETIRO', 6000, 'VEN', NULL, NULL, @m)"),
  'BNA-SALDO', 'trigger');
CALL prueba.rechaza('M10b', 'MySQL', 'Comprobación 10 (bug 7)', 'Un movimiento va en la moneda de su cuenta',
  JSON_ARRAY("CALL prueba.movimiento('CTA-PEN-2', 'DEPOSITO', 100, 'VEN', 'USD', NULL, @m)"),
  'BNA-MONEDA', 'trigger');

CALL prueba.rechaza('M11', 'MySQL', 'Comprobación 11 (bug 7)', 'El saldo disponible no supera al contable',
  JSON_ARRAY("UPDATE cuentas.cuenta_ahorro SET saldo_disponible = 9000 WHERE num_cuenta = 'CTA-PEN-2'"),
  'UPDATE command denied', 'privilegio');

CALL prueba.na('M12', 'MySQL', 'Comprobación 12 (bug 7)', 'El total de la cuota es la suma de sus partes',
  'N/A — prevenido por diseño: CUOTA no guarda el total; es un dato derivado de capital, interés y otros conceptos, eliminado en la normalización.');

CALL prueba.rechaza('M13a', 'MySQL', 'Comprobación 13 (bug 4)', 'No se aplica más de lo pagado',
  JSON_ARRAY("INSERT INTO creditos.aplicacion_pago VALUES (UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'), 3, 3500)"),
  'BNA-PAGO.*se aplicarían', 'trigger');
CALL prueba.rechaza('M13b', 'MySQL', 'Comprobación 13 (bug 4)', 'No se aplica más del saldo de la cuota',
  JSON_ARRAY("INSERT INTO creditos.aplicacion_pago VALUES (UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'), 1, 3101)"),
  'BNA-PAGO.*solo debe', 'trigger');

CALL prueba.rechaza('M14a', 'MySQL', 'Comprobación 14 (bug 7)', 'Una orden genera un solo crédito',
  JSON_ARRAY("INSERT INTO creditos.credito VALUES ('CR-0002', 'AL_DIA', UUID_TO_BIN('e0000000-0000-4000-8000-000000000001'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'))"),
  'uk_credito', 'declarativo');
CALL prueba.rechaza('M14b', 'MySQL', 'Comprobación 14 (bug 7)', 'Una solicitud tiene una sola orden confirmada, aun en otra ronda',
  JSON_ARRAY("INSERT INTO creditos.evaluacion (id_evaluacion, ronda, score_calculado, limite_aprobado, id_solicitud, id_consulta, id_regla)
     VALUES (UUID_TO_BIN('c0000000-0000-4000-8000-0000000000e2'), 2, 700, 10000, UUID_TO_BIN('b0000000-0000-4000-8000-000000000001'),
       UUID_TO_BIN('b1000000-0000-4000-8000-000000000001'), 'R-A')",
    "INSERT INTO creditos.orden_desembolso (codigo_orden, importe, estado_orden, idempotency_key, request_hash, usuario_preparacion,
       correlation_id, id_evaluacion, num_cuenta, id_canal)
     VALUES ('DES-T-4', 5000, 'CONFIRMADA', core.uuid_v4(), REPEAT('x', 64), 'u', core.uuid_v4(),
       UUID_TO_BIN('c0000000-0000-4000-8000-0000000000e2'), 'CTA-PEN-1', 'VEN')"),
  'BNA-ORDEN-UNICA', 'trigger');

CALL prueba.rechaza('M15a', 'MySQL', 'Comprobación 15 (bug 7)', 'Los últimos cuatro dígitos son numéricos',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
     VALUES ('tok-x', '455788', 'ABCD', '2026-01-01', '2030-01-01', 'ACTIVA', 'C002')"),
  'ck_tarjeta_2', 'declarativo');
CALL prueba.rechaza('M15b', 'MySQL', 'Comprobación 15 (bug 7)', 'La tarjeta vence después de emitirse',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
     VALUES ('tok-x', '455788', '1111', '2026-01-01', '2020-01-01', 'ACTIVA', 'C002')"),
  'ck_tarjeta_1', 'declarativo');

CALL prueba.rechaza('M16', 'MySQL', 'Comprobación 16 (bug 7)', 'La matriz no es una credencial de la tarjeta',
  JSON_ARRAY("INSERT INTO tarjetas.credencial (id_tarjeta, tipo_credencial, hash_credencial, sal)
     VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'TOKEN_MATRIZ', REPEAT('a', 64), REPEAT('b', 32))"),
  'ck_credencial_1', 'declarativo');

CALL prueba.rechaza('M17', 'MySQL', 'Comprobación 17 (bug 7)', 'La coordenada pedida existe en la matriz',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, coord_fila, coord_columna, id_canal, resultado, id_tarjeta)
     VALUES ('TOKEN_MATRIZ', 'Z', 9, 'HB', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  'ck_intento_autenticacion_1', 'declarativo');

CALL prueba.rechaza('M18', 'MySQL', 'Comprobación 18 (bug 7)', 'Una referencia apunta a un registro real',
  JSON_ARRAY("INSERT INTO creditos.evaluacion (ronda, score_calculado, limite_aprobado, id_solicitud, id_consulta, id_regla)
     VALUES (1, 700, 1000, UUID_TO_BIN('b0000000-0000-4000-8000-0000000000ff'), UUID_TO_BIN('b1000000-0000-4000-8000-000000000001'), 'R-A')"),
  'foreign key constraint fails', 'declarativo');

CALL prueba.rechaza('M19', 'MySQL', 'Comprobación 19', 'La auditoría solo registra eventos sobre registros reales',
  JSON_ARRAY("INSERT INTO creditos.evento_auditoria (modulo_emisor, id_entidad, accion, actor, correlation_id)
     VALUES (13, 'tabla_que_no_existe', 'x', 'y', core.uuid_v4())"),
  'fk_evento_auditoria_2', 'declarativo');

-- M20a: la aplicación no puede insertar el asiento directamente, y por
-- core.registrar_asiento el asiento descuadrado se rechaza.
CALL prueba.rechaza('M20a', 'MySQL', 'Comprobación 20 (bug 7)', 'Un asiento descuadrado se rechaza al confirmar',
  JSON_ARRAY("INSERT INTO core.asiento_contable (id_asiento, numero_asiento, fecha_contable, fecha_valor, glosa, moneda, correlation_id)
     VALUES (UUID_TO_BIN('9a000000-0000-4000-8000-000000000001'), 'T-DESC', CURRENT_DATE, CURRENT_DATE, 'Solo debe', 'PEN', core.uuid_v4())"),
  'INSERT command denied', 'privilegio');
CALL prueba.rechaza('M20a', 'MySQL', 'Comprobación 20 (bug 7)', 'Un asiento descuadrado se rechaza al confirmar',
  JSON_ARRAY("CALL core.registrar_asiento(UUID_TO_BIN('9a000000-0000-4000-8000-000000000001'), 'T-DESC', CURRENT_DATE, CURRENT_DATE,
       'Solo debe', 'PEN', core.uuid_v4(), NULL, JSON_ARRAY(JSON_OBJECT('partida', 'DEBE', 'importe', 100, 'cuenta', '1101')), @a)"),
  'BNA-PARTIDA-DOBLE', 'procedimiento');

CALL prueba.na('M21', 'MySQL', 'Comprobación 21', 'Una reversión la autoriza otra persona',
  'N/A — prevenido por diseño: el modelo no guarda usuarios ni empleados; el solicitante y la autorización son identificadores que emite Seguridad, que es quien controla a las personas.');

CALL prueba.verifica('M22', 'MySQL', 'Comprobación 22 (bug 5)', 'Un retiro se cuenta una sola vez en el tope y en el saldo',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, codigo_respuesta,
       id_terminal, id_tarjeta, num_cuenta)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000001'), 'RETIRO', 600, 'AUTORIZADA', '00', 'ATM-AQP-001',
       UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2')",
    "CALL prueba.movimiento('CTA-PEN-2', 'RETIRO', 600, 'ATM', NULL, UUID_TO_BIN('9b000000-0000-4000-8000-000000000001'), @m)",
    "UPDATE tarjetas.autorizacion SET estado_autorizacion = 'DISPENSADA'
      WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000001')"),
  "SELECT cd.monto_acumulado = 600 AND cu.saldo_contable = 4400 AND cu.saldo_disponible = 4400
        AND a.uuid_transaccion = a.uuid_autorizacion
       FROM core.consumo_diario cd
       JOIN cuentas.cuenta_ahorro cu ON cu.num_cuenta = cd.num_cuenta
       JOIN tarjetas.autorizacion a ON a.uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000001')
      WHERE cd.num_cuenta = 'CTA-PEN-2' AND cd.id_canal = 'ATM'",
  'consumido 600.00; contable 4400.00; disponible 4400.00; movimiento vinculado',
  "SELECT CONCAT('consumido ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-2' AND id_canal = 'ATM'), '0'),
       '; contable ', cu.saldo_contable, '; disponible ', cu.saldo_disponible, '; movimiento ',
       IF(a.uuid_transaccion = a.uuid_autorizacion, 'vinculado', 'sin vincular'))
       FROM cuentas.cuenta_ahorro cu, tarjetas.autorizacion a
      WHERE cu.num_cuenta = 'CTA-PEN-2' AND a.uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000001')",
  'trigger');

CALL prueba.rechaza('M23', 'MySQL', 'Comprobación 23 (bug 5)', 'Una autorización aprobada después también respeta el tope',
  JSON_ARRAY("CALL prueba.movimiento('CTA-PEN-2', 'RETIRO', 600, 'ATM', NULL, NULL, @m)",
    "INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000002'), 'RETIRO', 1000, 'INICIADA', 'ATM-AQP-001',
       UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2')",
    "UPDATE tarjetas.autorizacion SET estado_autorizacion = 'AUTORIZADA'
      WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000002')"),
  'ERR-TAR-007', 'trigger');

CALL prueba.rechaza('M24a', 'MySQL', 'Comprobación 24 (bug 5)', 'Se respeta el tope diario del cajero (movimiento)',
  JSON_ARRAY("CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 1600, 'ATM', NULL, NULL, @m)"),
  'RN-TOP-001', 'trigger');
CALL prueba.rechaza('M24b', 'MySQL', 'Comprobación 24 (bug 5)', 'Se respeta el tope diario del cajero (autorización)',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 1600, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')"),
  'ERR-TAR-007', 'trigger');

CALL prueba.rechaza('M24c', 'MySQL', 'Comprobación 24 (bug 5)', 'Dos autorizaciones aprobadas sin movimiento no superan juntas el tope',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 1000, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')",
    "INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 1000, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')"),
  'ERR-TAR-007', 'trigger');

CALL prueba.verifica('M25', 'MySQL', 'Comprobación 25 (bug 5)', 'v_tope_restante_hoy muestra el tope de cada tarjeta y cuenta',
  JSON_ARRAY("CALL prueba.movimiento('CTA-PEN-2', 'RETIRO', 600, 'ATM', NULL, NULL, @m)"),
  "SELECT (SELECT disponible_hoy FROM tarjetas.v_tope_restante_hoy WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')
              AND num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM') = 1500
        AND (SELECT disponible_hoy FROM tarjetas.v_tope_restante_hoy WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')
              AND num_cuenta = 'CTA-PEN-2' AND id_canal = 'ATM') = 900",
  'T1 1500.00; T2 900.00',
  "SELECT GROUP_CONCAT(CONCAT(LEFT(BIN_TO_UUID(id_tarjeta), 1), RIGHT(BIN_TO_UUID(id_tarjeta), 1), ' ', disponible_hoy)
            ORDER BY id_tarjeta SEPARATOR '; ')
       FROM tarjetas.v_tope_restante_hoy WHERE id_canal = 'ATM' AND moneda = 'PEN' AND num_cuenta IN ('CTA-PEN-1', 'CTA-PEN-2')",
  'trigger');

CALL prueba.verifica('M26', 'MySQL', 'Comprobación 26 (bug 6)', 'Al bloquear una tarjeta se guarda el motivo',
  JSON_ARRAY("CALL tarjetas.bloquear_tarjeta(UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'Robo reportado', 'CLIENTE', @h)"),
  "SELECT motivo = 'Robo reportado' AND origen = 'CLIENTE' FROM tarjetas.historial_estado_tarjeta
      WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002') ORDER BY id_historial DESC LIMIT 1",
  'Robo reportado / CLIENTE',
  "SELECT CONCAT(motivo, ' / ', origen) FROM tarjetas.historial_estado_tarjeta
      WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002') ORDER BY id_historial DESC LIMIT 1",
  'trigger');

CALL prueba.na('M28', 'MySQL', 'Comprobación 28', 'El diagrama muestra todas las relaciones',
  'N/A — prevenido por diseño: los diagramas, las tablas del informe y el DDL se generan del mismo modelo (modelo/modelo_bna.py), de modo que no pueden divergir.');

-- =====================================================================
-- F: objetos portados e implementados
-- =====================================================================
CALL prueba.rechaza('F01', 'Tarjetas', 'trg_tarjeta_bi (RF-TAR-005)', 'Solo se emite tarjeta a un cliente ACTIVO',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
     VALUES ('tok-x', '455788', '1111', '2026-01-01', '2030-01-01', 'ACTIVA', 'C004')"),
  'ERR-TAR-001', 'trigger');
CALL prueba.verifica('F02', 'Tarjetas', 'trg_tarjeta_ai (RN-SEG-002)', 'La emisión queda en el historial y en la bandeja hacia Seguridad',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
     VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f2'), 'tok-f2', '455788', '2222', '2026-01-01', '2030-01-01', 'PENDIENTE_ACTIVACION', 'C002')"),
  "SELECT (SELECT count(*) FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f2')) = 1
        AND (SELECT count(*) FROM tarjetas.evento_salida WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f2')
              AND tipo_evento = 'EMISION_TARJETA') = 1",
  'historial 1; evento EMISION_TARJETA 1',
  "SELECT CONCAT('historial ', (SELECT count(*) FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f2')),
       '; evento EMISION_TARJETA ', (SELECT count(*) FROM tarjetas.evento_salida
          WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f2') AND tipo_evento = 'EMISION_TARJETA'))",
  'trigger');
CALL prueba.rechaza('F03', 'Tarjetas', 'trg_tarjeta_bu (RN-TAR-003)', 'Una tarjeta CANCELADA no cambia de estado',
  JSON_ARRAY("INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, origen, id_tarjeta) VALUES ('CANCELADA', 'OPERADOR', UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'))",
    "INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, origen, id_tarjeta) VALUES ('ACTIVA', 'OPERADOR', UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'))"),
  'ERR-TAR-002', 'trigger');
CALL prueba.rechaza('F04', 'Tarjetas', 'trg_tarjeta_bu (RN-TAR-003)', 'Una tarjeta VENCIDA solo se cancela',
  JSON_ARRAY("INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, origen, id_tarjeta) VALUES ('VENCIDA', 'SISTEMA', UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'))",
    "INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, origen, id_tarjeta) VALUES ('ACTIVA', 'OPERADOR', UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'))"),
  'ERR-TAR-002', 'trigger');
CALL prueba.rechaza('F05', 'Tarjetas', 'trg_tarjeta_bu (RN-TAR-004)', 'El cliente no puede desbloquear su tarjeta',
  JSON_ARRAY("CALL tarjetas.bloquear_tarjeta(UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'Sospecha de fraude', 'SEGURIDAD', @h)",
    "INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, origen, id_tarjeta) VALUES ('ACTIVA', 'CLIENTE', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  'ERR-TAR-004', 'trigger');
-- F06: bna_app no actualiza el contador de intentos; los dos intentos
-- fallidos se registran como intentos (en la rama main, con un UPDATE).
CALL prueba.verifica('F06', 'Tarjetas', 'trg_tarjeta_au (RN-TAR-004)', 'El desbloqueo por un operador reinicia los intentos',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')),
            ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))",
    "CALL tarjetas.bloquear_tarjeta(UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'Sospecha de fraude', 'SEGURIDAD', @h)",
    "INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
     VALUES ('ACTIVA', 'Desbloqueo en ventanilla con huella dactilar', 'OPERADOR', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  "SELECT t.estado_tarjeta = 'ACTIVA' AND c.intentos_fallidos = 0 FROM tarjetas.tarjeta t
       JOIN tarjetas.credencial c ON c.id_tarjeta = t.id_tarjeta AND c.tipo_credencial = 'PIN_ATM'
      WHERE t.id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')",
  'ACTIVA; intentos 0',
  "SELECT CONCAT(t.estado_tarjeta, '; intentos ', c.intentos_fallidos) FROM tarjetas.tarjeta t
       JOIN tarjetas.credencial c ON c.id_tarjeta = t.id_tarjeta AND c.tipo_credencial = 'PIN_ATM'
      WHERE t.id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')",
  'trigger');
CALL prueba.rechaza('F07', 'Tarjetas', 'Historial (RN-SEG-002)', 'El estado de la tarjeta solo cambia registrando el historial',
  JSON_ARRAY("UPDATE tarjetas.tarjeta SET estado_tarjeta = 'BLOQUEADA' WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')"),
  'UPDATE command denied', 'privilegio');
CALL prueba.verifica('F08', 'Tarjetas', 'trg_intento_ai (RN-TAR-004)', 'El tercer intento fallido bloquea la tarjeta y avisa a Seguridad',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')),
            ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')),
            ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'))"),
  "SELECT (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')) = 'BLOQUEADA'
        AND (SELECT count(*) FROM tarjetas.evento_salida WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')
              AND tipo_evento = 'BLOQUEO_POR_INTENTOS') = 1",
  'BLOQUEADA; evento BLOQUEO_POR_INTENTOS 1',
  "SELECT CONCAT((SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')),
       '; evento BLOQUEO_POR_INTENTOS ', (SELECT count(*) FROM tarjetas.evento_salida
          WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002') AND tipo_evento = 'BLOQUEO_POR_INTENTOS'))",
  'trigger');
CALL prueba.verifica('F09', 'Tarjetas', 'trg_intento_ai (RN-TAR-004)', 'Un intento exitoso reinicia el contador',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')),
            ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')),
            ('PIN_ATM', 'ATM-AQP-001', 'EXITOSO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'))"),
  "SELECT intentos_fallidos = 0 FROM tarjetas.credencial WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')",
  'intentos 0',
  "SELECT CONCAT('intentos ', intentos_fallidos) FROM tarjetas.credencial WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002')",
  'trigger');
CALL prueba.verifica('F10', 'Tarjetas', 'trg_intento_ai (RN-TAR-004)', 'El tercer fallo de la matriz la bloquea junto con la tarjeta',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, coord_fila, coord_columna, id_canal, resultado, id_tarjeta)
     VALUES ('TOKEN_MATRIZ', 'B', 4, 'HB', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')),
            ('TOKEN_MATRIZ', 'B', 4, 'HB', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')),
            ('TOKEN_MATRIZ', 'B', 4, 'HB', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  "SELECT (SELECT estado_matriz FROM tarjetas.matriz_token WHERE numero_serie = 'MTZ-0001') = 'BLOQUEADA'
        AND (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')) = 'BLOQUEADA'",
  'matriz BLOQUEADA; tarjeta BLOQUEADA',
  "SELECT CONCAT('matriz ', (SELECT estado_matriz FROM tarjetas.matriz_token WHERE numero_serie = 'MTZ-0001'),
       '; tarjeta ', (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')))",
  'trigger');

CALL prueba.rechaza('F11a', 'Tarjetas', 'trg_intento_bu (RN-SEG-002)', 'La bitácora de intentos no se modifica',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'ATM-AQP-001', 'EXITOSO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'))",
    "UPDATE tarjetas.intento_autenticacion SET resultado = 'FALLIDO'"),
  'UPDATE command denied', 'privilegio');
CALL prueba.rechaza('F11b', 'Tarjetas', 'trg_historial_bd (RN-SEG-002)', 'El historial de estados no se borra',
  JSON_ARRAY("DELETE FROM tarjetas.historial_estado_tarjeta"),
  'DELETE command denied', 'privilegio');
-- F11c: TRUNCATE exige DROP, que bna_app no tiene. bna_admin sí lo tiene y
-- puede vaciar la bitácora: brecha G03 (run_tests.sh).
CALL prueba.rechaza('F11c', 'Tarjetas', 'trg_historial (RN-SEG-002)', 'El historial no se vacía con TRUNCATE',
  JSON_ARRAY("TRUNCATE TABLE tarjetas.historial_estado_tarjeta"),
  'DROP command denied', 'privilegio');
CALL prueba.rechaza('F11d', 'Cobranza', 'Bitácora de auditoría', 'La auditoría no se modifica',
  JSON_ARRAY("UPDATE creditos.evento_auditoria SET resultado = 'ALTERADO'"),
  'UPDATE command denied', 'privilegio');
CALL prueba.rechaza('F11e', 'CORE', 'Asientos inmutables', 'Un asiento no se modifica',
  JSON_ARRAY("UPDATE core.detalle_asiento SET importe = importe + 1"),
  'UPDATE command denied', 'privilegio');
CALL prueba.rechaza('F11f', 'Solicitud', 'Historial de la solicitud', 'El historial de la solicitud no se borra',
  JSON_ARRAY("DELETE FROM creditos.historial_estado_solicitud"),
  'DELETE command denied', 'privilegio');

CALL prueba.rechaza('F12a', 'Tarjetas', 'trg_autorizacion_bi (RN-TAR-003)', 'No se autoriza con una tarjeta bloqueada',
  JSON_ARRAY("CALL tarjetas.bloquear_tarjeta(UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'Pérdida', 'CLIENTE', @h)",
    "INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')"),
  'ERR-TAR-003.*no es operativa', 'trigger');
CALL prueba.rechaza('F12b', 'Tarjetas', 'trg_autorizacion_bi (RN-TAR-003)', 'No se autoriza con una tarjeta vencida',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
     VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f3'), 'tok-f3', '455788', '3333', '2020-01-01', '2021-01-31', 'ACTIVA', 'C002')",
    "INSERT INTO tarjetas.tarjeta_cuenta (id_tarjeta, num_cuenta) VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f3'), 'CTA-PEN-2')",
    "INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-0000000000f3'), 'CTA-PEN-2')"),
  'ERR-TAR-003.*venció', 'trigger');
CALL prueba.rechaza('F12c', 'Tarjetas', 'trg_autorizacion_bi (RN-ATM-005)', 'El cajero no opera una cuenta mancomunada conjunta',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-CONJ')"),
  'ERR-TAR-008', 'trigger');
CALL prueba.rechaza('F12d', 'Tarjetas', 'trg_autorizacion_bi (RN-BD-002)', 'La Billetera Digital no opera en dólares',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_canal, id_tarjeta, num_cuenta)
     VALUES ('FONDEO_BILLETERA', 100, 'AUTORIZADA', 'BD', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-USD-1')"),
  'ERR-TAR-006', 'trigger');
CALL prueba.rechaza('F12e', 'Tarjetas', 'trg_autorizacion_bi', 'No se autoriza en una terminal inactiva',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-OFF', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')"),
  'ERR-TAR-006.*terminal', 'trigger');
CALL prueba.rechaza('F12f', 'Tarjetas', 'sp_validar_reglas_autorizacion', 'No se autoriza más que el saldo disponible',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_canal, id_tarjeta, num_cuenta)
     VALUES ('TRANSFERENCIA_ENVIADA', 8000, 'AUTORIZADA', 'HB', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2')"),
  'BNA-SALDO', 'trigger');
CALL prueba.rechaza('F12g', 'Tarjetas', 'trg_autorizacion_bu (RN-ATM-007)', 'Una autorización rechazada no pasa a autorizada',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000003'), 'RETIRO', 100, 'RECHAZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')",
    "UPDATE tarjetas.autorizacion SET estado_autorizacion = 'AUTORIZADA' WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000003')"),
  'RN-ATM-007', 'trigger');
CALL prueba.verifica('F12h', 'Tarjetas', 'trg_autorizacion_bi (C06)', 'Una autorización válida se registra',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, codigo_respuesta, id_terminal, id_tarjeta, num_cuenta)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000004'), 'RETIRO', 200, 'AUTORIZADA', '00', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')"),
  "SELECT EXISTS (SELECT 1 FROM tarjetas.autorizacion WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000004'))",
  'registrada',
  "SELECT IF(EXISTS (SELECT 1 FROM tarjetas.autorizacion WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000004')),
             'registrada', 'no registrada')",
  'trigger');
CALL prueba.rechaza('F12i', 'Tarjetas', 'sp_validar_reglas_autorizacion', 'Dos autorizaciones aprobadas sin movimiento no superan juntas el saldo',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_canal, id_tarjeta, num_cuenta)
     VALUES ('TRANSFERENCIA_ENVIADA', 3000, 'AUTORIZADA', 'HB', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2')",
    "INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_canal, id_tarjeta, num_cuenta)
     VALUES ('TRANSFERENCIA_ENVIADA', 3000, 'AUTORIZADA', 'HB', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2')"),
  'BNA-SALDO', 'trigger');
CALL prueba.verifica('F12j', 'Tarjetas', 'trg_autorizacion_bu (C07)', 'Extornar una autorización sin movimiento libera el tope y el saldo',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000005'), 'RETIRO', 1000, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')",
    "UPDATE tarjetas.autorizacion SET estado_autorizacion = 'EXTORNADA', codigo_respuesta = 'EXT'
      WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000005')"),
  "SELECT coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'), 0) = 0
        AND (SELECT saldo_disponible FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = 15000",
  'consumido 0.00; disponible 15000.00',
  "SELECT CONCAT('consumido ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'), '0.00'),
       '; disponible ', (SELECT saldo_disponible FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1'))",
  'trigger');
-- F12k: bna_app no escribe uuid_transaccion (lo hace el trigger del
-- movimiento); bna_admin sí y se topa con el CHECK (pruebas_admin.sql).
CALL prueba.rechaza('F12k', 'Tarjetas', 'Operación única (RN-BUS-002)', 'Una autorización solo se vincula al movimiento de su misma operación',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000006'), 'RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')",
    "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 100, 'ATM', NULL, NULL, @m)",
    "UPDATE tarjetas.autorizacion SET uuid_transaccion = @m WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000006')"),
  'UPDATE command denied', 'privilegio');
-- F12l a F12n: la autorización se aprueba un día (ayer, en la fecha de
-- negocio de Lima) y su movimiento o su extorno llegan al día siguiente.
CALL prueba.verifica('F12l', 'Tarjetas', 'Tope diario (RN-TOP-001)', 'Una autorización de ayer contabilizada hoy cuenta para el tope de ayer, no para el de hoy',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta, fecha_hora)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000007'), 'RETIRO', 1000, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1', UTC_TIMESTAMP(6) - INTERVAL 1 DAY)",
    "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 1000, 'ATM', NULL, UUID_TO_BIN('9b000000-0000-4000-8000-000000000007'), @m)",
    "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 1500, 'ATM', NULL, NULL, @m)"),
  "SELECT (SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6) - INTERVAL 1 DAY)) = 1000
        AND (SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6))) = 1500
        AND (SELECT uuid_transaccion IS NOT NULL FROM tarjetas.autorizacion WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000007'))
        AND (SELECT saldo_contable = 12500 AND saldo_disponible = 12500 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1')",
  'ayer 1000.00; hoy 1500.00; vinculada; contable 12500.00; disponible 12500.00',
  "SELECT CONCAT('ayer ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6) - INTERVAL 1 DAY)), '0.00'),
       '; hoy ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6))), '0.00'),
       IF((SELECT uuid_transaccion IS NOT NULL FROM tarjetas.autorizacion WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000007')),
          '; vinculada', '; sin vincular'),
       (SELECT CONCAT('; contable ', saldo_contable, '; disponible ', saldo_disponible) FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1'))",
  'trigger');
CALL prueba.verifica('F12m', 'Tarjetas', 'Extorno (Tarjetas, C07)', 'El extorno hoy del movimiento de una autorización de ayer libera el tope de ayer, no el de hoy',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta, fecha_hora)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000008'), 'RETIRO', 1000, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1', UTC_TIMESTAMP(6) - INTERVAL 1 DAY)",
    "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 1000, 'ATM', NULL, UUID_TO_BIN('9b000000-0000-4000-8000-000000000008'), @m)",
    "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 400, 'ATM', NULL, NULL, @m)",
    "UPDATE cuentas.movimiento SET estado_transaccion = 'EXTORNADO' WHERE uuid_transaccion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000008')"),
  "SELECT (SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6) - INTERVAL 1 DAY)) = 0
        AND (SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6))) = 400",
  'ayer 0.00; hoy 400.00',
  "SELECT CONCAT('ayer ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6) - INTERVAL 1 DAY)), '0.00'),
       '; hoy ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6))), '0.00'))",
  'trigger');
CALL prueba.verifica('F12n', 'Tarjetas', 'trg_autorizacion_bu (C07)', 'El extorno hoy de una autorización de ayer sin movimiento libera el tope de ayer y el saldo',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (uuid_autorizacion, tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta, fecha_hora)
     VALUES (UUID_TO_BIN('9b000000-0000-4000-8000-000000000009'), 'RETIRO', 1000, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1', UTC_TIMESTAMP(6) - INTERVAL 1 DAY)",
    "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 400, 'ATM', NULL, NULL, @m)",
    "UPDATE tarjetas.autorizacion SET estado_autorizacion = 'EXTORNADA', codigo_respuesta = 'EXT'
      WHERE uuid_autorizacion = UUID_TO_BIN('9b000000-0000-4000-8000-000000000009')"),
  "SELECT (SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6) - INTERVAL 1 DAY)) = 0
        AND (SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6))) = 400
        AND (SELECT saldo_disponible FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = 14600",
  'ayer 0.00; hoy 400.00; disponible 14600.00',
  "SELECT CONCAT('ayer ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6) - INTERVAL 1 DAY)), '0.00'),
       '; hoy ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'
              AND fecha_corte = core.fn_fecha_negocio(UTC_TIMESTAMP(6))), '0.00'),
       '; disponible ', (SELECT saldo_disponible FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1'))",
  'trigger');
CALL prueba.rechaza('F13', 'Tarjetas', 'trg_autorizacion_bd (RN-ATM-003)', 'Una autorización no se borra; se extorna',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 100, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')",
    "DELETE FROM tarjetas.autorizacion"),
  'DELETE command denied', 'privilegio');

CALL prueba.verifica('F14a', 'Tarjetas', 'trg_cliente_ref_au (INT-T07)', 'Si Clientes bloquea al cliente, se bloquean sus tarjetas',
  JSON_ARRAY("UPDATE clientes.cliente SET estado_cliente = 'BLOQUEADO' WHERE cod_cliente = 'C002'"),
  "SELECT t.estado_tarjeta = 'BLOQUEADA' AND h.origen = 'MODULO_CLIENTES' FROM tarjetas.tarjeta t
       JOIN tarjetas.historial_estado_tarjeta h ON h.id_tarjeta = t.id_tarjeta
      WHERE t.id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002') ORDER BY h.id_historial DESC LIMIT 1",
  'BLOQUEADA por MODULO_CLIENTES',
  "SELECT CONCAT(t.estado_tarjeta, ' por ', h.origen) FROM tarjetas.tarjeta t
       JOIN tarjetas.historial_estado_tarjeta h ON h.id_tarjeta = t.id_tarjeta
      WHERE t.id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000002') ORDER BY h.id_historial DESC LIMIT 1",
  'trigger');
CALL prueba.verifica('F14b', 'Tarjetas', 'trg_cliente_ref_au (INT-T07)', 'Si Clientes da de baja al cliente, se cancelan sus tarjetas',
  JSON_ARRAY("UPDATE clientes.cliente SET estado_cliente = 'BAJA' WHERE cod_cliente = 'C003'"),
  "SELECT estado_tarjeta = 'CANCELADA' FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003')",
  'CANCELADA',
  "SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003')",
  'trigger');
-- F15: marcar_tarjetas_vencidas lo ejecuta el evento diario, no la
-- aplicación; la prueba la ejecuta bna_admin_user (pruebas_admin.sql).

CALL prueba.rechaza('F16a', 'Cobranza', 'Crédito (decisión I15)', 'El crédito nace de una orden CONFIRMADA',
  JSON_ARRAY("INSERT INTO creditos.credito VALUES ('CR-T1', 'AL_DIA', UUID_TO_BIN('e0000000-0000-4000-8000-000000000002'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000002'))"),
  'BNA-CREDITO.*CONFIRMADA', 'trigger');
CALL prueba.rechaza('F16b', 'Cobranza', 'Crédito (decisión I15)', 'El calendario del crédito es de la solicitud de su orden',
  JSON_ARRAY("INSERT INTO creditos.credito VALUES ('CR-T2', 'AL_DIA', UUID_TO_BIN('e0000000-0000-4000-8000-000000000001'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000002'))"),
  'BNA-CREDITO.*no pertenece', 'trigger');
CALL prueba.rechaza('F16c', 'Cobranza', 'Crédito (Solicitud)', 'El crédito usa el calendario OFICIAL',
  JSON_ARRAY("INSERT INTO creditos.credito VALUES ('CR-T3', 'AL_DIA', UUID_TO_BIN('e0000000-0000-4000-8000-000000000001'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000000'))"),
  'BNA-CREDITO.*OFICIAL', 'trigger');
CALL prueba.rechaza('F17a', 'Cobranza', 'Aplicación de pagos', 'Un pago no se aplica a cuotas de otro crédito',
  JSON_ARRAY("INSERT INTO creditos.aplicacion_pago VALUES (UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000002'), 1, 100)"),
  'BNA-PAGO.*no pertenece', 'trigger');
CALL prueba.rechaza('F17b', 'Cobranza', 'Aplicación de pagos', 'Solo se aplica un pago CONFIRMADO',
  JSON_ARRAY("INSERT INTO creditos.pago (id_pago, monto_pago, referencia_transaccion, estado_confirmacion, cod_credito, id_canal)
     VALUES (UUID_TO_BIN('f0000000-0000-4000-8000-0000000000f1'), 100, 'OP-T1', 'PENDIENTE', 'CR-0001', 'VEN')",
    "INSERT INTO creditos.aplicacion_pago VALUES (UUID_TO_BIN('f0000000-0000-4000-8000-0000000000f1'), UUID_TO_BIN('d0000000-0000-4000-8000-000000000001'), 1, 100)"),
  'BNA-PAGO.*CONFIRMADO', 'trigger');
CALL prueba.verifica('F18', 'Cobranza', 'sp_aplicar_pago (Cobranza)', 'aplicar_pago() reparte el pago de la cuota más antigua a la siguiente',
  JSON_ARRAY("CALL creditos.aplicar_pago(UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), @a)",
    "CALL creditos.aplicar_pago(UUID_TO_BIN('f0000000-0000-4000-8000-000000000002'), @a)"),
  "SELECT GROUP_CONCAT(CONCAT(estado_cuota, ' ', saldo_pendiente) ORDER BY numero_cuota SEPARATOR '; ')
          = 'PAGADA 0.00; PAGADA 0.00; PARCIAL 3200.00'
       FROM creditos.cuota WHERE id_calendario = UUID_TO_BIN('d0000000-0000-4000-8000-000000000001')",
  'PAGADA 0.00; PAGADA 0.00; PARCIAL 3200.00',
  "SELECT GROUP_CONCAT(CONCAT(estado_cuota, ' ', saldo_pendiente) ORDER BY numero_cuota SEPARATOR '; ')
       FROM creditos.cuota WHERE id_calendario = UUID_TO_BIN('d0000000-0000-4000-8000-000000000001')",
  'trigger');
CALL prueba.verifica('F19', 'Cobranza', 'Estado del crédito (Cobranza)', 'Pagadas todas las cuotas, el crédito queda CANCELADO',
  JSON_ARRAY("INSERT INTO creditos.pago (id_pago, monto_pago, referencia_transaccion, estado_confirmacion, cod_credito, id_canal)
     VALUES (UUID_TO_BIN('f0000000-0000-4000-8000-0000000000f2'), 10300, 'OP-T2', 'CONFIRMADO', 'CR-0001', 'VEN')",
    "CALL creditos.aplicar_pago(UUID_TO_BIN('f0000000-0000-4000-8000-0000000000f2'), @a)"),
  "SELECT estado_credito = 'CANCELADO' FROM creditos.credito WHERE cod_credito = 'CR-0001'",
  'CANCELADO',
  "SELECT estado_credito FROM creditos.credito WHERE cod_credito = 'CR-0001'",
  'trigger');
CALL prueba.rechaza('F20', 'Cobranza', 'Aplicación de pagos', 'Una aplicación de pago no se modifica',
  JSON_ARRAY("CALL creditos.aplicar_pago(UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), @a)",
    "UPDATE creditos.aplicacion_pago SET monto_aplicado = 1"),
  'UPDATE command denied', 'privilegio');

CALL prueba.rechaza('F21a', 'Cuentas', 'Estado de la cuenta (Cuentas)', 'Una cuenta BLOQUEADA no admite débitos',
  JSON_ARRAY("UPDATE cuentas.cuenta_ahorro SET estado_cuenta = 'BLOQUEADA' WHERE num_cuenta = 'CTA-PEN-2'",
    "CALL prueba.movimiento('CTA-PEN-2', 'RETIRO', 100, 'VEN', NULL, NULL, @m)"),
  'BNA-ESTADO-CUENTA', 'trigger');
CALL prueba.verifica('F21b', 'Cuentas', 'Estado de la cuenta (Cuentas)', 'Una cuenta BLOQUEADA_PREVENTIVA admite créditos',
  JSON_ARRAY("UPDATE cuentas.cuenta_ahorro SET estado_cuenta = 'BLOQUEADA_PREVENTIVA' WHERE num_cuenta = 'CTA-PEN-2'",
    "CALL prueba.movimiento('CTA-PEN-2', 'DEPOSITO', 100, 'VEN', NULL, NULL, @m)"),
  "SELECT saldo_contable = 5100 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2'",
  'saldo 5100.00',
  "SELECT CONCAT('saldo ', saldo_contable) FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2'",
  'trigger');
CALL prueba.verifica('F22', 'Cuentas', 'Extorno (Tarjetas, C07)', 'El extorno devuelve el monto al tope del día',
  JSON_ARRAY("CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 600, 'ATM', NULL, NULL, @v)",
    "UPDATE cuentas.movimiento SET estado_transaccion = 'EXTORNADO' WHERE uuid_transaccion = @v"),
  "SELECT monto_acumulado = 0 FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'",
  'consumido hoy 0.00',
  "SELECT CONCAT('consumido hoy ', monto_acumulado) FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'",
  'trigger');
CALL prueba.rechaza('F23', 'Cuentas', 'Movimiento inmutable', 'El importe de un movimiento no se modifica',
  JSON_ARRAY("UPDATE cuentas.movimiento SET monto = 1 WHERE num_cuenta = 'CTA-PEN-2'"),
  'UPDATE command denied', 'privilegio');
CALL prueba.rechaza('F24', 'CORE', 'Partida doble', 'Un asiento sin líneas se rechaza al confirmar',
  JSON_ARRAY("INSERT INTO core.asiento_contable (id_asiento, numero_asiento, fecha_contable, fecha_valor, glosa, moneda, correlation_id)
     VALUES (UUID_TO_BIN('9a000000-0000-4000-8000-000000000003'), 'T-VACIO', CURRENT_DATE, CURRENT_DATE, 'Sin líneas', 'PEN', core.uuid_v4())"),
  'INSERT command denied', 'privilegio');
CALL prueba.rechaza('F24', 'CORE', 'Partida doble', 'Un asiento sin líneas se rechaza al confirmar',
  JSON_ARRAY("CALL core.registrar_asiento(UUID_TO_BIN('9a000000-0000-4000-8000-000000000003'), 'T-VACIO', CURRENT_DATE, CURRENT_DATE,
       'Sin líneas', 'PEN', core.uuid_v4(), NULL, JSON_ARRAY(), @a)"),
  'BNA-PARTIDA-DOBLE', 'procedimiento');

CALL prueba.verifica('F25', 'Tarjetas', 'v_tarjeta_resumen (PCI-DSS)', 'La vista enmascara el número y muestra el vencimiento MM/AA',
  JSON_ARRAY(),
  "SELECT numero_enmascarado = '4557 88** **** 1234' AND vencimiento_mm_aa = '01/31' AND operativa
       FROM tarjetas.v_tarjeta_resumen WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')",
  '4557 88** **** 1234; 01/31; operativa',
  "SELECT CONCAT(numero_enmascarado, '; ', vencimiento_mm_aa, '; ', IF(operativa, 'operativa', 'no operativa'))
       FROM tarjetas.v_tarjeta_resumen WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')",
  'declarativo');
CALL prueba.verifica('F26', 'Tarjetas', 'v_consumo_diario (RN-TOP-001)', 'La vista suma lo autorizado por tarjeta, canal, moneda y día',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, codigo_respuesta, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 200, 'AUTORIZADA', '00', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1'),
            ('RETIRO', 300, 'AUTORIZADA', '00', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1')"),
  "SELECT monto_consumido = 500 AND operaciones = 2 FROM tarjetas.v_consumo_diario
      WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001') AND id_canal = 'ATM' AND moneda = 'PEN'
        AND fecha = core.fn_fecha_negocio(UTC_TIMESTAMP(6))",
  'ATM PEN hoy: 500.00 en 2 operaciones',
  "SELECT CONCAT(id_canal, ' ', moneda, ' hoy: ', monto_consumido, ' en ', operaciones, ' operaciones')
       FROM tarjetas.v_consumo_diario WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001')",
  'declarativo');
CALL prueba.verifica('F27', 'Tarjetas', 'v_credenciales_en_riesgo (RN-TAR-004)', 'La vista muestra los intentos acumulados y restantes',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'ATM-AQP-001', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  "SELECT count(*) = 1 AND min(intentos_fallidos) = 1 AND min(intentos_restantes) = 2 FROM tarjetas.v_credenciales_en_riesgo",
  'PIN_ATM: 1 fallido, 2 restantes',
  "SELECT GROUP_CONCAT(CONCAT(credencial, ': ', intentos_fallidos, ' fallido, ', intentos_restantes, ' restantes') SEPARATOR '; ')
       FROM tarjetas.v_credenciales_en_riesgo",
  'declarativo');
CALL prueba.verifica('F28', 'Desembolso', 'des_v_ordenes_inciertas', 'La vista lista las órdenes con resultado incierto en el CORE',
  JSON_ARRAY(),
  "SELECT GROUP_CONCAT(codigo_orden) = 'DES-2026-000003' FROM creditos.v_ordenes_inciertas",
  'DES-2026-000003',
  "SELECT GROUP_CONCAT(CONCAT(codigo_orden, ' (', estado_orden, ')') SEPARATOR ', ') FROM creditos.v_ordenes_inciertas",
  'declarativo');
CALL prueba.verifica('F29', 'Desembolso', 'des_v_entregas_pendientes', 'La vista lista las entregas que superan dos reintentos',
  JSON_ARRAY(),
  "SELECT count(*) = 1 AND min(intentos) = 3 FROM creditos.v_entregas_pendientes",
  '1 entrega, 3 intentos',
  "SELECT CONCAT(count(*), ' entrega, ', min(intentos), ' intentos') FROM creditos.v_entregas_pendientes",
  'declarativo');
CALL prueba.verifica('F30', 'Desembolso', 'des_v_conciliacion_diaria', 'La vista cuadra lo ordenado con lo abonado por fecha y moneda',
  JSON_ARRAY(),
  "SELECT importe_ordenes = 10000 AND importe_abonado = 10000 AND ordenes_sin_abono = 0
       FROM creditos.v_conciliacion_diaria WHERE moneda = 'PEN'",
  'PEN: ordenado 10000.00, abonado 10000.00, sin abono 0',
  "SELECT CONCAT(moneda, ': ordenado ', importe_ordenes, ', abonado ', importe_abonado, ', sin abono ', ordenes_sin_abono)
       FROM creditos.v_conciliacion_diaria",
  'declarativo');
-- F31: además de los ocho índices de consulta, ningún otro índice de esas
-- tablas es prefijo de uno de ellos (InnoDB crearía uno por cada clave
-- foránea sin índice; la rama main busca los nombres que tendrían).
CALL prueba.verifica('F31', 'Índices', 'Consultas de Tarjetas y Desembolso', 'Existen los índices de consulta y ninguno repite a otro de clave foránea',
  JSON_ARRAY(),
  "SELECT (SELECT count(DISTINCT INDEX_NAME) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA IN ('core', 'clientes', 'cuentas', 'tarjetas', 'creditos')
              AND INDEX_NAME IN ('ix_movimiento_cuenta_fecha', 'ix_autorizacion_tarjeta_fecha', 'ix_intento_tarjeta_fecha',
                   'ix_historial_tarjeta_fecha', 'ix_orden_estado_fecha', 'ix_evento_salida_pendiente',
                   'ix_evento_entrega_pendiente', 'ix_evento_auditoria_correlacion')) = 8
      AND (WITH ix AS (SELECT TABLE_SCHEMA s, TABLE_NAME t, INDEX_NAME i,
                              GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) c
                         FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA IN ('core', 'clientes', 'cuentas', 'tarjetas', 'creditos') GROUP BY 1, 2, 3)
           SELECT count(*) FROM ix a JOIN ix q ON q.s = a.s AND q.t = a.t AND a.i <> q.i AND a.i <> 'PRIMARY'
            WHERE q.i IN ('ix_movimiento_cuenta_fecha', 'ix_autorizacion_tarjeta_fecha',
                   'ix_intento_tarjeta_fecha', 'ix_historial_tarjeta_fecha', 'ix_orden_estado_fecha',
                   'ix_evento_salida_pendiente', 'ix_evento_entrega_pendiente', 'ix_evento_auditoria_correlacion')
              AND LEFT(q.c, CHAR_LENGTH(a.c) + 1) = CONCAT(a.c, ',')) = 0",
  '8 índices de consulta; 0 redundantes',
  "SELECT CONCAT((SELECT count(DISTINCT INDEX_NAME) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA IN ('core', 'clientes', 'cuentas', 'tarjetas', 'creditos')
              AND INDEX_NAME IN ('ix_movimiento_cuenta_fecha', 'ix_autorizacion_tarjeta_fecha', 'ix_intento_tarjeta_fecha',
                   'ix_historial_tarjeta_fecha', 'ix_orden_estado_fecha', 'ix_evento_salida_pendiente',
                   'ix_evento_entrega_pendiente', 'ix_evento_auditoria_correlacion')), ' índices de consulta; ',
      (WITH ix AS (SELECT TABLE_SCHEMA s, TABLE_NAME t, INDEX_NAME i,
                              GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) c
                         FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA IN ('core', 'clientes', 'cuentas', 'tarjetas', 'creditos') GROUP BY 1, 2, 3)
           SELECT count(*) FROM ix a JOIN ix q ON q.s = a.s AND q.t = a.t AND a.i <> q.i AND a.i <> 'PRIMARY'
            WHERE q.i IN ('ix_movimiento_cuenta_fecha', 'ix_autorizacion_tarjeta_fecha',
                   'ix_intento_tarjeta_fecha', 'ix_historial_tarjeta_fecha', 'ix_orden_estado_fecha',
                   'ix_evento_salida_pendiente', 'ix_evento_entrega_pendiente', 'ix_evento_auditoria_correlacion')
              AND LEFT(q.c, CHAR_LENGTH(a.c) + 1) = CONCAT(a.c, ',')), ' redundantes')",
  'declarativo');
-- F32 (solo MySQL): el identificador de una bitácora lo asigna la base. En
-- la rama main lo garantiza GENERATED ALWAYS AS IDENTITY, sin prueba propia.
CALL prueba.rechaza('F32', 'CORE', 'Bitácoras (decisión del informe)', 'El identificador de una bitácora lo asigna la base',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (id_intento, tipo_credencial, id_terminal, resultado, id_tarjeta)
     VALUES (999, 'PIN_ATM', 'ATM-AQP-001', 'EXITOSO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'))"),
  'INSERT command denied', 'privilegio');

-- =====================================================================
-- R: pruebas negativas originales del informe
-- =====================================================================
CALL prueba.rechaza('R1', 'Regresión', 'Pruebas negativas del DDL', 'Evento de auditoría sobre un registro no registrado como auditable',
  JSON_ARRAY("INSERT INTO creditos.evento_auditoria (modulo_emisor, id_entidad, accion, actor, correlation_id)
     VALUES (14, 'CR-0001', 'PAGO', 'cobranza', core.uuid_v4())"),
  'fk_evento_auditoria_2', 'declarativo');
CALL prueba.rechaza('R2', 'Regresión', 'Pruebas negativas del DDL', 'Intento con coordenada para una credencial que no es la matriz',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, coord_fila, coord_columna, id_canal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'A', 1, 'ATM', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  'ck_intento_autenticacion_4', 'declarativo');
CALL prueba.rechaza('R3', 'Regresión', 'Pruebas negativas del DDL', 'Intento con terminal y canal a la vez',
  JSON_ARRAY("INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, id_canal, resultado, id_tarjeta)
     VALUES ('PIN_ATM', 'ATM-AQP-001', 'ATM', 'FALLIDO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  'ck_intento_autenticacion_5', 'declarativo');
CALL prueba.rechaza('R4', 'Regresión', 'Pruebas negativas del DDL', 'Credencial de tipo TOKEN_MATRIZ',
  JSON_ARRAY("INSERT INTO tarjetas.credencial (id_tarjeta, tipo_credencial, hash_credencial, sal)
     VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'TOKEN_MATRIZ', REPEAT('a', 64), REPEAT('b', 32))"),
  'ck_credencial_1', 'declarativo');
CALL prueba.rechaza('R5', 'Regresión', 'Pruebas negativas del DDL', 'Autorización sobre una cuenta inexistente',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta)
     VALUES ('RETIRO', 100, 'INICIADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'NO-EXISTE')"),
  'foreign key constraint fails', 'declarativo');
CALL prueba.rechaza('R6', 'Regresión', 'Pruebas negativas del DDL', 'Segundo cliente con el mismo DNI',
  JSON_ARRAY("INSERT INTO clientes.verificacion_captacion (id_verificacion_captacion, estado_habilitante) VALUES ('VC-9', 'HABILITADO')",
    "INSERT INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, apellido_paterno, correo, celular,
       estado_cliente, id_verificacion_captacion, version_contrato)
     VALUES ('C009', 'DNI', '70000001', 'Otro', 'Cliente', 'otro@example.com', '959000009', 'ACTIVO', 'VC-9', 'v1')"),
  'uk_cliente_1', 'declarativo');
CALL prueba.rechaza('R7', 'Regresión', 'Pruebas negativas del DDL', 'Segunda orden CONFIRMADA para la misma aprobación',
  JSON_ARRAY("INSERT INTO creditos.orden_desembolso (codigo_orden, importe, estado_orden, idempotency_key, request_hash, usuario_preparacion,
       correlation_id, id_evaluacion, num_cuenta, id_canal)
     VALUES ('DES-T-5', 1000, 'CONFIRMADA', core.uuid_v4(), REPEAT('x', 64), 'u', core.uuid_v4(),
       UUID_TO_BIN('c0000000-0000-4000-8000-000000000001'), 'CTA-PEN-1', 'VEN')"),
  'BNA-ORDEN-UNICA|ux_orden_confirmada', 'trigger');
CALL prueba.rechaza('R8', 'Regresión', 'Pruebas negativas del DDL', 'Borrar una moneda en uso',
  JSON_ARRAY("DELETE FROM core.moneda WHERE cod_moneda = 'PEN'"),
  'DELETE command denied', 'privilegio');
