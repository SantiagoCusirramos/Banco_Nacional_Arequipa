# Requisitos funcionales SOL — matriz vigente

> Estado: **VIGENTE**. Última verificación documental: **2026-11-16** (código y evidencias existentes; sin repetir pruebas funcionales). Rama: `feature/sol-integracion-cap-eva`; SHA: `988dc0776da282fbef306632fc86426b6e372376`. Principal: [README SOL](../README.md).

| Requisito | Descripción / estado | Evidencia técnica | Limitación y dependencia pendiente |
|---|---|---|---|
| RF-SOL-001 | Cliente captado — INTEGRADO EN LABORATORIO | integrations.py: reference/validate_reference; P20 SOL consulta CAP y COREDB confirma código | Verificadores externos CAP simulados; identidad/habilitación institucional pendiente. |
| RF-SOL-002 | Plazo — IMPLEMENTADO Y PROBADO | schemas.ApplicationInput, service.prepare, política; suite SOL219 |6–60 meses del perfil académico; ratificación institucional pendiente. |
| RF-SOL-003 | Monto — IMPLEMENTADO Y PROBADO | Decimal15/2, prepare, snapshots; suite SOL219 |1000–50000 PEN propuestos; no política crediticia aprobada. |
| RF-SOL-004 | Moneda — IMPLEMENTADO Y PROBADO | política monedas=[PEN], rechazo de moneda fuera de catálogo |Sin conversión/catálogo institucional nuevo; no habilitar USD por capacidad del DTO EVA. |
| RF-SOL-005 | Pago doble — BLOQUEADO | service.prepare rechaza true; policy rechaza habilitación no soportada |Fórmula/meses/redondeo DA-SOL-005 sin decisión aprobada. El rechazo seguro no implementa el cálculo. |
| RF-SOL-006 | Calendario — IMPLEMENTADO Y PROBADO | finance.calendar, Decimal, snapshot; P20 preview/EVA |PRELIMINAR, francés/30 días/días360/TEA22%; política académica pendiente de ratificación. |
| RF-SOL-007 | Garantías — IMPLEMENTADO Y PROBADO | schemas.Guarantee, máximo10, snapshot; garantía vehicular P20 |Solo declaración/tasación ingresada; obligación, validación y soportes institucionales pendientes. |
| RF-SOL-008 | Fiadores — BLOQUEADO | guarantor_reference permite referencias solo SIMULADO y rechaza REAL; suite SOL219 |Registro sintético disponible; contrato de identidad institucional y reglas de respaldo pendientes. P20 usa lista vacía. |
| RF-SOL-009 | Remisión a EVA — INTEGRADO EN LABORATORIO | Delivery/worker, GET operación antes de POST, acuse; P20 SQL y caída/recuperación |Requiere fuentes EVA fijadas y configuración del laboratorio; no integrado al Compose principal. |
| RF-SOL-010 | Resultado y subsanación — INTEGRADO EN LABORATORIO | callback/Outcome, versión/ronda, revise; P20 APROBADA/OBSERVADA→v2→APROBADA/RECHAZADA |Dictamen académico de EVA; sin desembolso ni homologación de estados/condiciones institucionales. |

## Procedencia y diferencias

Consolidación de [matriz E01–cierre anterior](../06-historico/etapas/sol-matriz-rf.md), [detalle E02](../06-historico/etapas/sol-funcionalidades-internas.md), código actual y [evidencia P20](../04-pruebas/p20/evidencias.json). La matriz anterior conserva sus resultados: RF001/009/010 estaban pendientes del circuito conjunto. P20 aporta transporte de aplicaciones originales y persistencia; por ello ahora se clasifican INTEGRADO EN LABORATORIO. RF005/008 y decisiones DA no se desbloquean.

DA-SOL-001..009 son referencias de trazabilidad heredada, no actas aprobadas comprobadas. No se declara cobertura institucional10/10 ni se suman suites superpuestas.
