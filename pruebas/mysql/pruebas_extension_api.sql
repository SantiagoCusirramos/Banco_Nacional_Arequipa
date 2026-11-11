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
