# Chaski — Billetera Digital BNA (app móvil Flutter + API PostgreSQL)

📄 Documentación completa: [docs/Documentacion_Chaski.pdf](docs/Documentacion_Chaski.pdf)

Versión móvil de Chaski. Toma la PWA web anterior como base y la lleva a una app Android
hecha en **Flutter**, alineada con la Fase I TOGAF del módulo Billetera Digital (RF-BD-001 a RF-BD-009).

```
trabajo final chaski/
├── backend/          API REST/JSON (Node.js + Express) sobre PostgreSQL
│   ├── sql/schema.sql   esquema de la base de datos (el del diagrama + extensiones)
│   ├── db.js            conexión, transacciones ACID, saldo, tope diario, datos demo
│   ├── server.js        endpoints /api/*
│   └── test/            prueba de humo de toda la API (npm test)
└── app_movil/        app Flutter (Android Studio)
    └── lib/
        ├── main.dart
        ├── models.dart          modelos = tablas del diagrama
        ├── state/app_state.dart estado global (sesión, saldo, avisos, carrito)
        ├── services/            api.dart · cache_db.dart (SQLite local) · autorizacion.dart (huella/PIN)
        ├── screens/             login, inicio, movimientos, avisos, perfil, enviar/solicitar,
        │                        QR, promos y cupones, ofertas, tienda, carrito, pedidos, servicios
        └── widgets/comunes.dart
```

## Arquitectura

```
App Flutter (Android)  ──REST/JSON──►  API Chaski (Express)  ──►  PostgreSQL (ACID)
  SQLite local (caché del saldo                ▲ token firmado, idempotencia
  e historial, modo fuera de línea)            ▲ tope diario, auditoría
```

| Requisito del informe | Cómo está resuelto |
|---|---|
| RF-BD-001 Transferir P2P por celular | Enviar → celular → monto → confirmar → huella/PIN → constancia |
| RF-BD-002 Solicitar cobro | Solicitar; el otro lo ve en **Avisos** (pagar / rechazar). Expira a las 48 h |
| RF-BD-003 Pagar con QR | Escáner con cámara (`mobile_scanner`), código manual o lista de comercios. Mi QR fijo o con monto (vence en 15 min, se paga una vez) |
| RF-BD-004 Saldo e historial | Inicio y Movimientos; si el servidor no responde muestra el último saldo guardado con *“Modo fuera de línea - Saldo no actualizado”* |
| RF-BD-005 Enrolamiento | Crear cuenta con DNI, celular, PIN y aceptación de términos |
| RF-BD-006 Servicios | Recargas (Claro, Movistar, Entel, Bitel) y pago de luz, agua, gas, internet |
| RF-BD-007 Promos y cupones | Catálogo filtrable por comercio y **Obtener cupón** (código + QR para canje) |
| RF-BD-008 BNA Tienda | Catálogo, carrito multi-tienda, pago y código de retiro |
| RF-BD-009 Notificaciones | Cada operación genera notificación; la app consulta cada 8 s |
| RN-TOP-001 Tope S/ 500 | Tope **acumulado diario** (hora de Lima) validado en el servidor dentro de la transacción |
| RN-BUS-002 Idempotencia | Cada operación de dinero envía un `uuidTransaccion` (cabecera `Idempotency-Key`); un reintento no cobra dos veces |
| Timeout 15 s | La app anula la petición a los 15 s y reintenta una vez con el mismo uuid |
| INT-13 Auditoría | Tabla `auditoria`: toda operación exitosa o rechazada |
| Biometría / PIN | `local_auth` (huella o rostro); si el celular no tiene, pide el PIN y lo valida el servidor |

## Base de datos

`backend/sql/schema.sql` respeta el diagrama: `cliente`, `cuenta`, `comercio`, `transferencia`,
`solicitud_cobro`, `codigo_qr`, `pago_qr`, `movimiento` y `notificacion`, con sus tipos
(`bigserial`, `numeric(14,2)`, `timestamptz`…) y enums (`estado_general`, `estado_transferencia`,
`estado_solicitud`, `tipo_qr`, `estado_pago`, `tipo_movimiento`, `estado_envio`).

Extensiones (no están en el diagrama): `credencial` (PIN con scrypt), `producto`, `promocion`,
`cupon`, `oferta`, `orden`, `orden_item`, `servicio_pago`, `operacion_idempotente` y `auditoria`;
y en `movimiento` dos FK opcionales: `id_orden` e `id_pago_servicio`.

La app guarda en el celular (SQLite con `sqflite`) las tablas `cuenta_cache` y `movimiento_cache`.

## Cómo correrlo

### 1. Backend (PC)

Requisitos: Node.js 22.13+ y PostgreSQL (ya tienes PostgreSQL 18).

```bash
cd backend
copy .env.example .env      # y escribe la contraseña de tu usuario postgres
npm install
npm start
```

La primera vez crea la base `chaski`, las tablas y los datos demo. Usuarios demo (PIN `123456`):
`900000001`, `900000002`, `900000003`. Prueba de la API (con el servidor corriendo): `npm test`.

### 2. App (Android Studio)

1. Instala Flutter (https://docs.flutter.dev/get-started/install/windows) y en Android Studio el plugin **Flutter**.
2. Abre la carpeta `app_movil` en Android Studio.
3. `flutter pub get` (o el botón *Pub get*).
4. Elige el emulador o tu celular y pulsa ▶ Run. Para el APK: `flutter build apk --release`.

En la pantalla de ingreso, el engranaje ⚙ permite cambiar el servidor:

- Emulador de Android: `http://10.0.2.2:3000` (por defecto)
- Celular real por Wi-Fi: `http://IP-de-tu-PC:3000` (la consola del backend muestra la IP). Abre el puerto 3000 en el Firewall de Windows si no conecta.

## Compartir la app con compañeros

**El backend tiene que estar encendido y accesible**: la app no funciona sola, necesita la API.
- Misma red Wi-Fi: deja `npm start` corriendo en tu PC y permite el puerto 3000 en el Firewall de Windows.
  El APK de `entregables/` ya apunta a `http://192.168.15.2:3000` (tu IP de hoy; si cambia, cada uno la corrige con el ⚙ de la pantalla de ingreso).
- Desde cualquier lugar: `npx cloudflared tunnel --url http://localhost:3000` y que cada uno ponga en ⚙ la URL `https://….trycloudflare.com`.

**Android** — envía `entregables/Chaski.apk` (WhatsApp, Drive…). Al abrirlo, Android pide permitir
"instalar apps de origen desconocido". Para volver a generarlo:

```bash
cd app_movil
flutter build apk --release --dart-define=SERVIDOR=http://TU-IP:3000
```

**iPhone** — Apple no permite instalar un archivo como un APK, y en Windows no se compila iOS. Opciones:
1. Sube el proyecto a GitHub y ejecuta la acción **Build iOS (.ipa)** (`.github/workflows/ios.yml`): compila en una Mac de GitHub y deja `Chaski-sin-firma.ipa`.
   Cada compañero lo instala con **Sideloadly** (Windows/Mac) y su Apple ID gratuito (dura 7 días; hay que activar el modo desarrollador en el iPhone).
2. Con una Mac y Xcode: abre `app_movil/ios/Runner.xcworkspace`, elige tu equipo de firma y ejecuta en el iPhone conectado.
3. Para distribución formal: cuenta Apple Developer (US$ 99/año) y TestFlight.
4. Lo más simple para iPhone: la versión web/PWA (`chaskifast/chaski`) desde Safari → Compartir → Agregar a inicio.

## Verificación realizada

- Backend: `npm test` contra PostgreSQL 18 → 12/12 pruebas (P2P con idempotencia, tope diario, solicitudes,
  QR con promo, QR dinámico de un solo pago, cupones, tienda, recargas y servicios, movimientos, avisos).
- App: `flutter analyze` sin observaciones, `flutter test` 6/6 y `flutter build apk --debug` correcto (Flutter 3.47.7).
- La app aún no se probó en un emulador o celular.

## Notas

- El saldo es de prueba; no se conecta a ningún banco. Las deudas de servicios son simuladas.
- OAuth2/Keycloak, Bus de Servicios, notificaciones push (Firebase) y biometría facial contra
  el Módulo CLIENTES están fuera del alcance del prototipo: la API cumple el papel del Bus y
  emite un token firmado (HMAC, 12 h).
