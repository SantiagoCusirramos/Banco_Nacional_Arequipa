# Reporte de pruebas — CORE (Banco Nacional de Arequipa)

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Alcance:** `backend/CORE/tests/`
**Comando:** `cd backend && python -m pytest`

---

## 1. Línea base (antes de los fixes del equipo)

| Dato | Valor |
|---|---|
| Fecha de ejecución | AAAA-MM-DD |
| Rama / commit base | `main` @ `xxxxxxx` |
| Versión de Python | 3.x.x |
| Total de tests | N |
| Pasan | N |
| Fallan | N |
| Errores | N |
| Archivo de salida completa | `reporte_pruebas_base.txt` |

## 2. Matriz de pruebas existentes

| Archivo | Test | Base | Tras fixes | Observación |
|---|---|---|---|---|
| `test_api_smoke.py` | (completar) | ✅/❌ | | |
| `test_creditos_logica.py` | (completar) | ✅/❌ | | |
| `test_excepciones.py` | (completar) | ✅/❌ | | |
| `test_motor_reglas.py` | (completar) | ✅/❌ | | |
| `test_rbac.py` | (completar) | ✅/❌ | | |
| `test_utilidades.py` | (completar) | ✅/❌ | | |

> Para listar los nombres: `python -m pytest --collect-only -q`

## 3. Tests de los hallazgos (esperados tras los fixes)

Estado: **pendiente de recibir `test_revision_bna.py`** (o crearlos cuando cada integrante entregue su rama).

| Hallazgo | Test esperado | Responsable | Rama | Base | Tras fix |
|---|---|---|---|---|---|
| #1 Auth JWT (crítica) | login 200 con token / 401 genérico / token expirado | Nicolas Ayerve | | ⏳ | ⏳ |
| #2 `.env` trackeado (crítica) | `git ls-files backend/.env` vacío | Sebastian Castro | | ⏳ | ⏳ |
| #3 Hashing SHA256 | `TestHashing::test_hash_con_sal` | Nino Flores | | ⏳ | ⏳ |
| #9 `verify_sha256` con None | `TestHashing::test_verificar_con_hash_nulo_no_debe_explotar` | Nino Flores | | ⏳ | ⏳ |
| #4 TEA redondeada | `TestCalendario::test_tea_no_se_redondea_a_2_decimales` | Leonardo Lonasco | | ⏳ | ⏳ |
| #5 Validación de entrada | `test_cuotas_cero_valida_entrada`, `test_monto_negativo_rechazado`, `test_cuotas_negativas_rechazadas` | Leonardo Lonasco | | ⏳ | ⏳ |
| #6 Vencimientos | `test_vencimientos_mensuales_calendario` | Leonardo Lonasco | | ⏳ | ⏳ |
| #7 `montar_en()` | `TestApi::test_montar_en_es_idempotente` (33 rutas, no 66) | Mathias Ostolaza | | ⏳ | ⏳ |
| #8 / #14 RBAC | `TestRbac::test_asignar_acepta_rol_inventado` | Mathias Ostolaza | | ⏳ | ⏳ |
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

### Ronda 1 — AAAA-MM-DD
- Ramas integradas:
- Resultado: N pasan / N fallan
- Notas:

## 6. Conclusión
(Completar al final: estado general, riesgos pendientes, recomendación de merge.)