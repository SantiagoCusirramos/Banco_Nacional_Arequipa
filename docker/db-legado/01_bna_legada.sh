# Esquema legado `bna` (CORE legado, perfil `legado`), montado por compose.yaml en /legado.
# Sus SELECT de verificación imprimen filas de ejemplo con documento, fecha de nacimiento,
# celular y correo: se carga sin escribir esa salida en el registro del contenedor (P-4).
# Los errores siguen saliendo por stderr y detienen el arranque.
if [ -f /legado/bna_legada.sql ]; then
  docker_process_sql < /legado/bna_legada.sql > /dev/null
fi
