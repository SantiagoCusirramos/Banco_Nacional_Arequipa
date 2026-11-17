> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# Entrega de segunda etapa SOL — SOL-LAB-CLOSE

Fecha: 2026-11-16 (America/Lima). Rama `feature/sol-integracion-cap-eva`. Base E01–E06 y HEAD actual: `de4ace61f9fce7befb79828ea56133a6667eb914`. No commits nuevos, staging ni publicación.

**Veredicto: LISTA CON LIMITACIONES DOCUMENTADAS para revisión como segundo PR.** La regresión no muestra fallos nuevos. El circuito CAP→SOL→EVA→SOL y la integración institucional siguen sin demostrar: no se autorizó el simulador CR10 ni existe receptor homologado confirmado. Este cierre no cambia esa decisión ni activa SOL REAL.

Documentos de revisión: [descripción PR](sol-integracion-pr-descripcion.md), [archivos exactos](sol-integracion-archivos-commit.txt), [matriz RF vigente](../etapas/sol-matriz-rf.md), [HTTP independiente](../etapas/sol-pruebas-integracion-cap-eva.md), [laboratorio](../../laboratorio/README.md), [changelog](../../change-log.md).

## Diferencias exactas respecto a E01–E06

| Categoría | Cambios de esta segunda etapa |
|---|---|
| `backend/SOL/settings.py` | Seis variables URL/token CAP/EVA/Auditoría, parejas indivisibles, compatibilidad Bus cuando ambos campos propios faltan, configuración REAL explícita y callback distinto de salida |
| `backend/SOL/integrations.py` | Clientes por pareja destino/credencial, selección explícita por proveedor, URLs de petición relativas/redirects deshabilitados, sin fallback por fallos; normalización/proyección mínima de materno ausente/null/vacío |
| `backend/SOL/schemas.py` | `ClientResponse.apellido_materno` opcional/default vacío |
| `backend/SOL/service.py` | Nombre resumido sin inventar segundo apellido; proyección mínima de detalles/fiadores/historia sobre copia, sin reescribir snapshot |
| `backend/SOL/app.py` | Solo import/proyección de lista de clientes; receptor EVA y autenticación intactos |
| `backend/SOL/tests/test_providers.py` | 50 casos nuevos por parametrización, aislamiento de secretos/destinos, configuración incompleta, SIMULADO/Bus, gate CAP, pérdida de respuesta/conciliación y callback/subsanación con proveedores fake |
| Laboratorio | Compose exclusivo, overlay audit-sim opt-in, recetas, captura selectiva por SHA y SOL workspace, secretos externos, bootstrap SOL, guardias de escritura/simulación, sondas, pruebas HTTP independientes y controles estáticos/DTO/OpenAPI |
| Documentación | Auditoría PR, adaptadores, plan/build/HTTP, matriz actualizada, este cierre, descripción PR y manifiesto de commit |

Las cinco fuentes funcionales suman98 inserciones/31 eliminaciones frente a de4ace6. La selección completa tiene29 archivos, enumerados uno por línea en el manifiesto. No incluir todo el árbol mediante `git add .`.

**No cambian** finance.py, política demo, modelos SQL, migraciones, workers/reservas persistidas, operaciones de conciliación, callback, frontend, dependencias, COREDB/CAP/EVA/Seguridad ni Compose/CI compartidos. El primer PR contiene49 archivos (E01–E06 frente a86904ed), incluidos frontend SOL, OpenAPI y sus pruebas: esos cambios están heredados en HEAD y no deben atribuirse de nuevo al segundo PR.

## Pruebas nuevas ejecutadas en este cierre

Se usaron imágenes ya exclusivas del ensayo, montajes de fuentes solo lectura y contenedores efímeros. SQLite/CAP/contratos/frontend se ejecutaron sin red tras instalar dependencias frontend en copia temporal. Ninguna cifra de la tabla reutiliza pruebas históricas como si fueran nuevas.

| Prueba | Resultado real y alcance |
|---|---|
| Backend SOL SQLite | **219 passed**,1 warning,45,45s, salida0; aviso adicional pytest_asyncio de configuración de loop antes del resumen |
| Suite SOL con MySQL habilitado | **219 passed**,1 warning,51,77s, salida0. Fixtures que consumen SOL_TEST_DATABASE_URL usan MySQL; pruebas puras/configuraciones SQLite explícitas siguen en memoria. No afirmar219 casos íntegramente MySQL |
| Seguridad, roles, callback, auditoría, reservas, idempotencia, recuperación | Incluidos en las suites anteriores; Fake/MockTransport y bases de pruebas, no EVA/Seguridad institucionales |
| CAP COREDB/flujo/lógica | **33 passed**,1 módulo skipped,1 warning,1,32s, salida0; módulo CAP-SOL omitido en imagen COREDB por tzdata ausente |
| CAP→SOL, módulo omitido anterior | **4 passed**,1 warning,0,29s, salida0 en providers con tzdata. En conjunto se ejecutaron37 casos CAP distintos en dos imágenes; no se oculta el skip de la primera |
| DTO SOL/EVA/OpenAPI y caracterización worker | **10 passed**, dentro de ejecución22 passed,1,30s, salida0 |
| Motor EVA existente | **12 passed**, incluido en esos22; regla provisional del PR, no aprobación institucional |
| Validador de aislamiento | **9 passed**,0,621s, salida0; Compose base/overlay, destinos, tokens, permisos y97 hashes correctos |
| Frontend, copia idéntica a HEAD | **114 passed,2 expected fail**,7,24s, salida0. Los dos expected fail son preexistentes, no fallos nuevos ocultados |
| TypeScript / lint / Next build | **0 / 0 / 0**, copia temporal, Next16.3.8. npm ci474 paquetes salida0; sin actualizar lockfile/original |
| OpenAPI SIMULADO y REAL | Comparación completa en memoria contra E06 aprobada: único delta, materno opcional/default vacío; rutas, métodos, auth SOLSession/EVACallback, respuestas/códigos y callback coinciden |
| Git/seguridad/documentación |580 archivos Git escaneados sin coincidencias con patrones de claves privadas/GitHub/AWS o secretos sintéticos actuales; controles de candidatos y diff al cierre |

Advertencias backend: deprecación AnyIO/Starlette y aviso pytest_asyncio. Frontend: advertencia de configuración futura Vite y ESLint9 deprecado durante instalación. No se cambiaron dependencias para ocultarlas. No se ejecutó un análisis CVE exhaustivo; que no haya dependencias nuevas no certifica ausencia de vulnerabilidades del baseline.

### Seguridad de la regresión MySQL

Servidor: `bna-sol-cap-eva-lab-int20261116a-mysql-modulos-1`, etiqueta de proyecto y ausencia de puertos/tmpfs comprobadas. Se creó **solo un esquema nuevo bna_sol_mvp_test**, con un usuario aleatorio que tiene permisos únicamente sobre él; sin credenciales de CAP/EVA/COREDB en el runner. Fixtures SOL hacen drop_all/create_all de tablas de ese esquema; no ejecutan DROP DATABASE. Bases CAP/EVA no se alteraron por las suites.

El preparador temporal inicial falló por sustitución incorrecta de marcador SQL y dejó el esquema vacío creado por esta misma tarea. Se corrigió en /tmp y se verificó cero tablas antes de completar el usuario. No se eliminó ni se reutilizó una base institucional/ajena.

**No se ejecutaron** fixtures MySQL EVA que contienen DROP DATABASE/DROP USER/TRUNCATE, inicializadores del circuito SOL REAL, `./bna test/smoke`, resets ni `down -v`. La suite MySQL del PR EVA y el funcionamiento con main actualizado permanecen NO VERIFICADOS; este cierre usó los SHA fijados del laboratorio.

## RF-SOL-001..010: estado vigente

| RF | Estado local | Evidencia/límite externo |
|---|---|---|
|001 Cliente captado | Implementado/preparado para integración | CAP real por HTTP independiente y gate SOL unitario probados; **CAP→SOL activo NO VERIFICADO**; homologación pendiente |
|002 Plazo | Implementado localmente | Regresión aprobada; rango académico, DA-SOL-001 pendiente |
|003 Monto | Implementado localmente | Decimal/límites/histórico; DA-SOL-001 pendiente |
|004 Moneda | Implementado localmente | Catálogo demo; sin aprobación institucional nueva |
|005 Pago doble | **Bloqueado por decisión** | True sigue rechazado; **DA-SOL-005** sin fórmula aprobada |
|006 Calendario | Implementado localmente, PRELIMINAR | Regresión/DTO EVA; DA-SOL-003/004 pendientes |
|007 Garantías | Declaración local implementada | Verificación/valoración institucional DA-SOL-006 pendiente |
|008 Fiadores | Registro local; **validación institucional bloqueada** | **DA-SOL-006**, solo SIMULADA o rechazo REAL seguro |
|009 Envío EVA | Preparado localmente | MySQL/MockTransport y contrato DTO; entrega a EVA real **NO VERIFICADA**, CR10/DA-SOL-009 pendientes |
|010 Resultados/subsanación | Preparado localmente | Callback e historia por fake/DB probados; worker EVA→SOL y subsanación TCP **NO VERIFICADOS**, CR10/DA-SOL-002/008 pendientes |

Ningún RF se marca integrado institucionalmente. Integración independiente COREDB↔CAP no equivale a integración RF001 de SOL.

## Matriz CR-INT

| Contrato | Estado para revisión | Evidencia y pendiente |
|---|---|---|
|CR-INT-01 | COMPATIBLE por contrato; SOL HTTP completo NO VERIFICADO | Rutas CAP GET reales y materno opcional; token propio, gate/vigencia/estado; falta activar SOL y probar su consumo TCP. CAP devuelve200/REVOCADO, SOL debe rechazarlo |
|CR-INT-02 | COMPATIBLE por DTO; integración NO VERIFICADA | POST /eva/applications y GET /eva/operations/{idOperacion} preparados; reserva/idempotencia/conciliación probadas con fake y DB. Falta recepción válida/acuse real y respuesta perdida TCP |
|CR-INT-03 | COMPATIBLE por DTO; ensayo conjunto BLOQUEADO | Receptor /sol/integrations/evaluation-results intacto, tres decisiones, auth/correlación/ronda/versiones; falta callback real/subsanación/reinicio con reservas |
|CR-INT-10 | BLOQUEADA por decisión | Sin receptor homologado ni autorización expresa del simulador. Auditoría obligatoria conservada, no acuses ficticios institucionales |

La evidencia HTTP/MySQL de captación, revocación,401/403/404/409/422/503 y reinicio de APIs pertenece a SOL-LAB-INTEGRATION, está documentada con sus IDs/fecha en el informe independiente y **no se presenta como una nueva ejecución aquí**. En este cierre sí se repitió la inspección de logs en memoria: cero coincidencias con secretos sintéticos y documentos/contactos completos conocidos en COREDB/CAP/EVA; no se exportó log bruto. No es certificación exhaustiva de todos los logs futuros.

## Acciones para CAP, EVA y Seguridad

| Equipo | Acción concreta |
|---|---|
|CAP | Mantener materno opcional y semántica200/REVOCADO; confirmar R01/servicio CLIENTES y autoridad de caso/verificación/vigencia. Entregar proveedores institucionales y acuerdos de identidad. Ningún defecto funcional CAP probado por este cierre: corregidas expectativas/contactos del runner, no CAP |
|EVA | Revisar validación del acuse callback: la prueba unitaria `test_characterizes_eva_2xx_ack_weakness_without_sql` entrega HTTP200 con recibido:false/JSON incompatible y observa la transición solicitada ENTREGADO. `_terminar` interceptado, sin SQL ni TCP. Acordar acuse positivo compatible y validar antes de confirmar; no se editó EVA. Ensayar además lease/respuestas tardías,409 y reintentos, MySQL y subsanaciones reales |
|Seguridad | Definir receptor CR10, autenticación/ruta, idempotencia y acuse homologado. Alternativamente, autorizar explícitamente simulador solo académico con evidencia AUD-SIM; el cierre no lo autoriza. SSO/MFA/roles institucionales siguen fuera de validación local |

## Git, base del PR y conflictos

Consultas GitHub solo lectura del cierre: PR[75 SOL](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/75), [74 CAP](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/74) y [70 EVA](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/70) aparecen abiertos, merged_at null, mergeable unknown. Cabezas SOL de4ace6, CAP4ea5014 y EVA57b0e2a coinciden con las referencias usadas.

`main` local/origin-main permanecen86904ed, sin fetch. Git ls-remote observó main `fcc76b128dedafb6f8e374e03b3bbe1c24d5083d`; API commits/main devolvió729c1e5. Se registró la discrepancia y se comparó expresamente86904ed…fcc76b1 por API, confirmando la cabeza solicitada. En esa instantánea no hay solapamiento de archivos con los49 heredados ni los modificados en esta segunda etapa; los nuevos archivos SOL están bajo su propio directorio. **No garantiza merge limpio**: GitHub no calculó mergeability, no se simuló/fusionó ninguna rama y main contiene cambios COREDB/SQL que este laboratorio congelado no valida. Volver a comprobar al abrir el PR.

Base recomendada del segundo PR: **feature/integracion-sol**, mientras75 siga abierto, para mostrar solo esta etapa. Documentar dependencia de75 y disponibilidad contractual de70/74; no incorporarlos por merge. Cuando75 se fusione, revisar base/diff contra main y repetir la validación pertinente antes de solicitar integración conjunta. No hacer rebase automático ni forzar push.

## Selección de commit y exclusiones

El [manifiesto](sol-integracion-archivos-commit.txt) incluye29 archivos: cinco fuentes SOL, test_providers.py, trece fuentes/configuraciones/README de laboratorio y diez documentos/matriz/changelog/manifiesto de cierre. Solo cambios de esta etapa; no volver a añadir archivos de E01–E06 sin delta.

**Excluir y conservar localmente:** AGENTS.md y README-INICIO.md del usuario; `laboratorio/sources-manifest.json` y `laboratorio/evidencias-http-independientes.json` por ser salidas generadas; todos los contextos, runtime/envfiles, secretos, junit/logs, node_modules/.next, caches, bases/dumps, capturas /tmp y archivos de otros módulos. Los JSON generados no se borraron: se excluyen de la selección y los informes conservan resultados saneados. Las plantillas env del primer PR no se modifican ni se añaden otra vez.

Escaneo de candidatos sin secretos conocidos/patrones, revisión manual de configuración, montajes, código y fixtures; no constituye demostración matemática de ausencia de todo secreto. Credenciales por proveedor separadas, callback diferente, sin fallback de REAL a SIMULADO, controles de auditoría y dominio conservados. Sin dependencias nuevas ni cambios en lockfiles; ningún token real usado.

## Reproducción

1. Leer [README laboratorio](../../laboratorio/README.md), plan y BUILD. `prepare.py --run-id <id-unico>` captura COREDB HEAD, SOL workspace y solo CAP/EVA de sus SHA auditados, genera secretos externos y registra hashes. Guardar nueva evidencia saneada; no versionar runtime/contextos/salidas generadas.
2. Ejecutar validate.py y test_static.py sobre esa ruta, revisar redes/recursos nuevos y gates. No reutilizar un esquema/volumen/identificador de otro ensayo. Los comandos BUILD son posteriores a autorización, no scripts globales.
3. Para pruebas de código SOL, montar backend/SOL solo lectura en la imagen providers y ejecutar pytest con `SOL_INTEGRATION_MODE=SIMULADO`, `SOL_WORKER_SECONDS=0`, `PYTHONDONTWRITEBYTECODE=1`, sin red y sin SOL_TEST_DATABASE_URL:219 SQLite.
4. Para MySQL, crear esquema vacío **bna_sol_mvp_test** en servidor exclusivamente de pruebas y usuario limitado a él; suministrar URL por envfile externo0600, nunca argumento con contraseña. Conectar runner solo a su red privada. Auditar drop_all de tablas de las fixtures; no ejecutar los tests sobre una base de aplicación ni las fixtures EVA que eliminan bases.
5. Contratos/OpenAPI: test_close_contracts.py y test_motor.py con `--noconftest`, sin red y `SOL_CLOSE_REFERENCE_DIR` apuntando a documentación E06 montada solo lectura. DTO/motor no certifican servicio institucional.
6. Frontend: copia limpia sin .env, npm ci con lockfile; después tsc --noEmit, npm run lint, npm test -- --maxWorkers=2 y npm run build. No copiar salidas al repositorio.
7. Recorrido HTTP conjunto: **requiere decisión CR10 antes de SOL REAL**. Preparar caso CAP nuevo habilitado (el de prueba final se revocó); luego expediente, acuse, callback/subsanación y fallos conforme al plan. Este cierre no ejecuta esa fase ni enciende simuladores.

La descripción revisable está en el documento PR y los comandos de publicación manual aparecen al final de este informe. Estado final: código y pruebas listos para revisión; integración institucional y circuito conjunto permanecen pendientes. Los MySQL/API independientes y el esquema de regresión se conservan; no se limpiaron recursos ni se publicaron cambios.

## Publicación manual después de revisión — no ejecutada


Mensaje recomendado: `feat(sol): separar proveedores HTTP CAP y EVA y preparar laboratorio aislado`.

```bash
git branch --show-current
git status --short
git diff --check
git diff --stat feature/integracion-sol
git add --pathspec-from-file=Documents/solicitud-credito/06-historico/entregas/sol-integracion-archivos-commit.txt
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
# Revisar que el índice coincida exactamente con el manifiesto antes de continuar.
git commit -m "feat(sol): separar proveedores HTTP CAP y EVA y preparar laboratorio aislado"
git push --set-upstream origin feature/sol-integracion-cap-eva
```

Opcional, solo por el usuario y si tiene gh disponible:

```bash
gh pr create --draft --base feature/integracion-sol --head feature/sol-integracion-cap-eva --title "feat(sol): adaptadores CAP/EVA independientes y laboratorio de integración" --body-file Documents/solicitud-credito/06-historico/entregas/sol-integracion-pr-descripcion.md
```

Los comandos de staging/commit/push/PR anteriores son instrucciones de revisión humana; ninguno se ejecutó durante el cierre. No force push, merge ni rebase. Cuando75 se fusione, revisar base/diff contra main antes de cambiar la base del segundo PR.
