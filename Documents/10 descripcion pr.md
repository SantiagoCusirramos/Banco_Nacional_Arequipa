## Título sugerido

`docs(test): ronda 3 de validación, seguimiento de hallazgos y plan de pruebas manuales`

## Descripción (pegar en el Pull Request)

### Qué es este PR
Solo **documentación y reportes de pruebas** de la Actividad #8. **No modifica código** de CORE ni de otros módulos.

### Archivos
| Archivo | Cambio |
|---|---|
| `Documents/04-reporte-pruebas.md` | Ronda 3 (`main` con auth, bcrypt, `.env` y `montar_en()`), estado actualizado de los hallazgos y conclusión en borrador |
| `Documents/05-checklist-validacion.md` | Secciones 1, 2, 3, 4, 7, 9 y 11 marcadas; 4 fallas nuevas |
| `Documents/06-revision-arquitectura-schemas.md` | Ronda 3: estado de H1 y S1 a S3, código nuevo fuera de CORE |
| `Documents/08-seguimiento-hallazgos.md` | **Nuevo.** Tabla de los 14 hallazgos con estado, responsable y evidencia |
| `Documents/09-pruebas-manuales-swagger.md` | **Nuevo.** Plan de pruebas manuales (pendiente de ejecutar con la BD) |
| `Documents/reporte_ronda3.txt` | **Nuevo.** Salida completa de pytest sobre `main` |

### Resultados
- **Ronda 3 (`main`):** XX pasan / 0 fallan / XX saltados (tests de integración con MySQL).

### Estado de los hallazgos
- **Corregidos (10):** #2, #3, #4, #5, #6, #7, #9, #10, #11 y #13.
- **Parcial (1):** #1. Solo `usuarios`, `permisos`, `auditoria` y `reportes` exigen token; `clientes`, `cuentas`, `movimientos`, `tarjetas`, `creditos` y `catalogos` siguen abiertos y con el `actor` del cuerpo.
- **Sin corregir (3):** #8 y #14 (RBAC) y #12 (topes y contabilidad).

### Riesgos abiertos
1. 6 routers sin autenticación.
2. `comision`, `itf` y `retencion` aceptan negativos (S1); `moneda` e ids sin validar (S2, S3).
3. El historial público conserva el `.env` anterior: hay que rotar claves y decidir si se limpia el historial.
4. Los fixes de #10 y #11 se validaron con dobles de prueba, no con MySQL real.

### Pendiente
- `test_revision_bna.py` y los documentos de errores (Santiago).
- BD `bna`, credenciales y pruebas manuales (Miguel Andia).
- Fixes de Mathias (RBAC) y Marcelo (topes).

### Cómo reproducir
```bash
cd backend
pip install -r requirements.txt
python -m pytest -rs
git restore CORE/data/rbac.json
```