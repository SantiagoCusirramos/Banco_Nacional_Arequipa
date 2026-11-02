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
