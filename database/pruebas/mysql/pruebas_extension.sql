-- Pruebas de sql/bna_extension.sql. Las ejecuta bna_app_user y son solo de la
-- rama mysql. Requiere arnes.sql, datos.sql y los periodos de 2001 y 2002 que
-- carga run_tests.sh.
SET @u1 = UUID_TO_BIN('11111111-1111-4111-8111-111111111111');
SET @h = REPEAT('a', 64);
SET @h2 = REPEAT('b', 64);

CALL prueba.verifica('X01', 'Extensión', 'Usuarios', 'hash_password admite 255 caracteres',
  JSON_ARRAY("CALL core.crear_usuario(UUID_TO_BIN('11111111-1111-4111-8111-111111111111'), 'ana', 'Ana', 'ASESOR', REPEAT('x', 255), 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')"),
  "SELECT CHAR_LENGTH(hash_password) = 255 FROM core.usuario_sistema WHERE username = 'ana'",
  '255', "SELECT CHAR_LENGTH(hash_password) FROM core.usuario_sistema WHERE username = 'ana'", 'procedimiento');

CALL prueba.rechaza('X02', 'Extensión', 'Usuarios', 'bna_app no escribe directamente usuarios',
  JSON_ARRAY("INSERT INTO core.usuario_sistema (id_usuario, username, nombre, rol, hash_password, algoritmo_hash, version_hash) VALUES (UUID_TO_BIN(UUID()), 'b', 'B', 'ASESOR', 'h', 'BCRYPT', 'v2')"),
  'denied', 'privilegio');

CALL prueba.rechaza('X03', 'Extensión', 'Usuarios', 'username es único',
  JSON_ARRAY("CALL core.crear_usuario(UUID_TO_BIN('11111111-1111-4111-8111-111111111111'), 'ana', 'Ana', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')",
             "CALL core.crear_usuario(UUID_TO_BIN('22222222-2222-4222-8222-222222222222'), 'ana', 'Otra', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')"),
  'uk_usuario_sistema_1', 'declarativo');

CALL prueba.verifica('X04', 'Extensión', 'Usuarios', 'La migración de hash es condicional y deja un solo evento',
  JSON_ARRAY("CALL core.crear_usuario(UUID_TO_BIN('11111111-1111-4111-8111-111111111111'), 'ana', 'Ana', 'ASESOR', 'viejo', 'SHA256', 'v1', NULL, TRUE, 'pruebas')",
             "CALL core.migrar_hash_usuario(UUID_TO_BIN('11111111-1111-4111-8111-111111111111'), 'SHA256', 'nuevo', 'BCRYPT', 'v2', 'pruebas', @f1)",
             "CALL core.migrar_hash_usuario(UUID_TO_BIN('11111111-1111-4111-8111-111111111111'), 'SHA256', 'otro', 'BCRYPT', 'v2', 'pruebas', @f2)"),
  "SELECT @f1 = 1 AND @f2 = 0 AND (SELECT hash_password FROM core.usuario_sistema WHERE username = 'ana') = 'nuevo' AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'MIGRAR_HASH_PASSWORD' AND actor = 'pruebas') = 1",
  '1, 0 y un evento', "SELECT CONCAT(@f1, ', ', @f2)", 'procedimiento');

CALL prueba.rechaza('X05', 'Extensión', 'Productos', 'bna_app no escribe productos',
  JSON_ARRAY("INSERT INTO core.producto_credito (id_producto_credito, nombre, tasa_tea) VALUES (UUID_TO_BIN(UUID()), 'P', 0.1)"),
  'denied', 'privilegio');

CALL prueba.rechaza('X06', 'Extensión', 'Tipos de cambio', 'bna_app no escribe tipos de cambio',
  JSON_ARRAY("INSERT INTO core.tipo_cambio VALUES ('USD', 'PEN', '2026-01-01', 3.75)"), 'denied', 'privilegio');

CALL prueba.rechaza('X07', 'Extensión', 'Periodos', 'No se registra un asiento en un periodo cerrado',
  JSON_ARRAY("CALL core.registrar_asiento(NULL, 'X07', '2001-01-15', '2001-01-15', 'g', 'PEN', UUID_TO_BIN(UUID()), NULL, JSON_ARRAY(JSON_OBJECT('partida', 'DEBE', 'importe', 10, 'cuenta', '1101'), JSON_OBJECT('partida', 'HABER', 'importe', 10, 'cuenta', '2101')), @a)"),
  'BNA-PERIODO', 'trigger');

CALL prueba.verifica('X08', 'Extensión', 'Periodos', 'Un periodo abierto admite el asiento',
  JSON_ARRAY("CALL core.registrar_asiento(NULL, 'X08', '2002-01-15', '2002-01-15', 'g', 'PEN', UUID_TO_BIN(UUID()), NULL, JSON_ARRAY(JSON_OBJECT('partida', 'DEBE', 'importe', 10, 'cuenta', '1101'), JSON_OBJECT('partida', 'HABER', 'importe', 10, 'cuenta', '2101')), @a)"),
  "SELECT COUNT(*) = 1 FROM core.asiento_contable WHERE numero_asiento = 'X08'", 'asiento registrado',
  "SELECT COUNT(*) FROM core.asiento_contable WHERE numero_asiento = 'X08'", 'trigger');

CALL prueba.verifica('X09', 'Extensión', 'Movimientos', 'El depósito actualiza el saldo y guarda la llave',
  JSON_ARRAY("SET @s0 = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2')",
             "CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 100, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k1', REPEAT('a', 64), 'pruebas', @m, @r)"),
  "SELECT @r = 0 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @s0 + 100 AND (SELECT uuid_transaccion FROM cuentas.idempotencia_movimiento WHERE llave = 'k1') = @m",
  'saldo + 100 y llave', "SELECT @r", 'procedimiento');

CALL prueba.verifica('X10', 'Extensión', 'Movimientos', 'Repetir la llave devuelve la operación sin aplicarla',
  JSON_ARRAY("SET @s0 = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2')",
             "CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 100, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k2', REPEAT('a', 64), 'pruebas', @m1, @r1)",
             "CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 100, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k2', REPEAT('a', 64), 'pruebas', @m2, @r2)"),
  "SELECT @r2 = 1 AND @m1 = @m2 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @s0 + 100",
  'una sola aplicación', "SELECT @r2", 'procedimiento');

CALL prueba.rechaza('X11', 'Extensión', 'Movimientos', 'La misma llave con otros parámetros se rechaza',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 100, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k3', REPEAT('a', 64), 'pruebas', @m, @r)",
             "CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 200, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k3', REPEAT('b', 64), 'pruebas', @m, @r)"),
  'BNA-IDEMPOTENCIA', 'procedimiento');

CALL prueba.rechaza('X12', 'Extensión', 'Movimientos', 'El retiro sin saldo sigue rechazándose por el trigger',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-2', 'RETIRO', 99999999, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-SALDO|RN-TOP-001', 'trigger');

CALL prueba.verifica('X13', 'Extensión', 'Movimientos', 'La transferencia mueve el saldo con un asiento por tramo',
  JSON_ARRAY("SET @o0 = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2')",
             "SET @d0 = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1')",
             "CALL cuentas.registrar_transferencia('CTA-PEN-2', 'CTA-PEN-1', 50, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k4', REPEAT('a', 64), 'pruebas', @d, @c, @r)"),
  "SELECT (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @o0 - 50 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @d0 + 50 AND (SELECT id_asiento FROM cuentas.movimiento WHERE uuid_transaccion = @d) <> (SELECT id_asiento FROM cuentas.movimiento WHERE uuid_transaccion = @c)",
  'dos saldos y dos asientos', "SELECT @r", 'procedimiento');

CALL prueba.rechaza('X14', 'Extensión', 'Movimientos', 'No se transfiere entre monedas distintas',
  JSON_ARRAY("CALL cuentas.registrar_transferencia('CTA-PEN-1', 'CTA-USD-1', 50, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  'BNA-MONEDA', 'procedimiento');

CALL prueba.rechaza('X15', 'Extensión', 'Movimientos', 'No se transfiere a la misma cuenta',
  JSON_ARRAY("CALL cuentas.registrar_transferencia('CTA-PEN-1', 'CTA-PEN-1', 50, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  'BNA-TRANSFERENCIA', 'procedimiento');

CALL prueba.verifica('X16', 'Extensión', 'Auditoría', 'El movimiento deja su evento en la misma operación',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 1, 'g', 'VEN', UUID_TO_BIN(UUID()), 'kX16', REPEAT('a', 64), 'pruebas', @m, @r)"),
  "SELECT COUNT(*) = 1 FROM core.evento_auditoria WHERE id_entidad = BIN_TO_UUID(@m) AND accion = 'DEPOSITO'", 'un evento',
  "SELECT COUNT(*) FROM core.evento_auditoria WHERE id_entidad = BIN_TO_UUID(@m)", 'procedimiento');

CALL prueba.rechaza('X17', 'Extensión', 'Auditoría', 'bna_app no modifica la bitácora',
  JSON_ARRAY("UPDATE core.evento_auditoria SET actor = 'x'"), 'denied', 'privilegio');

CALL prueba.rechaza('X18', 'Extensión', 'Cuentas', 'Una mancomunada exige sus titulares',
  JSON_ARRAY("CALL cuentas.abrir_cuenta('CTA-X18', '00000000000000000018', 'PEN', 'MANCOMUNADA_CONJUNTA', 'AQP01', JSON_ARRAY('C001'), 'pruebas')"),
  'BNA-REGIMEN', 'procedimiento');

CALL prueba.verifica('X19', 'Extensión', 'Cuentas', 'La cuenta se abre con su titular',
  JSON_ARRAY("CALL cuentas.abrir_cuenta('CTA-X19', '00000000000000000019', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('C001'), 'pruebas')"),
  "SELECT COUNT(*) = 1 FROM cuentas.titularidad WHERE num_cuenta = 'CTA-X19' AND cod_cliente = 'C001'", 'un titular',
  "SELECT COUNT(*) FROM cuentas.titularidad WHERE num_cuenta = 'CTA-X19'", 'procedimiento');

CALL prueba.verifica('X20', 'Extensión', 'Tarjetas', 'La tarjeta se emite y cambia de estado por el historial',
  JSON_ARRAY("CALL tarjetas.emitir_tarjeta(UUID_TO_BIN('33333333-3333-4333-8333-333333333333'), 'tok-x20', '455788', '1234', '2026-01-01', '2030-01-01', 'C001', 'CTA-PEN-1', 'pruebas')",
             "CALL tarjetas.cambiar_estado_tarjeta(UUID_TO_BIN('33333333-3333-4333-8333-333333333333'), 'ACTIVA', 'Activación', 'CLIENTE', 'pruebas', @h1)"),
  "SELECT estado_tarjeta = 'ACTIVA' FROM tarjetas.tarjeta WHERE pan_token = 'tok-x20'", 'ACTIVA',
  "SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE pan_token = 'tok-x20'", 'trigger');

CALL prueba.verifica('X21', 'Extensión', 'Catálogos', 'Un valor de la API con equivalente exacto se traduce',
  JSON_ARRAY("SET @v = (SELECT valor_bd FROM core.equivalencia_catalogo WHERE catalogo = 'estado_tarjeta' AND valor_api = 'ANULADA')"),
  "SELECT @v = 'CANCELADA'", 'CANCELADA', "SELECT @v", 'declarativo');

-- Hallazgos de la revisión independiente.
CALL prueba.rechaza('X40', 'Extensión', 'Canal', 'Un movimiento sin canal se rechaza (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-2', 'RETIRO', 1, 'g', NULL, UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-CANAL', 'procedimiento');

CALL prueba.rechaza('X41', 'Extensión', 'Canal', 'Una transferencia sin canal se rechaza (C2)',
  JSON_ARRAY("CALL cuentas.registrar_transferencia('CTA-PEN-2', 'CTA-PEN-1', 1, 'g', NULL, UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  'BNA-CANAL', 'procedimiento');

CALL prueba.rechaza('X42', 'Extensión', 'Canal', 'El tope diario se aplica a la transferencia (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 20000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)",
             "CALL cuentas.registrar_transferencia('CTA-PEN-1', 'CTA-PEN-2', 11000, 'g', 'HB', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  'RN-TOP-001', 'trigger');

CALL prueba.rechaza('X43', 'Extensión', 'Canal', 'Un débito por ATM exige autorización de tarjeta (I7)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-CONJ', 'RETIRO', 1, 'g', 'ATM', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-CANAL', 'procedimiento');

CALL prueba.rechaza('X44', 'Extensión', 'Tarjetas', 'La tarjeta exige que el cliente sea titular de la cuenta (I3)',
  JSON_ARRAY("CALL tarjetas.emitir_tarjeta(UUID_TO_BIN('44444444-4444-4444-8444-444444444444'), 'tok-x44', '455788', '1234', '2026-01-01', '2030-01-01', 'C002', 'CTA-PEN-1', 'pruebas')"),
  'BNA-TARJETA', 'procedimiento');

CALL prueba.rechaza('X46', 'Extensión', 'Cuentas', 'Una cuenta individual tiene un solo titular (I4)',
  JSON_ARRAY("CALL cuentas.abrir_cuenta('CTA-X46', '00000000000000000046', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('C001', 'C002'), 'pruebas')"),
  'BNA-REGIMEN', 'procedimiento');

CALL prueba.rechaza('X47', 'Extensión', 'Cuentas', 'El titular debe poder operar (I4)',
  JSON_ARRAY("CALL cuentas.abrir_cuenta('CTA-X47', '00000000000000000047', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('C004'), 'pruebas')"),
  'BNA-TITULAR', 'procedimiento');

CALL prueba.rechaza('X48', 'Extensión', 'Cuentas', 'Los titulares son una lista JSON (I4)',
  JSON_ARRAY("CALL cuentas.abrir_cuenta('CTA-X48', '00000000000000000048', 'PEN', 'MANCOMUNADA_CONJUNTA', 'AQP01', JSON_OBJECT('a', 1, 'b', 2), 'pruebas')"),
  'BNA-REGIMEN', 'procedimiento');

CALL prueba.rechaza('X49', 'Extensión', 'Cuentas', 'Los titulares no se repiten (I4)',
  JSON_ARRAY("CALL cuentas.abrir_cuenta('CTA-X49', '00000000000000000049', 'PEN', 'MANCOMUNADA_CONJUNTA', 'AQP01', JSON_ARRAY('C001', 'C001'), 'pruebas')"),
  'BNA-REGIMEN', 'procedimiento');

CALL prueba.rechaza('X50', 'Extensión', 'Movimientos', 'registrar_movimiento solo admite depósito y retiro (I6)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-2', 'EXTORNO', 777, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-MOVIMIENTO', 'procedimiento');

CALL prueba.rechaza('X51', 'Extensión', 'Movimientos', 'Una transferencia de un solo tramo se rechaza (I6)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-2', 'TRANSFERENCIA_RECIBIDA', 1, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-MOVIMIENTO', 'procedimiento');

CALL prueba.verifica('X52', 'Extensión', 'Auditoría', 'crear_usuario deja su evento (I11)',
  JSON_ARRAY("CALL core.crear_usuario(UUID_TO_BIN('55555555-5555-4555-8555-555555555555'), 'x52', 'A', 'ADMINISTRADOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')"),
  "SELECT COUNT(*) = 1 FROM core.evento_auditoria WHERE accion = 'CREAR_USUARIO' AND id_entidad = '55555555-5555-4555-8555-555555555555'",
  'un evento', "SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'CREAR_USUARIO'", 'procedimiento');

CALL prueba.verifica('X53', 'Extensión', 'Auditoría', 'asignar_rol deja el rol anterior y el nuevo (I11, M11)',
  JSON_ARRAY("CALL core.crear_usuario(UUID_TO_BIN('55555555-5555-4555-8555-555555555556'), 'x53', 'A', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')",
             "CALL core.asignar_rol(UUID_TO_BIN('55555555-5555-4555-8555-555555555556'), 'AUDITOR', 'pruebas', @f)"),
  "SELECT COUNT(*) = 1 FROM core.evento_auditoria WHERE accion = 'ASIGNAR_ROLES' AND detalle->>'$.rol_anterior' = 'ASESOR' AND detalle->>'$.rol_nuevo' = 'AUDITOR'",
  'un evento con los dos roles', "SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'ASIGNAR_ROLES'", 'procedimiento');

CALL prueba.rechaza('X54', 'Extensión', 'Auditoría', 'bna_app no fabrica eventos de auditoría (I11)',
  JSON_ARRAY("CALL core.registrar_evento('CORE', 'e', '1', 'FALSO', 'nadie', NULL, NULL)"), 'denied', 'privilegio');

CALL prueba.rechaza('X55', 'Extensión', 'Movimientos', 'Una cuenta nula da un error de regla (M9)',
  JSON_ARRAY("CALL cuentas.registrar_transferencia(NULL, 'CTA-PEN-1', 1, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  'BNA-CUENTA', 'procedimiento');

CALL prueba.verifica('X57', 'Extensión', 'Movimientos', 'Repetir una transferencia devuelve la misma operación (I13)',
  JSON_ARRAY("SET @o0 = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2')",
             "CALL cuentas.registrar_transferencia('CTA-PEN-2', 'CTA-PEN-1', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'kX57', REPEAT('a', 64), 'pruebas', @d1, @c1, @r1)",
             "CALL cuentas.registrar_transferencia('CTA-PEN-2', 'CTA-PEN-1', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'kX57', REPEAT('a', 64), 'pruebas', @d2, @c2, @r2)"),
  "SELECT @r2 = 1 AND @d1 = @d2 AND @c1 = @c2 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @o0 - 10",
  'una sola aplicación', "SELECT @r2", 'procedimiento');

CALL prueba.rechaza('X58', 'Extensión', 'Movimientos', 'Una llave de depósito no sirve para una transferencia (I13)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'kX58', REPEAT('a', 64), 'pruebas', @m, @r)",
             "CALL cuentas.registrar_transferencia('CTA-PEN-2', 'CTA-PEN-1', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'kX58', REPEAT('b', 64), 'pruebas', @d, @c, @r)"),
  'BNA-IDEMPOTENCIA', 'procedimiento');

CALL prueba.verifica('X59', 'Extensión', 'Periodos', 'La fecha de negocio se corta a medianoche de Arequipa (I13)',
  JSON_ARRAY("SET @f = core.fn_fecha_negocio('2026-01-01 04:59:59')", "SET @g = core.fn_fecha_negocio('2026-01-01 05:00:00')"),
  "SELECT @f = '2025-12-31' AND @g = '2026-01-01'", '2025-12-31 y 2026-01-01', "SELECT CONCAT(@f, ' y ', @g)", 'procedimiento');

-- C2 reabierto: un débito sin fila en core.limite_canal se rechaza.
CALL prueba.rechaza('X60', 'Extensión', 'Canal', 'Un retiro por AGE, sin tope en las fuentes, se rechaza (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 20000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_movimiento('CTA-PEN-1', 'RETIRO', 2000, 'g', 'AGE', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-CANAL: el canal', 'trigger');

CALL prueba.rechaza('X61', 'Extensión', 'Canal', 'Una transferencia por AGE se rechaza (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 20000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_transferencia('CTA-PEN-1', 'CTA-PEN-2', 15000, 'g', 'AGE', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  'BNA-CANAL: el canal', 'trigger');

CALL prueba.rechaza('X62', 'Extensión', 'Canal', 'Un retiro en USD por HB, sin tope en las fuentes, se rechaza (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-USD-1', 'DEPOSITO', 5000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_movimiento('CTA-USD-1', 'RETIRO', 1000, 'g', 'HB', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-CANAL: el canal', 'trigger');

CALL prueba.rechaza('X63', 'Extensión', 'Canal', 'Un retiro en USD por AGE se rechaza (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-USD-1', 'DEPOSITO', 5000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_movimiento('CTA-USD-1', 'RETIRO', 1000, 'g', 'AGE', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-CANAL: el canal', 'trigger');

CALL prueba.rechaza('X149', 'Extensión', 'Canal', 'Un débito en USD por BD, con fila deshabilitada, se rechaza con RN-BD-002 (R5)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-USD-1', 'DEPOSITO', 5000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_movimiento('CTA-USD-1', 'RETIRO', 1, 'g', 'BD', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'RN-BD-002: el canal BD', 'trigger');

CALL prueba.verifica('X64', 'Extensión', 'Canal', 'Ventanilla no tiene tope automático: retiro de 2000 (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 20000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_movimiento('CTA-PEN-1', 'RETIRO', 2000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  "SELECT @m IS NOT NULL AND @r = 0", 'retiro aplicado', "SELECT @r", 'trigger');

CALL prueba.verifica('X65', 'Extensión', 'Canal', 'Ventanilla no tiene tope automático: transferencia de 15000 (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 20000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_transferencia('CTA-PEN-1', 'CTA-PEN-2', 15000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  "SELECT @d IS NOT NULL AND @r = 0", 'transferencia aplicada', "SELECT @r", 'trigger');

CALL prueba.verifica('X66', 'Extensión', 'Canal', 'Ventanilla opera en USD sin tope automático (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-USD-1', 'DEPOSITO', 5000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)", "CALL cuentas.registrar_movimiento('CTA-USD-1', 'RETIRO', 1000, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  "SELECT @m IS NOT NULL AND @r = 0", 'retiro aplicado', "SELECT @r", 'trigger');

CALL prueba.verifica('X67', 'Extensión', 'Canal', 'Un crédito por AGE no depende del tope (C2)',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 100, 'g', 'AGE', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  "SELECT @m IS NOT NULL", 'depósito aplicado', "SELECT @r", 'trigger');

CALL prueba.rechaza('X68', 'Extensión', 'Canal', 'Una autorización por HB en USD se rechaza como en el movimiento (C2)',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_canal, id_tarjeta, num_cuenta) VALUES ('RETIRO', 10, 'AUTORIZADA', 'HB', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-USD-1')"),
  'ERR-TAR-006: el canal HB no opera en USD$', 'trigger');
