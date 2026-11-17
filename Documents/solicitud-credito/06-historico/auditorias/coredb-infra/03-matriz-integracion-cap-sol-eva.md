> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# 03 — Matriz CAP → SOL → EVA y contratos

Fecha: 2026-11-16 (America/Lima). Rama analizada: `feature/sol-integracion-cap-eva`. HEAD: `988dc0776da282fbef306632fc86426b6e372376`. Auditoría estática, sin arranque, SQL, migraciones, cambios de rama ni consultas remotas. Las referencias `origin/*` son copias locales; su nombre no acredita el estado actual de un PR.

## Criterio de compatibilidad

Compatible significa coincidencia estática de campos/rutas, no integración ejecutada. Todas las rutas CAP/EVA pertenecen exclusivamente a las refs fijadas en [01](01-inventario-infraestructura.md). SOL y COREDB corresponden al HEAD. Transporte REAL significa HTTP; CAP declara verificaciones simuladas incluso cuando responde por HTTP y persiste en MySQL.

| Etapa | Emisor | Receptor | Endpoint real | Compatible | Bloqueos | Evidencia |
|---|---|---|---|---|---|---|
| A registro prospecto/caso | personal | CAP ref | POST /api/v1/captacion/solicitantes ; POST /api/v1/captacion/casos | sí, interno CAP | paquete no integrado; completar consentimientos/validaciones/perfil antes de habilitar | routers/captacion.py:42,66; services/captacion.py:177,453 |
| A habilitación | personal | CAP ref | POST /api/v1/captacion/casos/{id_caso}/habilitar | sí, estático | caso APROBADO y faltantes vacíos; proveedores de identidad simulados | routers/captacion.py; services/captacion.py:453–513 |
| A identidad/alta | CAP ref | COREDB | POST /coredb/clientes/validaciones/documento ; POST /coredb/clientes | sí, estático | usuario SERVICIO:CLIENTES y SQL inicializado | CAP/core_client.py:133–150; COREDB/routers/clientes.py |
| A contacto/consulta | CAP ref | COREDB | POST /coredb/clientes/{cod_cliente}/validaciones ; GET /coredb/clientes/{cod_cliente} | sí, estático | COREDB disponible; autorizaciones | CAP/core_client.py:142–150 |
| B búsqueda | SOL | CAP ref | GET /cap/references?search=…&limit=50 | sí, estático | CAP ausente en HEAD; token; búsqueda usa snapshot local CAP | CAP/routers/referencias.py:23; SOL/integrations.py:127 |
| B referencia vigente | SOL | CAP ref | GET /cap/references/{id_cliente} | sí, estático | ACTIVO/HABILITADO y fecha vigente; referencia individual consulta COREDB | CAP/services/captacion.py:547; SOL/integrations.py:116,243 |
| C crear solicitud | asesor | SOL | POST /sol/applications | sí, local implementado | sesión local, política, MySQL propia y referencia válida | SOL/app.py:328; service.py prepare; schemas.py:32 |
| D reservar envío | asesor | SOL | POST /sol/applications/{identifier}/send | sí, local implementado | revision y X-Idempotency-Key; REAL retorna 202, worker posterior | SOL/app.py:390–441 |
| D recepción/acuse | SOL | EVA ref | GET /eva/operations/{id_operacion} antes de POST /eva/applications | sí, estático | EVA ausente HEAD; token y worker; configuración REAL de auditoría | SOL/integrations.py:140; EVA/main.py:185–202 |
| D evaluar | analista | EVA ref | POST /eva/v1/evaluaciones/{id_evaluacion}/situacion-financiera ; POST /eva/v1/evaluaciones/{id_evaluacion}/decision | sí, estático | JWT COREDB y permisos; EN_REVISION y versión de edición | EVA/main.py:238–247; servicio.py:209,246 |
| E devolver resultado | EVA ref | SOL | POST /sol/integrations/evaluation-results | sí, esquema; ejecución pendiente | EVALUACION_SOL_URL vacía; callback solo REAL; requiere acuse ya conciliado | EVA/envios.py:30,70; SOL/app.py:531 |
| CR10 eventos | SOL | auditoría | ruta configurada; laboratorio /security/events | laboratorio preparado | REAL exige configuración; overlay y gate no activados; no homologación | SOL/settings.py:58; integrations.py audit; laboratorio/compose.audit-sim.yaml |

Ninguna fila está verificada de extremo a extremo en esta auditoría. Los informes `sol-pruebas-integracion-cap-eva.md` y `sol-integracion-entrega-final.md` contienen antecedentes HTTP independientes y tests; no equivalen a ejecutar SOL→EVA→SOL en este turno, ni prueban un acuse de resultado institucional.

## Autenticación y variables que deben coincidir

| Canal | Credencial exigida | Correspondencia / configuración |
|---|---|---|
| CAP→COREDB servicio | JWT obtenido por POST /coredb/auth/login, rol SERVICIO módulo CLIENTES | CAP_CORE_USUARIO y CAP_CORE_SECRETO o CAP_CORE_SECRETO_ARCHIVO corresponden al usuario creado en COREDB; CORE_BASE_URL=http://coredb:8012 |
| Personal CAP→COREDB | JWT de persona | CAP consulta /coredb/auth/me; CREAR_CLIENTE para operar, VER_CLIENTE para leer |
| EVA→COREDB | JWT de persona reenviado a /coredb/auth/me | COREDB_URL=http://coredb:8012; no token de servicio EVA para persistencia crediticia |
| SOL→CAP | Bearer fijo | SOL_CAP_TOKEN = CAP_SOL_TOKEN; SOL_CAP_BASE_URL=http://captacion:8014 |
| SOL→EVA | Bearer fijo | SOL_EVA_TOKEN = EVALUACION_TOKEN_SOL; SOL_EVA_BASE_URL=http://evaluacion:8015 |
| EVA→SOL | Bearer distinto del anterior | EVALUACION_SOL_TOKEN_RESULTADOS = SOL_EVA_CALLBACK_TOKEN; EVALUACION_SOL_URL=http://sol:8011 |
| SOL→auditoría laboratorio | Bearer fijo propio | SOL_AUDIT_TOKEN = SOL_SIMULATOR_TOKEN, SOL_AUDIT_BASE_URL=http://audit-lab:8020, SOL_AUDIT_PATH=/security/events |

Secretos solo en entorno/archivos privados, nunca en estos informes. SOL exige pares URL/token completos, tokens 32+ sin espacios y callback diferente de proveedores. Puede recurrir al par Bus si no se configura un par específico; un par específico incompleto falla, no se mezcla. EVA exige token receptor y callback distintos. CORE_DB_JWT_CLAVE solo firma JWT COREDB; no debe confundirse con los Bearer fijos de CR01/02/03. Roles SOL usan sesiones propias con hashes; no hay SSO institucional demostrado.

## Recorrido y persistencia

A. CAP registra un prospecto y un caso con IDs propios. Habilitar exige estado APROBADO y requisitos completos; consulta por documento en COREDB. Reutiliza cod_cliente del cliente ACTIVO o registra uno nuevo HABILITADO solo si motivo=NO_ES_CLIENTE. Guarda cod_cliente antes de continuar para recuperar fallos parciales; registra validaciones de contacto y consulta estado. El código generado en COREDB es la identidad compartida; id_solicitante e id_caso no lo reemplazan. Repetir validaciones tras fallo parcial puede crear nuevos registros: no confundir recuperación del alta con idempotencia global de CAP.

B. CAP proyecta cod_cliente→id_cliente, tipo_documento→cod_tipo_documento, id_verificacion_captacion→id_verificacion y añade caso/vigencia. Lista cruda, sin sobre ITIL; detalle crudo. La búsqueda puede contener REVOCADO o estado guardado desactualizado: no es por sí sola filtro definitivo de habilitación. SOL reconsulta detalle al crear/enviar. 404 CAP se convierte en 422 funcional SOL; transporte/JSON/campos inválidos en503. SOL exige coincidencia de ID, ACTIVO/HABILITADO y fecha_verificacion ≤ hoy Lima ≤ vigente_hasta.

C. SOL `prepare` valida política/condiciones, calcula calendario PRELIMINAR francés con Decimal y proyecta identidad mínima; persiste Application BORRADOR, Version 1 editable, snapshot, garantías y eventos en su propia base. No escribe COREDB. El envío congela versión y reserva Delivery durable antes del HTTP. Editar congelada se rechaza; revise crea versión nueva tras OBSERVADA. Fiadores REAL están bloqueados por falta de contrato específico; la demostración mínima debe usar escenario permitido sin fiadores, sin modificar ese control. Pago doble no se habilita con un booleano.

D. Worker consulta operación EVA; solo 404 autoriza POST. GET fallido no provoca POST ciego. Envelope: versionContrato, idSolicitud, versionSolicitud, idOperacion, idCorrelacion, expediente (cliente, condiciones, política, calendario, respaldos), actorEnvio y simulado. EVA guarda sobre íntegro/huella en eva_expediente y evaluación en eva_evaluacion; no usa creditos.solicitud_credito de COREDB. Acuse contiene idSolicitud/versionSolicitud/idOperacion/idEvaluacion/ronda/acuse. SOL valida coincidencias antes de CONFIRMADO/EN_EVALUACION. EVA deduplica misma operación/contenido y rechaza409 reutilización o versión ya recibida. VersionSolicitud y ronda no son intercambiables.

E. EVA registra situación financiera y decisión bajo permisos de analista; genera operación de resultado nueva, distinta de la de envío, conservando idSolicitud, versión, evaluación, ronda y correlación. Guarda eva_envio PENDIENTE y reintenta callback por worker. SOL valida Bearer, cuerpo/cabeceras, versión vigente, evaluación/ronda del acuse y Delivery REAL CONFIRMADO. Duplicado idéntico retorna recibido:true sin duplicar Outcome; mismo ID con cuerpo distinto o resultado viejo devuelve409. APROBADO/OBSERVADO/RECHAZADO se traducen a APROBADA/OBSERVADA/RECHAZADA. Callback anterior a conciliación:409 recuperable por EVA.

## Comparación de contratos concretos

| Campo / contrato | COREDB | CAP ref | SOL HEAD | EVA ref | Acción / propietario |
|---|---|---|---|---|---|
| Cliente | cod_cliente alfanumérico ≤12 | id_cliente=código COREDB ≤36 en ruta | referencia ≤36, no exige UUID | cliente.id_cliente ≤36 | compatible vía CAP, no inventar UUID |
| Documento | tipo_documento ≤10, numero ≤12 | proyección cod_tipo_documento/numero | número ≤20, tipo opcional | tipo default DNI, número ≤20 | usar dato CAP explícito; no ampliar validación COREDB |
| Segundo apellido | str o null | convierte a cadena vacía | project_identity normaliza null/ausencia a vacío | nullable/default null | compatible con HEAD; conservar normalización |
| Caso/verificación/vigencia | verificación sí; caso/vigencia no | agrega campos y fechas YYYY-MM-DD | exige strings no vacíos y fechas ISO canónicas | persiste snapshot recibido | COREDB directo no sustituye CR01 |
| version_contrato | términos del cliente | CR-INT-01-PROPUESTA-v2 | etiqueta de referencia distinta de política/envelope | versionContrato del envelope | no confundir versiones ni declarar homologación |
| Solicitud/operación | tablas binarias UUID; sin API CR02 | caso distinto | UUID solicitud string ≤36; operación patrón8–80 | strings, UNIQUE y huella | compatible por HTTP; no insertar SQL integrado |
| Versión y revisión | version_solicitud SQL | versión términos | versionSolicitud entera estricta; revision concurrencia | versionSolicitud estricta; version edición separada; ronda propia | no mapear revision a ronda |
| Monto/plazo/moneda | DECIMAL y catálogos | no fija crédito SOL | Decimal; DTO plazo1–600, política efectiva propuesta1000–50000 PEN/6–60 | Decimal15,2, plazo1–600, PEN/USD | EVA admite más; mantener límites de SOL sin ampliar política |
| Calendario | tablas calendario/cuota | no produce | PRELIMINAR, fechas date, importes strings decimales | cuotas tipadas y validación sumas/numeración/fechas | compatible estático; no representa calendario oficial |
| Garantías/fiadores | tablas propias SQL | no contrato específico fiadores | hasta10 garantías/5 referencias; REAL fiadores rechazado | ExpedienteSol valida núcleo e ignora extras, guarda JSON completo | no implica evaluación semántica de garantías/fiadores; contrato adicional externo |
| Estado/decisión | estado cliente y catálogos SQL | caso HABILITADO/REVOCADO, referencia simulado:true | BORRADOR→EN_EVALUACION→estado femenino | PENDIENTE/EN_REVISION, decisión masculina | mapeo explícito ya existe en SOL |
| Observaciones | sin API EVA | motivo captación distinto | callback min5/max1000 | DecisionIn min10/max1000 | salida de decisión manual compatible; probar todas las ramas del motor |
| Fechas/nulos | fecha_verificacion str; SQL datetime | fecha/vigencia date ISO | date para cuotas, eventos UTC con Z | date y datetime; desembolso AwareDatetime fuera del flujo | no copiar timestamp como fecha CR01 |
| Extras/errores | extra forbid/strict en clientes; error con code | sobre en API personal, crudo en CR01 | inputs forbid; 422 funcional/503 proveedor | CR02 extra ignore, personal forbid; ErrorEva | no usar /api/v1/captacion como CR01 ni mezclar sobres |

La mayoría de traducciones ya está en CAP/SOL. No hace falta nueva API COREDB para la demo por servicios propietarios. La ausencia de CAP/EVA en HEAD requiere componer fuentes/despliegue o integrar sus cambios en una fase posterior. Corregir el acuse del despachador EVA exige cambiar EVA, no se resuelve de manera fiable solo con adaptador SOL: `envios.py:78–80` marca ENTREGADO por cualquier 2xx sin comprobar recibido/idOperacion. Es riesgo estático confirmado por condición de código; no reproducido con HTTP en esta auditoría.

## Auditoría institucional y límites del laboratorio

SOL/settings.py:58–83 exige configurar auditoría al construir aplicación REAL. Ese es el bloqueo determinista del laboratorio base. `event` (service.py:100) y `security_event` guardan historial/outbox local; process_delivery y process_audit son independientes (operations.py:30,84,118). No se encontró gate que espere confirmación central para crear, enviar o recibir resultado; no se propone eliminar seguridad ni falsificar confirmación. Auditoría caída tras arranque deja pendientes/ERROR_CONTRATO según error; no convierte automáticamente una entrega EVA en fallida.

Alternativa existente: activar deliberadamente overlay de auditoría SIMULADA académica con credenciales propias, redes internas y datos tmpfs, conservar eventos locales y declarar CR10 simulado. Es mecanismo documentado y protegido por gate, no acta institucional aprobada. Si se exige cero procesos de auditoría, hoy no existe modo REAL CAP/EVA con auditoría solo local configurable: requeriría cambio explícito y revisado de SOL/settings/integrations/operations, conservando trazabilidad y separación del estado local frente al central. Esta auditoría no lo implementa ni autoriza su ejecución.
