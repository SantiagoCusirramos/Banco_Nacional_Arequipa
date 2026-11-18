# SOL: Solicitud de Crédito

El asesor arma el expediente de crédito de un cliente (condiciones, garantías, fiadores y calendario preliminar) y lo envía a Evaluación. **SOL no tiene base propia**: el borrador, su historial y la bitácora están en la base integrada, y SOL llega a ellos solo por COREDB, a través del Bus de Servicios.

| Con quién | Para qué | Cómo |
|---|---|---|
| COREDB | Login de las personas, borrador (`/coredb/creditos/borradores`), bandeja, detalle y bitácora (`/coredb/auditoria/eventos`) | Por el Bus. Lo que hace una persona va con su token de COREDB; lo de SOL, con `svc-sol` |
| CAPTACION (CR-INT-01) | Referencias de clientes y fiadores: identidad y habilitación vigente | Por el Bus, con `SOL_CAP_TOKEN` (el `CAP_SOL_TOKEN` de CAPTACION) |
| EVALUACION (CR-INT-02) | Recibe el expediente de una versión y lo registra en COREDB | Por el Bus, con `SOL_EVA_TOKEN` (el `EVALUACION_TOKEN_SOL`) |
| EVALUACION (CR-INT-03) | Devuelve el resultado final a `POST /sol/integrations/evaluation-results` | Por el Bus, con `SOL_EVA_CALLBACK_TOKEN` (el `EVALUACION_SOL_TOKEN_RESULTADOS`) |

Contratos de COREDB: [`backend/COREDB/CONTRATO_CREDITOS.md`](../COREDB/CONTRATO_CREDITOS.md) §3.1 (expediente) y §8 (borrador y eventos). Base: `bd-v1.14-mysql`, sección 19 (`creditos.guardar_borrador`, `core.recibir_evento_modulo`).

## Cómo entrar

Con el usuario del banco en COREDB, por la pantalla http://localhost:3000/solicitud-credito o por `POST /sol/auth/login`. El rol de COREDB decide el perfil de SOL:

| Rol en COREDB | Perfil en SOL | Puede |
|---|---|---|
| ASESOR | ASESOR | Buscar clientes, calcular, guardar y editar borradores, enviar a Evaluación |
| ADMINISTRADOR | SUPERVISOR | Consultar y ver las métricas |
| AUDITOR | AUDITOR | Consultar y ver las métricas |
| Otros, y los usuarios de servicio | — | No entran (403) |

El login es el de COREDB, con su bloqueo tras fallos seguidos. Un usuario ASESOR lo crea el administrador con `POST /coredb/usuarios`.

## Flujo

1. **Borrador.** SOL valida las condiciones contra su política (`config/politica_demo.json`), comprueba en CAPTACION que el cliente y cada fiador estén ACTIVOS, HABILITADOS y con la verificación vigente, calcula el calendario y guarda el borrador en COREDB con el token del asesor: una solicitud `REGISTRADA` con sus garantías y fiadores.
2. **Edición.** Exige la revisión vigente: si otra sesión lo cambió, 409. El cliente no se cambia.
3. **Envío (CR-INT-02).** Con `X-Idempotency-Key`, la revisión vigente, la política sin cambios y una fecha base que no pasó. El `idOperacion` es uno por versión, así que reenviar manda el mismo sobre y COREDB no lo duplica. Si Evaluación no responde, 202 `pendiente_envio`: se reintenta. Confirmado, la solicitud queda `EN_EVALUACION` y el envío queda en la bitácora (`ENVIAR_CR_INT_02`) a nombre del asesor.
4. **Resultado (CR-INT-03).** Evaluación lo entrega cada 10 s. SOL no lo guarda: lo contrasta con COREDB (evaluación, ronda, decisión y estado) y lo deja en la bitácora (`RECIBIR_CR_INT_03`), una vez por `idOperacion`. Sin bitácora, responde 503 y Evaluación reintenta.

## Qué cambió (sin base propia, noviembre de 2026)

SOL era un laboratorio con su propia base (`bna_sol_mvp` en `db-aux`) y un modo SIMULADO. Nadie lo llamaba salvo el frontend, que se adaptó en el mismo cambio.

| Antes | Ahora |
|---|---|
| Base propia `bna_sol_mvp` (tablas `mvp_sol_*`), `python -m SOL.manage init/migrate/...` y el servicio `sol-init` | Sin base: el borrador, el historial y la bitácora están en COREDB. `manage.py`, `models.py`, `database.py`, `migrations.py`, `seed.py` y `operations.py` ya no existen |
| Modo `SIMULADO` (Captación y Evaluación de mentira, `/gateway/sol`, `simulator.py`) o `REAL` | Solo REAL: CAPTACION y EVALUACION reales por el Bus. La ruta es `/sol/...` (el frontend usa `http://bus:8018/bus/sol/sol`) |
| Cuatro cuentas propias (`asesor.bna`, `supervisor.bna`, `auditor.bna`, `evaluador.demo`) con `SOL_INITIAL_PASSWORD`, sesiones y bloqueo propios | El login es el de COREDB; el rol de COREDB da el perfil (tabla de arriba). `/auth/logout` no revoca el token (COREDB aún no revoca sesiones): el frontend borra su cookie |
| `POST /sol/admin/users/{u}/disable` | Se quitó: los usuarios se administran en COREDB |
| `POST /sol/applications/{id}/demo-result` (consola EVA simulada) | Se quitó: el resultado lo da Evaluación |
| `POST /sol/applications/{id}/revise` (subsanar una solicitud OBSERVADA) | Se quitó: por la decisión T1 del equipo el analista decide APROBADO o RECHAZADO y nada vuelve OBSERVADO a SOL |
| `GET /sol/ops/pending` y las colas de envíos y auditoría con su trabajador | Se quitaron: el envío es directo (202 si Evaluación no responde) y los eventos van a la bitácora de COREDB en el momento |
| Estado `BORRADOR` | `REGISTRADA` (el estado del catálogo de la base) |
| Tipos de garantía PERSONAL, HIPOTECARIA, VEHICULAR, MOBILIARIA, FONDOS | Los del catálogo de la base: HIPOTECARIA, MOBILIARIA, PRENDARIA |
| Fiadores de la referencia simulada (en REAL, rechazados) | Clientes del CORE con referencia vigente en CAPTACION; uno respalda una sola solicitud (`uk_fiador_solicitud_1`) |
| Varias versiones por solicitud (subsanación) | Una versión; `versiones` trae solo la vigente |
| `correlacion` de cada evento del historial | Vacía: el historial viene de COREDB, que no la expone ahí (la bitácora sí la guarda) |
| `GET /ready` → `{"status", "base"}` | `{"status", "coredb"}` |
| Variables `SOL_DB_*`, `SOL_INTEGRATION_MODE`, `SOL_*_BASE_URL`, `SOL_*_PATH`, `SOL_AUDIT_*` | `SOL_BUS_URL`, `SOL_BUS_TOKEN`, `SOL_COREDB_USUARIO`, `SOL_COREDB_SECRETO`, `SOL_CAP_TOKEN`, `SOL_EVA_TOKEN`, `SOL_EVA_CALLBACK_TOKEN` |

Las demás respuestas conservan su forma (`DetailResponse`, `SummaryResponse`, `SnapshotResponse`, CR-INT-03).

## Preguntas abiertas para el equipo

- Tipos de garantía: SOL ofrecía además PERSONAL, VEHICULAR y FONDOS, que el catálogo de la base no tiene.
- Fiadores: con la verificación de Captación, el modelo deja que un cliente respalde una sola solicitud.
- Que COREDB revoque sesiones al cerrar (hoy el token vence solo).

## Configuración

| Variable | Qué es |
|---|---|
| `SOL_BUS_URL` | El Bus, p. ej. `http://bus:8018/bus` |
| `SOL_BUS_TOKEN` | Credencial de SOL ante el Bus (`BUS_TOKEN_SOL`) |
| `SOL_COREDB_USUARIO`, `SOL_COREDB_SECRETO` | Usuario de servicio de SOL en COREDB (`svc-sol`, módulo `SOLICITUD DE CREDITO`; lo crea `coredb-init`) |
| `SOL_CAP_TOKEN`, `SOL_EVA_TOKEN`, `SOL_EVA_CALLBACK_TOKEN` | Tokens de CR-INT-01, CR-INT-02 y CR-INT-03 |
| `SOL_POLICY_FILE` | La política (por omisión `config/politica_demo.json`) |
| `SOL_HTTP_TIMEOUT_SECONDS`, `SOL_HTTP_MAX_RETRIES` | 3 s y 1 reintento en las consultas |

Los tokens tienen al menos 32 caracteres y son distintos entre sí.

## Pruebas

`./bna test` corre `SOL/tests` (un Bus falso en memoria con COREDB, CAPTACION y EVALUACION), el contrato CR-INT-01 con CAPTACION real, CR-INT-02 con Evaluación real y el flujo de extremo a extremo, que recorre login, borrador, edición, envío, evaluación y el resultado en la bitácora por el proxy del frontend.
