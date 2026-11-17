# Plan de Integración del Cajero ATM (backend/ATM)

## Objetivo
Integrar el prototipo `bna-atm-consulta/` al producto BNA como módulo `ATM` (o `CAJERO`) real, usando TARJETAS y CUENTAS por el Bus de Servicios, sin simuladores ni Bus propio.

## Arquitectura
- Nuevo módulo `backend/ATM/` (FastAPI, puerto 8019)
- Sirve las pantallas HTML (`index.html`, `tecnico.html`) y expone API del cajero
- Llama a TARJETAS y CUENTAS por el Bus con `BUS_TOKEN_ATM`
- Consumidor nuevo del Bus en compose, k8s, .env.example, generar_env.sh
- Sin base propia, sin simuladores, logs a stdout
- Canal `ATM` y terminal del catálogo

## Flujo de Retiro
1. Validar PIN: `POST /api/v1/tarjetas/{id}/credenciales/PIN_ATM/validacion`
2. Autorizar (retención): `POST /api/v1/tarjetas/autorizaciones` con `X-Idempotency-Key`
3. "Dispensar" (simulado en el backend)
4. Confirmar: `POST /api/v1/tarjetas/autorizaciones/{uuid}/confirmacion` con `X-Idempotency-Key` y `id_canal`/`id_terminal`
5. Si falla dispensación → Extorno: `POST /api/v1/tarjetas/autorizaciones/{uuid}/extorno`

## Consultas
- Saldo: por CUENTAS (consulta consolidada del cliente)
- Movimientos: por CUENTAS

## Topes ATM
- Pregunta de equipo abierta: S/ 1,500 / US$ 500 (valor por omisión de la base)
- Los topes los aplica la autorización de Tarjetas (RN-ATM-005); no duplicar en el cajero

## Archivos a Crear/Modificar

### 1. backend/ATM/ (nuevo módulo)
- `main.py` - FastAPI app
- `config.py` - Configuración (core_base_url, bus_token, timeout)
- `core_client.py` - Cliente HTTP para Bus (TARJETAS, CUENTAS)
- `api.py` - Montar routers, manejo de errores
- `routers/atm.py` - Rutas del cajero (/api/retiro, /api/saldo, /api/movimientos, /api/estado, /api/config, /health, /ready)
- `schemas/atm.py` - Esquemas Pydantic
- `services/atm.py` - Lógica de negocio (validar PIN, autorizar, confirmar, extornar, consultar saldo/movimientos)
- `dependencies.py` - Dependencias FastAPI (core_client, correlation_id, idempotency_key, autorizacion)
- `respuestas.py` - Formato ITIL-02
- `errores.py` - Traducción de errores
- `exceptions.py` - Excepciones personalizadas
- `observabilidad.py` - Middleware de logging
- `tests/` - Suite de pruebas (conftest.py, test_atm.py, test_retiro.py, test_consultas.py)
- `README.md` - Documentación del módulo
- `CONTRATO.md` - Contrato para consumidores
- `openapi.json` - Especificación OpenAPI (generada)

### 2. Archivos estáticos (servidos por ATM)
- `static/index.html` - Pantalla principal (adaptada de bna-atm-consulta/atm/index.html)
- `static/tecnico.html` - Panel técnico (adaptado de bna-atm-consulta/atm/tecnico.html)
- `static/logo.png` - Logo
- `static/fuentes/` - Fuentes OFL (bricolage.woff2, plexmono-400.woff2, plexmono-500.woff2)
- `static/fuentes/OFL.txt` - Licencia OFL

### 3. Configuración del producto
- `compose.yaml` - Añadir servicio `atm` (puerto 8019), red `canales`, BUS_TOKEN_ATM, BUS_URL_ATM
- `.env.example` - Añadir BUS_TOKEN_ATM, BNA_PUERTO_ATM=8019
- `scripts/generar_env.sh` - Ya genera automáticamente
- `k8s/base/atm.yaml` - Deployment + Service
- `k8s/base/configuracion.yaml` - Añadir BUS_URL_ATM, BUS_CONSUMIDORES con ATM
- `scripts/comprobar_rutas_coredb.py` - Añadir ATM a MODULOS (solo si llega a COREDB directo; en este caso NO, solo llama a TARJETAS/CUENTAS por Bus)
- `scripts/pruebas.sh` - Añadir suite ATM
- `scripts/flujo_e2e.py` - Añadir tramo de retiro por cajero
- `README.md` (raíz) - Documentar ATM
- `.gitignore` - Añadir `atm/registro_operaciones.jsonl` (archivo generado del prototipo)

### 4. Limpieza del prototipo
- Mover contenido útil de `bna-atm-consulta/atm/` a `backend/ATM/static/`
- Borrar `bna-atm-consulta/atm/registro_operaciones.jsonl` (generado)
- Borrar `bna-atm-consulta/atm/servidor_atm.py` (reemplazado por backend/ATM)
- Si `bna-atm-consulta/` queda vacía, eliminarla

## Pruebas (Test-First)
1. Escribir pruebas en `backend/ATM/tests/` con transporte simulado de TARJETAS/CUENTAS
2. Casos: retiro feliz, PIN incorrecto, fondos insuficientes, fallo dispensación → extorno, repetición confirmación con misma llave → sin segundo débito
3. Ejecutar pruebas y verificar que FALLAN
4. Commit solo con pruebas que fallan
5. Implementar hasta que pasen

## Endpoints del ATM
| Método | Ruta | Descripción |
|---|---|---|
| GET | /health | Salud del servicio |
| GET | /ready | Listo si TARJETAS y CUENTAS responden por Bus |
| GET | / | Sirve index.html |
| GET | /tecnico.html | Sirve tecnico.html |
| GET | /static/... | Archivos estáticos |
| POST | /api/validar-pin | Validar PIN (llama a TARJETAS) |
| POST | /api/autorizar | Autorizar retención (llama a TARJETAS) |
| POST | /api/confirmar | Confirmar dispensación (llama a TARJETAS) |
| POST | /api/extornar | Extornar (llama a TARJETAS) |
| GET | /api/saldo | Consultar saldo (llama a CUENTAS) |
| GET | /api/movimientos | Consultar movimientos (llama a CUENTAS) |
| GET | /api/estado | Estado del cajero (bandejas, pendientes) |
| GET | /api/config | Configuración (modo prueba, id_cajero) |

## Notas sobre Confirmación de Autorización
- La confirmación (`POST /api/v1/tarjetas/autorizaciones/{uuid}/confirmacion`) la está terminando otra sesión en `oc-tarjetas-coredb` (rama `integracion/confirmar-autorizacion`)
- Contrato: cabecera `X-Idempotency-Key`, cuerpo con `id_canal` y/o `id_terminal`
- Respuesta = autorización en estado `DISPENSADA` con `uuid_transaccion`
- Programar contra ese contrato con transporte simulado
- Si `./bna test` falla solo por falta de confirmación en main, dejarlo escrito y anotar en RESUMEN

## Commits
- Todos los commits llevan: `Co-authored-by: Camila A. Lizarazo M. <138036528+Princessminute@users.noreply.github.com>`
- Commits en inglés, imperativo, pequeños y con sentido
- Sin menciones a IA

## Verificación Final
- Ejecutar `./bna test` completo (con candado `flock /tmp/bna-docker.lock`)
- Si se levantó stack con `./bna up`, bajarlo antes dentro del mismo candado
- Al terminar no debe quedar ningún contenedor ni volumen del proyecto `bna`
- Crear `RESUMEN-atm.md` en la raíz del worktree (SIN commitearlo)