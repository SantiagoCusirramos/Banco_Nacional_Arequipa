# Pruebas manuales con Swagger — CORE

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Fecha:** AAAA-MM-DD
**Entorno:** `uvicorn main:app --reload` · `http://localhost:8000/docs` · BD `bna` cargada con `99_bna_unificado.sql`
**Requisitos:** BD `bna` y credenciales de `bna_user` (Miguel Andia); `SECRET_KEY` propia de 32+ caracteres en `backend/.env`; usuario administrador de la carga inicial.

> Estado: **pendiente de ejecutar.** Completar `Resultado` con ✅ / ❌ y anotar las evidencias.

## 1. Autenticación

| # | Prueba | Pasos | Esperado | Resultado | Observación |
|---|---|---|---|---|---|
| 1.1 | Login correcto | `POST /core/auth/login` con usuario válido | 200 con `access_token`, `expires_in` y usuario sin hash | | |
| 1.2 | Login incorrecto | Contraseña errónea | 401 con mensaje genérico | | |
| 1.3 | Usuario inexistente | Usuario que no existe | 401 idéntico al 1.2 | | |
| 1.4 | Autorizar | Botón **Authorize** con el token | `GET /core/auth/me` devuelve perfil y acciones | | |
| 1.5 | Sin token | `GET /core/usuarios` sin token | 401 `TOKEN_REQUERIDO` | | |
| 1.6 | Sin permiso | Token de un rol sin `VER_AUDITORIA` | 403 `PERMISO_DENEGADO` | | |
| 1.7 | Rutas abiertas | `GET /core/clientes` sin token | **200 (hallazgo abierto: debería exigir token)** | | |

## 2. Clientes y cuentas

| # | Prueba | Esperado | Resultado | Observación |
|---|---|---|---|---|
| 2.1 | Crear cliente | 201 con el cliente creado | | |
| 2.2 | Abrir cuenta | 201, saldo en cero | | |

## 3. Movimientos

| # | Prueba | Esperado | Resultado | Observación |
|---|---|---|---|---|
| 3.1 | Depósito | Saldo aumenta; asiento generado | | |
| 3.2 | Retiro | Saldo disminuye | | |
| 3.3 | Retiro sin saldo | Error `SALDO_INSUFICIENTE` | | |
| 3.4 | Transferencia | Dos movimientos; saldos correctos | | |
| 3.5 | Repetir con la misma `idempotency_key` | Devuelve el mismo resultado | | |
| 3.6 | Misma key con otro monto | 409 `IDEMPOTENCY_KEY_REUTILIZADA` | | |
| 3.7 | Key de 63 o 64 caracteres | Rechazada (máx. 62) | | |
| 3.8 | `comision` negativa | **Hoy se acepta (hallazgo S1)** | | |

## 4. Créditos

| # | Prueba | Esperado | Resultado | Observación |
|---|---|---|---|---|
| 4.1 | Crear solicitud | Estado REGISTRADA y calendario SIMULADO | | |
| 4.2 | Evaluar | Estado EN_EVALUACION; resultado y puntaje | | |
| 4.3 | Aprobar | Estado APROBADA; no se crea `cob_credito` (hueco conocido) | | |
| 4.4 | Aprobar una evaluación rechazada | **Hoy se permite (hallazgo H-B1)** | | |

## 5. Reportes

| # | Prueba | Esperado | Resultado | Observación |
|---|---|---|---|---|
| 5.1 | Cuadre del día | Débitos y créditos cuadran | | |

## 6. Conclusión
(Completar tras la ejecución.)