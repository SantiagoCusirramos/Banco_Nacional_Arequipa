# CUENTAS

Modulo de Cuentas (linea Ahorros). No tiene base de datos propia: valida y llama a CORE (`/core/*`).

## Endpoints

| Metodo | Ruta | Llama a CORE |
|---|---|---|
| POST | /cuentas | POST /core/cuentas |
| GET | /cuentas/{num} | GET /core/cuentas/{num} |
| GET | /cuentas/cliente/{id} | GET /core/cuentas/cliente/{id} |
| POST | /cuentas/{num}/depositos | POST /core/movimientos |
| POST | /cuentas/{num}/retiros | POST /core/movimientos |
| POST | /cuentas/{num}/transferencias | POST /core/movimientos/transferencias |

Operaciones que mueven saldo exigen header `X-Idempotency-Key`. `X-Correlation-ID` se genera si no llega.
Canales validos: ATM, AGE, VEN, HB, BD (ids del catalogo `canal` de CORE).

## Errores

Mismo formato que CORE: `{"error": {"code", "message", "details"}, "correlation_id"}`.
Los errores de CORE (saldo insuficiente, tope diario, etc.) se devuelven tal cual.
Si CORE no responde en un movimiento: 504 `OPERACION_NO_CONFIRMADA`, reintentar con la misma llave.

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

## Pendiente

- Cierre mensual / intereses: CORE no tiene endpoint, solo la tabla `cta_interes_mensual`
- Eliminar cuenta: el PATCH de CORE no acepta estado CERRADA
- Validacion de token (Seguridad) y paso por el Bus: no existen aun
- Tope diario: lo valida CORE con `limite_canal`, sus valores no coinciden con el Diccionario
- Mancomunada indistinta/conjunta: CORE no lo guarda
