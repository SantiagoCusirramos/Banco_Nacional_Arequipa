# COBRANZA

Módulo de Cobranza (módulo 14, línea Créditos): el cliente paga las cuotas de un crédito ya desembolsado, por cualquier canal, en cualquier momento y en montos fraccionados. **Integrado sin base propia**: todo se guarda en COREDB (`creditos.*`, [CONTRATO_CREDITOS.md](../COREDB/CONTRATO_CREDITOS.md) §5).

Swagger: http://127.0.0.1:8014/docs (botón **Authorize** con un token de COREDB). Especificación publicada: [`openapi.json`](openapi.json) (RNF-23).

## Cómo se conecta

| Interfaz | Quién llama | Ruta | Estado |
|---|---|---|---|
| CR-INT-06 | Desembolso → COREDB | `POST /coredb/creditos/ordenes/{idOrden}/confirmacion` | El crédito nace en COREDB al confirmar el desembolso; Cobranza solo lo lee |
| CR-INT-07 | Cobranza → COREDB | `POST /coredb/creditos/{codCredito}/pagos` | **Real**: COREDB debita la cuenta y aplica el pago en la misma transacción |
| CR-INT-08 | Home Banking → Cobranza | `POST /cr-int-08/pagos` | La usan la pantalla "Pagar cuota" (`/pagar-cuota`) y el Home Banking (`/homebanking/index.html`) del frontend, por `/api/cobranza`; reenvía a COREDB |

El personal del banco entra con su **token de COREDB** (Bearer), que Cobranza reenvía; la tarea diaria usa el usuario de servicio `svc-cobranza` (rol `SERVICIO`, módulo `COBRANZA`), creado por `coredb-init`.

### CR-INT-07: cómo cobra la cuota

1. El operador llama a `POST /api/v1/creditos/{codCredito}/pagos` con su token de COREDB, indicando `numCuenta`, `monto`, `referencia` y `canal`.
2. Cobranza reenvía la petición a COREDB por el Bus de Servicios (`X-Bus-Token: BUS_TOKEN_COBRANZA`).
3. COREDB, en una sola transacción:
   - Debita la cuenta del titular (movimiento `DEBITO_CUOTA`).
   - Aplica el pago a la cuota más antigua con saldo (y a las siguientes si el monto lo permite).
   - Recalcula el crédito (pagar toda la deuda lo deja `CANCELADO`).
4. La `referencia` (1–40 caracteres) es la llave de idempotencia: la misma referencia con el mismo cuerpo responde **200** con el mismo pago, sin debitar otra vez; con otro cuerpo o en otro crédito, **409** `IDEMPOTENCIA_CONFLICTO`.
5. Si el débito se rechaza (fondos insuficientes, cuenta no operativa, tope del canal), el pago queda **RECHAZADO** con su `motivo`, sin movimiento y sin tocar las cuotas.

No hay base propia, no hay llamada a CUENTAS, no hay pagos `PENDIENTE` ni proceso de "resolver".

## Mora

La mora se **registra y muestra**, pero **no se cobra** (decisión T5 de [`Documents/decisiones-del-equipo.md`](../../Documents/decisiones-del-equipo.md)). Cobranza recibe el cálculo del núcleo y lo guarda en COREDB:

- `POST /api/v1/creditos/{codCredito}/cuotas/{n}/mora` (rol `REGISTRAR_MORA`, también `svc-cobranza`).
- `POST /api/v1/vencimientos` marca las cuotas vencidas y recalcula los créditos; es la tarea diaria de `svc-cobranza`.

## Requerimientos oficiales y rutas

| Requerimiento (Especificaciones Generales) | Ruta |
|---|---|
| RF-COB-01 Consultar saldo de deuda y estado | `GET /api/v1/creditos`, `GET /api/v1/creditos/{codCredito}` |
| RF-COB-02 Pagos por cualquier canal habilitado | `POST /api/v1/creditos/{codCredito}/pagos` (`canal`) |
| RF-COB-03 Pagos en cualquier momento | `POST /api/v1/creditos/{codCredito}/pagos`, sin restricción de fecha |
| RF-COB-04 Pagos fraccionados | `POST /api/v1/creditos/{codCredito}/pagos`: cada abono es un pago; la cuota queda `PARCIAL` |
| RF-COB-05 Aplicar el pago y actualizar el saldo | `POST /api/v1/creditos/{codCredito}/pagos`, `GET /api/v1/pagos/{referencia}` |
| RF-COB-06 Reflejar la mora calculada por el núcleo | `POST/GET /api/v1/creditos/{codCredito}/cuotas/{n}/mora`, `GET /creditos/{codCredito}/monto-a-pagar` |
| RF-COB-07 Estado del crédito: al día o en mora | `GET /api/v1/creditos/{codCredito}`, `POST /api/v1/vencimientos` |
| RF-COB-08 Conciliación diaria | `GET /api/v1/conciliacion` |

## Rutas que conserva la pantalla "Pagar cuota" (formato anterior)

| Ruta | Qué hace |
|---|---|
| `GET /clientes/{idCliente}/creditos` | Créditos con su cronograma (RF-COB-002 / RF-COB-012) |
| `GET /creditos/{codCredito}/monto-a-pagar` | Monto a pagar de la próxima cuota (RF-COB-003) |
| `GET /pagos/{referencia}/comprobante` | Comprobante de un pago confirmado (RN-COB-012) |
| `POST /cr-int-08/pagos` | CR-INT-08: pago desde Home Banking (misma idempotencia por `referenciaTransaccion`) |

## Configuración

`compose.yaml` la pone toda; las claves salen de `.env` (`./bna up` las genera).

| Variable | Para qué |
|---|---|
| `COREDB_URL` | `http://bus:8018/bus/coredb` (por el Bus, fase 2) |
| `BUS_TOKEN` | Credencial de Cobranza ante el Bus (`BUS_TOKEN_COBRANZA`) |
| `COBRANZA_COREDB_USUARIO` | `svc-cobranza` (usuario de servicio en COREDB) |
| `COBRANZA_COREDB_SECRETO` | Secreto del usuario de servicio (lo crea `coredb-init`) |
| `COBRANZA_TIMEOUT_SEG` | Timeout HTTP a COREDB (por omisión 5) |
| `COBRANZA_SESION_CACHE_SEG` | Cuánto recordar el perfil de un token de COREDB (por omisión 30) |

## Pruebas

```bash
./bna test                                      # incluye la suite COBRANZA
cd backend && python -m pytest COBRANZA/tests   # solo Cobranza, sin MySQL ni red
```

Las pruebas unitarias usan un transporte HTTP simulado (`httpx.MockTransport`). Las de integración (`tests/test_flujo.py`, `tests/test_permisos.py`) corren contra COREDB y la base integrada reales (requieren `COBRANZA_TEST_COREDB`, que `scripts/pruebas_integracion.sh` configura).

Con el producto levantado, la prueba de integración cobra por COREDB: registra un cliente, abre una cuenta, deposita, activa un crédito, paga una cuota, repite el pago y paga desde una cuenta sin saldo.

```bash
docker compose exec -T -e BNA_ADMIN_PASSWORD="$(grep '^BNA_ADMIN_PASSWORD=' .env | cut -d= -f2-)" \
    cobranza python -m COBRANZA.scripts.prueba_integracion
```

## Arquitectura

- **Sin base propia**: Cobranza no tiene `bna_cobranza`. Todo persiste en `creditos.*` de la base integrada (subtree `database/` desde `bna-core-db`).
- **Sin X-API-Key / X-Token-Seguridad**: el personal usa su token de COREDB (Bearer); `svc-cobranza` usa su secreto para la tarea diaria.
- **Bus de Servicios (fase 2)**: Cobranza llega a COREDB por `http://bus:8018/bus/coredb` con su credencial `BUS_TOKEN_COBRANZA` (cabecera `X-Bus-Token`).
- **Idempotencia**: la `referencia` del pago evita cobrar dos veces; COREDB la hace cumplir atómicamente.
- **Auditoría**: al reenviar el token de la persona, COREDB registra al operador real en sus eventos.

## Manifiestos de Kubernetes

`k8s/base/cobranza.yaml`: Deployment + Service. El `initContainer` espera a COREDB a través del Bus; las variables vienen del ConfigMap `bna-configuracion` y el Secret `bna-secretos` (`COBRANZA_COREDB_SECRETO`, `BUS_TOKEN_COBRANZA`). En kind no tiene NodePort: se llega por el Bus (`/bus/cobranza`) o por la pantalla `/pagar-cuota` del frontend.

## Decisiones adoptadas

Un pago mayor que la cuota se aplica a las siguientes y se rechaza solo si supera la deuda total (T4); la mora no se cobra (T5). Las dos son revisables: [`Documents/decisiones-del-equipo.md`](../../Documents/decisiones-del-equipo.md).

## Pendiente

- Ratificar en el Comité de Créditos quién es dueño del calendario después del desembolso (hoy, el OFICIAL que COREDB copia del de Solicitud al confirmar).