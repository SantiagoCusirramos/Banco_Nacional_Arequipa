> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# 02 — APIs COREDB y límites de persistencia

Fecha: 2026-11-16 (America/Lima). Rama analizada: `feature/sol-integracion-cap-eva`. HEAD: `988dc0776da282fbef306632fc86426b6e372376`. Auditoría estática, sin arranque, SQL, migraciones, cambios de rama ni consultas remotas. Las referencias `origin/*` son copias locales; su nombre no acredita el estado actual de un PR.

## Veredicto

COREDB sí implementa registro/consulta de clientes y registro de verificaciones. No implementa API HTTP de expedientes, evaluación, decisiones ni callbacks SOL. Las tablas creditos.* no equivalen a un servicio EVA. El permiso EVALUAR_CREDITO en RBAC tampoco implica un endpoint que lo ejecute.

`backend/COREDB/main.py:15–43` registra salud, auth, usuarios, clientes, movimientos, cuentas, tarjetas, catálogos y auditoría. No registra creditos ni evaluacion. Se inventariaron todos sus routers ejecutables; OpenAPI estático existe en backend/COREDB/openapi.json y hay exportador, pero no se verificó sincronía ejecutándolo. FastAPI proporciona /docs y /openapi.json al arrancar, no se consultaron en vivo.

## Matriz funcional obligatoria

IMPLEMENTADO SIN PRUEBA significa código inspeccionado sin ejecución nueva de esa operación. Las pruebas históricas no se reclasifican como ejecutadas hoy. NO EXISTE se refiere al servicio/refs auditados, no a sistemas externos.

| Funcionalidad | Servicio propietario | Método HTTP | Endpoint exacto | Autenticación | Request | Response | Persistencia | Estado | Evidencia |
|---|---|---|---|---|---|---|---|---|---|
| Registrar cliente | COREDB | POST | /coredb/clientes | JWT; CREAR_CLIENTE, HABILITADO solo SERVICIO:CLIENTES | ClienteRegistrar | 201 ClienteRegistrado | SP clientes.registrar_cliente | IMPLEMENTADO SIN PRUEBA | routers/clientes.py:117 registrar; services/clientes.py:66 |
| Consultar cliente por código | COREDB | GET | /coredb/clientes/{cod_cliente} | JWT VER_CLIENTE | código alfanumérico 1–12 | 200 ClienteRespuesta; 404 | SP clientes.consultar_cliente | IMPLEMENTADO SIN PRUEBA | routers/clientes.py:178 ver; services/clientes.py:59 |
| Buscar DNI con identidad verificada | COREDB | POST | /coredb/clientes/validaciones/documento | JWT VALIDAR_IDENTIDAD | tipo_documento, numero_documento, identidad_verificada, motivo opcional | 201 id_validacion, APROBADO/RECHAZADO, motivo, cliente nullable; nunca 404 | SP clientes.verificar_documento, registro de validación | IMPLEMENTADO SIN PRUEBA | routers/clientes.py:143 verificar_documento; services/clientes.py:83 |
| Búsqueda libre/listado clientes | COREDB | — | No existe | — | — | — | no API de búsqueda abierta | NO EXISTE | inventario completo inferior |
| Registrar verificación de captación | COREDB | POST | /coredb/clientes/{cod_cliente}/validaciones | JWT VALIDAR_IDENTIDAD | HUELLA/FACIAL/CELULAR/CORREO, APROBADO/RECHAZADO, motivo nullable | 201 id_validacion | SP clientes.registrar_validacion | IMPLEMENTADO SIN PRUEBA | routers/clientes.py:160 registrar_validacion; services/clientes.py:100 |
| Cambiar estado cliente | COREDB | POST | /coredb/clientes/{cod_cliente}/estado | JWT MODIFICAR_CLIENTE; BAJA solo persona | estado y motivo obligatorio | 200 ClienteConEstadoAnterior | SP clientes.cambiar_estado_cliente y bitácora | IMPLEMENTADO SIN PRUEBA | routers/clientes.py:185 cambiar_estado |
| Habilitación para SOL | CAP; COREDB aporta estado | GET | /cap/references/{id_cliente} (ref CAP) | CAP_SOL_TOKEN | código compartido | referencia con vigencia y caso | CAP caso propio + lectura COREDB | PARCIAL | CAP services/captacion.py:516–568; COREDB no aporta caso/vigente_hasta |
| Recuperar datos mínimos para SOL directamente | COREDB | GET | /coredb/clientes/{cod_cliente} | JWT VER_CLIENTE | código | incluye contacto y estado, falta contrato CR01 completo | lectura clientes | PARCIAL | ClienteRespuesta:63; no usar como CR01 sin CAP |
| Historial/listado verificaciones | COREDB | — | No existe ruta especializada | — | — | consulta de bitácora no equivale al historial íntegro de verificaciones | tablas clientes.validacion_identidad/verificacion_captacion | PARCIAL | bna_core.sql:209,222; router auditoria |
| Catálogos clientes | COREDB | GET | /coredb/catalogos/clientes | JWT | — | tipos_documento, estados_cliente | SP clientes.catalogos_cliente | IMPLEMENTADO SIN PRUEBA | routers/catalogos.py:102 |
| Catálogo productos crédito | COREDB | GET | /coredb/catalogos/productos-credito | JWT | — | lista ProductoCreditoRespuesta | core.producto_credito | IMPLEMENTADO SIN PRUEBA | routers/catalogos.py:73 |
| Registrar expediente SOL | COREDB | — | No existe | — | — | — | creditos.solicitud_credito es tabla, no API | NO EXISTE | main.py; bna_core.sql:589 |
| Bandeja pendientes EVA | COREDB | — | No existe | — | — | — | sin repositorio EVA en COREDB | NO EXISTE | inventario de routers |
| Registrar evaluación/decisión | COREDB | — | No existe | — | — | — | creditos.evaluacion/decision_analista solo esquema | NO EXISTE | bna_core.sql:739,790 |
| Consultar por operación/versionar/reintentar EVA | COREDB | — | No existe | — | — | — | sin contrato CR02 | NO EXISTE | main.py y routers |
| Historial evaluación/vinculación con SOL | COREDB | — | No existe API | — | — | — | FK id_solicitud y UNIQUE(id_solicitud,ronda) en SQL | PARCIAL | bna_core.sql:747,752; no confundir FK con operación HTTP |
| Callback EVA→SOL | SOL | POST | /sol/integrations/evaluation-results | SOL_EVA_CALLBACK_TOKEN | EvaluationResult | 200 recibido; 401/404/409/422 | Outcome, Application, Event, outbox | IMPLEMENTADO SIN PRUEBA | SOL/app.py:531–570; no pertenece a COREDB |
| Recibir expediente / consultar acuse | EVA ref | POST / GET | /eva/applications ; /eva/operations/{id_operacion} | EVALUACION_TOKEN_SOL | SobreExpediente / operación | 201 nuevo, 200 repetido; GET 200/404 | eva_expediente y eva_evaluacion | IMPLEMENTADO SIN PRUEBA | EVA/main.py:185–202; servicio.py:107–189 |
| Bandeja/detalle/historial EVA | EVA ref | GET | /eva/v1/evaluaciones ; /eva/v1/evaluaciones/{id_evaluacion} ; /eva/v1/historial | JWT COREDB y permisos EVA | filtros/ID | listas/detalle con historial | eva_* propias | IMPLEMENTADO SIN PRUEBA | EVA/main.py:227–236,263–266 |
| Registrar situación y decidir | EVA ref | POST | /eva/v1/evaluaciones/{id_evaluacion}/situacion-financiera ; /eva/v1/evaluaciones/{id_evaluacion}/decision | JWT persona EVALUAR_CREDITO / APROBAR_CREDITO | SituacionIn / DecisionIn | detalle; 409 versión/estado,422 esquema | eva_situacion_financiera, eva_evaluacion, eva_envio | IMPLEMENTADO SIN PRUEBA | EVA/main.py:238–247; contratos.py:90–105 |
| Retorno/reintentos EVA | EVA ref | GET / POST | /eva/v1/envios ; /eva/v1/envios/{id_operacion}/reintento | JWT personal con permiso | filtro/ID | items / reintento | eva_envio | PARCIAL | EVA/main.py:253–261; envios.py:78 acepta cualquier 2xx |

## Modelos y reglas concretas

`ClienteRegistrar` (routers/clientes.py:40) hereda tipo y número documento; exige nombres, apellido_paterno, correo, celular, version_contrato y estado_habilitante HABILITADO/OBSERVADO. Materno nullable. Campos extra prohibidos y tipos estrictos; normaliza documento a mayúsculas/correo a minúsculas; celular nueve dígitos que empieza por 9. Los códigos de cliente no son UUID ni DNI.

`ClienteRespuesta` incluye cod_cliente, identidad, correo, celular, estado_cliente, permite_operar, version_contrato, id_verificacion_captacion, estado_habilitante y fecha_verificacion (str). No incluye id_caso ni vigente_hasta. DocumentoVerificado puede devolver cliente=null y motivo; APROBADO exige cliente ACTIVO. No hay GET público por DNI.

Cambio de estado no es una API independiente para editar estado_habilitante: BLOQUEADO/SUSPENDIDO repercuten en tarjetas; BAJA cancela y es final. No usarlo como atajo de laboratorio. Validaciones biométricas/contacto registran resultados declarados por el llamador; COREDB no demuestra RENIEC/SMS reales.

## SQL, servicios, transacciones y seguridad

`services/clientes.py:59–130` llama SP clientes.consultar_cliente, registrar_cliente, verificar_documento, registrar_validacion, cambiar_estado_cliente y catalogos_cliente. `_escribir` y transacciones gestionan commit/rollback y traducción de errores. `database.py` valida nombres de procedimientos y oculta parámetros; modelos SQLAlchemy declaran schemas. No se encontró repositorio de expedientes/evaluaciones en COREDB.

`database/sql/bna_core.sql` contiene solicitud_credito:589, historial_estado_solicitud:607, garantia:628, fiador:651, fiador_solicitud:663, calendario_pago:674, cuota:700, situacion_financiera:727, evaluacion:739, regla_evaluacion:760 y decision_analista:790. SQL expresa estructura y restricciones; los procedimientos creditos.validar_orden, validar_credito y aplicar_pago atienden otros tramos del crédito, no una API CR02/03. No se aplicó ningún SQL.

COREDB JWT propio firmado con CORE_DB_JWT_CLAVE, verificación de emisor/audiencia/expiración (`tokens.py:75`), actor vigente releído en BD (`auth.py`). Roles/acciones son mapa en `permisos.py`. No existe permiso de servicio EVA dedicado en el mapa; EVA autentica personas mediante /coredb/auth/me, no guarda evaluaciones vía COREDB. Su persistencia directa a su propia base bna_evaluacion no equivale a escritura en schemas integrados.

Errores COREDB: 401 token/login,403 permiso,404 cliente,409 documento/correo/celular duplicados y reglas,422 validación Pydantic; detalles saneados por errores.py. Auditoría COREDB GET /coredb/auditoria es solo lectura con VER_AUDITORIA, no receptor CR10 de SOL.

## Inventario completo de rutas COREDB extraído del AST

| Método | Endpoint exacto | Evidencia y función |
|---|---|---|
| GET | `/coredb/auditoria` | `backend/COREDB/routers/auditoria.py:32` — `eventos` |
| POST | `/coredb/auth/login` | `backend/COREDB/routers/auth.py:69` — `login` |
| GET | `/coredb/auth/me` | `backend/COREDB/routers/auth.py:94` — `me` |
| GET | `/coredb/catalogos/monedas` | `backend/COREDB/routers/catalogos.py:58` — `monedas` |
| GET | `/coredb/catalogos/agencias` | `backend/COREDB/routers/catalogos.py:63` — `agencias` |
| GET | `/coredb/catalogos/productos-ahorro` | `backend/COREDB/routers/catalogos.py:68` — `productos_ahorro` |
| GET | `/coredb/catalogos/productos-credito` | `backend/COREDB/routers/catalogos.py:73` — `productos_credito` |
| GET | `/coredb/catalogos/tipos-cambio` | `backend/COREDB/routers/catalogos.py:78` — `tipos_cambio` |
| GET | `/coredb/catalogos/clientes` | `backend/COREDB/routers/catalogos.py:102` — `catalogos_de_clientes` |
| POST | `/coredb/clientes` | `backend/COREDB/routers/clientes.py:117` — `registrar` |
| POST | `/coredb/clientes/validaciones/documento` | `backend/COREDB/routers/clientes.py:143` — `verificar_documento` |
| POST | `/coredb/clientes/{cod_cliente}/validaciones` | `backend/COREDB/routers/clientes.py:160` — `registrar_validacion` |
| GET | `/coredb/clientes/{cod_cliente}` | `backend/COREDB/routers/clientes.py:178` — `ver` |
| POST | `/coredb/clientes/{cod_cliente}/estado` | `backend/COREDB/routers/clientes.py:185` — `cambiar_estado` |
| GET | `/coredb/cuentas` | `backend/COREDB/routers/cuentas.py:69` — `de_un_cliente` |
| GET | `/coredb/cuentas/{num_cuenta}` | `backend/COREDB/routers/cuentas.py:89` — `ver` |
| POST | `/coredb/cuentas` | `backend/COREDB/routers/cuentas.py:95` — `abrir` |
| POST | `/coredb/movimientos` | `backend/COREDB/routers/movimientos.py:51` — `registrar` |
| POST | `/coredb/movimientos/transferencias` | `backend/COREDB/routers/movimientos.py:60` — `transferir` |
| GET | `/coredb/movimientos/cuenta/{num_cuenta}` | `backend/COREDB/routers/movimientos.py:90` — `de_una_cuenta` |
| GET | `/coredb/movimientos/{uuid_transaccion}` | `backend/COREDB/routers/movimientos.py:118` — `ver` |
| GET | `/coredb/salud` | `backend/COREDB/routers/salud.py:10` — `salud` |
| GET | `/coredb/tarjetas` | `backend/COREDB/routers/tarjetas.py:88` — `de_un_cliente` |
| GET | `/coredb/tarjetas/{id_tarjeta}` | `backend/COREDB/routers/tarjetas.py:106` — `ver` |
| POST | `/coredb/tarjetas` | `backend/COREDB/routers/tarjetas.py:112` — `emitir` |
| POST | `/coredb/tarjetas/{id_tarjeta}/estado` | `backend/COREDB/routers/tarjetas.py:131` — `cambiar_estado` |
| GET | `/coredb/usuarios` | `backend/COREDB/routers/usuarios.py:67` — `listar` |
| GET | `/coredb/usuarios/{id_usuario}` | `backend/COREDB/routers/usuarios.py:77` — `ver` |
| POST | `/coredb/usuarios` | `backend/COREDB/routers/usuarios.py:83` — `crear` |
| POST | `/coredb/usuarios/{id_usuario}/rol` | `backend/COREDB/routers/usuarios.py:100` — `asignar_rol` |
| POST | `/coredb/usuarios/{id_usuario}/estado` | `backend/COREDB/routers/usuarios.py:110` — `cambiar_estado` |
| POST | `/coredb/usuarios/servicios` | `backend/COREDB/routers/usuarios.py:121` — `crear_servicio` |
| POST | `/coredb/usuarios/{id_usuario}/credencial` | `backend/COREDB/routers/usuarios.py:137` — `renovar_credencial` |

## Pruebas existentes y límites

COREDB tests/test_unidad.py comprueba tipos UUID, SQL seguro, contratos y OpenAPI; test_autenticacion.py verifica JWT/permisos con sustituciones. tests/integracion/test_clientes.py, test_login_y_servicios.py y test_usuarios.py requieren BD de pruebas; no ejecutados. CAP tiene test_contrato_core.py con COREDB falso y test_contrato_sol.py; EVA tiene test_cr_int_02.py, test_envios.py, test_flujo.py y fixtures MySQL con COREDB/SOL falsos. Existir un test no acredita IMPLEMENTADO Y PROBADO en esta ejecución. Ninguna operación se ha marcado así sin una prueba nueva.
