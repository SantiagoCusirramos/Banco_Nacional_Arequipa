# Contrato del módulo TARJETAS para los módulos que lo usan

**Estado:** implementado en `backend/TARJETAS` (puerto 8002), sobre COREDB. La especificación exacta está en `/openapi.json` y en `/docs` del servicio.
**Para quién:** Cajero ATM, Home Banking, Billetera Digital y Ahorros, que consultan tarjetas (`TARJETA_LEER` en el control de acceso), y el personal que las emite y bloquea.
**Qué no es:** el tramo TARJETAS → COREDB. Ese está en `backend/COREDB/README.md`.

## 1. Convenciones

- **URL base:** configurable, por ejemplo `TARJETAS_BASE_URL=http://127.0.0.1:8002`. Dentro del producto (`./bna up`) los demás módulos llegan por el Bus de Servicios: `http://bus:8018/bus/tarjetas`, con su credencial en `X-Bus-Token` (así lo hace el ATM). Todas las rutas empiezan con `/api/v1/tarjetas`.
- **Autenticación:** `Authorization: Bearer <token>` de COREDB en todas las rutas salvo `/health` y `/ready` (sección 2). `/ready` responde 200 si COREDB contesta y 503 si no; sirve para saber si TARJETAS puede atender, sin token. TARJETAS no valida el token: lo reenvía y COREDB decide.
- **Correlación:** `X-Correlation-ID` es opcional. Si es un UUID, llega igual a COREDB y a su bitácora; si no lo es, TARJETAS genera uno para COREDB. El identificador de la respuesta va en `metadata.uuid_transaccion` y en la cabecera `X-Idempotency-Key`.
- **Idempotencia:** la emisión exige `X-Idempotency-Key` (UUIDv4). Las consultas y los cambios de estado no la necesitan: repetir un bloqueo deja la tarjeta bloqueada.
- **Cuerpos JSON estrictos:** un campo desconocido se rechaza con 400 `ERR-VALIDACION-ESQUEMA`, sin devolver su valor.
- **Éxito (ITIL-02):**

  ```json
  {"success": true, "status_code": 200, "message": "Operacion ejecutada satisfactoriamente",
   "data": {…},
   "metadata": {"uuid_transaccion": "…", "timestamp": "2026-11-12T15:04:05.123Z",
                "modulo_emisor": "TARJETAS", "tiempo_ejecucion_ms": 41.7}}
  ```

- **Error (ITIL-02):** `{"success": false, "status_code": 404, "error_code": "ERR-TAR-NO-ENCONTRADA", "message": "…", "details": {}, "metadata": {…}}`. Un 422 de COREDB se devuelve como 400.
- **Datos de la tarjeta:** ninguna respuesta trae el PAN ni su token. Solo el BIN, los últimos cuatro dígitos y el número enmascarado.

### La tarjeta

```json
{
  "id_tarjeta": "7e570001-0000-4000-8000-000000000001",
  "bin": "004499",
  "ultimos4": "0001",
  "fecha_emision": "2026-01-15",
  "fecha_vencimiento": "2030-01-31",
  "estado_tarjeta": "ACTIVA",
  "cod_cliente": "CLI000000001",
  "num_cuenta": "10100000000001",
  "numero_enmascarado": "0044 99** **** 0001",
  "vencimiento_mm_aa": "01/30"
}
```

| `estado_tarjeta` | Significa | Opera |
|---|---|---|
| `PENDIENTE_ACTIVACION` | Emitida, aún sin activar | No |
| `ACTIVA` | En uso | Sí |
| `BLOQUEADA` | Bloqueada por el cliente, el personal o el sistema (tercer intento fallido) | No |
| `RETENIDA` | Retenida por el banco | No |
| `VENCIDA` | Pasó su fecha de vencimiento; la marca un proceso diario | No |
| `CANCELADA` | Anulada; es final | No |

## 2. Credenciales

TARJETAS no tiene usuarios propios: usa el token de COREDB de quien llama.

- **Personal del banco:** inicia sesión en COREDB (`POST /coredb/auth/login`) y envía ese token. Es lo que hace la pantalla `/tarjetas` del frontend.
- **Otro módulo:** debe autenticarse con su **usuario de servicio** de COREDB (rol `SERVICIO` y su módulo), como Clientes. El procedimiento de alta, rotación y revocación está en `backend/COREDB/CONTRATO_CLIENTES.md`, sección 2.

> En el producto ningún módulo llama a TARJETAS con un usuario de servicio propio. El cajero (ATM) reenvía el token del operador que lo abrió (decisión 13 de `Documents/decisiones-del-equipo.md`) y el Home Banking el del usuario del banco que atiende al cliente (decisión 14). La Billetera Digital no usa TARJETAS. Un módulo que necesite su propio usuario de servicio requiere `VER_TARJETA` para su rol en `backend/COREDB/permisos.py`.

## 3. Permisos

Los decide COREDB, según el rol del token:

| Ruta | Permiso | ADMINISTRADOR | OPERADOR | AUDITOR | ANALISTA, ASESOR |
|---|---|---|---|---|---|
| `GET /cliente/{cod_cliente}` | `VER_TARJETA` | Sí | Sí | Sí | No |
| `GET /{id_tarjeta}` | `VER_TARJETA` | Sí | Sí | Sí | No |
| `POST /emision` | `CREAR_TARJETA` | Sí | Sí | No | No |
| `POST /{id_tarjeta}/bloqueo` | `BLOQUEAR_TARJETA` | Sí | Sí | No | No |
| `POST /{id_tarjeta}/estado` | `BLOQUEAR_TARJETA` | Sí | Sí | No | No |
| `POST /{id_tarjeta}/autorizaciones` | `REGISTRAR_MOVIMIENTO` | Sí | Sí | No | No |
| `GET /autorizaciones/{uuid_autorizacion}` | `VER_TARJETA` | Sí | Sí | Sí | No |
| `POST /autorizaciones/{uuid_autorizacion}/extorno` | `REGISTRAR_MOVIMIENTO` | Sí | Sí | No | No |
| `POST /autorizaciones/{uuid_autorizacion}/confirmacion` | `REGISTRAR_MOVIMIENTO` | Sí | Sí | No | No |
| `PUT /{id_tarjeta}/credenciales/{tipo}` | `CREAR_TARJETA` | Sí | Sí | No | No |
| `POST /{id_tarjeta}/credenciales/{tipo}/validacion` | `REGISTRAR_MOVIMIENTO` | Sí | Sí | No | No |

Sin permiso, la respuesta es 403 `ERR-TAR-PERMISO-DENEGADO`.

## 4. Rutas

### 4.1 Tarjetas de un cliente: `GET /api/v1/tarjetas/cliente/{cod_cliente}`

Las tarjetas del cliente, de la más reciente a la más antigua, en `data` como lista. El código se acepta en minúsculas.

| Estado | `error_code` | Cuándo |
|---|---|---|
| 200 | | Lista, vacía si el cliente no tiene tarjetas |
| 404 | `ERR-CLI-NO-ENCONTRADO` | El cliente no existe |

No hay una ruta que liste todas las tarjetas.

### 4.2 Una tarjeta: `GET /api/v1/tarjetas/{id_tarjeta}`

| Estado | `error_code` | Cuándo |
|---|---|---|
| 200 | | La tarjeta |
| 400 | `ERR-TAR-ID-INVALIDO` | El identificador no es un UUID |
| 404 | `ERR-TAR-NO-ENCONTRADA` | No existe |

### 4.3 Emitir: `POST /api/v1/tarjetas/emision`

Cabecera obligatoria: `X-Idempotency-Key: <UUIDv4>`.

```json
{
  "cod_cliente": "CLI000000001",
  "num_cuenta": "10100000000001",
  "bin": "004499",
  "fecha_emision": "2026-11-12",
  "fecha_vencimiento": "2030-11-30",
  "ultimos4": "0001"
}
```

- Obligatorios: `cod_cliente` y `num_cuenta`, una cuenta en la que el cliente es titular.
- `bin`: `004499` si no se envía. Es un BIN de desarrollo, de tarjeta física; hay un BIN por tipo de tarjeta (decisión 10 de `Documents/decisiones-del-equipo.md`) y los reales los dará el emisor (issue #116).
- Sin fechas, la tarjeta se emite hoy y vence en cuatro años. El vencimiento debe ser posterior a la emisión (RN-TAR-003).
- `ultimos4`: los últimos cuatro dígitos del PAN, si ya se conocen. **El PAN nunca se envía**: un campo `pan` se rechaza.
- La tarjeta nace `PENDIENTE_ACTIVACION` y vinculada a la cuenta; se activa con 4.5.

| Estado | `error_code` | Cuándo |
|---|---|---|
| 201 | | `message`: `Tarjeta emitida, pendiente de activación` |
| 201 | | La misma llave y los mismos datos otra vez: devuelve la tarjeta ya emitida y no emite otra. `message`: `Emision ya procesada antes (idempotencia), se devuelve la tarjeta original` |
| 400 | `ERR-TAR-HEADER-REQUERIDO`, `ERR-TAR-HEADER-INVALIDO` | Falta la llave o no es un UUIDv4 |
| 400 | `ERR-VALIDACION-ESQUEMA` | Un campo falta, sobra o no tiene el formato; o el vencimiento no es posterior a la emisión |
| 400 | `ERR-TAR-001` | El cliente no está ACTIVO |
| 400 | `ERR-TAR-CUENTA-INVALIDA` | El cliente no es titular de la cuenta, o la cuenta está cancelada |
| 409 | `ERR-TAR-IDEMPOTENCIA` | La llave ya se usó para emitir otra tarjeta: otra cuenta (aunque sea del mismo cliente), otro cliente, otro BIN, u otros últimos cuatro dígitos o fechas enviados |

Si la respuesta se pierde (504, corte de red), se repite la llamada **con la misma llave** y los mismos datos. Si se omiten `ultimos4` o las fechas, vale lo de la primera emisión. Si la emisión falló por una regla (400), no se emitió nada y la misma llave sirve para reintentar.

### 4.4 Bloquear: `POST /api/v1/tarjetas/{id_tarjeta}/bloqueo`

```json
{"motivo": "Robo reportado por el cliente"}
```

El motivo es obligatorio (de 3 a 255 caracteres) y queda en el historial de la tarjeta. Responde la tarjeta `BLOQUEADA`, con `message`: `Tarjeta bloqueada`.

### 4.5 Cambiar el estado: `POST /api/v1/tarjetas/{id_tarjeta}/estado`

```json
{"estado": "ACTIVA", "motivo": "Activación en agencia"}
```

- `estado`: `ACTIVA`, `BLOQUEADA`, `RETENIDA` o `ANULADA`. `ANULADA` se guarda como `CANCELADA` y es final.
- `motivo`: opcional.
- El **desbloqueo** (de `BLOQUEADA` a `ACTIVA`) lo hace Seguridad: aquí responde 403 `ERR-TAR-DESBLOQUEO-NO-PERMITIDO`.
- Una transición que la base no admite (por ejemplo, reactivar una tarjeta `CANCELADA`) responde 400 `ERR-TAR-002`.
- El origen del cambio no se envía: COREDB lo toma del token (`OPERADOR` para personas, `SISTEMA` para otro módulo).

### 4.6 Autorizar un débito: `POST /api/v1/tarjetas/{id_tarjeta}/autorizaciones`

Antes de contabilizar un retiro o un pago con la tarjeta. Exige `X-Idempotency-Key` (UUIDv4), como la emisión.

```json
{"num_cuenta": "10100000000001", "tipo_operacion": "RETIRO", "monto": "150.00", "id_terminal": "DEV-ATM-01"}
```

- `tipo_operacion`: `RETIRO` (por omisión), `PAGO` o `FONDEO_BILLETERA`.
- `id_canal` (`ATM`, `AGE`, `VEN`, `HB`, `BD`) o `id_terminal`: uno de los dos.
- La cuenta debe ser una de las que opera la tarjeta.
- Si se aprueba, el monto queda retenido del saldo disponible y suma al tope del día del canal (RN-TOP-001) hasta que se contabilice o se extorne.

```json
{"uuid_autorizacion": "…", "id_tarjeta": "…", "num_cuenta": "10100000000001", "id_canal": null,
 "id_terminal": "DEV-ATM-01", "tipo_operacion": "RETIRO", "monto": "150.00",
 "estado_autorizacion": "AUTORIZADA", "codigo_respuesta": "00", "motivo_rechazo": null, "aprobada": true}
```

| Estado | `error_code` | Cuándo |
|---|---|---|
| 201 | | `aprobada: true`, `codigo_respuesta` `00`. `message`: `Operación autorizada` |
| 201 | | Una regla no se cumple: `aprobada: false`, `estado_autorizacion` `RECHAZADA` y `codigo_respuesta` `51` (sin fondos), `54` (vencida), `57` (no permitida en la cuenta o el canal, por ejemplo una cuenta mancomunada en cajero), `61` (excede el tope del día) o `62` (tarjeta no operativa). `message`: `Operación rechazada (código 51)` |
| 201 | | La misma llave y los mismos datos otra vez: devuelve la autorización ya registrada y no retiene el saldo dos veces |
| 400 | `ERR-TAR-HEADER-REQUERIDO`, `ERR-TAR-HEADER-INVALIDO` | Falta la llave o no es un UUIDv4 |
| 400 | `ERR-VALIDACION-ESQUEMA` | Un campo falta, sobra o no tiene el formato, o vienen el canal y la terminal a la vez |
| 400 | `ERR-TAR-CUENTA-INVALIDA` | La tarjeta no opera esa cuenta, o no existe |
| 409 | `ERR-TAR-IDEMPOTENCIA` | La llave ya se usó para otra autorización |

El motivo de un rechazo no trae montos ni saldos, para poder mostrarlo.

### 4.7 Una autorización: `GET /api/v1/tarjetas/autorizaciones/{uuid_autorizacion}`

Responde la autorización (404 `ERR-TAR-AUTORIZACION-NO-ENCONTRADA` si no existe).

### 4.8 Extornar: `POST /api/v1/tarjetas/autorizaciones/{uuid_autorizacion}/extorno`

```json
{"motivo": "Cajero sin efectivo"}
```

Pasa la autorización a `EXTORNADA` (`codigo_respuesta` `EXT`) y libera el saldo retenido y el tope (RN-ATM-003). Repetirlo responde lo mismo sin cambiar nada.

| Estado | `error_code` | Cuándo |
|---|---|---|
| 200 | | `message`: `Operación extornada` |
| 404 | `ERR-TAR-AUTORIZACION-NO-ENCONTRADA` | No existe |
| 409 | `ERR-TAR-EXTORNO-NO-PERMITIDO` | Fue rechazada, o la operación ya se contabilizó (se revierte con un movimiento inverso en CUENTAS) |

### 4.9 Confirmar una autorización: `POST /api/v1/tarjetas/autorizaciones/{uuid_autorizacion}/confirmacion`

Cuando el cajero dispensa el efectivo, confirma la autorización retenida: registra el movimiento real (débito) y pasa la autorización a `DISPENSADA`. Exige `X-Idempotency-Key` (UUIDv4) en cabecera. La **huella** (SHA-256 hex de 64 caracteres) la calcula COREDB a partir de `uuid_autorizacion`, `id_canal` e `id_terminal`; no se envía en el cuerpo.

```json
{"id_terminal": "DEV-ATM-01"}
```

Cabecera obligatoria: `X-Idempotency-Key: <UUIDv4>`.

- `id_canal` (`ATM`, `AGE`, `VEN`, `HB`, `BD`) o `id_terminal`: uno de los dos (o ambos). Deben coincidir con la autorización.
- Repetir con la **misma llave** devuelve el mismo resultado sin segundo débito.
- Repetir con **otra llave** falla: la autorización ya cambió a `DISPENSADA`.
- La misma llave con diferente canal/terminal falla con 409 `ERR-TAR-IDEMPOTENCIA` (huella distinta).

```json
{"uuid_autorizacion": "…", "id_tarjeta": "…", "num_cuenta": "10100000000001",
 "id_canal": "ATM", "id_terminal": "DEV-ATM-01", "tipo_operacion": "RETIRO",
 "monto": "150.00", "estado_autorizacion": "DISPENSADA", "codigo_respuesta": "00",
 "motivo_rechazo": null, "uuid_transaccion": "…", "aprobada": true}
```

| Estado | `error_code` | Cuándo |
|---|---|---|
| 200 | | `message`: `Operación confirmada` |
| 400 | `ERR-TAR-HEADER-REQUERIDO`, `ERR-TAR-HEADER-INVALIDO` | Falta la cabecera `X-Idempotency-Key` o no es un UUIDv4 |
| 400 | `ERR-VALIDACION-ESQUEMA` | Falta canal/terminal, o vienen ambos a la vez |
| 404 | `ERR-TAR-AUTORIZACION-NO-ENCONTRADA` | No existe |
| 409 | `ERR-TAR-CONFIRMACION-NO-PERMITIDA` | Fue rechazada, extornada, o ya dispensada |
| 409 | `ERR-TAR-IDEMPOTENCIA` | La llave se usó en otra operación (incluye misma llave con diferente canal/terminal) |

### 4.10 Claves de la tarjeta: `PUT /api/v1/tarjetas/{id_tarjeta}/credenciales/{tipo}` y `POST .../{tipo}/validacion`

`tipo`: `PIN_ATM` (4 dígitos) o `CLAVE_WEB` (6 dígitos), RN-TAR-001.

```json
{"valor": "4821"}
```

Asignar o cambiar la clave reinicia los intentos fallidos. La base guarda solo su hash con una sal propia. `message`: `Clave registrada`.

Para validar, se envía también el canal o la terminal:

```json
{"valor": "4821", "id_terminal": "DEV-ATM-01"}
```

| Estado | `error_code` | Cuándo |
|---|---|---|
| 200 | | `{"resultado": "EXITOSO", "intentos_restantes": 3}`, `message`: `Clave correcta` |
| 200 | | `{"resultado": "FALLIDO", "intentos_restantes": 2}`, `message`: `Clave incorrecta`. Con 0 la tarjeta quedó `BLOQUEADA` (RN-TAR-004) |
| 400 | `ERR-VALIDACION-ESQUEMA` | La clave no son de 4 a 6 dígitos, o el tipo no es uno de los dos |
| 400 | `ERR-TAR-CREDENCIAL-INVALIDA` | La longitud no es la del tipo, o la tarjeta aún no tiene esa clave |
| 400 | `ERR-TAR-003` | La tarjeta no está operativa: no se valida ni se cuenta el intento |

La clave nunca se devuelve, no se registra en la bitácora y no aparece en los mensajes de error.

## 5. Errores comunes

| Estado | `error_code` | Cuándo |
|---|---|---|
| 401 | `ERR-TAR-TOKEN-REQUERIDO`, `ERR-TAR-TOKEN-INVALIDO`, `ERR-TAR-TOKEN-EXPIRADO` | Sin token, token malo o vencido. Ante `ERR-TAR-TOKEN-EXPIRADO`, iniciar sesión otra vez y repetir una sola vez |
| 403 | `ERR-TAR-PERMISO-DENEGADO` | El rol no tiene el permiso |
| 503 | `ERR-COR-NO-DISPONIBLE` | COREDB no está disponible |
| 504 | `ERR-TAR-TIMEOUT-CORE` | COREDB no respondió a tiempo. En una emisión o una autorización, repetir con la misma llave |

## 6. Pendiente

- **Tarjeta matriz.** Validar una coordenada (RN-TAR-002) necesita un procedimiento que emita la matriz; la base aún no lo tiene.
- **Tarjetas virtuales.** Necesitan un BIN propio de tipo `VIRTUAL` en el catálogo, que dará el emisor junto con los BIN reales (issue #116).

Dudas o cambios: comentarios sobre este documento o al módulo Tarjetas.
