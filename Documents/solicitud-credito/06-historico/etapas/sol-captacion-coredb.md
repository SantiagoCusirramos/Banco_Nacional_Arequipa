> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# E03 — Captación HTTP, CR-INT-01 y límites COREDB

Fecha: 2026-11-14, America/Lima. Rama `feature/integracion-sol`. HEAD base `86904edd8dc866c1d4260a996748a1cda3770007` más cambios locales E02/E03, sin commit/push. Se preservó E02 y se reutilizó su entorno temporal. Referencias: [contratos E01](../contratos/sol-contratos-finalizacion.md), [funcionalidades E02](sol-funcionalidades-internas.md), [matriz RF](sol-matriz-rf.md), [transporte v2](../contratos/CONTRATOS_HTTP_V2.md), [changelog](../../change-log.md).

## Resultado

RF001 queda **preparado_para_integracion con contrato fake**, no integrado_real. Se reforzó el cliente HTTP existente; no se creó una API CAP ficticia ni se conectó COREDB completando campos ausentes. **107 pruebas aprobadas, 2 warnings, 19,28 s**: las 72 previas y 35 casos nuevos E03, SQLite/MockTransport. No hay evidencia nueva con proveedores institucionales, MySQL, Docker ni TCP.

La interrupción anterior ocurrió durante inspección: al retomar no había modificaciones E03. El estado Git inicial contenía los cinco archivos SOL modificados por E02 y documentación sin seguimiento; todo se preservó. E03 modifica únicamente `backend/SOL/integrations.py`, `backend/SOL/tests/test_integration_v2.py`, este informe, la matriz y el changelog. No cambia CORE/COREDB/CAP/EVA/Seguridad, frontend, Compose, configuración, modelos ni migraciones.

## APIs verificadas: qué puede reutilizarse

Implementado en código no significa desplegado/accesible. No se efectuaron llamadas a servicios del banco.

| API real en el repositorio | Método/ruta efectiva y permiso | Datos/efectos verificados | Reutilización para SOL |
| --- | --- | --- | --- |
| COREDB Cliente | GET `/coredb/clientes/{cod_cliente}`, JWT COREDB + VER_CLIENTE | Identidad, estado, permite_operar, versión, ID de verificación y fecha; sin caso/vencimiento CAP | Fuente parcial de identidad, insuficiente para habilitar CR-INT-01; no consumida por SOL |
| COREDB documento | POST `/coredb/clientes/validaciones/documento`, VALIDAR_IDENTIDAD | Recibe identidad_verificada declarada por llamador, registra validación, responde 201 con resultado/cliente | No sustituye GET de referencia ni valida por sí mismo el caso CAP; no se invoca |
| COREDB registro | POST `/coredb/clientes`, CREAR_CLIENTE | Alta con código generado por CORE; HABILITADO solo para SERVICIO:CLIENTES | SOL no debe crear/habilitar clientes como paso de solicitud |
| COREDB catálogos | GET `/coredb/catalogos/clientes`, autenticado | Tipos documentales y estados de cliente | No aporta vigencia/caso CAP; no necesario ni consumido en esta etapa |
| CORE legado Clientes | GET `/core/clientes` y GET `/core/clientes/{id_cliente}`, JWT CORE + VER_CLIENTE | Maestro legado; búsqueda documento/estado/limite/offset; sin referencia CAP completa | No compatible con búsqueda search/limit ni habilitación requerida; no consumido |

Fuentes: `backend/COREDB/routers/clientes.py:17`, `:62`, `:117`, `:143`, `:178`; `COREDB/CONTRATO_CLIENTES.md:24`, `:50`, `:146`, `:183`; `COREDB/permisos.py:44`; `CORE/routers/clientes.py:45`, `:63`; prefijo `/core` en `CORE/api.py:73`. COREDB registra explícitamente que no tiene búsqueda/listado por nombre/correo/celular. `fecha_verificacion` se ejemplifica como timestamp UTC, frente a fecha de negocio YYYY-MM-DD de CR-INT-01; no se recorta ni convierte automáticamente sin acuerdo.

No se encontraron backends CAP/EVA autónomos en el árbol revisado; sus SQL/modelos no son HTTP. Compose no registra CAP/Bus; los paths `/cap/references` son del simulador SOL. No cambió esa situación desde E01/E02.

## Identificadores, datos faltantes y autoridad

| Campo SOL/CR-INT-01 | COREDB / CORE legado | Regla que se conserva |
| --- | --- | --- |
| `id_cliente` | COREDB usa `cod_cliente` alfanumérico ≤12, generado como CLI+nueve dígitos; CORE legado tiene otro id_cliente | No asumir que son equivalentes. SOL admite referencia opaca ≤36; cualquier correspondencia debe aprobarla el propietario y ser estable/verificable |
| `cod_tipo_documento` | COREDB llama `tipo_documento` | Un cambio de nombre no completa el resto del contrato |
| `id_verificacion` | COREDB publica `id_verificacion_captacion` | No se asignan IDs nuevos ni se equiparan sin acuerdo |
| `id_caso` | No está en ClienteRespuesta COREDB/CORE legado | Debe proceder de CAP; falta → 503 de contrato, nunca inventarlo |
| `fecha_verificacion`, `vigente_hasta` | COREDB tiene fecha de verificación, no vencimiento contractual | CAP debe definir ventana y semántica; no sumar 30/60 días ni sustituir por fecha actual |
| `estado_cliente`, `estado_habilitante` | COREDB aporta ambos; CORE legado no entrega habilitación completa | ACTIVO/HABILITADO son valores del contrato local vigente, pendientes de homologación; permite_operar no los sustituye |
| `version_contrato` y procedencia | Versiones de COREDB/CORE no acreditan CR-INT-01 | Falta acordar versión/autoridad; no se presenta un marcador fake como certificación |

`bna_sol_mvp` contiene exclusivamente referencias mínimas, expedientes/versiones, sesiones y trazabilidad local (`SOL/models.py:1`, `:55`, `:76`; restricción de nombre `SOL/settings.py:58`). La referencia se refresca por HTTP y se guarda minimizada localmente; cada versión conserva el snapshot usado. No es un maestro institucional y no sustituye al proveedor autoritativo.

El CORE legado trabaja sobre `bna` (`CORE/config.py:29`). COREDB es el acceso autorizado a la base integrada y a sus procedimientos de Clientes (`COREDB/services/clientes.py:1`, `:59`). SOL no lee tablas de esas bases, no hace JOIN cruzado, no sincroniza IDs ni migra datos. La sesión SQLAlchemy usada por `captacion_reference` es la **base propia SOL**, no una conexión nueva a CAP/COREDB. La coexistencia de bases en infraestructura local no autoriza lectura directa.

## Contrato mínimo entregable al equipo de Captación

Estado: **propuesta v2 existente, reforzada en validación local**, no contrato homologado. Propietario de caso/verificación/vigencia/habilitación: CAP o proveedor/fachada expresamente acordados. Consumidor: SOL. No se proponen URLs institucionales inexistentes.

| Operación saliente SOL | Configuración | Request | Response esperado |
| --- | --- | --- | --- |
| Búsqueda GET | SOL_BUS_BASE_URL + SOL_CAP_SEARCH_PATH | Bearer SOL_BUS_TOKEN; X-Correlation-ID; query search y limit=50 | Lista JSON directa de 0–50 referencias; no envoltorio items |
| Referencia GET | SOL_BUS_BASE_URL + SOL_CAP_REFERENCE_PATH con `{idCliente}` | Mismas cabeceras; ID codificado para URL | Objeto de referencia completo; 404 significa ausencia |

Los ejemplos de transporte `/cap/references` y `/cap/references/{idCliente}` solo corresponden al simulador. Los tests E03 emplean también `/fake-cap/search` y `/fake-cap/ref/{idCliente}` para demostrar configuración, no para publicar nuevas rutas. SOL expone GET `/sol/clients` al frontend y valida referencia durante preview/alta/edición/envío; alias `/gateway/sol` solo SIMULADO. No se añadieron endpoints públicos.

Campos requeridos actuales: `id_cliente`, `numero_documento`, `nombres`, `apellido_paterno`, `apellido_materno`, `estado_cliente`, `id_caso`, `id_verificacion`, `fecha_verificacion`, `vigente_hasta`, `estado_habilitante`, `version_contrato`: cadenas no vacías ni solo espacios. Cliente ≤36, documento ≤20. Ambos campos de fecha deben ser YYYY-MM-DD válidos; no timestamps/fechas compactas. Opcionales por compatibilidad: `cod_tipo_documento` (si aparece, string no blanco), `simulado` (si aparece, booleano JSON auténtico). No se exige retrospectivamente su presencia ni se acepta un objeto anidado en esos campos.

Referencia individual: ID exactamente igual al solicitado, ACTIVO + HABILITADO y `fecha_verificacion <= hoy Lima <= vigente_hasta`; ausencia/no habilitación/vencida/futura → rechazo funcional. Búsqueda: normaliza esquema y minimiza, pero puede mostrar referencias observadas/bloqueadas/vencidas; no habilita por aparecer en lista. El guardado/envío consulta de nuevo la referencia, no usa la lista como prueba de habilitación. No se fuerza `simulado:false` como prueba de autenticidad ni un literal de versión no aprobado; incluso REAL puede usarse con proveedor fake de laboratorio. La procedencia institucional requiere contrato/despliegue/evidencia externos.

Los extras se descartan mediante `CLIENT_FIELDS`: no se almacena ni devuelve contacto, biometría u otros campos desconocidos. El número de documento sigue siendo parte de la referencia necesaria, no se promete anonimización del expediente. Los errores no reflejan cuerpo/URL/secretos remotos y los logs propios no imprimen cuerpos/query (`SOL/observability.py:23`). El fixture E03 usa documento sintético, sin datos personales reales.

## Cambios funcionales focalizados

1. `SOL/integrations.py:155`: normalizador rechaza campos requeridos blancos, tipos incorrectos de opcionales y fechas fuera de la forma documentada. Misma whitelist y mismos estados/reglas. No agrega un caso, verificación o fecha ausente.
2. `SOL/integrations.py:64`: JSON null en un 2xx es respuesta contractual inválida; solo un 404 explícito retorna ausencia. El control está en el transporte común y también evita tratar null como acuse EVA/AUD. La regresión completa sigue pasando.
3. `SOL/integrations.py:188`: si una sesión se declara REAL pero no tiene adaptador REAL, falla 503 antes de recurrir a una referencia local. La aplicación normal ya inyecta ese adaptador; se cubre una configuración interna incompleta sin fallback.

El cliente ya tenía rutas/token configurables, sin redirects ni proxies de entorno, timeout por fase 0,6 s, máximo dos reintentos adicionales y presupuesto de inicio de llamadas 2,4 s (`integrations.py:29`, `:41`, `:74`, `settings.py:17`). E03 los conserva y verifica, no instala otro cliente ni modifica defaults. Un fallo transitorio seguido de éxito se recupera; errores permanentes no consumen tres intentos. Se mantiene configuración REAL completa exigida al arrancar, incluyendo las dependencias EVA/AUD, sin activar un modo parcial nuevo.

## Autenticación y errores: cliente versus proveedor

| Caso | Respuesta/acción SOL |
| --- | --- |
| Navegador sin sesión SOL | 401 por auth local, antes de llamar CAP |
| Rol sin permiso de crear/editar/enviar | 403 de SOL; GET clientes permanece para sesiones autenticadas según contrato existente |
| Referencia CAP 404 | 422 funcional, sin reintento ni referencia inventada |
| CAP 401/403 | 503 de dependencia/contrato; no reenviar cuerpo remoto ni intentar sesión de persona en CAP; fallo permanente |
| CAP 422 o redirect 302 | 503 de contrato incompatible, sin seguir redirect ni reintentar a ciegas |
| CAP 503/timeout/conexión caída | Hasta tres intentos dentro del presupuesto, luego 503, sin fallback |
| Referencia deshabilitada/vencida/futura | 422; no congelar/enviar solicitud |
| JSON inválido/null/forma o campos incompatibles, cliente distinto | 503; no almacenar como referencia habilitante |

El Bearer saliente fijo del Bus de SOL no equivale a un JWT de COREDB con login/vencimiento/renovación y permisos. El mapa COREDB contempla SERVICIO:CLIENTES, no una cuenta SOL habilitada automáticamente. No se usa una identidad de Clientes para suplantar a SOL. COREDB y CAP deben acordar credenciales de servicio y acceso autorizado antes de cualquier conexión institucional.

## Plan de fachada/composición, sin implementación

Si CAP decide reutilizar COREDB sin modificarlo, una fachada autorizada podría leer identidad por GET de COREDB y combinarla con **datos CAP ya autoritativos**, mediante APIs aprobadas y correspondencia explícita de IDs. Antes necesita:

1. Responsable y contrato versionado para búsqueda y referencia; confirmar actor que entrega caso, verificación y vigencia.
2. Mapeo estable entre cod_cliente e id_cliente, y entre IDs de verificación, con discrepancias rechazadas. No generar UUIDs para aparentar correspondencia.
3. Fuente CAP accesible con todos los datos faltantes; si no existe, la fachada sigue bloqueada. No puede fabricar vencimiento ni inferir aprobación del estado ACTIVO.
4. Semántica de fecha/huso, apellidos opcionales, privacidad, permisos, tokens/TLS/origen, errores y límites de búsqueda aprobados.
5. Pruebas conjuntas con versiones, ambiente, responsables y datos sintéticos; prueba de revocación de habilitación entre guardado y envío.

Es un plan para los equipos, no un servicio desplegado. No se invocan altas/validaciones/estado de COREDB como efectos colaterales de una solicitud. RF008 mantiene su borde de identidad separado y rechazo REAL por falta de contrato; una referencia CAP no se transforma en fiador institucional verificado.

## Pruebas realizadas

Entorno temporal P01 existente, Python 3.13.5, worker 0, sin URL MySQL heredada. Ejecución autorizada fuera del sandbox por limitación conocida de TestClient; ninguna descarga/reinstalación en E03.

```bash
env -u SOL_TEST_DATABASE_URL PYTHONDONTWRITEBYTECODE=1 SOL_INTEGRATION_MODE=SIMULADO SOL_WORKER_SECONDS=0 timeout 90s /tmp/bna-sol-p01-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -o addopts= backend/SOL/tests/test_integration_v2.py -k e03
```

| Ejecución | Resultado real |
| --- | --- |
| Reproducción antes de corrección | Salida 1: 8 failed, 17 passed, 24 deselected, 2 warnings, 0,81 s |
| Focalizada tras corregir/ampliar casos | Salida 0: **35 passed**, 24 deselected, 2 warnings, 1,09 s |
| Regresión con `backend/SOL/tests` en vez del archivo/selector anteriores | Salida 0: **107 passed**, 2 warnings, 19,28 s; incluye las 72 previas |

Casos E03: campos malformados (seis), HTTP 401/403/404/422/503/302 (seis), timeouts/conexión (tres), JSON incompatible (cuatro), listas inválidas (tres), éxito con retry/headers/query/PII, adapter interno ausente, revalidación antes de enviar, campos autoritativos ausentes (cuatro), identidad/estado/vigencia (cuatro), opcionales omitidos y consultas repetidas con refresco mínimo sin duplicar referencia ni alterar snapshot de versión.

La prueba de cambio de habilitación confirma una sola consulta de búsqueda, una de referencia al crear y otra al enviar; tras OBSERVADO rechaza y no crea Delivery. La prueba de refresco usa dos lecturas HTTP, una sola referencia local y expediente histórico inalterado. No se cachea la autorización para omitir la segunda comprobación. Las dos advertencias heredadas siguen siendo AnyIO/Starlette y opción pytest-asyncio sin plugin.

Se completa `git diff --check`, AST y revisión documental al cierre. No se ejecutaron pruebas COREDB reales, MySQL, frontend, Docker/smoke global, TCP ni disponibilidad de CAP. No se reinterpreta el pase MockTransport como integración institucional.

## Pendientes y continuidad

| Entregable de Captación/propietarios | Situación |
| --- | --- |
| API/URL Testing de búsqueda y referencia completas | Pendiente; las rutas ejemplo son del simulador |
| Caso/verificación/vigencia/estados y su semántica | Pendiente de contrato y fuente autoritativa, sin valores fabricados |
| Versiones y correspondencia de IDs con COREDB | Pendiente de acuerdo; formatos reales distintos |
| Credenciales/roles/TLS/restricción de origen | Pendiente; no basta un token Bus o un estado ACTIVO |
| Prueba real entre equipos con revocación y errores | No ejecutada; requisito para integrado_real |

Se puede continuar **E04 — Evaluación** para fortalecer su borde local sin declarar integración real. No se ejecutó E04 en esta tarea. RF001 permanece preparado_para_integracion; COREDB se reutiliza solo como referencia técnica de una posible composición aprobada, no como proveedor CAP ya conectado.
