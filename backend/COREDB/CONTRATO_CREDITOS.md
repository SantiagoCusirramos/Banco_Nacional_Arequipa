# Contrato de COREDB para la línea de créditos

**Estado:** la sección 3 (Evaluación) está implementada en `backend/COREDB`. Las secciones 4 (Desembolso) y 5 (Cobranza) son la propuesta publicada para los equipos y se implementan en los PR siguientes; pueden cambiar en detalle. Los módulos EVALUACIÓN (#70), DESEMBOLSO (#71) y COBRANZA (#69) se integran después sobre estas rutas, con la co-autoría de sus autores.
**Qué es:** las operaciones que el CORE ofrece a Evaluación, Desembolso y Cobranza en `backend/COREDB`, sobre las tablas `creditos.*` de la base integrada (`database/`, desde `bd-v1.4-mysql`). La especificación exacta está en `openapi.json` y en `/docs`.
**De dónde sale:** la propuesta publicada en #70, #71 y #69 el 2026-11-16 (Con autorización de Santiago Cusirramos), para @Rodrigoss06 y @Rocio00006.

## 1. La idea

- Los datos de créditos viven en `creditos.*`, que ya modelan toda la línea. Cada módulo deja su base propia y llama a COREDB.
- COREDB escribe solo por procedimientos de la base. Cada operación es atómica y registra su auditoría dentro.
- **El dinero se mueve dentro de la misma transacción.** Confirmar una orden abona la cuenta, crea el crédito con su calendario OFICIAL y deja la solicitud DESEMBOLSADA, todo junto. Pagar una cuota debita la cuenta y aplica el pago, también junto. Si se pierde la respuesta HTTP, se reintenta con la misma llave sin mover el dinero dos veces. Por eso no hacen falta POR_VERIFICAR, el pago PENDIENTE ni sus procesos de recuperación.
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
- **Repeticiones:** el expediente es idempotente por `idSolicitud` + `versionSolicitud` + contenido (sección 3.1). La evaluación, la decisión y la revocación se hacen una sola vez: repetirlas responde 422 y el resultado está en el detalle de la solicitud. Las escrituras de dinero (secciones 4 y 5) llevan llave.
- **Mensajes:** ninguno repite cuentas, documentos, montos ni `codCliente`.
- **Credenciales:** cada módulo tiene su usuario de servicio (`svc-evaluacion`, `svc-desembolso`, `svc-cobranza`), que un administrador crea con `POST /coredb/usuarios/servicios` (`modulo`: `EVALUACION`, `DESEMBOLSO` o `COBRANZA`). Lo que hace una persona (analista, operador) va con **el token de esa persona**, que el módulo reenvía: así la auditoría registra a la persona.

| Usuario de servicio | Acciones |
|---|---|
| `SERVICIO:EVALUACION` | `CREAR_SOLICITUD_CREDITO`, `VER_CREDITO` |
| `SERVICIO:DESEMBOLSO` | `VER_CREDITO`, `VER_CUENTA` |
| `SERVICIO:COBRANZA` | `VER_CREDITO`, `CONSULTAR_DEUDA`, `REGISTRAR_MORA` |

Acciones propias de COREDB: `DESEMBOLSAR_CREDITO` (OPERADOR, ADMINISTRADOR) y `REGISTRAR_MORA` (ADMINISTRADOR, `SERVICIO:COBRANZA`). Las de evaluación son las de CORE: `EVALUAR_CREDITO` y `APROBAR_CREDITO` (ANALISTA, ADMINISTRADOR), `VER_CREDITO`.

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
- **Quién es analista:** el usuario del token debe estar ligado a un empleado activo (`id_empleado` al crearlo con `POST /coredb/usuarios`) y ese empleado debe estar registrado como analista con `POST /coredb/creditos/analistas {idEmpleado}` (un administrador). Si no, 422 `ANALISTA_REQUERIDO`. Los empleados (`core.empleado`) los carga hoy el administrador de la base: COREDB no tiene una ruta para crearlos.
- Errores: 404 `EVALUACION_NO_ENCONTRADA`; 422 `EVALUACION_NO_ADMITIDA` (no es OBSERVADO, ya tiene decisión o no es la vigente).

### 3.5 Revocación y aprobaciones

- `POST …/solicitudes/{idSolicitud}/revocacion {motivo}` pasa una solicitud APROBADA a RECHAZADA, con el motivo en el historial, si no tiene un desembolso confirmado. Sus órdenes abiertas quedan RECHAZADA. 422 `SOLICITUD_NO_ADMITIDA` en otro estado; 404 si no existe.
- `GET /coredb/creditos/aprobaciones` devuelve las aprobaciones que todavía admiten un desembolso: última ronda, aprobada por la regla o por el analista, sin orden confirmada y dentro de los 30 días (`vigenteHasta`). Campos: `idEvaluacion`, `idSolicitud`, `codCliente`, `ronda`, `monto`, `moneda`, `plazoMeses`, `limiteAprobado`, `fechaAprobacion`, `vigenteHasta`, `idCalendario`. El calendario está en el detalle de la solicitud.

### 3.6 Catálogo

`GET /coredb/catalogos/creditos`: `estadosSolicitud`, `reglas` (con `ratioMin` y `ratioMax` en %), `metodosAmortizacion`, `tiposValidacion`, `estadosOrden`, `estadosCuota`, `estadosCredito`, `canalesDesembolso` y `vigenciaAprobacionDias`.

**Qué cambia para Evaluación al integrarse:** se quita `bna_evaluacion`; la pantalla `/evaluacion` sigue sobre estas rutas (ids UUID, sin botón OBSERVAR); CR-INT-03 hacia SOL se reenvía sin estado propio, con un `idOperacion` determinista; las rutas `/eva/v1/aprobaciones` dejan de hacer falta.

## 4. Desembolso (propuesta; PR siguiente)

| Ruta | Permiso | Qué hace |
|---|---|---|
| `POST /coredb/clientes/validaciones/documento` (ya existe) | `VALIDAR_IDENTIDAD` (se le da también a OPERADOR) | Verificación del documento en ventanilla. Devuelve el `codCliente` y un `id_validacion` |
| `GET /coredb/creditos/aprobaciones?codCliente=` | `VER_CREDITO` | Las aprobaciones de ese cliente |
| `POST /coredb/creditos/ordenes` + llave | `DESEMBOLSAR_CREDITO` | `{idEvaluacion, numCuenta, canal?: VEN\|HB, idAgencia?}`. El importe es el monto aprobado. Se rechaza si la aprobación venció o si la primera cuota ya venció. 201 `{idOrden, codigoOrden, estado: PREPARADA, importe, moneda}` |
| `PUT …/ordenes/{id}/cuenta` | `DESEMBOLSAR_CREDITO` | Cambia la cuenta mientras la orden está PREPARADA o VALIDADA; vuelve a PREPARADA |
| `POST …/ordenes/{id}/validaciones` | `DESEMBOLSAR_CREDITO` | `{tipo: IDENTIDAD\|AUTORIZACION\|ANTIFRAUDE, resultado, referenciaEvidencia, detalle?}`. En IDENTIDAD, la evidencia es el `id_validacion` anterior, del mismo día (decisión 7). La validación CUENTA la registra COREDB. Con IDENTIDAD y CUENTA aprobadas, la orden pasa a VALIDADA |
| `POST …/ordenes/{id}/confirmacion` + llave | `DESEMBOLSAR_CREDITO` | Abona, crea el crédito y deja la solicitud DESEMBOLSADA, en una sola operación. `{codigoOrden, estado: CONFIRMADA, codCredito, uuidTransaccionAbono, fechaEfectiva}` |
| `POST …/ordenes/{id}/rechazo` | `DESEMBOLSAR_CREDITO` | `{motivo}` |
| `GET …/ordenes?estado=&codCliente=`, `GET …/ordenes/{id}`, `GET /coredb/creditos/conciliacion/desembolsos?fecha=` | `VER_CREDITO`, `GENERAR_REPORTES` | Monitor y conciliación |

## 5. Cobranza (propuesta; PR siguiente)

| Ruta | Permiso | Qué hace |
|---|---|---|
| `GET /coredb/creditos?codCliente=`, `GET /coredb/creditos/{codCredito}`, `GET …/{codCredito}/pagos`, `GET /coredb/creditos/pagos/{referencia}` | `CONSULTAR_DEUDA` | Crédito con sus cuotas, saldo, mora vigente y estado; pagos y comprobante |
| `POST /coredb/creditos/{codCredito}/pagos` | `REGISTRAR_PAGO` | `{numCuenta, monto, referencia, canal?}`. La `referencia` es la llave. Debita la cuenta del titular y aplica el pago de la cuota más antigua a la más reciente. Sin fondos o con la cuenta bloqueada: 201 `estado: RECHAZADO` con `motivo`. Un monto mayor que la deuda total: 422 |
| `POST …/{codCredito}/cuotas/{n}/mora`, `GET` en la misma ruta | `REGISTRAR_MORA`, `CONSULTAR_DEUDA` | Registra el cálculo de mora y su historial |
| `POST /coredb/creditos/vencimientos` | `REGISTRAR_MORA` | Marca las cuotas vencidas y recalcula AL_DIA o EN_MORA (también corre a diario en la base) |
| `GET /coredb/creditos/conciliacion/pagos?fecha=` | `GENERAR_REPORTES` | Lo cobrado frente a lo aplicado, por día y canal |

## 6. Trazabilidad CR-INT-04 a CR-INT-07

| Interfaz | Cómo se cumple | Procedimiento o vista | Ruta |
|---|---|---|---|
| CR-INT-04 Evaluación ↔ Desembolso | (a) Las aprobaciones vigentes se leen de la base, con el calendario PRELIMINAR sin cambios. (b) La confirmación deja la solicitud DESEMBOLSADA en la misma transacción que el abono | `v_aprobacion_api`, `v_calendario_api`, `preparar_orden`, `confirmar_orden` | `GET /coredb/creditos/aprobaciones`, `GET /coredb/creditos/solicitudes/{id}`, `POST …/ordenes/{id}/confirmacion` |
| CR-INT-05 Desembolso → CUENTAS | El abono es un movimiento `DESEMBOLSO` dentro de la confirmación; un reintento con la misma llave devuelve el mismo `uuidTransaccionAbono` | `confirmar_orden` | `POST /coredb/creditos/ordenes`, `PUT …/cuenta`, `POST …/confirmacion` |
| CR-INT-06 Desembolso → Cobranza | La confirmación crea el crédito (AL_DIA) y su calendario OFICIAL, copia del PRELIMINAR; Cobranza lo lee | `confirmar_orden`, `v_credito_api`, `v_cuota_api` | `GET /coredb/creditos`, `GET /coredb/creditos/{codCredito}` |
| CR-INT-07 Cobranza → CUENTAS | El débito es un movimiento `DEBITO_CUOTA` dentro del pago; sin fondos, pago RECHAZADO sin movimiento; la `referencia` evita cobrar dos veces | `registrar_pago_cuota`, `v_pago_api` | `POST /coredb/creditos/{codCredito}/pagos` |

## 7. Decisiones del equipo (valor por omisión; ninguna bloquea)

1. El analista no puede OBSERVAR: la decisión es APROBADO o RECHAZADO (diccionario de Evaluación). La base admitiría OBSERVADO si el equipo lo decide.
2. Vigencia de la aprobación: 30 días.
3. Revocar una aprobación antes del desembolso: se permite, con motivo.
4. Pago mayor que la cuota: se aplica a las siguientes; se rechaza solo si supera la deuda total.
5. Mora: se registra y se muestra, no se cobra (no hay fórmula ni tasa en las fuentes).
6. Supervisor de Desembolso: ADMINISTRADOR.
7. Vigencia de la verificación de identidad para desembolsar: el mismo día (fecha de Lima).

Siguen abiertos: los umbrales de RN-EVA-002-P (provisionales), el dominio de `resultado_verificacion` y la ratificación de `cod_cliente` como identificador común.
