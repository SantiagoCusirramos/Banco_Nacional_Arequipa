# BNA · Módulo de Clientes — guía técnica y de uso local

Sistema funcional del módulo **Clientes** del Banco Nacional de Arequipa (curso GSTI, UCSM): registra clientes, los valida por documento y por biometría (facial y huella), y deja auditoría de cada solicitud en un Core simulado.

> **Aviso.** Es un prototipo académico. Use solo datos y biometría **ficticios**. No es un sistema seguro para producción: la validación facial por imagen **no tiene detección de vida** (una foto del rostro puede engañarla) y la autenticación entre servicios es un token compartido.

---

## 1. Componentes y responsabilidades

| Componente | Tecnología | Responsabilidad | Puerto local |
|---|---|---|---|
| **Clientes** | FastAPI, sin BD | Reglas de negocio de registro/validación. Único que llama a RENIEC. Sirve el panel web | 8001 |
| **RENIEC simulado** | FastAPI + SQLite | Ciudadanos y plantillas biométricas. Única pieza que compara biometría (1:1, solo DNI). Interfaz administrativa | 8002 |
| **Mini-Bus** | FastAPI | Enruta por HTTP entre módulos con una tabla explícita. **No** habla con RENIEC | interno |
| **Core simulado** | FastAPI + MySQL | Guarda clientes y audita **toda** solicitud. Nunca guarda biometría | interno |
| **MySQL 8** | mysql:8.0 | 4 tablas del Core | interno |

Regla de oro: RENIEC solo es llamado por Clientes y no llama a nadie. Core y Clientes **nunca** almacenan biometría ni imágenes originales.

## 2. Arquitectura y flujos

```
Panel / otros módulos ──► Bus ──► Clientes ──(directo)──► RENIEC
                                     │
                                     └──► Bus ──► Core ──► MySQL
```

- **Registrar**: Bus→Clientes valida datos → (DNI) consulta RENIEC y compara nombres/fecha → Bus→Core registra cliente + auditoría. Pasaporte/PTP no se verifican contra RENIEC (`REGISTRADO_SIN_RENIEC`).
- **Validar documento**: DNI se confirma en RENIEC; el Core confirma si es cliente. Para pasaporte/PTP solo se devuelve `cliente:{id}` y un `aviso`, nunca datos personales.
- **Validar biometría** (solo DNI): Clientes pide a RENIEC comparar la plantilla; el resultado se audita en el Core.
- Rutas de negocio (`/clientes/*`) separadas de las del panel (`/panel/*`) para evitar ciclos.

### Contradicciones del enunciado y cómo se resolvieron (criterio de sencillez)

| Contradicción | Decisión |
|---|---|
| "Bus enruta todo" vs. "RENIEC solo lo llama Clientes" | Clientes llama a RENIEC **directo** (RENIEC se trata como sistema externo); el Bus solo cubre Clientes↔Core |
| Clientes "sin BD" vs. necesita mostrar solicitudes | El panel lee las solicitudes del Core vía Bus; Clientes no guarda copia |
| Auditar "toda" solicitud vs. error técnico | Los intentos rechazados e inválidos también se auditan; si RENIEC cae → `503 RENIEC_NO_DISPONIBLE` y aun así se audita |
| Resultado negativo ¿error o no? | `correcto:true` = se procesó sin falla técnica. Un "no coincide" es HTTP 200 con `coincide:false` |
| Pasaporte/PTP sin fuente oficial | Se valida formato, no identidad: no se devuelven datos personales |
| Biometría "no inventar coincidencias" | Sin plantilla o sin cruce real → `NO_COINCIDE`/`SIN_PLANTILLA`, nunca azar |
| Core "con MySQL" sin SQL inicial | El Core crea tablas y siembra `tipos_documento` al arrancar |

## 3. Estructura de carpetas

```
bna-clientes/
├── clientes/  core-simulado/  mini-bus/  reniec/   # un servicio por carpeta (app/, Dockerfile, requirements)
├── shared/            # esquemas, errores, auth, biometría y CSS compartidos
├── kubernetes/        # manifiestos K3s (namespace 2022251091) + desplegar.sh / eliminar.sh
├── scripts/           # generar_env.py, cargar_datos_prueba.py, publicar_imagenes.sh
├── datos_prueba/      # huellas sintéticas de ejemplo
├── tests/             # unit/ y e2e/
├── docker-compose.yml  docker-compose.debug.yml  .env.example
```

## 4. Instalación y ejecución local (Docker Compose)

Requisitos: Docker con Compose v2 y Python 3 (solo para los scripts). La primera construcción tarda: las imágenes de RENIEC y Clientes incluyen TensorFlow y el modelo ArcFace.

```bash
python scripts/generar_env.py          # crea .env con claves aleatorias (no se versiona)
docker compose up -d --build
python scripts/cargar_datos_prueba.py  # ciudadanos y clientes de prueba (idempotente)
```

- **Panel de Clientes:** http://localhost:8001 (usuario `panel`, clave en `CLIENTES_PANEL_PASSWORD` de `.env`)
- **Admin de RENIEC:** http://localhost:8002 (usuario `admin`, clave en `RENIEC_ADMIN_PASSWORD`)
- Bus, Core y MySQL no se publican. Para depurarlos: `docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d` (Bus 8003, Core 8004).
- Detener: `docker compose down` (conserva datos); `docker compose down -v` (borra datos).

> `nbis-py` (huellas) solo tiene binarios x86_64 Linux. Las imágenes usan `platform: linux/amd64`; en Mac con chip ARM se emulan (más lento).

## 5. Registrar ciudadanos en RENIEC

En http://localhost:8002 → **Registrar ciudadano** (DNI de 8 dígitos, nombres, apellidos, nacimiento, género). En la tabla, por cada ciudadano, suba una imagen **JPG/PNG** de **rostro** o **huella**: se convierte a plantilla y la imagen **no se guarda**.

```json
{ "numero_documento": "70000001", "nombres": "Juan Carlos", "apellidos": "Pérez Quispe",
  "fecha_nacimiento": "1990-05-14", "genero": "M" }
```

`scripts/cargar_datos_prueba.py` crea: `70000001` Juan Carlos Pérez Quispe (cliente, con huella A), `70000002` María Elena Mamani Condori (con huella B, no cliente), `70000003` Luis Alberto Huamán Ccama (sin biometría). El `70000099` no existe. Clientes de prueba: DNI 70000001, pasaporte `AB123456` (1985-07-09), PTP `PTP2024001` (1992-01-30).

## 6. Registrar un cliente

Panel → **Laboratorio de pruebas → 1 · Registrar cliente** (hay casos de ejemplo precargables). Por API (a través del Bus, `X-Service-Token: $BUS_TOKEN`):

```json
POST /bus/clientes/registrar
{ "modulo_origen": "AGENCIAS", "tipo_documento": "DNI", "numero_documento": "70000002",
  "nombres": "María Elena", "apellidos": "Mamani Condori", "fecha_nacimiento": "1995-11-02",
  "ingreso_mensual": "2500.00", "telefono": "954123456",
  "direccion": "Av. Ejército 123, Arequipa", "correo": "maria@example.com" }
```
Respuesta: `201` con `{"correcto":true,"cliente_id":1,"verificacion_reniec":true}`. Duplicado → `409 CLIENTE_DUPLICADO`.

## 7. Validar por documento

Laboratorio → **2 · Validar por documento**:

```json
POST /bus/clientes/validar-documento
{ "modulo_origen": "BANCA_LINEA", "tipo_documento": "DNI", "numero_documento": "70000001",
  "fecha_nacimiento": "1990-05-14" }
```
Los nombres solo se devuelven si la fecha de nacimiento coincide. Pasaporte/PTP: solo `cliente:{id}` + `aviso`.

## 8. Validar por biometría

Solo DNI, 1:1 dentro de RENIEC.

- **Huella:** formato `ISO_19794_2_2005`, `codificacion: "base64"`, `template` = cadena Base64. Se exige calidad NFIQ2 ≥ 35, ≥ 15 minucias; umbral Bozorth3 = 50.
- **Facial:** formato `ARCFACE_EMBEDDING`, `template` = lista de 512 números. Exactamente un rostro; distancia coseno ≤ 0.68.

En el Laboratorio → **3 · Validar biometría** puede pegar una plantilla o **subir una imagen**, que se convierte con el mismo motor que usa RENIEC.

```json
POST /bus/clientes/validar-biometria
{ "modulo_origen": "CAJERO_AUTOMATICO", "numero_documento": "70000001",
  "tipo_documento": "DNI", "tipo_biometria": "HUELLA", "formato": "ISO_19794_2_2005",
  "codificacion": "base64", "template": "<base64>" }
```
Coincide → `{"correcto":true,"coincide":true,"registrado_bna":true,"cliente":{...}}`. No coincide → `{"correcto":true,"coincide":false,"motivo":"NO_COINCIDE"}` sin datos personales.

**Preparar pares de imágenes:**
1. Registre el ciudadano y suba la imagen *de referencia* (ej. `datos_prueba/huellas/huella_A.png`).
2. Para un caso positivo suba en el Laboratorio otra captura de la **misma** persona (`huella_A_variante.png`); para uno negativo, una distinta (`huella_B.png`).
3. Facial: use fotos de rostro **propias o de uso libre**, de frente, un solo rostro, ≥ 64 px. Las fotos no se almacenan.

## 9. Ver los logs de solicitudes

Panel → pestañas **Solicitudes de registro** y **Solicitudes de validación** (módulo de origen, documento, fecha UTC, resultado; recarga automática cada 5 s opcional). Vienen del Core. Los logs de contenedor (`docker compose logs -f clientes`) no contienen biometría y enmascaran documentos.

## 10. Variables de entorno

Secretos (generados en `.env`): `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `BUS_TOKEN`, `CLIENTES_TOKEN`, `CORE_TOKEN`, `RENIEC_SERVICE_TOKEN`, `RENIEC_ADMIN_PASSWORD`, `CLIENTES_PANEL_PASSWORD`.

Configurables: `DOCKERHUB_USER`, `BNA_TAG`, `BIND_IP`, `CLIENTES_URL`/`CORE_URL`/`BUS_URL`/`RENIEC_URL`, `RENIEC_DB_PATH`, `FACE_DETECTOR_BACKEND`, `FACE_COSINE_DISTANCE_THRESHOLD`, `FINGERPRINT_*` (PPI, MIN_MINUTIAE, MIN_NFIQ2, MIN_RELIABILITY, MATCH_THRESHOLD), `MAX_IMAGE_MB`, `PRECARGAR_MODELO_FACIAL`, `RENIEC_TIMEOUT_SEG`, `BUS_TIMEOUT_SEG`. Valores por defecto en `.env.example`. Cambiar la URL del Bus por la del Bus oficial no requiere tocar código.

## 11. Swagger / OpenAPI

Clientes: http://localhost:8001/docs · RENIEC: http://localhost:8002/docs (con modo debug también Bus y Core en `/docs`). Los endpoints de servicio piden la cabecera `X-Service-Token`.

Formato de error uniforme: `{"correcto":false,"codigo":"DATOS_INVALIDOS","mensaje":"..."}` (códigos: `DATOS_INVALIDOS`, `CLIENTE_DUPLICADO`, `RENIEC_NO_DISPONIBLE`, `SERVICIO_NO_DISPONIBLE`, `ROSTRO_NO_DETECTADO`, `MULTIPLES_ROSTROS`, `HUELLA_SIN_CARACTERISTICAS`, …).

## 12. Pruebas

```bash
pip install -r tests/requirements-test.txt
pytest                 # unitarias (esquemas y biometría)
pytest -m e2e          # contra el stack levantado (ver tests/e2e/conftest.py)
```
Las pruebas E2E cubren los escenarios funcionales: registro correcto/duplicado/inválido/DNI inexistente/datos que no coinciden, validación por documento (DNI, pasaporte, PTP, inexistentes), huella positiva/negativa/sin plantilla, RENIEC caído (`-m reniec_caido`), tokens inválidos y módulo de origen faltante.

## 13. Publicar imágenes y desplegar en K3s

Ver el `README.md` de la raíz del repositorio (secuencia completa de despliegue) y `README-INTEGRACION-BUS.md` (conexión de otros módulos).

## Limitaciones conocidas

- **Sin detección de vida** en reconocimiento facial: una foto del titular puede aceptarse.
- La coincidencia facial se probó con lógica y embeddings sintéticos; **falta validarla con fotos reales** (umbral 0.68 de ArcFace, ajustable).
- Las huellas de ejemplo son sintéticas; con huellas reales ajuste `FINGERPRINT_*`.
- `nbis-py` solo funciona en Linux x86_64 con glibc ≥ 2.34.
- Las pruebas se ejecutaron contra MariaDB (compatible con MySQL), no MySQL 8 real; las imágenes Docker y los manifiestos K3s **no se ejecutaron** en el entorno de desarrollo (sin daemon ni clúster): la sintaxis YAML sí se validó. El primer `docker build` y el primer despliegue real son la verdadera prueba.
- Autenticación de servicios por token compartido; el panel usa HTTP Basic sin TLS. Para uso real: TLS, mTLS/JWT, rate limiting y gestión de secretos.
- El mini-Bus es un sustituto simple del Bus de Servicios oficial.
