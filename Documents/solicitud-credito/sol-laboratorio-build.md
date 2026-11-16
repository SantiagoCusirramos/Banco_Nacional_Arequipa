# SOL-LAB-BUILD — infraestructura preparada, no ejecutada

Fecha: 2026-11-16, America/Lima. Rama conservada: `feature/sol-integracion-cap-eva`.

## Resultado

Se preparó una infraestructura exclusiva para CAP → SOL → EVA → SOL. Pasaron las validaciones estáticas de la composición base y su overlay opcional, 97 hashes de fuentes, AST y nueve pruebas negativas del validador. **No se construyeron imágenes ni se arrancaron servicios; no hubo inicializadores, migraciones, DDL/DML, HTTP o MySQL ejecutados.** Los 219 tests SOL aprobados siguen siendo evidencia anterior, no regresión nueva de esta tarea.

El laboratorio permanece bloqueado para arranque por decisiones y comprobaciones enumeradas al final. Auditoría no se elimina ni se homologa por configuración: SOL REAL conserva sus requisitos y la base deliberadamente no tiene receptor CR-INT-10.

Fuentes de contexto: [plan del laboratorio](sol-plan-laboratorio-cap-eva.md), [auditoría PR](sol-auditoria-pr-cap-eva.md), [adaptadores](sol-adaptadores-cap-eva.md), [contrato EVA](sol-contrato-evaluacion.md), AGENTS.md, plan vigente y changelog. No se repitió la auditoría completa de APIs ni pruebas bancarias anteriores.

## Entregables y captura exacta

Los artefactos creados en BUILD están en [laboratorio/](laboratorio/README.md). Nota de cierre SOL-LAB-CLOSE: los JSON generados `sources-manifest.json` y `evidencias-http-independientes.json` se conservan localmente y se excluyen del commit; el manifiesto reproducible se genera externamente y los resultados saneados permanecen en los informes. La tabla conserva el inventario histórico de creación:

| Archivo | Función |
|---|---|
| `compose.yaml` | Topología base de 12 servicios, sin receptor de auditoría inventado |
| `compose.audit-sim.yaml` | Opción explícita del simulador existente, perfil audit-sim, no activada |
| `prepare.py` | Captura allowlist, secretos externos y manifiesto por archivo |
| `Dockerfile.api`, `Dockerfile.core` | Imágenes privadas del ensayo; no modifica Dockerfiles generales |
| `guard.py` | Gate DDL/inicialización y gate independiente de auditoría académica |
| `bootstrap_sol.py` | Creación del esquema/usuario SOL en MySQL de módulos, pendiente de ejecución |
| `http_probe.py` | Runner HTTP sin credenciales: sondas COREDB/CAP/SOL/EVA, no ensayo financiero |
| `validate.py` | Render seguro de Compose y restricciones estáticas |
| `test_static.py` | Rechazo de nueve configuraciones inseguras en memoria |
| `sources-manifest.json` | SHA256 y origen exacto de 97 archivos; hashes de diez herramientas/configuraciones |
| `README.md` | Uso seguro y referencias |

También se creó este informe y se amplió el único [change-log](change-log.md). No se modificó código funcional de SOL, módulos ajenos, Compose compartido, CI o política financiera. Los cinco archivos SOL previamente modificados y test_providers.py siguen intactos por hash; AGENTS/README y demás aportes locales se conservaron.

Captura final verificada: `/tmp/bna-sol-lab-lab20261116d-rd3tyyye`. Contiene `sources/api`, `sources/core`, `manifest.json` y `runtime/`. Es externa, directorio 0700; archivos de entorno 0600. Las capturas preliminares a/b/c también son externas, no usadas como evidencia final ni como recursos Docker. No se eliminaron archivos o recursos ajenos.

| Origen | Procedencia aplicada |
|---|---|
| COREDB y SQL integrado | HEAD `de4ace61f9fce7befb79828ea56133a6667eb914`, únicamente Python de COREDB y cinco archivos SQL/configuración seleccionados |
| SOL | Python y `config/politica_demo.json` del workspace actual, incluidos los cambios sin commit en adaptadores/modelos/proyección/configuración. Tests, caches, DB y archivos de entorno excluidos del contexto runtime |
| CAP | Solo Python de `backend/CAPTACION/` en `4ea5014bddb1a69289402f03b3fbc47c28cc9413` |
| EVA | Solo Python de `backend/EVALUACION/` en `57b0e2a34fd55fb96fd6245acc06a86536d220f8` |
| Dependencias | requirements-coredb desde HEAD, requirements-sol del workspace, requirements.txt del SHA EVA, con sus hashes |
| Herramientas | Archivos de laboratorio capturados con hashes; contextos sin paquetes CORE legado/CUENTAS/TARJETAS ni datos operativos |

No merge, checkout, rebase ni fetch. Se verificó que las referencias locales PR siguen en los SHA auditados. Las rutas COREDB de cuentas/tarjetas y los esquemas integrados permanecen porque son parte de COREDB; no se superpusieron implementaciones de otros módulos heredadas en CAP. El manifiesto registra el estado local relevante y cada archivo, sin hashes de secretos. Reejecutar prepare genera secretos distintos; reproduce procedencia y reglas, no valores secretos ni imágenes bit a bit. `tzdata>=2025.1` y dependencias transitivas no están completamente bloqueadas: documentar versiones/digests resultantes en una futura construcción, sin inventarlos ahora.

## Arquitectura y aislamiento

Proyecto: `bna-sol-cap-eva-lab-lab20261116d`. Imágenes propias con namespace del proyecto (`/coredb:lab`, `/providers:lab`, `/sol:lab`, `/mysql-core:lab`). MySQL de módulos usa imagen oficial 8.4 fijada por digest. No se sobrescriben `bna/backend:local` u otras imágenes compartidas. Python y MySQL fijan los mismos digests de base revisados del proyecto.

| Servicio | Redes | Inicialización/dependencia |
|---|---|---|
| mysql-core | core-data | tmpfs nuevo; gate DDL antes del entrypoint oficial |
| coredb-init | core-data | MySQL saludable; administrador inicial sintético |
| coredb:8012 | core-data, integration | coredb-init completado |
| mysql-modulos | module-data | tmpfs nuevo, sin SQL legado; gate DDL |
| captacion-init | module-data, integration | MySQL módulos y COREDB saludables; crea base/tablas/servicio |
| captacion:8014 | module-data, integration | Inicialización completada; secreto CAP montado solo lectura |
| sol-bootstrap / sol-init | module-data | Bootstrap esquema/usuario → init/migración/seed SOL explícito |
| sol:8011 | module-data, integration | Inicialización SOL y CAP/EVA saludables; perfil flow; Auditoría requerida por código |
| evaluacion-init | module-data | DDL y permisos específicos EVA |
| evaluacion:8015 | module-data, integration | Init completado y COREDB saludable; callback inicialmente vacío |
| http-runner | integration | Perfil tools, ejecución manual, sin credenciales ni dependencias que arranquen APIs |
| audit-lab:8020 | integration | Solo overlay + perfil audit-sim + autorización académica; en memoria |

Las tres redes son internas y propias del proyecto; no hay puertos publicados, `container_name`, redes/volúmenes externos, socket Docker, host networking, host-gateway ni binds de datos. Único volumen nombrado: `cap-secrets`, prefijado automáticamente por proyecto, no externo. MySQL usa tmpfs de 1536 MiB por servidor y 16 MiB para socket; revisar RAM disponible antes de aprobarlo. APIs son no-root, filesystem de solo lectura, `/tmp` tmpfs, capabilities eliminadas y no-new-privileges. Comprobar en runtime el propietario UID10001 del volumen CAP; no se afirma probado estáticamente.

Solo COREDB tiene red SQL integrada; CAP/SOL/EVA usan SQL de sus esquemas propios en mysql-modulos y HTTP para integración. Usuarios separados: cap_lab/sol_lab/eva_lab, sin root en APIs. Root de módulos solo en su MySQL e inicializadores con necesidad explícita. `MYSQL_ROOT_HOST=%` permite esos inicializadores únicamente dentro de la red privada de módulos, no publica MySQL al host. COREDB usa bna_app_user con roles originales, no root.

La construcción futura necesitará descargas de imágenes/paquetes; el aislamiento descrito corresponde al runtime. En este trabajo no hubo descargas ni build. tmpfs pierde datos al recrear/reiniciar MySQL: el ensayo de reinicio inicial debe limitarse a APIs con MySQL vivo. Cualquier prueba de durabilidad exige primero revisar almacenamiento persistente exclusivo.

## SQL e inicializadores revisados, no ejecutados

- `bna_core.sql`: esquemas explícitos core/clientes/cuentas/tarjetas/creditos, tablas, restricciones, rutinas, triggers, roles y owner bloqueado. No renombrar solo un esquema ni apuntar al servidor compartido.
- `bna_extension.sql`: usuarios/sesiones/auditoría integrada, catálogos, procedimientos y GRANT; no es un receptor CR10.
- `crear_usuarios.sh`: crea usuarios SQL app/admin/Seguridad mediante contraseñas de entorno obligatorias. `sh -n` pasó; nunca se ejecutó.
- `bna_datos_dev.sql`: seed académico, no datos institucionales. `LAB_DATOS_DEV=0` predeterminado excluye ese archivo de la imagen construida; requiere decidir si se autoriza 1 para catálogos sintéticos o cómo proporcionar catálogos mínimos. No asumir funcionamiento completo sin ellos.
- `bootstrap_sol.py`: valida host mysql-modulos, usuario sol_lab y nombre `bna_sol_mvp_<runid>`; CREATE DATABASE/USER, ALTER USER y GRANT ALL exclusivamente en ese esquema. Compatible con el init SOL que crea/migra sus tablas; no concede privilegios globales.
- SOL init: `python -m SOL.manage init`, migra estructura y crea cuatro cuentas demo con contraseña sintética externa; también carga referencias demo existentes. En REAL estas no reemplazan a CAP: las referencias del ensayo se obtendrán por HTTP y deben provenir de un caso CAP sintético. No presentar seed como captación real.
- CAP init: crea base/usuario/tablas, ALTER/GRANT propios, login administrador COREDB y creación/reactivación/rotación del servicio CLIENTES; escribe secreto en volumen privado. Repetir puede rotarlo; no es una sonda.
- EVA init: CREATE/ALTER/REVOKE/GRANT por tabla y DROP/CREATE TRIGGER en su propia base. No reutilizar usuario o base de otros ensayos.

**El primer arranque MySQL ya escribe SQL**, aunque todavía no se hayan ejecutado los servicios init. Gate `LAB_ALLOW_DDL=YES_ISOLATED_LAB` se exige antes de ese entrypoint y de cada inicializador; archivo control permanece NO. Es una barrera operativa del laboratorio, no una garantía frente a un operador que cambie/bypassee los comandos. Las fixtures destructivas de pruebas EVA no se incorporan ni ejecutan.

## Configuración preparada y credenciales

`prepare.py` genera secretos hexadecimales aleatorios de 64 caracteres, separados por función. Solo imprime ruta externa. `runtime/control.env` contiene rutas, identificador y gates no secretos; los otros envfiles contienen contraseñas/tokens y nunca deben adjuntarse. No ejecutar `source`, `cat` ni guardar el render interpolado de Compose. Docker entrega las variables al contenedor: un administrador del daemon puede inspeccionarlas; este laboratorio local no es un gestor institucional de secretos.

- SOL → CAP: `SOL_CAP_BASE_URL=http://captacion:8014`; token igual a `CAP_SOL_TOKEN`. Rutas `/cap/references` y `/cap/references/{idCliente}`.
- SOL → EVA: `SOL_EVA_BASE_URL=http://evaluacion:8015`; token igual a `EVALUACION_TOKEN_SOL`. Rutas POST `/eva/applications`, GET `/eva/operations/{idOperacion}`.
- EVA → SOL: `EVALUACION_SOL_TOKEN_RESULTADOS=SOL_EVA_CALLBACK_TOKEN`, diferente de CAP/EVA de salida. `EVALUACION_SOL_URL` queda vacío en la fase inicial; tras autorizar callbacks, su valor debe ser **http://sol:8011**, sin path. EVA añade POST `/sol/integrations/evaluation-results`.
- Auditoría: campos SOL_AUDIT_* vacíos en base; Bus vacío, sin fallback a SIMULADO. Overlay incorpora token de auditoría independiente, base http://audit-lab:8020 y path /security/events, exclusivamente hacia simulador existente.
- COREDB: host mysql-core, puerto3306, app_user y JWT propios; administrador humano admin-lab inicial para provisionar CAP. EVA necesitará perfiles humanos/permisos existentes creados vía API en fase posterior.
- Bases: `bna_sol_mvp_lab20261116d`, `bna_captacion_lab20261116d`, `bna_evaluacion_lab20261116d`. No localhost/remotos/variables heredadas como CAP_DB_URL, ni `.env` de compañeros en contexto.
- Se conservan tiempos SOL 0,6 s/2,4 s/dos reintentos/worker5 s; REAL global. CAP OTP simulado solo académico, EVA política provisional sin convertirla en aprobación institucional.

## CR-INT-10 y habilitación posterior

El simulador existente `SOL.simulator:app` expone también rutas CAP/EVA, pero solo se conectaría a él el canal de Auditoría; los clientes CAP/EVA siguen dirigidos a servicios propios y con otros tokens. Su ACK AUD-SIM y deduplicación en memoria **no son institucionales ni durables**. No se modificó su código.

La opción no está en el Compose base. Añadir `-f compose.audit-sim.yaml` no basta: los comandos de SOL y audit-lab exigen `LAB_AUDIT_SIM_AUTHORIZATION=AUTHORIZED_ACADEMIC_ONLY`. Archivo control sigue NO. La autorización tendría que indicar expresamente uso académico y evidencias marcadas simuladas. La alternativa institucional requiere receptor homologado y configuración/credenciales/ruta revisadas, no disponible todavía.

No usar URL ficticia para pasar validación, no desactivar workers/auditoría ni confundir 2xx con homologación. Una autorización de escrituras del laboratorio tampoco autoriza implícitamente el simulador.

## Comprobaciones ejecutadas

| Comprobación | Resultado real |
|---|---|
| Rama/status/referencias | Rama correcta, referencias coincidentes, cambios anteriores preservados; sin cambio de rama |
| prepare final | Salida0; captura externa y secretos sintéticos sin exposición |
| validate final | Salida0: 97 hashes, diez herramientas, AST, permisos externos y directorios de contexto0755, ausencia de secretos generados en fuentes/entregables, rutas/destinos/tokens, recursos/redes, dependencias sin ciclos, gates NO |
| Compose base y overlay | `config --format json` capturado en memoria, ambas salidas0; 12/13 servicios, sin daemon Docker |
| test_static | Nueve pruebas aprobadas, 0,626 s, salida0: rechaza puertos MySQL, red/volumen externo, token cruzado, root en API, ciclo, auditoría/callback anticipados y gate abierto |
| Shell SQL provisioning | `sh -n crear_usuarios.sh`, salida0; no ejecuta su contenido |
| Preservación | Hashes de 18 fuentes Python SOL, test_providers.py, AGENTS y README-INICIO coinciden con inicio de tarea |

Primera captura preliminar validó 97 fuentes; luego se añadieron hashes de herramientas y pruebas negativas y se hizo captura final. Una comprobación con directorio inexistente salió1/FileNotFoundError, rechazo seguro sin secretos. No se conservó salida interpolada de Compose. No se ejecutaron test bancarios, `./bna test/smoke`, Docker build/up ni inicializadores; no se vuelve a afirmar 219 aprobadas como resultado actual.

Las comprobaciones estáticas no certifican pull de imágenes, resolución de dependencias Python, capacidad RAM, readiness real, permisos de volúmenes, conectividad TCP ni funcionamiento del negocio. El runner preparado solo revisa sondas: recepción, idempotencia, callback, subsanación, errores y reinicios requieren el ensayo posterior del plan, con sus evidencias.

## Comandos posteriores — no ejecutados, requieren autorización

Desde la raíz, usar siempre archivos y proyecto exclusivos, nunca el Compose raíz. `LAB_ROOT` siguiente es una ruta, no una credencial. No abrir gates hasta completar las condiciones de la sección final.

```bash
LAB_ROOT=/tmp/bna-sol-lab-lab20261116d-rd3tyyye
LAB_FILES=Documents/solicitud-credito/laboratorio
PYTHONDONTWRITEBYTECODE=1 python3 "$LAB_FILES/validate.py" "$LAB_ROOT"
PYTHONDONTWRITEBYTECODE=1 python3 "$LAB_FILES/test_static.py" "$LAB_ROOT"
```

Antes de autorizar arranque, consultar solo nombres/labels/estados de Docker para comprobar que no existen contenedores, redes, volúmenes o tags del proyecto nuevo. No imprimir `.Config.Env`. La comprobación física sigue pendiente; el inventario de SOL-LAB-PREP no reserva nombres. Si hay colisión, generar otro run-id y renovar captura/manifiesto, sin borrar recursos. Validar memoria y revisar todos los archivos antes de descargar/construir.

Solo después de autorización separada de **build**:

```bash
docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" --profile '*' build
```

Build usa gates NO, no inicializa DB. Decidir `LAB_DATOS_DEV` antes de esa construcción; si se aprueba seed sintético, modificar solo ese campo no secreto del archivo externo y registrar la decisión. Nunca imprimir otros envfiles.

Solo después de autorización de **escrituras y primer arranque**, ejecutar por fases con prefijo de variable no secreta. Estos comandos contienen escrituras y **no se ejecutaron en esta tarea**:

```bash
LAB_ALLOW_DDL=YES_ISOLATED_LAB docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" up -d mysql-core mysql-modulos
LAB_ALLOW_DDL=YES_ISOLATED_LAB docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" up coredb-init
LAB_ALLOW_DDL=YES_ISOLATED_LAB docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" up -d coredb
LAB_ALLOW_DDL=YES_ISOLATED_LAB docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" up captacion-init evaluacion-init sol-init
LAB_ALLOW_DDL=YES_ISOLATED_LAB docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" up -d captacion evaluacion
```

Las dependencias de `up` pueden arrancar/revisar inicializadores anteriores; leer salida y no repetir CAP init por rutina. SOL init arrastra sol-bootstrap. En cualquier fallo parar la secuencia y diagnosticar solo recursos propios. No continuar hacia SOL REAL sin la decisión CR10.

Si posteriormente se autoriza **por escrito el simulador académico**, ejemplo de activación explícita (además de la autorización DDL):

```bash
LAB_ALLOW_DDL=YES_ISOLATED_LAB LAB_AUDIT_SIM_AUTHORIZATION=AUTHORIZED_ACADEMIC_ONLY docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" -f "$LAB_FILES/compose.audit-sim.yaml" --profile audit-sim up -d audit-lab sol
```

Con receptor institucional se necesita configuración revisada diferente, no este overlay. Una vez estén todas las APIs saludables, ejecutar manualmente el runner de sondas con la misma selección de archivos; no arrastra dependencias:

```bash
docker compose --env-file "$LAB_ROOT/runtime/control.env" -f "$LAB_FILES/compose.yaml" run --rm --no-deps http-runner
```

Para habilitar después callbacks, editar únicamente `EVALUACION_SOL_URL` del envfile EVA externo a http://sol:8011, preservar permisos0600 y recrear solo evaluacion con dependencias ya comprobadas y gates correspondientes; todavía no preparado como habilitación automática. Registrar decisiones y resultados. No usar fixtures destructivas de EVA, `down -v`, reset ni limpieza de volúmenes compartidos.

## Condiciones exactas para autorizar el primer arranque

1. Revisar y aprobar Compose, manifiesto, SQL/bootstrap, gates y snapshot; comprobar rama y hashes de nuevo. Si cambian fuentes/PR/herramientas, regenerar captura y evidencias.
2. Confirmar recursos nuevos sin colisiones, redes internas sin puertos, tmpfs suficiente y volumen CAP exclusivo; no acceder a recursos E06 o institucionales. El aislamiento estático pasó, el efectivo aún no se ha observado.
3. Aprobar catálogos: DATOS_DEV=0 exige resolver requisitos mínimos; DATOS_DEV=1 solo con aceptación explícita de seed sintético. Aceptar pérdida de tmpfs o aprobar otro almacenamiento aislado antes de usarlo.
4. Autorizar separadamente descarga/build y las escrituras de primer arranque/inicializadores. Generación externa de secretos ya está preparada y ejecutada; no autoriza esos pasos.
5. Para el recorrido conjunto con SOL REAL, decidir CR10: receptor de Seguridad homologado o autorización académica explícita del simulador. No es condición técnica para probar únicamente MySQL/COREDB/CAP/EVA por separado, sí para activar SOL conjunto.
6. Confirmar permisos humanos/servicio CAP y EVA y plan de datos sintéticos. No activar callback antes de disponer de SOL saludable y reserva válida; conservar controles de versión/operación/ronda/correlación.

**Listo para revisión estática y autorización de una tarea posterior de construcción/arranque por fases. No integrado_real.** El siguiente paso es decidir Auditoría/catálogos/almacenamiento y comprobar colisiones/capacidad; después autorizar build y arranque aislado explícitamente. No se requiere ni se propone cambiar lógica financiera de SOL.
