# Módulo 9 · Seguridad

Evaluación de operaciones con desafío, bitácora sellada con HMAC, incidentes y desbloqueo de
tarjetas. **No tiene base propia:** todo lo que guarda está en la base integrada (bna-core-db
desde `bd-v1.13-mysql`) y llega a ella solo por COREDB, a través del Bus de Servicios
(`/bus/coredb`), con su usuario de servicio `svc-seguridad`. Tampoco tiene usuarios propios:
entra el personal del banco con su usuario de COREDB.

Antes era un prototipo aparte sobre SQLite (usuarios con Argon2, topes y acumulados propios,
bitácora firmada en su archivo). Esa base y su volumen ya no existen; ver «Qué cambió».

## Con el producto

`./bna up`, desde la raíz del repositorio, lo levanta en http://127.0.0.1:8013 (consola en `/`,
API en `/docs`). `coredb-init` crea `svc-seguridad` con `SEGURIDAD_COREDB_SECRETO` de `.env`;
la clave de los HMAC es `SEGURIDAD_SECRET_KEY`. Los demás consumidores llegan por
`/bus/seguridad`. Se entra con el usuario `admin` (contraseña `BNA_ADMIN_PASSWORD` de `.env`) u
otro usuario de COREDB.

## Cómo llama a COREDB

Cada llamada que guarda algo lleva **dos tokens**: el de `svc-seguridad` en `Authorization`
(acción `OPERAR_SEGURIDAD`, que solo tiene ese usuario) y el de la persona en `X-Persona-Token`.
COREDB comprueba el permiso de la persona y la registra como actor en la bitácora. Así una
persona no llega a esas rutas sin pasar por Seguridad, y Seguridad no actúa sin una persona.
Leer la bitácora se hace con el token de la persona; sellarla y verificarla, con el del servicio.

## Contratos

Todas las rutas `/seguridad/*` exigen `X-Correlation-ID` (1 a 100 caracteres alfanuméricos o
`_ . : -`). Las protegidas, `Authorization: Bearer <token de COREDB>`. Errores:
`{"error": {"code", "message"}}`.

| Ruta | Método | Permiso (acción de COREDB) | En COREDB |
|---|---|---|---|
| `/seguridad/estado` | GET | público | `/coredb/salud` |
| `/seguridad/auth/login` | POST | credenciales de COREDB | `/coredb/auth/login` |
| `/seguridad/auth/me` | GET | sesión | `/coredb/auth/me` |
| `/seguridad/operaciones/evaluar` | POST | `REGISTRAR_MOVIMIENTO` | `/coredb/seguridad/evaluaciones`, `/coredb/seguridad/desafios` |
| `/seguridad/auditoria` | GET | `VER_AUDITORIA` | `/coredb/auditoria` (últimos 100) |
| `/seguridad/auditoria/sellos` | POST | `VER_AUDITORIA` | `/coredb/auditoria/sellos` |
| `/seguridad/auditoria/verificar` | GET | `VER_AUDITORIA` | `/coredb/auditoria`, `/coredb/auditoria/sellos` |
| `/seguridad/incidentes` | GET | `VER_AUDITORIA` o `GESTIONAR_INCIDENTES` | `/coredb/seguridad/incidentes` |
| `/seguridad/incidentes` | POST | `GESTIONAR_INCIDENTES` | `/coredb/seguridad/incidentes` |
| `/seguridad/incidentes/{id}` | PATCH | `GESTIONAR_INCIDENTES` | `/coredb/seguridad/incidentes/{id}/estado` |
| `/seguridad/tarjetas/{id}/desbloqueo` | POST | `BLOQUEAR_TARJETA` | `/coredb/tarjetas/{id}/desbloqueo` |

`GESTIONAR_INCIDENTES` la tienen OPERADOR y ADMINISTRADOR; `VER_AUDITORIA`, AUDITOR y
ADMINISTRADOR; `REGISTRAR_MOVIMIENTO` y `BLOQUEAR_TARJETA`, OPERADOR y ADMINISTRADOR.

### Evaluar una operación

```json
{"uuid_operacion": "…uuid…", "num_cuenta": "CTA-…", "canal": "ATM", "monto": "850.00"}
```

Canales: los de `core.canal` (`ATM`, `HB`, `BD`, `VEN`, `AGE`). COREDB compara el monto con el
**tope real** del canal en la moneda de la cuenta (`core.limite_canal`: ATM S/ 1 500, HB
S/ 10 000, BD S/ 500…) y el **consumo real** del día de la cuenta en ese canal
(`core.consumo_diario`). Respuesta: `decision` `AUTORIZADA`, `RECHAZADA` (`motivo` `TOPE`,
`CANAL` o `CUENTA`), `DESAFIO_REQUERIDO` o `DESAFIO_RECHAZADO`, con `tope`, `consumido`,
`repetida` y `efecto_financiero: false`. Evaluar no mueve dinero ni suma al consumo: el débito
real vuelve a pasar por el tope.

Sobre el 80 % del tope responde `DESAFIO_REQUERIDO` con `id_desafio`, `vence_en` (120 s) y
`codigo_demo`. Se reenvía la misma operación con `id_desafio` y `codigo`. Seguridad calcula el
HMAC del código con su clave y COREDB guarda solo ese HMAC; tres códigos incorrectos agotan el
desafío. **El código se muestra por el mismo canal: no demuestra un segundo factor.** El
`uuid_operacion` es la llave idempotente: repetirlo con los mismos datos devuelve la misma
decisión; con otros, 409 `BNA-IDEMPOTENCIA`.

### Bitácora sellada

La bitácora es la general de COREDB (`core.evento_auditoria`), que escriben los procedimientos
de todos los módulos. Seguridad la sella cada minuto (`SEGURIDAD_SELLADO_SEG`, 0 lo apaga): un
HMAC encadenado sobre los eventos del tramo que sigue al último sello, con al menos un minuto de
antigüedad (`SEGURIDAD_SELLADO_ANTIGUEDAD_SEG`; una transacción lenta podría confirmar después
un evento con un id menor). COREDB guarda el sello y comprueba que el tramo empieza donde acabó
el anterior y tiene los eventos declarados. `GET /seguridad/auditoria/verificar` recalcula
todos los sellos: un evento sellado cambiado, borrado o agregado, la bitácora vaciada (brecha
G03 de la base) o un sello cambiado rompen la cadena. Lo no sellado no queda protegido y quien
tenga la clave puede rehacer los sellos. No es un SIEM ni almacenamiento inmutable.

### Incidentes

ABIERTO → EN_PROGRESO → RESUELTO (exige `resolucion`) → CERRADO, sin saltos (409
`BNA-INCIDENTE-TRANSICION`). La respuesta agrega los SLA propuestos (P1 15/120 min, P2 30/240,
P3 120/1440, P4 480/4320): objetivos, no resultados medidos; reloj continuo.

### Desbloqueo de tarjetas

TARJETAS y `POST /coredb/tarjetas/{id}/estado` rechazan el desbloqueo (403
`BNA-DESBLOQUEO`): en la base solo el rol `bna_seguridad` puede ejecutar
`tarjetas.desbloquear_tarjeta`. Seguridad lo pide a COREDB por una persona con
`BLOQUEAR_TARJETA`; COREDB lo ejecuta con la cuenta `bna_seguridad_user` y nada más, y la
tarjeta vuelve a ACTIVA con origen `SEGURIDAD` y la persona como actor. Una tarjeta que no está
bloqueada responde 409 `TARJETA_NO_BLOQUEADA`.

## Pruebas

Desde la raíz del repositorio (todo en contenedores):

```bash
backend/seguridad/scripts/pruebas_integracion.sh
```

Levanta la base integrada, COREDB y el Bus, crea `admin` y `svc-seguridad` con los scripts de
arranque de COREDB y corre `seguridad/tests`: las unitarias, con un COREDB en memoria
(`tests/coredb_simulado.py`: evaluación y desafío, cadena de sellos y alteraciones, tokens,
COREDB caído, que el módulo no importe ningún almacenamiento), y las de integración contra el
COREDB real por el Bus. `./bna test` la corre como «Seguridad contra COREDB y MySQL».

## Fuera del producto

Con un COREDB y un Bus ya corriendo, desde `backend/` y Python 3.11:

```bash
python3 -m venv ../.venv-seguridad
../.venv-seguridad/bin/pip install -r requirements-seguridad.txt
cp seguridad/.env.example .env.seguridad.local   # completar la clave, el secreto y BUS_TOKEN
seguridad/run_local.sh
```

## Qué cambió (antes: prototipo sobre SQLite)

| Antes | Ahora |
|---|---|
| Usuarios propios (Argon2, roles CLIENTE/OPERADOR/AUDITOR/ADMINISTRADOR), `manage create-user` | Usuarios de COREDB y sus acciones (`COREDB/permisos.py`); no hay CLIENTE |
| Bloqueo a los 3 fallos | El de COREDB: 5 fallos, 15 minutos (decisión 15) |
| JWT propio y `logout` que revocaba sesiones | El token de COREDB; no hay revocación de sesiones en COREDB |
| Topes propios (ATM 1000, HB 5000, BILLETERA 500) y acumulado de decisiones | Topes reales de `core.limite_canal` y consumo real del día |
| `operation_id` libre, moneda en la petición | `uuid_operacion` y `num_cuenta`; la moneda es la de la cuenta |
| Rechazos con 403/401 | Decisión en el cuerpo (200); 401/403 solo para sesión y permisos |
| Bitácora propia firmada con HMAC por evento | Sellos HMAC encadenados de la bitácora general de COREDB |
| `manage backup` (SQLite) | Respaldo de la base integrada |

## Pendientes

Segundo factor por un canal independiente (SMS, aplicación), RENIEC/biometría, HSM para la
clave, SIEM, TLS/mTLS en el Bus, revocación de sesiones en COREDB, que los canales (ATM, Home
Banking, Billetera) llamen a la evaluación antes de debitar, y anclar los sellos fuera de la
base. No se afirma cumplimiento SBS/PCI.
