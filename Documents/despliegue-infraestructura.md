# Despliegue en el clúster de Infraestructura

Cómo se despliega el producto integrado en el clúster Kubernetes de Infraestructura: el overlay [`k8s/overlays/infraestructura`](../k8s/overlays/infraestructura/) sobre `k8s/base` y el script [`scripts/k8s-infra.sh`](../scripts/k8s-infra.sh). El despliegue local con kind (`./bna k8s-up`, `k8s/overlays/local`) no cambia.

Este documento no tiene ninguna clave. El kubeconfig y el acceso al clúster los entrega Infraestructura y se guardan fuera del repositorio. El namespace asignado tampoco está en el repositorio: se pasa en `BNA_NAMESPACE`.

## El clúster

| Tema | Valor |
|---|---|
| Kubernetes | k3s 1.34. Use un `kubectl` 1.34 |
| Ingress | Traefik, en 172.16.10.31, solo HTTP |
| Almacenamiento | StorageClass `local-path` (un solo nodo; los datos quedan en su disco) |
| Cuota | Ninguna de CPU ni de memoria (comprobado el 2026-11-20). Si aparece una cuota por número de objetos, ver «Si hay cuota de objetos» |
| Permisos de la cuenta | En su namespace: ConfigMap, Deployment, Service, Ingress, Job, PVC y Pod (con `exec`, `logs` y `port-forward`). **No** puede leer ni crear Secrets, ni ver eventos, ni crear namespaces |
| Ya existen en el namespace | `backend` y `mysql` (Deployment, Service, PVC `mysql-data` e Ingress `backend`). El producto no los toca: todos sus objetos se llaman `bna-*` |

## Qué se despliega

| Objeto | Para qué |
|---|---|
| 14 Deployment y 14 Service `bna-*` | Los mismos servicios de `k8s/base`: `bna-db`, `bna-coredb`, `bna-bus`, `bna-cuentas`, `bna-tarjetas`, `bna-sol`, `bna-evaluacion`, `bna-desembolso`, `bna-cobranza`, `bna-captacion`, `bna-seguridad`, `bna-atm`, `bna-billetera`, `bna-frontend` |
| PVC `bna-db-datos` (1Gi, `local-path`) | La base integrada |
| PVC `bna-secretos` (1Mi, `local-path`) | El `.env` del clúster (ver «Claves sin Secrets») |
| Job `bna-arranque` | Crea ese `.env` si no existe |
| ConfigMap `bna-configuracion`, `bna-bus` | Las direcciones internas, como en `k8s/base`, hacia los Services con prefijo (`http://bna-bus:8018/…`) |
| ConfigMap `bna-scripts-secretos`, `bna-generar-env` | Los scripts del Job y del copiador de claves, `scripts/generar_env.sh` y `.env.example`. Ninguno tiene claves |
| Ingress `bna-web` | La publicación por Traefik |

Todos llevan la etiqueta `app.kubernetes.io/instance=bna` (también en los selectores), que es la que usan `estado` y `borrar`.

Recursos: cada servicio pide 50m de CPU y 128Mi de memoria; la base, 50m y 256Mi, con un máximo de 512Mi. Los máximos de los demás son los de `k8s/base`.

Imágenes: `ghcr.io/miguelpro324/bna-core-db`, `bna-coredb`, `bna-backend`, `bna-sol`, `bna-seguridad`, `bna-billetera` y `bna-frontend`, etiquetadas con el commit (12 caracteres), públicas. Son las mismas que construye `docker compose build`; ninguna lleva `.env`. La de la base incluye los datos de desarrollo (`DATOS_DEV=1`): sirve para demostraciones, no para producción.

## Direcciones

| Dirección | Qué |
|---|---|
| http://bna.172.16.10.31.sslip.io | Portal (frontend), con `/login`, las pantallas de cada módulo y el Home Banking en `/homebanking/` |
| http://bna-cajero.172.16.10.31.sslip.io | Pantalla del cajero (ATM) |
| http://bna-billetera.172.16.10.31.sslip.io | API de la billetera (Chaski), en `/api` |
| http://bna-bus.172.16.10.31.sslip.io | Bus de Servicios (`/docs`). Cada ruta `/bus/…` exige la cabecera `X-Bus-Token` |

sslip.io resuelve `<nombre>.172.16.10.31.sslip.io` a 172.16.10.31, así que no hace falta un DNS propio. Hace falta llegar a esa dirección (la red de Infraestructura).

## Claves sin Secrets

La cuenta no puede crear Secrets, así que el overlay no usa ninguno: la CI falla si aparece un `kind: Secret` o un `secretKeyRef` en lo que genera.

1. **El Job `bna-arranque`** monta el PVC `bna-secretos` y, si no hay `.env`, lo crea con `scripts/generar_env.sh` (valores al azar) como archivo 0600 del usuario 10001. Si ya existe, solo le agrega las claves que `.env.example` tenga y él no; **nunca cambia un valor**, así que volver a aplicar no rota ninguna clave.
2. **Cada Deployment** tiene un primer contenedor de inicio, `secretos`, que monta el PVC en solo lectura y copia a un `emptyDir` en memoria (`/secretos`) **solo las claves que usa ese pod**, un archivo por contenedor (`/secretos/env` para el principal), 0440 y del grupo del pod. Espera hasta 5 minutos a que el Job deje el `.env`, y falla con un mensaje claro si le falta una clave.
3. **Cada contenedor** que usaba una clave ya no la recibe del Secret: arranca con `sh -c 'set -a; . /secretos/env; set +a; exec <su orden>'`. Los módulos reciben las mismas variables que con el Secret y su código no cambia. Las sondas de la base cargan el archivo del mismo modo.

Qué claves recibe cada pod lo dice `k8s/overlays/infraestructura/secretos.yaml` (variable `BNA_CLAVES` de cada contenedor `secretos`: archivo, variable y clave del `.env`). Ese archivo lo genera `scripts/overlay_infraestructura.py` a partir de los `secretKeyRef` de `k8s/base`. Si alguien agrega una clave a la base, la CI y `./bna test` fallan hasta que se regenere:

```bash
python3 scripts/overlay_infraestructura.py generar
```

### Limitaciones

- **Un solo nodo.** El PVC `bna-secretos` es `ReadWriteOnce` y lo montan el Job y el contenedor de inicio de cada pod: funciona porque todos corren en el mismo nodo. Con varios nodos, los pods de otro nodo no podrían montarlo. `local-path` también ata la base a ese nodo.
- **El `.env` está en claro en el disco del nodo** (la carpeta de `local-path`). Lo puede leer quien administre el nodo y cualquiera con permiso para crear pods en el namespace (podría montar el PVC). Con Secrets pasa algo parecido (k3s los guarda sin cifrar salvo que se active el cifrado), pero se pueden restringir por RBAC aparte de los pods.
- Dentro de los pods las claves están en memoria (`emptyDir` de tipo `Memory`) y en el entorno del proceso, igual que con un Secret leído como variable.
- El pod de COREDB ve los archivos de sus contenedores de inicio (los secretos de los usuarios de servicio que crea), además de los suyos.
- **Rotar una clave** es manual: borrar su línea del `.env` del PVC (con un pod temporal que monte `bna-secretos`), volver a aplicar (el Job la genera de nuevo) y reiniciar los Deployments que la usan (`kubectl rollout restart deployment/bna-<servicio>`). Las contraseñas de la base solo se aplican al crear su volumen: cambiarlas exige además `ALTER USER` en la base.
- **Borrar el PVC `bna-secretos` sin borrar la base** deja a COREDB sin poder entrar (el Job generaría claves nuevas). `borrar` quita los dos juntos.
- No hay respaldo del `.env` ni de la base.

### La alternativa con Secrets

Si Infraestructura da permiso sobre Secrets (y, mejor, activa el cifrado de Secrets de k3s), se usaría el esquema de `k8s/base` tal cual: un overlay sin `secretos.yaml`, `arranque.yaml` ni el PVC `bna-secretos`, y el Secret creado desde un `.env` guardado fuera del repositorio:

```bash
kubectl -n "$BNA_NAMESPACE" create secret generic bna-secretos --from-env-file=.env
```

Así cada clave se restringe por RBAC, no depende de un solo nodo y se rota con `kubectl create secret … --dry-run=client -o yaml | kubectl apply -f -` más un reinicio. Un gestor externo (Sealed Secrets, External Secrets) también necesita que lo instale quien administra el clúster.

## Pasos

Requisitos: Docker, git, Python 3.9+, un `kubectl` 1.34, el kubeconfig del clúster y acceso a su red.

```bash
export KUBECONFIG=/ruta/al/kubeconfig     # el que entrega Infraestructura; el script no usa ~/.kube/config
export BNA_NAMESPACE=<namespace asignado>
```

`scripts/k8s-infra.sh` exige las dos variables y solo usa ese namespace.

### 1. Publicar las imágenes

Con `docker login ghcr.io` hecho y el árbol de git limpio (la etiqueta es el commit):

```bash
scripts/k8s-infra.sh publicar     # docker compose build, etiqueta ghcr.io/miguelpro324/bna-*:<commit> y push
scripts/k8s-infra.sh imagenes     # las siete, con su etiqueta
```

La primera vez, marcar los siete paquetes como públicos en GitHub (Packages → cada `bna-*` → Package settings → Change visibility). Si quedan privados, el clúster no puede descargarlos (haría falta un `imagePullSecret`, y la cuenta no puede crear Secrets).

### 2. Aplicar

```bash
scripts/k8s-infra.sh manifiestos > /tmp/bna.yaml   # opcional: revisar lo que se aplicará
scripts/k8s-infra.sh aplicar
```

`aplicar` arma el overlay con el namespace, la etiqueta del commit y el ConfigMap `bna-generar-env`, comprueba que no haya Secrets ni direcciones sin prefijo, reemplaza el Job `bna-arranque` (la plantilla de un Job no se puede cambiar), espera a que termine y a cada Deployment (hasta 10 minutos cada uno, `BNA_ESPERA_SEGUNDOS`) y muestra las direcciones. Si algo no queda listo, muestra el estado y los registros de los pods que fallan. Se puede repetir: no cambia las claves ni los datos.

### 3. Datos de referencia

```bash
scripts/k8s-infra.sh datos
```

La imagen de la base ya los carga al crear su volumen (`database/sql/bna_datos_dev.sql`). `datos` los completa con `INSERT IGNORE` (se puede repetir) y comprueba que estén: periodo contable del mes abierto (y los 23 siguientes), BIN 004499, agencia `AQP01`, terminales `DEV-*` y el cajero de desarrollo `DEV-ATM-01` activo. La clave de root no sale del pod de la base.

### 4. Flujo de demostración

```bash
scripts/k8s-infra.sh flujo        # scripts/flujo_demo.py contra http://bna… y http://bna-bus…
```

Es el flujo de [`flujo-demo.md`](flujo-demo.md), con las mismas comprobaciones. Sin `.env` local: `flujo_demo.py` lee con `kubectl exec` las tres claves que necesita (`BUS_TOKEN_PRUEBAS` del pod del Bus; el usuario y la clave del administrador, del archivo `primer-administrador` del pod de COREDB) y no imprime ninguna. Sale con 0 si todo pasó. Para usar otras direcciones (por ejemplo, un `kubectl port-forward`): `BNA_FRONTEND` y `BNA_BUS`.

Para entrar al portal como administrador hace falta su clave:

```bash
kubectl -n "$BNA_NAMESPACE" exec deployment/bna-coredb -c coredb -- \
  sh -c '. /secretos/primer-administrador; echo "$BNA_ADMIN_USUARIO / $CORE_DB_ADMIN_INICIAL_PASSWORD"'
```

### 5. Estado y problemas

```bash
scripts/k8s-infra.sh estado        # pods, servicios, Ingress, PVC y Jobs del producto
scripts/k8s-infra.sh diagnostico   # además, registros y motivo de reinicio de los pods que no están listos
```

La cuenta no ve eventos: lo que diría un evento (una imagen que no se descarga, un PVC sin enlazar) aparece en el estado del pod (`ImagePullBackOff`, `Pending`).

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `ImagePullBackOff` | Las imágenes no están publicadas con esa etiqueta, o son privadas | `scripts/k8s-infra.sh publicar` con el mismo commit; marcarlas públicas |
| `Init:Error` en `secretos`, «Falta X en el .env» | Se agregó una clave a `.env.example` y el Job no corrió después | `scripts/k8s-infra.sh aplicar` (el Job la agrega) |
| `Init:Error` en `secretos`, «No apareció el .env» | El Job falló | `kubectl logs job/bna-arranque` |
| COREDB no entra a la base | Se borró `bna-secretos` pero no `bna-db-datos` | `scripts/k8s-infra.sh borrar --si` y aplicar de nuevo (se pierden los datos) |

### 6. Borrar

```bash
scripts/k8s-infra.sh borrar --si
```

Borra todos los objetos con la etiqueta del producto, después de comprobar que todos se llaman `bna-*`; si alguno no, no borra nada. Incluye los dos PVC: la base y el `.env` se pierden. No toca `backend`, `mysql` ni nada más del namespace.

## Si hay cuota de objetos

Hoy no hay cuota. Si Infraestructura pone una por número de objetos, lo primero que se puede agrupar:

- Los 14 Service: el Ingress solo necesita 4 (frontend, cajero, billetera, Bus); los demás se usan dentro del clúster y se podrían reemplazar por un Service con varios puertos, a costa de cambiar las direcciones de `bna-bus`.
- Los dos ConfigMap de scripts (`bna-scripts-secretos` y `bna-generar-env`) pueden ser uno.
- Los módulos Python sin base propia (CUENTAS, TARJETAS, ATM, EVALUACION, DESEMBOLSO, COBRANZA, CAPTACION) comparten imagen: podrían ir en menos Deployments, con varios contenedores por pod.

## Prueba en kind

[`scripts/prueba_k8s_infra_kind.sh`](../scripts/prueba_k8s_infra_kind.sh) prueba el mismo overlay en un clúster de kind v0.30.0 (Kubernetes 1.34): carga las imágenes con `kind load` en vez de descargarlas, crea un namespace numérico y una StorageClass `local-path`, aplica con `k8s-infra.sh`, comprueba que no haya Secrets, que cada pod tenga solo sus claves (0440, también los que corren con otro usuario) y que el Job no cambie un `.env` existente, carga los datos dos veces, corre `flujo_demo.py` por `kubectl port-forward` y borra todo. Al terminar elimina el clúster. La CI lo corre en el flujo «Kubernetes» (trabajo «Overlay de Infraestructura en kind»), junto con `kubectl kustomize`, `kubeconform` para Kubernetes 1.34 y `overlay_infraestructura.py comprobar` y `revisar`.

Lo que la prueba en kind no cubre: el Ingress de Traefik (en kind no hay Traefik; el Ingress solo se valida con `kubeconform`) y la descarga desde ghcr.io.
