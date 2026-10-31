# Revisión de arquitectura y schemas — CORE

**Responsable:** Sebastian Alberto Monteagudo Miranda
**Fecha:** 2026-10-23
**Base revisada:** `main` (antes de los fixes del equipo)
**Método:** búsqueda estática con `grep` sobre `backend/CORE/` (no se ejecutó el sistema)

---

## 1. Arquitectura

| # | Principio | Comando de verificación | Resultado | Estado |
|---|---|---|---|---|
| A1 | Único punto de acceso a BD | `grep -rn "create_engine\|sessionmaker\|Session(" CORE --include=*.py` | Solo aparece en `CORE/database.py` | ✅ Cumple |
| A2 | Routers sin acceso directo a modelos | `grep -rn "from CORE.models" CORE/routers` | Sin resultados | ✅ Cumple |
| A3 | Routers sin consultas SQL/ORM directas | `grep -rnE "\.query\(\|\.execute\(\|select\(\|\.add\(\|\.commit" CORE/routers` | Sin resultados | ✅ Cumple |
| A4 | Transacciones (`commit`) en la capa de servicios | `grep -rlE "\.commit\(" CORE/services` | `creditossvc`, `movimientos`, `tarjetassvc`, `usuariossvc`, `cuentassvc`, `clientessvc` | ✅ Cumple |
| A5 | Sesión inyectada con `Depends(db_session)` | revisar `CORE/dependencies.py` | Los 6 routers usan `db_session` | ✅ Cumple |
| A6 | CORE no depende de otros módulos ni del frontend | `grep -rn "frontend\|import httpx\|requests" CORE --include=*.py` | Sin imports. Solo aparece `"BUS_SERVICIOS"` como valor por defecto de un campo en `models/catalogos.py` (dato, no dependencia) | ✅ Cumple |
| A7 | Comunicación entre módulos vía Bus | — | CORE no implementa cliente del Bus. `.env.example` define `BUS_BASE_URL`, pero `config.py` no lo lee | ⚠️ A confirmar con Santiago si es el diseño previsto |
| A8 | El `actor` de auditoría proviene del usuario autenticado | `grep -rn "actor" CORE/schemas` | **12 schemas** reciben `actor: str = "sistema"` desde el cuerpo de la petición | ❌ No cumple (ver H1) |

### Hallazgos de arquitectura

**H1 — `actor` viene del body (severidad alta).**
Aparece en `movimientos.py` (2), `creditos.py` (4), `cuentas.py` (2), `tarjetas.py` (2) y `clientes.py` (2). Cualquier cliente de la API puede declarar un `actor` falso y la trazabilidad queda adulterada.
Relacionado con la tarea de Nicolas Ayerve (Actividad 2: "actor desde el token, nunca desde el body").
Validación pendiente: tras el fix, el campo `actor` debe desaparecer de los schemas de entrada.

**H2 — `BUS_BASE_URL` sin uso.**
Definida en `.env.example` pero ignorada por `config.py` (`extra="ignore"`). Documentar o retirar.

## 2. Schemas Pydantic

### Controles que sí existen

| Schema | Control |
|---|---|
| `MovimientoRegistrar`, `TransferenciaRegistrar` | `monto: Field(gt=0)` |
| `MovimientoRegistrar` | `tipo_operacion` con `pattern="^(DEPOSITO\|RETIRO)$"`; `idempotency_key` max 64 |
| `creditos.py` | `monto_solicitado` y `monto` de pago con `gt=0`; `plazo_meses` con `gt=0`; ingresos/egresos/cuota con `ge=0` |
| `usuarios.py` | `username` 3–40, `password` mínimo 8 |
| `clientes.py` | longitudes mínimas y máximas en documento, nombres y celular |

### Brechas

| # | Brecha | Dónde | Riesgo |
|---|---|---|---|
| S1 | `comision`, `itf` y `retencion` son `Decimal` **sin `ge=0`** | `MovimientoRegistrar` | Un cliente podría enviar valores negativos y alterar el saldo o los asientos. **Prioridad alta** |
| S2 | `moneda` es `str` libre, sin lista cerrada (PEN/USD) | `movimientos.py` (entrada), `creditos.py` (`moneda: str = "PEN"`) | Monedas inválidas llegan al servicio |
| S3 | Identificadores (`id_cliente`, `num_cuenta`, `id_producto_ahorro`, `id_agencia`, `id_tarjeta`, cuentas origen/destino) son `str` sin formato ni longitud | `cuentas.py`, `tarjetas.py`, `movimientos.py` | Sin validación de UUID o patrón; errores caen en la BD |
| S4 | Estados como `str` libre (`estado_cuenta`, `estado_cliente`, `estado_nuevo`, `tipo_tarjeta`, `regimen`) | `cuentas.py`, `clientes.py`, `tarjetas.py` | No hay enum; se aceptan valores arbitrarios |
| S5 | `anios_vigencia: int = 4` sin límites | `TarjetaCrear` | Se aceptan 0, negativos o 1000 |
| S6 | `Decimal` sin `max_digits` ni `decimal_places` | todos los montos | Precisión y escala no controladas en la API |
| S7 | `TransferenciaRegistrar` no impide `origen == destino` a nivel de schema | `movimientos.py` | Verificar si el servicio lo rechaza |
| S8 | `correlation_id` y `motivo` sin `max_length` | varios | Menor |

## 3. Acciones sugeridas (para el equipo)

| Hallazgo | Responsable sugerido |
|---|---|
| H1 `actor` desde body | Nicolas Ayerve |
| S1 importes negativos | Renzo Montoya / Marcelo Moscoso |
| S2–S6, S8 | Mathias Ostolaza (API/schemas) |
| S7 | Renzo Montoya (transferencias) |
| H2 `BUS_BASE_URL` | Sebastian Castro (configuración) |

## 4. Pendiente de validar tras los fixes
- [ ] El campo `actor` ya no existe en los schemas de entrada
- [ ] `comision`, `itf` y `retencion` rechazan valores negativos
- [ ] `moneda` solo acepta valores del catálogo
- [ ] Los identificadores validan formato
- [ ] Transferencia con origen = destino devuelve error

## 5. Ronda 1 — 2026-10-30

| Verificación | Resultado |
|---|---|
| CORE no depende de los módulos nuevos `SOL/` ni `CUENTAS/` | `grep -rnE "(from\|import) +(SOL\|CUENTAS)\b" CORE --include=*.py` → sin coincidencias (CORE no importa los módulos nuevos) |
| Cambios en CORE desde la línea base | Router nuevo `catalogos`, cambios en `services/movimientos.py`, `schemas/movimientos.py`, `exceptions.py` y `api.py` |
| Cambios fuera de CORE | `backend/main.py` agrega CORS (origen `http://localhost:3000`); módulos nuevos `SOL/`, `CUENTAS/`, `deploy_en_docker/` de otros equipos |
| H1 `actor` en body | **Sigue abierto**: 15 schemas lo reciben |
| S1 `comision`/`itf`/`retencion` sin `ge=0` | **Sigue abierto** |
| `montar_en()` con `api_router` global (#7) | **Sigue sin corregir**; además el router `catalogos` cambia el conteo de rutas (revisar el valor esperado del test de Mathias) |
| `idempotency_key` | Cambio de contrato: máx. 62 caracteres (antes 64) |

## 6. Ronda 2 — 2026-10-30 (patch de Leonardo Lonasco)

| Verificación | Resultado |
|---|---|
| Archivos que toca el patch | `services/creditossvc.py` (modificado) y 3 archivos nuevos (2 tests y 1 documento). No modifica schemas, routers ni modelos |
| Acceso a BD / capa de servicios | Sin cambios: la validación nueva vive en el servicio (`generar_calendario_frances`, `tasa_mensual_desde_tea`), no en el router |
| Dependencias nuevas | Ninguna: `_sumar_meses()` usa `calendar` en vez de `python-dateutil` |
| Compatibilidad con otros módulos | `SOL` usa la TEA también como fracción con tope 5 (`le=5`) y tiene su propio cálculo de calendario; no hay conflicto |
| Uso de `float` | El fix no agrega `float`. H-A4 (uso de `float` en la ponderación del puntaje) sigue abierto |
| S1 (importes negativos) y H1 (`actor` en body) | Sin cambios; siguen abiertos |
| Schemas de créditos | `monto_solicitado` y `plazo_meses` ya tienen `gt=0`; `tasa_tea` solo aparece en respuestas. La validación de TEA vive solo en el servicio |
