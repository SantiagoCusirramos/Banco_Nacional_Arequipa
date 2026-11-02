# Reporte de pruebas — CORE (Banco Nacional de Arequipa)

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Alcance:** `backend/CORE/tests/`
**Comando:** `cd backend && python -m pytest`

---

## 1. Línea base (antes de los fixes del equipo)

| Dato | Valor |
|---|---|
| Fecha de ejecución | 2026-10-23 |
| Rama / commit base | `main` @ `1ef490f` (obtener con `git rev-parse --short HEAD`) |
| Versión de Python | 3.12.2 |
| Versión de pytest | 8.3.3 (pytest-asyncio 0.24.0) |
| Total de tests | 24 |
| Pasan | 24 |
| Fallan | 0 |
| Errores | 0 |
| Warnings | 1 (`DeprecationWarning` de `anyio.abc.BlockingPortal` en starlette) + aviso de pytest-asyncio por `asyncio_default_fixture_loop_scope` sin definir |
| Archivo de salida completa | `Documents/reporte_pruebas_base.txt` |

## 2. Matriz de pruebas existentes

| Archivo | Test | Base | Tras fixes | Observación |
|---|---|---|---|---|
| `test_api_smoke.py` | `test_rutas_core_montadas` | ✅ | | |
| `test_api_smoke.py` | `test_error_core_devuelve_json_catalogado` | ✅ | | |
| `test_creditos_logica.py` | `test_tasa_mensual_desde_tea` | ✅ | | No cubre TEA fraccionaria (Hallazgo #4) |
| `test_creditos_logica.py` | `test_calendario_frances_cuadra` | ✅ | | No valida entradas inválidas (#5) ni meses calendario (#6) |
| `test_creditos_logica.py` | `test_calendario_tasa_cero` | ✅ | | |
| `test_excepciones.py` | `test_core_error_codes` | ✅ | | |
| `test_excepciones.py` | `test_not_found_es_404` | ✅ | | |
| `test_excepciones.py` | `test_saldo_insuficiente` | ✅ | | |
| `test_excepciones.py` | `test_cuenta_bloqueada` | ✅ | | |
| `test_motor_reglas.py` | `test_mayor` | ✅ | | |
| `test_motor_reglas.py` | `test_entre` | ✅ | | |
| `test_motor_reglas.py` | `test_excluye` | ✅ | | Semántica de EXCLUYE a revisar (Leonardo) |
| `test_motor_reglas.py` | `test_regla_inactiva_no_aplica` | ✅ | | |
| `test_motor_reglas.py` | `test_variable_ausente` | ✅ | | |
| `test_motor_reglas.py` | `test_riesgo_desde_puntaje` | ✅ | | |
| `test_rbac.py` | `test_catalogo_completo` | ✅ | | |
| `test_rbac.py` | `test_admin_tiene_todo` | ✅ | | |
| `test_rbac.py` | `test_rol_puede` | ✅ | | |
| `test_rbac.py` | `test_asignar_y_revocar` | ✅ | | Modifica el `rbac.json` real (Hallazgo #14) |
| `test_utilidades.py` | `test_hash_sha256_es_hex_de_64` | ✅ | | |
| `test_utilidades.py` | `test_verify_sha256` | ✅ | | No cubre hash `None` (#9) |
| `test_utilidades.py` | `test_uuid7_version` | ✅ | | |
| `test_utilidades.py` | `test_convertir_aplica_tasa` | ✅ | | |
| `test_utilidades.py` | `test_d_normaliza` | ✅ | | |
| `test_movimientos_concurrencia.py` | `TestOrdenBloqueo::test_bloquea_en_orden_ascendente_sin_importar_origen` | ✅ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestOrdenBloqueo::test_orden_antiguo_produce_espera_circular` | ✅ | | Hallazgo #10 · demuestra el bug anterior con candados simulados (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestOrdenBloqueo::test_orden_nuevo_no_produce_espera_circular` | ✅ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_detecta_deadlock_mysql` | ✅ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_reintenta_y_luego_confirma` | ✅ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_agota_reintentos_y_responde_503` | ✅ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_error_que_no_es_deadlock_no_se_reintenta` | ✅ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_transferir_reintenta_ante_deadlock` | ✅ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_replay_transferencia_no_intercambia_patas` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_misma_llave_otro_monto_da_409` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_misma_llave_otro_destino_da_409` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_llave_de_deposito_no_sirve_para_transferencia` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_llave_de_transferencia_no_sirve_para_deposito` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_deposito_vs_retiro_misma_llave_da_409` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_replay_deposito_identico` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_usa_hash_guardado_en_auditoria` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_sufijo_reservado_rechazado` | ✅ | | Hallazgo #11 · sufijo `#C` reservado (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_llave_transferencia_demasiado_larga` | ✅ | | Hallazgo #11 · `idempotency_key` máx. 62 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_huella_normaliza_monto` | ✅ | | Hallazgo #11 (nuevo, Renzo Montoya) |

**Resumen línea base:** 24 tests, 24 ✅, 0 ❌.

**Resumen Ronda 1:** 43 tests (24 existentes + 19 nuevos de `test_movimientos_concurrencia.py`). Resultado: 43 ✅, 0 ❌ (`43 passed, 1 warning in 3.30s`).

> Los 24 tests existentes pasan en la línea base. Esto no significa que el código esté correcto: los hallazgos #1 al #14 del informe no están cubiertos por ningún test actual. Los tests que los detectan (`TestHashing`, `TestCalendario`, `TestApi`, `TestRbac::test_asignar_acepta_rol_inventado`) viven en `test_revision_bna.py` y están pendientes de recibirse.

### 2b. Tests nuevos de la Ronda 2 — fixes de Leonardo Lonasco (rama `validar/leonardo-creditos`)

Estos tests **no están en `main`**: vienen del patch `leonardo-creditos-tea-calendario.patch` aplicado sobre `main` solo para validar. Los tests con `xfail(strict=True)` describen hallazgos que **no están corregidos** y requieren decisión del Comité de Créditos; fallan a propósito y pytest los reporta como `xfailed`, no como error.

| Archivo | Test | Resultado | Observación |
|---|---|---|---|
| `test_calendario_correcciones.py` | `TestCalendario::test_tea_no_se_redondea_a_2_decimales` | ✅ | Hallazgo #4 |
| `test_calendario_correcciones.py` | `TestCalendario::test_tea_con_mas_de_dos_decimales_se_respeta` | ✅ | Hallazgo #4 · parametrizado (5 TEA) |
| `test_calendario_correcciones.py` | `TestCalendario::test_cuota_hipotecario_tea_10_50` | ✅ | Hallazgo #4 · cuota S/ 1 933.51 (con el error salía S/ 1 994.28) |
| `test_calendario_correcciones.py` | `TestCalendario::test_tea_en_porcentaje_es_rechazada` | ✅ | Hallazgo #4 · `TEA_FUERA_DE_RANGO` |
| `test_calendario_correcciones.py` | `TestCalendario::test_tea_invalida_es_rechazada` | ✅ | Hallazgo #4 · parametrizado (4 casos) |
| `test_calendario_correcciones.py` | `TestCalendario::test_cuotas_cero_valida_entrada` | ✅ | Hallazgo #5 · parametrizado (2) |
| `test_calendario_correcciones.py` | `TestCalendario::test_cuotas_negativas_rechazadas` | ✅ | Hallazgo #5 |
| `test_calendario_correcciones.py` | `TestCalendario::test_monto_negativo_rechazado` | ✅ | Hallazgo #5 · parametrizado (3) |
| `test_calendario_correcciones.py` | `TestCalendario::test_numero_cuotas_no_entero_rechazado` | ✅ | Hallazgo #5 |
| `test_calendario_correcciones.py` | `TestCalendario::test_vencimientos_mensuales_calendario` | ✅ | Hallazgo #6 · 31-ene → 28-feb, 31-mar… |
| `test_calendario_correcciones.py` | `TestCalendario::test_vencimientos_anio_bisiesto` | ✅ | Hallazgo #6 |
| `test_calendario_correcciones.py` | `TestCalendario::test_ningun_mes_se_salta` | ✅ | Hallazgo #6 · 60 cuotas |
| `test_calendario_correcciones.py` | `TestCalendario::test_dia_de_pago_se_conserva` | ✅ | Hallazgo #6 |
| `test_calendario_correcciones.py` | `TestCalendario::test_calendario_cuadra` | ✅ | Hallazgo #4/#5/#6 · parametrizado (6) |
| `test_creditos_motor_flujo.py` | `test_excluye_se_comporta_igual_que_entre` | ✅ | Act. 2 · parametrizado (60 combinaciones): EXCLUYE = ENTRE |
| `test_creditos_motor_flujo.py` | `test_fronteras_de_los_operadores` | ✅ | Act. 2 |
| `test_creditos_motor_flujo.py` | `test_crear_solicitud_genera_calendario_simulado_con_meses_calendario` | ✅ | #6 |
| `test_creditos_motor_flujo.py` | `test_aprobar_no_genera_credito_ni_desembolso_hueco_conocido` | ✅ | Act. 2 · fija el hueco conocido del desembolso |
| `test_creditos_motor_flujo.py` | `test_estado_tras_evaluar_es_en_evaluacion_aunque_el_resultado_sea_rechazado` | ✅ | Act. 2 |
| `test_creditos_motor_flujo.py` | `test_solicitante_sano_no_pierde_puntos_por_cumplir_la_regla_saludable` | xfailed (esperado) | H-A1 · falla a propósito: pendiente de decisión del Comité |
| `test_creditos_motor_flujo.py` | `test_ratio_exacto_en_la_frontera_activa_una_sola_regla` | xfailed (esperado) | H-A2 · falla a propósito: pendiente de decisión del Comité |
| `test_creditos_motor_flujo.py` | `test_solicitante_sin_ingresos_no_es_aprobado` | xfailed (esperado) | H-A3 · falla a propósito: pendiente de decisión del Comité |
| `test_creditos_motor_flujo.py` | `test_no_se_puede_aprobar_una_evaluacion_rechazada` | xfailed (esperado) | H-B1 · falla a propósito: pendiente de decisión del Comité |
| `test_creditos_motor_flujo.py` | `test_no_se_aprueba_mas_de_lo_solicitado` | xfailed (esperado) | H-B3 · falla a propósito: pendiente de decisión del Comité |

**Resumen Ronda 2:** 136 pasan, 5 xfailed (esperado), 0 fallan (`136 passed, 5 xfailed, 1 warning in 3.62s`). Los 136 incluyen los 43 de la Ronda 1 más 93 casos nuevos de Leonardo (varios tests están parametrizados).

#### Hallazgos nuevos documentados por Leonardo (no corregidos)

| Código | Hallazgo | Estado |
|---|---|---|
| H-A1 | Las reglas con resultado APROBAR restan puntaje: el riesgo BAJO es inalcanzable | Abierto — decisión del Comité |
| H-A2 | Ratio exacto 0.80 activa dos reglas (RATIO_SALUDABLE y RATIO_LIMITE) | Abierto — propuesta: sembrar RATIO_LIMITE desde 0.8001 |
| H-A3 | Solicitante sin ingresos tiene ratio 0 y queda APROBADO | Abierto — propuesta: `INGRESOS_INVALIDOS` |
| H-A4 | `float`/`int` y truncamiento en la ponderación | Abierto |
| H-B1 | Se puede aprobar una evaluación RECHAZADA | Abierto |
| H-B2 | Aprobación sin aprobador identificado (`id_analista` opcional) | Abierto — depende del JWT (Nicolas) |
| H-B3 | El monto aprobado no tiene tope | Abierto |
| H-B4 | No existe workflow de aprobación por monto | Abierto — define el Comité |
| EXCLUYE | Se comporta igual que ENTRE (dispara dentro de la banda) | Abierto — eliminarlo o redefinirlo |
| Desembolso | Aprobar no genera `cob_credito` ni asiento (hueco conocido, README punto 2) | Abierto — definir dónde vive el desembolso |

### 2c. Tests nuevos de la Ronda 3 (ya integrados en `main`)

| Archivo | Tests (definiciones) | Hallazgo | Qué cubre | Resultado |
|---|---|---|---|---|
| `test_auth_jwt.py` | 25 | #1, #13, H1 parcial | Claims del token, token expirado, firma ajena, `alg=none`, login OK y 401 genérico (usuario inexistente, inactivo, clave incorrecta), `/me`, permisos por rol, usuario desactivado pierde acceso, el actor sale del token en las rutas de administración | ✅ |
| `test_hashing.py` | 22 | #3, #9 | Hash con sal, bcrypt para usuarios nuevos, migración SHA256 → bcrypt, hash `None` o corrupto, límite de 72 bytes, surrogates | ✅ |
| `test_autenticar.py` | 10 | #3, #13 | `autenticar()` devuelve el contrato; inexistente y clave incorrecta responden igual; inactivo no revela su estado; gasta una verificación para no filtrar por tiempo | ✅ |
| `test_configuracion.py` | 8 | #2 | Error legible sin `SECRET_KEY`, clave débil o valor de ejemplo rechazados, `.env.example` usa `DB_NAME=bna` | ✅ |
| `test_validacion_sin_eco.py` | 5 | Seguridad | Los errores 422 no devuelven el valor recibido (por ejemplo, la contraseña) | ✅ |
| `test_api_smoke.py` | (incluye `TestApi::test_montar_en_es_idempotente`) | #7 | `montar_en()` idempotente, rutas montadas | ✅ |
| `tests/integracion/test_real_mysql.py` | — | #3 | Hashing y autenticación contra MySQL real. **Solo corre con `BNA_INTEGRACION_MYSQL=1`**; sin eso aparece como *skipped* | ⏭️ Saltado (requiere BD) |

> Antes de subir: si en tu corrida algún archivo falla, cambia ✅ por ❌ en su fila y anótalo en la sección 4.

### Hallazgos propios detectados durante la corrida

| Hallazgo | Evidencia |
|---|---|
| Los tests modifican `backend/CORE/data/rbac.json` (archivo real) | `git status` lo muestra como modificado tras correr la suite (Hallazgo #14) |
| `backend/.env` está trackeado en Git | `git status` lo muestra como modificado (Hallazgo #2) |
| La suite no corre sin instalar `requirements.txt` | 4 de 6 archivos fallan en collection con `ModuleNotFoundError` (`fastapi`, `pydantic_settings`) |

## 3. Tests de los hallazgos (esperados tras los fixes)

Estado: **`test_revision_bna.py` sigue sin recibirse**; los tests de cada hallazgo son los que cada integrante incluyó en su rama. Estado actualizado en la Ronda 3 (2026-11-01).

| Hallazgo | Test esperado | Responsable | Rama | Base | Tras fix |
|---|---|---|---|---|---|
| #1 Auth JWT (crítica) | `test_auth_jwt.py` (25 tests): login 200 con token, 401 genérico, token expirado, `alg=none`, permisos por rol | Nicolas Ayerve | `main` | sin test previo | 🟡 ✅ login, `/me` y rutas de administración. ❌ 6 routers siguen sin token (`clientes`, `cuentas`, `movimientos`, `tarjetas`, `creditos`, `catalogos`) |
| #2 `.env` trackeado (crítica) | `git ls-files backend/.env` vacío; `test_configuracion.py` | Sebastian Castro | `main` | ❌ (confirmado) | ✅ (el árbol ya no incluye `backend/.env`; confirmar con `git ls-files`). Pendiente: rotar claves y limpiar el historial |
| #3 Hashing SHA256 | `test_hash_con_sal`, `test_usuario_nuevo_usa_bcrypt`, `test_sha256_migra_audita_y_confirma` | Nino Flores | `main` | sin test previo | ✅ |
| #9 `verify_sha256` con None | `test_verificar_con_hash_nulo_no_debe_explotar` | Nino Flores | `main` | sin test previo | ✅ |
| #4 TEA redondeada | `TestCalendario::test_tea_no_se_redondea_a_2_decimales` (+ 4 tests más) | Leonardo Lonasco | `main` | sin test previo | ✅ (Ronda 2 y 3; integrado en `main`) |
| #5 Validación de entrada | `test_cuotas_cero_valida_entrada`, `test_monto_negativo_rechazado`, `test_cuotas_negativas_rechazadas`, `test_numero_cuotas_no_entero_rechazado` | Leonardo Lonasco | `main` | sin test previo | ✅ (Ronda 2 y 3; integrado en `main`) |
| #6 Vencimientos | `test_vencimientos_mensuales_calendario`, `test_vencimientos_anio_bisiesto`, `test_ningun_mes_se_salta`, `test_dia_de_pago_se_conserva` | Leonardo Lonasco | `main` | sin test previo | ✅ (Ronda 2 y 3; integrado en `main`) |
| #7 `montar_en()` | `TestApi::test_montar_en_es_idempotente` (33 rutas, no 66) | Mathias Ostolaza | `main` | sin test previo | ✅ |
| #8 / #14 RBAC | `TestRbac::test_asignar_acepta_rol_inventado` | Mathias Ostolaza | — | ❌ (#14 confirmado) | ❌ Sin cambios: `rbac.py` no valida roles, no escribe de forma atómica y `test_rbac.py` sigue modificando `rbac.json` |
| #10 Deadlock transferencias | `TestOrdenBloqueo`, `TestReintentosDeadlock` (8 tests, con fakes) | Renzo Montoya | `main` | sin test previo | ✅ (Ronda 1, con fakes; falta prueba con MySQL real) |
| #11 Idempotencia | `TestIdempotencia` (11 tests, con fakes): key reutilizada con otros datos → 409 | Renzo Montoya | `main` | sin test previo | ✅ (Ronda 1, con fakes; falta prueba con MySQL real) |
| #12 Tope diario | (definir) | Marcelo Moscoso | — | ⏳ | ⏳ Sin cambios en `movimientos.py` ni `contabilidad.py` |
| #13 Login 404 vs 401 | `test_login_clave_incorrecta_y_usuario_inexistente_responden_igual`, `test_login_usuario_inactivo_responde_igual_que_clave_incorrecta` | Nicolas Ayerve | `main` | sin test previo | ✅ |

Leyenda: ✅ pasa · ❌ falla · ⏳ pendiente

## 4. Regresiones detectadas

| Fecha | Test | Rama que lo rompió | Responsable | Estado |
|---|---|---|---|---|
| | | | | |

Sin regresiones detectadas en las Rondas 1 y 2: los 24 tests de la línea base siguen pasando en ambas.

## 5. Rondas de validación

### Ronda 0 — Línea base, 2026-10-23
- Ramas integradas: `main`
- Resultado: 24 pasan / 0 fallan
- Notas: ver "Hallazgos propios detectados durante la corrida".

### Ronda 1 — 2026-10-30
- Ramas integradas: `main` (incluye fixes de Renzo Montoya: #10 y #11)
- Resultado: 43 pasan / 0 fallan (de 43 tests)
- Regresiones: ninguna (los 24 tests originales siguen pasando)
- Archivo de salida completa: `Documents/reporte_ronda1.txt`
- Notas:
  - Los tests de #10 y #11 usan dobles de prueba (fakes), no MySQL real. El propio archivo indica que la verificación definitiva requiere una prueba de integración con dos conexiones concurrentes (pendiente con Miguel Andia).
  - Cambio de contrato: `idempotency_key` bajó de 64 a 62 caracteres y el sufijo `#C` queda reservado.
  - Siguen sin integrarse: #1/#13 (Nicolas), #3/#9 (Nino), #4/#5/#6 (Leonardo), #7/#8/#14 (Mathias), #2 (Sebastian Castro) y #12 (Marcelo, por confirmar).

### Ronda 2 — 2026-10-30 (fixes de Leonardo Lonasco: #4, #5, #6)
- Base: `main` + patch `leonardo-creditos-tea-calendario.patch` (rama local `validar/leonardo-creditos`, no se sube).
- Archivos del patch: `services/creditossvc.py` (modificado), `tests/test_calendario_correcciones.py`, `tests/test_creditos_motor_flujo.py` y `CORE/CREDITOS_MOTOR_Y_FLUJO.md` (nuevos). Se verificó que el contenido del `.patch` y del `.zip` es idéntico.
- Resultado: 136 pasan / 5 xfailed / 0 fallan
- Regresiones: ninguna (los 43 tests anteriores siguen pasando)
- Archivo de salida completa: `Documents/reporte_ronda2_leonardo.txt`
- Notas:
  - Solo los hallazgos #4, #5 y #6 están corregidos. Las decisiones del motor de reglas (H-A1 a H-B4, EXCLUYE y desembolso) quedaron **documentadas, no corregidas**.
  - Cambio de contrato: la TEA se expresa como fracción (0.185 = 18.5 %). Valores fuera de [0, 5] se rechazan con `TEA_FUERA_DE_RANGO`; 0 cuotas, cuotas negativas o monto ≤ 0 devuelven `ValidationError`.
  - Los vencimientos usan meses calendario sin agregar `python-dateutil` a `requirements.txt`.
  - Pendiente: que Leonardo abra su Pull Request a `main` para integrar el cambio.

### Ronda 3 — 2026-11-01 (`main` con los fixes de Nicolas, Nino, Mathias, Sebastian Castro y Leonardo)
- Ramas integradas: `main` (autenticación JWT, bcrypt, `montar_en()` idempotente, configuración y `.env`, fixes de créditos).
- Resultado: 251 pasan / 0 fallan / 26 saltados (integración con MySQL) / 5 xfailed (decisiones del Comité de Créditos). Total: 282 tests. Ejecutado con Python 3.12 en Linux, sin MySQL.
- Regresiones: **1, ya corregida.** `TestApi::test_montar_en_es_idempotente` fallaba (esperaba 33 rutas y CORE expone 37 tras integrar auth). La idempotencia de `montar_en()` está bien (la 2.ª llamada no duplica rutas); se actualizó el número esperado en el test. Los 136 tests de la Ronda 2 siguen pasando.
- Archivo de salida completa: `Documents/reporte_ronda3.txt`
- Notas:
  - Integrado: #1 (parcial), #2, #3, #4, #5, #6, #7, #9, #13.
  - Sin integrar: #8 y #14 (RBAC) y #12 (topes y contabilidad).
  - **#1 es parcial:** solo `usuarios`, `permisos`, `auditoria` y `reportes` exigen token. Los otros 6 routers siguen abiertos y con el `actor` del cuerpo, porque `CUENTAS` y el frontend los llaman sin token (documentado en `AUTH_JWT.md`).
  - Código nuevo fuera de CORE: `COREDB/`, `database/`, docker-compose y `.github/CODEOWNERS`. `COREDB` es una API aparte, sin autenticación y de uso local.
  - Pendiente: pruebas contra MySQL real y Swagger (Miguel Andia), `test_revision_bna.py` (Santiago).

## 6. Conclusión
**Resultado de la Ronda 3 (251 pasan, 0 fallan, 26 saltados, 5 xfailed):**
- **Estado general:** 11 de los 14 hallazgos del informe están corregidos en `main` (#2, #3, #4, #5, #6, #7, #9, #10, #11 y #13, más #1 de forma parcial). Siguen abiertos #8, #12 y #14.
- **Riesgos pendientes:** (1) 6 routers sin autenticación y con el `actor` tomado del cuerpo; (2) importes negativos aceptados en `comision`, `itf` y `retencion`; (3) los secretos del `.env` anterior siguen en el historial público; (4) los fixes de #10 y #11 solo se validaron con dobles de prueba, no con MySQL real.
- **Recomendación:** no considerar cerrado el módulo CORE hasta migrar los 6 routers al JWT y corregir el RBAC.
