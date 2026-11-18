# E01 — Contratos de finalización y API pública de SOL

Fecha: 2026-11-14, America/Lima. Rama `feature/integracion-sol`, HEAD `86904edd8dc866c1d4260a996748a1cda3770007`. Diagnóstico AS-IS y propuesta documental `SOL-API-PROPUESTA-E01-v1`; no implementación nueva ni homologación institucional.

## Base de evidencia y límites

Se reutilizan [P00](sol-auditoria.md), [P01](sol-baseline.md) y el [informe de APIs](sol-apis-disponibles.md): mismo HEAD y `git diff HEAD -- backend frontend compose.yaml bna scripts docker .github` vacío. Las **52 pruebas aprobadas con 2 warnings, SQLite/MockTransport, 14,75 s** pertenecen a P01; no se repitieron en E01. No acreditan MySQL, Docker, navegador o CAP/EVA institucionales. No se localizó informe PDF ITIL/tabla 80 ni acta aprobada en Documents; se mantiene el contraste indirecto, no se inventan decisiones DA.

SOL conserva el expediente y sus versiones; no calcula riesgo ni desembolsa. Es proveedor de la API de solicitud y consumidor de referencias CAP, recepción EVA y auditoría. COREDB sigue siendo autoridad de su base integrada; la base local SOL no se sincroniza implícitamente con ella.

## OpenAPI generado e inspeccionado

Artefactos sin editar manualmente: SIMULADO (`sol-openapi-e01-simulado.json`, retirado del repositorio; ver `change-log.md`), REAL configurado con destinos fake (`sol-openapi-e01-real.json`, retirado del repositorio; ver `change-log.md`). Ambos son OpenAPI de FastAPI, versión de aplicación **2.0.0**; esa versión no equivale a aprobación de contrato.

| Comprobación E01 | Resultado real |
| --- | --- |
| SIMULADO | 31 paths, 35 operaciones |
| REAL | 17 paths, 19 operaciones; sin alias `/gateway/sol` |
| Callback | Presente en ambos esquemas; en SIMULADO el handler rechaza con 401 |
| `demo-result` | Presente también en REAL, pero el handler rechaza por modo/rol; presencia en OpenAPI no implica acción habilitada |
| Respuestas de login, alta, envío y callback | `application/json.schema: {}`; no hay DTO público de salida declarado |
| Respuestas del envío | OpenAPI declara 200/422, omite el 202 efectivo y errores funcionales |
| Auth | Sin `components.securitySchemes`; `authorization` se describe como header opcional salvo requerimientos de ciertas firmas, aunque el servidor exige sesión/token según ruta |
| Correlación | `X-Correlation-ID` manejada por middleware, no declarada en el contrato de parámetros del callback |

Generación segura con el entorno P01 ya existente: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 /tmp/bna-sol-p01-venv/bin/python`. Se importó `create_app` y se llamó `.openapi()` con `Settings('sqlite://', worker_seconds=0)`, y una variante REAL con base `http://bus.fake.test`, tokens sintéticos en memoria y los cinco paths de simulador. No se ejecutó lifespan, TestClient, petición HTTP ni conexión a base externa; se cerraron cliente HTTP y engine. Se comprobaron versión, callback y alias por modo, salida 0. El JSON no incluye esos tokens ni datos personales. No se reinstalaron paquetes.

Fuentes: `backend/SOL/app.py:56`, `:86`, `:501`, `:538`; entradas `backend/SOL/schemas.py:9`. **Los artefactos describen las limitaciones actuales**, no sustituyen los contratos de respuesta que faltan. La generación por importación puede leer `.env.sol` en otro equipo: usar entorno limpio y revisar instrucciones de P01; aquí no existía ese archivo.

## SOL expone: propietario, consumidores y rutas efectivas

Propietario de todas las operaciones de esta tabla: SOL. Base canónica implementada `/sol`; alias `/gateway/sol` solo SIMULADO para las filas del router. Consumidor web: servidor Next.js; el navegador usa el proxy, no recibe el Bearer. No se propone eliminar rutas o cambiar nombres JSON.

| Método y ruta canónica | Consumidor / permiso servidor | Request → response efectivo | Fuente |
| --- | --- | --- | --- |
| `POST /sol/auth/login` | Next; sin sesión previa | Login → 200 `{token,usuario}`; rechazo 401/429 | `app.py:188` |
| `GET /sol/auth/me` | Next; sesión | Sin body → usuario | `app.py:223` |
| `POST /sol/auth/logout` | Next; sesión | Sin body → `{ok:true}`; revoca sesión | `app.py:227` |
| `GET /sol/policy` | Next; sesión | Sin body → política y `integracion` | `app.py:238` |
| `GET /sol/clients` | Next; sesión | `search` (máx. 80) → lista de referencias mínimas, máx. 50 | `app.py:242` |
| `GET /sol/applications` | Next; sesión | `limit=50` (1–100), `offset=0` (≥0) → `{items,total,limit,offset,estados}` | `app.py:257` |
| `POST /sol/applications` | Next; ASESOR | ApplicationInput → 201 Detail | `app.py:299` |
| `POST /sol/preview` | Next; ASESOR | ApplicationInput → 200 Snapshot calculado; no crea expediente | `app.py:293` |
| `GET /sol/applications/{identifier}` | Next; sesión | ID → 200 Detail; 404 ausente | `app.py:330` |
| `PUT /sol/applications/{identifier}` | Next; ASESOR | ApplicationInput con revisión vigente → Detail; solo borrador no congelado | `app.py:336` |
| `POST /sol/applications/{identifier}/send` | Next; ASESOR | RevisionInput + clave → 202 Detail pendiente o 200 confirmado/reintento | `app.py:361` |
| `POST /sol/applications/{identifier}/revise` | Next; ASESOR | RevisionInput → Detail de nueva versión; exige OBSERVADA | `app.py:413` |
| `POST /sol/applications/{identifier}/demo-result` | Consola web de pruebas; EVALUADOR, SIMULADO | ResultInput + clave → Detail; no es callback institucional | `app.py:446` |
| `POST /sol/admin/users/{username}/disable` | Cliente administrativo; SUPERVISOR | DisableUser → `{usuario,activo:false,sesiones_revocadas}` | `app.py:268` |
| `GET /sol/ops/pending` | Cliente operativo; SUPERVISOR/AUDITOR | `{envios:[operaciones],auditoria:[{estado,cantidad}]}` | `app.py:287` |
| `GET /sol/ops/metrics` | Cliente operativo; SUPERVISOR/AUDITOR | Métricas por proceso; no SLA central | `app.py:283` |
| `POST /sol/integrations/evaluation-results` | EVA/Bus servidor a servidor; token de callback, REAL | EvaluationResult → recepción 200; sin alias gateway | `app.py:501` |
| `GET /health` | Operación/sonda; público | `{status,modulo,integracion}`; proceso | `app.py:173` |
| `GET /ready` | Operación/sonda; público | 200 base accesible o 503; solo SELECT 1 | `app.py:177` |

Lecturas autenticadas no están restringidas al creador del expediente en el código actual (`app.py:330`); no se promete autorización por agencia/propietario. Login REAL bloquea rol EVALUADOR (`app.py:202`); auth local no es SSO institucional. Password PBKDF2 y tokens por hash (`security.py:12`, `:31`); sesión validada en base y rol en servidor (`app.py:124`).

La página `/solicitud-credito` es HTML/UI (`frontend/app/solicitud-credito/page.tsx:417`). `/api/solicitud-credito/*` es el proxy JSON GET/POST/PUT (`frontend/app/api/solicitud-credito/[...path]/route.ts:98`): al login entrega `{usuario}` y cookie HttpOnly, ocultando `token`; bloquea prefijo `integrations` con 404 (`:20`), propaga idempotencia y crea correlación propia (`:22`, `:50`), timeout 3 s (`:61`). La exportación es Blob de Detail en el navegador (`page.tsx:633`); no existe endpoint independiente de exportación. Compose apunta a `http://sol:8011/gateway/sol` y fija SIMULADO (`compose.yaml:39`, `:218`); `/sol` y `/gateway/sol` son el mismo proceso. Los tipos TS de respuesta son locales, no validadores runtime (`page.tsx:19`–`:128`).

## DTOs públicos: actual y propuesta compatible

Las entradas actuales rechazan extras y recortan espacios, pero no todos sus tipos son estrictos. Los ejemplos siguientes son simbólicos/sintéticos, no datos reales ni fixture institucional.

| DTO | Campos/validación actual | Propuesta E01-v1, sin implementar |
| --- | --- | --- |
| Login | username 1–60, password 1–200 (`schemas.py:13`) | Mantener request; documentar LoginResponse y Usuario; nunca incluir token en logs ni OpenAPI de ejemplo |
| ApplicationInput | cliente 1–36, monto Decimal >0, 15 dígitos/2 decimales; moneda longitud 3; plazo entero estricto 1–600; destino 5–120; fecha ISO; booleano pago doble; garantías ≤10, fiadores ≤5; revisión opcional ≥1 (`:26`) | Mantener forma; distinguir límites de DTO de límites dinámicos de política; exigir revisión en contrato de edición sin romper alta |
| Guarantee | tipo PERSONAL/HIPOTECARIA/VEHICULAR/MOBILIARIA/FONDOS; descripción 5–200; valor Decimal positivo, 15/2 (`:18`) | Mantener, completar criterios/tests; obligatoriedad requiere DA-SOL-006 |
| RevisionInput | `revision` ≥1 (`:39`) | Mantener, no confundir revisión con número de versión |
| ResultInput | `version`, decisión y observaciones 5–1000 (`:43`) | Mantener solo demo, separado de CR-INT-03 |
| EvaluationResult | IDs/correlación, versión/ronda enteras estrictas positivas, decisiones APROBADO/OBSERVADO/RECHAZADO, observaciones 5–1000 (`:49`) | Mantener nombres y límites, declarar auth/correlación/idempotencia/errores en OpenAPI |
| DisableUser | motivo 5–200 (`:61`) | Mantener; permiso administrativo pendiente de homologación |
| Snapshot | `{cliente,condiciones,fiadores,politica,calendario}`; garantías en condiciones (`service.py:72`) | Formalizar DTO de salida sin cambiar claves; dinero como string decimal y fechas explícitas |
| Summary / Detail | Summary: id/código/estado/versión/revisión/cliente/documento/monto/moneda/plazo/actualizado; Detail añade versiones, eventos, resultados y envíos (`service.py:145`, `:165`) | Formalizar respuestas y nulos reales; campos adicionales de transporte opcionales para compatibilidad |
| Envío pendiente | Detail + `pendiente_envio:true`, `idOperacion` en 202 (`app.py:408`) | Documentar unión 200/202, sin presentar acuse mientras esté pendiente |

Ejemplo sintético de alta ya compatible con el DTO (requiere referencia existente en el entorno; no se ejecutó):

```json
{"id_cliente":"cliente-sintetico-e01","monto_solicitado":"15000.00","moneda":"PEN","plazo_meses":12,"destino_credito":"Mejoras de vivienda de prueba","fecha_base":"2026-11-14","pago_doble":false,"garantias":[],"fiadores":[]}
```

La fecha debe actualizarse al día de negocio de la prueba. El servidor recalcula; no acepta cuotas calculadas por UI. La política local vigente admite PEN, 1000–50000, 6–60, TEA 22 %, FRANCES, 30 días/días-360, sin pago doble ni cargos (`config/politica_demo.json:2`); todo propuesto. Snapshots preservan política, calendario y condiciones por versión; edición exige revisión y reenvío no muta la versión congelada (`app.py:336`, `:361`, `:413`; `models.py:76`).

Contrato propuesto de respuestas: nombrar `Usuario`, `LoginResponse`, `ClientReferenceResponse`, `SnapshotResponse`, `ApplicationSummary`, `ApplicationDetail`, `ApplicationPage`, `PendingSendResponse`, `EvaluationResultReceipt`, `PendingOperations`, `MetricsResponse`, `DisableUserResponse`, `HealthResponse` y `ReadyResponse`. Son **nombres de diseño, no clases existentes**. Para Detail conservar envíos con versión/operación/acuse/estado/evaluación/ronda/fecha, resultados con versión/decisión/observaciones/fecha y eventos con actor/acción/versión/estados/fecha/correlación. Permitir `estado_anterior:null` en creación y evaluación/ronda nulas antes del acuse; no asumir que los tipos TS ya describen todos los nulos (`service.py:165`, `models.py:117`).

## Cabeceras, errores y compatibilidad

- Sesión: `Authorization: Bearer <token-de-sesion>`, generado por login SOL y validado localmente; no JWT CORE. En Next se guarda en cookie HttpOnly. Callback: Bearer de servicio separado. Salidas: token fijo del Bus, sin login/renovación (`integrations.py:29`).
- `X-Idempotency-Key`: obligatorio en send/demo-result/callback. En send longitud 8–80 y caracteres validados; en callback debe coincidir con `idOperacion` del cuerpo. **Alta POST no implementa idempotencia por esta cabecera**: no se promete deduplicación de creación. Clave de envío y clave de resultado son operaciones distintas (`app.py:299`, `:361`, `:501`).
- Correlación: middleware acepta identificador seguro de 1–100 o genera UUID; devuelve `X-Correlation-ID` (`app.py:93`). Callback compara cuerpo con correlación efectiva. Aunque el documento v2 pide cabecera explícita, el middleware puede generarla si falta; documentar ese comportamiento actual, sin asumir obligatoriedad declarada en OpenAPI.
- Paginación: `items/total/limit/offset/estados`, sin filtro HTTP por estado, orden actualizado descendente y ID; búsqueda visual de UI por página. No sustituir por cursor ni envolver CAP sin versión de contrato (`app.py:257`).

| Código | Comportamiento implementado, según operación | Cierre documental propuesto |
| --- | --- | --- |
| 200/201 | Lectura/operación y alta, respectivamente | DTOs de respuesta explícitos; mantener forma |
| 202 | Envío reservado durable; no confirma recepción EVA | Añadir a OpenAPI y ejemplos sin acuse ficticio |
| 401 | Sesión/token inválido, callback en SIMULADO o credencial incorrecta | Declarar esquema Bearer diferenciado para sesión y callback |
| 403 | Rol insuficiente; demo-result deshabilitado en REAL | Documentar permiso y modo por operación |
| 404 | Solicitud/usuario inexistente; proxy bloquea integrations | No confundir con 404 EVA «no recibido» |
| 409 | Revisión/estado/clave/versión/ronda incompatibles o integridad SQL | Mantener claves y estados; catalogar causas sin filtrar datos remotos |
| 422 | JSON inválido, política funcional, CAP no habilitado/ausente, identificadores callback distintos | FastAPI devuelve detail como lista; errores funcionales usan detail string u objeto. No prometer un único DTO actual |
| 429 | Bloqueo temporal de ingreso | Mantenerlo en catálogo, aunque no esté declarado en OpenAPI |
| 503 | Base/política/dependencia CAP no disponible o contrato incompatible | Declarar respuesta segura sin detalles internos |

Propuesta E01-v1: documentar `detail` compatible como string/objeto/lista de validación, cabecera de correlación y catálogo por operación; cualquier futura normalización debe conservar lectura de errores del frontend (`page.tsx:139`). Las respuestas de validación por defecto requieren comprobación específica de PII; E01 no afirma que todo error esté sanitizado. Los logs propios no registran cuerpos/query y la proyección elimina contacto/nacimiento, pero el expediente sí contiene documento de identidad (`observability.py:23`, `service.py:228`).

Estrategia: mantener rutas, casing, alias condicionado y payloads; ampliar primero documentación/modelos de salida con tests de compatibilidad. No introducir `/v3`, ruta de envío nueva o traducción CORE en E01. La API pública estable es **objetivo pendiente** hasta formalizar/verificar respuestas, auth y errores; este diagnóstico no la declara finalizada.

## SOL consume: contratos propuestos y propietarios

Las rutas CAP/EVA/AUD de esta tabla son **referencias del simulador**, configurables, no endpoints institucionales confirmados. Su propietario futuro es el módulo indicado, con eventual enrutamiento Bus; SOL es consumidor. No se propone construir un Bus corporativo ficticio.

| Contrato | Operación / cabecera / request | Response requerido por adaptador | Propietario y disponibilidad |
| --- | --- | --- | --- |
| CR-INT-01 búsqueda | GET `SOL_CAP_SEARCH_PATH`, ejemplo `/cap/references`, query `search`, `limit=50`; Bearer Bus y correlación | Lista directa ≤50 referencias mínimas | CAP/Clientes vía contrato acordado; solo simulador compatible |
| CR-INT-01 referencia | GET `SOL_CAP_REFERENCE_PATH`, ejemplo `/cap/references/{idCliente}` | Referencia con cliente/caso/verificación/vigencia/habilitación/versionado; 404 ausencia | CAP; solo simulador completo |
| CR-INT-02 recepción | GET `SOL_EVA_STATUS_PATH`, ejemplo `/eva/operations/{idOperacion}` | Mismo acuse del POST; 404 inequívoco «no recibido» | EVA; solo simulador |
| CR-INT-02 entrega | POST `SOL_EVA_SEND_PATH`, ejemplo `/eva/applications`; sobre, correlación y clave estable | Acuse ligado a solicitud, versión, operación, evaluación y ronda | EVA; solo simulador |
| CR-INT-03 resultado | POST real de SOL `/sol/integrations/evaluation-results`; payload y headers de servicio | Recepción positiva y deduplicación local | SOL receptor existente; EVA/Bus emisor pendiente |
| CR-INT-10 auditoría | POST `SOL_AUDIT_PATH`, ejemplo `/security/events`; evento, correlación y clave idEvento | `{idEvento,confirmado:true,acuse}` | Seguridad receptor pendiente; solo simulador compatible |

### CR-INT-01: esquema mínimo a acordar

Ejemplo simbólico/sintético, no documento personal ni referencia institucional válida:

```json
{"id_cliente":"cliente-sintetico-e01","cod_tipo_documento":"DEMO","numero_documento":"DOC-SINTETICO","nombres":"Persona de prueba","apellido_paterno":"Sintetico","apellido_materno":"Laboratorio","estado_cliente":"ACTIVO","id_caso":"CASO-E01","id_verificacion":"VER-E01","fecha_verificacion":"2026-11-14","vigente_hasta":"2026-11-15","estado_habilitante":"HABILITADO","version_contrato":"CR-INT-01-PROPUESTA-v2","simulado":true}
```

Fechas solo ilustrativas; el proveedor real debe determinar vigencia/caso e identidad, nunca SOL. El código actual exige cadenas no vacías salvo `simulado` y `cod_tipo_documento`, opcionales; limita cliente a 36 y documento a 20, fechas ISO, coincidencia de ID y vigencia inclusiva Lima. No fija un valor de `version_contrato` ni exige `simulado:false`; la búsqueda normaliza pero no ejecuta toda la validación funcional individual (`integrations.py:150`, `:163`). La propuesta requiere homologar esos campos y procedencia sin inventar una expiración. Ausencia/no habilitación → 422 SOL; transporte/JSON incompatible → 503. No solicitar contacto ni nacimiento como parte del contrato.

### CR-INT-02: sobre, acuse y conciliación

Sobre actual: `versionContrato=CR-INT-02-PROPUESTA-v2`, `idSolicitud`, `versionSolicitud`, `idOperacion`, `idCorrelacion`, `expediente` (Snapshot), `simulado` y `actorEnvio` de sesión (`integrations.py:204`, `app.py:398`). No se envían adjuntos/streaming. Acuse ilustrativo:

```json
{"idSolicitud":"sol-e01","versionSolicitud":1,"idOperacion":"envio-e01-0001","idEvaluacion":"eva-e01","ronda":8,"acuse":"ACK-E01"}
```

Evaluación 1–80 caracteres, acuse 1–60 y ronda entera positiva; identidad solicitud/versión/operación debe coincidir (`integrations.py:194`). Ronda pertenece a EVA; no deducir de versión. EVA debe persistir recepción, deduplicar misma clave/mismo contenido y consultar por operación tras pérdida de respuesta. Reutilización con contenido diferente: rechazo a acordar, 409 en simulador. SOL consulta antes de cada POST; consulta fallida impide reenvío ciego. Reserva 30 s, backoff 10–300 s; error permanente queda ERROR_CONTRATO para revisión. Deadline limita inicio de llamadas, timeout HTTPX por fase no es plazo absoluto total (`operations.py:30`, `integrations.py:102`).

### CR-INT-03: callback servidor a servidor

Cabeceras requeridas por contrato propuesto: Bearer callback, `X-Idempotency-Key: resultado-e01-0001`, `X-Correlation-ID: trace-e01`. Ejemplo:

```json
{"idSolicitud":"sol-e01","versionSolicitud":1,"idEvaluacion":"eva-e01","ronda":8,"idOperacion":"resultado-e01-0001","idCorrelacion":"trace-e01","decision":"OBSERVADO","observaciones":"Precisar el destino declarado de prueba."}
```

Primera recepción: `{"recibido":true,"idOperacion":"resultado-e01-0001","estado":"OBSERVADA"}`. Repetición idéntica: `{"recibido":true,"reintento_reconocido":true,"idOperacion":"resultado-e01-0001"}`; el estado no aparece en esa segunda variante. Se exige entrega REAL confirmada y versión/evaluación/ronda vigente; otro contenido con clave usada o resultado viejo produce 409. Si callback llega antes de conciliar acuse, EVA debe reintentar. SOL aplica traducción existente a APROBADA/OBSERVADA/RECHAZADA; no evalúa ni autoriza desembolso (`app.py:501`).

### CR-INT-10: evento y confirmación

Ejemplo de evento de acceso sin PII ni secreto:

```json
{"idEvento":"evento-e01-0001","idOperacion":"evento-e01-0001","idCorrelacion":"trace-e01","tipo":"INGRESO_EXITOSO","actor":"usuario-sintetico","sujeto":null,"fecha":"2026-11-14T15:00:00Z","simulado":true}
```

En expediente se agregan solicitud/versión/estadoAnterior/estadoNuevo, sin cuerpo del expediente. Acuse: `{"idEvento":"evento-e01-0001","confirmado":true,"acuse":"ACK-AUD-E01"}` (acuse 1–80). Outbox transaccional, al menos una vez, exige deduplicación persistente en Seguridad. SIMULADO conserva marcador SIMULADO; no se reexportan pendientes de otro modo (`operations.py:17`, `:75`, `:104`; `integrations.py:132`). La retención, TLS y responsabilidad operativa requieren acuerdo.

## Proveedores reales frente a contratos: incompatibilidades vigentes

| Proveedor real en código | Incompatibilidad vigente / no hacer | Fuente |
| --- | --- | --- |
| COREDB GET `/coredb/clientes/{cod_cliente}` | `cod_cliente` de hasta 12, `tipo_documento`, `id_verificacion_captacion`; faltan caso y vencimiento. No hay GET búsqueda ni equivalencia automática de IDs | `COREDB/routers/clientes.py:17`, `:62`, `:178` |
| COREDB POST `/coredb/clientes/validaciones/documento` | Registra efecto de validación, responde 201 con veredicto/cliente; no sustituye GET referencia | `COREDB/routers/clientes.py:143` |
| CORE GET `/core/clientes[/{id_cliente}]` | Query `documento/estado/limite/offset`, JSON sin referencia completa habilitante CR-INT-01 | `CORE/routers/clientes.py:45`, `:63`; `CORE/api.py:73` |
| CORE POST `/core/creditos/solicitudes/{id_solicitud}/evaluar` | Solicitud preexistente en base `bna`, request situación/mora, 201 de evaluación con puntaje/riesgo; no acuse operación/versión/ronda ni consulta de recepción | `CORE/routers/creditos.py:67`, `CORE/schemas/creditos.py:54` |
| CORE POST `.../decision` | APROBAR/RECHAZAR/DERIVAR; sin emisor callback CR-INT-03. No traducir DERIVAR a OBSERVADO | `CORE/routers/creditos.py:99`, `CORE/schemas/creditos.py:72` |
| Seguridad GET `/seguridad/auditoria` | Consulta de su prototipo; no recepción POST `/security/events` ni acuse CR-INT-10 | `seguridad/api.py:59`, `:165` |

CORE y COREDB exigen JWT propios y permisos (`CORE/dependencies.py:31`, `COREDB/auth.py:34`); SOL usa otro esquema de sesión y Bearer Bus sin renovar. No basta configurar una URL real. CAP/EVA/Bus no aparecen como backends autónomos/servicios Compose; sus SQL/modelos no prueban HTTP. No se probaron servidores remotos nuevos en E01.

## Decisiones y siguiente etapa

Mapeo DA heredado de la planificación P00/P01, **no acta ni texto normativo**: DA-SOL-001 política/montos/plazos/moneda; 003/004 calendario; 005 pago doble; 006 garantías/fiadores; 007 referencia CAP; 009 remisión EVA; 002/008 estados/resultados. Se requiere recuperar los documentos originales para precisar cada decisión, especialmente separar 002 de 008. No se atribuyen aprobaciones ni responsables firmantes inexistentes.

Acuerdos externos mínimos: CAP entrega referencia y vigencia autoritativas; EVA acuerda sobre/acuse/consulta/callback/rondas/dedupe; Seguridad credenciales/roles/auditoría/dedupe/retención; COREDB/Tecnología propiedad e identidad de datos; comité reglas de crédito, pago doble y respaldos. Faltan URLs/versiones/credenciales Testing y evidencia institucional de extremo a extremo.

**Se puede continuar con E02 en el alcance local autorizado**: reutilizar RF ya probados, completar tests de límites y respaldos, preservar snapshots/Decimal y bloqueo de pago doble. No se espera a proveedores para ese trabajo. RF005 seguirá `bloqueado_decision`; RF008 no podrá declararse identidad institucional verificada. La [matriz RF](sol-matriz-rf.md) fija criterios y pendientes. No se ejecutó E02 ni se modificó código funcional para simular cierre de estos acuerdos.
