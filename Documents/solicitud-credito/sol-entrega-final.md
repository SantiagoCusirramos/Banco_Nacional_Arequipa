# E06 — Entrega final SOL

Fecha: 2026-11-14, America/Lima. Base `86904edd8dc866c1d4260a996748a1cda3770007`, rama `feature/integracion-sol`, cambios E02–E06 sin commit/push. [Evidencias y reproducción](sol-evidencias-testing.md), [matriz histórica y actual](sol-matriz-rf.md), [changelog](change-log.md).

## Dictamen

**SOL validado localmente y preparado para integración condicionada; ningún RF está integrado_real.** Cinco RF implementados en el perfil académico, tres preparados para consumir contratos y dos bloqueados por decisión institucional con parte local verificable. No corresponde afirmar 10/10 funcionales institucionales: pago doble no tiene fórmula aprobada y la validación real de fiadores no está homologada.

Regresión final: backend **169 SQLite + 169 con fixtures MySQL**, dos advertencias por ejecución; frontend **114 aprobadas + dos fallos esperados heredados**, lint/TypeScript/build aprobados. **142 comprobaciones TCP**, siete de migración/rollback/locks y cuatro de logs/reinicio. Las cifras no son casos únicos sumables: las regresiones repiten el mismo conjunto. Datos sintéticos; CAP/EVA/Auditoría simulados. E2E navegador real y proveedores institucionales pendientes.

## Matriz final de los diez RF

| RF | Estado al cierre / fuente | Pruebas ejecutadas | Bloqueo / recomendación |
| --- | --- | --- | --- |
| 001 Cliente captado | `preparado_para_integracion`; `backend/SOL/integrations.py:189`, `app.py:271` | Gate habilitado/estado/vigencia/ID, errores/timeouts/JSON/PII y refresco en suite SQLite/MySQL; referencia demo en TCP | CAP debe publicar CR-INT-01 completo con caso/verificación/vigencia autoritativos, búsqueda, IDs y seguridad. COREDB cliente existente es parcial y no lo sustituye; DA-SOL-007 |
| 002 Plazo | `implementado_local`; `schemas.py:31`, `service.py:24` | Límites inclusivos, entero estricto, rollback, revisión; edición/calendario TCP | Ratificar DA-SOL-001; 6–60 meses es propuesta académica |
| 003 Monto | `implementado_local`; `service.py:24`, `finance.py:13` | Extremos, Decimal/centavos, inválidos sin mutación, persistencia y recálculo en ambos motores/TCP | Ratificar DA-SOL-001; 1000–50000 PEN propuesto |
| 004 Moneda | `implementado_local`; `service.py:24`, `policy.py` | PEN, rechazo USD/formato, política histórica y snapshots; rechazo TCP | Aprobar catálogo DA-SOL-001; no conversión automática |
| 005 Pago doble | `bloqueado_decision`; `policy.py`, `service.py:24` | Rechazo del flag y de política que lo habilite sin regla, sin calendario ficticio; TCP 422 | DA-SOL-005: fórmula, meses, interés/amortización y redondeo aprobados; luego implementar y probar |
| 006 Calendario | `implementado_local`; `finance.py:13`, `service.py:152` | Fechas/Decimal/centavos/totales/saldo cero y conservación histórica; TCP/reinicio MySQL | Aprobar DA-SOL-003/004; calendario PRELIMINAR, TEA 22%, francés/días360/30 días propuestos, sin TCEA definitiva |
| 007 Garantías | `implementado_local` como declaración básica; `schemas.py:19`, `service.py:24` | Catálogo, valor/cantidad/rollback, edición/freeze/versiones, garantía TCP | DA-SOL-006 para obligatoriedad, soportes/tasación institucional; no certificación de la garantía |
| 008 Fiadores | `bloqueado_decision` real; registro local implementado; `integrations.py:210` | Referencias 1–36/máx5, duplicados/autofiador/estado, whitelist/histórico, rechazo REAL; fiador SIMULADA TCP | Homologar identidad y validación DA-SOL-006. No reutilizar CAP automáticamente ni inventar verificación |
| 009 Remisión | `preparado_para_integracion`; `app.py:390`, `operations.py:30` | Clave/sobre inmutables, timeout/consulta/reintento/202/generaciones/crash con MockTransport y fixtures MySQL; envío/reintento demo TCP | EVA/Bus CR-INT-02 con dedupe durable, GET por operación, acuse/evaluación/ronda/404/seguridad y DA-SOL-009. 202 solo reserva local |
| 010 Resultado/estado | `preparado_para_integracion`; `app.py:531`, `app.py:443` | Callback servicio, versión/evaluación/ronda/operación/correlación, duplicado/conflicto/viejo y subsanaciones en suites; OBSERVADA→v2→APROBADA demo TCP | Emisor EVA reintentable, CR-INT-03, estados/resultados DA-SOL-002/008 aprobados. No decisión de riesgo ni desembolso SOL |

Persistencia complementaria E06: fecha de respuesta usa valor canónico MySQL; registro/snapshot/sesión se conservan al reiniciar SOL. La precisión DATETIME no se cambió. Los cinco implementado_local y tres preparado_para_integracion tienen cobertura técnica del alcance definido; el registro parcial de RF008 no cierra su validación y el rechazo seguro de RF005 no calcula pago doble.

## Integraciones y guía de consumo

URLs del laboratorio: backend `http://127.0.0.1:18016`, frontend `http://127.0.0.1:13016/solicitud-credito`. Rutas canónicas `/sol`; `/gateway/sol` es alias en el mismo proceso únicamente SIMULADO. OpenAPI [SIMULADO servido](sol-openapi-e06-simulado.json) / [REAL generado sin proveedor](sol-openapi-e06-real.json). Swagger local `/docs`. Dinero JSON como string decimal, fechas `YYYY-MM-DD`, eventos UTC con Z. Los JSON contienen esquemas completos; no secretos ni aprobación de negocio.

| Consumidor / propietario | Endpoints confirmados de SOL | JSON / autenticación / respuesta |
| --- | --- | --- |
| Frontend / SOL | POST `/sol/auth/login`; GET `/sol/auth/me`; POST `/sol/auth/logout` | Login `{username,password}` → `{token,usuario}`; Bearer **opaco local**, no JWT/SSO. Proxy entrega solo usuario/cookie HttpOnly; logout 200 y uso posterior 401 |
| Asesor / SOL | GET `/sol/clients?search=&limit=`, GET `/sol/policy` | Referencias mínimas y política/marcador integración; sesión requerida. Proveedor remoto inválido 503, no referencia inventada |
| Asesor / SOL | POST `/sol/preview`, POST `/sol/applications`, PUT `/sol/applications/{identifier}` | `ApplicationInput`: id_cliente,monto_solicitado,moneda,plazo_meses,destino_credito,fecha_base,pago_doble,garantias,fiadores; edición añade revision. Preview 200, alta 201, edición 200; 409 revisión/freeze, 422 datos/política |
| Lectores / SOL | GET `/sol/applications?limit=&offset=`, GET `/sol/applications/{identifier}` | Página/conteos; detalle con condiciones/calendario, versiones, eventos, envíos/resultados mínimos. 401 sesión, 404 inexistente |
| Asesor / SOL | POST `/sol/applications/{identifier}/send` | `{revision}` + `X-Idempotency-Key`; 200 confirmado o **202 reserva pendiente**, no acuse institucional. Reintentar misma clave y cuerpo; conflicto 409 |
| Asesor / SOL | POST `/sol/applications/{identifier}/revise` | `{revision}`; solo OBSERVADA, nueva versión BORRADOR sin sobrescribir anterior; 200/409 |
| Evaluador demo / SOL | POST `/sol/applications/{identifier}/demo-result` | `{version,decision,observaciones}` + clave; solo SIMULADO/rol EVALUADOR. Estado de demo, no servicio EVA |
| EVA servicio / SOL | POST `/sol/integrations/evaluation-results` | EvaluationResult + Bearer callback distinto + `X-Idempotency-Key`=idOperacion y `X-Correlation-ID`=idCorrelacion; 200/401/404/409/422/503. No pasa por proxy navegador |
| Operadores / SOL | GET `/sol/ops/pending`, GET `/sol/ops/metrics` | Supervisor/auditor; pendientes y métricas en memoria. No endpoint para prometer SLA |
| Supervisor / SOL | POST `/sol/admin/users/{username}/disable` | `{motivo}`; baja local y revoca todas las sesiones; 403 otros roles/409 autobaja |
| Operación / SOL | GET `/health`, `/ready` | 200 liveness; readiness 200/503 con schema, comprueba BD |

Sesiones y roles se validan en backend. 401 no equivale a 403 de permiso ni a 503 por caída/proveedor. Errores conservan `detail` string/objeto/lista; no reintentar validaciones 422 o conflicto 409 a ciegas. Envío pendiente conserva operación, snapshot y correlación; workers consultan antes de repostear. Alta de borrador no es idempotente por la clave de envío. Ronda de EVA no se deduce de versión salvo dentro del simulador explícito.

Ejemplo **simbólico** del callback (reemplazar con identidad y ronda de recepción confirmada, no generarlas):

```json
{"idSolicitud":"<solicitud>","versionSolicitud":1,"idEvaluacion":"<evaluacion>","ronda":1,"idOperacion":"<operacion-resultado>","idCorrelacion":"<correlacion>","decision":"OBSERVADO","observaciones":"<observacion externa>"}
```

| Contrato / responsable externo | Adaptador disponible / rutas del simulador existente | Pendiente real |
| --- | --- | --- |
| CR-INT-01 / Captación | GET búsqueda y GET referencia; simulador `/cap/references`, `/cap/references/{identifier}` | No backend CAP desplegado compatible confirmado; caso/identidad/verificación/habilitación/vigencia deben provenir del dueño. [Análisis COREDB](sol-captacion-coredb.md) |
| CR-INT-02 / Evaluación | POST sobre versionado y GET por operación; simulador `/eva/applications`, `/eva/operations/{operation}` | No EVA real compatible confirmado; contrato con dedupe, recepción durable y consulta autoritativa. [Contrato EVA](sol-contrato-evaluacion.md) |
| CR-INT-03 / Evaluación→SOL | Receptor SOL implementado y probado con MockTransport/fixtures MySQL; demo TCP separado | Emisor institucional y reintentos durables por homologar; no se fabrican evaluaciones/rondas |
| CR-INT-10 / Seguridad | Outbox y POST configurables; simulador `/security/events`, acuse `{idEvento,confirmado:true,acuse}` | Prototipo `/seguridad/...` no implementa ese contrato; faltan identidad central, roles, SSO/MFA, dedupe, retención, TLS y operación institucional |

**Las rutas de esa tabla externa son del simulador SOL existente o plantillas de adaptador, no endpoints institucionales confirmados.** CORE legado y COREDB no se modificaron ni se conectaron por SQL; sus APIs parciales no cierran estos contratos.

Configuración backend: `SOL_DB_HOST/PORT/NAME/USER/PASSWORD`, `SOL_POLICY_FILE`, `SOL_INTEGRATION_MODE`; en REAL exige `SOL_BUS_BASE_URL`, `SOL_BUS_TOKEN`, `SOL_EVA_CALLBACK_TOKEN` distintos ≥32 caracteres, `SOL_CAP_SEARCH_PATH`, `SOL_CAP_REFERENCE_PATH` con `{idCliente}`, `SOL_EVA_SEND_PATH`, `SOL_EVA_STATUS_PATH` con `{idOperacion}`, `SOL_AUDIT_PATH`. Timeout/presupuesto/reintentos/worker: `SOL_HTTP_TIMEOUT_SECONDS`, `SOL_REQUEST_BUDGET_SECONDS`, `SOL_HTTP_MAX_RETRIES`, `SOL_WORKER_SECONDS`. Configuración incompleta falla, nunca fallback. No basta cambiar el modo para homologar un proveedor.

Frontend solo servidor: `SOL_GATEWAY_URL` (SIMULADO `/gateway/sol`; REAL `/sol`), `SOL_PUBLIC_ORIGIN` (origen público HTTP(S) exacto, sin ruta/trailing slash/credenciales), `SOL_COOKIE_SECURE=true` para HTTPS. Sin origen explícito conserva comparación con nextUrl; **Docker/reverse proxy pueden ver origen interno, por lo que deben configurar el público**. No se acepta Forwarded del cliente como autoridad. Compose global quedó intacto y su despliegue público requiere ese ajuste operativo autorizado. La configuración REAL no se activó.

## Cambios y auditoría final

E02–E05 conservan validaciones financieras/respaldos, minimización, adaptadores estrictos, idempotencia/conciliación/causalidad, outbox y OpenAPI/RBAC/UI. E06 corrigió exclusivamente tres brechas verificadas: proyección de fecha persistida (`service.py:152`), origen público del proxy SOL y query sensible en access log Uvicorn (`observability.py:19`, lifespan `app.py:69`). Más cuatro tests de fecha, dos de logging y cinco frontend; el test E05 de vencimiento se adaptó al deadline almacenado. El filtro se limita al ciclo de vida SOL y al formato fijado Uvicorn 0.30.6; no reemplaza redacción/retención institucional. Paths/IDs operativos siguen visibles.

No cambios en otros módulos, modelos SQL, migraciones, políticas, Compose global, CI, package/lock/config Next/Vitest. El único Compose nuevo y scripts de evidencia residen en documentación SOL. Git mantiene diez archivos seguidos modificados más tests/documentos sin seguimiento; los aportes previos AGENTS/plan/prompts/README se preservan. Se revisaron también archivos sin seguimiento: no hay `.env` privado/dumps/BD/claves privadas agregados ni marcadores de conflicto. Los fixtures contienen claves/identidades sintéticas preexistentes, no credenciales institucionales. Escaneo limitado por patrones y comprobación de secretos efímeros, no certificación universal de ausencia de secretos.

## Entrega revisable, rollback y siguientes acciones

Resumen de PR **sin crear/publicar**: completar el alcance local SOL y endurecer contratos/seguridad/recuperación; preservar perfil académico y proveedores simulados; adjuntar matriz, OpenAPI y evidencias de 169 casos backend, 114 frontend y TCP/MySQL. Riesgos principales: acuerdos financieros pendientes, ausencia de proveedores, origen/TLS de despliegue y dependencias transitivas no totalmente fijadas; no llamar a esta entrega certificación productiva.

Rollback local: detener únicamente servicios del proyecto `bna-sol-e06` con el archivo/env de laboratorio; conservar diff y artefactos para revisión. No reset/checkout/clean ni restauración masiva sobre trabajo ajeno. MySQL tmpfs es desechable y pierde datos al detenerlo; no contiene datos reales. En un futuro despliegue persistente, respaldar y probar restauración antes de migrar, respetar reserva/versiones/outbox; no revertir columnas ni borrar entregas para ocultar fallos. Retirar cambios por archivo solo mediante revisión coordinada, nunca ejecutar rollback de una base institucional desde este ensayo.

Próximo trabajo: Captación debe entregar contrato/URL/credenciales/fuente autoritativa de CR-INT-01; Evaluación recepción/consulta/dedupe/callback CR-INT-02/03; Seguridad autenticación central/roles/revocación/CR-INT-10/TLS/retención; negocio debe resolver DA-SOL-001..009, especialmente 005/006. Con esos insumos, realizar homologación y ensayo institucional autorizado, más E2E navegador y despliegue público. **E06 cierra validación local y entrega documental; no cierra integración bancaria ni autoriza producción.**

Estado operativo de cierre: laboratorio E06 detenido con salida 0, sin contenedores activos ni volúmenes persistentes de ese proyecto; tmpfs sintético descartado. Evidencias y [manifiesto](sol-e06-manifiesto.json) conservados. Ninguna base/volumen institucional tocado.
