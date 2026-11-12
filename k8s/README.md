# Kubernetes

Manifiestos del producto integrado, con [kustomize](https://kustomize.io/).

| Carpeta | Qué contiene |
|---|---|
| `base/` | Namespace `bna`, y por cada servicio su Deployment y su Service: `db`, `db-aux`, `coredb`, `cuentas`, `sol`, `seguridad` y `frontend`. Un ConfigMap con las direcciones internas |
| `overlays/local/` | Ajustes para un clúster local de [kind](https://kind.sigs.k8s.io/): cada servicio como NodePort y las imágenes cargadas en el clúster |
| `kind-config.yaml` | El clúster local, que publica esos NodePort en `127.0.0.1` |

## Desplegar en un clúster local

Requiere Docker, `kind` y `kubectl`. Desde la raíz del repositorio:

```bash
./bna k8s-up       # crea el clúster si falta, carga las imágenes y despliega
./bna k8s-smoke    # flujo de extremo a extremo dentro del clúster
./bna k8s-ps       # pods y servicios
./bna k8s-down     # elimina el clúster
```

Al terminar, `./bna k8s-up` muestra las direcciones. Usan puertos distintos de los de `./bna up`, así que los dos pueden estar levantados a la vez:

| Servicio | Dirección |
|---|---|
| Frontend | http://localhost:13000 |
| COREDB | http://127.0.0.1:18012/docs |
| CUENTAS | http://127.0.0.1:18001/docs |
| SOL | http://127.0.0.1:18011/docs |
| Seguridad | http://127.0.0.1:18013 |

`scripts/k8s.sh` solo usa el contexto `kind-bna`: no toca ningún otro clúster configurado en la máquina.

## Claves

**Ningún Secret está en el repositorio.** `./bna k8s-up` crea `bna-secretos` a partir del `.env` local (el mismo que genera `./bna up`) y lo aplica directo al clúster, sin escribirlo en un archivo. La CI falla si aparece un `kind: Secret` dentro de `k8s/`.

Para cambiar una clave: editarla en `.env`, volver a ejecutar `./bna k8s-up` y reiniciar el servicio que la usa (`kubectl --context kind-bna -n bna rollout restart deployment/<servicio>`). Las contraseñas de las bases solo se aplican al crear su volumen.

## Cómo está armado

- **Bases de datos:** Deployment con un PVC y estrategia `Recreate`. No es un StatefulSet para que la base sirva también en clústeres donde la cuenta no puede crearlos.
- **Arranque en orden:** COREDB y SOL esperan a su base con un contenedor de inicio. Otro contenedor de inicio crea el primer administrador de COREDB si no existe, y prepara la base de SOL.
- **Sondas:** cada servicio tiene sonda de arranque, de disponibilidad y de vida. Las de las bases leen la contraseña del entorno del contenedor, no de la línea de órdenes.
- **Límites:** cada contenedor declara CPU y memoria pedidas y máximas.
- **Sin root:** todos los contenedores corren con un usuario sin privilegios, sin escalamiento y sin capacidades.
- **Imágenes:** las mismas de `compose.yaml` (`bna/*:local`), construidas en la máquina y cargadas con `kind load`. Ninguna usa la etiqueta `latest`.

El CORE legado no se despliega aquí: ningún servicio lo usa. Sigue disponible con Docker Compose (`COMPOSE_PROFILES=legado ./bna up`).

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

Para un clúster que no sea kind hace falta un overlay propio sobre `base/` con tres cosas: de dónde descarga las imágenes (un registro al que el clúster llegue), cómo se publican los servicios (por ejemplo un Ingress) y el namespace. El Secret se crea igual, desde un `.env` que no se versiona:

```bash
kubectl -n <namespace> create secret generic bna-secretos --from-env-file=.env
```
