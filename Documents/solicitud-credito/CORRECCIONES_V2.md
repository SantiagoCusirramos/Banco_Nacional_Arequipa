# Correcciones del MVP v2

Fecha de entrega: 23/10/2026. Código basado en el MVP v1 local proporcionado. No se modificó ninguna rama remota ni otro módulo del banco.

| Pedido | Cambio realizado | Prueba principal |
|---|---|---|
| 1. Fecha nocturna | `clock.business_today()` usa America/Lima en guardado, envío, Captación y seed. El formulario también calcula Lima. Los instantes del historial siguen en UTC. `tzdata` permite ejecutar ZoneInfo en Windows. | `test_lima_night_creation_and_send_no_false_stale`; `test_lima_midnight_really_expires_old_base`. |
| 2. Adaptadores HTTP | Modo REAL configurable vía Bus, sin fallback a referencias locales. Validación de configuración; timeout y máximo dos reintentos por ciclo. CR-INT-03 entra como callback autenticado. | Casos `test_cr01_*`, `test_cr02_*`, `test_real_requires_*`; recorrido HTTP local. |
| 3. Resultado real | Callback con token de servicio, idEvaluacion y ronda ligados al acuse. Valida correlación y operación; rechaza versión antigua y mensaje repetido diferente. Demo bloqueada en REAL. | `test_cr03_callback_auth_round_version_and_full_v2_cycle`. |
| 4. Consulta antes de repetir | Reserva persistente, versión congelada, consulta por idOperacion antes de cada POST; sin consulta disponible no hay reenvío ciego. | Timeout tras aceptación: GET/POST/GET y un solo expediente remoto. Recuperación de pendiente desde otra conexión a la base. |
| 5. Auditoría | Outbox transaccional con identificador de evento estable, reserva temporal, acuse y reprogramación. Worker interno y comando manual. SIMULADO se distingue de CONFIRMADO. | `test_cr10_outbox_survives_failure_recovers_and_deduplicates`; rollback conjunto. |
| 6. Logs/correlación | JSON a stdout con ruta normalizada, duración, estado, idOperacion/idCorrelacion. Cabecera devuelta por API y puente. Sin cuerpos, query, claves o tokens en logs. | `test_correlation_logs_and_measured_p95`; control de secretos en log de accesos. |
| 7. Readiness | `/health` sigue verificando el proceso; `/ready` ejecuta SELECT 1 y devuelve 503 si falla la base. | `test_readiness_when_db_fails_but_liveness_remains`. |
| 8. p95 | Medición real por operación, ventana máxima 10 000 muestras por proceso; endpoint restringido de métricas. | Mismo caso de correlación/p95. No se fija un SLA ni se inventa una meta. |
| 9. Baja/sesiones | Supervisor local puede deshabilitar otra cuenta y revocar todas sus sesiones. Se rechaza el ingreso y uso de la sesión retirada. Limpieza de sesiones e intentos vencidos. | `test_session_revocation_and_cleanup`. El rol institucional debe homologarse. |
| 10. Accesos de seguridad | Eventos de ingreso exitoso, fallo, bloqueo, cierre y baja con outbox. El contador usa identidad normalizada; variar mayúsculas no evita el bloqueo. | `test_access_events_lockout_and_no_secrets_in_logs`. |
| 11. Datos de cliente | Lista mínima para todos los roles, sin celular/correo/nacimiento. También se filtran versiones históricas y referencias al consultar/exportar detalles. | `test_client_and_legacy_detail_minimization_all_roles`. Se reducen datos expuestos; no se declara cumplimiento legal integral. |
| 12. Bandeja | Paginación 1–100, página de 50 en UI, total/conteos por estado; join de versión vigente en consulta única de filas. Búsqueda visual rotulada por página. | `test_paginated_listing_has_constant_query_count_and_detail_no_lock`. |
| 13. Lectura | GET de detalle no pide bloqueo de fila. Los cambios mantienen bloqueo/revisión. | Caso anterior; ejecutado también con MySQL. |
| 14. Canal digital | Puente Next.js aborta a 3 s. En REAL el envío se reserva con 202 y el worker gestiona HTTP. La UI no anuncia recepción ante un 202. | Compilación, revisión del puente y recorrido HTTP local. |
| Adicional de MySQL | Historial ordenado por versión y revisión, sin depender de UUID cuando varios eventos comparten hora al segundo. | `test_event_order_follows_revision_when_mysql_timestamps_tie`. |

## Qué conserva la actualización

El archivo `politica_demo.json` y el cálculo `finance.py` conservan exactamente el contenido de v1. No se programan pago doble, estados oficiales ni obligatoriedad de garantías. Se mantienen las decisiones y estados de demostración existentes, pendientes de aprobación. Los fiadores institucionales se rechazan explícitamente en REAL mientras su contrato no esté homologado; no se sustituye esa validación por una referencia sintética.

La autenticación de trabajadores sigue siendo local. El callback tiene credencial de servicio separada; ello no equivale a integración con Seguridad central, MFA, roles institucionales o cumplimiento regulatorio certificado.

## Actualizar una instalación v1

Con backend detenido y una copia de seguridad de tu base, desde `backend`:

```powershell
.\.venv-sol\Scripts\python.exe -m pip install -r requirements-sol.txt
.\.venv-sol\Scripts\python.exe -m SOL.manage migrate
.\.venv-sol\Scripts\python.exe -m pytest SOL/tests -q
```

Conserva `.env.sol` y `.env.local`; no los reemplaces por los ejemplos. No borres tu base ni tu entorno virtual. `migrate` añade columnas/tablas y no cambia contraseñas. Los envíos antiguos se identifican como SIMULADO; no se reenvían al pasar a REAL. En MySQL el DDL se confirma por columnas y puede reanudarse: respalda antes de actualizar. Las filas históricas que no tenían revisión conservan ese dato como 0; no se inventa su orden temporal anterior.

Arranca backend y frontend como antes. Para integración consulta `CONTRATOS_HTTP_V2.md`; para resultados y capturas consulta `VALIDACION.md` y `evidencias-v2/indice.html`.

## Referencias técnicas para mantenimiento

- Python ZoneInfo: https://docs.python.org/3/library/zoneinfo.html
- HTTPX, timeouts: https://www.python-httpx.org/advanced/timeouts/
- HTTPX, transportes y simulación: https://www.python-httpx.org/advanced/transports/

Estas referencias explican herramientas; las reglas financieras y contratos del proyecto deben ratificarlos sus responsables.
