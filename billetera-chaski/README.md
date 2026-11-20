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

### 2. App (Flutter)

1. Instala Flutter (https://docs.flutter.dev/get-started/install) y, si usas Android Studio, su plugin **Flutter**.
2. En `app_movil`: `flutter pub get`.
3. Pruebas: `flutter analyze` y `flutter test` (la API va simulada; no hace falta el producto).
4. Con el producto levantado (`./bna up`), elige el servidor al compilar con `--dart-define=SERVIDOR=...`
   o cámbialo en la pantalla de ingreso (engranaje ⚙). La API de Chaski está en el puerto **8020**.

| Dónde corre la app | Servidor | Build |
|---|---|---|
| Celular por USB | `http://localhost:8020`, con `adb reverse tcp:8020 tcp:8020` en la PC | release o debug |
| Emulador de Android | `http://10.0.2.2:8020` (el valor por omisión) | debug |
| Celular por Wi-Fi | `http://IP-del-servidor:8020` (hay que exponer el puerto, ver abajo) | debug |
| Cualquier lugar | `https://…` (por ejemplo, un túnel) | release o debug |

```bash
cd app_movil
flutter build apk --release --dart-define=SERVIDOR=http://localhost:8020 --target-platform android-arm64
adb reverse tcp:8020 tcp:8020   # con el celular conectado por USB
```

**HTTP sin cifrar.** El build release solo permite HTTP sin cifrar hacia `localhost` y `127.0.0.1`
(`android/app/src/main/res/xml/network_security_config.xml`): con `adb reverse` el celular llega a la API
de la PC por su propio `localhost`, y cualquier otro servidor tiene que ir por HTTPS. El build debug
(`src/debug/res/xml/network_security_config.xml`) lo permite a cualquier host, para el emulador y la red
local. Antes la app lo permitía a todos en todos los builds (`usesCleartextTraffic="true"`), y un APK
release mandaba el PIN y el token sin cifrar por la red.

## La app móvil frente a la API integrada

La app de `app_movil/` está adaptada a esta API (PR #132 de Gabriel Tapia y la rama `fix/chaski-app-api-integrada`). Lo
verificado: `flutter analyze` sin errores ni advertencias, `flutter test` en verde con la API simulada y
el APK release compilado. La prueba en un celular contra `./bna up` se registra en el PR.

### Qué se adaptó

| Pieza | Qué hace ahora |
|---|---|
| Ids (`models.dart`) y caché local (`services/cache_db.dart`) | Ids de texto (código `CLI…`, número de cuenta, UUID); la caché pasa a la versión 2 y borra la anterior (#132). |
| Servidor por omisión (`state/app_state.dart`) | `http://10.0.2.2:8020`; `--dart-define=SERVIDOR=...` lo cambia al compilar (#132). |
| QR (`screens/qr_screens.dart`) | Trama `CHASKI|<uuid>` y código manual como texto (#132). |
| Enviar y solicitar (`screens/enviar_screens.dart`, `services/operaciones.dart`) | `POST /api/clientes/buscar` con `{"celular": …}` en el cuerpo, nunca en la URL. Sin «Recientes»: la API no devuelve celulares de otros clientes y la app no los guarda. |
| Idempotencia (`screens/operacion.dart`, `services/operaciones.dart`) | Cada operación de dinero (envío, pago con QR, pago de un cobro) tiene un uuid que se manda en `Idempotency-Key` y se repite en el reintento automático tras un corte de red y si el usuario vuelve a tocar el botón en la misma pantalla. Rechazar y cancelar un cobro también lo mandan, el mismo mientras no se sepa el resultado. |
| Rechazos de la API | La app muestra el mensaje de la API (por ejemplo, «El límite por operación es S/ 500» para un QR de más de S/ 500). |
| Fuera de esta versión (`funciones.dart`) | Registro, promociones, ofertas, cupones, tienda, órdenes, recargas y servicios no se muestran ni se llaman (tampoco `/api/promos` al iniciar). El ingreso explica que la billetera se activa en una agencia. Para reactivarlas, cambiar la constante en `funciones.dart`. |
| Perfil | Muestra el nombre corto que da `/api/me`; el documento y el celular, que la API no entrega, no aparecen. |
| Celular y PIN | La app no los escribe en registros ni los guarda: `shared_preferences` solo tiene servidor, token, código de cliente y preferencias; la caché SQLite no guarda el celular. |

### Lo que sigue abierto

- **Celular real por Wi-Fi.** La API solo escucha en `127.0.0.1` (`compose.yaml`) salvo que se use
  `BNA_IP_RED`. Por el Bus exige `X-Bus-Token`, que una app no puede guardar en secreto (`BUS_MODULOS_PUBLICOS`
  está vacío en el producto).
- **Registro por la app con OTP (RF-BD-005)** y las funciones de «Fuera de esta versión»: decisión del equipo.
- `LEEME_Chaski.txt`, los PDF de `docs/`, `iniciar_backend.bat` y `.github/workflows/ios.yml` describen el
  prototipo (PostgreSQL propio, puerto 3000), y el flujo de GitHub de esta subcarpeta no corre (GitHub solo
  lee `.github/` en la raíz del repositorio).

## Compartir la app con compañeros

**El producto tiene que estar levantado y accesible** (`./bna up`): la app no funciona sola, necesita la API de Chaski y COREDB.
- Por USB: APK release con `SERVIDOR=http://localhost:8020` y `adb reverse tcp:8020 tcp:8020` (ver «2. App»).
- Misma red Wi-Fi: con el producto levantado con `BNA_IP_RED` (por ejemplo `0.0.0.0`) para publicar el puerto
  8020 en la red, permitido en el Firewall, y un APK **debug** (el release no permite HTTP sin cifrar a otra IP).
  Un APK del prototipo original (ids numéricos, puerto 3000) no sirve con esta API.
- Desde cualquier lugar: `npx cloudflared tunnel --url http://localhost:8020` y que cada uno ponga en ⚙ la URL `https://….trycloudflare.com` (sirve con el APK release).

**Android** — el APK no está en el repositorio (`entregables/` solo tiene su README: los instaladores van a GitHub → Releases). Genéralo y envíalo (WhatsApp, Drive…). Al abrirlo, Android pide permitir
"instalar apps de origen desconocido". Para generarlo:

```bash
cd app_movil
flutter build apk --release --dart-define=SERVIDOR=https://TU-TUNEL   # o http://localhost:8020 con adb reverse
flutter build apk --debug --dart-define=SERVIDOR=http://TU-IP:8020    # red local
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
- App adaptada a la API integrada (#132 y la rama `fix/chaski-app-api-integrada`), con Flutter 3.50.1: `flutter analyze` sin
  errores ni advertencias, `flutter test` 17/17 con la API simulada y
  `flutter build apk --release --target-platform android-arm64`. La prueba en el celular se registra en el PR.
- Prototipo original (PostgreSQL propio): `npm test` 12/12, `flutter analyze`, `flutter test` 6/6
  y `flutter build apk --debug` (Flutter 3.47.7).

## Notas

- El saldo es el de la cuenta de ahorro del cliente en la base integrada (datos de desarrollo).
- Quedan fuera de esta versión: notificaciones push (Firebase), biometría facial contra el
  módulo Clientes, el registro por la app con OTP, y lo listado en «Fuera de esta versión».
