# Chaski — Billetera Digital BNA (app móvil Flutter + API sobre COREDB)

📄 Documentación del prototipo original: [docs/Documentacion_Chaski.pdf](docs/Documentacion_Chaski.pdf)
(describe la versión con PostgreSQL propio; la integración al producto cambió el backend, ver abajo).

Versión móvil de Chaski, hecha en **Flutter**, alineada con la Fase I TOGAF del módulo
Billetera Digital (RF-BD-001 a RF-BD-009). Trabajo de RoBeRaMe, recuperado en el PR #94 e
integrado al producto: la API ya no tiene base propia y opera sobre la base integrada.

```
billetera-chaski/
├── backend/          API REST/JSON (Node.js + Express) para la app, sobre COREDB por el Bus
│   ├── server.js        endpoints /api/* (las mismas rutas que usa la app)
│   ├── coredb.js        cliente de COREDB a través del Bus de Servicios
│   └── test/            pruebas de la API contra un COREDB falso (npm test)
└── app_movil/        app Flutter (Android Studio)
    └── lib/              pantallas, estado, caché SQLite local y autorización con huella/PIN
```

## Arquitectura (integrada al producto)

```
App Flutter ──REST/JSON──► API Chaski (Express, puerto 8020) ──► Bus de Servicios ──► COREDB ──► base integrada
                             sin base propia                       /bus/coredb          /coredb/billetera/*   esquema billetera
```

- **Sin base propia.** Clientes, cuentas, saldos, QR, solicitudes de cobro, operaciones y avisos
  están en la base integrada (esquema `billetera` desde `bd-v1.9-mysql`). Cada envío, pago con QR
  o cobro aceptado es una transferencia del CORE por el canal BD, con su asiento contable y el
  tope diario del canal (S/ 500, `core.limite_canal`).
- **Por el Bus.** Chaski llama a `http://bus:8018/bus/coredb` con su credencial ante el Bus
  (`BUS_TOKEN_BILLETERA`) y el token de su usuario de servicio en COREDB (`svc-billetera`,
  rol SERVICIO, módulo BILLETERA). La app llega a Chaski en el puerto 8020 (o por el Bus,
  `/bus/billetera/api/...`).
- **Acceso del cliente.** `POST /api/login` (celular y PIN de 6 dígitos) lo valida COREDB
  (`POST /coredb/billetera/acceso`), que cuenta los intentos (al tercero la billetera queda
  bloqueada) y entrega un **token de cliente** (rol CLIENTE). Ese token es la sesión de la app:
  Chaski lo reenvía en `X-Cliente-Token` y COREDB identifica al cliente por él, nunca por lo
  que diga Chaski. Chaski no firma ni guarda nada.
- **Los clientes no los crea Chaski (punto R-01).** Los registra el módulo Clientes (hoy,
  CAPTACION) y un usuario del banco los afilia a la billetera con su cuenta en soles y su PIN
  (`POST /coredb/billetera/afiliaciones`, roles ADMINISTRADOR, ASESOR u OPERADOR); los comercios
  con `POST /coredb/billetera/comercios`. `POST /api/registro` responde 403 y lo explica.
- **Idempotencia (RN-BUS-002).** La app manda su `uuid_transaccion` (cabecera `Idempotency-Key`
  o en el cuerpo) y Chaski lo pasa como `X-Idempotency-Key`: repetir la operación devuelve la
  misma (`repetida: true`) sin cobrar dos veces.
- **El celular nunca en claro.** Ni la bitácora, ni los avisos, ni la glosa de los movimientos,
  ni los errores lo guardan; Chaski no registra cuerpos ni consultas, y a COREDB el celular le
  llega en el cuerpo, nunca en la ruta.

| Requisito | En el producto integrado |
|---|---|
| RF-BD-001 Transferir P2P por celular | `POST /api/transferencias` → `billetera.transferir` |
| RF-BD-002 Solicitar cobro | `POST /api/solicitudes`, `GET /api/solicitudes`, `POST /api/solicitudes/:id/responder`; vence a las 48 h |
| RF-BD-003 Pagar con QR | `POST /api/qr` (fijo o con monto, vence en 15 min y se paga una vez), `GET /api/qr/:id`, `POST /api/qr/:id/pagar`, `GET /api/comercios` |
| Contactos | `POST /api/clientes/buscar` con el celular en el cuerpo: devuelve el nombre corto |
| RF-BD-004 Saldo e historial | `GET /api/me`, `GET /api/movimientos`, `GET /api/operaciones` |
| RF-BD-005 Enrolamiento | Lo hace el banco (afiliación); falta el registro por la app con verificación del celular (OTP) |
| RF-BD-009 Notificaciones | `GET /api/notificaciones`, `POST /api/notificaciones/leidas` |
| RN-TOP-001 / RN-BD-002 Tope S/ 500 | Lo aplica la base: tope diario del canal BD por cuenta |
| Biometría / PIN | Sin biometría, `POST /api/pin/verificar` lo valida COREDB con los mismos intentos |

**Fuera de esta versión** (decisión pendiente del equipo, PR #94): tienda, promociones, cupones,
ofertas, órdenes (RF-BD-007, RF-BD-008), recargas y pago de servicios (RF-BD-006). Las rutas
existen para que la app cargue: las listas vienen vacías y las acciones responden 501.

## Cómo correrlo

### 1. Backend (en el producto)

Con el producto: `./bna up` desde la raíz del repositorio. La API queda en
`http://127.0.0.1:8020` (`GET /api/salud`). Para entrar, un usuario del banco afilia antes a un
cliente (por ejemplo, uno registrado por CAPTACION) con su cuenta en soles y un PIN:

```bash
curl -X POST http://127.0.0.1:8018/bus/coredb/coredb/billetera/afiliaciones \
  -H "X-Bus-Token: $BUS_TOKEN_PRUEBAS" -H "Authorization: Bearer <token de admin>" \
  -H "Content-Type: application/json" -d '{"cod_cliente": "...", "num_cuenta": "...", "pin": "246810"}'
```

Pruebas de la API: `docker run --rm bna/billetera:local npm test` (o la suite «BILLETERA
(Chaski)» de `./bna test`). El flujo de extremo a extremo (`./bna smoke`) recorre un envío por
celular y un pago con QR contra el producto real.

Fuera de compose: `cp .env.example .env`, completar `BUS_TOKEN` y `CHASKI_COREDB_SECRETO` (los
del `.env` del producto), `npm install` y `npm start`.

### 2. App (Android Studio)

1. Instala Flutter (https://docs.flutter.dev/get-started/install/windows) y en Android Studio el plugin **Flutter**.
2. Abre la carpeta `app_movil` en Android Studio.
3. `flutter pub get` (o el botón *Pub get*).
4. Elige el emulador o tu celular y pulsa ▶ Run. Para el APK: `flutter build apk --release`.

En la pantalla de ingreso, el engranaje ⚙ permite cambiar el servidor:

- Emulador de Android: `http://10.0.2.2:8020` con el producto levantado (`./bna up`).
- Celular real por Wi-Fi: `http://IP-de-tu-PC:8020`. El producto publica el puerto solo en `127.0.0.1`: para un celular real hay que exponerlo (por ejemplo, un túnel) bajo tu responsabilidad.

## La app móvil frente a la API integrada (estado al 2026-11-18)

**La app Flutter de `app_movil/` no funciona todavía con esta API.** La API (`backend/server.js`) sí: el
flujo de extremo a extremo del producto entra, consulta, envía por celular, cobra con QR y responde
solicitudes por ella. La app no se pudo compilar ni probar en la integración (no hay Flutter en el
equipo que la hizo); lo que sigue sale de leer su código contra la API. Nada de esto está probado en un
emulador.

### Qué se rompe y dónde

| Pantalla o pieza | Archivo | Qué pasa con la API nueva |
|---|---|---|
| Ingreso → inicio | `state/app_state.dart:138-150`, `models.dart:8, 46, 99, 104, 179, 196` | Cae justo después del login. `/api/me`, `/api/movimientos`, `/api/solicitudes` y `/api/notificaciones` devuelven ids de texto (`id_cliente` = código `CLI…`, `id_cuenta` = número de cuenta, UUID en movimientos, operaciones, solicitudes y avisos) y los modelos los declaran `int`: `TypeError` al leer `/api/me`. Además se guarda `setInt('id_cliente')`. |
| Caché local | `services/cache_db.dart`, `models.dart:132` (`toRow(int idCliente)`) | Las tablas y `toRow` asumen ids enteros. |
| Servidor por omisión | `state/app_state.dart:13`, `screens/login_screen.dart:72-74` | Apunta a `:3000`, que en el producto es el frontend web. La API de Chaski está en `8020`. |
| Enviar por celular | `screens/enviar_screens.dart:41` | Llama `GET /clientes/buscar?celular=…`; la API solo tiene `POST /api/clientes/buscar` con `{"celular": …}` en el cuerpo (en la URL el celular quedaba en los registros del Bus) → 404 "Ruta no encontrada". El envío no puede empezar. |
| Contactos recientes | `screens/enviar_screens.dart:30` | `/api/recientes` devuelve `[]`: COREDB ya no entrega celulares. `Solicitud.celular` llega vacío por lo mismo. |
| Cobrar y pagar con QR | `models.dart:247, 372, 392-394`, `screens/qr_screens.dart:96, 151` | La trama es `CHASKI|<int>`, el escáner hace `int.parse` y el código manual `int.tryParse`; `id_qr` ahora es UUID: no se puede leer ni teclear un QR. |
| Responder solicitudes | `screens/home_shell.dart:278, 296` | La ruta existe, pero `s.id` es `int` (ver la primera fila). Aceptar ya manda `Idempotency-Key`; rechazar (l. 278) no, y sin llave la API genera una nueva en cada intento. |
| Registro | `state/app_state.dart:107` | `POST /api/registro` responde 403: la billetera se activa en una agencia (R-01). |
| Promociones, ofertas, tienda, órdenes, cupones, recargas, servicios | `screens/tienda_screens.dart`, `screens/servicios_screen.dart`, `state/app_state.dart:142` | Promos y ofertas devuelven listas vacías; tienda, órdenes, cupones, recargas y servicios responden 501 "No disponible en esta versión". Las pantallas siguen visibles. |
| Nombre y celular en el perfil | `models.dart:9-37` | `/api/me` trae el nombre corto (`apellidos` vacío) y no trae el celular. |
| Celular real | `compose.yaml` (`127.0.0.1:${BNA_PUERTO_BILLETERA}`) | La API solo escucha en `127.0.0.1`: hoy solo llega el emulador de Android en la misma máquina (`http://10.0.2.2:8020`). La app no puede ir por el Bus: exige `X-Bus-Token`, que una app no puede guardar en secreto (ver #105, `BUS_MODULOS_PUBLICOS`). |

### Cómo adaptarla

1. `models.dart`: todos los ids (`idCliente`, `idCuenta`, `idMovimiento`, `idTransferencia`, `idPago`,
   `Notificacion.id`, `Solicitud.id`, `idQr`, `idComercio`…) a `String`; `fromJson` sin conversiones a
   número. `tramaQr(String idQr)`.
2. `state/app_state.dart`: `servidorPorDefecto = 'http://10.0.2.2:8020'`; `setString('id_cliente', …)`;
   no pedir `/api/promos` al iniciar. `login_screen.dart`: la pista con `:8020`.
3. `services/cache_db.dart`: columnas de id como `TEXT` y una migración que borre la caché anterior.
4. `screens/enviar_screens.dart`: `api.post('/clientes/buscar', {'celular': cel})`; ocultar "recientes"
   mientras devuelva `[]`.
5. `screens/qr_screens.dart`: leer `CHASKI|(<uuid>)` con una expresión regular de UUID y aceptar el
   código manual como texto.
6. `screens/home_shell.dart`: rechazar también con `Idempotency-Key` (la misma si se reintenta), como
   ya hace aceptar.
7. Esconder registro, tienda, órdenes, cupones, recargas, servicios y promociones (o mostrar "No
   disponible en esta versión" sin llamar a la API).
8. `test/logica_test.dart`: actualizar los casos con ids de texto; correr `flutter analyze` y
   `flutter test`, y probar en el emulador contra `./bna up`: ingreso, saldo, envío por celular, QR,
   solicitudes y avisos.

Fuera de esto, `LEEME_Chaski.txt`, los PDF de `docs/`, `iniciar_backend.bat` y
`.github/workflows/ios.yml` describen el prototipo (PostgreSQL propio, puerto 3000) y el flujo de
GitHub de esta subcarpeta no corre (GitHub solo lee `.github/` en la raíz del repositorio).

## Compartir la app con compañeros

**El producto tiene que estar levantado y accesible** (`./bna up`): la app no funciona sola, necesita la API de Chaski y COREDB.
- Misma red Wi-Fi: con el producto levantado (`./bna up`), expón el puerto 8020 y permítelo en el Firewall.
  El APK de `entregables/` es del prototipo original (ids numéricos, puerto 3000): no sirve con esta API hasta adaptar la app.
- Desde cualquier lugar: `npx cloudflared tunnel --url http://localhost:8020` y que cada uno ponga en ⚙ la URL `https://….trycloudflare.com`.

**Android** — envía `entregables/Chaski.apk` (WhatsApp, Drive…). Al abrirlo, Android pide permitir
"instalar apps de origen desconocido". Para volver a generarlo:

```bash
cd app_movil
flutter build apk --release --dart-define=SERVIDOR=http://TU-IP:8020
```

**iPhone** — Apple no permite instalar un archivo como un APK, y en Windows no se compila iOS. Opciones:
1. Sube el proyecto a GitHub y ejecuta la acción **Build iOS (.ipa)** (`.github/workflows/ios.yml`): compila en una Mac de GitHub y deja `Chaski-sin-firma.ipa`.
   Cada compañero lo instala con **Sideloadly** (Windows/Mac) y su Apple ID gratuito (dura 7 días; hay que activar el modo desarrollador en el iPhone).
2. Con una Mac y Xcode: abre `app_movil/ios/Runner.xcworkspace`, elige tu equipo de firma y ejecuta en el iPhone conectado.
3. Para distribución formal: cuenta Apple Developer (US$ 99/año) y TestFlight.
4. Lo más simple para iPhone: la versión web/PWA (`chaskifast/chaski`) desde Safari → Compartir → Agregar a inicio.

## Verificación realizada

- Integración (PR que cierra #94): `npm test` 16/16 contra un COREDB falso; COREDB contra MySQL
  real (acceso, envíos, QR, solicitudes, concurrencia con la misma llave y con llaves distintas);
  `./bna test` y el flujo de extremo a extremo con dos clientes de CAPTACION.
- **La app móvil no se adaptó ni se compiló en la integración** (no había Flutter en el equipo): ver
  "La app móvil frente a la API integrada".
- Prototipo original (PostgreSQL propio): `npm test` 12/12, `flutter analyze`, `flutter test` 6/6
  y `flutter build apk --debug` (Flutter 3.47.7).

## Notas

- El saldo es el de la cuenta de ahorro del cliente en la base integrada (datos de desarrollo).
- Quedan fuera de esta versión: notificaciones push (Firebase), biometría facial contra el
  módulo Clientes, el registro por la app con OTP, y lo listado en «Fuera de esta versión».
