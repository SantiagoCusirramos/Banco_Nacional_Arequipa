# Contrato del módulo TARJETAS para los módulos que lo usan

**Estado:** implementado en `backend/TARJETAS` (puerto 8002), sobre COREDB. La especificación exacta está en `/openapi.json` y en `/docs` del servicio.
**Para quién:** Cajero ATM, Home Banking, Billetera Digital y Ahorros, que consultan tarjetas (`TARJETA_LEER` en el control de acceso), y el personal que las emite y bloquea.
**Qué no es:** el tramo TARJETAS → COREDB. Ese está en `backend/COREDB/README.md`.

## 1. Convenciones

- **URL base:** configurable, por ejemplo `TARJETAS_BASE_URL=http://127.0.0.1:8002`. Dentro del producto (`./bna up`) es `http://tarjetas:8002`. Cuando exista el Bus de Servicios apuntará al Bus. Todas las rutas empiezan con `/api/v1/tarjetas`.
- **Autenticación:** `Authorization: Bearer <token>` de COREDB en todas las rutas salvo `/health` (sección 2). TARJETAS no valida el token: lo reenvía y COREDB decide.
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

> Hoy solo `SERVICIO:CLIENTES` tiene permisos en COREDB. Para que Cajero ATM, Home Banking o Billetera Digital consulten tarjetas con su propio usuario de servicio, hay que darle `VER_TARJETA` en `backend/COREDB/permisos.py` (sección 6).

## 3. Permisos

Los decide COREDB, según el rol del token:

| Ruta | Permiso | ADMINISTRADOR | OPERADOR | AUDITOR | ANALISTA, ASESOR |
|---|---|---|---|---|---|
| `GET /cliente/{cod_cliente}` | `VER_TARJETA` | Sí | Sí | Sí | No |
| `GET /{id_tarjeta}` | `VER_TARJETA` | Sí | Sí | Sí | No |
| `POST /emision` | `CREAR_TARJETA` | Sí | Sí | No | No |
| `POST /{id_tarjeta}/bloqueo` | `BLOQUEAR_TARJETA` | Sí | Sí | No | No |
| `POST /{id_tarjeta}/estado` | `BLOQUEAR_TARJETA` | Sí | Sí | No | No |

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
- `bin`: `004499` si no se envía, el único del catálogo (tarjeta física).
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
| 409 | `ERR-TAR-IDEMPOTENCIA` | La llave ya se usó para emitir otra tarjeta (otro cliente, BIN o fechas) |

Si la respuesta se pierde (504, corte de red), se repite la llamada **con la misma llave**.

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

## 5. Errores comunes

| Estado | `error_code` | Cuándo |
|---|---|---|
| 401 | `ERR-TAR-TOKEN-REQUERIDO`, `ERR-TAR-TOKEN-INVALIDO`, `ERR-TAR-TOKEN-EXPIRADO` | Sin token, token malo o vencido. Ante `ERR-TAR-TOKEN-EXPIRADO`, iniciar sesión otra vez y repetir una sola vez |
| 403 | `ERR-TAR-PERMISO-DENEGADO` | El rol no tiene el permiso |
| 503 | `ERR-COR-NO-DISPONIBLE` | COREDB no está disponible |
| 504 | `ERR-TAR-TIMEOUT-CORE` | COREDB no respondió a tiempo. En una emisión, repetir con la misma llave |

## 6. Pendiente

- **Autorizar, extornar y validar claves.** Retiros en cajero (RN-TOP-001), extornos (RN-ATM-003) y validación del PIN, la clave web y la tarjeta matriz (RN-TAR-001, 002 y 004) necesitan procedimientos en la base que COREDB pueda ejecutar. Propuestos en [miguelpro324/bna-core-db#1](https://github.com/miguelpro324/bna-core-db/issues/1). Cuando existan, este contrato suma sus rutas.
- **Usuarios de servicio de los módulos consumidores.** Dar `VER_TARJETA` a `SERVICIO:CAJERO_ATM`, `SERVICIO:HOME_BANKING` y `SERVICIO:BILLETERA_DIGITAL` en COREDB, cuando esos módulos se integren.
- **Tarjetas virtuales.** Necesitan un BIN propio de tipo `VIRTUAL` en el catálogo (issue #34, pregunta 7).

Dudas o cambios: comentarios sobre este documento o al módulo Tarjetas.
