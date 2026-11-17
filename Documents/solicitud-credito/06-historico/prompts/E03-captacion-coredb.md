> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# ETAPA 3 — Captación, identidad y límites con COREDB (unifica P06 y P10)

> Instrucciones obligatorias: lee `AGENTS.md`, `Documents/solicitud-credito/06-historico/planes/plan-integracion-sol.md`, `Documents/solicitud-credito/change-log.md` y los informes previos de la rama. Comprueba rama, HEAD, `git status` y cualquier cambio no confirmado. **Registra cada modificación del repositorio, incluso documental, en `Documents/solicitud-credito/change-log.md`, sin sobrescribir historia.** No commits/push/merge, comandos destructivos ni cambios en otros módulos sin autorización. Toda nueva documentación va a `Documents/solicitud-credito/`. Cada acción debe distinguir evidencia REAL, SIMULADA, fake y no ejecutada.

**Objetivo:** preparar RF-SOL-001 y referencias de fiadores cuando aplique, respetando las fuentes maestras; no simular que COREDB es automáticamente CAP.

1. Inspecciona APIs reales de COREDB Clientes, CORE legado y cualquier CAP que exista; anota rutas, permisos, contratos y diferencia entre `id_cliente`, `cod_cliente`, `id_verificacion`, `id_caso`, vigencia y estado habilitante. No inventes `vigente_hasta`, caso CAP ni conversiones de identificador.
2. Define el contrato CR-INT-01 mínimo para búsqueda y consulta por referencia, incluyendo qué proveedor confirma vigencia/estado y cómo se presenta a SOL; contrastar con `CONTRATOS_HTTP_V2.md`. Distingue especificación **propuesta** de endpoint real.
3. Completa dentro de SOL el cliente HTTP o interfaz de proveedor (adaptador) con rutas/tokens configurables, timeouts, validación estricta de JSON y estados, permisos y errores 401/403/404/422/503. Nunca fallback silencioso de REAL a SIMULADO; nunca leer tablas centrales directamente.
4. Preserva modo SIMULADO para pruebas, no enmascares proveedor fake como institucional. Solo conectar COREDB real si contrato validado contiene TODOS los datos habilitantes necesarios; si no, crea propuesta/plan de fachada sin construir datos inventados.
5. Analiza autoridad de datos en `bna_sol_mvp`, `bna` y COREDB, ownership y política de lectura/escritura. No migres, sincronices o hagas JOIN directo a bases externas. El contrato de mapeo de IDs y sus decisiones quedan documentados.
6. Tests de referencias válidas, ausentes, deshabilitadas, expiradas, inconsistentes, proveedor caído, auth fallida, respuesta malformada, fuga de PII y doble consulta.

**Entregables:** cambios focalizados SOL/tests; `sol-captacion-coredb.md` con contrato para el equipo CAP y diagnóstico de propiedad de datos; matriz RF/CR-INT y changelog. **Aceptación:** RF001 validado localmente con contrato fake y claramente `preparado_para_integracion` si CAP real no existe.
