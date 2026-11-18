# Decisiones del equipo

Valores que el producto aplica donde las fuentes de los módulos no dicen nada o se contradicen. Se adoptaron el 2026-11-18, con autorización de Santiago Cusirramos, a partir del valor por omisión que la base y los servicios ya aplicaban (issue #34 y contrato de créditos). **Todas son revisables:** el módulo afectado puede cambiarlas con un issue o un PR. Si el cambio toca la base, va primero a [bna-core-db](https://github.com/miguelpro324/bna-core-db) y llega aquí con una actualización de `database/` ([`database/README-UPSTREAM.md`](../database/README-UPSTREAM.md)).

Lo que no tiene valor por omisión está en el issue #116, «Pendientes tras la entrega».

## Clientes, cuentas y canales

| # | Decisión | Valor | Origen | Módulo afectado |
|---|---|---|---|---|
| 1 | Quién registra un cliente `HABILITADO` (R-01) | Solo el usuario de servicio del módulo Clientes, porque es quien verificó la identidad. El personal del banco registra `OBSERVADO`. La regla está en `permisos.puede_registrar_habilitado` de COREDB | #34, pregunta 1 (PR #11, #14, #28) | Clientes, CAPTACION, COREDB |
| 2 | Tope de Ventanilla (`VEN`) frente a Home Banking (`HB`) | `VEN` no tiene tope diario automático, como documenta Tarjetas. El canal lo declara quien llama, así que un débito rechazado por el tope de `HB` puede repetirse por `VEN` hasta que el canal salga del usuario autenticado | #34, pregunta 2 | Cuentas, Tarjetas |
| 3 | Topes de Agentes (`AGE`) y de `HB` en dólares | Sin fila en `core.limite_canal`: el débito se rechaza con `BNA-CANAL` (un tope ausente no se lee como «sin tope»). El depósito funciona | #34, pregunta 3 | Cuentas, Tarjetas |
| 4 | Ventana del tope de la Billetera Digital (S/ 500) | Día calendario: se reinicia a medianoche, hora de Lima (como el corte de Tarjetas a las 00:00:00), no 24 horas corridas | #34, pregunta 4 | Billetera, Cuentas |
| 5 | Transferencias internas y caja (hallazgo M10) | Cada tramo se asienta contra 1101 Caja y 2101. En contabilidad una transferencia interna aparece como una salida y una entrada de efectivo | #34, pregunta 5 | Contabilidad, Cuentas |
| 6 | Transferencias entre monedas (RF-COR-14) | Se rechazan; falta el documento fuente | #34, pregunta 8 | Cuentas |
| 7 | Quién abre y cierra los periodos contables | Los carga el administrador de la base con los datos iniciales; en desarrollo, 24 meses abiertos desde el mes en curso. El producto no tiene ruta para abrirlos ni cerrarlos. Sin periodo para la fecha no se registra ningún movimiento | #34, pregunta 9 | Contabilidad |
| 8 | Identificador común del cliente | `cod_cliente`, que la base ya exige en todos los módulos | Contrato de créditos, sección 7 | Todos |

## Tarjetas, cajero y Home Banking

| # | Decisión | Valor | Origen | Módulo afectado |
|---|---|---|---|---|
| 9 | Origen `BANCO` de un cambio de estado de tarjeta | Se guarda como `OPERADOR`; `BANCO` no es un origen de Tarjetas | #34, pregunta 6 (respuesta de Tarjetas, 2026-11-13) | Tarjetas |
| 10 | BIN `004499` | `FISICA`, con la regla «un BIN por tipo de tarjeta». Es un valor de desarrollo; los BIN reales los dará el emisor y, hasta entonces, se emiten solo tarjetas físicas | #34, pregunta 7 (respuesta de Tarjetas, 2026-11-13) | Tarjetas |
| 11 | Plazo de una retención de tarjeta sin confirmar | 15 minutos; luego la base la libera (evento cada minuto) y confirmarla responde `BNA-CONFIRMACION` (`tarjetas.fn_minutos_retencion`, bd-v1.11-mysql) | PR #113 | Tarjetas, ATM, COREDB |
| 12 | Topes del cajero (`ATM`) | S/ 1 500 y US$ 500 diarios, los de la base (coinciden con el prototipo del cajero) | #93 | ATM, Tarjetas |
| 13 | Quién autentica al cajero | Lo abre un operador del banco con su usuario de COREDB (`POST /api/apertura`); su token se reenvía a TARJETAS y CUENTAS. No hay credencial de terminal | PR #110 | ATM |
| 14 | Cómo entra un cliente al Home Banking | Lo atiende un usuario del banco: inicia sesión con su usuario de COREDB y opera con el código de cliente. No hay login de clientes | PR #111 | Home Banking (frontend) |

## Seguridad

| # | Decisión | Valor | Origen | Módulo afectado |
|---|---|---|---|---|
| 15 | Bloqueo del login del personal | 5 fallos seguidos bloquean el usuario 15 minutos (`core.fn_intentos_login`, `core.fn_minutos_bloqueo_login`, bd-v1.12-mysql). El login bloqueado responde el mismo 401. Los usuarios de servicio no se bloquean | PR #114 | Seguridad, COREDB |

## Créditos

T1 a T7 son las decisiones de la sección 7 de [`backend/COREDB/CONTRATO_CREDITOS.md`](../backend/COREDB/CONTRATO_CREDITOS.md).

| # | Decisión | Valor | Origen | Módulo afectado |
|---|---|---|---|---|
| T1 | El analista puede OBSERVAR y devolver a SOL | No: la decisión del analista es `APROBADO` o `RECHAZADO` (diccionario de Evaluación). `OBSERVADO` es un resultado de la regla que pasa la solicitud al analista. En el CORE legado, `OBSERVAR` responde 422 desde #65 | Contrato de créditos | Evaluación |
| T2 | Vigencia de la aprobación | 30 días, como en #70 | Contrato de créditos | Evaluación, Desembolso |
| T3 | Revocar una aprobación antes del desembolso | Se permite, con motivo obligatorio | Contrato de créditos | Evaluación, Desembolso |
| T4 | Pago mayor que la cuota | Se aplica a las cuotas siguientes; se rechaza solo si supera la deuda total | Contrato de créditos | Cobranza |
| T5 | Mora | Se registra y se muestra, no se cobra (no hay fórmula ni tasa en las fuentes) | Contrato de créditos | Cobranza |
| T6 | Supervisor de Desembolso | Rol `ADMINISTRADOR` | Contrato de créditos | Desembolso |
| T7 | Vigencia de la verificación de identidad para desembolsar | El mismo día (fecha de Lima), al registrar la orden y al confirmarla | Contrato de créditos | Desembolso |
| 16 | Umbrales de RN-EVA-002-P | Los de `creditos.regla_evaluacion` (80 % / 100 %), con la fórmula de #70 | Contrato de créditos | Evaluación |
| 17 | Dominio de `resultado_verificacion` | Texto libre de hasta 20 caracteres, sin lista cerrada | Contrato de créditos | Evaluación |
| 18 | Decisión `DERIVAR` en el CORE legado | La base la admite (el ENUM de `eva_decision_analista` la incluye) y la solicitud queda `EN_EVALUACION`, pero no se documenta como función del producto: las fuentes solo tienen `APROBADO` y `RECHAZADO` | #34, pregunta 10 | Créditos (CORE legado) |
