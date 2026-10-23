# Checklist de validación — CORE

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Base:** `REPORTE_ERRORES_BUGS_CORE_Y_ARQUITECTURA.md` (sección 7) e Informe de Errores BNA
**Marcar:** `[x]` validado · `[ ]` pendiente · `[!]` falla (anotar abajo)

---

## 1. Autenticación y seguridad (Nicolas Ayerve, Nino Flores)
- [ ] `POST /core/auth/login` devuelve token JWT con credenciales correctas
- [ ] Credenciales incorrectas → **401** con mensaje genérico "Credenciales inválidas"
- [ ] Usuario inexistente, inactivo o bloqueado → misma respuesta (sin fuga de información)
- [ ] Token expirado o inválido → 401
- [ ] `get_current_user` lee `Authorization: Bearer <token>`
- [ ] `require_action(accion)` valida contra RBAC
- [ ] El `actor` proviene del token, nunca del body

## 2. Hashing de contraseñas (Nino Flores)
- [ ] Contraseñas nuevas se guardan con bcrypt
- [ ] Usuario con SHA256 inicia sesión y migra a bcrypt
- [ ] `verify_sha256(None)` devuelve `False`, sin excepción

## 3. Secretos y configuración (Sebastian Castro)
- [ ] `git ls-files backend/.env` no devuelve nada
- [ ] `.gitignore` cubre `.env` y mantiene `!.env.example`
- [ ] `.env.example` usa `DB_NAME=bna`
- [ ] Arranque sin `.env` o sin `SECRET_KEY` da error legible
- [ ] Proceso de rotación de secretos documentado

## 4. Créditos (Leonardo Lonasco)
- [ ] TEA fraccionaria (ej. 18.5%) no se redondea antes de calcular
- [ ] `numero_cuotas < 1` → `ValidationError`
- [ ] `monto <= 0` → `ValidationError`
- [ ] Vencimientos por mes calendario (31 ene → 28/29 feb)
- [ ] Redondeo solo en importes monetarios
- [ ] Flujo CREAR_SOLICITUD → EVALUAR → APROBAR documentado
- [ ] Documentado: aprobar **no** genera `cob_credito`

## 5. Transferencias e idempotencia (Renzo Montoya)
- [ ] Cuentas bloqueadas en orden consistente
- [ ] Reintento ante deadlock implementado
- [ ] Misma `idempotency_key` con otros datos → **409**
- [ ] Replay de transferencia identifica bien pata origen/destino
- [ ] Una key usada en depósito no se aplica a transferencia

## 6. Topes y contabilidad (Marcelo Moscoso)
- [ ] Regla RGN-04 documentada (a qué aplica el tope)
- [ ] Acumulación y validación consistentes
- [ ] Casos borde: tope deshabilitado, `monto_maximo_diario` NULL
- [ ] Asiento de transferencia correcto según plan de cuentas
- [ ] `cuadre_del_dia()` cuadra con asientos reales
- [ ] `importe_moneda_base` correcto

## 7. API y RBAC (Mathias Ostolaza)
- [ ] `montar_en()` idempotente (33 rutas, no 66)
- [ ] `asignar_accion()` rechaza roles inventados
- [ ] Escritura atómica de `rbac.json`
- [ ] Los tests no modifican el `rbac.json` real

## 8. Arquitectura (revisión propia)
- [ ] Acceso a BD solo a través de `CORE/database.py`
- [ ] CORE no importa ni modifica otros módulos
- [ ] Comunicación entre módulos vía Bus, no directa
- [ ] Schemas Pydantic: montos > 0, UUID válidos, monedas válidas

## 9. Pruebas
- [ ] `python -m pytest` pasa completo en la rama integrada
- [ ] Ningún test que pasaba en la línea base falla ahora
- [ ] Cada fix tiene su test

## 10. Prueba manual con Swagger (`/docs`)
- [ ] Login y uso del token (Authorize)
- [ ] Crear cliente → abrir cuenta
- [ ] Depósito y retiro
- [ ] Transferencia + repetirla con la misma key
- [ ] Solicitud de crédito: crear → evaluar → aprobar
- [ ] Cuadre del día

## 11. Documentación
- [ ] `CORE/README.md` con sección de Autenticación
- [ ] `API_CORE.md` actualizado con `/core/auth/login`
- [ ] Hallazgos resueltos registrados

---

## Fallas encontradas

| # | Ítem | Descripción | Responsable | Estado |
|---|---|---|---|---|
| | | | | |