# Base integrada del CORE con su esquema dentro de la imagen. El contexto de
# construcción es database/, que no se edita aquí (ver database/README-UPSTREAM.md).
# Los scripts de inicio solo corren sobre un volumen vacío.
ARG MYSQL_IMAGE=mysql:8.4@sha256:24989179f58856db763f418010c1169fecc944e3ec1ea7e921572d83eb070f70
FROM ${MYSQL_IMAGE}

# 1 carga los datos de desarrollo: periodos contables de 24 meses, una agencia,
# un terminal por canal, el BIN 004499 y el cliente DEV001. Sin ellos ningún
# movimiento se acepta. No usar 1 en producción.
ARG DATOS_DEV=1

COPY conf/mysql/bna.cnf /etc/mysql/conf.d/bna.cnf
COPY sql/bna_core.sql /docker-entrypoint-initdb.d/01_bna_core.sql
COPY sql/bna_extension.sql /docker-entrypoint-initdb.d/02_bna_extension.sql
COPY conf/mysql/crear_usuarios.sh /docker-entrypoint-initdb.d/03_crear_usuarios.sh
COPY sql/bna_datos_dev.sql /docker-entrypoint-initdb.d/04_bna_datos_dev.sql
# MySQL ignora un archivo de configuración escribible por todos.
RUN chmod 644 /etc/mysql/conf.d/bna.cnf /docker-entrypoint-initdb.d/* \
    && if [ "$DATOS_DEV" != "1" ]; then rm /docker-entrypoint-initdb.d/04_bna_datos_dev.sql; fi
