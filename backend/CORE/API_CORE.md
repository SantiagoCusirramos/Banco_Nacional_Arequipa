# CORE — Guía de rutas y fuentes de información

Documento de referencia de la API unificada del módulo **CORE**
(`backend/CORE/`). Describe cada ruta expuesta, qué recibe, qué
devuelve y **de qué tabla(s) de la base `bna` se extrae la
información**.

- Prefijo base: **`/core`** (montado desde `backend/main.py`).
- Documentación interactiva (Swagger): `GET /docs` con la app levantada.
- Todas las respuestas de error siguen el formato RNF-29:
  ```json
  {
    "error": { "code": "CODIGO_NEGOCIO", "message": "...", "details": {} },
    "correlation_id": "..."
  }
  ```
- Casi todos los endpoints de escritura aceptan en el body
  `actor` (quién ejecuta, para auditoría) y `correlation_id`
  (trazabilidad entre sistemas).

---

## 1. Clientes (`CORE/routers/clientes.py`)

Tablas involucradas: `cliente`, `tipo_documento`.

| Método | Ruta | Acción CORE |
|---|---|---|
| GET | `/core/clientes` | VER_CLIENTE (listado) |
| GET | `/core/clientes/{id_cliente}` | VER_CLIENTE (uno) |
| POST | `/core/clientes` | CREAR_CLIENTE |
| PATCH | `/core/clientes/{id_cliente}` | MODIFICAR_CLIENTE |

### GET `/core/clientes`
Lista clientes con filtros opcionales.

| Query param | Tipo | Descripción |
|---|---|---|
| `documento` | str | Subcadena del número de documento |
| `estado` | str | `ACTIVO`, `INACTIVO`, etc. |
| `limite` | int | 1–200, defecto 50 |
| `offset` | int | Desplazamiento para paginación |

**Origen de datos**: tabla `cliente` (todas las columnas del modelo
`Cliente`). Devuelve: `id_cliente`, `cod_tipo_documento`,
`numero_documento`, `nombres`, `apellido_paterno/materno`,
`fecha_nacimiento`, `numero_celular`, `correo_electronico`,
`estado_cliente`, `fecha_registro`.

### GET `/core/clientes/{id_cliente}`
Cliente por su UUID (PK de `cliente`). 404 `CLIENTE_NO_ENCONTRADO`
si no existe.

### POST `/core/clientes`
Body: `cod_tipo_documento`, `numero_documento`, `nombres`,
`apellido_paterno`, `apellido_materno?`, `fecha_nacimiento?`,
`numero_celular`, `correo_electronico?`, `actor?`, `correlation_id?`.

**Origen/destino**: inserta en `cliente`. Valida que
`cod_tipo_documento` exista en el catálogo `tipo_documento`.

**RGN-05 (deduplicación)**: si el par (tipo documento, número) ya
existe, **no crea otro registro**: devuelve el cliente existente con
`"duplicado": true` (útil para recuperar el `id_cliente` de un DNI
conocido).

Respuesta: `{ "cliente": {...}, "duplicado": bool }`.

### PATCH `/core/clientes/{id_cliente}`
Actualización parcial (solo los campos enviados). Campos editables:
nombres, apellidos, celular, correo, `estado_cliente`.
Registra el cambio en `auditoria_evento` con el detalle campo a campo.

---

## 2. Cuentas de ahorro (`CORE/routers/cuentas.py`)

Tablas involucradas: `cuenta_ahorro`, `cliente_cuenta`,
`producto_ahorro`, `agencia`.

| Método | Ruta | Acción CORE |
|---|---|---|
| GET | `/core/cuentas/cliente/{id_cliente}` | VER_CUENTA (por cliente) |
| GET | `/core/cuentas/{num_cuenta}` | VER_CUENTA (una) |
| POST | `/core/cuentas` | CREAR_CUENTA |
| PATCH | `/core/cuentas/{num_cuenta}` | MODIFICAR_CUENTA |

### GET `/core/cuentas/{num_cuenta}`
Saldo y estado en tiempo real (RF-COR-04).

**Origen de datos**:
- `cuenta_ahorro` → `num_cuenta`, `moneda`, `regimen`,
  `estado_cuenta`, **`saldo_contable`**, **`saldo_disponible`**,
  `saldo_retenido`, `fecha_apertura`, `id_agencia`,
  `id_producto_ahorro`.
- `cliente_cuenta` (JOIN por `num_cuenta`) → lista de titulares con
  su `rol_titular` (`TITULAR`, `MANCOMUNADO`, `APODERADO`,
  `TUTOR`, `BENEFICIARIO`).

### GET `/core/cuentas/cliente/{id_cliente}`
Todas las cuentas donde el cliente figura como titular
(JOIN `cuenta_ahorro` ⋈ `cliente_cuenta` por `id_cliente`).
Cada ítem incluye el resumen completo (saldos + titulares).

### POST `/core/cuentas`
Body: `id_cliente`, `id_producto_ahorro`, `id_agencia`,
`regimen` (`LIBRE`|`PROGRAMADO`|`INFANTIL`|`CTS`|`A_PLAZO`),
`titulares?` (lista de `{id_cliente, rol_titular}`).

**Destino**: inserta en `cuenta_ahorro` (saldo en cero, estado
`ACTIVA`) y una fila en `cliente_cuenta` por cada titular.
Valida que el producto exista y esté activo en `producto_ahorro`, y
la agencia en `agencia`. Número de cuenta generado por la app
(14 dígitos: `20` + YYMMDD + 6 aleatorios).

**RGN-16**: si algún titular es `MANCOMUNADO`, se exigen ≥2 titulares.

### PATCH `/core/cuentas/{num_cuenta}`
Cambia `estado_cuenta` entre: `ACTIVA`, `INACTIVA`, `BLOQUEADA`,
`EMBARGO`. El cambio queda en `auditoria_evento`.

---

## 3. Movimientos (`CORE/routers/movimientos.py`)

Tablas involucradas: `cta_transaccion`, `cuenta_ahorro`,
`cta_control_tope_diario`, `limite_canal`, `tipo_cambio`,
`asiento_contable`, `asiento_detalle`.

| Método | Ruta | Acción CORE |
|---|---|---|
| POST | `/core/movimientos` | REGISTRAR_MOVIMIENTO (depósito/retiro) |
| POST | `/core/movimientos/transferencias` | REGISTRAR_MOVIMIENTO (transferencia) |

### POST `/core/movimientos`
Body: `tipo_operacion` (`DEPOSITO`|`RETIRO`), `num_cuenta`,
`monto`, `moneda?`, `id_canal`, `id_terminal?`,
`num_cuenta_contraparte?`, `idempotency_key?`, `comision?`,
`itf?`, `retencion?`.

**Escritura atómica (RF-COR-06 / RGN-01..09)** en una sola
transacción:
1. **Saldo** → lee y actualiza `cuenta_ahorro.saldo_disponible` /
   `saldo_contable`. Rechaza si el débito excede el disponible
   (`SALDO_INSUFICIENTE`, RGN-03).
2. **Tope diario** → valida contra `limite_canal`
   (límite por canal+moneda) y acumula en
   `cta_control_tope_diario` (RGN-04).
3. **Tipo de cambio** → si la moneda de la operación difiere de la
   de la cuenta, lee `tipo_cambio` vigente a la fecha
   (`TIPO_CAMBIO_NO_ENCONTRADO` si no existe, RGN-10).
4. **Estado de cuenta** → cuentas `BLOQUEADA`/`INACTIVA` no originan
   débitos (`CUENTA_NO_OPERATIVA`, RGN-09).
5. **Movimiento** → inserta fila en `cta_transaccion`
   (con `idempotency_key` única).
6. **Asiento contable** → crea cabecera en `asiento_contable` y
   líneas en `asiento_detalle` (partida doble cuadrada; cuentas
   `CAJA`/`FONDOS_BANCO` vs `DEPOSITOS_AHORRO`).
7. **Auditoría** → evento en `auditoria_evento`.

**Idempotencia (RF-COR-11 / RGN-06)**: si se envía
`idempotency_key` y ya existe un movimiento con esa llave, se
devuelve el resultado original con `"replay": true` sin repetir
efectos.

- El replay solo ocurre si la petición es **la misma**: se compara una
  huella SHA-256 de `tipo_operacion`, `num_cuenta`,
  `num_cuenta_contraparte`, `monto`, `moneda` (o la de la cuenta si no
  se envía) e `id_canal`. La huella se guarda en
  `auditoria_evento.detalle.hash_peticion`; en transacciones antiguas
  sin huella se reconstruye desde la fila de `cta_transaccion`.
- Si la llave ya fue usada con otros datos (otra cuenta, otro monto,
  otro tipo de operación, otra contraparte...) se responde **409**
  `IDEMPOTENCY_KEY_REUTILIZADA`, con `details.diferencias` indicando
  cada campo `original` vs `solicitado`. Una llave usada en un depósito
  no puede reutilizarse en un retiro ni en una transferencia (y viceversa).
- La llave no puede terminar en `#C` (sufijo reservado):
  **422** `IDEMPOTENCY_KEY_INVALIDA`.

Respuesta: id de transacción, saldo posterior, id de asiento,
`replay`.

### POST `/core/movimientos/transferencias`
Body: `num_cuenta_origen`, `num_cuenta_destino`, `monto`,
`moneda?`, `id_canal`, `id_terminal?`, `idempotency_key?`.

Débito en origen + crédito destino en **un solo asiento** atómico.
Idempotencia: la pierna origen guarda la llave tal cual; la
contraparte la guarda con sufijo `#C`. Devuelve ambas piernas y el
asiento único.

- `idempotency_key` admite máximo **62** caracteres (62 + `#C` = 64,
  tamaño de la columna) y no puede terminar en `#C`.
- **Replay**: se valida la huella de la petición igual que en
  `/core/movimientos` (409 si no coincide). La pata origen se identifica
  por `tipo_movimiento='D'` y llave sin sufijo; la destino por
  `tipo_movimiento='C'` y llave con `#C`. **No** se usa `fecha_hora`
  (ambas patas tienen el mismo instante), por lo que el replay nunca
  intercambia origen y destino.

**Concurrencia y deadlocks**:
- Las dos cuentas se bloquean con `SELECT ... FOR UPDATE` **siempre en
  orden ascendente de `num_cuenta`**, sin importar cuál es origen o
  destino. Dos transferencias cruzadas simultáneas (A→B y B→A) piden
  primero el mismo candado: una espera a la otra y no se forma un
  ciclo de espera.
- Si InnoDB aún elige la transacción como víctima de un deadlock
  (error MySQL 1213, p. ej. por gap locks al crear el primer registro
  del día en `cta_control_tope_diario`), CORE hace rollback y
  **reintenta la operación completa** hasta 3 veces con backoff
  exponencial + jitter (~50 ms, ~100 ms). Aplica también a
  `/core/movimientos`.
- Si se agotan los reintentos se responde **503**
  `CONCURRENCIA_REINTENTOS_AGOTADOS`. Es seguro reintentar con la misma
  `idempotency_key`.

---

## 4. Tarjetas (`CORE/routers/tarjetas.py`)

Tablas involucradas: `tar_tarjeta`, `tar_tarjeta_cuenta`,
`tar_historial_estado`, `cliente`, `cuenta_ahorro`, `cliente_cuenta`.

| Método | Ruta | Acción CORE |
|---|---|---|
| GET | `/core/tarjetas` | VER_TARJETA (listado) |
| GET | `/core/tarjetas/{id_tarjeta}` | VER_TARJETA (una) |
| POST | `/core/tarjetas` | CREAR_TARJETA |
| POST | `/core/tarjetas/{id_tarjeta}/cambiar-estado` | BLOQUEAR_TARJETA |

**RNF-13**: el PAN nunca se almacena ni se devuelve. Solo se exponen
`bin` (6 primeros), `ultimos4` y el `id_tarjeta`. El hash completo
del PAN queda únicamente en `tar_tarjeta.pan_token`.

### GET `/core/tarjetas`
Filtros: `id_cliente`, `estado` (`ACTIVA`|`BLOQUEADA`|`VENCIDA`|
`ANULADA`), `limite`, `offset`.

**Origen**: tabla `tar_tarjeta` (vista pública sin token).

### POST `/core/tarjetas`
Body: `id_cliente`, `num_cuenta`, `tipo_tarjeta`
(`DEBITO`|`CREDITO`|`PREPAGO`), `anios_vigencia?`, `es_principal?`,
`habilitada_atm?`.

**Validaciones**: el cliente existe (`cliente`), es titular de la
cuenta (`cliente_cuenta`), y la cuenta existe (`cuenta_ahorro`).

**Escritura**: inserta en `tar_tarjeta` (BIN fijo de emisión +
token SHA-256 del PAN efímero) y en `tar_tarjeta_cuenta`
(vínculo tarjeta↔cuenta).

### POST `/core/tarjetas/{id_tarjeta}/cambiar-estado`
Body: `estado_nuevo`, `motivo` (requerido), `origen?`
(`BANCO`|`CLIENTE`).

**Escritura**: actualiza `tar_tarjeta.estado` e inserta fila en
`tar_historial_estado` (historial inmutable
`estado_anterior` → `estado_nuevo` con motivo y fecha).

---

## 5. Créditos (`CORE/routers/creditos.py`)

Tablas involucradas: `sol_solicitud`, `sol_fiador`, `sol_garantia`,
`sol_calendario_version`, `sol_cuota_calendario`,
`sol_historial_estado`, `eva_situacion_financiera`, `eva_regla`,
`eva_evaluacion`, `eva_decision_analista`, `cob_credito`,
`cob_cuota`, `cob_pago`, `cob_aplicacion_pago`, `cob_mora`,
`canal_pago`, `producto_credito`, `cliente`.

| Método | Ruta | Acción CORE |
|---|---|---|
| POST | `/core/creditos/solicitudes` | CREAR_SOLICITUD_CREDITO |
| GET | `/core/creditos/solicitudes/{id_solicitud}` | VER_CREDITO |
| POST | `/core/creditos/solicitudes/{id_solicitud}/evaluar` | EVALUAR_CREDITO |
| POST | `/core/creditos/solicitudes/{id_solicitud}/decision` | APROBAR_CREDITO |
| GET | `/core/creditos/deuda` | CONSULTAR_DEUDA |
| POST | `/core/creditos/pagos` | REGISTRAR_PAGO |

### POST `/core/creditos/solicitudes`
Body: `id_cliente`, `id_producto_credito`, `monto_solicitado`,
`moneda`, `plazo_meses`, `destino_credito?`, `id_asesor?`,
`id_agencia?`, `fiadores?[]`, `garantias?[]`.

**Validaciones**: cliente existe; producto existe y está activo en
`producto_credito`; el plazo cae dentro de
`plazo_min_meses`/`plazo_max_meses` del producto (RN-16).

**Escrituras**:
- `sol_solicitud` (estado inicial `REGISTRADA`)
- `sol_historial_estado` (primer evento)
- `sol_fiador` y `sol_garantia` (una fila por cada ítem del payload)
- `sol_calendario_version` (versión 1, estado `SIMULADO`) +
  `sol_cuota_calendario` (cuotas proyectadas con sistema francés:
  cuota fija, interés sobre saldo insoluto)

Respuesta: la vista completa de `VER_CREDITO` (ver abajo).

### GET `/core/creditos/solicitudes/{id_solicitud}`
Vista 360° de la solicitud. **Origen de datos**:

| Sección de la respuesta | Tabla |
|---|---|
| `fiadores` | `sol_fiador` |
| `garantias` | `sol_garantia` |
| `historial` (cambios de estado) | `sol_historial_estado` |
| `calendario` + `cuotas` | `sol_calendario_version` ⋈ `sol_cuota_calendario` |
| `credito_desembolsado` (si ya se desembolsó) | `cob_credito` |

### POST `/core/creditos/solicitudes/{id_solicitud}/evaluar`
Body: `situacion?` (ingresos/egresos/patrimonio/cuota otros créditos),
`dias_mayor_mora?`.

**Motor de reglas**: evalúa cada fila activa de `eva_regla` contra
dos variables:
- `ratio_capacidad` = (cuota propuesta + otros créditos) / ingresos
- `dias_mayor_mora` (de central de riesgos, el caller lo envía)

Si no se envía `situacion`, se reutiliza la última fila de
`eva_situacion_financiera` de la solicitud.

**Escrituras**: `eva_situacion_financiera` (si se declaró),
`eva_evaluacion` (puntaje 0–100, resultado
`APROBADO`/`OBSERVADO`/`RECHAZADO`, nivel de riesgo
`BAJO`/`MEDIO`/`ALTO`/`MUY_ALTO`, detalle JSON de reglas
coincidentes), `sol_historial_estado`.

Respuesta: `puntaje`, `resultado`, `monto_maximo_sugerido`,
`nivel_riesgo`, `detalle_reglas`.

### POST `/core/creditos/solicitudes/{id_solicitud}/decision`
Body: `decision` (`APROBAR`|`RECHAZAR`|`OBSERVAR`|`DERIVAR`),
`id_analista?`, `monto_aprobado?`, `plazo_aprobado?`,
`observacion?`.

**Precondición**: la solicitud debe haber sido evaluada (debe
existir al menos una fila en `eva_evaluacion`).

**Escrituras**: `eva_decision_analista` (decisión del humano),
`sol_solicitud.estado_solicitud` (→ `APROBADA`, `RECHAZADA`,
`OBSERVADO` o `EN_EVALUACION`), `sol_historial_estado`.

> **Nota (RGN-12 parcial)**: al aprobar aún no se genera
> automáticamente `cob_credito` ni el asiento de desembolso; eso
> queda pendiente de definir con el módulo Desembolso.

### GET `/core/creditos/deuda`
Filtros: `id_credito` y/o `id_cliente` (al menos uno recomendado).

**Origen de datos**:

| Campo | Tabla |
|---|---|
| `saldo_capital`, `estado_credito`, `dias_mora` | `cob_credito` |
| `saldo_mora` (suma de mora vigente) | `cob_mora` (join `cob_cuota`) |
| `proxima_cuota` | primera `cob_cuota` pendiente por fecha de vencimiento |
| `cuotas` (calendario real) | `cob_cuota` |
| `estado_riesgo` (`AL_DIA`/`EN_MORA`) | calculado vs fecha de hoy |

`saldo_total` = `saldo_capital` + `saldo_mora`.

### POST `/core/creditos/pagos`
Body: `id_credito`, `monto`, `id_canal_pago`, `num_cuenta?`,
`num_operacion` (única), `id_cobrador?`.

**Validaciones**: crédito existe (`cob_credito`), canal activo
(`canal_pago`), `num_operacion` no repetida (`PAGO_DUPLICADO`),
hay cuotas pendientes.

**Aplicación del pago (orden: mora → interés → seguro → capital)**:
1. Busca cuotas pendientes en `cob_cuota` (vencidas primero).
2. Lee la mora vigente en `cob_mora` por cada cuota.
3. Actualiza `cob_cuota.monto_pagado` / `saldo_capital` /
   `estado_cuota` (`PARCIAL`/`PAGADA`) y `cob_mora` si aplica.
4. Inserta `cob_pago` + una fila en `cob_aplicacion_pago` por cuota
   tocada.
5. **RGN-14**: si el pago viene con `num_cuenta`, cada aplicación
   genera **su propio asiento** (`asiento_contable` +
   `asiento_detalle`): débito `DEPOSITOS_AHORRO`, crédito
   `CTAS_POR_COBRAR`/`INGRESOS_INTERESES`/`INGRESOS_MORA` según
   corresponda.
6. Si el capital llega a cero → `cob_credito.estado_credito =
   CANCELADO`.

Respuesta: montos aplicado/no aplicado, lista de
`{id_aplicacion, id_asiento}`, saldo restante y estado del crédito.

---

## 6. Usuarios (`CORE/routers/admin.py` → `usuarios_router`)

Tablas involucradas: `usuario_sistema`, `empleado`.

| Método | Ruta | Acción CORE |
|---|---|---|
| GET | `/core/usuarios` | VER_USUARIO (listado) |
| GET | `/core/usuarios/{id_usuario}` | VER_USUARIO (uno) |
| POST | `/core/usuarios` | CREAR_USUARIO |
| POST | `/core/usuarios/{id_usuario}/rol` | ASIGNAR_ROLES |

### GET `/core/usuarios`
Filtros: `activo` (bool), `rol`, `limite`, `offset`.
**Origen**: `usuario_sistema` (nunca expone `hash_password`).

### POST `/core/usuarios`
Body: `username` (único), `nombre`, `password` (≥8 caracteres),
`rol` (`ADMINISTRADOR`|`ASESOR`|`ANALISTA`|`OPERADOR`|`AUDITOR`),
`id_empleado?`.

**Escritura**: inserta en `usuario_sistema` con
`hash_password` = SHA-256 hex (CHAR(64), compatible con los seeds
MySQL `SHA2(pass,256)`) y `algoritmo_hash='SHA256'`.
Valida `id_empleado` contra `empleado` si se envía.

### POST `/core/usuarios/{id_usuario}/rol`
Body: `rol`. Actualiza `usuario_sistema.rol` (ENUM de la BD) y
registra el cambio en `auditoria_evento`.

---

## 7. Permisos RBAC (`CORE/routers/admin.py` → `permisos_router`)

**Fuente**: no hay tablas de permisos en el esquema `bna`; se usa el
archivo versionado **`backend/CORE/data/rbac.json`**
(catálogo de 21 acciones + asignaciones rol→acciones).

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/core/permisos` | Catálogo completo + permisos por rol |
| GET | `/core/permisos/rol/{rol}` | Lista de acciones que puede ejecutar un rol |
| POST | `/core/permisos/asignar` | Asigna una acción a un rol (`{rol, accion}`) |
| POST | `/core/permisos/revocar` | Revoca una acción de un rol (`{rol, accion}`) |

El JSON de respuesta de GET es la fuente de verdad para que los
demás módulos pre-autoricen operaciones antes de invocar CORE.

---

## 8. Auditoría (`CORE/routers/admin.py` → `auditoria_router`)

| Método | Ruta | Acción CORE |
|---|---|---|
| GET | `/core/auditoria` | VER_AUDITORIA |

### GET `/core/auditoria`
**Origen**: tabla `auditoria_evento` (**solo lectura**; no hay
endpoints de modificar/eliminar, RF-COR-19 / RNF-11).

| Query param | Descripción |
|---|---|
| `desde`, `hasta` | Rango de `fecha_hora` (YYYY-MM-DD) |
| `modulo` | Ej. `CORE` |
| `accion` | Ej. `CREAR_CLIENTE`, `REGISTRAR_MOVIMIENTO` |
| `actor` | Usuario o sistema que ejecutó |
| `correlation_id` | Trazabilidad entre sistemas |
| `limite`, `offset` | Paginación (máx. 500) |

Cada evento incluye `entidad`, `id_entidad`, `accion`, `actor`,
`detalle` (JSON con el resumen del cambio; nunca datos sensibles
como PAN o claves) y `correlation_id`.

---

## 9. Reportes (`CORE/routers/admin.py` → `reportes_router`)

| Método | Ruta | Acción CORE |
|---|---|---|
| GET | `/core/reportes/cuadre-contable` | GENERAR_REPORTES |
| GET | `/core/reportes/asientos` | GENERAR_REPORTES |
| GET | `/core/reportes/movimientos` | GENERAR_REPORTES |
| GET | `/core/reportes/historial-cliente/{id_cliente}` | GENERAR_REPORTES |

### GET `/core/reportes/cuadre-contable?fecha=YYYY-MM-DD`
Verificación de partida doble del día (RF-COR-20 / RNF-10).
**Origen**: suma de `asiento_detalle.debe` y `.haber` unidas a
`asiento_contable` filtrando por fecha. Devuelve
`total_debe`, `total_haber`, `diferencia`, `cuadra` (bool).

### GET `/core/reportes/asientos?desde=&hasta=&estado=`
Asientos contables con sus líneas.
**Origen**: `asiento_contable` (cabecera) +
`asiento_detalle` (líneas: cuenta, debe, haber, moneda,
tipo de cambio, importe en moneda base).

### GET `/core/reportes/movimientos?num_cuenta=&desde=&hasta=`
Histórico de transacciones de una cuenta o de todo el banco.
**Origen**: tabla `cta_transaccion` (monto, moneda, comisión, ITF,
retención, saldo posterior, canal, llave de idempotencia).

### GET `/core/reportes/historial-cliente/{id_cliente}`
Histórico de productos del cliente.
**Origen**:
- `sol_solicitud` + `sol_historial_estado` → solicitudes con sus
  cambios de estado.
- `tar_tarjeta` + `tar_historial_estado` → tarjetas con su historial
  de bloqueos/estados.

---

## 10. Mapa rápido: "¿de dónde saco X?"

| Información que necesitas | Endpoint | Tabla(s) `bna` |
|---|---|---|
| Datos personales de un cliente | `GET /core/clientes/{id}` | `cliente` |
| Recuperar `id_cliente` por DNI | `GET /core/clientes?documento=` o `POST /core/clientes` (devuelve existente) | `cliente` |
| Saldo disponible de una cuenta | `GET /core/cuentas/{num}` | `cuenta_ahorro` |
| Titulares de una cuenta | `GET /core/cuentas/{num}` | `cliente_cuenta` |
| Cuentas de un cliente | `GET /core/cuentas/cliente/{id}` | `cuenta_ahorro` ⋈ `cliente_cuenta` |
| Últimos movimientos de una cuenta | `GET /core/reportes/movimientos?num_cuenta=` | `cta_transaccion` |
| Estado de una tarjeta (sin PAN) | `GET /core/tarjetas/{id}` | `tar_tarjeta` |
| Historial de bloqueos de tarjeta | `GET /core/reportes/historial-cliente/{id}` | `tar_historial_estado` |
| Solicitud de crédito completa | `GET /core/creditos/solicitudes/{id}` | `sol_*` + `eva_*` + `cob_credito` |
| Resultado de evaluación de riesgo | `GET /core/creditos/solicitudes/{id}` (tras evaluar) | `eva_evaluacion`, `eva_regla` |
| Cuotas pendientes de un crédito | `GET /core/creditos/deuda?id_credito=` | `cob_cuota`, `cob_mora` |
| Saldo total adeudado | `GET /core/creditos/deuda?id_credito=` | `cob_credito` + `cob_mora` |
| Comprobantes de pago | `GET /core/creditos/deuda` + `auditoria_evento` | `cob_pago`, `cob_aplicacion_pago` |
| Catálogo de acciones y permisos | `GET /core/permisos` | `CORE/data/rbac.json` |
| Quién hizo qué y cuándo | `GET /core/auditoria?actor=&accion=` | `auditoria_evento` |
| Cuadre contable del día | `GET /core/reportes/cuadre-contable` | `asiento_contable` + `asiento_detalle` |
| Asientos contables por fecha | `GET /core/reportes/asientos` | `asiento_contable` + `asiento_detalle` |
| Tipos de cambio oficiales | (uso interno del motor) | `tipo_cambio` |
| Topes diarios por canal | (uso interno del motor) | `limite_canal`, `cta_control_tope_diario` |
| Usuarios del sistema y roles | `GET /core/usuarios` | `usuario_sistema` |
| Productos de ahorro/crédito | (validación interna al crear) | `producto_ahorro`, `producto_credito` |

---

## 11. Notas para consumidores (otros módulos / Bus)

1. **Moneda**: los montos siempre viajan como `Decimal` (JSON number
   o string); la BD usa `NUMERIC(15,2)`. Nunca usar float.
2. **IDs**: son UUID v7 en `CHAR(36)`, generados por la app.
3. **Idempotencia**: en operaciones de dinero siempre enviar
   `idempotency_key` (movimientos) o `num_operacion` única (pagos)
   para poder reintentar sin riesgo de duplicar.
4. **Auditoría**: cada escritura deja un evento con `actor` y
   `correlation_id`; usar el mismo `correlation_id` que el caller
   para poder reconstruir la traza en `/core/auditoria`.
5. **Billetera**: las acciones de billetera/tarjeta-billetera de
   `Acciones CORE.md` están omitidas por decisión de alcance (no
   existen tablas en el modelo).
