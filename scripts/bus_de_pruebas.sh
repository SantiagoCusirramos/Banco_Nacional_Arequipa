# Bus de Servicios para las suites de integración de los módulos (fase 2): como en el producto,
# el módulo bajo prueba llega a COREDB a través del Bus, con su propia credencial, y las
# pruebas preparan sus datos en COREDB también por el Bus, con la credencial PRUEBAS.
#
# Uso, con `source` desde el script de la suite:
#   bus_de_pruebas_levantar <red> <contenedor> <imagen del backend> <URL de COREDB> <MÓDULO>
#     Arranca el Bus y espera a que responda. Deja definidas:
#       BUS_PRUEBAS_COREDB         dirección de COREDB a través del Bus
#       BUS_PRUEBAS_TOKEN_MODULO   credencial del módulo (su BUS_TOKEN)
#       BUS_PRUEBAS_TOKEN_PRUEBAS  credencial de las pruebas
#   bus_de_pruebas_comprobar <contenedor> <MÓDULO>
#     Falla si, según /metricas, el módulo no llegó a COREDB a través del Bus.
# Quien lo levanta lo elimina al terminar: docker rm -fv <contenedor>.

bus_de_pruebas_levantar() {
  local red="$1" nombre="$2" imagen="$3" coredb="$4" modulo="$5"
  BUS_PRUEBAS_TOKEN_MODULO="$(openssl rand -hex 24)"
  BUS_PRUEBAS_TOKEN_PRUEBAS="$(openssl rand -hex 24)"
  BUS_PRUEBAS_COREDB="http://$nombre:8018/bus/coredb"
  # El Bus exige la dirección de cada módulo; en estas suites solo existe COREDB.
  local ausente=http://modulo-ausente.invalid:9
  docker run -d --name "$nombre" --network "$red" \
    -e BUS_URL_COREDB="$coredb" \
    -e BUS_URL_CUENTAS="$ausente" -e BUS_URL_TARJETAS="$ausente" -e BUS_URL_CAPTACION="$ausente" \
    -e BUS_URL_SOL="$ausente" -e BUS_URL_EVALUACION="$ausente" -e BUS_URL_DESEMBOLSO="$ausente" \
    -e BUS_URL_SEGURIDAD="$ausente" \
    -e BUS_CONSUMIDORES="$modulo,PRUEBAS" \
    -e "BUS_TOKEN_$modulo=$BUS_PRUEBAS_TOKEN_MODULO" \
    -e BUS_TOKEN_PRUEBAS="$BUS_PRUEBAS_TOKEN_PRUEBAS" \
    "$imagen" uvicorn BUS_SERVICIOS.main:app --host 0.0.0.0 --port 8018 >/dev/null
  local _
  for _ in $(seq 1 60); do
    if docker exec "$nombre" python -c \
      'import urllib.request as u; u.urlopen("http://127.0.0.1:8018/salud", timeout=3)' >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "El Bus de pruebas no arrancó:" >&2
  docker logs --tail 30 "$nombre" >&2
  return 1
}

bus_de_pruebas_comprobar() {
  local nombre="$1" modulo="$2"
  docker exec -e TOKEN="$BUS_PRUEBAS_TOKEN_PRUEBAS" -e MODULO="$modulo" "$nombre" python -c '
import json, os, sys, urllib.request as u
pedido = u.Request("http://127.0.0.1:8018/metricas", headers={"X-Bus-Token": os.environ["TOKEN"]})
reenvios = json.load(u.urlopen(pedido, timeout=5))["reenvios"]
modulo = os.environ["MODULO"]
n = reenvios.get(modulo, {}).get("COREDB", 0)
if not n:
    sys.exit(f"{modulo} no llegó a COREDB a través del Bus: {reenvios}")
print(f"Bus de Servicios: {modulo} llegó a COREDB {n} veces a través del Bus.")
'
}
