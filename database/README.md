# bna-core-db — base de datos integrada del CORE del BNA (MySQL 8.4)

Esta es la rama `mysql`: la misma base de datos integrada del CORE del Banco
Nacional de Arequipa (BNA) de la rama `main` (PostgreSQL), implementada en
MySQL 8.4 porque el equipo de infraestructura decidió mantener MySQL. Solo
una de las dos versiones se usará; el informe de diseño de la base de datos
(curso Gestión de Sistemas y Tecnologías de la Información, UCSM) documenta
las dos.

## Relación con la rama main

- **El modelo es el mismo.** El modelo entidad-relación, la transformación al
  modelo relacional y la normalización (`modelo/modelo_bna.py`,
  `modelo/diagramas_mer.py` y los fragmentos del modelo en `informe/`) son
  idénticos a los de `main`. `trazabilidad/matriz.py` lo comprueba archivo por
  archivo contra el commit `MAIN_COMMIT` de `trazabilidad/catalogo.py` y se
  detiene si alguno difiere.
- **Cambia la capa física.** `modelo/ddl_bna.py` conserva los datos del
  diseño (tipos lógicos, claves, CHECK, catálogos, semillas) y escribe MySQL;
  `modelo/programacion_bna.sql` es la capa programable reescrita para MySQL,
  con las mismas reglas.
- **Las pruebas tienen los mismos ID.** Las 100 pruebas de `main` están
  portadas en `pruebas/mysql/`; L02, M20c, F32 y G01–G05 son solo de MySQL.
- **Queda en main** lo que respalda la selección del gestor: los experimentos
  E1–E7, la reproducción de las fallas de la línea base MySQL (`ab6a6ec`) y
  el control sobre el DDL sin triggers.

Sobre el origen del repositorio (clon de
[SantiagoCusirramos/Banco_Nacional_Arequipa](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa),
línea base `ab6a6ec`) y la licencia, ver el README de la rama `main`: el
repositorio no declara licencia.

## Cómo se cumplen las reglas en MySQL

| En PostgreSQL (main) | En MySQL (esta rama) |
|---|---|
| Partida doble con un trigger de restricción diferido hasta el COMMIT | `core.registrar_asiento` registra el asiento con todas sus líneas solo si cuadra; `bna_app` no inserta asientos directamente |
| Bitácoras de solo inserción con triggers por fila y un trigger de TRUNCATE | `bna_app` no tiene UPDATE, DELETE ni DROP (TRUNCATE exige DROP); los triggers por fila son la segunda línea |
| Índices únicos parciales | Índices únicos funcionales (`CASE WHEN condición THEN columna END`) |
| Tipos UUID, BOOLEAN, INET, TIMESTAMPTZ | BINARY(16), TINYINT(1) y VARCHAR(45) con CHECK; DATETIME(6) en UTC |
| `marcar_tarjetas_vencidas()` programada fuera de la base | Procedimiento y evento diario `tarjetas.ev_marcar_tarjetas_vencidas` |

## Roles

- `bna_owner`: cuenta bloqueada, dueña (DEFINER) de los triggers,
  procedimientos, vistas y del evento.
- `bna_admin`: DDL y DML sobre las cinco bases, sin privilegios de servidor.
- `bna_app`: la aplicación. Lee todo, inserta en las tablas de negocio salvo
  los asientos y el consumo diario, actualiza solo las columnas que cambia una
  operación de negocio, y no borra, no trunca ni altera nada.

Las pruebas corren con `bna_app`; las reglas protegidas por privilegio se
repiten con `bna_admin`, que debe toparse con el trigger o la restricción.

## Contenido

| Ruta | Qué contiene |
|---|---|
| `modelo/` | El modelo integrado (igual que en `main`), el generador del DDL para MySQL (`ddl_bna.py`), los diagramas y la capa programable (`programacion_bna.sql`). |
| `sql/bna_core.sql` | El DDL generado, listo para cargar en MySQL 8.4 con `conf/mysql/bna.cnf`. |
| `conf/mysql/bna.cnf` | La configuración del servidor de la que dependen las reglas: modo estricto, UTC, collation y planificador de eventos. |
| `pruebas/mysql/` | Arnés, datos de prueba, pruebas (`pruebas.sql` con `bna_app`, `pruebas_admin.sql` con `bna_admin`) y el ejecutor. |
| `trazabilidad/` | Catálogo de fuentes y de cómo se cumple cada regla en cada gestor, fallas MySQL con su línea en `ab6a6ec` y el generador de la matriz. |
| `resultados/` | Salidas en bruto de las pruebas con `metadatos.txt` (fecha, commit, versión, imagen y configuración del servidor) y la matriz. |
| `informe/` | Fragmentos LaTeX generados. El informe incluye desde esta rama solo los `mysql-*`; el modelo lo toma de `main`. |
| `imagenes.env` | La imagen de MySQL 8.4, fijada por digest. |

## Ejecución

Requisitos: Docker, Python 3.9 o superior y Git con la historia completa del
repositorio (la matriz lee `ab6a6ec` y la rama `main`). Un solo comando vuelve
a ejecutar todo:

```bash
./run_all.sh
```

1. Regenera `sql/bna_core.sql` y los fragmentos del modelo en `informe/`.
2. Ejecuta las pruebas en MySQL 8.4 (`resultados/mysql/`).
3. Genera la matriz de trazabilidad (`resultados/trazabilidad.md` y `.csv`),
   comprueba que el modelo sea el de `main` y escribe los fragmentos
   `informe/mysql-*.tex`, con los resultados de PostgreSQL de `main`.

Conviene ejecutarlo con el árbol limpio y confirmar después solo `resultados/`
e `informe/`.

Para cargar la base fuera de las pruebas, el servidor debe tener la
configuración de `conf/mysql/bna.cnf` y las tablas de zonas horarias
(`mysql_tzinfo_to_sql`); `CALL core.verificar_configuracion()` lo comprueba.

## Despliegue

`conf/mysql/crear_usuarios.sh` crea `bna_app_user` y `bna_admin_user` al
inicializar un volumen vacío, con las contraseñas de `CORE_DB_APP_PASSWORD` y
`CORE_DB_ADMIN_PASSWORD`, y `bna_seguridad_user` con `CORE_DB_SEGURIDAD_PASSWORD`. No hay contraseñas en el repositorio. El contenedor se
arranca con `sql/bna_core.sql`, `sql/bna_extension.sql` y ese script en
`/docker-entrypoint-initdb.d/`, en ese orden, y con `bna.cnf` copiado a `/etc/mysql/conf.d/` con permisos 644, porque
MySQL ignora un archivo de configuración escribible por todos.

`pruebas/mysql/prueba_despliegue.sh` comprueba ese arranque.

Los archivos SQL fijan `SET NAMES utf8mb4` porque el cliente del contenedor los leería como latin1.
Un volumen creado antes de ese cambio conserva los acentos dañados, en los datos y en los mensajes de las rutinas: hay que recrearlo.
`pruebas/mysql/lecturas_api.txt` es la lista exacta de lo que `bna_api` puede leer; las pruebas X136 y X137 y `prueba_despliegue.sh` fallan ante cualquier lectura adicional.

Las versiones publicadas son etiquetas inmutables `bd-vX.Y-mysql`.

## Extensiones de integración

`sql/bna_extension.sql` agrega lo que necesita la API de integración: usuarios y
empleados, productos, tipos de cambio, periodos contables, idempotencia de
movimientos, auditoría general, equivalencias de catálogo y los procedimientos de
escritura. Está escrito a mano y se carga después de `sql/bna_core.sql`. **Queda
fuera del modelo normalizado:** no está en `modelo_bna.py`, ni en el MER, ni en la
rama `main`, y es una divergencia de esta rama.

Cada procedimiento público es atómico aunque se llame sin una transacción, registra
su propio evento de auditoría y exige un canal. La API se conecta con el rol `bna_api`,
que ejecuta esos procedimientos y lee solo las tablas que usa, con la tarjeta por
`tarjetas.v_tarjeta_api`, sin `pan_token` y con la cuenta principal; no lee credenciales de tarjeta ni datos
biométricos. Ninguna cuenta desplegada tiene `bna_app`, que conserva sus permisos para
las pruebas de la matriz y para los módulos que aún no tengan procedimientos.
`cambiar_estado_tarjeta` rechaza todo desbloqueo y el origen `SEGURIDAD`:
`tarjetas.desbloquear_tarjeta` solo la ejecuta el rol `bna_seguridad`
(`bna_seguridad_user`, con la clave de `CORE_DB_SEGURIDAD_PASSWORD`). `bna_admin` y
`bna_app` siguen pudiendo saltarse esa restricción con sus permisos directos.

Un débito por un canal y una moneda sin fila en `core.limite_canal` se rechaza con
`BNA-CANAL` (`ERR-TAR-006` en una autorización). `RN-BD-002` queda para la regla de la Billetera Digital, la fila con `habilitado` falso:

| Canal | PEN | USD | Fuente |
|---|---|---|---|
| ATM | 1500 | 500 | Cuentas, INT-04, p. 41; Tarjetas, C05, p. 27 |
| HB | 10000 | Sin fila: se rechaza | Cuentas, INT-07, p. 41; ninguna para USD |
| BD | 500 | No opera (`habilitado` falso) | Cuentas, INT-09, p. 41; Tarjetas, tabla 4 |
| VEN | Sin tope (monto nulo) | Sin tope (monto nulo) | Tarjetas, tabla 4: «NULL significa sin límite automático (ventanilla)» |
| AGE | Sin fila: se rechaza | Sin fila: se rechaza | Ninguna |

### Usuarios de servicio y clientes (desde `bd-v1.1-mysql`)

- **Usuarios de servicio:** un módulo se autentica en la API con un usuario de rol
  `SERVICIO` y su `modulo` (FK a `core.modulo`). `core.crear_usuario` no puede crearlos,
  porque `ck_usuario_servicio` exige el módulo. Se crean, renuevan y revocan con
  `core.crear_usuario_servicio`, `core.renovar_credencial` (solo usuarios de servicio) y
  `core.cambiar_estado_usuario`. `core.registrar_login` toma el actor de la fila del
  usuario, así que quien llama no puede atribuir el login a otro nombre.
- **Clientes:** `bna_api` no lee `clientes.*`. Todo pasa por estos procedimientos,
  concedidos solo a `bna_api` (no a `bna_app`):

| Procedimiento | Qué hace |
|---|---|
| `clientes.registrar_cliente` | Valida el documento con `clientes.tipo_documento` y genera `cod_cliente` (`CLI` y nueve dígitos). Crea la verificación de captación y el cliente: HABILITADO da ACTIVO y OBSERVADO da OBSERVADO |
| `clientes.consultar_cliente` | El cliente por su código, en JSON y sin biometría |
| `clientes.verificar_documento` | La consulta por documento. Sin identidad verificada responde lo mismo a un cliente y a quien no lo es; con identidad verificada aprueba solo a un cliente ACTIVO. Siempre deja la fila en `clientes.validacion_identidad` y el evento |
| `clientes.registrar_validacion` | Los veredictos de huella, rostro, celular y correo de Clientes |
| `clientes.cambiar_estado_cliente` | Exige un motivo, que queda en la bitácora. BAJA es final y el mismo estado no cambia nada. El trigger de tarjetas bloquea o cancela sus tarjetas; reactivar al cliente no las desbloquea |
| `clientes.catalogos_cliente` | Tipos de documento y estados de cliente |

Los mensajes de error de estos procedimientos no repiten documentos, correos ni
celulares, porque la API puede devolverlos. Qué actor puede registrar un cliente
HABILITADO o fijar cada estado lo decide la API. **Una base creada con
`bd-v1.0-mysql` debe recrearse** (volumen nuevo): `core.usuario_sistema` cambió.

### Lecturas de consulta de la API (desde `bd-v1.2-mysql`)

Para listar los movimientos de una cuenta, las cuentas de un cliente y la bitácora,
`bna_api` lee dos vistas y una tabla más. Sigue sin leer `cuentas.movimiento` ni
`core.evento_auditoria`.

| Objeto | Qué entrega |
|---|---|
| `cuentas.v_movimiento_api` | El movimiento sin su asiento contable, con la naturaleza de la operación (`D` o `C`) y la moneda de la cuenta |
| `core.v_evento_auditoria_api` | La bitácora general con el nombre del módulo. Los procedimientos no guardan datos personales en el detalle |
| `cuentas.titularidad` | Qué cuentas tiene cada cliente |

Solo agrega objetos: una base creada con `bd-v1.1-mysql` sigue sirviendo a una API
anterior, pero necesita un volumen nuevo para tener las vistas, porque los scripts de
inicio solo corren sobre un volumen vacío.

### Créditos (desde `bd-v1.4-mysql`)

La línea de créditos (Evaluación, Desembolso y Cobranza) escribe en `creditos.*` solo
por estos procedimientos, concedidos solo a `bna_api`, y lee por vistas: `bna_api` no lee
ninguna tabla de `creditos`.

| Procedimiento | Qué hace |
|---|---|
| `creditos.registrar_solicitud` | El expediente de SOL: la solicitud EN_EVALUACION y su calendario PRELIMINAR, que la base comprueba (cuotas consecutivas, fechas crecientes, saldos encadenados, tantas cuotas como meses). Una versión nueva, mientras la ronda no esté evaluada, abre otra ronda. La misma versión con la misma huella devuelve lo mismo. Devuelve la ronda y el id de la evaluación, que es determinista (`creditos.fn_id_evaluacion`) para el acuse a SOL |
| `creditos.evaluar_solicitud` | Guarda la situación financiera y la evaluación. COREDB calcula el score y el límite; la regla sale de `creditos.regla_evaluacion` por el ratio monto / límite. R-A aprueba, R-C rechaza, R-B queda para el analista |
| `creditos.registrar_analista`, `creditos.decidir_evaluacion` | El analista (un empleado activo) decide APROBADO o RECHAZADO una evaluación R-B, una vez y con comentario |
| `creditos.revocar_aprobacion` | Una aprobación sin desembolso pasa a RECHAZADA con motivo; sus órdenes abiertas, también |
| `creditos.preparar_orden`, `creditos.cambiar_cuenta_orden`, `creditos.registrar_validacion_orden`, `creditos.rechazar_orden` | La orden de una aprobación vigente (30 días, primera cuota sin vencer), con llave de idempotencia, sobre una cuenta de ahorros activa, individual, del titular y en la moneda del crédito. IDENTIDAD exige una verificación aprobada hoy (`clientes.verificar_documento`); CUENTA la registra la base |
| `creditos.confirmar_orden` | En una sola transacción: el movimiento DESEMBOLSO, la orden CONFIRMADA, el calendario OFICIAL (copia exacta del PRELIMINAR), el crédito AL_DIA y la solicitud DESEMBOLSADA. Repetirla devuelve lo mismo sin abonar otra vez |
| `creditos.registrar_pago_cuota` | En una sola transacción: el movimiento DEBITO_CUOTA y la aplicación de la cuota más antigua a la más reciente. Sin saldo, con la cuenta bloqueada o sobre el tope, el pago queda RECHAZADO con el código de la regla. La referencia es la llave |
| `creditos.registrar_mora`, `creditos.actualizar_vencimientos` | El cálculo de mora de una cuota vencida (se muestra, no se cobra) y el paso diario a VENCIDA y EN_MORA; lo corre el evento `creditos.ev_actualizar_vencimientos` |
| `creditos.catalogos_credito` | Estados, reglas con sus umbrales, métodos, tipos de validación y canales |

Vistas: `v_solicitud_api`, `v_calendario_api`, `v_historial_solicitud_api`,
`v_evaluacion_api`, `v_aprobacion_api`, `v_orden_api`, `v_validacion_orden_api`,
`v_credito_api`, `v_cuota_api`, `v_pago_api`, `v_mora_api`, `v_evento_credito_api`,
`v_conciliacion_cobranza` y `v_conciliacion_diaria`, sin nombres, documentos ni
contactos del cliente. Como el dinero se mueve dentro de estos procedimientos, la orden
no usa EN_PROCESO ni POR_VERIFICAR, el pago no usa PENDIENTE y `evento_entrega` queda sin
uso. La extensión agrega cuatro tablas (`numerador_orden`, `numerador_credito`,
`recepcion_solicitud`, `cobro_pago`); el modelo no cambia. Los mensajes de error no llevan
cifras ni valores de entrada. Solo agrega objetos, pero una base existente necesita un
volumen nuevo para tenerlos.

### Autorizaciones y credenciales de tarjeta (desde `bd-v1.5-mysql`)

El módulo Tarjetas autoriza, extorna y valida credenciales por COREDB. Las reglas son
las de los triggers que ya estaban (`tg_autorizacion_validar_bi`, `tg_intento_contar`);
estos procedimientos son la entrada de la API y se conceden a `bna_api`, `bna_app` y
`bna_admin`.

| Procedimiento | Qué hace |
|---|---|
| `tarjetas.autorizar_operacion` | Registra la autorización con el uuid que envía quien llama (RN-BUS-002). Si se cumplen las reglas queda AUTORIZADA con `00`, retiene el saldo y compromete el tope. Si una regla falla queda RECHAZADA con su código ISO 8583 (`51`, `54`, `57`, `61`, `62`) y un motivo sin montos. El mismo uuid con los mismos datos devuelve lo registrado; con otros datos falla con `BNA-IDEMPOTENCIA` |
| `tarjetas.extornar_autorizacion` | Pasa a EXTORNADA, con `EXT`, una autorización sin movimiento: los triggers liberan el saldo y el tope (RN-ATM-003). Repetirlo no cambia nada. Una rechazada o una que ya tiene su movimiento se rechaza con `BNA-EXTORNO` |
| `tarjetas.registrar_credencial` | Asigna o cambia el PIN (4 dígitos) o la clave web (6), con una sal aleatoria, y reinicia los intentos |
| `tarjetas.validar_credencial` | Compara el valor con el hash dentro de la base y registra el intento; el tercer fallo bloquea la tarjeta (RN-TAR-004). Con la tarjeta no operativa se rechaza sin registrar el intento |

`bna_api` lee la autorización en `tarjetas.v_autorizacion_api`, sin la IP de origen ni
el nivel de riesgo, y sigue sin leer `tarjetas.credencial`. El hash es
`SHA2(CONCAT(sal, valor), 256)`; ningún evento ni mensaje de error repite el valor. La
matriz de coordenadas queda para cuando haya un procedimiento que la emita. Solo agrega
objetos y cuatro códigos de respuesta: una base anterior necesita un volumen nuevo.

### Empleados (desde `bd-v1.6-mysql`)

Un administrador registra empleados por la API, sin el administrador de la base, y así
un analista de crédito queda disponible: empleado, usuario ANALISTA ligado a él y
`creditos.registrar_analista`.

| Procedimiento | Qué hace |
|---|---|
| `core.registrar_empleado` | Crea el empleado activo (código, nombre, cargo y agencia opcional) y, si se indica, lo liga a un usuario: una persona que todavía no tiene empleado. Rechaza el código repetido (`BNA-EMPLEADO-DUPLICADO`), la agencia inexistente (`BNA-AGENCIA`), el usuario inexistente (`BNA-USUARIO`) y el usuario de servicio o ya ligado (`BNA-USUARIO-EMPLEADO`) |

Se concede solo a `bna_api`; `bna_api` sigue sin escribir ni leer `core.empleado`. El
evento `REGISTRAR_EMPLEADO` guarda el código, el cargo y el usuario, no el nombre; los
mensajes de error no repiten valores de entrada. Solo agrega un procedimiento: una base
anterior necesita un volumen nuevo para tenerlo.

### Captación (desde `bd-v1.7-mysql`)

El expediente del **prospecto**, que todavía no es cliente, en tablas de extensión del
esquema `clientes`: `solicitante_captacion`, `caso_captacion`, `consentimiento_captacion`,
`otp_captacion`, `validacion_captacion`, `consulta_riesgo_captacion` y
`perfil_riesgo_captacion`. El modelo normalizado no cambia: solo se ligan a él por el
cliente que resulta (`clientes.cliente`), la agencia y, a través del cliente, su
verificación de captación. Los proveedores (RENIEC, listas, PEP, centrales, SMS) y el
puntaje son del módulo CAPTACION; la base guarda lo que responden y aplica las reglas del
expediente.

| Procedimiento | Qué hace |
|---|---|
| `clientes.registrar_solicitante_captacion` | Registra al prospecto con su documento validado por `clientes.tipo_documento`; un documento repetido devuelve el mismo solicitante (`p_duplicado`) |
| `clientes.abrir_caso_captacion` | Abre el caso (INICIADO). Un solo caso abierto por solicitante (`BNA-CASO-ABIERTO`, y un índice único sobre una columna generada) |
| `clientes.registrar_consentimientos_captacion` | De uno a cuatro consentimientos en JSON; vale el último de cada tipo y la versión se guarda solo en TERMINOS |
| `clientes.emitir_otp_captacion` / `verificar_otp_captacion` | Guarda el HMAC que calcula CAPTACION, vence el pendiente anterior del mismo canal y cuenta intentos; vencimiento e intentos salen de `clientes.tipo_contacto`. El código correcto registra la verificación CELULAR o CORREO |
| `clientes.registrar_validacion_captacion` | RENIEC, listas, PEP o biometría (con su consentimiento), del proveedor o manual; reemplaza al resultado anterior del mismo tipo |
| `clientes.registrar_consulta_riesgo_captacion` / `registrar_perfil_captacion` | La respuesta de una central (exige CONSULTA_BUROS) y el perfil de 0 a 1000 (exige una consulta; una consulta posterior lo deja desactualizado) |
| `clientes.cambiar_estado_caso_captacion` | Observar, levantar la observación, rechazar o revocar (solo un caso HABILITADO) |
| `clientes.vincular_cliente_captacion` | Liga al caso APROBADO el cliente ACTIVO con el documento del solicitante; quien verificó la identidad lo registra antes con `registrar_cliente` (punto R-01) |
| `clientes.habilitar_caso_captacion` | HABILITADO con vigencia de 1 a 365 días desde la fecha de negocio; deja en `clientes.validacion_identidad` las verificaciones de contacto. Repetirlo no cambia nada |

El estado se recalcula tras cada paso: INICIADO → EN_VALIDACION → APROBADO → HABILITADO,
OBSERVADO mientras algo quede por resolver, y RECHAZADO (validación rechazada, perfil
MUY_ALTO o decisión del asesor) o REVOCADO como finales. Las vistas
`clientes.v_*_captacion_api` dan a `bna_api` lo que necesita leer, con lo que falta para
habilitar el caso (`faltantes`) y sin el hash del OTP; `bna_api` no escribe ni lee las
tablas. Los eventos van al módulo CLIENTES (punto R-01: `core.modulo` no tiene CAPTACION)
sin documento, nombres ni contactos. Solo agrega objetos: una base anterior necesita un
volumen nuevo para tenerlos.

`pruebas/mysql/run_tests.sh` ejecuta toda la suite con la extensión cargada. Sus
pruebas (ID `X`) quedan en `resultados/mysql/resultado-extension.tsv`, fuera de la
matriz. `pruebas_sin_transaccion.sh` prueba cada procedimiento en autocommit, porque
el arnés siempre abre una transacción.

### Confirmación de autorización (desde `bd-v1.8-mysql`)

El cajero automático confirma una autorización retenida para convertirla en el débito
real al dispensar el efectivo.

| Procedimiento | Qué hace |
|---|---|
| `tarjetas.confirmar_autorizacion` | Confirma una autorización en estado AUTORIZADA o DISPENSADA sin movimiento: registra el movimiento real (RETIRO) con el mismo uuid de la autorización (RN-BUS-002), pasa la autorización a DISPENSADA y libera la retención (saldo_contable y saldo_disponible quedan iguales). Idempotente: repetir con la misma llave devuelve el mismo resultado; otra llave sobre autorización ya confirmada falla con `BNA-IDEMPOTENCIA`. Después de confirmar, `extornar_autorizacion` falla porque la operación ya tiene su movimiento. |

`bna_api` ejecuta este procedimiento y lee la autorización en `tarjetas.v_autorizacion_api`.
Solo agrega un procedimiento: una base anterior necesita un volumen nuevo para tenerlo.

### Billetera Digital (desde `bd-v1.9-mysql`)

La billetera «Chaski» (canal BD) en el esquema nuevo `billetera`, sobre las cuentas del
núcleo y sin saldo propio: su cuenta es una cuenta de ahorro individual en soles del
cliente, y cada envío, pago con QR o cobro aceptado es una
`cuentas.registrar_transferencia` por el canal BD, con su asiento y el tope diario del
canal (500 PEN, `core.limite_canal`). Tablas: `afiliacion` (PIN de 6 dígitos con sal,
intentos y cuenta), `comercio`, `codigo_qr`, `solicitud_cobro`, `operacion` y
`notificacion`. Agrega el módulo `BILLETERA` (id 10) a `core.modulo`.

| Procedimiento | Qué hace |
|---|---|
| `billetera.afiliar` | Afilia a un cliente ACTIVO que ya existe (punto R-01: la billetera no crea clientes) con una cuenta suya, ACTIVA, en soles y sin firma conjunta; repetirlo cambia el PIN o la cuenta, reinicia los intentos y anula los QR de la cuenta anterior |
| `billetera.validar_acceso` | Celular (el de `clientes.cliente`) y PIN: EXITOSO devuelve el cliente; FALLIDO cuenta el intento y al tercero deja la afiliación BLOQUEADA; también BLOQUEADA, NO_AFILIADO y CLIENTE_NO_OPERA. No es un error, así que el intento queda confirmado |
| `billetera.buscar_contacto` | El nombre corto («Ana D.») del dueño de un celular con billetera, o nulo |
| `billetera.registrar_comercio` | Comercio con RUC, razón social y cuenta de abono en soles, y su QR estático |
| `billetera.crear_qr` | Sin monto, el QR estático del cliente (siempre el mismo); con monto, uno dinámico que vence en 1 a 60 minutos (15 por omisión) |
| `billetera.transferir` | Envío a otra billetera por su celular (P2P) |
| `billetera.pagar_qr` | Pago de un QR de cliente o de comercio; un dinámico cobra su monto y queda PAGADO |
| `billetera.crear_solicitud` / `responder_solicitud` | Pedir dinero por celular (vence a las 48 horas); el pagador acepta (paga) o rechaza, quien la pidió la cancela |
| `billetera.marcar_notificaciones_leidas` | Los avisos del cliente |

Las operaciones de dinero exigen una llave de idempotencia y la reservan antes de
bloquear el QR o la solicitud, en su misma transacción: la petición repetida espera a la
primera y devuelve su operación (`p_repetido`), y la misma llave con otros parámetros se
rechaza. Después llaman a `registrar_transferencia` sin llave. Usan el savepoint
`bna_billetera`: con el `bna_op` de `registrar_transferencia`, el savepoint anidado
reemplazaría al suyo dentro de la transacción de quien llama. Ni la bitácora, ni los
avisos, ni la glosa de los movimientos, ni los errores guardan el celular o el PIN.
`bna_api` ejecuta los procedimientos y lee `billetera.v_*_api` (sin hash, sal, PIN ni
celular; los QR y las solicitudes vencidos se muestran VENCIDO); no lee ni escribe las
tablas. Tienda, promociones, cupones, recargas y pago de servicios quedan fuera. Solo
agrega objetos: una base anterior necesita un volumen nuevo para tenerlos.

### Billetera: lecturas con bloqueo (desde `bd-v1.10-mysql`)

Una operación de dinero repetida a la vez (misma llave) busca la operación de la primera
con una lectura con bloqueo (`FOR SHARE`): si quien llama ya había leído en su transacción,
como la API al validar al cliente, una lectura sin bloqueo vería esa instantánea y
respondería `BNA-IDEMPOTENCIA` en vez de la misma operación (pruebas X654 y X655).
`bna_admin` recibe sobre `billetera.*` lo mismo que sobre los demás esquemas (X670).
Solo cambia procedimientos y permisos: una base anterior necesita un volumen nuevo.

### Retenciones de tarjeta con caducidad (desde `bd-v1.11-mysql`)

Una autorización AUTORIZADA retiene el saldo disponible y el tope del día hasta que el
cajero la confirma o la extorna. Si el cajero cae en medio, la retención ya no queda
sin plazo:

| Objeto | Qué hace |
|---|---|
| `tarjetas.fn_minutos_retencion()` | El plazo por omisión: **15 minutos**. Es provisional; el plazo lo decide el equipo (pregunta en el issue #34) |
| `tarjetas.liberar_retenciones_vencidas(minutos, actor, OUT liberadas)` | Extorna las AUTORIZADA sin movimiento más antiguas que el plazo (`NULL` = el de omisión; de 1 a 1440, si no `BNA-PLAZO`). Los triggers devuelven el disponible y el tope del día en que se comprometieron. Deja `codigo_respuesta` `EXT`, el motivo `BNA-RETENCION` y un evento `LIBERAR_RETENCION` por autorización. Las DISPENSADA no se tocan |
| evento `tarjetas.ev_liberar_retenciones` | Llama al procedimiento cada minuto con el plazo por omisión (actor `SISTEMA`) |

`confirmar_autorizacion` rechaza una retención vencida con `BNA-CONFIRMACION: la
retención venció`, aunque el evento aún no la haya liberado. La liberación lee con
`FOR UPDATE SKIP LOCKED`: si una confirmación tiene la autorización bloqueada, la salta
y gana la confirmación; si la liberación llega primero, la confirmación espera y falla
(pruebas X510 a X520). El cajero debe confirmar dentro del plazo. Agrega un índice,
una función, un procedimiento y un evento, y cambia `confirmar_autorizacion`: una base
anterior necesita un volumen nuevo.

### Bloqueo del login del personal (desde `bd-v1.12-mysql`)

COREDB verifica la contraseña de una persona del banco; la base cuenta sus fallos
seguidos en `core.bloqueo_login` (que `bna_api` no lee):

| Objeto | Qué hace |
|---|---|
| `core.fn_intentos_login()` / `core.fn_minutos_bloqueo_login()` | **5** fallos seguidos bloquean el login **15 minutos**. Son provisionales: el número lo decide el equipo (pregunta en el issue #34) |
| `core.registrar_login_fallido(id, correlación, OUT bloqueado_hasta)` | Cuenta el fallo; al quinto bloquea y deja `BLOQUEAR_LOGIN`. Cada fallo deja `LOGIN_FALLIDO`. Con id nulo (usuario que no existe) no hace nada ni guarda lo escrito. Los fallos durante el bloqueo no suman ni lo alargan |
| `core.fn_login_bloqueado_hasta(id)` | Hasta cuándo está bloqueado, o `NULL` |
| `core.desbloquear_login(id, actor)` | El administrador levanta el bloqueo (`DESBLOQUEAR_LOGIN`) |

`core.registrar_login` rechaza con `BNA-LOGIN-BLOQUEADO` el login de un usuario bloqueado
y reinicia los fallos tras uno exitoso. El bloqueo vence solo. Un usuario de servicio
(rol `SERVICIO`) no se bloquea: su secreto es aleatorio, y bloquearlo dejaría a un módulo
sin acceso a pedido de cualquiera; sus fallos se auditan igual (pruebas X700 a X710).
Agrega una tabla: una base anterior necesita un volumen nuevo.

`sql/bna_datos_dev.sql` es **solo para desarrollo**: los periodos contables de 24 meses
desde el mes en curso, todos abiertos, el BIN 004499, una agencia, un terminal por canal y un cliente, para que una base nueva
pueda hacer un depósito. No va en producción.

## Brechas conocidas

Lo que MySQL no puede hacer cumplir a la base. Cada brecha tiene una prueba
que muestra que existe; si alguna dejara de existir, la matriz se detiene.

- **G01.** Una sesión puede quitar el modo estricto (`SET SESSION sql_mode`)
  sin privilegios; sus INSERT y UPDATE directos guardan valores truncados o
  ajustados. Los triggers y procedimientos usan el modo con que se crearon.
- **G02.** Una sesión puede apagar `foreign_key_checks` sin privilegios y
  guardar referencias a filas inexistentes.
- **G03.** `bna_admin` puede vaciar una bitácora con TRUNCATE (en PostgreSQL,
  un trigger lo impide incluso al dueño de la tabla).
- **G04.** Una cuenta con INSERT directo sobre los asientos (`bna_admin`)
  puede registrar un asiento descuadrado; `core.v_asientos_descuadrados` lo
  muestra.
- **G05.** DATETIME no guarda zona: la base no puede comprobar que una marca
  de tiempo que da la aplicación esté en UTC.

Además, como en `main`, una autorización AUTORIZADA que nunca se contabiliza
ni se extorna conserva para siempre su parte del tope diario y su retención
en el saldo disponible: ningún documento fija un plazo para liberarla.
