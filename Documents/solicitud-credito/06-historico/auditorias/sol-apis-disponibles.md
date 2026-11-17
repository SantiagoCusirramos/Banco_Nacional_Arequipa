> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# APIs disponibles para integrar SOL con Captación y Evaluación

Fecha de revisión: 14/11/2026.

## Dictamen

**No es posible conectar el SOL actual con CAP y EVA reales solamente cambiando su configuración.** No se encontraron backends autónomos CAP/EVA ni proveedores reales de CR-INT-01/02/03. Existen APIs implementadas de Clientes y de evaluación crediticia en CORE, pero no son compatibles con los adaptadores actuales de SOL. Las rutas `/cap/references`, `/eva/applications` y `/eva/operations/...` existen únicamente en el simulador de SOL y en dobles de pruebas.

El receptor CR-INT-03 sí está implementado en SOL; falta un emisor real compatible. `REAL` selecciona transporte HTTP: no acredita que el proveedor sea real ni que el contrato esté homologado.

Alcance: inspección estática de los archivos del repositorio, routers y montaje de aplicaciones, esquemas, servicios, SQL, frontend, scripts, configuración Docker y contratos. «Confirmado» significa implementado y montado en código; no se verificó que un servidor esté desplegado, accesible o tenga datos/credenciales válidos. No se levantaron servicios ni se modificó código de aplicación.

## Ubicación de los módulos y Docker Compose

- `backend/SOL`: aplicación FastAPI, base propia `bna_sol_mvp`, adaptadores HTTP y simuladores.
- No existen directorios backend CAP/EVA. Los SQL `backend/Infraestructura - BD/Trabajo_hecho/BD/05_captacion.sql` y `07_evaluacion.sql` definen persistencia; las tablas, modelos y documentos no constituyen endpoints HTTP.
- `backend/CORE`: implementa evaluación en `routers/creditos.py` y `services/creditossvc.py`, montada por `CORE/api.py` desde `backend/main.py`. Usa la base legada `bna`, distinta de la base de SOL.
- `backend/COREDB`: implementa Clientes y su referencia de verificación de captación; `main.py` no monta rutas de créditos/evaluación. Los nombres de permisos crediticios en `permisos.py` no prueban existencia de una API EVA.

| Archivo | Servicios relevantes registrados | Resultado |
| --- | --- | --- |
| `compose.yaml` | `sol`, `sol-init`, `db-aux`, `coredb`, `db`, `core-legado`, además de cuentas, tarjetas, seguridad y frontend | CAP, EVA y Bus no están registrados. Tampoco el simulador HTTP. |
| `compose.yaml`: SOL | `uvicorn SOL.app:app`, puerto interno 8011; publicación local por defecto 8011 | `SOL_INTEGRATION_MODE: SIMULADO` en el entorno compartido de SOL. No se inyectan rutas ni tokens del Bus. |
| `compose.yaml`: COREDB | `uvicorn COREDB.main:app`, 8012 | API de Clientes disponible en código; no es CAP. |
| `compose.yaml`: CORE legado | `uvicorn main:app`, 8000, perfil `legado` | Evaluación implementada, pero servicio opcional; requiere habilitar el perfil y disponer de base/autenticación. |
| `docker-compose.coredb.yml` | `bna-core-db` | Solo MySQL; no agrega APIs. |
| `docker-compose.coredb.dev.yml` | extensión de `bna-core-db` | Añade datos de desarrollo; no agrega APIs. |

Los puertos publicados pueden cambiar mediante variables `BNA_PUERTO_*`. La existencia de la declaración Compose no demuestra que el contenedor esté ejecutándose. El frontend apunta por defecto a `http://sol:8011/gateway/sol`; esa entrada desaparece al cambiar SOL a REAL y debe revisarse también.

## Endpoints confirmados relacionados con la integración

Las rutas siguientes incluyen sus prefijos efectivos. Se omiten operaciones ajenas al análisis de CAP/EVA/SOL.

| Proveedor / naturaleza | Método y ruta implementada | Entrada / respuesta principal | Autenticación y observación |
| --- | --- | --- | --- |
| CORE legado / real | `POST /core/auth/login` | Credenciales; 200 con `access_token`, caducidad y usuario | Obtiene JWT de CORE. |
| CORE legado / real | `GET /core/clientes` | Query `documento`, `estado`, `limite` (50, máximo 200), `offset`; 200 lista de clientes | JWT + `VER_CLIENTE`. No usa `search`/`limit`. |
| CORE legado / real | `GET /core/clientes/{id_cliente}` | 200 cliente; ausencia como error 404 | JWT + `VER_CLIENTE`; no entrega referencia completa CR-INT-01. |
| COREDB / real | `POST /coredb/auth/login` | Credenciales; 200 con JWT propio y caducidad | No intercambiable por contrato con el token del Bus. |
| COREDB / real | `GET /coredb/clientes/{cod_cliente}` | 200 `ClienteRespuesta`; 404 si no existe | JWT + `VER_CLIENTE`; código alfanumérico de hasta 12 caracteres. No hay GET de búsqueda de clientes en este router. |
| COREDB / real | `POST /coredb/clientes/validaciones/documento` | `tipo_documento`, `numero_documento`, `identidad_verificada`, `motivo` opcional; 201 con `id_validacion`, `resultado`, `motivo`, `cliente` | JWT + `VALIDAR_IDENTIDAD`; registra una validación. No es consulta GET sin efectos. |
| COREDB / real | `POST /coredb/clientes` | Datos de alta y habilitación; 201 con código, estado, habilitación e ID de verificación | JWT + `CREAR_CLIENTE`; solo `SERVICIO:CLIENTES` puede registrar HABILITADO. No sustituye la consulta CAP de SOL. |
| CORE legado / real | `POST /core/creditos/solicitudes` | `SolicitudCrear`; 201 `SolicitudRespuesta` | JWT + `CREAR_SOLICITUD_CREDITO`; crea una solicitud en la base legada. |
| CORE legado / real | `GET /core/creditos/solicitudes/{id_solicitud}` | 200 solicitud, historial y otros datos del crédito | JWT + `VER_CREDITO`; consulta por solicitud, no por operación de entrega. |
| CORE legado / real | `POST /core/creditos/solicitudes/{id_solicitud}/evaluar` | `situacion`, `dias_mayor_mora`, `actor`, `correlation_id`; 201 `EvaluacionRespuesta` | JWT + `EVALUAR_CREDITO`; actor efectivo tomado del token. |
| CORE legado / real | `POST /core/creditos/solicitudes/{id_solicitud}/decision` | `decision`, montos/plazos y observación; 200 `SolicitudRespuesta` | JWT + `APROBAR_CREDITO`; analista efectivo tomado del usuario, requiere empleado asociado. |
| SOL / real como receptor, no proveedor CAP/EVA | `GET /sol/clients` | Query `search`; lista obtenida del adaptador en REAL o de referencias locales en SIMULADO | Sesión de SOL; no expone un backend CAP autónomo. |
| SOL / envío local | `POST /sol/applications/{identifier}/send` | `{"revision":1}` + `X-Idempotency-Key`; REAL responde 202 mientras está pendiente | Sesión rol ASESOR; aceptación local, no acuse EVA. |
| SOL / receptor CR-INT-03 | `POST /sol/integrations/evaluation-results` | `EvaluationResult`; 200 con `recibido`, `idOperacion`, `estado`; repetición idéntica con `reintento_reconocido` | Solo REAL, Bearer de callback y cabeceras de operación/correlación coherentes. |
| Simulador HTTP / sintético | `GET /cap/references` | `search`, `limit` (1–50); 200 lista | Bearer `SOL_SIMULATOR_TOKEN`. |
| Simulador HTTP / sintético | `GET /cap/references/{identifier}` | 200 referencia CR-INT-01 sintética o 404 | Mismo token; fechas calculadas respecto a Lima. |
| Simulador HTTP / sintético | `POST /eva/applications` | Sobre CR-INT-02; 200 acuse, 409 si operación repetida cambia contenido | Bearer y `X-Idempotency-Key`; persistencia solo en memoria. |
| Simulador HTTP / sintético | `GET /eva/operations/{operation}` | 200 mismo acuse o 404 «no recibido» | Bearer; no es un endpoint del CORE. |
| Simulador HTTP / sintético | `POST /security/events` | Evento; 200 `idEvento`, `confirmado:true`, `acuse` | Dependencia adicional de REAL; no acredita auditoría central. |

Fuentes: [router Clientes CORE](../../../../backend/CORE/routers/clientes.py), [router Clientes COREDB](../../../../backend/COREDB/routers/clientes.py), [router Créditos CORE](../../../../backend/CORE/routers/creditos.py), [montaje CORE](../../../../backend/CORE/api.py), [montaje COREDB](../../../../backend/COREDB/main.py), [SOL](../../../../backend/SOL/app.py), [simulador](../../../../backend/SOL/simulator.py).

## Comparación con CONTRATOS_HTTP_V2.md

El [documento v2](../contratos/CONTRATOS_HTTP_V2.md) se declara propuesta para homologación y señala expresamente que sus rutas de ejemplo son del simulador.

### CR-INT-01: referencia habilitada de Captación

SOL requiere dos GET: búsqueda con `search` y `limit=50`, y referencia por `{idCliente}`. La búsqueda exige una lista JSON directa de hasta 50 referencias, sin envoltorio. La referencia usa campos `id_cliente`, `cod_tipo_documento`, `numero_documento`, nombres/apellidos, `estado_cliente`, `id_caso`, `id_verificacion`, `fecha_verificacion`, `vigente_hasta`, `estado_habilitante`, `version_contrato`, `simulado`.

El normalizador exige cadenas no vacías salvo `cod_tipo_documento` y `simulado`, que son opcionales en el código; exige fechas ISO. La referencia individual valida identidad exacta, `ACTIVO`, `HABILITADO` y vigencia inclusiva según Lima. La búsqueda normaliza campos, pero no aplica esa validación funcional completa. El código no fija el valor de `version_contrato` ni exige `simulado:false`: no demuestra por sí mismo procedencia institucional.

| Aspecto | CORE legado | COREDB | Consecuencia |
| --- | --- | --- | --- |
| Ruta/query | `/core/clientes`, filtros `documento/estado/limite/offset` | Solo GET individual por `cod_cliente`; la validación por documento es POST | Cambiar rutas no adapta query, búsqueda ni efectos laterales. |
| Identificador | `id_cliente` | `cod_cliente`, `tipo_documento`, `id_verificacion_captacion` | COREDB necesita correspondencia de identidad y nombres; no asumir equivalencia UUID/código. |
| Referencia | No devuelve caso, verificación, vigencia, habilitación ni versión de contrato CAP | Devuelve verificación/habilitación/fecha/versión, pero no `id_caso`, `vigente_hasta`, `id_cliente`, `id_verificacion` con esos nombres | Ambos JSON fallan la validación actual de SOL; no inventar vencimientos ni casos. |
| Datos adicionales | Nacimiento, celular y correo | Correo, celular y `permite_operar`; apellido materno puede ser nulo | SOL conserva solo campos permitidos, pero además exige apellido materno no vacío. Se necesita contrato mínimo de referencia. |
| Seguridad | JWT CORE + permiso | JWT COREDB + permiso | El Bearer fijo configurado para el Bus no incorpora login/renovación ni permisos institucionales automáticamente. |

En SOL, referencia ausente 404 se transforma en 422; estado/vigencia inhabilitante produce 422; transporte/JSON incompatible produce 503. Un 401/403 remoto es incompatibilidad permanente del transporte y termina como 503 para la consulta CAP, no como una sesión de usuario renovada.

### CR-INT-02: entrega del expediente a Evaluación

SOL envía POST con `versionContrato: CR-INT-02-PROPUESTA-v2`, `idSolicitud`, `versionSolicitud`, `idOperacion`, `idCorrelacion`, `expediente`, `actorEnvio` de la sesión y `simulado`. Antes de cada POST consulta GET por operación; solo 404 autoriza intentar la entrega. POST y GET deben devolver `idSolicitud`, `versionSolicitud`, `idOperacion`, `idEvaluacion`, `ronda` positiva y `acuse`, con identidad consistente.

La API real del CORE difiere:

- El POST `/evaluar` actúa sobre una solicitud ya existente en `bna`; no importa el expediente versionado de SOL ni crea la solicitud de `bna_sol_mvp`. El alta real exige, entre otros, `id_producto_credito`, monto, plazo, destino e identidad del cliente del CORE. No existe sincronización implementada entre ambas solicitudes.
- El JSON de evaluación usa snake_case y devuelve `id_evaluacion`, `id_solicitud`, `puntaje`, `resultado`, `monto_maximo_sugerido`, `nivel_riesgo`, `detalle_reglas`, `fecha_evaluacion`; no contiene el acuse, versión, operación o ronda del contrato SOL.
- No se encontró GET de recepción por `idOperacion`, ni deduplicación de entrega con `X-Idempotency-Key` en ese router/flujo. Un GET de solicitud no demuestra recepción de una operación concreta. No debe configurarse como sustituto del status de EVA.
- La evaluación responde 201 síncrono, frente al protocolo de entrega/conciliación de SOL. El actor sale del JWT y `correlation_id` es campo del cuerpo del CORE; SOL usa además cabecera de correlación y un token de Bus fijo.

Por tanto, ni apuntar `SOL_EVA_SEND_PATH` al POST real ni cambiar solo nombres de rutas permite integración funcional.

### CR-INT-03: resultado de Evaluación hacia SOL

El receptor SOL está implementado con los campos del contrato: `idSolicitud`, `versionSolicitud`, `idEvaluacion`, `ronda`, `idOperacion`, `idCorrelacion`, `decision`, `observaciones`. Rechaza campos extra; decisiones permitidas `APROBADO/OBSERVADO/RECHAZADO`; observaciones de 5–1000 caracteres. Exige `Authorization: Bearer <SOL_EVA_CALLBACK_TOKEN>`, `X-Idempotency-Key` y correlación coincidentes con el cuerpo.

Respuestas: 401 por credencial/modo incorrecto, 422 por JSON/identificadores incompatibles, 409 por conflicto de operación o versión/evaluación/ronda no pendiente, 200 al aceptar o reconocer una repetición idéntica. Si aún no se concilió el acuse, el emisor debe reintentar.

No se encontró emisor de este callback en CORE/COREDB. El endpoint real `/decision` recibe `APROBAR/RECHAZAR/DERIVAR`, devuelve una solicitud y no publica CR-INT-03; `DERIVAR` tampoco equivale automáticamente a `OBSERVADO`. No deben confundirse el resultado del motor y la decisión del analista ni inventarse ronda y versión. El simulador HTTP tampoco emite callbacks automáticamente. `demo-result` es otra vía local de simulación, deshabilitada en REAL.

## Adaptadores HTTP de SOL y configuración necesaria

Implementación: [integrations.py](../../../../backend/SOL/integrations.py), [settings.py](../../../../backend/SOL/settings.py), [operations.py](../../../../backend/SOL/operations.py), [ejemplo de entorno](../../../../backend/.env.sol.example).

| Adaptador | Función | Configuración |
| --- | --- | --- |
| CAP búsqueda | `Integrations.clients` | `SOL_CAP_SEARCH_PATH` |
| CAP referencia | `Integrations.reference`, `captacion_reference` | `SOL_CAP_REFERENCE_PATH` con `{idCliente}` |
| EVA envío y conciliación | `Integrations.deliver` | `SOL_EVA_SEND_PATH`, `SOL_EVA_STATUS_PATH` con `{idOperacion}` |
| Auditoría | `Integrations.audit` | `SOL_AUDIT_PATH`; exige acuse `idEvento`, `confirmado:true`, `acuse` |
| Resultado EVA entrante | Handler `evaluation_result` en SOL | `SOL_EVA_CALLBACK_TOKEN`, distinto del token saliente |

Todos los adaptadores salientes comparten **una URL base y un Bearer**: `SOL_BUS_BASE_URL`, `SOL_BUS_TOKEN`. No hay adaptadores específicos al CORE/COREDB, transformación de contratos, login JWT, renovación automática ni configuración independiente por proveedor. Añaden `X-Correlation-ID`; las escrituras usan `X-Idempotency-Key`. No siguen redirecciones ni usan proxies del entorno (`trust_env=False`).

Para arrancar REAL se necesitan `SOL_INTEGRATION_MODE=REAL`, URL HTTP(S) válida sin credenciales/query/fragmento, los cinco paths relativos, placeholders exigidos y dos tokens distintos de al menos 32 caracteres. Se necesita también la base propia de SOL inicializada y accesible (`SOL_DB_HOST/PORT/USER/PASSWORD/NAME`). Una configuración incompleta impide el arranque; no hay fallback silencioso a simulación. TLS es requisito operativo del documento, pero la validación admite HTTP para laboratorio.

Parámetros: `SOL_HTTP_TIMEOUT_SECONDS=0.6`, `SOL_HTTP_MAX_RETRIES=2`, `SOL_REQUEST_BUDGET_SECONDS=2.4`, `SOL_WORKER_SECONDS=5`. Son configurables dentro de los límites de `Settings.validate`. El worker interno procesa entregas/auditoría persistidas; intervalo 0 lo desactiva y requiere mantenimiento externo/CLI. Un acuse inválido queda como error de contrato; no se resuelve cambiando tokens.

Compose fija SIMULADO: editar únicamente `backend/.env.sol` no sustituye esa variable inyectada por Compose. Para REAL también deben llegar al contenedor las variables completas y debe cambiar `SOL_GATEWAY_URL` del frontend a una entrada válida (`/sol` directo en laboratorio o la entrada homologada del Bus). No existe hoy el Bus institucional en Compose.

## Rutas propuestas y dependencias pendientes

**Las rutas siguientes son las del ejemplo/simulador, no una propuesta aprobada ni endpoints institucionales existentes.** Los equipos proveedores deben confirmar las definitivas.

| Contrato | Ruta de referencia propuesta / configurable | Disponibilidad real actual | Dependencias pendientes |
| --- | --- | --- | --- |
| CR-INT-01 búsqueda | `GET /cap/references?search=...&limit=50` | Solo simulador | Proveedor CAP o fachada acordada; búsqueda acotada y JSON mínimo completo. |
| CR-INT-01 referencia | `GET /cap/references/{idCliente}` | Solo simulador | Caso, verificación, vigencia, identidad y estados homologados; no derivarlos sin regla aprobada. |
| CR-INT-02 entrega | `POST /eva/applications` | Solo simulador | Recepción durable del expediente/versiones, mapeo de identidades y catálogos, deduplicación y acuse estable. |
| CR-INT-02 recepción | `GET /eva/operations/{idOperacion}` | Solo simulador | Consulta durable por operación, 404 inequívoco «no recibido», mismo acuse del POST. |
| CR-INT-03 resultado | `POST /sol/integrations/evaluation-results` | Receptor implementado en SOL | Emisor EVA/Bus, credencial independiente, evaluación/ronda/versiones consistentes y reintentos. |
| Auditoría necesaria en REAL | `POST /security/events` | Solo simulador para este contrato | Receptor central compatible, deduplicación por evento y acuse positivo. |
| Entrada web | Ruta definitiva del Bus pendiente; SOL ofrece `/sol` | `/gateway/sol` es solo simulación | URL de Testing, enrutamiento, credenciales, TLS y configuración Compose/frontend. |

## Qué puede hacerse hoy sin modificar otros módulos

1. Ejecutar SOL en SIMULADO: referencias locales sembradas en su base y acuses EVA/AUD sintéticos (`seed.py`, ramas SIMULADO de `integrations.py`). No utiliza APIs reales de CAP/EVA.
2. Probar HTTP configurando REAL contra `SOL.simulator:app` (8020 según el ejemplo). Requiere token del simulador y envío explícito del callback si se prueba CR-INT-03. Sigue siendo una simulación, con entregas/eventos en memoria.
3. Consultar por separado las APIs reales de CORE/COREDB con sus credenciales y permisos. Eso no constituye integración del flujo SOL.

Para integrar realmente se necesita implementar proveedores compatibles o una fachada/Bus que traduzca y complete los contratos con información real. Cambiar solo SOL para consumir CORE también exige diseño y código nuevos, además de resolver las dependencias de negocio que faltan; no existe una adaptación lista para activar. No puede afirmarse que sea obligatorio modificar internamente CAP/EVA si una futura fachada obtiene todos los datos autorizados, pero **esa fachada y esos contratos completos no están implementados en este repositorio**.

## Verificación documental e instrucciones locales

Se buscaron archivos `AGENTS.md` en el repositorio y en sus directorios ascendentes. Solo se encontró `frontend/AGENTS.md`, cuyas reglas corresponden al frontend Next.js; no establece formato de changelog ni aplica a `docs/`. No existían `docs/` ni `docs/change-log.md` en el estado revisado. Se crean el informe y un registro explícito, fechado y limitado a documentación. No se ejecutaron pruebas de aplicación por tratarse de una revisión estática sin cambios de código.
