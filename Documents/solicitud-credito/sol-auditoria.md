# P00 — Auditoría local y trazabilidad de SOL

> **Registro histórico.** El CORE legado (`backend/CORE`, su esquema `bna` en `backend/Infraestructura - BD/` y el perfil `legado` de compose) se eliminó en #125. Las rutas, archivos y servicios del CORE legado que se citan aquí ya no existen en `main`; quedan en el historial de git.

Fecha: 2026-11-14, America/Lima. Alcance: exclusivamente auditoría y documentación.

## Resultado y línea base

SOL tiene un recorrido local implementado y adaptadores para contratos HTTP propuestos. **No está integrado con CAP/EVA/Seguridad institucionales.** La ausencia de proveedores compatibles sigue impidiendo una integración real por configuración. No se cambió código funcional, configuración, bases, CI ni otros módulos.

- Rama verificada: `feature/integracion-sol`.
- HEAD: `86904edd8dc866c1d4260a996748a1cda3770007`.
- Últimos cambios: `86904ed` merge PR #65; `1a29c4c` errores 422 del crédito legado; `8aa462d` pruebas MySQL del crédito legado. Último commit localizado para SOL/UI: `4c152e0 feat(sol): implement credit application management module`.
- Estado inicial (`git status --short`): todos sin seguimiento: `AGENTS.md`, `Documents/solicitud-credito/change-log.md`, `plan-integracion-sol.md`, `prompts/`, `sol-apis-disponibles.md` y `README-INICIO.md`. Son aportes presentes en el workspace, no contenido confirmado de HEAD; se preservaron. Por ello esta auditoría describe HEAD más esos documentos locales, sin atribuirlos a un commit.
- Entorno: Linux/bash, Python 3.13.5; Docker 26.1.5, Compose 2.26.1. `node` no se encontró en PATH. No se mostraron secretos ni se leyeron archivos privados de entorno.
- Docker: la consulta inicial del socket fue denegada por el sandbox; repetida con autorización, `docker ps` no mostró contenedores en ejecución. No había imágenes BNA locales. No se inspeccionaron volúmenes ni contenedores detenidos: no se afirma ausencia de datos persistidos.

Se leyeron completos `AGENTS.md`, el plan, el changelog y P00. Se inspeccionaron guías SOL, contratos v2, decisiones, validación histórica, informe local de APIs, README, Compose, bna, scripts de pruebas/smoke, Docker, manifiestos/CI y fuentes relevantes frontend/SOL/CORE/COREDB/Seguridad. El inventario de archivos no mostró un backend autónomo CAP/EVA ni PDF del informe ITIL. La inspección progresiva prioriza las dependencias SOL; no constituye auditoría financiera o de seguridad integral de todo el banco.

## Inventario de interfaz y API SOL

Fuentes de rutas: `backend/SOL/app.py:173`, `:188`, `:238`, `:257`, `:268`, `:283`, `:293`, `:299`, `:330`, `:336`, `:361`, `:413`, `:446`, `:501`, `:538`.

El router siguiente se monta en `/sol` siempre y en `/gateway/sol` solo con SIMULADO (`app.py:538`). Son dos prefijos del mismo proceso y negocio, no dos servicios. El callback se registra directamente en la aplicación y no tiene alias gateway.

| Método | Ruta bajo `/sol` (alias `/gateway/sol` en SIMULADO) | Entrada / salida y autorización |
| --- | --- | --- |
| POST | `/auth/login` | `Login`; token opaco y usuario, sin sesión previa; 401/429 ante rechazo/bloqueo |
| GET | `/auth/me` | Usuario de la sesión |
| POST | `/auth/logout` | Revoca la sesión autenticada |
| GET | `/policy` | Política versionada y modo; autenticado |
| GET | `/clients` | `search` hasta 80 caracteres; lista mínima de referencias; autenticado |
| GET | `/applications` | `limit` 1–100, `offset` no negativo; bandeja paginada y conteos por estado, sin filtro HTTP por estado; autenticado |
| POST | `/admin/users/{username}/disable` | `DisableUser`; baja/revocación local, supervisor |
| GET | `/ops/metrics` | Métricas del proceso; supervisor/auditor |
| GET | `/ops/pending` | Entregas/outbox pendientes; supervisor/auditor |
| POST | `/preview` | `ApplicationInput`; expediente calculado; asesor |
| POST | `/applications` | `ApplicationInput`; detalle creado, 201; asesor |
| GET | `/applications/{identifier}` | Detalle, versiones, envíos, eventos y resultados; autenticado |
| PUT | `/applications/{identifier}` | `ApplicationInput` con revisión vigente; detalle; asesor |
| POST | `/applications/{identifier}/send` | `RevisionInput` y clave de idempotencia; detalle o 202 pendiente; asesor |
| POST | `/applications/{identifier}/revise` | `RevisionInput`; nueva versión desde OBSERVADA; asesor |
| POST | `/applications/{identifier}/demo-result` | `ResultInput` y clave; resultado sintético, evaluador, solo SIMULADO |

Rutas directas adicionales: `GET /health`, `GET /ready` y `POST /sol/integrations/evaluation-results` (`app.py:173`, `:177`, `:501`). Health verifica proceso; ready consulta base, no salud de vecinos ni migraciones. El callback usa credencial de servicio y devuelve recepción, no un dictamen generado por SOL.

DTOs (`backend/SOL/schemas.py:9`): modelos de entrada con `extra=forbid`; `ApplicationInput` contiene cliente, monto Decimal (15 dígitos/2 decimales), moneda, plazo entero, destino, fecha, pago doble, hasta 10 garantías, hasta 5 referencias de fiadores y revisión opcional en el modelo (la edición la comprueba). `Guarantee` exige tipo del catálogo, descripción de 5–200 caracteres y valor positivo. `EvaluationResult` contiene solicitud/versión/evaluación/ronda/operación/correlación/decisión/observaciones; `ResultInput` es distinto y solo de demo. Login y DisableUser son contratos separados. Los endpoints SOL devuelven diccionarios y no declaran `response_model` explícitos (`app.py:188` en adelante): P02 debe revisar la precisión del OpenAPI de respuestas; no se generó un artefacto ni se declara estable la API en P00.

Frontend: `/solicitud-credito` usa `frontend/app/solicitud-credito/page.tsx:417`, su layout y CSS. El helper llama a `/api/solicitud-credito/*` (`page.tsx:139`); exporta el detalle a JSON en el navegador, sin endpoint de exportación independiente (`:633`). Conserva la clave pendiente y distingue el 202 (`:446`, `:567`, `:600`); fechas con America/Lima (`:172`).

El proxy catch-all soporta GET/POST/PUT, codifica segmentos, bloquea `integrations`, comprueba origen cuando se proporciona en escrituras, toma token de cookie y reenvía idempotencia (`frontend/app/api/solicitud-credito/[...path]/route.ts:12`, `:20`, `:23`, `:38`, `:98`). Cookie HttpOnly/SameSite=Lax, Secure configurable, ruta `/api/solicitud-credito`; aborta upstream a 3 s y responde 503 en fallo (`:61`, `:68`, `:86`). Es control de origen condicionado a la cabecera, no prueba de un mecanismo CSRF institucional completo. No se editó frontend.

## Mapa de integración y endpoints reales

Flujo actual: navegador → proxy Next → `/gateway/sol` → SOL/base propia. En SIMULADO, CAP usa referencias sembradas y EVA/AUD acuses locales; en REAL, SOL llama a una URL base y token compartidos para las rutas configuradas. No hay llamadas SOL directas a COREDB. Fuentes: `compose.yaml:30`, `backend/SOL/integrations.py:29`, `:102`, `:132`, `:176`, `backend/SOL/seed.py:19`.

| Proveedor | Endpoints confirmados en código | Contraste con SOL |
| --- | --- | --- |
| CORE legado, real, opcional | `GET /core/clientes`, `GET /core/clientes/{id_cliente}`, POST/PATCH de clientes; `POST /core/auth/login` | Búsqueda `documento/estado/limite/offset`, no `search/limit`. Cliente sin caso, verificación, habilitación y vigencia completas CR-INT-01. Fuentes: `backend/CORE/routers/clientes.py:45`, `:63`, `:71`, `:97`; prefijo en `CORE/api.py:73`; auth en `CORE/routers/auth.py:15`. |
| COREDB Clientes, real | `GET /coredb/clientes/{cod_cliente}`, `POST /coredb/clientes`, `POST /coredb/clientes/validaciones/documento`, `POST /coredb/clientes/{cod_cliente}/validaciones`, `POST /coredb/clientes/{cod_cliente}/estado`; login propio | Código de cliente hasta 12 caracteres y nombres JSON diferentes; sin caso/vencimiento exigidos; no hay GET de búsqueda en el router. Validación documental POST registra efectos. Fuentes: `backend/COREDB/routers/clientes.py:17`, `:62`, `:117`, `:143`, `:160`, `:178`, `:185`; montaje `COREDB/main.py:37`. |
| CORE legado créditos, real | `POST /core/creditos/solicitudes`, `GET /core/creditos/solicitudes/{id_solicitud}`, `POST .../evaluar`, `POST .../decision` | No importa expediente versionado de SOL ni consulta recepción por operación; no devuelve acuse CR-INT-02 ni emite callback CR-INT-03. Fuentes: `backend/CORE/routers/creditos.py:27`, `:30`, `:59`, `:67`, `:99`. |
| Seguridad, prototipo real separado | `/seguridad/auth/login`, GET `/seguridad/auditoria` y `/seguridad/auditoria/verificar`, operaciones e incidentes | JWT propio, SQLite y correlación requerida. No ofrece POST `/security/events` ni acuse CR-INT-10. Fuentes: `backend/seguridad/api.py:59`, `:70`, `:165`, `:172`; `seguridad/app.py:7`. |
| SOL simulador HTTP | GET `/cap/references`, GET `/cap/references/{identifier}`, POST `/eva/applications`, GET `/eva/operations/{operation}`, POST `/security/events` | Sintético, memoria, Bearer `SOL_SIMULATOR_TOKEN`; sin callback automático. Fuentes: `backend/SOL/simulator.py:20`, `:34`, `:38`, `:45`, `:51`, `:66`. |

CR-INT-01: SOL exige lista directa y referencia con `id_cliente`, caso, verificación, vigencia y estados ACTIVO/HABILITADO. La referencia devuelve 422 ante ausencia/no habilitación; 503 ante transporte o esquema incompatible (`integrations.py:78`, `:150`, `:163`). La búsqueda normaliza, pero no aplica toda la validación funcional individual. CORE/COREDB requieren JWT y permisos, frente al Bearer fijo del Bus de SOL; no hay login/renovación en ese adaptador (`CORE/dependencies.py:31`, `COREDB/auth.py:34`, `SOL/integrations.py:29`). Cambiar paths no resuelve JSON ni credenciales.

CR-INT-02: SOL envía camelCase, snapshot y actor desde sesión; consulta antes de POST y valida identidad/versión/operación/evaluación/ronda/acuse (`integrations.py:102`, `:194`, `:204`; `app.py:398`). CORE espera solicitud preexistente en otra base y `situacion/dias_mayor_mora`; devuelve snake_case con puntaje, resultado y riesgo, sin acuse por operación (`CORE/schemas/creditos.py:54`, `:61`).

CR-INT-03: receptor implementado en SOL valida token independiente, idempotencia, correlación, versión vigente, estado, acuse confirmado y pareja evaluación/ronda; 401/422/409/200 según rechazo/aceptación/repetición (`app.py:501`). No se encontró emisor real. CORE usa decisiones APROBAR/RECHAZAR/DERIVAR, distintas de APROBADO/OBSERVADO/RECHAZADO de SOL (`CORE/schemas/creditos.py:72`; `SOL/schemas.py:49`). No hay traducción autorizada.

Configuración REAL: URL base HTTP(S), cinco paths relativos con placeholders, tokens saliente/callback distintos de 32+ caracteres; timeout 0,6 s, hasta dos reintentos y presupuesto de inicio de llamadas 2,4 s por defecto (`settings.py:17`, `:37`). Es presupuesto de llamadas, no plazo absoluto total. No hay fallback a datos locales ante falla REAL (`integrations.py:176`). Auditoría también es obligatoria en la configuración. TLS/origen/roles centrales y contratos definitivos siguen pendientes.

Compose registra SOL, COREDB, Seguridad y CORE legado con perfil; no CAP/EVA/Bus ni el simulador HTTP (`compose.yaml:30`, `:189`, `:245`). Fija SIMULADO y frontend apunta a `/gateway/sol`; REAL exige cambiar ambos entornos de forma coordinada. `k8s/base/sol.yaml:1` y `k8s/base/configuracion.yaml` reproducen el laboratorio, no agregan proveedores institucionales. Las tablas SQL `05_captacion.sql`/`07_evaluacion.sql` y los modelos EVA del CORE no son backends autónomos.

## Matriz RF-SOL-001..010

`implementado_local` indica código del alcance académico, no aprobación. `parcial` indica que solo una parte del RF está cubierta. Las pruebas citadas existen pero **no se ejecutaron con pytest en P00**. Ningún RF se clasifica `integrado_real`. Las dependencias DA se toman del plan local, no de actas aprobadas (`plan-integracion-sol.md:18`).

| RF | Estado actual | Implementación/persistencia y pruebas existentes | Dependencia o límite |
| --- | --- | --- | --- |
| 001 Cliente captado | parcial | `integrations.py:163`, `:176`; referencia mínima en base local; `test_workflow.py:96`, `test_integration_v2.py:157`, `:164` | CR-INT-01, DA-SOL-007; CAP real ausente |
| 002 Plazo | implementado_local | Validación servidor `service.py:36`, política 6–60; snapshot; `test_workflow.py:85` | DA-SOL-001: límites propuestos |
| 003 Monto | implementado_local | Decimal y límites `schemas.py:28`, `service.py:29`; `test_workflow.py:74` | DA-SOL-001: 1000–50000 PEN propuestos |
| 004 Moneda | implementado_local | Catálogo PEN `config/politica_demo.json:6`, `service.py:27`; `test_workflow.py:233` rechaza USD | DA-SOL-001; no cambio de catálogo aprobado |
| 005 Pago doble | bloqueado | Rechazo explícito del flag `service.py:45` y política que impide activarlo `policy.py:44`; `test_workflow.py:233` | DA-SOL-005: faltan fórmula, meses y acuerdo; bloqueo seguro no equivale a cálculo implementado |
| 006 Calendario preliminar | implementado_local | `finance.py:14`, snapshot `service.py:79`, `models.py:76`; `test_workflow.py:280`; seis comprobaciones aisladas P00 aprobadas | DA-SOL-003/004, fórmula académica y redondeo pendientes de ratificación |
| 007 Garantías | parcial | DTO tipo/descripción/valor y snapshot `schemas.py:18`, `service.py:76`; caso positivo `test_workflow.py:248` | DA-SOL-006: obligatoriedad/documentación por producto pendiente; cobertura negativa específica por completar/verificar |
| 008 Fiadores | parcial | Referencias sintéticas, rechazo duplicado/autofiador y rechazo en REAL `service.py:54`; `test_workflow.py:233` | DA-SOL-006: identidad institucional sin contrato |
| 009 Remisión EVA | parcial | Entrega durable, reserva, consulta y acuse `app.py:361`, `operations.py:30`, `models.py:102`; tests v2 `:170`, `:186`, `:207`, `:219` | CR-INT-02, DA-SOL-009; proveedor durable real ausente |
| 010 Resultado/estado | parcial | Callback, resultado y subsanación `app.py:413`, `:501`, `models.py:125`; `test_workflow.py:164`, `test_integration_v2.py:231` | CR-INT-03, DA-SOL-002/008: estados/resultado institucional y emisor pendientes |

## Persistencia, seguridad y operación

- Base propia `bna_sol_mvp`; restricción de nombre en entorno y SQLAlchemy separado, sin escritura directa COREDB (`settings.py:58`, `database.py:8`). Tabla `ClientReference` guarda referencia/snapshot, no un maestro institucional (`models.py:55`). La configuración no es autorización para migrar a la base integrada.
- Snapshot incluye cliente, condiciones, garantías/fiadores, política y calendario; versión/revisión son conceptos separados (`service.py:79`, `models.py:63`, `:76`). Guardar exige revisión; enviar congela antes de HTTP; subsanar copia a otra versión (`app.py:336`, `:361`, `:413`).
- Entrega única solicitud/versión y operación primaria, fingerprint; HTTP fuera de transacción; reserva 30 s y backoff de 10–300 s; error permanente queda ERROR_CONTRATO (`models.py:102`, `operations.py:30`). Worker interno y lotes acotados, no servicio externo (`app.py:63`, `operations.py:104`). Concurrencia real MySQL y recuperación necesitan ejecución focalizada; SQLite no demuestra bloqueo de filas de MySQL.
- Eventos y outbox se guardan en la transacción de negocio; audit distingue SIMULADO/CONFIRMADO y requiere deduplicación remota (`service.py:124`, `operations.py:17`, `:75`, `models.py:148`). No hay garantía exactamente una vez en el sistema externo.
- Dinero con Decimal, ROUND_HALF_UP y ajuste final; días/360 y 30 días, no mes calendario (`finance.py:3`, `:14`). Valores propuestos identificados como pendientes de comité (`config/politica_demo.json:2`). Negocio Lima y auditoría UTC (`clock.py:5`, `:12`; `models.py:22`).
- Hash PBKDF2 y tokens almacenados por hash; autorización de sesión y rol en servidor; cuenta EVALUADOR bloqueada al ingresar en REAL, demo-result rechazado en REAL (`security.py:12`, `:31`; `app.py:124`, `:188`, `:446`). No hay SSO/MFA central.
- Minimización de contacto/nacimiento al listar y proyectar historial; logs estructurados sin cuerpos ni query (`app.py:242`, `service.py:228`, `observability.py:23`, `app.py:93`). Los documentos de identidad sí forman parte del DTO de referencia: minimizar no significa anonimizar todo el expediente. Revalidar privacidad también en errores de validación: SOL no declara manejador propio de `RequestValidationError`; sin ensayo HTTP no se afirma sanitización completa de errores.
- OperationalError → 503, IntegrityError → 409; 202 no acuse. Validación funcional suele usar 422; no se unificó contrato de errores (`app.py:155`, `:164`, `:408`). Migraciones incrementales agregan tablas/columnas, con commit DDL implícito MySQL; no se ejecutaron (`migrations.py:1`, `:24`).

## Diferencias con el informe del módulo y evidencia histórica

No se localizó PDF ni archivo fuente del informe ITIL Fase II de 23/10/2026, ni su tabla 80. **No es posible contrastar literalmente esa tabla, CP y DA contra el informe original.** Se emplean como referencias secundarias el plan, `PROPUESTAS_Y_DECISIONES.md` y `VALIDACION.md`; sus descripciones no sustituyen actas.

| Afirmación/documento | Resultado de auditoría |
| --- | --- |
| Validación histórica de 52 casos SQLite/MySQL, build/lint, navegador y TCP (`VALIDACION.md:7`) | Son resultados fechados de la entrega anterior. Existen evidencias-v2; no se recertifican para este HEAD ni este equipo. P00 no reprodujo las 52 pruebas. |
| «REAL» y resultado real en documentación v2 | Es transporte HTTP con callback preparado. Los tests v2 usan `httpx.MockTransport` (`test_integration_v2.py:89`); la validación TCP histórica usó SOL.simulator. No demuestra proveedor institucional. |
| Inventario histórico Demo/Parcial del plan | El código ya contiene cola durable, consulta previa, callback seguro, minimización y métricas. No conviene reimplementarlos desde cero; verificar/regresar antes de ampliar. Mantienen bloqueos institucionales. |
| `sol-apis-disponibles.md` | Se confirma el dictamen: no hay CAP/EVA/Bus compatibles y cambiar rutas no basta. Esta auditoría agrega RF, seguridad, frontend, CI y estado real del entorno. |
| Última sección del informe APIs (`sol-apis-disponibles.md:142`) y entrada previa del changelog | Describen el estado anterior sin AGENTS raíz y rutas `docs/`. Hoy AGENTS existe y los archivos están en Documents; esas afirmaciones son históricas. No se sobreescribieron ni se creó changelog paralelo. |
| Propiedad SOL frente a base integrada | Persistencia local separada, no integración COREDB (`models.py:1`). No se da por aprobada la propiedad final ni se sincronizan identidades de ambas bases. |
| «Smoke de extremo a extremo del producto» | `scripts/flujo_e2e.py:27` solo incluye `/ready` de SOL; su recorrido transaccional corresponde a clientes/cuentas/tarjetas. No prueba crear/enviar/observar/subsanar SOL. |

## Pruebas y comandos ejecutados

| Comando / comprobación | Resultado real P00 | Clasificación |
| --- | --- | --- |
| `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git log -5 --oneline` | Salida 0; rama/HEAD/estado registrados arriba | Inspección real Git |
| `python3 --version`; `python3 -m pytest --version` | Python 3.13.5; pytest salida 1, módulo ausente | Entorno, no suite aprobada |
| `python3 -m pytest -p no:cacheprovider backend/SOL/tests -q` | Salida 1: `No module named pytest`; ningún caso ejecutado | Intento de suite bloqueado |
| `docker --version`, `docker compose version` | Salida 0; versiones arriba | CLI disponible |
| `docker ps --format ...`, `docker image ls --format ...` | Primer intento salida 1 por sandbox; repetición autorizada salida 0, sin contenedores activos ni imágenes BNA | Lectura real Docker, sin arranque |
| Script Python estándar `ast.parse` sobre `backend/SOL/**/*.py` | Salida 0; 21 archivos válidos | Sintaxis estática; no importación ni ejecución de API |
| Script Python estándar cargando solo `finance.py` mediante `compile/exec` | Salida 0; TEA 0 y 0.2200 × plazos 6/12/60, monto sintético 15000; número de cuotas, suma de capital y saldo final comprobados en seis escenarios | Prueba aislada de función real; no equivale a pytest ni aprobación financiera |
| `git diff --check` | Salida 0 | Archivos seguidos; nuevos documentos comprobados aparte |

Reproducción de las comprobaciones aisladas, sin base ni dependencias externas y sin archivos generados:

```python
import ast
from pathlib import Path
from decimal import Decimal
from datetime import date
for p in Path('backend/SOL').rglob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
ns = {}
exec(compile(Path('backend/SOL/finance.py').read_text(),
             'backend/SOL/finance.py', 'exec'), ns)
for tea in ['0', '0.2200']:
    for months in [6, 12, 60]:
        c = ns['calendar'](Decimal('15000.00'), Decimal(tea), months,
                           date(2026, 11, 14))
        assert len(c['cuotas']) == months
        assert sum(Decimal(r['amortizacion']) for r in c['cuotas']) == Decimal('15000.00')
        assert Decimal(c['cuotas'][-1]['saldo_final']) == 0
```

No ejecutado: suites MySQL/API/MockTransport, frontend lint/build/navegador, HTTP entre procesos, `./bna up`, `./bna smoke`, `./bna test`, migraciones ni pruebas institucionales. Faltan pytest/entorno de dependencias y producto desplegado; no se instalaron dependencias durante P00. Los fixtures permiten SQLite y desactivan worker; si se configura MySQL borran/recrean tablas en `bna_sol_mvp_test` (`tests/conftest.py:21`, `test_integration_v2.py:78`): no deben lanzarse con una URL heredada sin comprobar aislamiento.

`scripts/pruebas.sh:31` genera entorno, construye y arranca producto (`:82`) y puede ejecutar `docker compose down -v --remove-orphans` (`:54`). `bna:123` prepara/arranca; smoke ejecuta un flujo que crea clientes/cuentas y movimientos (`scripts/flujo_e2e.py:6`). No se invocaron como pruebas inocuas en una auditoría. CI los usa en runner (`.github/workflows/ci.yml:35`); la existencia del workflow no acredita su resultado en este commit. Kubernetes también despliega para probar (`.github/workflows/k8s.yml`), sin integración real CAP/EVA.

## Bloqueos, riesgos de regresión y siguiente orden ejecutable

Bloqueos externos: CR-INT-01/02/03/10 definitivos, URLs/credenciales/TLS, deduplicación remota y callback reintentable; DA-SOL-001..009 según el mapeo del plan; identidad de fiadores, pago doble, estados, condiciones resultantes, propiedad de datos y operación central. Sin actas no se cambian reglas.

Riesgos prioritarios para las próximas tareas:

1. Activar REAL manteniendo gateway de demo o apuntando rutas CORE incompatibles: falla de disponibilidad/contrato, sin integración funcional (`settings.py:37`, `app.py:538`).
2. Alterar versiones, claves o reintentos: riesgo de duplicidad o resultado viejo; preservar pruebas existentes antes de ampliar (`models.py:102`, `app.py:501`).
3. Ejecutar pruebas globales o fixtures MySQL sin revisar destino: riesgo sobre datos y volúmenes; preparar entorno aislado primero.
4. Dar por aprobadas políticas/demo, precisión del OpenAPI o privacidad de errores sin evidencia: validar en P02/P03/P09; no realizar refactors por hipótesis.
5. Reportar smoke general o MockTransport como integración EVA: mantener clasificación explícita y añadir después un recorrido E2E específico de SOL.

**Siguiente tarea: P01 — baseline**, preparando dependencias y pruebas seguras y reproducibles en aislamiento. Después **P02 — contratos/API**, para cerrar inventario OpenAPI, DTOs, errores y matriz de proveedores. No se ejecutó ninguno de esos prompts en esta tarea.

Tareas internas que podrán avanzar tras P01/P02 sin esperar CAP/EVA: verificar límites/Decimal/calendario/snapshots (P03), garantías y límites de referencias (P04), y mantener bloqueo probado de pago doble (P05). P06–P09 pueden verificar adaptadores, idempotencia, callback y outbox contra fakes rotulados, pero no declararse integrados. No modificar COREDB/Docker/CI ni contratos compartidos sin analizar y comunicar impacto. El contraste exacto de tabla 80 queda pendiente de disponer del informe histórico verificable.
