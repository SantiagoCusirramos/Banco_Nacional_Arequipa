# Cierre documental de feature/integracion-sol

Fecha: 2026-11-14, America/Lima. Rama verificada `feature/integracion-sol`, HEAD `86904edd8dc866c1d4260a996748a1cda3770007`. E01–E06 cerradas; sin desarrollo funcional nuevo, staging, commit, push o PR publicado. [Descripción de PR](sol-pr-descripcion.md), [nota para equipos](sol-coordinacion-proveedores.md), selección exacta (`sol-archivos-commit.txt`, retirado del repositorio; ver `change-log.md`), [changelog](change-log.md).

## Dictamen de selección

Se revisaron diez archivos seguidos modificados y 37 sin seguimiento al comenzar, expandiendo el directorio de prompts a sus seis archivos. Este cierre agrega cuatro documentos/ayudas: tres Markdown y una lista de selección. Al terminar: **diez seguidos modificados y 41 untracked; 49 archivos recomendados para el commit, dos excluidos**. Clasificación de lo recomendado: ocho archivos funcionales SOL, cuatro de pruebas y 37 de documentación/ayudas/evidencias (24 Markdown, nueve JSON, dos scripts, un Compose de laboratorio y una lista TXT).

No hay cachés, builds, entornos virtuales, logs crudos, dumps o BD entre los archivos candidatos. Los JSON son artefactos documentales deliberados: seis OpenAPI E01/E05/E06 y tres evidencias/manifiesto E06. Incluirlos preserva enlaces, comparación histórica y reproducción; E06 es el contrato final, E01/E05 no representan el estado actual. Los seis OpenAPI ocupan unos 482 KiB; el tamaño no justifica eliminar evidencias ya referenciadas. Prompts/plan se incluyen como historial de alcance, no para ejecutar otra fase.

`AGENTS.md` raíz se conserva y sigue rigiendo esta sesión, pero se propone fuera del commit SOL porque introduce instrucciones persistentes a nivel repositorio; el equipo puede decidir versionarlo separadamente. `README-INICIO.md` es el instructivo de instalación del ZIP de prompts, ya innecesario en la entrega funcional. No se borró ni movió ninguno. No se modifica `.gitignore` para esconderlos.

## Inventario exhaustivo de cambios y sin seguimiento

| Archivo | Clase | Recomendación | Motivo |
| --- | --- | --- | --- |
| `AGENTS.md` | Instrucciones locales de raíz | Excluir de este commit | Aportado por usuario; alcance de instrucciones raíz requiere acuerdo del equipo |
| `Documents/solicitud-credito/change-log.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/compose-e06.yaml` | Configuración de laboratorio SOL | Incluir | Compose separado bajo documentación, secretos solo por entorno |
| `Documents/solicitud-credito/e06_validar_http.py` | Ensayo reproducible E06 | Incluir | No autoejecutable en CI; solo laboratorio sintético explícito |
| `Documents/solicitud-credito/e06_validar_mysql.py` | Ensayo reproducible E06 | Incluir | No autoejecutable en CI; solo laboratorio sintético explícito |
| `Documents/solicitud-credito/plan-integracion-sol.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/prompts/E01-diagnostico-contratos.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/prompts/E02-funcionalidades-rf.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/prompts/E03-captacion-coredb.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/prompts/E04-evaluacion.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/prompts/E05-seguridad-frontend.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/prompts/E06-validacion-entrega.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-apis-disponibles.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-archivos-commit.txt` | Lista explícita de selección | Incluir | Ayuda revisable para Git; no ejecuta comandos |
| `Documents/solicitud-credito/sol-auditoria-e01.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-auditoria.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-baseline.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-captacion-coredb.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-cierre-rama.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-contrato-evaluacion.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-contratos-finalizacion.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-coordinacion-proveedores.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-e06-http-evidencia.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-e06-manifiesto.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-e06-reinicio-privacidad.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-entrega-final.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-evaluacion.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-evidencias-testing.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-funcionalidades-internas.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-matriz-rf.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-openapi-e01-real.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-openapi-e01-simulado.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-openapi-e05-real.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-openapi-e05-simulado.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-openapi-e06-real.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/openapi.json` | Artefacto documental saneado | Incluir | OpenAPI histórico/final o evidencia deliberada; no caché temporal |
| `Documents/solicitud-credito/sol-pr-descripcion.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `Documents/solicitud-credito/sol-seguridad-frontend.md` | Documentación SOL | Incluir | Trazabilidad/contratos/plan/prompts/resultados o cierre para el equipo |
| `README-INICIO.md` | Instalación del paquete de prompts | Excluir | Material de preparación local, no entrega funcional; conservar sin borrar |
| `backend/SOL/app.py` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |
| `backend/SOL/integrations.py` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |
| `backend/SOL/observability.py` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |
| `backend/SOL/operations.py` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |
| `backend/SOL/schemas.py` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |
| `backend/SOL/service.py` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |
| `backend/SOL/tests/test_integration_v2.py` | Prueba automatizada | Incluir | Regresión SOL; fixtures sintéticas |
| `backend/SOL/tests/test_workflow.py` | Prueba automatizada | Incluir | Regresión SOL; fixtures sintéticas |
| `frontend/__tests__/sol-pagina.test.tsx` | Prueba automatizada | Incluir | Regresión SOL; fixtures sintéticas |
| `frontend/__tests__/sol-proxy.test.ts` | Prueba automatizada | Incluir | Regresión SOL; fixtures sintéticas |
| `frontend/app/api/solicitud-credito/[...path]/route.ts` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |
| `frontend/app/solicitud-credito/page.tsx` | Código funcional SOL | Incluir | Cambios E02–E06 ya validados; sin edición en este cierre |

## Alcance, seguridad e integridad

- Diff seguido completo revisado: `backend/SOL/` y las dos rutas frontend SOL; ocho fuentes funcionales y dos tests seguidos. Los dos tests frontend nuevos deben añadirse explícitamente: no aparecen en `git diff --stat` mientras estén untracked.
- Sin diff en CORE/COREDB, CAP/EVA, Seguridad, esquemas/modelos SQL/migraciones/política demo, Docker/Compose globales, CI, package/lock/Next/Vitest compartidos. Compose nuevo es un laboratorio SOL, no reemplaza el global. El filtro de Uvicorn vive durante lifespan de SOL; debe desplegarse en su proceso separado como documentado. `SOL_PUBLIC_ORIGIN` es configuración operativa nueva del proxy; no se modificó el entorno compartido para activarla.
- Todos los 28 hashes del manifiesto E06 siguen coincidiendo, incluidos código/tests/política/dependencias de referencia. Las pruebas E06 registradas siguen vinculadas a esas fuentes, sin reejecutar suites por este cierre documental.
- Lectura/escaneo de todos los candidatos: sin claves privadas, PAT GitHub, patrones AWS/JWT, URLs con contraseña, conflictos, symlinks ni archivos `.env` privados detectados; claves efímeras E06 conocidas ausentes. Solo se imprimieron nombres/tipos, no valores sensibles. Fixtures y tokens marcados como sintéticos permanecen en tests: no son credenciales institucionales ni configuración para producción. OpenAPI describe campos de autenticación, no valores secretos.
- Este escaneo está limitado a archivos modificados/untracked y patrones conocidos; no certifica toda la historia Git ni todos los formatos posibles. No se incorporaron archivos ignorados ni se usó `git add -f`.
- Rutas `/tmp` de evidencia describen la ejecución pasada, no contienen el archivo privado. Excluir `/tmp/bna-sol-e06.env`, venv/cachés npm/Node/build `.next`/node_modules, copias frontend temporales y logs sin sanear. Están fuera de la lista; no se trasladaron al repo ni se eliminaron.
- Los enlaces históricos ya conocidos en `sol-apis-disponibles.md` pueden reflejar su ubicación antigua `docs/`; la entrega actual/matriz y este cierre son los índices vigentes. No se reescribió el informe histórico. Las instrucciones del plan y los prompts son históricas, no autorización para recomenzar E01–E06.

## Validación reutilizada y limitaciones de revisión

E06: 169 backend SQLite/MockTransport y 169 con fixtures MySQL, dos advertencias cada ejecución; 114 frontend más dos fallos esperados heredados; lint/TypeScript/build correctos. TCP 142, migración/transacciones/locks 7 y privacidad/reinicio 4. Algunos tests independientes son SQLite aun con fixtures MySQL; no sumar repeticiones como casos únicos. CAP/EVA/Auditoría simulados, sin navegador real/SSO/TLS institucional/proveedores homologados. Ningún RF integrado_real; pago doble y validación institucional de fiadores siguen bloqueados. Detalle en [evidencias](sol-evidencias-testing.md).

En este cierre solo se ejecutaron comprobaciones de lectura/diff/hashes/AST/JSON/espacios/enlaces nuevos y escaneo de secretos. No Docker, pruebas de BD ni scripts globales/destructivos. La comparación es HEAD local frente al workspace; no se eligió ni actualizó la rama destino del PR, no se hizo fetch y no se certifica ausencia de conflictos con la rama que el equipo seleccione.

## Comandos recomendados, para ejecutar solo después de revisar

La lista contiene paths literales: evita `git add .` y conserva el tratamiento correcto de `[...path]`. No ejecutados por el asistente:

```bash
git branch --show-current
git status --short
cat Documents/solicitud-credito/sol-archivos-commit.txt
git diff --check
git --literal-pathspecs add --pathspec-from-file=Documents/solicitud-credito/sol-archivos-commit.txt
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
git diff --cached
git status --short
```

Comprobar rama feature/integracion-sol, 49 archivos seleccionados y solo AGENTS.md/README-INICIO.md fuera de la selección en este estado. Si aparecen otros archivos, detener y revisar; no ampliar automáticamente la selección. La lista es una instantánea, no garantía sobre contenido editado después. Si algo se selecciona por error, `git restore --staged -- <ruta>` retira únicamente ese archivo del índice, sin borrar su trabajo.

Después de aprobar el diff staged, el commit recomendado (no ejecutado) es:

```bash
git commit -m "feat(sol): validar flujo local y preparar contratos de integración"
```

No se recomienda publicar ni hacer push en este cierre. Título y cuerpo del futuro PR están en sol-pr-descripcion.md; la nota a proveedores está preparada, no enviada. El siguiente paso es revisión del equipo y selección consciente del commit, no otra fase funcional.
