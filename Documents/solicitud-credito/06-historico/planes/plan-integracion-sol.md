> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# Plan maestro SOL — 6 etapas para Codex CLI

**Meta:** lograr máxima cobertura técnica verificable de RF-SOL-001 a RF-SOL-010, ofrecer API pública estable y preparar integraciones CAP/EVA/Seguridad. No confundir `SIMULADO` con proveedores reales. Toda la documentación nueva corresponde a `Documents/solicitud-credito/`, incluido `change-log.md`.

## Secuencia

| Etapa | Archivo | Unifica | Resultado |
|---|---|---|---|
| E01 | `prompts/E01-diagnostico-contratos.md` | P00–P02 | Auditoría incremental + baseline + contratos/API y matriz RF |
| E02 | `prompts/E02-funcionalidades-rf.md` | P03–P05 | RF 002–008: política, calendario, garantías, fiadores, pago doble condicionado |
| E03 | `prompts/E03-captacion-coredb.md` | P06 + P10 | RF001/CR-INT-01 y límites COREDB |
| E04 | `prompts/E04-evaluacion.md` | P07–P08 | RF009/010, envío EVA, resultados y subsanación |
| E05 | `prompts/E05-seguridad-frontend.md` | P09 + P11 | CR-INT-10, roles, auditoría, Next.js y proxy |
| E06 | `prompts/E06-validacion-entrega.md` | P12–P13 | Pruebas/E2E, OpenAPI, documentación y entrega |

## Estado al iniciar

Según el baseline P01 aportado por el usuario (14/11/2026), se ejecutaron **52 tests aprobados con 2 warnings** en SQLite + HTTP fake; no se levantó Docker/MySQL ni se probó el E2E real. **E01 debe reutilizar** `sol-auditoria.md` y `sol-baseline.md` existentes si corresponden al HEAD, evitando repetir innecesariamente P00/P01. No incluir registros históricos ficticios en el changelog.

## Reglas de ejecución

- Una etapa por vez. Puede incluir varias acciones internas, pero trabajar en lotes pequeños con test y changelog por modificación.
- No tocar CAP, EVA, COREDB, Seguridad ni infra compartida salvo acuerdo explícito; definir interfaces/adaptadores en SOL y especificaciones para cada equipo.
- No encender REAL sin contratos completos: es modo de transporte, no certificación del proveedor. No inventar URLs ni reglas financieras.
- RF005 pago doble depende de política DA-SOL-005; no declarar completo si falta decisión. Lo mismo aplica a validación institucional CAP/fiadores y EVA.
- Nunca `down -v`, reset destructivo, ni ejecutar scripts globales sin revisar sus efectos y aislar datos. No commits/push.
- `AGENTS.md` es el único archivo de instrucciones para Codex en la raíz; el `frontend/AGENTS.md` propio del repo se respeta al editar frontend.

## Entregables de cierre

API OpenAPI verificada, matriz RF, contratos CR-INT claros para equipos CAP/EVA/Seguridad, evidencia clasificada fake/real, procedimientos Docker/entorno seguro, changelog y resumen PR sin publicarlo.
