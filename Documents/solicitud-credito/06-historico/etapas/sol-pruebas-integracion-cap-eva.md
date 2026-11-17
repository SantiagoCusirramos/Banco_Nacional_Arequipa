> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# SOL-LAB-INTEGRATION — pruebas independientes y bloqueo del circuito conjunto

Fecha: 2026-11-16, America/Lima. Rama: `feature/sol-integracion-cap-eva`, HEAD `de4ace61f9fce7befb79828ea56133a6667eb914`, cambios locales anteriores conservados.

## Conclusión

**No está demostrado CAP → SOL → EVA → SOL de extremo a extremo.** No existe receptor CR-INT-10 homologado confirmado ni autorización explícita del simulador en esta tarea. Se solicitó esa decisión, sin inferirla del prompt. SOL REAL, sol-bootstrap, sol-init y audit-lab no se arrancaron; tampoco se habilitaron callbacks EVA.

Se aprovechó la excepción expresa del usuario para ejecutar comprobaciones independientes: construcción y arranque aislado de MySQL/COREDB/CAP/EVA, captura sintética completa por HTTP, persistencia MySQL, errores de autenticación/autorización/contrato, revocación, indisponibilidad controlada y reinicio de APIs. Ningún resultado de este informe convierte simulación de identidad/riesgo en validación institucional.

Evidencia estructurada local: `laboratorio/evidencias-http-independientes.json`, salida generada excluida del commit de cierre. Los resultados saneados versionables constan en este informe. Runner añadido: [independent_http.py](../../laboratorio/independent_http.py). Contexto: [BUILD](../planes/sol-laboratorio-build.md), [plan](../planes/sol-plan-laboratorio-cap-eva.md), [adaptadores](sol-adaptadores-cap-eva.md), [auditoría](../auditorias/sol-auditoria-pr-cap-eva.md), [changelog](../../change-log.md).

## Precondiciones y aislamiento efectivo

La captura BUILD `/tmp/bna-sol-lab-lab20261116d-rd3tyyye` ya no existía. Se regeneró una captura externa privada: `/tmp/bna-sol-lab-int20261116a-gk7hulyy`, con secretos nuevos e independientes, sin imprimirlos. No se sobrescribió el manifiesto histórico BUILD; el manifiesto de este ensayo se incorpora en la evidencia nueva.

| Comprobación | Resultado |
|---|---|
| Fuentes | COREDB/SQL HEAD de4ace6; SOL workspace; CAP `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; EVA `57b0e2a34fd55fb96fd6245acc06a86536d220f8`; referencias coincidentes |
| Validación de captura | 97 archivos por hash, diez herramientas originales, AST/permisos/tokens/destinos y Compose base/overlay correctos, salida0 |
| Negativos estáticos | Nueve aprobados, 0,686s, salida0; no equivalen a pruebas backend SOL |
| Colisiones | Inventario previo sin recursos del nuevo proyecto; E06 y cinco volúmenes ajenos identificados y preservados |
| Proyecto exclusivo | `bna-sol-cap-eva-lab-int20261116a`, imágenes propias con ese namespace; bases oficiales fijadas por digest se consumen sin retag de imágenes ajenas |
| Redes efectivas | core-data, module-data e integration del proyecto, verificadas `internal=true`; sin conexión a redes E06/otros equipos |
| MySQL | Dos contenedores nuevos, tmpfs propios, `PortBindings={}`; sin datos/credenciales institucionales ni volúmenes de bases compartidos |
| Volumen CAP | cap-secrets exclusivo del proyecto, nuevo; init produjo secreto de servicio y runtime lo consumió correctamente con montaje de solo lectura |
| Destinos | Solo DNS coredb/captacion/evaluacion/mysql-core/mysql-modulos del laboratorio; SOL/Auditoría sin arranque. Ningún SQL integrado directo desde SOL |
| Capacidad | RAM disponible inicial3318MiB; tmpfs1536MiB por servidor es límite, no reserva íntegra. Servicios independientes arrancaron sin error observado de memoria |
| CR10 | No homologado ni autorizado; se conservó el bloqueo conjunto y el gate de simulación NO |

Acceso Docker inicial restringido falló con permiso denegado (salida1); las repeticiones autorizadas funcionaron. No se imprimió configuración interpolada ni `.Config.Env`. No se modificó Compose raíz ni se reutilizaron tags de aplicación compartidos. Las redes/volumen CAP se crearon únicamente con el prefijo nuevo.

## Inicializadores y versiones realmente ejecutados

Se inspeccionaron nuevamente las operaciones antes de inicializar: SQL integrado con CREATE/GRANT/rutinas/triggers y owner bloqueado; bootstrap SOL con CREATE/ALTER/GRANT; CAP con ALTER/GRANT y rotación del servicio CLIENTES; EVA con ALTER/REVOKE y DROP/CREATE TRIGGER. Las fixtures destructivas EVA no se ejecutaron ni se importaron como tests.

La excepción de pruebas independientes se limitó a:

1. Construir `mysql-core`, `coredb` y `captacion` (esta última genera la imagen providers usada también por EVA): salida0.
2. Arrancar mysql-core/mysql-modulos nuevos con `LAB_ALLOW_DDL=YES_ISOLATED_LAB`: salida0, ambos saludables. `DATOS_DEV=0`; no se cargó bna_datos_dev.sql ni se inventaron catálogos sustitutos.
3. Inicializar administrador COREDB y bases/usuarios CAP/EVA, y arrancar sus APIs: salida0. Los tres contenedores init terminaron0. SOL no se inicializó.
4. Usar el administrador sintético admin-lab para login y crear un AUDITOR ficticio por API, sin ampliar permisos existentes. No se creó analista ni se registró situación financiera EVA porque no existe expediente legítimo de SOL en este ensayo.

Versiones observadas en runtime: **MySQL8.4.11, Python3.11.18, FastAPI0.115.0, PyJWT2.15.1** (estas tres últimas consultadas en la imagen COREDB). Las versiones de dependencias no consultadas no se infieren del tag. Recetas base y hashes de requirements constan en el manifiesto; este no es un lock transitivo completo.

| Imagen exclusiva | ID obtenido de Docker |
|---|---|
| mysql-core:lab | `sha256:6a141e52c5919f29d528859427761b803911113f433953ec03b3bc5ec0712149` |
| coredb:lab | `sha256:38609841f4f4b6dd4ee95cbd2e97494570bfe0d026de1a21cfa32cf1c1bf7555` |
| providers:lab | `sha256:3d1c7fa8107af52ffc4fc42adf8c4edf3c2f98b125167815e2ecb9344366672d` |

Las tres etiquetas completas usan el prefijo `bna-sol-cap-eva-lab-int20261116a/`. MySQL módulos consume el digest oficial de BUILD. Las descargas de build usan red de construcción, separada del aislamiento interno de runtime; no hubo llamadas a servicios bancarios externos.

## HTTP independiente ejecutado

Runner final: **24 comprobaciones HTTP aprobadas y una validación local de contrato SOL aprobada**, salida0. Las comprobaciones adicionales de permisos, EVA, fallos y reinicios se muestran separadamente, sin sumarlas como suite backend SOL.

| Operación real | HTTP observado | Resultado |
|---|---|---|
| GET COREDB `/coredb/salud`, CAP `/ready`, EVA `/salud` | 200 cada uno | Salud de los tres componentes |
| POST `/coredb/auth/login`, GET `/coredb/auth/me` | 200 | Administrador sintético autenticado; token no almacenado en informe |
| GET `/coredb/auth/me` sin token | 401 | Rechazo real |
| POST `/api/v1/captacion/solicitantes` sin apellido materno | 201 | Prospecto guardado, materno null; documento/contactos omitidos en evidencia |
| POST `/api/v1/captacion/casos`, canal WEB | 201 | Caso nuevo sin agencia inventada; funciona con DATOS_DEV=0 para este recorrido |
| POST caso `/consentimientos` | 201 | Tratamiento de datos, consulta de burós y términos sintéticos |
| POST caso `/otp`, `/otp/verificar` | 201 / 200 | OTP de laboratorio, no impreso ni conservado en evidencia |
| POST caso `/validaciones` | 201 | RENIEC/listas/PEP del proveedor SIMULADO existente |
| POST caso `/consultas-riesgo`, `/perfil` | 201 / 201 | Central y perfil del simulador CAP; no se introdujo reporte manual ni ingresos/deudas verificados |
| POST caso `/habilitar` | 200 | CAP registró cliente vía HTTP COREDB con su servicio CLIENTES |
| GET `/cap/references` y `/cap/references/{id_cliente}` | 200 / 200 | Identificadores comunes, ACTIVO/HABILITADO y materno vacío |
| GET referencias con token incorrecto | 401 | Sin aceptación de credenciales inválidas |
| GET EVA operación con token CAP | 401 | Credenciales cruzadas rechazadas |
| GET CAP referencia inexistente | 404 | No se inventó identidad |
| POST CAP solicitante con JSON incompatible | 400 | Contrato real CAP, no422 supuesto |
| POST caso `/estado` REVOCAR | 200 | Revocación persistida por API |
| GET detalle/búsqueda después de revocar | 200 | Devuelven explícitamente estado REVOCADO; **no404 ni exclusión de lista** |
| Función `SOL.integrations.validate_reference` sobre ese JSON revocado | 422 local | Rechaza referencia; **no es HTTP422 de SOL ni prueba del adaptador HTTP activo** |

Comprobaciones adicionales reales:

| Caso | HTTP/resultado |
|---|---|
| Token EVA correcto + GET `/eva/operations/unknown-lab-operation` | 404 |
| Token EVA correcto + POST `/eva/applications` con `{}` | 422; no creó expediente |
| POST COREDB `/coredb/usuarios`, rol AUDITOR ficticio | 201 |
| AUDITOR intenta POST CAP `/solicitantes` | 403 |
| Repetir REVOCAR sobre caso ya revocado | 409 |
| API COREDB propia detenida brevemente: CAP `/ready` | 503 |
| Misma caída: GET CAP referencia existente | 503; dependencia caída, sin referencia simulada sustituta |

La API COREDB fue restaurada en `finally`; no se paró MySQL. No se inventó una respuesta 500: el 5xx reproducido fue503. Timeout, respuesta perdida tras persistencia e idempotencia de entregas EVA siguen pendientes, no se sustituyen por estos fallos de conectividad.

## Ejemplo saneado y persistencia MySQL

IDs generados realmente en el recorrido final, todos sintéticos:

- Solicitante: `1f56071c-973b-4fbf-b0be-0d20d193f179`.
- Caso: `79d564de-dd9d-49de-afb7-091f902acb46`.
- Cliente COREDB/CAP: `CLI000000003`.
- Verificación: `6b394b85-f999-45dd-a414-a9497ea2f71b`.

Solicitud de captura saneada (los marcadores reemplazan valores enviados; **no es un body literal para reenviar**):

```json
{"tipo_documento":"DNI","numero_documento":"[sintético omitido]","nombres":"Persona Sintetica","apellido_paterno":"Laboratorio","celular":"[sintético omitido]","correo":"[sintético omitido]"}
```

Proyección de la respuesta real GET `/cap/references/CLI000000003` antes de revocar, omitiendo identidad innecesaria:

```json
{"id_cliente":"CLI000000003","id_caso":"79d564de-dd9d-49de-afb7-091f902acb46","id_verificacion":"6b394b85-f999-45dd-a414-a9497ea2f71b","apellido_materno":"","estado_cliente":"ACTIVO","estado_habilitante":"HABILITADO","fecha_verificacion":"2026-11-16","vigente_hasta":"2026-12-16","simulado":true}
```

Fechas e identificadores proceden de CAP/COREDB; no fueron fabricados por SOL. Tras REVOCAR, la referencia conserva cliente y devuelve estado habilitante REVOCADO. El maestro COREDB permanece independiente del estado del caso CAP.

SELECT de evidencia con el usuario propio de CAP, **fuera de SOL**, devolvió:

```text
SELECT VERSION()                    → 8.4.11
SELECT DATABASE()                   → bna_captacion_int20261116a
SELECT id_caso,cod_cliente,estado
  FROM cap_caso WHERE id_caso=:id    → 79d564de-… | CLI000000003 | REVOCADO
```

EVA con su propio usuario confirmó base `bna_evaluacion_int20261116a`, versión8.4.11 y `SELECT COUNT(*) FROM eva_expediente` =0. No se afirma persistencia de expedientes SOL/EVA, ni existe un `idOperacion`/`idEvaluacion` de ese flujo para mostrar. COREDB verificó su MySQL con usuario de aplicación y la captura se registró mediante su API, sin escritura directa en sus tablas por SOL.

## Reinicio, privacidad y estado final

Se reiniciaron **solo APIs COREDB/CAP/EVA**, salida0. IDs y StartedAt de ambos MySQL permanecieron iguales. Después: tres sondas HTTP200, referencia CAP HTTP200 con REVOCADO y mismo caso persistido en MySQL. No se volvieron a ejecutar inicializadores, no se rotó el secreto CAP por reiniciar runtime y no se perdieron bases tmpfs. Esto demuestra recuperación de esos componentes, no durabilidad tras reinicio de MySQL ni recuperación de reservas SOL.

Inspección de logs COREDB/CAP/EVA en memoria: cero coincidencias con secretos sintéticos generados y cero coincidencias con documentos/celulares/correos completos de los prospectos del ensayo. Se imprimieron solo contadores; no se guardó el log bruto. Alcance temporal de esa inspección: después del primer reinicio; no es una auditoría exhaustiva de todos los futuros eventos.

Estado al cierre: dos MySQL y tres APIs independientes siguen ejecutándose para conservar los datos tmpfs; tres inicializadores terminaron0. SOL y Auditoría no existen como contenedores de este proyecto. E06 continúa detenido con sus cuatro contenedores originales. No se eliminaron contenedores, imágenes, redes o volúmenes compartidos; no `down -v`, reset, commit, push, merge ni cambio de rama.

## Fallos encontrados y correcciones realizadas

1. Runner inicial esperaba404 tras revocar: 22 checks HTTP correctos y una expectativa fallida. Código CAP confirma200 con REVOCADO. Se corrigió solo el runner, conservando historia; no se pide a CAP cambiar un contrato válido. El gate puro SOL rechazó luego correctamente422.
2. Segunda captura del runner reutilizaba contactos entre prospectos; habilitar devolvió409 tras14 checks correctos. No se obtuvo prueba suficiente para atribuir un defecto CAP/COREDB. Se separaron contactos sintéticos por ejecución y la tercera pasó. Los casos anteriores se preservaron, sin borrar registros ni modificar proveedores.
3. Snapshot BUILD temporal ausente: regeneración externa nueva y registro de fuentes, sin sobrescribir el manifiesto histórico ni cambios locales.

Archivos funcionales SOL/CAP/EVA/COREDB no cambiaron. Únicos cambios de código: runner de laboratorio. La corrección se verificó repitiendo el recorrido HTTP completo independiente, no declarando las 219 pruebas anteriores como regresión de hoy.

## Matriz CR-INT y pruebas pendientes

| Conexión | Clasificación actual | Evidencia y falta |
|---|---|---|
| COREDB ↔ CAP | COMPATIBLE en recorrido independiente ejecutado | Login/servicio CLIENTES/captura/referencia y persistencia; verificaciones de identidad CAP siguen simuladas |
| CR-INT-01 CAP → SOL | COMPATIBLE por contrato; integración HTTP con SOL NO VERIFICADA | CAP HTTP real y validador puro SOL probados; falta SOL REAL autorizado y adapter/lista/creación por HTTP, vencimiento y errores de transporte hacia SOL |
| CR-INT-02 SOL → EVA | NO VERIFICADA de extremo a extremo | EVA real arranca y rechaza401/404/422 correctamente; faltan expediente congelado, acuse, correlación, idempotencia y conciliación MySQL |
| CR-INT-03 EVA → SOL | BLOQUEADA para este ensayo conjunto | Callback intacto por evidencia anterior, pero SOL no arrancó; faltan APROBADO/OBSERVADO/RECHAZADO, IDs/rondas/versiones, duplicados y resultados antiguos |
| CR-INT-10 Auditoría | BLOQUEADA por decisión | Sin receptor institucional homologado ni autorización de simulador. No acuses obtenidos ni falseados |

Pendientes explícitos: solicitud/calendario preliminar real SOL; envío/consulta por operación; persistencia/reservas SOL; pérdida de respuesta tras persistencia; reintentos sin duplicación; timeouts y JSON de proveedor incompatible hacia SOL; referencia vencida sin manipular SQL/fechas; resultados EVA; v1 OBSERVADO → subsanación v2 → nuevo envío/ronda; inmutabilidad y callbacks viejos/duplicados; recuperación de workers con entregas pendientes.

**Riesgo worker EVA (cualquier2xx se considera entrega):** confirmado previamente por inspección de código, no reproducido en esta ejecución porque no se creó expediente ni callback. No se declara defecto demostrado por TCP/MySQL. Propuesta para equipo EVA: reproducir en su ensayo un destino controlado que devuelva2xx con JSON/IDs incompatibles y verificar que no cierre la entrega; evaluar validación del acuse y conciliación, sin modificar unilateralmente su módulo ni presentar el destino de prueba como proveedor institucional.

No hay respuestas saneadas de expediente/acuse/decisión/subsanación para incluir: **no ocurrieron**. Las pruebas SQLite/MockTransport previas siguen siendo evidencia local separada de este ensayo TCP/MySQL parcial.

## Reanudación necesaria

Primero resolver CR10: receptor homologado con contrato/configuración verificables, o autorización explícita del simulador exclusivamente académico. La pregunta de autorización no está respondida al cierre de este informe; el transcurso del tiempo no la concede.

Después revisar salud/recursos/secretos y fuentes del proyecto nuevo; construir imagen SOL exclusiva, inicializar solo su base propia y arrancar REAL con auditoría autorizada. Capturar un caso CAP nuevo habilitado (el de referencia final fue revocado a propósito), crear solicitud por APIs SOL y ejecutar la secuencia pendiente. No reutilizar los casos revocados ni fabricar habilitación, ingresos/deudas, acuses o identificadores por SQL. La situación financiera EVA necesita datos sintéticos explícitamente identificados y verificación de laboratorio mediante sus operaciones existentes, sin convertirlos en política bancaria.

Los comandos exactos de construcción/arranque independientes usados son los de BUILD con el nuevo `control.env`, selección explícita mysql-core/coredb/captacion y, después, mysql-core/mysql-modulos y coredb/captacion/evaluacion, con gate DDL solo en el proceso autorizado. No se utilizó el overlay audit-sim ni se estableció su gate. Las credenciales solo se entregaron por envfiles externos y entorno de los procesos, nunca en argumentos con valores ni en el informe.
