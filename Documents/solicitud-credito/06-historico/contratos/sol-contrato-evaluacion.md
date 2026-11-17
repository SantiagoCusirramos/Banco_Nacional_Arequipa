> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# E04 — Contrato de intercambio SOL ↔ Evaluación

Fecha: 2026-11-14, America/Lima. Base HEAD `86904edd8dc866c1d4260a996748a1cda3770007` más cambios locales E02–E04. Estado: contrato técnico existente de laboratorio y propuesta para homologación; **no hay proveedor EVA/Bus institucional confirmado**. Este documento no publica un servicio externo ni aprueba política crediticia.

Fuentes: [CONTRATOS_HTTP_V2.md](CONTRATOS_HTTP_V2.md), `backend/SOL/app.py:361`, `:501`, `integrations.py:105`, `:227`, `operations.py:30`, `schemas.py:53`. Evidencia y limitaciones en [sol-evaluacion.md](../etapas/sol-evaluacion.md).

## Propietarios, rutas y credenciales

| Operación | Propietario / consumidor | Ruta y disponibilidad |
| --- | --- | --- |
| Iniciar envío local | SOL / asesor mediante Next.js | POST `/sol/applications/{identifier}/send`, implementado; alias `/gateway/sol/...` solo SIMULADO |
| Consultar detalle/transporte local | SOL / usuario autenticado | GET `/sol/applications/{identifier}`; `envios` contiene operación/versión/acuse/estado/evaluación/ronda. No es endpoint por operación de EVA |
| Pendientes operativos | SOL / SUPERVISOR o AUDITOR | GET `/sol/ops/pending`; no autoriza al token callback a consultar expedientes |
| Consultar recepción remota | EVA o Bus acordado / worker SOL | GET `SOL_EVA_STATUS_PATH`, debe incluir `{idOperacion}`. Ejemplo `/eva/operations/{idOperacion}` existe en simulador, no confirmado institucionalmente |
| Recibir expediente | EVA o Bus acordado / worker SOL | POST `SOL_EVA_SEND_PATH`. Ejemplo `/eva/applications` es de simulador |
| Recibir resultado | SOL / EVA o Bus servidor a servidor | POST `/sol/integrations/evaluation-results`, implementado, habilitado solo REAL; no tiene alias gateway ni pasa por proxy navegador |
| Crear versión de subsanación | SOL / asesor | POST `/sol/applications/{identifier}/revise`, implementado |

Sesión de asesor: Bearer opaco de login SOL; el proxy lo toma de cookie HttpOnly. Salida SOL→proveedor: Bearer `SOL_BUS_TOKEN`, base `SOL_BUS_BASE_URL`, configurados en servidor. Entrada EVA→SOL: Bearer `SOL_EVA_CALLBACK_TOKEN`, distinto al saliente y de al menos 32 caracteres. No se exponen tokens en ejemplos ni se confunden con JWT CORE/COREDB. Los esquemas OpenAPI E01 son históricos: E04 agrega la cabecera callback requerida, no resuelve todavía los DTOs de salida/auth incompletos registrados en E01.

## CR-INT-02 — Reserva, sobre y acuse

### Inicio local

POST `/sol/applications/{identifier}/send`, usuario ASESOR, JSON `{"revision":1}`, `X-Idempotency-Key` estable de 8–80 caracteres seguros (`A-Za-z0-9._:-`), correlación segura o generada por middleware. La versión se obtiene del servidor; actorEnvio sale de la sesión. No se acepta expediente/actor editable en este endpoint.

Antes de HTTP se valida cliente CAP, revisión/estado/política/fecha, se guarda Delivery y se congela Version. La restricción única solicitud/versión y la PK operación evitan reservar otra entrega local. En REAL se responde **202** con Detail, `pendiente_envio:true` e `idOperacion`; el negocio sigue BORRADOR pero la versión está congelada. No significa recepción EVA ni permite editarla.

Reintento misma clave y misma revisión original: reutiliza sobre/operación/correlación originales. Otra clave para esa versión o misma clave con revisión/solicitud distinta: 409. Tras confirmación, la misma petición devuelve 200 con detalle y `reintento_reconocido:true`; no reenvía el expediente. No se cambia la clave para resolver un timeout. Esta garantía es del envío; no se extiende a POST de alta.

### Sobre saliente

Campos actuales: `versionContrato`, `idSolicitud`, `versionSolicitud`, `idOperacion`, `idCorrelacion`, `expediente`, `actorEnvio`, `simulado`. `expediente` es el snapshot completo de la versión: cliente mínimo, condiciones/garantías, referencias de fiadores, política y calendario preliminar. Los ejemplos de fiadores reales siguen bloqueados por su contrato de identidad; no se inventa validación para habilitar el envío.

Ejemplo simbólico, no expediente operativo válido por sí solo:

```json
{"versionContrato":"CR-INT-02-PROPUESTA-v2","idSolicitud":"sol-e04","versionSolicitud":1,"idOperacion":"envio-e04-0001","idCorrelacion":"trace-envio-e04","actorEnvio":"asesor-sintetico","simulado":true,"expediente":{"cliente":{},"condiciones":{},"fiadores":[],"politica":{},"calendario":{}}}
```

Los objetos vacíos representan contenido omitido del snapshot, no una aceptación de expedientes incompletos por EVA. No se envían adjuntos ni streaming. SIMULADO usa acuse local; REAL significa transporte HTTP y puede seguir apuntando a un fake de laboratorio.

### Consulta y recepción remotas a homologar con EVA

Antes de **cada** POST, SOL hace GET por la operación original con Bearer y `X-Correlation-ID`. Si obtiene acuse válido, confirma sin POST. Un **404 debe significar de forma autoritativa «no recibido»**; solo entonces hace POST con el sobre y `X-Idempotency-Key=idOperacion`. Si GET falla, no se reenvía a ciegas. EVA debe deduplicar persistentemente por operación y devolver el mismo acuse en POST/GET, incluso si la respuesta inicial se pierde. La reutilización de clave con contenido distinto debe rechazarse; esa capacidad remota requiere evidencia del proveedor, no basta la unicidad local.

Acuse simbólico:

```json
{"idSolicitud":"sol-e04","versionSolicitud":1,"idOperacion":"envio-e04-0001","idEvaluacion":"eva-e04","ronda":8,"acuse":"ACK-E04"}
```

SOL exige identidad exacta de solicitud/versión/operación; versión entero JSON real (no bool/decimal/string); `idEvaluacion` string de 1–80, no blanco ni con espacios exteriores (compatible con el DTO callback); ronda entera positiva; acuse string de 1–60 no blanco. La ronda la asigna EVA; no se deduce de versión. Un 2xx sin acuse compatible no es confirmación.

Transporte actual: timeout por fase 0,6 s; máximo dos reintentos adicionales por ciclo y presupuesto de inicio de llamadas 2,4 s. HTTPX no garantiza con ello un plazo absoluto de toda la operación. Reintentos no generan nuevos IDs ni nuevos snapshots. Logs evitan cuerpos/secretos remotos.

### Persistencia, caída y exclusión de intentos tardíos

La transacción de reserva termina antes de HTTP. Un worker reserva 30 s y aumenta `Delivery.attempts`; ese contador existente identifica la generación de la reserva. Al regresar del HTTP bloquea/relee Delivery:

- CONFIRMADO por otro intento: mantiene confirmación, sin otro evento de envío.
- Generación o estado cambiados: el resultado tardío no cambia la reserva ni el expediente.
- Intento vigente y acuse válido: guarda evaluación/ronda/acuse, pasa negocio a EN_EVALUACION y crea historial/outbox en transacción.
- Error transitorio vigente: deja PENDIENTE y reprograma con backoff 10–300 s.
- Error contractual vigente: deja ERROR_CONTRATO, sin reintento automático.

Si el proceso cae tras aceptar EVA pero antes de persistir acuse, la reserva permanece durable; al vencer, otro intento consulta GET y concilia. No libera ni modifica la versión congelada. Un operador puede revisar configuración/contrato y usar el comando existente `python -m SOL.manage retry-errors` en un entorno SOL autorizado, que conserva IDs; no se ejecutó ese comando sobre bases reales en E04. Repetir send no corrige por sí solo ERROR_CONTRATO, aunque responda 202 con estado técnico en el detalle.

## CR-INT-03 — Callback de resultado

POST `/sol/integrations/evaluation-results`, directamente a SOL. Cabeceras **explícitas**:

- `Authorization: Bearer <credencial-de-callback>`.
- `X-Idempotency-Key: resultado-e04-0001`, igual a `idOperacion` del resultado.
- `X-Correlation-ID: trace-resultado-e04`, igual a `idCorrelacion` del cuerpo; caracteres seguros 1–100. No se sustituye por la correlación generada del middleware si falta.

La operación de resultado identifica ese mensaje, no la operación de envío. Su correlación debe coincidir cuerpo/cabecera; no se impone que sea idéntica a la correlación de envío, porque el contrato actual no establece esa regla. EVA debe reutilizar ambas al reintentar el mismo resultado.

```json
{"idSolicitud":"sol-e04","versionSolicitud":1,"idEvaluacion":"eva-e04","ronda":8,"idOperacion":"resultado-e04-0001","idCorrelacion":"trace-resultado-e04","decision":"OBSERVADO","observaciones":"Precisar el destino declarado de prueba."}
```

Tipos actuales: solicitud string 1–36; evaluación 1–80; versión/ronda enteras estrictas positivas; operación segura 8–80; correlación segura 1–100; decisión APROBADO/OBSERVADO/RECHAZADO; observaciones 5–1000. Pydantic rechaza campos extra. El receptor valida solicitud existente, versión vigente EN_EVALUACION y Delivery REAL CONFIRMADO con la misma evaluación/ronda. No consume un puntaje ni decide riesgo.

Respuesta primera recepción: `{"recibido":true,"idOperacion":"resultado-e04-0001","estado":"OBSERVADA"}`. Repetición idéntica ya registrada: `{"recibido":true,"reintento_reconocido":true,"idOperacion":"resultado-e04-0001"}`, sin nuevo resultado/evento ni cambio de revisión. Esa repetición puede reconocerse después de una subsanación; **no vuelve a aplicar el resultado viejo**. Una operación nueva con versión vieja/ronda incorrecta, identidad cruzada o resultado sobre versión ya resuelta devuelve 409. Misma operación con contenido distinto también 409.

Si callback llega antes de que SOL concilie el acuse local: 409 sin aplicar nada. EVA debe reintentar el mismo mensaje después; la deduplicación local reconoce una recepción repetida si EVA perdió la respuesta. SOL no implementa aquí una cola de resultados adelantados ni inventa otra ronda para encajarlos.

## Estados existentes y subsanación

| Disparador | Transición local permitida |
| --- | --- |
| Reserva de envío | BORRADOR con versión congelada; 202 técnico |
| Acuse compatible confirmado | BORRADOR → EN_EVALUACION |
| Callback OBSERVADO | EN_EVALUACION → OBSERVADA |
| Callback APROBADO | EN_EVALUACION → APROBADA |
| Callback RECHAZADO | EN_EVALUACION → RECHAZADA |
| Asesor solicita revise con revisión vigente | Solo OBSERVADA → BORRADOR, versión+1/revisión+1, copia snapshot a nueva versión |

Las ediciones posteriores recalculan solamente el borrador nuevo y no alteran versiones previas. Otra observación puede generar v3 de la misma forma. No se admite subsanar una solicitud APROBADA/RECHAZADA mediante revise. Son los estados de demo existentes, pendientes de homologación de negocio. APROBADA en SOL no acredita autorización institucional de desembolso ni aceptación del cliente. No hay equivalencia automática DERIVAR→OBSERVADO, condiciones financieras resultantes ni motor de riesgo nuevo.

## Respuestas y responsabilidad de reintento

| HTTP / condición | Receptor / acción |
| --- | --- |
| 200 local | Detalle confirmado o callback recibido/duplicado idéntico; inspeccionar cuerpo |
| 202 local | Envío durable pendiente; consultar detalle, conservar clave. No anunciar acuse EVA |
| 401 | Sesión SOL o credencial callback inválida; callback no disponible en SIMULADO |
| 403 | Rol SOL no permitido; demo-result bloqueado en REAL |
| 404 | Solicitud inexistente; distinto de 404 de recepción EVA |
| 409 | Conflicto de clave/revisión/estado/versión/evaluación/ronda; si callback adelantado, EVA reintenta el mismo mensaje tras conciliación |
| 422 | JSON/cabeceras/IDs incompatibles o CAP no habilita el envío; corregir causa, no inventar referencia |
| 503 local | Base/política/dependencia CAP indisponible; no equivale a recepción EVA |
| 408/429/5xx transitorio o timeout remoto | Worker reprograma con la misma operación; consulta recepción antes de POST |
| Rechazo/acuse/JSON remoto incompatible | ERROR_CONTRATO; revisión operativa, sin reintento automático |

Los errores funcionales actuales usan `detail` string/objeto y la validación FastAPI usa lista. No se promete un DTO uniforme ni respuesta p95 institucional. La selección exacta de código puede depender de validación de entrada previa a auth: un mensaje sin cabeceras requeridas puede recibir 422 antes de verificar credencial.

## Conexión futura y bloqueos

EVA/Bus deben entregar rutas/versiones reales de recepción y consulta, significado consistente de 404, acuse durable/idempotente, política de evaluación/ronda, credenciales/TLS/origen y un emisor callback reintentable. Deben acordarse estados/decisiones/resultados financieros y DA-SOL-002/008/009 con sus actas originales. No hay evidencia nueva de homologación en E04.

CORE legado `/core/creditos/solicitudes/{id}/evaluar` no satisface este sobre/acuse/consulta por operación ni emite este callback; no se conecta ni modifica. Los fakes prueban transporte/gestión local, no la persistencia ni deduplicación de un proveedor institucional. MySQL/locks concurrentes, HTTP entre procesos y recorrido real se verificarán en entorno aislado y con los equipos, sin inferir autorización para scripts globales destructivos.
