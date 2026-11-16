# CAPTACION

Módulo de Captación de Clientes. Lleva a una persona desde que pide un producto hasta que queda
**habilitada** como cliente del banco, con su identidad verificada:

1. **Registro** del solicitante (prospecto) y apertura de su **caso**.
2. **Consentimientos**: tratamiento de datos, consulta a centrales y términos (biometría, opcional).
3. **Verificación de datos**: código OTP al celular (y al correo, opcional); RENIEC, listas
   restrictivas y PEP; validaciones manuales para la debida diligencia.
4. **Centrales de riesgo** (SBS, Infocorp, Sentinel, Equifax) y **perfil** de riesgo de 0 a 1000.
5. **Habilitación**: registra al cliente en **COREDB** como `HABILITADO` (o reutiliza el cliente
   activo que ya tenga ese documento), le anota las verificaciones de celular y correo, y deja la
   **referencia vigente** que consulta **Solicitud de Crédito** (contrato CR-INT-01).

Puerto **8017**. Pantalla del asesor: **http://localhost:3000/captacion**.

## Cómo se integra

```mermaid
flowchart LR
  ase["Asesor en /captacion"] --> fe["frontend /api/captacion"] --> cap["CAPTACION :8017"]
  cap -->|"token del asesor: GET /coredb/auth/me"| coredb["COREDB :8012"]
  cap -->|"usuario de servicio: alta, validaciones, consulta"| coredb
  cap --> aux[("db-aux: bna_captacion")]
  sol["SOL :8011"] -.->|"CR-INT-01: GET /cap/references (cuando haya Bus)"| cap
```

| Con | Cómo | Qué |
|---|---|---|
| **COREDB / Clientes** | Usuario de servicio `svc-captacion` (rol SERVICIO, módulo CLIENTES) | `POST /coredb/clientes/validaciones/documento` (¿ya es cliente?), `POST /coredb/clientes` (alta HABILITADA), `POST /coredb/clientes/{cod}/validaciones` (CELULAR, CORREO), `GET /coredb/clientes/{cod}` |
| **COREDB / sesión** | Token JWT del asesor | `GET /coredb/auth/me`: quién es y sus permisos. Leer exige `VER_CLIENTE`; trabajar un caso, `CREAR_CLIENTE` (ASESOR y ADMINISTRADOR) |
| **Solicitud de Crédito** | Token de servicio `CAP_SOL_TOKEN` | `GET /cap/references?search=&limit=50` y `GET /cap/references/{idCliente}`, con la forma exacta que espera `backend/SOL/integrations.py` |
| **Base propia** | `cap_user` sobre `bna_captacion` en db-aux | El expediente: solicitantes, casos, consentimientos, OTP, validaciones, consultas, perfiles y bitácora. **No** escribe en la base integrada: el cliente vive en COREDB |

- **Por qué un usuario de servicio del módulo CLIENTES.** COREDB solo acepta un cliente
  `HABILITADO` de ese usuario (punto R-01 de [`CONTRATO_CLIENTES.md`](../COREDB/CONTRATO_CLIENTES.md)), y
  la base integrada no tiene un módulo `CAPTACION` en `core.modulo`: la captación forma parte del
  dominio de Clientes (`clientes.verificacion_captacion`). Si el equipo decide otra cosa, solo
  cambia `CAP_CORE_USUARIO` y el módulo con el que se crea (`CAPTACION/manage.py`).
- **El usuario de servicio lo crea el arranque**: `captacion-init` inicia sesión con el
  administrador de COREDB, crea `svc-captacion` por `POST /coredb/usuarios/servicios` (o renueva su
  secreto si ya existe) y lo escribe en un volumen que solo lee CAPTACION. Es el procedimiento de la
  sección 2 de `CONTRATO_CLIENTES.md`. Ningún secreto queda en el repositorio.
- **SOL hoy sigue en modo SIMULADO**: para pasar a REAL necesita además Evaluación, Seguridad y el
  Bus. Mientras tanto, la prueba `tests/test_contrato_sol.py` usa **el adaptador real de SOL, sin
  cambios**, contra CAPTACION: SOL acepta la referencia de un cliente habilitado y rechaza una
  revocada o inexistente. Cuando exista el Bus, SOL se configura con:
  ```dotenv
  SOL_CAP_SEARCH_PATH=/cap/references
  SOL_CAP_REFERENCE_PATH=/cap/references/{idCliente}
  # SOL_BUS_TOKEN = CAP_SOL_TOKEN de CAPTACION
  ```

## Estados del caso

```
INICIADO → EN_VALIDACION → APROBADO → HABILITADO
               ↘ OBSERVADO (validación observada u observación del asesor) ↗
RECHAZADO: lista restrictiva, validación rechazada, riesgo MUY_ALTO o decisión del asesor
REVOCADO:  el asesor retira una habilitación; SOL deja de aceptarla
```

Para **habilitar** hacen falta: los tres consentimientos requeridos, el celular verificado por OTP,
RENIEC y listas restrictivas aprobadas, ninguna validación rechazada ni observada sin resolver, el
perfil calculado con la última consulta y distinto de `MUY_ALTO`. `GET /casos/{id}` devuelve la
lista `faltantes` y `listo_para_habilitar`.

La habilitación dura `CAP_VIGENCIA_DIAS` (30). Pasado ese plazo, SOL rechaza la referencia y se abre
un caso nuevo para verificar otra vez.

## Rutas

Base `/api/v1/captacion`, con respuestas ITIL-02 (`success`, `data`, `metadata`; en error,
`error_code` `ERR-CAP-...`), como CUENTAS y TARJETAS.

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/solicitantes` | Registra al solicitante. Documento repetido: 200 con `duplicado: true` |
| GET | `/solicitantes?documento=` · `/solicitantes/{id}` | Búsqueda y consulta |
| POST | `/casos` | Abre el caso (un solo caso abierto por solicitante: 409 `ERR-CAP-CASO-ABIERTO`) |
| GET | `/casos?estado=` · `/casos/{id}` | Bandeja y expediente completo, con `faltantes` |
| POST | `/casos/{id}/consentimientos` | Consentimientos |
| POST | `/casos/{id}/otp` · `/casos/{id}/otp/verificar` | Código OTP (HMAC-SHA256, 5 min, 3 intentos) |
| POST | `/casos/{id}/validaciones` · `/casos/{id}/validaciones/manual` | Identidad |
| POST | `/casos/{id}/consultas-riesgo` · `/casos/{id}/perfil` | Centrales y perfil |
| POST | `/casos/{id}/estado` | `OBSERVAR`, `LEVANTAR_OBSERVACION`, `RECHAZAR`, `REVOCAR`, con motivo |
| POST | `/casos/{id}/habilitar` | Cliente en COREDB y referencia vigente. Se puede repetir sin duplicar |
| GET | `/casos/{id}/referencia` | La referencia que verá SOL |
| GET | `/cap/references` · `/cap/references/{idCliente}` | CR-INT-01, solo con `CAP_SOL_TOKEN` |
| GET | `/health` · `/ready` | `/ready` comprueba la base propia, COREDB y la credencial de servicio |

## Proveedores simulados

RENIEC, listas restrictivas, PEP, biometría, centrales de riesgo y el envío de SMS y correo no
están contratados: `proveedores.py` responde de forma determinista, y la referencia lleva
`simulado: true`. Con `CAP_OTP_SIMULADO=true` el código OTP vuelve en la respuesta.

| Documento | Resultado |
|---|---|
| `99999999` | Lista restrictiva: caso RECHAZADO |
| `88888880` | PEP: caso OBSERVADO hasta una validación manual aprobada |
| último dígito 0 a 6 / 7 / 8 / 9 | Central NORMAL / CPP / DEFICIENTE / DUDOSO (DUDOSO: riesgo muy alto, RECHAZADO) |
| Documento que no es DNI | RENIEC OBSERVADO: verificación presencial |

## Configuración

| Variable | Para qué |
|---|---|
| `CORE_BASE_URL` | COREDB (`http://coredb:8012`) |
| `CAP_DB_HOST`, `CAP_DB_PORT`, `CAP_DB_USER`, `CAP_DB_PASSWORD`, `CAP_DB_NAME` | Base propia en db-aux |
| `CAP_CORE_USUARIO`, `CAP_CORE_SECRETO_ARCHIVO` (o `CAP_CORE_SECRETO`) | Usuario de servicio en COREDB |
| `CAP_SOL_TOKEN` | Token de SOL para CR-INT-01 (32 caracteres o más) |
| `CAP_OTP_CLAVE`, `CAP_OTP_SIMULADO` | HMAC de los OTP; devolver el código en laboratorio |
| `CAP_VIGENCIA_DIAS`, `CAP_VERSION_TERMINOS` | Vigencia de la habilitación (30) y versión de los términos (`v1`) |

En el producto, `./bna up` genera las claves en `.env` y levanta `captacion-init` y `captacion`.

## Pruebas

```bash
cd backend
python -m pytest -q CAPTACION/tests                      # SQLite en memoria, COREDB falso
CAP_TEST_DB_URL="mysql+pymysql://cap_user:...@127.0.0.1:3306/bna_captacion" \
  python -m pytest -q CAPTACION/tests                    # lo mismo contra MySQL
```

`./bna test` corre además, en las imágenes de cada módulo:
- `test_contrato_core.py` en la de COREDB: lo que CAPTACION envía cumple sus esquemas reales.
- `test_contrato_sol.py` en la de SOL: el adaptador real de SOL acepta las referencias.
- El flujo de `./bna smoke`, que capta y habilita a un cliente en el producto levantado y comprueba
  el cliente en COREDB, la referencia CR-INT-01 y el puente del frontend.

## Pendiente

| Qué | De quién depende |
|---|---|
| Proveedores reales (RENIEC, centrales, SMS) en lugar del simulador | Contratos con terceros; se reemplaza `proveedores.py` |
| Confirmar que CAPTACION registre clientes HABILITADOS como usuario de servicio de CLIENTES (R-01) | Equipos de Clientes y CORE |
| SOL en modo REAL contra CAPTACION | Bus de Servicios, Evaluación y Seguridad (SOL exige los tres) |
| `apellido_materno`: COREDB lo admite vacío, SOL lo exige | Homologar CR-INT-01 con SOL |
| Corregir celular o correo de un solicitante antes de habilitarlo | CAPTACION (siguiente versión) |
