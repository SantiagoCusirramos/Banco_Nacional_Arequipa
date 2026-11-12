# Seguimiento de hallazgos — CORE (Informe de Errores BNA)

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Actualizado:** 2026-11-01 (Ronda 3)
**Estado revisado:** 2026-11-11, sin ronda nueva: solo los cambios de estado de la sección 5
**Fuente de los hallazgos:** `Informe_Errores_BNA.pdf` y `TAREAS_POR_INTEGRANTE.md`
**Evidencia:** `Documents/04-reporte-pruebas.md`, `05-checklist-validacion.md` y `06-revision-arquitectura-schemas.md`

Leyenda: ✅ corregido y validado · 🟡 parcial · ❌ sin corregir

## 1. Hallazgos del informe

| # | Severidad | Hallazgo | Responsable | Estado | Evidencia | Pendiente |
|---|---|---|---|---|---|---|
| 1 | Crítica | Sin autenticación JWT | Nicolas Ayerve | ✅ (desde el PR #46) | `POST /core/auth/login`, `GET /core/auth/me`, `test_auth_jwt.py`, `test_rutas_protegidas.py` | — En la Ronda 3: 6 routers sin token (`clientes`, `cuentas`, `movimientos`, `tarjetas`, `creditos`, `catalogos`) |
| 2 | Crítica | `backend/.env` con secretos trackeado en Git | Sebastian Castro | ✅ | El árbol de `main` ya no incluye `backend/.env`; `test_configuracion.py` | Rotar claves y limpiar el historial público (decide Santiago); documentar la rotación |
| 3 | Alta | Contraseñas con SHA256 | Nino Flores | ✅ | `utils/hashing.py` (bcrypt y migración en el primer login); `test_hashing.py` | Prueba contra MySQL real (`BNA_INTEGRACION_MYSQL=1`) |
| 4 | Alta | TEA redondeada a 2 decimales | Leonardo Lonasco | ✅ | `test_calendario_correcciones.py` | — |
| 5 | Media | Calendario sin validar entradas | Leonardo Lonasco | ✅ | `test_calendario_correcciones.py` | — |
| 6 | Media | Vencimientos a 30 días | Leonardo Lonasco | ✅ | `test_calendario_correcciones.py` | — |
| 7 | Media | `montar_en()` no idempotente | Mathias Ostolaza | ✅ | `TestApi::test_montar_en_es_idempotente` | — |
| 8 | Media | `asignar_accion()` acepta roles inventados; escritura no atómica | Mathias Ostolaza | ❌ | `rbac.py` sin cambios | Validar roles, escritura atómica y bloqueo |
| 9 | Baja | `verify_sha256` falla con hash `None` | Nino Flores | ✅ | `test_verificar_con_hash_nulo_no_debe_explotar` | — |
| 10 | Alta | Deadlock en transferencias cruzadas | Renzo Montoya | ✅ | `TestOrdenBloqueo`, `TestReintentosDeadlock` (con fakes) | Prueba con MySQL real y dos conexiones |
| 11 | Alta | Idempotencia sin validar el cuerpo | Renzo Montoya | ✅ | `TestIdempotencia` (con fakes) | Prueba con MySQL real; avisar del cambio de contrato (`idempotency_key` máx. 62) |
| 12 | Media | Tope diario: validación y acumulación inconsistentes | Marcelo Moscoso | ❌ | `movimientos.py` y `contabilidad.py` sin cambios | Definir la regla RGN-04 y corregir |
| 13 | Baja | Login devuelve 404 en vez de 401 | Nicolas Ayerve | ✅ | `test_login_*_responden_igual` | — |
| 14 | Baja | Los tests modifican `rbac.json` real | Mathias Ostolaza | ❌ | `test_asignar_y_revocar` | Usar archivo temporal en los tests |

**Resumen:** 11 corregidos y 3 sin corregir (#8, #12, #14). En la Ronda 3 eran 10 corregidos y 1 parcial (#1).

## 2. Hallazgos propios de la validación

| Código | Hallazgo | Responsable sugerido | Estado |
|---|---|---|---|
| H1 | El `actor` de la auditoría llega por el cuerpo de la petición | Nicolas Ayerve | ✅ Desde el PR #46 sale del token en todos los routers; el `actor` del cuerpo se acepta y se ignora. En la Ronda 3: resuelto solo en `usuarios`, `permisos`, `auditoria` y `reportes` |
| S1 | `comision`, `itf` y `retencion` aceptan valores negativos | Renzo Montoya / Marcelo Moscoso | ❌ |
| S2 | `moneda` es texto libre (sin lista cerrada PEN/USD) | Mathias Ostolaza | ❌ |
| S3 | Identificadores sin validación de formato | Mathias Ostolaza | ❌ |
| S7 | Transferencia con origen igual a destino | Renzo Montoya | ✅ El servicio la rechaza (falta un test) |
| H2 | `BUS_BASE_URL` definida y sin uso | Sebastian Castro | ❌ |
| H3 | El router `catalogos` consulta la BD con `select()` y sin token | Autor de `catalogos` | 🟡 Desde el PR #46 exige un token vigente. Sigue consultando la BD con `select()` en el router. En la Ronda 3: ❌ |
| H4 | `test_configuracion.py` de CORE importa `CUENTAS.config` | Autor del test | ⚠️ |

## 3. Decisiones pendientes del Comité de Créditos (Leonardo Lonasco)

Documentadas en `backend/CORE/CREDITOS_MOTOR_Y_FLUJO.md`; no son errores corregibles sin una decisión de negocio.

| Código | Tema | Estado |
|---|---|---|
| H-A1 | Las reglas APROBAR restan puntaje | Abierto (test `xfail`) |
| H-A2 | Frontera 0.80 duplicada entre dos reglas | Abierto (test `xfail`) |
| H-A3 | Solicitante sin ingresos queda APROBADO | Abierto (test `xfail`) |
| H-A4 | `float` e `int` en la ponderación del puntaje | Abierto |
| H-B1 | Se puede aprobar una evaluación RECHAZADA | Abierto (test `xfail`) |
| H-B2 | Aprobación sin aprobador identificado | Resuelto en parte (PR #46): `/core/creditos` exige token y permiso, y `id_analista` es el empleado del usuario que decide. Abierto: si aprobar exige un usuario con empleado (`CREDITOS_MOTOR_Y_FLUJO.md` §4.2) |
| H-B3 | El monto aprobado no tiene tope | Abierto (test `xfail`) |
| H-B4 | No existe workflow de aprobación por monto | Abierto |
| EXCLUYE | Se comporta igual que ENTRE | Abierto |
| Desembolso | Aprobar no genera `cob_credito` ni asiento | Abierto |

## 4. Historial de rondas

| Ronda | Fecha | Alcance | Resultado |
|---|---|---|---|
| 0 | 2026-10-23 | Línea base | 24 pasan |
| 1 | 2026-10-30 | `main` + fixes de Renzo (#10, #11) | 43 pasan |
| 2 | 2026-10-30 | `main` + patch de Leonardo (#4, #5, #6) | 136 pasan, 5 xfailed |
| 3 | 2026-11-01 | `main` con auth, bcrypt, `.env`, `montar_en()` y créditos | 251 pasan, 26 saltados, 5 xfailed (1 test desactualizado corregido: `montar_en()` = 37 rutas) |

## 5. Cambios de estado posteriores a la Ronda 3

No hubo una ronda de validación nueva. Esta sección solo registra qué hallazgos cambiaron de estado en `main` y con qué PR; las tablas de arriba ya muestran el estado actual.

| Fecha | Hallazgo | Antes | Ahora | PR | Evidencia |
|---|---|---|---|---|---|
| 2026-11-11 | #1 Sin autenticación JWT | 🟡 6 routers sin token | ✅ Las 22 rutas de `clientes`, `cuentas`, `movimientos`, `tarjetas`, `creditos` y `catalogos` exigen token; salvo los catálogos, también el permiso de su acción en `rbac.json`. Solo `POST /core/auth/login` queda abierta | #46 | `test_rutas_protegidas.py` (80 pruebas; falla si una ruta de `/core` distinta del login queda sin token), `AUTH_JWT.md` |
| 2026-11-11 | H1 `actor` por el cuerpo | 🟡 Resuelto en 4 routers | ✅ El actor sale del token en todos | #46 | `test_rutas_protegidas.py` |
| 2026-11-11 | H3 `catalogos` con `select()` y sin token | ❌ | 🟡 Con token; el `select()` sigue en el router | #46 | `routers/catalogos.py` |
| 2026-11-11 | H-B2 Aprobación sin aprobador identificado | Abierto | Resuelto en parte: el analista es el empleado del usuario del token | #46 | `CREDITOS_MOTOR_Y_FLUJO.md` §4.2 |

Sin cambios en el código de `main` desde la Ronda 3: #8, #12, #14, S1, S2, S3, S7 (sigue sin test), H2 y H4. Lo que figura como pendiente en #2, #3, #10 y #11 no se revisó aquí.

Contexto: desde el PR #42 ningún servicio del producto llama a este CORE. CUENTAS y el frontend usan COREDB, la API sobre la base integrada, y el CORE legado solo se levanta con `COMPOSE_PROFILES=legado ./bna up`. Los hallazgos de este documento siguen siendo de `backend/CORE`.
