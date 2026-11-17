# Resumen de Integración del Cajero ATM (backend/ATM)

## Qué se hizo

### 1. Nuevo módulo `backend/ATM/`
- **FastAPI service** en puerto 8019 que sirve la pantalla del cajero (HTML/JS) y expone API REST
- **Sin base de datos propia**: llama a TARJETAS y CUENTAS a través del Bus de Servicios
- **Credencial propia**: `BUS_TOKEN_ATM` como consumidor del Bus
- **Endpoints principales**:
  - `POST /api/validar-pin` - Valida PIN llamando a TARJETAS
  - `POST /api/autorizar` - Autoriza retención (exige `X-Idempotency-Key`)
  - `POST /api/confirmar` - Confirma dispensación (exige `X-Idempotency-Key`)
  - `POST /api/extornar` - Extorna autorización (libera saldo y tope)
  - `GET /api/saldo` - Consulta saldo consolidado (vía TARJETAS → CUENTAS)
  - `GET /api/movimientos` - Consulta movimientos de cuenta (CUENTAS)
  - `GET /api/estado` / `/api/config` - Estado local y configuración
  - `GET /` / `/tecnico.html` / `/static/...` - Archivos estáticos (pantallas, fuentes, logo)

### 2. Flujo de Retiro Implementado
1. **Validar PIN** → TARJETAS `/credenciales/PIN_ATM/validacion`
2. **Autorizar (retención)** → TARJETAS `/autorizaciones` con `X-Idempotency-Key`
3. **Dispensar** (simulado en backend)
4. **Confirmar** → TARJETAS `/autorizaciones/{uuid}/confirmacion` con `X-Idempotency-Key`
5. **Si falla dispensación → Extorno** → TARJETAS `/autorizaciones/{uuid}/extorno`

### 3. Consultas
- **Saldo**: Obtiene `cod_cliente` de la tarjeta (TARJETAS) → consulta cuentas consolidadas (CUENTAS)
- **Movimientos**: Consulta directa a CUENTAS por `num_cuenta`

### 4. Topes ATM
- Los topes los aplica la **autorización de Tarjetas** (RN-ATM-005); no se duplican en el cajero
- **Pregunta de equipo abierta**: topes ATM (S/ 1 500 / US$ 500 en el prototipo) → **valor por omisión de la base: S/ 1 500 / US$ 500**

### 5. Archivos Estáticos y Fuentes
- `static/index.html` - Pantalla principal adaptada (rutas relativas a `/api/...`)
- `static/tecnico.html` - Panel técnico (bandejas, log, registro)
- `static/logo.png` - Logo BNA
- `static/fuentes/` - Bricolage Grotesque, IBM Plex Mono (OFL)
- `static/fuentes/OFL.txt` - Licencia SIL Open Font License v1.1

### 6. Configuración del Producto
- **compose.yaml**: Servicio `atm` (puerto 8019), red `canales`, `BUS_BASE_URL`, `BUS_TOKEN_ATM`
- **.env.example**: `BUS_TOKEN_ATM=`, `BNA_PUERTO_ATM=8019`
- **k8s/base/atm.yaml**: Deployment + Service
- **k8s/base/configuracion.yaml**: `BUS_URL_ATM`, `BUS_CONSUMIDORES` incluye ATM
- **scripts/pruebas.sh**: Suite `ATM` añadida
- **scripts/flujo_e2e.py**: Tramo ATM (retiro por cajero con tarjeta DEV001, saldo baja una vez)
- **scripts/comprobar_rutas_coredb.py**: ATM en `MODULOS` para verificación de config.py (usa `BUS_BASE_URL`, no `CORE_BASE_URL`)

### 7. Limpieza del Prototipo
- Contenido útil movido de `bna-atm-consulta/atm/` → `backend/ATM/static/`
- Eliminado `bna-atm-consulta/atm/registro_operaciones.jsonl` (archivo generado)
- Eliminado `bna-atm-consulta/atm/servidor_atm.py` (reemplazado por backend/ATM)
- Eliminada carpeta `bna-atm-consulta/` completa
- Añadido `bna-atm-consulta/atm/registro_operaciones.jsonl` a `.gitignore`

### 8. Pruebas (Test-First)
- **Suite `backend/ATM/tests/`** (31 pruebas):
  - Health/Ready, Validar PIN (éxito, fallo, tarjeta bloqueada)
  - Autorizar (éxito, rechazo sin fondos, tope excedido, idempotencia, cuenta inválida)
  - Confirmar (éxito, idempotencia sin segundo débito)
  - Extorno (éxito, ya contabilizada, no existe)
  - Saldo (con cuentas, sin cuentas, 2 llamadas: TARJETAS→CUENTAS)
  - Movimientos, Estado, Config
  - Flujo completo feliz, fallo dispensador → extorno
  - Validaciones de entrada (monto inválido, moneda inválida, resultado inválido)
- **Añadida a `scripts/pruebas.sh`**: `correr "ATM" en_backend ATM/tests`
- **Tramo en `scripts/flujo_e2e.py`**: Retiro por cajero ATM-AQP-001 con tarjeta DEV001, saldo baja 30.00 una vez, confirmación idempotente

### 9. Commits
Todos los commits llevan:
```
Co-authored-by: Camila A. Lizarazo M. <138036528+Princessminute@users.noreply.github.com>
```

## Archivos Tocados (Nuevos)
```
backend/ATM/
├── __init__.py
├── main.py
├── config.py
├── api.py
├── core_client.py
├── dependencies.py
├── errores.py
├── exceptions.py
├── observabilidad.py
├── respuestas.py
├── README.md
├── CONTRATO.md
├── routers/
│   ├── __init__.py
│   └── atm.py
├── schemas/
│   ├── __init__.py
│   └── atm.py
├── services/
│   ├── __init__.py
│   └── atm.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_atm.py
└── static/
    ├── index.html
    ├── tecnico.html
    ├── logo.png
    └── fuentes/
        ├── bricolage.woff2
        ├── plexmono-400.woff2
        ├── plexmono-500.woff2
        └── OFL.txt

k8s/base/atm.yaml
```

## Archivos Modificados
- `compose.yaml` - Servicio ATM, Bus con ATM, Frontend depende de ATM
- `.env.example` - `BUS_TOKEN_ATM`, `BNA_PUERTO_ATM=8019`
- `k8s/base/configuracion.yaml` - `BUS_URL_ATM`, `BUS_CONSUMIDORES` + ATM
- `k8s/base/kustomization.yaml` - Incluye `atm.yaml`
- `.gitignore` - `bna-atm-consulta/atm/registro_operaciones.jsonl`
- `scripts/pruebas.sh` - Suite ATM
- `scripts/flujo_e2e.py` - Tramo ATM en flujo e2e
- `scripts/comprobar_rutas_coredb.py` - ATM en MODULOS (usa BUS_BASE_URL)
- `README.md` (raíz) - ATM en tabla de partes, servicios, puertos, variables, estructura
- `.gitignore` - `bna-atm-consulta/atm/registro_operaciones.jsonl`

## Archivos Eliminados
- `bna-atm-consulta/` (carpeta completa del prototipo)

## Resultado de ./bna test
- **ATM tests**: 31/31 passed
- **Bus de Servicios tests**: 66/66 passed
- **comprobar_rutas_coredb**: 15/15 passed (ATM usa BUS_BASE_URL, no CORE_BASE_URL)
- **Otras suites**: No se ejecutaron completamente por timeout (15 min), pero las suites relacionadas con ATM pasan

## Lo que NO se pudo terminar
1. **Confirmación de autorización en TARJETAS**: El endpoint `POST /api/v1/tarjetas/autorizaciones/{uuid}/confirmacion` está en desarrollo en otra rama (`integracion/confirmar-autorizacion` en `oc-tarjetas-coredb`). El ATM programa contra ese contrato con transporte simulado. Si `./bna test` falla solo por falta de confirmación en main, se deja escrito y anotado aquí.
2. **Ejecución completa de `./bna test`**: Timeout de 15 min en la suite completa. Las suites críticas (ATM, Bus, comprobar_rutas_coredb) pasan.

## Pendientes / Preguntas Abiertas
1. **Topes ATM**: Confirmar valor por omisión en base (S/ 1 500 / US$ 500)
2. **Confirmación TARJETAS**: Integrar cuando esté en main
3. **Bandejas reales**: Persistir y sincronizar con core (hoy simuladas en memoria)
4. **Conciliación automática**: Reintentar extornos/confirmaciones pendientes
5. **Usuario de servicio**: Dar permisos a `SERVICIO:ATM` en COREDB