# COBRANZA

Módulo de Cobranza (módulo 14, línea Créditos): el cliente paga las cuotas de un crédito ya desembolsado, por cualquier canal, en cualquier momento y en montos fraccionados. Estado: **laboratorio**, como SOL. Tiene base propia (`bna_cobranza` en `db-aux`) y no toca la base integrada; el cobro sí es real, por el módulo CUENTAS del producto.

Swagger: http://127.0.0.1:8014/docs (botón **Authorize** con una de sus claves). Especificación publicada: [`openapi.json`](openapi.json) (RNF-23).

## Cómo se conecta

| Interfaz | Quién llama | Ruta | Estado |
|---|---|---|---|
| CR-INT-06 | Desembolso → Cobranza | `POST /cr-int-06/obligaciones` | Lista para que Desembolso la llame. Mientras no exista, se llama a mano o con la prueba de integración |
| CR-INT-07 | Cobranza → CUENTAS | `POST /api/v1/cuentas/retiro` de CUENTAS | **Real**: debita la cuenta de ahorros por CUENTAS, que registra el movimiento en COREDB |
| CR-INT-08 | Home Banking → Cobranza | `POST /cr-int-08/pagos` | **En uso**: la pantalla "Pagar cuota" del frontend (`frontend/app/pagar-cuota`) la llama por su puente `/api/cobranza` |
| CR-INT-10 | Cobranza → Seguridad/Auditoría | `GET /auditoria` | Local: los eventos quedan en la tabla `EVENTO_AUDITORIA` de Cobranza |

Desembolso y Home Banking entran con la clave del rol `INTEGRACION_BUS` (`COBRANZA_API_KEY_INTEGRACION` en `.env`). Las consultas usan `COBRANZA_LEER` y las acciones de operación `COBRANZA_EJECUTAR`.

### CR-INT-07: cómo cobra la cuota

1. `cobranza-init` crea en COREDB el usuario de servicio `svc-cobranza` (rol `SERVICIO`, módulo `COBRANZA`), como pide [COREDB](../COREDB/README.md), y guarda su secreto en el volumen `cobranza-datos`. Sus permisos están en `COREDB/permisos.py`: `VER_CUENTA` y `REGISTRAR_MOVIMIENTO`.
2. Cobranza inicia sesión con ese usuario y llama a `POST /api/v1/cuentas/retiro` con:
   - `Authorization: Bearer <token>`. Ante un 401 vuelve a iniciar sesión una vez.
   - `X-Idempotency-Key`: un UUIDv4 derivado de la referencia del pago. La misma referencia da siempre la misma llave, así que un reintento no cobra dos veces (RN-INT-CR-006).
   - `X-Channel-ID: WEB` (Home Banking, `HB` en el CORE; tope de 10 000 PEN diarios). Se cambia con `COBRANZA_CANAL_CUENTAS`.
   - `X-Request-Timestamp` y `X-Correlation-ID`.
   - Cuerpo: `num_cuenta`, `monto` como texto (`"150.00"`), `moneda` y una glosa con `(ref. <referencia>)`.
3. La respuesta decide el pago:

| CUENTAS responde | Pago en Cobranza | Cuota |
|---|---|---|
| 201 | `CONFIRMADO` | Se aplica el pago |
| 4xx (p. ej. `ERR-CTA-FONDOS-INSUFICIENTES`, `ERR-CTA-BLOQUEADA`) | `RECHAZADO`, con el `error_code` en `motivo` | No cambia (RN-COB-009) |
| 5xx o sin respuesta (p. ej. 504 `ERR-CTA-OPERACION-NO-CONFIRMADA`) | `PENDIENTE` (INC-01) | No cambia |

Un pago `PENDIENTE` se resuelve con `POST /pagos/{referencia}/resolver`. Cobranza **no vuelve a cobrar**: busca la referencia en los movimientos de la cuenta (`GET /api/v1/cuentas/{num_cuenta}/movimientos`). Si el cargo está, el pago queda `CONFIRMADO`; si no está, no se cobró y queda `RECHAZADO`.

## Mora

La calcula el núcleo; Cobranza solo la registra y la refleja: RGN-15 y RF-COB-06 de *Requerimientos y Especificaciones Generales BNA*, y la tabla `creditos.mora` de la base integrada. Mientras CORE no la envíe, se registra con `POST /creditos/{codCredito}/cuotas/{n}/mora` (rol `COBRANZA_EJECUTAR`) y queda con historial.

## Requerimientos oficiales y rutas

| Requerimiento (Especificaciones Generales) | Ruta |
|---|---|
| RF-COB-01 Consultar saldo de deuda y estado | `GET /creditos/{codCredito}`, `GET /clientes/{idCliente}/creditos` |
| RF-COB-02 Pagos por cualquier canal habilitado | `POST /cr-int-08/pagos` (`idCanal`) |
| RF-COB-03 Pagos en cualquier momento | `POST /cr-int-08/pagos`, sin restricción de fecha |
| RF-COB-04 Pagos fraccionados | `POST /cr-int-08/pagos`: cada abono es un pago; la cuota queda `PARCIAL` |
| RF-COB-05 Aplicar el pago y actualizar el saldo | `POST /cr-int-08/pagos`, `GET /pagos/{referencia}/comprobante` |
| RF-COB-06 Reflejar la mora calculada por el núcleo | `POST` y `GET /creditos/{codCredito}/cuotas/{n}/mora`, `GET /creditos/{codCredito}/monto-a-pagar` |
| RF-COB-07 Estado del crédito: al día o en mora | `GET /creditos/{codCredito}`, `POST /creditos/{codCredito}/recalcular-estado` |
| RF-COB-08 Conciliación diaria | `GET /conciliacion` |

## Configuración

`compose.yaml` la pone toda; las claves salen de `.env` (`./bna up` las genera).

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | `mysql://cobranza_user:...@db-aux:3306/bna_cobranza`. Las tablas se crean al arrancar |
| `CUENTAS_MODO=BNA`, `CUENTAS_URL`, `COREDB_URL` | CUENTAS real. Sin `CUENTAS_MODO` ni `CUENTAS_URL`, el cobro es simulado (pruebas) |
| `COBRANZA_SVC_ARCHIVO` | Archivo con el usuario de servicio. También se puede dar `COBRANZA_SVC_USUARIO` y `COBRANZA_SVC_SECRETO` |
| `API_KEY_COBRANZA_LEER`, `API_KEY_COBRANZA_EJECUTAR`, `API_KEY_INTEGRACION_BUS` | Claves `X-API-Key` de los tres roles |

## Pruebas

```bash
./bna test                                      # incluye la suite COBRANZA
cd backend && python -m pytest COBRANZA/tests   # solo Cobranza, sin MySQL ni red
```

Las pruebas usan SQLite en memoria y un CUENTAS simulado por HTTP (`tests/test_cuentas_bna.py`, `tests/test_api_cuentas_bna.py`).

Con el producto levantado, la prueba de integración cobra de verdad por CUENTAS: registra un cliente, abre dos cuentas, deposita, activa un crédito, paga una cuota, repite el pago y paga desde una cuenta sin saldo.

```bash
docker compose exec -T -e BNA_ADMIN_PASSWORD="$(grep '^BNA_ADMIN_PASSWORD=' .env | cut -d= -f2-)" \
    cobranza python -m COBRANZA.scripts.prueba_integracion
```

La colección [`postman/`](postman/) apunta a `http://127.0.0.1:8014`. Se escribió para el modo simulado: sus cuentas de ejemplo no existen en COREDB, así que con CUENTAS real esos pagos salen `RECHAZADO`.

## Pendiente

- Trabajar sobre las tablas de Cobranza que ya tiene la base integrada (`creditos.credito`, `pago`, `aplicacion_pago`, `mora`, `evento_auditoria`), en vez de la base propia. Hace falta que COREDB ofrezca rutas de créditos y pagos.
- Recibir los créditos de Desembolso (la bandeja `creditos.evento_entrega`) y la mora de CORE cuando existan.
- Enviar la auditoría al módulo de Seguridad cuando publique cómo recibirla.
- Manifiesto de Kubernetes (`k8s/`).
- Decisiones del Comité de Créditos: propietario del calendario después del desembolso y tratamiento de un pago mayor a la cuota (hoy se rechaza).
