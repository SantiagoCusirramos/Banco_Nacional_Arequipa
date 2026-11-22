# COREDB: API de la base integrada

API FastAPI sobre la base integrada de `database/`. Es la API del CORE que usa el producto:
la llaman el frontend, CUENTAS, TARJETAS, CAPTACION, EVALUACIÓN, DESEMBOLSO, COBRANZA,
BILLETERA y Seguridad, todos a través del Bus de Servicios (`/bus/coredb`), y ningún otro servicio se conecta
a esa base.

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
  usuario inactivo, login bloqueado y contraseña no admitida responden el mismo 401
  `CREDENCIALES_INVALIDAS`, y el tiempo se iguala con una verificación bcrypt simulada.
  Cada login exitoso queda en la bitácora (`LOGIN`), con el `X-Correlation-ID` si es un
  UUID, y cada fallo de un usuario que existe como `LOGIN_FALLIDO`.
- **Bloqueo (bd-v1.12):** 5 fallos seguidos bloquean el login de una persona 15 minutos
  (`BLOQUEAR_LOGIN`); con el login bloqueado ni la contraseña correcta entra. Un login
  exitoso reinicia la cuenta. Los usuarios de servicio no se bloquean (su secreto es
  aleatorio; bloquearlos dejaría a un módulo sin acceso a pedido de cualquiera).
  `GET /coredb/usuarios/{id}` muestra `bloqueado_hasta` y
  `POST /coredb/usuarios/{id}/desbloqueo` (`CREAR_USUARIO`) lo levanta antes. Los números
  son una decisión del equipo, revisable ([`Documents/decisiones-del-equipo.md`](../../Documents/decisiones-del-equipo.md)).
- Las demás rutas exigen `Authorization: Bearer <token>`. El token lleva `sub`,
  `username`, `rol`, `modulo`, `type`, `iss` (`bna-coredb`), `aud` (`coredb`), `iat`, `exp`
  y `jti`, todos obligatorios. El algoritmo lo fija el servidor (`CORE_DB_JWT_ALGORITMO`,
  HS256 por omisión). El usuario se relee en cada petición: desactivarlo o cambiarle el
  rol surte efecto de inmediato. Un token de CORE no sirve aquí.
- `GET /coredb/auth/me` devuelve el perfil y sus acciones.
- Errores: 401 `TOKEN_REQUERIDO | TOKEN_INVALIDO | TOKEN_EXPIRADO | USUARIO_NO_VIGENTE |
  CREDENCIALES_INVALIDAS`, con `WWW-Authenticate: Bearer`; 403 `PERMISO_DENEGADO`.

**Permisos:** `permisos.py` es un mapa versionado de rol a acciones. Los cinco roles de
personas son los de `CORE/data/rbac.json` del CORE legado en `a9bd70f` (eliminado en #125), y la API nunca lo escribe. La
acción propia `VALIDAR_IDENTIDAD` la tienen ASESOR, OPERADOR (verifica el documento antes de
un desembolso) y el usuario de servicio de Clientes;
`DESEMBOLSAR_CREDITO` (OPERADOR, ADMINISTRADOR) y `REGISTRAR_MORA` (ADMINISTRADOR y el servicio de Cobranza) son las
propias de créditos. `REGISTRAR_EMPLEADO` (solo ADMINISTRADOR) registra empleados con
`POST /coredb/empleados` y los liga a su usuario: así un analista queda disponible sin el
administrador de la base. Hay usuarios de servicio para CLIENTES (en el producto, `svc-captacion`
de CAPTACION), EVALUACION, DESEMBOLSO, COBRANZA y BILLETERA.
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

En el producto, los seis usuarios de servicio (`svc-evaluacion`, `svc-desembolso`,
`svc-captacion`, `svc-cobranza`, `svc-billetera` y `svc-seguridad`) no se crean por la API sino en el arranque
(`coredb-init` en compose, contenedores de inicio de `coredb` en Kubernetes). Por ejemplo,
`CORE_DB_SERVICIO_SECRETO=<secreto> python -m COREDB.scripts.crear_servicio --modulo
EVALUACION --username svc-evaluacion --nombre Evaluación` lo crea con el secreto que el despliegue
ya tiene (`EVALUACION_COREDB_SECRETO` en `.env` o en el Secret de Kubernetes). Repetirlo no cambia
nada; con otro secreto, reemplaza el anterior. No toca a una persona con ese nombre.

**Primer administrador:** `python -m COREDB.scripts.crear_administrador` lo crea con las
credenciales de la base y pide la contraseña en la terminal. Se niega si ya hay un
administrador activo. Con `--si-falta` eso no es un error: así lo usa el arranque del
producto (`compose.yaml`), que toma la contraseña de `CORE_DB_ADMIN_INICIAL_PASSWORD`.

**Pendiente:** el bloqueo por intentos (arriba) es el único límite: no hay límite de frecuencia por
dirección ni por usuario.

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
- **Quién registra (punto R-01, decisión del equipo revisable, [`Documents/decisiones-del-equipo.md`](../../Documents/decisiones-del-equipo.md)):** solo el usuario de
  servicio del módulo Clientes registra un cliente `HABILITADO`; los demás registran
  `OBSERVADO`. La regla está en `permisos.puede_registrar_habilitado`.
- La baja es final y la fija una persona, no un usuario de servicio.
- Ningún mensaje de error repite el documento, el correo ni el celular.
- `X-Correlation-ID` es opcional; vuelve siempre en la respuesta y queda en la bitácora.
- No hay rutas para listar clientes ni para buscarlos por nombre, correo o celular.

El segundo archivo carga datos solo de desarrollo; ver `database/README-UPSTREAM.md`.

## Captación

El expediente del **prospecto** antes de ser cliente, en las tablas de extensión
`clientes.*_captacion` (desde `bd-v1.7-mysql`). Lo usa el módulo CAPTACION: con el token
del asesor para lo que hace una persona y con su usuario de servicio (módulo CLIENTES) para
ligar el cliente que registró y leer las referencias que consulta SOL.

| Ruta | Permiso |
|---|---|
| `POST /coredb/captacion/solicitantes` (201; 200 con `duplicado` si el documento ya estaba) | `CREAR_CLIENTE` |
| `POST /coredb/captacion/solicitantes/busqueda` (cuerpo: `documento`, `texto`, `con_cliente`, `limite`), `GET …/solicitantes/{id}` | `VER_CLIENTE` |
| `POST /coredb/captacion/casos`, `GET /coredb/captacion/casos` (`estado`, `id_solicitante`, `cod_cliente`) | `CREAR_CLIENTE` / `VER_CLIENTE` |
| `GET /coredb/captacion/casos/{id_caso}`: el expediente con `faltantes` y `listo_para_habilitar` | `VER_CLIENTE` |
| `POST …/casos/{id_caso}/consentimientos`, `/validaciones`, `/consultas-riesgo`, `/perfil`, `/estado` | `CREAR_CLIENTE` |
| `POST …/casos/{id_caso}/otps`, `POST …/otps/{id_otp}/verificacion` | `CREAR_CLIENTE` |
| `POST …/casos/{id_caso}/cliente` (ligar el cliente), `POST …/casos/{id_caso}/habilitacion` | `CREAR_CLIENTE` |

- La base aplica las reglas del expediente y recalcula el estado (INICIADO →
  EN_VALIDACION → APROBADO → HABILITADO; OBSERVADO; RECHAZADO y REVOCADO finales). Cada
  escritura devuelve el expediente completo.
- El OTP: CAPTACION genera el código, calcula su HMAC con su clave y el `id_otp`, y manda
  solo el HMAC; la base lo compara, cuenta los intentos y lo vence según
  `clientes.tipo_contacto`. Ninguna respuesta incluye el hash.
- El cliente `HABILITADO` lo sigue registrando solo el usuario de servicio de CLIENTES con
  `POST /coredb/clientes` (punto R-01); `…/cliente` solo liga al caso APROBADO un cliente
  ACTIVO con el documento del solicitante. Habilitar deja en el cliente las verificaciones
  de celular y correo hechas por OTP.
- Códigos: `DOCUMENTO_INVALIDO`, `SOLICITANTE_NO_ENCONTRADO`, `CASO_NO_ENCONTRADO`,
  `CASO_ABIERTO`, `CASO_CERRADO`, `ESTADO_INVALIDO`, `CASO_NO_LISTO`,
  `CASO_CON_OTRO_CLIENTE`, `AGENCIA_NO_ENCONTRADA`, `CONSENTIMIENTO_REQUERIDO`,
  `OTP_NO_ENCONTRADO`, `SIN_CONSULTA`, `CLIENTE_NO_ENCONTRADO`, `CLIENTE_NO_COINCIDE`,
  `CLIENTE_NO_ACTIVO`, `DATOS_INVALIDOS`. Ningún mensaje repite el documento ni los
  contactos.

## Autorizaciones y credenciales de tarjeta

Desde `bd-v1.5-mysql`, por los procedimientos de la base; las reglas las aplica la base.

| Ruta | Permiso | Qué hace |
|---|---|---|
| `POST /coredb/autorizaciones` | `REGISTRAR_MOVIMIENTO` | Autoriza una operación con tarjeta o registra su rechazo |
| `GET /coredb/autorizaciones/{uuid_autorizacion}` | `VER_TARJETA` | Una autorización |
| `POST /coredb/autorizaciones/{uuid_autorizacion}/extorno` | `REGISTRAR_MOVIMIENTO` | Extorna una autorización sin movimiento |
| `POST /coredb/autorizaciones/{uuid_autorizacion}/confirmacion` | `REGISTRAR_MOVIMIENTO` | Confirma una autorización retenida: registra el movimiento real |
| `POST /coredb/autorizaciones/liberaciones` | `REGISTRAR_MOVIMIENTO` | Libera las retenciones vencidas (`{"minutos": 1..1440}`, sin él el plazo de la base, 15 por omisión; decisión 11 de `Documents/decisiones-del-equipo.md`). La base ya lo hace cada minuto; una retención vencida no se confirma (`BNA-CONFIRMACION`) |
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
- **La confirmación** convierte una autorización `AUTORIZADA` o `DISPENSADA` sin movimiento
  en el débito real: registra el movimiento con el mismo `uuid_autorizacion`, pasa la
  autorización a `DISPENSADA` y libera la retención (el saldo contable ya bajó). Exige
  `X-Idempotency-Key` y su huella SHA-256 hex (64 caracteres). Repetir con la misma llave
  devuelve el mismo resultado sin segundo débito; repetir con otra llave falla (ya no está
  en estado vigente). El canal o terminal deben coincidir con la autorización. Una
  autorización extornada o rechazada responde 409 `BNA-CONFIRMACION`.
- Un PIN equivocado responde 200 con `FALLIDO` y los intentos que quedan; el tercero
  seguido bloquea la tarjeta. Con la tarjeta no operativa responde 422 `ERR-TAR-003` sin
  registrar el intento. El valor no se devuelve, no se registra y no aparece en los errores.

## Créditos

Sobre `creditos.*` (`bd-v1.4-mysql`), descritas en [`CONTRATO_CREDITOS.md`](CONTRATO_CREDITOS.md).
Las tres áreas: evaluación, desembolso y cobranza.

| Ruta | Permiso |
|---|---|
| `POST /coredb/creditos/solicitudes` (expediente de SOL, CR-INT-02) | `CREAR_SOLICITUD_CREDITO` |
| `GET /coredb/creditos/solicitudes`, `GET /coredb/creditos/solicitudes/{id}`, `GET /coredb/creditos/solicitudes/conteo` | `VER_CREDITO` |
| `POST /coredb/creditos/borradores`, `PUT /coredb/creditos/borradores/{id}` (borrador de SOL, `bd-v1.14-mysql`) | `CREAR_SOLICITUD_CREDITO` |
| `POST /coredb/creditos/solicitudes/{id}/evaluaciones` (RN-EVA-002-P) | `EVALUAR_CREDITO` |
| `POST /coredb/creditos/evaluaciones/{id}/decision` | `APROBAR_CREDITO` |
| `POST /coredb/creditos/solicitudes/{id}/revocacion` | `APROBAR_CREDITO` |
| `GET /coredb/creditos/aprobaciones` | `VER_CREDITO` |
| `POST /coredb/creditos/analistas` | `CREAR_USUARIO` |
| `POST /coredb/empleados` (el empleado y su usuario; antes de `…/analistas`) | `REGISTRAR_EMPLEADO` |
| `GET /coredb/catalogos/creditos` | autenticado |
| `POST /coredb/creditos/ordenes` (con `X-Idempotency-Key`) | `DESEMBOLSAR_CREDITO` |
| `PUT …/ordenes/{id}/cuenta`, `POST …/ordenes/{id}/validaciones`, `POST …/ordenes/{id}/confirmacion`, `POST …/ordenes/{id}/rechazo` | `DESEMBOLSAR_CREDITO` |
| `GET /coredb/creditos/ordenes`, `GET /coredb/creditos/ordenes/{id}` | `VER_CREDITO` |
| `GET /coredb/creditos/conciliacion/desembolsos` | `GENERAR_REPORTES` |
| `GET /coredb/creditos`, `GET /coredb/creditos/{codCredito}`, `GET …/{codCredito}/pagos`, `GET /coredb/creditos/pagos/{referencia}` | `CONSULTAR_DEUDA` |
| `POST /coredb/creditos/{codCredito}/pagos` (la `referencia` es la llave) | `REGISTRAR_PAGO` |
| `POST …/{codCredito}/cuotas/{n}/mora`, `POST /coredb/creditos/vencimientos` | `REGISTRAR_MORA` |
| `GET …/{codCredito}/cuotas/{n}/mora` | `CONSULTAR_DEUDA` |
| `GET /coredb/creditos/conciliacion/pagos` | `GENERAR_REPORTES` |

- Campos en camelCase, como el contrato con SOL.
- La fórmula de RN-EVA-002-P es la del módulo EVALUACIÓN (#70), en
  `services/regla_evaluacion.py`; los umbrales 80 % / 100 % salen de
  `creditos.regla_evaluacion`, y la base elige la regla.
- El expediente es idempotente por id, versión y contenido; la evaluación y la decisión se
  hacen una vez.
- Para decidir, el usuario del analista debe estar ligado a un empleado de `core.empleado`
  registrado como analista (`POST /coredb/empleados` y `POST /coredb/creditos/analistas`).
- Confirmar un desembolso abona la cuenta, crea el crédito con su calendario OFICIAL y deja la
  solicitud DESEMBOLSADA en una sola transacción de la base. Repetir la confirmación devuelve el
  mismo crédito y el mismo abono, sin abonar otra vez.
- La evidencia IDENTIDAD de una orden es el `id_validacion` de
  `POST /coredb/clientes/validaciones/documento`, aprobado el mismo día (fecha de Lima).
- Pagar una cuota debita la cuenta del titular y aplica el pago a las cuotas en una sola
  transacción. Sin fondos o con la cuenta bloqueada, el pago queda RECHAZADO con su motivo y
  sin mover dinero. Repetir la referencia devuelve el mismo pago.
- `POST /coredb/creditos/vencimientos` es la tarea diaria de `svc-cobranza` (la base también la
  corre a las 00:10 de Lima). La mora se registra y se muestra, pero no se cobra.
- El borrador de SOL es una solicitud `REGISTRADA` con sus garantías y fiadores; lo guarda el
  asesor con su token, que SOL reenvía. Editar exige la revisión vigente (409
  `REVISION_DESACTUALIZADA`). La bandeja sin `estado` no muestra borradores. Ver
  `CONTRATO_CREDITOS.md` §8.
- El usuario de la API no lee tablas de `creditos`: lee las vistas `v_*_api`.

## Billetera Digital

Sobre los procedimientos `billetera.*` de `bd-v1.9-mysql` (`bd-v1.10-mysql` lee con bloqueo la
operación repetida). La usa el módulo BILLETERA (Chaski, `billetera-chaski/`).

**Acceso de clientes (rol CLIENTE).** El módulo llama con su usuario de servicio (`svc-billetera`,
módulo BILLETERA, permiso `OPERAR_BILLETERA`) en `Authorization`. `POST /coredb/billetera/acceso`
(celular y PIN de 6 dígitos) entrega el **token de cliente**: otra audiencia
(`coredb-billetera`) y otro tipo, con `sub` = código del cliente y `rol` = CLIENTE; no sirve como
token del personal y viceversa. Las rutas del cliente exigen además ese token en
`X-Cliente-Token`; el cliente sale del token, nunca del cuerpo, y en cada petición se vuelve a
leer su afiliación (una billetera bloqueada o reafiliada corta la sesión). Un PIN equivocado y un
celular sin billetera responden lo mismo (401 `CREDENCIALES_INVALIDAS`); al tercer PIN equivocado
la billetera queda BLOQUEADA (403 `BILLETERA_BLOQUEADA`) hasta que el banco la afilie otra vez.

| Ruta | Quién | Qué hace |
|---|---|---|
| `POST /coredb/billetera/afiliaciones` | `AFILIAR_BILLETERA` (ADMINISTRADOR, ASESOR, OPERADOR) | Afilia a un cliente ACTIVO que ya existe (punto R-01) con su cuenta individual en soles y su PIN; repetirla cambia el PIN o la cuenta y reactiva |
| `POST /coredb/billetera/comercios` | `REGISTRAR_COMERCIO` (ADMINISTRADOR, OPERADOR) | Comercio con RUC, razón social y cuenta de abono, y su QR estático |
| `POST /coredb/billetera/acceso` | servicio BILLETERA | Valida celular y PIN; entrega el token de cliente |
| `POST /coredb/billetera/pin/verificacion` | cliente | Confirma el PIN antes de operar (mismos intentos) |
| `GET /coredb/billetera/yo` | cliente | Saldo disponible, tope del canal BD, consumo y disponible de hoy, avisos sin leer y solicitudes por pagar |
| `GET /coredb/billetera/movimientos`, `GET /coredb/billetera/operaciones` | cliente | Movimientos de su cuenta; envíos, pagos y cobros enviados o recibidos |
| `POST /coredb/billetera/contactos` | cliente | Nombre corto («Ana D.») del dueño de un celular con billetera |
| `POST /coredb/billetera/transferencias` | cliente | Envío por celular (P2P). Exige `X-Idempotency-Key` |
| `POST /coredb/billetera/qr`, `GET /coredb/billetera/qr/{id_qr}` | cliente | QR estático (sin monto) o dinámico (monto, vence, un pago); lo que ve el pagador, sin la cuenta del beneficiario |
| `POST /coredb/billetera/qr/{id_qr}/pagos` | cliente | Paga un QR de otro cliente o de un comercio. Exige `X-Idempotency-Key` |
| `GET /coredb/billetera/comercios` | cliente | Comercios activos con su QR |
| `POST /coredb/billetera/solicitudes`, `GET /coredb/billetera/solicitudes` | cliente | Pedir dinero por celular (vence a las 48 h); recibidas y enviadas |
| `POST /coredb/billetera/solicitudes/{id}/respuesta` | cliente | ACEPTAR (paga; exige `X-Idempotency-Key`) o RECHAZAR, el pagador; CANCELAR, quien la pidió |
| `GET /coredb/billetera/notificaciones`, `POST /coredb/billetera/notificaciones/leidas` | cliente | Avisos |

Cada operación de dinero es una transferencia del CORE por el canal BD (tope diario de S/ 500).
La huella de la llave se calcula aquí con el cliente y los parámetros: la misma llave con otros
datos, o de otro cliente, es 409 `BNA-IDEMPOTENCIA`; repetida con los mismos devuelve la misma
operación con `repetido: true`. El celular va siempre en el cuerpo (nunca en la ruta ni en la
consulta, que quedan en los registros de acceso) y ninguna respuesta ni evento lo devuelve.
Pruebas: `tests/test_billetera_rutas.py` (sin base) y `tests/integracion/test_billetera.py`
(contra MySQL, con concurrencia).

## Seguridad

Sobre la sección 18 de `bd-v1.13-mysql`. Lo usa solo el módulo Seguridad (`backend/seguridad`),
que no tiene base propia. Llama con su usuario de servicio (`svc-seguridad`, módulo SEGURIDAD) y,
en `X-Persona-Token`, el token de la persona por la que actúa. `OPERAR_SEGURIDAD` la tiene solo
`SERVICIO:SEGURIDAD`; COREDB exige además el permiso propio de la persona (relee su usuario: uno
desactivado o de servicio da 401 `PERSONA_NO_VIGENTE`; sin cabecera, `PERSONA_TOKEN_REQUERIDO`) y
la registra como actor. Nadie llega a estas rutas sin pasar por Seguridad.

| Ruta | Persona | Qué hace |
|---|---|---|
| `POST /coredb/seguridad/evaluaciones` | `REGISTRAR_MOVIMIENTO` | Compara el monto con el tope real del canal y el consumo real del día: `AUTORIZADA`, `RECHAZADA` (`TOPE`, `CANAL`, `CUENTA`), `DESAFIO_REQUERIDO` (sobre el 80 %) o, con `id_desafio` y `hmac_codigo`, `DESAFIO_RECHAZADO`. No mueve dinero. El `uuid_operacion` repetido devuelve la misma decisión (`repetida`); con otros datos, 409 `BNA-IDEMPOTENCIA` |
| `POST /coredb/seguridad/desafios` | `REGISTRAR_MOVIMIENTO` | Guarda el desafío con el HMAC del código (la clave es de Seguridad; COREDB nunca ve el código). Vence a los 120 s, tres fallos lo agotan |
| `GET /coredb/seguridad/incidentes` | `VER_AUDITORIA` o `GESTIONAR_INCIDENTES` | Los incidentes, del más reciente al más antiguo |
| `POST /coredb/seguridad/incidentes` | `GESTIONAR_INCIDENTES` (OPERADOR, ADMINISTRADOR) | Abre un incidente P1 a P4 |
| `POST /coredb/seguridad/incidentes/{id}/estado` | `GESTIONAR_INCIDENTES` | EN_PROGRESO → RESUELTO (con `resolucion`) → CERRADO, sin saltos (409 `BNA-INCIDENTE-TRANSICION`) |
| `POST /coredb/tarjetas/{id}/desbloqueo` | `BLOQUEAR_TARJETA` | BLOQUEADA o RETENIDA → ACTIVA, origen SEGURIDAD, con la cuenta `bna_seguridad_user`; devuelve la tarjeta y `cambio` (el registro del historial: id, fecha, motivo, estado anterior y actor); 409 `TARJETA_NO_BLOQUEADA` |

Sellos de la bitácora: `POST /coredb/auditoria/sellos` (solo `OPERAR_SEGURIDAD`, sin persona)
guarda el HMAC encadenado que calculó Seguridad sobre los eventos que siguen al último sello; la
base comprueba el tramo (409 `BNA-SELLO`). `GET /coredb/auditoria/sellos` (`VER_AUDITORIA`) los
lista y `GET /coredb/auditoria?despues_de_id=` lee los eventos del más antiguo al más reciente
para sellar y verificar. Pruebas: `tests/integracion/test_seguridad.py`.

## Consultas

| Ruta | Permiso | Qué devuelve |
|---|---|---|
| `GET /coredb/movimientos/cuenta/{num_cuenta}` | `VER_CUENTA` | Los movimientos de una cuenta, del más reciente al más antiguo (`limite`, `antes_de`) |
| `GET /coredb/movimientos/{uuid_transaccion}` | `VER_CUENTA` | Un movimiento |
| `GET /coredb/cuentas?cod_cliente=` | `VER_CUENTA` | Las cuentas en las que el cliente es titular |
| `GET /coredb/tarjetas?cod_cliente=` | `VER_TARJETA` | Las tarjetas del cliente, de la más reciente a la más antigua |
| `GET /coredb/tarjetas/{id}/historial?limite=` | `VER_TARJETA` | Los cambios de estado (estado, motivo, origen, fecha), del más reciente al más antiguo; hasta 100 (por omisión 20). Vista `tarjetas.v_historial_estado_tarjeta_api` (bd-v1.16) |
| `GET /coredb/auditoria` | `VER_AUDITORIA` | La bitácora, del evento más reciente al más antiguo, con filtros (con `despues_de_id`, del más antiguo al más reciente) |
| `GET /coredb/auditoria/sellos` | `VER_AUDITORIA` | Los sellos HMAC de la bitácora (ver «Seguridad») |
| `POST /coredb/auditoria/eventos` | `REGISTRAR_EVENTO_MODULO` (`svc-sol`) | Registra un evento que reporta un módulo sin base propia, una vez por `idEvento` (201; 200 si se repite; 409 con otro contenido) |

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
- **Desbloqueo de tarjetas:** solo por el módulo Seguridad (`POST /coredb/tarjetas/{id}/desbloqueo`,
  ver «Seguridad»). `POST /coredb/tarjetas/{id}/estado` lo rechaza con 403 `BNA-DESBLOQUEO`,
  porque en la base solo el rol `bna_seguridad` puede desbloquear. Para esa sola ruta COREDB abre
  una segunda conexión como `bna_seguridad_user` (`CORE_DB_SEGURIDAD_PASSWORD`); sin ella
  responde 503 `SEGURIDAD_NO_CONFIGURADA`.
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
