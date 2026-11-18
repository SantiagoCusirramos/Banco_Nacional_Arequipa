# E02 — Funcionalidades internas SOL, RF002–008

Fecha: 2026-11-14, America/Lima. Rama `feature/integracion-sol`. Base HEAD `86904edd8dc866c1d4260a996748a1cda3770007`; los cambios E02 están en el workspace, sin commit ni push. Plan vigente (`plan-integracion-sol.md`, retirado del repositorio; ver `change-log.md`), [matriz RF](sol-matriz-rf.md), [contratos E01](sol-contratos-finalizacion.md), [changelog](change-log.md).

## Resultado y alcance

**72 pruebas aprobadas, 2 warnings, 18,62 s**, salida 0, con SQLite aislado y HTTP fake. Incluyen las 52 pruebas anteriores y 20 casos nuevos. E02 consolida las funcionalidades internas del perfil local existente; no homologa políticas ni acredita CAP/EVA/Seguridad institucionales. RF005 y la validación real RF008 permanecen bloqueados.

No se reprogramaron límites, moneda, calendario, cálculo financiero, versiones o garantías que ya funcionaban. Las únicas correcciones funcionales son el formato acotado de referencia de fiador y la minimización/resolución de identidad en el borde de integración y en la lectura histórica. No se modificaron frontend, CORE/COREDB, CAP/EVA, Seguridad, Docker/CI, modelos SQL ni migraciones. No se ejecutaron scripts globales, arranque de bases ni comandos destructivos.

## Antes, después y evidencia por RF

Fuentes relativas a `backend/SOL/`. Cada estado local se refiere al alcance descrito, no a cumplimiento institucional completo. Los nombres de prueba abreviados con `test_e02_` están en `tests/test_workflow.py`, salvo indicación.

| RF | Antes E01 | Después E02 | Pruebas ejecutadas y evidencia | Bloqueos pendientes |
| --- | --- | --- | --- | --- |
| 002 Plazo | implementado_local, bordes básicos | implementado_local consolidado; sin cambio de regla | `test_month_boundaries`; `test_e02_invalid_conditions_and_guarantees_never_mutate_draft` rechaza booleano/string/fracción/fuera de política; `test_e02_policy_limits_apply_to_preview_create_and_edit` verifica rangos dinámicos y bordes | DA-SOL-001; rango 6–60 de demo, no aprobado |
| 003 Monto | implementado_local, Decimal/límites | implementado_local consolidado, rechazo sin efectos laterales | `test_amount_boundaries`; negativos NaN/Infinity/precisión y fuera de límites en preview/alta/edición; política temporal y snapshot exacto de preview frente a alta | DA-SOL-001; 1000–50000 PEN propuestos |
| 004 Moneda | implementado_local, catálogo PEN | implementado_local consolidado; sin conversión o ampliación | `test_fiadores_currency_and_double_payment`; negativos USD/minúsculas/longitud inválida en las tres operaciones, sin mutar expediente/eventos/outbox | DA-SOL-001; catálogo institucional pendiente |
| 005 Pago doble | bloqueado_decision, rechazo true | bloqueado_decision; rechazo y protección de política probados | `test_fiadores_currency_and_double_payment`; `test_e02_payment_double_policy_cannot_bypass_block`: habilitar flag en política temporal causa 503, no envío ni nuevos registros; true en entrada produce 422 con política válida | DA-SOL-005, meses/regla/tasa/amortización/redondeo no aprobados; no se calcula |
| 006 Calendario | implementado_local | implementado_local consolidado; fórmula intacta | `test_calendar_invariants`; cinco escenarios E02 de centavos/extremos/tasa cero/fechas desde 31 de enero bisiesto/totales/saldos; tests Lima, recálculo de edición y preservación v1 tras subsanación | DA-SOL-003/004; francés/30 días/días-360/22 % propuestos; no calendario definitivo ni TCEA |
| 007 Garantías | implementado_local de declaración básica, cobertura específica pendiente | declaración local validada/persistida/versionada y cobertura ampliada | `test_e02_all_guarantee_types_and_maximum_are_supported`: cinco tipos, diez garantías y valor positivo; 11 y campos/valor/tipo/precisión inválidos rechazados; `test_e02_guarantees_and_guarantors_versioned_with_recalculated_calendar` prueba edición, revisión vieja, freeze y snapshot en DB | DA-SOL-006: obligatoriedad por producto, documentos y tasación institucional; no se inventan umbrales |
| 008 Fiadores | registro sintético parcial; bloqueado_decision institucional | registro local acotado/minimizado, borde testeable; continúa bloqueado_decision en REAL | Cinco casos de formato, extremos 1/36, duplicados normalizados/autofiador/inexistente/bloqueado/exceso de lista; identidad por whitelist, histórico intacto y permisos; `tests/test_integration_v2.py::test_e02_real_guarantors_remain_blocked_without_mutating_draft` | DA-SOL-006 y contrato de identidad real; no se afirma verificación institucional |

RF001/009/010 no se ampliaron funcionalmente en esta etapa. Sus pruebas existentes forman parte de la regresión completa y siguen pasando; sus dependencias externas no cambian.

## Implementación mínima y compatibilidad

### Condiciones, calendario y garantías reutilizadas

`schemas.py` conserva monto Decimal 15/2, plazo entero estricto y forma de garantía. `service.prepare` sigue consultando política, validando y recalculando en servidor. `finance.py` conserva precisión Decimal, ROUND_HALF_UP y ajuste residual; ninguna cifra financiera o fórmula cambió. Las pruebas usan políticas alternativas solo en archivos temporales de fixtures, no en `config/politica_demo.json`.

Preview, alta y edición comparten validación; los nuevos negativos verifican 21 payloads inválidos contra las tres rutas (63 rechazos), detalle sin cambios y conteos de Application/Version/Event/Delivery/AuditOutbox intactos. La política dinámica se prueba con bordes inclusivos y rechazo de valores inmediatamente exteriores. La edición de respaldos recalcula el calendario; revisión antigua produce 409. Una solicitud observada genera otra versión, permitiendo retirar garantías/fiadores en v2 mientras v1 y su snapshot almacenado permanecen intactos.

No hay norma de obligatoriedad nueva de garantías: lista vacía sigue válida y el catálogo, máximo diez y valor positivo son controles del DTO local existente. No se crea maestro de garantías o fiadores.

### Referencia de fiador y punto de integración

- `schemas.py`: `ReferenceIdentifier` es string de 1–36 caracteres, aplicado a cada elemento de `fiadores`, máximo cinco. Espacios se recortan con la configuración existente; duplicados/autofiador siguen rechazándose después de normalizar. Se acepta referencia opaca, sin presuponer UUID o código de COREDB.
- `integrations.py::guarantor_reference(db, identifier)`: concentra la resolución que antes estaba en service. En SIMULADO exige referencia local ACTIVO y devuelve `{id_cliente, identidad, validacion:"SIMULADA"}`. La identidad se reduce a `CLIENT_FIELDS`. No usa referencia CAP como identidad institucional de fiador.
- En REAL el mismo borde responde 422 explícito por falta de contrato **antes de leer el fiador local**. La prueba HTTP fake demuestra rechazo de preview/alta/edición, expediente inalterado, conteos intactos y ausencia de POST remoto. No se implementó un falso adapter HTTP ni una URL nueva.
- `service.py`: delega a ese borde y conserva las restricciones de no autofiador/no duplicado. La proyección de identidad de solicitante/fiadores históricos usa también whitelist sobre una copia: elimina claves adicionales no permitidas sin reescribir la historia persistida. Los tests de privacidad existentes y los cuatro roles siguen pasando.

El punto es testeable mediante la función con sesión de prueba; no es un servicio institucional. Para un futuro adapter REAL se necesita acordar fuente autorizada, identificación, evidencias mínimas, estados de identidad/vigencia y errores; se requerirán pruebas de contrato y bloqueo explícito si el proveedor falla. No se agregan campos/fechas/casos/acuses inventados para anticipar ese contrato.

Riesgo de compatibilidad acotado: IDs de fiador vacíos o >36 ahora fallan en DTO con 422 temprano; antes podían llegar al servicio. La forma JSON sigue siendo lista de strings. Claves de identidad desconocidas ya no se exportan, incluso de snapshots históricos; los campos permitidos siguen disponibles. No se migran ni eliminan datos almacenados.

### Pago doble: bloqueo verificable y futura extensión

`service.prepare` ya rechaza `pago_doble:true` con 422. `Policy.consistent` ya rechaza `pago_doble_habilitado:true` con política inválida, traducida a 503 en operaciones que la cargan. E02 prueba ambas barreras y que el intento no congela/envía ni altera datos. No se encontró decisión aprobada en las fuentes verificadas; [PROPUESTAS_Y_DECISIONES.md](PROPUESTAS_Y_DECISIONES.md) mantiene pendiente mecanismo/meses.

El futuro punto de extensión exige **primero** DA-SOL-005 verificable: modalidad/meses aplicables, periodicidad e interés, tratamiento de amortización, fechas, redondeo, cargos y compatibilidad de versiones. Después requerirá contrato de entrada versionado si hay selección de meses, regla de calendario implementada/testeada, snapshots reproducibles y política con versión/fuente/vigencia aprobadas. Son requisitos pendientes, no campos o fórmulas disponibles. Activar un booleano no basta; RF005 no se marca completo.

## Ejecuciones y resultados reales, por lote

Todos los comandos pytest se ejecutaron desde la raíz con este prefijo, reutilizando el entorno temporal P01:

```bash
env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts=
```

Las ejecuciones usaron la autorización de ejecución fuera del sandbox porque TestClient no avanzó en el sandbox en P01. Sin URL MySQL heredada; fixtures SQLite en memoria/temporales, worker 0. REAL en pruebas significa adaptador configurado con MockTransport, no proveedor real. Ningún archivo `.env` se creó ni se imprimió contraseña/token/documento personal.

| Lote / argumentos posteriores al prefijo | Resultado real | Acción |
| --- | --- | --- |
| 1: `backend/SOL/tests/test_workflow.py -k e02` | Salida 0, 11 passed, 29 deselected, 2 warnings, 2,64 s | Valida implementación preexistente; sin cambio de reglas |
| 2a: `backend/SOL/tests/test_workflow.py -k e02_guarantor` | Salida 1, 4 failed, 2 passed, 40 deselected, 2 warnings, 0,41 s | Reproduce brechas antes de corregir: vacío/espacios/largo y campo adicional filtrado incorrectamente |
| 2b: `backend/SOL/tests -k 'e02 or client_and_legacy_detail'` | Salida 1, 1 failed, 20 passed, 51 deselected, 2 warnings, 4,19 s | Brechas corregidas; la nueva prueba REAL falló por import Version omitido en el test, corregido sin cambiar producción |
| 2b repetición, mismos argumentos | Salida 0, 21 passed, 51 deselected, 2 warnings, 4,35 s | Corrección y privacidad/reglas REAL verificadas |
| Regresión: `backend/SOL/tests` | Salida 0, **72 passed, 2 warnings, 18,62 s** | Incluye los 52 casos anteriores; sin regresión observada |

Dos warnings heredados, sin ocultarlos: alias AnyIO usado por Starlette y opción `asyncio_default_fixture_loop_scope` sin plugin en requisitos SOL. No se instalaron ni modificaron dependencias para eliminarlos.

Comparación OpenAPI segura en memoria con las instantáneas E01, ambos modos: salida 0; paths, métodos y schemas idénticos **salvo** límites minLength=1/maxLength=36 de los items de fiadores. No se arrancó lifespan/base ni se editaron los JSON E01, que son evidencia histórica. No se corrigen aquí los response models/auth/202 pendientes de la API. `git diff --check` y revisión documental se completan al cierre.

## Pendientes y siguiente etapa

- No se ejecutó MySQL, build/UI/Next, Docker smoke/test global ni HTTP TCP; un pase SQLite/fake no demuestra locks MySQL o integración institucional. Se conservan las restricciones de scripts de P01.
- No hay informe ITIL/tabla 80 ni actas originales verificadas; las referencias DA son trazabilidad heredada, no aprobación. Límites, tasas, moneda, pago doble, requisitos de respaldo y fuente de fiadores requieren sus acuerdos.
- Se puede continuar con **E03 — Captación/COREDB**, dentro de SOL y sus contratos; no se ejecutó E03 ni se autoriza escritura directa a COREDB. E04/E05/E06 conservan sus trabajos de integración, seguridad/frontend y validación/entrega.
