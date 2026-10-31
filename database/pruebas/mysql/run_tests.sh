#!/usr/bin/env bash
# Pruebas de la base integrada (sql/bna_core.sql) en MySQL 8.4.
# Corre en un contenedor temporal, con la configuración de conf/mysql/bna.cnf,
# que se elimina al terminar. Además de pruebas/mysql/pruebas.sql (con
# bna_app_user) y pruebas_admin.sql (con bna_admin_user), ejecuta:
#   L01 y L02  la carga del DDL y la configuración del servidor;
#   M20b, M20c el asiento descuadrado en un COMMIT real y el que falla fuera
#              de una transacción;
#   C01 a C03  la concurrencia, con dos sesiones;
#   pruebas_extension_api.sql con bna_api_user, el rol de la API desplegada;
#   G01 a G05  las brechas conocidas: cada prueba muestra que la brecha
#              existe (si alguna dejara de existir, la prueba falla).
# Todo corre con sql/bna_extension.sql cargado. Sus pruebas (ID X) quedan aparte,
# en resultados/mysql/resultado-extension.tsv, porque la extensión está fuera
# del modelo y de la matriz.
# Salidas en bruto y metadatos: resultados/mysql/; tablas del informe:
# informe/mysql-pruebas-*.tex.
#
# Uso: pruebas/mysql/run_tests.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
. "$ROOT/lib/comun.sh"
DDL_ORIGEN="sql/bna_core.sql en $(commit_actual)"
OUT="$ROOT/resultados/mysql"
rm -rf "$OUT"
mkdir -p "$OUT"
C="bna-pruebas-mysql-$$"

cleanup() { docker rm -fv "$C" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --name "$C" -e MYSQL_ALLOW_EMPTY_PASSWORD=1 \
  -v "$ROOT/conf/mysql/bna.cnf:/etc/mysql/conf.d/bna.cnf:ro" "$MYSQL_IMAGE" >/dev/null
# El servidor definitivo es el que escucha por TCP (el de inicialización no).
for _ in $(seq 1 90); do
  docker exec "$C" mysql -uroot -h127.0.0.1 --protocol=TCP -e 'SELECT 1' >/dev/null 2>&1 && break
  sleep 2
done

root_() { docker exec -i "$C" mysql -uroot --default-character-set=utf8mb4 "$@"; }
app_() { docker exec -i -e MYSQL_PWD=app "$C" mysql -ubna_app_user --default-character-set=utf8mb4 "$@"; }
api_() { docker exec -i -e MYSQL_PWD=api "$C" mysql -ubna_api_user --default-character-set=utf8mb4 "$@"; }
admin_() { docker exec -i -e MYSQL_PWD=admin "$C" mysql -ubna_admin_user --default-character-set=utf8mb4 "$@"; }
sql_str() { printf "'%s'" "$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g")"; }
# registrar ID USUARIO GRUPO REFERENCIA DESCRIPCION MECANISMO ESPERADO OBTENIDO OK(1|0)
registrar() {
  root_ -e "INSERT INTO prueba.resultado (id, usuario, grupo, referencia, descripcion, mecanismo, esperado, obtenido, ok)
    VALUES ($(sql_str "$1"), $(sql_str "$2"), $(sql_str "$3"), $(sql_str "$4"), $(sql_str "$5"), $(sql_str "$6"),
            $(sql_str "$7"), $(sql_str "$8"), $9)"
}
# rechazo_o MENSAJE SI_NO_HAY: «Rechazo: MENSAJE», o SI_NO_HAY si no hubo error
rechazo_o() { if [ -n "$1" ]; then echo "Rechazo: $1"; else echo "$2"; fi; }
# primer error de una salida del cliente mysql
error_de() { grep -m1 -oE '^ERROR [0-9]+ \([0-9A-Z]+\)( at line [0-9]+)?: .*' "$1" | sed -E 's/^ERROR [0-9]+ \([0-9A-Z]+\)( at line [0-9]+)?: //' || true; }

version="$(root_ -N -e "SELECT VERSION()")"
echo "== MySQL $version"

# L01: el script completo carga sin errores.
if root_ < "$ROOT/sql/bna_core.sql" > "$OUT/carga.log" 2>&1; then
  carga_ok=1; carga="Carga sin errores"
else
  carga_ok=0; carga="Error: $(error_de "$OUT/carga.log")"
fi
root_ < "$HERE/arnes.sql"
registrar L01 root Carga 'Script DDL' 'El script completo se ejecuta sobre una base vacía' declarativo \
  'Carga sin errores' "$carga" "$carga_ok"
[ "$carga_ok" = 1 ] || { echo "   la carga falló; ver $OUT/carga.log"; exit 1; }

# L02 (solo MySQL): el servidor tiene la configuración de la que dependen las
# reglas (modo estricto, UTC, zonas horarias, planificador de eventos).
l02="$(app_ -N -e "CALL core.verificar_configuracion()" 2>&1 || true)"
ok=0; echo "$l02" | grep -q 'BNA-CONFIGURACION: correcta' && ok=1
registrar L02 bna_app_user Carga 'Configuración del servidor' \
  'El servidor tiene modo estricto, zona UTC, zonas horarias y el planificador de eventos' procedimiento \
  'BNA-CONFIGURACION: correcta' "$(echo "$l02" | tail -1)" "$ok"

root_ < "$HERE/datos.sql"
root_ < "$ROOT/sql/bna_extension.sql"
root_ -e "INSERT INTO core.periodo_contable VALUES (2001, 1, '2001-01-01', '2001-01-31', 'CERRADO'),
                                                   (2002, 1, '2002-01-01', '2002-01-31', 'ABIERTO')"
root_ -e "CREATE USER 'bna_api_user'@'%' IDENTIFIED BY 'api' DEFAULT ROLE bna_api;
          GRANT EXECUTE ON prueba.* TO 'bna_api_user'@'%';
          GRANT INSERT ON prueba.resultado TO 'bna_api_user'@'%'"
root_ -e "CREATE TABLE prueba.cerrojo (id VARCHAR(10) PRIMARY KEY);
          GRANT INSERT ON prueba.cerrojo TO 'bna_api_user'@'%'"
app_ < "$HERE/pruebas.sql" > "$OUT/pruebas-app.log" 2>&1
app_ < "$HERE/pruebas_extension.sql" > "$OUT/pruebas-extension-app.log" 2>&1
api_ < "$HERE/pruebas_extension_api.sql" > "$OUT/pruebas-extension-api.log" 2>&1
admin_ < "$HERE/pruebas_admin.sql" > "$OUT/pruebas-admin.log" 2>&1
admin_ < "$HERE/pruebas_extension_admin.sql" > "$OUT/pruebas-extension-admin.log" 2>&1

# M20b: el asiento descuadrado se rechaza aunque la sesión confirme después.
app_ --force > "$OUT/M20b.log" 2>&1 <<'SQL' || true
START TRANSACTION;
CALL core.registrar_asiento(UUID_TO_BIN('9a000000-0000-4000-8000-000000000002'), 'T-COMMIT', CURRENT_DATE, CURRENT_DATE,
  'Solo debe', 'PEN', core.uuid_v4(), NULL, JSON_ARRAY(JSON_OBJECT('partida', 'DEBE', 'importe', 100, 'cuenta', '1101')), @a);
COMMIT;
SQL
quedo="$(root_ -N -e "SELECT count(*) FROM core.asiento_contable WHERE numero_asiento = 'T-COMMIT'")"
msg="$(error_de "$OUT/M20b.log")"
ok=0; [[ "$msg" == BNA-PARTIDA-DOBLE* ]] && [ "$quedo" = 0 ] && ok=1
registrar M20b bna_app_user MySQL 'Comprobación 20 (bug 7)' 'Un asiento descuadrado se rechaza en un COMMIT real' procedimiento \
  'Rechazo: BNA-PARTIDA-DOBLE; asientos guardados: 0' "$(rechazo_o "$msg" 'COMMIT aceptado'); asientos guardados: $quedo" "$ok"

# M20c (solo MySQL): fuera de una transacción, si una línea falla al
# insertarse (cuenta contable inexistente), no queda la cabecera sola.
app_ > "$OUT/M20c.log" 2>&1 <<'SQL' || true
CALL core.registrar_asiento(UUID_TO_BIN('9a000000-0000-4000-8000-000000000004'), 'T-AUTO', CURRENT_DATE, CURRENT_DATE,
  'Línea sin cuenta', 'PEN', core.uuid_v4(), NULL,
  JSON_ARRAY(JSON_OBJECT('partida', 'DEBE', 'importe', 100, 'cuenta', '1101'),
             JSON_OBJECT('partida', 'HABER', 'importe', 100, 'cuenta', '9999')), @a);
SQL
quedo="$(root_ -N -e "SELECT count(*) FROM core.asiento_contable WHERE numero_asiento = 'T-AUTO'")"
msg="$(error_de "$OUT/M20c.log")"
ok=0; echo "$msg" | grep -q 'foreign key constraint fails' && [ "$quedo" = 0 ] && ok=1
registrar M20c bna_app_user MySQL 'Comprobación 20 (bug 7)' \
  'Fuera de una transacción, un asiento cuya línea falla no deja la cabecera sola' procedimiento \
  'Rechazo: foreign key constraint fails; asientos guardados: 0' \
  "$(rechazo_o "$msg" aceptado); asientos guardados: $quedo" "$ok"

# Pruebas de concurrencia: la sesión A ejecuta SQL_A dentro de una
# transacción que espera 2 s antes de confirmar; la sesión B ejecuta SQL_B
# un segundo después. B debe rechazarse con PATRON y el estado final debe
# cumplir COND (consulta que devuelve 1).
# concurrente ID REF DESC SQL_A SQL_B PATRON COND ESPERADO OBTENIDO_SQL
concurrente() {
  local id="$1" ref="$2" desc="$3" sql_a="$4" sql_b="$5" patron="$6" cond="$7" esperado="$8" obt_sql="$9"
  printf 'START TRANSACTION;\n%s;\nDO SLEEP(2);\nCOMMIT;\n' "$sql_a" | app_ > "$OUT/$id-a.log" 2>&1 &
  sleep 1
  printf 'START TRANSACTION;\n%s;\nCOMMIT;\n' "$sql_b" | app_ > "$OUT/$id-b.log" 2>&1 || true
  wait
  local ok=0 estado b
  estado="$(root_ -N -e "$obt_sql")"
  b="$(error_de "$OUT/$id-b.log" | grep -oE "($patron)[^(]*" | head -1 || true)"
  if [ -n "$b" ] && [ "$(root_ -N -e "$cond")" = 1 ]; then ok=1; fi
  registrar "$id" bna_app_user Concurrencia "$ref" "$desc" trigger "$esperado" "$estado; segunda operación: ${b:-aceptada}" "$ok"
}

# C01: dos retiros de 3000 sobre un saldo de 5000, en ventanilla (sin tope).
concurrente C01 'Requisito 3 (E7)' 'Dos retiros simultáneos no dejan el saldo en negativo' \
  "CALL prueba.movimiento('CTA-PEN-2', 'RETIRO', 3000, 'VEN', NULL, NULL, @m)" \
  "CALL prueba.movimiento('CTA-PEN-2', 'RETIRO', 3000, 'VEN', NULL, NULL, @m)" \
  'BNA-SALDO' \
  "SELECT saldo_contable = 2000 FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2'" \
  'saldo 2000.00; segunda operación: BNA-SALDO' \
  "SELECT CONCAT('saldo ', saldo_contable) FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-PEN-2'"

# C02: dos retiros de 1000 en cajero (tope 1500 PEN): cada uno cabe solo,
# juntos no.
concurrente C02 'RN-TOP-001 (bug 5)' 'Dos retiros simultáneos en cajero no superan juntos el tope diario' \
  "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 1000, 'ATM', NULL, NULL, @m)" \
  "CALL prueba.movimiento('CTA-PEN-1', 'RETIRO', 1000, 'ATM', NULL, NULL, @m)" \
  'RN-TOP-001' \
  "SELECT monto_acumulado = 1000 FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'" \
  'consumido 1000.00; segunda operación: RN-TOP-001' \
  "SELECT CONCAT('consumido ', coalesce((SELECT monto_acumulado FROM core.consumo_diario WHERE num_cuenta = 'CTA-PEN-1' AND id_canal = 'ATM'), '0.00'))"

# C03: dos autorizaciones de 300 en cajero sobre la cuenta en dólares (tope
# 500 USD), sin movimiento todavía: cada una cabe sola, juntas no.
concurrente C03 'RN-TOP-001 (bug 5)' 'Dos autorizaciones simultáneas sin movimiento no superan juntas el tope diario' \
  "INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta) VALUES ('RETIRO', 300, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-USD-1')" \
  "INSERT INTO tarjetas.autorizacion (tipo_operacion, monto, estado_autorizacion, id_terminal, id_tarjeta, num_cuenta) VALUES ('RETIRO', 300, 'AUTORIZADA', 'ATM-AQP-001', UUID_TO_BIN('a0000000-0000-4000-8000-000000000001'), 'CTA-USD-1')" \
  'ERR-TAR-007' \
  "SELECT count(*) = 1 FROM tarjetas.autorizacion WHERE num_cuenta = 'CTA-USD-1' AND estado_autorizacion = 'AUTORIZADA'" \
  'autorizadas 1; segunda operación: ERR-TAR-007' \
  "SELECT CONCAT('autorizadas ', count(*)) FROM tarjetas.autorizacion WHERE num_cuenta = 'CTA-USD-1' AND estado_autorizacion = 'AUTORIZADA'"

# --- Brechas conocidas (solo MySQL). Cada una deja la base como estaba,
# salvo G03, que va al final.
# brecha ID USUARIO REF DESC ESPERADO VALOR_QUE_LA_CONFIRMA OBTENIDO_PREFIJO <<SQL
brecha() {
  local id="$1" usuario="$2" ref="$3" desc="$4" esperado="$5" confirma="$6" prefijo="$7" salida ok=0
  case "$usuario" in
    bna_app_user) salida="$(app_ -N 2>&1 || true)" ;;
    bna_admin_user) salida="$(admin_ -N 2>&1 || true)" ;;
  esac
  echo "$salida" > "$OUT/$id.log"
  salida="$(echo "$salida" | tail -1)"
  [ "$salida" = "$confirma" ] && ok=1
  registrar "$id" "$usuario" Brecha "$ref" "$desc" brecha "$esperado" "$prefijo$salida" "$ok"
}

brecha G01 bna_app_user 'sql_mode de la sesión' \
  'Una sesión que quita el modo estricto guarda un texto truncado sin error' \
  'Brecha: actor de 60 caracteres guardado con 40, sin error' 40 'actor de 60 caracteres guardado con ' <<'SQL'
SET SESSION sql_mode = '';
START TRANSACTION;
INSERT INTO creditos.evento_auditoria (modulo_emisor, id_entidad, accion, actor, correlation_id)
VALUES (13, 'e0000000-0000-4000-8000-000000000001', 'G01', REPEAT('x', 60), core.uuid_v4());
SELECT CHAR_LENGTH(actor) FROM creditos.evento_auditoria WHERE accion = 'G01';
ROLLBACK;
SQL

brecha G02 bna_app_user 'foreign_key_checks de la sesión' \
  'Una sesión que apaga foreign_key_checks guarda una referencia a una cuenta inexistente' \
  'Brecha: 1 fila huérfana guardada' 1 'filas huérfanas guardadas: ' <<'SQL'
SET SESSION foreign_key_checks = 0;
START TRANSACTION;
INSERT INTO tarjetas.tarjeta_cuenta (id_tarjeta, num_cuenta) VALUES (UUID_TO_BIN('a0000000-0000-4000-8000-000000000003'), 'NO-EXISTE');
SELECT count(*) FROM tarjetas.tarjeta_cuenta WHERE num_cuenta = 'NO-EXISTE';
ROLLBACK;
SQL

brecha G04 bna_admin_user 'Partida doble (CORE)' \
  'Una cuenta con INSERT directo registra un asiento descuadrado; solo la vista de control lo muestra' \
  'Brecha: aceptado; v_asientos_descuadrados: 1' 1 'aceptado; v_asientos_descuadrados: ' <<'SQL'
START TRANSACTION;
INSERT INTO core.asiento_contable (id_asiento, numero_asiento, fecha_contable, fecha_valor, glosa, moneda, correlation_id)
VALUES (UUID_TO_BIN('9a000000-0000-4000-8000-000000000005'), 'T-G04', CURRENT_DATE, CURRENT_DATE, 'Solo debe', 'PEN', core.uuid_v4());
INSERT INTO core.detalle_asiento VALUES (UUID_TO_BIN('9a000000-0000-4000-8000-000000000005'), 1, 'DEBE', 100, '1101');
SELECT count(*) FROM core.v_asientos_descuadrados WHERE numero_asiento = 'T-G04';
ROLLBACK;
SQL

brecha G05 bna_app_user 'Marcas de tiempo en UTC' \
  'Una sesión con otra zona horaria guarda una hora local como si fuera UTC' \
  'Brecha: la marca guardada difiere 5 h de UTC' 5 'diferencia con UTC (h): ' <<'SQL'
SET SESSION time_zone = '-05:00';
START TRANSACTION;
INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta, fecha_hora)
VALUES ('PIN_ATM', 'ATM-AQP-001', 'EXITOSO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'), NOW(6));
SELECT ROUND(TIMESTAMPDIFF(MINUTE, fecha_hora, UTC_TIMESTAMP(6)) / 60) FROM tarjetas.intento_autenticacion
 ORDER BY id_intento DESC LIMIT 1;
ROLLBACK;
SQL

# G03, al final porque TRUNCATE confirma y no se deshace.
brecha G03 bna_admin_user 'Bitácoras de solo inserción' \
  'Una cuenta con DROP (bna_admin) vacía una bitácora con TRUNCATE; ningún trigger lo impide' \
  'Brecha: intentos después de TRUNCATE: 0' 0 'intentos después de TRUNCATE: ' <<'SQL'
INSERT INTO tarjetas.intento_autenticacion (tipo_credencial, id_terminal, resultado, id_tarjeta)
VALUES ('PIN_ATM', 'ATM-AQP-001', 'EXITOSO', UUID_TO_BIN('a0000000-0000-4000-8000-000000000002'));
TRUNCATE TABLE tarjetas.intento_autenticacion;
SELECT count(*) FROM tarjetas.intento_autenticacion;
SQL

# shellcheck source=pruebas_sin_transaccion.sh
. "$HERE/pruebas_sin_transaccion.sh"

root_ -N -B -e "SELECT id, usuario, grupo, referencia, descripcion, mecanismo, esperado, obtenido,
                       CASE WHEN ok IS NULL THEN 'N/A' WHEN ok THEN 'pasa' ELSE 'falla' END
                  FROM prueba.resultado WHERE id NOT LIKE 'X%' ORDER BY n" > "$OUT/resultado.tsv"
root_ -N -B -e "SELECT id, usuario, descripcion, CASE WHEN ok THEN 'pasa' ELSE 'falla' END
                  FROM prueba.resultado WHERE id LIKE 'X%' ORDER BY n" > "$OUT/resultado-extension.tsv"
modo="$(root_ -N -e "SELECT @@GLOBAL.sql_mode")"
zona="$(root_ -N -e "SELECT @@GLOBAL.time_zone")"
coll="$(root_ -N -e "SELECT DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = 'core'")"
ev="$(root_ -N -e "SELECT @@GLOBAL.event_scheduler")"
iso="$(root_ -N -e "SELECT @@GLOBAL.transaction_isolation")"
metadatos "$OUT/metadatos.txt" "ddl=$DDL_ORIGEN" "mysql=$version" "imagen=$MYSQL_IMAGE" \
  "sql_mode=$modo" "time_zone=$zona" "collation=$coll" "event_scheduler=$ev" "aislamiento=$iso" \
  "extension=sql/bna_extension.sql"
python3 -I "$HERE/combinar.py" "$OUT" "$ROOT/informe" "$version"
"$HERE/prueba_revisar_resultados.sh" >/dev/null
"$HERE/revisar_resultados.sh" "$OUT"
echo "   Extensión: $(grep -c 'pasa$' "$OUT/resultado-extension.tsv") pasan"
