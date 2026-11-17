# ATM — Módulo Cajero Automático

Módulo de cajero automático del BNA. Sirve la pantalla del cajero (HTML/JS) y expone la API para
orquestar retiros: validar PIN → autorizar (retención) → dispensar → confirmar (idempotente) /
extorno si falla. Consultas de saldo y movimientos.

No tiene base de datos propia: llama a **TARJETAS** y **CUENTAS** a través del **Bus de Servicios**
con su credencial `BUS_TOKEN_ATM`.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Salud del servicio |
| GET | `/ready` | Listo si TARJETAS y CUENTAS responden por el Bus |
| GET | `/` | Pantalla principal del cajero (HTML) |
| GET | `/tecnico.html` | Panel técnico (HTML) |
| GET | `/static/...` | Archivos estáticos (fuentes, logo) |
| POST | `/api/validar-pin` | Validar PIN (llama a TARJETAS) |
| POST | `/api/autorizar` | Autorizar retención (llama a TARJETAS, exige `X-Idempotency-Key`) |
| POST | `/api/confirmar` | Confirmar dispensación (llama a TARJETAS, exige `X-Idempotency-Key`) |
| POST | `/api/extornar` | Extornar autorización (llama a TARJETAS) |
| GET | `/api/saldo` | Consultar saldo consolidado (llama a CUENTAS) |
| GET | `/api/movimientos` | Consultar movimientos de una cuenta (llama a CUENTAS) |
| GET | `/api/estado` | Estado local del cajero (bandejas, pendientes) |
| GET | `/api/config` | Configuración (id_cajero, modo pruebas) |
| POST | `/api/registrar` | Recibe eventos del frontend para el log del canal |
| GET | `/api/registro` | Devuelve últimas N líneas del registro de operaciones |

## Flujo de Retiro

1. **Validar PIN**: `POST /api/validar-pin` con `{id_tarjeta, pin, id_terminal}`
   → llama a `TARJETAS: POST /api/v1/tarjetas/{id}/credenciales/PIN_ATM/validacion`

2. **Autorizar (retención)**: `POST /api/autorizar` con `{id_tarjeta, num_cuenta, moneda, monto, id_terminal, uuid_transaccion}` + `X-Idempotency-Key`
   → llama a `TARJETAS: POST /api/v1/tarjetas/{id}/autorizaciones` (retiene saldo y tope diario)

3. **Dispensar**: el cajero físico entrega los billetes (simulado en el backend)

4. **Confirmar**: `POST /api/confirmar` con `{uuid_autorizacion, id_terminal, resultado: "DISPENSADO"}` + `X-Idempotency-Key`
   → llama a `TARJETAS: POST /api/v1/tarjetas/autorizaciones/{uuid}/confirmacion`
   → respuesta: autorización en estado `DISPENSADA` con `uuid_transaccion`

5. **Si falla dispensación → Extorno**: `POST /api/extornar` con `{uuid_autorizacion, motivo}`
   → llama a `TARJETAS: POST /api/v1/tarjetas/autorizaciones/{uuid}/extorno`
   → libera saldo retenido y tope (RN-ATM-003)

## Consultas

- **Saldo**: `GET /api/saldo?id_tarjeta=...` → obtiene `cod_cliente` de la tarjeta (TARJETAS) y consulta cuentas consolidadas (CUENTAS)
- **Movimientos**: `GET /api/movimientos?num_cuenta=...` → llama a CUENTAS

## Topes ATM

Los topes de retiro por canal los aplica la **autorización de Tarjetas** (RN-ATM-005); el cajero no los duplica.

> **Pregunta de equipo abierta**: topes ATM (S/ 1 500 / US$ 500 en el prototipo) → valor por omisión de la base: **S/ 1 500 / US$ 500**.

## Autenticación y Bus

- Todas las llamadas a TARJETAS/CUENTAS van por el Bus: `http://bus:8018/bus/tarjetas/...`, `http://bus:8018/bus/cuentas/...`
- El ATM presenta su credencial `X-Bus-Token: ${BUS_TOKEN_ATM}` en cada llamada.
- El token de autorización del usuario (`Authorization: Bearer ...`) se reenvía a TARJETAS/CUENTAS.

## Configuración

Variables de entorno (`.env`):

| Variable | Descripción | Ejemplo |
|---|---|---|
| `BUS_BASE_URL` | Raíz del Bus de Servicios (sin `/bus`) | `http://bus:8018` |
| `BUS_TOKEN` | Credencial ante el Bus | (generado por `./bna up`) |
| `ATM_ID` | Identificador del cajero | `ATM-AQP-001` |
| `PRUEBAS` | Modo pruebas (simular fallos) | `false` |

## Puertos

- Contenedor: 8019
- Host (compose): `${BNA_PUERTO_ATM:-8019}`

## Ejecutar

Con Docker Compose (parte del producto):

```bash
./bna up
# Pantalla: http://localhost:8019
# Panel técnico: http://localhost:8019/tecnico.html
# API docs: http://localhost:8019/docs
```

Solo el módulo (requiere Bus, TARJETAS, CUENTAS):

```bash
cd backend/ATM
uvicorn ATM.main:app --port 8019
```

## Pruebas

```bash
# Unitarias (con transporte simulado)
cd backend/ATM
python -m pytest ATM/tests -v

# Desde la raíz del repo (en contenedor)
./bna test
# Incluye: correr "ATM" en_backend ATM/tests
```

## Archivos Estáticos

- `static/index.html` — Pantalla principal del cajero
- `static/tecnico.html` — Panel técnico (bandejas, log, registro)
- `static/logo.png` — Logo BNA
- `static/fuentes/` — Fuentes OFL (Bricolage Grotesque, IBM Plex Mono)
- `static/fuentes/OFL.txt` — Licencia SIL Open Font License v1.1

## Kubernetes

Deployment + Service en `k8s/base/atm.yaml`. Se despliega con `./bna k8s-up`.

## Contrato

Ver [`CONTRATO.md`](CONTRATO.md) para la especificación completa de la API, errores, idempotencia y permisos.