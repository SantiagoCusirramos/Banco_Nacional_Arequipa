# Pruebas de sql/bna_extension.sql fuera de una transacción. El arnés siempre abre
# una, así que estas corren con el cliente mysql en autocommit, como bna_api_user,
# el rol de la API desplegada.
# Las carga run_tests.sh, que define root_, api_ y registrar.
# shellcheck shell=bash

seguridad_() { docker exec -i -e MYSQL_PWD=seg "$C" mysql -ubna_seguridad_user --default-character-set=utf8mb4 "$@"; }
root_ -e "CREATE ROLE IF NOT EXISTS bna_seguridad;
          CREATE USER 'bna_seguridad_user'@'%' IDENTIFIED BY 'seg' DEFAULT ROLE bna_seguridad;
          GRANT INSERT ON prueba.cerrojo TO 'bna_seguridad_user'@'%'"

# caso ID DESCRIPCION CONDICION < sentencias: tras ejecutarlas, CONDICION debe ser 1.
# CLIENTE elige la sesión: api_ por omisión.
caso() {
  local id="$1" desc="$2" cond="$3" salida obtenido
  salida="$("${CLIENTE:-api_}" --force 2>&1 || true)"
  obtenido="$(root_ -N -e "SELECT coalesce(($cond), 0)" 2>&1 || true)"
  registrar "$id" bna_api_user Extensión 'Sin transacción' "$desc" procedimiento 1 \
    "$obtenido; $(echo "$salida" | grep -m1 ERROR | cut -c1-120 | tr -d "'")" "$([ "$obtenido" = 1 ] && echo 1 || echo 0)"
}
asientos() { root_ -N -e "SELECT COUNT(*) FROM core.asiento_contable"; }

root_ <<'SQL'
INSERT INTO cuentas.cuenta_ahorro (num_cuenta, cci, moneda, regimen, estado_cuenta, id_agencia) VALUES
  ('AC-1', '00000000000000000071', 'PEN', 'INDIVIDUAL', 'ACTIVA', 'AQP01'),
  ('AC-2', '00000000000000000072', 'PEN', 'INDIVIDUAL', 'ACTIVA', 'AQP01'),
  ('AC-B', '00000000000000000073', 'PEN', 'INDIVIDUAL', 'BLOQUEADA', 'AQP01');
INSERT INTO cuentas.titularidad (cod_cliente, num_cuenta) VALUES ('C001', 'AC-1'), ('C002', 'AC-2'), ('C002', 'AC-B');
START TRANSACTION;
CALL prueba.movimiento('AC-1', 'DEPOSITO', 1000, 'VEN', NULL, NULL, @m);
COMMIT;
SQL

n="$(asientos)"
caso X70 'Una transferencia a una cuenta bloqueada no deja nada (C1)' \
  "SELECT (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-1') = 1000
      AND (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento WHERE llave = 'k70') = 0
      AND (SELECT COUNT(*) FROM core.asiento_contable) = $n" <<'SQL'
CALL cuentas.registrar_transferencia('AC-1', 'AC-B', 300, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k70', REPEAT('a', 64), 'pruebas', @d, @c, @r);
SQL
caso X71 'Repetir la llave tras un fallo no informa éxito (C1)' \
  "SELECT COUNT(*) = 0 FROM cuentas.idempotencia_movimiento WHERE llave = 'k70'" <<'SQL'
CALL cuentas.registrar_transferencia('AC-1', 'AC-B', 300, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k70', REPEAT('a', 64), 'pruebas', @d, @c, @r);
SQL
n="$(asientos)"
caso X72 'Un retiro sin saldo no deja asiento ni llave (C1)' \
  "SELECT (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento WHERE llave = 'k72') = 0
      AND (SELECT COUNT(*) FROM core.asiento_contable) = $n" <<'SQL'
CALL cuentas.registrar_movimiento('AC-2', 'RETIRO', 5, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k72', REPEAT('a', 64), 'pruebas', @m, @r);
SQL
caso X73 'Un titular inexistente no deja la cuenta (C1)' \
  "SELECT COUNT(*) = 0 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-X73'" <<'SQL'
CALL cuentas.abrir_cuenta('AC-X73', '00000000000000000075', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('NOEXISTE'), 'pruebas');
SQL
# Fallo a mitad de cada procedimiento: el evento es su último paso y un actor nulo
# lo rechaza después de las escrituras.
root_ <<'SQL'
INSERT INTO core.usuario_sistema (id_usuario, username, nombre, rol, hash_password, algoritmo_hash, version_hash)
VALUES (UUID_TO_BIN('77777777-7777-4777-8777-777777777777'), 'ac-rol', 'R', 'ASESOR', 'viejo', 'SHA256', 'v1');
INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
VALUES (UUID_TO_BIN('77777777-7777-4777-8777-777777777778'), 'tok-ac', '455788', '1234', '2026-01-01', '2030-01-01', 'ACTIVA', 'C001');
SQL
USUARIO="UUID_TO_BIN('77777777-7777-4777-8777-777777777777')"
PLASTICO="UUID_TO_BIN('77777777-7777-4777-8777-777777777778')"
caso X74 'crear_usuario no deja la fila si falla el evento (C1)' \
  "SELECT COUNT(*) = 0 FROM core.usuario_sistema WHERE username = 'ac-x74'" <<SQL
CALL core.crear_usuario(UUID_TO_BIN(UUID()), 'ac-x74', 'A', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, NULL);
SQL
caso X75 'asignar_rol no cambia el rol si falla el evento (C1)' \
  "SELECT rol = 'ASESOR' FROM core.usuario_sistema WHERE username = 'ac-rol'" <<SQL
CALL core.asignar_rol($USUARIO, 'AUDITOR', NULL, @f);
SQL
caso X76 'migrar_hash_usuario no cambia el hash si falla el evento (C1)' \
  "SELECT hash_password = 'viejo' FROM core.usuario_sistema WHERE username = 'ac-rol'" <<SQL
CALL core.migrar_hash_usuario($USUARIO, 'SHA256', 'nuevo', 'BCRYPT', 'v2', NULL, @f);
SQL
n="$(asientos)"
caso X77 'registrar_movimiento no deja saldo, asiento ni llave si falla el evento (C1)' \
  "SELECT (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-1') = 1000
      AND (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento WHERE llave = 'k77') = 0
      AND (SELECT COUNT(*) FROM core.asiento_contable) = $n" <<'SQL'
CALL cuentas.registrar_movimiento('AC-1', 'DEPOSITO', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k77', REPEAT('a', 64), NULL, @m, @r);
SQL
caso X78 'registrar_transferencia no mueve saldos si falla el evento (C1)' \
  "SELECT (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-1') = 1000
      AND (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento WHERE llave = 'k78') = 0
      AND (SELECT COUNT(*) FROM core.asiento_contable) = $n" <<'SQL'
CALL cuentas.registrar_transferencia('AC-1', 'AC-2', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k78', REPEAT('a', 64), NULL, @d, @c, @r);
SQL
caso X79 'abrir_cuenta no deja la cuenta si falla el evento (C1)' \
  "SELECT COUNT(*) = 0 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-X79'" <<'SQL'
CALL cuentas.abrir_cuenta('AC-X79', '00000000000000000079', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('C001'), NULL);
SQL
caso X80 'emitir_tarjeta no deja la tarjeta si falla el evento (C1)' \
  "SELECT COUNT(*) = 0 FROM tarjetas.tarjeta WHERE pan_token = 'tok-x80'" <<'SQL'
CALL tarjetas.emitir_tarjeta(UUID_TO_BIN(UUID()), 'tok-x80', '455788', '1234', '2026-01-01', '2030-01-01', 'C001', 'AC-1', NULL);
SQL
caso X81 'cambiar_estado_tarjeta no cambia el estado si falla el evento (C1)' \
  "SELECT estado_tarjeta = 'ACTIVA' FROM tarjetas.tarjeta WHERE pan_token = 'tok-ac'" <<SQL
CALL tarjetas.cambiar_estado_tarjeta($PLASTICO, 'BLOQUEADA', 'x', 'CLIENTE', NULL, @h);
SQL

caso X82 'Una operación válida se confirma sola y deja su evento (C1)' \
  "SELECT (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-2') = 40
      AND (SELECT uuid_transaccion IS NOT NULL FROM cuentas.idempotencia_movimiento WHERE llave = 'k82')" <<'SQL'
CALL cuentas.registrar_movimiento('AC-2', 'DEPOSITO', 40, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k82', REPEAT('a', 64), 'pruebas', @m, @r);
SQL
# Dentro de una transacción del que llama, cada procedimiento que falla deshace solo
# lo suyo: el trabajo previo se confirma y de la operación no queda nada. Fallan al
# registrar el evento, el último paso, con las escrituras ya hechas (N2).
previo() { echo "START TRANSACTION;
CALL cuentas.registrar_movimiento('AC-2', 'DEPOSITO', 1, 'g', 'VEN', UUID_TO_BIN(UUID()), '$1', REPEAT('a', 64), 'pruebas', @m, @r);"; }
quedo() { echo "(SELECT uuid_transaccion IS NOT NULL FROM cuentas.idempotencia_movimiento WHERE llave = '$1')"; }
caso X83 'Un retiro sin saldo en una transacción no deshace el trabajo previo (C1)' \
  "SELECT $(quedo p83) AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-2') = 41
      AND (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento WHERE llave = 'k83') = 0" <<SQL
$(previo p83)
CALL cuentas.registrar_movimiento('AC-2', 'RETIRO', 9999, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k83', REPEAT('a', 64), 'pruebas', @m, @r);
COMMIT;
SQL
caso X94 'crear_usuario deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p94) AND (SELECT COUNT(*) FROM core.usuario_sistema WHERE username = 'ac-x94') = 0" <<SQL
$(previo p94)
CALL core.crear_usuario(UUID_TO_BIN(UUID()), 'ac-x94', 'A', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, NULL);
COMMIT;
SQL
caso X95 'asignar_rol deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p95) AND (SELECT rol FROM core.usuario_sistema WHERE username = 'ac-rol') = 'ASESOR'" <<SQL
$(previo p95)
CALL core.asignar_rol($USUARIO, 'AUDITOR', NULL, @f);
COMMIT;
SQL
caso X96 'migrar_hash_usuario deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p96) AND (SELECT hash_password FROM core.usuario_sistema WHERE username = 'ac-rol') = 'viejo'" <<SQL
$(previo p96)
CALL core.migrar_hash_usuario($USUARIO, 'SHA256', 'nuevo', 'BCRYPT', 'v2', NULL, @f);
COMMIT;
SQL
n="$(asientos)"
caso X97 'registrar_movimiento deshace saldo, asiento y llave tras el asiento (N2)' \
  "SELECT $(quedo p97) AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-1') = 1000
      AND (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento WHERE llave = 'k97') = 0
      AND (SELECT COUNT(*) FROM core.asiento_contable) = $n + 1" <<SQL
$(previo p97)
CALL cuentas.registrar_movimiento('AC-1', 'DEPOSITO', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k97', REPEAT('a', 64), NULL, @m, @r);
COMMIT;
SQL
n="$(asientos)"
caso X98 'registrar_transferencia deshace los dos tramos (N2)' \
  "SELECT $(quedo p98) AND (SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-1') = 1000
      AND (SELECT COUNT(*) FROM cuentas.idempotencia_movimiento WHERE llave = 'k98') = 0
      AND (SELECT COUNT(*) FROM core.asiento_contable) = $n + 1" <<SQL
$(previo p98)
CALL cuentas.registrar_transferencia('AC-1', 'AC-2', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k98', REPEAT('a', 64), NULL, @d, @c, @r);
COMMIT;
SQL
caso X99 'abrir_cuenta deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p99) AND (SELECT COUNT(*) FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-X99') = 0" <<SQL
$(previo p99)
CALL cuentas.abrir_cuenta('AC-X99', '00000000000000000099', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('C001'), NULL);
COMMIT;
SQL
caso X100 'emitir_tarjeta deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p100) AND (SELECT COUNT(*) FROM tarjetas.tarjeta WHERE pan_token = 'tok-x100') = 0" <<SQL
$(previo p100)
CALL tarjetas.emitir_tarjeta(UUID_TO_BIN(UUID()), 'tok-x100', '455788', '1234', '2026-01-01', '2030-01-01', 'C001', 'AC-1', NULL);
COMMIT;
SQL
caso X101 'cambiar_estado_tarjeta deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p101) AND (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE pan_token = 'tok-ac') = 'ACTIVA'" <<SQL
$(previo p101)
CALL tarjetas.cambiar_estado_tarjeta($PLASTICO, 'BLOQUEADA', 'x', 'CLIENTE', NULL, @h);
COMMIT;
SQL
CLIENTE=app_ caso X104 'registrar_asiento deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT (SELECT COUNT(*) FROM cuentas.movimiento WHERE glosa = 'x104') = 1
      AND (SELECT COUNT(*) FROM core.asiento_contable WHERE numero_asiento = 'X104') = 0" <<SQL
START TRANSACTION;
CALL cuentas.registrar_movimiento('AC-2', 'DEPOSITO', 1, 'x104', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'pruebas', @m, @r);
CALL core.registrar_asiento(NULL, 'X104', CURRENT_DATE, CURRENT_DATE, 'g', 'PEN', UUID_TO_BIN(UUID()), NULL,
  JSON_ARRAY(JSON_OBJECT('partida', 'DEBE', 'importe', 1, 'cuenta', '1101'), JSON_OBJECT('partida', 'HABER', 'importe', 1, 'cuenta', '9999')), @a);
COMMIT;
SQL

# I1: la sesión 1 fija su instantánea, otra sesión desbloquea la tarjeta y la
# sesión 1 pide bloquearla.
root_ <<'SQL'
INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
VALUES (UUID_TO_BIN('66666666-6666-4666-8666-666666666666'), 'tok-x84', '455788', '1234', '2026-01-01', '2030-01-01', 'ACTIVA', 'C001');
INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
VALUES ('BLOQUEADA', 'x', 'SEGURIDAD', UUID_TO_BIN('66666666-6666-4666-8666-666666666666'));
SQL
TARJETA="UUID_TO_BIN('66666666-6666-4666-8666-666666666666')"
api_ > "$OUT/X84-sesion1.log" 2>&1 <<SQL &
START TRANSACTION;
SELECT estado_tarjeta FROM tarjetas.v_tarjeta_api WHERE id_tarjeta = $TARJETA;
DO SLEEP(2);
CALL tarjetas.cambiar_estado_tarjeta($TARJETA, 'BLOQUEADA', 'robo', 'CLIENTE', 'pruebas', @h);
COMMIT;
SQL
sesion1=$!
sleep 1
seguridad_ -e "CALL tarjetas.desbloquear_tarjeta($TARJETA, 'y', 'pruebas', @h)" || true
wait "$sesion1" || true
caso X84 'Un bloqueo concurrente se aplica y avisa a SEGURIDAD (I1)' \
  "SELECT (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = $TARJETA) = 'BLOQUEADA'
      AND (SELECT COUNT(*) FROM tarjetas.evento_salida WHERE id_tarjeta = $TARJETA AND carga_json->>'\$.motivo' = 'robo') = 1" </dev/null

# I2: el desbloqueo solo existe para bna_seguridad.
root_ <<'SQL'
INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
VALUES (UUID_TO_BIN('88888888-8888-4888-8888-888888888881'), 'tok-x85', '455788', '1234', '2026-01-01', '2030-01-01', 'ACTIVA', 'C001'),
       (UUID_TO_BIN('88888888-8888-4888-8888-888888888882'), 'tok-x87', '455788', '1234', '2026-01-01', '2030-01-01', 'ACTIVA', 'C001'),
       (UUID_TO_BIN('88888888-8888-4888-8888-888888888883'), 'tok-x92', '455788', '1234', '2026-01-01', '2030-01-01', 'PENDIENTE_ACTIVACION', 'C001'),
       (UUID_TO_BIN('88888888-8888-4888-8888-888888888884'), 'tok-x102', '455788', '1234', '2026-01-01', '2030-01-01', 'ACTIVA', 'C001'),
       (UUID_TO_BIN('88888888-8888-4888-8888-888888888885'), 'tok-x102b', '455788', '1234', '2026-01-01', '2030-01-01', 'ACTIVA', 'C001');
INSERT INTO tarjetas.historial_estado_tarjeta (estado_nuevo, motivo, origen, id_tarjeta)
VALUES ('BLOQUEADA', 'x', 'SEGURIDAD', UUID_TO_BIN('88888888-8888-4888-8888-888888888881')),
       ('RETENIDA', 'x', 'SISTEMA', UUID_TO_BIN('88888888-8888-4888-8888-888888888882')),
       ('BLOQUEADA', 'x', 'SEGURIDAD', UUID_TO_BIN('88888888-8888-4888-8888-888888888884')),
       ('BLOQUEADA', 'x', 'SEGURIDAD', UUID_TO_BIN('88888888-8888-4888-8888-888888888885'));
SQL
T1="UUID_TO_BIN('88888888-8888-4888-8888-888888888881')"
T2="UUID_TO_BIN('88888888-8888-4888-8888-888888888882')"
T3="UUID_TO_BIN('88888888-8888-4888-8888-888888888883')"
T4="UUID_TO_BIN('88888888-8888-4888-8888-888888888884')"
T5="UUID_TO_BIN('88888888-8888-4888-8888-888888888885')"
estado() { echo "SELECT estado_tarjeta = '$2' FROM tarjetas.tarjeta WHERE id_tarjeta = $1"; }
caso X85 'cambiar_estado_tarjeta no desbloquea con origen OPERADOR (I2)' "$(estado "$T1" BLOQUEADA)" <<SQL
CALL tarjetas.cambiar_estado_tarjeta($T1, 'ACTIVA', 'x', 'OPERADOR', 'pruebas', @h);
SQL
caso X86 'cambiar_estado_tarjeta no desbloquea con origen SEGURIDAD (I2)' "$(estado "$T1" BLOQUEADA)" <<SQL
CALL tarjetas.cambiar_estado_tarjeta($T1, 'ACTIVA', 'x', 'SEGURIDAD', 'pruebas', @h);
SQL
caso X87 'cambiar_estado_tarjeta no reactiva una tarjeta RETENIDA (I2)' "$(estado "$T2" RETENIDA)" <<SQL
CALL tarjetas.cambiar_estado_tarjeta($T2, 'ACTIVA', 'x', 'OPERADOR', 'pruebas', @h);
SQL
CLIENTE=app_ caso X88 'bna_app no ejecuta desbloquear_tarjeta (I2)' "$(estado "$T1" BLOQUEADA)" <<SQL
CALL tarjetas.desbloquear_tarjeta($T1, 'x', 'pruebas', @h);
SQL
CLIENTE=seguridad_ caso X89 'Sin actor no se desbloquea: la operación es atómica (I2)' "$(estado "$T1" BLOQUEADA)" <<SQL
CALL tarjetas.desbloquear_tarjeta($T1, 'x', NULL, @h);
SQL
CLIENTE=seguridad_ caso X90 'bna_seguridad desbloquea, con historial, aviso y auditoría (I2)' \
  "SELECT (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = $T1) = 'ACTIVA'
      AND (SELECT origen FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = $T1 ORDER BY id_historial DESC LIMIT 1) = 'SEGURIDAD'
      AND (SELECT COUNT(*) FROM tarjetas.evento_salida WHERE id_tarjeta = $T1 AND carga_json->>'\$.estado_nuevo' = 'ACTIVA') = 1
      AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'DESBLOQUEAR_TARJETA' AND id_entidad = BIN_TO_UUID($T1)) = 1" <<SQL
CALL tarjetas.desbloquear_tarjeta($T1, 'revisado', 'pruebas', @h);
SQL
CLIENTE=seguridad_ caso X91 'bna_seguridad también libera una tarjeta RETENIDA (I2)' "$(estado "$T2" ACTIVA)" <<SQL
CALL tarjetas.desbloquear_tarjeta($T2, 'revisado', 'pruebas', @h);
SQL
CLIENTE=seguridad_ caso X92 'desbloquear_tarjeta no activa una tarjeta que no está bloqueada (I2)' \
  "$(estado "$T3" PENDIENTE_ACTIVACION)" <<SQL
CALL tarjetas.desbloquear_tarjeta($T3, 'x', 'pruebas', @h);
SQL
caso X106 'cambiar_estado_tarjeta no acepta el origen SEGURIDAD de quien llama (I2)' \
  "$(estado "$T2" ACTIVA)" <<SQL
CALL tarjetas.cambiar_estado_tarjeta($T2, 'BLOQUEADA', 'x', 'SEGURIDAD', 'pruebas', @h);
SQL
CLIENTE=seguridad_ caso X102 'desbloquear_tarjeta deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = $T4) = 'ACTIVA'
      AND (SELECT estado_tarjeta FROM tarjetas.tarjeta WHERE id_tarjeta = $T5) = 'BLOQUEADA'" <<SQL
START TRANSACTION;
CALL tarjetas.desbloquear_tarjeta($T4, 'x', 'pruebas', @h);
CALL tarjetas.desbloquear_tarjeta($T5, 'x', NULL, @h);
COMMIT;
SQL
CLIENTE=seguridad_ caso X93 'bna_seguridad no ejecuta los otros procedimientos (I2)' \
  "SELECT COUNT(*) = 0 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-X93'" <<'SQL'
CALL cuentas.abrir_cuenta('AC-X93', '00000000000000000093', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('C001'), 'pruebas');
SQL

# N1: un deadlock dentro de core.registrar_asiento. La sesión W, con más trabajo para
# que InnoDB no la elija como víctima, bloquea la moneda; V reserva la llave y espera
# esa moneda al insertar el asiento; W pide la misma llave y cierra el ciclo.
# deadlock ID DESCRIPCION LLAVE INICIO FIN [LLAMADA]: V debe recibir 1213 y no dejar
# nada. LLAMADA, con $llave, reemplaza al depósito.
deadlock() {
  local id="$1" desc="$2" llave="$3" inicio="$4" fin="$5" salida ok=0 saldo_antes saldo_despues
  local llamada="${6:-CALL cuentas.registrar_movimiento('AC-1', 'DEPOSITO', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), '$llave', REPEAT('a', 64), 'pruebas', @m, @r);}"
  saldo_antes="$(root_ -N -e "SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-1'")"
  root_ > "$OUT/$id-w.log" 2>&1 <<SQL &
START TRANSACTION;
INSERT INTO core.tipo_cambio
WITH RECURSIVE n (i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 500)
SELECT 'USD', 'PEN', '2000-01-01' + INTERVAL i DAY, 1 FROM n;
SELECT cod_moneda FROM core.moneda WHERE cod_moneda = 'PEN' FOR UPDATE;
DO SLEEP(2);
INSERT INTO cuentas.idempotencia_movimiento (llave, huella) VALUES ('$llave', REPEAT('w', 64));
ROLLBACK;
SQL
  local w=$!
  sleep 1
  salida="$(api_ --force 2>&1 <<SQL || true
$inicio
$llamada
SELECT 'repetido', @r, 'uuid', HEX(@m);
$fin
SQL
)"
  wait "$w" || true
  echo "$salida" > "$OUT/$id-v.log"
  saldo_despues="$(root_ -N -e "SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-1'")"
  echo "$salida" | grep -q '^ERROR 1213' && [ "$saldo_antes" = "$saldo_despues" ] && ok=1
  registrar "$id" bna_api_user Extensión 'Deadlock' "$desc" procedimiento 'ERROR 1213' \
    "$(echo "$salida" | grep -m1 ERROR | cut -c1-120 | tr -d "'")" "$ok"
}
deadlock X107 'El deadlock en registrar_asiento llega al cliente en autocommit (N1)' k107 '' ''
deadlock X108 'El deadlock en registrar_asiento llega al cliente en su transacción (N1)' k108 'START TRANSACTION;' 'COMMIT;'

# R3: la guarda de 1305 de cada procedimiento. Fuera de la transacción de quien llama
# no hace falta, porque ROLLBACK no depende del savepoint.
TRANSFERENCIA() { echo "CALL cuentas.registrar_transferencia('AC-1', 'AC-2', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), '$1', REPEAT('a', 64), 'pruebas', @m, @c, @r);"; }
deadlock X140 'El deadlock de una transferencia llega al cliente en autocommit (R3)' k140 '' '' "$(TRANSFERENCIA k140)"
deadlock X141 'El deadlock de una transferencia llega al cliente en su transacción (R3)' k141 \
  'START TRANSACTION;' 'COMMIT;' "$(TRANSFERENCIA k141)"

# El mismo ciclo para los procedimientos sin asiento: V toma un candado propio antes de
# llamar y espera la bitácora, que W tiene bloqueada; W pide ese candado.
# deadlock_procedimiento ID NOMBRE CONDICION LLAMADA: tras 1213, CONDICION debe ser 1.
deadlock_procedimiento() {
  local id="$1" nombre="$2" cond="$3" llamada="$4" salida obtenido ok=0
  root_ > "$OUT/$id-w.log" 2>&1 <<SQL &
START TRANSACTION;
INSERT INTO core.tipo_cambio
WITH RECURSIVE n (i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 500)
SELECT 'USD', 'PEN', '2000-01-01' + INTERVAL i DAY, 1 FROM n;
SELECT COUNT(*) FROM core.evento_auditoria FOR UPDATE;
DO SLEEP(2);
INSERT INTO prueba.cerrojo VALUES ('$id');
ROLLBACK;
SQL
  local w=$!
  sleep 1
  salida="$("${CLIENTE:-api_}" --force 2>&1 <<SQL || true
START TRANSACTION;
INSERT INTO prueba.cerrojo VALUES ('$id');
$llamada
COMMIT;
SQL
)"
  wait "$w" || true
  echo "$salida" > "$OUT/$id-v.log"
  obtenido="$(root_ -N -e "SELECT coalesce(($cond), 0)" 2>&1 || true)"
  echo "$salida" | grep -q '^ERROR 1213' && [ "$obtenido" = 1 ] && ok=1
  registrar "$id" bna_api_user Extensión 'Deadlock' "$nombre conserva 1213 en la transacción de quien llama (R3)" procedimiento \
    'ERROR 1213' "$obtenido; $(echo "$salida" | grep -m1 ERROR | cut -c1-120 | tr -d "'")" "$ok"
}
deadlock_procedimiento X142 crear_usuario "SELECT COUNT(*) = 0 FROM core.usuario_sistema WHERE username = 'ac-x142'" \
  "CALL core.crear_usuario(UUID_TO_BIN(UUID()), 'ac-x142', 'A', 'ASESOR', 'h', 'BCRYPT', 'v2', NULL, TRUE, 'pruebas');"
deadlock_procedimiento X143 asignar_rol "SELECT rol = 'ASESOR' FROM core.usuario_sistema WHERE id_usuario = $USUARIO" \
  "CALL core.asignar_rol($USUARIO, 'AUDITOR', 'pruebas', @f);"
deadlock_procedimiento X144 migrar_hash_usuario "SELECT hash_password = 'viejo' FROM core.usuario_sistema WHERE id_usuario = $USUARIO" \
  "CALL core.migrar_hash_usuario($USUARIO, 'SHA256', 'nuevo', 'BCRYPT', 'v2', 'pruebas', @f);"
deadlock_procedimiento X145 abrir_cuenta "SELECT COUNT(*) = 0 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'AC-X145'" \
  "CALL cuentas.abrir_cuenta('AC-X145', '00000000000000000145', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('C001'), 'pruebas');"
deadlock_procedimiento X146 emitir_tarjeta "SELECT COUNT(*) = 0 FROM tarjetas.tarjeta WHERE pan_token = 'tok-x146'" \
  "CALL tarjetas.emitir_tarjeta(UUID_TO_BIN(UUID()), 'tok-x146', '455788', '1234', '2026-01-01', '2030-01-01', 'C001', 'AC-1', 'pruebas');"
deadlock_procedimiento X147 cambiar_estado_tarjeta "$(estado "$PLASTICO" ACTIVA)" \
  "CALL tarjetas.cambiar_estado_tarjeta($PLASTICO, 'BLOQUEADA', 'x', 'CLIENTE', 'pruebas', @h);"
CLIENTE=seguridad_ deadlock_procedimiento X148 desbloquear_tarjeta "$(estado "$T5" BLOQUEADA)" \
  "CALL tarjetas.desbloquear_tarjeta($T5, 'x', 'pruebas', @h);"

# R4: la lista de lo que bna_api puede leer es exacta. Se intenta leer cada tabla y
# vista de las bases del sistema con la sesión de la API.
lista="$(lecturas_de root_ api_ || true)"
diferencia="$(diff "$HERE/lecturas_api.txt" <(echo "$lista") || true)"
registrar X136 bna_api_user Extensión 'Permisos' 'bna_api lee exactamente los objetos de lecturas_api.txt (R4)' privilegio \
  'sin diferencias' "${diferencia:-sin diferencias}" "$([ -z "$diferencia" ] && echo 1 || echo 0)"
comodines="$(root_ -N -e "$CONCESIONES_AMPLIAS_API")"
registrar X137 root Extensión 'Permisos' 'bna_api no tiene SELECT global, por base, por columna ni roles heredados (R4)' privilegio \
  0 "$comodines" "$([ "$comodines" = 0 ] && echo 1 || echo 0)"

# Una llave reservada sin operación no devuelve un resultado vacío (rama de reservar_llave).
llave_sin_operacion() {
  local id="$1" desc="$2" llave="$3" llamada="$4" salida ok=0
  root_ -e "INSERT INTO cuentas.idempotencia_movimiento (llave, huella) VALUES ('$llave', REPEAT('a', 64))"
  salida="$(api_ --force 2>&1 <<< "$llamada" || true)"
  echo "$salida" | grep -q 'BNA-IDEMPOTENCIA.*no tiene una operación registrada' && ok=1
  registrar "$id" bna_api_user Extensión 'Idempotencia' "$desc" procedimiento 'BNA-IDEMPOTENCIA' \
    "$(echo "$salida" | head -1 | cut -c1-120 | tr -d "'")" "$ok"
}
llave_sin_operacion X138 'Un depósito rechaza una llave sin operación registrada' k138 \
  "CALL cuentas.registrar_movimiento('AC-1', 'DEPOSITO', 10, 'g', 'VEN', UUID_TO_BIN(UUID()), 'k138', REPEAT('a', 64), 'pruebas', @m, @r);"
llave_sin_operacion X139 'Una transferencia rechaza una llave sin operación registrada' k139 \
  "$(TRANSFERENCIA k139)"

# --- v1.1: usuarios de servicio, clientes y validaciones. Lo que bna_api no puede
# leer (la bitácora y clientes.*) lo comprueba root después.
SRV="UUID_TO_BIN('15000000-0000-4000-8000-0000000000a1')"
uuid_v11() { echo "UUID_TO_BIN('15000000-0000-4000-8000-0000000000$1')"; }
caso X208 'Crear un usuario de servicio y su login dejan sus eventos; el login toma el actor de la fila (v1.1)' \
  "SELECT (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'CREAR_USUARIO_SERVICIO' AND id_entidad = BIN_TO_UUID($SRV)
             AND actor = 'admin-x208' AND detalle->>'\$.modulo' = 'CLIENTES') = 1
      AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'LOGIN' AND id_entidad = BIN_TO_UUID($SRV)
             AND actor = 'svc-x208' AND correlation_id = $(uuid_v11 c1) AND detalle->>'\$.modulo' = 'CLIENTES') = 1" <<SQL
CALL core.crear_usuario_servicio($SRV, 'svc-x208', 'Clientes', 'CLIENTES', 'h0', 'BCRYPT', 'v2', 'admin-x208');
CALL core.registrar_login($SRV, $(uuid_v11 c1));
SQL
caso X209 'Renovar, desactivar y reactivar dejan un evento cada uno, sin el hash (v1.1)' \
  "SELECT (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'RENOVAR_CREDENCIAL' AND id_entidad = BIN_TO_UUID($SRV)
             AND JSON_SEARCH(detalle, 'one', 'h1') IS NULL) = 1
      AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'DESACTIVAR_USUARIO' AND id_entidad = BIN_TO_UUID($SRV)) = 1
      AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'ACTIVAR_USUARIO' AND id_entidad = BIN_TO_UUID($SRV)) = 1
      AND (SELECT activo AND hash_password = 'h1' FROM core.usuario_sistema WHERE id_usuario = $SRV)" <<SQL
CALL core.renovar_credencial($SRV, 'h1', 'BCRYPT', 'v2', 'admin', @f);
CALL core.cambiar_estado_usuario($SRV, FALSE, 'admin', @f);
CALL core.cambiar_estado_usuario($SRV, FALSE, 'admin', @f);
CALL core.cambiar_estado_usuario($SRV, TRUE, 'admin', @f);
SQL
caso X210 'Registrar un cliente deja su captación y un evento de CLIENTES sin datos personales (v1.1)' \
  "SELECT (SELECT c.estado_cliente = 'ACTIVO' AND v.estado_habilitante = 'HABILITADO' AND c.correo = 'c210@example.com'
             FROM clientes.cliente c JOIN clientes.verificacion_captacion v USING (id_verificacion_captacion)
            WHERE c.numero_documento = '71000210')
      AND (SELECT COUNT(*) FROM core.evento_auditoria e JOIN clientes.cliente c ON e.id_entidad = c.cod_cliente
            WHERE c.numero_documento = '71000210' AND e.accion = 'REGISTRAR_CLIENTE' AND e.actor = 'svc-x208'
              AND e.correlation_id = $(uuid_v11 c2) AND e.id_modulo = 2
              AND JSON_SEARCH(e.detalle, 'one', '71000210') IS NULL AND JSON_SEARCH(e.detalle, 'one', '%example.com') IS NULL
              AND JSON_SEARCH(e.detalle, 'one', '961000210') IS NULL) = 1" <<SQL
CALL clientes.registrar_cliente('DNI', '71000210', ' Prueba ', 'Ficticio', '', ' C210@Example.com ', '961000210', 'v1', 'HABILITADO', $(uuid_v11 c2), 'svc-x208', @c);
SQL
caso X211 'La verificación por documento deja su validación y el evento con los dos motivos (v1.1)' \
  "SELECT (SELECT COUNT(*) FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 c3)
             AND tipo_validacion = 'DOCUMENTO' AND resultado = 'RECHAZADO' AND cod_cliente = 'C001') = 1
      AND (SELECT COUNT(*) FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 c4)
             AND resultado = 'RECHAZADO' AND cod_cliente IS NULL) = 1
      AND (SELECT COUNT(*) FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 c5)
             AND resultado = 'APROBADO' AND cod_cliente = 'C001') = 1
      AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'VALIDAR_DOCUMENTO' AND correlation_id = $(uuid_v11 c3)
             AND detalle->>'\$.motivo_llamador' = 'RENIEC_NO_COINCIDE' AND detalle->>'\$.motivo_core' = 'IDENTIDAD_NO_VERIFICADA') = 1" <<SQL
CALL clientes.verificar_documento('DNI', '70000001', FALSE, 'RENIEC_NO_COINCIDE', $(uuid_v11 c3), 'pruebas', @i, @r, @m, @j);
CALL clientes.verificar_documento('DNI', '71999999', FALSE, 'RENIEC_NO_COINCIDE', $(uuid_v11 c4), 'pruebas', @i, @r, @m, @j);
CALL clientes.verificar_documento('DNI', '70000001', TRUE, NULL, $(uuid_v11 c5), 'pruebas', @i, @r, @m, @j);
SQL
caso X212 'Una validación dactilar deja su fila y el motivo en el evento (v1.1)' \
  "SELECT (SELECT COUNT(*) FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 c6)
             AND tipo_validacion = 'HUELLA' AND resultado = 'RECHAZADO' AND cod_cliente = 'C002') = 1
      AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'REGISTRAR_VALIDACION' AND correlation_id = $(uuid_v11 c6)
             AND detalle->>'\$.motivo' = 'SIMILITUD_BAJA') = 1" <<SQL
CALL clientes.registrar_validacion('C002', 'HUELLA', 'RECHAZADO', 'SIMILITUD_BAJA', $(uuid_v11 c6), 'pruebas', @i);
SQL
caso X213 'Un cambio de estado deja el motivo en el evento; repetir el estado no deja otro (v1.1)' \
  "SELECT (SELECT COUNT(*) FROM core.evento_auditoria e JOIN clientes.cliente c ON e.id_entidad = c.cod_cliente
            WHERE c.numero_documento = '71000213' AND e.accion = 'CAMBIAR_ESTADO_CLIENTE' AND e.detalle->>'\$.motivo' = 'Fraude'
              AND e.detalle->>'\$.estado_anterior' = 'ACTIVO' AND e.detalle->>'\$.estado_nuevo' = 'SUSPENDIDO') = 1
      AND (SELECT COUNT(*) FROM core.evento_auditoria e JOIN clientes.cliente c ON e.id_entidad = c.cod_cliente
            WHERE c.numero_documento = '71000213' AND e.accion = 'CAMBIAR_ESTADO_CLIENTE') = 1" <<SQL
CALL clientes.registrar_cliente('DNI', '71000213', 'Prueba', 'Ficticio', NULL, 'c213@example.com', '961000213', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c);
CALL clientes.cambiar_estado_cliente(@c, 'SUSPENDIDO', 'Fraude', 'pruebas', @a);
CALL clientes.cambiar_estado_cliente(@c, 'SUSPENDIDO', 'Otra vez', 'pruebas', @a);
SQL

# C1 para v1.1: sin actor, el evento (último paso) falla con las escrituras hechas.
root_ <<'SQL'
INSERT INTO clientes.verificacion_captacion (id_verificacion_captacion, estado_habilitante) VALUES ('VC-X218', 'HABILITADO');
INSERT INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, apellido_paterno, correo, celular,
                              estado_cliente, id_verificacion_captacion, version_contrato)
VALUES ('CX218', 'DNI', '71000218', 'Prueba', 'Ficticio', 'c218@example.com', '961000218', 'ACTIVO', 'VC-X218', 'v1');
INSERT INTO tarjetas.tarjeta (id_tarjeta, pan_token, bin, ultimos4, fecha_emision, fecha_vencimiento, estado_tarjeta, cod_cliente)
VALUES (UUID_TO_BIN('15000000-0000-4000-8000-0000000000d1'), 'tok-x218', '455788', '1234', '2026-01-01', '2030-01-01', 'ACTIVA', 'CX218');
SQL
captaciones() { root_ -N -e "SELECT COUNT(*) FROM clientes.verificacion_captacion"; }
vc="$(captaciones)"
caso X214 'registrar_cliente no deja cliente ni captación si falla el evento (C1)' \
  "SELECT (SELECT COUNT(*) FROM clientes.cliente WHERE numero_documento = '71000214') = 0
      AND (SELECT COUNT(*) FROM clientes.verificacion_captacion) = $vc" <<'SQL'
CALL clientes.registrar_cliente('DNI', '71000214', 'Prueba', 'Ficticio', NULL, 'c214@example.com', '961000214', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), NULL, @c);
SQL
caso X215 'Un correo duplicado no deja una captación huérfana (C1)' \
  "SELECT (SELECT COUNT(*) FROM clientes.cliente WHERE numero_documento = '71000215') = 0
      AND (SELECT COUNT(*) FROM clientes.verificacion_captacion) = $vc" <<'SQL'
CALL clientes.registrar_cliente('DNI', '71000215', 'Prueba', 'Ficticio', NULL, 'juan@example.com', '961000215', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c);
SQL
caso X216 'verificar_documento no deja la validación si falla el evento (C1)' \
  "SELECT COUNT(*) = 0 FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 c7)" <<SQL
CALL clientes.verificar_documento('DNI', '70000001', TRUE, NULL, $(uuid_v11 c7), NULL, @i, @r, @m, @j);
SQL
caso X217 'registrar_validacion no deja la validación si falla el evento (C1)' \
  "SELECT COUNT(*) = 0 FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 c8)" <<SQL
CALL clientes.registrar_validacion('C001', 'HUELLA', 'APROBADO', NULL, $(uuid_v11 c8), NULL, @i);
SQL
TARJETA_X218="UUID_TO_BIN('15000000-0000-4000-8000-0000000000d1')"
caso X218 'cambiar_estado_cliente no cambia el estado ni bloquea tarjetas si falla el evento (C1)' \
  "SELECT (SELECT estado_cliente FROM clientes.cliente WHERE cod_cliente = 'CX218') = 'ACTIVO'
      AND ($(estado "$TARJETA_X218" ACTIVA))
      AND (SELECT COUNT(*) FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = $TARJETA_X218 AND estado_nuevo = 'BLOQUEADA') = 0" <<'SQL'
CALL clientes.cambiar_estado_cliente('CX218', 'BLOQUEADO', 'Fraude', NULL, @a);
SQL
caso X219 'crear_usuario_servicio no deja la fila si falla el evento (C1)' \
  "SELECT COUNT(*) = 0 FROM core.usuario_sistema WHERE username = 'svc-x219'" <<'SQL'
CALL core.crear_usuario_servicio(UUID_TO_BIN(UUID()), 'svc-x219', 'S', 'CLIENTES', 'h', 'BCRYPT', 'v2', NULL);
SQL
caso X220 'renovar_credencial no cambia el hash si falla el evento (C1)' \
  "SELECT hash_password = 'h1' FROM core.usuario_sistema WHERE id_usuario = $SRV" <<SQL
CALL core.renovar_credencial($SRV, 'h2', 'BCRYPT', 'v2', NULL, @f);
SQL
caso X221 'cambiar_estado_usuario no desactiva si falla el evento (C1)' \
  "SELECT activo FROM core.usuario_sistema WHERE id_usuario = $SRV" <<SQL
CALL core.cambiar_estado_usuario($SRV, FALSE, NULL, @f);
SQL
# N2 para v1.1: dentro de la transacción de quien llama, solo se deshace lo propio.
caso X222 'registrar_cliente deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p222) AND (SELECT COUNT(*) FROM clientes.cliente WHERE numero_documento = '71000222') = 0
      AND (SELECT COUNT(*) FROM clientes.verificacion_captacion) = $vc" <<SQL
$(previo p222)
CALL clientes.registrar_cliente('DNI', '71000222', 'Prueba', 'Ficticio', NULL, 'c222@example.com', '961000222', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), NULL, @c);
COMMIT;
SQL
caso X223 'cambiar_estado_cliente deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p223) AND (SELECT estado_cliente FROM clientes.cliente WHERE cod_cliente = 'CX218') = 'ACTIVO'
      AND ($(estado "$TARJETA_X218" ACTIVA))" <<SQL
$(previo p223)
CALL clientes.cambiar_estado_cliente('CX218', 'BAJA', 'Baja', NULL, @a);
COMMIT;
SQL
caso X224 'verificar_documento deshace solo lo suyo dentro de una transacción (N2)' \
  "SELECT $(quedo p224) AND (SELECT COUNT(*) FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 c9)) = 0" <<SQL
$(previo p224)
CALL clientes.verificar_documento('DNI', '70000001', TRUE, NULL, $(uuid_v11 c9), NULL, @i, @r, @m, @j);
COMMIT;
SQL
# R3 para v1.1: el deadlock llega a quien llama y no queda nada.
deadlock_procedimiento X225 registrar_cliente "SELECT COUNT(*) = 0 FROM clientes.cliente WHERE numero_documento = '71000225'" \
  "CALL clientes.registrar_cliente('DNI', '71000225', 'Prueba', 'Ficticio', NULL, 'c225@example.com', '961000225', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c);"
deadlock_procedimiento X226 verificar_documento \
  "SELECT COUNT(*) = 0 FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 ca)" \
  "CALL clientes.verificar_documento('DNI', '70000001', TRUE, NULL, $(uuid_v11 ca), 'pruebas', @i, @r, @m, @j);"
deadlock_procedimiento X227 registrar_validacion \
  "SELECT COUNT(*) = 0 FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 cb)" \
  "CALL clientes.registrar_validacion('C001', 'FACIAL', 'APROBADO', NULL, $(uuid_v11 cb), 'pruebas', @i);"
deadlock_procedimiento X228 cambiar_estado_cliente \
  "SELECT (SELECT estado_cliente FROM clientes.cliente WHERE cod_cliente = 'CX218') = 'ACTIVO' AND ($(estado "$TARJETA_X218" ACTIVA))" \
  "CALL clientes.cambiar_estado_cliente('CX218', 'BLOQUEADO', 'x', 'pruebas', @a);"
deadlock_procedimiento X229 crear_usuario_servicio "SELECT COUNT(*) = 0 FROM core.usuario_sistema WHERE username = 'svc-x229'" \
  "CALL core.crear_usuario_servicio(UUID_TO_BIN(UUID()), 'svc-x229', 'S', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas');"
deadlock_procedimiento X230 renovar_credencial "SELECT hash_password = 'h1' FROM core.usuario_sistema WHERE id_usuario = $SRV" \
  "CALL core.renovar_credencial($SRV, 'h3', 'BCRYPT', 'v2', 'pruebas', @f);"
deadlock_procedimiento X231 cambiar_estado_usuario "SELECT activo FROM core.usuario_sistema WHERE id_usuario = $SRV" \
  "CALL core.cambiar_estado_usuario($SRV, FALSE, 'pruebas', @f);"
deadlock_procedimiento X232 registrar_login \
  "SELECT COUNT(*) = 0 FROM core.evento_auditoria WHERE accion = 'LOGIN' AND correlation_id = $(uuid_v11 cc)" \
  "CALL core.registrar_login($SRV, $(uuid_v11 cc));"
# Los procedimientos nuevos son solo de bna_api: bna_app, que conserva INSERT directo, no
# los ejecuta.
CLIENTE=app_ caso X233 'bna_app no ejecuta los procedimientos de clientes ni de usuarios de servicio (v1.1)' \
  "SELECT (SELECT COUNT(*) FROM clientes.cliente WHERE numero_documento = '71000233') = 0
      AND (SELECT COUNT(*) FROM clientes.validacion_identidad WHERE correlation_id = $(uuid_v11 cd)) = 0
      AND (SELECT COUNT(*) FROM core.usuario_sistema WHERE username = 'svc-x233') = 0
      AND (SELECT estado_cliente FROM clientes.cliente WHERE cod_cliente = 'CX218') = 'ACTIVO'
      AND (SELECT COUNT(*) FROM core.evento_auditoria WHERE accion = 'LOGIN' AND correlation_id = $(uuid_v11 cd)) = 0" <<SQL
CALL clientes.registrar_cliente('DNI', '71000233', 'Prueba', 'Ficticio', NULL, 'c233@example.com', '961000233', 'v1', 'HABILITADO', UUID_TO_BIN(UUID()), 'pruebas', @c);
CALL clientes.verificar_documento('DNI', '70000001', TRUE, NULL, $(uuid_v11 cd), 'pruebas', @i, @r, @m, @j);
CALL clientes.cambiar_estado_cliente('CX218', 'BLOQUEADO', 'x', 'pruebas', @a);
CALL core.crear_usuario_servicio(UUID_TO_BIN(UUID()), 'svc-x233', 'S', 'CLIENTES', 'h', 'BCRYPT', 'v2', 'pruebas');
CALL core.registrar_login($SRV, $(uuid_v11 cd));
SQL
