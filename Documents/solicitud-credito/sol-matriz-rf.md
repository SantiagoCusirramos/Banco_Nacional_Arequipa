# Matriz de trazabilidad RF-SOL-001..010 — E01 y actualización E02

Fecha: 2026-11-14, America/Lima. Base HEAD `86904edd8dc866c1d4260a996748a1cda3770007`. La tabla siguiente conserva el diagnóstico E01; los cambios funcionales E02 del workspace y la evidencia actual se registran al final. [Contratos E01](sol-contratos-finalizacion.md), [auditoría P00](sol-auditoria.md), [baseline P01](sol-baseline.md), [detalle E02](sol-funcionalidades-internas.md).

Clasificación de E01: `implementado_local` describe cobertura del perfil académico; `preparado_para_integracion` describe borde técnico probado con fake, no homologado; `bloqueado_decision` impide cerrar la función institucional; `integrado_real` exige proveedor y evidencia de extremo a extremo. **Ningún RF está integrado_real.** Las celdas de criterio son objetivos verificables de cierre, no afirmaciones de cobertura total. Los tests mencionados integran las 52 pruebas aprobadas P01 (SQLite/fake, 2 warnings, 14,75 s) del mismo código; E01 no los ejecutó otra vez. Tests aún necesarios se indican expresamente.

Las rutas son canónicas `/sol`; las operaciones del router tienen alias `/gateway/sol` solo SIMULADO. `mvp_sol_*` es persistencia local; no implica autorización de escritura COREDB. Fuentes backend relativas a `backend/SOL/`.

| RF / estado | Criterios de aceptación local y límite institucional | API / implementación | Persistencia | Tests y evidencia reutilizada; pendiente |
| --- | --- | --- | --- | --- |
| 001 Cliente captado — `preparado_para_integracion` | Aceptar referencia ACTIVO/HABILITADO vigente Lima e ID coincidente; rechazar ausente, bloqueada, vencida y transporte inválido sin fallback. Cierre institucional requiere CAP real CR-INT-01/DA-SOL-007 | GET `/sol/clients`, POST `/sol/preview`, POST/PUT `/sol/applications`, send; `integrations.py:78`, `:150`, `:163`, `:176`; `app.py:242` | Referencia mínima en `ClientReference` (`models.py:55`) y snapshot por versión | `test_captacion_gate`, `test_cr01_real_adapter_gate_with_http_simulator`, `test_real_never_falls_back_to_local_reference`; P01 fake. Pendiente proveedor, vigencia/caso autoritativos y pruebas reales; búsqueda solo normaliza, no toda regla individual |
| 002 Plazo — `implementado_local` | Entero y rango de política vigente, límites inclusivos; edición recalcula y respeta revisión/congelación. DA-SOL-001 para límites oficiales | POST preview/alta, PUT edición; `schemas.py:30`, `service.py:36`, `app.py:336` | `Version.snapshot.condiciones.plazo_meses` y política, `models.py:76` | `test_month_boundaries`, `test_optimistic_concurrency`, `test_idempotency_and_frozen_version`, P01. Consolidar negativos DTO fraccionario y persistencia según E02; no ampliar 6–60 sin acuerdo |
| 003 Monto — `implementado_local` | Decimal 15/2, positivo y rango vigente; no usar float en cálculo; conservar monto histórico y recalcular borrador. DA-SOL-001 | POST preview/alta, PUT edición; `schemas.py:28`, `service.py:29`, `finance.py:14` | String decimal en snapshot JSON y política | `test_amount_boundaries`, `test_policy_changes_require_recalculation_but_preserve_sent_policy`, P01. Verificar cobertura específica exceso de decimales y rollback antes de añadir tests; 1000–50000 es demo |
| 004 Moneda — `implementado_local` | Solo catálogo vigente; rechazar moneda no habilitada, sin conversión silenciosa; conservar moneda/versionado. DA-SOL-001 | GET policy y operaciones de condiciones; `config/politica_demo.json:6`, `service.py:27`, `policy.py:48` | Condiciones y política en snapshot | `test_fiadores_currency_and_double_payment` rechaza USD y `test_policy_changes_require_recalculation_but_preserve_sent_policy`, P01; validar casos adicionales de formato en E02 según brecha real |
| 005 Pago doble — `bloqueado_decision` | Hoy true debe devolver rechazo explícito y no generar fórmula. Solo cerrar cálculo con DA-SOL-005 suficiente, meses, interés/amortización/redondeo y pruebas | POST preview/alta, PUT; `service.py:45`, `policy.py:44`, `schemas.py:33` | Flag false preservado en condiciones; no calendario de pago doble | `test_fiadores_currency_and_double_payment`, P01: rechazo true. Pendiente política aprobada; bloqueo seguro local no equivale RF calculado |
| 006 Calendario preliminar — `implementado_local` | PRELIMINAR con Decimal/ROUND_HALF_UP, capital sumado y saldo final cero; fechas Lima y periodos de política; regenerar borrador sin mutar versión enviada. DA-SOL-003/004 | POST preview/alta, PUT, GET detalle; `finance.py:14`, `clock.py:12`, `service.py:74`, `app.py:336` | Calendario, política y condiciones en `Version.snapshot`, `models.py:76` | `test_calendar_invariants`, tests Lima noche/medianoche, `test_subsanation_preserves_old_snapshot_and_rejects_stale_results`, P01; 6 comprobaciones aisladas P00. Falta ratificación financiera; no declarar TCEA/calendario definitivo |
| 007 Garantías — `implementado_local` (declaración básica) | Tipo permitido, descripción, valor Decimal positivo, máximo 10; edición por revisión, snapshot íntegro/congelado. Obligatoriedad/soportes institucionales requieren DA-SOL-006 | `Guarantee`, ApplicationInput, POST/PUT expediente; `schemas.py:18`, `:34`, `service.py:72` | Garantías en `snapshot.condiciones.garantias`, no maestro independiente | `test_fiadores_currency_and_double_payment` caso positivo y tests generales de congelación, P01. Pendiente cobertura específica negativa de catálogo/valor/cantidad y persistencia histórica de garantías en E02; no afirmar RF completo |
| 008 Fiadores — `bloqueado_decision` (validación real) | Registro local trazable sin autofiador ni duplicados; referencias activas sintéticas; REAL rechaza mientras falte contrato; no fabricar identidad. DA-SOL-006 | `schemas.py:35`, `service.py:54`; POST/PUT expediente | IDs/snapshot de identidad y marcador SIMULADA en `snapshot.fiadores` | `test_fiadores_currency_and_double_payment`, P01: rechazo autofiador/inexistente y caso positivo sintético. E02 debe revisar formatos y cobertura duplicados/rechazo REAL, sin confundir validación activa con CAP habilitado |
| 009 Remisión EVA — `preparado_para_integracion` | Reserva durable/congelada antes de HTTP; misma clave sin duplicar; GET recepción antes de POST; no repetir si consulta falla; acuse íntegro y recuperación tras caída; CR-INT-02/DA-SOL-009 | POST `/sol/applications/{identifier}/send`; GET detalle y ops/pending; `app.py:361`, `integrations.py:102`, `operations.py:30` | Delivery PK operación, unique solicitud/versión, lease/backoff, snapshot congelado (`models.py:102`) | Tests `test_cr02_timeout_after_acceptance_is_reconciled_without_second_post`, `test_cr02_failed_status_consult_never_reposts_and_survives_restart`, `test_cr02_max_two_retries_and_no_edit_of_reserved_version`, `test_cr02_rejects_mismatched_receipt_without_changing_business_state`; P01 fake. Pendiente dedupe durable EVA, ronda/acuse reales y concurrencia MySQL |
| 010 Resultado/estado — `preparado_para_integracion` | Callback servicio auténtico y coherente con versión/evaluación/ronda; repetido idéntico reconocido y conflicto rechazado; subsanación nueva preserva historia; CR-INT-03/DA-SOL-002/008 | POST `/sol/integrations/evaluation-results`, revise, GET detalle; `app.py:501`, `:413`; demo-result separado `:446` | Outcome PK operación/fingerprint y Event/Version (`models.py:125`, `:88`, `:76`) | `test_cr03_callback_auth_round_version_and_full_v2_cycle`, `test_subsanation_preserves_old_snapshot_and_rejects_stale_results`, P01 fake. Pendiente emisor EVA real, estados/condiciones resultantes homologados; SOL no aprueba desembolsos |

## Cobertura transversal y acuerdos

- Auth/roles/privacidad: `test_readonly_roles_cannot_create`, `test_session_logout_and_actor_cannot_be_spoofed`, `test_assessor_cannot_evaluate`, tests v2 de revocación, accesos y minimización; implementados en `app.py:124`, `:188`, `service.py:228`. No se acredita SSO/MFA/CSRF institucional ni privacidad de cada error de validación.
- CR-INT-10: `test_cr10_outbox_survives_failure_recovers_and_deduplicates` y `test_event_and_outbox_rollback_together`; outbox `operations.py:17`, `:75`, `models.py:148`. Preparación local, receptor Seguridad compatible ausente.
- Lecturas/persistencia: `test_persistence_after_restart`, `test_paginated_listing_has_constant_query_count_and_detail_no_lock`, `test_incremental_migration_preserves_v1_records` y test de orden de eventos; P01 SQLite. No garantiza semántica de locks ni DDL de MySQL.
- DA numeradas: trazabilidad heredada del plan anterior y P00, no texto de acta verificado; falta el original ITIL/tabla 80 para confirmar correspondencias exactas. No se inventan CP ni decisiones aprobadas.

La clasificación cambia respecto a «parcial» de P00 por la taxonomía requerida por E01, **sin cambio de código ni nueva certificación**. RF007 se etiqueta implementado_local solo para declaración básica, con pendientes explícitos. RF001/009/010 tienen borde preparado con contrato propuesto, no `listo_contrato` homologado.

## Continuidad E02

Sí puede ejecutarse E02 para RF002–008 dentro del perfil local existente: comprobar primero cada prueba/criterio y cambiar únicamente brechas verificadas. Prioridades: negativos de DTO/garantías/fiadores, persistencia y snapshots de respaldos, compatibilidad con UI y bloqueo de pago doble. No rehacer calendario/colas que ya satisfacen criterios. La falta de DA-SOL-005 bloquea pago doble funcional; la falta del contrato de identidad bloquea cierre institucional de RF008. Las demás políticas conservan marcador propuesto. Proveedores reales se abordan con E03/E04/E05 y evidencia en E06; ningún pase fake elimina esos bloqueos.

## Actualización E02 — estado actual del workspace

La tabla E01 queda como línea base; sus referencias archivo:línea corresponden al código anterior a E02. `tests/test_workflow.py` y `tests/test_integration_v2.py` incorporan 20 casos; código funcional modificado solo en schemas/integrations/service. Los detalles antes/después y comandos están en [sol-funcionalidades-internas.md](sol-funcionalidades-internas.md). Regresión actual **72 passed, 2 warnings in 18.62s**, salida 0; SQLite y MockTransport, sin MySQL ni instituciones reales.

| RF | Estado E02 | Criterio consolidado / API y persistencia | Evidencia actual | Bloqueo |
| --- | --- | --- | --- | --- |
| 001 | preparado_para_integracion, sin ampliación | Referencia CAP y snapshot, rutas actuales conservadas | Regresión de casos CR01 sin fallos | CAP real/DA-SOL-007, E03 |
| 002 | implementado_local consolidado | DTO entero y política dinámica en preview/alta/edición, snapshot | Bordes previos + negativos de tipo y rango E02, rollback y política temporal | DA-SOL-001 |
| 003 | implementado_local consolidado | Decimal, precisión/rango y persistencia, sin cambio de límites | Bordes previos + NaN/Infinity/precisión, rollback y bordes de política temporal E02 | DA-SOL-001 |
| 004 | implementado_local consolidado | PEN de política vigente; sin conversión; condiciones en snapshot | USD/minúsculas/longitud inválida rechazados en las tres rutas sin efectos | DA-SOL-001 |
| 005 | bloqueado_decision; bloqueo local verificado | true en request 422; política con flag habilitado 503; sin mutar/enviar expediente | Pruebas previas + `test_e02_payment_double_policy_cannot_bypass_block` | DA-SOL-005, sin fórmula/meses aprobados |
| 006 | implementado_local consolidado | Calendario preliminar Decimal intacto, recálculo/fechas/histórico | Cinco escenarios centavos/extremos/bisiesto/tasa cero E02 + pruebas previas, versión enviada intacta | DA-SOL-003/004 |
| 007 | implementado_local de declaración, con cobertura específica | Garantías DTO + snapshot, máximo diez; edición por revisión y versiones | Catálogo completo/máximo/negativos, rollback y respaldo v1 persistido tras retirar en v2 | DA-SOL-006: obligación y verificación institucional |
| 008 | registro local consolidado; bloqueado_decision institucional | Strings 1–36, máximo cinco; `integrations.guarantor_reference`, SIMULADA o rechazo REAL; proyección mínima histórica sin reescritura | Formato/duplicados/autofiador/inexistente/bloqueado, whitelist/histórico/todos los roles; REAL fake sin mutación ni POST remoto | DA-SOL-006; sin proveedor/contrato de identidad |
| 009 | preparado_para_integracion, sin ampliación | Remisión/acuse/cola conservados | Regresión de CR02/idempotencia/reservas sin fallos | EVA real/DA-SOL-009, E04 |
| 010 | preparado_para_integracion, sin ampliación | Callback/subsanación/historial conservados | Regresión CR03/versión/ronda sin fallos | EVA real/estados/DA-SOL-002/008, E04 |

Los JSON OpenAPI E01 permanecen históricos; comparación en memoria en E02 confirma única diferencia: límites de cada string de fiador. Ninguna ruta/método cambia. Ningún RF pasa a integrado_real. Siguiente etapa recomendada: E03, sin ejecutar todavía.

## Actualización E03 — Captación y autoridad de datos

[Informe E03](sol-captacion-coredb.md). HEAD base igual, cambios E02 preservados más validación focalizada de integrations y tests E03. Regresión actual **107 passed, 2 warnings in 19.28s**, salida 0, SQLite/MockTransport (72 anteriores +35 nuevos). No se certifican proveedores reales ni MySQL.

| RF/contrato | Estado después de E03 | Evidencia / pendiente |
| --- | --- | --- |
| RF001 / CR-INT-01 | preparado_para_integracion local, no integrado_real | Búsqueda/lista acotada y referencia GET configurables; tipos/fechas/JSON inválidos rechazados, campos autoritativos no inventados, sin fallback por fallos de transporte o adapter ausente. 35 pruebas E03 de éxito/error/auth/timeout/PII/ID/estado/vigencia y doble consulta. Fuentes `backend/SOL/integrations.py:64`, `:84`, `:155`, `:188` |
| RF001 / DA-SOL-007 | bloqueado para cierre institucional | COREDB GET cliente no tiene caso/vencimiento/búsqueda requeridos; timestamp de verificación e IDs difieren. Falta CAP/fachada autorizada completa, mapeo, versiones, credenciales y ensayo institucional. No se conecta COREDB ni se accede a tablas ajenas |
| RF008 / DA-SOL-006 | sin cambio: registro local consolidado, validación real bloqueada | No reutiliza CAP automáticamente como identidad de fiador; borde E02 y privacidad conservados por regresión |
| RF002–007, RF009–010 / CR-INT-02/03/10 | estados E02 conservados | Todas las 72 pruebas anteriores pasan. Transporte común rechaza null como respuesta contractual, sin cambiar rutas, modelos o reglas financieras |

COREDB/CAP siguen siendo dueños de identidad/caso/verificación/habilitación/vigencia según contratos por acordar; SOL solo conserva referencias mínimas y snapshots en su base propia. Los errores de auth del proveedor se traducen a 503, diferentes de 401/403 de la sesión/rol SOL. Siguiente etapa recomendada E04, no ejecutada aquí. No hay contratos externos nuevos homologados.

## Actualización E04 — Evaluación y resultados

[Informe E04](sol-evaluacion.md) y [contrato para EVA](sol-contrato-evaluacion.md). Base HEAD igual con cambios E02–E04 en workspace. Regresión **149 passed, 2 warnings in 26.99s**, salida 0 (107 previas +42 E04), SQLite/MockTransport; sin MySQL/servicios institucionales.

| RF/contrato | Estado E04 | Implementación/evidencia | Bloqueo |
| --- | --- | --- | --- |
| RF009 / CR-INT-02 | preparado_para_integracion local reforzado | Sobre/reserva/202 existentes; acuse con versión int exacta y valores no blancos. attempts actúa como generación: respuesta vieja no pisa otra reserva ni deshace confirmación. Pruebas de payload/idempotencia, pérdida de respuesta, caída y recuperación por GET sin duplicar entrega/evento. `backend/SOL/integrations.py:227`, `operations.py:30`, `app.py:361` | EVA real con recepción/consulta/dedupe/acuse/ronda/404 acordados, seguridad y DA-SOL-009 |
| RF010 / CR-INT-03 | preparado_para_integracion local reforzado | Header de correlación explícito y coincidente; resultados malformados/cruzados/viejos rechazados; duplicado idéntico reconocido sin efecto. Dos subsanaciones y v3 resuelta preservan historia; callback adelantado reintenta después del acuse local. `backend/SOL/app.py:501`, `:413` | Emisor EVA/Bus, reglas/estados/condiciones resultantes y DA-SOL-002/008; no aprobación de desembolso |
| RF001–008 / CR-INT-01 y CR-INT-10 | estados anteriores conservados | Toda la baseline 107 pasa; no cambios de política/cálculo/maestros ni API COREDB | Pendientes CAP, fiadores, pago doble, auditoría institucional y demás acuerdos anteriores |

No hay RF integrado_real. No se cambian estados ni tablas; los JSON E01 continúan como snapshots históricos. E04 añade obligación explícita de X-Correlation-ID al OpenAPI actual del callback, conforme a v2, sin rutas nuevas. Concurrencia probada con intercalados SQLite, no certificación de bloqueo MySQL. Siguiente etapa recomendada E05, no ejecutada.

## Actualización E05 — Seguridad, API y frontend

[Informe E05](sol-seguridad-frontend.md), OpenAPI SIMULADO (`sol-openapi-e05-simulado.json`, retirado del repositorio; ver `change-log.md`) y OpenAPI REAL (`sol-openapi-e05-real.json`, retirado del repositorio; ver `change-log.md`). HEAD base igual con cambios locales E02–E05. Backend **163 passed, 2 warnings, 38.50s** (149 anteriores +14 E05). Frontend **109 passed, 2 expected fail (111)** (83 aprobadas anteriores +26 SOL), lint/TypeScript/build aprobados en copia temporal. No navegador/TCP/MySQL ni proveedor institucional.

| Alcance | Estado tras E05 | Evidencia y pendiente |
| --- | --- | --- |
| API pública RF001–010 | Contratos locales tipados y documentados | 40 schemas, respuestas anidadas, auth SOLSession/EVACallback y códigos por ruta (incluye 202/503); formatos/nulos/snapshots y rutas conservados por regresión. Artefactos E01 quedan históricos |
| Sesión/RBAC/revocación | Implementado_local reforzado | 422 sin eco de secretos, vencimiento exacto, demo residual bloqueada en REAL, permisos en servidor y revocación múltiple. Sin SSO/MFA/roles institucionales homologados |
| CR-INT-10 | preparado_para_integracion local | Outbox con generación de reserva contra respuestas tardías y acuse no blanco/positivo; prueba fake/rollback/dedupe conservada. Receptor Seguridad institucional compatible pendiente |
| UI RF001–010 | Flujo local/mock verificado en componentes | Alta/preview/guardado, detalle/subsanación, reintento pendiente con misma clave, error contractual/doble clic, sesiones y consola demo por modo. Operación de supervisor/auditor y baja supervisor usando endpoints existentes. Sin rediseño ni cambios de política |
| Proxy/modes | Implementado_local reforzado | Origin completo requerido, rechazo de traversal/callbacks, cookies y no-store; configura /sol o /gateway/sol sin fallback. Reverse proxy/TLS público requiere validación E06 |
| RF005/RF008 real y CAP/EVA institucional | Bloqueos anteriores conservados | No fórmulas/aprobaciones/identidad/proveedores inventados; pruebas locales no cambian homologación |

Ningún RF integrado_real. Siguiente etapa E06, preparada para validación/entrega local con limitaciones externas explícitas; no ejecutada aquí.

## Actualización E06 — validación final y entrega

[Entrega final con diez RF/CR-INT](sol-entrega-final.md), [evidencias y comandos](sol-evidencias-testing.md), [OpenAPI SIMULADO](openapi.json) y REAL generado (`sol-openapi-e06-real.json`, retirado del repositorio; ver `change-log.md`). HEAD base preservado, workspace E02–E06 sin commit/push. Backend final **169 passed/2 warnings** en SQLite (40,34s) y con fixtures MySQL (49,36s); frontend **114 passed/2 expected fail**, lint/TypeScript/build salida 0. **142 comprobaciones TCP** Next→SOL→MySQL, **7** de migración/rollback/locks y **4** de logs/reinicio, todas salida 0. Proveedores CAP/EVA/Auditoría SIMULADO; REAL de suite es MockTransport, nunca institucional. Algunos tests independientes siguen SQLite aun con fixtures MySQL.

| RF | Estado final | Cobertura / pendiente |
| --- | --- | --- |
| 001 | preparado_para_integracion | Gate/referencias/privacidad probados, CAP autoritativo y DA-SOL-007 pendientes |
| 002 | implementado_local | Plazo/límites/persistencia, ratificar DA-SOL-001 |
| 003 | implementado_local | Monto Decimal/extremos/recálculo, DA-SOL-001 |
| 004 | implementado_local | PEN/catálogo/rechazo, DA-SOL-001 |
| 005 | bloqueado_decision | Rechazo seguro probado; fórmula DA-SOL-005 ausente |
| 006 | implementado_local | Calendario preliminar y snapshots/reinicio, DA-SOL-003/004 |
| 007 | implementado_local (declaración básica) | Garantías/validaciones/versiones; soportes/tasación DA-SOL-006 |
| 008 | bloqueado_decision real, registro local implementado | Referencias SIMULADAS/minimización y rechazo REAL; identidad DA-SOL-006 |
| 009 | preparado_para_integracion | Idempotencia/202/conciliación/freeze, EVA/DA-SOL-009 pendientes |
| 010 | preparado_para_integracion | Callback/causalidad/replay/subsanación; emisor EVA/DA-SOL-002/008 pendientes |

Cinco implementados localmente, tres preparados para integración y dos bloqueados: no 10/10 institucionales y **cero integrado_real**. CR-INT-01/02/03/10 siguen preparados técnicamente, sin homologación externa. E06 corrigió fecha canónica MySQL tras flush, origen público configurable del proxy y query en access logs nativos, sin cambiar contratos/políticas/esquemas. Migración v1 usuario preservada y repetible; exclusión MySQL real con dos conexiones, no certificación de todas las carreras distribuidas. Pendientes navegador real/TLS público/SSO/MFA/proveedores y acuerdos. Evidencia nueva sustituye solamente los pendientes locales MySQL/TCP anteriores; informes E01–E05 siguen históricos.
