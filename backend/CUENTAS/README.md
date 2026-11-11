# CUENTAS

Modulo de Cuentas (linea Ahorros). No tiene base de datos propia: valida y llama a COREDB (`/coredb/*`, puerto 8012).
Sigue el estandar del Comite de Ahorros (DOC-ITIL-01 y DOC-ITIL-02).

## Endpoints

| Metodo | Ruta | Llama a COREDB |
|---|---|---|
| POST | /api/v1/cuentas/apertura | POST /coredb/cuentas |
| GET | /api/v1/cuentas/{num_cuenta} | GET /coredb/cuentas/{num} |
| GET | /api/v1/cuentas/consolidada/{id_cliente} | GET /coredb/cuentas?cod_cliente= |
| POST | /api/v1/cuentas/deposito | POST /coredb/movimientos |
| POST | /api/v1/cuentas/retiro | POST /coredb/movimientos |
| POST | /api/v1/cuentas/transferencia | POST /coredb/movimientos/transferencias |
| GET | /api/v1/cuentas/{num_cuenta}/movimientos | GET /coredb/movimientos/cuenta/{num} |
| GET | /api/v1/cuentas/movimiento/{uuid_transaccion} | GET /coredb/movimientos/{uuid} |
| GET | /health | - |

## Cabeceras

Deposito, retiro y transferencia exigen:

- `X-Idempotency-Key`: UUIDv4
- `X-Channel-ID`: ATM, AGE, VEN, WEB o MOB (WEB pasa a HB y MOB a BD en CORE; VEN no esta en ITIL-01, se agrego porque CORE lo tiene)
- `X-Request-Timestamp`: ISO-8601

`X-Correlation-ID` es opcional. El `uuid_transaccion` de respuestas y logs sale de X-Idempotency-Key, luego X-Correlation-ID, y si no hay ninguno se genera.

## Respuestas (ITIL-02)

Exito: `{success, status_code, message, data, metadata{uuid_transaccion, timestamp, modulo_emisor, tiempo_ejecucion_ms}}`

Error: `{success:false, status_code, error_code, message, details, metadata}`. 422 se devuelve como 400.

Los montos van como texto decimal ("500.00") para no perder precision, igual que CORE. ITIL-02 los muestra como numero.

| Origen | error_code | HTTP |
|---|---|---|
| COREDB BNA-SALDO | ERR-CTA-FONDOS-INSUFICIENTES | 400 |
| COREDB RN-TOP-001 | ERR-CTA-TOPE-EXCEDIDO | 400 |
| COREDB BNA-ESTADO-CUENTA | ERR-CTA-BLOQUEADA | 403 |
| CORE CUENTA_NO_ENCONTRADA | ERR-CTA-NO-ENCONTRADA | 404 |
| CORE CLIENTE_NO_ENCONTRADO | ERR-CLI-NO-ENCONTRADO | 404 |
| CORE TIPO_CAMBIO_NO_ENCONTRADO | ERR-COR-TC-NO-VIGENTE | 400 |
| CORE CUENTA_MANCOMUNADA_INCOMPLETA | ERR-CTA-MANCOMUNADA-SIN-COTITULARES | 400 |
| CORE TRANSFERENCIA_MISMA_CUENTA | ERR-CTA-CUENTAS-IGUALES | 400 |
| COREDB BNA-CUENTA | ERR-CTA-NO-ENCONTRADA | 404 |
| COREDB BNA-REGIMEN / BNA-CANAL | ERR-CTA-REGIMEN-INVALIDO / ERR-CTA-CANAL-INVALIDO | 400 |
| COREDB BNA-IDEMPOTENCIA / REGISTRO_DUPLICADO | ERR-CTA-IDEMPOTENCIA / ERR-CTA-CUENTA-DUPLICADA | 409 |
| COREDB TOKEN_* / PERMISO_DENEGADO | ERR-CTA-TOKEN-* / ERR-CTA-PERMISO-DENEGADO | 401 / 403 |
| Otro codigo de CORE | ERR-COR-<CODIGO> | el de CORE |
| Pydantic | ERR-VALIDACION-ESQUEMA | 400 |
| Header faltante o invalido | ERR-CTA-HEADER-REQUERIDO / ERR-CTA-HEADER-INVALIDO | 400 |
| CORE apagado | ERR-COR-NO-DISPONIBLE | 503 |
| CORE sin respuesta (consulta) | ERR-CTA-TIMEOUT-CORE | 504 |
| CORE sin respuesta (movimiento) | ERR-CTA-OPERACION-NO-CONFIRMADA | 504 |
| Error no controlado | ERR-INTERNO-SERVIDOR (sin detalle interno) | 500 |

Si un movimiento da 504, reintentar con la misma llave: CORE devuelve el resultado original con `replay: true`.

## Logs

Una linea JSON por peticion con los campos de ITIL-02 (timestamp, level, uuid_transaccion, modulo, endpoint, status_code, tiempo_ms, client_ip, mensaje, datos_contexto). No se registran cuerpos de peticion.

## Correr

Con todo el producto, desde la raiz del repositorio: `./bna up` (CUENTAS queda en http://127.0.0.1:8001/docs).

Solo el modulo, con COREDB ya levantado:

```bash
cd backend
uvicorn CUENTAS.main:app --port 8001
```

Variables: `CORE_BASE_URL` (por defecto http://localhost:8012, la API COREDB), `CORE_TIMEOUT_SECONDS` (5) y `CORS_ORIGINS` (por defecto http://localhost:3000,http://127.0.0.1:3000).

## Tests

```bash
cd backend
python -m pytest CUENTAS/tests -q
```

`test_contrato_core.py` valida los payloads contra los schemas reales de CORE (se omite si CORE no esta en el path).

## Diferencias con ITIL-02 / pendientes

- 409 por llave duplicada: CORE devuelve el resultado original con `replay: true` si la peticion es la misma, y 409 (`ERR-COR-IDEMPOTENCY-KEY-REUTILIZADA`) si la llave se reutiliza con otros datos
- Cuentas no usa MySQL directo: las tablas las escribe CORE
- Extorno ATM (INT05), cierre mensual e intereses, eliminar cuenta: requieren cambios en CORE (RFC)
- Validacion de token (Seguridad) y paso por el Bus: no existen aun
- Tope diario: lo valida CORE con `limite_canal`, sus valores no coinciden con el Diccionario
- Mancomunada indistinta/conjunta: CORE no lo guarda


## Autenticacion y campos (COREDB)
- Todas las rutas piden `Authorization: Bearer <token>` (JWT de `POST /coredb/auth/login`). Cuentas lo reenvia a COREDB, que valida rol y permisos. Sin el header responde 401 `ERR-CTA-TOKEN-REQUERIDO`.
- Abrir cuenta y mover dinero requieren rol ADMINISTRADOR u OPERADOR en COREDB.
- Apertura: `num_cuenta`, `cci` (20 digitos), `moneda` (PEN/USD), `regimen` (INDIVIDUAL, MANCOMUNADA_INDISTINTA, MANCOMUNADA_CONJUNTA), `id_agencia` y `titulares` (lista de `{id_cliente}`) o `id_cliente` si es un solo titular.
- Deposito/retiro: `num_cuenta`, `monto`, `glosa` (opcional). Respuesta: `uuid_transaccion` y `replay`.
- Transferencia: `num_cuenta_origen`, `num_cuenta_destino`, `monto`, `glosa` (opcional). Respuesta: `uuid_debito`, `uuid_abono`, `replay`.
- PROPUESTA: los codigos ERR-CTA nuevos de esta tabla no estan en ITIL-02, falta aprobarlos.
- Cada cuenta trae `titulares`, los codigos de sus clientes, como los devuelve COREDB.
- Un movimiento trae `tipo_operacion`, `naturaleza` (D debito, C credito), `monto`, `moneda`, `glosa`, `id_canal`, `estado_transaccion` y `fecha_hora`. COREDB no guarda el saldo posterior ni la cuenta de contraparte.
