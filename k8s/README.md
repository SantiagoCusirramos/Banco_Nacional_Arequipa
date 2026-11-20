# Kubernetes

Manifiestos del producto integrado, con [kustomize](https://kustomize.io/).

| Carpeta | Qué contiene |
|---|---|
| `base/` | Namespace `bna`, y por cada servicio su Deployment y su Service: `db`, `coredb`, `cuentas`, `tarjetas`, `sol`, `evaluacion`, `desembolso`, `cobranza`, `captacion`, `seguridad`, `atm`, `billetera`, `bus` (Bus de Servicios) y `frontend`. Dos ConfigMap: `bna-configuracion` (las direcciones que usan los módulos, todas hacia el Bus) y `bna-bus` (las direcciones directas de los módulos, que solo lee el Bus) |
| `overlays/local/` | Ajustes para un clúster local de [kind](https://kind.sigs.k8s.io/): las imágenes cargadas en el clúster y, como NodePort, el frontend, el Bus, COREDB, CUENTAS, TARJETAS, SOL, Evaluación, Desembolso, CAPTACION y Seguridad. Las bases, COBRANZA, ATM y BILLETERA quedan solo dentro del clúster |
| `overlays/infraestructura/` | El clúster de Infraestructura (k3s): imágenes de ghcr.io, prefijo `bna-`, Ingress de Traefik y las claves sin objetos Secret (un PVC con el `.env` y un contenedor de inicio por pod). Guía: [`Documents/despliegue-infraestructura.md`](../Documents/despliegue-infraestructura.md) |
| `kind-config.yaml` | El clúster local, que publica esos NodePort en `127.0.0.1` |

## Desplegar en un clúster local

Requiere Docker, `kind` y `kubectl`. Desde la raíz del repositorio:

```bash
./bna k8s-up       # crea el clúster si falta, carga las imágenes y despliega
./bna k8s-smoke    # flujo de extremo a extremo dentro del clúster
./bna k8s-ps       # pods y servicios
./bna k8s-down     # elimina el clúster y la red de Docker `kind`, si nada más la usa
```

Al terminar, `./bna k8s-up` muestra las direcciones. Usan puertos distintos de los de `./bna up`, así que los dos pueden estar levantados a la vez:

| Servicio | Dirección |
|---|---|
| Frontend | http://localhost:13000 |
| Bus de Servicios | http://127.0.0.1:18018/docs |
| COREDB | http://127.0.0.1:18012/docs |
| CUENTAS | http://127.0.0.1:18001/docs |
| TARJETAS | http://127.0.0.1:18002/docs |
| SOL | http://127.0.0.1:18011/docs |
| Evaluación | http://localhost:13000/evaluacion (API: http://127.0.0.1:18015/docs) |
| Desembolso | http://localhost:13000/desembolso (API: http://127.0.0.1:18016/docs) |
| CAPTACION | http://127.0.0.1:18017/docs |
| Seguridad | http://127.0.0.1:18013 |
| COBRANZA | http://localhost:13000/pagar-cuota (la API, solo por el Bus: `/bus/cobranza`) |
| ATM, BILLETERA | Sin NodePort: por el Bus, `/bus/atm` y `/bus/billetera` |

`scripts/k8s.sh` solo usa el contexto `kind-bna`: no toca ningún otro clúster configurado en la máquina.

## Claves

**Ningún Secret está en el repositorio.** `./bna k8s-up` crea `bna-secretos` a partir del `.env` local (el mismo que genera `./bna up`) y lo aplica directo al clúster, sin escribirlo en un archivo. La CI falla si aparece un `kind: Secret` dentro de `k8s/`.

Para cambiar una clave: editarla en `.env`, volver a ejecutar `./bna k8s-up` y reiniciar el servicio que la usa (`kubectl --context kind-bna -n bna rollout restart deployment/<servicio>`). Las contraseñas de las bases solo se aplican al crear su volumen.

## Cómo está armado

- **Bases de datos:** Deployment con un PVC y estrategia `Recreate`. No es un StatefulSet para que la base sirva también en clústeres donde la cuenta no puede crearlos.
- **Arranque en orden:** COREDB y SOL esperan a su base con un contenedor de inicio. Otros contenedores de inicio crean el primer administrador de COREDB si no existe y los usuarios de servicio `svc-evaluacion`, `svc-desembolso`, `svc-captacion` (módulo CLIENTES), `svc-cobranza` y `svc-billetera`, cada uno con su secreto del Secret (`EVALUACION_COREDB_SECRETO`, `DESEMBOLSO_COREDB_SECRETO`, `CAPTACION_COREDB_SECRETO`, `COBRANZA_COREDB_SECRETO`, `BILLETERA_COREDB_SECRETO`), y preparan la base de SOL. CAPTACION, Evaluación, Desembolso, COBRANZA y BILLETERA esperan a que COREDB responda a través del Bus.
- **Sondas:** cada servicio tiene sonda de arranque, de disponibilidad y de vida. Las de vida de Evaluación, Desembolso y COBRANZA solo miran el puerto: su `/salud` depende de COREDB y no debe reiniciarlas si COREDB cae. Las de las bases leen la contraseña del entorno del contenedor, no de la línea de órdenes.
- **Bus de Servicios:** el frontend llega a los módulos y los módulos llegan a COREDB por el Service `bus`. En el ConfigMap `bna-configuracion`, `CORE_BASE_URL`, `COREDB_URL` y los `*_GATEWAY_URL` apuntan al Bus; cada Deployment presenta su credencial del Secret (`BUS_TOKEN_FRONTEND`, `BUS_TOKEN_CUENTAS`…), también los contenedores de arranque que esperan a COREDB. Las direcciones directas de los módulos están en otro ConfigMap, `bna-bus`, que solo lee el Bus. `./bna k8s-smoke` corre el flujo en el pod del Bus, que solo llama al Bus y al frontend y comprueba con las métricas del Bus que cada módulo llegó a COREDB por él. A diferencia de compose (redes `canales` y `core`), aquí no hay NetworkPolicy que impida una llamada directa: lo comprueban `scripts/comprobar_rutas_coredb.py` (ningún Deployment tiene la dirección directa de COREDB) y las métricas del Bus.
- **Límites:** cada contenedor declara CPU y memoria pedidas y máximas.
- **Sin root:** todos los contenedores corren con un usuario sin privilegios, sin escalamiento y sin capacidades.
- **Imágenes:** las mismas de `compose.yaml` (`bna/*:local`), construidas en la máquina y cargadas con `kind load`. Ninguna usa la etiqueta `latest`.

## Si algo falla

`./bna k8s-up` espera a cada servicio hasta 10 minutos (`BNA_ESPERA_SEGUNDOS`). Si uno no queda listo, muestra los pods, los últimos eventos y, de cada pod que no está listo, el final de sus registros y el motivo de su último reinicio. `scripts/k8s.sh diagnostico` muestra lo mismo en cualquier momento.

**Las bases no arrancan en Ubuntu con MySQL instalado.** El pod `db` se reinicia y su sonda responde `la zona del servidor es SYSTEM, no +00:00`; en los registros de su primera ejecución aparece `Can't connect to local MySQL server through socket '/var/run/mysqld/mysqld.sock'`. La causa es el perfil de AppArmor que el paquete de MySQL instala para `/usr/sbin/mysqld`: kind corre los pods sin perfil propio, así que el del anfitrión se aplica también al `mysqld` de los pods y le impide leer `/etc/my.cnf` ([problema conocido de kind](https://kind.sigs.k8s.io/docs/user/known-issues/#apparmor)). `./bna k8s-up` avisa si encuentra ese perfil. Para desactivarlo:

```bash
sudo ln -s /etc/apparmor.d/usr.sbin.mysqld /etc/apparmor.d/disable/
sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.mysqld
./bna k8s-down && ./bna k8s-up    # el volumen de la base quedó a medio cargar: hay que crearlo de nuevo
```

La CI hace lo mismo antes de desplegar. Con Docker Compose (`./bna up`) no ocurre, porque Docker pone su propio perfil a cada contenedor.

## Otro clúster

El clúster de Infraestructura tiene su overlay, `overlays/infraestructura/`, y su script, `scripts/k8s-infra.sh` (publicar las imágenes, aplicar, cargar los datos de referencia, correr el flujo de demostración y borrar). Allí la cuenta no puede crear Secrets: el `.env` vive en un PVC y cada pod copia a memoria solo sus claves. Todo está en [`Documents/despliegue-infraestructura.md`](../Documents/despliegue-infraestructura.md).

`overlays/infraestructura/secretos.yaml` se genera desde `base/` con `scripts/overlay_infraestructura.py`. Si cambia una clave (un `secretKeyRef`) en `base/`, hay que regenerarlo (`python3 scripts/overlay_infraestructura.py generar`); `./bna test` y la CI fallan mientras no esté al día. Una dirección interna nueva en `base/` también necesita su versión con prefijo en `overlays/infraestructura/direcciones.yaml`: `overlay_infraestructura.py revisar` lo detecta.

Para otro clúster donde sí se puedan crear Secrets basta un overlay sobre `base/` con de dónde descarga las imágenes, cómo se publican los servicios y el namespace, y el Secret creado desde un `.env` que no se versiona:

```bash
kubectl -n <namespace> create secret generic bna-secretos --from-env-file=.env
```
