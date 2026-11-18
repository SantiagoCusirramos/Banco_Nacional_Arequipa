# Contrato del módulo ATM para los módulos que lo usan

**Estado:** implementado en `backend/ATM` (puerto 8019), sobre TARJETAS y CUENTAS por Bus de Servicios.
**Para quién:** la pantalla del cajero y el panel técnico, que sirve el propio módulo desde `static/`, y las pruebas de integración.
**Qué no es:** el tramo ATM → Bus → TARJETAS/CUENTAS. Ese está en este README y en el código.

## 1. Convenciones

- **URL base:** configurable, por ejemplo `ATM_BASE_URL=http://127.0.0.1:8019`. Dentro del producto (`./bna up`) otro módulo llega por el Bus de Servicios: `http://bus:8018/bus/atm`, con su credencial en `X-Bus-Token`. Todas las rutas de la API empiezan con `/api`.
- **Autenticación:** `Authorization: Bearer <token>` de COREDB en todas las rutas salvo `/health`, `/ready`, `/`, `/tecnico.html` y los archivos de `static/` (`/logo.png`, `/fuentes/...`) (sección 2). `/ready` responde 200 si TARJETAS y CUENTAS contestan por el Bus y 503 si no; sirve para saber si ATM puede atender, sin token. ATM no valida el token: lo reenvía y TARJETAS/CUENTAS deciden.
- **Correlación:** `X-Correlation-ID` es opcional. Si es un UUID, llega igual a TARJETAS/CUENTAS y a su bitácora; si no lo es, ATM genera uno para el Bus. El identificador de la respuesta va en `metadata.uuid_transaccion`.
- **Idempotencia:** la autorización y la confirmación exigen `X-Idempotency-Key` (UUIDv4). La validación de PIN y las consultas no la necesitan. Repetir una confirmación con la misma llave devuelve el mismo resultado sin segundo débito.
- **Cuerpos JSON estrictos:** un campo desconocido se rechaza con 400 `ERR-ATM-VALIDACION-ESQUEMA`, sin devolver su valor.
- **Éxito (ITIL-02):**

  ```json
  {"success": true, "status_code": 200, "message": "Operacion ejecutada satisfactoriamente",
   "data": {…},
   "metadata": {"uuid_transaccion": "…", "timestamp": "2026-11-12T15:04:05.123Z",
                "modulo_emisor": "ATM", "tiempo_ejecucion_ms": 41.7}}
  ```

- **Error (ITIL-02):** `{"success": false, "status_code": 404, "error_code": "ERR-ATM-TARJETA-NO-ENCONTRADA", "message": "…", "details": {}, "metadata": {…}}`. Un 422 de TARJETAS/CUENTAS se devuelve como 400.
- **Datos de la tarjeta:** ninguna respuesta trae el PAN ni su token. Solo el tokenizado interno (`tok_XXXX`).

## 2. Rutas públicas (sin token)

| Ruta | Descripción |
|---|---|
| `GET /health` | `{"status": "healthy", "modulo": "atm"}` |
| `GET /ready` | `{"status": "ready"}` o 503 `{"status": "not_ready", "tarjetas_o_cuentas": "no disponible"}` |
| `GET /` | Pantalla HTML del cajero |
| `GET /tecnico.html` | Panel técnico HTML |
| `GET /logo.png`, `GET /fuentes/...` | Archivos estáticos de `static/` (fuentes, logo); nada fuera de esa carpeta |

## 3. Rutas de la API (exigen token COREDB)

### 3.1 Validar PIN: `POST /api/validar-pin`

```json
{"id_tarjeta": "7e570001-0000-4000-8000-000000000001", "pin": "4821", "id_terminal": "ATM-AQP-001"}
```

- `id_tarjeta`: UUID de la tarjeta en TARJETAS (el frontend envía `tok_XXXX` y ATM lo mapea).
- `pin`: 4 dígitos.
- `id_terminal`: identificador del cajero (canal ATM).

**Respuesta 200:**

```json
{"resultado": "EXITOSO", "intentos_restantes": 3}
```

**Errores:**

| Estado | `error_code` | Cuándo |
|---|---|---|
| 400 | `ERR-ATM-TARJETA-NO-OPERATIVA` | Tarjeta bloqueada, vencida, etc. (viene de TARJETAS `ERR-TAR-003`) |
| 404 | `ERR-ATM-TARJETA-NO-ENCONTRADA` | No existe (viene de TARJETAS `ERR-TAR-NO-ENCONTRADA`) |
| 200 | `resultado: "FALLIDO"` | PIN incorrecto, `intentos_restantes` disminuye; a 0 la tarjeta queda bloqueada |

### 3.2 Autorizar retiro (retención): `POST /api/autorizar`

Exige `X-Idempotency-Key` (UUIDv4).

```json
{"id_tarjeta": "...", "num_cuenta": "10100000000001", "moneda": "PEN", "monto": "150.00",
 "id_terminal": "ATM-AQP-001", "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001"}
```

- `moneda`: `PEN` o `USD`.
- `monto`: múltiplo de 10, mayor a 0.
- `id_canal` (`ATM`, `AGE`, `VEN`, `HB`, `BD`) o `id_terminal`: uno de los dos.
- `uuid_transaccion`: UUIDv4 generado por el cajero para correlacionar todo el flujo.

**Respuesta 201 (aprobada):**

```json
{"uuid_autorizacion": "...", "id_tarjeta": "...", "num_cuenta": "...", "id_canal": "ATM",
 "id_terminal": null, "tipo_operacion": "RETIRO", "monto": "150.00",
 "estado_autorizacion": "AUTORIZADA", "codigo_respuesta": "00", "motivo_rechazo": null,
 "aprobada": true}
```

**Respuesta 201 (rechazada):**

```json
{"uuid_autorizacion": "...", ..., "estado_autorizacion": "RECHAZADA", "codigo_respuesta": "51",
 "motivo_rechazo": null, "aprobada": false}
```

| `codigo_respuesta` | Significado |
|---|---|
| `00` | Aprobada |
| `51` | Sin fondos |
| `54` | Tarjeta vencida |
| `57` | No permitida en la cuenta/canal (ej. mancomunada en ATM) |
| `61` | Excede tope diario del canal (RN-TOP-001) |
| `62` | Tarjeta no operativa |

**Errores:**

| Estado | `error_code` | Cuándo |
|---|---|---|
| 400 | `ERR-ATM-HEADER-REQUERIDO` | Falta `X-Idempotency-Key` |
| 400 | `ERR-ATM-HEADER-INVALIDO` | `X-Idempotency-Key` no es UUIDv4 |
| 400 | `ERR-ATM-VALIDACION-ESQUEMA` | Campo falta/sobra/formato inválido; o moneda no soportada; o monto no múltiplo de 10 |
| 400 | `ERR-ATM-CUENTA-INVALIDA` | La tarjeta no opera esa cuenta (viene de TARJETAS `ERR-TAR-CUENTA-INVALIDA`) |
| 409 | `ERR-ATM-IDEMPOTENCIA` | La misma llave se usó para otra autorización (viene de TARJETAS `ERR-TAR-IDEMPOTENCIA`) |
| 401 | `ERR-ATM-TOKEN-EXPIRADO` | Token COREDB vencido |
| 503 | `ERR-ATM-COR-NO-DISPONIBLE` | Bus no disponible |
| 504 | `ERR-ATM-TIMEOUT-BUS` | Bus no respondió a tiempo |

### 3.3 Confirmar dispensación: `POST /api/confirmar`

Exige `X-Idempotency-Key` (UUIDv4).

```json
{"uuid_autorizacion": "...", "id_terminal": "ATM-AQP-001", "resultado": "DISPENSADO"}
```

- `resultado`: `DISPENSADO` o `NO_DISPENSADO`.
- `id_canal` o `id_terminal`: uno de los dos.

**Respuesta 200:**

```json
{"uuid_autorizacion": "...", ..., "estado_autorizacion": "DISPENSADA", "codigo_respuesta": "00",
 "uuid_transaccion": "9e8d7c6b-0000-4000-8000-000000000001", "aprobada": true}
```

**Errores:**

| Estado | `error_code` | Cuándo |
|---|---|---|
| 400 | `ERR-ATM-HEADER-REQUERIDO` | Falta `X-Idempotency-Key` |
| 400 | `ERR-ATM-HEADER-INVALIDO` | `X-Idempotency-Key` no es UUIDv4 |
| 400 | `ERR-ATM-RESULTADO_INVALIDO` | `resultado` no es `DISPENSADO` ni `NO_DISPENSADO` |
| 404 | `ERR-ATM-AUTORIZACION-NO-ENCONTRADA` | No existe (viene de TARJETAS) |
| 409 | `ERR-ATM-EXTORNO-NO-PERMITIDO` | Ya contabilizada (viene de TARJETAS) |

**Idempotencia:** repetir la confirmación con la misma `X-Idempotency-Key` devuelve la misma respuesta (mismo `uuid_transaccion`) sin segundo débito.

### 3.4 Extornar autorización: `POST /api/extornar`

```json
{"uuid_autorizacion": "...", "motivo": "FALLA_DISPENSADOR"}
```

Libera el saldo retenido y el tope del día (RN-ATM-003). Repetirlo responde lo mismo sin cambiar nada.

**Respuesta 200:**

```json
{"uuid_autorizacion": "...", ..., "estado_autorizacion": "EXTORNADA", "codigo_respuesta": "EXT",
 "id_contra_asiento": "CA-000001", "saldo_disponible": "100.00", "aprobada": false}
```

**Errores:**

| Estado | `error_code` | Cuándo |
|---|---|---|
| 404 | `ERR-ATM-AUTORIZACION-NO-ENCONTRADA` | No existe |
| 409 | `ERR-ATM-EXTORNO-NO-PERMITIDO` | Fue rechazada, o ya se contabilizó (se revierte con movimiento inverso en CUENTAS) |

### 3.5 Consultar saldo: `GET /api/saldo?id_tarjeta=...`

Obtiene el `cod_cliente` de la tarjeta (TARJETAS) y consulta las cuentas consolidadas (CUENTAS).

**Respuesta 200:**

```json
{"lista_cuentas": [
  {"id_cuenta": "10100000000001", "num_cuenta_enmascarado": "****0001", "moneda": "PEN", "saldo_disponible": "500.00"},
  {"id_cuenta": "10100000000002", "num_cuenta_enmascarado": "****0002", "moneda": "USD", "saldo_disponible": "100.00"}
], "uuid_consulta": "...", "simulado": false}
```

### 3.6 Consultar movimientos: `GET /api/movimientos?num_cuenta=...`

**Respuesta 200:**

```json
[{"uuid_transaccion": "txn-1", "tipo_operacion": "RETIRO", "naturaleza": "D", "monto": "150.00", "fecha_hora": "2026-11-15T10:00:00Z"},
 {"uuid_transaccion": "txn-2", "tipo_operacion": "DEPOSITO", "naturaleza": "C", "monto": "500.00", "fecha_hora": "2026-11-14T10:00:00Z"}]
```

### 3.7 Estado del cajero: `GET /api/estado`

Estado local (bandejas simuladas, operaciones pendientes de conciliación).

**Respuesta 200:**

```json
{"terminal": "ATM-AQP-001",
 "bandejas": {"PEN": {"200": 20, "100": 40, "50": 60, "20": 80, "10": 80},
              "USD": {"100": 20, "50": 40, "20": 60, "10": 60}},
 "pendientes": [], "pruebas": null}
```

### 3.8 Configuración: `GET /api/config`

**Respuesta 200:**

```json
{"id_cajero": "ATM-AQP-001", "pruebas": false}
```

### 3.9 Registro de eventos del canal: `POST /api/registrar`

Recibe eventos del frontend (clave, consulta, retiro) para el log del canal.
No guarda datos sensibles (clave, token, PAN completo).

```json
{"tipo": "AUTENTICACION", "estado": "AUTENTICADA", "correlationId": "...",
 "tarjeta": "****4821", "codigo": null, "ms": 123}
```

**Respuesta 200:** `{"ok": true}`

### 3.10 Leer registro: `GET /api/registro?n=30`

Devuelve las últimas N líneas del registro de operaciones (máx. 500).

## 4. Permisos

Los decide COREDB según el rol del token (reenvía el token a TARJETAS/CUENTAS):

| Ruta ATM | Permiso en TARJETAS/CUENTAS | ADMINISTRADOR | OPERADOR | AUDITOR | ANALISTA, ASESOR |
|---|---|---|---|---|---|
| `POST /api/validar-pin` | `REGISTRAR_MOVIMIENTO` (TARJETAS) | Sí | Sí | No | No |
| `POST /api/autorizar` | `REGISTRAR_MOVIMIENTO` (TARJETAS) | Sí | Sí | No | No |
| `POST /api/confirmar` | `REGISTRAR_MOVIMIENTO` (TARJETAS) | Sí | Sí | No | No |
| `POST /api/extornar` | `REGISTRAR_MOVIMIENTO` (TARJETAS) | Sí | Sí | No | No |
| `GET /api/saldo` | `VER_CUENTA` (CUENTAS) | Sí | Sí | Sí | No |
| `GET /api/movimientos` | `VER_CUENTA` (CUENTAS) | Sí | Sí | Sí | No |

Sin permiso, la respuesta es 403 `ERR-TAR-PERMISO-DENEGADO` o `ERR-CUE-PERMISO-DENEGADO`.

## 5. Errores comunes

| Estado | `error_code` | Cuándo |
|---|---|---|
| 401 | `ERR-ATM-TOKEN-REQUERIDO`, `ERR-ATM-TOKEN-INVALIDO`, `ERR-ATM-TOKEN-EXPIRADO` | Sin token, token malo o vencido. Ante `EXPIRADO`, iniciar sesión otra vez y repetir una sola vez |
| 403 | `ERR-TAR-PERMISO-DENEGADO`, `ERR-CUE-PERMISO-DENEGADO` | El rol no tiene el permiso |
| 503 | `ERR-ATM-COR-NO-DISPONIBLE` | Bus no disponible |
| 504 | `ERR-ATM-TIMEOUT-BUS` | Bus no respondió a tiempo. En autorización/confirmación, repetir con la misma llave |
| 502 | `ERR-ATM-RESPUESTA_INVALIDA` | El Bus cortó la respuesta |

## 6. Pendiente

- **Bandejas reales:** hoy son simuladas en memoria; en producción deben persistirse y sincronizarse con el core.
- **Conciliación automática:** reintentar extornos/confirmaciones pendientes (hoy manual por panel técnico).
- **Retenciones pendientes en la pantalla:** `/api/estado` no lista las retenciones del cajero que siguen sin confirmar; la base las libera a los 15 minutos (decisión 11 de `Documents/decisiones-del-equipo.md`).

El cajero no tiene usuario de servicio propio: lo abre un operador del banco y su token se reenvía (decisión 13).

---

Dudas o cambios: comentarios sobre este documento o al módulo ATM.