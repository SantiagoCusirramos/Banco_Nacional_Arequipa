# SOL — Adaptadores HTTP multiproveedor CAP/EVA/Auditoría

Fecha: 2026-11-15, America/Lima. Rama comprobada y conservada `feature/sol-integracion-cap-eva`, HEAD base `de4ace61f9fce7befb79828ea56133a6667eb914` más cambios locales de esta tarea, sin commit/push/merge. [Auditoría PR](sol-auditoria-pr-cap-eva.md), [contrato EVA](sol-contrato-evaluacion.md), [matriz histórica](sol-matriz-rf.md), [changelog](change-log.md).

## Resultado y alcance

SOL puede seleccionar clientes HTTP independientes de Captación, Evaluación y Auditoría, conservando sus métodos públicos, configuración Bus anterior y modo SIMULADO. Cada llamada usa la pareja destino/credencial de su canal; un fallo REAL no cambia al Bus ni al simulador. El receptor CR-INT-03 y su autenticación permanecen intactos.

CAP admite apellido materno omitido, null o vacío: SOL lo normaliza a `""`, sin fabricar PII. La salida conserva string para compatibilidad con el frontend actual. Nombres resumidos omiten ese componente, y proyección histórica trabaja sobre copia sin reescribir el expediente persistido. Mantiene los demás campos obligatorios, whitelist, ACTIVO/HABILITADO y ventana de vigencia Lima; número/bool/lista/objeto como apellido se rechazan.

**Regresión completa: 219 passed, 2 warnings, 42,16 s**, SQLite/MockTransport (169 anteriores +50 nuevos). Selección nueva: **50 passed, 2 warnings, 2,24 s**. No significa integración institucional ni ensayo conjunto TCP/MySQL. CR-INT-10 sigue exigiendo receptor/configuración completos en REAL: no se habilitó omisión, acuse local ni modo parcial nuevo.

## Selección de proveedor y compatibilidad Bus

| Configuración de un canal | Comportamiento |
| --- | --- |
| URL y token propios presentes | Usa ambos; prevalecen sobre el Bus |
| URL y token propios ausentes | Usa la pareja SOL_BUS_BASE_URL/SOL_BUS_TOKEN por compatibilidad de configuración |
| Solo uno de URL/token propios presente | ValueError explícito; no completa la pareja con el Bus |
| Sin pareja propia ni Bus suficiente en REAL | Error explícito de configuración; no arranca un proveedor REAL ficticio |
| Error, timeout, 401, JSON incompatible o redirección en proveedor propio | Conserva ese proveedor/modo; aplica los errores/reintentos existentes, sin fallback |

Se valida URL HTTP(S) con host y puerto válido, sin credenciales embebidas/query/fragmento/espacios, token ≥32 sin espacios, callback ≥32 distinto de los tokens de salida y rutas relativas válidas con sus placeholders. Las rutas de petición no pueden redirigir credenciales a un host absoluto o `//host`; httpx tiene `follow_redirects=False`, `trust_env=False`. Errores no incluyen secretos ni cuerpos remotos.

No se exige que tokens CAP/EVA/Auditoría sean distintos entre sí para no romper un Bus anterior que utiliza uno solo; para proveedores separados deben provisionarse secretos diferentes. SOL no los intercambia: el canal determina su cliente. El callback siempre debe tener otra credencial.

`Integrations.clients/reference/deliver/audit` mantienen firma y significado. `request/read` conservan parámetros anteriores y añaden `provider` opcional (`bus` por defecto); `self.client` sigue identificando el Bus. Clientes con la misma pareja efectiva se reutilizan; `close()` cierra cada cliente único. La inyección `transport` de pruebas se conserva. El cliente no decide proveedor por coincidencias de path: cada operación de dominio lo selecciona explícitamente.

Persistencia y recuperación no cambian: sobre/congelación/idOperacion, reservas/leases/generaciones, GET antes de POST EVA, presupuesto de petición/reintentos/backoff y outbox continúan en los servicios existentes. En SIMULADO, envío/acuses siguen siendo locales y las referencias se leen de la base de laboratorio; configurar URLs no activa automáticamente HTTP ni cambia el modo.

## Variables de entorno

| Variable | Función |
| --- | --- |
| `SOL_INTEGRATION_MODE` | SIMULADO o REAL, sigue siendo global |
| `SOL_CAP_BASE_URL`, `SOL_CAP_TOKEN` | Nueva pareja de Captación; por ejemplo base Docker `http://captacion:8014`, token debe coincidir con CAP_SOL_TOKEN del PR #74 |
| `SOL_EVA_BASE_URL`, `SOL_EVA_TOKEN` | Nueva pareja de Evaluación; base Docker `http://evaluacion:8015`, token coincide con EVALUACION_TOKEN_SOL del PR #70 |
| `SOL_AUDIT_BASE_URL`, `SOL_AUDIT_TOKEN` | Nueva pareja de Auditoría; **receptor pendiente de decisión**, sin URL institucional propuesta como existente |
| `SOL_BUS_BASE_URL`, `SOL_BUS_TOKEN` | Pareja anterior; se usa solo en los canales sin pareja propia. No es mecanismo de recuperación tras fallo |
| `SOL_CAP_SEARCH_PATH` | Ruta relativa configurada: `/cap/references` |
| `SOL_CAP_REFERENCE_PATH` | `/cap/references/{idCliente}` |
| `SOL_EVA_SEND_PATH` | `/eva/applications` |
| `SOL_EVA_STATUS_PATH` | `/eva/operations/{idOperacion}` |
| `SOL_AUDIT_PATH` | Ruta homologada del receptor CR-INT-10; sigue obligatoria REAL, sin default inventado |
| `SOL_EVA_CALLBACK_TOKEN` | Credencial de receptor SOL, distinta de salida; coincide con EVALUACION_SOL_TOKEN_RESULTADOS |
| `SOL_HTTP_TIMEOUT_SECONDS`, `SOL_REQUEST_BUDGET_SECONDS`, `SOL_HTTP_MAX_RETRIES`, `SOL_WORKER_SECONDS` | Conservadas: timeout default0,6s (≤3), presupuesto2,4s (<3), máximo dos reintentos y worker5s |
| `SOL_DB_*`, `SOL_POLICY_FILE` | Sin cambios; base propia y política demo propuesta |

Los cuatro paths CAP/EVA continúan siendo variables existentes explícitas; sus defaults vacíos no se sustituyen silenciosamente por rutas nuevas. Para configuración separada se pueden dejar las dos variables Bus sin definir. Para configuración Bus anterior basta conservar sus variables/paths existentes. Es válida una configuración mixta: CAP propio y EVA/Auditoría por Bus, o viceversa, siempre con parejas completas y rutas correctas.

Ejemplo parcial **no ejecutable todavía sin completar Auditoría** (secretos simbólicos, nunca copiar valores reales al repo):

```dotenv
SOL_INTEGRATION_MODE=REAL
SOL_CAP_BASE_URL=http://captacion:8014
SOL_CAP_TOKEN=<secreto CAP de al menos 32 caracteres>
SOL_CAP_SEARCH_PATH=/cap/references
SOL_CAP_REFERENCE_PATH=/cap/references/{idCliente}
SOL_EVA_BASE_URL=http://evaluacion:8015
SOL_EVA_TOKEN=<secreto EVA de al menos 32 caracteres>
SOL_EVA_SEND_PATH=/eva/applications
SOL_EVA_STATUS_PATH=/eva/operations/{idOperacion}
SOL_EVA_CALLBACK_TOKEN=<secreto callback distinto de salida>
# Faltan SOL_AUDIT_BASE_URL/TOKEN/PATH homologados, o pareja Bus real válida para ese canal.
```

En EVA la variable existente `EVALUACION_SOL_URL` debe ser la base de SOL (`http://sol:8011`), no incluir el path final: su worker añade `/sol/integrations/evaluation-results`. En frontend, REAL utiliza base `/sol` porque el alias `/gateway/sol` solo existe en SIMULADO; `SOL_PUBLIC_ORIGIN` debe corresponder al origen público. Ninguna de esas configuraciones compartidas se modificó ni activó aquí.

## Contratos conservados

| Contrato | Comportamiento preparado / límite |
| --- | --- |
| CR-INT-01 CAP | GET de búsqueda/lista acotada y referencia individual con su token; mínimos id_cliente/caso/verificación/fechas/estados/version_contrato. Apellido materno opcional se proyecta vacío. `simulado:true` de CAP se conserva aunque SOL use transporte REAL |
| CR-INT-02 EVA | POST sobre versionado + operación/correlación/idempotencia, GET de recepción antes de reenviar; valida acuse con idSolicitud/versionSolicitud/idOperacion/idEvaluacion/ronda/acuse, sin deducir ronda de versión |
| CR-INT-03 EVA→SOL | POST `/sol/integrations/evaluation-results`, Bearer exclusivo y headers X-Idempotency-Key/X-Correlation-ID coincidentes con body. Duplicado reconocido; identidad/versiones/rondas cruzadas rechazadas. APROBADO/OBSERVADO/RECHAZADO conservados |
| CR-INT-10 Auditoría | HTTP separado o Bus legado real; solo acuse positivo compatible confirma outbox. SIMULADO sigue identificado localmente; no se creó acuse institucional ni se decidió receptor |

No se cambian decisiones de negocio, identidad de fiadores institucionales, reglas de pago doble, calendario financiero, tablas o migraciones. RF001/009/010 siguen preparados para integración técnica, RF008 real/DA-SOL-006 y RF005/DA-SOL-005 mantienen bloqueos; ningún RF integrado_real por estas pruebas.

## Implementación y pruebas

Archivos funcionales: `backend/SOL/settings.py`, `integrations.py`, `schemas.py`, `service.py` y `app.py`. Este último solo cambia import/proyección de listado, **no el receptor callback/auth**. No cambios en workers/reservas, finance/policy/modelos SQL/migraciones, frontend, CAP/EVA/COREDB, dependencias o Compose compartido.

Pruebas nuevas en `backend/SOL/tests/test_providers.py`:

- Tokens/destinos separados de CAP/EVA/Auditoría y callback nunca enviado como credencial de salida; Bus puro conservado por regresión anterior y caso mixto Bus+EVA propio.
- URL/token ausentes o pareja parcial (incluso con Bus válido), callback reutilizado y URLs inválidas: error explícito sin eco; petición no puede elegir host externo.
- Timeout/401/503 de CAP no consultan otro proveedor ni SIMULADO; respuesta EVA perdida tras aceptación se concilia con GET y un único POST.
- Apellido omitido/null/vacío/texto, rechazo de tipos inválidos y de vigencia/estado/caso incompatibles; SIMULADO, listado/resumen/preview/detalle e historia sin reescritura.
- Ciclo de API SOL REAL con tres destinos fake: CAP null → alta →202/congelación → proceso de entrega → reintento idempotente → callback exclusivo → OBSERVADA → v2 → APROBADA, v1 intacta y dos envíos. Todo en memoria/MockTransport, no backend EVA institucional.

| Ejecución efectiva | Resultado |
| --- | --- |
| Reproducción antes de implementar | 29 failed, 4 passed, 2 warnings, 1,40s; campos nuevos ausentes y apellido/historia incompatibles |
| Focalizada tras implementación inicial | 33 passed, 2 warnings, 1,34s |
| Focalizada ampliada final | **50 passed, 2 warnings, 2,24s** |
| Regresión completa SOL | **219 passed, 2 warnings, 42,16s**, salida0; incluye169 anteriores y50 nuevos |
| CAP #74 en copia temporal con SOL actualizado | **35 passed, 1 skipped, 1 warning, 1,38s**; incluye cuatro tests del adaptador SOL; SQLite/COREDB falso, contrato COREDB omitido por dependencia jwt ausente |
| Caso CAP #74 sin apellido | Habilitación200, referencia/búsqueda aceptadas y marcador simulado conservado, salida0; TestClient/SQLite/MockTransport, no TCP |
| OpenAPI en memoria | Rutas/auth sin cambios; ClientResponse.apellido_materno deja de ser required y tiene default `""`; sin lifespan/BD/red |

Advertencias heredadas SOL: alias AnyIO/Starlette y opción pytest sin plugin. No se ocultaron ni se cambiaron dependencias. La regresión completa recogió ya los50 casos ampliados; no se suman ejecuciones como casos únicos. Comando desde raíz:

```bash
env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-pr-auditoria-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts= backend/SOL/tests
# Focalizadas: mismo prefijo, backend/SOL/tests/test_providers.py
```

El entorno temporal de la auditoría se reutilizó sin instalar más dependencias. Ejecución autorizada fuera del sandbox por limitación conocida de TestClient. CAP se comprobó mediante su copia temporal del SHA auditado4ea5014, sin modificar el PR ni el workspace. Se fijó SQLite en memoria y se eliminaron variables de pruebas MySQL para no heredar bases compartidas.

No se ejecutaron Docker, scripts globales, migraciones, MySQL nuevo, navegador, frontend/build/lint nuevos ni conexiones TCP institucionales. Los OpenAPI/manifiesto/lista de commit E06 se conservan como históricos: el manifiesto previo ya no describe las cinco fuentes modificadas y no se debe reutilizar sin revisar. No se sobrescribieron evidencias pasadas para aparentar que certifican este cambio.

## Conexiones listas y bloqueos

CAP y EVA tienen transporte separado listo para ensayos HTTP con sus contratos auditados, configuración completa y secretos propios. El caso CAP sin segundo apellido ya funciona con código CAP #74 en TestClient. El callback SOL queda preparado y autenticado como antes; falta demostrar el proceso EVA real publicando contra él sobre MySQL/Docker aislados.

El flujo completo **no se activa todavía**: Auditoría REAL requiere receptor/ruta/credenciales y no existe decisión homologada; sin configuración la validación falla explícitamente. También faltan composición de ensayo autorizada, credenciales y COREDB/usuario de servicio CAP aprobado (R-01), verificación de esquemas MySQL/colas EVA, proveedores institucionales/actas financieras y pruebas de callback/subsanación ante fallos reales. Los riesgos de EVA (validar acuse de callback y proteger respuestas tardías de su worker) identificados en auditoría no fueron modificados por SOL.

Siguiente acción: acordar CR-INT-10 con Seguridad y preparar configuración/entorno de integración aislado en una tarea autorizada; entonces probar CAP→SOL→EVA→SOL con datos sintéticos, errores y reinicios. No sustituir ese acuerdo por un receptor inventado, no usar SQL directo ni relajar reglas financieras para completar la demostración.
