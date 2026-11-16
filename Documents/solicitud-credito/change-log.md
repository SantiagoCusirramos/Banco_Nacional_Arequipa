# Registro de cambios

## 2026-11-14

- Creado `docs/sol-apis-disponibles.md`: revisión de endpoints implementados, Docker Compose y adaptadores de SOL frente a CR-INT-01, CR-INT-02 y CR-INT-03; distingue APIs reales de CORE/COREDB y simuladores, documenta incompatibilidades y dependencias pendientes.
- Alcance: solo documentación; sin cambios de código, configuración ni base de datos.
- Validación: inspección estática de routers, montaje, esquemas, servicios, contratos y configuración; comprobación de enlaces locales y del diff. No se verificó disponibilidad de servidores en ejecución.
- Instrucciones: el único `AGENTS.md` encontrado es `frontend/AGENTS.md`; no contiene reglas para `docs/` ni formato de registro de cambios.

## 2026-11-14 — P00: auditoría local y trazabilidad

- Motivo y alcance: ejecutar exclusivamente `prompts/P00-auditoria.md` bajo el nuevo `AGENTS.md`, sin cambios funcionales. Rama `feature/integracion-sol`, HEAD `86904edd8dc866c1d4260a996748a1cda3770007`.
- Archivos modificados: creado `Documents/solicitud-credito/sol-auditoria.md`; ampliado este changelog, preservando sus entradas anteriores. No se modifican los documentos, prompts o instrucciones aportados sin seguimiento.
- Antes/nuevo: había un diagnóstico de APIs sin baseline runtime ni matriz RF completa; ahora hay inventario con fuentes archivo:línea, matriz RF-SOL-001..010, mapa real/simulado, contraste documental, pruebas efectivamente realizadas, bloqueos y orden P01→P02. El comportamiento de la aplicación no cambia.
- Contratos: CR-INT-01/02/03/10 y DA-SOL-001..009 según mapeo del plan. No se homologa ningún contrato ni se aprueba política, estados, persistencia o reglas financieras.
- Pruebas/resultados reales: `python3 -m pytest -p no:cacheprovider backend/SOL/tests -q` salió 1 por ausencia de pytest, sin casos ejecutados. Script estándar AST salió 0 para 21 archivos Python SOL. Seis escenarios sintéticos de `finance.calendar` salieron 0 para cuotas, suma de capital y saldo final. Docker CLI disponible; consulta inicial falló por sandbox y repetición autorizada salió 0: ningún contenedor activo ni imágenes BNA. `git diff --check` salió 0; revisión adicional de enlaces y espacios de los documentos nuevos al cierre. No se ejecutaron suites MySQL, frontend, smoke/test global, migraciones ni integración institucional.
- Riesgos y pendientes: scripts globales pueden arrancar servicios y borrar volúmenes creados por su corrida; fixtures MySQL borran/recrean tablas de pruebas. Preparar aislamiento en P01. Faltan proveedores reales/actas y el PDF histórico/tabla 80; no se inventa contraste literal ni resultados de las 52 pruebas históricas.
- Diferencia documental preservada: la entrada anterior y el cierre de `sol-apis-disponibles.md` hacen referencia a la ubicación antigua `docs/` y a la ausencia anterior de AGENTS raíz; hoy rige `AGENTS.md` y toda documentación SOL nueva queda en esta carpeta. No se reescribió historia ni se creó otro changelog.
- Siguiente prompt recomendado: P01; luego P02. P03/P04 y bloqueo seguro P05 podrán continuar tras baseline/contratos, sin declarar integración real.
- Revisión final P00: corregido el inventario para aclarar que GET applications entrega conteos por estado, sin filtro HTTP por estado, y ajustada la referencia de minimización a `service.py:228`. El primer comprobador de enlaces interpretó una expresión del bloque Python como enlace; se corrigió el comprobador para omitir bloques de código, sin cambiar código del repositorio.

## 2026-11-14 — P01: línea base aislada

- Motivo/alcance: reproducir la suite SOL sin modificar bases compartidas, código funcional, Docker ni CI; rama `feature/integracion-sol`, HEAD `86904edd8dc866c1d4260a996748a1cda3770007`.
- Archivos: creado `Documents/solicitud-credito/sol-baseline.md`; ampliado este changelog. Aportes previos sin seguimiento preservados. Entorno/caché creados exclusivamente bajo `/tmp`, sin archivos de credenciales en el repositorio.
- Antes/nuevo: pytest no estaba disponible en P00; ahora hay un entorno temporal con requisitos SOL y baseline actual **52 passed, 2 warnings in 14.75s**, salida 0, Python 3.13.5, SQLite y MockTransport. Sin cambio del comportamiento de la aplicación.
- Contratos/RF: pruebas locales RF-SOL-001..010 según alcance existente, CR-INT-01/02/03/10 simulados; DA-SOL y proveedores institucionales continúan pendientes. REAL no se declara integración institucional.
- Pruebas reales: suite focalizada fuera del sandbox con límite 90 s, sin `SOL_TEST_DATABASE_URL`, worker global desactivado, sin caché/bytecode; configuración SIMULADO/REAL, rutas y cinco configuraciones negativas aprobadas; Compose renderizado con placeholders sin crear `.env`; sintaxis bash válida. Docker consultado con autorización: ningún contenedor BNA ni imagen BNA. `git diff --check` y revisión documental al cierre.
- Incidencias: caché uv inicial sin escritura (salida 2), corregida a `/tmp`; descarga falló por DNS del sandbox (salida 2), repetición autorizada aprobada; suite en sandbox sin avance, interrumpida con salida 130, repetición autorizada aprobada. Inspección Compose sin perfil produjo KeyError al consultar legado; corregido el comando con perfil, sin cambiar archivos. Dos advertencias: alias AnyIO obsoleto usado por Starlette y opción pytest-asyncio sin plugin en requisitos SOL.
- Riesgos/no ejecutado: no se arrancó stack, no hubo smoke/test global, MySQL, frontend ni pruebas TCP/institucionales. Scripts globales escriben datos y `test` puede llamar `down -v`; no se ejecutaron ni alteraron. Requisitos transitivos no completamente fijados; versiones efectivas documentadas. SQLite no acredita bloqueos MySQL.
- Siguiente: P02, contratos/API y matriz RF. Baseline Docker/MySQL/E2E pendiente de entorno seguro y compatibilidad de los scripts con las restricciones, sin invalidar el pase local SQLite/fake.

## 2026-11-14 — E01: exportación OpenAPI de diagnóstico

- Motivo: complementar P00/P01 con OpenAPI generado de la aplicación sin cambios funcionales, rama `feature/integracion-sol`, HEAD `86904edd8dc866c1d4260a996748a1cda3770007`.
- Archivos creados: `sol-openapi-e01-simulado.json` y `sol-openapi-e01-real.json`, ambos bajo `Documents/solicitud-credito/`; actualizado este changelog. Antes no había exportación SOL local; ahora hay instantáneas AS-IS por modo, no contratos homologados.
- Método/pruebas: entorno temporal P01 reutilizado, `create_app(Settings(sqlite://, worker_seconds=0)).openapi()` y variante REAL con configuración fake; sin lifespan, servidor, peticiones HTTP, tablas ni conexión a bases externas. Aserciones de versión 2.0.0, callback y alias gateway por modo aprobadas, salida 0. JSON sin tokens/credenciales ni datos de cliente.
- Alcance: API SOL/RF-SOL-001..010 y CR-INT-03; adaptadores CR-INT-01/02/10 no son endpoints salientes documentados por FastAPI. Riesgos: respuestas sin modelos, autenticación no declarada como esquema de seguridad y errores/202 incompletos en OpenAPI; diagnóstico y propuestas se completan en los documentos E01. Baseline P01 se reutiliza, no se vuelve a ejecutar.

## 2026-11-14 — E01: diagnóstico incremental y contratos

- Motivo: ejecutar únicamente E01 conforme al plan vigente de seis etapas, reutilizando P00/P01 del mismo HEAD `86904edd8dc866c1d4260a996748a1cda3770007` en `feature/integracion-sol`. Sin cambios funcionales, infraestructura, datos, dependencias ni commits/push.
- Archivos creados: `Documents/solicitud-credito/sol-contratos-finalizacion.md`, `sol-matriz-rf.md`, `sol-auditoria-e01.md`; actualizado este changelog. Los dos OpenAPI se registraron en la entrada anterior. Informes/instrucciones/plan/prompts/ZIP aportados se preservan.
- Antes/nuevo: P00/P01 aportaban auditoría y baseline; ahora existe contrato AS-IS con consumidores/propietarios, propuestas E01-v1 claramente diferenciadas, diez RF con criterios/API/persistencia/tests/bloqueos y anexo de brechas OpenAPI. No se declara API estable implementada ni homologación por crear documentación.
- Contratos: RF-SOL-001..010; CR-INT-01/02/03/10; DA-SOL-001..009 como referencias heredadas pendientes de informe/actas originales. Ejemplos sintéticos/simbólicos, sin secretos ni documentos personales completos. Ningún proveedor simulado se reclasifica real.
- Pruebas/evidencia: rama/HEAD/status/diff funcional revisados, sin cambio desde P01. Reutilizadas sus 52 pruebas aprobadas/2 warnings SQLite+MockTransport, sin repetir suite ni instalar. Nueva generación OpenAPI en entorno P01, sin lifespan ni bases externas, salida 0: SIMULADO 31 paths/35 operaciones; REAL 17/19; aserciones de versión/callback/alias aprobadas. Validación JSON/enlaces/espacios y `git diff --check` al cierre; sin MySQL, navegador, Docker o integración institucional nueva.
- Hallazgos/riesgos: response schemas vacíos, auth ausente de securitySchemes, 202/errores funcionales incompletos en OpenAPI; callback/correlación y demo dependen del modo; alta no deduplica por clave de envío. Contratos públicos deben formalizarse en etapas posteriores sin romper UI. No se corrige código en E01.
- Pendientes: PDF ITIL/tabla 80, actas/políticas, identidad fiadores y pago doble, proveedores/URL/credenciales/dedupe/callback/auditoría reales y MySQL/E2E. Se puede continuar E02 en alcance local con pruebas focalizadas, manteniendo bloqueos institucionales. No se ejecutó E02.
- Validación final E01: enlaces relativos y espacios correctos en los tres informes nuevos y changelog; ambos JSON parsean y confirman schemas/operaciones/auth/ausencia de 202 documentadas, sin tokens fake ni URL de configuración; matriz contiene diez RF. El primer comprobador esperaba erróneamente once propiedades en ApplicationInput; se corrigió la aserción a las diez claves reales, sin editar código o artefactos. Repetición salida 0. `git diff --check` salida 0; diff seguido vacío porque los documentos locales siguen sin seguimiento, revisados aparte.

## 2026-11-14 — E02, lote 1: cobertura interna existente

- Motivo/alcance: consolidar RF002/003/004/005/006/007 y respaldos RF008 sin reimplementar reglas ya presentes. Rama `feature/integracion-sol`, HEAD `86904edd8dc866c1d4260a996748a1cda3770007`.
- Archivos: ampliado `backend/SOL/tests/test_workflow.py` y este changelog. Antes había cobertura de bordes básica; ahora se añaden negativos de condiciones/garantías con rollback en preview/alta/edición, política dinámica temporal, calendario en extremos/fechas/redondeo, persistencia y versiones de respaldos, máximos/tipos de garantía, permisos y bloqueo del flag de pago doble en política. Sin cambios de código funcional o política versionada.
- Contratos: RF002..008, DA-SOL-001/003/004/005/006; referencias sintéticas y decisiones de laboratorio. No se aprueba obligatoriedad, fórmula de pago doble o validación institucional.
- Pruebas: ejecución focalizada del lote pendiente inmediatamente después de esta edición; resultado se añadirá tras correrla. Base SQLite aislada, worker desactivado; sin MySQL, Docker ni otros módulos.
- Riesgos/pendientes: RF008 necesita límites de longitud propios y separar resolución de referencias en su borde; no hay contrato institucional. No se alteran APIs públicas ni artefactos históricos E01.
- Resultado lote 1: comando focalizado `pytest ... backend/SOL/tests/test_workflow.py -k e02` con SQLite, fuera del sandbox, salida 0: **11 passed, 29 deselected, 2 warnings in 2.64s**. Sin regresión detectada en los escenarios ejercitados; warnings heredados P01.

## 2026-11-14 — E02, lote 2a: reproducción de brechas RF008

- Archivos: `backend/SOL/tests/test_workflow.py` y este changelog. Añadidas pruebas de formato individual de referencia y minimización por lista permitida de campos, con duplicados/autofiador/inexistente/bloqueado/exceso de cantidad. Datos sintéticos; no se añade dependencia institucional.
- Antes/nuevo: la lista solo tenía máximo de cinco elementos y el snapshot filtraba tres campos conocidos; se especifican regresiones para IDs vacíos/largos y campos adicionales no autorizados. Sin cambiar todavía implementación. Contratos RF008/DA-SOL-006 y minimización; no impone UUID ni nueva política financiera.
- Pruebas: reproducción focalizada pendiente inmediatamente después; resultado se añadirá antes de corregir. Riesgo confirmado por inspección: posibles campos nuevos del snapshot podrían salir por preview/expediente; no se afirma identidad institucional validada.
- Resultado lote 2a: `pytest ... test_workflow.py -k e02_guarantor --tb=short`, salida 1: **4 failed, 2 passed, 40 deselected, 2 warnings in 0.41s**. Reproduce tres formatos aceptados indebidamente (vacío/espacios/37 caracteres) y filtrado incompleto de campos. Fallos esperados antes de corrección, no ocultados.

## 2026-11-14 — E02, lote 2b: referencia de fiador acotada y minimizada

- Archivos: `backend/SOL/schemas.py`, `integrations.py`, `service.py`, `tests/test_workflow.py`, `tests/test_integration_v2.py` y este changelog.
- Cambio: referencia de fiador con 1–36 caracteres como el identificador ya usado por SOL, sin imponer UUID; resuelta en borde `guarantor_reference` dentro de integrations, activo local + SIMULADA o rechazo explícito en REAL. Se conserva lista JSON de strings, máximo cinco, rechazo de duplicados/autofiador y mensajes funcionales. Antes service leía directamente ClientReference; ahora delega a un punto testeable sin endpoint/credencial nueva.
- Privacidad: whitelist CLIENT_FIELDS en resolución de fiador y proyección de identidades históricas, en vez de negar solo tres campos conocidos. No se reescriben snapshots persistidos ni se inventan datos; tests verifican vista mínima para todos los roles y snapshot original intacto.
- Contratos: RF008/DA-SOL-006, minimización de referencias y compatibilidad API; tests negativos de REAL verifican rechazo sin mutación de expediente/eventos/outbox ni POST remoto. RF005 continúa bloqueado sin fórmula.
- Pruebas: focalizadas E02 y regresión del flujo/privacidad se ejecutan inmediatamente a continuación; resultado pendiente de añadir. Riesgo: clientes que enviaran fiadores vacíos o >36 caracteres ahora reciben 422 temprano; referencias válidas mantienen formato y comportamiento. No cambian modelos, migraciones, política financiera ni módulos externos.
- Primer resultado lote 2b: selección `-k 'e02 or client_and_legacy_detail'`, salida 1, **1 failed, 20 passed, 51 deselected, 2 warnings in 4.19s**. Las cuatro brechas reproducidas quedaron corregidas; falló la nueva prueba REAL por import omitido de `Version` en el propio test. Se añade ese import en `tests/test_integration_v2.py`, sin cambiar implementación, y se repite la selección a continuación.
- Resultado repetido lote 2b: mismos argumentos, salida 0, **21 passed, 51 deselected, 2 warnings in 4.35s**. Corrección de formato/minimización, proyección histórica intacta y rechazo REAL sin efectos laterales verificados.
- Regresión completa posterior: `env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts= backend/SOL/tests`, fuera del sandbox, salida 0: **72 passed, 2 warnings in 18.62s**. Se incluyen los 52 anteriores y 20 nuevos; SQLite/MockTransport, no integración institucional. Warnings heredados, no se cambian dependencias/configuración compartida.

## 2026-11-14 — E02, cierre documental y compatibilidad

- Archivos: creado `Documents/solicitud-credito/sol-funcionalidades-internas.md`; actualizado `sol-matriz-rf.md` con sección E02 preservando tabla E01; ampliado este changelog. Antes solo existía diagnóstico; ahora hay antes/después de RF002–008, evidencia por lote y bloqueos verificables. RF001/009/010 sin ampliación, regresión conservada.
- Contratos/decisiones: RF002–008 y DA-SOL-001/003/004/005/006; políticas financieras sin cambio ni aprobación. Pago doble y fiadores reales siguen bloqueados; puerto de referencia local testeable y whitelist no equivalen a validación institucional.
- Pruebas adicionales: comparación OpenAPI actual en memoria versus JSON E01 para ambos modos, sin lifespan/red/base, salida 0: única diferencia minLength=1/maxLength=36 en items fiadores; paths/métodos y resto de schemas idénticos. JSON E01 preservados como evidencia histórica, sin regenerarlos. `git diff --check` y revisión documental al cierre.
- Riesgos/pendientes: nuevos límites de referencias pueden producir 422 temprano para entradas inválidas; claves desconocidas de identidad ya no se exportan, sin reescribir snapshots. No pruebas MySQL, frontend, Docker/TCP ni CAP/EVA/Seguridad reales. No scripts globales destructivos, no commits/push. Detalle de pruebas fallidas intermedias y correcciones preservado arriba.
- Siguiente etapa recomendada: E03 Captación/COREDB, en alcance SOL/contratos y sin escritura directa a base central. No se ejecutó E03.
- Verificación final E02: `git diff --check` salida 0; cinco archivos seguidos de SOL modificados (271 inserciones/25 eliminaciones, principalmente tests), documentos locales sin seguimiento revisados aparte. AST de 21 Python SOL válido, enlaces/espacios de informe/matriz/changelog correctos y diez RF presentes en actualización E02, salida 0. No modificaciones seguidas fuera de SOL ni staging/commits/push.

## 2026-11-14 — E03, lote 1: contrato CAP y fallos reproducibles

- Alcance: RF001/CR-INT-01, base HEAD `86904edd8dc866c1d4260a996748a1cda3770007` más E02 preservada. La interrupción anterior no dejó cambios E03. Leídos instrucciones/plan/informes y prompt; COREDB inspeccionado sin modificarlo.
- Archivos: `backend/SOL/tests/test_integration_v2.py` y este changelog. Añadidas pruebas de tipos de referencia, JSON inválido, auth/404/422/503/redirección, timeouts y reintentos, lista acotada, configuración/headers, PII y revalidación antes del envío sin doble consulta accidental. También falta de adapter REAL con referencia local disponible.
- Antes/nuevo: cobertura CAP básica ampliada; pruebas reproducen potenciales brechas de campos opcionales no tipados, blancos, fecha compacta, null confundido con 404 y configuración interna REAL ausente. Sin corrección funcional todavía; no se conecta COREDB ni se inventan fechas/casos.
- Pruebas focalizadas pendientes inmediatamente después; entorno P01 reutilizado, datos sintéticos SQLite/MockTransport. COREDB no ofrece caso/vigencia/búsqueda CR-INT-01 completa, por lo que no se implementa traducción ficticia. Riesgos y resultados se registrarán tras reproducción.
- Reproducción lote 1: selección `-k e03` en test_integration_v2, salida 1: **8 failed, 17 passed, 24 deselected, 2 warnings in 0.81s**. Fallos esperados antes de corregir: seis campos malformados aceptados, JSON null confundido con 404 y configuración interna REAL sin adapter que leía referencia local.

## 2026-11-14 — E03, lote 2: validación HTTP y ausencia sin fallback

- Archivos: `backend/SOL/integrations.py`, `tests/test_integration_v2.py` y este changelog. Corrección focalizada sobre E02 preservada.
- Antes/nuevo: campos requeridos rechazan blancos; opcionales `cod_tipo_documento`/`simulado` siguen opcionales, pero si vienen deben ser string no blanco/bool respectivamente. Fechas requieren forma YYYY-MM-DD ya documentada, sin calcular fechas nuevas. JSON null en 2xx se rechaza como contrato permanente inválido, no se confunde con 404. Configuración interna REAL sin adapter REAL falla con 503 antes de leer referencia local.
- Contratos: RF001/CR-INT-01/DA-SOL-007. Estados habilitantes ACTIVO/HABILITADO y ventana Lima existentes se preservan; no se impone versión homologada ni simulado=false ficticios. No se construye fachada COREDB ni se hacen consultas a bases externas.
- Pruebas: añadidos campos autoritativos ausentes, discrepancia de cliente/estados/vigencia, opcionales omitidos y doble consulta con refresco mínimo local sin duplicar referencia ni mutar versión. Ejecución focalizada a continuación. Riesgo: proveedores que enviaran tipos/fechas no documentados ahora reciben rechazo 503; efectos de null sobre acuses EVA/AUD también serán verificados en la regresión completa.
- Resultado lote 2: focalizada `-k e03` salida 0, **35 passed, 24 deselected, 2 warnings in 1.09s**. Regresión completa `backend/SOL/tests`, salida 0, **107 passed, 2 warnings in 19.28s**, incluye las 72 anteriores. Misma ejecución aislada con `env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts=`, fuera del sandbox, SQLite/MockTransport; sin bases/servicios institucionales.

## 2026-11-14 — E03, cierre documental

- Archivos: creado `Documents/solicitud-credito/sol-captacion-coredb.md`; ampliada `sol-matriz-rf.md` con sección E03 y este changelog, sin sobrescribir historia. Antes había diagnóstico E01/E02; ahora existe contrato mínimo, tabla de reutilización COREDB y límites de IDs/fechas, autoridad de datos, plan de fachada no implementado y evidencia de 35 casos adicionales.
- RF/contratos: RF001/CR-INT-01/DA-SOL-007 preparado_para_integracion local, nunca integrado_real; RF008/DA-SOL-006 mantiene bloqueo de identidad institucional. COREDB no modifica contrato ni es consultado por SOL. No se fabrican vigencias/casos/verificaciones ni se hacen JOIN/sincronizaciones SQL externas.
- Cambios E03 solo en integrations.py/tests integración y documentación: rutas/token/timeout existentes reutilizados; tipos/fechas/null/configuración REAL inválidos fallan explícitamente. La llamada HTTP real de producción sigue bloqueada por falta de proveedor/URL/credenciales completos, no por la ausencia de un cliente HTTP.
- Pruebas: 107 aprobadas/2 warnings, detalles de reproducción y corrección arriba. Comprobaciones finales AST, enlaces/espacios, scope de cambios y `git diff --check` al cierre. No smoke/test global, Docker/MySQL, TCP, frontend ni prueba institucional nueva; warnings heredados no ocultados.
- Riesgos/pendientes: campos/fechas no conformes ahora reciben 503; los JSON E01 siguen históricos y las rutas públicas no cambian. Faltan fuentes CAP de caso/verificación/vigencia, mapeo de IDs, versión/estados aprobados, seguridad y prueba real. Plan de fachada sin implementar; sin suplantar usuario de Clientes ni usar un JWT COREDB como token Bus automáticamente.
- Siguiente: E04 Evaluación, dentro del alcance de SOL; no ejecutado. Sin commits/push ni modificación de otros módulos; cambios E02 preservados.
- Verificación final E03: `git diff --check` salida 0; AST de 21 Python SOL válido; enlaces/espacios de informe/matriz/changelog correctos, salida 0. Diff seguido acumulado E02+E03: cinco archivos SOL, 484 inserciones/28 eliminaciones, principalmente tests; de ellos E03 añadió cambios solo en integrations.py/test_integration_v2.py. Documentos sin seguimiento revisados aparte, sin staging. Ningún archivo seguido fuera de SOL modificado.

## 2026-11-14 — E04, lote 1: reproducción de acuses y reservas

- Alcance RF009/010, CR-INT-02/03, base HEAD `86904edd8dc866c1d4260a996748a1cda3770007` más E02/E03 preservadas. Archivos: `backend/SOL/tests/test_integration_v2.py` y este changelog. Sin cambios funcionales todavía.
- Añadidas pruebas de tipos/identidad/acuse, sobre durable e idempotencia pendiente, callback malformado sin mutación, obligación de correlación en OpenAPI y respuestas tardías de un intento anterior a una recuperación de reserva. Intercalados de workers controlados con SQLite, no prueba de locks MySQL ni concurrencia institucional.
- Pruebas focalizadas a continuación; resultados se registrarán tras ejecución. Brechas por inspección: bool/float comparan igual que int en versión de acuse; callback no declara cabecera correlación requerida; fallo tardío podría deshacer confirmación o reserva más nueva. No se inventan decisiones/estados ni se modifica EVA/CORE.
- Reproducción lote 1: salida 1, **9 failed, 20 passed, 59 deselected, 2 warnings in 4.58s**. Confirma cinco acuses inválidos aceptados, cabecera no declarada y tres intercalados de worker con confirmación/reserva sobrescrita. Fallos esperados previos a corrección, preservados.

## 2026-11-14 — E04, lote 2: tipos de acuse, correlación y recuperación

- Archivos: `backend/SOL/integrations.py`, `operations.py`, `app.py` y este changelog. RF009/010, CR-INT-02/03; sin cambio de estados financieros, tablas, migraciones, proveedores o módulos externos.
- Antes/nuevo: acuse exige versión int exacta (no bool/float), evaluación no blanca/sin padding compatible con DTO callback y acuse no blanco. Callback requiere explícitamente X-Correlation-ID válido y coincidente con cuerpo/middleware, conforme al contrato v2 existente; no se apoya en una correlación generada para sustituir cabecera faltante.
- Worker: usa el contador attempts ya persistido como generación de reserva. Al volver del HTTP bloquea/relee la fila, preserva confirmación hecha por otro intento y no aplica éxito/error tardío sobre una reserva recuperada con otra generación. No agrega columnas ni altera payload/ID; conserva lease, consulta GET y reintentos existentes.
- Pruebas focalizadas del lote se ejecutan a continuación. Riesgos: proveedores que devolvieran versión booleana/decimal o IDs no canónicos ahora quedan ERROR_CONTRATO; callback sin cabecera explícita recibe 422 temprano. Concurrencia probada por intercalados deterministas SQLite; bloqueo real MySQL sigue pendiente.
- Resultado lote 2: selección E04, salida 0, **29 passed, 59 deselected, 2 warnings in 4.37s**. Las nueve regresiones reproducidas quedan corregidas; no se homologa proveedor real.

## 2026-11-14 — E04, lote 3: causalidad y recorrido completo fake

- Archivos: `backend/SOL/tests/test_integration_v2.py` y este changelog. Sin nueva modificación funcional. RF009/010, CR-INT-02/03 y estados de demo ya existentes.
- Añadidas pruebas de cabeceras de servicio faltantes/incoherentes, acuse HTTP incompatible por GET/POST sin reenvío ciego, callback antes de conciliación, caída tras aceptación remota y recuperación desde otro engine, identidad cruzada y dos subsanaciones sucesivas con v1/v2 intactas, duplicados reconocidos/conflictos rechazados y v3 rechazada sin nueva subsanación.
- Extendida recuperación del intercalado de reserva para confirmar posteriormente mediante el intento vigente. No se prueban locks MySQL ni EVA institucional. Pruebas focalizadas del lote y regresión completa a continuación; resultados se añadirán tras ejecución.
- Resultado lote 3: selección E04, salida 0, **42 passed, 59 deselected, 2 warnings in 8.03s**. Regresión completa, salida 0, **149 passed, 2 warnings in 26.99s**, incluye las 107 anteriores y 42 nuevas; mismo entorno aislado P01, sin instalar dependencias. Warnings heredados conservados.

## 2026-11-14 — E04, cierre documental

- Archivos: creados `Documents/solicitud-credito/sol-evaluacion.md` (resultado pedido) y `sol-contrato-evaluacion.md` (contrato para EVA requerido por prompt); ampliados `sol-matriz-rf.md` y este changelog. Antes diagnóstico general; ahora hay contrato y evidencia de entrega, causalidad, recuperación y subsanaciones, separando AS-IS/propuesta/fake/pendiente.
- RF009/RF010 y CR-INT-02/03: preparados_para_integracion local reforzados, nunca integrado_real; DA-SOL-002/008/009 pendientes. JSON/headers, responsables de retry, 200/202/401/403/404/409/422/503, estados existentes y límites institucionales documentados. No se inventan equivalencias con CORE ni servicio EVA.
- Pruebas completas: `env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts= backend/SOL/tests`, salida 0, 149/2 warnings/26.99 s. Focalizadas con archivo test_integration_v2.py y `-k e04`, resultados intermedios reales arriba. Intercalados de worker deterministas y nuevo engine SQLite no certifican locks MySQL ni proveedor real.
- Compatibilidad/riesgos: mantuvo SIMULADO y estados/versiones/snapshots, sin tablas/migraciones/política ni otros módulos cambiados. Callback sin correlación ahora 422 explícito y acuses no conformes ERROR_CONTRATO. JSON OpenAPI E01 históricos preservados; modelos de respuesta/auth/errores pendientes no se dan por resueltos.
- Pendientes: recepción/consulta/dedupe persistentes y callback EVA/Bus reales, URLs/credenciales/TLS, aprobación de estados/resultados financieros, ensayo institucional/MySQL/TCP. No scripts destructivos, bases compartidas, commits/push ni E05 ejecutados. Siguiente etapa E05.
- Verificación final E04: `git diff --check` salida 0; AST de 21 Python SOL válido, enlaces/espacios de informe/contrato/matriz/changelog correctos. OpenAPI en memoria de ambos modos comparado con E01, salida 0: únicas diferencias límites fiador E02 y X-Correlation-ID requerido E04; paths/métodos conservados. Añadida esta evidencia al informe sol-evaluacion.md y registro. Diff seguido acumulado E02–E04: siete archivos SOL, 783 inserciones/31 eliminaciones, principalmente tests; documentos sin seguimiento revisados aparte. Ningún archivo seguido fuera de SOL modificado; sin staging.

## 2026-11-14 — E05, lote 1: reproducción de seguridad y contrato

- Archivos: `backend/SOL/tests/test_integration_v2.py` y este changelog. Base HEAD y cambios E02–E04 preservados. Leídos AGENTS/plan/prompt E05/informes y frontend/AGENTS antes de editar frontend.
- Añadidas pruebas para secretos en errores de validación, expiración exacta de sesión, respuesta/auth/códigos OpenAPI, generaciones de reserva de auditoría y permisos operativos/revocación de todas las sesiones. Sin cambio funcional todavía. RF transversales/CR-INT-10/seguridad, sin SSO ficticio.
- Reproducción focalizada pendiente a continuación. Preparación frontend fuera del repo: Node temporal en /tmp porque el sistema no tiene node/npm; primera versión 22.16.0 insuficiente para engines del lockfile, descargando 22.22.2 compatible. Instalación de dependencias en copia temporal, sin modificar lockfile/scripts compartidos ni ejecutar proveedores reales.
- Resultado reproducción: **5 failed, 2 passed, 101 deselected, 2 warnings in 2.34s**, salida 1: eco de secretos en 422, sesión válida exactamente al vencer, ausencia de seguridad OpenAPI y reservas audit sobrescritas por respuesta tardía. La instalación npm inicial además falló con EAI_AGAIN/exit handler; se repite autorizada fuera del sandbox con Node 22.22.2 en copia /tmp.

## 2026-11-14 — E05, lote 2: seguridad backend y contrato OpenAPI

- Archivos: `backend/SOL/app.py`, `schemas.py`, `operations.py` y changelog. Respuestas explícitas anidadas para API SOL, paginación, expediente/calendario, estado/transporte, operación y errores; preserve claves/nulos y omite opcionales ausentes. Se declaran códigos por ruta, incluido 202 de reserva y 503 readiness.
- Auth: esquemas HTTP Bearer separados SOLSession/EVACallback declarados mediante Security; tokens locales continúan por hash, sin SSO nuevo. Caducidad rechaza expires <= now. Error 422 devuelve loc/tipo sin input/ctx/valores; nombre de campo extra se sustituye por etiqueta segura para no reflejar un secreto usado como clave.
- Auditoría CR-INT-10: misma protección de generación attempts usada en E04, sin migración. Respuesta vieja no sobrescribe una reserva nueva ni acuse/estado confirmado. No se conecta Seguridad institucional.
- Pruebas focalizadas y regresión a continuación. Riesgos: validación de salidas ahora detecta snapshots incompatibles; no se relajan modelos ni inventan valores. UI debe conservar manejo de detail string/objeto/lista y Bearer sigue solo en servidor. Respuestas financieras mantienen strings y snapshots; no se cambia política.
- Resultado backend: selección E05 **7 passed, 101 deselected, 2 warnings in 2.83s**, salida 0; primera regresión completa **156 passed, 2 warnings in 39.21s**, salida 0, incluye 149 previas.

## 2026-11-14 — E05, lote 3: pruebas frontend SOL

- Archivos creados: `frontend/__tests__/sol-proxy.test.ts` y `sol-pagina.test.tsx`; actualizado changelog. Pruebas de proxy/cookie/auth/errores/origen/rutas y pantallas de creación, pendiente, observada/subsanada, sesión vencida, operación por roles. Datos sintéticos, sin proveedores reales.
- Entorno: npm ci en copia /tmp salió 0 (474 paquetes), Node 22.22.2 compatible. Leídas guías Next instaladas de Route Handlers/cookies/Vitest, según frontend/AGENTS.md. Baseline frontend existente: **83 passed, 2 expected fail (85), 5 archivos**, salida 0, 4.92 s. No se cambian lockfile/scripts/dependencias.
- Antes/nuevo: no había pruebas SOL de proxy/página; se añaden para reproducir brechas antes de corregir frontend. Se ejecutarán en copia temporal sincronizada; registro de resultados después. No se modifica frontend ajeno a SOL ni se publica sitio.
- Reproducción frontend: primer comando npm se lanzó por error en raíz sin package.json (ENOENT), corregido a /tmp/bna-e05-frontend sin cambios del repo. Selección SOL allí: **10 failed, 8 passed (18), 2 archivos, salida 1**, 1.69 s. Reproduce errores objeto ilegibles, origen/traversal/cache del proxy y controles operativos ausentes; creación, sesión y subsanación ya funcionaban en los casos probados.

## 2026-11-14 — E05, lote 4: proxy y pantallas SOL

- Archivos: `frontend/app/api/solicitud-credito/[...path]/route.ts`, `frontend/app/solicitud-credito/page.tsx` y changelog. Leídas guías Next instaladas antes de edición. Sin tocar otras páginas bancarias ni configuración compartida.
- Proxy: escrituras requieren Origin válido y mismo origen completo, sin excepción de URL malformada; rechaza segmentos de navegación y callbacks fuera de canal; respuestas no-store, login oculta token y valida presencia antes de cookie, 401/logout limpian cookie (también logout con transporte caído). No fallback de URL ni proveedor inventado.
- UI: detail objeto muestra mensaje legible; distingue reintento pendiente/revisión por ERROR_CONTRATO, bloquea edición congelada; limpia datos de sesión al caducar/cerrar incluso en carga paginada. Integra métricas/pendientes para supervisor/auditor y baja local solo supervisor, reutilizando endpoints y permisos backend. Modo HTTP no se presenta como certificación institucional.
- Pruebas focalizadas a continuación, seguidas de suite frontend y build/lint seguros en copia temporal. Riesgo de despliegue: Origin exige esquema/host/puerto coherentes con URL pública que ve Next; revisar reverse proxy/TLS en E06, no modificar infra en esta etapa.
- Resultado lote 4: selección SOL **18 passed, 2 archivos, salida 0, 1.68 s**; lint completo en copia temporal salió 0. La baseline de 83 aprobadas/2 fallos esperados se preservará en regresión final.

## 2026-11-14 — E05, lote 5: bordes de sesión/auditoría y cobertura de interfaz

- Archivos: tests backend integración, tests frontend SOL página/proxy y changelog. Nuevos casos de sesión residual EVALUADOR en REAL, acuses auditoría inconsistentes/blancos, cookie logout con transporte fallido/login inválido/Secure, revocación desde UI, permisos, error contractual, doble click y login/logout. Solo datos sintéticos.
- Reproducción backend a continuación antes de corregir los dos bordes por inspección. UI nueva se verifica con pruebas adicionales sin modificar aún su código. No se amplían roles/reglas institucionales.
- Reproducción adicional: **2 failed, 5 passed, 108 deselected, 2 warnings in 0.56s**, salida 1. Confirma sesión EVALUADOR residual aceptada en REAL y acuse auditoría solo de espacios aceptado.

## 2026-11-14 — E05, lote 6: corrección de sesión residual y acuse

- Archivos: `backend/SOL/app.py`, `integrations.py`, `schemas.py` (orden de import), changelog. Auth aplica también a sesiones existentes la prohibición demo EVALUADOR en REAL que ya regía al login; no agrega rol/regla bancaria. Acuse CR-INT-10 exige texto no blanco, sin alterar IDs, retry o formato.
- Pruebas focalizadas y regresión se ejecutan inmediatamente después. Mantiene sesiones SIMULADO y separación callback/sesión. Sin migraciones ni cambios a Seguridad institucional. Resultado se registra al ejecutar.
- Resultado lote 6: selección E05 **14 passed, 101 deselected, 2 warnings in 3.13s**, salida 0. Suite frontend ampliada: **107 passed, 2 expected fail (109), 7 archivos, 5.72 s**, salida 0. TypeScript `tsc --noEmit --incremental false` salida 0. Build inicial no avanzó en sandbox y terminó con error Turbopack de binding de puerto no permitido; se repetirá autorizado sin tocar fuentes/infra compartida.

## 2026-11-14 — E05, lote 7: consola demo por modo

- Archivo: `frontend/__tests__/sol-pagina.test.tsx` y changelog. Añadidos dos casos de presentación/recepción de resultado demo por modo, en coherencia con restricción backend de EVALUADOR en REAL. Ejecución antes de corregir visibilidad a continuación; pruebas no activan EVA real.
- Reproducción: **1 failed, 1 passed, 11 skipped (13), salida 1**, 1.04 s; la consola seguía visible con un perfil EVALUADOR mock en modo REAL (backend ya lo rechaza). Corregido `frontend/app/solicitud-credito/page.tsx`: visibilidad exige también SIMULADO, sin activar proveedor ni cambiar contrato. Se repite suite frontend a continuación.
- Regresión backend final del lote 6: **163 passed, 2 warnings in 38.50s**, salida 0, incluye las 149 anteriores +14 E05. Solo SQLite/MockTransport, sin proveedores institucionales.

## 2026-11-14 — E05, lote 8: exportación OpenAPI actual

- Archivos: creados `Documents/solicitud-credito/sol-openapi-e05-simulado.json` y `sol-openapi-e05-real.json`; actualizado este changelog. Se preservan instantáneas E01. Diagnóstico antiguo sin respuestas/auth/códigos completos ahora contrastable con los modelos y mecanismos reales del código.
- Generación segura con entorno P01: create_app con Settings SQLite/worker 0 y variante REAL de configuración fake, sin lifespan/red/tablas; salida 0, dos esquemas HTTP Bearer, respuestas 2xx no vacías y 202 comprobados. No tokens/credenciales ni PII en artefactos. HEAD base 86904edd8dc866c1d4260a996748a1cda3770007 más cambios locales E02–E05.
- Límites: exportar no homologa contratos institucionales ni certifica E2E/MySQL; formatos públicos preservados por 163 pruebas backend. Resultado final frontend/build y reporte se registrarán al cierre.

## 2026-11-14 — E05, cierre documental y validación

- Archivos: creado `Documents/solicitud-credito/sol-seguridad-frontend.md`; ampliados `sol-matriz-rf.md` y este changelog, preservando historial. Artefactos OpenAPI E05 registrados arriba. Incluye endpoints/pantallas, resultados intermedios, cambios, comandos, limitaciones y bloqueos de Seguridad; sin afirmar SSO/integración real.
- Resultados finales: backend **163 passed, 2 warnings, 38.50s**, salida 0; frontend **109 passed, 2 expected fail (111), 7 archivos, 4.83s**, salida 0. Son 149 backend anteriores +14 nuevos, 83 frontend anteriores +26 SOL. Lint completo repetido salió 0, TypeScript aislado y del build aprobados.
- Build: repetición autorizada con caché antigua reprodujo error de binding interno; tras mover solo caché fallida en /tmp, build limpio autorizado salió 0 (compilación 3.6s, TypeScript 3.5s y rutas previstas). No se cambian build scripts, Next config, lockfile ni infraestructura para forzar pase.
- Cambios E05 únicamente backend SOL, página/proxy/tests de frontend SOL y documentación. No modelos SQL/migraciones/política/otros módulos/commits/push; E02–E04 preservados. Reporte distingue RTL/jsdom + mocks, backend SQLite/fake y compilación reales frente a navegador/TCP/MySQL/institucional no ejecutados.
- Riesgos/bloqueos: Origin requiere configuración pública coherente, Seguridad debe aportar identidad/roles/SSO/MFA/API CR-INT-10/dedupe/retención/TLS y operación central; CAP/EVA y reglas pendientes conservadas. Preparado para E06 local, sin ejecutarla. Comprobaciones finales de enlaces/AST/scope/JSON/diff a continuación.
- Verificación final E05: `git diff --check` salida 0; AST de 21 Python SOL válido, enlaces/espacios correctos en informe/matriz/changelog, dos JSON OpenAPI parsean y confirman 40 modelos/2 Bearer/202 y ausencia de tokens fake, salida 0. Diff seguido acumulado E02–E05: nueve archivos SOL/frontend-SOL (1267 inserciones/80 eliminaciones), más tests/documentos sin seguimiento revisados aparte. Diff vacío en CORE/COREDB/Seguridad/Docker/CI/Compose/package/lockfile/Next/Vitest config. Sin staging, commits ni pushes.

## 2026-11-14 — E06, lote 1: aislamiento y revisión inicial

- Creado `compose-e06.yaml` en documentación SOL: proyecto independiente requerido por CLI, MySQL 8.4 en tmpfs sin volúmenes compartidos, dos bases exclusivamente sintéticas (suite test y flujo HTTP), puertos loopback 13316/18016/13016. Frontend usa build de copia temporal y montaje de solo lectura; secretos aleatorios solo en /tmp con modo 0600. No se altera Compose global ni módulos ajenos.
- Rama feature/integracion-sol/HEAD 86904edd8dc866c1d4260a996748a1cda3770007 y cambios E02–E05 preservados. Docker accesible tras autorización; no contenedores activos ni del proyecto BNA, imagen mysql:8.4 disponible.
- Inspeccionados bna/scripts/pruebas.sh/scripts/flujo_e2e.py: test ejecuta down -v y levanta producto global; smoke crea clientes/cuentas/movimientos ajenos. No se ejecutan; se sustituye por ensayo SOL aislado autorizado.
- RF001–010/CR-INT-01/02/03/10: sin cambio de contrato ni políticas; regresiones SQLite/frontend iniciadas, resultados pendientes. Riesgos: descarga/build de imágenes y permisos Docker; proveedores institucionales siguen ausentes. No se declara prueba MySQL/TCP realizada aún.

## 2026-11-14 — E06, lote 2: ensayo HTTP reproducible

- Creado `e06_validar_http.py` exclusivamente en documentación SOL: aserciones TCP de readiness/OpenAPI, backend directo y proxy Next, cookies/origen, creación/edición/preview/calendario/garantías/fiadores, envío idempotente, observación demo, subsanación/versionado y rechazo de resultado viejo, roles/logout/errores/PII. No imprime credenciales ni cuerpos. RF001–010 y CR-INT-02/03 demo; no llama proveedor institucional. Ejecución pendiente al terminar arranque.
- Regresiones E06 reales: backend SQLite/MockTransport 163 passed/2 warnings/39.34s, frontend 109 passed/2 expected fail/5.27s, lint y TypeScript salida 0. Build en curso.
- Compose intentó descargar imagen local del init antes de construirla (acceso denegado al registro), continuó al build SOL; resultado global pendiente. No prueba declarada aprobada por arrancar un comando.

## 2026-11-14 — E06, lote 3: arranque y corrección del ensayo

- `compose-e06.yaml up -d --build` salió 0: MySQL healthy, init completado y SOL/Next arrancados. Imagen SOL sha256:d171e7d8277f0c691170f5b2f71951c0b80f6a158616480a333bbb0496ab32a8; build reutiliza Dockerfile/requisitos originales, sin cambios funcionales. Build Next repetido salió 0 (TypeScript 1655ms, ocho páginas).
- Corregida antes de ejecutar la ruta del script `e06_validar_http.py`: métricas es GET ops/metrics, no metrics; confirmada en app.py/OpenAPI. No se inventa endpoint. Suite MySQL iniciada en bna_sol_mvp_test independiente de bna_sol_mvp_e06 del flujo HTTP; resultados pendientes.
- RF001–010: sin nuevas decisiones/políticas; no navegador instalado detectado. Ensayo TCP no equivale a E2E browser.

## 2026-11-14 — E06, lote 4: diferencia OpenAPI entre runtimes

- Primera ejecución TCP salió 1 en comparación literal OpenAPI antes del recorrido: 25 descripciones 422 dicen Unprocessable Entity en Docker Python 3.11 frente a Unprocessable Content en Python 3.13 del export E05. Comparación recursiva confirmó que son las únicas diferencias; no rutas/JSON/auth/códigos.
- `e06_validar_http.py` compara semántica normalizando exclusivamente esos dos textos conocidos; no omite otros metadatos ni errores. No se modifica código de aplicación. Repetición pendiente. Suite MySQL sigue en curso y mostró fallos que requieren diagnóstico.

## 2026-11-14 — E06, lote 5: reproducción de precisión MySQL

- Suite MySQL inicial salió 1: **3 failed, 160 passed, 2 warnings in 45.69s**. Los tres fallos comparan actualizado de respuesta de escritura contra GET: MySQL DATETIME(0) redondea el valor .5+ al segundo siguiente, mientras la instancia ORM todavía contiene microsegundos y serializa truncando. No es una nueva edición ni cambio del snapshot; sí una inconsistencia observable real.
- Añadida prueba parametrizada en test_workflow.py (0/499999/500000/999999 microsegundos) para escritura/edición frente a lectura. Corrección mínima dentro SOL prevista, sin ALTER ni migración/destrucción. RF transversales de persistencia/versionado. Focalizada antes de corregir a continuación.
- Segunda ejecución HTTP salió 1 antes de flujo: callback con cuerpo vacío obtiene 422 de validación antes de ejecutar auth. Ajustado e06_validar_http.py a cuerpo válido sintético para probar 401 de servicio. No se cambió código/auth ni se declaró vulnerabilidad por el orden de validación.

## 2026-11-14 — E06, lote 6: proyección canónica persistida

- Focalizada previa MySQL: **2 failed, 2 passed, 48 deselected, 2 warnings, 2.13s**, salida 1; reproduce exactamente .500000 y .999999. No se relaja ninguna aserción de integridad/historia.
- Cambiado únicamente `backend/SOL/service.py`: detail hace refresh del expediente después del flush para serializar actualizado canónico de la base, preservando campos/snapshots/estado y sin cambiar precisión/esquema/fechas almacenadas. Coste: una lectura adicional de expediente en detalle; no agrega bloqueo FOR UPDATE. RF de persistencia transversal/CR-INT-02/03.
- Focalizadas/regresión SQLite y MySQL se repiten; se reconstruirá imagen antes de repetir TCP. Sin cambios de política ni otros módulos.

## 2026-11-14 — E06, lote 7: migración y transacciones nativas

- Creado `e06_validar_mysql.py`: ensayo exclusivo en hostname mysql/base e06 del Compose separado; crea scratch bna_sol_mvp_e06migration, exige ausencia de tablas, migra usuario v1 dos veces conservando marcador, verifica columnas, READ COMMITTED, rollback y exclusión FOR UPDATE NOWAIT con dos conexiones, incluida liberación tras rollback. No DROP ni acceso ajeno; no datos personales/credenciales en salida. RF persistencia/versionado transversal.
- Prueba pendiente de ejecución; el ensayo de dos conexiones no certifica concurrencia distribuida/institucional ni rendimiento/SLA. Se conserva base scratch para inspección mientras vive tmpfs.

## 2026-11-14 — E06, lote 8: origen público Next/Docker

- Focalizadas MySQL tras corrección: 7 passed/160 deselected/2 warnings/4.60s, salida 0. Regresión SQLite final 167 passed/2 warnings/39.82s, salida 0. Migración scratch primer intento falló import SOL por PYTHONPATH; repetición con PYTHONPATH=/app salió 0: MySQL 8.4.13, siete comprobaciones de migración/aislamiento/rollback/locks.
- Ensayo HTTP avanzó completo por backend directo y falló login proxy con 403. Next start construye nextUrl con hostname/puerto internos, diferentes del origen publicado 127.0.0.1:13016; confirma riesgo E05. No falla MySQL ni se aceptan permisos arbitrarios.
- Añadidos cinco casos en frontend/__tests__/sol-proxy.test.ts para origen público explícito de configuración servidor, rechazo de interno/externo y configuración inválida. Leídas guías Next instaladas Route Handlers/headers/self-hosting antes de editar. Reproducción a continuación; ajuste mínimo proxy/config de laboratorio previsto, sin modificar Compose global/otros módulos.

## 2026-11-14 — E06, lote 9: configuración pública y deadline persistido

- Reproducción proxy: 5 failed/13 passed, salida 1 (311ms). Corregido únicamente proxy SOL: variable opcional servidor SOL_PUBLIC_ORIGIN, HTTP(S) canónico sin ruta/credenciales; inválida devuelve 503, Origin ausente/interno/externo sigue 403. No confía X-Forwarded-* suministrado por cliente. Sin configurar conserva comportamiento anterior. Compose de laboratorio fija http://127.0.0.1:13016. No altera despliegue compartido: operadores deberán definir origen público/TLS.
- Suite MySQL completa tras primera corrección: 1 failed/166 passed/2 warnings/48.26s: test E05 congelaba reloj en timestamp previo a redondeo, no en deadline persistido. Cambiado solo test_integration_v2.py para leer expires efectivo tras commit y congelar exactamente allí. No se relaja <= ni se cambia auth; corrección del test para cumplir su propósito en ambos motores.
- Archivos: route.ts SOL, compose-e06.yaml, test_integration_v2.py y changelog. Pruebas/build focalizados y regresión final a continuación. Riesgos: SOL_PUBLIC_ORIGIN debe corresponder al despliegue; HTTP local sin Secure no certifica HTTPS institucional.

## 2026-11-14 — E06, lote 10: privacidad de access logs reales

- TCP con imagen final previa: 142 comprobaciones aprobadas, salida 0; backend directo y Next→SOL→MySQL reales, proveedores locales SIMULADO. Suite MySQL 167 passed/2 warnings/48.53s; frontend 114 passed/2 expected fail/4.77s, build/lint/TypeScript salida 0. Deadline SQLite focalizado 1 passed/114 deselected/2 warnings/0.64s.
- Auditoría de logs nativos detectó marcador de búsqueda sintético en uvicorn.access (true), clave/token efímeros ausentes (false). Logs estructurados sol sí omiten query, pero el access logger por defecto incluye target completo. Vulnerabilidad de minimización reproducida; no se imprimió valor personal ni secreto.
- Añadidos dos casos `test_e06_uvicorn_access_logs_omit_query_values` en test_integration_v2.py, ruta conocida y 404; corrección local de logging de SOL prevista con ciclo de vida acotado, sin cambiar scripts Docker/globales. Reproducción focalizada a continuación.

## 2026-11-14 — E06, lote 11: minimización Uvicorn

- Reproducción: 2 failed/115 deselected/2 warnings/0.90s, salida 1. Cambiados observability.py y app.py solo SOL: filtro uvicorn.access elimina query del target antes de cualquier handler; formato inesperado se omite de forma segura. Se instala al iniciar lifespan SOL y se retira al finalizar; no cambia logger/infra de otros procesos. Se conserva método/ruta/status/duración de logs propios.
- Riesgo: filtro depende del formato de Uvicorn 0.30.6 fijado; otra versión requiere volver a validar. Paths/IDs operativos siguen presentes, no se afirma anonimización total. Sin credenciales ni PII añadidas a fixtures; no se cambia búsqueda/JSON. Focalizadas y regresión completa SQLite/MySQL y TCP/logs se repiten.

## 2026-11-14 — E06, lote 12: evidencia y OpenAPI finales

- Creados openapi.json (servido por Docker/TCP) y sol-openapi-e06-real.json (generado por la misma imagen con Settings fake, sin lifespan/red/proveedor); E01/E05 preservados. Verificados 2 Bearer, 40 modelos, respuestas 2xx no vacías y 202; SIMULADO 31 paths/35 operaciones, REAL 17/19. Contratos no cambian ni se homologan.
- Creados sol-e06-http-evidencia.json (142 comprobaciones reales TCP, CAP/EVA/Auditoría simulados) y sol-e06-reinicio-privacidad.json (4 comprobaciones: query/credenciales ausentes de logs nuevos y persistencia de sesión/expediente tras reinicio solo SOL). Solo nombres/resultados, sin cookies/tokens/cuerpos/PII.
- Regresión SQLite final 169 passed/2 warnings/40.34s, salida 0; suite MySQL final en curso. Snapshot servida Python3.11 difiere de E05 Python3.13 solo por descripción HTTP422; esquemas/rutas/security equivalentes. Riesgos externos y navegador real pendientes.

## 2026-11-14 — E06, lote 13: cierre de pruebas e informes

- Creados `sol-evidencias-testing.md` y `sol-entrega-final.md`; ampliada sección E06 de `sol-matriz-rf.md`, sin sobrescribir diagnósticos previos. Incluyen diez RF, CR-INT-01/02/03/10, guía de consumo/propietarios/JSON/auth/errores/versiones/variables, Compose aislado, comandos, incidencias, rollback y resumen PR sin publicarlo. No endpoints institucionales inventados.
- Resultado final MySQL **169 passed, 2 warnings, 49.36s**, salida 0; SQLite **169 passed, 2 warnings, 40.34s**, salida 0. Frontend **114 passed/2 expected fail/4.77s**, lint/tsc/build salida 0; TCP final **142** comprobaciones y reinicio/privacidad **4**, migración/locks **7**, salida 0. Incluyen regresiones E05 y nuevas 6 backend/5 frontend; no se suman repeticiones como tests únicos.
- Cinco RF implementado_local, tres preparado_para_integracion y dos bloqueado_decision; cero integrado_real. RF005 no calcula pago doble; RF008 institucional no homologado. Proveedores/decisiones/SSO/TLS/navegador real pendientes. API callbacks/timeouts/202 probados con fake/MySQL, no EVA real.
- Scope seguido acumulado: diez archivos SOL/frontend-SOL, 1344 inserciones/87 eliminaciones; tests/documentos untracked preservados y revisados aparte. Git diff --check salida 0 e índice sin staging. Escaneo inicial 10 archivos seguidos/artefactos sin seguimiento: sin conflictos/claves privadas/PAT/AWS/.env privados; ejemplos .env preexistentes son plantillas, no secretos. Comprobaciones finales y estado del laboratorio se registrarán tras ejecutarse.

## 2026-11-14 — E06, lote 14: integridad de entrega

- Creado sol-e06-manifiesto.json: HEAD/rama y SHA256 de 28 fuentes/configuraciones relevantes (21 Python SOL, política y seis frontend), sin credenciales ni estado Git alterado. Comprobada igualdad de fuentes frontend repo/copia que produjo tests/build.
- AST/JSON/enlaces relativos/espacios correctos; escaneo de todos los cambios seguidos y untracked no contiene claves efímeras del laboratorio, marcadores de conflicto, claves privadas/PAT/AWS por patrones. No se afirma escaneo universal ni ausencia de datos sintéticos de fixtures. Evidencias permiten revisar código sin commit.
- Git diff --check final y scope fuera SOL/índice se comprueban al cierre; no se repiten pruebas funcionales por cambios exclusivamente documentales.

## 2026-11-14 — E06, cierre verificado

- Ampliados sol-evidencias-testing.md y sol-entrega-final.md con manifiesto/digests, comprobaciones Git y estado del entorno. `docker compose ... stop frontend sol mysql` solo proyecto bna-sol-e06 salió 0; MySQL exited, tmpfs /var/lib/mysql confirmado en HostConfig, cero contenedores E06 activos, cero volúmenes persistentes E06 y ningún contenedor del proyecto BNA. Datos sintéticos efímeros descartados; sin down -v/SQL compartido/DROP DATABASE. Imágenes/contenedores detenidos/archivo externo 0600 preservados, sin claves en documentación.
- Final: git diff --check salida 0; diez archivos seguidos acumulados E02–E06 (1344 inserciones/87 eliminaciones) más tests/docs untracked preservados, índice vacío, HEAD intacto. Diff fuera SOL/infra/CI/package/lock/config vacío. AST/JSON/enlaces/espacios y hashes validados, sin secretos efímeros/patrones de claves/conflictos detectados.
- E06 completada en alcance local: 169 backend SQLite +169 con fixtures MySQL (2 warnings cada uno), 114 frontend +2 fallos esperados, build/lint/TypeScript correctos; TCP 142, migración/locks 7 y reinicio/privacidad 4. No navegador real, TLS público ni proveedor institucional ejecutados. Ningún RF integrado_real, RF005/008 y políticas externas bloqueados. Siguiente acción precisa: homologación por CAP/EVA/Seguridad y decisiones de negocio, después ensayo institucional autorizado; sin commits/push/PR publicado.

## 2026-11-14 — CIERRE-RAMA, lote 1: PR y coordinación para revisión

- Alcance exclusivamente documental, sin nueva fase ni cambio funcional: creados `sol-pr-descripcion.md` y `sol-coordinacion-proveedores.md` en esta carpeta. Antes había entrega E06; ahora hay cuerpo de PR revisable y nota breve para CAP/EVA/Seguridad, no publicados ni enviados. RF001–010 y CR-INT-01/02/03/10 conservan estados y bloqueos DA-SOL; sin aprobación institucional inventada.
- Revisión inicial: rama feature/integracion-sol/HEAD 86904edd8dc866c1d4260a996748a1cda3770007, índice vacío, diez archivos seguidos modificados/37 sin seguimiento (incluye seis prompts expandidos). Diff 1344 inserciones/87 eliminaciones solo backend SOL/frontend SOL. Ningún cambio en módulos bancarios ajenos/infra/CI/dependencias/config compartida.
- Verificaciones no destructivas salida 0: diff --check, AST de Python cambiado, parseo JSON, 28 hashes del manifiesto E06 vigentes. Lectura/escaneo de todos los cambios y untracked sin symlinks, archivos .env privados/dumps/BD/logs/claves privadas/PAT/AWS/JWT/URI con clave/conflictos detectados por patrones; las claves efímeras E06 conocidas no aparecen. Credenciales/identidades de fixtures son sintéticas, no proveedores institucionales. No se imprimieron secretos.
- Pruebas E06 reutilizadas (no reejecutadas): 169 backend SQLite y 169 con fixtures MySQL/2 warnings cada uno, 114 frontend/2 expected fail, lint/tsc/build salida 0, TCP 142/migración 7/reinicio-privacidad 4. Sin Docker ni pruebas funcionales/destructivas nuevas. Riesgos: no garantiza ausencia universal de secretos; decisión sobre publicar instrucciones locales AGENTS raíz corresponde al equipo. Inventario/lista de commit y verificación final a continuación; sin staging/commit/push/PR.

## 2026-11-14 — CIERRE-RAMA, lote 2: inventario y lista explícita de commit

- Creados `sol-cierre-rama.md` y `sol-archivos-commit.txt`: inventario exhaustivo, clasificación/recomendación por archivo y allowlist revisable de 49 rutas, incluidos este cierre/PR/nota/lista. Antes solo status disperso; ahora ocho fuentes SOL, cuatro tests y 37 archivos documentales/de evidencia tienen selección explícita. Dos aportes raíz (AGENTS.md/README-INICIO.md) se recomiendan excluir sin borrarlos; el primero requiere decisión del equipo por alcance persistente compartido.
- Todos los nuevos documentos permanecen en Documents/solicitud-credito. Los OpenAPI/evidencias saneados se incluyen con motivo de trazabilidad, no se confunden con temporales; /tmp/envs/builds/cachés/logs/dumps fuera de selección. Ningún secreto trasladado ni archivo ignorado forzado.
- Comandos Git solo propuestos, con --literal-pathspecs y --pathspec-from-file para evitar expansión de [...path]/staging indiscriminado. PR y nota no publicados/enviados; rama destino pendiente de elección del equipo, sin fetch ni afirmación de conflictos resueltos. RF/CR-INT/DA-SOL y pruebas E06 no cambian.
- Validación final de inventario/selección/enlaces/secretos/diff/índice a continuación. Riesgo: futuras ediciones necesitan volver a revisar contenido y selección. No código funcional, configuración compartida, pruebas destructivas ni commits/push/staging ejecutados.

## 2026-11-14 — CIERRE-RAMA, verificación final

- Inventario/lista comprobados: 51 rutas candidatas = 49 recomendadas + AGENTS.md y README-INICIO.md excluidos; diez seguidos modificados/41 sin seguimiento, índice vacío. Recomendados: ocho fuentes, cuatro tests y 37 ayudas/documentos (24 Markdown, nueve JSON, dos ensayos Python, un Compose aislado y una lista TXT). Todos existen, sin symlinks ni duplicados.
- Salida 0: git diff --check; enlaces/espacios nuevos; AST/JSON de candidatos; 28 hashes E06 vigentes; escaneo completo de candidatos por secretos conocidos/patrones/conflictos sin hallazgos. Diff acumulado seguido conserva diez archivos SOL/frontend SOL, 1344 inserciones/87 eliminaciones. Código/pruebas/configuraciones no se editaron en este cierre.
- Sin suites nuevas/Docker/SQL destructivo/fetch/staging/commit/push/PR ni mensajes a proveedores. Descripción PR y nota listas para revisión local. La selección explícita debe revisarse nuevamente si cambian archivos; siguiente paso exclusivamente revisión humana y eventual commit autorizado por usuario.

## 2026-11-16 — Integración en `main` (con autorización de Santiago Cusirramos)

- Se quitaron del repositorio las instrucciones para agentes (`prompts/` y `plan-integracion-sol.md`), las copias antiguas de OpenAPI (E01, E05 y E06 REAL), la lista de archivos del cierre (`sol-archivos-commit.txt`) y el laboratorio E06 aparte de `./bna` (`compose-e06.yaml`, `e06_validar_http.py`, `e06_validar_mysql.py`): `./bna test` y el flujo de extremo a extremo ya prueban SOL con MySQL y por el proxy del frontend. Siguen en el historial de git (PR #75).
- El OpenAPI vigente es `openapi.json`: el que publica SOL en `/openapi.json` en modo SIMULADO, idéntico al E06 simulado. Las menciones a los archivos quitados en los informes de arriba son históricas.
- Proxy del frontend: sin `SOL_PUBLIC_ORIGIN`, el origen esperado es el `Host` que recibe el servidor (con el esquema de Next). Así funciona detrás de compose con cualquier `BNA_PUERTO_FRONTEND` y del NodePort de kind, donde Next escucha en el 3000 y el navegador usa otro puerto. `SOL_PUBLIC_ORIGIN` queda para un proxy TLS delante.
