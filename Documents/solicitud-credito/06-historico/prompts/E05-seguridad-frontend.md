> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# ETAPA 5 — Seguridad, auditoría y frontend Next.js (unifica P09 y P11)

> Instrucciones obligatorias: lee `AGENTS.md`, `Documents/solicitud-credito/06-historico/planes/plan-integracion-sol.md`, `Documents/solicitud-credito/change-log.md` y los informes previos de la rama. Comprueba rama, HEAD, `git status` y cualquier cambio no confirmado. **Registra cada modificación del repositorio, incluso documental, en `Documents/solicitud-credito/change-log.md`, sin sobrescribir historia.** No commits/push/merge, comandos destructivos ni cambios en otros módulos sin autorización. Toda nueva documentación va a `Documents/solicitud-credito/`. Cada acción debe distinguir evidencia REAL, SIMULADA, fake y no ejecutada.

**Objetivo:** integrar todas las funcionalidades SOL en una interfaz utilizable y asegurar controles, sin exponer credenciales ni alterar módulos ajenos.

1. Revisa `frontend/AGENTS.md`, rutas Next.js reales y `/api/solicitud-credito/[...path]`, sesiones, cookies y flujo `frontend→proxy→SOL`. Compara `/sol` en REAL y `/gateway/sol` solo SIMULADO; no asumir Bus existente. Mantener configuraciones de despliegue coherentes y secretos solo en servidor.
2. Autenticación local SOL: `/auth/login`, `/auth/me`, `/auth/logout`, roles, permisos del servidor, caducidad y revocación; identificar fronteras de seguridad central, sin afirmar SSO si no existe.
3. CR-INT-10: eventos críticos, autorización RBAC, outbox durable, deduplicación, correlación, retry y acuse; adaptar servicio Seguridad únicamente si existe API homologada. Si no existe, documentar dependencia y test fake; minimizar PII, tokens, documentos y detalles sensibles en logs/respuestas.
4. UI de asesor: consultar cliente, previsualizar condiciones/calendario, crear/editar solicitud, garantías/fiadores y pago doble solo si legalmente definido, enviar sin doble click, mostrar pendientes/acuse, estado y observaciones, subsanar y consultar historial. Mostrar errores HTTP significativos y conservar estado tras recarga.
5. UI supervisor/auditor según rol para métricas, pendientes y revocaciones si esos endpoints están disponibles; prohibir controles administrativos al asesor tanto en UI como API. No hacer rediseños grandes ni tocar frontend de otros módulos.
6. Pruebas de permisos/errores 401/403, callback no autorizado, retry de auditoría, no fuga de secretos, rutas proxy, formularios, cambio de estado, modo REAL/SIMULADO y compatibilidad con frontend existente. Ejecutar build/lint SOLO scripts seguros y registrar resultados reales.

**Entregables:** cambios focalizados SOL/frontend-SOL/tests; `sol-seguridad-frontend.md`, matriz RF y changelog. **Aceptación:** flujo completo de UI hasta mock/EVA real según disponibilidad, controles de acceso desde backend y diagnósticos claros.
