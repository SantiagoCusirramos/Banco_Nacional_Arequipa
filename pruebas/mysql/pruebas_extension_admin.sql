-- Pruebas de sql/bna_extension.sql con bna_admin_user, que tiene los
-- privilegios y debe toparse con la restricción o el trigger.
CALL prueba.rechaza('X30', 'Extensión', 'Usuarios', 'El empleado exige una agencia existente',
  JSON_ARRAY("INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo, id_agencia) VALUES (UUID_TO_BIN(UUID()), 'E1', 'E', 'CAJERO', 'NOEXISTE')"),
  'fk_empleado_agencia', 'declarativo');

CALL prueba.rechaza('X31', 'Extensión', 'Tipos de cambio', 'La tasa debe ser positiva',
  JSON_ARRAY("INSERT INTO core.tipo_cambio VALUES ('USD', 'PEN', '2026-01-01', 0)"),
  'ck_tipo_cambio_tasa', 'declarativo');

CALL prueba.rechaza('X32', 'Extensión', 'Productos', 'El plazo mínimo no supera al máximo',
  JSON_ARRAY("INSERT INTO core.producto_credito (id_producto_credito, nombre, tasa_tea, plazo_min_meses, plazo_max_meses) VALUES (UUID_TO_BIN(UUID()), 'P', 0.1, 10, 5)"),
  'ck_producto_credito_plazo', 'declarativo');

CALL prueba.rechaza('X33', 'Extensión', 'Auditoría', 'La bitácora rechaza UPDATE aun con privilegios',
  JSON_ARRAY("CALL core.registrar_evento('CORE', 'e', '1', 'A', 'x', NULL, NULL)",
             "UPDATE core.evento_auditoria SET actor = 'y'"),
  'BNA-SOLO-INSERCION', 'trigger');

CALL prueba.rechaza('X34', 'Extensión', 'Auditoría', 'La bitácora rechaza DELETE aun con privilegios',
  JSON_ARRAY("CALL core.registrar_evento('CORE', 'e', '1', 'A', 'x', NULL, NULL)",
             "DELETE FROM core.evento_auditoria"),
  'BNA-SOLO-INSERCION', 'trigger');

CALL prueba.rechaza('X35', 'Extensión', 'Usuarios', 'El identificador del empleado debe ser un UUID válido (M6)',
  JSON_ARRAY("INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo) VALUES ('c2', 'E2', 'E', 'CAJERO')"),
  'ck_empleado_id', 'declarativo');

CALL prueba.rechaza('X45', 'Extensión', 'Tarjetas', 'No se emite tarjeta sobre una cuenta cancelada (I3)',
  JSON_ARRAY("UPDATE cuentas.cuenta_ahorro SET estado_cuenta = 'CANCELADA' WHERE num_cuenta = 'CTA-PEN-1'",
             "CALL tarjetas.emitir_tarjeta(UUID_TO_BIN('44444444-4444-4444-8444-444444444445'), 'tok-x45', '455788', '1234', '2026-01-01', '2030-01-01', 'C001', 'CTA-PEN-1', 'pruebas')"),
  'BNA-TARJETA', 'procedimiento');

CALL prueba.rechaza('X69', 'Extensión', 'Canal', 'Sin la fila explícita, ventanilla también se rechaza (C2)',
  JSON_ARRAY("DELETE FROM core.limite_canal WHERE id_canal = 'VEN' AND moneda = 'PEN'",
             "CALL cuentas.registrar_movimiento('CTA-PEN-2', 'RETIRO', 1, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-CANAL: el canal', 'trigger');

CALL prueba.rechaza('X56', 'Extensión', 'Canal', 'Un canal inactivo se rechaza (I7)',
  JSON_ARRAY("UPDATE core.canal SET activo = FALSE WHERE id_canal = 'VEN'",
             "CALL cuentas.registrar_movimiento('CTA-PEN-2', 'DEPOSITO', 1, 'g', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  'BNA-CANAL', 'procedimiento');

CALL prueba.rechaza('X205', 'Extensión', 'Usuarios', 'Un usuario SERVICIO sin módulo se rechaza aun con privilegios',
  JSON_ARRAY("INSERT INTO core.usuario_sistema (id_usuario, username, nombre, rol, hash_password, algoritmo_hash, version_hash) VALUES (UUID_TO_BIN(UUID()), 'svc-x205', 'S', 'SERVICIO', 'h', 'BCRYPT', 'v2')"),
  'ck_usuario_servicio', 'declarativo');

CALL prueba.rechaza('X206', 'Extensión', 'Usuarios', 'Una persona con módulo se rechaza aun con privilegios',
  JSON_ARRAY("INSERT INTO core.usuario_sistema (id_usuario, username, nombre, rol, hash_password, algoritmo_hash, version_hash, modulo) VALUES (UUID_TO_BIN(UUID()), 'ana-x206', 'A', 'ASESOR', 'h', 'BCRYPT', 'v2', 'CLIENTES')"),
  'ck_usuario_servicio', 'declarativo');

CALL prueba.verifica('X207', 'Extensión', 'Clientes', 'bna_admin ejecuta los procedimientos de clientes por su privilegio sobre la base',
  JSON_ARRAY("CALL clientes.catalogos_cliente(@k)",
             "CALL clientes.registrar_cliente('DNI', '71000207', 'Prueba', 'Ficticio', NULL, 'c207@example.com', '961000207', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  "SELECT @k IS NOT NULL AND (SELECT COUNT(*) FROM clientes.cliente WHERE cod_cliente = @c) = 1",
  'catálogos y cliente', "SELECT @c", 'privilegio');

-- v1.4: bna_admin ejecuta los procedimientos de créditos por su privilegio sobre creditos.*.
CALL prueba.verifica('X342', 'Extensión', 'Créditos', 'bna_admin ejecuta los procedimientos de créditos',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000342', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.catalogos_credito(@cat)"),
  "SELECT @r = 1 AND JSON_LENGTH(@cat, '$.estados_solicitud') = 5", 'ronda 1 y catálogos', "SELECT @r", 'procedimiento');

-- v1.10: bna_admin tiene sobre billetera.* lo mismo que sobre los demás esquemas.
CALL prueba.verifica('X670', 'Extensión', 'Billetera', 'bna_admin lee las tablas de la billetera y ejecuta sus procedimientos',
  JSON_ARRAY("CALL billetera.afiliar('C001', 'CTA-PEN-1', '123456', 'pruebas', NULL, @n)",
             "SELECT COUNT(*) INTO @a FROM billetera.afiliacion WHERE cod_cliente = 'C001'"),
  "SELECT @a = 1 AND @n = 1", 'afiliación leída', "SELECT @a", 'privilegio');
