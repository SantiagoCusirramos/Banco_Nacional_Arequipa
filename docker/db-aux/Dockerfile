# Base auxiliar: MySQL con el script que crea sus usuarios. El contexto de
# construcción es docker/db-aux/. El esquema legado `bna` no va en la imagen:
# compose.yaml lo monta para el CORE legado.
ARG MYSQL_IMAGE=mysql:8.4@sha256:24989179f58856db763f418010c1169fecc944e3ec1ea7e921572d83eb070f70
FROM ${MYSQL_IMAGE}
COPY 02_usuarios.sh /docker-entrypoint-initdb.d/02_usuarios.sh
RUN chmod 644 /docker-entrypoint-initdb.d/02_usuarios.sh
