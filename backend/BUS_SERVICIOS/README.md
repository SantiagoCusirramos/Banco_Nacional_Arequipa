# Bus de Servicios

Punto único por el que los canales llegan a los módulos del producto y los módulos llegan a COREDB, como pide [`Documents/01-stack-tecnologico.md`](../../Documents/01-stack-tecnologico.md) («Módulos de negocio → CORE: REST interno vía Bus»). Lo usan los puentes del frontend, el flujo de extremo a extremo y cada módulo que llama a COREDB (CUENTAS, TARJETAS, CAPTACION, Evaluación y Desembolso; fase 2), cada uno con su credencial.

Parte del aporte de Gabriel Tapia (PR #91): la idea de un Bus con credencial por consumidor y el reenvío de `Authorization` y de la llave de idempotencia.

## Qué hace

`/bus/<módulo>/<ruta>` se reenvía a `<URL del módulo>/<ruta>`. Hay una ruta por módulo:

| Ruta del Bus | Módulo | Variable con su dirección |
|---|---|---|
| `/bus/coredb/...` | COREDB | `BUS_URL_COREDB` |
| `/bus/cuentas/...` | CUENTAS | `BUS_URL_CUENTAS` |
| `/bus/tarjetas/...` | TARJETAS | `BUS_URL_TARJETAS` |
| `/bus/captacion/...` | CAPTACION | `BUS_URL_CAPTACION` |
| `/bus/sol/...` | SOL | `BUS_URL_SOL` |
| `/bus/evaluacion/...` | EVALUACIÓN | `BUS_URL_EVALUACION` |
| `/bus/desembolso/...` | DESEMBOLSO | `BUS_URL_DESEMBOLSO` |
| `/bus/seguridad/...` | Seguridad | `BUS_URL_SEGURIDAD` |

Además, módulos opcionales: solo se publican si su variable tiene valor. En compose, ATM y BILLETERA están siempre; CLIENTES y CORE vienen de `bna-bus-servicios` y viven fuera de este compose:

| Ruta del Bus | Módulo | Variable con su dirección |
|---|---|---|
| `/bus/atm/...` | Cajero ATM: adaptador del canal (`/autenticar`, `/consulta-saldo`, `/retiro`, `/confirmar-dispensacion`, `/extorno`) sobre Cuentas y Tarjetas simulados del prototipo | `BUS_URL_ATM` |
| `/bus/billetera/...` | Billetera Digital Chaski (rutas `/api/...`) | `BUS_URL_BILLETERA` |
| `/bus/clientes/...` | CLIENTES | `BUS_URL_CLIENTES` |
| `/bus/core/...` | CORE (rutas `/interno/...`) | `BUS_URL_CORE` |

Por ejemplo, `GET /bus/cuentas/api/v1/cuentas/001-...` llega a CUENTAS como `GET /api/v1/cuentas/001-...`.

**No toca nada.** Reenvía el método, la ruta y la consulta tal como llegaron (sin decodificar), el cuerpo en bytes y todas las cabeceras: `Authorization`, `X-Idempotency-Key`, `X-Correlation-ID`, cookies, `X-Channel-ID`… No reenvía las de salto a salto (`Connection`, `Transfer-Encoding`…), `Host` ni su propia credencial. No agrega ninguna: si no llega `X-Correlation-ID`, no la inventa. De vuelta entrega el código, las cabeceras (también varias `Set-Cookie`) y el cuerpo del módulo tal como llegaron, comprimido si venía comprimido. No sigue redirecciones.

**Nunca reintenta.** Un POST repetido lo resuelve el módulo con su `X-Idempotency-Key`: el Bus entrega cada petición una sola vez.

**Lo único que responde por su cuenta** (cuerpo `{"detail", "codigo", "modulo"}`, con la `X-Correlation-ID` de la petición si vino):

| Código | `codigo` | Cuándo |
|---|---|---|
| 401 | `BUS_CREDENCIAL_INVALIDA` | Falta `X-Bus-Token` o no es de ningún consumidor. No reenvía nada |
| 403 | `BUS_CONSUMIDOR_NO_AUTORIZADO` | El módulo tiene `BUS_PERMITIDOS_<MÓDULO>` y el consumidor no está. No reenvía nada |
| 404 | `MODULO_DESCONOCIDO` | El módulo no está en la tabla |
| 503 | `MODULO_NO_DISPONIBLE` | El módulo no acepta la conexión (caído) |
| 504 | `MODULO_SIN_RESPUESTA` | El módulo no responde en `BUS_TIMEOUT_SEG` |
| 502 | `MODULO_RESPUESTA_INVALIDA` | El módulo cortó la respuesta a medias |

Para ver qué módulos están integrados:

- `GET /docs`: el Swagger del Bus muestra una sección por módulo con **sus rutas reales**, leídas en vivo del `/openapi.json` de cada uno y publicadas bajo `/bus/<módulo>`. Con **Authorize** se presenta `X-Bus-Token` (y, si el módulo la pide, su propia credencial, como el bearer de COREDB). Un módulo que no publica su OpenAPI aparece como «NO DISPONIBLE».
- `GET /modulos` (con credencial): contacta cada módulo y responde `DISPONIBLE` (con milisegundos) o `NO_DISPONIBLE` (con el motivo), y cuántos contestan del total.

Además: `GET /salud` (sin credencial, no depende de los módulos) y `GET /metricas` (con credencial): cuántas peticiones reenvió por consumidor y módulo desde que arrancó. El flujo de extremo a extremo la usa para comprobar que todo pasó por el Bus.

En el registro escribe una línea por petición: consumidor, método, módulo, código, milisegundos y correlación. Nunca el cuerpo, la consulta ni las cabeceras.

## Configuración

Sin valores por omisión para direcciones ni credenciales: si falta algo, no arranca y el error nombra cada variable que falta.

| Variable | Qué es |
|---|---|
| `BUS_URL_<MÓDULO>` | Dirección de cada módulo de la tabla, `http(s)://host:puerto[/prefijo]`, sin credenciales ni consulta. Las ocho son obligatorias |
| `BUS_CONSUMIDORES` | Nombres de los consumidores, separados por comas (mayúsculas, dígitos y `_`). En el producto: `FRONTEND,PRUEBAS,CUENTAS,TARJETAS,CAPTACION,EVALUACION,DESEMBOLSO,ATM` (ATM es la pantalla del cajero) |
| `BUS_TOKEN_<CONSUMIDOR>` | Credencial de cada consumidor, que presenta en `X-Bus-Token`. Al menos 32 caracteres, distinta de las demás. `./bna up` las genera en `.env` (`BUS_TOKEN_FRONTEND`, `BUS_TOKEN_PRUEBAS`, una por módulo: `BUS_TOKEN_CUENTAS`…, y `BUS_TOKEN_ATM`) |
| `BUS_CONSUMIDORES_EXTRA` | Opcional. Consumidores que se suman a `BUS_CONSUMIDORES` sin reemplazarla (por ejemplo `CLIENTES`, del stack de clientes) |
| `BUS_URL_CLIENTES`, `BUS_URL_CORE`, `BUS_URL_BILLETERA` | Opcionales. Vacías, el módulo no se publica |
| `BUS_CREDENCIAL_<MÓDULO>` | Opcional. Credencial que el Bus presenta al módulo en `X-Service-Token` (al menos 32 caracteres). La que traiga el consumidor se descarta. Sin ella, `X-Service-Token` pasa tal cual |
| `BUS_PERMITIDOS_<MÓDULO>` | Opcional. Consumidores (de `BUS_CONSUMIDORES`) que pueden usar ese módulo. Sin ella, todos |
| `BUS_MODULOS_PUBLICOS` | Opcional. Módulos a los que se llega sin `X-Bus-Token`, como consumidor `PUBLICO` (en compose: `BILLETERA`, para la app móvil, que no puede guardar un secreto, y `SEGURIDAD`, para su consola en http://127.0.0.1:8018/bus/seguridad/; los dos autentican a sus usuarios). Una credencial presente pero inválida sigue siendo 401 |
| `BUS_TIMEOUT_SEG` | Segundos que espera la respuesta de un módulo. Por omisión 9, menos que los 10 del puente del frontend, para que el navegador vea el 504 del Bus |
| `BUS_TIMEOUT_CONEXION_SEG` | Segundos para conectar con un módulo. Por omisión 2 |

En compose el Bus escucha en el 8018 (`BNA_PUERTO_BUS`) y está en tres redes: la de los módulos, `canales` (solo con el frontend) y `core` (solo con COREDB, su base y `coredb-init`). Así ni el frontend ve los módulos ni los módulos ven COREDB. En kind, NodePort 30018 → `127.0.0.1:18018`; el Bus es el único que lee el ConfigMap `bna-bus`, el de las direcciones de los módulos.

Cada módulo que llama a COREDB tiene `CORE_BASE_URL` o `COREDB_URL` = `http://bus:8018/bus/coredb` y presenta `BUS_TOKEN` (en compose y k8s, su `BUS_TOKEN_<MÓDULO>`) en cada llamada, también en sus sondas y en los contenedores de arranque de k8s. Sus clientes de COREDB tienen un tiempo de espera de 5 s, menos que los 9 del Bus: si COREDB no responde, el módulo da su propio error, igual que antes. `scripts/comprobar_rutas_coredb.py` (en `./bna test`) falla si algún módulo tiene la dirección directa de COREDB.

El frontend presenta `BUS_TOKEN` (en compose y k8s, el valor de `BUS_TOKEN_FRONTEND`) desde su servidor; nunca reenvía una `X-Bus-Token` del navegador. Sin `BUS_TOKEN` no la envía, para poder apuntar directo a los módulos con `npm run dev`.

## Pruebas

```bash
./bna test     # incluye la suite "Bus de Servicios"
# o solo esta suite, con la imagen del backend ya construida:
docker run --rm bna/backend:local python -m pytest -q -o addopts= BUS_SERVICIOS/tests
```

`tests/test_bus.py` simula los módulos con `httpx.MockTransport` para ver exactamente lo que les llega, y usa sockets reales para un módulo caído, uno que no responde y un recorrido completo con uvicorn delante y un servidor HTTP detrás. Comprueba: configuración obligatoria; credencial; una ruta por módulo; cabeceras, cuerpo, ruta y consulta iguales en los dos sentidos; errores del módulo con su código y su cuerpo; idempotencia sin reintentos; 503 y 504 claros sin colgar; métricas.

El flujo de `./bna smoke` corre en el contenedor del Bus y solo conoce el Bus y el frontend. Al terminar comprueba con `/metricas` que cada módulo llegó a COREDB a través del Bus. Las suites de integración de CAPTACION, Evaluación y Desembolso levantan un Bus de pruebas delante de su COREDB (`scripts/bus_de_pruebas.sh`) y hacen la misma comprobación.

## Migración desde `bna-bus-servicios`

El Bus anterior publicaba rutas fijas con `X-Service-Token` como credencial del consumidor. Aquí la credencial es `X-Bus-Token` y la ruta es la del módulo tal cual:

| Antes | Ahora |
|---|---|
| `POST /bus/clientes/registrar` | `POST /bus/clientes/clientes/registrar` |
| `POST /bus/clientes/validar-documento` | `POST /bus/clientes/clientes/validar-documento` |
| `POST /bus/core/registrar-cliente` | `POST /bus/core/interno/registrar-cliente` |
| `GET /bus/core/solicitudes-registro` | `GET /bus/core/interno/solicitudes-registro` |
| `POST /bus/cuentas/deposito` | `POST /bus/cuentas/api/v1/cuentas/deposito` |
| `GET /bus/atm/consulta-saldo/{cuenta}` | `GET /bus/cuentas/api/v1/cuentas/{cuenta}` |
| `/bus/seguridad/<ruta>` | `/bus/seguridad/seguridad/<ruta>` |
| `/api/<módulo>/...` con `X-API-Key` | `/bus/<módulo>/...` con `X-Bus-Token` |

Equivalencias de configuración: `CLIENTES_TOKEN` → `BUS_CREDENCIAL_CLIENTES`, `CORE_TOKEN` → `BUS_CREDENCIAL_CORE`, `BUS_CORE_TOKEN` (solo CLIENTES llega a CORE) → consumidor `CLIENTES` con `BUS_TOKEN_CLIENTES` y `BUS_PERMITIDOS_CORE=CLIENTES`.
