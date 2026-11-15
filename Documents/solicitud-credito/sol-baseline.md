# P01 — Línea base segura de SOL

Fecha: 2026-11-14 (America/Lima). Rama `feature/integracion-sol`. HEAD `86904edd8dc866c1d4260a996748a1cda3770007`.

## Resultado

**52 pruebas SOL aprobadas, 2 advertencias, 14,75 s, salida 0.** Ejecución local con Python 3.13.5, SQLite aislado y HTTP fake `httpx.MockTransport`. No acredita integración real CAP/EVA/Seguridad, comportamiento MySQL ni recorrido frontend→SOL→MySQL.

Se resolvió la falta local de pytest mediante un entorno temporal `/tmp/bna-sol-p01-venv`, sin modificar dependencias del repositorio ni Python del sistema. No fue necesario corregir código funcional, tests, Compose o CI. Se crean este baseline y su entrada en [change-log.md](change-log.md); se preserva la [auditoría P00](sol-auditoria.md) como registro anterior.

Estado Git inicial: sin cambios seguidos; sin seguimiento `AGENTS.md`, `README-INICIO.md`, `Documents/solicitud-credito/{change-log.md,plan-integracion-sol.md,sol-apis-disponibles.md,sol-auditoria.md,prompts/}`. Se conservaron todos. No hubo commits, staging, push ni cambio de rama.

## Inspección de operaciones antes de ejecutar

| Operación | Efectos constatados en código | Decisión P01 |
| --- | --- | --- |
| `./bna up` | Genera `.env`, construye/arranca servicios y ejecuta inicializadores (`bna:122`; `compose.yaml:104`, `:179`) | No ejecutada: afectaría el producto completo y sus bases. |
| `./bna smoke` | Ejecuta el script dentro de COREDB con credenciales de entorno (`bna:130`); crea clientes/cuentas y movimientos (`scripts/flujo_e2e.py:6`) | No ejecutada: no hay stack activo ni `.env`; no es una comprobación de solo lectura. SOL solo participa con `/ready` (`flujo_e2e.py:31`). |
| `./bna test` | Genera entorno, construye imágenes, ejecuta suites globales, arranca el producto y smoke; puede limpiar con `down -v` (`scripts/pruebas.sh:31`, `:54`, `:82`) | No ejecutada: incompatible con la restricción de no usar `down -v`; no se alteró el script compartido. |
| Suite `backend/SOL/tests` | Fixtures borran/recrean tablas de su destino SQLite/MySQL; MySQL exige nombre `bna_sol_mvp_test` (`tests/conftest.py:21`, `test_integration_v2.py:78`) | Ejecutada eliminando `SOL_TEST_DATABASE_URL` del entorno: solo SQLite por defecto y archivos temporales. No se ejecutó `SOL.manage init/migrate`. |
| `docker compose config` | Resuelve la configuración; no arranca servicios | Ejecutada con placeholders en memoria y `--env-file /dev/null`, sin mostrar configuración con secretos ni crear archivos. |

Se verificó existencia, sin leer contenido, de `.env`, `backend/.env.sol` y `frontend/.env.local`: ninguno estaba presente. No se escribieron. El entorno de pruebas desactivó el worker y forzó SIMULADO para la aplicación global importada; las fixtures REAL inyectaron su propia configuración fake.

## Entorno y Docker

- Python 3.13.5; Docker CLI 26.1.5; Compose 2.26.1. Dockerfile del proyecto usa Python 3.11-slim (`docker/python/Dockerfile:4`): el pase local no sustituye una corrida de esa imagen.
- Consulta Docker autorizada, salida 0: ningún contenedor activo, ningún contenedor BNA incluso detenido (filtro `com.docker.compose.project=bna`), ninguna imagen `bna/*`. No se inspeccionaron/borraron volúmenes; no se afirma que no existan datos persistidos.
- No se construyeron imágenes ni se arrancó MySQL. Docker se verificó mediante consultas de estado y resolución Compose. Queda pendiente la ejecución en contenedor y MySQL aislado.
- El entorno temporal y caché permanecen en `/tmp`; no son archivos del repositorio ni una instalación persistente garantizada.

| Servicio / puerto por defecto | Configuración constatada | Estado runtime P01 |
| --- | --- | --- |
| Frontend `127.0.0.1:3000` | `SOL_GATEWAY_URL=http://sol:8011/gateway/sol` | No levantado |
| SOL `127.0.0.1:8011` | `SOL_INTEGRATION_MODE=SIMULADO`, MySQL `db-aux:3306/bna_sol_mvp` | API probada en proceso con TestClient/SQLite, sin servidor TCP |
| COREDB `127.0.0.1:8012` | Base integrada `db:3306` | No levantado |
| Base integrada `127.0.0.1:3307` | Publica MySQL 3306 | No levantada |
| CORE legado `127.0.0.1:8000` | Solo perfil `legado`; base `bna` en db-aux | No levantado |
| CUENTAS 8001, TARJETAS 8002, Seguridad 8013 | Publicación local en Compose | No levantados |
| db-aux | Puerto interno 3306, sin publicación al host en Compose | No levantada |

Puertos configurables por `BNA_PUERTO_*`; no se comprobó si otros procesos ajenos a Docker los ocupan. CAP/EVA/Bus/simulador HTTP no están declarados en Compose. La consulta con perfil legado mostró 11 servicios; sin perfil mostró 10. Una primera inspección intentó acceder al servicio legado en el resultado sin perfil y produjo `KeyError`: se corrigió el comando de inspección añadiendo `--profile legado`, sin cambio del repositorio.

## Configuración SIMULADO y REAL comprobada

Se resolvió Compose con placeholders de validación para sus variables obligatorias. Aserciones aprobadas: SOL fija `SIMULADO` y frontend apunta a `http://sol:8011/gateway/sol`. Las rutas y variables coinciden con `backend/.env.sol.example`, `frontend/.env.sol.example` y el proxy `frontend/app/api/solicitud-credito/[...path]/route.ts:32`.

Comprobación adicional en proceso con `Settings('sqlite://', worker_seconds=0)` y `create_app`, sin lifespan/red/base externa, salida 0:

- SIMULADO acepta configuración local y monta `/gateway/sol/clients`.
- REAL sin configuración rechaza el arranque con `ValueError`.
- REAL con URL/token/rutas fake completas acepta configuración, monta `/sol/integrations/evaluation-results` y no monta `/gateway/sol/clients`.
- Cinco configuraciones negativas se rechazan: tokens iguales, referencia sin `{idCliente}`, consulta EVA sin `{idOperacion}`, ruta auditoría vacía y tres reintentos adicionales.

REAL requiere `SOL_BUS_BASE_URL`, `SOL_BUS_TOKEN`, `SOL_EVA_CALLBACK_TOKEN`, `SOL_CAP_SEARCH_PATH`, `SOL_CAP_REFERENCE_PATH`, `SOL_EVA_SEND_PATH`, `SOL_EVA_STATUS_PATH`, `SOL_AUDIT_PATH`. Tokens distintos de 32+ caracteres; paths relativos y placeholders exigidos (`backend/SOL/settings.py:37`). Timeout por fase 0,6 s, máximo dos reintentos, presupuesto de inicio de llamadas 2,4 s y worker cada 5 s por defecto. HTTP permitido para laboratorio no acredita TLS institucional.

El `.env.sol` local no sustituye `SOL_INTEGRATION_MODE` inyectado por Compose. Activar REAL exige ajustar la configuración del contenedor y la entrada del proxy (en laboratorio `/sol`; Bus institucional pendiente). No se activó REAL en un servicio desplegado ni se modificaron esas variables. Los endpoints de ejemplo CAP/EVA/AUD continúan siendo del simulador, conforme a [CONTRATOS_HTTP_V2.md](CONTRATOS_HTTP_V2.md).

## Pruebas, fallos y resultados efectivos

| Comando/actividad | Resultado |
| --- | --- |
| `git branch --show-current`, `git status --short`, `git rev-parse HEAD`, `git log -3 --oneline` | Salida 0; rama/HEAD conservados |
| `uv venv --python python3 /tmp/bna-sol-p01-venv` | Primer intento salida 2: caché predeterminada sin escritura; corregido usando `UV_CACHE_DIR=/tmp/bna-sol-p01-cache`, salida 0 |
| `uv pip install ... -r backend/requirements-sol.txt` con caché temporal | Primer intento salida 2 por DNS del sandbox; repetición autorizada fuera del sandbox salida 0: 26 paquetes instalados |
| Suite SOL dentro del sandbox | No avanzó ni produjo resultado; interrumpida, salida 130. No se atribuye a un fallo de SOL sin evidencia |
| Misma suite fuera del sandbox, con `timeout 90s` | Salida 0; **52 passed, 2 warnings in 14.75s** |
| Configuración de modos/rutas y cinco casos negativos | Salida 0, comprobaciones indicadas arriba |
| Docker consultas de estado | Primer acceso bloqueado por sandbox; repetición autorizada salida 0, sin recursos BNA encontrados en las consultas indicadas |
| Compose config sin perfil / con perfil legado | Render salida 0; inspección inicial del legado ausente falló, repetición con perfil salida 0 |
| `bash -n bna scripts/pruebas.sh scripts/generar_env.sh` | Salida 0; comprobación de sintaxis, no ejecución de scripts |
| `git diff --check` y revisión de documentos | Salida 0; sin cambios seguidos, nuevos archivos revisados aparte |

Advertencias de la suite, sin cambios para ocultarlas:

1. Starlette 0.38.6 referencia el alias obsoleto `anyio.abc.BlockingPortal` con AnyIO 4.16.0. No falló la suite.
2. `backend/pytest.ini` contiene `asyncio_default_fixture_loop_scope`, desconocido sin plugin pytest-asyncio en los requisitos SOL. No falló la suite; no se modificó esa configuración compartida para una advertencia.

Cobertura ejercitada: límites/política/calendario, roles/sesiones, idempotencia, snapshots y subsanación, Lima, referencia CAP, conciliación de timeout EVA, callback y ronda/versión, outbox/rollback, PII de respuestas, readiness fallida, métricas, paginación y migración incremental sobre SQLite. Los tests `real_lab` usan `httpx.MockTransport`; el nombre REAL se refiere al adaptador, no a proveedores del banco. Los resultados actuales reproducen 52 casos del código; no recertifican MySQL/frontend de las evidencias históricas.

## Reproducción segura desde la raíz

Requiere `uv`, Python disponible y acceso al índice de paquetes; en un entorno administrado pueden requerirse autorizaciones para descargar y para TestClient. No usar una URL de pruebas heredada. Estos comandos solo preparan `/tmp` y ejecutan las fixtures aisladas:

```bash
UV_CACHE_DIR=/tmp/bna-sol-p01-cache uv venv --python python3 /tmp/bna-sol-p01-venv
UV_CACHE_DIR=/tmp/bna-sol-p01-cache uv pip install --python /tmp/bna-sol-p01-venv/bin/python -r backend/requirements-sol.txt
env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q -o addopts= backend/SOL/tests
```

Antes de reproducir en otro equipo, revisar los `.env` privados que carga `settings.py` y usar un checkout/entorno de pruebas; aquí estaban ausentes. El flag `-o addopts=` permite una salida focalizada y la ruta explícita evita el `testpaths=CORE/tests` predeterminado. `PYTHONDONTWRITEBYTECODE` y desactivar cacheprovider evitan artefactos Python/pytest en el repo.

Versiones efectivas instaladas en esta corrida (dependencias transitivas no están completamente fijadas por requirements):

```text
annotated-types==0.8.0 anyio==4.16.0 certifi==2026.10.23 cffi==2.1.1
click==8.5.1 cryptography==43.0.1 fastapi==0.115.0 h11==0.16.0
httpcore==1.0.9 httpx==0.27.2 idna==3.20 iniconfig==2.3.1
packaging==26.3 pluggy==1.7.0 pycparser==3.12 pydantic==2.9.2
pydantic-core==2.23.4 pymysql==1.1.1 pytest==8.3.3 python-dotenv==1.0.1
sniffio==1.3.1 sqlalchemy==2.0.35 starlette==0.38.6 typing-extensions==4.16.0
tzdata==2026.6 uvicorn==0.30.6
```

No se creó lockfile ni se cambió la política de dependencias. Para reproducir exactamente el entorno, contrastar también estas versiones y Python, no solo el número de pruebas.

## Pendientes y siguiente tarea

P01 deja una baseline SQLite/fake aprobada, no una baseline Docker/MySQL de extremo a extremo. No se ejecutaron build/lint/frontend, servidor TCP, smoke, suite global ni MySQL. Tampoco se verificó la deduplicación persistente de EVA/Seguridad ni se homologaron DA-SOL o políticas. Un `/ready` exitoso no demostraría nada de eso.

La siguiente tarea es **P02 — contratos y API pública**, con el inventario/OpenAPI y matriz RF. No depende de levantar bases compartidas. Las futuras pruebas MySQL deben usar instancia y base de pruebas aisladas, credenciales propias y revisión del destino antes de los `drop_all` de fixtures. El arranque completo y la política de limpieza de los scripts globales requieren resolver antes su compatibilidad con AGENTS; no se ejecutarán por inferir autorización de un pase SQLite.
