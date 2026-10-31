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
| `test_movimientos_concurrencia.py` | `TestOrdenBloqueo::test_bloquea_en_orden_ascendente_sin_importar_origen` | ⏳ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestOrdenBloqueo::test_orden_antiguo_produce_espera_circular` | ⏳ | | Hallazgo #10 · demuestra el bug anterior con candados simulados (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestOrdenBloqueo::test_orden_nuevo_no_produce_espera_circular` | ⏳ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_detecta_deadlock_mysql` | ⏳ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_reintenta_y_luego_confirma` | ⏳ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_agota_reintentos_y_responde_503` | ⏳ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_error_que_no_es_deadlock_no_se_reintenta` | ⏳ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestReintentosDeadlock::test_transferir_reintenta_ante_deadlock` | ⏳ | | Hallazgo #10 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_replay_transferencia_no_intercambia_patas` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_misma_llave_otro_monto_da_409` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_misma_llave_otro_destino_da_409` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_llave_de_deposito_no_sirve_para_transferencia` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_llave_de_transferencia_no_sirve_para_deposito` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_deposito_vs_retiro_misma_llave_da_409` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_replay_deposito_identico` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_usa_hash_guardado_en_auditoria` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_sufijo_reservado_rechazado` | ⏳ | | Hallazgo #11 · sufijo `#C` reservado (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_llave_transferencia_demasiado_larga` | ⏳ | | Hallazgo #11 · `idempotency_key` máx. 62 (nuevo, Renzo Montoya) |
| `test_movimientos_concurrencia.py` | `TestIdempotencia::test_huella_normaliza_monto` | ⏳ | | Hallazgo #11 (nuevo, Renzo Montoya) |

**Resumen línea base:** 24 tests, 24 ✅, 0 ❌.

**Resumen Ronda 1:** 43 tests (24 existentes + 19 nuevos de `test_movimientos_concurrencia.py`). Resultado: XX ✅, XX ❌. *(Reemplaza los ⏳ de los 19 tests nuevos por ✅/❌ según tu corrida.)*

> Los 24 tests existentes pasan en la línea base. Esto no significa que el código esté correcto: los hallazgos #1 al #14 del informe no están cubiertos por ningún test actual. Los tests que los detectan (`TestHashing`, `TestCalendario`, `TestApi`, `TestRbac::test_asignar_acepta_rol_inventado`) viven en `test_revision_bna.py` y están pendientes de recibirse.

### Hallazgos propios detectados durante la corrida

| Hallazgo | Evidencia |
|---|---|
| Los tests modifican `backend/CORE/data/rbac.json` (archivo real) | `git status` lo muestra como modificado tras correr la suite (Hallazgo #14) |
| `backend/.env` está trackeado en Git | `git status` lo muestra como modificado (Hallazgo #2) |
| La suite no corre sin instalar `requirements.txt` | 4 de 6 archivos fallan en collection con `ModuleNotFoundError` (`fastapi`, `pydantic_settings`) |

## 3. Tests de los hallazgos (esperados tras los fixes)

Estado: **pendiente de recibir `test_revision_bna.py`** (o crearlos cuando cada integrante entregue su rama).

| Hallazgo | Test esperado | Responsable | Rama | Base | Tras fix |
|---|---|---|---|---|---|
| #1 Auth JWT (crítica) | login 200 con token / 401 genérico / token expirado | Nicolas Ayerve | | ⏳ | ⏳ |
| #2 `.env` trackeado (crítica) | `git ls-files backend/.env` vacío | Sebastian Castro | | ❌ (confirmado) | ⏳ |
| #3 Hashing SHA256 | `TestHashing::test_hash_con_sal` | Nino Flores | | ⏳ | ⏳ |
| #9 `verify_sha256` con None | `TestHashing::test_verificar_con_hash_nulo_no_debe_explotar` | Nino Flores | | ⏳ | ⏳ |
| #4 TEA redondeada | `TestCalendario::test_tea_no_se_redondea_a_2_decimales` | Leonardo Lonasco | | ⏳ | ⏳ |
| #5 Validación de entrada | `test_cuotas_cero_valida_entrada`, `test_monto_negativo_rechazado`, `test_cuotas_negativas_rechazadas` | Leonardo Lonasco | | ⏳ | ⏳ |
| #6 Vencimientos | `test_vencimientos_mensuales_calendario` | Leonardo Lonasco | | ⏳ | ⏳ |
| #7 `montar_en()` | `TestApi::test_montar_en_es_idempotente` (33 rutas, no 66) | Mathias Ostolaza | | ⏳ | ⏳ |
| #8 / #14 RBAC | `TestRbac::test_asignar_acepta_rol_inventado` | Mathias Ostolaza | | ❌ (#14 confirmado) | ⏳ |
| #10 Deadlock transferencias | `TestOrdenBloqueo`, `TestReintentosDeadlock` (8 tests, con fakes) | Renzo Montoya | `main` | ⏳ | ⏳ (confirmar con la corrida; falta prueba con MySQL real) |
| #11 Idempotencia | `TestIdempotencia` (11 tests, con fakes): key reutilizada con otros datos → 409 | Renzo Montoya | `main` | ⏳ | ⏳ (confirmar con la corrida; falta prueba con MySQL real) |
| #12 Tope diario | (definir) | Marcelo Moscoso | | ⏳ | ⏳ |
| #13 Login 404 vs 401 | login inválido → 401 | Nicolas Ayerve | | ⏳ | ⏳ |

Leyenda: ✅ pasa · ❌ falla · ⏳ pendiente

## 4. Regresiones detectadas

| Fecha | Test | Rama que lo rompió | Responsable | Estado |
|---|---|---|---|---|
| | | | | |

## 5. Rondas de validación

### Ronda 0 — Línea base, 2026-10-23
- Ramas integradas: `main`
- Resultado: 24 pasan / 0 fallan
- Notas: ver "Hallazgos propios detectados durante la corrida".

### Ronda 1 — 2026-10-30
- Ramas integradas: `main` (incluye fixes de Renzo Montoya: #10 y #11)
- Resultado: XX pasan / XX fallan (de 43 tests)
- Regresiones: ninguna *(si falla alguno de los 24 originales, listarlo en la sección 4)*
- Archivo de salida completa: `Documents/reporte_ronda1.txt`
- Notas:
  - Los tests de #10 y #11 usan dobles de prueba (fakes), no MySQL real. El propio archivo indica que la verificación definitiva requiere una prueba de integración con dos conexiones concurrentes (pendiente con Miguel Andia).
  - Cambio de contrato: `idempotency_key` bajó de 64 a 62 caracteres y el sufijo `#C` queda reservado.
  - Siguen sin integrarse: #1/#13 (Nicolas), #3/#9 (Nino), #4/#5/#6 (Leonardo), #7/#8/#14 (Mathias), #2 (Sebastian Castro) y #12 (Marcelo, por confirmar).

## 6. Conclusión
(Completar al final: estado general, riesgos pendientes, recomendación de merge.)