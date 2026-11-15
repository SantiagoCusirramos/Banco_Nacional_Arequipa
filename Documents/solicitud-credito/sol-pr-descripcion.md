# SOL: validación local de solicitudes y preparación de contratos CAP/EVA/Seguridad

## Resumen

SOL conserva solicitudes versionadas y un calendario preliminar, pero sus bordes de integración necesitaban validaciones más estrictas, recuperación segura de entregas y cobertura de seguridad/interfaz. Este cambio consolida esa parte local, mantiene el modo SIMULADO y deja explícitos los requisitos para conectar proveedores institucionales.

Por ejemplo, ante una respuesta EVA perdida se conserva la operación reservada y se consulta su recepción antes de reenviar; una respuesta tardía no sobrescribe una reserva posterior. Una subsanación crea otra versión y conserva el expediente enviado. Un 202 significa reserva local pendiente, no recepción confirmada por EVA.

## Cambios técnicos

- Referencias de Captación con validación estricta de campos, tipos, fechas, identidad y vigencia; JSON null o configuración REAL incompleta fallan explícitamente. No hay fallback a referencias simuladas ni SQL a bases ajenas.
- Fiadores con IDs acotados, rechazo de duplicados/autofiador y proyección mínima por campos permitidos, también en lecturas históricas. Identidad institucional de fiadores sigue bloqueada.
- Acuses EVA con versión/ronda de tipo exacto, evaluación y acuse válidos; recuperación de entrega y auditoría usa la generación persistida de la reserva. Callback exige correspondencia de solicitud/versión/evaluación/ronda/operación/correlación y protege contra duplicados/conflictos/resultados viejos.
- Autenticación Bearer documentada, caducidad exacta y bloqueo de sesión demo residual en REAL; errores 422 sin eco de datos sensibles. Query eliminada del access log Uvicorn mientras SOL está activo.
- Modelos de salida y códigos OpenAPI explícitos, incluidos 202/503. Detalle de escritura refresca el expediente persistido para coincidir con el redondeo DATETIME de MySQL.
- Proxy SOL con cookie HttpOnly, no-store, protección de origen/rutas y configuración servidor `SOL_PUBLIC_ORIGIN` para Docker/reverse proxy. Interfaz maneja errores, sesiones, reservas pendientes, subsanación y permisos operativos; demo solo en SIMULADO.
- Pruebas SOL, laboratorio Compose exclusivo y documentación de contratos, trazabilidad, resultados y límites. No cambian políticas financieras, tablas ni migraciones.

## Validación registrada en E06

| Comprobación | Resultado |
| --- | --- |
| Backend SQLite/MockTransport | 169 aprobadas, 2 advertencias, 40,34 s |
| Backend con fixtures MySQL 8.4.13 | 169 aprobadas, 2 advertencias, 49,36 s; algunos tests independientes siguen usando SQLite |
| Frontend Vitest/RTL | 114 aprobadas, 2 fallos esperados heredados, 4,77 s |
| Lint, TypeScript, build Next 16.3.8 | Salida 0 |
| TCP Next→SOL→MySQL | 142 comprobaciones; CAP/EVA/Auditoría simulados |
| Migración v1/rollback/locks MySQL | 7 comprobaciones |
| Privacidad de logs y persistencia al reiniciar SOL | 4 comprobaciones |

Las ejecuciones backend repiten el mismo conjunto: no son 338 casos únicos. Las advertencias backend heredadas corresponden a AnyIO/Starlette y configuración pytest sin plugin. Los dos fallos esperados frontend no pertenecen a SOL. [Evidencias y comandos](sol-evidencias-testing.md), [entrega](sol-entrega-final.md), [matriz RF](sol-matriz-rf.md), [OpenAPI final](sol-openapi-e06-simulado.json).

Este cierre documental no volvió a ejecutar suites ni Docker; verificó diff, scope, JSON/AST y los 28 hashes E06, que siguen vigentes.

## Alcance, limitaciones y dependencias

Cinco RF implementados localmente, tres preparados para integración y dos bloqueados por decisión; **cero integrado_real**. RF005 no calcula pago doble sin DA-SOL-005. RF008 tiene registro simulado, pero requiere homologar identidad/validación DA-SOL-006. Montos, plazo, moneda, TEA y cálculo siguen siendo perfil académico propuesto.

CAP debe ofrecer CR-INT-01 completo; COREDB cliente existente solo cubre una parte y no sustituye caso/verificación/vigencia. EVA debe homologar recepción/consulta/dedupe/callback CR-INT-02/03. Seguridad debe definir identidad central, roles/revocación y receptor CR-INT-10; no se declara SSO/MFA ni auditoría institucional. [Nota para proveedores](sol-coordinacion-proveedores.md).

No se ejecutó E2E de navegador real, TLS/reverse proxy institucional, carga ni alta disponibilidad. REAL significa transporte configurado, no certificación. El filtro de access log depende del formato de Uvicorn 0.30.6; `detail` añade una lectura de expediente; `SOL_PUBLIC_ORIGIN` requiere configuración pública correcta. Compose global y plantillas de entorno quedaron intactos: el despliegue público debe incorporar esa variable mediante su responsable.

## Revisión y operación

No se modifican CORE/COREDB, CAP/EVA, Seguridad, CI, Compose/Docker globales, dependencias ni configuración frontend compartida. Laboratorio E06 detenido, MySQL tmpfs desechable, sin datos/volúmenes institucionales. Rollback y reproducción están descritos en la entrega; no ejecutar limpieza global ni revertir reservas/snapshots para ocultar errores.

Los OpenAPI y JSON saneados son evidencias deliberadas de revisión; E01/E05 son históricos y E06 es la referencia final. Excluir cachés, builds, entornos, logs crudos y secretos temporales. La [lista explícita de commit](sol-archivos-commit.txt) excluye las instrucciones locales de raíz y el README de instalación del paquete. Descripción preparada para revisión: PR no creado ni publicado.
