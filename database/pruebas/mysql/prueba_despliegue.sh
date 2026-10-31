#!/usr/bin/env bash
# Comprueba el despliegue con los mismos montajes que usa
# docker-compose.coredb.yml: arranca el contenedor con bna.cnf, el DDL, la
# extensión y crear_usuarios.sh, y revisa la configuración y los usuarios. bna.cnf se monta
# con permisos 666, como puede verse un montaje desde Windows: MySQL ignora un
# archivo de configuración escribible por todos, y el arranque debe evitarlo.
#
# También monta sql/bna_datos_dev.sql, como docker-compose.coredb.dev.yml, y
# comprueba que una base nueva puede abrir una cuenta y hacer un depósito.
#
# Uso: pruebas/mysql/prueba_despliegue.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
. "$ROOT/lib/comun.sh"
C="bna-prueba-despliegue-$$"
TMP="$(mktemp -d)"
PW_ROOT="raiz-$RANDOM"
# Comillas y barra invertida: crear_usuarios.sh debe escaparlas.
PW_APP="app'con\\raros-$RANDOM"
PW_ADMIN="admin-$RANDOM"
PW_SEGURIDAD="seguridad-$RANDOM"

cleanup() { docker rm -fv "$C" >/dev/null 2>&1 || true; rm -rf "$TMP"; }
trap cleanup EXIT

cp "$ROOT/conf/mysql/bna.cnf" "$TMP/bna.cnf"
chmod 666 "$TMP/bna.cnf"

docker run -d --name "$C" \
  -e MYSQL_ROOT_PASSWORD="$PW_ROOT" \
  -e CORE_DB_APP_PASSWORD="$PW_APP" \
  -e CORE_DB_ADMIN_PASSWORD="$PW_ADMIN" \
  -e CORE_DB_SEGURIDAD_PASSWORD="$PW_SEGURIDAD" \
  -v "$TMP/bna.cnf:/bna/bna.cnf:ro" \
  -v "$ROOT/sql/bna_core.sql:/docker-entrypoint-initdb.d/01_bna_core.sql:ro" \
  -v "$ROOT/sql/bna_extension.sql:/docker-entrypoint-initdb.d/02_bna_extension.sql:ro" \
  -v "$ROOT/conf/mysql/crear_usuarios.sh:/docker-entrypoint-initdb.d/03_crear_usuarios.sh:ro" \
  -v "$ROOT/sql/bna_datos_dev.sql:/docker-entrypoint-initdb.d/04_bna_datos_dev.sql:ro" \
  --entrypoint sh "$MYSQL_IMAGE" \
  -c 'install -m 644 /bna/bna.cnf /etc/mysql/conf.d/bna.cnf && exec docker-entrypoint.sh mysqld' >/dev/null

app() { docker exec -i -e MYSQL_PWD="$PW_APP" "$C" mysql -ubna_app_user -h127.0.0.1 --protocol=TCP -N "$@"; }

for _ in $(seq 1 90); do
  app -e 'SELECT 1' >/dev/null 2>&1 && break
  sleep 2
done

fallas=0
comprobar() { # DESCRIPCION ESPERADO OBTENIDO
  if printf '%s' "$3" | grep -q -- "$2"; then
    echo "ok    $1"
  else
    echo "FALLA $1: $3"
    fallas=$((fallas + 1))
  fi
}

comprobar 'configuración del servidor' 'BNA-CONFIGURACION: correcta' \
  "$(app -e 'CALL core.verificar_configuracion()' 2>&1 || true)"
comprobar 'rol de bna_app_user' 'bna_api' "$(app -e 'SELECT CURRENT_ROLE()' 2>&1 || true)"
comprobar 'extensión cargada' '^1$' \
  "$(app -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'core' AND table_name = 'usuario_sistema'" 2>&1 || true)"
comprobar 'bna_app_user no borra' 'denied' \
  "$(app -e 'DELETE FROM core.agencia' 2>&1 || true)"
for tabla in cuenta_ahorro titularidad movimiento; do
  comprobar "bna_app_user no inserta en cuentas.$tabla" 'denied' \
    "$(app -e "INSERT INTO cuentas.$tabla () VALUES ()" 2>&1 || true)"
done
comprobar 'bna_app_user no inserta en tarjetas.historial_estado_tarjeta' 'denied' \
  "$(app -e "INSERT INTO tarjetas.historial_estado_tarjeta () VALUES ()" 2>&1 || true)"
for tabla in tarjeta tarjeta_cuenta; do
  comprobar "bna_app_user no inserta en tarjetas.$tabla" 'denied' \
    "$(app -e "INSERT INTO tarjetas.$tabla () VALUES ()" 2>&1 || true)"
done
for tabla in tarjetas.credencial tarjetas.matriz_token tarjetas.matriz_coordenada tarjetas.token_pago \
             tarjetas.tarjeta clientes.biometria_cliente clientes.codigo_verificacion; do
  comprobar "bna_app_user no lee $tabla" 'denied' "$(app -e "SELECT 1 FROM $tabla LIMIT 1" 2>&1 || true)"
done
comprobar 'bna_app_user lee la vista de tarjetas' '^0$' "$(app -e 'SELECT COUNT(*) FROM tarjetas.v_tarjeta_api' 2>&1 || true)"
comprobar 'ninguna cuenta desplegada tiene bna_app' '^0$' \
  "$(docker exec -e MYSQL_PWD="$PW_ROOT" "$C" mysql -uroot -N \
     -e "SELECT COUNT(*) FROM mysql.role_edges WHERE FROM_USER = 'bna_app' AND TO_USER LIKE 'bna%user'" 2>&1 || true)"
comprobar 'bna_admin_user con su rol' 'bna_admin' \
  "$(docker exec -e MYSQL_PWD="$PW_ADMIN" "$C" mysql -ubna_admin_user -h127.0.0.1 --protocol=TCP -N \
     -e 'SELECT CURRENT_ROLE()' 2>&1 || true)"

comprobar 'depósito con los datos de desarrollo' '^100.00$' "$(app 2>&1 <<'SQL' || true
START TRANSACTION;
CALL cuentas.abrir_cuenta('CTA-DESPLIEGUE', '00000000000000000001', 'PEN', 'INDIVIDUAL', 'AQP01', JSON_ARRAY('DEV001'), 'despliegue');
CALL cuentas.registrar_movimiento('CTA-DESPLIEGUE', 'DEPOSITO', 100, 'Prueba', 'VEN', UUID_TO_BIN(UUID()), NULL, NULL, 'despliegue', @m, @r);
COMMIT;
SELECT saldo_contable FROM cuentas.cuenta_ahorro WHERE num_cuenta = 'CTA-DESPLIEGUE';
SQL
)"

seguridad() { docker exec -i -e MYSQL_PWD="$PW_SEGURIDAD" "$C" mysql -ubna_seguridad_user -h127.0.0.1 --protocol=TCP -N "$@"; }
comprobar 'rol de bna_seguridad_user' 'bna_seguridad' "$(seguridad -e 'SELECT CURRENT_ROLE()' 2>&1 || true)"
comprobar 'bna_app_user no desbloquea' 'denied' \
  "$(app -e "CALL tarjetas.desbloquear_tarjeta(UUID_TO_BIN(UUID()), 'x', 'x', @h)" 2>&1 || true)"
comprobar 'bna_seguridad_user solo ejecuta desbloquear_tarjeta' 'denied' \
  "$(seguridad -e "CALL cuentas.abrir_cuenta('X', '00000000000000000002', 'PEN', 'INDIVIDUAL', NULL, JSON_ARRAY('DEV001'), 'x')" 2>&1 || true)"
comprobar 'bna_seguridad_user llega al procedimiento' 'BNA-DESBLOQUEO' \
  "$(seguridad -e "CALL tarjetas.desbloquear_tarjeta(UUID_TO_BIN('11111111-1111-4111-8111-111111111111'), 'x', 'x', @h)" 2>&1 || true)"

# Los archivos se cargan con el cliente del contenedor, que sin SET NAMES los lee como latin1.
utf8() { app --default-character-set=utf8mb4 "$@"; }
root_despliegue() { docker exec -i -e MYSQL_PWD="$PW_ROOT" "$C" mysql -uroot --default-character-set=utf8mb4 "$@"; }
exacto() { # DESCRIPCION ESPERADO OBTENIDO
  if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FALLA $1: $3"; fallas=$((fallas + 1)); fi
}
exacto 'acento del DDL' 'Dólar estadounidense' "$(utf8 -e "SELECT nombre FROM core.moneda WHERE cod_moneda = 'USD'" 2>&1)"
exacto 'acento de la extensión' 'Depósitos de ahorro' \
  "$(root_despliegue -N -e "SELECT nombre FROM core.cuenta_contable WHERE codigo_contable = '2101'" 2>&1)"
exacto 'acento de los datos de desarrollo' 'Débito BNA física' \
  "$(root_despliegue -N -e "SELECT descripcion FROM tarjetas.bin_tarjeta WHERE bin = '004499'" 2>&1)"
comprobar 'acento en un mensaje de la extensión' 'un débito por ATM exige una autorización' \
  "$(utf8 -e "CALL cuentas.registrar_movimiento('CTA-DESPLIEGUE', 'RETIRO', 1, 'x', 'ATM', UUID_TO_BIN(UUID()), NULL, NULL, 'x', @m, @r)" 2>&1 || true)"
exacto 'rutinas y triggers cargados en utf8mb4' 0 "$(root_despliegue -N -e "
  SELECT (SELECT COUNT(*) FROM information_schema.routines
           WHERE routine_schema IN ('core', 'clientes', 'cuentas', 'tarjetas', 'creditos') AND character_set_client <> 'utf8mb4')
       + (SELECT COUNT(*) FROM information_schema.triggers
           WHERE trigger_schema IN ('core', 'clientes', 'cuentas', 'tarjetas', 'creditos') AND character_set_client <> 'utf8mb4')" 2>&1)"
exacto 'bna_app_user lee exactamente lecturas_api.txt' "$(cat "$HERE/lecturas_api.txt")" "$(lecturas_de root_despliegue utf8 2>&1 || true)"
exacto 'bna_api sin concesiones amplias' 0 "$(root_despliegue -N -e "$CONCESIONES_AMPLIAS_API" 2>&1)"

if [ "$fallas" -ne 0 ]; then
  docker logs "$C" 2>&1 | tail -20
  exit 1
fi
echo 'Despliegue correcto.'
