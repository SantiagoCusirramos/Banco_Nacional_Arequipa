# TARJETAS

Modulo de Tarjetas de debito. No tiene base de datos propia: valida y llama a COREDB (`/coredb/tarjetas`,
puerto 8012), que guarda las tarjetas en el esquema `tarjetas` de la base integrada. Sigue el mismo
estandar de respuestas que CUENTAS (DOC-ITIL-02).

## Endpoints

| Metodo | Ruta | Llama a COREDB |
|---|---|---|
| GET | /api/v1/tarjetas/cliente/{cod_cliente} | GET /coredb/tarjetas?cod_cliente= |
| GET | /api/v1/tarjetas/{id_tarjeta} | GET /coredb/tarjetas/{id} |
| POST | /api/v1/tarjetas/emision | POST /coredb/tarjetas |
| POST | /api/v1/tarjetas/{id_tarjeta}/bloqueo | POST /coredb/tarjetas/{id}/estado |
| POST | /api/v1/tarjetas/{id_tarjeta}/estado | POST /coredb/tarjetas/{id}/estado |
| GET | /health | - |
| GET | /ready | GET /coredb/salud (503 si COREDB no responde) |

Todas exigen `Authorization: Bearer <token>` de COREDB, que se reenvia: COREDB valida el token y el
permiso (`VER_TARJETA`, `CREAR_TARJETA`, `BLOQUEAR_TARJETA`). `X-Correlation-ID` es opcional.

## Reglas

- **El PAN no pasa por el modulo.** La emision recibe el cliente, la cuenta, el BIN y, si se quiere, las
  fechas y los ultimos cuatro digitos; a COREDB se envia un token aleatorio en lugar del PAN. Un campo
  desconocido, como `pan`, se rechaza y su valor no se devuelve.
- Sin fechas, la tarjeta se emite hoy y vence en cuatro anos. El vencimiento debe ser posterior a la
  emision (RN-TAR-003), y cada tarjeta se devuelve tambien con `vencimiento_mm_aa` y
  `numero_enmascarado`.
- El bloqueo exige un motivo, que queda en el historial de la tarjeta.
- El desbloqueo (de BLOQUEADA a ACTIVA) lo rechaza COREDB: es de Seguridad.

## Respuestas (ITIL-02)

Exito: `{success, status_code, message, data, metadata{uuid_transaccion, timestamp, modulo_emisor, tiempo_ejecucion_ms}}`

Error: `{success:false, status_code, error_code, message, details, metadata}`. 422 se devuelve como 400.

| Origen | error_code | HTTP |
|---|---|---|
| COREDB TARJETA_NO_ENCONTRADA | ERR-TAR-NO-ENCONTRADA | 404 |
| COREDB CLIENTE_NO_ENCONTRADO | ERR-CLI-NO-ENCONTRADO | 404 |
| COREDB BNA-DESBLOQUEO | ERR-TAR-DESBLOQUEO-NO-PERMITIDO | 403 |
| COREDB ERR-TAR-007 o RN-TOP-001 | ERR-TAR-TOPE-EXCEDIDO | 400 |
| COREDB ERR-TAR-001 a 009 | el mismo codigo | 400 |
| COREDB PERMISO_DENEGADO | ERR-TAR-PERMISO-DENEGADO | 403 |
| Identificador que no es UUID | ERR-TAR-ID-INVALIDO | 400 |
| COREDB caido | ERR-COR-NO-DISPONIBLE | 503 |
| COREDB no responde | ERR-TAR-TIMEOUT-CORE | 504 |

## Pendiente

Autorizar una operacion, extornarla y validar una clave o una coordenada de la tarjeta matriz
necesitan procedimientos en la base que el rol de COREDB pueda ejecutar; hoy no existen.

## Ejecutar

Desde `backend/`, con COREDB levantado:

```bash
uvicorn TARJETAS.main:app --port 8002
python -m pytest TARJETAS/tests
```

Con Docker, `./bna up` lo levanta en http://127.0.0.1:8002/docs.
