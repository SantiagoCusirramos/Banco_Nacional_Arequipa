# Frontend

Banca personal del BNA en [Next.js](https://nextjs.org) 16 (App Router) con React 19 y TypeScript.

## Pantallas

| Ruta | Qué es | De dónde salen los datos |
|---|---|---|
| `/login` | Inicio de sesión. El formulario de registro de usuarios solo funciona con una sesión que tenga el permiso `CREAR_USUARIO` | COREDB (`/coredb/auth/login`, `/coredb/usuarios`) |
| `/` | Banca personal (portada). Exige una sesión vigente | Saluda al usuario por nombre. Menú con enlaces a 7 pantallas reales + Home Banking. "Crear cuenta" y "Modificar cuenta" usan CUENTAS y COREDB. |
| `/cuenta` | Módulo de cuentas: abrir, consultar, depositar, retirar, transferir y ver movimientos | CUENTAS |
| `/tarjetas` | Módulo de tarjetas, para el personal: tarjetas de un cliente, consulta, emisión, bloqueo y cambio de estado | TARJETAS |
| `/evaluacion` | Evaluación de créditos: expedientes, reglas, decisiones | EVALUACION |
| `/desembolso` | Desembolso: identidad, órdenes, validación, confirmación | DESEMBOLSO |
| `/captacion` | Captación: prospectos, consentimientos, OTP, validaciones, habilitación | CAPTACION |
| `/solicitud-credito` | Solicitud de crédito (asesor) | SOL |
| `/pagar-cuota` | Pago de cuotas de crédito (CR-INT-08): créditos de un cliente, monto a pagar hoy, pago desde una cuenta de ahorros y su resultado | COBRANZA, con las cuentas del cliente desde CUENTAS |
| `/homebanking/index.html` | Home Banking estático (prototipo HTML+JS) | Servido por Next.js desde `public/`. Usa puentes `/api/*`. |

El cambio de estado de una cuenta se muestra deshabilitado: falta decidir los estados y quién los cambia, y COREDB no ofrece esa operación (`MODIFICAR_CUENTA`, issue #116).

## Cómo llega a los servicios

El navegador solo llama a rutas de este mismo servidor, que las reenvía desde el lado servidor (`lib/proxy.ts`). Así el navegador nunca conoce la dirección de un servicio.

| Ruta del frontend | Reenvía a | Variable |
|---|---|---|
| `/api/core/coredb/*` | COREDB, `/coredb/*` | `COREDB_URL` |
| `/api/cuenta/*` | CUENTAS, `/api/v1/cuentas/*` | `CUENTAS_GATEWAY_URL` |
| `/api/tarjeta/*` | TARJETAS, `/api/v1/tarjetas/*` | `TARJETAS_GATEWAY_URL` |
| `/api/captacion/*` | CAPTACION, `/api/v1/captacion/*` | `CAPTACION_GATEWAY_URL` |
| `/api/solicitud-credito/*` | SOL, `/sol/*` (login con el usuario de COREDB) | `SOL_GATEWAY_URL` |
| `/api/evaluacion/*` | EVALUACIÓN, `/eva/v1/*` | `EVALUACION_GATEWAY_URL` |
| `/api/desembolso/*` | DESEMBOLSO, `/api/v1/*` | `DESEMBOLSO_GATEWAY_URL` |
| `/api/cobranza/*` | COBRANZA | `COBRANZA_GATEWAY_URL` |
| `/api/seguridad/*` | Seguridad, solo `auth/me`, `tarjetas`, `tarjetas/{id}` y `POST tarjetas/{id}/desbloqueo` (pantalla `/tarjetas/desbloqueo`); lo demás responde 404 | `SEGURIDAD_GATEWAY_URL` |

En el producto, todas las variables apuntan al Bus de Servicios (`http://bus:8018/bus/<módulo>/...`, ver `compose.yaml`) y el servidor agrega `X-Bus-Token` con `BUS_TOKEN`.

`GET /api/config-publica` (sin sesión, `Cache-Control: no-store`) publica `BNA_URL_BILLETERA`, `BNA_URL_CAJERO` y `BNA_URL_APK` como `urlBilletera`, `urlCajero` y `urlApk`: solo http(s) sin credenciales y vacío o inválido → `null`. La app Chaski lo usa para conectarse y descargar el APK; los QR de `/billetera` se generan en el navegador con `qrcode`.

Las variables se leen al ejecutar, no al construir. De cada petición se reenvían `Authorization`, `X-Idempotency-Key`, `X-Channel-ID` y `X-Request-Timestamp`; si falta `X-Correlation-ID`, se genera uno. La sesión de COREDB (el token) se guarda en `localStorage` con clave `bna_access_token`; la de SOL, en una cookie que maneja su propio puente.

Cobranza funciona igual que los demás: el puente `/api/cobranza` reenvía el bearer token de COREDB y `X-Bus-Token`; sin claves propias.

## Home Banking (prototipo estático)

El prototipo de Home Banking de Tamara-Martinez (commit c73fa20, issue #100) estaba en `app/homebanking/`, donde Next no lo servía, y llamaba a 14 rutas `/bus/v1/...` que no existen, con datos simulados en `js/datos.js`. Ahora está en `public/homebanking/` y se abre en `/homebanking/index.html`.

- **Acceso:** no hay login de clientes. Entra un usuario del banco con su clave de COREDB e indica el código del cliente que atiende (decisión 14 de [`Documents/decisiones-del-equipo.md`](../Documents/decisiones-del-equipo.md), revisable). El token queda en `localStorage` (`bna_access_token`), como en el resto del frontend.
- **Rutas que usa** (`js/bus.js`, solo puentes de `app/api/`):
  - `POST /api/core/coredb/auth/login`, `GET /api/core/coredb/auth/me`; auditoría: `GET /api/core/coredb/auditoria` (administrador).
  - Cuentas: `GET /api/cuenta/consolidada/{codCliente}`, `GET /api/cuenta/{numCuenta}`, `GET /api/cuenta/{numCuenta}/movimientos`, `GET /api/cuenta/{numCuenta}/destino` (titular enmascarado antes de transferir), `POST /api/cuenta/transferencia` (canal `WEB`, que CUENTAS registra como Home Banking `HB`: COREDB aplica su tope diario).
  - Tarjetas: `GET /api/tarjeta/cliente/{codCliente}`; «Bloquear» en `cuentas.html` (solo tarjetas ACTIVA, tras confirmar): `POST /api/tarjeta/{idTarjeta}/bloqueo` con un motivo. El desbloqueo no se hace en el Home Banking (TARJETAS responde 403; lo hace Seguridad).
  - Créditos: `GET /api/cobranza/clientes/{codCliente}/creditos`, `GET /api/cobranza/creditos/{codCredito}/monto-a-pagar`, `POST /api/cobranza/cr-int-08/pagos`.
- **Dinero:** la transferencia y el pago de cuota llevan una llave por operación (`X-Idempotency-Key`; en el pago, `referenciaTransaccion`). Se conserva si se reintenta tras un error o un timeout y cambia al editar los datos o cuando la operación se registra o cuando el banco la rechaza.
- **Pago de cuota** (`creditos.html`, `js/confirmacion.js`): «Revisar y pagar» no cobra; abre un resumen (monto, cuota desde la que se aplica, crédito y cuenta de origen) con «Cancelar» y un código de 6 dígitos. **El código es una simulación** (se muestra en la misma pantalla y el servidor no lo verifica: no hay proveedor de segundo factor ni acceso de clientes), pero si no coincide el pago no se envía y al tercer error se cancela. El botón queda deshabilitado mientras se procesa. El comprobante muestra solo lo que devuelve COBRANZA (monto, cuota pagada, cuenta, saldo del crédito, cuotas pendientes) y el saldo de la cuenta releído de CUENTAS; si falta un dato o el monto no coincide, error con el número de operación y sin comprobante.
- **Transferencias** (`transferencias.html`, mismo `js/confirmacion.js`): entre cuentas propias o a otra cuenta BNA de la misma moneda. «Revisar y transferir» consulta la cuenta de destino (si no existe, no está activa o es de otra moneda, lo dice y no envía nada) y abre un resumen (monto, cuenta de origen y de destino, titular de destino enmascarado) con «Cancelar» y el mismo código **simulado**. El comprobante muestra solo lo que devuelve CUENTAS (monto, cuentas, titular, saldo de la cuenta de origen, fecha y número de operación; en una transferencia entre cuentas propias, también el saldo de la de destino releído de CUENTAS); si falta un dato o el monto o las cuentas no coinciden, error con el número de operación y sin comprobante. Un rechazo (saldo, tope diario, cuenta no operativa) se explica en texto llano.
- **Fuera de esta versión** (no hacen ninguna petición): Token Matriz real (en el pago de cuota y en la transferencia hay un código simulado), evaluación de riesgo, transferencias interbancarias (la pestaña se quitó) y constancias PDF. El tope diario lo aplica COREDB al canal Home Banking; la pantalla no lo repite. La consola del Bus en pantalla, los datos de prueba de la entrada y los avisos de «modo local» se quitaron.
- Pruebas: `__tests__/homebanking.test.ts`, `__tests__/homebanking-bloqueo.test.ts` (la página de cuentas en jsdom) `__tests__/homebanking-pago-credito.test.ts` (la página de créditos en jsdom: cancelar, código, doble clic, reintento, comprobante) y `__tests__/homebanking-transferencias.test.ts` (lo mismo en transferencias, más destino inexistente y rechazo); el flujo de extremo a extremo pide `/homebanking/index.html`, bloquea una tarjeta con la misma petición que el botón, paga una cuota y hace una transferencia por los puentes, cada una con dos envíos simultáneos y un reintento con la misma llave (un solo débito y, en la transferencia, un solo abono).

## Ejecutar

Con todo el producto, desde la raíz del repositorio: `./bna up`. El frontend queda en http://localhost:3000 y se entra con `admin` y la contraseña de `BNA_ADMIN_PASSWORD` en `.env`.

Para desarrollar con recarga en vivo hace falta Node.js 20.9 o superior (la imagen usa Node 22) y los servicios levantados:

```bash
./bna up                          # en la raíz: deja cada servicio en su puerto de 127.0.0.1
cd frontend
cat .env.example .env.sol.example > .env.local
npm ci
npm run dev -- --port 3001        # el 3000 lo ocupa el frontend del producto
```

`.env.local` no se versiona. Sus valores apuntan directo a los puertos de `./bna up`, sin pasar por el Bus (sin `BUS_TOKEN` el servidor no envía `X-Bus-Token`).

## Pruebas

```bash
npm run lint
npm test          # Vitest con Testing Library
npm run build
```

Sin Node en la máquina, `./bna test` desde la raíz corre el lint y las pruebas en un contenedor.

## Notas

- `AGENTS.md` y `CLAUDE.md` los genera `next dev`. Piden leer la documentación incluida en `node_modules/next/dist/docs/` antes de escribir código, porque esta versión de Next.js cambia API y convenciones.
- La imagen del producto se construye con [`docker/frontend/Dockerfile`](../docker/frontend/Dockerfile).
- Prototipo Home Banking original de Tamara-Martinez (ID 203461599).