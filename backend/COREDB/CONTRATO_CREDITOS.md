# Contrato de COREDB para la línea de créditos

**Estado:** las secciones 3 (Evaluación), 4 (Desembolso) y 5 (Cobranza) están implementadas en `backend/COREDB`. EVALUACIÓN (#70) ya usa la sección 3 (`backend/EVALUACION`, sin base propia, con el usuario de servicio `svc-evaluacion`); DESEMBOLSO (#71) y COBRANZA (#69) se integran después sobre estas rutas, con la co-autoría de sus autores.
**Qué es:** las operaciones que el CORE ofrece a Evaluación, Desembolso y Cobranza en `backend/COREDB`, sobre las tablas `creditos.*` de la base integrada (`database/`, desde `bd-v1.4-mysql`). La especificación exacta está en `openapi.json` y en `/docs`.
**De dónde sale:** la propuesta publicada en #70, #71 y #69 el 2026-11-16 (Con autorización de Santiago Cusirramos), para @Rodrigoss06 y @Rocio00006.

## 1. La idea

- Los datos de créditos viven en `creditos.*`, que ya modelan toda la línea. Cada módulo deja su base propia y llama a COREDB.
- COREDB escribe solo por procedimientos de la base. Cada operación es atómica y registra su auditoría dentro.
- **El dinero se mueve dentro de la misma transacción.** Confirmar una orden abona la cuenta, crea el crédito con su calendario OFICIAL y deja la solicitud DESEMBOLSADA, todo junto. Pagar una cuota debita la cuenta y aplica el pago, también junto. Si se pierde la respuesta HTTP, se repite la llamada (con la misma llave en el pago) sin mover el dinero dos veces. Por eso no hacen falta POR_VERIFICAR, el pago PENDIENTE ni sus procesos de recuperación.
- **Las llamadas entre módulos desaparecen.** CR-INT-04 (Desembolso → Evaluación) y CR-INT-06 (Desembolso → Cobranza) pasan a ser lecturas a COREDB; CR-INT-05 y CR-INT-07 (abonos y débitos por CUENTAS) los hace COREDB. CR-INT-02 y CR-INT-03 (con SOL) siguen.

## 2. Convenciones

Las mismas de [`CONTRATO_CLIENTES.md`](CONTRATO_CLIENTES.md) §1, con estas diferencias:

- **Campos en camelCase** (`idSolicitud`, `montoSolicitado`), como el contrato con SOL. El nombre en snake_case se rechaza como campo desconocido (422).
- **Montos:** texto decimal en las respuestas (`"15000.00"`); en las peticiones se aceptan texto o número, con 2 decimales como máximo. Las tasas, con 4 decimales y como fracción (`"0.2200"` es 22 %).
- **Fechas:** `AAAA-MM-DD`; fechas y horas en UTC con zona.
- **Identificadores:**
  - `idSolicitud`: el UUID de SOL.
  - `codCliente`: el `cod_cliente` de COREDB (hasta 12, letras y dígitos). La base exige que el cliente exista y pueda operar.
  - `idEvaluacion`, `idOrden` e `idPago`: UUID.
  - `codigoOrden`: `DES-AAAA-NNNNNN`; `codCredito`: `CRE-AAAA-NNNNNN`, que nace al confirmar el desembolso.
- **Repeticiones:** el expediente es idempotente por `idSolicitud` + `versionSolicitud` + contenido (sección 3.1). La evaluación, la decisión y la revocación se hacen una sola vez: repetirlas responde 422 y el resultado está en el detalle de la solicitud. Preparar una orden lleva `X-Idempotency-Key` (UUID) y el pago, su `referencia`: la misma llave con el mismo cuerpo responde 200 con el resultado original y con otro cuerpo, 409 `IDEMPOTENCIA_CONFLICTO`. Confirmar otra vez una orden responde 200 con el mismo crédito y el mismo abono.
- **Mensajes:** ninguno repite cuentas, documentos, montos ni `codCliente`.
- **Credenciales:** cada módulo tiene su usuario de servicio (`svc-evaluacion`, `svc-desembolso`, `svc-cobranza`), que un administrador crea con `POST /coredb/usuarios/servicios` (`modulo`: `EVALUACION`, `DESEMBOLSO` o `COBRANZA`). Lo que hace una persona (analista, operador) va con **el token de esa persona**, que el módulo reenvía: así la auditoría registra a la persona.

| Usuario de servicio | Acciones |
|---|---|
| `SERVICIO:EVALUACION` | `CREAR_SOLICITUD_CREDITO`, `VER_CREDITO` |
| `SERVICIO:DESEMBOLSO` | `VER_CREDITO`, `VER_CUENTA` |
| `SERVICIO:COBRANZA` | `VER_CREDITO`, `CONSULTAR_DEUDA`, `REGISTRAR_MORA` |

Acciones propias de COREDB: `DESEMBOLSAR_CREDITO` (OPERADOR, ADMINISTRADOR) y `REGISTRAR_MORA` (ADMINISTRADOR, `SERVICIO:COBRANZA`). Las de evaluación son las de CORE: `EVALUAR_CREDITO` y `APROBAR_CREDITO` (ANALISTA, ADMINISTRADOR), `VER_CREDITO`. Las de cobranza también: `REGISTRAR_PAGO` (OPERADOR, ADMINISTRADOR) y `CONSULTAR_DEUDA` (todos los roles de personas y `svc-cobranza`).

## 3. Evaluación (implementada)

| Ruta | Permiso | Respuesta |
|---|---|---|
| `POST /coredb/creditos/solicitudes` | `CREAR_SOLICITUD_CREDITO` | 201 acuse; 200 si es el mismo expediente |
| `GET /coredb/creditos/solicitudes?estado=&codCliente=&limite=&offset=` | `VER_CREDITO` | Bandeja |
| `GET /coredb/creditos/solicitudes/{idSolicitud}` | `VER_CREDITO` | Detalle: calendario vigente, evaluaciones, historial |
| `POST /coredb/creditos/solicitudes/{idSolicitud}/evaluaciones` | `EVALUAR_CREDITO` | Resultado de RN-EVA-002-P |
| `POST /coredb/creditos/evaluaciones/{idEvaluacion}/decision` | `APROBAR_CREDITO` | Decisión del analista |
| `POST /coredb/creditos/solicitudes/{idSolicitud}/revocacion` | `APROBAR_CREDITO` | Solicitud RECHAZADA |
| `GET /coredb/creditos/aprobaciones?codCliente=&idSolicitud=` | `VER_CREDITO` | Aprobaciones que admiten desembolso |
| `POST /coredb/empleados` | `REGISTRAR_EMPLEADO` | 201 el empleado (sin el nombre); 409 `EMPLEADO_DUPLICADO` o `USUARIO_NO_ADMITIDO` |
| `POST /coredb/creditos/analistas` | `CREAR_USUARIO` | 201 `{idAnalista}` |
| `GET /coredb/catalogos/creditos` | autenticado | Catálogos |

### 3.1 Expediente de SOL (CR-INT-02)

`POST /coredb/creditos/solicitudes`, con el usuario de servicio de Evaluación:

```json
{
  "idSolicitud": "0b6f…", "versionSolicitud": 1, "codCliente": "C001",
  "montoSolicitado": "15000.00", "moneda": "PEN", "plazoMeses": 12,
  "condicionPagoDoble": false, "destino": "Capital de trabajo",
  "calendario": {
    "metodo": "FRANCES", "tasa": "0.2200",
    "cuotas": [{"numeroCuota": 1, "fechaVencimiento": "2027-01-15", "saldoInicial": "15000.00",
                "amortizacion": "1130.12", "interes": "275.00", "cuotaTotal": "1405.12",
                "saldoFinal": "13869.88"}]
  }
}
```

- La base comprueba el calendario: tantas cuotas como `plazoMeses`, números consecutivos desde 1, fechas crecientes, `cuotaTotal = amortizacion + interes`, `saldoFinal = saldoInicial − amortizacion`, la primera cuota parte del monto y la última termina en 0. Se guarda como calendario PRELIMINAR, sin cambios (RN-SOL-006).
- Respuesta: `{idSolicitud, versionSolicitud, ronda, idEvaluacion, estado}`. Con ella Evaluación arma el acuse para SOL. `idEvaluacion` es determinista (`creditos.fn_id_evaluacion`): es el id que tendrá la evaluación de esa ronda, aunque todavía no exista.
- **Versiones:** cada versión nueva abre una ronda nueva con otro calendario (el anterior queda HISTORICO). Se acepta solo mientras la solicitud está EN_EVALUACION y su ronda vigente no está evaluada.
- **Repeticiones:** la misma versión con el mismo contenido responde 200 con el mismo acuse; con otro contenido, 409 `IDEMPOTENCIA_CONFLICTO`. No hace falta `X-Idempotency-Key`.
- `destino` forma parte del contenido (de la huella), pero no se guarda: lo conserva SOL.
- Errores: 422 `CLIENTE_NO_HABILITADO` (no existe o no puede operar), `CALENDARIO_INVALIDO`, `SOLICITUD_NO_ADMITIDA` (versión no posterior, ronda ya evaluada, solicitud en estado final, expediente de otro cliente, moneda desconocida).

### 3.2 Bandeja y detalle

- La bandeja devuelve, de la más reciente a la más antigua: `idSolicitud`, `versionSolicitud`, `ronda`, `codCliente`, `montoSolicitado`, `moneda`, `plazoMeses`, `condicionPagoDoble`, `estado`, `fechaCreacion`, `numeroCuotas`, `totalCuotas`, `primerVencimiento`. Sin nombres ni documentos del cliente. `estado` es REGISTRADA, EN_EVALUACION, APROBADA, RECHAZADA o DESEMBOLSADA.
- El detalle agrega `calendario` (`tipo` PRELIMINAR u OFICIAL, `metodo`, `tasa` y sus `cuotas`), `evaluaciones` por ronda (`score`, `limite`, `regla`, `resultadoRegla`, `ingresoMensual`, `deudaMensual`, `decision`, `comentario`, `idAnalista`, `resultado`, `esUltima`) e `historial` de estados (`estado`, `fechaHora`, `actor`, `motivo`). 404 `SOLICITUD_NO_ENCONTRADA`.

### 3.3 Evaluación (RN-EVA-002-P)

`POST …/solicitudes/{idSolicitud}/evaluaciones`, con el token del analista:
`{versionSolicitud, ingresoMensual, deudaMensual, riesgo: BUENO|REGULAR|ALTO, verificada}`.

- La regla es la de #70 (`motor.py`), sin cambios: capacidad = 35 % del ingreso − la deuda; límite = capacidad × plazo × factor de riesgo (1; 0,75; 0,4), al céntimo. Score: 850, 650 o 400 según el riesgo.
- COREDB calcula el score y el límite; **la base elige la regla** por el ratio monto / límite con los umbrales de `creditos.regla_evaluacion`: hasta 80 % R-A APROBADO, hasta 100 % R-B OBSERVADO, más de 100 % (o límite 0) R-C RECHAZADO.
- Respuesta: `{idEvaluacion, idSolicitud, resultado, regla, score, limite, ratio, estadoSolicitud}`. APROBADO deja la solicitud APROBADA, RECHAZADO la deja RECHAZADA y OBSERVADO la deja EN_EVALUACION para el analista. `ratio` es null si no hay capacidad de pago.
- `verificada: false` → 422 `SITUACION_NO_VERIFICADA`, sin registrar nada.
- Errores: 404 `SOLICITUD_NO_ENCONTRADA`; 422 `SOLICITUD_NO_ADMITIDA` (no está EN_EVALUACION o la versión no es la vigente), `EVALUACION_NO_ADMITIDA` (la ronda ya se evaluó).

### 3.4 Decisión del analista

`POST /coredb/creditos/evaluaciones/{idEvaluacion}/decision` con `{decision: APROBADO|RECHAZADO, comentario}` (10 a 500 caracteres), con el token del analista.

- Solo para una evaluación OBSERVADO de la ronda vigente, y una sola vez. Respuesta: `{idEvaluacion, idSolicitud, decision, estadoSolicitud}`.
- **Quién es analista:** el usuario del token debe estar ligado a un empleado activo (`id_empleado` al crearlo con `POST /coredb/usuarios`) y ese empleado debe estar registrado como analista con `POST /coredb/creditos/analistas {idEmpleado}` (un administrador). Si no, 422 `ANALISTA_REQUERIDO`. El empleado lo registra un administrador con `POST /coredb/empleados` (permiso `REGISTRAR_EMPLEADO`, solo ADMINISTRADOR), que también lo liga a un usuario existente (`id_usuario`): una persona sin empleado. Orden: usuario ANALISTA, empleado ligado, `POST /coredb/creditos/analistas`.
- Errores: 404 `EVALUACION_NO_ENCONTRADA`; 422 `EVALUACION_NO_ADMITIDA` (no es OBSERVADO, ya tiene decisión o no es la vigente).

### 3.5 Revocación y aprobaciones

- `POST …/solicitudes/{idSolicitud}/revocacion {motivo}` pasa una solicitud APROBADA a RECHAZADA, con el motivo en el historial, si no tiene un desembolso confirmado. Sus órdenes abiertas quedan RECHAZADA. 422 `SOLICITUD_NO_ADMITIDA` en otro estado; 404 si no existe.
- `GET /coredb/creditos/aprobaciones` devuelve las aprobaciones que todavía admiten un desembolso: última ronda, aprobada por la regla o por el analista, sin orden confirmada y dentro de los 30 días (`vigenteHasta`). Campos: `idEvaluacion`, `idSolicitud`, `codCliente`, `ronda`, `monto`, `moneda`, `plazoMeses`, `limiteAprobado`, `fechaAprobacion`, `vigenteHasta`, `idCalendario`. El calendario está en el detalle de la solicitud.

### 3.6 Catálogo

`GET /coredb/catalogos/creditos`: `estadosSolicitud`, `reglas` (con `ratioMin` y `ratioMax` en %), `metodosAmortizacion`, `tiposValidacion`, `estadosOrden`, `estadosCuota`, `estadosCredito`, `canalesDesembolso` y `vigenciaAprobacionDias`.

**Qué cambia para Evaluación al integrarse:** se quita `bna_evaluacion`; la pantalla `/evaluacion` sigue sobre estas rutas (ids UUID, sin botón OBSERVAR); CR-INT-03 hacia SOL se reenvía sin estado propio, con un `idOperacion` determinista; las rutas `/eva/v1/aprobaciones` dejan de hacer falta.

## 4. Desembolso (implementada)

| Ruta | Permiso | Respuesta |
|---|---|---|
| `POST /coredb/clientes/validaciones/documento` (de Clientes) | `VALIDAR_IDENTIDAD` (también OPERADOR) | `id_validacion`: la evidencia IDENTIDAD |
| `GET /coredb/creditos/aprobaciones?codCliente=` | `VER_CREDITO` | Aprobaciones del cliente (sección 3.5) |
| `POST /coredb/creditos/ordenes` + `X-Idempotency-Key` | `DESEMBOLSAR_CREDITO` | 201 la orden; 200 la misma llave y el mismo cuerpo |
| `PUT /coredb/creditos/ordenes/{idOrden}/cuenta` | `DESEMBOLSAR_CREDITO` | La orden |
| `POST /coredb/creditos/ordenes/{idOrden}/validaciones` | `DESEMBOLSAR_CREDITO` | 201 la orden |
| `POST /coredb/creditos/ordenes/{idOrden}/confirmacion` | `DESEMBOLSAR_CREDITO` | 201 la confirmación; 200 si ya estaba confirmada |
| `POST /coredb/creditos/ordenes/{idOrden}/rechazo` | `DESEMBOLSAR_CREDITO` | La orden |
| `GET /coredb/creditos/ordenes?estado=&codCliente=&idSolicitud=&limite=&offset=` | `VER_CREDITO` | Monitor |
| `GET /coredb/creditos/ordenes/{idOrden}` | `VER_CREDITO` | La orden con `validaciones` y `eventos` |
| `GET /coredb/creditos/conciliacion/desembolsos?fecha=` | `GENERAR_REPORTES` | Por día y moneda |

### 4.1 Preparar

`POST /coredb/creditos/ordenes` con el token del operador y `X-Idempotency-Key` (UUID, obligatoria): `{idEvaluacion, numCuenta, canal?: VEN|HB, idAgencia?}`. El canal es VEN si no se indica.

- `idEvaluacion` es una aprobación de `GET /coredb/creditos/aprobaciones`. El importe es el monto solicitado.
- La cuenta debe ser de ahorros, ACTIVA, INDIVIDUAL, del titular y en la moneda del crédito. COREDB registra la validación CUENTA.
- Se rechaza si la aprobación no está vigente (422 `APROBACION_NO_VIGENTE`), si la primera cuota del calendario ya venció (422 `CALENDARIO_INVALIDO`) o si la aprobación ya tiene una orden abierta (422 `ORDEN_NO_ADMITIDA`). Cuenta no elegible: 422 `CUENTA_NO_ELEGIBLE`.
- La misma llave con el mismo cuerpo responde 200 con la orden (en su estado actual); con otro cuerpo, 409 `IDEMPOTENCIA_CONFLICTO`.
- La orden: `idOrden`, `codigoOrden` (`DES-AAAA-NNNNNN`), `estado`, `motivoRechazo`, `importe`, `moneda`, `numCuenta`, `canal`, `idAgencia`, `idEvaluacion`, `idSolicitud`, `codCliente`, `usuarioPreparacion`, `usuarioConfirmacion`, `uuidTransaccionAbono`, `codCredito`, `fechaCreacion`, `fechaActualizacion`.

### 4.2 Validar y cambiar la cuenta

- `POST …/ordenes/{idOrden}/validaciones` `{tipo: IDENTIDAD|AUTORIZACION|ANTIFRAUDE, resultado: APROBADA|RECHAZADA, referenciaEvidencia, detalle?, venceEn?}`. En IDENTIDAD aprobada, `referenciaEvidencia` es el `id_validacion` de `POST /coredb/clientes/validaciones/documento`, APROBADO para el titular el mismo día (fecha de Lima, decisión 7). Si no, 422 `VALIDACION_NO_ADMITIDA`.
- El estado se deriva de la última validación de cada tipo: IDENTIDAD y CUENTA aprobadas y ninguna rechazada → VALIDADA; si no, PREPARADA.
- `PUT …/ordenes/{idOrden}/cuenta` `{numCuenta}` cambia la cuenta de una orden PREPARADA o VALIDADA y registra otra validación CUENTA. Si la identidad sigue aprobada, la orden sigue VALIDADA.
- En otro estado: 422 `ORDEN_NO_ADMITIDA`. Orden inexistente: 404 `ORDEN_NO_ENCONTRADA`.

### 4.3 Confirmar

`POST …/ordenes/{idOrden}/confirmacion`, sin cuerpo, con el token del operador.

- Solo una orden VALIDADA, con la identidad verificada ese mismo día. En una transacción: revalida la aprobación y la cuenta, registra el movimiento `DESEMBOLSO` en la cuenta, deja la orden CONFIRMADA, crea el calendario OFICIAL (copia del PRELIMINAR vigente, que queda HISTORICO) y el crédito AL_DIA, y deja la solicitud DESEMBOLSADA.
- Respuesta 201: `{idOrden, codigoOrden, estado, codCredito, uuidTransaccionAbono, fechaEfectiva}`. `fechaEfectiva` es la del abono.
- **Sin llave:** confirmar otra vez la misma orden responde 200 con el mismo crédito y el mismo abono, sin otro movimiento. Si se pierde la respuesta, se repite la llamada.
- Errores: 422 `ORDEN_NO_ADMITIDA` (no está VALIDADA), `APROBACION_NO_VIGENTE`, `VALIDACION_NO_ADMITIDA` (identidad de otro día), `CUENTA_NO_ELEGIBLE`; 404 `ORDEN_NO_ENCONTRADA`.

### 4.4 Rechazar, monitor y conciliación

- `POST …/ordenes/{idOrden}/rechazo` `{motivo}` deja RECHAZADA una orden PREPARADA o VALIDADA. La aprobación sigue vigente y admite otra orden.
- `GET /coredb/creditos/ordenes` lista de la más reciente a la más antigua; el detalle agrega `validaciones` (`idValidacion`, `tipo`, `resultado`, `referenciaEvidencia`, `detalle`, `venceEn`, `fecha`) y `eventos` de la bitácora de créditos (`accion`, `resultado`, `actor`, `correlationId`, `detalle`, `fechaHora`).
- `GET /coredb/creditos/conciliacion/desembolsos?fecha=`: `fecha`, `moneda`, `ordenesConfirmadas`, `importeOrdenes`, `importeAbonado`, `ordenesSinAbono`, por día de negocio (Lima). Sin `fecha`, los últimos días.

**Qué cambia para Desembolso al integrarse:** se quitan `bna_desembolso`, los clientes de Evaluación, CUENTAS y Cobranza, POR_VERIFICAR, el outbox y el simulador de Cobranza; las pantallas `/desembolso` siguen sobre estas rutas, con el token del operador. La reversión sigue pendiente (CUENTAS no tiene extorno).

## 5. Cobranza (implementada)

| Ruta | Permiso | Respuesta |
|---|---|---|
| `GET /coredb/creditos?codCliente=&estado=&limite=&offset=` | `CONSULTAR_DEUDA` | Créditos, del más reciente al más antiguo |
| `GET /coredb/creditos/{codCredito}` | `CONSULTAR_DEUDA` | El crédito con `cuotas` y `eventos` |
| `POST /coredb/creditos/{codCredito}/pagos` | `REGISTRAR_PAGO` (OPERADOR, ADMINISTRADOR) | 201 el pago (CONFIRMADO o RECHAZADO); 200 la misma referencia y el mismo cuerpo |
| `GET /coredb/creditos/{codCredito}/pagos?limite=&offset=` | `CONSULTAR_DEUDA` | Los pagos del crédito, del más reciente al más antiguo |
| `GET /coredb/creditos/pagos/{referencia}` | `CONSULTAR_DEUDA` | El comprobante |
| `POST /coredb/creditos/{codCredito}/cuotas/{n}/mora` | `REGISTRAR_MORA` (ADMINISTRADOR, `svc-cobranza`) | 201 el cálculo |
| `GET /coredb/creditos/{codCredito}/cuotas/{n}/mora` | `CONSULTAR_DEUDA` | Los cálculos de la cuota, del más reciente al más antiguo |
| `POST /coredb/creditos/vencimientos` | `REGISTRAR_MORA` | `{fecha, cuotasVencidas, creditosActualizados}` |
| `GET /coredb/creditos/conciliacion/pagos?fecha=` | `GENERAR_REPORTES` | Por día, canal y moneda |

### 5.1 Consultar la deuda

- El crédito: `codCredito`, `estado` (AL_DIA, EN_MORA o CANCELADO), `codCliente`, `idSolicitud`, `idOrden`, `codigoOrden`, `moneda`, `montoDesembolsado`, `fechaDesembolso`, `numeroCuotas`, `cuotasPagadas`, `cuotasVencidas`, `saldoPendiente`, `proximoVencimiento` (la cuota más antigua con saldo; nulo si no queda deuda) y `moraVigente`.
- El detalle agrega `cuotas` (`numeroCuota`, `fechaVencimiento`, `capital`, `interes`, `otrosConceptos`, `cuotaTotal`, `saldoPendiente`, `estado`, `diasAtraso`, `moraVigente`) y `eventos` del crédito y de sus cuotas (`accion`, `resultado`, `numeroCuota`, `actor`, `correlationId`, `detalle`, `fechaHora`).
- `diasAtraso` cuenta desde el vencimiento hasta hoy (Lima) y es 0 si la cuota no tiene saldo o no venció.
- Crédito inexistente: 404 `CREDITO_NO_ENCONTRADO`.

### 5.2 Pagar

`POST /coredb/creditos/{codCredito}/pagos` con el token del operador: `{numCuenta, monto, referencia, canal?: VEN|HB}`. El canal es VEN si no se indica.

- La `referencia` (1 a 40 caracteres: letras, dígitos y `.`, `_`, `:`, `-`) es la llave del pago.
- En una transacción: debita la cuenta (movimiento `DEBITO_CUOTA`), aplica el pago de la cuota más antigua a la más reciente (una cuota queda PARCIAL o PAGADA) y recalcula el crédito (pagar toda la deuda lo deja CANCELADO).
- **Débito rechazado:** sin fondos, con la cuenta no operativa (bloqueada, por ejemplo) o por el tope del canal, el pago queda **RECHAZADO** con su `motivo` (`SALDO_INSUFICIENTE`, `CUENTA_NO_OPERATIVA`, `TOPE_DIARIO_SUPERADO`, `CANAL_NO_ADMITIDO`), sin movimiento y sin tocar las cuotas. Responde 201.
- Respuesta: `idPago`, `codCredito`, `referencia`, `estado`, `motivo`, `monto`, `montoAplicado`, `numCuenta`, `canal`, `uuidTransaccion` (nulo si se rechazó), `fecha`, `aplicaciones` (`[{numeroCuota, montoAplicado}]`), y el `estadoCredito` y el `saldoPendiente` del crédito al responder.
- **Repetir:** la misma referencia con el mismo cuerpo en el mismo crédito responde 200 con el mismo pago, sin debitar otra vez; también si el pago fue RECHAZADO, así que un intento nuevo lleva otra referencia. Con otro cuerpo o en otro crédito: 409 `IDEMPOTENCIA_CONFLICTO`. Dos pagos simultáneos del mismo crédito se ordenan en la base: con fondos para uno solo, uno queda CONFIRMADO y el otro RECHAZADO.
- No se registra nada y responde 422 si el monto supera la deuda total (`PAGO_NO_ADMITIDO`), si la cuenta no es del titular o no está en la moneda del crédito (`CUENTA_NO_ELEGIBLE`) o si el crédito está cancelado (`CREDITO_NO_ADMITIDO`). Crédito inexistente: 404 `CREDITO_NO_ENCONTRADO`.
- `GET /coredb/creditos/pagos/{referencia}` devuelve el pago sin los campos del crédito; si no existe, 404 `PAGO_NO_ENCONTRADO`.

### 5.3 Mora y vencimientos

- `POST …/{codCredito}/cuotas/{n}/mora` `{montoCalculado}` (0 o más) registra un cálculo para una cuota vencida con saldo; si la cuota no existe, no tiene saldo o aún no vence, 422 `CUOTA_NO_ADMITIDA`. Responde `{idMora, codCredito, numeroCuota, montoCalculado, fechaCalculo, diasAtraso, vigente}`. No lleva llave: cada llamada es un cálculo nuevo y queda vigente el último. La mora se muestra en la deuda, pero no se cobra (decisión 5).
- `POST /coredb/creditos/vencimientos` `{fecha?}` (el cuerpo es opcional) marca VENCIDA cada cuota PENDIENTE o PARCIAL que venció antes de `fecha` (hoy, en Lima, si no se indica) y deja cada crédito no cancelado EN_MORA (con una cuota VENCIDA) o AL_DIA. `fecha` no puede ser posterior a hoy: 422 `FECHA_NO_ADMITIDA`. Repetirlo el mismo día no cambia nada. La base lo corre también todos los días a las 00:10 de Lima (`creditos.ev_actualizar_vencimientos`); `svc-cobranza` lo llama como tarea diaria y registra la mora.

### 5.4 Conciliación

`GET /coredb/creditos/conciliacion/pagos?fecha=`: `fecha`, `canal`, `moneda`, `pagosConfirmados`, `importeCobrado` (movimientos `DEBITO_CUOTA`), `importeAplicado` (a cuotas) y `pagosRechazados`, por día de negocio (Lima). Sin `fecha`, todos los días con pagos.

**Qué cambia para Cobranza al integrarse:** se quitan `bna_cobranza`, `X-API-Key` (las personas usan su token y `svc-cobranza` solo hace las tareas diarias), `/cr-int-06/obligaciones` (el crédito ya existe al confirmarse el desembolso), el cliente de CUENTAS y el "resolver PENDIENTE". La pantalla "Pagar cuota" pasa a la sesión del operador. CR-INT-08 (Home Banking) queda sin consumidor.

## 6. Trazabilidad CR-INT-04 a CR-INT-07

| Interfaz | Cómo se cumple | Procedimiento o vista | Ruta |
|---|---|---|---|
| CR-INT-04 Evaluación ↔ Desembolso | (a) Las aprobaciones vigentes se leen de la base, con el calendario PRELIMINAR sin cambios. (b) La confirmación deja la solicitud DESEMBOLSADA en la misma transacción que el abono | `v_aprobacion_api`, `v_calendario_api`, `preparar_orden`, `confirmar_orden` | `GET /coredb/creditos/aprobaciones`, `GET /coredb/creditos/solicitudes/{id}`, `POST …/ordenes/{id}/confirmacion` |
| CR-INT-05 Desembolso → CUENTAS | El abono es un movimiento `DESEMBOLSO` dentro de la confirmación; confirmar otra vez la misma orden devuelve el mismo `uuidTransaccionAbono` | `confirmar_orden` | `POST /coredb/creditos/ordenes`, `PUT …/cuenta`, `POST …/confirmacion` |
| CR-INT-06 Desembolso → Cobranza | La confirmación crea el crédito (AL_DIA) y su calendario OFICIAL, copia del PRELIMINAR; Cobranza lo lee | `confirmar_orden`, `v_credito_api`, `v_cuota_api` | `GET /coredb/creditos`, `GET /coredb/creditos/{codCredito}` |
| CR-INT-07 Cobranza → CUENTAS | El débito es un movimiento `DEBITO_CUOTA` dentro del pago; sin fondos o con la cuenta no operativa, pago RECHAZADO sin movimiento; la `referencia` evita cobrar dos veces | `registrar_pago_cuota`, `v_pago_api` | `POST /coredb/creditos/{codCredito}/pagos`, `GET /coredb/creditos/pagos/{referencia}` |

## 7. Decisiones del equipo (valor por omisión; ninguna bloquea)

1. El analista no puede OBSERVAR: la decisión es APROBADO o RECHAZADO (diccionario de Evaluación). La base admitiría OBSERVADO si el equipo lo decide.
2. Vigencia de la aprobación: 30 días.
3. Revocar una aprobación antes del desembolso: se permite, con motivo.
4. Pago mayor que la cuota: se aplica a las siguientes; se rechaza solo si supera la deuda total.
5. Mora: se registra y se muestra, no se cobra (no hay fórmula ni tasa en las fuentes).
6. Supervisor de Desembolso: ADMINISTRADOR.
7. Vigencia de la verificación de identidad para desembolsar: el mismo día (fecha de Lima).

Siguen abiertos: los umbrales de RN-EVA-002-P (provisionales), el dominio de `resultado_verificacion` y la ratificación de `cod_cliente` como identificador común.
