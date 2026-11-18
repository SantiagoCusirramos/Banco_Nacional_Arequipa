#!/bin/sh
# Usuario de la base del CORE legado sobre `bna`, creado al inicializar el contenedor. La
# contraseña viene del entorno. No usa `set -e` porque el contenedor puede cargar este
# archivo con `source`.
: "${LEGADO_DB_PASSWORD:?Falta LEGADO_DB_PASSWORD}"

cadena_sql() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"; }

MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -uroot <<SQL || exit 1
CREATE USER 'bna_user'@'%' IDENTIFIED BY '$(cadena_sql "$LEGADO_DB_PASSWORD")';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON bna.* TO 'bna_user'@'%';
SQL
