# Base auxiliar: MySQL con el script que crea sus usuarios. El contexto de
# construcción es docker/db-aux/. El esquema legado `bna` no va en la imagen:
# compose.yaml lo monta en /legado para el CORE legado y 01_bna_legada.sh lo carga sin
# imprimir sus filas de ejemplo.
ARG MYSQL_IMAGE=mysql:8.4@sha256:24989179f58856db763f418010c1169fecc944e3ec1ea7e921572d83eb070f70
FROM ${MYSQL_IMAGE}
COPY 01_bna_legada.sh 02_usuarios.sh /docker-entrypoint-initdb.d/
RUN chmod 644 /docker-entrypoint-initdb.d/01_bna_legada.sh /docker-entrypoint-initdb.d/02_usuarios.sh
