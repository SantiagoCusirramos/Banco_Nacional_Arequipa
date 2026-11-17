# E01 — Anexo incremental a la auditoría

Fecha: 2026-11-14, America/Lima. Rama `feature/integracion-sol`, HEAD `86904edd8dc866c1d4260a996748a1cda3770007`.

Se preservan [P00](sol-auditoria.md) y [P01](sol-baseline.md) sin reescribir su historia. La planificación vigente unifica las tareas en seis etapas; la recomendación antigua P02 queda absorbida en esta E01. Se leyeron AGENTS, plan, changelog, E01 e informes previos; E02 solo para identificar continuidad, no se ejecutó.

## Validez de lo reutilizado

HEAD idéntico y diff funcional vacío en backend/frontend/Compose/bna/scripts/Docker/CI. Por ello siguen válidos el inventario de rutas/fuentes y las 52 pruebas P01 (SQLite/MockTransport, 2 warnings, 14,75 s). No se repitieron auditoría completa, suite, consultas Docker ni instalación. Los estados Docker son observaciones fechadas P01, no una nueva lectura runtime E01.

Al inicio, los archivos locales previos continuaban sin seguimiento; se añadía el ZIP aportado `SOL_Codex_Plan_6_Etapas.zip`. Se preservaron instrucciones, plan, prompts, ZIP y documentos ajenos. No se extrajo ni modificó el ZIP; el inventario de Documents siguió sin localizar PDF/actas ITIL. La ausencia del informe original impide contraste literal de tabla 80 y decisiones DA; se conserva ese pendiente.

## Nuevo análisis verificado

Se generó OpenAPI mediante `create_app`/`.openapi()` sin lifespan/base externa: SIMULADO 31 paths/35 operaciones, REAL 17/19. Aserciones de versión 2.0.0, callback presente y alias gateway condicionado aprobadas, salida 0. Se reutilizó entorno P01. No se generaron datos de prueba persistidos ni se publicaron secretos. Los artefactos y el método quedan en [contratos](sol-contratos-finalizacion.md).

Brechas constatadas:

- Respuestas generadas con esquema vacío por falta de DTO de salida; send omite 202 efectivo (`backend/SOL/app.py:361`, `:408`).
- Sin securitySchemes; header authorization opcional en especificación, exigido por lógica de sesión/callback (`app.py:124`, `:501`). Correlación de middleware no declarada como parámetro callback (`:93`).
- `demo-result` aparece en REAL aunque está bloqueado en ejecución; callback aparece en SIMULADO aunque devuelve 401 (`app.py:446`, `:501`).
- Creación de solicitud no implementa idempotencia de alta; no extender a ella la garantía de idempotencia de send (`app.py:299`, `:361`).
- Tipos TS locales no modelan todo el contrato (p. ej. estado anterior nullable y variantes de recepción); no equivalen a validación runtime (`frontend/app/solicitud-credito/page.tsx:19`, `:102`; `backend/SOL/service.py:165`).

Los hallazgos de CAP/EVA/Bus ausentes y APIs CORE/COREDB/Seguridad incompatibles se confirman por ausencia de cambios y lectura focalizada de routers/esquemas. No se inventan proveedores, rutas homologadas, casos/vencimientos o acuses. El informe APIs trasladado conserva enlaces relativos de su ubicación antigua; no se modifica el documento previo de terceros, y los nuevos entregables enlazan correctamente desde Documents.

## Entrega y continuidad

E01 completa el diagnóstico documental: [matriz de diez RF](sol-matriz-rf.md), contratos AS-IS/propuesta separados, propiedad/consumo de API, OpenAPI por modo y bloqueos. No completa la implementación de DTOs de respuesta, estabilidad formal de API ni homologación de contratos. Esas brechas se documentan para las etapas posteriores sin alterar comportamiento en esta etapa.

Comprobaciones E01: Git rama/HEAD/status/diff (salida 0), exportación y aserciones OpenAPI (salida 0), lectura de fuentes y validación documental/JSON al cierre. No suite nueva, no MySQL, Docker E2E, navegador ni servicios institucionales. `git diff --check` se complementa con validación de documentos sin seguimiento. No staging/commit/push.

Se puede continuar con E02 local: no hay un bloqueo externo para verificar/consolidar condiciones, calendario y respaldos con reglas existentes. Pago doble y fiadores reales siguen bloqueados por decisión/contrato. E03–E05 requieren acuerdos para declararse integrados y E06 deberá aportar pruebas faltantes. La taxonomía nueva de la matriz no implica que haya aumentado la cobertura funcional desde P01.
