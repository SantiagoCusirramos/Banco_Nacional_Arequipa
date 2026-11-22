-- Permisos de sql/bna_extension.sql con bna_api_user, que tiene el rol bna_api como
-- la cuenta desplegada de la API. Lo que no debe poder hacer, y lo que sí lee.

CALL prueba.rechaza('X110', 'Extensión', 'bna_api', 'bna_api no puede: SELECT tarjetas.credencial',
  JSON_ARRAY("SELECT * FROM tarjetas.credencial"), 'denied', 'privilegio');

CALL prueba.rechaza('X111', 'Extensión', 'bna_api', 'bna_api no puede: SELECT tarjetas.matriz_token',
  JSON_ARRAY("SELECT * FROM tarjetas.matriz_token"), 'denied', 'privilegio');

CALL prueba.rechaza('X112', 'Extensión', 'bna_api', 'bna_api no puede: SELECT tarjetas.matriz_coordenada',
  JSON_ARRAY("SELECT * FROM tarjetas.matriz_coordenada"), 'denied', 'privilegio');

CALL prueba.rechaza('X113', 'Extensión', 'bna_api', 'bna_api no puede: SELECT tarjetas.token_pago',
  JSON_ARRAY("SELECT * FROM tarjetas.token_pago"), 'denied', 'privilegio');

CALL prueba.rechaza('X114', 'Extensión', 'bna_api', 'bna_api no puede: SELECT clientes.biometria_cliente',
  JSON_ARRAY("SELECT * FROM clientes.biometria_cliente"), 'denied', 'privilegio');

CALL prueba.rechaza('X115', 'Extensión', 'bna_api', 'bna_api no puede: SELECT clientes.codigo_verificacion',
  JSON_ARRAY("SELECT * FROM clientes.codigo_verificacion"), 'denied', 'privilegio');

CALL prueba.rechaza('X116', 'Extensión', 'bna_api', 'bna_api no puede: SELECT tarjetas.tarjeta, con pan_token',
  JSON_ARRAY("SELECT pan_token FROM tarjetas.tarjeta"), 'denied', 'privilegio');

CALL prueba.rechaza('X117', 'Extensión', 'bna_api', 'bna_api no puede: SELECT clientes.cliente',
  JSON_ARRAY("SELECT * FROM clientes.cliente"), 'denied', 'privilegio');

CALL prueba.rechaza('X118', 'Extensión', 'bna_api', 'bna_api no puede: registrar_evento',
  JSON_ARRAY("CALL core.registrar_evento('CORE', 'e', '1', 'FALSO', 'nadie', NULL, NULL)"), 'denied', 'privilegio');

CALL prueba.rechaza('X119', 'Extensión', 'bna_api', 'bna_api no puede: registrar_asiento',
  JSON_ARRAY("CALL core.registrar_asiento(NULL, 'X119', CURRENT_DATE, CURRENT_DATE, 'g', 'PEN', UUID_TO_BIN(UUID()), NULL, JSON_ARRAY(), @a)"), 'denied', 'privilegio');

CALL prueba.rechaza('X120', 'Extensión', 'bna_api', 'bna_api no puede: reservar_llave',
  JSON_ARRAY("CALL cuentas.reservar_llave('k', 'h', @r, @u, @a)"), 'denied', 'privilegio');

CALL prueba.rechaza('X121', 'Extensión', 'bna_api', 'bna_api no puede: aplicar_movimiento',
  JSON_ARRAY("CALL cuentas.aplicar_movimiento('CTA-PEN-1', 'DEPOSITO', 1, 'g', 'VEN', UUID_TO_BIN(UUID()), @u)"), 'denied', 'privilegio');

CALL prueba.rechaza('X122', 'Extensión', 'bna_api', 'bna_api no puede: validar_canal',
  JSON_ARRAY("CALL cuentas.validar_canal('VEN', TRUE)"), 'denied', 'privilegio');

CALL prueba.rechaza('X123', 'Extensión', 'bna_api', 'bna_api no puede: bloquear_tarjeta',
  JSON_ARRAY("CALL tarjetas.bloquear_tarjeta(UUID_TO_BIN(UUID()), 'x', 'OPERADOR', @h)"), 'denied', 'privilegio');

CALL prueba.rechaza('X124', 'Extensión', 'bna_api', 'bna_api no puede: desbloquear_tarjeta',
  JSON_ARRAY("CALL tarjetas.desbloquear_tarjeta(UUID_TO_BIN(UUID()), 'x', 'x', @h)"), 'denied', 'privilegio');

CALL prueba.rechaza('X125', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en historial_estado_tarjeta',
  JSON_ARRAY("INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, origen, id_tarjeta) VALUES ('ACTIVA', 'SEGURIDAD', UUID_TO_BIN(UUID()))"), 'denied', 'privilegio');

CALL prueba.rechaza('X126', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en cuenta_ahorro',
  JSON_ARRAY("INSERT INTO cuentas.cuenta_ahorro (num_cuenta) VALUES ('X')"), 'denied', 'privilegio');

CALL prueba.rechaza('X127', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en titularidad',
  JSON_ARRAY("INSERT INTO cuentas.titularidad (cod_cliente, num_cuenta) VALUES ('C001', 'X')"), 'denied', 'privilegio');

CALL prueba.rechaza('X128', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en movimiento',
  JSON_ARRAY("INSERT INTO cuentas.movimiento (uuid_transaccion) VALUES (UUID_TO_BIN(UUID()))"), 'denied', 'privilegio');

CALL prueba.rechaza('X129', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en tarjeta',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta (id_tarjeta) VALUES (UUID_TO_BIN(UUID()))"), 'denied', 'privilegio');

CALL prueba.rechaza('X130', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en tarjeta_cuenta',
  JSON_ARRAY("INSERT INTO tarjetas.tarjeta_cuenta (id_tarjeta, num_cuenta) VALUES (UUID_TO_BIN(UUID()), 'X')"), 'denied', 'privilegio');

CALL prueba.rechaza('X131', 'Extensión', 'bna_api', 'bna_api no puede: UPDATE de saldos',
  JSON_ARRAY("UPDATE cuentas.cuenta_ahorro SET saldo_contable = 1"), 'denied', 'privilegio');

CALL prueba.rechaza('X132', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en usuario_sistema',
  JSON_ARRAY("INSERT INTO core.usuario_sistema (id_usuario) VALUES (UUID_TO_BIN(UUID()))"), 'denied', 'privilegio');

CALL prueba.rechaza('X133', 'Extensión', 'bna_api', 'bna_api no puede: UPDATE de la bitácora',
  JSON_ARRAY("UPDATE core.evento_auditoria SET actor = 'x'"), 'denied', 'privilegio');

CALL prueba.verifica('X134', 'Extensión', 'bna_api', 'bna_api lee la tarjeta por la vista, sin pan_token',
  JSON_ARRAY("SET @n = (SELECT COUNT(*) FROM tarjetas.v_tarjeta_api)"),
  "SELECT @n >= 1 AND (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'tarjetas' AND table_name = 'v_tarjeta_api' AND column_name = 'pan_token') = 0",
  'filas y sin pan_token', "SELECT @n", 'privilegio');

CALL prueba.verifica('X135', 'Extensión', 'bna_api', 'bna_api lee lo que usa la API',
  JSON_ARRAY("SET @a = (SELECT COUNT(*) FROM core.moneda) + (SELECT COUNT(*) FROM core.agencia) + (SELECT COUNT(*) FROM core.usuario_sistema) + (SELECT COUNT(*) FROM core.producto_ahorro) + (SELECT COUNT(*) FROM core.producto_credito) + (SELECT COUNT(*) FROM core.tipo_cambio) + (SELECT COUNT(*) FROM core.equivalencia_catalogo) + (SELECT COUNT(*) FROM core.periodo_contable) + (SELECT COUNT(*) FROM cuentas.cuenta_ahorro) + (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento)"),
  "SELECT @a > 0", 'lecturas permitidas', "SELECT @a", 'privilegio');

-- ---------------------------------------------------------------------
-- v1.1: usuarios de servicio (autenticación de COREDB)
-- ---------------------------------------------------------------------
SET @srv = UUID_TO_BIN('15000000-0000-4000-8000-000000000001');
SET @hum = UUID_TO_BIN('15000000-0000-4000-8000-000000000002');

CALL prueba.verifica('X150', 'Extensión', 'Usuarios', 'Se crea un usuario de servicio para un módulo',
  JSON_ARRAY("CALL core.crear_usuario_servicio(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), 'svc-clientes', 'Módulo Clientes', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas')"),
  "SELECT rol = 'SERVICIO' AND modulo = 'CLIENTES' AND activo FROM core.usuario_sistema WHERE username = 'svc-clientes'",
  'SERVICIO de CLIENTES, activo', "SELECT CONCAT(rol, ' ', modulo) FROM core.usuario_sistema WHERE username = 'svc-clientes'", 'procedimiento');

CALL prueba.rechaza('X151', 'Extensión', 'Usuarios', 'crear_usuario no crea un usuario de servicio',
  JSON_ARRAY("CALL core.crear_usuario(UUID_TO_BIN(UUID()), 'svc-x151', 'S', 'SERVICIO', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')"),
  'ck_usuario_servicio', 'declarativo');

CALL prueba.rechaza('X152', 'Extensión', 'Usuarios', 'Un usuario de servicio exige un módulo existente',
  JSON_ARRAY("CALL core.crear_usuario_servicio(UUID_TO_BIN(UUID()), 'svc-x152', 'S', 'NOEXISTE', 'h', 'BCRYPT', 'v2', 'pruebas')"),
  'fk_usuario_modulo', 'declarativo');

CALL prueba.verifica('X153', 'Extensión', 'Usuarios', 'Se renueva la credencial de un usuario de servicio',
  JSON_ARRAY("CALL core.crear_usuario_servicio(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), 'svc-clientes', 'S', 'CLIENTES', 'viejo', 'BCRYPT', 'v2', 'pruebas')",
             "CALL core.renovar_credencial(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), 'nuevo', 'BCRYPT', 'v2', 'pruebas', @f)"),
  "SELECT @f = 1 AND (SELECT hash_password FROM core.usuario_sistema WHERE username = 'svc-clientes') = 'nuevo'",
  '1 y hash nuevo', "SELECT @f", 'procedimiento');

CALL prueba.rechaza('X154', 'Extensión', 'Usuarios', 'No se renueva por esta vía la contraseña de una persona',
  JSON_ARRAY("CALL core.crear_usuario(UUID_TO_BIN('15000000-0000-4000-8000-000000000002'), 'ana-x154', 'Ana', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')",
             "CALL core.renovar_credencial(UUID_TO_BIN('15000000-0000-4000-8000-000000000002'), 'nuevo', 'BCRYPT', 'v2', 'pruebas', @f)"),
  '^BNA-USUARIO-SERVICIO:', 'procedimiento');

CALL prueba.rechaza('X155', 'Extensión', 'Usuarios', 'No se renueva la credencial de un usuario inexistente',
  JSON_ARRAY("CALL core.renovar_credencial(UUID_TO_BIN(UUID()), 'nuevo', 'BCRYPT', 'v2', 'pruebas', @f)"),
  '^BNA-USUARIO:', 'procedimiento');

CALL prueba.verifica('X156', 'Extensión', 'Usuarios', 'Desactivar un usuario lo cambia una vez; repetirlo no cambia nada',
  JSON_ARRAY("CALL core.crear_usuario_servicio(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), 'svc-clientes', 'S', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas')",
             "CALL core.cambiar_estado_usuario(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), FALSE, 'pruebas', @f1)",
             "CALL core.cambiar_estado_usuario(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), FALSE, 'pruebas', @f2)"),
  "SELECT @f1 = 1 AND @f2 = 0 AND NOT (SELECT activo FROM core.usuario_sistema WHERE username = 'svc-clientes')",
  '1, 0 e inactivo', "SELECT CONCAT(@f1, ', ', @f2)", 'procedimiento');

CALL prueba.rechaza('X157', 'Extensión', 'Usuarios', 'No se registra el login de un usuario inactivo',
  JSON_ARRAY("CALL core.crear_usuario_servicio(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), 'svc-clientes', 'S', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas')",
             "CALL core.cambiar_estado_usuario(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), FALSE, 'pruebas', @f)",
             "CALL core.registrar_login(UUID_TO_BIN('15000000-0000-4000-8000-000000000001'), UUID_TO_BIN(UUID()))"),
  '^BNA-USUARIO:', 'procedimiento');

CALL prueba.rechaza('X158', 'Extensión', 'Usuarios', 'No se registra el login de un usuario inexistente',
  JSON_ARRAY("CALL core.registrar_login(UUID_TO_BIN(UUID()), UUID_TO_BIN(UUID()))"),
  '^BNA-USUARIO:', 'procedimiento');

CALL prueba.rechaza('X159', 'Extensión', 'Usuarios', 'No se cambia el estado de un usuario inexistente',
  JSON_ARRAY("CALL core.cambiar_estado_usuario(UUID_TO_BIN(UUID()), FALSE, 'pruebas', @f)"),
  '^BNA-USUARIO:', 'procedimiento');

-- ---------------------------------------------------------------------
-- v1.1: registro de clientes
-- ---------------------------------------------------------------------
CALL prueba.verifica('X160', 'Extensión', 'Clientes', 'Un cliente HABILITADO queda ACTIVO con código CLI y nueve dígitos',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000160', 'Prueba', 'Ficticio', 'Uno', 'c160@example.com', '961000160', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)",
             "CALL clientes.consultar_cliente(@c, @j)"),
  "SELECT REGEXP_LIKE(@c, '^CLI[0-9]{9}$', 'c') AND JSON_VALUE(@j, '$.estado_cliente') = 'ACTIVO' AND JSON_VALUE(@j, '$.estado_habilitante') = 'HABILITADO' AND JSON_VALUE(@j, '$.apellido_materno') = 'Uno' AND JSON_VALUE(@j, '$.version_contrato') = 'v1'",
  'CLI######### ACTIVO HABILITADO', "SELECT CONCAT(@c, ' ', JSON_VALUE(@j, '$.estado_cliente'))", 'procedimiento');

CALL prueba.verifica('X161', 'Extensión', 'Clientes', 'Un cliente OBSERVADO queda OBSERVADO',
  JSON_ARRAY("CALL clientes.registrar_cliente('PASAPORTE', 'X1234567', 'Prueba', 'Ficticio', NULL, 'c161@example.com', '961000161', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c)",
             "CALL clientes.consultar_cliente(@c, @j)"),
  "SELECT JSON_VALUE(@j, '$.estado_cliente') = 'OBSERVADO' AND JSON_VALUE(@j, '$.estado_habilitante') = 'OBSERVADO'",
  'OBSERVADO OBSERVADO', "SELECT JSON_VALUE(@j, '$.estado_cliente')", 'procedimiento');

CALL prueba.verifica('X162', 'Extensión', 'Clientes', 'CE, PTP y pasaporte en sus límites se aceptan, con códigos distintos',
  JSON_ARRAY("CALL clientes.registrar_cliente('CE', 'AB1234567', 'Prueba', 'Ficticio', NULL, 'c162a@example.com', '961000162', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c1)",
             "CALL clientes.registrar_cliente('CE', 'AB1234567890', 'Prueba', 'Ficticio', NULL, 'c162b@example.com', '961000163', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c2)",
             "CALL clientes.registrar_cliente('PTP', '123456789', 'Prueba', 'Ficticio', NULL, 'c162c@example.com', '961000164', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c3)",
             "CALL clientes.registrar_cliente('PASAPORTE', 'Z12345', 'Prueba', 'Ficticio', NULL, 'c162d@example.com', '961000165', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c4)"),
  "SELECT @c1 <> @c2 AND @c2 <> @c3 AND @c3 <> @c4 AND @c1 <> @c4",
  'cuatro códigos distintos', "SELECT CONCAT_WS(' ', @c1, @c2, @c3, @c4)", 'procedimiento');

CALL prueba.rechaza('X163', 'Extensión', 'Clientes', 'Un DNI de siete dígitos se rechaza sin repetir el número',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '7100016', 'Prueba', 'Ficticio', NULL, 'c163@example.com', '961000166', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DOCUMENTO: [^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X164', 'Extensión', 'Clientes', 'Un DNI con una letra se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '7100016A', 'Prueba', 'Ficticio', NULL, 'c164@example.com', '961000167', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DOCUMENTO:', 'procedimiento');

CALL prueba.rechaza('X165', 'Extensión', 'Clientes', 'Un PTP con una letra se rechaza (es numérico)',
  JSON_ARRAY("CALL clientes.registrar_cliente('PTP', '12345678A', 'Prueba', 'Ficticio', NULL, 'c165@example.com', '961000168', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DOCUMENTO:', 'procedimiento');

CALL prueba.rechaza('X166', 'Extensión', 'Clientes', 'Un pasaporte en minúsculas se rechaza (la API lo normaliza)',
  JSON_ARRAY("CALL clientes.registrar_cliente('PASAPORTE', 'x12345', 'Prueba', 'Ficticio', NULL, 'c166@example.com', '961000169', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DOCUMENTO:', 'procedimiento');

CALL prueba.rechaza('X167', 'Extensión', 'Clientes', 'Un tipo de documento desconocido se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('LE', '71000167', 'Prueba', 'Ficticio', NULL, 'c167@example.com', '961000170', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DOCUMENTO:', 'procedimiento');

CALL prueba.rechaza('X168', 'Extensión', 'Clientes', 'Un documento ya registrado se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '70000001', 'Prueba', 'Ficticio', NULL, 'c168@example.com', '961000171', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  'uk_cliente_1', 'declarativo');

CALL prueba.rechaza('X169', 'Extensión', 'Clientes', 'Un correo ya registrado se rechaza aunque cambie de mayúsculas',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000169', 'Prueba', 'Ficticio', NULL, 'JUAN@Example.com', '961000172', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  'uk_cliente_2', 'declarativo');

CALL prueba.rechaza('X170', 'Extensión', 'Clientes', 'Un celular ya registrado se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000170', 'Prueba', 'Ficticio', NULL, 'c170@example.com', '959000001', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  'uk_cliente_3', 'declarativo');

CALL prueba.rechaza('X171', 'Extensión', 'Clientes', 'Un celular que no empieza en 9 se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000171', 'Prueba', 'Ficticio', NULL, 'c171@example.com', '861000171', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  'ck_cliente_1', 'declarativo');

CALL prueba.rechaza('X172', 'Extensión', 'Clientes', 'La versión del contrato en blanco se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000172', 'Prueba', 'Ficticio', NULL, 'c172@example.com', '961000173', '  ', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DATOS-CLIENTE:', 'procedimiento');

CALL prueba.rechaza('X173', 'Extensión', 'Clientes', 'Los nombres en blanco se rechazan',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000173', ' ', 'Ficticio', NULL, 'c173@example.com', '961000174', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DATOS-CLIENTE:', 'procedimiento');

CALL prueba.rechaza('X174', 'Extensión', 'Clientes', 'Un correo sin arroba se rechaza sin repetirlo',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000174', 'Prueba', 'Ficticio', NULL, 'c174.example.com', '961000175', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DATOS-CLIENTE: [^@]*$', 'procedimiento');

CALL prueba.rechaza('X175', 'Extensión', 'Clientes', 'El registro exige correlation_id',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000175', 'Prueba', 'Ficticio', NULL, 'c175@example.com', '961000176', 'v1', 'HABILITADO', NULL, 'pruebas', @c)"),
  '^BNA-DATOS-CLIENTE:', 'procedimiento');

CALL prueba.rechaza('X176', 'Extensión', 'Clientes', 'Un estado habilitante desconocido se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000176', 'Prueba', 'Ficticio', NULL, 'c176@example.com', '961000177', 'v1', 'APROBADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DATOS-CLIENTE:', 'procedimiento');

CALL prueba.rechaza('X177', 'Extensión', 'Clientes', 'El apellido paterno en blanco se rechaza',
  JSON_ARRAY("CALL clientes.registrar_cliente('DNI', '71000177', 'Prueba', '', NULL, 'c177@example.com', '961000178', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c)"),
  '^BNA-DATOS-CLIENTE:', 'procedimiento');

CALL prueba.verifica('X178', 'Extensión', 'Clientes', 'La consulta por código no devuelve biometría y un código inexistente da NULL',
  JSON_ARRAY("CALL clientes.consultar_cliente('C001', @j)", "CALL clientes.consultar_cliente('NOEXISTE', @n)"),
  "SELECT @n IS NULL AND JSON_VALUE(@j, '$.cod_cliente') = 'C001' AND JSON_VALUE(@j, '$.numero_documento') = '70000001' AND JSON_CONTAINS_PATH(@j, 'one', '$.datos_biometricos', '$.biometria') = 0 AND JSON_VALUE(@j, '$.permite_operar' RETURNING CHAR) = 'true'",
  'C001 sin biometría; NULL', "SELECT JSON_KEYS(@j)", 'procedimiento');

CALL prueba.verifica('X179', 'Extensión', 'Clientes', 'Los catálogos traen los cuatro tipos de documento y los cinco estados',
  JSON_ARRAY("CALL clientes.catalogos_cliente(@k)"),
  "SELECT JSON_LENGTH(@k, '$.tipos_documento') = 4 AND JSON_LENGTH(@k, '$.estados_cliente') = 5 AND JSON_CONTAINS(@k, JSON_OBJECT('codigo', 'PTP', 'longitud_min', 9, 'longitud_max', 9), '$.tipos_documento')",
  '4 y 5', "SELECT CONCAT(JSON_LENGTH(@k, '$.tipos_documento'), ' y ', JSON_LENGTH(@k, '$.estados_cliente'))", 'procedimiento');

-- ---------------------------------------------------------------------
-- v1.1: verificación por documento (hallazgo 4 de la revisión del PR 25)
-- ---------------------------------------------------------------------
CALL prueba.verifica('X180', 'Extensión', 'Clientes', 'Sin identidad verificada, cliente y no cliente reciben la misma respuesta',
  JSON_ARRAY("CALL clientes.verificar_documento('DNI', '70000001', FALSE, 'RENIEC_NO_COINCIDE', UUID_TO_BIN(UUID()), 'pruebas', @i1, @r1, @m1, @j1)",
             "CALL clientes.verificar_documento('DNI', '71999999', FALSE, 'RENIEC_NO_COINCIDE', UUID_TO_BIN(UUID()), 'pruebas', @i2, @r2, @m2, @j2)"),
  "SELECT @i1 IS NOT NULL AND @i2 IS NOT NULL AND @r1 = 'RECHAZADO' AND @r2 = 'RECHAZADO' AND @m1 = 'IDENTIDAD_NO_VERIFICADA' AND @m2 = @m1 AND @j1 IS NULL AND @j2 IS NULL",
  'RECHAZADO IDENTIDAD_NO_VERIFICADA sin cliente, en los dos', "SELECT CONCAT_WS(' ', @r1, @m1, @j1, '|', @r2, @m2, @j2)", 'procedimiento');

CALL prueba.verifica('X181', 'Extensión', 'Clientes', 'Con identidad verificada, un cliente ACTIVO se aprueba',
  JSON_ARRAY("CALL clientes.verificar_documento('DNI', '70000001', TRUE, NULL, UUID_TO_BIN(UUID()), 'pruebas', @i, @r, @m, @j)"),
  "SELECT @r = 'APROBADO' AND @m IS NULL AND JSON_VALUE(@j, '$.cod_cliente') = 'C001'",
  'APROBADO C001', "SELECT CONCAT_WS(' ', @r, @m, JSON_VALUE(@j, '$.cod_cliente'))", 'procedimiento');

CALL prueba.verifica('X182', 'Extensión', 'Clientes', 'Con identidad verificada, un cliente BLOQUEADO se rechaza y se informa su estado',
  JSON_ARRAY("CALL clientes.verificar_documento('DNI', '70000004', TRUE, NULL, UUID_TO_BIN(UUID()), 'pruebas', @i, @r, @m, @j)"),
  "SELECT @r = 'RECHAZADO' AND @m = 'CLIENTE_NO_ACTIVO' AND JSON_VALUE(@j, '$.estado_cliente') = 'BLOQUEADO'",
  'RECHAZADO CLIENTE_NO_ACTIVO BLOQUEADO', "SELECT CONCAT_WS(' ', @r, @m, JSON_VALUE(@j, '$.estado_cliente'))", 'procedimiento');

CALL prueba.verifica('X183', 'Extensión', 'Clientes', 'Con identidad verificada, un documento sin cliente se rechaza sin datos',
  JSON_ARRAY("CALL clientes.verificar_documento('DNI', '71999999', TRUE, NULL, UUID_TO_BIN(UUID()), 'pruebas', @i, @r, @m, @j)"),
  "SELECT @r = 'RECHAZADO' AND @m = 'NO_ES_CLIENTE' AND @j IS NULL",
  'RECHAZADO NO_ES_CLIENTE', "SELECT CONCAT_WS(' ', @r, @m, @j)", 'procedimiento');

CALL prueba.verifica('X184', 'Extensión', 'Clientes', 'Un cliente OBSERVADO no se aprueba (RF-CLI-001 exige ACTIVO)',
  JSON_ARRAY("CALL clientes.registrar_cliente('PASAPORTE', 'Y7654321', 'Prueba', 'Ficticio', NULL, 'c184@example.com', '961000184', 'v1', 'OBSERVADO', UUID_TO_BIN(UUID()), 'pruebas', @c)",
             "CALL clientes.verificar_documento('PASAPORTE', 'Y7654321', TRUE, NULL, UUID_TO_BIN(UUID()), 'pruebas', @i, @r, @m, @j)"),
  "SELECT @r = 'RECHAZADO' AND @m = 'CLIENTE_NO_ACTIVO'",
  'RECHAZADO CLIENTE_NO_ACTIVO', "SELECT CONCAT_WS(' ', @r, @m)", 'procedimiento');

CALL prueba.rechaza('X185', 'Extensión', 'Clientes', 'La verificación exige correlation_id',
  JSON_ARRAY("CALL clientes.verificar_documento('DNI', '70000001', TRUE, NULL, NULL, 'pruebas', @i, @r, @m, @j)"),
  '^BNA-VALIDACION:', 'procedimiento');

CALL prueba.rechaza('X186', 'Extensión', 'Clientes', 'La verificación exige declarar si la identidad se verificó',
  JSON_ARRAY("CALL clientes.verificar_documento('DNI', '70000001', NULL, NULL, UUID_TO_BIN(UUID()), 'pruebas', @i, @r, @m, @j)"),
  '^BNA-VALIDACION:', 'procedimiento');

-- ---------------------------------------------------------------------
-- v1.1: otras validaciones de identidad
-- ---------------------------------------------------------------------
CALL prueba.verifica('X187', 'Extensión', 'Clientes', 'Se registra una validación dactilar de un cliente',
  JSON_ARRAY("CALL clientes.registrar_validacion('C001', 'HUELLA', 'APROBADO', NULL, UUID_TO_BIN(UUID()), 'pruebas', @i)"),
  "SELECT @i IS NOT NULL", 'identificador', "SELECT @i", 'procedimiento');

CALL prueba.rechaza('X188', 'Extensión', 'Clientes', 'La validación de documento no se registra por esta vía',
  JSON_ARRAY("CALL clientes.registrar_validacion('C001', 'DOCUMENTO', 'APROBADO', NULL, UUID_TO_BIN(UUID()), 'pruebas', @i)"),
  '^BNA-VALIDACION:', 'procedimiento');

CALL prueba.rechaza('X189', 'Extensión', 'Clientes', 'Una validación de un cliente inexistente se rechaza',
  JSON_ARRAY("CALL clientes.registrar_validacion('NOEXISTE', 'HUELLA', 'APROBADO', NULL, UUID_TO_BIN(UUID()), 'pruebas', @i)"),
  '^BNA-CLIENTE:', 'procedimiento');

CALL prueba.rechaza('X190', 'Extensión', 'Clientes', 'Un resultado desconocido se rechaza',
  JSON_ARRAY("CALL clientes.registrar_validacion('C001', 'HUELLA', 'QUIZAS', NULL, UUID_TO_BIN(UUID()), 'pruebas', @i)"),
  '^BNA-VALIDACION:', 'procedimiento');

CALL prueba.rechaza('X191', 'Extensión', 'Clientes', 'Un tipo de validación desconocido se rechaza',
  JSON_ARRAY("CALL clientes.registrar_validacion('C001', 'IRIS', 'APROBADO', NULL, UUID_TO_BIN(UUID()), 'pruebas', @i)"),
  'fk_validacion_identidad_1', 'declarativo');

-- ---------------------------------------------------------------------
-- v1.1: estado del cliente
-- ---------------------------------------------------------------------
CALL prueba.verifica('X192', 'Extensión', 'Clientes', 'Bloquear un cliente con motivo bloquea su tarjeta activa',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('C003', 'BLOQUEADO', 'Investigación de fraude', 'pruebas', @a)",
             "CALL clientes.consultar_cliente('C003', @j)"),
  "SELECT @a = 'ACTIVO' AND JSON_VALUE(@j, '$.estado_cliente') = 'BLOQUEADO' AND (SELECT estado_tarjeta FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003')) = 'BLOQUEADA'",
  'ACTIVO -> BLOQUEADO, tarjeta BLOQUEADA', "SELECT CONCAT_WS(' ', @a, JSON_VALUE(@j, '$.estado_cliente'), (SELECT estado_tarjeta FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003')))", 'procedimiento');

CALL prueba.verifica('X193', 'Extensión', 'Clientes', 'Dar de baja un cliente cancela su tarjeta',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('C003', 'BAJA', 'Solicitud del cliente', 'pruebas', @a)"),
  "SELECT (SELECT estado_tarjeta FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003')) = 'CANCELADA'",
  'tarjeta CANCELADA', "SELECT estado_tarjeta FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003')", 'procedimiento');

CALL prueba.rechaza('X194', 'Extensión', 'Clientes', 'El cambio de estado exige un motivo',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('C003', 'BLOQUEADO', '  ', 'pruebas', @a)"),
  '^BNA-MOTIVO:', 'procedimiento');

CALL prueba.rechaza('X195', 'Extensión', 'Clientes', 'BAJA es final: un cliente dado de baja no vuelve a ACTIVO',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('C003', 'BAJA', 'Solicitud del cliente', 'pruebas', @a)",
             "CALL clientes.cambiar_estado_cliente('C003', 'ACTIVO', 'Error', 'pruebas', @a)"),
  '^BNA-ESTADO:', 'procedimiento');

CALL prueba.rechaza('X196', 'Extensión', 'Clientes', 'No se cambia el estado de un cliente inexistente',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('NOEXISTE', 'BLOQUEADO', 'x', 'pruebas', @a)"),
  '^BNA-CLIENTE:', 'procedimiento');

CALL prueba.rechaza('X197', 'Extensión', 'Clientes', 'Un estado desconocido se rechaza',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('C003', 'CONGELADO', 'x', 'pruebas', @a)"),
  '^BNA-ESTADO:', 'procedimiento');

CALL prueba.verifica('X198', 'Extensión', 'Clientes', 'Reactivar un cliente no desbloquea sus tarjetas (lo hace Seguridad)',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('C003', 'BLOQUEADO', 'Investigación', 'pruebas', @a1)",
             "CALL clientes.cambiar_estado_cliente('C003', 'ACTIVO', 'Investigación cerrada', 'pruebas', @a2)",
             "CALL clientes.consultar_cliente('C003', @j)"),
  "SELECT @a2 = 'BLOQUEADO' AND JSON_VALUE(@j, '$.estado_cliente') = 'ACTIVO' AND (SELECT estado_tarjeta FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003')) = 'BLOQUEADA'",
  'cliente ACTIVO, tarjeta BLOQUEADA', "SELECT (SELECT estado_tarjeta FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'))", 'procedimiento');

CALL prueba.verifica('X199', 'Extensión', 'Clientes', 'El mismo estado no cambia nada y devuelve el actual',
  JSON_ARRAY("CALL clientes.cambiar_estado_cliente('C001', 'ACTIVO', 'Sin cambio', 'pruebas', @a)",
             "CALL clientes.consultar_cliente('C001', @j)"),
  "SELECT @a = 'ACTIVO' AND JSON_VALUE(@j, '$.estado_cliente') = 'ACTIVO'",
  'ACTIVO', "SELECT @a", 'procedimiento');

-- ---------------------------------------------------------------------
-- v1.1: permisos de bna_api sobre clientes
-- ---------------------------------------------------------------------
CALL prueba.rechaza('X200', 'Extensión', 'bna_api', 'bna_api no puede: SELECT clientes.validacion_identidad',
  JSON_ARRAY("SELECT * FROM clientes.validacion_identidad"), 'denied', 'privilegio');

CALL prueba.rechaza('X201', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en clientes.cliente',
  JSON_ARRAY("INSERT INTO clientes.cliente (cod_cliente) VALUES ('X201')"), 'denied', 'privilegio');

CALL prueba.rechaza('X202', 'Extensión', 'bna_api', 'bna_api no puede: UPDATE del estado del cliente',
  JSON_ARRAY("UPDATE clientes.cliente SET estado_cliente = 'BAJA'"), 'denied', 'privilegio');

CALL prueba.rechaza('X203', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en clientes.numerador_cliente',
  JSON_ARRAY("INSERT INTO clientes.numerador_cliente () VALUES ()"), 'denied', 'privilegio');

CALL prueba.rechaza('X204', 'Extensión', 'bna_api', 'bna_api no puede: UPDATE de usuario_sistema',
  JSON_ARRAY("UPDATE core.usuario_sistema SET rol = 'ADMINISTRADOR'"), 'denied', 'privilegio');

-- ---------------------------------------------------------------------
-- v1.2: lecturas de consulta de la API (movimientos, titulares y bitácora)
-- ---------------------------------------------------------------------
CALL prueba.verifica('X235', 'Extensión', 'Consultas', 'bna_api lee el movimiento de un depósito, con su naturaleza y la moneda de la cuenta',
  JSON_ARRAY("CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 25, 'Depósito X235', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r)"),
  "SELECT COUNT(*) = 1 FROM cuentas.v_movimiento_api WHERE uuid_transaccion = @m AND num_cuenta = 'CTA-PEN-1' AND tipo_operacion = 'DEPOSITO' AND naturaleza = 'C' AND monto = 25 AND moneda = 'PEN' AND glosa = 'Depósito X235' AND id_canal = 'VEN' AND estado_transaccion = 'APROBADO' AND fecha_hora IS NOT NULL",
  'una fila', "SELECT COUNT(*) FROM cuentas.v_movimiento_api WHERE uuid_transaccion = @m", 'vista');

CALL prueba.verifica('X236', 'Extensión', 'Consultas', 'Una transferencia se lee como un débito en el origen y un abono en el destino',
  JSON_ARRAY("CALL cuentas.registrar_transferencia('CTA-PEN-2', 'CTA-PEN-1', 40, 'Transferencia X236', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @d, @c, @r)"),
  "SELECT (SELECT CONCAT(num_cuenta, ' ', tipo_operacion, ' ', naturaleza) FROM cuentas.v_movimiento_api WHERE uuid_transaccion = @d) = 'CTA-PEN-2 TRANSFERENCIA_ENVIADA D' AND (SELECT CONCAT(num_cuenta, ' ', tipo_operacion, ' ', naturaleza) FROM cuentas.v_movimiento_api WHERE uuid_transaccion = @c) = 'CTA-PEN-1 TRANSFERENCIA_RECIBIDA C'",
  'ENVIADA D y RECIBIDA C', "SELECT GROUP_CONCAT(CONCAT(num_cuenta, ' ', tipo_operacion, ' ', naturaleza) ORDER BY naturaleza DESC SEPARATOR '; ') FROM cuentas.v_movimiento_api WHERE uuid_transaccion IN (@d, @c)", 'vista');

CALL prueba.rechaza('X237', 'Extensión', 'Consultas', 'La vista de movimientos no expone el asiento contable',
  JSON_ARRAY("SELECT id_asiento FROM cuentas.v_movimiento_api"), 'Unknown column', 'vista');

CALL prueba.rechaza('X238', 'Extensión', 'bna_api', 'bna_api no puede: SELECT cuentas.movimiento',
  JSON_ARRAY("SELECT * FROM cuentas.movimiento"), 'denied', 'privilegio');

CALL prueba.verifica('X239', 'Extensión', 'Consultas', 'bna_api lee las cuentas de un titular',
  JSON_ARRAY("SET @cuentas = (SELECT GROUP_CONCAT(num_cuenta ORDER BY num_cuenta) FROM cuentas.titularidad WHERE cod_cliente = 'C002')"),
  "SELECT @cuentas = 'CTA-CONJ,CTA-PEN-2'",
  'CTA-CONJ,CTA-PEN-2', "SELECT @cuentas", 'privilegio');

CALL prueba.verifica('X240', 'Extensión', 'Consultas', 'bna_api lee la bitácora por la vista, con el nombre del módulo y el evento de la operación',
  JSON_ARRAY("SET @correlacion = UUID_TO_BIN(UUID())",
             "CALL cuentas.registrar_movimiento('CTA-PEN-1', 'DEPOSITO', 30, 'Depósito X240', 'VEN', @correlacion, NULL, NULL, 'pruebas', @m, @r)"),
  "SELECT COUNT(*) = 1 FROM core.v_evento_auditoria_api WHERE correlation_id = @correlacion AND modulo = 'CUENTAS' AND actor = 'pruebas' AND accion IS NOT NULL AND entidad IS NOT NULL AND id_entidad IS NOT NULL AND fecha_hora IS NOT NULL AND id_evento > 0",
  'un evento de CUENTAS', "SELECT CONCAT(COUNT(*), ' ', IFNULL(GROUP_CONCAT(modulo), '')) FROM core.v_evento_auditoria_api WHERE correlation_id = @correlacion", 'vista');

CALL prueba.verifica('X241', 'Extensión', 'Consultas', 'La vista de la bitácora tiene exactamente las columnas acordadas',
  JSON_ARRAY("SET @columnas = (SELECT GROUP_CONCAT(column_name ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema = 'core' AND table_name = 'v_evento_auditoria_api')"),
  "SELECT @columnas = 'id_evento,modulo,entidad,id_entidad,accion,actor,correlation_id,detalle,fecha_hora'",
  'id_evento,modulo,entidad,id_entidad,accion,actor,correlation_id,detalle,fecha_hora', "SELECT @columnas", 'vista');

CALL prueba.rechaza('X242', 'Extensión', 'bna_api', 'bna_api no puede: SELECT core.evento_auditoria',
  JSON_ARRAY("SELECT * FROM core.evento_auditoria"), 'denied', 'privilegio');

CALL prueba.rechaza('X243', 'Extensión', 'bna_api', 'bna_api no puede: escribir por la vista de la bitácora',
  JSON_ARRAY("UPDATE core.v_evento_auditoria_api SET actor = 'x'"), 'denied', 'privilegio');

CALL prueba.rechaza('X244', 'Extensión', 'bna_api', 'bna_api no puede: borrar por la vista de movimientos',
  JSON_ARRAY("DELETE FROM cuentas.v_movimiento_api"), 'denied', 'privilegio');

CALL prueba.rechaza('X245', 'Extensión', 'bna_api', 'bna_api no puede: escribir en cuentas.titularidad',
  JSON_ARRAY("INSERT INTO cuentas.titularidad (cod_cliente, num_cuenta) VALUES ('C003', 'CTA-PEN-1')"), 'denied', 'privilegio');

-- ---------------------------------------------------------------------
-- v1.3: la cuenta principal de una tarjeta (idempotencia de la emisión, issue #52)
-- ---------------------------------------------------------------------
CALL prueba.verifica('X246', 'Extensión', 'Consultas', 'La vista de tarjetas tiene exactamente las columnas acordadas',
  JSON_ARRAY("SET @columnas = (SELECT GROUP_CONCAT(column_name ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema = 'tarjetas' AND table_name = 'v_tarjeta_api')"),
  "SELECT @columnas = 'id_tarjeta,bin,ultimos4,fecha_emision,fecha_vencimiento,estado_tarjeta,cod_cliente,num_cuenta'",
  'id_tarjeta,bin,ultimos4,fecha_emision,fecha_vencimiento,estado_tarjeta,cod_cliente,num_cuenta', "SELECT @columnas", 'vista');

CALL prueba.verifica('X247', 'Extensión', 'Consultas', 'bna_api lee la cuenta principal de una tarjeta: una fila por tarjeta, NULL si no tiene cuenta',
  JSON_ARRAY("SET @principal = (SELECT GROUP_CONCAT(IFNULL(num_cuenta, 'NULL')) FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))",
             "SET @sin_cuenta = (SELECT GROUP_CONCAT(IFNULL(num_cuenta, 'NULL')) FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'))"),
  "SELECT @principal = 'CTA-PEN-1' AND @sin_cuenta = 'NULL'",
  'CTA-PEN-1 y NULL', "SELECT CONCAT_WS(' ', @principal, @sin_cuenta)", 'privilegio');

CALL prueba.verifica('X248', 'Extensión', 'Consultas', 'Una tarjeta emitida por el procedimiento muestra su cuenta en la vista',
  JSON_ARRAY("CALL tarjetas.emitir_tarjeta(UUID_TO_BIN('a0000000-0000-4000-8000-000000000248'), 'tok-0248', '455788', '0248', CURRENT_DATE, DATE_ADD(CURRENT_DATE, INTERVAL 4 YEAR), 'C002', 'CTA-PEN-2', 'pruebas')"),
  "SELECT num_cuenta = 'CTA-PEN-2' FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000248')",
  'CTA-PEN-2', "SELECT IFNULL(num_cuenta, 'NULL') FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000248')", 'procedimiento');

-- ---------------------------------------------------------------------
-- v1.4: créditos (solicitud, evaluación, desembolso y cobranza)
-- ---------------------------------------------------------------------
-- Ayudantes de pruebas/mysql/arnes_creditos.sql. Los mensajes de los procedimientos
-- nuevos no llevan cifras: así no repiten cuentas, documentos ni cod_cliente, y los
-- patrones lo comprueban con [^0-9]*$.

-- Registro del expediente de SOL
CALL prueba.verifica('X249', 'Extensión', 'Créditos', 'Un expediente nuevo queda EN_EVALUACION con su calendario PRELIMINAR y el id de evaluación determinista',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000249', 'C001', 3000, 3, 1, NULL, @ronda, @eval)"),
  "SELECT @ronda = 1 AND @eval = creditos.fn_id_evaluacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000249'), 1) AND @cr_repetido = FALSE AND (SELECT CONCAT(estado_solicitud, ' ', version_solicitud, ' ', ronda, ' ', tipo_calendario, ' ', numero_cuotas, ' ', total_cuotas) FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000249')) = 'EN_EVALUACION 1 1 PRELIMINAR 3 3030.00'",
  'EN_EVALUACION 1 1 PRELIMINAR 3 3030.00', "SELECT CONCAT(estado_solicitud, ' ', version_solicitud, ' ', ronda, ' ', tipo_calendario, ' ', numero_cuotas, ' ', total_cuotas) FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000249')", 'procedimiento');

CALL prueba.verifica('X250', 'Extensión', 'Créditos', 'Repetir la misma versión con el mismo contenido devuelve lo mismo y no crea otro calendario',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000250', 'C001', 3000, 3, 1, NULL, @r1, @e1)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000250', 'C001', 3000, 3, 1, NULL, @r2, @e2)"),
  "SELECT @cr_repetido = TRUE AND @r1 = @r2 AND @e1 = @e2 AND (SELECT COUNT(DISTINCT id_calendario) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000250')) = 1",
  'repetido, un calendario', "SELECT CONCAT(@cr_repetido, ' ', (SELECT COUNT(DISTINCT id_calendario) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000250')))", 'procedimiento');

CALL prueba.rechaza('X251', 'Extensión', 'Créditos', 'La misma versión con otro contenido se rechaza',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000251', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL prueba.cr_calendario(3000, 3, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)",
             "CALL creditos.registrar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000251'), 1, 'C001', 3000, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('z', 64), 'pruebas', UUID_TO_BIN(UUID()), @r, @e, @rep)"),
  '^BNA-IDEMPOTENCIA:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X252', 'Extensión', 'Créditos', 'Una versión nueva antes de evaluar abre la ronda 2 con su calendario; el anterior queda HISTORICO',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000252', 'C001', 3000, 3, 1, NULL, @r1, @e1)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000252', 'C001', 4000, 4, 2, NULL, @r2, @e2)"),
  "SELECT @r2 = 2 AND @e2 = creditos.fn_id_evaluacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000252'), 2) AND (SELECT CONCAT(version_solicitud, ' ', ronda, ' ', monto_solicitado, ' ', plazo_meses, ' ', numero_cuotas) FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000252')) = '2 2 4000.00 4 4' AND (SELECT GROUP_CONCAT(DISTINCT CONCAT(version, estado_calendario) ORDER BY version) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000252')) = '1HISTORICO,2VIGENTE'",
  'ronda 2; 1HISTORICO,2VIGENTE', "SELECT (SELECT GROUP_CONCAT(DISTINCT CONCAT(version, estado_calendario) ORDER BY version) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000252'))", 'procedimiento');

CALL prueba.rechaza('X253', 'Extensión', 'Créditos', 'No se acepta una versión nueva cuando la ronda ya se evaluó',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000253', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000253'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000253', 'C001', 3000, 3, 2, NULL, @r, @e)"),
  '^BNA-SOLICITUD:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X254', 'Extensión', 'Créditos', 'Un expediente de un cliente inexistente se rechaza sin repetir el código',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000254', 'C999', 3000, 3, 1, NULL, @r, @e)"),
  '^BNA-CLIENTE:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X255', 'Extensión', 'Créditos', 'Un expediente de un cliente que no puede operar se rechaza',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000255', 'C004', 3000, 3, 1, NULL, @r, @e)"),
  '^BNA-CLIENTE:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X256', 'Extensión', 'Créditos', 'Un calendario con cuotas no consecutivas se rechaza',
  JSON_ARRAY("CALL prueba.cr_calendario(3000, 3, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)",
             "SET @cuotas = JSON_SET(@cuotas, '$[1].numero_cuota', 5)",
             "CALL creditos.registrar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000256'), 1, 'C001', 3000, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('a', 64), 'pruebas', UUID_TO_BIN(UUID()), @r, @e, @rep)"),
  '^BNA-CALENDARIO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X257', 'Extensión', 'Créditos', 'Un calendario que no amortiza el monto solicitado se rechaza',
  JSON_ARRAY("CALL prueba.cr_calendario(3000, 3, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)",
             "CALL creditos.registrar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000257'), 1, 'C001', 3500, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('a', 64), 'pruebas', UUID_TO_BIN(UUID()), @r, @e, @rep)"),
  '^BNA-CALENDARIO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X258', 'Extensión', 'Créditos', 'Un calendario con más cuotas que meses de plazo se rechaza',
  JSON_ARRAY("CALL prueba.cr_calendario(3000, 4, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)",
             "CALL creditos.registrar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000258'), 1, 'C001', 3000, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('a', 64), 'pruebas', UUID_TO_BIN(UUID()), @r, @e, @rep)"),
  '^BNA-CALENDARIO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X259', 'Extensión', 'Créditos', 'Una versión anterior a la vigente se rechaza',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000259', 'C001', 3000, 3, 3, NULL, @r, @e)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000259', 'C001', 3000, 3, 2, NULL, @r, @e)"),
  '^BNA-SOLICITUD:[^0-9]*$', 'procedimiento');

-- Evaluación (RN-EVA-002-P: los umbrales salen de creditos.regla_evaluacion)
CALL prueba.verifica('X260', 'Extensión', 'Créditos', 'Ratio hasta 80 %: R-A, APROBADO y la solicitud APROBADA, con la evaluación en el id determinista',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000260', 'C001', 3000, 3, 1, NULL, @r, @e0)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000260'), 1, 20000, 0, 850, 30000, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  "SELECT @e = @e0 AND @res = 'APROBADO' AND @regla = 'R-A' AND (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000260')) = 'APROBADA' AND (SELECT COUNT(*) FROM creditos.v_historial_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000260') AND estado_nuevo = 'APROBADA' AND actor = 'pruebas') = 1",
  'APROBADO R-A APROBADA', "SELECT CONCAT_WS(' ', @res, @regla, (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000260')))", 'procedimiento');

CALL prueba.verifica('X261', 'Extensión', 'Créditos', 'Ratio entre 80 % y 100 %: R-B, OBSERVADO y la solicitud sigue EN_EVALUACION',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000261', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000261'), 1, 20000, 0, 650, 3333.33, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  "SELECT @res = 'OBSERVADO' AND @regla = 'R-B' AND (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000261')) = 'EN_EVALUACION'",
  'OBSERVADO R-B EN_EVALUACION', "SELECT CONCAT_WS(' ', @res, @regla, (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000261')))", 'procedimiento');

CALL prueba.verifica('X262', 'Extensión', 'Créditos', 'Ratio mayor que 100 %: R-C, RECHAZADO y la solicitud RECHAZADA',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000262', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000262'), 1, 2000, 500, 400, 2999.99, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  "SELECT @res = 'RECHAZADO' AND @regla = 'R-C' AND (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000262')) = 'RECHAZADA'",
  'RECHAZADO R-C RECHAZADA', "SELECT CONCAT_WS(' ', @res, @regla)", 'procedimiento');

CALL prueba.verifica('X263', 'Extensión', 'Créditos', 'Sin capacidad (límite cero): R-C',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000263', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000263'), 1, 1000, 900, 400, 0, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  "SELECT @res = 'RECHAZADO' AND @regla = 'R-C'", 'RECHAZADO R-C', "SELECT CONCAT_WS(' ', @res, @regla)", 'procedimiento');

CALL prueba.verifica('X264', 'Extensión', 'Créditos', 'Ratio exactamente 80 %: R-A',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000264', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000264'), 1, 20000, 0, 850, 3750, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  "SELECT @regla = 'R-A'", 'R-A', "SELECT @regla", 'procedimiento');

CALL prueba.verifica('X265', 'Extensión', 'Créditos', 'Ratio exactamente 100 %: R-B',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000265', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000265'), 1, 20000, 0, 650, 3000, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  "SELECT @regla = 'R-B'", 'R-B', "SELECT @regla", 'procedimiento');

CALL prueba.rechaza('X266', 'Extensión', 'Créditos', 'Una ronda se evalúa una sola vez',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000266', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000266'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000266'), 1, 20000, 0, 850, 30000, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  '^BNA-EVALUACION:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X267', 'Extensión', 'Créditos', 'No se evalúa una versión que no es la vigente',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000267', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000267', 'C001', 3000, 3, 2, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000267'), 1, 20000, 0, 850, 30000, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  '^BNA-SOLICITUD:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X268', 'Extensión', 'Créditos', 'La evaluación guarda la situación financiera verificada y el score',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000268', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000268'), 1, 5000, 250, 650, 30000, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)"),
  "SELECT CONCAT_WS(' ', ingreso_mensual, deuda_reportada, resultado_verificacion, score_calculado, limite_aprobado, resultado_regla, resultado, ronda) = '5000.00 250.00 VERIFICADO 650.00 30000.00 APROBADO APROBADO 1' FROM creditos.v_evaluacion_api WHERE id_evaluacion = @e",
  '5000.00 250.00 VERIFICADO 650.00 30000.00 APROBADO APROBADO 1', "SELECT CONCAT_WS(' ', ingreso_mensual, deuda_reportada, resultado_verificacion, score_calculado, limite_aprobado, resultado_regla, resultado, ronda) FROM creditos.v_evaluacion_api WHERE id_evaluacion = @e", 'procedimiento');

-- Analista y decisión (solo APROBADO o RECHAZADO, y solo sobre R-B)
CALL prueba.verifica('X269', 'Extensión', 'Créditos', 'Un administrador registra a un empleado activo como analista',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'pruebas', @an)"),
  "SELECT @an REGEXP '^AN[0-9A-F]{8}$' AND (SELECT COUNT(*) FROM creditos.v_evaluacion_api) >= 0",
  'AN y ocho caracteres', "SELECT @an", 'procedimiento');

CALL prueba.rechaza('X270', 'Extensión', 'Créditos', 'Un empleado inactivo no se registra como analista',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000003'), 'pruebas', @an)"),
  '^BNA-EMPLEADO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X271', 'Extensión', 'Créditos', 'Un empleado inexistente no se registra como analista',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN(UUID()), 'pruebas', @an)"),
  '^BNA-EMPLEADO:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X272', 'Extensión', 'Créditos', 'El analista aprueba una evaluación R-B: decisión, analista y solicitud APROBADA',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'pruebas', @an)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000272', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000272'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.decidir_evaluacion(@e, 'APROBADO', 'Ingresos estables y sustentados', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', UUID_TO_BIN(UUID()), @estado)"),
  "SELECT @estado = 'APROBADA' AND (SELECT CONCAT_WS(' ', decision, id_analista, resultado) FROM creditos.v_evaluacion_api WHERE id_evaluacion = @e) = CONCAT_WS(' ', 'APROBADO', @an, 'APROBADO') AND (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000272')) = 'APROBADA'",
  'APROBADO, analista, APROBADA', "SELECT CONCAT_WS(' ', @estado, (SELECT CONCAT_WS(' ', decision, id_analista, resultado) FROM creditos.v_evaluacion_api WHERE id_evaluacion = @e))", 'procedimiento');

CALL prueba.verifica('X273', 'Extensión', 'Créditos', 'El analista rechaza una evaluación R-B: solicitud RECHAZADA',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'pruebas', @an)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000273', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000273'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.decidir_evaluacion(@e, 'RECHAZADO', 'Endeudamiento alto en otras entidades', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', UUID_TO_BIN(UUID()), @estado)"),
  "SELECT @estado = 'RECHAZADA' AND (SELECT resultado FROM creditos.v_evaluacion_api WHERE id_evaluacion = @e) = 'RECHAZADO'",
  'RECHAZADA', "SELECT @estado", 'procedimiento');

CALL prueba.rechaza('X274', 'Extensión', 'Créditos', 'No se decide sobre una evaluación R-A',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'pruebas', @an)",
             "CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000274', 'C001', 3000, 3, NULL, @e)",
             "CALL creditos.decidir_evaluacion(@e, 'RECHAZADO', 'Cambio de criterio del analista', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-EVALUACION:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X275', 'Extensión', 'Créditos', 'Una evaluación R-B se decide una sola vez',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'pruebas', @an)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000275', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000275'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.decidir_evaluacion(@e, 'APROBADO', 'Ingresos estables y sustentados', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', UUID_TO_BIN(UUID()), @estado)",
             "CALL creditos.decidir_evaluacion(@e, 'RECHAZADO', 'Ingresos estables y sustentados', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-EVALUACION:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X276', 'Extensión', 'Créditos', 'Decidir exige un usuario que sea analista registrado',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000276', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000276'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.decidir_evaluacion(@e, 'APROBADO', 'Ingresos estables y sustentados', UUID_TO_BIN('32000000-0000-4000-8000-000000000002'), 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-ANALISTA:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X277', 'Extensión', 'Créditos', 'La decisión exige un comentario suficiente',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'pruebas', @an)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000277', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000277'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.decidir_evaluacion(@e, 'APROBADO', ' corto  ', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-MOTIVO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X278', 'Extensión', 'Créditos', 'El analista no puede devolver OBSERVADO (diccionario de Evaluación)',
  JSON_ARRAY("CALL creditos.registrar_analista(UUID_TO_BIN('31000000-0000-4000-8000-000000000001'), 'pruebas', @an)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000278', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000278'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.decidir_evaluacion(@e, 'OBSERVADO', 'Falta sustento de ingresos', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'analista.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-EVALUACION:[^0-9]*$', 'procedimiento');

-- Revocación de una aprobación
CALL prueba.verifica('X279', 'Extensión', 'Créditos', 'Revocar una aprobación la deja RECHAZADA con el motivo y rechaza su orden abierta',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000279', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.revocar_aprobacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000279'), 'Documentación falsa detectada', 'analista.cr', UUID_TO_BIN(UUID()))"),
  "SELECT (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000279')) = 'RECHAZADA' AND (SELECT motivo FROM creditos.v_historial_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000279') AND estado_nuevo = 'RECHAZADA') = 'Documentación falsa detectada' AND (SELECT estado_orden FROM creditos.v_orden_api WHERE id_orden = @o) = 'RECHAZADA'",
  'RECHAZADA con motivo; orden RECHAZADA', "SELECT CONCAT_WS(' ', (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000279')), (SELECT estado_orden FROM creditos.v_orden_api WHERE id_orden = @o))", 'procedimiento');

CALL prueba.rechaza('X280', 'Extensión', 'Créditos', 'Solo se revoca una solicitud APROBADA',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000280', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.revocar_aprobacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000280'), 'Documentación falsa detectada', 'analista.cr', UUID_TO_BIN(UUID()))"),
  '^BNA-SOLICITUD:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X281', 'Extensión', 'Créditos', 'No se revoca un crédito ya desembolsado',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000281', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.revocar_aprobacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000281'), 'Documentación falsa detectada', 'analista.cr', UUID_TO_BIN(UUID()))"),
  '^BNA-SOLICITUD:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X282', 'Extensión', 'Créditos', 'Revocar exige un motivo',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000282', 'C001', 3000, 3, NULL, @e)",
             "CALL creditos.revocar_aprobacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000282'), '   ', 'analista.cr', UUID_TO_BIN(UUID()))"),
  '^BNA-MOTIVO:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X283', 'Extensión', 'Créditos', 'Las aprobaciones vigentes: la aprobada con 30 días de vigencia; ni la desembolsada ni la rechazada',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000283', 'C001', 3000, 3, NULL, @e)",
             "CALL prueba.cr_credito('33000000-0000-4000-8000-000000000284', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000285', 'C001', 3000, 3, 1, NULL, @r, @e2)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000285'), 1, 2000, 500, 400, 100, 'pruebas', UUID_TO_BIN(UUID()), @e2, @res, @regla)"),
  "SELECT (SELECT GROUP_CONCAT(BIN_TO_UUID(id_solicitud)) FROM creditos.v_aprobacion_api WHERE cod_cliente = 'C001' AND id_solicitud IN (UUID_TO_BIN('33000000-0000-4000-8000-000000000283'), UUID_TO_BIN('33000000-0000-4000-8000-000000000284'), UUID_TO_BIN('33000000-0000-4000-8000-000000000285'))) = '33000000-0000-4000-8000-000000000283' AND (SELECT TIMESTAMPDIFF(DAY, fecha_aprobacion, vigente_hasta) = 30 AND monto = 3000 AND id_evaluacion = @e AND id_calendario IS NOT NULL FROM creditos.v_aprobacion_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000283'))",
  'solo la aprobada, vigente 30 días', "SELECT GROUP_CONCAT(BIN_TO_UUID(id_solicitud)) FROM creditos.v_aprobacion_api WHERE cod_cliente = 'C001'", 'vista');

-- Preparación de la orden
CALL prueba.verifica('X284', 'Extensión', 'Créditos', 'Preparar una orden: PREPARADA, código DES, importe aprobado y la validación CUENTA',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000286', 'C001', 'CTA-PEN-1', 3000, 3, @o)"),
  "SELECT @cr_repetido = FALSE AND @cr_codigo REGEXP '^DES-[0-9]{4}-[0-9]{6}$' AND (SELECT CONCAT_WS(' ', estado_orden, importe, moneda, num_cuenta, id_canal, cod_cliente, usuario_preparacion) FROM creditos.v_orden_api WHERE id_orden = @o) = 'PREPARADA 3000.00 PEN CTA-PEN-1 VEN C001 operador.cr' AND (SELECT GROUP_CONCAT(CONCAT(tipo_validacion, ' ', resultado)) FROM creditos.v_validacion_orden_api WHERE id_orden = @o) = 'CUENTA APROBADA'",
  'PREPARADA 3000.00 PEN CTA-PEN-1 VEN C001 operador.cr; CUENTA APROBADA', "SELECT CONCAT_WS('; ', (SELECT CONCAT_WS(' ', estado_orden, importe, moneda, num_cuenta, id_canal, cod_cliente, usuario_preparacion) FROM creditos.v_orden_api WHERE id_orden = @o), (SELECT GROUP_CONCAT(CONCAT(tipo_validacion, ' ', resultado)) FROM creditos.v_validacion_orden_api WHERE id_orden = @o))", 'procedimiento');

CALL prueba.verifica('X285', 'Extensión', 'Créditos', 'Repetir la preparación con la misma llave y contenido devuelve la misma orden',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000287', 'C001', 3000, 3, NULL, @e)",
             "SET @llave = UUID_TO_BIN(UUID())",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'VEN', NULL, @llave, REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o1, @c1, @rep1)",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'VEN', NULL, @llave, REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o2, @c2, @rep2)"),
  "SELECT @o1 = @o2 AND @c1 = @c2 AND @rep1 = FALSE AND @rep2 = TRUE AND (SELECT COUNT(*) FROM creditos.v_orden_api WHERE id_evaluacion = @e) = 1",
  'misma orden, repetida', "SELECT CONCAT_WS(' ', @rep1, @rep2, (SELECT COUNT(*) FROM creditos.v_orden_api WHERE id_evaluacion = @e))", 'procedimiento');

CALL prueba.rechaza('X286', 'Extensión', 'Créditos', 'La misma llave con otro contenido se rechaza',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000288', 'C001', 3000, 3, NULL, @e)",
             "SET @llave = UUID_TO_BIN(UUID())",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'VEN', NULL, @llave, REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)",
             "CALL creditos.preparar_orden(@e, 'CR-PEN-1B', 'VEN', NULL, @llave, REPEAT('b', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-IDEMPOTENCIA:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X287', 'Extensión', 'Créditos', 'Una aprobación tiene a lo sumo una orden abierta',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000289', 'C001', 3000, 3, NULL, @e)",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-ORDEN:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X288', 'Extensión', 'Créditos', 'No se prepara una orden sin aprobación (R-B sin decidir)',
  JSON_ARRAY("CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000290', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000290'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-APROBACION:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X289', 'Extensión', 'Créditos', 'No se prepara una orden de un id de evaluación inexistente',
  JSON_ARRAY("CALL creditos.preparar_orden(UUID_TO_BIN(UUID()), 'CTA-PEN-1', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-APROBACION:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X290', 'Extensión', 'Créditos', 'No se prepara una orden si la primera cuota ya venció',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000291', 'C001', 3000, 3, CURRENT_DATE - INTERVAL 1 DAY, @e)",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-CALENDARIO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X291', 'Extensión', 'Créditos', 'La cuenta destino debe ser del cliente, y el mensaje no la repite',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000292', 'C001', 3000, 3, NULL, @e)",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-2', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-CUENTA-DESTINO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X292', 'Extensión', 'Créditos', 'La cuenta destino debe estar en la moneda del crédito',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000293', 'C001', 3000, 3, NULL, @e)",
             "CALL creditos.preparar_orden(@e, 'CTA-USD-1', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-CUENTA-DESTINO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X293', 'Extensión', 'Créditos', 'La cuenta destino debe ser individual',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000294', 'C001', 3000, 3, NULL, @e)",
             "CALL creditos.preparar_orden(@e, 'CTA-CONJ', 'VEN', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-CUENTA-DESTINO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X294', 'Extensión', 'Créditos', 'El desembolso es por ventanilla o Home Banking',
  JSON_ARRAY("CALL prueba.cr_aprobada('33000000-0000-4000-8000-000000000295', 'C001', 3000, 3, NULL, @e)",
             "CALL creditos.preparar_orden(@e, 'CTA-PEN-1', 'ATM', NULL, UUID_TO_BIN(UUID()), REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @o, @c, @rep)"),
  '^BNA-CANAL:[^0-9]*$', 'procedimiento');

-- Validaciones previas
CALL prueba.verifica('X295', 'Extensión', 'Créditos', 'La identidad verificada hoy en ventanilla con la cuenta elegida deja la orden VALIDADA',
  JSON_ARRAY("CALL prueba.cr_validada('33000000-0000-4000-8000-000000000296', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @o)"),
  "SELECT @cr_estado = 'VALIDADA' AND (SELECT estado_orden FROM creditos.v_orden_api WHERE id_orden = @o) = 'VALIDADA' AND (SELECT GROUP_CONCAT(tipo_validacion ORDER BY tipo_validacion) FROM creditos.v_validacion_orden_api WHERE id_orden = @o AND resultado = 'APROBADA') = 'CUENTA,IDENTIDAD'",
  'VALIDADA', "SELECT @cr_estado", 'procedimiento');

CALL prueba.rechaza('X296', 'Extensión', 'Créditos', 'La validación de identidad de otro cliente no sirve como evidencia',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000297', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL clientes.verificar_documento('DNI', '70000002', TRUE, NULL, UUID_TO_BIN(UUID()), 'operador.cr', @v, @res, @mot, @cli)",
             "CALL creditos.registrar_validacion_orden(@o, 'IDENTIDAD', 'APROBADA', CAST(@v AS CHAR), NULL, NULL, 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-VALIDACION:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X297', 'Extensión', 'Créditos', 'Una validación de identidad RECHAZADA no sirve como evidencia',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000298', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL clientes.verificar_documento('DNI', '70000001', FALSE, NULL, UUID_TO_BIN(UUID()), 'operador.cr', @v, @res, @mot, @cli)",
             "CALL creditos.registrar_validacion_orden(@o, 'IDENTIDAD', 'APROBADA', CAST(@v AS CHAR), NULL, NULL, 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-VALIDACION:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X298', 'Extensión', 'Créditos', 'La validación CUENTA la registra la base, no quien llama',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000299', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.registrar_validacion_orden(@o, 'CUENTA', 'APROBADA', 'x', NULL, NULL, 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-VALIDACION:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X299', 'Extensión', 'Créditos', 'Una identidad RECHAZADA queda registrada y la orden sigue PREPARADA',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000300', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.registrar_validacion_orden(@o, 'IDENTIDAD', 'RECHAZADA', 'Documento no coincide', 'Rostro distinto', NULL, 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  "SELECT @estado = 'PREPARADA' AND (SELECT COUNT(*) FROM creditos.v_validacion_orden_api WHERE id_orden = @o AND tipo_validacion = 'IDENTIDAD' AND resultado = 'RECHAZADA') = 1",
  'PREPARADA', "SELECT @estado", 'procedimiento');

CALL prueba.verifica('X300', 'Extensión', 'Créditos', 'Cambiar la cuenta de una orden VALIDADA a otra elegible deja una validación CUENTA nueva',
  JSON_ARRAY("CALL prueba.cr_validada('33000000-0000-4000-8000-000000000301', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.cambiar_cuenta_orden(@o, 'CR-PEN-1B', 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  "SELECT @estado = 'VALIDADA' AND (SELECT num_cuenta FROM creditos.v_orden_api WHERE id_orden = @o) = 'CR-PEN-1B' AND (SELECT COUNT(*) FROM creditos.v_validacion_orden_api WHERE id_orden = @o AND tipo_validacion = 'CUENTA') = 2",
  'VALIDADA con CR-PEN-1B', "SELECT CONCAT_WS(' ', @estado, (SELECT num_cuenta FROM creditos.v_orden_api WHERE id_orden = @o))", 'procedimiento');

CALL prueba.rechaza('X301', 'Extensión', 'Créditos', 'No se cambia la cuenta a una que no es elegible',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000302', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.cambiar_cuenta_orden(@o, 'CTA-USD-1', 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-CUENTA-DESTINO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X302', 'Extensión', 'Créditos', 'No se cambia la cuenta de una orden confirmada',
  JSON_ARRAY("CALL prueba.cr_validada('33000000-0000-4000-8000-000000000303', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.confirmar_orden(@o, 'operador.cr', UUID_TO_BIN(UUID()), @cod, @abono, @rep)",
             "CALL creditos.cambiar_cuenta_orden(@o, 'CR-PEN-1B', 'operador.cr', UUID_TO_BIN(UUID()), @estado)"),
  '^BNA-ORDEN:[^0-9]*$', 'procedimiento');

-- Confirmación: abono, crédito y solicitud DESEMBOLSADA en una sola operación
CALL prueba.rechaza('X303', 'Extensión', 'Créditos', 'No se confirma una orden sin validar',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000304', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.confirmar_orden(@o, 'operador.cr', UUID_TO_BIN(UUID()), @cod, @abono, @rep)"),
  '^BNA-ORDEN:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X304', 'Extensión', 'Créditos', 'Confirmar abona la cuenta (DESEMBOLSO), crea el crédito AL_DIA y deja la solicitud DESEMBOLSADA',
  JSON_ARRAY("SET @antes = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1')",
             "CALL prueba.cr_validada('33000000-0000-4000-8000-000000000305', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.confirmar_orden(@o, 'operador.cr', UUID_TO_BIN(UUID()), @cod, @abono, @rep)"),
  "SELECT @rep = FALSE AND @cod REGEXP '^CRE-[0-9]{4}-[0-9]{6}$' AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @antes + 3000 AND (SELECT CONCAT_WS(' ', tipo_operacion, naturaleza, monto, id_canal) FROM cuentas.v_movimiento_api WHERE uuid_transaccion = @abono) = 'DESEMBOLSO C 3000.00 VEN' AND (SELECT CONCAT_WS(' ', estado_orden, cod_credito = @cod, uuid_transaccion_abono = @abono, usuario_confirmacion) FROM creditos.v_orden_api WHERE id_orden = @o) = 'CONFIRMADA 1 1 operador.cr' AND (SELECT CONCAT_WS(' ', estado_credito, cod_cliente, monto_desembolsado, numero_cuotas, saldo_pendiente) FROM creditos.v_credito_api WHERE cod_credito = @cod) = 'AL_DIA C001 3000.00 3 3030.00' AND (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000305')) = 'DESEMBOLSADA'",
  'abono, CONFIRMADA, AL_DIA, DESEMBOLSADA', "SELECT CONCAT_WS('; ', (SELECT CONCAT_WS(' ', tipo_operacion, naturaleza, monto, id_canal) FROM cuentas.v_movimiento_api WHERE uuid_transaccion = @abono), (SELECT CONCAT_WS(' ', estado_credito, cod_cliente, monto_desembolsado, numero_cuotas, saldo_pendiente) FROM creditos.v_credito_api WHERE cod_credito = @cod))", 'procedimiento');

CALL prueba.verifica('X305', 'Extensión', 'Créditos', 'El calendario OFICIAL es copia exacta del PRELIMINAR vigente (RN-SOL-006), que queda HISTORICO',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000306', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)"),
  "SELECT (SELECT GROUP_CONCAT(CONCAT_WS('/', numero_cuota, fecha_vencimiento, capital, interes, saldo_capital, cuota_total) ORDER BY numero_cuota) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000306') AND tipo_calendario = 'PRELIMINAR') = (SELECT GROUP_CONCAT(CONCAT_WS('/', numero_cuota, fecha_vencimiento, capital, interes, saldo_capital, cuota_total) ORDER BY numero_cuota) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000306') AND tipo_calendario = 'OFICIAL') AND (SELECT GROUP_CONCAT(DISTINCT CONCAT(tipo_calendario, ' ', estado_calendario) ORDER BY version) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000306')) = 'PRELIMINAR HISTORICO,OFICIAL VIGENTE' AND (SELECT SUM(saldo_pendiente) FROM creditos.v_cuota_api WHERE cod_credito = @cod) = 3030 AND (SELECT COUNT(*) FROM creditos.v_cuota_api WHERE cod_credito = @cod AND estado_cuota = 'PENDIENTE') = 3",
  'cuotas iguales; PRELIMINAR HISTORICO, OFICIAL VIGENTE', "SELECT GROUP_CONCAT(DISTINCT CONCAT(tipo_calendario, ' ', estado_calendario) ORDER BY version) FROM creditos.v_calendario_api WHERE id_solicitud = UUID_TO_BIN('33000000-0000-4000-8000-000000000306')", 'procedimiento');

CALL prueba.verifica('X306', 'Extensión', 'Créditos', 'Repetir la confirmación devuelve el mismo crédito y el mismo abono, sin abonar otra vez',
  JSON_ARRAY("SET @antes = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1')",
             "CALL prueba.cr_validada('33000000-0000-4000-8000-000000000307', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.confirmar_orden(@o, 'operador.cr', UUID_TO_BIN(UUID()), @cod1, @ab1, @rep1)",
             "CALL creditos.confirmar_orden(@o, 'operador.cr', UUID_TO_BIN(UUID()), @cod2, @ab2, @rep2)"),
  "SELECT @cod1 = @cod2 AND @ab1 = @ab2 AND @rep1 = FALSE AND @rep2 = TRUE AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @antes + 3000",
  'mismo crédito, un solo abono', "SELECT CONCAT_WS(' ', @rep1, @rep2, (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') - @antes)", 'procedimiento');

CALL prueba.verifica('X307', 'Extensión', 'Créditos', 'La confirmación deja los eventos ORDEN y CREDITO en la bitácora de créditos y el del movimiento en la general',
  JSON_ARRAY("SET @corr = UUID_TO_BIN(UUID())",
             "CALL prueba.cr_validada('33000000-0000-4000-8000-000000000308', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.confirmar_orden(@o, 'operador.cr', @corr, @cod, @abono, @rep)"),
  "SELECT (SELECT GROUP_CONCAT(CONCAT(tipo_entidad, ' ', accion, ' ', modulo) ORDER BY id_evento) FROM creditos.v_evento_credito_api WHERE correlation_id = @corr) = 'ORDEN CONFIRMAR_ORDEN DESEMBOLSO,CREDITO CREAR_CREDITO DESEMBOLSO' AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE correlation_id = @corr AND modulo = 'CUENTAS' AND accion = 'DESEMBOLSO' AND id_entidad = BIN_TO_UUID(@abono)) = 1",
  'ORDEN y CREDITO; movimiento en CUENTAS', "SELECT GROUP_CONCAT(CONCAT(tipo_entidad, ' ', accion, ' ', modulo) ORDER BY id_evento) FROM creditos.v_evento_credito_api WHERE correlation_id = @corr", 'procedimiento');

CALL prueba.verifica('X308', 'Extensión', 'Créditos', 'Rechazar una orden PREPARADA la deja RECHAZADA con su motivo; ya no se confirma',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000309', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.rechazar_orden(@o, 'El cliente desistió en ventanilla', 'operador.cr', UUID_TO_BIN(UUID()))"),
  "SELECT CONCAT_WS(' / ', estado_orden, motivo_rechazo) = 'RECHAZADA / El cliente desistió en ventanilla' FROM creditos.v_orden_api WHERE id_orden = @o",
  'RECHAZADA / El cliente desistió en ventanilla', "SELECT CONCAT_WS(' / ', estado_orden, motivo_rechazo) FROM creditos.v_orden_api WHERE id_orden = @o", 'procedimiento');

CALL prueba.rechaza('X309', 'Extensión', 'Créditos', 'Rechazar una orden exige un motivo',
  JSON_ARRAY("CALL prueba.cr_orden('33000000-0000-4000-8000-000000000310', 'C001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.rechazar_orden(@o, '', 'operador.cr', UUID_TO_BIN(UUID()))"),
  '^BNA-MOTIVO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X310', 'Extensión', 'Créditos', 'Una orden RECHAZADA no se confirma',
  JSON_ARRAY("CALL prueba.cr_validada('33000000-0000-4000-8000-000000000311', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @o)",
             "CALL creditos.rechazar_orden(@o, 'El cliente desistió en ventanilla', 'operador.cr', UUID_TO_BIN(UUID()))",
             "CALL creditos.confirmar_orden(@o, 'operador.cr', UUID_TO_BIN(UUID()), @cod, @abono, @rep)"),
  '^BNA-ORDEN:[^0-9]*$', 'procedimiento');

-- Pago de cuotas: débito y aplicación en una sola operación
CALL prueba.verifica('X311', 'Extensión', 'Créditos', 'Un pago parcial debita la cuenta (DEBITO_CUOTA) y deja la cuota PARCIAL',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000312', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "SET @antes = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1')",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 500, 'REF-X311', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)"),
  "SELECT @estado = 'CONFIRMADO' AND @aplicado = 500 AND @motivo IS NULL AND @rep = FALSE AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @antes - 500 AND (SELECT CONCAT_WS(' ', estado_cuota, saldo_pendiente) FROM creditos.v_cuota_api WHERE cod_credito = @cod AND numero_cuota = 1) = 'PARCIAL 510.00' AND (SELECT CONCAT_WS(' ', tipo_operacion, naturaleza, monto) FROM cuentas.v_movimiento_api m JOIN creditos.v_pago_api p ON p.uuid_transaccion = m.uuid_transaccion WHERE p.id_pago = @pago) = 'DEBITO_CUOTA D 500.00'",
  'CONFIRMADO 500; cuota PARCIAL 510.00', "SELECT CONCAT_WS(' ', @estado, @aplicado, (SELECT CONCAT_WS(' ', estado_cuota, saldo_pendiente) FROM creditos.v_cuota_api WHERE cod_credito = @cod AND numero_cuota = 1))", 'procedimiento');

CALL prueba.verifica('X312', 'Extensión', 'Créditos', 'Un pago mayor que la cuota se aplica a la siguiente, de la más antigua a la más reciente',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000313', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 1500, 'REF-X312', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)"),
  "SELECT (SELECT GROUP_CONCAT(CONCAT_WS(' ', numero_cuota, estado_cuota, saldo_pendiente) ORDER BY numero_cuota) FROM creditos.v_cuota_api WHERE cod_credito = @cod) = '1 PAGADA 0.00,2 PARCIAL 520.00,3 PENDIENTE 1010.00' AND (SELECT monto_aplicado FROM creditos.v_pago_api WHERE id_pago = @pago) = 1500",
  '1 PAGADA 0.00,2 PARCIAL 520.00,3 PENDIENTE 1010.00', "SELECT GROUP_CONCAT(CONCAT_WS(' ', numero_cuota, estado_cuota, saldo_pendiente) ORDER BY numero_cuota) FROM creditos.v_cuota_api WHERE cod_credito = @cod", 'procedimiento');

CALL prueba.verifica('X313', 'Extensión', 'Créditos', 'Pagar toda la deuda deja las cuotas PAGADA y el crédito CANCELADO',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000314', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 3030, 'REF-X313', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)"),
  "SELECT (SELECT CONCAT_WS(' ', estado_credito, saldo_pendiente, cuotas_pagadas) FROM creditos.v_credito_api WHERE cod_credito = @cod) = 'CANCELADO 0.00 3'",
  'CANCELADO 0.00 3', "SELECT CONCAT_WS(' ', estado_credito, saldo_pendiente, cuotas_pagadas) FROM creditos.v_credito_api WHERE cod_credito = @cod", 'procedimiento');

CALL prueba.rechaza('X314', 'Extensión', 'Créditos', 'Un pago mayor que la deuda total se rechaza',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000315', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 3030.01, 'REF-X314', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)"),
  '^BNA-PAGO:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X315', 'Extensión', 'Créditos', 'La cuenta que paga debe ser del titular del crédito, y el mensaje no la repite',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000316', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-2', 100, 'REF-X315', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)"),
  '^BNA-CUENTA-ORIGEN:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X316', 'Extensión', 'Créditos', 'Un crédito CANCELADO no recibe pagos',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000317', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 3030, 'REF-X316a', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 10, 'REF-X316b', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)"),
  '^BNA-CREDITO:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X317', 'Extensión', 'Créditos', 'Sin fondos, el pago queda RECHAZADO con su motivo, sin movimiento y sin tocar las cuotas',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000318', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CR-PEN-1B', 100, 'REF-X317', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @estado, @aplicado, @motivo, @rep)"),
  "SELECT @estado = 'RECHAZADO' AND @motivo = 'BNA-SALDO' AND @aplicado = 0 AND (SELECT CONCAT_WS(' ', estado_confirmacion, motivo_rechazo, uuid_transaccion IS NULL, monto_aplicado) FROM creditos.v_pago_api WHERE id_pago = @pago) = 'RECHAZADO BNA-SALDO 1 0.00' AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CR-PEN-1B') = 0 AND (SELECT SUM(saldo_pendiente) FROM creditos.v_cuota_api WHERE cod_credito = @cod) = 3030",
  'RECHAZADO BNA-SALDO 1 0.00', "SELECT CONCAT_WS(' ', @estado, @motivo, (SELECT CONCAT_WS(' ', estado_confirmacion, motivo_rechazo, uuid_transaccion IS NULL, monto_aplicado) FROM creditos.v_pago_api WHERE id_pago = @pago))", 'procedimiento');

CALL prueba.verifica('X318', 'Extensión', 'Créditos', 'Repetir la referencia con el mismo contenido devuelve el mismo pago, sin debitar otra vez',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000319', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "SET @antes = (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1')",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 500, 'REF-X318', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p1, @e1, @a1, @m1, @r1)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 500, 'REF-X318', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p2, @e2, @a2, @m2, @r2)"),
  "SELECT @p1 = @p2 AND @e2 = 'CONFIRMADO' AND @a2 = 500 AND @r1 = FALSE AND @r2 = TRUE AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @antes - 500",
  'mismo pago, un débito', "SELECT CONCAT_WS(' ', @r1, @r2, @antes - (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1'))", 'procedimiento');

CALL prueba.rechaza('X319', 'Extensión', 'Créditos', 'La misma referencia con otro contenido se rechaza',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000320', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 500, 'REF-X319', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p, @e, @a, @m, @r)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 600, 'REF-X319', 'VEN', REPEAT('b', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p, @e, @a, @m, @r)"),
  '^BNA-IDEMPOTENCIA:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X320', 'Extensión', 'Créditos', 'Repetir la referencia de un pago RECHAZADO devuelve RECHAZADO y no intenta debitar otra vez',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000321', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CR-PEN-1B', 100, 'REF-X320', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p1, @e1, @a1, @m1, @r1)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CR-PEN-1B', 100, 'REF-X320', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p2, @e2, @a2, @m2, @r2)"),
  "SELECT @p1 = @p2 AND @e2 = 'RECHAZADO' AND @m2 = 'BNA-SALDO' AND @r2 = TRUE AND (SELECT COUNT(*) FROM creditos.v_pago_api WHERE cod_credito = @cod) = 1",
  'RECHAZADO repetido', "SELECT CONCAT_WS(' ', @e2, @m2, @r2)", 'procedimiento');

CALL prueba.rechaza('X321', 'Extensión', 'Créditos', 'Un crédito inexistente no recibe pagos',
  JSON_ARRAY("CALL creditos.registrar_pago_cuota('CRE-NO-EXISTE', 'CTA-PEN-1', 10, 'REF-X321', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p, @e, @a, @m, @r)"),
  '^BNA-CREDITO:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X322', 'Extensión', 'Créditos', 'El pago se lee con su cuenta, su movimiento y su reparto entre cuotas',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000322', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 1500, 'REF-X322', 'HB', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @pago, @e, @a, @m, @r)"),
  "SELECT CONCAT_WS(' ', referencia, num_cuenta, id_canal, estado_confirmacion, monto_pago, monto_aplicado, uuid_transaccion IS NOT NULL, JSON_LENGTH(aplicaciones), JSON_CONTAINS(aplicaciones, JSON_OBJECT('numero_cuota', 2, 'monto_aplicado', 490.00)), JSON_CONTAINS(aplicaciones, JSON_OBJECT('numero_cuota', 1, 'monto_aplicado', 1010.00))) = 'REF-X322 CTA-PEN-1 HB CONFIRMADO 1500.00 1500.00 1 2 1 1' FROM creditos.v_pago_api WHERE id_pago = @pago",
  'REF-X322 CTA-PEN-1 HB CONFIRMADO 1500.00 1500.00 1 2 1 1', "SELECT CONCAT_WS(' ', referencia, num_cuenta, id_canal, estado_confirmacion, monto_pago, monto_aplicado, uuid_transaccion IS NOT NULL, JSON_LENGTH(aplicaciones), CAST(aplicaciones AS CHAR)) FROM creditos.v_pago_api WHERE id_pago = @pago", 'vista');

-- Mora y vencimientos (CR-0001 de datos.sql: la cuota 1 venció el 2026-11-15)
CALL prueba.verifica('X323', 'Extensión', 'Créditos', 'Se registra la mora de una cuota atrasada; queda vigente con sus días de atraso',
  JSON_ARRAY("CALL creditos.registrar_mora('CR-0001', 1, 15.50, 'svc-cobranza', UUID_TO_BIN(UUID()), @mora)"),
  "SELECT (SELECT CONCAT_WS(' ', monto_calculado, vigente, dias_atraso = DATEDIFF(core.fn_fecha_negocio(UTC_TIMESTAMP(6)), '2026-11-15')) FROM creditos.v_mora_api WHERE id_mora = @mora) = '15.50 1 1' AND (SELECT mora_vigente FROM creditos.v_cuota_api WHERE cod_credito = 'CR-0001' AND numero_cuota = 1) = 15.50",
  '15.50 1 1', "SELECT CONCAT_WS(' ', monto_calculado, vigente, dias_atraso) FROM creditos.v_mora_api WHERE id_mora = @mora", 'procedimiento');

CALL prueba.verifica('X324', 'Extensión', 'Créditos', 'Un cálculo nuevo de mora deja vigente solo el último',
  JSON_ARRAY("CALL creditos.registrar_mora('CR-0001', 1, 15.50, 'svc-cobranza', UUID_TO_BIN(UUID()), @m1)",
             "DO SLEEP(0.01)",
             "CALL creditos.registrar_mora('CR-0001', 1, 18.25, 'svc-cobranza', UUID_TO_BIN(UUID()), @m2)"),
  "SELECT (SELECT GROUP_CONCAT(CONCAT(monto_calculado, ':', vigente) ORDER BY fecha_calculo) FROM creditos.v_mora_api WHERE id_mora IN (@m1, @m2)) = '15.50:0,18.25:1' AND (SELECT mora_vigente FROM creditos.v_credito_api WHERE cod_credito = 'CR-0001') = 18.25",
  '15.50:0,18.25:1', "SELECT GROUP_CONCAT(CONCAT(monto_calculado, ':', vigente) ORDER BY fecha_calculo) FROM creditos.v_mora_api WHERE id_mora IN (@m1, @m2)", 'procedimiento');

CALL prueba.rechaza('X325', 'Extensión', 'Créditos', 'No se registra mora de una cuota que aún no vence',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000325', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.registrar_mora(@cod, 1, 5, 'svc-cobranza', UUID_TO_BIN(UUID()), @mora)"),
  '^BNA-CUOTA:[^0-9]*$', 'procedimiento');

CALL prueba.rechaza('X326', 'Extensión', 'Créditos', 'La mora no puede ser negativa',
  JSON_ARRAY("CALL creditos.registrar_mora('CR-0001', 1, -1, 'svc-cobranza', UUID_TO_BIN(UUID()), @mora)"),
  '^BNA-MORA:[^0-9]*$', 'procedimiento');

CALL prueba.verifica('X327', 'Extensión', 'Créditos', 'Los vencimientos del día marcan la cuota VENCIDA y el crédito EN_MORA; uno al día no cambia',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000327', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.actualizar_vencimientos(NULL, 'svc-cobranza', @cuotas, @creditos)"),
  "SELECT @cuotas >= 1 AND @creditos >= 1 AND (SELECT estado_cuota FROM creditos.v_cuota_api WHERE cod_credito = 'CR-0001' AND numero_cuota = 1) = 'VENCIDA' AND (SELECT estado_credito = 'EN_MORA' AND cuotas_vencidas >= 1 FROM creditos.v_credito_api WHERE cod_credito = 'CR-0001') AND (SELECT estado_credito FROM creditos.v_credito_api WHERE cod_credito = @cod) = 'AL_DIA'",
  'VENCIDA, EN_MORA; el nuevo AL_DIA', "SELECT CONCAT_WS(' ', @cuotas, @creditos, (SELECT estado_credito FROM creditos.v_credito_api WHERE cod_credito = 'CR-0001'), (SELECT estado_credito FROM creditos.v_credito_api WHERE cod_credito = @cod))", 'procedimiento');

CALL prueba.verifica('X328', 'Extensión', 'Créditos', 'Pagar la cuota vencida devuelve el crédito a AL_DIA',
  JSON_ARRAY("CALL prueba.cr_credito('33000000-0000-4000-8000-000000000328', 'C001', '70000001', 'CTA-PEN-1', 3000, 3, @cod)",
             "CALL creditos.actualizar_vencimientos(CURRENT_DATE + INTERVAL 40 DAY, 'svc-cobranza', @cuotas, @creditos)",
             "SET @mora = (SELECT estado_credito FROM creditos.v_credito_api WHERE cod_credito = @cod)",
             "CALL creditos.registrar_pago_cuota(@cod, 'CTA-PEN-1', 1010, 'REF-X328', 'VEN', REPEAT('a', 64), 'operador.cr', UUID_TO_BIN(UUID()), @p, @e, @a, @m, @r)"),
  "SELECT @mora = 'EN_MORA' AND (SELECT estado_credito FROM creditos.v_credito_api WHERE cod_credito = @cod) = 'AL_DIA' AND (SELECT estado_cuota FROM creditos.v_cuota_api WHERE cod_credito = @cod AND numero_cuota = 1) = 'PAGADA'",
  'EN_MORA y luego AL_DIA', "SELECT CONCAT_WS(' ', @mora, (SELECT estado_credito FROM creditos.v_credito_api WHERE cod_credito = @cod))", 'procedimiento');

CALL prueba.verifica('X329', 'Extensión', 'Créditos', 'Los días de atraso se cuentan desde el vencimiento y son cero si la cuota no vence',
  JSON_ARRAY("DO 0"),
  "SELECT (SELECT dias_atraso FROM creditos.v_cuota_api WHERE cod_credito = 'CR-0001' AND numero_cuota = 1) = DATEDIFF(core.fn_fecha_negocio(UTC_TIMESTAMP(6)), '2026-11-15') AND (SELECT dias_atraso FROM creditos.v_cuota_api WHERE cod_credito = 'CR-0001' AND numero_cuota = 3) = GREATEST(0, DATEDIFF(core.fn_fecha_negocio(UTC_TIMESTAMP(6)), '2027-01-15'))",
  'días desde el vencimiento', "SELECT GROUP_CONCAT(dias_atraso ORDER BY numero_cuota) FROM creditos.v_cuota_api WHERE cod_credito = 'CR-0001'", 'vista');

-- Catálogos, función y vistas
CALL prueba.verifica('X330', 'Extensión', 'Créditos', 'Los catálogos de créditos incluyen estados, reglas con umbrales, métodos, validaciones y canales',
  JSON_ARRAY("CALL creditos.catalogos_credito(@cat)"),
  "SELECT JSON_LENGTH(@cat, '$.estados_solicitud') = 5 AND JSON_UNQUOTE(JSON_EXTRACT(@cat, '$.reglas[1].id_regla')) = 'R-B' AND JSON_EXTRACT(@cat, '$.reglas[1].ratio_min') = 80 AND JSON_EXTRACT(@cat, '$.reglas[1].ratio_max') = 100 AND JSON_LENGTH(@cat, '$.metodos_amortizacion') = 3 AND JSON_LENGTH(@cat, '$.tipos_validacion') = 4 AND JSON_LENGTH(@cat, '$.estados_orden') = 7 AND JSON_LENGTH(@cat, '$.estados_cuota') = 4 AND JSON_LENGTH(@cat, '$.estados_credito') = 3 AND JSON_CONTAINS(@cat, '\"VEN\"', '$.canales_desembolso') AND JSON_CONTAINS(@cat, '\"HB\"', '$.canales_desembolso') AND JSON_EXTRACT(@cat, '$.vigencia_aprobacion_dias') = 30",
  'catálogos completos', "SELECT LEFT(@cat, 200)", 'procedimiento');

CALL prueba.verifica('X331', 'Extensión', 'Créditos', 'El id de evaluación es determinista, distinto por ronda y un UUID válido (versión 8)',
  JSON_ARRAY("SET @a = creditos.fn_id_evaluacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000331'), 1)",
             "SET @b = creditos.fn_id_evaluacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000331'), 1)",
             "SET @c = creditos.fn_id_evaluacion(UUID_TO_BIN('33000000-0000-4000-8000-000000000331'), 2)"),
  "SELECT @a = @b AND @a <> @c AND (ASCII(SUBSTR(@a, 7, 1)) >> 4) = 8 AND (ASCII(SUBSTR(@a, 9, 1)) & 0xC0) = 0x80 AND LENGTH(@a) = 16",
  'determinista, versión 8', "SELECT BIN_TO_UUID(@a)", 'procedimiento');

CALL prueba.verifica('X332', 'Extensión', 'Créditos', 'Las vistas de créditos no exponen nombres, documentos ni contactos del cliente',
  JSON_ARRAY("SET @n = (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'creditos' AND table_name LIKE 'v\\_%\\_api' AND column_name IN ('nombres', 'apellido_paterno', 'apellido_materno', 'numero_documento', 'tipo_documento', 'correo', 'celular'))",
             "SET @v = (SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'creditos' AND table_name LIKE 'v\\_%\\_api')"),
  "SELECT @n = 0 AND @v = 16", '0 columnas personales en 16 vistas', "SELECT CONCAT(@n, ' columnas en ', @v, ' vistas')", 'vista');

-- Permisos de bna_api sobre creditos
CALL prueba.rechaza('X333', 'Extensión', 'bna_api', 'bna_api no puede: SELECT creditos.solicitud_credito',
  JSON_ARRAY("SELECT * FROM creditos.solicitud_credito"), 'denied', 'privilegio');

CALL prueba.rechaza('X334', 'Extensión', 'bna_api', 'bna_api no puede: SELECT creditos.orden_desembolso',
  JSON_ARRAY("SELECT * FROM creditos.orden_desembolso"), 'denied', 'privilegio');

CALL prueba.rechaza('X335', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en creditos.pago',
  JSON_ARRAY("INSERT INTO creditos.pago (monto_pago, referencia_transaccion, estado_confirmacion, cod_credito, id_canal) VALUES (1, 'X335', 'CONFIRMADO', 'CR-0001', 'VEN')"), 'denied', 'privilegio');

CALL prueba.rechaza('X336', 'Extensión', 'bna_api', 'bna_api no puede: registrar_evento_credito',
  JSON_ARRAY("CALL creditos.registrar_evento_credito('ORDEN', 'x', NULL, 'FALSO', NULL, 13, 'nadie', UUID_TO_BIN(UUID()), NULL)"), 'denied', 'privilegio');

CALL prueba.rechaza('X337', 'Extensión', 'bna_api', 'bna_api no puede: aplicar_pago',
  JSON_ARRAY("CALL creditos.aplicar_pago(UUID_TO_BIN('f0000000-0000-4000-8000-000000000001'), @a)"), 'denied', 'privilegio');

CALL prueba.rechaza('X338', 'Extensión', 'bna_api', 'bna_api no puede: verificar_aprobacion',
  JSON_ARRAY("CALL creditos.verificar_aprobacion(UUID_TO_BIN(UUID()), @s, @c, @m, @mo)"), 'denied', 'privilegio');

CALL prueba.rechaza('X339', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en creditos.numerador_orden',
  JSON_ARRAY("INSERT INTO creditos.numerador_orden () VALUES ()"), 'denied', 'privilegio');

CALL prueba.rechaza('X340', 'Extensión', 'bna_api', 'bna_api no puede: escribir por la vista de créditos',
  JSON_ARRAY("UPDATE creditos.v_credito_api SET estado_credito = 'CANCELADO'"), 'denied', 'privilegio');

CALL prueba.rechaza('X341', 'Extensión', 'bna_api', 'bna_api no puede: UPDATE de creditos.cuota',
  JSON_ARRAY("UPDATE creditos.cuota SET saldo_pendiente = 0"), 'denied', 'privilegio');

-- Autorizaciones y credenciales de tarjeta (v1.5), con el rol de la API.
CALL prueba.verifica('X378', 'Extensión', 'bna_api', 'bna_api autoriza por el procedimiento y lee la autorización en su vista',
  JSON_ARRAY("CALL tarjetas.autorizar_operacion(UUID_TO_BIN('a3000000-0000-4000-8000-000000000001'), UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2', 'VEN', NULL, 'RETIRO', 10, NULL, 'pruebas', @e, @c)"),
  "SELECT @e = 'AUTORIZADA' AND (SELECT estado_autorizacion FROM tarjetas.v_autorizacion_api WHERE uuid_autorizacion = UUID_TO_BIN('a3000000-0000-4000-8000-000000000001')) = 'AUTORIZADA' AND (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'tarjetas' AND table_name = 'v_autorizacion_api' AND column_name IN ('ip_origen', 'nivel_riesgo')) = 0",
  'AUTORIZADA y legible en v_autorizacion_api', "SELECT @e", 'privilegio');

CALL prueba.rechaza('X379', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en autorizacion',
  JSON_ARRAY("INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_canal, id_tarjeta, num_cuenta) VALUES ('RETIRO', 1, 'AUTORIZADA', 'VEN', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'CTA-PEN-2')"),
  'denied', 'privilegio');

CALL prueba.rechaza('X380', 'Extensión', 'bna_api', 'bna_api no puede: formato_credencial',
  JSON_ARRAY("CALL tarjetas.formato_credencial('PIN_ATM', '1234')"), 'denied', 'privilegio');

CALL prueba.verifica('X381', 'Extensión', 'bna_api', 'bna_api registra y valida un PIN sin leer las credenciales',
  JSON_ARRAY("CALL tarjetas.registrar_credencial(UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'PIN_ATM', '2468', 'pruebas')",
             "CALL tarjetas.validar_credencial(UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), 'PIN_ATM', '2468', NULL, 'ATM-AQP-001', NULL, NULL, 'pruebas', @r, @i)"),
  "SELECT @r = 'EXITOSO' AND @i = 3", 'EXITOSO', "SELECT @r", 'privilegio');

-- Empleados (v1.6), con el rol de la API. El usuario 34…01 es una persona sin empleado.
SET @emp_usr = "CALL core.crear_usuario(UUID_TO_BIN('34000000-0000-4000-8000-000000000001'), 'nuevo.analista', 'Nueva Analista', 'ANALISTA', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')";

CALL prueba.verifica('X386', 'Extensión', 'Empleados', 'Un administrador registra un empleado y lo liga a un usuario sin empleado',
  JSON_ARRAY(@emp_usr,
             "CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000386'), ' EMP-AN-386 ', 'Nueva Analista', 'ANALISTA', 'AQP01', UUID_TO_BIN('34000000-0000-4000-8000-000000000001'), 'pruebas')"),
  "SELECT (SELECT id_empleado FROM core.usuario_sistema WHERE id_usuario = UUID_TO_BIN('34000000-0000-4000-8000-000000000001')) = UUID_TO_BIN('34100000-0000-4000-8000-000000000386')",
  'el usuario queda ligado al empleado', "SELECT BIN_TO_UUID(id_empleado) FROM core.usuario_sistema WHERE id_usuario = UUID_TO_BIN('34000000-0000-4000-8000-000000000001')", 'procedimiento');

CALL prueba.verifica('X387', 'Extensión', 'Empleados', 'El registro del empleado se audita sin el nombre de la persona',
  JSON_ARRAY(@emp_usr,
             "CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000387'), 'EMP-AN-387', 'Nueva Analista', 'ANALISTA', 'AQP01', UUID_TO_BIN('34000000-0000-4000-8000-000000000001'), 'admin.pruebas')"),
  "SELECT (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE modulo = 'CORE' AND entidad = 'empleado' AND id_entidad = '34100000-0000-4000-8000-000000000387' AND accion = 'REGISTRAR_EMPLEADO' AND actor = 'admin.pruebas' AND JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.codigo_empleado')) = 'EMP-AN-387' AND JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.id_usuario')) = '34000000-0000-4000-8000-000000000001') = 1 AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'REGISTRAR_EMPLEADO' AND detalle LIKE '%Nueva%') = 0",
  'un evento REGISTRAR_EMPLEADO sin el nombre', "SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'REGISTRAR_EMPLEADO'", 'procedimiento');

CALL prueba.verifica('X388', 'Extensión', 'Empleados', 'El empleado registrado por la API queda disponible como analista y decide una evaluación R-B',
  JSON_ARRAY(@emp_usr,
             "CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000388'), 'EMP-AN-388', 'Nueva Analista', 'ANALISTA', 'AQP01', UUID_TO_BIN('34000000-0000-4000-8000-000000000001'), 'pruebas')",
             "CALL creditos.registrar_analista(UUID_TO_BIN('34100000-0000-4000-8000-000000000388'), 'pruebas', @an)",
             "CALL prueba.cr_solicitud('33000000-0000-4000-8000-000000000388', 'C001', 3000, 3, 1, NULL, @r, @e)",
             "CALL creditos.evaluar_solicitud(UUID_TO_BIN('33000000-0000-4000-8000-000000000388'), 1, 20000, 0, 650, 3500, 'pruebas', UUID_TO_BIN(UUID()), @e, @res, @regla)",
             "CALL creditos.decidir_evaluacion(@e, 'APROBADO', 'Ingresos estables y sustentados', UUID_TO_BIN('34000000-0000-4000-8000-000000000001'), 'nuevo.analista', UUID_TO_BIN(UUID()), @estado)"),
  "SELECT @estado = 'APROBADA' AND (SELECT id_analista FROM creditos.v_evaluacion_api WHERE id_evaluacion = @e) = @an",
  'APROBADA por el analista nuevo', "SELECT CONCAT_WS(' ', @estado, @an)", 'procedimiento');

CALL prueba.verifica('X389', 'Extensión', 'Empleados', 'Sin usuario, el empleado se registra y puede ser analista',
  JSON_ARRAY("CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000389'), 'EMP-AN-389', 'Otro Analista', 'ANALISTA', NULL, NULL, 'pruebas')",
             "CALL creditos.registrar_analista(UUID_TO_BIN('34100000-0000-4000-8000-000000000389'), 'pruebas', @an)"),
  "SELECT @an REGEXP '^AN[0-9A-F]{8}$'", 'AN y ocho caracteres', "SELECT @an", 'procedimiento');

CALL prueba.rechaza('X390', 'Extensión', 'Empleados', 'Un código de empleado repetido se rechaza sin mostrar el código',
  JSON_ARRAY("CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000390'), 'EMP-AN-1', 'Otro Analista', 'ANALISTA', 'AQP01', NULL, 'pruebas')"),
  '^BNA-EMPLEADO-DUPLICADO: el código de empleado ya existe$', 'procedimiento');

CALL prueba.rechaza('X391', 'Extensión', 'Empleados', 'Un usuario que ya tiene empleado no se liga a otro',
  JSON_ARRAY("CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000391'), 'EMP-AN-391', 'Otro Analista', 'ANALISTA', 'AQP01', UUID_TO_BIN('32000000-0000-4000-8000-000000000001'), 'pruebas')"),
  '^BNA-USUARIO-EMPLEADO: el usuario ya está ligado a un empleado$', 'procedimiento');

CALL prueba.rechaza('X392', 'Extensión', 'Empleados', 'Un usuario de servicio no se liga a un empleado',
  JSON_ARRAY("CALL core.crear_usuario_servicio(UUID_TO_BIN('34000000-0000-4000-8000-000000000002'), 'svc-x392', 'Servicio', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas')",
             "CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000392'), 'EMP-AN-392', 'Otro Analista', 'ANALISTA', 'AQP01', UUID_TO_BIN('34000000-0000-4000-8000-000000000002'), 'pruebas')"),
  '^BNA-USUARIO-EMPLEADO: un usuario de servicio no se liga a un empleado$', 'procedimiento');

CALL prueba.rechaza('X393', 'Extensión', 'Empleados', 'Un usuario inexistente se rechaza',
  JSON_ARRAY("CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000393'), 'EMP-AN-393', 'Otro Analista', 'ANALISTA', 'AQP01', UUID_TO_BIN(UUID()), 'pruebas')"),
  '^BNA-USUARIO: el usuario no existe$', 'procedimiento');

CALL prueba.rechaza('X394', 'Extensión', 'Empleados', 'Una agencia inexistente se rechaza sin mostrarla',
  JSON_ARRAY("CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000394'), 'EMP-AN-394', 'Otro Analista', 'ANALISTA', 'NOEXISTE', NULL, 'pruebas')"),
  '^BNA-AGENCIA: la agencia no existe$', 'procedimiento');

CALL prueba.rechaza('X395', 'Extensión', 'Empleados', 'El código, el nombre y el cargo son obligatorios',
  JSON_ARRAY("CALL core.registrar_empleado(UUID_TO_BIN('34100000-0000-4000-8000-000000000395'), 'EMP-AN-395', '   ', 'ANALISTA', 'AQP01', NULL, 'pruebas')"),
  '^BNA-EMPLEADO-DATOS: faltan el código, el nombre o el cargo$', 'procedimiento');

CALL prueba.rechaza('X396', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en core.empleado',
  JSON_ARRAY("INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo) VALUES (UUID_TO_BIN(UUID()), 'E396', 'E', 'ANALISTA')"),
  'denied', 'privilegio');

-- ---------------------------------------------------------------------
-- Captación (v1.7): el expediente del prospecto en tablas de extensión de clientes.
-- Ayudantes en arnes_captacion.sql. Caso de la prueba X4NN: 35100000-…-000000000NNN.
-- ---------------------------------------------------------------------
CALL prueba.verifica('X401', 'Extensión', 'Captación', 'Un asesor registra al prospecto con su documento validado por el catálogo',
  JSON_ARRAY("CALL clientes.registrar_solicitante_captacion(prueba.cap_id('35000000', 401), 'DNI', '71000401', ' Rosa ', 'Prospecto', '', '951000401', 'Rosa@Example.com', 'asesor.cap', UUID_TO_BIN(UUID()), @id, @dup)"),
  "SELECT @dup = 0 AND BIN_TO_UUID(@id) = '35000000-0000-4000-8000-000000000401' AND (SELECT COUNT(*) FROM clientes.v_solicitante_captacion_api WHERE id_solicitante = '35000000-0000-4000-8000-000000000401' AND nombres = 'Rosa' AND apellido_materno IS NULL AND correo = 'rosa@example.com' AND cod_cliente IS NULL AND creado_por = 'asesor.cap') = 1",
  'un solicitante nuevo, correo en minúsculas', "SELECT CONCAT_WS(' ', @dup, BIN_TO_UUID(@id))", 'procedimiento');

CALL prueba.verifica('X402', 'Extensión', 'Captación', 'El mismo documento devuelve el mismo solicitante y lo marca como duplicado',
  JSON_ARRAY("CALL prueba.cap_solicitante(402, '71000402', @a)",
             "CALL clientes.registrar_solicitante_captacion(UUID_TO_BIN(UUID()), 'DNI', '71000402', 'Otro', 'Nombre', NULL, '951999402', 'otro@example.com', 'asesor.cap', UUID_TO_BIN(UUID()), @b, @dup)"),
  "SELECT @dup = 1 AND @a = @b AND (SELECT COUNT(*) FROM clientes.v_solicitante_captacion_api WHERE numero_documento = '71000402' AND nombres = 'Prospecto') = 1",
  'el primero, sin cambios', "SELECT CONCAT_WS(' ', @dup, BIN_TO_UUID(@b))", 'procedimiento');

CALL prueba.verifica('X403', 'Extensión', 'Captación', 'El registro del solicitante se audita sin su documento ni su nombre',
  JSON_ARRAY("CALL prueba.cap_solicitante(403, '71000403', @a)"),
  "SELECT (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE modulo = 'CLIENTES' AND entidad = 'solicitante_captacion' AND id_entidad = '35000000-0000-4000-8000-000000000403' AND accion = 'REGISTRAR_SOLICITANTE' AND actor = 'asesor.cap') = 1 AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '35000000-0000-4000-8000-000000000403' AND (detalle LIKE '%71000403%' OR detalle LIKE '%Prospecto%' OR detalle LIKE '%example%')) = 0",
  'un evento REGISTRAR_SOLICITANTE sin datos personales', "SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'REGISTRAR_SOLICITANTE'", 'procedimiento');

CALL prueba.rechaza('X404', 'Extensión', 'Captación', 'Un DNI que no cumple su formato se rechaza sin repetirlo',
  JSON_ARRAY("CALL clientes.registrar_solicitante_captacion(UUID_TO_BIN(UUID()), 'DNI', '7100A', 'Rosa', 'Prospecto', NULL, '951000404', 'r@example.com', 'asesor.cap', UUID_TO_BIN(UUID()), @id, @dup)"),
  '^BNA-DOCUMENTO: el número no cumple el formato de su tipo de documento$', 'procedimiento');

CALL prueba.rechaza('X405', 'Extensión', 'Captación', 'Un celular que no es de nueve dígitos con 9 se rechaza',
  JSON_ARRAY("CALL clientes.registrar_solicitante_captacion(UUID_TO_BIN(UUID()), 'DNI', '71000405', 'Rosa', 'Prospecto', NULL, '851000405', 'r@example.com', 'asesor.cap', UUID_TO_BIN(UUID()), @id, @dup)"),
  '^BNA-SOLICITANTE-DATOS: el celular no es válido$', 'procedimiento');

CALL prueba.verifica('X406', 'Extensión', 'Captación', 'Abrir el caso lo deja INICIADO con lo que falta para habilitarlo',
  JSON_ARRAY("CALL prueba.cap_caso(406, '71000406', @c)"),
  "SELECT (SELECT estado = 'INICIADO' AND canal = 'AGENCIA' AND id_agencia = 'AQP01' AND JSON_CONTAINS(faltantes, '\"Consentimiento TRATAMIENTO_DATOS aceptado\"') AND JSON_CONTAINS(faltantes, '\"Verificación OTP del celular\"') AND JSON_CONTAINS(faltantes, '\"Perfil de riesgo calculado\"') FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000406')",
  'INICIADO con faltantes', "SELECT CONCAT_WS(' ', estado, faltantes) FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000406'", 'procedimiento');

CALL prueba.rechaza('X407', 'Extensión', 'Captación', 'Un solicitante no tiene dos casos abiertos',
  JSON_ARRAY("CALL prueba.cap_caso(407, '71000407', @c)",
             "CALL clientes.abrir_caso_captacion(UUID_TO_BIN(UUID()), prueba.cap_id('35000000', 407), 'WEB', NULL, NULL, 'asesor.cap', UUID_TO_BIN(UUID()))"),
  '^BNA-CASO-ABIERTO: el solicitante ya tiene un caso abierto$', 'procedimiento');

CALL prueba.rechaza('X408', 'Extensión', 'Captación', 'Un caso de un solicitante inexistente se rechaza',
  JSON_ARRAY("CALL clientes.abrir_caso_captacion(UUID_TO_BIN(UUID()), UUID_TO_BIN(UUID()), 'WEB', NULL, NULL, 'asesor.cap', UUID_TO_BIN(UUID()))"),
  '^BNA-SOLICITANTE: el solicitante no existe$', 'procedimiento');

CALL prueba.rechaza('X409', 'Extensión', 'Captación', 'Un canal desconocido se rechaza',
  JSON_ARRAY("CALL prueba.cap_solicitante(409, '71000409', @s)",
             "CALL clientes.abrir_caso_captacion(UUID_TO_BIN(UUID()), @s, 'FAX', NULL, NULL, 'asesor.cap', UUID_TO_BIN(UUID()))"),
  '^BNA-CASO-DATOS: el canal no es válido$', 'procedimiento');

CALL prueba.verifica('X410', 'Extensión', 'Captación', 'Los consentimientos pasan el caso a EN_VALIDACION y TERMINOS guarda su versión',
  JSON_ARRAY("CALL prueba.cap_consentido(410, '71000410', @c)"),
  "SELECT @cap_estado = 'EN_VALIDACION' AND (SELECT COUNT(*) FROM clientes.v_consentimiento_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000410' AND aceptado = 1) = 3 AND (SELECT version FROM clientes.v_consentimiento_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000410' AND tipo = 'TERMINOS') = 'v1' AND (SELECT COUNT(*) FROM clientes.v_consentimiento_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000410' AND tipo <> 'TERMINOS' AND version IS NOT NULL) = 0",
  'EN_VALIDACION, tres aceptados, versión solo en TERMINOS', "SELECT @cap_estado", 'procedimiento');

CALL prueba.rechaza('X411', 'Extensión', 'Captación', 'Un tipo de consentimiento desconocido se rechaza',
  JSON_ARRAY("CALL prueba.cap_caso(411, '71000411', @c)",
             "CALL clientes.registrar_consentimientos_captacion(@c, JSON_ARRAY(JSON_OBJECT('tipo', 'MARKETING', 'aceptado', TRUE, 'medio', 'DIGITAL')), 'v1', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-CONSENTIMIENTO-DATOS: tipo, aceptación o medio no válidos$', 'procedimiento');

CALL prueba.rechaza('X412', 'Extensión', 'Captación', 'Sin consentimiento de tratamiento de datos no se envía un OTP',
  JSON_ARRAY("CALL prueba.cap_caso(412, '71000412', @c)",
             "CALL clientes.emitir_otp_captacion(UUID_TO_BIN(UUID()), @c, 'SMS', REPEAT('a', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @x)"),
  '^BNA-CONSENTIMIENTO-REQUERIDO: falta el consentimiento TRATAMIENTO_DATOS$', 'procedimiento');

CALL prueba.verifica('X413', 'Extensión', 'Captación', 'Un OTP nuevo vence en los minutos del catálogo y deja vencido al pendiente anterior del mismo canal',
  JSON_ARRAY("CALL prueba.cap_consentido(413, '71000413', @c)",
             "CALL clientes.emitir_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000413'), @c, 'SMS', REPEAT('a', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @x1)",
             "CALL clientes.emitir_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000001413'), @c, 'SMS', REPEAT('b', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @x2)"),
  "SELECT (SELECT estado FROM clientes.v_otp_captacion_api WHERE id_otp = '35200000-0000-4000-8000-000000000413') = 'EXPIRADO' AND (SELECT estado = 'PENDIENTE' AND TIMESTAMPDIFF(SECOND, fecha_emision, fecha_expiracion) = 300 AND fecha_expiracion = @x2 FROM clientes.v_otp_captacion_api WHERE id_otp = '35200000-0000-4000-8000-000000001413')",
  'el primero EXPIRADO, el segundo PENDIENTE por 5 minutos', "SELECT GROUP_CONCAT(estado) FROM clientes.v_otp_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000413'", 'procedimiento');

CALL prueba.verifica('X414', 'Extensión', 'Captación', 'El código correcto queda USADO y registra la verificación del celular',
  JSON_ARRAY("CALL prueba.cap_consentido(414, '71000414', @c)",
             "CALL clientes.emitir_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000414'), @c, 'SMS', REPEAT('a', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @x)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000414'), @c, REPEAT('a', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @cod, @rest, @est)"),
  "SELECT @cod = 'USADO' AND @rest = 3 AND (SELECT COUNT(*) FROM clientes.v_validacion_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000414' AND tipo = 'CELULAR' AND resultado = 'APROBADO' AND proveedor = 'OTP-SMS') = 1",
  'USADO y CELULAR APROBADO', "SELECT CONCAT_WS(' ', @cod, @rest, @est)", 'procedimiento');

CALL prueba.verifica('X415', 'Extensión', 'Captación', 'El tercer código errado bloquea el OTP y no verifica el celular',
  JSON_ARRAY("CALL prueba.cap_consentido(415, '71000415', @c)",
             "CALL clientes.emitir_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000415'), @c, 'SMS', REPEAT('a', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @x)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000415'), @c, REPEAT('b', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @cod1, @rest1, @est)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000415'), @c, REPEAT('b', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @cod2, @rest2, @est)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000415'), @c, REPEAT('b', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @cod3, @rest3, @est)"),
  "SELECT @cod1 = 'PENDIENTE' AND @rest1 = 2 AND @cod3 = 'BLOQUEADO' AND @rest3 = 0 AND (SELECT intentos_fallidos FROM clientes.v_otp_captacion_api WHERE id_otp = '35200000-0000-4000-8000-000000000415') = 3 AND (SELECT COUNT(*) FROM clientes.v_validacion_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000415') = 0",
  'BLOQUEADO al tercero, sin validación', "SELECT CONCAT_WS(' ', @cod1, @rest1, @cod3, @rest3)", 'procedimiento');

CALL prueba.rechaza('X416', 'Extensión', 'Captación', 'Un OTP bloqueado ya no se verifica',
  JSON_ARRAY("CALL prueba.cap_consentido(416, '71000416', @c)",
             "CALL clientes.emitir_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000416'), @c, 'SMS', REPEAT('a', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @x)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000416'), @c, REPEAT('b', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @a, @b, @e)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000416'), @c, REPEAT('b', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @a, @b, @e)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000416'), @c, REPEAT('b', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @a, @b, @e)",
             "CALL clientes.verificar_otp_captacion(UUID_TO_BIN('35200000-0000-4000-8000-000000000416'), @c, REPEAT('a', 64), 'asesor.cap', UUID_TO_BIN(UUID()), @a, @b, @e)"),
  '^BNA-OTP: no hay un código pendiente$', 'procedimiento');

CALL prueba.rechaza('X417', 'Extensión', 'Captación', 'El celular y el correo se verifican solo con un OTP',
  JSON_ARRAY("CALL prueba.cap_consentido(417, '71000417', @c)",
             "CALL clientes.registrar_validacion_captacion(@c, 'CELULAR', 'APROBADO', 'MANUAL', 'Llamada', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-VALIDACION-CAPTACION: tipo o resultado no válidos$', 'procedimiento');

CALL prueba.rechaza('X418', 'Extensión', 'Captación', 'La biometría exige su propio consentimiento',
  JSON_ARRAY("CALL prueba.cap_consentido(418, '71000418', @c)",
             "CALL clientes.registrar_validacion_captacion(@c, 'BIOMETRIA', 'APROBADO', 'SIMULADO', 'Rostro', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-CONSENTIMIENTO-REQUERIDO: falta el consentimiento BIOMETRIA$', 'procedimiento');

CALL prueba.verifica('X419', 'Extensión', 'Captación', 'Una validación rechazada cierra el caso como RECHAZADO con su motivo',
  JSON_ARRAY("CALL prueba.cap_consentido(419, '71000419', @c)",
             "CALL clientes.registrar_validacion_captacion(@c, 'LISTAS_NEGRAS', 'RECHAZADO', 'SIMULADO', 'Coincidencia', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  "SELECT @e = 'RECHAZADO' AND (SELECT motivo_cierre = 'Validación rechazada: LISTAS_NEGRAS' AND fecha_cierre IS NOT NULL AND JSON_LENGTH(faltantes) = 0 FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000419')",
  'RECHAZADO, cerrado, sin faltantes', "SELECT CONCAT_WS(' ', estado, motivo_cierre) FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000419'", 'procedimiento');

CALL prueba.rechaza('X420', 'Extensión', 'Captación', 'Un caso cerrado no admite cambios',
  JSON_ARRAY("CALL prueba.cap_consentido(420, '71000420', @c)",
             "CALL clientes.registrar_validacion_captacion(@c, 'RENIEC', 'RECHAZADO', 'SIMULADO', 'No coincide', 'asesor.cap', UUID_TO_BIN(UUID()), @e)",
             "CALL clientes.registrar_validacion_captacion(@c, 'RENIEC', 'APROBADO', 'MANUAL', 'Revisado', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-CASO-CERRADO: el caso ya no admite cambios$', 'procedimiento');

CALL prueba.verifica('X421', 'Extensión', 'Captación', 'Una validación OBSERVADA deja el caso OBSERVADO hasta que una revisión manual la reemplaza',
  JSON_ARRAY("CALL prueba.cap_consentido(421, '71000421', @c)",
             "CALL clientes.registrar_validacion_captacion(@c, 'PEP', 'OBSERVADO', 'SIMULADO', 'Posible PEP', 'asesor.cap', UUID_TO_BIN(UUID()), @e1)",
             "CALL clientes.registrar_validacion_captacion(@c, 'PEP', 'APROBADO', 'MANUAL', 'Debida diligencia', 'asesor.cap', UUID_TO_BIN(UUID()), @e2)"),
  "SELECT @e1 = 'OBSERVADO' AND @e2 = 'EN_VALIDACION'",
  'OBSERVADO y luego EN_VALIDACION', "SELECT CONCAT_WS(' ', @e1, @e2)", 'procedimiento');

CALL prueba.rechaza('X422', 'Extensión', 'Captación', 'Sin consentimiento de consulta a burós no se consulta una central',
  JSON_ARRAY("CALL prueba.cap_caso(422, '71000422', @c)",
             "CALL clientes.registrar_consentimientos_captacion(@c, JSON_ARRAY(JSON_OBJECT('tipo', 'TRATAMIENTO_DATOS', 'aceptado', TRUE, 'medio', 'DIGITAL'), JSON_OBJECT('tipo', 'CONSULTA_BUROS', 'aceptado', FALSE, 'medio', 'DIGITAL')), 'v1', 'asesor.cap', UUID_TO_BIN(UUID()), @e)",
             "CALL clientes.registrar_consulta_riesgo_captacion(@c, 'SBS', 'NORMAL', 0, 0, 0, 'SIMULADO', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-CONSENTIMIENTO-REQUERIDO: falta el consentimiento CONSULTA_BUROS$', 'procedimiento');

CALL prueba.rechaza('X423', 'Extensión', 'Captación', 'El perfil de riesgo exige al menos una consulta a una central',
  JSON_ARRAY("CALL prueba.cap_consentido(423, '71000423', @c)",
             "CALL clientes.registrar_perfil_captacion(@c, 800, 'BAJO', NULL, 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-SIN-CONSULTA: consulte al menos una central de riesgo$', 'procedimiento');

CALL prueba.verifica('X424', 'Extensión', 'Captación', 'Con todo lo requerido el caso queda APROBADO y sin faltantes',
  JSON_ARRAY("CALL prueba.cap_listo(424, '71000424', @c)"),
  "SELECT (SELECT estado = 'APROBADO' AND JSON_LENGTH(faltantes) = 0 FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000424') AND (SELECT puntaje = 820 AND vigente = 1 FROM clientes.v_perfil_riesgo_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000424')",
  'APROBADO, perfil vigente', "SELECT CONCAT_WS(' ', estado, faltantes) FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000424'", 'procedimiento');

CALL prueba.verifica('X425', 'Extensión', 'Captación', 'Una consulta posterior al perfil exige recalcularlo',
  JSON_ARRAY("CALL prueba.cap_listo(425, '71000425', @c)",
             "CALL clientes.registrar_consulta_riesgo_captacion(@c, 'INFOCORP', 'CPP', 1500.50, 2, 15, 'MANUAL', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  "SELECT @e = 'EN_VALIDACION' AND (SELECT JSON_CONTAINS(faltantes, '\"Perfil de riesgo actualizado con la última consulta\"') FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000425') AND (SELECT vigente = 0 FROM clientes.v_perfil_riesgo_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000425')",
  'EN_VALIDACION, perfil no vigente', "SELECT @e", 'procedimiento');

CALL prueba.verifica('X426', 'Extensión', 'Captación', 'Un perfil MUY_ALTO rechaza el caso',
  JSON_ARRAY("CALL prueba.cap_listo(426, '71000426', @c)",
             "CALL clientes.registrar_perfil_captacion(@c, 150, 'MUY_ALTO', 'Mora alta', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  "SELECT @e = 'RECHAZADO' AND (SELECT motivo_cierre FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000426') = 'Perfil de riesgo MUY_ALTO'",
  'RECHAZADO por el perfil', "SELECT @e", 'procedimiento');

CALL prueba.verifica('X427', 'Extensión', 'Captación', 'La observación del asesor detiene el caso y al levantarla vuelve a APROBADO',
  JSON_ARRAY("CALL prueba.cap_listo(427, '71000427', @c)",
             "CALL clientes.cambiar_estado_caso_captacion(@c, 'OBSERVAR', 'Falta sustento de domicilio', 'asesor.cap', UUID_TO_BIN(UUID()), @e1)",
             "CALL clientes.cambiar_estado_caso_captacion(@c, 'LEVANTAR_OBSERVACION', 'Domicilio sustentado', 'asesor.cap', UUID_TO_BIN(UUID()), @e2)"),
  "SELECT @e1 = 'OBSERVADO' AND @e2 = 'APROBADO' AND (SELECT observacion IS NULL FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000427')",
  'OBSERVADO y luego APROBADO', "SELECT CONCAT_WS(' ', @e1, @e2)", 'procedimiento');

CALL prueba.verifica('X428', 'Extensión', 'Captación', 'El asesor rechaza un caso abierto con su motivo',
  JSON_ARRAY("CALL prueba.cap_caso(428, '71000428', @c)",
             "CALL clientes.cambiar_estado_caso_captacion(@c, 'RECHAZAR', 'Desistió', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  "SELECT @e = 'RECHAZADO' AND (SELECT motivo_cierre = 'Desistió' AND fecha_cierre IS NOT NULL FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000428')",
  'RECHAZADO', "SELECT @e", 'procedimiento');

CALL prueba.verifica('X429', 'Extensión', 'Captación', 'Cerrado un caso, el solicitante puede abrir otro',
  JSON_ARRAY("CALL prueba.cap_caso(429, '71000429', @c)",
             "CALL clientes.cambiar_estado_caso_captacion(@c, 'RECHAZAR', 'Desistió', 'asesor.cap', UUID_TO_BIN(UUID()), @e)",
             "CALL clientes.abrir_caso_captacion(UUID_TO_BIN('35100000-0000-4000-8000-000000001429'), prueba.cap_id('35000000', 429), 'WEB', NULL, NULL, 'asesor.cap', UUID_TO_BIN(UUID()))"),
  "SELECT (SELECT COUNT(*) FROM clientes.v_caso_captacion_api WHERE id_solicitante = '35000000-0000-4000-8000-000000000429') = 2",
  'dos casos, uno abierto', "SELECT GROUP_CONCAT(estado) FROM clientes.v_caso_captacion_api WHERE id_solicitante = '35000000-0000-4000-8000-000000000429'", 'procedimiento');

CALL prueba.rechaza('X430', 'Extensión', 'Captación', 'Solo se revoca un caso HABILITADO',
  JSON_ARRAY("CALL prueba.cap_listo(430, '71000430', @c)",
             "CALL clientes.cambiar_estado_caso_captacion(@c, 'REVOCAR', 'Fraude', 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-CASO-ESTADO: solo se revoca un caso HABILITADO$', 'procedimiento');

CALL prueba.rechaza('X431', 'Extensión', 'Captación', 'Un caso que no está listo no se liga a un cliente',
  JSON_ARRAY("CALL prueba.cap_consentido(431, '70000001', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C001', FALSE, 'asesor.cap', UUID_TO_BIN(UUID()))"),
  '^BNA-CASO-NO-LISTO: el caso no cumple los requisitos para habilitarse$', 'procedimiento');

CALL prueba.rechaza('X432', 'Extensión', 'Captación', 'El cliente ligado debe tener el documento del solicitante',
  JSON_ARRAY("CALL prueba.cap_listo(432, '71000432', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C001', FALSE, 'asesor.cap', UUID_TO_BIN(UUID()))"),
  '^BNA-CLIENTE-DOCUMENTO: el cliente no tiene el documento del solicitante$', 'procedimiento');

CALL prueba.rechaza('X433', 'Extensión', 'Captación', 'Un cliente que no está ACTIVO no se liga',
  JSON_ARRAY("CALL prueba.cap_listo(433, '70000004', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C004', FALSE, 'asesor.cap', UUID_TO_BIN(UUID()))"),
  '^BNA-CLIENTE-NO-ACTIVO: el cliente no está ACTIVO$', 'procedimiento');

CALL prueba.rechaza('X434', 'Extensión', 'Captación', 'Sin cliente ligado el caso no se habilita',
  JSON_ARRAY("CALL prueba.cap_listo(434, '71000434', @c)",
             "CALL clientes.habilitar_caso_captacion(@c, 30, 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-CASO-NO-LISTO: el caso no tiene un cliente ligado$', 'procedimiento');

CALL prueba.verifica('X435', 'Extensión', 'Captación', 'Un cliente existente se liga y el caso se habilita con su vigencia',
  JSON_ARRAY("CALL prueba.cap_listo(435, '70000001', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C001', FALSE, 'svc-captacion', UUID_TO_BIN(UUID()))",
             "CALL clientes.habilitar_caso_captacion(@c, 30, 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  "SELECT @e = 'HABILITADO' AND (SELECT cod_cliente = 'C001' AND cliente_nuevo = 0 AND estado_cliente = 'ACTIVO' AND id_verificacion_captacion = 'VC-1' AND fecha_verificacion = core.fn_fecha_negocio(UTC_TIMESTAMP(6)) AND vigente_hasta = fecha_verificacion + INTERVAL 30 DAY AND fecha_cierre IS NOT NULL FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000435') AND (SELECT cod_cliente FROM clientes.v_solicitante_captacion_api WHERE id_solicitante = '35000000-0000-4000-8000-000000000435') = 'C001'",
  'HABILITADO con C001 por 30 días', "SELECT CONCAT_WS(' ', estado, cod_cliente, fecha_verificacion, vigente_hasta) FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000435'", 'procedimiento');

CALL prueba.verifica('X436', 'Extensión', 'Captación', 'Un cliente nuevo registrado HABILITADO se liga, y la verificación del celular queda también en el cliente',
  JSON_ARRAY("CALL prueba.cap_listo(436, '71000436', @c)",
             "CALL clientes.registrar_cliente('DNI', '71000436', 'Prospecto', 'Ficticio', NULL, 'p436@example.com', '950000436', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'svc-captacion', @cli)",
             "CALL clientes.vincular_cliente_captacion(@c, @cli, TRUE, 'svc-captacion', UUID_TO_BIN(UUID()))",
             "CALL clientes.habilitar_caso_captacion(@c, 30, 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  "SELECT @e = 'HABILITADO' AND (SELECT cliente_nuevo = 1 AND cod_cliente = @cli FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000436') AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'REGISTRAR_VALIDACION' AND JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.cod_cliente')) = @cli AND JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.tipo_validacion')) = 'CELULAR' AND actor = 'asesor.cap') = 1",
  'HABILITADO y la validación CELULAR del cliente', "SELECT CONCAT_WS(' ', @e, @cli)", 'procedimiento');

CALL prueba.verifica('X437', 'Extensión', 'Captación', 'Habilitar otra vez no cambia nada ni repite eventos',
  JSON_ARRAY("CALL prueba.cap_listo(437, '70000002', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C002', FALSE, 'svc-captacion', UUID_TO_BIN(UUID()))",
             "CALL clientes.habilitar_caso_captacion(@c, 30, 'asesor.cap', UUID_TO_BIN(UUID()), @e1)",
             "CALL clientes.habilitar_caso_captacion(@c, 60, 'asesor.cap', UUID_TO_BIN(UUID()), @e2)"),
  "SELECT @e1 = 'HABILITADO' AND @e2 = 'HABILITADO' AND (SELECT vigente_hasta = fecha_verificacion + INTERVAL 30 DAY FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000437') AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '35100000-0000-4000-8000-000000000437' AND accion = 'HABILITAR') = 1",
  'un solo HABILITAR, vigencia de la primera', "SELECT CONCAT_WS(' ', @e1, @e2)", 'procedimiento');

CALL prueba.verifica('X438', 'Extensión', 'Captación', 'Un caso HABILITADO se revoca con su motivo',
  JSON_ARRAY("CALL prueba.cap_listo(438, '70000003', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C003', FALSE, 'svc-captacion', UUID_TO_BIN(UUID()))",
             "CALL clientes.habilitar_caso_captacion(@c, 30, 'asesor.cap', UUID_TO_BIN(UUID()), @e1)",
             "CALL clientes.cambiar_estado_caso_captacion(@c, 'REVOCAR', 'Documento adulterado', 'asesor.cap', UUID_TO_BIN(UUID()), @e2)"),
  "SELECT @e2 = 'REVOCADO' AND (SELECT motivo_cierre = 'Documento adulterado' AND cod_cliente = 'C003' FROM clientes.v_caso_captacion_api WHERE id_caso = '35100000-0000-4000-8000-000000000438')",
  'REVOCADO', "SELECT @e2", 'procedimiento');

CALL prueba.rechaza('X439', 'Extensión', 'Captación', 'La vigencia de la habilitación va de 1 a 365 días',
  JSON_ARRAY("CALL prueba.cap_listo(439, '70000001', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C001', FALSE, 'svc-captacion', UUID_TO_BIN(UUID()))",
             "CALL clientes.habilitar_caso_captacion(@c, 0, 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  '^BNA-CASO-DATOS: la vigencia va de 1 a 365 días$', 'procedimiento');

CALL prueba.verifica('X440', 'Extensión', 'Captación', 'Cada paso del expediente se audita con su actor, sin el documento ni el hash del OTP',
  JSON_ARRAY("CALL prueba.cap_listo(440, '70000001', @c)",
             "CALL clientes.vincular_cliente_captacion(@c, 'C001', FALSE, 'svc-captacion', UUID_TO_BIN(UUID()))",
             "CALL clientes.habilitar_caso_captacion(@c, 30, 'asesor.cap', UUID_TO_BIN(UUID()), @e)"),
  "SELECT (SELECT COUNT(DISTINCT accion) FROM core.v_evento_auditoria_api WHERE modulo = 'CLIENTES' AND entidad = 'caso_captacion' AND id_entidad = '35100000-0000-4000-8000-000000000440' AND accion IN ('ABRIR_CASO', 'REGISTRAR_CONSENTIMIENTOS', 'ENVIAR_OTP', 'VERIFICAR_OTP', 'REGISTRAR_VALIDACION', 'CONSULTAR_CENTRAL', 'CALCULAR_PERFIL', 'VINCULAR_CLIENTE', 'HABILITAR')) = 9 AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '35100000-0000-4000-8000-000000000440' AND (detalle LIKE '%70000001%' OR detalle LIKE '%aaaaaaaa%')) = 0",
  'nueve acciones auditadas', "SELECT GROUP_CONCAT(DISTINCT accion) FROM core.v_evento_auditoria_api WHERE id_entidad = '35100000-0000-4000-8000-000000000440'", 'procedimiento');

CALL prueba.verifica('X441', 'Extensión', 'Captación', 'La vista de OTP de la API no expone el hash del código',
  JSON_ARRAY("DO 0"),
  "SELECT (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'clientes' AND table_name = 'v_otp_captacion_api') > 0 AND (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'clientes' AND table_name = 'v_otp_captacion_api' AND column_name LIKE '%codigo%') = 0",
  'sin columna del código', "SELECT GROUP_CONCAT(column_name) FROM information_schema.columns WHERE table_schema = 'clientes' AND table_name = 'v_otp_captacion_api'", 'declarativo');

CALL prueba.rechaza('X442', 'Extensión', 'bna_api', 'bna_api no puede: leer clientes.otp_captacion (el hash del código)',
  JSON_ARRAY("SELECT COUNT(*) INTO @n FROM clientes.otp_captacion"),
  'denied', 'privilegio');

CALL prueba.rechaza('X443', 'Extensión', 'bna_api', 'bna_api no puede: UPDATE en clientes.caso_captacion',
  JSON_ARRAY("UPDATE clientes.caso_captacion SET estado = 'APROBADO'"),
  'denied', 'privilegio');

-- ---------------------------------------------------------------------
-- Billetera Digital (v1.9). prueba.bd_afiliar afilia a C001 (CTA-PEN-1, PIN 123456)
-- y a C002 (CTA-PEN-2, PIN 654321); los celulares son los de clientes.cliente.
-- ---------------------------------------------------------------------
CALL prueba.verifica('X600', 'Extensión', 'Billetera', 'Un cliente ACTIVO se afilia con su cuenta en soles y queda auditado sin el PIN',
  JSON_ARRAY("CALL prueba.bd_afiliar()"),
  "SELECT (SELECT estado = 'ACTIVA' AND num_cuenta = 'CTA-PEN-1' AND intentos_fallidos = 0 AND nombre_corto = 'Juan P.' AND tope_diario = 500 FROM billetera.v_afiliacion_api WHERE cod_cliente = 'C001') AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE modulo = 'BILLETERA' AND accion = 'AFILIAR' AND id_entidad = 'C001' AND actor = 'asesor.bd' AND detalle NOT LIKE '%123456%') = 1",
  'C001 ACTIVA con CTA-PEN-1 y un evento AFILIAR', "SELECT CONCAT_WS(' ', estado, num_cuenta, nombre_corto) FROM billetera.v_afiliacion_api WHERE cod_cliente = 'C001'", 'procedimiento');

CALL prueba.rechaza('X601', 'Extensión', 'Billetera', 'El PIN de la billetera tiene 6 dígitos',
  JSON_ARRAY("CALL billetera.afiliar('C001', 'CTA-PEN-1', '12345', 'asesor.bd', NULL, @n)"),
  '^BNA-BILLETERA-PIN: el PIN debe tener 6 dígitos$', 'procedimiento');

CALL prueba.rechaza('X602', 'Extensión', 'Billetera', 'Un cliente que no está ACTIVO no se afilia',
  JSON_ARRAY("CALL billetera.afiliar('C004', 'CTA-PEN-1', '123456', 'asesor.bd', NULL, @n)"),
  '^BNA-CLIENTE-NO-ACTIVO: el cliente no está ACTIVO$', 'procedimiento');

CALL prueba.rechaza('X603', 'Extensión', 'Billetera', 'La cuenta de la billetera es del cliente',
  JSON_ARRAY("CALL billetera.afiliar('C001', 'CTA-PEN-2', '123456', 'asesor.bd', NULL, @n)"),
  '^BNA-BILLETERA-TITULAR: el cliente no es titular de la cuenta$', 'procedimiento');

CALL prueba.rechaza('X604', 'Extensión', 'Billetera', 'La billetera opera solo en soles',
  JSON_ARRAY("CALL billetera.afiliar('C001', 'CTA-USD-1', '123456', 'asesor.bd', NULL, @n)"),
  '^BNA-BILLETERA-MONEDA: la billetera opera solo en soles', 'procedimiento');

CALL prueba.rechaza('X605', 'Extensión', 'Billetera', 'Una cuenta de firma conjunta no es de billetera',
  JSON_ARRAY("CALL billetera.afiliar('C001', 'CTA-CONJ', '123456', 'asesor.bd', NULL, @n)"),
  '^BNA-BILLETERA-CUENTA: la cuenta debe estar ACTIVA y no exigir firma conjunta$', 'procedimiento');

CALL prueba.verifica('X606', 'Extensión', 'Billetera', 'Celular y PIN correctos devuelven el cliente',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.validar_acceso('959000001', '123456', NULL, @c, @r, @i)"),
  "SELECT @r = 'EXITOSO' AND @c = 'C001' AND @i = 3",
  'EXITOSO C001 3', "SELECT CONCAT_WS(' ', @r, @c, @i)", 'procedimiento');

CALL prueba.verifica('X607', 'Extensión', 'Billetera', 'Un PIN equivocado no es un error: cuenta el intento y no devuelve el cliente',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.validar_acceso('959000001', '000000', NULL, @c, @r, @i)"),
  "SELECT @r = 'FALLIDO' AND @c IS NULL AND @i = 2 AND (SELECT intentos_fallidos FROM billetera.v_afiliacion_api WHERE cod_cliente = 'C001') = 1",
  'FALLIDO sin cliente, 2 restantes', "SELECT CONCAT_WS(' ', @r, coalesce(@c, '-'), @i)", 'procedimiento');

CALL prueba.verifica('X608', 'Extensión', 'Billetera', 'Al tercer PIN equivocado la billetera se bloquea, y luego ni el PIN correcto entra',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.validar_acceso('959000001', '000000', NULL, @c, @r, @i)",
             "CALL billetera.validar_acceso('959000001', '000001', NULL, @c, @r, @i)",
             "CALL billetera.validar_acceso('959000001', '000002', NULL, @c, @r3, @i3)",
             "CALL billetera.validar_acceso('959000001', '123456', NULL, @c, @r, @i)"),
  "SELECT @r3 = 'FALLIDO' AND @i3 = 0 AND @r = 'BLOQUEADA' AND @c IS NULL AND (SELECT estado FROM billetera.v_afiliacion_api WHERE cod_cliente = 'C001') = 'BLOQUEADA'",
  'tercero FALLIDO, luego BLOQUEADA', "SELECT CONCAT_WS(' ', @r3, @i3, @r)", 'procedimiento');

CALL prueba.verifica('X609', 'Extensión', 'Billetera', 'Un celular sin billetera o desconocido es NO_AFILIADO',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.validar_acceso('959000003', '123456', NULL, @c1, @r1, @i1)",
             "CALL billetera.validar_acceso('900000000', '123456', NULL, @c2, @r2, @i2)"),
  "SELECT @r1 = 'NO_AFILIADO' AND @r2 = 'NO_AFILIADO' AND @c1 IS NULL AND @c2 IS NULL",
  'NO_AFILIADO NO_AFILIADO', "SELECT CONCAT_WS(' ', @r1, @r2)", 'procedimiento');

CALL prueba.verifica('X610', 'Extensión', 'Billetera', 'Afiliar otra vez cambia el PIN, desbloquea y reinicia los intentos',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.validar_acceso('959000001', '000000', NULL, @c, @r, @i)",
             "CALL billetera.validar_acceso('959000001', '000001', NULL, @c, @r, @i)",
             "CALL billetera.validar_acceso('959000001', '000002', NULL, @c, @r, @i)",
             "CALL billetera.afiliar('C001', 'CTA-PEN-1', '111222', 'asesor.bd', NULL, @nueva)",
             "CALL billetera.validar_acceso('959000001', '123456', NULL, @c1, @r1, @i1)",
             "CALL billetera.validar_acceso('959000001', '111222', NULL, @c2, @r2, @i2)"),
  "SELECT @nueva = 0 AND @r1 = 'FALLIDO' AND @r2 = 'EXITOSO' AND @c2 = 'C001' AND (SELECT estado = 'ACTIVA' AND intentos_fallidos = 0 FROM billetera.v_afiliacion_api WHERE cod_cliente = 'C001') AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'CAMBIAR_PIN' AND id_entidad = 'C001') = 1",
  'PIN viejo FALLIDO, nuevo EXITOSO', "SELECT CONCAT_WS(' ', @nueva, @r1, @r2)", 'procedimiento');

CALL prueba.verifica('X611', 'Extensión', 'Billetera', 'La bitácora del acceso no guarda el celular ni el PIN',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.validar_acceso('959000001', '123456', NULL, @c, @r, @i)",
             "CALL billetera.validar_acceso('959000001', '987654', NULL, @c, @r, @i)"),
  "SELECT (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE modulo = 'BILLETERA' AND accion = 'VALIDAR_ACCESO' AND id_entidad = 'C001' AND actor = 'cliente:C001') = 2 AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE modulo = 'BILLETERA' AND (detalle LIKE '%959000001%' OR detalle LIKE '%123456%' OR detalle LIKE '%987654%' OR id_entidad LIKE '%959%')) = 0",
  'dos eventos sin celular ni PIN', "SELECT GROUP_CONCAT(detalle) FROM core.v_evento_auditoria_api WHERE accion = 'VALIDAR_ACCESO'", 'procedimiento');

CALL prueba.verifica('X612', 'Extensión', 'Billetera', 'Un envío por celular mueve el dinero por el canal BD, registra la operación y avisa a los dos',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.transferir('C001', '959000002', 100, 'Almuerzo', 'k612', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  "SELECT @r = 0 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @bd_s1 - 100 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @bd_s2 + 100 AND (SELECT tipo = 'P2P' AND monto = 100 AND nombre_destino = 'Ana D.' AND referencia = 'Almuerzo' AND uuid_debito = BIN_TO_UUID(@d) FROM billetera.v_operacion_api WHERE id_operacion = BIN_TO_UUID(@o)) AND (SELECT COUNT(*) FROM cuentas.v_movimiento_api WHERE id_canal = 'BD' AND (uuid_transaccion = @d OR uuid_transaccion = (SELECT uuid_abono FROM cuentas.idempotencia_movimiento WHERE llave = 'k612'))) = 2 AND (SELECT COUNT(*) FROM billetera.v_notificacion_api WHERE id_operacion = BIN_TO_UUID(@o)) = 2",
  '−100 y +100 por BD, operación P2P y dos avisos', "SELECT CONCAT_WS(' ', @r, (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') - @bd_s1)", 'procedimiento');

CALL prueba.verifica('X613', 'Extensión', 'Billetera', 'Repetir un envío con la misma llave devuelve la misma operación y no cobra dos veces',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.transferir('C001', '959000002', 100, NULL, 'k613', REPEAT('a', 64), 'cliente:C001', NULL, @o1, @d1, @r1)",
             "CALL billetera.transferir('C001', '959000002', 100, NULL, 'k613', REPEAT('a', 64), 'cliente:C001', NULL, @o2, @d2, @r2)"),
  "SELECT @r1 = 0 AND @r2 = 1 AND @o1 = @o2 AND @d1 = @d2 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @bd_s1 - 100 AND (SELECT COUNT(*) FROM billetera.v_operacion_api WHERE cod_cliente_origen = 'C001') = 1",
  'repetida, misma operación, un solo débito', "SELECT CONCAT_WS(' ', @r1, @r2, @o1 = @o2)", 'procedimiento');

CALL prueba.rechaza('X614', 'Extensión', 'Billetera', 'La misma llave con otros parámetros se rechaza',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.transferir('C001', '959000002', 100, NULL, 'k614', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)",
             "CALL billetera.transferir('C001', '959000002', 200, NULL, 'k614', REPEAT('b', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-IDEMPOTENCIA: la llave k614 se usó con otros parámetros$', 'procedimiento');

CALL prueba.rechaza('X615', 'Extensión', 'Billetera', 'Un celular sin billetera no recibe, y el error no repite el celular',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.transferir('C001', '959000003', 10, NULL, 'k615', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-BILLETERA-DESTINO: el celular no tiene una billetera que pueda recibir$', 'procedimiento');

CALL prueba.rechaza('X616', 'Extensión', 'Billetera', 'Nadie se envía dinero a sí mismo',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.transferir('C001', '959000001', 10, NULL, 'k616', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-BILLETERA-PROPIA: el origen y el destino son la misma billetera$', 'procedimiento');

CALL prueba.rechaza('X617', 'Extensión', 'Billetera', 'Un envío respeta el tope diario del canal BD (500 PEN)',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.transferir('C001', '959000002', 600, NULL, 'k617', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^RN-TOP-001: tope diario de BD excedido', 'trigger');

CALL prueba.rechaza('X618', 'Extensión', 'Billetera', 'Una operación de dinero sin llave de idempotencia se rechaza',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.transferir('C001', '959000002', 10, NULL, NULL, NULL, 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-IDEMPOTENCIA: la llave de idempotencia es obligatoria$', 'procedimiento');

CALL prueba.verifica('X619', 'Extensión', 'Billetera', 'El QR estático de un cliente es siempre el mismo',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_qr('C001', NULL, NULL, 'cliente:C001', NULL, @q1, @n1)",
             "CALL billetera.crear_qr('C001', NULL, NULL, 'cliente:C001', NULL, @q2, @n2)"),
  "SELECT @q1 = @q2 AND @n1 = 1 AND @n2 = 0 AND (SELECT tipo = 'ESTATICO' AND monto IS NULL AND estado = 'ACTIVO' AND beneficiario = 'Juan P.' AND num_cuenta = 'CTA-PEN-1' FROM billetera.v_qr_api WHERE id_qr = BIN_TO_UUID(@q1))",
  'un solo QR estático', "SELECT CONCAT_WS(' ', @n1, @n2, @q1 = @q2)", 'procedimiento');

CALL prueba.verifica('X620', 'Extensión', 'Billetera', 'Un QR dinámico lleva su monto y vence a los 15 minutos',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_qr('C002', 25.50, NULL, 'cliente:C002', NULL, @q, @n)"),
  "SELECT (SELECT tipo = 'DINAMICO' AND monto = 25.50 AND estado = 'ACTIVO' AND TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(6), fecha_expiracion) BETWEEN 800 AND 900 FROM billetera.v_qr_api WHERE id_qr = BIN_TO_UUID(@q))",
  'DINAMICO 25.50 ACTIVO', "SELECT CONCAT_WS(' ', tipo, monto, estado) FROM billetera.v_qr_api WHERE id_qr = BIN_TO_UUID(@q)", 'procedimiento');

CALL prueba.verifica('X621', 'Extensión', 'Billetera', 'Pagar un QR dinámico cobra su monto y lo deja PAGADO',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.crear_qr('C002', 30, NULL, 'cliente:C002', NULL, @q, @n)",
             "CALL billetera.pagar_qr('C001', @q, NULL, 'k621', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  "SELECT @r = 0 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @bd_s1 - 30 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @bd_s2 + 30 AND (SELECT estado FROM billetera.v_qr_api WHERE id_qr = BIN_TO_UUID(@q)) = 'PAGADO' AND (SELECT tipo = 'QR' AND id_qr = BIN_TO_UUID(@q) AND cod_cliente_destino = 'C002' FROM billetera.v_operacion_api WHERE id_operacion = BIN_TO_UUID(@o))",
  '−30 y +30, QR PAGADO', "SELECT CONCAT_WS(' ', @r, (SELECT estado FROM billetera.v_qr_api WHERE id_qr = BIN_TO_UUID(@q)))", 'procedimiento');

CALL prueba.rechaza('X622', 'Extensión', 'Billetera', 'Un QR dinámico ya pagado no se paga otra vez con otra llave',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_qr('C002', 30, NULL, 'cliente:C002', NULL, @q, @n)",
             "CALL billetera.pagar_qr('C001', @q, NULL, 'k622a', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)",
             "CALL billetera.pagar_qr('C001', @q, NULL, 'k622b', REPEAT('b', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-QR-NO-VIGENTE: el código QR ya no está vigente$', 'procedimiento');

CALL prueba.verifica('X623', 'Extensión', 'Billetera', 'Repetir el pago de un QR dinámico con la misma llave devuelve el mismo pago',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.crear_qr('C002', 30, NULL, 'cliente:C002', NULL, @q, @n)",
             "CALL billetera.pagar_qr('C001', @q, NULL, 'k623', REPEAT('a', 64), 'cliente:C001', NULL, @o1, @d1, @r1)",
             "CALL billetera.pagar_qr('C001', @q, NULL, 'k623', REPEAT('a', 64), 'cliente:C001', NULL, @o2, @d2, @r2)"),
  "SELECT @r1 = 0 AND @r2 = 1 AND @o1 = @o2 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @bd_s1 - 30",
  'repetido, un solo débito', "SELECT CONCAT_WS(' ', @r1, @r2, @o1 = @o2)", 'procedimiento');

CALL prueba.rechaza('X624', 'Extensión', 'Billetera', 'Nadie paga su propio QR',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_qr('C001', NULL, NULL, 'cliente:C001', NULL, @q, @n)",
             "CALL billetera.pagar_qr('C001', @q, 10, 'k624', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-QR-PROPIO: no se puede pagar un código QR propio$', 'procedimiento');

CALL prueba.rechaza('X625', 'Extensión', 'Billetera', 'Un QR estático exige el monto',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_qr('C002', NULL, NULL, 'cliente:C002', NULL, @q, @n)",
             "CALL billetera.pagar_qr('C001', @q, NULL, 'k625', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-BILLETERA-MONTO: el monto debe ser mayor que cero$', 'procedimiento');

CALL prueba.rechaza('X626', 'Extensión', 'Billetera', 'Un QR dinámico no acepta otro monto',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_qr('C002', 30, NULL, 'cliente:C002', NULL, @q, @n)",
             "CALL billetera.pagar_qr('C001', @q, 20, 'k626', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  '^BNA-QR-MONTO: el monto no es el del código QR$', 'procedimiento');

CALL prueba.verifica('X627', 'Extensión', 'Billetera', 'Un comercio afiliado cobra en su cuenta con su QR estático',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.registrar_comercio('20100000001', 'Bodega Ficticia', 'CTA-PEN-2', 'operador.bd', NULL, @m, @q)",
             "CALL billetera.pagar_qr('C001', @q, 12.50, 'k627', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)"),
  "SELECT (SELECT id_qr = BIN_TO_UUID(@q) AND estado = 'ACTIVO' FROM billetera.v_comercio_api WHERE id_comercio = BIN_TO_UUID(@m)) AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @bd_s2 + 12.50 AND (SELECT id_comercio = BIN_TO_UUID(@m) AND cod_cliente_destino IS NULL AND nombre_destino = 'Bodega Ficticia' FROM billetera.v_operacion_api WHERE id_operacion = BIN_TO_UUID(@o)) AND (SELECT COUNT(*) FROM billetera.v_notificacion_api WHERE id_operacion = BIN_TO_UUID(@o)) = 1",
  '+12.50 al comercio, un aviso', "SELECT CONCAT_WS(' ', (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') - @bd_s2, (SELECT nombre_destino FROM billetera.v_operacion_api WHERE id_operacion = BIN_TO_UUID(@o)))", 'procedimiento');

CALL prueba.rechaza('X628', 'Extensión', 'Billetera', 'Un RUC se afilia una sola vez',
  JSON_ARRAY("CALL billetera.registrar_comercio('20100000001', 'Bodega Ficticia', 'CTA-PEN-2', 'operador.bd', NULL, @m, @q)",
             "CALL billetera.registrar_comercio('20100000001', 'Otra', 'CTA-PEN-2', 'operador.bd', NULL, @m, @q)"),
  '^BNA-COMERCIO-DUPLICADO: el RUC ya está afiliado$', 'procedimiento');

CALL prueba.verifica('X629', 'Extensión', 'Billetera', 'Una solicitud de cobro aceptada paga a quien la pidió',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.crear_solicitud('C002', '959000001', 40, 'Entradas', 'cliente:C002', NULL, @s)",
             "CALL billetera.responder_solicitud('C001', @s, 'ACEPTAR', 'k629', REPEAT('a', 64), 'cliente:C001', NULL, @e, @o, @d, @r)"),
  "SELECT @e = 'PAGADA' AND @r = 0 AND (SELECT estado FROM billetera.v_solicitud_api WHERE id_solicitud = BIN_TO_UUID(@s)) = 'PAGADA' AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @bd_s1 - 40 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2') = @bd_s2 + 40 AND (SELECT tipo = 'SOLICITUD' AND referencia = 'Entradas' AND cod_cliente_destino = 'C002' FROM billetera.v_operacion_api WHERE id_operacion = BIN_TO_UUID(@o)) AND (SELECT COUNT(*) FROM billetera.v_notificacion_api WHERE id_solicitud = BIN_TO_UUID(@s)) = 3",
  'PAGADA, −40 y +40, tres avisos', "SELECT CONCAT_WS(' ', @e, @r)", 'procedimiento');

CALL prueba.verifica('X630', 'Extensión', 'Billetera', 'Aceptar otra vez con la misma llave devuelve el mismo pago',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.crear_solicitud('C002', '959000001', 40, NULL, 'cliente:C002', NULL, @s)",
             "CALL billetera.responder_solicitud('C001', @s, 'ACEPTAR', 'k630', REPEAT('a', 64), 'cliente:C001', NULL, @e1, @o1, @d1, @r1)",
             "CALL billetera.responder_solicitud('C001', @s, 'ACEPTAR', 'k630', REPEAT('a', 64), 'cliente:C001', NULL, @e2, @o2, @d2, @r2)"),
  "SELECT @r1 = 0 AND @r2 = 1 AND @e2 = 'PAGADA' AND @o1 = @o2 AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @bd_s1 - 40",
  'repetida, un solo débito', "SELECT CONCAT_WS(' ', @r1, @r2, @e2)", 'procedimiento');

CALL prueba.rechaza('X631', 'Extensión', 'Billetera', 'Solo el pagador acepta una solicitud',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_solicitud('C002', '959000001', 40, NULL, 'cliente:C002', NULL, @s)",
             "CALL billetera.responder_solicitud('C002', @s, 'ACEPTAR', 'k631', REPEAT('a', 64), 'cliente:C002', NULL, @e, @o, @d, @r)"),
  '^BNA-SOLICITUD-PERMISO: el cliente no puede responder esta solicitud$', 'procedimiento');

CALL prueba.rechaza('X632', 'Extensión', 'Billetera', 'Una solicitud rechazada ya no se acepta',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.crear_solicitud('C002', '959000001', 40, NULL, 'cliente:C002', NULL, @s)",
             "CALL billetera.responder_solicitud('C001', @s, 'RECHAZAR', NULL, NULL, 'cliente:C001', NULL, @e, @o, @d, @r)",
             "CALL billetera.responder_solicitud('C001', @s, 'ACEPTAR', 'k632', REPEAT('a', 64), 'cliente:C001', NULL, @e, @o, @d, @r)"),
  '^BNA-SOLICITUD-NO-PENDIENTE: la solicitud ya no está pendiente$', 'procedimiento');

CALL prueba.verifica('X633', 'Extensión', 'Billetera', 'Quien pidió el cobro lo cancela sin mover dinero',
  JSON_ARRAY("CALL prueba.bd_afiliar()", "CALL prueba.bd_saldos()",
             "CALL billetera.crear_solicitud('C002', '959000001', 40, NULL, 'cliente:C002', NULL, @s)",
             "CALL billetera.responder_solicitud('C002', @s, 'CANCELAR', NULL, NULL, 'cliente:C002', NULL, @e, @o, @d, @r)"),
  "SELECT @e = 'CANCELADA' AND @o IS NULL AND (SELECT estado FROM billetera.v_solicitud_api WHERE id_solicitud = BIN_TO_UUID(@s)) = 'CANCELADA' AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-1') = @bd_s1",
  'CANCELADA sin operación', "SELECT CONCAT_WS(' ', @e, coalesce(@o, '-'))", 'procedimiento');

CALL prueba.verifica('X634', 'Extensión', 'Billetera', 'Buscar un contacto devuelve solo el nombre corto de quien tiene billetera',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.buscar_contacto('C001', '959000002', @n1)",
             "CALL billetera.buscar_contacto('C001', '959000001', @n2)",
             "CALL billetera.buscar_contacto('C001', '959000003', @n3)"),
  "SELECT @n1 = 'Ana D.' AND @n2 IS NULL AND @n3 IS NULL",
  'Ana D., nada, nada', "SELECT CONCAT_WS(' ', @n1, coalesce(@n2, '-'), coalesce(@n3, '-'))", 'procedimiento');

CALL prueba.verifica('X635', 'Extensión', 'Billetera', 'Marcar los avisos como leídos solo toca los del cliente',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.transferir('C001', '959000002', 10, NULL, 'k635', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)",
             "CALL billetera.marcar_notificaciones_leidas('C002', @f)"),
  "SELECT @f = 1 AND (SELECT COUNT(*) FROM billetera.v_notificacion_api WHERE cod_cliente = 'C002' AND leida = 0) = 0 AND (SELECT COUNT(*) FROM billetera.v_notificacion_api WHERE cod_cliente = 'C001' AND leida = 0) = 1",
  'una leída de C002, C001 sin tocar', "SELECT @f", 'procedimiento');

CALL prueba.verifica('X636', 'Extensión', 'Billetera', 'Las vistas de la billetera no exponen el hash, la sal, el PIN ni el celular',
  JSON_ARRAY("DO 0"),
  "SELECT (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'billetera' AND table_name LIKE 'v\\_%\\_api') > 0 AND (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'billetera' AND table_name LIKE 'v\\_%\\_api' AND column_name IN ('hash_pin', 'sal', 'pin', 'celular', 'numero_documento')) = 0",
  'sin columnas sensibles', "SELECT GROUP_CONCAT(DISTINCT column_name) FROM information_schema.columns WHERE table_schema = 'billetera'", 'declarativo');

CALL prueba.rechaza('X637', 'Extensión', 'bna_api', 'bna_api no puede: leer billetera.afiliacion (el hash del PIN)',
  JSON_ARRAY("SELECT COUNT(*) INTO @n FROM billetera.afiliacion"),
  'denied', 'privilegio');

CALL prueba.rechaza('X638', 'Extensión', 'bna_api', 'bna_api no puede: INSERT en billetera.operacion',
  JSON_ARRAY("INSERT INTO billetera.operacion (id_operacion) VALUES (UUID_TO_BIN(UUID()))"),
  'denied', 'privilegio');

CALL prueba.verifica('X639', 'Extensión', 'Billetera', 'Ni la glosa, ni los avisos, ni la bitácora guardan el celular',
  JSON_ARRAY("CALL prueba.bd_afiliar()",
             "CALL billetera.transferir('C001', '959000002', 10, NULL, 'k639', REPEAT('a', 64), 'cliente:C001', NULL, @o, @d, @r)",
             "CALL billetera.crear_solicitud('C002', '959000001', 5, NULL, 'cliente:C002', NULL, @s)"),
  "SELECT (SELECT COUNT(*) FROM cuentas.v_movimiento_api WHERE id_canal = 'BD') = 2 AND (SELECT COUNT(*) FROM cuentas.v_movimiento_api WHERE glosa LIKE '%9590000%') = 0 AND (SELECT COUNT(*) FROM billetera.v_notificacion_api WHERE mensaje LIKE '%9590000%') = 0 AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE detalle LIKE '%9590000%' AND modulo IN ('BILLETERA', 'CUENTAS')) = 0",
  'sin celulares', "SELECT GROUP_CONCAT(glosa) FROM cuentas.v_movimiento_api WHERE id_canal = 'BD'", 'procedimiento');

-- Bloqueo del login del personal (v1.12): 5 fallos seguidos (core.fn_intentos_login)
-- bloquean el login 15 minutos (core.fn_minutos_bloqueo_login). Los usuarios de
-- servicio no se bloquean. @usr_bl crea a la persona; @f5 suma cinco fallos.
SET @usr_bl = "CALL core.crear_usuario(UUID_TO_BIN('70000000-0000-4000-8000-000000000001'), 'ana.x700', 'Ana', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas')";
SET @fallo_bl = "CALL core.registrar_login_fallido(UUID_TO_BIN('70000000-0000-4000-8000-000000000001'), NULL, @b)";
SET @bl_hasta = "core.fn_login_bloqueado_hasta(UUID_TO_BIN('70000000-0000-4000-8000-000000000001'))";

CALL prueba.verifica('X700', 'Extensión', 'Login', 'Cuatro fallos seguidos no bloquean el login',
  JSON_ARRAY(@usr_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl),
  CONCAT("@b IS NULL AND ", @bl_hasta, " IS NULL AND core.fn_intentos_login() = 5"),
  'sin bloqueo; intentos 5', CONCAT("CONCAT('bloqueado hasta ', coalesce(", @bl_hasta, ", 'nunca'))"), 'procedimiento');

CALL prueba.verifica('X701', 'Extensión', 'Login', 'El quinto fallo bloquea el login 15 minutos y lo audita',
  JSON_ARRAY(@usr_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl),
  CONCAT("@b BETWEEN UTC_TIMESTAMP(6) + INTERVAL 14 MINUTE AND UTC_TIMESTAMP(6) + INTERVAL 15 MINUTE AND ", @bl_hasta, " = @b",
         " AND core.fn_minutos_bloqueo_login() = 15",
         " AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '70000000-0000-4000-8000-000000000001' AND accion = 'LOGIN_FALLIDO' AND actor = 'ana.x700') = 5",
         " AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '70000000-0000-4000-8000-000000000001' AND accion = 'BLOQUEAR_LOGIN') = 1"),
  'bloqueado 15 minutos; 5 LOGIN_FALLIDO y 1 BLOQUEAR_LOGIN',
  "CONCAT('hasta ', coalesce(@b, 'nunca'), ', fallidos ', (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '70000000-0000-4000-8000-000000000001' AND accion = 'LOGIN_FALLIDO'))", 'procedimiento');

CALL prueba.rechaza('X702', 'Extensión', 'Login', 'Con el login bloqueado no se registra un login exitoso',
  JSON_ARRAY(@usr_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl,
             "CALL core.registrar_login(UUID_TO_BIN('70000000-0000-4000-8000-000000000001'), NULL)"),
  '^BNA-LOGIN-BLOQUEADO:', 'procedimiento');

CALL prueba.verifica('X703', 'Extensión', 'Login', 'Un login exitoso reinicia la cuenta de fallos',
  JSON_ARRAY(@usr_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl,
             "CALL core.registrar_login(UUID_TO_BIN('70000000-0000-4000-8000-000000000001'), NULL)",
             @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl),
  CONCAT("@b IS NULL AND ", @bl_hasta, " IS NULL"), 'sin bloqueo tras 4 + login + 4',
  CONCAT("CONCAT('bloqueado hasta ', coalesce(", @bl_hasta, ", 'nunca'))"), 'procedimiento');

CALL prueba.verifica('X704', 'Extensión', 'Login', 'Un usuario de servicio no se bloquea, pero sus fallos se auditan',
  JSON_ARRAY("CALL core.crear_usuario_servicio(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), 'svc-x704', 'S', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas')",
             "CALL core.registrar_login_fallido(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), NULL, @b1)",
             "CALL core.registrar_login_fallido(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), NULL, @b2)",
             "CALL core.registrar_login_fallido(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), NULL, @b3)",
             "CALL core.registrar_login_fallido(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), NULL, @b4)",
             "CALL core.registrar_login_fallido(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), NULL, @b5)",
             "CALL core.registrar_login_fallido(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), NULL, @b6)",
             "CALL core.registrar_login(UUID_TO_BIN('70000000-0000-4000-8000-000000000004'), NULL)"),
  "@b6 IS NULL AND core.fn_login_bloqueado_hasta(UUID_TO_BIN('70000000-0000-4000-8000-000000000004')) IS NULL AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '70000000-0000-4000-8000-000000000004' AND accion = 'LOGIN_FALLIDO') = 6",
  'sin bloqueo; 6 LOGIN_FALLIDO; login registrado',
  "CONCAT('fallidos ', (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '70000000-0000-4000-8000-000000000004' AND accion = 'LOGIN_FALLIDO'))", 'procedimiento');

CALL prueba.verifica('X705', 'Extensión', 'Login', 'El administrador desbloquea el login y queda auditado',
  JSON_ARRAY(@usr_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl,
             "CALL core.desbloquear_login(UUID_TO_BIN('70000000-0000-4000-8000-000000000001'), 'admin.x705')",
             "CALL core.registrar_login(UUID_TO_BIN('70000000-0000-4000-8000-000000000001'), NULL)",
             @fallo_bl),
  CONCAT(@bl_hasta, " IS NULL AND @b IS NULL AND EXISTS (SELECT 1 FROM core.v_evento_auditoria_api WHERE id_entidad = '70000000-0000-4000-8000-000000000001' AND accion = 'DESBLOQUEAR_LOGIN' AND actor = 'admin.x705')"),
  'desbloqueado, login registrado, la cuenta empieza de cero',
  CONCAT("CONCAT('bloqueado hasta ', coalesce(", @bl_hasta, ", 'nunca'))"), 'procedimiento');

CALL prueba.verifica('X706', 'Extensión', 'Login', 'Un fallo de un usuario que no existe no deja rastro (no se guarda lo que se escribió)',
  JSON_ARRAY("SET @n0 = (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'LOGIN_FALLIDO')",
             "CALL core.registrar_login_fallido(NULL, NULL, @b)"),
  "@b IS NULL AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'LOGIN_FALLIDO') = @n0",
  'sin error ni evento', "CONCAT('eventos nuevos ', (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'LOGIN_FALLIDO') - @n0)", 'procedimiento');

CALL prueba.verifica('X707', 'Extensión', 'Login', 'Los fallos durante el bloqueo no lo alargan',
  JSON_ARRAY(@usr_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl,
             "SET @hasta = @b", "DO SLEEP(0.01)", @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl, @fallo_bl),
  CONCAT(@bl_hasta, " = @hasta AND @b = @hasta"), 'el mismo fin de bloqueo',
  CONCAT("CONCAT(@hasta, ' / ', coalesce(", @bl_hasta, ", 'nunca'))"), 'procedimiento');

CALL prueba.rechaza('X708', 'Extensión', 'Login', 'No se desbloquea un usuario que no existe',
  JSON_ARRAY("CALL core.desbloquear_login(UUID_TO_BIN(UUID()), 'pruebas')"),
  '^BNA-USUARIO:', 'procedimiento');

CALL prueba.rechaza('X709', 'Extensión', 'bna_api', 'bna_api no lee core.bloqueo_login',
  JSON_ARRAY("SELECT COUNT(*) INTO @n FROM core.bloqueo_login"),
  'denied', 'privilegio');

-- ---------------------------------------------------------------------
-- Seguridad (v1.13): evaluación con desafío, sellos de la bitácora e incidentes.
-- Cada prueba abre su propia cuenta (SEG-1), sin consumo del día.
-- ---------------------------------------------------------------------
SET @seg_cta = "CALL cuentas.abrir_cuenta('SEG-1', '00219100000000007201', 'PEN', 'INDIVIDUAL', NULL, JSON_ARRAY('C001'), 'pruebas')";
SET @seg_op = "UUID_TO_BIN('72000000-0000-4000-8000-000000000001')";
SET @seg_d1 = "UUID_TO_BIN('72000000-0000-4000-8000-0000000000d1')";
SET @seg_ok = "REPEAT('a', 64)";
SET @seg_mal = "REPEAT('b', 64)";
-- @seg_eval(canal, monto, desafío, hmac) para la operación @seg_op, actor op.seg.
SET @seg_eval_atm = CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'ATM', 1300, ");
SET @seg_desafio = CONCAT("CALL core.crear_desafio(", @seg_d1, ", ", @seg_op, ", 'SEG-1', 'ATM', 1300, ", @seg_ok, ", 'op.seg', @vence)");
SET @seg_sin = CONCAT(@seg_eval_atm, "NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)");
SET @seg_bien = CONCAT(@seg_eval_atm, @seg_d1, ", ", @seg_ok, ", 'op.seg', @d, @m, @l, @a, @r)");
SET @seg_falla = CONCAT(@seg_eval_atm, @seg_d1, ", ", @seg_mal, ", 'op.seg', @d, @m, @l, @a, @r)");
SET @seg_eventos = "(SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '72000000-0000-4000-8000-000000000001' AND modulo = 'SEGURIDAD' AND accion = ";

CALL prueba.verifica('X720', 'Extensión', 'Seguridad', 'Bajo el 80 % del tope del canal la operación se autoriza y se audita',
  JSON_ARRAY(@seg_cta, CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'ATM', 1000, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)")),
  CONCAT("@d = 'AUTORIZADA' AND @m IS NULL AND @l = 1500 AND @a = 0 AND NOT @r AND ", @seg_eventos, "'EVALUAR_OPERACION' AND actor = 'op.seg') = 1"),
  'AUTORIZADA, tope 1500, consumido 0, un evento', "CONCAT_WS(' ', @d, @m, @l, @a, @r)", 'procedimiento');

CALL prueba.verifica('X721', 'Extensión', 'Seguridad', 'Sobre el tope del canal la operación se rechaza (TOPE)',
  JSON_ARRAY(@seg_cta, CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'ATM', 1500.01, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)")),
  "@d = 'RECHAZADA' AND @m = 'TOPE' AND @l = 1500", 'RECHAZADA TOPE', "CONCAT_WS(' ', @d, @m, @l, @a)", 'procedimiento');

CALL prueba.verifica('X722', 'Extensión', 'Seguridad', 'Sobre el 80 % pide un desafío y no guarda decisión',
  JSON_ARRAY(@seg_cta, @seg_sin, "SET @d1 = @d", @seg_sin),
  CONCAT("@d1 = 'DESAFIO_REQUERIDO' AND @d = 'DESAFIO_REQUERIDO' AND NOT @r AND core.fn_umbral_desafio() = 0.80 AND ",
         @seg_eventos, "'EVALUAR_OPERACION') = 0"),
  'DESAFIO_REQUERIDO dos veces, sin evento de decisión', "CONCAT_WS(' ', @d1, @d, @r)", 'procedimiento');

CALL prueba.verifica('X723', 'Extensión', 'Seguridad', 'Con el código correcto el desafío autoriza una vez',
  JSON_ARRAY(@seg_cta, @seg_sin, @seg_desafio, @seg_bien),
  CONCAT("@d = 'AUTORIZADA' AND NOT @r AND @vence BETWEEN UTC_TIMESTAMP(6) + INTERVAL 119 SECOND AND UTC_TIMESTAMP(6) + INTERVAL 120 SECOND",
         " AND core.fn_segundos_desafio() = 120 AND ", @seg_eventos, "'CREAR_DESAFIO') = 1 AND ",
         @seg_eventos, "'EVALUAR_OPERACION' AND JSON_EXTRACT(detalle, '$.con_desafio') = TRUE) = 1"),
  'AUTORIZADA; vence en 120 s; CREAR_DESAFIO y EVALUAR_OPERACION con desafío', "CONCAT_WS(' ', @d, @r, @vence)", 'procedimiento');

CALL prueba.verifica('X724', 'Extensión', 'Seguridad', 'Un código incorrecto no es un error: DESAFIO_RECHAZADO, y el correcto sigue sirviendo',
  JSON_ARRAY(@seg_cta, @seg_desafio, @seg_falla, "SET @d1 = @d", @seg_bien),
  CONCAT("@d1 = 'DESAFIO_RECHAZADO' AND @d = 'AUTORIZADA' AND ", @seg_eventos, "'RECHAZAR_DESAFIO') = 1"),
  'DESAFIO_RECHAZADO y luego AUTORIZADA', "CONCAT_WS(' ', @d1, @d)", 'procedimiento');

CALL prueba.verifica('X725', 'Extensión', 'Seguridad', 'Tres códigos incorrectos agotan el desafío',
  JSON_ARRAY(@seg_cta, @seg_desafio, @seg_falla, @seg_falla, @seg_falla, @seg_bien),
  "@d = 'DESAFIO_RECHAZADO' AND core.fn_intentos_desafio() = 3", 'DESAFIO_RECHAZADO con el código correcto', "@d", 'procedimiento');

CALL prueba.verifica('X726', 'Extensión', 'Seguridad', 'El desafío de otra operación no sirve ni gasta sus intentos',
  JSON_ARRAY(@seg_cta, @seg_desafio,
             CONCAT("CALL core.evaluar_operacion(UUID_TO_BIN('72000000-0000-4000-8000-000000000002'), 'SEG-1', 'ATM', 1300, ", @seg_d1, ", ", @seg_ok, ", 'op.seg', @d, @m, @l, @a, @r)"),
             "SET @d1 = @d",
             CONCAT("CALL core.evaluar_operacion(UUID_TO_BIN('72000000-0000-4000-8000-000000000002'), 'SEG-1', 'ATM', 1300, ", @seg_d1, ", ", @seg_ok, ", 'op.seg', @d, @m, @l, @a, @r)"),
             CONCAT("CALL core.evaluar_operacion(UUID_TO_BIN('72000000-0000-4000-8000-000000000002'), 'SEG-1', 'ATM', 1300, ", @seg_d1, ", ", @seg_ok, ", 'op.seg', @d, @m, @l, @a, @r)"),
             CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'ATM', 1300, ", @seg_d1, ", ", @seg_ok, ", 'otro.seg', @d, @m, @l, @a, @r)"),
             "SET @d2 = @d", @seg_bien),
  "@d1 = 'DESAFIO_RECHAZADO' AND @d2 = 'DESAFIO_RECHAZADO' AND @d = 'AUTORIZADA'",
  'otra operación y otro actor: DESAFIO_RECHAZADO; la suya: AUTORIZADA', "CONCAT_WS(' ', @d1, @d2, @d)", 'procedimiento');

CALL prueba.verifica('X727', 'Extensión', 'Seguridad', 'Repetir la operación devuelve la misma decisión sin otro evento',
  JSON_ARRAY(@seg_cta, @seg_desafio, @seg_bien, @seg_sin),
  CONCAT("@d = 'AUTORIZADA' AND @r AND ", @seg_eventos, "'EVALUAR_OPERACION') = 1"),
  'AUTORIZADA repetida, un evento', "CONCAT_WS(' ', @d, @r)", 'procedimiento');

CALL prueba.rechaza('X728', 'Extensión', 'Seguridad', 'Repetir la operación con otro monto falla',
  JSON_ARRAY(@seg_cta, CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'ATM', 10, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)"),
             CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'ATM', 11, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)")),
  '^BNA-IDEMPOTENCIA:', 'procedimiento');

CALL prueba.verifica('X729', 'Extensión', 'Seguridad', 'La evaluación usa el consumo real del día de la cuenta en el canal',
  JSON_ARRAY(@seg_cta,
             "CALL cuentas.registrar_movimiento('SEG-1', 'DEPOSITO', 10000, 'Depósito X729', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @u, @x)",
             "CALL cuentas.registrar_movimiento('SEG-1', 'RETIRO', 9000, 'Retiro X729', 'HB', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @u, @x)",
             CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'HB', 600, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)"),
             "SET @d1 = @d",
             "CALL core.evaluar_operacion(UUID_TO_BIN('72000000-0000-4000-8000-000000000003'), 'SEG-1', 'HB', 1000.01, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)"),
  "@d1 = 'DESAFIO_REQUERIDO' AND @d = 'RECHAZADA' AND @m = 'TOPE' AND @a = 9000 AND @l = 10000",
  'consumido 9000 de 10000: 600 pide desafío, 1000.01 se rechaza', "CONCAT_WS(' ', @d1, @d, @m, @a, @l)", 'procedimiento');

CALL prueba.verifica('X730', 'Extensión', 'Seguridad', 'Un canal sin tope en la moneda se rechaza (CANAL); ventanilla no tiene tope',
  JSON_ARRAY(@seg_cta,
             CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'AGE', 10, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)"),
             "SET @d1 = CONCAT_WS(' ', @d, @m)",
             "CALL core.evaluar_operacion(UUID_TO_BIN('72000000-0000-4000-8000-000000000003'), 'SEG-1', 'VEN', 999999, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)"),
  "@d1 = 'RECHAZADA CANAL' AND @d = 'AUTORIZADA' AND @l IS NULL",
  'AGE: RECHAZADA CANAL; VEN: AUTORIZADA sin tope', "CONCAT_WS(' / ', @d1, CONCAT_WS(' ', @d, coalesce(@l, 'sin tope')))", 'procedimiento');

CALL prueba.rechaza('X731', 'Extensión', 'Seguridad', 'No se evalúa una operación de una cuenta que no existe',
  JSON_ARRAY(CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'NO-EXISTE', 'ATM', 10, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)")),
  '^BNA-CUENTA:', 'procedimiento');

CALL prueba.rechaza('X732', 'Extensión', 'Seguridad', 'El desafío exige un HMAC de 64 hexadecimales en minúscula',
  JSON_ARRAY(@seg_cta, CONCAT("CALL core.crear_desafio(", @seg_d1, ", ", @seg_op, ", 'SEG-1', 'ATM', 1300, REPEAT('A', 64), 'op.seg', @vence)")),
  '^BNA-DESAFIO:', 'procedimiento');

CALL prueba.rechaza('X733', 'Extensión', 'Seguridad', 'No se crea un desafío para una operación que ya tiene decisión',
  JSON_ARRAY(@seg_cta, CONCAT("CALL core.evaluar_operacion(", @seg_op, ", 'SEG-1', 'ATM', 10, NULL, NULL, 'op.seg', @d, @m, @l, @a, @r)"),
             @seg_desafio),
  '^BNA-DESAFIO:', 'procedimiento');

CALL prueba.rechaza('X734', 'Extensión', 'bna_api', 'bna_api no lee core.desafio_operacion (el HMAC del código)',
  JSON_ARRAY("SELECT COUNT(*) INTO @n FROM core.desafio_operacion"), 'denied', 'privilegio');

CALL prueba.rechaza('X735', 'Extensión', 'bna_api', 'bna_api no escribe core.evaluacion_operacion',
  JSON_ARRAY(CONCAT("INSERT INTO core.evaluacion_operacion (uuid_operacion, num_cuenta, id_canal, monto, actor, decision, acumulado) VALUES (", @seg_op, ", 'CTA-PEN-1', 'ATM', 1, 'x', 'AUTORIZADA', 0)")),
  'denied', 'privilegio');

-- Sellos de la bitácora. Ninguna otra prueba deja sellos confirmados; cada una abre un
-- incidente para que haya al menos un evento que sellar.
SET @sel_prep = JSON_ARRAY(
  "CALL core.abrir_incidente(UUID_TO_BIN('72000000-0000-4000-8000-0000000000e0'), 'P4', 'Evento para sellar', 'op.seg')",
  "SET @sd = coalesce((SELECT max(hasta_evento) FROM core.v_sello_auditoria_api), 0)",
  "SET @sh = (SELECT max(id_evento) FROM core.v_evento_auditoria_api)",
  "SET @sn = (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_evento > @sd AND id_evento <= @sh)");

CALL prueba.verifica('X740', 'Extensión', 'Seguridad', 'El sello cubre el tramo que sigue al último sello',
  JSON_MERGE_PRESERVE(@sel_prep, JSON_ARRAY("CALL core.sellar_auditoria(@sh, @sn, REPEAT('c', 64), 'svc-seguridad', @s, @desde)")),
  "@desde = @sd AND EXISTS (SELECT 1 FROM core.v_sello_auditoria_api WHERE id_sello = @s AND desde_evento = @sd AND hasta_evento = @sh AND eventos = @sn AND actor = 'svc-seguridad')",
  'un sello de (último, máximo]', "CONCAT_WS(' ', @s, @desde, @sh, @sn)", 'procedimiento');

CALL prueba.verifica('X741', 'Extensión', 'Seguridad', 'El sello siguiente empieza donde acabó el anterior',
  JSON_MERGE_PRESERVE(@sel_prep, JSON_ARRAY(
    "CALL core.sellar_auditoria(@sh, @sn, REPEAT('c', 64), 'svc-seguridad', @s1, @desde1)",
    "CALL core.abrir_incidente(UUID_TO_BIN('72000000-0000-4000-8000-0000000000e1'), 'P3', 'Evento para el sello X741', 'op.seg')",
    "SET @sh2 = (SELECT max(id_evento) FROM core.v_evento_auditoria_api)",
    "CALL core.sellar_auditoria(@sh2, 1, REPEAT('d', 64), 'svc-seguridad', @s2, @desde2)")),
  "@desde2 = @sh AND @s2 > @s1", 'el segundo tramo empieza en el fin del primero', "CONCAT_WS(' ', @sh, @desde2)", 'procedimiento');

CALL prueba.rechaza('X742', 'Extensión', 'Seguridad', 'El sello rechaza un tramo con otra cantidad de eventos',
  JSON_MERGE_PRESERVE(@sel_prep, JSON_ARRAY("CALL core.sellar_auditoria(@sh, @sn + 1, REPEAT('c', 64), 'svc-seguridad', @s, @desde)")),
  '^BNA-SELLO: el tramo no tiene', 'procedimiento');

CALL prueba.rechaza('X743', 'Extensión', 'Seguridad', 'No se vuelve a sellar un tramo ya sellado',
  JSON_MERGE_PRESERVE(@sel_prep, JSON_ARRAY(
    "CALL core.sellar_auditoria(@sh, @sn, REPEAT('c', 64), 'svc-seguridad', @s, @desde)",
    "CALL core.sellar_auditoria(@sh, @sn, REPEAT('c', 64), 'svc-seguridad', @s, @desde)")),
  '^BNA-SELLO: el tramo no sigue', 'procedimiento');

CALL prueba.rechaza('X744', 'Extensión', 'Seguridad', 'El sello exige un HMAC de 64 hexadecimales',
  JSON_MERGE_PRESERVE(@sel_prep, JSON_ARRAY("CALL core.sellar_auditoria(@sh, @sn, 'corto', 'svc-seguridad', @s, @desde)")),
  '^BNA-SELLO:', 'procedimiento');

CALL prueba.rechaza('X745', 'Extensión', 'bna_api', 'bna_api no escribe core.sello_auditoria',
  JSON_ARRAY("INSERT INTO core.sello_auditoria (desde_evento, hasta_evento, eventos, hmac, actor) VALUES (0, 1, 1, REPEAT('c', 64), 'x')"),
  'denied', 'privilegio');

-- Incidentes.
SET @inc = "UUID_TO_BIN('72000000-0000-4000-8000-0000000000f1')";
SET @inc_abrir = CONCAT("CALL core.abrir_incidente(", @inc, ", 'P2', 'Intentos de acceso repetidos', 'op.seg')");

CALL prueba.verifica('X750', 'Extensión', 'Seguridad', 'Un incidente se abre ABIERTO y queda auditado',
  JSON_ARRAY(@inc_abrir),
  "(SELECT CONCAT(estado, ' ', prioridad, ' ', abierto_por) FROM core.v_incidente_api WHERE id_incidente = '72000000-0000-4000-8000-0000000000f1') = 'ABIERTO P2 op.seg' AND EXISTS (SELECT 1 FROM core.v_evento_auditoria_api WHERE id_entidad = '72000000-0000-4000-8000-0000000000f1' AND accion = 'ABRIR_INCIDENTE')",
  'ABIERTO P2 op.seg, con evento', "(SELECT CONCAT(estado, ' ', prioridad, ' ', abierto_por) FROM core.v_incidente_api WHERE id_incidente = '72000000-0000-4000-8000-0000000000f1')", 'procedimiento');

CALL prueba.verifica('X751', 'Extensión', 'Seguridad', 'El ciclo completo llega a CERRADO y conserva la resolución',
  JSON_ARRAY(@inc_abrir,
             CONCAT("CALL core.avanzar_incidente(", @inc, ", 'EN_PROGRESO', NULL, 'op.seg')"),
             CONCAT("CALL core.avanzar_incidente(", @inc, ", 'RESUELTO', 'Se bloqueó el origen', 'op.seg')"),
             CONCAT("CALL core.avanzar_incidente(", @inc, ", 'CERRADO', NULL, 'admin.seg')")),
  "(SELECT CONCAT(estado, ' / ', resolucion) FROM core.v_incidente_api WHERE id_incidente = '72000000-0000-4000-8000-0000000000f1') = 'CERRADO / Se bloqueó el origen' AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE id_entidad = '72000000-0000-4000-8000-0000000000f1' AND accion IN ('INCIDENTE_EN_PROGRESO', 'INCIDENTE_RESUELTO', 'INCIDENTE_CERRADO')) = 3",
  'CERRADO / Se bloqueó el origen; 3 eventos de estado', "(SELECT CONCAT(estado, ' / ', coalesce(resolucion, '')) FROM core.v_incidente_api WHERE id_incidente = '72000000-0000-4000-8000-0000000000f1')", 'procedimiento');

CALL prueba.rechaza('X752', 'Extensión', 'Seguridad', 'Un incidente no salta de ABIERTO a RESUELTO',
  JSON_ARRAY(@inc_abrir, CONCAT("CALL core.avanzar_incidente(", @inc, ", 'RESUELTO', 'Resuelto sin pasar por EN_PROGRESO', 'op.seg')")),
  '^BNA-INCIDENTE-TRANSICION:', 'procedimiento');

CALL prueba.rechaza('X753', 'Extensión', 'Seguridad', 'Resolver un incidente exige la resolución',
  JSON_ARRAY(@inc_abrir, CONCAT("CALL core.avanzar_incidente(", @inc, ", 'EN_PROGRESO', NULL, 'op.seg')"),
             CONCAT("CALL core.avanzar_incidente(", @inc, ", 'RESUELTO', '  ', 'op.seg')")),
  '^BNA-INCIDENTE: resolverlo', 'procedimiento');

CALL prueba.rechaza('X754', 'Extensión', 'Seguridad', 'No se avanza un incidente que no existe',
  JSON_ARRAY(CONCAT("CALL core.avanzar_incidente(", @inc, ", 'EN_PROGRESO', NULL, 'op.seg')")),
  '^BNA-INCIDENTE: el incidente no existe', 'procedimiento');

CALL prueba.rechaza('X755', 'Extensión', 'Seguridad', 'La prioridad de un incidente es P1 a P4',
  JSON_ARRAY(CONCAT("CALL core.abrir_incidente(", @inc, ", 'P5', 'Prioridad inexistente', 'op.seg')")),
  '^BNA-INCIDENTE: la prioridad', 'procedimiento');

-- Al final: cambia la hora de la sesión. Un desafío vencido no autoriza aunque el código sea
-- el correcto, ni gasta la decisión.
CALL prueba.verifica('X736', 'Extensión', 'Seguridad', 'Un desafío vencido (más de 120 s) no autoriza',
  JSON_ARRAY(@seg_cta, @seg_desafio, "SET TIMESTAMP = UNIX_TIMESTAMP() + 121", @seg_bien,
             "SET TIMESTAMP = DEFAULT"),
  "@d = 'DESAFIO_RECHAZADO'", 'DESAFIO_RECHAZADO', "@d", 'procedimiento');
SET TIMESTAMP = DEFAULT;

-- ---------------------------------------------------------------------
-- Solicitud de crédito sin base propia (v1.14): el borrador del asesor, sus garantías y
-- fiadores, el paso a evaluación y el receptor de eventos de auditoría de los módulos.
-- ---------------------------------------------------------------------
SET @sol_id = "UUID_TO_BIN('80000000-0000-4000-8000-000000000001')";
SET @sol_pol = "JSON_OBJECT('version', 'SOL-DEMO-2026-01', 'tea', '0.2200', 'amortizacion', 'FRANCES', 'dias_por_periodo', 30)";
SET @sol_gar1 = "JSON_ARRAY(JSON_OBJECT('tipo', 'HIPOTECARIA', 'descripcion', 'Casa en Cayma', 'valor', 25000))";
SET @sol_crear = CONCAT("CALL creditos.guardar_borrador(", @sol_id, ", NULL, 'C001', 3000, 'PEN', 3, FALSE, 'Capital de trabajo', CURRENT_DATE, ",
                        @sol_pol, ", ", @sol_gar1, ", JSON_ARRAY('C002'), REPEAT('a', 64), 'asesor.sol', UUID_TO_BIN(UUID()), @rev, @cod, @rep)");
SET @sol_editar = CONCAT("CALL creditos.guardar_borrador(", @sol_id, ", 1, 'C001', 3000, 'PEN', 3, FALSE, 'Capital de trabajo y equipos', CURRENT_DATE, ",
                         @sol_pol, ", JSON_ARRAY(JSON_OBJECT('tipo', 'MOBILIARIA', 'descripcion', 'Camioneta 2024', 'valor', 18000), JSON_OBJECT('tipo', 'PRENDARIA', 'descripcion', 'Joyas de oro', 'valor', 2000.50)), ",
                         "JSON_ARRAY('C003'), REPEAT('b', 64), 'asesor.sol', UUID_TO_BIN(UUID()), @rev2, @cod2, @rep2)");
-- El borrador con otros datos: p_extra cambia un argumento a la vez.
SET @sol_otro = CONCAT("CALL creditos.guardar_borrador(", @sol_id, ", NULL, '%CLI%', 3000, 'PEN', 3, FALSE, '%DES%', CURRENT_DATE, ",
                       @sol_pol, ", %GAR%, %FIA%, REPEAT('c', 64), 'asesor.sol', UUID_TO_BIN(UUID()), @rev, @cod, @rep)");
SET @sol_base = REPLACE(REPLACE(REPLACE(@sol_otro, '%CLI%', 'C001'), '%DES%', 'Capital de trabajo'), '%GAR%', 'JSON_ARRAY()');
SET @sol_enviar = CONCAT("CALL creditos.registrar_solicitud(", @sol_id, ", 1, 'C001', %MONTO%, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('e', 64), 'svc-evaluacion', UUID_TO_BIN(UUID()), @ronda, @eval, @rep3)");

CALL prueba.verifica('X800', 'Extensión', 'Solicitud', 'Un borrador nuevo queda REGISTRADO con su revisión, código, garantías, fiadores, historial y evento',
  JSON_ARRAY(@sol_crear),
  "@rev = 1 AND NOT @rep AND @cod REGEXP '^SOL-[0-9]{4}-80000000$' AND (SELECT CONCAT(estado_solicitud, ' ', codigo, ' ', revision, ' ', destino) FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = CONCAT('REGISTRADA ', @cod, ' 1 Capital de trabajo') AND (SELECT COUNT(*) FROM creditos.v_garantia_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001') AND tipo_garantia = 'HIPOTECARIA' AND moneda = 'PEN' AND estado_garantia = 'REGISTRADA') = 1 AND (SELECT GROUP_CONCAT(cod_cliente) FROM creditos.v_fiador_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 'C002' AND (SELECT COUNT(*) FROM creditos.v_historial_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001') AND estado_nuevo = 'REGISTRADA' AND actor = 'asesor.sol') = 1 AND EXISTS (SELECT 1 FROM core.v_evento_auditoria_api WHERE id_entidad = '80000000-0000-4000-8000-000000000001' AND accion = 'CREAR_BORRADOR')",
  'REGISTRADA, revisión 1, SOL-AAMM-80000000, 1 garantía, fiador C002, historial y evento',
  "CONCAT_WS(' ', @rev, @cod, @rep, (SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')))", 'procedimiento');

CALL prueba.verifica('X801', 'Extensión', 'Solicitud', 'Repetir la creación con el mismo contenido devuelve el mismo borrador sin duplicar nada',
  JSON_ARRAY(@sol_crear, "SET @c1 = @cod", @sol_crear),
  "@rep AND @rev = 1 AND @cod = @c1 AND (SELECT COUNT(*) FROM creditos.v_garantia_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 1 AND (SELECT COUNT(*) FROM creditos.v_historial_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 1",
  'repetido, revisión 1, una garantía, un historial', "CONCAT_WS(' ', @rep, @rev)", 'procedimiento');

CALL prueba.rechaza('X802', 'Extensión', 'Solicitud', 'Crear otra vez el mismo id con otro contenido se rechaza',
  JSON_ARRAY(@sol_crear, REPLACE(@sol_base, '%FIA%', 'JSON_ARRAY()')), '^BNA-IDEMPOTENCIA:', 'procedimiento');

CALL prueba.verifica('X803', 'Extensión', 'Solicitud', 'Editar con la revisión vigente reemplaza condiciones, garantías y fiadores y sube la revisión',
  JSON_ARRAY(@sol_crear, @sol_editar),
  "@rev2 = 2 AND NOT @rep2 AND @cod2 = @cod AND (SELECT CONCAT(revision, ' ', destino) FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = '2 Capital de trabajo y equipos' AND (SELECT GROUP_CONCAT(tipo_garantia ORDER BY tipo_garantia) FROM creditos.v_garantia_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 'MOBILIARIA,PRENDARIA' AND (SELECT GROUP_CONCAT(cod_cliente) FROM creditos.v_fiador_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 'C003' AND (SELECT COUNT(*) FROM creditos.v_historial_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 2 AND EXISTS (SELECT 1 FROM core.v_evento_auditoria_api WHERE id_entidad = '80000000-0000-4000-8000-000000000001' AND accion = 'EDITAR_BORRADOR')",
  'revisión 2; MOBILIARIA,PRENDARIA; fiador C003; dos historiales; evento EDITAR_BORRADOR',
  "CONCAT_WS(' ', @rev2, (SELECT GROUP_CONCAT(tipo_garantia) FROM creditos.v_garantia_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')))", 'procedimiento');

CALL prueba.rechaza('X804', 'Extensión', 'Solicitud', 'Editar con una revisión vieja y otro contenido se rechaza (otra sesión la cambió)',
  JSON_ARRAY(@sol_crear, @sol_editar, REPLACE(@sol_editar, "REPEAT('b', 64)", "REPEAT('d', 64)")), '^BNA-REVISION:', 'procedimiento');

CALL prueba.verifica('X805', 'Extensión', 'Solicitud', 'Repetir la última edición (misma revisión de partida y mismo contenido) devuelve la revisión ya guardada',
  JSON_ARRAY(@sol_crear, @sol_editar, @sol_editar),
  "@rep2 AND @rev2 = 2 AND (SELECT COUNT(*) FROM creditos.v_historial_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 2",
  'repetido, revisión 2, dos historiales', "CONCAT_WS(' ', @rep2, @rev2)", 'procedimiento');

CALL prueba.rechaza('X806', 'Extensión', 'Solicitud', 'El cliente de un borrador no se cambia',
  JSON_ARRAY(@sol_crear, REPLACE(@sol_editar, "1, 'C001'", "1, 'C002'")), '^BNA-SOLICITUD: el cliente', 'procedimiento');

CALL prueba.rechaza('X807', 'Extensión', 'Solicitud', 'Un cliente que no puede operar no registra un borrador',
  JSON_ARRAY(REPLACE(REPLACE(@sol_base, '%FIA%', 'JSON_ARRAY()'), "'C001'", "'C004'")), '^BNA-CLIENTE:', 'procedimiento');

CALL prueba.rechaza('X808', 'Extensión', 'Solicitud', 'El solicitante no es su propio fiador',
  JSON_ARRAY(REPLACE(@sol_base, '%FIA%', "JSON_ARRAY('C001')")), '^BNA-FIADOR:', 'procedimiento');

CALL prueba.rechaza('X809', 'Extensión', 'Solicitud', 'Un fiador no se repite en la misma solicitud',
  JSON_ARRAY(REPLACE(@sol_base, '%FIA%', "JSON_ARRAY('C002', 'C002')")), '^BNA-FIADOR:', 'procedimiento');

CALL prueba.rechaza('X810', 'Extensión', 'Solicitud', 'Un fiador que no existe o no puede operar se rechaza',
  JSON_ARRAY(REPLACE(@sol_base, '%FIA%', "JSON_ARRAY('C004')")), '^BNA-FIADOR:', 'procedimiento');

CALL prueba.rechaza('X811', 'Extensión', 'Solicitud', 'Una garantía de un tipo fuera del catálogo se rechaza',
  JSON_ARRAY(REPLACE(REPLACE(REPLACE(REPLACE(@sol_otro, '%CLI%', 'C001'), '%DES%', 'Capital de trabajo'), '%FIA%', 'JSON_ARRAY()'),
             '%GAR%', "JSON_ARRAY(JSON_OBJECT('tipo', 'PERSONAL', 'descripcion', 'Aval personal', 'valor', 100))")),
  '^BNA-GARANTIA:', 'procedimiento');

CALL prueba.rechaza('X812', 'Extensión', 'Solicitud', 'Una garantía sin valor positivo se rechaza',
  JSON_ARRAY(REPLACE(REPLACE(REPLACE(REPLACE(@sol_otro, '%CLI%', 'C001'), '%DES%', 'Capital de trabajo'), '%FIA%', 'JSON_ARRAY()'),
             '%GAR%', "JSON_ARRAY(JSON_OBJECT('tipo', 'HIPOTECARIA', 'descripcion', 'Casa en Cayma', 'valor', 0))")),
  '^BNA-GARANTIA:', 'procedimiento');

CALL prueba.rechaza('X813', 'Extensión', 'Solicitud', 'Más de diez garantías se rechazan',
  JSON_ARRAY(CONCAT("SET @g = JSON_ARRAY(", REPEAT("JSON_OBJECT('tipo', 'PRENDARIA', 'descripcion', 'Prenda de prueba', 'valor', 10), ", 10),
                    "JSON_OBJECT('tipo', 'PRENDARIA', 'descripcion', 'Prenda de prueba', 'valor', 10))"),
             REPLACE(REPLACE(REPLACE(REPLACE(@sol_otro, '%CLI%', 'C001'), '%DES%', 'Capital de trabajo'), '%FIA%', 'JSON_ARRAY()'), '%GAR%', '@g')),
  '^BNA-GARANTIA:', 'procedimiento');

CALL prueba.rechaza('X814', 'Extensión', 'Solicitud', 'El destino del crédito tiene entre 5 y 120 caracteres',
  JSON_ARRAY(REPLACE(REPLACE(REPLACE(REPLACE(@sol_otro, '%CLI%', 'C001'), '%DES%', 'Uso'), '%FIA%', 'JSON_ARRAY()'), '%GAR%', 'JSON_ARRAY()')),
  '^BNA-SOLICITUD: el destino', 'procedimiento');

CALL prueba.verifica('X815', 'Extensión', 'Solicitud', 'El expediente de un borrador lo pasa a EN_EVALUACION en la ronda 1 con su calendario PRELIMINAR',
  JSON_ARRAY(@sol_crear, "CALL prueba.cr_calendario(3000, 3, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)", REPLACE(@sol_enviar, '%MONTO%', '3000')),
  "@ronda = 1 AND NOT @rep3 AND (SELECT CONCAT(estado_solicitud, ' ', ronda, ' ', tipo_calendario, ' ', numero_cuotas, ' ', codigo) FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = CONCAT('EN_EVALUACION 1 PRELIMINAR 3 ', @cod) AND (SELECT GROUP_CONCAT(estado_nuevo ORDER BY id_historial) FROM creditos.v_historial_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = 'REGISTRADA,EN_EVALUACION' AND (SELECT CONCAT(version_solicitud, ' ', ronda, ' ', id_evaluacion = @eval) FROM creditos.v_recepcion_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001')) = '1 1 1'",
  'EN_EVALUACION, ronda 1, PRELIMINAR de 3 cuotas; historial REGISTRADA,EN_EVALUACION; recepción con el id de la evaluación',
  "(SELECT CONCAT_WS(' ', estado_solicitud, ronda, tipo_calendario, numero_cuotas) FROM creditos.v_solicitud_api WHERE id_solicitud = UUID_TO_BIN('80000000-0000-4000-8000-000000000001'))", 'procedimiento');

CALL prueba.rechaza('X816', 'Extensión', 'Solicitud', 'Un expediente que no coincide con el borrador registrado se rechaza',
  JSON_ARRAY(@sol_crear, "CALL prueba.cr_calendario(3500, 3, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)",
             CONCAT("CALL creditos.registrar_solicitud(", @sol_id, ", 1, 'C001', 3500, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('e', 64), 'svc-evaluacion', UUID_TO_BIN(UUID()), @ronda, @eval, @rep3)")),
  '^BNA-SOLICITUD: el expediente no coincide', 'procedimiento');

CALL prueba.rechaza('X817', 'Extensión', 'Solicitud', 'El expediente de un borrador llega con su misma versión',
  JSON_ARRAY(@sol_crear, "CALL prueba.cr_calendario(3000, 3, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)",
             CONCAT("CALL creditos.registrar_solicitud(", @sol_id, ", 2, 'C001', 3000, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('e', 64), 'svc-evaluacion', UUID_TO_BIN(UUID()), @ronda, @eval, @rep3)")),
  '^BNA-SOLICITUD: la versión', 'procedimiento');

CALL prueba.rechaza('X818', 'Extensión', 'Solicitud', 'Un borrador enviado a evaluación ya no se edita',
  JSON_ARRAY(@sol_crear, "CALL prueba.cr_calendario(3000, 3, CURRENT_DATE + INTERVAL 30 DAY, @cuotas)",
             CONCAT("CALL creditos.registrar_solicitud(", @sol_id, ", 1, 'C001', 3000, 'PEN', 3, FALSE, 'FRANCES', 0.2200, @cuotas, REPEAT('e', 64), 'svc-evaluacion', UUID_TO_BIN(UUID()), @ronda, @eval, @rep3)"),
             @sol_editar),
  '^BNA-SOLICITUD: la solicitud ya se envió', 'procedimiento');

CALL prueba.rechaza('X819', 'Extensión', 'Solicitud', 'Con su verificación de Captación, un fiador respalda una sola solicitud (uk_fiador_solicitud_1)',
  JSON_ARRAY(@sol_crear,
             CONCAT("CALL creditos.guardar_borrador(UUID_TO_BIN('80000000-0000-4000-8000-000000000002'), NULL, 'C003', 3000, 'PEN', 3, FALSE, 'Capital de trabajo', CURRENT_DATE, ",
                    @sol_pol, ", JSON_ARRAY(), JSON_ARRAY('C002'), REPEAT('f', 64), 'asesor.sol', UUID_TO_BIN(UUID()), @r, @c, @p)")),
  '^BNA-FIADOR: el fiador ya respalda', 'procedimiento');

CALL prueba.rechaza('X820', 'Extensión', 'Solicitud', 'La revisión de una edición es positiva',
  JSON_ARRAY(@sol_crear, REPLACE(@sol_editar, "1, 'C001'", "0, 'C001'")), '^BNA-REVISION:', 'procedimiento');

CALL prueba.rechaza('X821', 'Extensión', 'bna_api', 'bna_api no escribe creditos.expediente_sol',
  JSON_ARRAY("UPDATE creditos.expediente_sol SET revision = 9"), 'denied', 'privilegio');

CALL prueba.rechaza('X822', 'Extensión', 'bna_api', 'bna_api no borra garantías directamente',
  JSON_ARRAY("DELETE FROM creditos.garantia"), 'denied', 'privilegio');

CALL prueba.rechaza('X823', 'Extensión', 'Solicitud', 'Editar un borrador que no existe se rechaza',
  JSON_ARRAY(@sol_editar), '^BNA-SOLICITUD: la solicitud no existe', 'procedimiento');

-- Receptor de eventos de auditoría de los módulos.
SET @aud = CONCAT("CALL core.recibir_evento_modulo(UUID_TO_BIN('81000000-0000-4000-8000-000000000001'), 'SOLICITUD DE CREDITO', ",
                  "'solicitud_credito', '80000000-0000-4000-8000-000000000001', 'RECIBIR_CR_INT_03', 'svc-sol', UUID_TO_BIN(UUID()), ",
                  "JSON_OBJECT('decision', 'APROBADO'), REPEAT('a', 64), @ev, @aud_rep)");

CALL prueba.verifica('X830', 'Extensión', 'Auditoría', 'Un evento de módulo queda en la bitácora con su módulo, acción, actor e id de origen',
  JSON_ARRAY(@aud),
  "NOT @aud_rep AND (SELECT CONCAT(modulo, ' ', accion, ' ', actor, ' ', JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.id_evento_modulo')), ' ', JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.decision'))) FROM core.v_evento_auditoria_api WHERE id_evento = @ev) = 'SOLICITUD DE CREDITO RECIBIR_CR_INT_03 svc-sol 81000000-0000-4000-8000-000000000001 APROBADO'",
  'SOLICITUD DE CREDITO RECIBIR_CR_INT_03 svc-sol <id> APROBADO',
  "(SELECT CONCAT_WS(' ', modulo, accion, actor) FROM core.v_evento_auditoria_api WHERE id_evento = @ev)", 'procedimiento');

CALL prueba.verifica('X831', 'Extensión', 'Auditoría', 'Repetir el mismo evento devuelve el mismo registro sin duplicarlo',
  JSON_ARRAY(@aud, "SET @ev1 = @ev", @aud),
  "@aud_rep AND @ev = @ev1 AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE JSON_UNQUOTE(JSON_EXTRACT(detalle, '$.id_evento_modulo')) = '81000000-0000-4000-8000-000000000001') = 1",
  'repetido, mismo registro, un evento', "CONCAT_WS(' ', @aud_rep, @ev = @ev1)", 'procedimiento');

CALL prueba.rechaza('X832', 'Extensión', 'Auditoría', 'El mismo id de evento con otro contenido se rechaza',
  JSON_ARRAY(@aud, REPLACE(@aud, "REPEAT('a', 64)", "REPEAT('b', 64)")), '^BNA-IDEMPOTENCIA:', 'procedimiento');

CALL prueba.rechaza('X833', 'Extensión', 'Auditoría', 'La acción de un evento es un código en mayúsculas',
  JSON_ARRAY(REPLACE(@aud, "'RECIBIR_CR_INT_03'", "'borrar todo'")), '^BNA-AUDITORIA:', 'procedimiento');

CALL prueba.rechaza('X834', 'Extensión', 'Auditoría', 'Un evento de un módulo desconocido se rechaza',
  JSON_ARRAY(REPLACE(@aud, "'SOLICITUD DE CREDITO'", "'NINGUNO'")), '^BNA-AUDITORIA:', 'procedimiento');

CALL prueba.rechaza('X835', 'Extensión', 'bna_api', 'bna_api no escribe core.evento_modulo',
  JSON_ARRAY("INSERT INTO core.evento_modulo (id_evento_modulo, id_modulo, huella, id_evento) VALUES (UUID_TO_BIN(UUID()), 11, REPEAT('a', 64), 1)"),
  'denied', 'privilegio');

CALL prueba.rechaza('X836', 'Extensión', 'Auditoría', 'Un evento sin actor se rechaza',
  JSON_ARRAY(REPLACE(@aud, "'svc-sol'", "NULL")), '^BNA-AUDITORIA:', 'procedimiento');

-- ---------------------------------------------------------------------
-- v1.16: el historial de estados de una tarjeta, para la pantalla de desbloqueo
-- ---------------------------------------------------------------------
CALL prueba.verifica('X837', 'Extensión', 'Consultas', 'La vista del historial de tarjetas tiene exactamente las columnas acordadas',
  JSON_ARRAY("SET @columnas = (SELECT GROUP_CONCAT(column_name ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema = 'tarjetas' AND table_name = 'v_historial_estado_tarjeta_api')"),
  "SELECT @columnas = 'id_historial,id_tarjeta,estado_nuevo,motivo,origen,fecha_hora'",
  'id_historial,id_tarjeta,estado_nuevo,motivo,origen,fecha_hora', "SELECT IFNULL(@columnas, 'sin vista')", 'vista');

CALL prueba.verifica('X838', 'Extensión', 'Consultas', 'bna_api lee el motivo y el origen de un bloqueo en el historial de la tarjeta',
  JSON_ARRAY("CALL tarjetas.cambiar_estado_tarjeta(UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'BLOQUEADA', 'Bloqueo solicitado por el cliente', 'CLIENTE', 'pruebas', @h)",
             "SET @fila = (SELECT CONCAT_WS(' | ', estado_nuevo, motivo, origen, fecha_hora IS NOT NULL) FROM tarjetas.v_historial_estado_tarjeta_api WHERE id_historial = @h AND id_tarjeta = UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'))"),
  "SELECT @fila = 'BLOQUEADA | Bloqueo solicitado por el cliente | CLIENTE | 1'",
  'BLOQUEADA | Bloqueo solicitado por el cliente | CLIENTE | 1', "SELECT IFNULL(@fila, 'NULL')", 'privilegio');

CALL prueba.rechaza('X839', 'Extensión', 'bna_api', 'bna_api no puede: escribir en el historial de la tarjeta por la vista',
  JSON_ARRAY("INSERT INTO tarjetas.v_historial_estado_tarjeta_api (id_tarjeta, estado_nuevo, motivo, origen) VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'ACTIVA', 'x', 'SEGURIDAD')"),
  'denied', 'privilegio');

CALL prueba.rechaza('X840', 'Extensión', 'bna_api', 'bna_api no puede: SELECT tarjetas.historial_estado_tarjeta (solo la vista)',
  JSON_ARRAY("SELECT * FROM tarjetas.historial_estado_tarjeta"), 'denied', 'privilegio');

-- ---------------------------------------------------------------------
-- v1.17: contraseña inicial y cambio obligatorio en el primer ingreso
-- ---------------------------------------------------------------------
SET @ana_x84 = "CALL core.crear_usuario(UUID_TO_BIN('17000000-0000-4000-8000-000000000001'), 'ana-x84', 'Ana', 'ASESOR', 'h-inicial', 'BCRYPT', 'v2', NULL, TRUE, 'admin')";
SET @svc_x84 = "CALL core.crear_usuario_servicio(UUID_TO_BIN('17000000-0000-4000-8000-000000000002'), 'svc-x84', 'S', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas')";

CALL prueba.verifica('X841', 'Extensión', 'Usuarios', 'Un usuario nuevo no debe cambiar su contraseña salvo que se le exija',
  JSON_ARRAY(@ana_x84),
  "SELECT (SELECT debe_cambiar_clave FROM core.usuario_sistema WHERE username = 'ana-x84') = 0",
  '0', "SELECT IFNULL((SELECT debe_cambiar_clave FROM core.usuario_sistema WHERE username = 'ana-x84'), 'sin columna')", 'declarativo');

CALL prueba.verifica('X842', 'Extensión', 'Usuarios', 'Exigir el cambio de contraseña marca a la persona y queda en la bitácora',
  JSON_ARRAY(@ana_x84, "CALL core.exigir_cambio_clave(UUID_TO_BIN('17000000-0000-4000-8000-000000000001'), 'admin', @f)"),
  "SELECT @f = 1 AND (SELECT debe_cambiar_clave FROM core.usuario_sistema WHERE username = 'ana-x84') = 1 AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'EXIGIR_CAMBIO_CLAVE' AND id_entidad = '17000000-0000-4000-8000-000000000001' AND actor = 'admin') = 1",
  '1, marca y un evento', "SELECT CONCAT_WS(' ', @f, (SELECT debe_cambiar_clave FROM core.usuario_sistema WHERE username = 'ana-x84'))", 'procedimiento');

CALL prueba.rechaza('X843', 'Extensión', 'Usuarios', 'A un usuario de servicio no se le exige cambiar la contraseña',
  JSON_ARRAY(@svc_x84, "CALL core.exigir_cambio_clave(UUID_TO_BIN('17000000-0000-4000-8000-000000000002'), 'admin', @f)"),
  '^BNA-USUARIO-SERVICIO:', 'procedimiento');

CALL prueba.verifica('X844', 'Extensión', 'Usuarios', 'Restablecer la contraseña de una persona la reemplaza, exige cambiarla y queda en la bitácora',
  JSON_ARRAY(@ana_x84, "CALL core.restablecer_clave(UUID_TO_BIN('17000000-0000-4000-8000-000000000001'), 'h-temporal', 'BCRYPT', 'v2', 'admin', @f)"),
  "SELECT @f = 1 AND (SELECT CONCAT(hash_password, ' ', debe_cambiar_clave) FROM core.usuario_sistema WHERE username = 'ana-x84') = 'h-temporal 1' AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'RESTABLECER_CLAVE' AND id_entidad = '17000000-0000-4000-8000-000000000001' AND actor = 'admin' AND detalle NOT LIKE '%h-temporal%') = 1",
  '1, hash nuevo, marca y un evento sin el hash', "SELECT CONCAT_WS(' ', @f, (SELECT CONCAT(hash_password, ' ', debe_cambiar_clave) FROM core.usuario_sistema WHERE username = 'ana-x84'))", 'procedimiento');

CALL prueba.rechaza('X845', 'Extensión', 'Usuarios', 'La contraseña de un usuario de servicio no se restablece por esta vía',
  JSON_ARRAY(@svc_x84, "CALL core.restablecer_clave(UUID_TO_BIN('17000000-0000-4000-8000-000000000002'), 'h', 'BCRYPT', 'v2', 'admin', @f)"),
  '^BNA-USUARIO-SERVICIO:', 'procedimiento');

CALL prueba.rechaza('X846', 'Extensión', 'Usuarios', 'No se restablece la contraseña de un usuario inexistente',
  JSON_ARRAY("CALL core.restablecer_clave(UUID_TO_BIN(UUID()), 'h', 'BCRYPT', 'v2', 'admin', @f)"),
  '^BNA-USUARIO:', 'procedimiento');

CALL prueba.verifica('X847', 'Extensión', 'Usuarios', 'La persona cambia su contraseña: se reemplaza, ya no debe cambiarla y queda en la bitácora a su nombre',
  JSON_ARRAY(@ana_x84, "CALL core.restablecer_clave(UUID_TO_BIN('17000000-0000-4000-8000-000000000001'), 'h-temporal', 'BCRYPT', 'v2', 'admin', @f)",
             "CALL core.cambiar_clave(UUID_TO_BIN('17000000-0000-4000-8000-000000000001'), 'h-propia', 'BCRYPT', 'v2', @f)"),
  "SELECT @f = 1 AND (SELECT CONCAT(hash_password, ' ', debe_cambiar_clave) FROM core.usuario_sistema WHERE username = 'ana-x84') = 'h-propia 0' AND (SELECT COUNT(*) FROM core.v_evento_auditoria_api WHERE accion = 'CAMBIAR_CLAVE' AND id_entidad = '17000000-0000-4000-8000-000000000001' AND actor = 'ana-x84') = 1",
  '1, hash propio, sin marca, evento de ana-x84', "SELECT CONCAT_WS(' ', @f, (SELECT CONCAT(hash_password, ' ', debe_cambiar_clave) FROM core.usuario_sistema WHERE username = 'ana-x84'))", 'procedimiento');

CALL prueba.rechaza('X848', 'Extensión', 'Usuarios', 'Un usuario de servicio no cambia su contraseña por esta vía',
  JSON_ARRAY(@svc_x84, "CALL core.cambiar_clave(UUID_TO_BIN('17000000-0000-4000-8000-000000000002'), 'h', 'BCRYPT', 'v2', @f)"),
  '^BNA-USUARIO-SERVICIO:', 'procedimiento');

CALL prueba.rechaza('X849', 'Extensión', 'Usuarios', 'No cambia la contraseña un usuario inexistente',
  JSON_ARRAY("CALL core.cambiar_clave(UUID_TO_BIN(UUID()), 'h', 'BCRYPT', 'v2', @f)"),
  '^BNA-USUARIO:', 'procedimiento');

CALL prueba.rechaza('X850', 'Extensión', 'bna_api', 'bna_api no puede: quitar la marca de cambio obligatorio directamente',
  JSON_ARRAY("UPDATE core.usuario_sistema SET debe_cambiar_clave = 0"), 'denied', 'privilegio');
