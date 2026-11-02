# BNA · Módulo de Clientes

Módulo **Clientes** del Banco Nacional de Arequipa (curso GSTI, UCSM · línea de negocio Ahorros): registra clientes, los valida por documento y por biometría (huella y rostro) y audita cada solicitud en un Core simulado. Prototipo académico: use solo datos **ficticios**.

| Documento | Para quién | Contenido |
|---|---|---|
| **README.md** (este) | Quien despliega | Secuencia para levantar el servicio en el clúster K3s |
| [README-INTEGRACION-BUS.md](README-INTEGRACION-BUS.md) | Bus de Servicios y demás módulos | Cómo conectarse a Clientes: rutas, autenticación, contratos JSON y errores |
| [docs/GUIA-TECNICA.md](docs/GUIA-TECNICA.md) | Equipo | Arquitectura, ejecución local con Docker Compose, pruebas y limitaciones |

## Qué se despliega

Cinco Deployments en el namespace **`2022251091`** (no se crea el namespace ni recursos globales):

| Servicio | Imagen | Acceso | Datos |
|---|---|---|---|
| `clientes` (panel + API) | `edmaster1214/bna-clientes:latest` | **NodePort 31091** | sin BD |
| `reniec` (RENIEC simulado + admin) | `edmaster1214/bna-reniec:latest` | **NodePort 31092** | SQLite en `/mnt/data/2022251091/bna-clientes/reniec` |
| `bus` (mini-Bus) | `edmaster1214/bna-bus:latest` | interno (ClusterIP) | sin BD |
| `core` (Core simulado) | `edmaster1214/bna-core:latest` | interno (ClusterIP) | MySQL |
| `mysql` | `mysql:8.0` | interno (ClusterIP) | `/mnt/data/2022251091/bna-clientes/mysql` |

Flujo: `otro módulo → Bus → Clientes → RENIEC (directo) → Bus → Core → MySQL`. El Bus nunca llama a RENIEC.

## Requisitos

- **VPN WireGuard** activa y `kubectl` apuntando al clúster (comprobar: `kubectl -n 2022251091 get pods`).
- **Docker** en tu equipo y sesión en Docker Hub (`docker login -u edmaster1214`).
- **Python 3** (solo para generar claves y cargar datos de prueba) y **bash** (en Windows, Git Bash o WSL).
- Los NodePorts **31091** y **31092** deben estar libres en el clúster (ver «Problemas frecuentes»).

## Secuencia para levantar el servicio

### 1. Obtener el código
```bash
git clone <URL-del-repositorio> bna-clientes
cd bna-clientes
git checkout <rama-de-clientes>
```

### 2. Generar las claves (una sola vez)
```bash
python scripts/generar_env.py
```
Crea `.env` con claves aleatorias (MySQL, tokens entre servicios, claves del panel y del admin de RENIEC). **`.env` no se sube a Git.** Guárdalo: de ahí salen el Secret del clúster y las credenciales de acceso.

### 3. Construir y publicar las imágenes
```bash
docker login -u edmaster1214
bash scripts/publicar_imagenes.sh
```
Publica `bna-core`, `bna-bus`, `bna-reniec` y `bna-clientes` con la etiqueta `latest`, compiladas para **linux/amd64** (aunque tu equipo sea ARM). La primera vez tarda: las imágenes de RENIEC y Clientes incluyen TensorFlow y el modelo ArcFace.

### 4. Desplegar en el clúster
```bash
bash kubernetes/desplegar.sh
```
El script: (a) comprueba que el namespace es accesible; (b) crea el Secret `bna-secretos` desde `.env` (los YAML no contienen claves); (c) aplica `00-config` → `10-mysql` → `20-core` → `30-bus` → `40-reniec` → `50-clientes`; (d) espera a que los cinco Deployments estén listos. En el primer arranque MySQL y la descarga de imágenes pueden tardar varios minutos.

### 5. Verificar
```bash
kubectl -n 2022251091 get pods,svc
curl http://172.16.10.31:31091/salud     # {"servicio":"clientes","estado":"ok"}
curl http://172.16.10.31:31092/salud     # RENIEC simulado
```
- Panel de Clientes: `http://172.16.10.31:31091` (usuario `panel`, clave `CLIENTES_PANEL_PASSWORD` de `.env`). Los indicadores verdes de la cabecera (Bus, Core, RENIEC) muestran el estado de las dependencias.
- Admin de RENIEC: `http://172.16.10.31:31092` (usuario `admin`, clave `RENIEC_ADMIN_PASSWORD`).
- Swagger: `/docs` en ambos.

### 6. Cargar datos de prueba (opcional)
```bash
RENIEC_URL_HOST=http://172.16.10.31:31092 CLIENTES_URL_HOST=http://172.16.10.31:31091 python scripts/cargar_datos_prueba.py
```
Crea 3 ciudadanos ficticios en RENIEC (con huellas sintéticas) y clientes de ejemplo. Es repetible. Los rostros se suben a mano desde la interfaz de RENIEC.

### 7. Prueba rápida de extremo a extremo
En el panel: **Laboratorio de pruebas → 1 · Registrar cliente → «DNI válido»**. Debe responder `201` y aparecer en la pestaña *Solicitudes de registro*. El Bus no está expuesto; para llamarlo a mano: `kubectl -n 2022251091 port-forward svc/bus 8003:8000` y usar `http://localhost:8003` (ver el otro README).

## Actualizar una versión
```bash
bash scripts/publicar_imagenes.sh          # reconstruye y sube :latest
REINICIAR=1 bash kubernetes/desplegar.sh   # fuerza a los pods a descargar la imagen nueva
```
Con `:latest` + `imagePullPolicy: Always`, un simple reinicio de pods basta para tomar la imagen nueva.

## Conectar con el Bus de Servicios oficial
Por defecto Clientes usa el mini-Bus interno (`BUS_URL: http://bus:8000` en `kubernetes/00-config.yaml`). Para usar el Bus oficial: cambiar `BUS_URL`, poner en `BUS_TOKEN` (Secret) la credencial que el Bus oficial indique, y entregarle al Bus el `CLIENTES_TOKEN`. Detalle en [README-INTEGRACION-BUS.md](README-INTEGRACION-BUS.md).

## Operación
```bash
kubectl -n 2022251091 logs deploy/clientes -f      # también: reniec, bus, core, mysql
kubectl -n 2022251091 describe pod <pod>           # si un pod no arranca
kubectl -n 2022251091 rollout restart deploy/clientes
bash kubernetes/eliminar.sh                        # retira todo (NO borra las carpetas de datos ni el namespace)
```
Los logs no contienen biometría y enmascaran los documentos.

## Problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `provided port is already allocated` al aplicar `40-reniec` o `50-clientes` | El NodePort 31091/31092 lo usa otro Service del clúster (p. ej. el antiguo `reniec-api` en 31091) | Eliminar ese Service/Deployment antiguo, o cambiar `nodePort` en el YAML |
| `ImagePullBackOff` | Imagen no publicada o nombre/etiqueta distintos | Repetir el paso 3; revisar con `kubectl describe pod` |
| `CreateContainerConfigError` | Falta el Secret `bna-secretos` o una clave | Ejecutar `kubernetes/desplegar.sh` (lo crea) y comprobar que `.env` tiene las 8 claves |
| `exec format error` | Imagen compilada para ARM | Usar `scripts/publicar_imagenes.sh` (fuerza `linux/amd64`) |
| `reniec` en `Error` / `Permission denied` sobre `/data` | El clúster no permite el initContainer como root | Crear la carpeta con `chown 10001:10001 /mnt/data/2022251091/bna-clientes/reniec` y quitar el bloque `initContainers` de `40-reniec.yaml` |
| `OOMKilled` en `reniec` o `clientes` | TensorFlow necesita memoria al procesar un rostro | Subir `limits.memory` en el YAML correspondiente |
| Un indicador de la cabecera del panel (Bus, Core, RENIEC) está en rojo | Pod aún iniciando o caído | `kubectl get pods`; revisar logs del servicio caído |

## Persistencia y seguridad
- Los datos viven en carpetas `hostPath` bajo `/mnt/data/2022251091/bna-clientes/` (no hay StorageClass). Los manifiestos **no fijan el nodo**: si el clúster tuviera varios nodos, añade `nodeSelector` hacia el nodo que tiene la carpeta, o los datos podrían «desaparecer» al reprogramarse el pod.
- Ningún secreto está en el repositorio: `.env` y `kubernetes/secretos.env` están en `.gitignore`.
- La autenticación entre servicios es un token compartido y el panel usa HTTP Basic sin TLS; es suficiente para el entorno académico, no para producción.
- La validación facial no tiene detección de vida.

## Estado de verificación
Verificado: pruebas automáticas (72 aprobadas, 2 omitidas, 0 fallidas) con los servicios ejecutados de forma nativa sobre MariaDB, y sintaxis de los YAML. **No verificado aún**: construcción de las imágenes Docker, despliegue real en K3s, MySQL 8 real y verificación facial con fotografías reales. Reporta cualquier fallo del primer despliegue en el equipo del módulo.

## Estructura
```
clientes/  core-simulado/  mini-bus/  reniec/   # un servicio por carpeta (app/, Dockerfile)
shared/        # esquemas, errores, autenticación y biometría compartidos
kubernetes/    # 00-config … 50-clientes.yaml, desplegar.sh, eliminar.sh, secretos.env.example
scripts/       # generar_env.py, cargar_datos_prueba.py, publicar_imagenes.sh
datos_prueba/  tests/  docs/  docker-compose.yml  .env.example
```
