> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# E05 — Seguridad, auditoría, OpenAPI y frontend SOL

Fecha: 2026-11-14, America/Lima. Rama `feature/integracion-sol`. HEAD base `86904edd8dc866c1d4260a996748a1cda3770007` más cambios locales E02–E05, sin commits/push. Se preservaron aportes y modificaciones previas. Referencias: [plan](../planes/plan-integracion-sol.md), [matriz RF](sol-matriz-rf.md), [contratos E01](../contratos/sol-contratos-finalizacion.md), [evaluación E04](sol-evaluacion.md), [changelog](../../change-log.md).

## Resultado y alcance verificado

| Verificación final | Resultado real |
| --- | --- |
| Backend SOL completo | **163 passed, 2 warnings, 38,50 s**, salida 0; 149 anteriores +14 E05, SQLite/MockTransport |
| Frontend completo, 7 archivos | **109 passed, 2 expected fail (111), 4,83 s**, salida 0; 83 aprobadas previas +26 SOL nuevas; dos fallos esperados ya existentes |
| Lint frontend completo | `npm run lint`, salida 0 |
| TypeScript aislado | `tsc --noEmit --incremental false`, salida 0; también aprobado durante build final |
| Producción Next.js 16.3.8/Turbopack | `npm run build`, salida 0 en copia temporal con caché limpia y ejecución autorizada; compilación 3,6 s, TypeScript 3,5 s; `/solicitud-credito` y proxy presentes |
| OpenAPI actual por modo | Generado y comprobado sin lifespan/base externa; 40 modelos, 2 esquemas HTTP Bearer; SIMULADO 31 paths/35 operaciones, REAL 17/19 |

Las pantallas se verificaron mediante **React Testing Library/jsdom con fetch mock**; el proxy se ejecutó con NextRequest/Response y upstream fake. No se ejecutó navegador real, recorrido TCP Next→FastAPI→MySQL ni proveedor Seguridad institucional. La compilación es real, pero no acredita esos servicios. Las pruebas backend comprueban reglas/persistencia local y no certifican locks MySQL.

E05 está completada en ese alcance y **SOL puede pasar a E06 para validación/entrega**, conservando los bloqueos externos. No se declara integrado_real. No se modificaron CORE/COREDB, CAP/EVA, Seguridad, otras páginas bancarias, Docker/CI, modelos SQL, migraciones, política financiera, package.json o lockfile.

## Autenticación, sesiones y privacidad

Fuentes actuales: `backend/SOL/app.py:129`, `:132`, `:165`, `:210`, `:524`; `SOL/security.py`; pruebas en `SOL/tests/test_integration_v2.py` con prefijo `test_e05_`.

| Hallazgo reproducido | Cambio aplicado | Evidencia |
| --- | --- | --- |
| 422 de FastAPI reflejaba password/valores y nombres de campos extra enviados por cliente | Manejador RequestValidationError devuelve loc/msg/type sin input/ctx; claves extra se reemplazan por campo_no_admitido; ubicación se serializa sin surrogate inválido | Marcador sensible sintético ausente en respuesta/logs; mantiene detail como lista compatible con UI |
| Sesión era válida exactamente en su instante de vencimiento | Rechazo con `expires <= now()` | Reloj congelado al deadline devuelve 401 |
| Login bloqueaba EVALUADOR en REAL, pero una sesión residual podía seguir usándose | La comprobación de sesión aplica también la restricción existente por modo | Token sintético de sesión demo previa rechazado con 401 en REAL; SIMULADO conservado |
| OpenAPI no expresaba mecanismo real de autenticación | HTTPBearer/Security con esquemas separados SOLSession y EVACallback, auto_error desactivado para conservar 401 propio | Rutas protegidas declaran security y callback usa solo EVACallback; token de sesión no sustituye al de servicio |

Se mantiene PBKDF2 con salt y hash de tokens; el rol/actividad se consultan en servidor, no se aceptan desde el navegador. Revocación local de supervisor elimina **todas** las sesiones del objetivo; se probó con dos sesiones, ausencia de permiso del asesor, lectura operativa de supervisor/auditor y prohibición de autobaja. La facultad de supervisor es de laboratorio, pendiente de Seguridad institucional.

Minimización E02/E03 se conserva: whitelist de identidad/referencia, sin contacto/nacimiento/biometría extra en respuestas o snapshots nuevos; proyección histórica no reescribe registros. Los documentos de identidad y actor/solicitud siguen presentes donde el contrato actual los requiere; no se afirma anonimización absoluta. Los logs propios usan ruta normalizada/correlación/operación/estado/duración, no cuerpos, query, tokens ni contraseñas. Las pruebas previas de PII, accesos, actor/sujeto y rollback continúan pasando.

El token de login es necesario en la respuesta **servidor SOL→proxy**, pero el proxy devuelve al navegador solo usuario y cookie HttpOnly. No se confunde minimizar con eliminar credenciales del transporte que las necesita. Los fakes usan credenciales sintéticas; los JSON OpenAPI no incluyen sus valores.

## Auditoría CR-INT-10

Se conserva outbox transaccional, evento estable, acuse positivo, backoff, reservas y separación por modo. `backend/SOL/operations.py:84` ahora comprueba bajo bloqueo la generación `attempts` al volver de HTTP. Una respuesta vieja no confirma/libera/reprograma otra reserva ni cambia datos de un evento ya confirmado. Reutiliza columnas existentes, sin migración.

`Integrations.audit` rechaza acuse solo de espacios, además de ID incorrecto, confirmado distinto de true, null o exceso de longitud. Contrato sigue `{idEvento,confirmado:true,acuse}` y reintentos conservan idEvento; el receptor debe deduplicar persistentemente. Las pruebas simulan generaciones/intercalados y fallos; no certifican concurrencia del receptor real.

SIMULADO marca SIMULADO con acuse local. REAL marca CONFIRMADO únicamente tras el acuse positivo del **receptor configurado**, que puede ser fake: no significa por sí mismo Seguridad institucional. Pendientes de otro modo no se exportan automáticamente. La pantalla muestra esa distinción.

El prototipo `backend/seguridad` tiene su API `/seguridad/...`, pero no el POST compatible `/security/events` de CR-INT-10; no se modificó ni conectó. No se declara SSO/MFA, SIEM, retención, roles institucionales o entrega exactamente una vez. Se conserva la dependencia real del propietario de Seguridad.

## Brechas OpenAPI E01 cerradas localmente

Artefactos actuales: [SIMULADO](../../sol-openapi-e05-simulado.json) y [REAL con configuración fake](../../sol-openapi-e05-real.json). Los JSON E01 quedan como evidencia histórica sin sobrescribirlos.

- Respuestas nombradas/anidadas para usuario/login, referencias, política, condiciones/garantías/fiadores, calendario, resumen/detalle/versiones/eventos/resultados/envíos, paginación, recepción, baja, pendientes, métricas y salud. Dinero permanece string decimal; float solo se usa para duración de métricas, no cálculo financiero. Modelos en `backend/SOL/schemas.py:72`–`:280`.
- `response_model_exclude_unset` preserva opcionales ausentes; nulos explícitos como evaluación/ronda pendientes y estado anterior en creación se conservan. La regresión de snapshots/acuse/lecturas pasó con los modelos de salida.
- Dos mecanismos Bearer documentados y usados en dependencias del servidor. No son una nueva identidad central ni un JWT compatible con COREDB.
- Códigos por operación: 201 de alta, **202 de reserva pendiente**, 401/403 de auth/rol, 404/409/422/429/503 según ruta; readiness 503 con su schema de salud. Los errores públicos conservan detail string/objeto/lista, ahora sin reflejar entradas sensibles.

Generación con `create_app(Settings('sqlite://', worker_seconds=0)).openapi()` y variante REAL fake del entorno P01; sin lifespan, HTTP, tablas o conexión externa. Aserciones de schemas no vacíos para 2xx, security schemes y 202 aprobadas, salida 0. OpenAPI sigue versión de aplicación 2.0.0; no se cambió contrato financiero ni se homologa por exportarlo. Las respuestas JSONResponse (por ejemplo 202) se construyen con la misma proyección de expediente y se documentan explícitamente.

## Proxy y configuración por modo

Archivo: `frontend/app/api/solicitud-credito/[...path]/route.ts`; se leyeron guías locales de Next 16.3.8 Route Handlers/cookies/Vitest antes de editar, conforme a frontend/AGENTS.md.

- Escrituras exigen Origin presente, parseable y con mismo esquema/host/puerto que la URL de Next. Origen nulo, ausente, externo o con esquema distinto devuelve 403; URL inválida ya no produce excepción sin manejar. Esto protege el canal de cookie del navegador; integraciones servidor a servidor usan sus endpoints directos.
- Se rechazan segmentos `.`/`..`, vacíos o separadores dentro del segmento; callbacks `integrations` devuelven 404 en el canal navegador. No se agregan rutas a otro módulo ni se permite elegir host desde la petición.
- Todas las respuestas del proxy tienen Cache-Control no-store. Cookie HttpOnly/SameSite=Lax, Secure configurable; 401 y logout la eliminan, incluso si transporte del logout falla. En ese caso la revocación remota no se confirma: la sesión del servidor puede permanecer hasta caducar y no se presenta como revocada centralmente.
- Login sin token válido devuelve 503 sin crear cookie. El token nunca se devuelve en el JSON del navegador; Authorization saliente usa cookie de servidor, no la cabecera arbitraria enviada por el navegador.
- Se preservan X-Idempotency-Key, correlación por petición, abort de 3 s, no-store upstream y redirect error; fallo de transporte devuelve 503 sin texto remoto. URL faltante falla explícitamente, sin fallback.

`SOL_GATEWAY_URL` se usa tal como está configurada: `/gateway/sol` en laboratorio SIMULADO o `/sol` directo de laboratorio para transporte REAL. Se probó ambos valores con upstream fake, sin activar proveedor. Compose sigue SIMULADO; cambiar a REAL requiere configuración completa coordinada, no un cambio silencioso del proxy. `SOL_COOKIE_SECURE=true` corresponde a HTTPS; la configuración pública/reverse proxy debe conservar el origen correcto y verificarse en E06. No se cambiaron variables ni infraestructura para fingir ese despliegue.

## Pantallas y endpoints verificados

Las rutas de la tabla son canónicas FastAPI; el navegador llama `/api/solicitud-credito/*`. Los callbacks EVA no pasan por ese proxy. Fuente UI: `frontend/app/solicitud-credito/page.tsx`, pruebas `frontend/__tests__/sol-pagina.test.tsx` y `sol-proxy.test.ts`.

| Pantalla/acción | Endpoints SOL | Verificación E05 |
| --- | --- | --- |
| Acceso/cierre/caducidad | POST auth/login, GET auth/me, POST auth/logout | Login/logout en componente; cookie/token/Secure/401 en proxy; sesión y revocación real en backend aislado. Limpieza de expediente/formulario/credencial/operaciones y claves al salir o recibir 401 |
| Bandeja/política/clientes | GET applications paginado, policy, clients | Carga por rol; asesor ve alta, supervisor/auditor no; conserva manejo de esquema/lista y catálogo. E02/E03 siguen verificando validación autoritativa servidor |
| Crear/previsualizar/guardar | POST preview, POST applications | Wizard con cliente/condiciones, calendario mock y guardado sin envío; UI llama a backend, no impone política nueva |
| Editar/subsanar | PUT applications/{id}, POST applications/{id}/revise | Apertura editable de nueva versión observada; bloqueo de edición congelada. Persistencia/inmutabilidad y PUT se verifican también en regresión backend E02/E04 |
| Envío/pendiente recargado | POST applications/{id}/send, GET detalle | Recupera idOperacion de envíos, reintenta misma clave, 202 se muestra pendiente y no como acuse; doble clic durante petición produce un solo envío; ERROR_CONTRATO bloquea reenvío con etiqueta de revisión |
| Resultado demo | POST applications/{id}/demo-result | Render y envío OBSERVADO solo con EVALUADOR + SIMULADO; control oculto en REAL y servidor rechaza sesión demo residual |
| Operación/auditoría | GET ops/pending, GET ops/metrics | Nueva sección dentro de Integraciones para SUPERVISOR/AUDITOR, muestra IDs pendientes/errores, conteos y p95 local; oculta al asesor |
| Revocación local | POST admin/users/{username}/disable | Solo SUPERVISOR ve formulario; prueba UI invoca ruta/cuerpo existentes y limpia motivo, backend revoca todas las sesiones y prohíbe autobaja |
| Historial/versiones/exportación | GET detalle; Blob local para JSON | Esquema de detalle y proyección mínima conservados por backend; no endpoint de exportación nuevo. No se hizo prueba de descarga en navegador real |
| Resultado EVA real | POST integrations/evaluation-results | Esquema/auth/errores y regresión E04; proxy lo bloquea. Ninguna llamada a EVA/Bus institucional |

Las secciones de calendario/historial/versiones pertenecen al mismo detalle, no a servicios separados. No hubo rediseño visual ni cambios CSS. Los errores detail objeto muestran `mensaje` legible, en vez de `[object Object]`; se mantienen errores de validación en lista y strings. El cambio de modo se rotula como HTTP configurado/institucional pendiente, no integración certificada.

## Reproducción y resultados intermedios

Backend: entorno `/tmp/bna-sol-p01-venv` ya preparado, sin instalar más paquetes. Prefijo real de pruebas:

```bash
env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts=
```

| Lote/argumentos | Resultado real |
| --- | --- |
| test_integration_v2.py -k e05, reproducción | Salida 1: 5 failed, 2 passed, 101 deselected, 2 warnings, 2,34 s |
| Misma selección, corrección inicial | Salida 0: 7 passed, 101 deselected, 2 warnings, 2,83 s |
| SOL/tests, primera regresión | Salida 0: 156 passed, 2 warnings, 39,21 s |
| Selección sesión residual/acuse, reproducción | Salida 1: 2 failed, 5 passed, 108 deselected, 2 warnings, 0,56 s |
| -k e05 completo, tras correcciones | Salida 0: 14 passed, 101 deselected, 2 warnings, 3,13 s |
| SOL/tests final | Salida 0: 163 passed, 2 warnings, 38,50 s |

Frontend: no había node/npm en PATH. Se descargó Node oficial temporal; 22.16.0 disparó warnings de engine del lockfile, se usó **22.22.2** compatible. `npm ci --ignore-scripts --no-audit --no-fund` instaló 474 paquetes en `/tmp/bna-e05-frontend`, copia de fuentes con cambios sincronizados, caché `/tmp/bna-e05-npm-cache`. No se modifica lockfile ni node_modules del repo. Primer npm ci falló por EAI_AGAIN y exit handler; repetición autorizada funcionó. Un comando inicial de test en raíz sin package.json falló ENOENT y se corrigió a la copia temporal.

Comandos en esa copia, con `PATH=/tmp/node-v22.22.2-linux-x64/bin:$PATH`:

```bash
npm test
npm run lint
./node_modules/.bin/tsc --noEmit --incremental false
NEXT_TELEMETRY_DISABLED=1 timeout 180s npm run build
```

| Frontend | Resultado real |
| --- | --- |
| Baseline sin tests SOL | 83 passed, 2 expected fail, 5 archivos, salida 0, 4,92 s |
| Primera selección SOL (antes de corregir) | 10 failed, 8 passed, 2 archivos, salida 1, 1,69 s |
| Selección SOL corregida | 18 passed, salida 0, 1,68 s |
| Ampliación de pruebas de UI/proxy | 107 passed, 2 expected fail, salida 0, 5,72 s |
| Modo consola demo antes de ocultar REAL | 1 failed, 1 passed, 11 skipped, salida 1, 1,04 s |
| Suite final | 109 passed, 2 expected fail, 7 archivos, salida 0, 4,83 s |
| Build inicial sandbox y repetición con caché anterior | Salida 1, Turbopack/PostCSS no pudo abrir puerto interno; no fallo de TypeScript atribuido a SOL |
| Build autorizado con caché temporal limpia | Salida 0; Next 16.3.8 compiló y verificó tipos, generó ocho páginas y rutas esperadas |
| Lint/TypeScript | Ambos salida 0; lint repetido al cierre salió 0 |

La caché `.next` fallida se movió dentro de `/tmp`, sin borrar datos del usuario ni modificar configuración. No se ejecutaron `./bna test/smoke`, reset, down -v, migraciones o bases compartidas. Warning Vite preexistente sobre __dirname/configLoader y aviso de deprecación de ESLint durante instalación no se ocultaron. Los dos expected fail son de las pruebas anteriores, no fallos introducidos por SOL.

## Bloqueos institucionales y paso a E06

| Pendiente | Responsable/condición |
| --- | --- |
| Identidad central/SSO/MFA y roles autorizados | Seguridad; sesión local y supervisor de laboratorio no equivalen a aprobación institucional |
| API receptora CR-INT-10 compatible, acuse/dedupe persistentes | Seguridad/Bus; el prototipo actual no ofrece el contrato esperado |
| TLS/origen/cookies y reverse proxy público | Infraestructura/Seguridad; comprobar en despliegue real, sin cambiar infra desde SOL |
| Retención, custodia, monitoreo, operación del worker y revocación central | Equipos responsables; p95 de proceso y outbox local no constituyen plataforma institucional |
| MySQL, navegador/TCP y E2E real entre equipos | E06 en entorno aislado y con proveedores disponibles; no sustituir con mocks |
| Reglas CAP/EVA, pago doble y fiadores reales | Bloqueos E02–E04 conservados; ningún pase local los aprueba |

**Preparado para E06 en el alcance local.** Las vulnerabilidades reproducidas y brechas OpenAPI de E01 están corregidas/verificadas dentro de SOL. E06 debe consolidar trazabilidad/evidencia y documentar o ejecutar las pruebas de despliegue faltantes sin anunciar integración real mientras esos acuerdos/proveedores falten. No se ejecutó E06 en esta tarea.
