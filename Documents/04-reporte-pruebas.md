# Reporte de pruebas — CORE (Banco Nacional de Arequipa)

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Alcance:** `backend/CORE/tests/`
**Comando:** `cd backend && python -m pytest`

---

## 1. Línea base (antes de los fixes del equipo)

| Dato | Valor |
|---|---|
| Fecha de ejecución | 2026-10-23 |
| Rama / commit base | `main` @ `HASH_AQUI` (obtener con `git rev-parse --short HEAD`) |
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

**Resumen:** 24 tests, 24 ✅, 0 ❌.

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
| #10 Deadlock transferencias | (definir) | Renzo Montoya | | ⏳ | ⏳ |
| #11 Idempotencia | key reutilizada con otros datos → 409 | Renzo Montoya | | ⏳ | ⏳ |
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

### Ronda 1 — AAAA-MM-DD
- Ramas integradas:
- Resultado: N pasan / N fallan
- Notas:

## 6. Conclusión
(Completar al final: estado general, riesgos pendientes, recomendación de merge.)