# Preparación del laboratorio CAP → SOL → EVA

Fecha: 2026-11-16 (America/Lima). Tarea: SOL-LAB-PREP.

## Dictamen y alcance

La preparación documental está completa; **el laboratorio conjunto no se ha construido ni ejecutado y su aislamiento efectivo todavía debe verificarse**. Los clientes HTTP de SOL están preparados, pero activar SOL REAL requiere resolver el receptor de Auditoría CR-INT-10. No basta con configurar CAP y EVA. No se autoriza ni implementa una excepción a ese control.

Esta tarea solo inspeccionó fuentes y recursos Docker. No creó Compose, imágenes, secretos, contenedores, redes o volúmenes; no ejecutó inicializadores, migraciones ni pruebas de integración. Las 219 pruebas SOL aprobadas y dos advertencias corresponden al cierre anterior, SQLite/MockTransport; no se repitieron ni demuestran el circuito TCP conjunto.

Fuentes leídas: AGENTS.md, [plan vigente](plan-integracion-sol.md), [auditoría de PR](sol-auditoria-pr-cap-eva.md), [adaptadores multiproveedor](sol-adaptadores-cap-eva.md) y [registro](change-log.md). Se revisaron Compose, Dockerfiles, configuración, inicializadores, autenticación y workers de las referencias siguientes, sin cambiar de rama ni fusionarlas:

| Fuente | Referencia inspeccionada |
|---|---|
| SOL actual | Rama `feature/sol-integracion-cap-eva`, HEAD `de4ace61f9fce7befb79828ea56133a6667eb914`, más cambios locales multiproveedor pendientes de commit |
| CAP PR #74 | `origin/pr-cap-74`, `4ea5014bddb1a69289402f03b3fbc47c28cc9413` |
| EVA PR #70 | `origin/pr-eva-70`, `57b0e2a34fd55fb96fd6245acc06a86536d220f8` |

Estos SHA son instantáneas, no garantía de futuros cambios en los PR. Preservar los archivos locales de SOL: exportar solo HEAD perdería los adaptadores nuevos. No superponer todo el árbol CAP: su historia también contiene cambios de otros módulos.

## Servicios y dependencias confirmados

| Servicio | Implementación y puerto interno | Dependencias efectivas |
|---|---|---|
| COREDB | `COREDB.main`, 8012 | MySQL integrado inicializado; credencial SQL de aplicación y clave JWT; comprobación `core.verificar_configuracion()` al arrancar |
| CAP | `uvicorn CAPTACION.main:app`, 8014 | Base propia, COREDB HTTP, usuario de servicio y secreto de CLIENTES; token SOL y clave OTP; `captacion-init` previo |
| SOL | Servicio existente, 8011 | Base propia inicializada, política demo existente; en REAL los tres proveedores CAP/EVA/Auditoría configurados y token callback |
| EVA | `uvicorn EVALUACION.main:app`, 8015 | Base propia y permisos específicos; COREDB para sesiones humanas; `evaluacion-init` previo; worker de resultados |
| MySQL integrado | Dockerfile `docker/core-db/Dockerfile`, contexto `database/` | SQL inicial del proyecto, tres contraseñas SQL y root; catálogos sintéticos si `DATOS_DEV=1` |
| MySQL de módulos | Propuesta: MySQL 8.4 fijado por digest | Esquemas independientes CAP/SOL/EVA; bootstrap mínimo de SOL y los inicializadores revisados de CAP/EVA |
| Ejecutor HTTP | Propuesto, no creado | Misma red interna; datos sintéticos, credenciales separadas y evidencias saneadas |

Ambos PR usan Compose con proyecto `bna` e imágenes compartidas como `bna/backend:local`; **no ejecutar sus Compose sin adaptación**. CAP depende de `db-aux` saludable, COREDB saludable e inicialización completada. EVA depende de inicialización y COREDB saludable. No necesitan arrancar CORE legado, Cuentas, Tarjetas, Seguridad local ni frontend para el primer ensayo HTTP.

CAP `/health` y `/ready` y EVA `/salud` sirven como sondas, pero no prueban el circuito completo: `/ready` no certifica autenticación y permisos reales de todas las operaciones; `/salud` no acredita recepción del callback por SOL.

## Diseño aislado propuesto, todavía sin archivo Compose

Usar proyecto único `bna-sol-cap-eva-lab-<runid>`, imágenes con etiqueta exclusiva del ensayo y redes internas propias (`internal: true`). Sin `container_name`, redes/volúmenes `external`, nombres globales `bna`, red host, socket Docker, `host-gateway`, bases remotas ni directorios de datos compartidos. No reutilizar recursos E06 ni volúmenes de compañeros.

Separar dos servidores MySQL:

- `mysql-core`: esquemas fijos `core`, `clientes`, `cuentas`, `tarjetas`, `creditos`; solo COREDB accede por SQL. No se aíslan cambiando un supuesto `CORE_DB_NAME`: los procedimientos y modelos usan esquemas explícitos.
- `mysql-modulos`: `bna_sol_mvp_lab<runid>`, `bna_captacion_lab<runid>` y `bna_evaluacion_lab<runid>`, con usuarios y privilegios propios. CAP/SOL/EVA no reciben credenciales SQL del integrado. SOL conserva acceso a CAP y EVA exclusivamente HTTP.

Proponer una red de datos COREDB, otra de datos de módulos y una red HTTP de integración. Ningún puerto MySQL publicado; inicialmente tampoco APIs publicadas: ejecutar el cliente HTTP dentro de la red. Si después se necesita navegador, publicar solo loopback con puertos libres revisados y configurar el origen público SOL. El frontend queda fuera del primer hito.

Datos MySQL inicialmente en `tmpfs`, con tamaño definido tras revisar recursos. **Reiniciar APIs conserva las bases; reiniciar/recrear MySQL con tmpfs no constituye prueba de durabilidad**. Si se exige supervivencia de MySQL, aprobar y verificar volúmenes nuevos exclusivos del proyecto antes del arranque. El secreto de servicio CAP necesita almacenamiento nuevo del proyecto, escritura del inicializador y lectura solamente del runtime; comprobar propietario UID 10001 y permisos, sin reutilizar `captacion-datos` existente.

Construir en una futura tarea un contexto temporal saneado: backend base actual, SOL del workspace, solo `CAPTACION/` del SHA CAP y solo `EVALUACION/` del SHA EVA. Registrar hashes de las fuentes realmente copiadas. No hacer merge ni checkout. Excluir `.env`, credenciales, caches y dumps. El Dockerfile Python copia backend y hace `chown` de `CORE/data`: no funciona suponiendo un contexto con únicamente el directorio CAP o EVA. COREDB usa `requirements-coredb.txt`, SOL `requirements-sol.txt`; revisar requisitos compartidos del PR EVA, incluido `tzdata`, para la imagen CAP/EVA. No sobrescribir tags compartidos.

No reutilizar sin cambios `docker/db-aux/Dockerfile`: su inicializador exige contraseña del legado y crea usuario/permisos del legado y SOL; el Compose general también monta SQL legado. El laboratorio mínimo necesita bootstrap revisado exclusivamente para el esquema/usuario SOL, sin ese SQL. No se ha escrito ni ejecutado dicho bootstrap.

## Inventario de operaciones que escriben

| Inicializador o arranque | Efectos observados | Condición previa obligatoria |
|---|---|---|
| Primer arranque MySQL integrado | Ejecuta `bna_core.sql`, `bna_extension.sql`, `crear_usuarios.sh` y, por defecto, `bna_datos_dev.sql`; crea esquemas, tablas, rutinas, triggers, roles, usuarios y permisos | Servidor y almacenamiento nuevos; revisar scripts completos de la instantánea final **antes de arrancar MySQL** |
| `DATOS_DEV=1` en construcción integrada | Incluye datos explícitamente de desarrollo, entre ellos agencia AQP01 y cliente DEV001 | Aprobar uso solo sintético; no presentar ese cliente como captado por CAP. Con `DATOS_DEV=0` faltan catálogos que deben resolverse, no asumir funcionalidad completa |
| `COREDB.scripts.crear_administrador --si-falta` | Crea usuario administrador mediante procedimiento; evita recrearlo si ya existe administrador activo | Base integrada aislada e inicializada; contraseña inicial solo de laboratorio |
| `python -m CAPTACION.manage init` | Puede crear base, crear/alterar usuario y conceder ALL en su esquema; crea tablas; autentica administrador COREDB, crea/reactiva usuario de servicio y **rota su credencial**, guardándola en archivo | Ambos servidores aislados; COREDB API operativo y administrador creado. Repetir puede rotar secretos, no es una simple sonda |
| CAP con `CAP_CORE_SECRETO` explícito | Omite creación/rotación automática del servicio y usa el secreto suministrado | Servicio previamente provisionado y permiso CLIENTES verificado; no usar secretos institucionales |
| `python -m EVALUACION.scripts.preparar_base` | Crea base/tablas, elimina/recrea triggers, crea/altera usuario, **REVOKE ALL PRIVILEGES, GRANT OPTION**, luego concede permisos por tabla | Servidor y usuario exclusivos; DDL con commits implícitos. Nunca ejecutarlo sobre un usuario compartido |
| Inicialización SOL existente | Crea estructura propia; requiere esquema/usuario previamente provisionados | Solo su esquema de laboratorio; revisar comando y configuración final antes de autorizarlo |
| Arranque de workers SOL/EVA | Procesa reservas/outbox, reintentos y callbacks pendientes; no es lectura pasiva | Destinos y datos verificados antes de iniciar cada worker |
| Fixtures MySQL de EVA | Crean/eliminan base `bna_evaluacion_pruebas`, usuario y truncan tablas | No ejecutar contra servidor compartido ni contra datos del ensayo persistente; necesitan otro destino desechable |
| Acceso humano y captura | Login escribe sesiones/eventos; CAP escribe casos/verificaciones y registra clientes vía COREDB HTTP | Identidades sintéticas, rol correcto y consentimiento/validaciones de laboratorio |

## Variables y credenciales necesarias

Valores siguientes son nombres y destinos **propuestos dentro del laboratorio**, no servicios levantados. Generar credenciales diferentes por función en una tarea posterior, fuera del repositorio, directorio 0700/archivos 0600. No introducir valores en Compose versionado, terminal, evidencias o comandos con historial. No heredar `.env` de compañeros. Los clientes actuales consumen variables de entorno: no suponer soporte automático de sufijos `_FILE` donde no está implementado.

| Componente | Configuración |
|---|---|
| MySQL integrado | `MYSQL_ROOT_PASSWORD`, `CORE_DB_APP_PASSWORD`, `CORE_DB_ADMIN_PASSWORD`, `CORE_DB_SEGURIDAD_PASSWORD`; las tres últimas son exigidas por el script aunque no se levante Seguridad |
| COREDB | `CORE_DB_HOST=mysql-core`, `CORE_DB_PORT=3306`, `CORE_DB_APP_USER=bna_app_user`, `CORE_DB_APP_PASSWORD`, `CORE_DB_JWT_CLAVE`; no usar defaults localhost/3307. Revisar configuración `.env` propia para impedir herencia |
| Administrador inicial | `CORE_DB_ADMIN_INICIAL_PASSWORD`; usuario/nombre sintéticos del CLI. `BNA_ADMIN_USUARIO`/`BNA_ADMIN_PASSWORD` deben corresponder al administrador que usa CAP init |
| MySQL módulos | `MYSQL_ROOT_PASSWORD` distinto del integrado; `AUX_DB_ROOT_PASSWORD` solo en inicializadores que lo necesitan, nunca en APIs |
| CAP base | `CAP_DB_HOST=mysql-modulos`, `CAP_DB_PORT=3306`, `CAP_DB_NAME`, `CAP_DB_USER`, `CAP_DB_PASSWORD`; dejar `CAP_DB_URL` ausente para evitar que reemplace todo el destino |
| CAP HTTP/servicio | `CORE_BASE_URL=http://coredb:8012`, `CAP_CORE_USUARIO`, `CAP_CORE_SECRETO_ARCHIVO=/datos/coredb_secreto` o secreto provisionado; `CAP_SOL_TOKEN`; `CAP_OTP_CLAVE`; `CAP_OTP_SIMULADO=true` solo laboratorio. Mantener vigencia/términos existentes |
| SOL base | `SOL_DB_HOST=mysql-modulos`, `SOL_DB_PORT=3306`, `SOL_DB_NAME=bna_sol_mvp_lab<runid>`, usuario no root y `SOL_DB_PASSWORD`; conservar política demo vigente |
| SOL → CAP | `SOL_CAP_BASE_URL=http://captacion:8014`, `SOL_CAP_TOKEN=CAP_SOL_TOKEN`; `SOL_CAP_SEARCH_PATH=/cap/references`, `SOL_CAP_REFERENCE_PATH=/cap/references/{idCliente}` |
| SOL → EVA | `SOL_EVA_BASE_URL=http://evaluacion:8015`, `SOL_EVA_TOKEN=EVALUACION_TOKEN_SOL`; `SOL_EVA_SEND_PATH=/eva/applications`, `SOL_EVA_STATUS_PATH=/eva/operations/{idOperacion}` |
| SOL → Auditoría | `SOL_AUDIT_BASE_URL`, `SOL_AUDIT_TOKEN`, `SOL_AUDIT_PATH`: **sin destino homologado, bloqueado** |
| SOL modos y tiempos | `SOL_INTEGRATION_MODE=REAL` solo tras resolver CR10; timeout 0,6 s, presupuesto 2,4 s, máximo dos reintentos, worker 5 s actuales. No desactivar worker como sustituto de auditoría |
| EVA base | `EVALUACION_DATABASE_URL` con esquema/usuario exclusivo y host `mysql-modulos`; construir URL escapando credenciales. Inicializador: `EVALUACION_DB_HOST/PORT/NAME/USER/PASSWORD`, coherentes con esa URL, y `AUX_DB_ROOT_PASSWORD` |
| EVA sesiones | `COREDB_URL=http://coredb:8012`; usuario humano con rol/permisos de evaluación, diferente del servicio CAP |
| EVA → SOL | `EVALUACION_SOL_URL=http://sol:8011` **base sin path**; `EVALUACION_SOL_TOKEN_RESULTADOS=SOL_EVA_CALLBACK_TOKEN`; worker añade `/sol/integrations/evaluation-results` |
| EVA control de envío | `EVALUACION_ENVIO_INTERVALO_SEG` (5), `EVALUACION_TIMEOUT_SEG` (3), `EVALUACION_SESION_CACHE_SEG` (30); vigencia existente `EVALUACION_VIGENCIA_DIAS` (30) sin homologarla como política bancaria |

Tokens de servicio de al menos 32 caracteres. CAP, EVA, callback y Auditoría deben ser diferentes; callback distinto de todas las credenciales de salida. En laboratorio configurar parejas propias completas y no inyectar `SOL_BUS_BASE_URL/TOKEN`: faltar ambos campos de un proveedor selecciona Bus legado, no un proveedor simulado. La compatibilidad Bus permanece; no se utilizará para ocultar un receptor ausente. No existe modo REAL por proveedor: SIMULADO global no prueba estas conexiones HTTP.

Usuarios humanos CAP se validan contra COREDB y permisos VER_CLIENTE/CREAR_CLIENTE; servicio CAP usa CLIENTES. EVA requiere permisos de evaluación. Confirmar con responsables la habilitación y el alcance del rol de servicio, incluida R01, sin ampliar permisos globales para hacer pasar el ensayo.

## Auditoría CR-INT-10: bloqueo real

| Candidato revisado | Evidencia | Conclusión |
|---|---|---|
| `backend/seguridad/api.py` | Consultas `/seguridad/auditoria`, verificación, incidentes y evaluación local de operaciones | No implementa recepción genérica CR10 ni su acuse. No adaptar eventos SOL a incidentes/operaciones sin contrato |
| `backend/COREDB/routers/auditoria.py` | GET `/coredb/auditoria`, consulta de bitácora integrada | No es receptor POST CR10 |
| `backend/SOL/simulator.py` | POST `/security/events`, Bearer `SOL_SIMULATOR_TOKEN`, acuse `idEvento/confirmado/acuse`, prefijo AUD-SIM, deduplicación en memoria | Compatible para simulación de laboratorio, **no institucional ni durable**; no seleccionado ni ejecutado |

SOL REAL exige configuración de Auditoría y confirmación positiva; conserva outbox persistente, reintentos y separación de modos. Una URL inventada con token de relleno no resuelve el bloqueo. Tampoco se debe declarar confirmación institucional porque un simulador devuelve 2xx.

Decisión necesaria: (a) Seguridad entrega receptor y contrato homologados, opción preferida; o (b) el responsable autoriza explícitamente usar el simulador existente **solo para el ensayo sintético**, con limitación de pérdida de deduplicación al reiniciar y evidencia marcada como simulada. Otra estrategia de auditoría en cola sin receptor requeriría acuerdo y desarrollo posterior; no está implementada ni autorizada aquí. Hasta decidir, se pueden planificar pruebas independientes de CAP/COREDB y EVA, pero no declarar habilitado el recorrido conjunto SOL REAL.

## Puertas de control y ejecución progresiva futura

1. **Congelar fuentes y preparar Compose revisable** en una tarea posterior. Guardar documentación/configuración nueva únicamente bajo `Documents/solicitud-credito/`, por ejemplo un subdirectorio `laboratorio/`; secretos/contextos fuera del árbol versionado. No modificar Compose compartido.
2. **Verificar aislamiento antes de cualquier arranque**: revisar configuración renderizada sin mostrar secretos, imágenes/contextos/hashes, `depends_on`, inicializadores y ausencia de montajes externos, puertos públicos, destinos remotos, credenciales heredadas o volúmenes existentes. Comprobar recursos disponibles y colisiones. No basta con el nombre del proyecto. `docker compose config --services` es lectura; la configuración completa interpolada puede revelar secretos y no debe imprimirse ni adjuntarse.
3. **Aprobar catálogos sintéticos, estrategia de almacenamiento y CR10**. Las primeras escrituras incluyen el primer arranque MySQL. No ejecutar esta secuencia como consecuencia automática de aprobar el documento: el alcance actual termina en preparación.
4. Crear únicamente recursos propios; inicializar MySQL integrado; ejecutar administrador inicial; arrancar COREDB y comprobar acceso humano/servicio. Inicializar MySQL de módulos con bootstrap mínimo SOL revisado. Ejecutar CAP init y EVA init una sola vez, explícitamente, verificando efectos y credenciales. Inicializar SOL únicamente en su esquema propio.
5. Arrancar CAP y EVA; mantener `EVALUACION_SOL_URL` vacío durante comprobación independiente de recepción para evitar callbacks prematuros. El control de despacho EVA es por fases, no una excepción de auditoría SOL. Verificar sondas, permisos y ausencia de accesos externos.
6. Solo con CR10 decidido/configurado, arrancar SOL REAL y probar **CAP → SOL**. Crear un cliente sintético mediante CAP, con sus verificaciones de laboratorio; comprobar referencia individual y búsqueda. No fabricar `idCaso`, verificación, habilitación o vigencia en SOL ni copiar registros por SQL.
7. Probar **SOL → EVA**: solicitud válida según perfil existente, congelación de versión, entrega, acuse y consulta por operación. Diferenciar 202 SOL pendiente de acuse EVA. No cambiar fórmulas, moneda, pago doble ni reglas de riesgo para forzar aceptación.
8. Habilitar **EVA → SOL** con base/token callback correctos, crear decisiones mediante las operaciones existentes EVA, probar tres resultados y subsanación versionada. Registrar IDs sintéticos de solicitud, versión, operación, evaluación, ronda y correlación para conciliación.
9. Ejecutar errores y reinicios de servicios propios, recopilar evidencias saneadas y comparar persistencia. Revisar outboxes antes/después. No limpiar con `docker compose down -v` ni eliminar recursos compartidos; cualquier cierre posterior debe enumerar exactamente recursos propios y conservar evidencias.

## Casos propuestos y criterios de aceptación — no ejecutados

| Hito | Casos | Evidencia esperada |
|---|---|---|
| CAP → SOL / CR01 | Búsqueda/detalle; materno ausente/null/vacío; habilitada válida; vencida/revocada/incompatible; token incorrecto; COREDB no disponible | Proyección mínima sin identidad inventada; rechazos seguros; ningún token de EVA en CAP; sin fallback SIMULADO |
| Creación/edición SOL | Condiciones, calendario preliminar, garantías y fiadores con datos sintéticos permitidos; límites/errores/permisos | Persistencia y snapshots correctos según contratos actuales; decisiones financieras pendientes siguen bloqueadas |
| Recepción EVA / CR02 | Expediente versionado; acuse completo; GET operación; pérdida de respuesta después de persistir, timeout y reintento | Mismo idOperacion y X-Idempotency-Key; una sola recepción; conciliación persistente, sin duplicar evaluación |
| Conflictos CR02 | Misma operación con contenido diferente; otra versión; cabeceras/JSON malformados; token ausente/cruzado | Rechazos del contrato real y sin modificar expediente congelado; capturar HTTP/body exactos, no inferirlos del README |
| Callback / CR03 | APROBADO, OBSERVADO, RECHAZADO; token incorrecto/ausente; IDs/correlación/ronda/versiones incompatibles | Resultado solo aplicado a reserva/versión correspondiente; seguridad y estados existentes conservados |
| Repeticiones CR03 | Callback duplicado, antiguo, fuera de orden; caída después de aplicar y antes de recibir acuse | Sin aplicación doble ni sobrescritura histórica; deduplicación y respuesta efectiva registradas |
| Subsanación | OBSERVADO → edición permitida → nueva versión/envío/ronda → nuevo resultado | Historia anterior inmutable y correlaciones nuevas correctas; resultado previo no contamina versión vigente |
| Errores/red | CAP/EVA 4xx/5xx, JSON incompatible, desconexión, timeout, respuesta perdida | Fallo explícito y reintento/conciliación según contrato, no cambio a Bus/SIMULADO ni exposición de secretos |
| Reinicio | Reiniciar solo APIs/worker SOL y EVA con BD viva; reservas pendientes, reinicio durante entrega/callback | Recuperación desde BD, sin duplicados; distinguir expiración del lease de resolución efectiva |
| Auditoría/privacidad | Evento/acuse, error/timeout/duplicado, reintento, acceso sin rol y sesión caducada; revisar logs/respuestas | Outbox y autorización conservados; sin tokens, documentos completos o PII innecesaria; indicar proveedor simulado si autorizado |

Para fallos temporizados se necesitará un mecanismo controlado de laboratorio (por ejemplo un proxy de pruebas revisado o parada de una API propia), aún no creado. No modificar módulos de compañeros para inyectar fallos. Un acuse perdido debe reproducirse después de la persistencia y probarse por consulta de operación, no solo simulando conexión rechazada.

Riesgos EVA ya identificados por inspección: el worker considera cualquier 2xx como entrega sin validar el cuerpo del acuse; el lease no incorpora generación de intento; 409 puede tener causas diferentes y acaba agotando reintentos. Probar respuesta incompatible, concurrencia y recuperación antes de certificar estos escenarios; no afirmar que esas carreras ya se reprodujeron con MySQL. No ejecutar fixtures destructivas EVA sobre el servidor del ensayo.

## Evidencia obtenida ahora y pendientes

- Docker Compose disponible: versión 2.26.1-4. Consulta Docker inicial restringida devolvió permiso denegado; lectura autorizada posterior salió 0, sin mutaciones.
- Inventario Docker: cuatro contenedores E06 detenidos (`bna-sol-e06-sol-1`, `init-1`, `frontend-1`, `mysql-1`); red `bna-sol-e06_default`, redes estándar y red de PostgreSQL ajena; cinco volúmenes de proyectos ajenos. Ninguno reutilizado ni eliminado. La consulta filtrada al proyecto `bna` no devolvió contenedores. Este inventario no reserva nombres ni certifica un Compose aún inexistente.
- Se verificaron referencias locales y configuraciones por lectura; no hubo fetch, cambio de rama ni ejecución de inicializadores. No se realizaron pruebas HTTP/MySQL nuevas, build ni `./bna test`/`./bna smoke`, porque excederían la preparación y podrían arrancar servicios compartidos.

| Elemento | Preparación | Falta para ejecutar |
|---|---|---|
| Fuentes CAP/SOL/EVA | Referencias y adapters identificados | Snapshot saneado, manifiesto nuevo y revisión de diferencias locales |
| Topología y dependencias | Diseño aislado definido | Compose exclusivo, bootstrap mínimo, validación de recursos/redes/montajes y autorización de arranque posterior |
| CAP → SOL | Contrato y variables disponibles | COREDB/CAP provisionados y prueba HTTP; confirmar permisos de servicio y mantener identificación simulada |
| SOL → EVA | Rutas, tokens, idempotencia y consulta preparados | MySQL real de laboratorio y evidencia de conciliación TCP |
| EVA → SOL | Callback y credenciales emparejables | Ensayo real de resultados, subsanación, reintentos y riesgos del worker |
| Auditoría CR10 | Ausencia institucional confirmada en repositorio | Receptor homologado o autorización explícita del simulador para laboratorio; sin esto no habilitar SOL REAL conjunto |
| Datos y decisiones | Solo datos sintéticos propuestos | Aceptar seed de desarrollo o resolver catálogos mínimos; decidir tmpfs frente a durabilidad; no aprobar políticas financieras por este ensayo |

**Siguiente acción recomendada:** resolver primero el alcance de CR10 con Seguridad y el responsable del ensayo. En paralelo puede prepararse, para revisión, el Compose aislado y el bootstrap mínimo documentados, sin arrancarlos. Después verificar aislamiento y autorizar escrituras/arranque por fases. Los proveedores HTTP pueden probarse como software real de laboratorio; CAP conserva verificaciones simuladas y EVA reglas provisionales, por lo que el éxito técnico no equivaldrá a integración institucional homologada.
