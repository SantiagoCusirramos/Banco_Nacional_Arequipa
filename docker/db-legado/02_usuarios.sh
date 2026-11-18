#!/bin/sh
# Usuarios de la base auxiliar, creados al inicializar el contenedor: el del CORE
# legado sobre `bna` y el de SOL sobre `bna_sol_mvp`. Las contraseñas vienen del
# entorno. No usa `set -e` porque el contenedor puede cargar este archivo con `source`.
: "${LEGADO_DB_PASSWORD:?Falta LEGADO_DB_PASSWORD}"
: "${SOL_DB_PASSWORD:?Falta SOL_DB_PASSWORD}"

cadena_sql() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"; }

MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -uroot <<SQL || exit 1
CREATE USER 'bna_user'@'%' IDENTIFIED BY '$(cadena_sql "$LEGADO_DB_PASSWORD")';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON bna.* TO 'bna_user'@'%';
CREATE USER 'sol_user'@'%' IDENTIFIED BY '$(cadena_sql "$SOL_DB_PASSWORD")';
-- SOL crea su base al iniciar (python -m SOL.manage init).
GRANT ALL PRIVILEGES ON \`bna\\_sol\\_mvp\`.* TO 'sol_user'@'%';
SQL
