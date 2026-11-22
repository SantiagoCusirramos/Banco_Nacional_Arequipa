# Despliegue en el clúster de Infraestructura

Cómo se despliega el producto integrado en el clúster Kubernetes de Infraestructura: el overlay [`k8s/overlays/infraestructura`](../k8s/overlays/infraestructura/) sobre `k8s/base` y el script [`scripts/k8s-infra.sh`](../scripts/k8s-infra.sh). El despliegue local con kind (`./bna k8s-up`, `k8s/overlays/local`) no cambia.

Este documento no tiene ninguna clave. El kubeconfig y el acceso al clúster los entrega Infraestructura y se guardan fuera del repositorio. El namespace asignado tampoco está en el repositorio: se pasa en `BNA_NAMESPACE`.

## El clúster

| Tema | Valor |
|---|---|
| Kubernetes | k3s 1.34. Use un `kubectl` 1.34 |
| Ingress | Traefik, en 172.16.10.31, solo HTTP |
| Almacenamiento | StorageClass `local-path` (un solo nodo; los datos quedan en su disco) |
| Cuota | La cuenta no puede listar cuotas ni ver el uso (`kubectl top`); el 2026-11-20 los 14 pods arrancaron con sus pedidos sin problema. Si aparece una cuota por número de objetos, ver «Si hay cuota de objetos» |
| Permisos de la cuenta | En su namespace: ConfigMap, Deployment, Service, Ingress, Job, PVC y Pod (con `exec` y `logs`; `port-forward` lo rechaza la API: «cannot create resource pods/portforward», aunque `kubectl auth can-i create pods/portforward` diga que sí, comprobado el 2026-11-20 con kubectl 1.37). **No** puede leer ni crear Secrets, ni ver eventos, ni crear namespaces |
| Objetos anteriores | El `backend` y el `mysql` de un despliegue anterior (Deployment, Service, PVC `mysql-data`, Ingress `backend` y ConfigMap `bna-config`) se borraron el 2026-11-20 a pedido del dueño: ya no existen. El producto solo usa objetos `bna-*` con la etiqueta `app.kubernetes.io/instance=bna` |

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

Recursos: cada servicio pide 50m de CPU y 128Mi de memoria; la base, 50m y 512Mi. Los máximos son los de `k8s/base` (la base, 1Gi: con 512Mi MySQL muere durante la primera carga del esquema).

Imágenes: `ghcr.io/miguelpro324/bna-core-db`, `bna-coredb`, `bna-backend`, `bna-sol`, `bna-seguridad`, `bna-billetera` y `bna-frontend`, etiquetadas con el commit (12 caracteres), públicas. Son las mismas que construye `docker compose build`; ninguna lleva `.env`. La de la base incluye los datos de desarrollo (`DATOS_DEV=1`): sirve para demostraciones, no para producción.

## Direcciones

| Dirección | Qué |
|---|---|
| http://bna.172.16.10.31.sslip.io | Portal (frontend), con `/login`, las pantallas de cada módulo y el Home Banking en `/homebanking/index.html` (con `/homebanking/` Next.js redirige a `/homebanking` y da 404, también en local) |
| http://bna-cajero.172.16.10.31.sslip.io | Pantalla del cajero (ATM) |
| http://bna-billetera.172.16.10.31.sslip.io | API de la billetera (Chaski), en `/api` |
| http://bna-bus.172.16.10.31.sslip.io | Bus de Servicios (`/docs`). Cada ruta `/bus/…` exige la cabecera `X-Bus-Token` |

sslip.io resuelve `<nombre>.172.16.10.31.sslip.io` a 172.16.10.31, así que no hace falta un DNS propio. Hace falta llegar a esa dirección (la red de Infraestructura).

Históricamente la IP sola iba a un Ingress `backend` sin host; ese Ingress ya no existe y la IP sola responde 404 de Traefik. Solo los cuatro hosts de arriba llegan al producto.

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

Es el flujo de [`flujo-demo.md`](flujo-demo.md), con las mismas comprobaciones. Sin `.env` local: `flujo_demo.py` lee con `kubectl exec` las tres claves que necesita (`BUS_TOKEN_PRUEBAS` del pod del Bus; el usuario y la clave del administrador, del archivo `primer-administrador` del pod de COREDB) y no imprime ninguna. Sale con 0 si todo pasó. Para usar otras direcciones (por ejemplo, las de otro clúster donde `kubectl port-forward` sí funcione): `BNA_FRONTEND` y `BNA_BUS`.

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
| COREDB no entra a la base («Access denied for user 'bna_app_user'») | Se borró `bna-secretos` pero no `bna-db-datos`, o `bna-db` se reinició durante su primera carga y el volumen quedó sin los usuarios (`diagnostico` muestra el motivo del reinicio) | `scripts/k8s-infra.sh borrar --si` y aplicar de nuevo (se pierden los datos) |

### 6. Borrar

```bash
scripts/k8s-infra.sh borrar --si
```

Borra todos los objetos con la etiqueta del producto, después de comprobar que todos se llaman `bna-*`; si alguno no, no borra nada. Incluye los dos PVC: la base y el `.env` se pierden. No toca nada más del namespace.

## Si hay cuota de objetos

No se conoce ninguna cuota (la cuenta no puede verlas). Si Infraestructura pone una por número de objetos, lo primero que se puede agrupar:

- Los 14 Service: el Ingress solo necesita 4 (frontend, cajero, billetera, Bus); los demás se usan dentro del clúster y se podrían reemplazar por un Service con varios puertos, a costa de cambiar las direcciones de `bna-bus`.
- Los dos ConfigMap de scripts (`bna-scripts-secretos` y `bna-generar-env`) pueden ser uno.
- Los módulos Python sin base propia (CUENTAS, TARJETAS, ATM, EVALUACION, DESEMBOLSO, COBRANZA, CAPTACION) comparten imagen: podrían ir en menos Deployments, con varios contenedores por pod.

## Prueba en kind

[`scripts/prueba_k8s_infra_kind.sh`](../scripts/prueba_k8s_infra_kind.sh) prueba el mismo overlay en un clúster de kind v0.30.0 (Kubernetes 1.34): carga las imágenes con `kind load` en vez de descargarlas, crea un namespace numérico y una StorageClass `local-path`, aplica con `k8s-infra.sh`, comprueba que no haya Secrets, que cada pod tenga solo sus claves (0440, también los que corren con otro usuario) y que el Job no cambie un `.env` existente, carga los datos dos veces, corre `flujo_demo.py` por `kubectl port-forward` y borra todo. Al terminar elimina el clúster. La CI lo corre en el flujo «Kubernetes» (trabajo «Overlay de Infraestructura en kind»), junto con `kubectl kustomize`, `kubeconform` para Kubernetes 1.34 y `overlay_infraestructura.py comprobar` y `revisar`.

Lo que la prueba en kind no cubre: el Ingress de Traefik (en kind no hay Traefik; el Ingress solo se valida con `kubeconform`) y la descarga desde ghcr.io. Las dos cosas se comprobaron en el clúster real (ver abajo).

## Despliegue real (2026-11-20)

Primer despliegue en el clúster, con las imágenes de `a14d8f35c571` ya públicas y `kubectl` 1.34.

- **Aplicar.** `scripts/k8s-infra.sh aplicar` sin cambios en el overlay: el Job `bna-arranque` terminó en 11 s (`.env` con 45 claves) y los 14 pods quedaron listos sin reinicios en menos de 90 s, con la descarga de las imágenes desde ghcr.io incluida (sin credenciales). Los módulos que esperan a COREDB tardan unos 80 s; mientras tanto `/ready` de TARJETAS responde 503 y lo registra como ERROR, y es normal.
- **Datos.** `scripts/k8s-infra.sh datos` no tuvo que agregar nada: la imagen de la base ya los carga (periodo del mes abierto, BIN 004499, agencia `AQP01`, 5 terminales `DEV-*`, `DEV-ATM-01` activo).
- **Flujo.** `scripts/k8s-infra.sh flujo` por el Ingress: sale con 0, saldo final 1500.00; en COREDB, solicitud DESEMBOLSADA, crédito AL_DIA con 6 cuotas y tarjeta BLOQUEADA. El texto del paso 4 dice `http://127.0.0.1:8019` (es la dirección del cajero en local); en el clúster la pantalla es http://bna-cajero.172.16.10.31.sslip.io.
- **Direcciones.** Dan 200 el portal, `/login`, `/homebanking/index.html`, la pantalla del cajero, su `/api/health` y `/docs` del Bus. La billetera responde 401 en `/api/…` sin sesión y el Bus, 401 en `/bus/…` sin `X-Bus-Token`.
- **Registros.** Sin datos personales ni claves: solo códigos internos (CLI…, número de cuenta, UUID) en las rutas. Se comprobó que ningún valor del `.env` aparece en los registros ni en los ConfigMap.
- **Claves.** `kubectl auth can-i list secrets` y `create secrets` dan `no`; los Deployment, Job y pods no tienen `secretKeyRef`, `secretRef`, volúmenes de Secret ni `imagePullSecrets`. El PVC `bna-secretos` lo escribe solo el Job; los contenedores `secretos` lo montan en solo lectura y en cada contenedor queda un archivo 0440 en un tmpfs (`/secretos`).

Revisión después de cada despliegue:

```bash
scripts/k8s-infra.sh estado                       # 14 pods 1/1 y 0 reinicios; Job Complete
kubectl -n "$BNA_NAMESPACE" auth can-i list secrets   # no
for p in $(kubectl -n "$BNA_NAMESPACE" get pod -l app.kubernetes.io/instance=bna -o name); do
  kubectl -n "$BNA_NAMESPACE" logs "$p" --all-containers --prefix
done > registros.txt                              # revisar y borrar; no se versiona
```

## Cambio de base a mano: vista v1.16 (2026-11-21)

La base del clúster vive en el PVC `bna-db-datos`. La imagen de la base solo ejecuta sus scripts (`database/sql/`) cuando el volumen está vacío, así que una versión nueva de bna-core-db no llega a una base que ya existe. `bd-v1.16-mysql` agregó la vista `tarjetas.v_historial_estado_tarjeta_api` (la usa COREDB en `GET /coredb/tarjetas/{id}/historial` y en la respuesta del desbloqueo), así que antes del redespliegue de `d3f9e99f6c9b` se aplicó a mano en el pod de la base, como root y con la clave dentro del pod (igual que `datos`): el `CREATE OR REPLACE VIEW` y el `GRANT SELECT … TO bna_api` de `database/sql/bna_extension.sql`. Sin la vista, el código nuevo de COREDB fallaría en esas rutas; el código anterior no la usa, así que no le afectó.

No choca con la base nueva: en un volumen vacío la crea `bna_extension.sql` con la misma definición (`DEFINER bna_owner`, `SQL SECURITY DEFINER`) y en el volumen actual el script no vuelve a correr. Comprobado después del redespliegue: la vista existe con ese definidor, `bna_api` tiene el `SELECT` y devuelve filas.

Redespliegue de `d3f9e99f6c9b` (`aplicar`): 14 pods 1/1 sin reinicios con las imágenes nuevas. Por el Ingress, `/tarjetas/desbloqueo` y `/homebanking/auditoria.html` dan 200; `/api/seguridad/auditoria` da 404 (el puente no la deja pasar) y `/api/seguridad/tarjetas/<uuid>` sin token, 401. `scripts/flujo_e2e.py` corrió en el pod del Bus con datos nuevos y terminó con «Flujo completo»: el Home Banking bloquea la tarjeta, el cajero la rechaza, un operador la desbloquea en la pantalla y el cajero vuelve a aceptarla.

Si otra versión de bna-core-db cambia el esquema, hay dos caminos: aplicar a mano solo lo nuevo (si es idempotente, como aquí) o `borrar --si` y `aplicar` para crear la base de cero (se pierden los datos del clúster).
