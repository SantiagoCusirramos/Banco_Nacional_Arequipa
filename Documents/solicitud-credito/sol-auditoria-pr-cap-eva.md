# Auditoría de PR #74 CAP y #70 EVA — CAP → SOL → EVA

Fecha: 2026-11-15, America/Lima. Auditoría de código y pruebas acotadas; no merge, checkout, commit, push, migración ni modificación funcional. Este informe y la entrada del changelog son los únicos cambios del repositorio.

## 1. Conclusión y evidencia de origen

**Podemos comenzar pruebas de contrato aisladas; no basta configurar URLs para ejecutar ya el circuito completo en Docker con el SOL actual.** Los PR sí implementan las APIs que antes faltaban. El bloqueo principal en SOL es su cliente único de Bus para tres proveedores separados; además CR-INT-01 necesita homologar apellido materno opcional y la auditoría REAL continúa sin proveedor compatible confirmado.

| Conexión | Clasificación del conjunto | Evidencia / condición para probar el circuito |
| --- | --- | --- |
| CAP → SOL, CR-INT-01 | **COMPATIBLE CON AJUSTES** | Rutas, campos y caso habilitado funcionan con adaptador SOL actual en TestClient. CAP admite apellido materno ausente; SOL rechaza referencia/lista. Separar destino/token CAP y acordar ese campo |
| SOL → EVA, CR-INT-02 | **COMPATIBLE CON AJUSTES** | Sobre, acuse y consulta coinciden por inspección/validación DTO; idempotencia persistente implementada. Separar destino/token EVA; validar recepción/dedupe/locks sobre MySQL aislado después de autorizar preparación |
| EVA → SOL, CR-INT-03 | **COMPATIBLE CON AJUSTES** | JSON, headers, token y decisiones coinciden por inspección y DTO. Activar callback únicamente con SOL REAL correctamente configurado; probar conciliación, reintentos, subsanación y acuse positivo real |
| SOL → Seguridad, CR-INT-10 | **BLOQUEADA** | Ninguno de estos PR incorpora el receptor de auditoría requerido por SOL. Acordar proveedor o un canal explícitamente pendiente, sin acuse institucional simulado |
| Circuito Docker CAP→SOL→EVA→SOL | **NO VERIFICADA** como integración ejecutada | Cada PR contiene servicios, pero no se levantó una composición conjunta ni se ejecutó un callback EVA real contra SOL/MySQL |

Las tres primeras clasificaciones no certifican políticas ni proveedores institucionales. Las verificaciones de CAP, RENIEC/listas/PEP/centrales/OTP siguen simuladas; el motor EVA es provisional. Compatibilidad técnica no significa habilitación crediticia aprobada.

### Referencias exactas utilizadas

| Fuente | Referencia inspeccionada |
| --- | --- |
| SOL actual | HEAD `de4ace61f9fce7befb79828ea56133a6667eb914`, commit de cierre E01–E06; sus 28 hashes de evidencia E06 siguen coincidiendo |
| [PR CAP #74](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/74) | `origin/pr-cap-74` = `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; commit propio sobre `8595f62cf4ff1c083bc85b1dc1f38245df76d64d` |
| [PR EVA #70](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/70) | `origin/pr-eva-70` = `57b0e2a34fd55fb96fd6245acc06a86536d220f8`; tres commits desde `86904edd8dc866c1d4260a996748a1cda3770007` |

Las referencias existían: se usaron sin fetch ni acceso de escritura a GitHub. Las páginas públicas fueron accesibles y mostraron esos commits cortos. Los checks y el enlace de Actions citado en #70 no se pudieron recuperar (Cache miss); no se afirma CI verificada ni ejecución propia de sus 65 pruebas MySQL. El contenido auditado queda fijado por SHA, no por una promesa de actualización futura del PR.

**Rama encontrada y conservada:** `feature/sol-integracion-cap-eva`, diferente de `feature/integracion-sol` citada históricamente en AGENTS/entrega. Estado inicial: solo `AGENTS.md` y `README-INICIO.md` sin seguimiento; índice vacío. Se respetó la orden más reciente de no cambiar de rama. No se reescriben documentos E01–E06; sus conclusiones de ausencia de CAP/EVA eran correctas para su base, pero estos PR las actualizan.

Leídos AGENTS, plan, changelog, contratos de finalización, CAP/COREDB, contrato EVA, entrega y matriz RF. Fuentes de detalle: árboles Git de ambos SHA, routers/DTO/servicios/modelos/auth/config/tests/frontend/Compose/scripts/Kubernetes; copias de lectura en `/tmp/bna-auditoria-pr/`. Para contrastar tests se colocó SOL del HEAD actual en esas copias temporales, sin mezclar ramas del workspace.

## 2. Resumen y alcance completo de los PR

**CAP:** solicitante → caso → consentimientos → OTP → verificaciones → centrales → perfil → habilitación; registra/reutiliza cliente en COREDB y publica referencias CR-INT-01. Persistencia `cap_*` propia, frontend `/captacion`, proxy `/api/captacion`, Compose y Kubernetes. Su commit propio cambia **46 archivos** (3946 inserciones/17 eliminaciones): 27 bajo `backend/CAPTACION/`, UI/cliente/tests CAP, `.env.example`, README, `bna`, Compose, scripts de pruebas/smoke/Kubernetes y manifiestos/config de k8s. Incluye inicializadores, archivos vacíos de paquete y dobles de prueba en la revisión.

La comparación de su punta contra la base antigua de SOL arroja **59 archivos**: los trece adicionales provienen de ancestros de Cuentas/Tarjetas (#73/#67), no del commit CAP. Se inspeccionaron también: Swagger/auth Cuentas, cuenta vinculada en respuesta Tarjetas, sus tests/UI/CSS/login/layouts y `frontend/lib/tarjetas.ts`. No atribuir esos cambios a CR-INT-01 ni eliminarlos al integrar. `origin/main` local sigue en 86904ed y no sirve para inferir el estado remoto actual de main. `git diff --check 86904ed...origin/pr-cap-74` detecta un espacio final heredado en CUENTAS; no es defecto del nuevo contrato CAP.

**EVA:** recepción versionada CR-INT-02, evaluación por analista/motor provisional, aprobación con calendario SOL conservado, cola CR-INT-03, consultas/marca de desembolso CR-INT-04. **39 archivos** (5484 inserciones/2 eliminaciones): 26 bajo `backend/EVALUACION/`, OpenAPI/scripts/tests, pantalla `/evaluacion`, proxy/cliente/test frontend, README, `.env.example`, `bna`, Compose, pruebas globales y `tzdata` añadido a requirements compartido. No añade despliegue EVA a Kubernetes. Diff check de ese rango sin errores.

Archivos compartidos a reconciliar por el equipo, sin hacerlo aquí: `.env.example`, README, `bna`, `compose.yaml`, `scripts/pruebas.sh` y `frontend/lib/api.ts`; CAP además scripts/k8s y smoke, EVA requirements. Ambos reutilizan backend Python y frontend Next existentes; no agregan Dockerfile propio. En ninguno se cambia el código SOL. Se analizaron por AST 32 Python del delta ampliado CAP y 23 de EVA, sin errores de sintaxis; esto no acredita su ejecución ni compilación frontend.

## 3. Inventario completo de endpoints CAP

Fuentes: `CAP:backend/CAPTACION/routers/captacion.py:42–157`, `routers/referencias.py:23–39`, `main.py:31–52`, `schemas.py`, `api.py`, `dependencies.py`, `services/captacion.py`. Prefijos montados realmente por `api.montar_en`, sin duplicarlos. **20 operaciones HTTP de negocio/salud, solo GET/POST.** Además FastAPI publica documentación automática `/docs`, `/redoc`, `/openapi.json` y redirect Swagger; no son contratos interbancarios.

Convenciones: **L** = JWT COREDB validado por GET `/coredb/auth/me`, acción `VER_CLIENTE`; **A** = JWT con `CREAR_CLIENTE`; perfiles cacheados 30 s. **S** = Bearer fijo `CAP_SOL_TOKEN` (≥32), no JWT de persona. Las rutas de personal usan `W(data)={success,status_code,message,data,metadata}`; metadata incluye correlación, timestamp y módulo. CR-INT-01 entrega objeto/lista **sin W** al acertar. Todos los errores, incluso los de CR-INT-01, pasan por el sobre `{success:false,status_code,error_code,message,details,metadata}`.

En todas las rutas autenticadas: 401 credencial, 403 permiso donde corresponda; esquema inválido se convierte en **400**, no 422, por handler global. 404 entidad, 409 estado/duplicidad, 502 rechazo no previsto COREDB, 503 dependencia/configuración según operación. Excepción no controlada/BD local puede terminar en 500 por middleware. El OpenAPI implícito de FastAPI puede anunciar 422 aunque el handler responda 400; prevalece el comportamiento observado.

| Método y ruta completa | Entrada | Respuesta de éxito / errores particulares | Auth |
| --- | --- | --- | --- |
| POST `/api/v1/captacion/solicitantes` | tipo_documento DNI/CE/PTP/PASAPORTE, numero_documento 6–12 (regla específica en servicio), nombres, apellido_paterno, apellido_materno opcional/null, celular `9`+8 dígitos, correo | 201 W({solicitante,duplicado:false}); documento existente 200 y duplicado:true; 400 documento inválido | A |
| GET `/api/v1/captacion/solicitantes` | documento opcional ≤12, limite 1–200/default50 | 200 W(lista SolicitanteVista) | L |
| GET `/api/v1/captacion/solicitantes/{id_solicitante}` | ID path | 200 W(SolicitanteVista), 404 | L |
| POST `/api/v1/captacion/casos` | id_solicitante string36, canal AGENCIA/WEB/MOVIL/AGENTE/CAMPANA; id_agencia≤10 y producto_interes≤60 opcionales | 201 W(CasoVista); 404 solicitante, 409 caso abierto | A |
| GET `/api/v1/captacion/casos` | estado opcional≤15, limite 1–200/default50, offset≥0 | 200 W(lista CasoVista+solicitante) | L |
| GET `/api/v1/captacion/casos/{id_caso}` | ID | 200 W(caso+solicitante+consentimientos+validaciones+consultas+perfil+faltantes+listo_para_habilitar), 404 | L |
| POST `/api/v1/captacion/casos/{id_caso}/consentimientos` | consentimientos 1–4: tipo TRATAMIENTO_DATOS/CONSULTA_BUROS/TERMINOS/BIOMETRIA, aceptado bool, medio DIGITAL/FISICO/BIOMETRICO | 201 W(lista tipo/aceptado/medio/version/registrado_por/fecha), 404/409/400 | A |
| POST `/api/v1/captacion/casos/{id_caso}/otp` | canal SMS/EMAIL, defaultSMS | 201 W({canal,destino_enmascarado,expira_en,codigo_simulado}); código solo laboratorio; 503 falta HMAC | A |
| POST `/api/v1/captacion/casos/{id_caso}/otp/verificar` | canal, codigo seis dígitos | 200 W({verificado,estado_codigo,intentos_restantes}); incorrecto/expirado puede ser 200 con false, no acuse de identidad; 404 sin código | A |
| POST `/api/v1/captacion/casos/{id_caso}/validaciones` | tipos lista RENIEC/LISTAS_NEGRAS/PEP/BIOMETRIA; default primeras tres | 201 W(lista tipo/resultado/proveedor/detalle/registrado_por/fecha); 400 sin consentimiento, 409 cerrado | A |
| POST `/api/v1/captacion/casos/{id_caso}/validaciones/manual` | tipo anterior, resultado APROBADO/OBSERVADO/RECHAZADO, detalle3–200 | 201 W(ValidacionVista), 400/404/409 | A |
| POST `/api/v1/captacion/casos/{id_caso}/consultas-riesgo` | central SBS/INFOCORP/SENTINEL/EQUIFAX defaultSBS; reporte opcional con calificacion NORMAL/CPP/DEFICIENTE/DUDOSO/PERDIDA, deuda_total Decimal≥0, entidades0–99, dias_mora0–9999 | 201 W(central/calificacion/deuda_total/entidades/dias_mora/fuente/fecha); fuente SIMULADO o MANUAL | A |
| POST `/api/v1/captacion/casos/{id_caso}/perfil` | Sin body | 201 W(puntaje/calificacion/observacion/fecha), 400 sin consulta, 404/409 | A |
| POST `/api/v1/captacion/casos/{id_caso}/estado` | accion OBSERVAR/LEVANTAR_OBSERVACION/RECHAZAR/REVOCAR; motivo3–255 | 200 W(CasoVista), 409 transición inválida | A |
| POST `/api/v1/captacion/casos/{id_caso}/habilitar` | Sin body | 200 W(CasoVista con cod_cliente/caso/verificación/fechas); repetible sin duplicar en caso habilitado; 400 requisitos/cliente no activo, 409/502/503 COREDB | A |
| GET `/api/v1/captacion/casos/{id_caso}/referencia` | ID | 200 W(Referencia CR01); 409 aún sin referencia, 404/502/503 | L |
| GET `/cap/references` | search≤100/defaultvacío, limit1–50/default50 | 200 lista Referencia; consulta snapshot CAP, no COREDB por fila; incluye revocadas/vencidas para que SOL aplique gate; 400 query inválida, 503 token no configurado | S |
| GET `/cap/references/{id_cliente}` | string path≤36; acepta cod_cliente, no id_solicitante | 200 Referencia, 404 ausente, 503 fallo COREDB/config; relee identidad/estado en COREDB | S |
| GET `/health` | Sin body | 200 `{status:healthy,modulo:captacion}` | Pública |
| GET `/ready` | Sin body | 200 `{status:ready,modulo:captacion}` o 503 `{status:not_ready,faltan:[base/coredb/credencial_coredb]}` | Pública |

Vistas de personal contienen PII necesaria para CAP (documento/contactos); no usarlas como referencia SOL. SolicitanteVista incluye id_solicitante,tipo_documento,numero_documento,nombres,apellidos,celular,correo,cod_cliente,creado_en. CasoVista contiene IDs, canal/agencia/producto, estado/observación/cierre, cod_cliente/cliente_nuevo/id_verificacion_captacion/fechas/actor. La referencia mínima no transmite contactos, nacimiento, informes de centrales ni OTP.

### CR-INT-01: coincidencias y diferencias concretas

`CAP:services/captacion.py:453–589` arma la forma requerida por `SOL:integrations.py:156–207`:

```json
{"id_cliente":"<cod_cliente COREDB>","cod_tipo_documento":"DNI","numero_documento":"<documento>","nombres":"<nombre>","apellido_paterno":"<apellido>","apellido_materno":"<apellido o vacío>","estado_cliente":"ACTIVO","id_caso":"<caso CAP>","id_verificacion":"<verificación COREDB>","fecha_verificacion":"YYYY-MM-DD","vigente_hasta":"YYYY-MM-DD","estado_habilitante":"HABILITADO","version_contrato":"CR-INT-01-PROPUESTA-v2","simulado":true}
```

Ejemplo simbólico, no dato real ni respuesta obtenida de un despliegue. CAP toma cod_cliente/id_verificacion_captacion del COREDB; genera caso propio y fecha de habilitación Lima con vigencia `CAP_VIGENCIA_DIAS` (30 por defecto). SOL admite identificadores no UUID hasta36: **CLI... cabe sin traducción ni inventar IDs**. Individual usa estado/identidad vigentes COREDB; búsqueda usa snapshot guardado y recorre como máximo200 solicitantes para devolver≤50. No garantiza búsqueda exhaustiva en un maestro grande. La habilitación puede revocarse; SOL exige ACTIVO+HABILITADO y fecha vigente, vuelve a consultar al guardar/enviar. El proveedor devuelve referencia vencida/revocada con 200; es correcto que SOL la rechace funcionalmente, no confundir con 404.

**Brecha reproducida:** apellido_materno es opcional/null en CAP y COREDB; `_referencia` lo convierte en `""`. SOL exige string no blanco para todos los campos obligatorios, incluido este apellido. Resultado: GET CAP200 → `Integrations.reference` SOL503; una lista con ese registro provoca `clients`503 completo. No rellenar con un apellido ficticio. Homologar representación legítima (vacío/null) y adaptar normalización/DTO de salida/snapshots/UI de SOL de manera compatible, manteniendo los demás campos y gates. Existe también declaración del pendiente en README CAP; la reproducción de esta auditoría lo confirma con SOL actual.

`simulado:true` es honesto: este PR tiene una API HTTP real, persistencia y llamada COREDB, pero RENIEC/listas/PEP/biometría/centrales/contacto son fakes o revisión manual. No eliminar el marcador al activar transporte REAL. Vigencia, autorización R-01 y calidad institucional de las verificaciones requieren acuerdos.

## 4. Inventario completo de endpoints EVA

Fuentes: `EVA:backend/EVALUACION/main.py:172–267`, `contratos.py`, `servicio.py`, `auth.py`. **14 operaciones/rutas de negocio/salud, solo GET/POST**, más documentación automática FastAPI. La ficha anterior `/api/evaluaciones` **no coincide con este código**: no hay tal ruta ni alias; el analista usa `/eva/v1/evaluaciones`, SOL usa `/eva/applications` y `/eva/operations/...`. No cambiar el adaptador para enviar a la ficha vieja.

Auth: **ES** = Bearer fijo `EVALUACION_TOKEN_SOL`, solo CR02; **EL** = persona COREDB con alguna acción EVALUAR_CREDITO/APROBAR_CREDITO/VER_AUDITORIA; **EE** = persona EVALUAR_CREDITO; **ED** = persona APROBAR_CREDITO; **EA** = persona VER_AUDITORIA o APROBAR_CREDITO; **DS** = usuario COREDB rol SERVICIO/módulo DESEMBOLSO; **AL** = DS o EL. JWT se comprueba por GET COREDB `/coredb/auth/me`, caché configurable/default30s; no comparte sesión SOL ni clave de firma. Servicio no accede a rutas de persona.

Errores comunes: 401 token/sesión, 403 permiso, 404 entidad, 409 versión/estado/idempotencia, 422 DTO/negocio y 503 BD/COREDB. Negocio `{error:{code,message,details?}}`; validación `{detail:[{loc,type,msg}]}` sin input. DBAPI con SIGNAL1644 se homologa a409. Middleware conserva/genera correlación y responde header `X-Correlation-ID`.

| Método/ruta | Entrada | Salida efectiva / códigos particulares | Auth |
| --- | --- | --- | --- |
| GET `/salud` | Ninguna | 200 `{estado:ok,modulo:EVALUACION,version:0.5.0,resultadosASol:configurado o pendiente...}`; consulta BD, 503 si falla; no exige COREDB/callback disponible | Pública |
| POST `/eva/applications` | SobreExpediente CR02 detallado abajo; X-Idempotency-Key opcional, si existe debe igualar body | 201 acuse nuevo/200 mismo acuse repetido; 409 OPERACION_REUTILIZADA/VERSION_YA_RECIBIDA/EVALUACION_EN_CURSO/SOLICITUD_CON_RESULTADO/VERSION_ANTERIOR; 422 CLAVE_DISTINTA/EXPEDIENTE_INCONSISTENTE | ES |
| GET `/eva/operations/{id_operacion}` | Operación de envío, no ID de evaluación | 200 `{idSolicitud,versionSolicitud,idOperacion,idEvaluacion,ronda,acuse}`; 404 OPERACION_NO_RECIBIDA | ES |
| GET `/eva/v1/aprobaciones` | numeroDocumento≤20 o codCredito≤20; estado opcional VIGENTE/VENCIDA/DESEMBOLSADA/REVOCADA | 200 `{items:[Aprobacion sin cuotas detalladas]}` máx20; 422 FILTRO_REQUERIDO sin filtro identificador | AL |
| GET `/eva/v1/aprobaciones/{id_aprobacion}` | ID | 200 Aprobacion+calendario/cuotas/desembolso/revocacion; 404 | AL |
| POST `/eva/v1/aprobaciones/{id_aprobacion}/desembolso` | version≥1, codigoOrden1–30 patrón seguro, fechaDesembolso con zona | 200 Aprobacion; misma orden repetida idempotente; 409 versión/vencida/revocada/otra orden, 422 fecha futura | DS |
| GET `/eva/v1/evaluaciones` | estado PENDIENTE/EN_REVISION/APROBADO/OBSERVADO/RECHAZADO; buscar≤80; limite1–200/default50 | 200 `{items:[Evaluacion],conteos:{estado:cantidad}}`; documento enmascarado en bandeja | EL |
| GET `/eva/v1/evaluaciones/{id_evaluacion}` | ID | 200 DetalleEvaluacion con expediente/calendario/garantías/conteo fiadores, situación, aprobación/envío/historial; 404 | EL |
| POST `/eva/v1/evaluaciones/{id_evaluacion}/situacion-financiera` | ingresoMensual Decimal>0, deudaMensual Decimal≥0 (15/2), riesgo BUENO/REGULAR/ALTO, verificada bool, version≥1 | 200 DetalleEvaluacion; 409 ya no PENDIENTE/revisión, 422 SITUACION_NO_VERIFICADA | EE |
| POST `/eva/v1/evaluaciones/{id_evaluacion}/decision` | decision APROBADO/OBSERVADO/RECHAZADO, observaciones10–1000, version≥1 | 200 DetalleEvaluacion; solo EN_REVISION; 409 otro estado/versión | ED |
| POST `/eva/v1/aprobaciones/{id_aprobacion}/revocacion` | motivo10–500, version≥1 | 200 Aprobacion; 409 no vigente/vencida/versión | ED |
| GET `/eva/v1/envios` | estado PENDIENTE/ENTREGADO/ERROR; limite1–200/default50 | 200 `{items:[Envio],configurado:bool}` | EL |
| POST `/eva/v1/envios/{id_operacion}/reintento` | ID de operación de resultado, sin body | 200 Envio PENDIENTE conservando operación/contenido; 404/409 ENVIO_NO_EN_ERROR; no resetea intentos | ED |
| GET `/eva/v1/historial` | limite1–500/default100 | 200 `{items:[Evento]}` | EA |

Evaluacion contiene idEvaluacion/idSolicitud/versionSolicitud/ronda/estado/version, cliente, producto/destino/montoSolicitado/moneda/plazoMeses/tasaTea, motor/motivo/decisión/fechas. **version del registro EVA no es versionSolicitud ni ronda**. Aprobacion agrega idAprobacion/codCredito/condiciones aprobadas/vigencia/calendario/desembolso/revocación; no es el payload CR03. Envio expone idOperacion/idEvaluacion/interfaz/decision/estado/intentos/siguienteIntento/ultimoError/creadoEn/entregadoEn, sin token. En lectura de detalle, analista/decisor puede ver documento completo; auditor lo recibe enmascarado. El calendario se copia desde SOL, no se recalcula en EVA.

## 5. Comparación CR-INT-02/03 e identificadores

### Recepción CR-INT-02

`SOL:integrations.py:241` genera `{versionContrato,idSolicitud,versionSolicitud,idOperacion,idCorrelacion,expediente,simulado}`, y send añade actorEnvio desde sesión. `EVA:contratos.py:17–93` recibe esa forma. Expediente contiene cliente, condiciones, politica, calendario; fiadores y campos adicionales se conservan en JSON crudo aunque sus DTO usan extra=ignore. No envolverlo en `data` ni convertirlo al camelCase de la pantalla EVA.

Condiciones: cliente≤36, monto Decimal15/2, PEN/USD, plazo1–600, fecha_base; política versión/producto/tea; cuotas con número/fecha/saldos/amortización/interés/total Decimal. EVA valida coincidencia cliente-condiciones, numeración, cantidad de cuotas/plazo, suma capital, suma total y fechas crecientes. SOL actual PEN/6–60 y su calendario satisfacen ese subconjunto; que EVA admita USD/otro plazo no amplía política SOL. Se validó en memoria un sobre construido con la función demo EVA y el calendario/política del SOL actual; no se creó una evaluación persistida en esta auditoría.

Acuse EVA coincide con `validate_receipt`: `{idSolicitud,versionSolicitud,idOperacion,idEvaluacion,ronda,acuse}`; genera `EVA-AAAA-NNNNNN`, ronda positiva propia y `ACK-EVA-...`. No necesita UUID de evaluación; SOL acepta hasta80 y acuse hasta60. **EVA asigna evaluación/ronda; SOL no debe inventarlas ni igualar ronda a versión por conveniencia.** Se guardan sobre+huella SHA256 y evaluación en una transacción MySQL; PK operación, unique solicitud/versión, operación y solicitud/ronda, y triggers protegen datos inmutables. Mismo sobre/operación → mismo acuse; otra huella o distinta operación para la misma versión →409. GET404 significa no recibido. Encaja con GET-antes-de-POST de SOL, incluido timeout tras aceptación.

Diferencias a homologar, sin alterar SOL ahora: EVA no exige presencia del header de idempotencia (sí lo compara si llega); versionContrato es string acotado, no enum de v2; la correlación de middleware/header no se coteja con el body recibido, aunque guarda la del body para callback. SOL ya manda ambas cabeceras coherentes; no bloquea el camino correcto, pero faltan negativos para asegurar el borde del receptor. El documento crudo deduplica por representación JSON, no por equivalencia de números/strings: reintentos deben conservar exactamente el sobre congelado.

### Resultado CR-INT-03

`EVA:servicio.py:258–279` crea transaccionalmente un mensaje final con **nuevo** UUID idOperacion para el resultado, solicitud/versión/evaluación/ronda persistidas, correlación original y decisión/observaciones. No reutiliza la operación de recepción: es correcto que envío y resultado tengan operaciones distintas. Debe coincidir la operación del resultado entre su body/header/reintentos.

`EVA:envios.py:29–110` publica exactamente a `POST /sol/integrations/evaluation-results`, con Bearer `EVALUACION_SOL_TOKEN_RESULTADOS`, `X-Idempotency-Key=body.idOperacion`, `X-Correlation-ID=body.idCorrelacion`. Compatibilidad con DTO `SOL:schemas.py:54` y receptor `app.py:531–569`: ambas versiones/ronda enteras positivas, operación8–80/correlación1–100, decisión APROBADO/OBSERVADO/RECHAZADO y observaciones. SOL admite5–1000; decisión manual EVA10–1000 cumple. Callback responde200 `{recibido:true,idOperacion,estado?}` o repetición reconocida; sesión de usuario no sustituye credencial de servicio. En SIMULADO el handler rechaza401: no enviar resultados reales a `/demo-result` ni habilitar EVALUADOR en REAL para sortearlo.

Outbox `eva_envio`: sin URL/token, PENDIENTE sin HTTP; reserva60s con FOR UPDATE SKIP LOCKED, backoff10/20/.../300s; timeout/408/429/5xx reprograman, 409 reintenta mientras intentos<20; 401/403/404/422 y resto no exitoso van a ERROR; ruta manual permite reintentar ERROR con mismo mensaje. El contador compara intentos totales, no exclusivamente cantidad de409. Un callback antes del acuse local de SOL409 es compatible con reintento. Un409 por versión vieja/conflicto real no se debe explicar operativamente siempre como «aún no concilia».

**Riesgos EVA a corregir/confirmar:** considera cualquier 2xx ENTREGADO sin validar JSON/recibido/idOperacion; una página o202 ajena podría producir confirmación falsa. Validar el acuse que SOL ya emite, sin inventar otro contrato. Su reserva no tiene generación/token de intento al aplicar respuesta tardía (solo `estado=PENDIENTE`); no extender a despliegue multiworker hasta probar expiración de lease/reintento/respuesta vieja. SOL ya protege sus propias reservas, pero no puede proteger la base del worker EVA. Son hallazgos de inspección, no carreras reproducidas en MySQL aquí.

### Estados y subsanación

| EVA | Intercambio con SOL / regla efectiva |
| --- | --- |
| PENDIENTE / EN_REVISION | Estados internos de trabajo, no decisiones de callback. SOL permanece EN_EVALUACION una vez conciliado el acuse |
| Resultado del motor OBSERVADO | EVA lo convierte en **EN_REVISION**, no llama todavía a SOL para subsanar; un analista debe resolver |
| Decisión final OBSERVADO | Callback → SOL OBSERVADA; asesor crea versión siguiente BORRADOR, preserva v1 y reenvía con operación nueva |
| Nueva versión después de observar | EVA permite versión mayor solo si evaluación anterior OBSERVADO; nueva ronda incrementada; solicitud en curso o ya APROBADO/RECHAZADO devuelve409 |
| APROBADO / RECHAZADO | Callback → SOL APROBADA/RECHAZADA. No confundir sufijos de estado interno con valores de decision externos |
| REVOCADA/VENCIDA/DESEMBOLSADA | Estados de aprobación CR04, no decisiones CR03; SOL no los acepta como nuevos resultados. `revocar` no emite callback de revocación; definir con negocio si se necesita otro contrato, sin mapear a RECHAZADO automáticamente |

RN-EVA-002-P (35% ingreso, factor/umbrales de demo) está fuera de SOL; no se alteró ni se adopta como política institucional. Aprobación de motor conserva calendario SOL y permite consumo Desembolso aunque éste no forma parte de esta auditoría de integración.

## 6. Docker, configuración y arquitectura

| Componente | Lo implementado en los PR | Condición/pendiente |
| --- | --- | --- |
| CAP | `captacion:8014`, `captacion-init`; imagen bna/backend:local construida con requirements.txt, base bna_captacion/cap_user en db-aux | Inicializador crea BD/tablas y usuario, autentica admin COREDB y crea/rota svc-captacion con módulo CLIENTES; secreto en volumen captacion-datos, montado ro por API. Depende de db-aux, coredb/coredb-init |
| EVA | `evaluacion:8015`, `evaluacion-init`; misma familia de imagen backend; bna_evaluacion/evaluacion_user en db-aux | Inicializador instala tablas/triggers/permisos; depende db-aux y coredb. MySQL8.4/InnoDB/JSON/SKIP LOCKED, no SQLite para persistencia EVA |
| SOL | `sol:8011`, base propia; ambos PR mantienen SIMULADO | No se configura conexión CAP/EVA ni Bus real por añadir esos servicios |
| Frontend | CAPTACION_GATEWAY_URL=`http://captacion:8014/api/v1/captacion`; EVALUACION_GATEWAY_URL=`http://evaluacion:8015/eva/v1`; GET/POST de proxys Next | No transportan CR01/CR02 de servicio; pantallas usan JWT COREDB. SOL conserva su sesión opaca propia. No hay SSO entre las tres pantallas |
| Callback | EVA base `EVALUACION_SOL_URL` vacía por defecto | Configurar **base** `http://sol:8011`, sin `/sol` ni path final: el despachador añade `/sol/integrations/evaluation-results` |
| Red Compose | Cada servicio en red por defecto del proyecto, puertos host loopback8014/8015 | DNS captacion/evaluacion/sol funciona si se despliegan en el mismo proyecto/red. Ejecutar Compose de cada rama por separado no prueba comunicación conjunta; localhost dentro de contenedor es el propio contenedor |
| Kubernetes | CAP añade deployment/service/ConfigMap/NodePort30014 y scripts; EVA no añade manifiesto | No declarar circuito desplegable en k8s con ambos PR sin trabajo adicional |

**Variables CAP efectivas:** CORE_BASE_URL(defaultlocalhost8012), CORE_TIMEOUT_SECONDS(default5); CAP_DB_URL override o CAP_DB_HOST/PORT/USER/PASSWORD/NAME; CAP_CORE_USUARIO, CAP_CORE_SECRETO o CAP_CORE_SECRETO_ARCHIVO; CAP_SOL_TOKEN, CAP_OTP_CLAVE, CAP_OTP_SIMULADO, CAP_VIGENCIA_DIAS(default30), CAP_VERSION_TERMINOS(defaultv1). Inicializador: AUX_DB_ROOT_PASSWORD, BNA_ADMIN_USUARIO/PASSWORD, CAP_ESPERA_SEGUNDOS(default300). Compose: BNA_PUERTO_CAPTACION(default8014), CAPTACION_GATEWAY_URL frontend. No valores de secretos en este informe.

**Variables EVA efectivas:** EVALUACION_DATABASE_URL obligatoria, COREDB_URL; EVALUACION_TOKEN_SOL; EVALUACION_SOL_URL y EVALUACION_SOL_TOKEN_RESULTADOS; EVALUACION_VIGENCIA_DIAS(default30), EVALUACION_ENVIO_INTERVALO_SEG(default5), EVALUACION_TIMEOUT_SEG(default3), EVALUACION_SESION_CACHE_SEG(default30). Inicializador: EVALUACION_DB_HOST/PORT/NAME/USER/PASSWORD y AUX_DB_ROOT_PASSWORD. Demo: EVALUACION_URL; tests: EVALUACION_TEST_MYSQL. Compose: BNA_PUERTO_EVALUACION(default8015), EVALUACION_GATEWAY_URL frontend. Tokens no vacíos deben tener≥32 y ser distintos entre recepción y callback; Config permite token_sol vacío si no se configura recepción (responderá401), y exige token de resultados si se configura sol_url.

**SOL actual:** `Settings` solo tiene SOL_BUS_BASE_URL/SOL_BUS_TOKEN, cinco paths relativos CAP/EVA/Auditoría y SOL_EVA_CALLBACK_TOKEN. `Integrations.__init__` crea **un solo** httpx.Client con esa base/token. No admite URL absoluta por path (`Settings.validate` la rechaza). Poner base CAP deja EVA sin destino; poner EVA deja CAP sin destino; tokens CAP_SOL_TOKEN y EVALUACION_TOKEN_SOL no se enrutan por proveedor. Igualar todos los secretos no resuelve que hay hosts distintos y aumenta exposición.

RELACIONES DE CREDENCIALES A HOMOLOGAR: token del cliente CAP en SOL ↔ CAP_SOL_TOKEN; token del cliente EVA en SOL ↔ EVALUACION_TOKEN_SOL; SOL_EVA_CALLBACK_TOKEN ↔ EVALUACION_SOL_TOKEN_RESULTADOS, distinto de ambos de salida. Los nombres de clientes CAP/EVA en SOL son **propuesta**, no variables ya implementadas. Tokens JWT COREDB de analistas/asesores y credencial de servicio CAP→COREDB son otros canales. Un Bus único permitiría mantener SOL, pero estos PR **no implementan ese gateway**; no se presume existente.

Modo REAL de SOL exige configurar también auditoría. No inventar `/security/events` institucional ni devolver un acuse local para desbloquearlo. Antes de ejecución de los tres módulos, acordar receptor o una política explícita de auditoría pendiente/no configurada, separada del modo de CAP/EVA, durable y visible. Si se adopta esa segunda opción implica cambio de configuración/validación/operación/pruebas SOL y aprobación de Seguridad; no está implementada por esta auditoría.

## 7. Pruebas incluidas, ejecutadas y no verificadas

Entorno nuevo temporal Python3.13.5 con requirements-sol.txt, fuera del repo, sin `.env` institucional. El entorno `/tmp/bna-sol-p01-venv` de E06 ya no existía: los dos intentos iniciales de pytest salieron127 sin ejecutar tests. Creación de venv nueva correcta; instalación inicial salió2 por DNS de sandbox, repetición autorizada de dependencias salió0. No se cambiaron requirements/lockfiles. Copias de PR más SOL actual, sin merge; COREDB se sustituye por MockTransport en CAP.

| Prueba / origen | Resultado real de esta auditoría | Alcance |
| --- | --- | --- |
| CAP `CAPTACION/tests`, CAP_TEST_DB_URL=`sqlite://` | **35 passed, 1 skipped, 1 warning, 1,37s**, salida0 | 21 flujo, diez lógica parametrizada y cuatro contratos con adaptador SOL actual; SQLite en memoria, no COREDB real ni TCP |
| CAP contrato COREDB omitido | Collect-only confirmó skip por falta de `jwt`; salida5 sin casos recogidos | No declarar esas dos pruebas de esquema aprobadas; no se instaló todo COREDB para ejecutarlas |
| Reproducción adicional CAP/SOL | Cinco comprobaciones aprobadas, salida0 | Habilitar sin materno, HTTP200 con vacío, referencia SOL503, búsqueda SOL503 y query limit51→400; fixture en memoria/COREDB falso |
| EVA `EVALUACION/tests`, sin EVALUACION_TEST_MYSQL | **12 passed, 53 skipped, 1 warning, 0,37s**, salida0 | Lógica pura del motor; recepción, outbox, permisos con API, triggers, locks y TCP/MySQL quedaron omitidos por fixture, no pasaron |
| DTO/sobre/calendario SOL→EVA y decisiones→DTO SOL | Salida0 tras corregir una aserción del comprobador que contaba13 rutas en vez de14 | DTO SobreExpediente y validador de calendario compatibles con generación demo basada en SOL; tres decisiones aceptadas por EvaluationResult. Sin lifespan/BD/recepción/callback |
| AST de fuentes/JSON y diff estático | Correctos; se extrajeron20 operaciones CAP y14 EVA | Sintaxis/inventario, no ejecución completa |
| SOL E06 | Hashes28 vigentes; evidencia histórica169 SQLite/169 fixturesMySQL y114 frontend/2 fallos esperados | No se volvió a correr SOL ni se atribuyen estos resultados a CAP/EVA |

Comandos de suite efectivamente usados, con entorno temporal y autorizaciones por limitación TestClient:

```bash
# En /tmp/bna-auditoria-pr/cap/backend (fuentes PR + SOL de4ace6)
env -u SOL_TEST_DATABASE_URL -u EVALUACION_TEST_MYSQL PYTHONDONTWRITEBYTECODE=1 CAP_TEST_DB_URL=sqlite:// SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-pr-auditoria-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts= CAPTACION/tests
# En /tmp/bna-auditoria-pr/eva/backend
env -u EVALUACION_TEST_MYSQL -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 PYTHONPATH=/tmp/bna-auditoria-pr/eva/backend timeout 60s /tmp/bna-pr-auditoria-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts= EVALUACION/tests
```

Advertencia: alias AnyIO/Starlette obsoleto, no fallo. CAP trae cuatro archivos de tests (flujo, lógica, contrato COREDB, contrato SOL) y frontend cinco casos CAP-01..05; EVA seis archivos (base, CR02, envíos, flujo, motor, permisos),65 casos recogidos y frontend cinco EV-01..05. Los tests EVA incluyen idempotencia/acuse validado por SOL, un servidor Uvicorn real para `Integrations.deliver`, resultados validados con DTO SOL, timeout/503/409/401, espera sin URL, permisos y triggers; **que existan no implica que se ejecutaran aquí**. Sus resultados de callback son recibidos por `SolFalso`, no necesariamente por el handler/persistencia real de SOL.

El autor de [EVA #70](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/70) declara65 pruebas MySQL y cinco frontend/lint/build y enlaza [Actions del fork](https://github.com/Rodrigoss06/Banco_Nacional_Arequipa/actions/runs/43763406068). Esa ejecución/checks no fue accesible al navegador de esta auditoría; se registra como **declarada, no verificada**. CAP incorpora smoke que habilita cliente COREDB/referencia/proxy, pero no ejecuta por sí mismo el ciclo de expediente SOL→EVA→SOL; no se encontró salida CI accesible para certificarlo. No se ejecutaron suites frontend, build/lint nuevos, Docker, inicializadores, smoke/test global, migraciones ni BD MySQL en esta auditoría.

Razón de no ejecutar las suites de BD/globales: EVA fixture hace DROP DATABASE/TRUNCATE y prepara esquema/usuarios; scripts de prueba globales tienen limpieza de recursos/volúmenes. CAP permite CAP_TEST_DB_URL arbitrario y su fixture hace drop_all: aquí se fijó explícitamente SQLite en memoria recién creada, sin datos previos ni destino MySQL. No sugerir el ejemplo MySQL CAP sobre una BD compartida para probar. El dato histórico SOL/MySQL no verifica estos nuevos esquemas.

## 8. Cambios concretos necesarios y prioridades

### En SOL — propuesta, sin implementarla

1. **Primero desacoplar transporte por proveedor** en settings/integrations: clientes/base URL/token independientes CAP, EVA y auditoría, validación fail-closed y pruebas de que cada llamada usa solo su host/secreto. Conservar API interna `reference/clients/deliver/audit`, sobre congelado, idempotencia, consulta previa, timeout/presupuesto y SIMULADO. Posibles nombres nuevos SOL_CAP_BASE_URL/TOKEN, SOL_EVA_BASE_URL/TOKEN y SOL_AUDIT_BASE_URL/TOKEN deben acordarse; hoy no existen. Compatibilidad Bus legado puede mantenerse solo con reglas explícitas, no fallback de REAL a simulación. La auditoría ausente necesita decisión explícita antes de habilitar el circuito global.
2. Homologar apellido materno opcional con CAP/COREDB; cambiar mínimo normalización/DTO/proyección/UI y agregar casos ausente/null/vacío/lista mixta y no mutación de historia. No relajar identidad, caso, verificación, estado ni vigencia ni completar PII ficticia.
3. Definir configuración de ensayo local por canal: destinos `http://captacion:8014` y `http://evaluacion:8015`, paths existentes `/cap/references`, `/cap/references/{idCliente}`, `/eva/applications`, `/eva/operations/{idOperacion}`. Timeout CAP actual SOL0,6s puede ser menor que CORE_TIMEOUT_SECONDS5 y primer login COREDB; medir y ajustar dentro del presupuesto sin reintentos descontrolados.
4. Configurar callback explícito REAL y credencial exclusiva; conservar rechazado en SIMULADO y validar conciliación antes de aplicar resultados. Frontend debe llamar `/sol` si el alias gateway SIMULADO desaparece: ajustar SOL_GATEWAY_URL y SOL_PUBLIC_ORIGIN de despliegue. No añadir callbacks a su proxy web.
5. Mantener pago doble/fiadores reales y reglas financieras pendientes; no tocar finance.py para adaptar las decisiones EVA. Configurar fiadores vacíos en primer recorrido REAL hasta tener identidad homologada.

### En CAP / confirmaciones del equipo

- Aprobar CR01 y semántica de apellido opcional, vigencia/caso/verificación y marcador simulado; confirmar adopción cod_cliente como ID común. Datos de identidad no se transforman para fingir compatibilidad.
- R-01 de servicio CLIENTES requiere aceptación por Clientes/CORE; init crea o rota su secreto y escribe en COREDB, no es una sonda de solo lectura. Probar registro/reutilización, revocación/vencimiento y caída COREDB en entorno autorizado.
- Diferenciar búsqueda cacheada de consulta autoritativa; revisar límite interno200/no paginación completa y caso de identidad modificada en COREDB. Endurecer observabilidad/correlación: middleware CAP acepta header arbitrario y Uvicorn por defecto puede registrar query pese a log propio mínimo; verificar con canarios sintéticos antes de usar PII real.
- Resolver proveedores institucionales/OTP; mantener `simulado:true` mientras sigan ausentes, no presentar esta API como identidad institucional certificada.

### En EVA / confirmaciones del equipo

- Aceptar contractVersion/idempotency/correlación obligatorios o documentar tolerancia actual; agregar negativos de cabeceras/tipos/crudo y ensayo real con **SOL actual**, no solo modelo/demo/fake.
- Validar acuse200 JSON de callback (`recibido:true` e idOperacion coincidente); probar respuesta perdida, duplicado, conflicto por versión anterior, maxintentos y recuperación manual sin nueva operación. Añadir generación de lease o equivalente antes de multiworker.
- Homologar OBSERVADO final frente a EN_REVISION interno, rondas, resultados terminales, subsanación y revocación fuera CR03. Confirmar que el calendario de SOL se copia y no sustituirlo por una ficha anterior.
- Verificar MySQL/triggers/permisos e init en instancia efímera autorizada, y política de riesgo/vigencia de aprobación con negocio. Kubernetes EVA sigue pendiente.

## 9. Riesgos, dependencias y plan para integrar

Dependencias reales: contratos/actas de políticas, servicio de identidad/COREDB, credenciales por canal seguro, auditoría CR10, red/DNS/TLS, preparación de bases aisladas y reconciliación de archivos compartidos. No hay mecanismo automático de sesión única CAP/EVA/SOL. Revocación de perfiles COREDB tiene ventana de caché30s; no prometer revocación instantánea entre módulos. DB de CAP/SQLAlchemy no equivale a transacción distribuida COREDB; los reintentos de habilitar ayudan, pero deben probarse caídas a mitad de alta/validaciones.

Secuencia propuesta para el siguiente trabajo **cuando se autorice implementar**, sin ejecutarla ahora:

1. Equipos confirman estos SHA, esquema mínimo CR01/02/03, cod_cliente común, apellido opcional y canal de auditoría pendiente/real. Acordar responsable, credenciales y estados; resolver cualquier diferencia contractual antes de alterar negocio.
2. Implementar en SOL separación de transportes/proveedores con pruebas de enrutamiento, secretos, fail-closed y SIMULADO; incorporar la representación acordada de apellido. No cambiar fórmulas ni estados financieros.
3. Revisar conjuntamente diff de infra de ambos PR y dependencias previas de CAP, sin escoger automáticamente «nuestra» versión de Compose/lib/api. En una tarea autorizada preparar composición de prueba separada con COREDB, CAP, SOL, EVA y MySQL desechable, datos sintéticos, sin volúmenes institucionales. Aquí no se hizo merge ni se generó ese Compose.
4. Con autorización específica, instalar bases/roles de prueba; comprobar health/readiness y DNS. Sembrar solo perfiles sintéticos; probar token correcto/incorrecto y evitar imprimirlos en logs/config. No activar REAL si depende de un receptor inexistente.
5. Probar CAP→SOL: captar/habilitar, buscar, consultar, crear/editar preview/calendario; negativos sin materno, bloqueado, revocado, vencido y COREDB caído. Confirmar caso/verificación/fechas de origen y minimización.
6. Probar CR02: reservar/congelar,202 local, GET404/POST201/GET200, repetir misma operación, conflicto otra huella/versión, corte tras aceptar y conciliación GET tras reinicio, locks MySQL y un único expediente persistido.
7. Probar CR03 real: caso EN_REVISION sin callback prematuro, OBSERVADO→SOL OBSERVADA→subsanar v2→reenvío/ronda nueva; APROBADO y RECHAZADO por separado. Callback adelantado409→reintento, token/correlación/ronda incorrectos, pérdida de respuesta, duplicado idéntico y resultado viejo. Comprobar v1 inmutable y outbox tanto EVA como SOL sin falso acuse.
8. Verificar frontend sobre sesión/permisos/origen correctos, E2E navegador, auditoría/logs saneados, reinicios y métricas. Ejecutar regresiones de los tres módulos en entorno aislado, guardar evidencia separada de fakes y proveedor real. Solo entonces declarar integrado_real en el alcance realmente ejecutado y autorizado.

## 10. Respuesta final

**Sí a comenzar ya pruebas de contrato aisladas**: varias se ejecutaron aquí, y ambos PR aportan implementaciones utilizables. **Todavía no al circuito conjunto sin cambios**: necesitamos primero separación de URLs/tokens por proveedor en SOL y decisión explícita de auditoría, más homologar apellido materno opcional. Después, preparar un despliegue de pruebas autorizado y validar MySQL/HTTP/callback/subsanación de extremo a extremo. Esta auditoría no demuestra integración institucional ni autoriza producción.

No se cambiaron ni reiniciaron módulos, bases, Docker ni infraestructura; no fetch necesario, no switch/merge/staging/commit/push. Se conservaron las fuentes/pruebas SOL (hashes E06 vigentes) y aportes locales sin seguimiento. Validación documental y `git diff --check` al cierre se registran en [change-log](change-log.md).

### Fuentes de código inmutables para el equipo

- CAP: [routers del personal](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/4ea5014bddb1a69289402f03b3fbc47c28cc9413/backend/CAPTACION/routers/captacion.py), [CR-INT-01](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/4ea5014bddb1a69289402f03b3fbc47c28cc9413/backend/CAPTACION/routers/referencias.py), [habilitación/referencias](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/4ea5014bddb1a69289402f03b3fbc47c28cc9413/backend/CAPTACION/services/captacion.py#L453), [autenticación](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/4ea5014bddb1a69289402f03b3fbc47c28cc9413/backend/CAPTACION/dependencies.py).
- EVA: [API montada](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/57b0e2a34fd55fb96fd6245acc06a86536d220f8/backend/EVALUACION/main.py#L189), [DTOs](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/57b0e2a34fd55fb96fd6245acc06a86536d220f8/backend/EVALUACION/contratos.py), [recepción/estados](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/57b0e2a34fd55fb96fd6245acc06a86536d220f8/backend/EVALUACION/servicio.py#L117), [callback/outbox](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/blob/57b0e2a34fd55fb96fd6245acc06a86536d220f8/backend/EVALUACION/envios.py#L29).
- SOL del HEAD auditado: [settings](../../backend/SOL/settings.py), [adaptadores](../../backend/SOL/integrations.py), [receptor](../../backend/SOL/app.py), [contrato EVA](sol-contrato-evaluacion.md), [CAP/COREDB histórico](sol-captacion-coredb.md), [matriz histórica](sol-matriz-rf.md).
