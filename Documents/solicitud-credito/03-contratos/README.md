# Contratos HTTP utilizados y homologación pendiente

> Estado: **VIGENTE**. Última verificación documental: **2026-11-16** (código y evidencias existentes; sin repetir pruebas funcionales). Rama: `feature/sol-integracion-cap-eva`; SHA: `988dc0776da282fbef306632fc86426b6e372376`. Principal: [README SOL](../README.md).

## Jerarquía contractual

**Utilizado y verificado en laboratorio**: código actual SOL, CAP/EVA de SHA fijados y contrato que sigue. **PROPUESTO institucionalmente**: etiquetas CR-INT-01/02-PROPUESTA-v2 y CR03/10 no cuentan con homologación comprobada. No hay contrato corporativo de Bus desplegado. Los [contratos históricos](../06-historico/contratos/) conservan propuestas anteriores, no prevalecen sobre código y acuses P20.

Fuentes: [schemas SOL](../../../backend/SOL/schemas.py), [adaptador](../../../backend/SOL/integrations.py), [callback](../../../backend/SOL/app.py), CAP/EVA fijados por [prepare](../laboratorio/prepare.py), [registro contractual P20](../04-pruebas/p20/02-endpoints-y-contratos.md). El parche [patch_eva.py](../laboratorio/patch_eva.py) endurece acuse de retorno en copia aislada; no se declara aplicado a la rama EVA original.

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

## Propuestas y compatibilidad

La documentación HTTP v2 antigua mezclaba rutas de simulador con transporte REAL; aquí cada propietario está identificado. REAL describe transporte HTTP, no homologación ni identidad externa real. Materno nullable/ausente se normaliza sin inventar apellido; cod_cliente COREDB se conserva como id_cliente, no se convierte a UUID. CAP completa caso/vigencia que COREDB no proporciona por sí solo.

[CONTRATOS_HTTP_V2 original](../06-historico/contratos/CONTRATOS_HTTP_V2.md), [contrato E04](../06-historico/contratos/sol-contrato-evaluacion.md) y [coordinación pendiente](../06-historico/coordinacion/sol-coordinacion-proveedores.md) explican procedencia. Políticas financieras/resultantes, identidad de fiadores, SSO/TLS y auditoría institucional continúan propuestas/bloqueadas. No reutilizar contratos demo como callback institucional.

## Restricciones de modelos y respuestas (código actual)

Entradas SOL heredan extra=forbid y strip de strings. No se pueden enviar cuotas calculadas por el navegador como autoridad financiera. Las validaciones de política se aplican además de las del DTO.

| Modelo / campo | Restricción efectiva del DTO |
|---|---|
| Login |username1–60,password1–200; credenciales no se registran en evidencia. |
| ApplicationInput.id_cliente |string1–36; no exige UUID, conserva código COREDB. |
| monto_solicitado |Decimal positivo,max_digits15,decimal_places2; política restringe1000–50000. |
| moneda |string longitud3; política actual soloPEN. |
| plazo_meses |int estricto1–600 en DTO; política actual6–60. |
| destino_credito / fecha_base |string5–120 / date; prepare rechaza fecha anterior a hoy Lima. |
| pago_doble / revision |bool defaultfalse (true rechazado por negocio) /int≥1 nullable en ApplicationInput; envío/revise exigen RevisionInput. |
| garantias |lista≤10 defaultvacía; cada Guarantee:PERSONAL,HIPOTECARIA,VEHICULAR,MOBILIARIA,FONDOS; descripción5–200;tasación Decimal positiva15/2. |
| fiadores |lista≤5,strings1–36; no duplicados/autofiador; validación REAL bloqueada. |
| EvaluationResult.idSolicitud |string1–36. |
| versionSolicitud / ronda |int estricto≥1, ambos; no bool ni string. |
| idEvaluacion |string1–80. |
| idOperacion / idCorrelacion |patrones `^[A-Za-z0-9._:-]{8,80}$` y `^[A-Za-z0-9._:-]{1,100}$`. |
| decision / observaciones |APROBADO,OBSERVADO,RECHAZADO /string5–1000; el DecisionIn humano EVA exige10–1000 en su ref fijada. |

Acuse CR02: objeto con coincidencia exacta de idSolicitud/versionSolicitud/idOperacion; versión int real;idEvaluacion1–80 sin espacios externos;ronda int≥1;acuse string1–60 no vacío. Un2xx sin este contrato no confirma Delivery. El callback SOL devuelve recibido:true e idOperacion; el parche EVA exige exactamente HTTP200 y estos campos coherentes antes de ENTREGADO. Extras de respuesta no se confunden con autorización para campos extra de entrada.

Respuestas de solicitud preservan id,codigo,estado,version,revision,versiones e historial según modelos de [schemas.py](../../../backend/SOL/schemas.py); parámetros opcionales ausentes usan response_model_exclude_unset. CAP personal devuelve sobre data; referencia CR01 lista/objeto crudos. No inferir un wrapper universal. Errores SOL se saneán en [app.py](../../../backend/SOL/app.py); los cuerpos remotos y secretos no se retransmiten al usuario.

Configuración REAL: URL/token completos por proveedor o par Bus legado completo; URLHTTP(S) sin credenciales/query/fragment, tokens≥32 sin espacios y callback distinto de salidas. Timeout configurado≤3s, presupuesto de inicio de llamadas<3s (default2,4), máximo2 reintentos adicionales; HTTPX mide fases, no un deadline absoluto de operación. Worker por defecto5s; reserva persistente30s y backoff. Contrato incompleto falla al construir app; auditoría vacía también impide REAL hasta configurar receptor académico explícito o institucional homologado.
