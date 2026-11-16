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
  "SELECT @n = 0 AND @v = 12", '0 columnas personales en 12 vistas', "SELECT CONCAT(@n, ' columnas en ', @v, ' vistas')", 'vista');

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
