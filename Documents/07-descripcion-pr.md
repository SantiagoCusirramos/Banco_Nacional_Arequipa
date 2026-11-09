## Título sugerido

`docs(test): rondas 1 y 2 de validación, revisión de arquitectura/schemas y checklist`

## Descripción (pegar en el Pull Request)

### Qué es este PR
Solo **documentación y reportes de pruebas** de la Actividad #8 (pruebas, validación y documentación). **No modifica código de CORE** ni de otros módulos.

### Archivos
| Archivo | Cambio |
|---|---|
| `Documents/04-reporte-pruebas.md` | Línea base (24/24), Ronda 1 (fixes de Renzo, #10 y #11) y Ronda 2 (fixes de Leonardo, #4/#5/#6) |
| `Documents/05-checklist-validacion.md` | Checklist de validación con secciones 4, 5 y 8 actualizadas y tabla de fallas |
| `Documents/06-revision-arquitectura-schemas.md` | Revisión estática de arquitectura y schemas, con las rondas 1 y 2 |
| `Documents/reporte_ronda1.txt` | Salida completa de pytest sobre `main` |
| `Documents/reporte_ronda2_leonardo.txt` | Salida completa de pytest sobre `main` + patch de Leonardo (solo evidencia) |
| `backend/CORE/README.md` | Sección "Autenticación" (pendiente de implementación), 23 líneas agregadas, 0 eliminadas |
| `README.md` | Sección "Autenticación" (pendiente de implementación) |
| `backend/pytest.ini` | Configuración de pytest (ya integrado) |

### Resultados
- **Ronda 1 (`main`):** 43 pasan / 0 fallan de 43 tests. Incluye los 19 tests de Renzo (#10 deadlock y #11 idempotencia), validados con dobles de prueba, no con MySQL real.
- **Ronda 2 (`main` + patch de Leonardo):** 136 pasan / 5 `xfailed` esperados / 0 fallan. Cubre #4 (TEA exacta), #5 (validación de entradas) y #6 (vencimientos por mes calendario).

### Hallazgos abiertos detectados
1. **H1 — `actor` viene del body** en 15 schemas: cualquiera puede falsificar la trazabilidad (depende del JWT, Nicolas).
2. **S1 — `comision`, `itf` y `retencion` sin `ge=0`**: aceptan valores negativos (Renzo / Marcelo).
3. **S2, S3 — `moneda` e ids sin validación de formato** (Mathias).
4. **Motor de reglas (Leonardo):** H-A1 a H-B4, EXCLUYE y desembolso quedaron documentados, no corregidos; esperan decisión del Comité de Créditos.
5. **Los tests modifican `rbac.json` real** (#14) y **`backend/.env` sigue trackeado** (#2).

### Cambios de contrato a comunicar
- `idempotency_key` bajó de 64 a 62 caracteres y el sufijo `#C` está reservado (Renzo).
- La TEA se envía como fracción (0.185 = 18.5 %); fuera de [0, 5] se rechaza (Leonardo, aún no integrado).

### Pendiente
- Fixes de Nicolas (JWT), Nino (bcrypt), Mathias (`montar_en`/RBAC), Sebastian Castro (`.env`) y Marcelo (topes), por validar cuando suban su rama.
- `test_revision_bna.py` y los documentos de errores (Santiago).
- Pruebas manuales con Swagger y prueba de integración con MySQL (Miguel Andia).

### Cómo reproducir
```bash
cd backend
pip install -r requirements.txt
python -m pytest
```
(Después de correr la suite: `git restore CORE/data/rbac.json`.)