# CORE — API única de acceso a la base de datos `bna`

Módulo **CORE** del backend del Banco Nacional de Arequipa. Es el
único componente que toca la base de datos `bna` (esquema unificado en
`backend/Infraestructura - BD/Trabajo_hecho/BD/`). El resto del software
(incluido el futuro Bus de Servicios, RNF-22) consume estas acciones
como API única.

Fuente de requisitos: `Contexto_BNA/Acciones CORE.md` (21 acciones;
la billetera se omitió por no existir tablas en el modelo).

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
| CREAR_USUARIO | `POST /core/usuarios` | `usuariossvc` (SHA256) |
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
├── dependencies.py   # dependencia FastAPI de sesión SQLAlchemy
├── exceptions.py     # CoreError y subclases con code + status_code
├── models/           # SQLAlchemy 2.0 mapeados al esquema unificado bna
├── schemas/          # Pydantic v2 de entrada/salida
├── routers/          # FastAPI routers por dominio
├── services/         # lógica de negocio (única que toca la BD)
├── utils/            # ids (UUIDv7), money (Decimal), hashing (SHA256)
├── data/rbac.json    # catálogo de acciones y asignaciones rol→acciones
└── tests/            # pytest (sin BD; lógica pura + smoke de API)
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

## Ejecución local

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Variables relevantes (`.env`): `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`, `DB_NAME` (**ojo**: los scripts SQL crean la base
`bna`, mientras `.env.example` declara `bna_db` — alinear antes de
conectar a MySQL real).

## Autenticación

> 🚧 **Pendiente de implementación.** Hoy CORE no autentica peticiones:
> la función `autenticar()` existe en `services/usuariossvc.py` pero no
> está expuesta por ningún router, y el `actor` de la auditoría se
> recibe en el cuerpo de cada petición. Esta sección se completará
> cuando se integre el sistema JWT (Nicolas Ayerve / Nino Flores).

Contenido previsto:

- Endpoint `POST /core/auth/login` (credenciales inválidas → `401` con
  mensaje genérico).
- Formato del token JWT y expiración (`ACCESS_TOKEN_EXPIRE_MINUTES`,
  firma con `SECRET_KEY`).
- Uso del header `Authorization: Bearer <token>`.
- Dependencias `get_current_user` y `require_action(accion)` (valida
  contra el catálogo RBAC).
- El `actor` de trazabilidad se obtiene del token, nunca del body.
- Migración de hashes SHA256 a bcrypt en el primer login exitoso.

Ver `Documents/05-checklist-validacion.md` (secciones 1 y 2) y
`Documents/06-revision-arquitectura-schemas.md` (hallazgo H1).

## Pruebas

```bash
cd backend
python -m pytest CORE/tests -q
```

Cobertura actual: lógica de calendario francés, motor de reglas,
utilidades (UUIDv7, Decimal, SHA256), excepciones de negocio, catálogo
RBAC y smoke de montaje de la app (28 rutas `/core/*`). Las pruebas
end-to-end con MySQL quedan pendientes de un entorno con la BD `bna`
creada desde `Trabajo_hecho/BD/`.

## Pendientes conocidos

1. **`GESTIONAR_PERMISOS`** persiste en `data/rbac.json` porque el
   esquema `bna` no tiene tablas de permisos (el módulo
   `BNA_CONTROL_ACCESO` solo cubre comités). Migrar a tablas cuando el
   diccionario de datos las incorpore.
2. **Desembolso de crédito**: `aprobar_credito` marca la solicitud como
   APROBADA pero no genera automáticamente `cob_credito` + asiento de
   desembolso (RGN-12 completo) — requiere decisión de dónde vive el
   canal de desembolso (CORE vs módulo Desembolso).
3. **Discrepancia `DB_NAME`**: `.env.example` dice `bna_db`; los seeds
   crean `bna`. Revisar con el equipo de infraestructura.
4. Tests end-to-end con MySQL (Docker) sobre el esquema unificado.