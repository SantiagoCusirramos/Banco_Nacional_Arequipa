# Seguimiento de hallazgos — CORE (Informe de Errores BNA)

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Actualizado:** 2026-11-01 (Ronda 3)
**Fuente de los hallazgos:** `Informe_Errores_BNA.pdf` y `TAREAS_POR_INTEGRANTE.md`
**Evidencia:** `Documents/04-reporte-pruebas.md`, `05-checklist-validacion.md` y `06-revision-arquitectura-schemas.md`

Leyenda: ✅ corregido y validado · 🟡 parcial · ❌ sin corregir

## 1. Hallazgos del informe

| # | Severidad | Hallazgo | Responsable | Estado | Evidencia | Pendiente |
|---|---|---|---|---|---|---|
| 1 | Crítica | Sin autenticación JWT | Nicolas Ayerve | 🟡 | `POST /core/auth/login`, `GET /core/auth/me`, `test_auth_jwt.py` | 6 routers sin token (`clientes`, `cuentas`, `movimientos`, `tarjetas`, `creditos`, `catalogos`) |
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

**Resumen:** 10 corregidos, 1 parcial (#1) y 3 sin corregir (#8, #12, #14).

## 2. Hallazgos propios de la validación

| Código | Hallazgo | Responsable sugerido | Estado |
|---|---|---|---|
| H1 | El `actor` de la auditoría llega por el cuerpo de la petición | Nicolas Ayerve | 🟡 Resuelto solo en `usuarios`, `permisos`, `auditoria` y `reportes` |
| S1 | `comision`, `itf` y `retencion` aceptan valores negativos | Renzo Montoya / Marcelo Moscoso | ❌ |
| S2 | `moneda` es texto libre (sin lista cerrada PEN/USD) | Mathias Ostolaza | ❌ |
| S3 | Identificadores sin validación de formato | Mathias Ostolaza | ❌ |
| S7 | Transferencia con origen igual a destino: sin verificar en el servicio | Renzo Montoya | ⏳ |
| H2 | `BUS_BASE_URL` definida y sin uso | Sebastian Castro | ❌ |

## 3. Decisiones pendientes del Comité de Créditos (Leonardo Lonasco)

Documentadas en `backend/CORE/CREDITOS_MOTOR_Y_FLUJO.md`; no son errores corregibles sin una decisión de negocio.

| Código | Tema | Estado |
|---|---|---|
| H-A1 | Las reglas APROBAR restan puntaje | Abierto (test `xfail`) |
| H-A2 | Frontera 0.80 duplicada entre dos reglas | Abierto (test `xfail`) |
| H-A3 | Solicitante sin ingresos queda APROBADO | Abierto (test `xfail`) |
| H-A4 | `float` e `int` en la ponderación del puntaje | Abierto |
| H-B1 | Se puede aprobar una evaluación RECHAZADA | Abierto (test `xfail`) |
| H-B2 | Aprobación sin aprobador identificado | Abierto: depende del JWT en `/core/creditos` |
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
| 3 | 2026-11-01 | `main` con auth, bcrypt, `.env`, `montar_en()` y créditos | XX pasan, XX saltados |
