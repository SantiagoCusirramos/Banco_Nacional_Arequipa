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
`tarjetas.v_tarjeta_api`, sin `pan_token`; no lee credenciales de tarjeta ni datos
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

`pruebas/mysql/run_tests.sh` ejecuta toda la suite con la extensión cargada. Sus
pruebas (ID `X`) quedan en `resultados/mysql/resultado-extension.tsv`, fuera de la
matriz. `pruebas_sin_transaccion.sh` prueba cada procedimiento en autocommit, porque
el arnés siempre abre una transacción.

`sql/bna_datos_dev.sql` es **solo para desarrollo**: periodo abierto del mes en curso,
BIN 004499, una agencia, un terminal por canal y un cliente, para que una base nueva
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
