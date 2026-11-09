#!/bin/sh
# Crea los usuarios de la aplicación, de administración y de Seguridad al inicializar el
# contenedor (/docker-entrypoint-initdb.d, después de los SQL). Las
# contraseñas vienen del entorno: ninguna se guarda en el repositorio. No usa
# `set -e` porque el contenedor puede cargar este archivo con `source`.
: "${CORE_DB_APP_PASSWORD:?Falta CORE_DB_APP_PASSWORD}"
: "${CORE_DB_ADMIN_PASSWORD:?Falta CORE_DB_ADMIN_PASSWORD}"
: "${CORE_DB_SEGURIDAD_PASSWORD:?Falta CORE_DB_SEGURIDAD_PASSWORD}"

cadena_sql() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"; }

MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -uroot <<SQL || exit 1
CREATE USER 'bna_app_user'@'%' IDENTIFIED BY '$(cadena_sql "$CORE_DB_APP_PASSWORD")' DEFAULT ROLE bna_api;
CREATE USER 'bna_admin_user'@'%' IDENTIFIED BY '$(cadena_sql "$CORE_DB_ADMIN_PASSWORD")' DEFAULT ROLE bna_admin;
CREATE USER 'bna_seguridad_user'@'%' IDENTIFIED BY '$(cadena_sql "$CORE_DB_SEGURIDAD_PASSWORD")' DEFAULT ROLE bna_seguridad;
SQL
