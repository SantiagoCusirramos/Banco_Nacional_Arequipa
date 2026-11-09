# Revisión de arquitectura y schemas — CORE

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Actualizado:** 2026-11-01 (Ronda 3)
**Base de la revisión original:** `main` del 2026-10-23, antes de los fixes del equipo
**Método:** búsqueda estática con `grep` sobre `backend/CORE/` (no se ejecutó el sistema; los resultados de pytest están en `04-reporte-pruebas.md`)

Leyenda: ✅ cumple · ⚠️ cumple con reservas · ❌ no cumple · ⏳ por verificar

---

## 1. Arquitectura

| # | Principio | Verificación | Resultado (Ronda 3) | Estado |
|---|---|---|---|---|
| A1 | Único punto de acceso a BD | `grep -rn "create_engine\|sessionmaker\|Session(" CORE --include=*.py` (sin tests) | Solo `database.py` y `dependencies.py` (la sesión inyectada) | ✅ |
| A2 | Routers sin acceso directo a modelos | `grep -rn "from CORE.models" CORE/routers` | `admin.py` importa `UsuarioSistema` solo como anotación de tipo. **`catalogos.py` importa `Agencia` y `ProductoAhorro`** | ❌ Router nuevo `catalogos` |
| A3 | Routers sin consultas ORM directas | `grep -rnE "\.query\(\|\.execute\(\|select\(\|\.add\(\|\.commit" CORE/routers` | **`catalogos.py` ejecuta `select(Agencia)` y `select(ProductoAhorro)` dentro del router** | ❌ Router nuevo `catalogos` |
| A4 | Transacciones (`commit`) en la capa de servicios | `grep -rlE "\.commit\(" CORE/services` | `authsvc`, `creditossvc`, `movimientos`, `tarjetassvc`, `usuariossvc`, `cuentassvc`, `clientessvc` | ✅ |
| A5 | Sesión inyectada con `Depends(db_session)` | `grep -l "db_session" CORE/routers/*.py` | Los 8 routers: `admin`, `auth`, `catalogos`, `clientes`, `creditos`, `cuentas`, `movimientos`, `tarjetas` | ✅ |
| A6 | CORE no depende de otros módulos ni del frontend | `grep -rnE "(from\|import) +(COREDB\|SOL\|CUENTAS)\b" CORE --include=*.py` | Producción: sin imports. **En tests:** `CORE/tests/test_configuracion.py` importa `CUENTAS.config` | ⚠️ Acoplamiento solo en pruebas |
| A7 | Comunicación entre módulos vía Bus | — | CORE no implementa cliente del Bus. `.env.example` define `BUS_BASE_URL` y `config.py` no lo lee | ⏳ Confirmar con Santiago si es el diseño previsto |
| A8 | El `actor` de auditoría proviene del usuario autenticado | `grep -rn "actor" CORE/schemas CORE/routers` | Cumple en `usuarios`, `permisos`, `auditoria` y `reportes`. **No cumple en `clientes`, `cuentas`, `movimientos`, `tarjetas` y `creditos`**: 12 schemas de entrada reciben `actor: str = "sistema"` y el router lo usa (`actor=payload.actor`) | ❌ Parcial (H1) |
| A9 | Rutas protegidas con token | `grep -c "usuario_actual\|requiere_permiso" CORE/routers/*.py` | Con token: `admin` y `auth`. **Sin token:** `catalogos`, `clientes`, `creditos`, `cuentas`, `movimientos` y `tarjetas` (documentado en `AUTH_JWT.md`: `CUENTAS` y el frontend los llaman sin token) | ❌ Parcial (hallazgo #1) |

### Hallazgos de arquitectura

**H1 — `actor` viene del body en 5 routers (severidad alta).**
Repartido en `creditos.py` (4 schemas), `clientes.py` (2), `movimientos.py` (2), `tarjetas.py` (2) y `cuentas.py` (2). Quien llame a la API puede declarar un `actor` falso y la trazabilidad queda adulterada.
Resuelto solo en las rutas de administración, que toman el actor del token y ignoran el del cuerpo.
Validación pendiente: tras migrar cada router al JWT, el campo `actor` debe desaparecer de sus schemas de entrada.

**H2 — `BUS_BASE_URL` sin uso.**
Definida en `.env.example` e ignorada por `config.py` (`extra="ignore"`). Documentar o retirar.

**H3 — Router `catalogos` con consultas ORM propias (nuevo).**
Rompe el principio "los routers solo llaman a servicios". Propuesta: mover las dos consultas a un servicio (por ejemplo `catalogossvc.py`) y que el router solo lo invoque. Además `catalogos` no exige token.

**H4 — Un test de CORE depende de `CUENTAS` (nuevo, severidad baja).**
`test_configuracion.py` importa `CUENTAS.config` para comprobar que `.env.example` declara lo que leen ambas configuraciones. Si `CUENTAS` cambia o se separa, ese test de CORE se rompe.

## 2. Schemas Pydantic

### Controles que sí existen

| Schema | Control |
|---|---|
| `MovimientoRegistrar`, `TransferenciaRegistrar` | `monto: Field(gt=0)` |
| `MovimientoRegistrar` | `tipo_operacion` con `pattern="^(DEPOSITO\|RETIRO)$"`; `idempotency_key` máx. 62 caracteres |
| `creditos.py` | `monto_solicitado` y `monto` de pago con `gt=0`; `plazo_meses` con `gt=0`; ingresos, egresos y cuota con `ge=0` |
| `usuarios.py` | `username` de 3 a 40 caracteres, `password` mínimo 8 |
| `clientes.py` | Longitudes mínimas y máximas en documento, nombres y celular |
| Errores 422 | Ya no devuelven el valor recibido (por ejemplo, la contraseña) |

### Brechas

| # | Brecha | Dónde | Riesgo | Estado en la Ronda 3 |
|---|---|---|---|---|
| S1 | `comision`, `itf` y `retencion` son `Decimal` **sin `ge=0`** | `MovimientoRegistrar` | Valores negativos alteran el saldo y los asientos. **Prioridad alta** | ❌ Abierto |
| S2 | `moneda` es `str` libre, sin lista cerrada (PEN/USD) | `movimientos.py`, `creditos.py` (`moneda: str = "PEN"`) | Monedas inválidas llegan al servicio | ❌ Abierto |
| S3 | Identificadores (`id_cliente`, `num_cuenta`, `id_producto_ahorro`, `id_agencia`, `id_tarjeta`) como `str` sin formato ni longitud | `cuentas.py`, `tarjetas.py`, `movimientos.py` | Los errores caen en la BD | ❌ Abierto |
| S4 | Estados y tipos como `str` libre (`estado_cuenta`, `estado_nuevo`, `tipo_tarjeta`, `regimen`) | `cuentas.py`, `tarjetas.py` | No hay enum; se aceptan valores arbitrarios | ❌ Abierto |
| S5 | `anios_vigencia: int = 4` sin límites | `TarjetaCrear` | Se aceptan 0, negativos o 1000 | ❌ Abierto |
| S6 | `Decimal` sin `max_digits` ni `decimal_places` | Todos los montos | Precisión no controlada en la API | ❌ Abierto |
| S7 | Transferencia con origen igual a destino | `movimientos.py` | — | ✅ El servicio la rechaza con `ValidationError` (verificado en el código; falta test) |
| S8 | `correlation_id` y `motivo` sin `max_length` | Varios schemas | Menor | ❌ Abierto |

## 3. Acciones sugeridas (para el equipo)

| Hallazgo | Responsable sugerido |
|---|---|
| H1 `actor` en el body y hallazgo #1 (6 routers sin token) | Nicolas Ayerve |
| H3 consultas ORM en el router `catalogos` | Quien creó `catalogos` (a confirmar con Santiago) |
| S1 importes negativos | Renzo Montoya / Marcelo Moscoso |
| S2, S3, S4, S5, S6, S8 | Mathias Ostolaza (API y schemas) |
| H2 `BUS_BASE_URL` | Sebastian Castro (configuración) |
| H4 test acoplado a `CUENTAS` | Quien escribió `test_configuracion.py` |

## 4. Pendiente de validar tras los fixes

- [ ] El campo `actor` desaparece de los schemas de entrada de `clientes`, `cuentas`, `movimientos`, `tarjetas` y `creditos`
- [ ] Los 6 routers abiertos exigen token
- [ ] `comision`, `itf` y `retencion` rechazan valores negativos
- [ ] `moneda` solo acepta valores del catálogo
- [ ] Los identificadores validan formato
- [ ] Las consultas del router `catalogos` pasan a un servicio
- [x] Transferencia con origen igual a destino devuelve error (ya implementado en el servicio)

---

## 5. Historial de rondas

### Ronda 1 — 2026-10-30 (`main` con los fixes de Renzo Montoya)

| Verificación | Resultado |
|---|---|
| CORE no depende de `SOL` ni `CUENTAS` | Sin imports en producción |
| Cambios en CORE desde la línea base | Router `catalogos`; cambios en `services/movimientos.py`, `schemas/movimientos.py`, `exceptions.py` y `api.py` |
| Cambios fuera de CORE | `backend/main.py` agrega CORS (origen `http://localhost:3000`); módulos nuevos `SOL/`, `CUENTAS/` y `deploy_en_docker/` de otros equipos |
| H1 y S1 | Siguen abiertos |
| `montar_en()` | Seguía con un `api_router` global |
| `idempotency_key` | Cambio de contrato: máx. 62 caracteres (antes 64) |

### Ronda 2 — 2026-10-30 (patch de Leonardo Lonasco, hallazgos #4, #5 y #6)

| Verificación | Resultado |
|---|---|
| Archivos del patch | `services/creditossvc.py` (modificado) y 3 archivos nuevos (2 tests y 1 documento). No toca schemas, routers ni modelos |
| Dependencias nuevas | Ninguna: `_sumar_meses()` usa `calendar` en lugar de `python-dateutil` |
| Compatibilidad con otros módulos | `SOL` usa también la TEA como fracción con tope 5 y tiene su propio cálculo de calendario; no hay conflicto |
| `float` | El fix no agrega `float`; H-A4 (ponderación del puntaje) sigue abierto |
| Schemas de créditos | La validación de la TEA vive solo en el servicio |

### Ronda 3 — 2026-11-01 (`main` con los fixes integrados)

| Verificación | Resultado |
|---|---|
| Autenticación | Nuevos `routers/auth.py`, `schemas/auth.py`, `services/authsvc.py` y `utils/tokens.py`. El token lleva solo identidad; los permisos se consultan en cada petición |
| H1 (`actor` en el body) | Parcial: resuelto en administración, abierto en 5 routers |
| Routers sin token | `catalogos`, `clientes`, `creditos`, `cuentas`, `movimientos` y `tarjetas` |
| S1, S2, S3 | Siguen abiertos |
| `montar_en()` | Corregido: router local y bandera en `app.state` |
| `config.py` | Valida `SECRET_KEY` (mínimo 32 caracteres, rechaza el valor de ejemplo) con un mensaje que no repite el valor |
| Código nuevo fuera de CORE | `COREDB/` (API aparte, **sin autenticación**, uso local), `database/`, `docker-compose.coredb*.yml`, `.github/CODEOWNERS`. Sus puertos (8012 y 3307) no chocan con los de CORE |
| Nuevos hallazgos | H3 (consultas ORM en `catalogos`), H4 (test de CORE acoplado a `CUENTAS`) |
