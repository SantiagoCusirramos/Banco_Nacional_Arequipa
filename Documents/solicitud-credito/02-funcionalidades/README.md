# Funcionalidades, política y límites

> Estado: **VIGENTE**. Última verificación documental: **2026-11-16** (código y evidencias existentes; sin repetir pruebas funcionales). Rama: `feature/sol-integracion-cap-eva`; SHA: `988dc0776da282fbef306632fc86426b6e372376`. Principal: [README SOL](../README.md).

La [matriz RF vigente](matriz-rf.md) es la referencia específica de RF-SOL-001..010. Los estados de implementación están definidos en el README principal.

## Operaciones disponibles

Sesiones locales, cierre/baja/revocación y permisos de servidor; búsqueda CAP y revalidación de referencia; preview; registro y edición de BORRADOR por revisión; calendario PRELIMINAR; garantías declaradas; envío congelado/acuse EVA; callback autenticado; subsanación versionada; historial append-only desde API; bandeja paginada; monitoreo ops/pending y ops/metrics para supervisor/auditor. No hay endpoint de borrar historial ni edición de versión enviada.

`version` identifica el expediente congelado; `revision` detecta modificaciones concurrentes; `ronda` la asigna EVA; no intercambiarlos. BORRADOR→EN_EVALUACION requiere acuse; APROBADA/OBSERVADA/RECHAZADA vienen del resultado EVA. OBSERVADA→BORRADOR en versión nueva permite subsanar.202 no es EN_EVALUACION confirmado.

## Política vigente en código, aprobación pendiente

[politica_demo.json](../../../backend/SOL/config/politica_demo.json): SOL-DEMO-2026-01, PROPUESTO_PENDIENTE_COMITE, PEN1000–50000, plazo6–60 meses, TEA0.2200, francés,30 días, ROUND_HALF_UP, sin cargos adicionales. La conversión periódica usa días360. Decimal se conserva en cálculo y strings decimales en snapshots. Ajuste final deja saldo cero. No representa TCEA, calendario definitivo ni política bancaria aprobada.

Pago doble no está implementado: true se rechaza y no puede habilitarse solo por configuración. Fiadores tienen referencias sintéticas en SIMULADO, pero REAL los rechaza mientras falte contrato institucional. Garantía es declaración con catálogo/valor/límites; no verifica tasación ni elegibilidad institucional. El escenario mínimo P20 no usa fiadores/pago doble.

## Pendientes y procedencia

Homologación de política, identidad/fiadores, garantías, condiciones resultantes, Seguridad/TLS/SSO y operación productiva. Sin actas comprobadas no se atribuyen decisiones aprobadas ni responsables nuevos. Consolida [E02](../06-historico/etapas/sol-funcionalidades-internas.md), [propuestas](../06-historico/coordinacion/PROPUESTAS_Y_DECISIONES.md) y código actual. La declaración de integración P20 no elimina estos límites.
