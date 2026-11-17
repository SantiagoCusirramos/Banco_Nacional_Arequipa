> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# ETAPA 2 — Finalizar las funcionalidades internas RF-SOL-002 a 008 (unifica P03–P05)

> Instrucciones obligatorias: lee `AGENTS.md`, `Documents/solicitud-credito/06-historico/planes/plan-integracion-sol.md`, `Documents/solicitud-credito/change-log.md` y los informes previos de la rama. Comprueba rama, HEAD, `git status` y cualquier cambio no confirmado. **Registra cada modificación del repositorio, incluso documental, en `Documents/solicitud-credito/change-log.md`, sin sobrescribir historia.** No commits/push/merge, comandos destructivos ni cambios en otros módulos sin autorización. Toda nueva documentación va a `Documents/solicitud-credito/`. Cada acción debe distinguir evidencia REAL, SIMULADA, fake y no ejecutada.

**Objetivo:** consolidar los siete RF internos: 002 plazo, 003 monto, 004 moneda, 005 pago doble, 006 calendario preliminar, 007 garantías, 008 fiadores. Trabaja en **cambios pequeños con pruebas y changelog después de cada cambio**; evita reescrituras masivas.

1. Verifica la implementación actual y matriz de etapa 1; conserva rutas públicas y compatibilidad de UI, modelos y migraciones. No reprogramar un RF que ya satisface sus criterios.
2. **RF 002/003/004:** monto/plazo/moneda, validaciones por política versionada, persistencia, mensajes de error, límites y permisos. Los límites históricos de laboratorio (PEN, 1,000–50,000, 6–60 meses) no son aprobación institucional.
3. **RF 006:** calendario PRELIMINAR con `Decimal`, redondeos coherentes, base de días y fechas Lima según políticas verificadas; snapshots por versión inmutables, regeneración al editar, conservación del calendario original en envíos.
4. **RF 007:** garantías: campos, obligatoriedad solo si hay norma aprobada, validaciones, edición por revisión, persistencia, snapshot. Evitar maestro institucional ficticio.
5. **RF 008:** fiadores: registrar referencias de forma trazable, comprobar formato y duplicados; verificación institucional solo si existe proveedor/contrato real. Si no, preparar puerto/adaptador testeable sin afirmar identidad verificada.
6. **RF 005:** buscar decisión DA-SOL-005, meses en pago doble, tasa, amortización, recalculo y redondeo. **No inventes fórmulas ni habilites un flag ignorando la regla**. Si hay política aprobada y suficiente, implementar con pruebas exhaustivas; si falta, bloquear activación explícitamente con respuesta clara, documentar el contrato/punto de extensión y marcar RF `bloqueado_decision`, no completo.
7. Tests positivos y negativos: bordes, PII, permisos, precisión, versionado, concurrencia, idempotencia, invalidaciones, rollback, histórico y manejo de error. Preferir SQLite aislado para pruebas rápidas; MySQL solo instancia de test independiente y destino verificado.

**Entregables:** cambios puntuales backend/tests solo autorizados; matriz RF actualizada, `sol-funcionalidades-internas.md` con implementación, decisiones y bloqueos; changelog actualizado. **Aceptación:** pruebas verificadas para cada RF y distinción explícita entre cobertura local completa y reglas no aprobadas.
