# DESEMBOLSO: desembolso de créditos (módulo 13, Línea de Créditos)

Servicio SRV-CR-04. Convierte una aprobación de Evaluación en un abono confirmado en la cuenta de
ahorros del titular, entrega a Cobranza la obligación de cobro con el calendario de Solicitud y avisa
a Evaluación que la aprobación ya se usó. Puerto 8016; base propia `bna_desembolso` en `db-aux`.
Desarrollo original y documentación de diseño: https://github.com/Rodrigoss06/Modulo-Desembolso.

## Flujo en el producto

1. El operador busca el crédito por documento o código (`GET /api/v1/creditos-habilitados`): Desembolso
   consulta a Evaluación (CR-INT-04) con su usuario de servicio de COREDB.
2. Prepara la orden (`POST /api/v1/ordenes`, idempotente): guarda la aprobación, el `idSolicitud` y el
   **calendario de SOL tal cual llegó** (RN-SOL-006). No se prepara si falta el calendario o si su primera
   cuota ya venció.
3. Verifica la identidad en ventanilla: registra el número del documento original y se compara con el del
   titular según Evaluación. El módulo Clientes no está en el producto: no hay biometría.
4. Elige la cuenta: CUENTAS devuelve las cuentas del cliente; solo es elegible una cuenta de ahorros
   ACTIVA, INDIVIDUAL, del titular y en la moneda del crédito.
5. Confirma: revalida aprobación, calendario y cuenta, y abona con `POST /api/v1/cuentas/deposito`, canal
   VEN, una sola vez, con una llave UUIDv4 derivada de la orden. Si la respuesta se pierde, la orden queda
   POR_VERIFICAR y se busca el movimiento por la referencia de la glosa, sin volver a abonar.
6. Con el abono confirmado, en la misma transacción quedan dos entregas (outbox):
   - a Cobranza, `POST /cr-int-06/obligaciones` con `codCredito`, `idCliente`, `idSolicitud`, monto, fecha
     del desembolso y `calendarioPagos` (`numeroCuota`, `fechaVencimiento`, `montoCuota` = cuota total);
     un 409 RN-COB-001 es el acuse de una repetición;
   - a Evaluación, `POST /eva/v1/aprobaciones/{id}/desembolso`, que marca la aprobación DESEMBOLSADA.

## Accesos

El personal entra con su token de COREDB, que valida COREDB (`GET /coredb/auth/me`):

| Rol de COREDB | Perfil en Desembolso |
|---|---|
| OPERADOR | Operador de agencia: prepara, verifica y confirma |
| ADMINISTRADOR | Supervisor: monitor, recuperación, entregas, conciliación y reversiones (COREDB no tiene un rol de supervisor; decisión pendiente del Comité) |
| AUDITOR | Solo consulta |

Para llamar a Evaluación y CUENTAS, Desembolso usa su usuario de servicio `svc-desembolso`
(`SERVICIO:DESEMBOLSO` en `COREDB/permisos.py`: `VER_CUENTA` y `REGISTRAR_MOVIMIENTO`), que crea
`desembolso-init` y cuyo secreto queda en el volumen `desembolso-datos`. A Cobranza la llama con su clave
`X-API-Key` de integración.

## Configuración

Variables con prefijo `DESEMBOLSO_` (ver `config.py`). En el producto las pone `compose.yaml`. Cobranza aún
no está en el producto (PR #68): mientras `DESEMBOLSO_COBRANZA_URL` esté vacía, sus entregas esperan sin
gastar intentos. Cuando entre, agregar a `.env`:

```dotenv
DESEMBOLSO_COBRANZA_URL=http://cobranza:8014
DESEMBOLSO_COBRANZA_API_KEY=<el valor de COBRANZA_API_KEY_INTEGRACION>
```

## Base de datos

`sql/esquema.sql`: tablas `des_*`, triggers (máquina de estados, datos financieros y calendario
inmutables, bitácora de solo inserción) y vistas operativas. Lo aplica `scripts/preparar_base.py` en cada
arranque, sin borrar datos. El usuario `desembolso_user` no tiene DELETE en ninguna tabla.

## Pruebas

```bash
backend/DESEMBOLSO/scripts/pruebas_integracion.sh      # en contenedores, contra un MySQL 8.4 nuevo
DESEMBOLSO_TEST_MYSQL=mysql+pymysql://root:clave@127.0.0.1:3306 python -m pytest DESEMBOLSO/tests   # desde backend/
```

`tests/simulador.py` imita los contratos reales de COREDB, Evaluación, CUENTAS y Cobranza, y permite
inyectar fallas: respuesta perdida, rechazo de la cuenta, caídas, Cobranza con ids de 20 caracteres.
Los escenarios cubren duplicidad, concurrencia, recuperación sin doble abono, entregas, conciliación,
permisos y triggers.

## Pendiente

- Reversión: deshabilitada; CUENTAS no ofrece extorno (requiere un cambio en el CORE).
- Antifraude y eventos a Seguridad (CR-INT-10): Seguridad todavía no los ofrece a los módulos; la bitácora
  local es la fuente de verdad.
- Comité: supervisor = ADMINISTRADOR, `cod_cliente` de COREDB como identificador común, ratificar que SOL
  arma el calendario. Cobranza: ampliar `idSolicitud` e `idCliente` a 36 caracteres.
- Kubernetes (`k8s/`).
