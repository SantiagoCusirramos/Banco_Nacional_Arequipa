# DESEMBOLSO: desembolso de créditos (módulo 13, Línea de Créditos)

Módulo del equipo de Desembolso (Rodrigoss06, #71), integrado sobre COREDB. Convierte una aprobación en un
abono en la cuenta de ahorros del titular: el operador verifica el documento, prepara la orden, registra la
identidad y confirma. Puerto 8016. Desarrollo original y documentación de diseño:
https://github.com/Rodrigoss06/Modulo-Desembolso.

**No tiene base propia.** Los datos viven en las tablas `creditos.*` de la base integrada y solo COREDB los
escribe, por sus procedimientos (`backend/COREDB/CONTRATO_CREDITOS.md` §4). La confirmación es una sola
operación de la base: abona la cuenta, crea el crédito con su calendario OFICIAL (copia del de Solicitud,
RN-SOL-006) y deja la solicitud DESEMBOLSADA. Por eso ya no hay llamadas a Evaluación, a CUENTAS ni a
Cobranza, ni POR_VERIFICAR, outbox o recuperación: si se pierde la respuesta, se repite la confirmación y
COREDB devuelve el mismo crédito y el mismo abono, sin abonar otra vez.

## Flujo

1. **Identidad en ventanilla.** El operador revisa el documento original y a la persona, y lo registra:
   `POST /api/v1/identidad`. COREDB aprueba la verificación solo para un cliente ACTIVO y devuelve su
   `codCliente` y un `idValidacion`, la evidencia de la orden.
2. **Aprobación (CR-INT-04).** `GET /api/v1/aprobaciones?codCliente=…`: las aprobaciones vigentes (última
   ronda, 30 días, sin desembolso) se leen de COREDB, no de Evaluación. `ordenAbierta` dice si ya tienen
   una orden PREPARADA o VALIDADA.
3. **Cuenta.** `GET /api/v1/clientes/{codCliente}/cuentas?moneda=PEN`: solo admite el abono una cuenta de
   ahorros INDIVIDUAL, ACTIVA, del titular y en la moneda del crédito. COREDB lo vuelve a comprobar al
   preparar, al cambiar la cuenta y al confirmar.
4. **Orden.** `POST /api/v1/ordenes` con `X-Idempotency-Key` (UUID): el importe es el monto aprobado. La
   misma llave con el mismo cuerpo devuelve la misma orden (200); con otro cuerpo, 409.
5. **Validación.** `POST /api/v1/ordenes/{id}/validaciones` con `tipo: IDENTIDAD`, `resultado: APROBADA` y
   el `idValidacion` del paso 1. Con la identidad y la cuenta aprobadas, la orden queda VALIDADA.
6. **Confirmación.** `POST /api/v1/ordenes/{id}/confirmacion`: 201 con `codCredito`,
   `uuidTransaccionAbono` y `fechaEfectiva`; repetirla, 200 con lo mismo. La constancia la arma la pantalla
   con el detalle de la orden.

**Vigencia de la identidad (T7, valor por omisión del equipo):** la verificación debe ser del mismo día
(fecha de Lima). Una de otro día no valida la orden, y una orden validada ayer no se confirma hoy: hay que
verificar el documento otra vez.

## Rutas

| Ruta | Quién | En COREDB |
|---|---|---|
| `GET /api/v1/sesion` | `VER_CREDITO` o `DESEMBOLSAR_CREDITO` | `GET /coredb/auth/me` |
| `POST /api/v1/identidad` | `DESEMBOLSAR_CREDITO` (y `VALIDAR_IDENTIDAD` en COREDB) | `POST /coredb/clientes/validaciones/documento` |
| `GET /api/v1/aprobaciones` | `VER_CREDITO` o `DESEMBOLSAR_CREDITO` | `GET /coredb/creditos/aprobaciones` (`svc-desembolso`) |
| `GET /api/v1/clientes/{cod}/cuentas` | `DESEMBOLSAR_CREDITO` | `GET /coredb/cuentas` (`svc-desembolso`) |
| `POST /api/v1/ordenes`, `PUT …/{id}/cuenta`, `POST …/{id}/validaciones`, `…/confirmacion`, `…/rechazo` | `DESEMBOLSAR_CREDITO` | `/coredb/creditos/ordenes…` |
| `GET /api/v1/ordenes`, `GET /api/v1/ordenes/{id}` | `VER_CREDITO` | Monitor y detalle; el detalle agrega el calendario de la solicitud |
| `GET /api/v1/conciliacion` | `GENERAR_REPORTES` | `GET /coredb/creditos/conciliacion/desembolsos` |

Lo que hace una persona va con **su token de COREDB**, que Desembolso reenvía: COREDB vuelve a comprobar el
permiso y la bitácora de la orden registra al operador. El usuario de servicio `svc-desembolso`
(`SERVICIO:DESEMBOLSO`: `VER_CREDITO`, `VER_CUENTA`) solo lee las aprobaciones y las cuentas, y sirve para
`/salud`. Un usuario de servicio no entra en las rutas del personal. Errores como COREDB:
`{"error": {"code", "message"}}`, con sus códigos (`APROBACION_NO_VIGENTE`, `CUENTA_NO_ELEGIBLE`,
`VALIDACION_NO_ADMITIDA`, …). Especificación: `openapi.json` (`python -m DESEMBOLSO.scripts.exporta_openapi`).

| Rol de COREDB | Perfil en Desembolso |
|---|---|
| OPERADOR | Operador de agencia: verifica, prepara, valida, confirma y rechaza |
| ADMINISTRADOR | Supervisor: lo mismo, y concilia (COREDB no tiene un rol de supervisor; pregunta T6 del equipo) |
| AUDITOR | Consulta y concilia |

## Configuración

| Variable | Qué es |
|---|---|
| `DESEMBOLSO_COREDB_SECRETO` | Secreto de `svc-desembolso`. En el producto lo crea `coredb-init` con `COREDB.scripts.crear_servicio` |
| `DESEMBOLSO_COREDB_USUARIO` | `svc-desembolso` por omisión |
| `COREDB_URL` | COREDB, a través del Bus: `http://bus:8018/bus/coredb` en compose y k8s |
| `BUS_TOKEN` | Credencial del módulo ante el Bus (`X-Bus-Token`; en el producto, `BUS_TOKEN_DESEMBOLSO`) |

## Ejecutar y probar

Con el producto: `./bna up` (pantallas en http://localhost:3000/desembolso, API en http://127.0.0.1:8016/docs).

```bash
backend/DESEMBOLSO/scripts/pruebas_integracion.sh      # en contenedores: bna-core-db y COREDB nuevos
```

Las pruebas usan la base integrada y COREDB reales: aprobación → orden → validación → confirmación (un solo
abono, el crédito con su calendario OFICIAL, la solicitud DESEMBOLSADA), confirmar otra vez sin otro abono,
una cuenta mancomunada y una identidad de otro día rechazadas, y los permisos de cada rol. Al terminar no
quedan contenedores ni volúmenes.

## Pendiente

- Reversión: CUENTAS no tiene extorno y el modelo deja `solicitud_reversion` sin uso en esta fase.
- Antifraude y eventos a Seguridad (CR-INT-10): Seguridad todavía no los ofrece; la orden admite las
  validaciones AUTORIZACION y ANTIFRAUDE para cuando existan.
- Decisiones del equipo adoptadas, revisables: supervisor = ADMINISTRADOR (T6), identidad del mismo día (T7)
  ([`Documents/decisiones-del-equipo.md`](../../Documents/decisiones-del-equipo.md)).
