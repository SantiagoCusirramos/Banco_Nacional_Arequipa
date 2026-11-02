# Checklist de validación — CORE

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Base:** `REPORTE_ERRORES_BUGS_CORE_Y_ARQUITECTURA.md` (sección 7) e Informe de Errores BNA
**Marcar:** `[x]` validado · `[ ]` pendiente · `[!]` falla (anotar abajo)

---

## 1. Autenticación y seguridad (Nicolas Ayerve, Nino Flores)
- [x] `POST /core/auth/login` devuelve token JWT con credenciales correctas *(Ronda 3)*
- [x] Credenciales incorrectas → **401** con mensaje genérico *(Ronda 3)*
- [x] Usuario inexistente, inactivo o bloqueado → misma respuesta (sin fuga de información) *(Ronda 3)*
- [x] Token expirado o inválido → 401 *(Ronda 3)*
- [x] `usuario_actual` lee `Authorization: Bearer <token>` (en el código se llama `usuario_actual`, no `get_current_user`)
- [x] `requiere_permiso(accion)` valida contra RBAC (en el código se llama `requiere_permiso`)
- [!] El `actor` proviene del token — **parcial**: solo en `usuarios`, `permisos`, `auditoria` y `reportes`. Los otros 6 routers siguen con `actor=payload.actor`

## 2. Hashing de contraseñas (Nino Flores)
- [x] Contraseñas nuevas se guardan con bcrypt *(Ronda 3)*
- [x] Usuario con SHA256 inicia sesión y migra a bcrypt *(Ronda 3)*
- [x] `verify_sha256(None)` devuelve `False`, sin excepción *(Ronda 3)*

## 3. Secretos y configuración (Sebastian Castro)
- [x] `git ls-files backend/.env` no devuelve nada *(el árbol de `main` ya no incluye `backend/.env`; confirmar con el comando)*
- [x] `.gitignore` cubre `.env` y mantiene `!.env.example`
- [x] `.env.example` usa `DB_NAME=bna`
- [x] Arranque sin `.env` o sin `SECRET_KEY` da error legible *(`test_configuracion.py`)*
- [!] Proceso de rotación de secretos documentado — **pendiente**: no existe el documento y el historial público conserva el `.env` anterior

## 4. Créditos (Leonardo Lonasco)
- [x] TEA fraccionaria (ej. 18.5%) no se redondea antes de calcular *(Ronda 2; confirmar con la corrida)*
- [x] `numero_cuotas < 1` → `ValidationError` *(Ronda 2)*
- [x] `monto <= 0` → `ValidationError` *(Ronda 2)*
- [x] Vencimientos por mes calendario (31 ene → 28/29 feb) *(Ronda 2)*
- [x] Redondeo solo en importes monetarios *(Ronda 2)*
- [x] Flujo CREAR_SOLICITUD → EVALUAR → APROBAR documentado (`CORE/CREDITOS_MOTOR_Y_FLUJO.md`)
- [x] Documentado: aprobar **no** genera `cob_credito`
- [x] Fix integrado en `main`
- [!] Motor de reglas: hallazgos H-A1, H-A2, H-A3, H-A4, H-B1, H-B3 **abiertos**, pendientes de decisión del Comité de Créditos (5 tests `xfail`)
- [!] EXCLUYE se comporta igual que ENTRE: pendiente decidir si se elimina o se redefine
- [ ] Contrato: la TEA se envía como fracción (0.185), tope 5; avisar a quien consuma la API

## 5. Transferencias e idempotencia (Renzo Montoya)
- [x] Cuentas bloqueadas en orden consistente *(validado con fakes; pendiente con MySQL real)*
- [x] Reintento ante deadlock implementado *(validado con fakes; pendiente con MySQL real)*
- [x] Misma `idempotency_key` con otros datos → **409**
- [x] Replay de transferencia identifica bien pata origen/destino
- [x] Una key usada en depósito no se aplica a transferencia
- [ ] Prueba de integración con MySQL y dos conexiones concurrentes (pendiente: Miguel Andia)
- [ ] Contrato: `idempotency_key` máx. 62 caracteres, sufijo `#C` reservado (avisar al frontend)

## 6. Topes y contabilidad (Marcelo Moscoso)
- [ ] Regla RGN-04 documentada (a qué aplica el tope)
- [ ] Acumulación y validación consistentes
- [ ] Casos borde: tope deshabilitado, `monto_maximo_diario` NULL
- [ ] Asiento de transferencia correcto según plan de cuentas
- [ ] `cuadre_del_dia()` cuadra con asientos reales
- [ ] `importe_moneda_base` correcto

## 7. API y RBAC (Mathias Ostolaza)
- [x] `montar_en()` idempotente (33 rutas, no 66) *(Ronda 3)*
- [!] `asignar_accion()` rechaza roles inventados — **sin corregir** (`rbac.py` no cambió)
- [!] Escritura atómica de `rbac.json` — **sin corregir**
- [!] Los tests no modifican el `rbac.json` real — **sin corregir** (se sigue restaurando a mano)

## 8. Arquitectura (revisión propia — ver `Documents/06-revision-arquitectura-schemas.md`)
- [x] Acceso a BD solo a través de `CORE/database.py`
- [x] Routers sin acceso directo a modelos ni consultas ORM
- [x] Commits de transacción en la capa de servicios
- [x] CORE no importa ni modifica otros módulos *(código de producción; en tests, `test_configuracion.py` importa `CUENTAS.config`)*
- [ ] Comunicación entre módulos vía Bus (CORE no implementa cliente del Bus; a confirmar con Santiago)
- [!] El `actor` proviene del usuario autenticado — **falla**: 12 schemas lo reciben por body (H1)
- [!] Schemas Pydantic: montos > 0 — parcial; `comision`, `itf` y `retencion` aceptan negativos (S1)
- [!] Schemas Pydantic: UUID/ids con formato — **falla**: ids como `str` libre (S3)
- [!] Schemas Pydantic: monedas válidas — **falla**: `moneda` es `str` libre (S2)

## 9. Pruebas
- [x] `python -m pytest` pasa completo en la rama integrada *(Ronda 3: XX pasan, 0 fallan)*
- [x] Ningún test que pasaba en la línea base falla ahora
- [!] Cada fix tiene su test — falta test para #8, #12 y #14 (sin fix)

## 10. Prueba manual con Swagger (`/docs`)
- [ ] Login y uso del token (Authorize)
- [ ] Crear cliente → abrir cuenta
- [ ] Depósito y retiro
- [ ] Transferencia + repetirla con la misma key
- [ ] Solicitud de crédito: crear → evaluar → aprobar
- [ ] Cuadre del día

## 11. Documentación
- [x] `CORE/README.md` con sección de Autenticación (contenido real; ver `AUTH_JWT.md` y `AUTENTICACION.md`)
- [x] `API_CORE.md` actualizado con `/core/auth/login`
- [x] Hallazgos resueltos registrados (`Documents/08-seguimiento-hallazgos.md`)

---

## Fallas encontradas

| # | Ítem | Descripción | Responsable | Estado |
|---|---|---|---|---|
| 1 | 8 | `actor` recibido por body en 12 schemas (H1) | Nicolas Ayerve | Abierto |
| 2 | 8 | `comision`/`itf`/`retencion` sin `ge=0` (S1) | Renzo Montoya / Marcelo Moscoso | Abierto |
| 3 | 8 | `moneda` e ids sin validación de formato (S2, S3) | Mathias Ostolaza | Abierto |
| 4 | 4 | Motor de reglas: reglas APROBAR restan puntos (H-A1), frontera 0.80 duplicada (H-A2), sin ingresos queda APROBADO (H-A3), se aprueba evaluación RECHAZADA (H-B1), monto sin tope (H-B3) | Leonardo Lonasco / Comité de Créditos | Abierto (documentado, sin corregir) |
| 5 | 1 | 6 routers sin autenticación y con `actor` del cuerpo: `clientes`, `cuentas`, `movimientos`, `tarjetas`, `creditos`, `catalogos` | Nicolas Ayerve | Abierto (documentado en `AUTH_JWT.md`) |
| 6 | 7 | RBAC: roles inventados, escritura no atómica y tests que modifican `rbac.json` (#8, #14) | Mathias Ostolaza | Abierto |
| 7 | 6 | Topes diarios y contabilidad (#12): sin cambios en el código | Marcelo Moscoso | Abierto |
| 8 | 3 | Rotación de secretos sin documentar; el historial público conserva el `.env` anterior (#2) | Sebastian Castro / Santiago | Abierto |