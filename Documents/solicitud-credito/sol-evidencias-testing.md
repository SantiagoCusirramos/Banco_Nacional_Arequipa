# E06 — Evidencias de validación

Fecha: 2026-11-14 (America/Lima). Rama `feature/integracion-sol`, HEAD base `86904edd8dc866c1d4260a996748a1cda3770007` más cambios sin commit E02–E06. No se ejecutaron commits, staging ni pushes. [Entrega](sol-entrega-final.md), [matriz](sol-matriz-rf.md), [registro](change-log.md).

## Resultados finales efectivamente ejecutados

| Verificación | Resultado / entorno | Límite de la evidencia |
| --- | --- | --- |
| Regresión backend SQLite | **169 passed, 2 warnings, 40,34 s**, salida 0; Python 3.13.5 | SQLite temporal/MockTransport; incluye 163 E05 + cuatro casos de fecha + dos de access log |
| Regresión con MySQL | **169 passed, 2 warnings, 49,36 s**, salida 0; Python 3.11 en imagen SOL, MySQL **8.4.13** | Fixtures `lab`/`real_lab` usan `bna_sol_mvp_test`; algunos tests independientes siguen creando SQLite por diseño. No son 169 ensayos exclusivamente MySQL ni proveedores institucionales |
| Migración incremental / transacciones | **7 comprobaciones**, salida 0 | Base scratch `bna_sol_mvp_e06migration`: usuario v1 preservado, migración repetida, columnas incrementales, READ COMMITTED, rollback, exclusión FOR UPDATE NOWAIT entre dos conexiones y liberación del lock |
| Frontend completo | **114 passed, 2 expected fail (116)**, 7 archivos, 4,77 s, salida 0 | Vitest/RTL/jsdom y upstream mock; conserva dos fallos esperados ajenos a SOL. Cinco casos nuevos E06 de origen público |
| Lint / TypeScript | Ambos salida 0 | Copia temporal sincronizada; sin modificar package/lock/config compartida |
| Build Next final | Salida 0; compilación 386 ms, TypeScript 1497 ms, 8 páginas | Next 16.3.8/Turbopack, Node 22.22.2; `/solicitud-credito` y proxy presentes |
| Compose aislado | Build, MySQL healthy, init salida 0, SOL y Next arrancados | Proyecto `bna-sol-e06`; no extiende el Compose BNA ni usa sus volúmenes |
| HTTP TCP backend y proxy | **142 comprobaciones**, salida 0 | Next→SOL→MySQL reales; Captación, Evaluación y Auditoría **SIMULADO**. [Evidencia saneada](sol-e06-http-evidencia.json) |
| Reinicio / privacidad real | **4 comprobaciones**, salida 0 | Query/clave/token ausentes de nuevos logs; sesión y expediente intactos tras reiniciar solo SOL. [Evidencia](sol-e06-reinicio-privacidad.json) |
| OpenAPI | 40 modelos, dos esquemas Bearer; SIMULADO 31 rutas/35 operaciones, REAL 17/19 | SIMULADO exportado del servidor TCP; REAL generado en la misma imagen con configuración fake, sin lifespan ni peticiones externas |

Advertencias backend heredadas: alias AnyIO `BlockingPortal` usado por Starlette y opción pytest `asyncio_default_fixture_loop_scope` sin plugin. Vitest advierte sobre `__dirname` y el futuro configLoader nativo; no se ocultó ni se cambió configuración global. Dos fallos esperados frontend ya existían antes de SOL.

## Incidencias y correcciones, sin ocultar fallos

| Ejecución anterior | Resultado | Diagnóstico / acción |
| --- | --- | --- |
| Suite MySQL inicial (163) | 3 failed / 160 passed / 2 warnings, 45,69 s | `DATETIME(0)` redondea .5+; respuesta ORM de escritura truncaba antes de recargar. `service.detail` ahora refresca expediente tras flush, sin ALTER ni cambio de snapshot |
| Reproducción determinista de fecha | 2 failed / 2 passed, 2,13 s | Cuatro precisiones 0/499999/500000/999999; se conservaron todas las aserciones de igualdad escritura/GET |
| Selección tras corrección | 7 passed / 160 deselected, 4,60 s | Cuatro casos nuevos y tres regresiones afectadas |
| Segunda suite MySQL (167) | 1 failed / 166 passed, 48,26 s | Test de vencimiento congelaba instante previo a redondeo. Ahora usa deadline realmente persistido; autenticación sigue rechazando `expires <= now()` |
| Suite MySQL siguiente | 167 passed / 2 warnings, 48,53 s | Antes de agregar dos casos de logs; no sustituye la regresión final de 169 |
| Primeras ejecuciones HTTP | Salida 1, sin recorrido completo aprobado | Comparación literal OpenAPI 422 entre Python 3.11/3.13; callback vacío 422 antes de auth; luego proxy login 403 por origen interno Next. Script ajustado a semántica HTTP y payload válido; proxy corregido con origen explícito |
| Reproducción proxy | 5 failed / 13 passed, 311 ms | `SOL_PUBLIC_ORIGIN` validado en servidor; inválido 503, origen distinto/ausente 403; no confía cabeceras Forwarded del cliente |
| Privacidad TCP previa | Marcador de consulta encontrado en uvicorn.access; contraseña/token ausentes | Logs propios ya eran mínimos. Nuevo filtro durante lifespan SOL elimina query de access log nativo |
| Reproducción logging | 2 failed / 115 deselected, 0,90 s | Ruta conocida y desconocida; ambas pasan dentro de las regresiones finales |
| Migración primer intento | Salida 1, import SOL no encontrado | Repetida con `PYTHONPATH=/app`, salida 0; no cambiaron datos de la aplicación |

Compose intentó descargar la etiqueta local de init antes del build (denegado por registro), pero continuó a construir SOL y terminó con salida 0. Para reproducir sin ese aviso, construir SOL primero y luego `up`. No se eliminaron imágenes ni volúmenes compartidos.

## Recorrido TCP comprobado

`e06_validar_http.py` comprueba readiness real y contrato OpenAPI, login, roles, referencia mínima, política SIMULADO, preview, calendario Decimal/capital/saldo, garantía y fiador SIMULADA, creación, edición y revisión vieja 409. Rechaza pago doble, USD, plazo inválido, autofiador y campo extra sin eco sensible. Congela al enviar, conserva clave y una entrega al reintentar, rechaza edición congelada y resultado desde asesor. Evaluador demo observa; asesor crea v2, subsana y reenvía; resultado v1 nuevo se rechaza y v2 demo cierra APROBADA conservando v1. Auditor consulta detalle/pendientes/métricas y no puede crear; logout revoca sesión. Proxy oculta token, usa cookie HttpOnly/no-store, rechaza origen ajeno y callback por canal navegador. Se realiza por `/sol` directo y `/api/solicitud-credito`.

APROBADA en este recorrido es resultado sintético de laboratorio, no aprobación bancaria/desembolso. El flujo SIMULADO confirma envío síncronamente: no acredita un proveedor EVA en espera. Los casos 202, timeout, respuesta perdida, callback de servicio, versiones/rondas/operaciones/correlación y generaciones de worker se prueban en la suite con MockTransport y persistencia MySQL/SQLite. No se afirma que se hayan probado esos fallos contra EVA real.

## Reproducción segura

Usar únicamente el Compose E06 (`compose-e06.yaml`, retirado del repositorio; ver `change-log.md`). Sus puertos 13316/18016/13016 son loopback, MySQL guarda datos en tmpfs y no hay volumen de datos ni montajes institucionales. Dos bases separan suite destructiva de fixtures (`bna_sol_mvp_test`) y recorrido HTTP (`bna_sol_mvp_e06`). La scratch de migración debe estar vacía; un segundo ensayo se detiene si ya tiene tablas. Nunca apuntar estos comandos a otro servidor.

En esta ejecución se usó `/tmp/bna-sol-e06.env`, permisos 0600, con claves aleatorias `E06_MYSQL_PASSWORD`, `E06_LOGIN_PASSWORD` y `E06_FRONTEND_DIR=/tmp/bna-e05-frontend`. No versionar ni publicar ese archivo ni ejecutar `compose config` sin filtrar (puede imprimir secretos). La copia frontend contiene los archivos finales del repo, dependencias del lockfile y build; no `.env` privado. Instalar Node/dependencias y construir una copia temporal antes de arrancar, siguiendo `frontend/AGENTS.md`. La imagen Next ejecuta ese build mediante montaje de solo lectura: no se afirma haber construido el Dockerfile frontend de producción.

Desde raíz, estos son los comandos realmente usados (con permisos Docker/red cuando correspondía):

```bash
env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts= backend/SOL/tests
docker compose --env-file /tmp/bna-sol-e06.env -p bna-sol-e06 -f Documents/solicitud-credito/compose-e06.yaml up -d --build
docker compose --env-file /tmp/bna-sol-e06.env -p bna-sol-e06 -f Documents/solicitud-credito/compose-e06.yaml run --rm --no-deps -T -e SOL_WORKER_SECONDS=0 sol python -c 'import os,subprocess; from SOL.settings import Settings; from sqlalchemy.engine import make_url; os.environ["SOL_TEST_DATABASE_URL"]=make_url(Settings.from_env().database_url).set(database="bna_sol_mvp_test").render_as_string(hide_password=False); raise SystemExit(subprocess.call(["python","-m","pytest","-p","no:cacheprovider","-q","--tb=short","-o","addopts=","SOL/tests"]))'
/tmp/bna-sol-p01-venv/bin/python Documents/solicitud-credito/e06_validar_http.py --env-file /tmp/bna-sol-e06.env
docker compose --env-file /tmp/bna-sol-e06.env -p bna-sol-e06 -f Documents/solicitud-credito/compose-e06.yaml run --rm --no-deps -T -e SOL_WORKER_SECONDS=0 -e PYTHONPATH=/app -v "$PWD/Documents/solicitud-credito:/evidence:ro" sol python /evidence/e06_validar_mysql.py
```

Frontend, en la copia temporal, con PATH de `/tmp/node-v22.22.2-linux-x64/bin`: `npm test`, `npm run lint`, `./node_modules/.bin/tsc --noEmit --incremental false`, `NEXT_TELEMETRY_DISABLED=1 timeout 180s npm run build`. El build requirió ejecución autorizada fuera del sandbox; no se ajustó código para saltar restricciones. Se verificó igualdad por hash de fuentes relevantes entre copia y repo.

No ejecutar `./bna test`: genera entorno/levanta todo y su limpieza contiene `down -v`. No ejecutar `./bna smoke` sobre el stack compartido: crea clientes, cuentas y movimientos en otros módulos. Ambos se inspeccionaron y se sustituyeron por pruebas SOL aisladas. No se ejecutó reset, DROP DATABASE ni migración institucional.

## Pendientes y límites

No hay navegador/Chromium instalado: **no se ejecutó E2E en navegador real**; GET de página y proxy HTTP no prueban hidratación/interacción visual real. No se instalaron servicios institucionales ni se usaron datos reales. Tampoco se certifican TLS/reverse proxy público, SSO/MFA, alta disponibilidad, concurrencia distribuida de workers, SLA, backup/restauración productiva o carga. FOR UPDATE con dos conexiones prueba exclusión MySQL, no todas las carreras posibles. Migración prueba tabla usuario v1 y creación del resto, no un dump histórico completo.

Captación/COREDB, Evaluación y Seguridad mantienen los bloqueos descritos en la [entrega](sol-entrega-final.md). REAL del esquema exportado solo representa transporte configurado, jamás homologación.

## Integridad y estado del laboratorio al cierre

[Manifiesto SHA256 de 28 archivos](sol-e06-manifiesto.json): incluye 21 Python SOL, política y seis archivos frontend/package/lock. Fuentes relevantes de copia y repo coinciden. Imagen SOL final `sha256:d3fbe94c810230d42465d2943fd1bf500ab3f7429507abd14a060f198ee0049f`; MySQL `sha256:b35575a03e5327131916eb8d39222c4c89590881fb44ed69b5814910e5fefa34`; Node runtime `sha256:b774d993885c47eca14db241ba8cc7e5789235142f76e4a2a6a65ec350a1bac0`. No se confunde Node runtime del contenedor con Node 22.22.2 usado para construir.

Se detuvieron únicamente frontend/sol/mysql del proyecto E06, salida 0. Verificación posterior: cero contenedores E06 activos, MySQL exited con `HostConfig.Tmpfs={"/var/lib/mysql":""}`, ningún volumen persistente E06 y ningún contenedor BNA compartido. El montaje frontend `/app` era bind de solo lectura. Los datos sintéticos tmpfs se descartan al detener MySQL; las evidencias saneadas quedan en esta carpeta. Contenedores detenidos/imágenes y archivo temporal externo 0600 se conservan para revisión; no se borraron volúmenes ni se ejecutó down -v.

`git diff --check` salida 0; diff acumulado E02–E06: diez archivos seguidos, 1344 inserciones/87 eliminaciones, más tests/documentos sin seguimiento revisados. Índice vacío, HEAD preservado y diff vacío en módulos ajenos/infra/CI/package/lock/config compartidas. Escaneo de cambios no encontró secretos efímeros, claves privadas/PAT/AWS por patrones o conflictos; no agrega `.env` privado, dumps o bases. AST/JSON/enlaces/espacios correctos. No se repitieron suites por el cierre exclusivamente documental.
