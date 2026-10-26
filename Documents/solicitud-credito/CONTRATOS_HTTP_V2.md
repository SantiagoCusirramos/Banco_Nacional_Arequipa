# Transporte HTTP v2 — propuesta para homologación

Fecha: 23/10/2026. `REAL` significa que SOL usa HTTP hacia las rutas configuradas del Bus. No significa que los contratos, reglas financieras o integración institucional estén aprobados. La validación entregada utiliza un simulador, con datos sintéticos.

## Qué deben entregar Bus, Captación, Evaluación y Seguridad

- URL de Testing, rutas exactas y versión del contrato. No se inventa una URL institucional.
- Dos credenciales distintas: SOL → Bus y Bus/EVA → callback SOL. Configuración solo en servidor. El receptor debe verificar TLS y restringir el origen; no se implementa SSO/MFA institucional.
- CAP: forma de búsqueda, referencia, estado habilitante, verificación y vigencia. El adaptador usa actualmente `ACTIVO` + `HABILITADO`; homologar estos nombres antes de conectar.
- EVA: POST de recepción, GET por `idOperacion`, acuse estable y callback reintentable. Un GET 404 significa **no recibido**. Si el GET falla, SOL no repite el POST a ciegas. Una entrega confirmada queda congelada.
- Seguridad: acuse central positivo y deduplicación por `idEvento`. La cola garantiza persistencia y entrega al menos una vez; que el receptor reconozca el identificador es indispensable para evitar duplicación tras una respuesta perdida.
- Calidad: criterios de aceptación, pruebas conjuntas y evidencia con versión, fecha y ambiente.

## Configuración

Ver `backend/.env.sol.example`. En `REAL` se exigen todas las rutas y dos tokens distintos de 32+ caracteres; una configuración incompleta impide arrancar con un mensaje explícito. No hay retorno silencioso a datos locales.

Las siguientes rutas son **solo del simulador local**, reemplazables por las acordadas:

```dotenv
SOL_INTEGRATION_MODE=REAL
SOL_BUS_BASE_URL=http://127.0.0.1:8020
SOL_CAP_SEARCH_PATH=/cap/references
SOL_CAP_REFERENCE_PATH=/cap/references/{idCliente}
SOL_EVA_SEND_PATH=/eva/applications
SOL_EVA_STATUS_PATH=/eva/operations/{idOperacion}
SOL_AUDIT_PATH=/security/events
```

Definir también `SOL_BUS_TOKEN` y `SOL_EVA_CALLBACK_TOKEN` con valores privados diferentes. No copiarlos en capturas. En otra terminal, definir `SOL_SIMULATOR_TOKEN` con el mismo valor de `SOL_BUS_TOKEN` y ejecutar `python -m uvicorn SOL.simulator:app --host 127.0.0.1 --port 8020`. Este servidor es un simulador en memoria, no el Bus del proyecto.

El frontend usa `SOL_GATEWAY_URL=http://127.0.0.1:8011/sol` al practicar HTTP local. Con Bus institucional debe apuntar a la ruta de entrada que ese equipo publique. `/gateway/sol` solo se expone en modo SIMULADO.

## CR-INT-01

GET de búsqueda con `search` y `limit=50`; devuelve una lista acotada. GET de referencia con `{idCliente}`; devuelve:

```json
{"id_cliente":"0198b000-0000-7009-8000-000000000001","cod_tipo_documento":"DNI","numero_documento":"70000001","nombres":"Cliente sintético","apellido_paterno":"Prueba","apellido_materno":"Laboratorio","estado_cliente":"ACTIVO","id_caso":"CASO-DEMO-1","id_verificacion":"VER-DEMO-1","fecha_verificacion":"2026-10-23","vigente_hasta":"2026-11-22","estado_habilitante":"HABILITADO","version_contrato":"CR-INT-01-PROPUESTA-v2","simulado":true}
```

Se validan coincidencia de cliente y vigencia según Lima. Ausente, bloqueado o vencido: rechazo funcional 422. Fallo de transporte/contrato: 503. SOL conserva una referencia mínima en su propia base; no escribe en tablas de Clientes. No solicita ni expone celular, correo o nacimiento, tampoco en versiones históricas leídas por la API. Los fiadores reales necesitan un contrato específico de identidad: no se incorpora una dependencia directa nueva a Clientes ni se presenta una referencia sintética como validación institucional.

## CR-INT-02

POST envío conserva `idSolicitud`, `versionSolicitud`, `idOperacion`, `idCorrelacion`, `expediente`, `actorEnvio`, `versionContrato=CR-INT-02-PROPUESTA-v2` y `simulado`. `actorEnvio` se obtiene de la sesión, nunca de un campo editable del navegador. El expediente conserva las condiciones, respaldos, política y calendario de esa versión.

Acuse esperado (POST y GET de consulta deben devolver el mismo objeto):

```json
{"idSolicitud":"UUID-solicitud","versionSolicitud":1,"idOperacion":"UUID-operacion","idEvaluacion":"EVA-ID","ronda":8,"acuse":"ACK-ID"}
```

La ronda es de EVA: no se deduce de la versión. SOL valida solicitud, versión, operación, evaluación, ronda positiva y acuse. La restricción única solicitud/versión y la reserva temporal impiden iniciar dos entregas locales de la misma versión.

`POST /sol/applications/{id}/send` recibe la revisión y `X-Idempotency-Key`. En REAL confirma primero una reserva durable y responde **202 pendiente**; el worker realiza HTTP fuera de la petición digital. Un 202 no significa recepción de EVA. Durante la reserva se bloquean ediciones. La interfaz conserva/reutiliza la operación pendiente, incluso al recargar el detalle, y permite actualizar su estado. Con acuse válido se aplica el estado existente EN_EVALUACION y se registra el evento. Repetir la misma clave devuelve el acuse; otra clave para esa versión se rechaza.

Timeout de fase HTTP configurable (0,6 s por defecto); como máximo dos reintentos adicionales por ciclo (tres intentos). Antes de cada POST se consulta recepción. El presupuesto de inicio de llamadas del ciclo es 2,4 s; HTTPX mide fases de conexión/lectura, no un plazo absoluto de reloj de toda la operación. El puente del navegador aborta a los 3 s. La cola reprograma ciclos fallidos con espera creciente de 10 a 300 s; no genera claves nuevas. Una reserva abandonada se recupera tras 30 s. No se envían adjuntos ni se admite streaming.

## CR-INT-03

EVA/Bus llama **POST `/sol/integrations/evaluation-results`**, directamente al servidor, fuera del puente del navegador. Cabeceras: `Authorization: Bearer <SOL_EVA_CALLBACK_TOKEN>`, `X-Idempotency-Key` y `X-Correlation-ID`. Los dos identificadores deben coincidir con el cuerpo:

```json
{"idSolicitud":"UUID-solicitud","versionSolicitud":1,"idEvaluacion":"EVA-ID","ronda":8,"idOperacion":"UUID-resultado","idCorrelacion":"UUID-correlacion","decision":"OBSERVADO","observaciones":"Precisar el destino declarado."}
```

Se valida evaluación/ronda del acuse y versión vigente pendiente. Se rechaza un resultado de otra versión/ronda, una operación reutilizada con otro contenido o una sesión de usuario usada como credencial de servicio. Un mensaje idéntico repetido solo se reconoce, sin añadir un resultado/evento. EVA debe reintentar si el callback llega antes de que SOL concilie el acuse. En REAL se deshabilita `demo-result` y el ingreso de la cuenta evaluador.demo.

Se conservan únicamente las decisiones de la demo (APROBADO/OBSERVADO/RECHAZADO) y su traducción existente. No se inventan estados oficiales, rondas adicionales sobre la misma versión, condiciones financieras resultantes ni aceptación del cliente: requieren acuerdo de negocio.

## CR-INT-10 y operación

Cada evento de expediente y acceso crea su outbox en la misma transacción. Mensaje: `idEvento`, `idOperacion`, `idCorrelacion`, `tipo`, `actor`, `sujeto` afectado cuando corresponda, `fecha` UTC y, cuando corresponda, solicitud/versión/estados. Sin cuerpo de solicitud, contraseña, token o datos de contacto.

Acuse: `{"idEvento":"UUID-evento","confirmado":true,"acuse":"ACK-ID"}`. Solo entonces se marca CONFIRMADO. En modo SIMULADO se marca SIMULADO con acuse AUD-DEMO; no se presenta como confirmación central. Los pendientes de un modo no se exportan automáticamente al cambiar al otro.

El worker vive en el proceso FastAPI, con intervalo de 5 s; tras reiniciar recupera pendientes y respeta las reservas. Para un ciclo manual: `python -m SOL.manage maintain`. Se pueden ejecutar varios procesos: la reserva usa bloqueo en MySQL y vence tras una caída. Un error de contrato queda ERROR_CONTRATO para revisión, sin reintentos automáticos. Tras corregirlo, un operador puede ejecutar `python -m SOL.manage retry-errors` para reencolar conservando los identificadores.

`GET /sol/ops/pending` (supervisor/auditor) permite ver operaciones pendientes y conteos de auditoría. `GET /sol/ops/metrics` devuelve muestras y p95 medido por operación; ventana máxima de 10 000 por proceso, reiniciada al arrancar. No equivale a una plataforma central ni fija metas de I-05.

`/health` comprueba proceso. `/ready` ejecuta SELECT 1 y devuelve 503 si la base no responde; no acredita disponibilidad de los vecinos ni migraciones aplicadas. Los logs JSON se escriben a stdout: Infraestructura debe conservarlos y definir retención. Incluyen ruta normalizada, estado, duración, `idOperacion` y `idCorrelacion`, sin cuerpos, cabeceras secretas ni query. `X-Correlation-ID` se devuelve al navegador.

La baja local es `POST /sol/admin/users/{username}/disable`, supervisor autenticado, cuerpo `{"motivo":"Baja autorizada de laboratorio"}`. Deshabilita y revoca todas las sesiones; no permite autobaja. La facultad del supervisor es del laboratorio, pendiente de homologación con Seguridad. No reemplaza SSO/MFA. Se limpian sesiones vencidas al ingresar y en mantenimiento. Se registran ingresos, fallos, bloqueo temporal, cierre y baja en eventos/outbox. No se registra la contraseña ni el texto libre del motivo en los logs.
