> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Registro de ejecución P20. Evidencia válida para aquella ejecución; no certifica disponibilidad actual ni homologación.

# Endpoints y contratos utilizados

Fecha: 2026-11-16 (America/Lima). Rama `feature/sol-integracion-cap-eva`; HEAD `988dc0776da282fbef306632fc86426b6e372376`. CAP `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; EVA `57b0e2a34fd55fb96fd6245acc06a86536d220f8`. Sin merge, cherry-pick, cambio de rama, commit ni push.

## Direcciones y credenciales

Los nombres internos son los de Docker; los puertos host iniciales son18120 COREDB,18121 CAP,18122 SOL,18123 EVA y18124 Next.js (configurables por --port). El estado privado determina los valores efectivos. Una reproducción con --port18130 usa18130–18134.

| Canal | Credencial / requisito |
|---|---|
| CAP→COREDB | Login del servicio SERVICIO:CLIENTES con CAP_CORE_USUARIO y secreto propio; JWT COREDB. |
| Personal CAP/EVA | JWT obtenido por /coredb/auth/login; CAP valida /coredb/auth/me. Analista real creado por API con rol ANALISTA. |
| SOL→CAP | SOL_CAP_TOKEN=CAP_SOL_TOKEN. |
| SOL→EVA | SOL_EVA_TOKEN=EVALUACION_TOKEN_SOL. |
| EVA→SOL | EVALUACION_SOL_TOKEN_RESULTADOS=SOL_EVA_CALLBACK_TOKEN, distinto de tokens de proveedores. |
| SOL→auditoría académica | SOL_AUDIT_TOKEN=SOL_SIMULATOR_TOKEN; receptor explícitamente SIMULADO. |
| Asesor SOL | Sesión local emitida en /sol/auth/login; autorización de rol en servidor. Next guarda token en cookie HttpOnly. |

## APIs usadas por el runner

| Servicio | Método y ruta | Petición / respuesta resumida |
|---|---|---|
| COREDB | POST /coredb/auth/login | username/password → access_token JWT. Nunca guardar token en evidencia. |
| COREDB | POST /coredb/usuarios | usuario/nombre/password/rol ANALISTA →201 usuario; solo admin autorizado. |
| COREDB | GET /coredb/auth/me | JWT →perfil y acciones. |
| COREDB | POST /coredb/clientes/validaciones/documento | CAP declara identidad verificada →201 resultado y cliente nullable. |
| COREDB | POST /coredb/clientes | Identidad/contacto/términos/estado habilitante →201 cod_cliente generado. |
| COREDB | POST /coredb/clientes/{cod_cliente}/validaciones | Tipo/resultado/motivo →201 id_validacion. |
| COREDB | GET /coredb/clientes/{cod_cliente} |200 estado/identidad; se verifica código compartido y ACTIVO. |
| CAP | POST /api/v1/captacion/solicitantes | Prospecto sintético →201 data.solicitante. |
| CAP | POST /api/v1/captacion/casos | id_solicitante/canal WEB →201 caso. |
| CAP | POST /api/v1/captacion/casos/{id}/consentimientos | Lista TRATAMIENTO_DATOS/CONSULTA_BUROS/TERMINOS aceptados →201. |
| CAP | POST /api/v1/captacion/casos/{id}/otp | canal SMS →201 código simulado solo en memoria del runner. |
| CAP | POST /api/v1/captacion/casos/{id}/otp/verificar | canal/código →200. |
| CAP | POST /api/v1/captacion/casos/{id}/validaciones | RENIEC/LISTAS_NEGRAS/PEP →201; proveedores simulados. |
| CAP | POST /api/v1/captacion/casos/{id}/consultas-riesgo | central SBS →201; reporte externo simulado. |
| CAP | POST /api/v1/captacion/casos/{id}/perfil |201 perfil académico. |
| CAP | POST /api/v1/captacion/casos/{id}/habilitar |200 caso y código COREDB. |
| CAP | POST /api/v1/captacion/casos/{id}/estado | REVOCAR/motivo sintético →200; negativo de SOL. |
| CAP | GET /cap/references?search=…&limit=50 | Bearer servicio →lista cruda; búsqueda no certifica habilitación. |
| CAP | GET /cap/references/{id_cliente} | Bearer servicio →referencia cruda y vigente consultando COREDB. |
| SOL | POST /sol/auth/login | asesor.bna/password privado →token sesión. |
| SOL | GET /sol/clients?search=… | Sesión asesor →referencias desde CAP por HTTP. |
| SOL | POST /sol/preview | ApplicationInput →snapshot/calendario PRELIMINAR. |
| SOL | POST /sol/applications | ApplicationInput →201 BORRADOR/version1. |
| SOL | GET /sol/applications | Bandeja/paginación. Usada también mediante Next. |
| SOL | GET /sol/applications/{id} | Detalle/versiones/historial/estado. |
| SOL | PUT /sol/applications/{id} | Formulario+revision →edita solo BORRADOR. |
| SOL | POST /sol/applications/{id}/send | revision + X-Idempotency-Key →202 reserva local REAL; no acuse EVA. Repetición confirmada200. |
| SOL | POST /sol/applications/{id}/revise | revision →BORRADOR versión2 tras OBSERVADA; v1 inmutable. |
| EVA | GET /eva/operations/{id_operacion} | Bearer SOL →200 acuse;404 no recibido. |
| EVA | POST /eva/applications | Sobre CR02 + X-Idempotency-Key →201 nuevo/200 idéntico/409 reutilizado. |
| EVA | GET /eva/v1/evaluaciones/{id_evaluacion} | JWT analista →detalle, situación, envío e historial. |
| EVA | POST /eva/v1/evaluaciones/{id}/situacion-financiera | Ingreso/deuda/BUENO/verificada/version →EN_REVISION para escenario elegido. |
| EVA | POST /eva/v1/evaluaciones/{id}/decision | APROBADO/OBSERVADO/RECHAZADO,observaciones,version →resultado y outbox. |
| SOL | POST /sol/integrations/evaluation-results | Bearer callback+X-Idempotency-Key+X-Correlation-ID →200 recibido:true,idOperacion,estado. |
| Simulador auditoría | POST /security/events | Evento mínimo/idEvento →acuse académico explícitamente SIMULADO. |

Las APIs de personal CAP usan sobre data; CR01/02/03 utilizan objetos/listas crudos. No aplicar un desenvuelto genérico a todos los servicios.

## JSON de crédito sintético permitido

```json
{"id_cliente":"<código real generado por COREDB>","monto_solicitado":"15000.00","moneda":"PEN","plazo_meses":12,"destino_credito":"Integracion academica sintetica","fecha_base":"<hoy America/Lima YYYY-MM-DD>","garantias":[{"tipo_garantia":"VEHICULAR","descripcion":"Vehiculo sintetico laboratorio","valor_tasacion":"20000.00"}],"fiadores":[],"pago_doble":false}
```

El ejemplo usa marcadores, no se envía literalmente. Dinero Decimal, TEA/política vigente guardada en snapshot, sistema francés y saldo final0,00. No es política institucional aprobada.

CR01 contiene id_cliente, identidad mínima, id_caso, id_verificacion, fecha_verificacion, vigente_hasta, estado_cliente/estado_habilitante, version_contrato y simulado:true por verificadores externos. CAP transforma cod_cliente sin inventar UUID. Materno puede omitirse/null; SOL normaliza a vacío.

CR02 contiene versionContrato,idSolicitud,versionSolicitud,idOperacion,idCorrelacion,expediente,actorEnvio,simulado. El expediente congela cliente/condiciones/política/calendario y respaldos. GET y POST de EVA devuelven mismo acuse con idSolicitud,versionSolicitud,idOperacion,idEvaluacion,ronda,acuse. Ronda la asigna EVA, no se deduce de versión.

```json
{"idSolicitud":"<sol>","versionSolicitud":1,"idEvaluacion":"<eva>","ronda":1,"idOperacion":"<operación nueva de resultado>","idCorrelacion":"<correlación envío>","decision":"APROBADO","observaciones":"Decision academica sintetica para verificar integracion HTTP."}
```

CR03 usa una operación de resultado nueva. Cabeceras deben coincidir con cuerpo. SOL exige versión actual EN_EVALUACION y Delivery REAL CONFIRMADO, misma evaluación/ronda. Repetición idéntica200/reintento_reconocido; contenido distinto409. Acuse EVA endurecido exige recibido booleano true y operación exacta; cualquier2xx ya no basta.

## Errores y estados

401 token incorrecto;403 rol sin permiso;404 operación EVA ausente/cliente CAP ausente;409 conflicto de versión/operación/estado;422 esquema/referencia funcional;503 proveedor/transporte incompatible. CAP personal puede emitir400 por JSON inválido según su contrato. SOL convierte referencia no encontrada/no habilitada/vencida en422 y fallo de dependencia en503. No se fuerza cada servicio a devolver el mismo sobre de error.

La reserva202 mantiene versión congelada y operación durable. Worker consulta EVA antes del POST; solo404 permite enviar. Acuse válido produce EN_EVALUACION. Callback traduce APROBADO→APROBADA,OBSERVADO→OBSERVADA,RECHAZADO→RECHAZADA. No hay nueva decisión de riesgo calculada por SOL ni desembolso.
