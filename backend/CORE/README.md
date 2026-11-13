# CORE legado — API sobre la base de datos `bna`

API anterior del CORE del Banco Nacional de Arequipa, sobre la base `bna`
(esquema unificado en `backend/Infraestructura - BD/Trabajo_hecho/BD/`).

> **Estado:** ningún servicio del producto la llama. CUENTAS, TARJETAS y el frontend
> usan [COREDB](../COREDB/README.md), la API sobre la base integrada de
> `database/`. Este módulo se conserva porque tiene los créditos, que COREDB
> todavía no ofrece, y solo se levanta si se pide (ver "Ejecución").

Fuente de requisitos: `Acciones CORE.md`, documento del equipo que no está en
este repositorio (21 acciones; la billetera se omitió por no existir tablas
en el modelo).

## Acciones implementadas

| Acción | Endpoint | Servicio |
|---|---|---|
| VER_CLIENTE | `GET /core/clientes[/{id}]` | `clientessvc` |
| CREAR_CLIENTE | `POST /core/clientes` | `clientessvc` (RGN-05: duplicado devuelve existente) |
| MODIFICAR_CLIENTE | `PATCH /core/clientes/{id}` | `clientessvc` |
| VER_CUENTA | `GET /core/cuentas/{num}` | `cuentassvc` |
| CREAR_CUENTA | `POST /core/cuentas` | `cuentassvc` (titulares, RGN-16) |
| MODIFICAR_CUENTA | `PATCH /core/cuentas/{num}` | `cuentassvc` |
| REGISTRAR_MOVIMIENTO | `POST /core/movimientos` y `POST /core/movimientos/transferencias` | `movimientos` (RGN-01..09, RF-COR-11) |
| VER_TARJETA | `GET /core/tarjetas[/{id}]` | `tarjetassvc` (RNF-13: sin PAN) |
| CREAR_TARJETA | `POST /core/tarjetas` | `tarjetassvc` (tokenización) |
| BLOQUEAR_TARJETA | `POST /core/tarjetas/{id}/cambiar-estado` | `tarjetassvc` (historial) |
| CREAR_SOLICITUD_CREDITO | `POST /core/creditos/solicitudes` | `creditossvc` (RN-16, calendario francés) |
| EVALUAR_CREDITO | `POST /core/creditos/solicitudes/{id}/evaluar` | `creditossvc` (motor de reglas `eva_regla`) |
| APROBAR_CREDITO | `POST /core/creditos/solicitudes/{id}/decision` | `creditossvc` (RGN-12) |
| VER_CREDITO | `GET /core/creditos/solicitudes/{id}` | `creditossvc` |
| REGISTRAR_PAGO | `POST /core/creditos/pagos` | `creditossvc` (RGN-14: asiento por aplicación) |
| CONSULTAR_DEUDA | `GET /core/creditos/deuda` | `creditossvc` |
| CREAR_USUARIO | `POST /core/usuarios` | `usuariossvc` (bcrypt) |
| ASIGNAR_ROLES | `POST /core/usuarios/{id}/rol` | `usuariossvc` (ENUM de roles) |
| GESTIONAR_PERMISOS | `GET/POST /core/permisos*` | `rbac` (`data/rbac.json`) |
| VER_AUDITORIA | `GET /core/auditoria` | `reportessvc` (RF-COR-19, solo lectura) |
| GENERAR_REPORTES | `GET /core/reportes/*` | `reportessvc` (cuadre, asientos, movimientos, historial) |

Documentación interactiva: `GET /docs` (Swagger) una vez levantada la app.

## Estructura

```
backend/CORE/
├── api.py            # montaje del router /core + handler de CoreError
├── config.py         # Settings (pydantic-settings, variables DB_*)
├── database.py       # engine, session factory, Base
├── dependencies.py   # dependencias FastAPI: sesión SQLAlchemy y JWT
├── exceptions.py     # CoreError y subclases con code + status_code
├── models/           # SQLAlchemy 2.0 mapeados al esquema unificado bna
├── schemas/          # Pydantic v2 de entrada/salida
├── routers/          # FastAPI routers por dominio
├── services/         # lógica de negocio (única que toca la BD)
├── utils/            # ids (UUIDv7), money (Decimal), hashing (bcrypt), tokens (JWT)
├── data/rbac.json    # catálogo de acciones y asignaciones rol→acciones
└── tests/            # pytest (lógica, API, SQLite en memoria e integración con MySQL)
```

## Reglas de negocio aplicadas

- **RGN-01/RF-COR-06**: todo movimiento genera asiento de partida doble
  cuadrado (`contabilidad.crear_asiento` rechaza asientos descuadrados).
- **RGN-03/RF-COR-07**: débito mayor que saldo disponible → rechazo
  (`InsufficientFundsError`).
- **RGN-04/RF-COR-08**: tope diario por cuenta+canal
  (`limite_canal` + `cta_control_tope_diario`).
- **RGN-05**: documento duplicado devuelve el cliente existente.
- **RGN-06/RF-COR-11**: idempotencia por `idempotency_key`; en
  transferencias la contraparte lleva el sufijo `#C`.
- **RGN-09**: cuentas bloqueadas no originan débitos.
- **RGN-10/RF-COR-14**: conversión con tipo de cambio vigente.
- **RGN-12**: solo solicitud APROBADA genera crédito desembolsable.
- **RGN-14**: cada aplicación de pago genera su propio asiento
  (mora → interés → seguro → capital).
- **RNF-13**: el PAN jamás se almacena; solo token, BIN y últimos 4.
- **RNF-29**: errores con `code` + `status_code` en respuesta JSON.

## Ejecución

Con el producto, desde la raíz del repositorio:

```bash
COMPOSE_PROFILES=legado ./bna up     # queda en http://127.0.0.1:8000/docs
```

Usa el esquema `bna` del servicio `db-aux`, que se carga desde
`99_bna_unificado.sql`. Ese script trae cinco usuarios de ejemplo, uno por rol,
con sus contraseñas a la vista en el propio archivo (tabla `usuario_sistema`):
sirven para probar en local y nada más.

Solo el módulo, con Python 3.11 y un MySQL que ya tenga la base `bna`:

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # valor para SECRET_KEY
uvicorn main:app --reload
```

Variables relevantes (`backend/.env`, que no se versiona): `DB_HOST`,
`DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (`bna`, la base que crean los
scripts SQL) y `SECRET_KEY`. Sin una `SECRET_KEY` propia de al menos 32
caracteres el backend no arranca, y el error indica qué hacer. No reutilizar
ningún valor del antiguo `backend/.env` que estuvo versionado: están
comprometidos.

## Autenticación

`POST /core/auth/login` emite un JWT, y `usuario_actual` y
`requiere_permiso(accion)` (`dependencies.py`) lo validan contra el catálogo
RBAC. Todas las rutas salvo el login lo exigen; la tabla de permisos por ruta
y la configuración están en
[`AUTH_JWT.md`](AUTH_JWT.md); el hash de contraseñas y la migración de SHA-256
a bcrypt, en [`AUTENTICACION.md`](AUTENTICACION.md).

## Pruebas

```bash
cd backend
python -m pytest CORE/tests -q
```

Sin Python 3.11 en la máquina, `./bna test` desde la raíz corre esta suite en
un contenedor, junto con las demás.

Cobertura actual: lógica de calendario francés, motor de reglas y flujo
de créditos, concurrencia de movimientos, autenticación y JWT, token y
permiso en cada ruta (`test_rutas_protegidas.py`), configuración, utilidades
(UUIDv7, Decimal, hashing), excepciones de negocio, catálogo RBAC y smoke de
montaje de la app.
`CORE/tests/integracion/` corre contra un MySQL real con el esquema `bna`:
`test_real_mysql.py` (autenticación) y `test_creditos_mysql.py` (ciclo de
crédito por HTTP: ENUM y NOT NULL que SQLite no aplica, issue #19). Se omiten
salvo que `BNA_INTEGRACION_MYSQL=1`. `CORE/scripts/pruebas_integracion.sh`
levanta solo `db-aux` en un proyecto propio con claves nuevas, las corre en la
imagen `bna/backend:local` y lo elimina todo al terminar; `./bna test` lo
ejecuta como suite "CORE legado contra MySQL".

## Pendientes conocidos

1. **`GESTIONAR_PERMISOS`** persiste en `data/rbac.json` porque el
   esquema `bna` no tiene tablas de permisos. Migrar a tablas cuando el
   diccionario de datos las incorpore.
2. **Desembolso de crédito**: `aprobar_credito` marca la solicitud como
   APROBADA pero no genera automáticamente `cob_credito` + asiento de
   desembolso (RGN-12 completo) — requiere decisión de dónde vive el
   canal de desembolso (CORE vs módulo Desembolso).
3. Tests end-to-end con MySQL (Docker) sobre el esquema unificado, fuera
   de autenticación y créditos: `CORE/tests/integracion/` solo cubre esos
   dos flujos.