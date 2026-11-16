# COREDB: API de la base integrada

API FastAPI sobre la base integrada de `database/`. Es la API del CORE que usa el producto:
CUENTAS, TARJETAS y el frontend la llaman, y ningún otro servicio se conecta a esa base. El CORE
legado (`backend/CORE`) es otra API, sobre otra base, y sigue aparte.

> **Exige un JWT propio en toda ruta salvo `/coredb/salud` y el login.** No tiene TLS:
> no exponer fuera de la máquina sin un proxy con TLS delante.

## Clonar y levantar

Con todo el producto, desde la raíz del repositorio: `./bna up` (COREDB queda en
http://127.0.0.1:8012/docs y el administrador es `admin`, con la contraseña de
`BNA_ADMIN_PASSWORD` en `.env`).

Solo la base y esta API, con Python 3.11, desde la raíz del repositorio:

```bash
cp backend/COREDB/.env.example backend/COREDB/.env      # completar las claves y CORE_DB_JWT_CLAVE
docker compose -f docker-compose.coredb.yml -f docker-compose.coredb.dev.yml \
  --env-file backend/COREDB/.env up -d --wait
pip install -r backend/requirements-coredb.txt
cd backend
python -m COREDB.scripts.crear_administrador --username admin --nombre "Su nombre"   # una vez
uvicorn COREDB.main:app --host 127.0.0.1 --port 8012
```

El arranque falla si `CORE_DB_JWT_CLAVE` tiene menos de 32 caracteres o es el valor de
ejemplo (`openssl rand -hex 32`). Es otra clave que el `SECRET_KEY` de CORE.

## Autenticación

Portada del JWT de CORE (Nicolas Ayerve) y de `autenticar()` (Nino Flores), sobre la base
integrada y con PyJWT:

- `POST /coredb/auth/login` con `{"username", "password"}` entrega
  `{access_token, token_type, expires_in, usuario}`. Usuario inexistente, clave incorrecta,
  usuario inactivo y contraseña no admitida responden el mismo 401
  `CREDENCIALES_INVALIDAS`, y el tiempo se iguala con una verificación bcrypt simulada.
  Cada login exitoso queda en la bitácora (`LOGIN`), con el `X-Correlation-ID` si es un
  UUID. Los intentos fallidos no se registran ni bloquean la cuenta, como en CORE.
- Las demás rutas exigen `Authorization: Bearer <token>`. El token lleva `sub`,
  `username`, `rol`, `modulo`, `type`, `iss` (`bna-coredb`), `aud` (`coredb`), `iat`, `exp`
  y `jti`, todos obligatorios. El algoritmo lo fija el servidor (`CORE_DB_JWT_ALGORITMO`,
  HS256 por omisión). El usuario se relee en cada petición: desactivarlo o cambiarle el
  rol surte efecto de inmediato. Un token de CORE no sirve aquí.
- `GET /coredb/auth/me` devuelve el perfil y sus acciones.
- Errores: 401 `TOKEN_REQUERIDO | TOKEN_INVALIDO | TOKEN_EXPIRADO | USUARIO_NO_VIGENTE |
  CREDENCIALES_INVALIDAS`, con `WWW-Authenticate: Bearer`; 403 `PERMISO_DENEGADO`.

**Permisos:** `permisos.py` es un mapa versionado de rol a acciones. Los cinco roles de
personas son los de `CORE/data/rbac.json` en `a9bd70f`, y la API nunca lo escribe. La
acción propia `VALIDAR_IDENTIDAD` la tienen ASESOR, OPERADOR (verifica el documento antes de
un desembolso) y el usuario de servicio de Clientes;
`DESEMBOLSAR_CREDITO` (OPERADOR, ADMINISTRADOR) y `REGISTRAR_MORA` (ADMINISTRADOR) son las
propias de créditos. Hay usuarios de servicio para CLIENTES, EVALUACION, DESEMBOLSO y COBRANZA.
Cada ruta declara su permiso con `requiere_permiso`; una prueba falla si una escritura no
lo declara o si una ruta, salvo las públicas, no exige token.

**Usuarios de servicio:** un módulo se autentica con su propio usuario (rol `SERVICIO` y
su módulo), nunca con una cuenta de persona:

1. Un administrador lo crea con `POST /coredb/usuarios/servicios`
   `{"modulo": "CLIENTES", "username": "svc-clientes", "nombre": "Módulo Clientes"}`. La
   respuesta trae el secreto **una sola vez** (`Cache-Control: no-store`); la base guarda su
   hash bcrypt.
2. Quien despliega el módulo guarda el usuario y el secreto en su almacén de secretos.
3. El módulo inicia sesión con ellos y repite el login ante un 401 `TOKEN_EXPIRADO`.
4. `POST /coredb/usuarios/{id}/credencial` entrega un secreto nuevo y anula el anterior;
   `POST /coredb/usuarios/{id}/estado {"activo": false}` corta el acceso en la siguiente
   petición.

**Primer administrador:** `python -m COREDB.scripts.crear_administrador` lo crea con las
credenciales de la base y pide la contraseña en la terminal. Se niega si ya hay un
administrador activo. Con `--si-falta` eso no es un error: así lo usa el arranque del
producto (`compose.yaml`), que toma la contraseña de `CORE_DB_ADMIN_INICIAL_PASSWORD`.

**Pendiente:** ningún límite de intentos de login ni de frecuencia.

## Clientes

Las rutas que usa el módulo Clientes, y el personal, están descritas en
[`CONTRATO_CLIENTES.md`](CONTRATO_CLIENTES.md):

| Ruta | Permiso |
|---|---|
| `POST /coredb/clientes` | `CREAR_CLIENTE` |
| `POST /coredb/clientes/validaciones/documento` | `VALIDAR_IDENTIDAD` |
| `POST /coredb/clientes/{cod_cliente}/validaciones` | `VALIDAR_IDENTIDAD` |
| `GET /coredb/clientes/{cod_cliente}` | `VER_CLIENTE` |
| `POST /coredb/clientes/{cod_cliente}/estado` | `MODIFICAR_CLIENTE` |
| `GET /coredb/catalogos/clientes` | autenticado |

- El usuario de la API no lee `clientes.*`: el cliente llega como JSON de un
  procedimiento, sin datos biométricos.
- **Quién registra (punto R-01, por confirmar con el equipo):** solo el usuario de
  servicio del módulo Clientes registra un cliente `HABILITADO`; los demás registran
  `OBSERVADO`. La regla está en `permisos.puede_registrar_habilitado`.
- La baja es final y la fija una persona, no un usuario de servicio.
- Ningún mensaje de error repite el documento, el correo ni el celular.
- `X-Correlation-ID` es opcional; vuelve siempre en la respuesta y queda en la bitácora.
- No hay rutas para listar clientes ni para buscarlos por nombre, correo o celular.

El segundo archivo carga datos solo de desarrollo; ver `database/README-UPSTREAM.md`.

## Autorizaciones y credenciales de tarjeta

Desde `bd-v1.5-mysql`, por los procedimientos de la base; las reglas las aplica la base.

| Ruta | Permiso | Qué hace |
|---|---|---|
| `POST /coredb/autorizaciones` | `REGISTRAR_MOVIMIENTO` | Autoriza una operación con tarjeta o registra su rechazo |
| `GET /coredb/autorizaciones/{uuid_autorizacion}` | `VER_TARJETA` | Una autorización |
| `POST /coredb/autorizaciones/{uuid_autorizacion}/extorno` | `REGISTRAR_MOVIMIENTO` | Extorna una autorización sin movimiento |
| `PUT /coredb/tarjetas/{id_tarjeta}/credenciales/{tipo}` | `CREAR_TARJETA` | Asigna o cambia el `PIN_ATM` o la `CLAVE_WEB` |
| `POST /coredb/tarjetas/{id_tarjeta}/credenciales/{tipo}/validacion` | `REGISTRAR_MOVIMIENTO` | Valida el PIN o la clave web |

- El `uuid_autorizacion` lo genera quien llama. Repetirlo con los mismos datos devuelve la
  autorización ya registrada sin volver a retener el saldo; con otros datos, 409
  `BNA-IDEMPOTENCIA`.
- Una regla que no se cumple responde 201 con la autorización `RECHAZADA` y su código ISO
  8583 (`51` sin fondos, `54` vencida, `57` no permitida, `61` excede el tope, `62`
  restringida). El motivo no trae montos ni saldos. Se indica el canal o la terminal, uno
  de los dos.
- El extorno libera el saldo retenido y el tope del día. Repetirlo responde lo mismo; una
  autorización rechazada o ya contabilizada responde 409 `BNA-EXTORNO`.
- Un PIN equivocado responde 200 con `FALLIDO` y los intentos que quedan; el tercero
  seguido bloquea la tarjeta. Con la tarjeta no operativa responde 422 `ERR-TAR-003` sin
  registrar el intento. El valor no se devuelve, no se registra y no aparece en los errores.

## Créditos

Sobre `creditos.*` (`bd-v1.4-mysql`), descritas en [`CONTRATO_CREDITOS.md`](CONTRATO_CREDITOS.md).
Por ahora, las áreas de evaluación y desembolso; cobranza viene en el PR siguiente.

| Ruta | Permiso |
|---|---|
| `POST /coredb/creditos/solicitudes` (expediente de SOL, CR-INT-02) | `CREAR_SOLICITUD_CREDITO` |
| `GET /coredb/creditos/solicitudes`, `GET /coredb/creditos/solicitudes/{id}` | `VER_CREDITO` |
| `POST /coredb/creditos/solicitudes/{id}/evaluaciones` (RN-EVA-002-P) | `EVALUAR_CREDITO` |
| `POST /coredb/creditos/evaluaciones/{id}/decision` | `APROBAR_CREDITO` |
| `POST /coredb/creditos/solicitudes/{id}/revocacion` | `APROBAR_CREDITO` |
| `GET /coredb/creditos/aprobaciones` | `VER_CREDITO` |
| `POST /coredb/creditos/analistas` | `CREAR_USUARIO` |
| `GET /coredb/catalogos/creditos` | autenticado |
| `POST /coredb/creditos/ordenes` (con `X-Idempotency-Key`) | `DESEMBOLSAR_CREDITO` |
| `PUT …/ordenes/{id}/cuenta`, `POST …/ordenes/{id}/validaciones`, `POST …/ordenes/{id}/confirmacion`, `POST …/ordenes/{id}/rechazo` | `DESEMBOLSAR_CREDITO` |
| `GET /coredb/creditos/ordenes`, `GET /coredb/creditos/ordenes/{id}` | `VER_CREDITO` |
| `GET /coredb/creditos/conciliacion/desembolsos` | `GENERAR_REPORTES` |

- Campos en camelCase, como el contrato con SOL.
- La fórmula de RN-EVA-002-P es la del módulo EVALUACIÓN (#70), en
  `services/regla_evaluacion.py`; los umbrales 80 % / 100 % salen de
  `creditos.regla_evaluacion`, y la base elige la regla.
- El expediente es idempotente por id, versión y contenido; la evaluación y la decisión se
  hacen una vez.
- Para decidir, el usuario del analista debe estar ligado a un empleado de `core.empleado`
  registrado como analista. COREDB no crea empleados: los carga el administrador de la base.
- Confirmar un desembolso abona la cuenta, crea el crédito con su calendario OFICIAL y deja la
  solicitud DESEMBOLSADA en una sola transacción de la base. Repetir la confirmación devuelve el
  mismo crédito y el mismo abono, sin abonar otra vez.
- La evidencia IDENTIDAD de una orden es el `id_validacion` de
  `POST /coredb/clientes/validaciones/documento`, aprobado el mismo día (fecha de Lima).
- El usuario de la API no lee tablas de `creditos`: lee las vistas `v_*_api`.
- Las rutas de crédito del CORE legado (perfil `legado`) siguen aparte.

## Consultas

| Ruta | Permiso | Qué devuelve |
|---|---|---|
| `GET /coredb/movimientos/cuenta/{num_cuenta}` | `VER_CUENTA` | Los movimientos de una cuenta, del más reciente al más antiguo (`limite`, `antes_de`) |
| `GET /coredb/movimientos/{uuid_transaccion}` | `VER_CUENTA` | Un movimiento |
| `GET /coredb/cuentas?cod_cliente=` | `VER_CUENTA` | Las cuentas en las que el cliente es titular |
| `GET /coredb/tarjetas?cod_cliente=` | `VER_TARJETA` | Las tarjetas del cliente, de la más reciente a la más antigua |
| `GET /coredb/auditoria` | `VER_AUDITORIA` | La bitácora, del evento más reciente al más antiguo, con filtros |

- Un movimiento trae `naturaleza` (`D` débito, `C` crédito) y la moneda de su cuenta, y
  no trae el asiento contable. Una transferencia se lee como `TRANSFERENCIA_ENVIADA` en
  la cuenta de origen y `TRANSFERENCIA_RECIBIDA` en la de destino.
- Toda cuenta incluye `titulares`, los códigos de sus clientes titulares.
- No hay una ruta que liste todas las cuentas, todas las tarjetas ni todos los clientes.
- Se leen por las vistas de `bd-v1.2-mysql`; el usuario de la API no lee
  `cuentas.movimiento` ni `core.evento_auditoria`.

Documentación interactiva: `http://127.0.0.1:8012/docs`. Especificación publicada:
`openapi.json`, que se regenera desde `backend/` con
`python -m COREDB.scripts.exporta_openapi`.

## Reglas

- **Conexión:** `bna_app_user`, con el rol `bna_api`: ejecuta procedimientos y lee solo las
  tablas que usa; un endpoint que lea otra necesita su `GRANT` en la base. La tarjeta se lee
  por `tarjetas.v_tarjeta_api`, sin `pan_token`. No lee credenciales ni datos biométricos.
  En UTC y modo estricto. El arranque falla si `core.verificar_configuracion()` no pasa.
- **Desbloqueo de tarjetas:** no disponible, pendiente de un cliente de Seguridad. La API
  responde 403 `BNA-DESBLOQUEO`, porque solo el rol `bna_seguridad` puede desbloquear.
- **Emisión de tarjetas:** `POST /coredb/tarjetas` acepta un `id_tarjeta` opcional. Con un id
  que ya existe responde 409 `REGISTRO_DUPLICADO` y no emite otra tarjeta; el módulo TARJETAS
  lo deriva de su `X-Idempotency-Key` para repetir una emisión sin duplicarla. Cada tarjeta se
  devuelve con `num_cuenta`, su cuenta principal (la de la emisión), para que TARJETAS compruebe
  que una repetición es sobre la misma cuenta.
- **Actor:** sale del token. Una cabecera `X-Actor` se ignora.
- **Origen de un cambio de estado de tarjeta:** no lo envía el cliente; sale del token:
  `OPERADOR` para personas, `MODULO_CLIENTES` para el usuario de servicio de Clientes y
  `SISTEMA` para otro módulo. Un cuerpo con `origen` se rechaza con 422.
- **Canal:** lo envía el cliente, y debe tener fila en
  `core.limite_canal` para debitar (ver `database/README.md`): por `AGE`, y por `HB` en USD,
  un débito se rechaza con `BNA-CANAL`; por `BD` en USD, con `RN-BD-002`.
- **Periodos:** sin un periodo contable para la fecha de negocio, todo movimiento se
  rechaza y esta API no puede crearlo. `docker-compose.coredb.dev.yml` carga el del mes
  en curso; en otro entorno lo carga `bna_admin`.
- **Escrituras:** siempre con `CALL` a un procedimiento (`database.llamar`). Una prueba
  rechaza `INSERT`, `UPDATE` o `DELETE` en este paquete.
- **Identificadores:** `BINARY(16)` en la base y `uuid.UUID` en Python (`UuidBinario`).
- **Cambios en la base:** primero en bna-core-db, nunca en `database/` (ver
  `database/README-UPSTREAM.md`).

## Pruebas

```bash
cd backend/COREDB && python -m pytest -q         # unitarias; integración omitida
backend/COREDB/scripts/pruebas_integracion.sh    # contra un contenedor nuevo
```

Sin Python 3.11 en la máquina, `./bna test` desde la raíz corre las dos suites en
contenedores (el script acepta `COREDB_IMAGEN_PRUEBAS=<imagen>` para eso).
