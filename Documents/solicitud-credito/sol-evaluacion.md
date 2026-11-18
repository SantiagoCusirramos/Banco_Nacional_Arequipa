# E04 — Evaluación, entrega versionada y resultados

> **Registro histórico.** El CORE legado (`backend/CORE`, su esquema `bna` en `backend/Infraestructura - BD/` y el perfil `legado` de compose) se eliminó en #125. Las rutas, archivos y servicios del CORE legado que se citan aquí ya no existen en `main`; quedan en el historial de git.

Fecha: 2026-11-14, America/Lima. Rama `feature/integracion-sol`, HEAD base `86904edd8dc866c1d4260a996748a1cda3770007` con cambios locales E02/E03 preservados y E04 sin commit/push.

## Resultado

**149 pruebas aprobadas, 2 warnings, 26,99 s**, salida 0. Regresión SQLite/MockTransport: 107 casos anteriores +42 nuevos E04. RF009 y RF010 quedan **preparado_para_integracion local**, no integrado_real. No se modificaron CORE legado, COREDB, CAP/EVA, Seguridad, frontend o infraestructura; no se inventaron estados, decisiones bancarias, rondas o proveedor EVA.

Entregables: [contrato técnico para EVA](sol-contrato-evaluacion.md), actualización de [matriz](sol-matriz-rf.md) y [changelog](change-log.md). Los informes E01–E03 y sus evidencias conservan su carácter histórico. No se reinstalaron dependencias ni se arrancaron bases reales.

## Implementado antes y cambios verificados

| Área | Ya existía | Corrección E04 / archivo |
| --- | --- | --- |
| CR-INT-02 | Sobre con snapshot/actor/operación/correlación, Delivery durable, freeze y 202; consulta GET antes de POST, backoff y conciliación | Acuse exige versión int exacta y evaluación/acuse no blancos; evaluación sin espacios exteriores, compatible con DTO callback. `backend/SOL/integrations.py:227` |
| Reservas de worker | Lease 30 s, contador attempts, recuperación y confirmación en transacción | Usa attempts como generación; relee/bloquea fila en error y éxito, ignora respuesta vieja sobre generación nueva, no deshace confirmación. Sin columna nueva. `backend/SOL/operations.py:30` |
| CR-INT-03 | Bearer separado, comparación operación/correlación, evaluación/ronda/versión confirmadas, dedupe y rechazo de resultados viejos | Cabecera X-Correlation-ID explícita requerida y segura, cotejada con cuerpo/middleware. `backend/SOL/app.py:501` |
| RF010/estados | OBSERVADA admite otra versión; APROBADA/RECHAZADA y snapshot histórico | Reutilizado sin modificar reglas; nueva cobertura de dos subsanaciones y v3 rechazada, identidad cruzada, conflictos y duplicados tardíos |

La reproducción mostró que `True == 1` y `1.0 == 1` podían aceptar una versión de acuse incompatible. También que un error tardío de worker podía cambiar CONFIRMADO a PENDIENTE, o borrar una reserva recuperada por otro intento. Las nueve pruebas inicialmente fallidas quedaron corregidas; no se trataron como problemas del proveedor ni se ocultaron.

El límite de generación usa contador persistido, no fechas con precisión dependiente de MySQL: cada reserva incrementa attempts y solo su intento vigente puede cambiar estado. Un worker que ve confirmación de otro devuelve éxito sin duplicar evento; otro que ve una nueva reserva devuelve sin liberarla/reprogramarla. La deduplicación remota sigue siendo necesaria si dos llamadas HTTP llegaron a EVA; esta protección no puede garantizar exactamente una vez en otra base.

Compatibilidad: rutas, sobre, JSON de negocio, modelos SQL, migraciones, cálculo, política y SIMULADO conservados. Acuses con bool/decimal/blancos ahora fallan permanentemente; callback sin correlación explícita recibe 422. Son restricciones del contrato v2 ya documentado. No se actualizan manualmente las instantáneas OpenAPI E01; el contrato actual y la prueba de su cabecera se describen aquí.

## Pruebas por lote y regresión

Entorno P01 reutilizado: Python 3.13.5, SQLite temporal/en memoria, MockTransport, worker global 0. Se eliminó SOL_TEST_DATABASE_URL del entorno para no heredar destino MySQL. Ejecutado fuera del sandbox con autorización por limitación conocida de TestClient. No se generó `.env`, ni se registraron secretos/cuerpos de expediente en logs de producción.

Prefijo de comandos desde la raíz:

```bash
env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts=
```

| Argumentos / ejecución | Resultado real |
| --- | --- |
| `backend/SOL/tests/test_integration_v2.py -k e04`, reproducción previa | Salida 1: **9 failed, 20 passed**, 59 deselected, 2 warnings, 4,58 s |
| Misma selección tras correcciones | Salida 0: **29 passed**, 59 deselected, 2 warnings, 4,37 s |
| Misma selección tras ampliar escenarios | Salida 0: **42 passed**, 59 deselected, 2 warnings, 8,03 s |
| `backend/SOL/tests`, regresión completa | Salida 0: **149 passed**, 2 warnings, 26,99 s |

Warnings heredados: alias AnyIO usado por Starlette y opción pytest-asyncio sin plugin. No se ocultaron ni se cambiaron dependencias/configuración compartida para eliminarlos. Las pruebas anteriores de SIMULADO, CAP, condiciones/calendario/respaldos, permisos, outbox y privacidad siguen pasando.

Comprobaciones adicionales al cierre, salida 0: AST de 21 archivos Python SOL, enlaces/espacios y `git diff --check`. Comparación OpenAPI en memoria contra E01 para ambos modos: solo difieren los límites de cada fiador añadidos en E02 y la cabecera callback requerida añadida en E04; rutas/métodos y resto del esquema conservados. Sin lifespan, peticiones externas ni exportación nueva de JSON.

### Cobertura nueva E04 (42 casos)

- 15 acuses inválidos por identidad/tipos/versión/ronda/evaluación/acuse.
- Sobre durable y actor desde sesión; reintento pendiente conserva payload/correlación, misma clave con revisión distinta u otra clave para misma versión rechazada.
- 9 resultados inválidos: bool en versión/ronda, otra versión/evaluación/ronda, decisión no admitida, observación vacía, campo extra y operación inválida; sin mutar expediente ni crear Outcome.
- Obligación de correlación en OpenAPI y 7 casos de cabeceras faltantes/incorrectas (auth, clave y trace).
- 3 intercalados controlados de worker: error viejo tras confirmación y éxito/error viejo tras reserva nueva; recuperación posterior del intento vigente.
- 2 acuses HTTP incompatibles en GET/POST sin reenvío ciego ni reintento permanente.
- Callback adelantado: 409 sin Outcome; conciliación por GET y reintento del mismo resultado aceptado una vez.
- Caída sintética después de aceptar el fake y antes de guardar acuse: reserva impide segundo worker mientras está vigente; tras vencer se recupera desde otro engine y secuencia GET/POST/GET, un solo envío remoto/evento local.
- Identidad cruzada entre dos solicitudes con evaluaciones diferentes rechazada, sin resultados aplicados.
- Dos subsanaciones sucesivas, conflicto misma clave/contenido diferente, repetición idéntica vieja reconocida sin efecto, resultado viejo con clave nueva rechazado; v1/v2 intactas, tres versiones/entregas/resultados y cierre v3 RECHAZADA sin revise.

Las pruebas previas conservadas cubren timeout tras aceptación/respuesta perdida, consulta remota caída sin POST, máximo de reintentos, bloqueo de edición reservada, acuse falso y ciclo OBSERVADO→APROBADO. No se declara que el fake implemente todas las garantías de almacenamiento/concurrencia de EVA real.

## Estado RF y límites de evidencia

| RF | Antes E03 | Después E04 | Pendiente institucional |
| --- | --- | --- | --- |
| RF009 remisión | preparado_para_integracion local | Igual clasificación, reforzada con tipos exactos, generación de reserva, caída y reintentos comprobados | Recepción/consulta durables y dedupe EVA, URLs/credenciales/TLS, homologación de acuse/ronda/404, DA-SOL-009 |
| RF010 resultado/estado | preparado_para_integracion local | Igual clasificación, correlación explícita y recorrido de callbacks/subsanación reforzado | Emisor callback reintentable, evaluación/ronda autorizadas, estados/decisiones/resultados financieros/DA-SOL-002/008 aprobados |

No se aplican resultados de CORE como dictamen EVA ni se traduce DERIVAR. SOL gestiona el resultado externo con estados existentes de demo; no evalúa riesgo, aprueba desembolsos, acepta condiciones por el cliente ni introduce nuevas rondas sobre la misma versión.

## Pendientes y siguiente etapa

No se ejecutó MySQL, prueba concurrente de locks con procesos reales, TCP, navegador, Docker/smoke global ni proveedor EVA institucional. Los intercalados SQLite reproducen y protegen la lógica de intentos, pero no certifican aislamiento/locks MySQL. No se ejecutaron migraciones, `retry-errors` o mantenimiento sobre bases compartidas.

EVA/Bus deben confirmar endpoints/versiones/seguridad, semántica de recepción, acuse y round, persistencia/dedupe y callback de resultado. El [contrato](sol-contrato-evaluacion.md) identifica quién reintenta y cómo consultar estado. Falta evidencia institucional de extremo a extremo y actas de negocio verificables; la ausencia del PDF/tabla 80 sigue sin resolverse con una prueba fake.

Se puede continuar con **E05 — Seguridad y frontend**; no se ejecutó E05. Los modelos de respuesta/auth/errores OpenAPI pendientes y la operación de auditoría quedan para las etapas correspondientes, sin ampliar aquí el alcance a otros módulos.
