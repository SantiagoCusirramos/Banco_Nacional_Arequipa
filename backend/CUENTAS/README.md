# CUENTAS

Modulo de Cuentas (linea Ahorros). No tiene base de datos propia: valida y llama a CORE (`/core/*`).
Sigue el estandar del Comite de Ahorros (DOC-ITIL-01 y DOC-ITIL-02).

## Endpoints

| Metodo | Ruta | Llama a CORE |
|---|---|---|
| POST | /api/v1/cuentas/apertura | POST /core/cuentas |
| GET | /api/v1/cuentas/{num_cuenta} | GET /core/cuentas/{num} |
| GET | /api/v1/cuentas/consolidada/{id_cliente} | GET /core/cuentas/cliente/{id} |
| POST | /api/v1/cuentas/deposito | POST /core/movimientos |
| POST | /api/v1/cuentas/retiro | POST /core/movimientos |
| POST | /api/v1/cuentas/transferencia | POST /core/movimientos/transferencias |
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
| CORE SALDO_INSUFICIENTE | ERR-CTA-FONDOS-INSUFICIENTES | 400 |
| CORE TOPE_DIARIO_EXCEDIDO | ERR-CTA-TOPE-EXCEDIDO | 400 |
| CORE CUENTA_NO_OPERATIVA | ERR-CTA-BLOQUEADA | 403 |
| CORE CUENTA_NO_ENCONTRADA | ERR-CTA-NO-ENCONTRADA | 404 |
| CORE CLIENTE_NO_ENCONTRADO | ERR-CLI-NO-ENCONTRADO | 404 |
| CORE TIPO_CAMBIO_NO_ENCONTRADO | ERR-COR-TC-NO-VIGENTE | 400 |
| CORE CUENTA_MANCOMUNADA_INCOMPLETA | ERR-CTA-MANCOMUNADA-SIN-COTITULARES | 400 |
| CORE TRANSFERENCIA_MISMA_CUENTA | ERR-CTA-CUENTAS-IGUALES | 400 |
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

```bash
cd backend
uvicorn main:app --port 8000                  # CORE
uvicorn CUENTAS.main:app --port 8001          # CUENTAS
```

Variables: `CORE_BASE_URL` (por defecto http://localhost:8000), `CORE_TIMEOUT_SECONDS` (5).

## Tests

```bash
cd backend
python -m pytest CUENTAS/tests -q
```

`test_contrato_core.py` valida los payloads contra los schemas reales de CORE (se omite si CORE no esta en el path).

## Diferencias con ITIL-02 / pendientes

- 409 por llave duplicada: CORE no lo hace, devuelve el resultado original con `replay: true`
- Cuentas no usa MySQL directo: las tablas las escribe CORE
- Extorno ATM (INT05), cierre mensual e intereses, eliminar cuenta: requieren cambios en CORE (RFC)
- Validacion de token (Seguridad) y paso por el Bus: no existen aun
- Tope diario: lo valida CORE con `limite_canal`, sus valores no coinciden con el Diccionario
- Mancomunada indistinta/conjunta: CORE no lo guarda
