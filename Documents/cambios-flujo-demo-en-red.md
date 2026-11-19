# Cambios para el flujo de la demo y el uso en red

Registro de lo que se cambió para que el flujo pedido por el profesor funcione de punta a punta,
y para que el producto se pueda usar desde varias máquinas y desde un celular Android.

El flujo pedido:

1. Registrar un cliente nuevo y dejarlo habilitado (Captación).
2. Abrirle una cuenta de ahorros (Cuentas) y depositarle por ventanilla.
3. Emitirle una tarjeta de débito asociada a esa cuenta (Tarjetas).
4. Con la tarjeta, en el ATM: consultar el saldo y retirar.
5. Por ventanilla, depositar 1000 soles más.
6. Afiliar al cliente a la billetera Chaski y hacer un pago desde la app.
7. Bloquear la tarjeta (Tarjetas) y comprobar que el ATM ya no la acepta.

Estado de cada paso antes de los cambios:

| Paso | Pantalla | Estado previo |
|---|---|---|
| 1 | `/captacion` | Funcionaba |
| 2 y 5 | `/cuenta` (apertura y depósito con canal VEN, ventanilla) | Funcionaba en la máquina del servidor; fallaba desde otra máquina (cambio 1) |
| 3 y 7 | `/tarjetas` (emisión, PIN en "Claves", bloqueo en "Estado") | Igual que el anterior |
| 4 | Cajero en el puerto 8019 | El retiro fallaba desde otra máquina (cambio 2) |
| 6 | Afiliación y app Chaski | No había pantalla de afiliación y la app móvil no estaba adaptada a la API (issue #116) |

---

## 1. Llaves de idempotencia en el frontend fuera de `localhost`

**Problema.** Varias páginas generan sus llaves de idempotencia con `crypto.randomUUID()`. El
navegador solo ofrece esa función en un contexto seguro (HTTPS o `localhost`). Si un compañero
abre el frontend desde otra máquina (`http://IP-del-servidor:3000`), la función no existe y las
páginas de Cuentas y Tarjetas fallan al cargar.

**Cambio.**

- Archivo nuevo [`frontend/lib/uuid.ts`](../frontend/lib/uuid.ts): `nuevoUuid()` usa
  `crypto.randomUUID()` cuando existe y, si no, arma un UUID v4 con `crypto.getRandomValues()`,
  que sí está disponible en cualquier contexto.
- En el código del navegador se reemplazó `crypto.randomUUID()` por `nuevoUuid()` y se agregó
  `import { nuevoUuid } from "@/lib/uuid";` en la línea 2 de cada archivo:

| Archivo | Líneas cambiadas |
|---|---|
| [`frontend/app/cuenta/page.tsx`](../frontend/app/cuenta/page.tsx) | 2 (import), 36, 39, 100 |
| [`frontend/app/tarjetas/page.tsx`](../frontend/app/tarjetas/page.tsx) | 2 (import), 205, 208, 225, 228, 268, 307, 335 |
| [`frontend/app/pagar-cuota/page.tsx`](../frontend/app/pagar-cuota/page.tsx) | 2 (import), 52, 88, 98, 102 |
| [`frontend/app/solicitud-credito/page.tsx`](../frontend/app/solicitud-credito/page.tsx) | 2 (import), 455 |
| [`frontend/lib/desembolso/api.ts`](../frontend/lib/desembolso/api.ts) | 1 (import), 21, 51 |

Los usos que corren en el servidor de Next.js (`frontend/lib/proxy.ts` y
`frontend/app/api/solicitud-credito/[...path]/route.ts`) no se tocaron: en Node.js
`crypto.randomUUID()` siempre existe.

## 2. Id de la transacción en la pantalla del cajero

**Problema.** En [`backend/ATM/static/index.html`](../backend/ATM/static/index.html) ya había un
respaldo para cuando no existe `crypto.randomUUID()`, pero generaba un texto como
`1732000000000a1b2c3`. La API del ATM exige que `uuid_transaccion` tenga exactamente 36
caracteres (`backend/ATM/schemas/atm.py`, línea 42), así que desde otra máquina el retiro se
rechazaba.

**Cambio.** En `backend/ATM/static/index.html`, líneas 227 a 230, la función `uuid()` ahora arma
un UUID v4 real con `crypto.getRandomValues()` cuando `crypto.randomUUID()` no existe.

## 3. Publicar el frontend, el cajero y Chaski en la red

**Problema.** En [`compose.yaml`](../compose.yaml) todos los puertos se publicaban solo en
`127.0.0.1`. Ninguna otra máquina ni un celular podía conectarse.

**Cambio.** Una variable nueva, `BNA_IP_RED`, decide en qué dirección se publican solo los tres
puertos que usan las personas. Si no se define, el valor sigue siendo `127.0.0.1`, así que nada
cambia para quien no la configure.

| Archivo | Línea | Servicio | Antes | Ahora |
|---|---|---|---|---|
| `compose.yaml` | 381 | `atm` | `"127.0.0.1:${BNA_PUERTO_ATM:-8019}:8019"` | `"${BNA_IP_RED:-127.0.0.1}:${BNA_PUERTO_ATM:-8019}:8019"` |
| `compose.yaml` | 415 | `billetera` (Chaski) | `"127.0.0.1:${BNA_PUERTO_BILLETERA:-8020}:3000"` | `"${BNA_IP_RED:-127.0.0.1}:${BNA_PUERTO_BILLETERA:-8020}:3000"` |
| `compose.yaml` | 547 | `frontend` | `"127.0.0.1:${BNA_PUERTO_FRONTEND:-3000}:3000"` | `"${BNA_IP_RED:-127.0.0.1}:${BNA_PUERTO_FRONTEND:-3000}:3000"` |

La base de datos (3307), COREDB, el Bus y los demás módulos siguen publicados solo en `127.0.0.1`.

En [`.env.example`](../.env.example), líneas 77 a 83, se agregó la sección "Acceso desde otras
máquinas" con `BNA_IP_RED=127.0.0.1` y su explicación. `scripts/generar_env.sh` agrega las claves
nuevas a un `.env` que ya existe sin cambiar las demás, así que cada compañero la recibe al correr
`./bna up`.

**Cómo se usa.** En la máquina que hará de servidor, poner `BNA_IP_RED=0.0.0.0` en `.env` y correr
`./bna up`. Los demás entran por `http://IP-del-servidor:3000` (banco), `:8019` (cajero) y
`:8020` (API que usa la app Chaski). Windows pedirá permitir Docker en el firewall la primera vez.

## Error ya corregido: "Servicio no disponible" al consultar el saldo en el cajero

**Síntoma.** Con un PIN correcto (`/validar-pin` responde 200), la consulta de saldo mostraba
"Servicio no disponible" y el registro del cajero decía `API -> ATM 500 DESCONOCIDO`. Ejemplo
observado el 2026-11-18 a las 18:18, con la tarjeta `b768c825-…-9da7` (cliente `CLI000000013`).

**Causa.** Para el saldo, el ATM pide a CUENTAS la vista consolidada del cliente. CUENTAS la
devuelve como **lista** de cuentas, pero el ATM esperaba un **objeto** con `lista_cuentas`. Al
convertir la respuesta fallaba, y toda consulta de saldo terminaba en 500. Las pruebas no lo
detectaban porque simulaban la forma antigua de la respuesta.

**Corrección** (commit `04e21bd`, rama `fix/git-bash-y-saldo-atm`):

- [`backend/ATM/services/atm.py`](../backend/ATM/services/atm.py), función de consulta de saldo:
  si la respuesta es una lista, se convierte a `SaldoOut` con el número de cuenta enmascarado
  (`****` + últimos 4); si es un objeto, se usa como antes.
- [`backend/ATM/tests/test_atm.py`](../backend/ATM/tests/test_atm.py): prueba nueva
  `test_consultar_saldo_con_la_consolidada_real_de_cuentas`, con la respuesta real de CUENTAS.

**Importante para el equipo.** La corrección todavía no está en `main`. Quien tenga el error debe
traer esta rama y reconstruir el cajero: `docker compose up -d --build atm`. Si el cajero dice
"Servicio no disponible" por otro motivo, revise `./bna ps`: si TARJETAS, CUENTAS o el Bus no están
`healthy` (por ejemplo, porque Docker se reinició por falta de memoria), el cajero también
responde así.

---

## 4. Pantalla de afiliación a Chaski en el frontend (`/billetera`)

**Problema.** El paso 6 del flujo ("afiliamos al cliente a la billetera Chaski") no tenía
pantalla: la afiliación solo existía en la API de COREDB (`POST /coredb/billetera/afiliaciones`).

**Cambio.**

| Archivo | Qué hace |
|---|---|
| [`frontend/lib/billetera.ts`](../frontend/lib/billetera.ts) (nuevo) | `afiliar()` y `registrarComercio()` llaman a `/coredb/billetera/afiliaciones` y `/coredb/billetera/comercios` por el puente `/api/core` (el navegador nunca llama a COREDB). `mensajeDeError()` muestra el mensaje de COREDB. |
| [`frontend/app/billetera/page.tsx`](../frontend/app/billetera/page.tsx) (nuevo) | Pestaña "1. Afiliar cliente": código del cliente, número de cuenta en soles y PIN de 6 dígitos. Pestaña "2. Registrar comercio": RUC, razón social y cuenta de abono; muestra el código del QR del comercio. |
| [`frontend/app/billetera/layout.tsx`](../frontend/app/billetera/layout.tsx) (nuevo) | Título y estilos, igual que Cuentas y Tarjetas. |
| [`frontend/app/components/BancaPersonal.tsx`](../frontend/app/components/BancaPersonal.tsx), línea 34 | Agrega "Billetera Chaski" al menú y al resumen de la portada. |
| [`frontend/__tests__/page.test.tsx`](../frontend/__tests__/page.test.tsx), líneas 14 y 23 | La prueba de la portada espera la nueva pantalla. |

COREDB exige el permiso `AFILIAR_BILLETERA` (roles ADMINISTRADOR, ASESOR u OPERADOR). Si el
cliente ya estaba afiliado, se le cambia el PIN o la cuenta y la billetera se desbloquea.

## 5. App móvil Chaski adaptada a la API sobre COREDB (issue #116)

**Problema.** La app se escribió para la versión original con PostgreSQL propio, donde todos los
ids eran números. La API actual devuelve los del CORE: el cliente `CLI000000016`, la cuenta
`CTA-…` y UUID para movimientos, solicitudes y QR. Dart fallaba al leerlos como `int`, así que
la app no pasaba del login. Además, los movimientos ya no traen `saldo_resultante` y el puerto
por defecto era 3000 en vez de 8020.

**Cambios** (carpeta `billetera-chaski/app_movil/`):

| Archivo | Líneas | Cambio |
|---|---|---|
| `lib/models.dart` | 8, 22 | `Cliente.idCliente`: de `int` a `String` |
| `lib/models.dart` | 46, 53 | `Cuenta.idCuenta`: de `int` a `String` |
| `lib/models.dart` | 100–154 | `Movimiento`: id en texto (UUID), `saldoResultante` opcional, ids de operación en texto, `toRow()` recibe el código del cliente |
| `lib/models.dart` | 168–170 | Nombres legibles para `deposito`, `retiro` y `fondeo_billetera` (los tipos del CORE) |
| `lib/models.dart` | 202 | `Solicitud.id`: de `int` a `String` (UUID) |
| `lib/models.dart` | 253, 378 | `Promo.idQr` y `QrInfo.idQr`: de `int` a `String` (UUID) |
| `lib/models.dart` | 399–401 | La trama del QR es `CHASKI|<uuid>`; `uuidRe` valida un código digitado |
| `lib/services/cache_db.dart` | 16–22 y tablas | Caché SQLite versión 2: columnas de id en `TEXT`, `saldo_resultante` opcional, orden por fecha. Al actualizar, borra y recrea la caché vieja. |
| `lib/state/app_state.dart` | 14 | Servidor por defecto `http://10.0.2.2:8020` (o el `--dart-define=SERVIDOR=…` de la compilación) |
| `lib/state/app_state.dart` | 124, 152, 170 | El cliente de la caché se guarda como texto (`setString('cliente')`) |
| `lib/screens/login_screen.dart` | 72, 74 | La ayuda del servidor indica el puerto 8020 |
| `lib/screens/qr_screens.dart` | 16, 96, 150–155 | `abrirPagoQr` recibe el UUID; el código manual acepta el UUID o la trama completa |
| `lib/widgets/comunes.dart` | 150 | El detalle muestra el saldo resultante solo si viene |
| `test/logica_test.dart` | 43–74 | Prueba de la trama con UUID y prueba nueva con las respuestas reales de la API |

Para compilar con Flutter 3.50, en `android/settings.gradle.kts` (línea 22) el plugin de Android
(`com.android.application`) pasó de la versión `9.1.0` a la `9.1.1`, la mínima que acepta esa
versión de Flutter.

`flutter analyze` sin errores y `flutter test`: 7 de 7 pruebas pasan. `pubspec.lock` cambió solo
porque `flutter pub get` ajustó cuatro dependencias al SDK de Flutter 3.50.

## 6. Mensaje del cajero para una tarjeta bloqueada

En [`backend/ATM/static/index.html`](../backend/ATM/static/index.html), línea 516: con una tarjeta
no operativa (código `ERR-ATM-TARJETA-NO-OPERATIVA`), la pantalla decía "Superaste los 3
intentos", aunque la hubiera bloqueado el banco (paso 7 del flujo). Ahora dice "Esta tarjeta no
está habilitada para operar (bloqueada, cancelada o vencida). Acude a tu banco."

## 7. `./bna demo`: el flujo del profesor automatizado

| Archivo | Cambio |
|---|---|
| [`scripts/flujo_profesor.py`](../scripts/flujo_profesor.py) (nuevo) | Ejecuta los 7 pasos con los mismos servicios que las pantallas (Captación, CUENTAS con canal de ventanilla, TARJETAS, el ATM y Chaski), comprueba cada saldo y al final muestra los datos creados. |
| [`bna`](../bna), líneas 23, 183–193 y 205 | Orden nueva `./bna demo`, que corre el script dentro del contenedor del Bus, como `./bna smoke`. |

Sirve para comprobar en segundos que todo funciona antes de presentar, y deja un cliente con datos
para repetir el flujo a mano. Resultado del 2026-11-19:

```
OK  1. Captación registró a Carmen Mamani (CLI000000018) y quedó HABILITADO
OK  2. cuenta de ahorros CTA-0017950658847799 abierta; depósito por ventanilla de S/ 500.00 (saldo 500.00)
OK  3. tarjeta 0044 99** **** 7055 emitida sobre CTA-0017950658847799, ACTIVA y con PIN de cajero
OK  4. ATM: PIN correcto, saldo S/ 500.00, retiro de S/ 100.00 dispensado (saldo 400.00)
OK  5. depósito por ventanilla de S/ 1000.00 (saldo 1400.00)
OK  6. afiliado a Chaski; envío de S/ 50.00 a Jorge Condori y pago con QR de S/ 20.00 (saldo en la app 1330.00)
OK  7. tarjeta BLOQUEADA; el ATM la rechaza (400 ERR-ATM-TARJETA-NO-OPERATIVA)
```

---

## Cómo trabajar todos sobre la misma base

**La idea:** una sola PC (el "servidor") corre Docker con la base de datos. Las demás PCs y los
celulares **no** levantan nada: solo abren el navegador o la app apuntando a la IP del servidor. Así
todos ven los mismos clientes, cuentas y saldos. Si cada uno corre `./bna up` en su PC, cada uno
tiene su propia base y los datos no coinciden.

### En la PC servidor (una sola vez)

1. En `.env`: `BNA_IP_RED=0.0.0.0`, y luego `./bna up`.
2. Abrir el firewall de Windows a los tres puertos. En **PowerShell como administrador**:
   ```powershell
   New-NetFirewallRule -DisplayName "BNA - frontend, cajero y Chaski" -Direction Inbound -Protocol TCP -LocalPort 3000,8019,8020 -Action Allow -Profile Any
   ```
3. Averiguar su IP: `ipconfig` (en Wi-Fi) o la IP que muestre Tailscale o ZeroTier.
4. Que la PC no se suspenda durante la demo.

### En las demás PCs y celulares

| Qué | Dirección |
|---|---|
| Banco (Captación, Cuentas, Tarjetas, Billetera) | `http://IP-del-servidor:3000` |
| Cajero (ATM) | `http://IP-del-servidor:8019` |
| App Chaski | En la pantalla de ingreso, ⚙ servidor: `http://IP-del-servidor:8020` |

### ¿Y si no estamos en el mismo Wi-Fi? (lo de "Warp")

Cloudflare **WARP** (la app 1.1.1.1) solo cifra la salida a Internet de cada equipo: **no** pone a
varias PCs en una misma red, así que no sirve para esto. Lo que sí sirve es una red privada virtual
entre los equipos:

- **Tailscale** (recomendado, gratis): cada uno instala Tailscale e inicia sesión en la misma red
  (el dueño invita a los demás). Cada equipo recibe una IP `100.x.y.z`; se usa la del servidor en
  la tabla de arriba. También hay app para Android.
- **ZeroTier**: parecido; se crea una red, todos se unen con su ID y el administrador los aprueba.

En clase, lo más simple es que todos estén en el mismo Wi-Fi (o en el punto de acceso de un
celular) y usen la IP de `ipconfig`. Algunas redes de universidad aíslan a los equipos entre sí; en
ese caso, Tailscale.

### Código actualizado en todas las máquinas

El **código** se comparte con Git (`git pull` y luego `./bna up` para reconstruir). Los **datos**
viven solo en la base del servidor. Si alguien quiere su propia copia para desarrollar, puede correr
`./bna up` en su PC, pero esos datos son solo suyos.

---

## Guía de la demo paso a paso (en las pantallas)

Se entra al banco con el usuario `admin` y la contraseña `BNA_ADMIN_PASSWORD` del `.env` del
servidor.

1. **Registrar y habilitar al cliente** — `/captacion`: registrar al solicitante (DNI, nombres,
   **celular**: es con el que entrará a Chaski), crear el caso, consentimientos, OTP (el código
   simulado aparece en pantalla), validaciones, consulta de riesgo, perfil y **Habilitar**. Anotar
   el **código del cliente** (`CLI…`).
2. **Cuenta y depósito** — `/cuenta`: "1. Crear cuenta" con el código del cliente y la agencia
   `AQP01`. Luego "3. Depositar / Transferir" → Depositar en esa cuenta (canal de ventanilla).
3. **Tarjeta** — `/tarjetas`: "Emitir tarjeta" con el cliente y la cuenta (queda
   PENDIENTE_ACTIVACION); en "Bloqueos y estados" → ACTIVA; en "Claves de la tarjeta" registrar el
   **PIN_ATM** (4 dígitos). Copiar el **Identificador** de la tarjeta (UUID): es lo que pide el
   cajero.
4. **Cajero** — `http://IP:8019`: el operador lo abre con `admin`. Pegar el identificador de la
   tarjeta, ingresar el PIN, **Consultar saldo** y luego **Retiro**.
5. **Segundo depósito** — `/cuenta`, depositar 1000.
6. **Chaski** — `/billetera`: "Afiliar cliente" con su código, su cuenta y un PIN de 6 dígitos.
   Para pagar hace falta a quién: otro cliente afiliado (envío por celular) o un comercio
   registrado en "Registrar comercio" (pago con QR). En el celular: abrir Chaski, ingresar con el
   celular del cliente y el PIN, y hacer el envío o el pago.
7. **Bloqueo** — `/tarjetas` → "Bloqueos y estados" → BLOQUEADA. En el cajero, la tarjeta ahora muestra
   "Tarjeta bloqueada". El desbloqueo no se hace en Tarjetas: lo hace el módulo Seguridad.

Para comprobarlo todo antes de presentar: `./bna demo`.

## Fuera del repositorio (solo en la máquina que compila el APK)

- Se instalaron en el Android SDK (`%LOCALAPPDATA%\Android\Sdk`) los paquetes `platform-tools`,
  `build-tools;35.0.0`, `platforms;android-35`, `ndk;28.2.13676358` y `cmake;3.22.1` (este último lo instaló Gradle solo), que faltaban para compilar.
  En otra PC, Android Studio los instala solo al abrir el proyecto (SDK Manager).
- Compilar el APK: en `billetera-chaski/app_movil`,
  `flutter build apk --release --dart-define=SERVIDOR=http://IP-del-servidor:8020`. Queda en
  `build/app/outputs/flutter-apk/app-release.apk`. Si la IP del servidor cambia, no hace falta
  recompilar: se cambia desde el ⚙ de la pantalla de ingreso de la app.
- Instalar en el celular: copiar el APK al teléfono y abrirlo (permitir "instalar apps de origen
  desconocido"), o por cable con depuración USB: `adb install -r app-release.apk`.
- En esta PC, el antivirus AVG intercepta HTTPS. Para descargar, Java necesita un almacén de
  certificados con el de AVG (`~/.gradle/gradle.properties`). Una PC sin AVG no necesita esto.
