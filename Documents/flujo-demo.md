# Flujo de demostración: del cliente nuevo al bloqueo de su tarjeta

Recorrido completo del producto integrado con un cliente nuevo: crear cliente, cuenta y tarjeta; pedir un crédito de S/ 1000.00; desembolsarlo; consultar el saldo en el cajero; depositar S/ 1000.00 en ventanilla; pagar S/ 500.00 con la billetera digital, y bloquear la tarjeta.

Comprobado el 2026-11-19 con `./bna up`, recorriendo cada paso con las mismas peticiones que hacen las pantallas, y con [`scripts/flujo_demo.py`](../scripts/flujo_demo.py), que lo repite entero y verifica los saldos en COREDB. Los dos pasos que estaban bloqueados (la consulta de saldo del cajero y el bloqueo desde el Home Banking) se corrigieron en #128 y #129.

## Resumen

| Paso | Qué | Dónde | Estado hoy |
|---|---|---|---|
| 0 | Entrar como administrador | `/login` | Funciona |
| 1a | Crear el cliente | `/captacion` | Funciona |
| 1b | Abrir la cuenta de ahorros | `/cuenta` | Funciona |
| 1c | Emitir y activar la tarjeta, asignar el PIN | `/tarjetas` | Funciona |
| 2a | Pedir el crédito de 1000.00 | `/solicitud-credito` | Funciona |
| 2b | Evaluar la solicitud | `/evaluacion` | Funciona |
| 3 | Desembolsar | `/desembolso` | Funciona |
| 4 | Consultar el saldo en el cajero | Cajero, `http://127.0.0.1:8019` | Funciona |
| 5 | Depositar 1000.00 en ventanilla | `/cuenta` | Funciona |
| 6a | Afiliar la billetera y registrar el comercio | `/billetera` | Funciona |
| 6b | Pagar 500.00 con la billetera | App Chaski (Flutter) contra la API integrada, o curl al Bus | Funciona |
| 7 | Bloquear la tarjeta | Home Banking, `/homebanking/cuentas.html` (también `/tarjetas`) | Funciona |

Saldo de la cuenta del cliente después de cada paso: 0.00 → 1000.00 (desembolso) → 1000.00 (consulta) → 2000.00 (depósito) → 1500.00 (pago).

## Requisitos

- Docker con Compose 2.20 o superior (en Windows, Git Bash o WSL2).
- Python 3.9 o superior, solo para el script (usa la biblioteca estándar).
- Un navegador, para las pantallas.

## Levantar el producto

```bash
git clone https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa.git
cd Banco_Nacional_Arequipa
./bna up       # crea .env, construye las imágenes y espera a que los 14 servicios estén sanos
```

`./bna up` imprime las direcciones al terminar. Las que usa este flujo:

| Qué | Dirección |
|---|---|
| Portal (frontend) | http://localhost:3000 |
| Cajero (ATM) | http://127.0.0.1:8019 |
| Bus de Servicios | http://127.0.0.1:8018 (documentación en `/docs`) |

## Usuarios y claves

Ninguna clave está en el repositorio. `./bna up` genera `.env` la primera vez (`scripts/generar_env.sh`) con valores al azar, y ese archivo no se versiona.

| Usuario | Rol | De dónde sale |
|---|---|---|
| `admin` | ADMINISTRADOR | Lo crea el arranque de COREDB. Su clave: `grep BNA_ADMIN_PASSWORD .env` |
| Asesora de crédito | ASESOR | La crea el administrador en `/login`, con el formulario de usuarios internos (`POST /coredb/usuarios`). Usuario y clave a elección |
| Operador | OPERADOR | Igual que la asesora, con rol OPERADOR. Prepara el desembolso y abre el cajero |
| El cliente en el cajero | – | Su tarjeta (el `id_tarjeta`, un UUID) y el PIN de 4 dígitos que se le asigna en el paso 1c |
| El cliente en la billetera | – | El celular que registró en Captación y el PIN de 6 dígitos que se le asigna en el paso 6a |
| curl al Bus | – | Cabecera `X-Bus-Token` con `BUS_TOKEN_PRUEBAS` de `.env`. Sin ella el Bus responde 401 |

Para los ejemplos con curl:

```bash
BUS=http://127.0.0.1:8018
BT=$(grep '^BUS_TOKEN_PRUEBAS=' .env | cut -d= -f2-)
TOKEN=$(curl -s -X POST $BUS/bus/coredb/coredb/auth/login -H "X-Bus-Token: $BT" -H 'Content-Type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"$(grep '^BNA_ADMIN_PASSWORD=' .env | cut -d= -f2-)\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')
H=(-H "X-Bus-Token: $BT" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json')
curl -s "${H[@]}" $BUS/bus/coredb/coredb/cuentas/<num_cuenta>   # saldo de una cuenta
```

## Paso a paso

Los datos de ejemplo son los de la corrida del script. Use otros en cada demostración: el documento y el celular no pueden repetirse.

### 0. Entrar como administrador

- **Pantalla:** http://localhost:3000/login, usuario `admin` y la clave de `.env`.
- **Petición:** `POST /api/core/coredb/auth/login` (COREDB por el Bus).
- **Resultado:** sesión con rol ADMINISTRADOR. En la misma pantalla, cree la asesora (rol ASESOR) y el operador (rol OPERADOR) que usan los pasos 2 y 3.

### 1a. Crear el cliente (Captación)

- **Pantalla:** http://localhost:3000/captacion, «nuevo».
- **Datos:** DNI de 8 dígitos que termine en 0 a 6 (la central de riesgo simulada califica por el último dígito: 0 a 6 NORMAL, 7 CPP, 8 DEFICIENTE, 9 DUDOSO), nombres `Lucía Mamani Torres`, un celular de 9 dígitos que empiece con 9 y un correo. Canal AGENCIA, agencia `AQP01`.
- **Secuencia en el expediente:** consentimientos (los tres aceptados) → enviar el código OTP por SMS (el código es simulado y la pantalla lo muestra con «usar») → verificarlo → validaciones RENIEC, listas restrictivas y PEP → central de riesgo SBS → calcular el perfil → habilitar.
- **Peticiones:** `/api/captacion/solicitantes`, `/casos`, `/casos/{id}/consentimientos`, `/otp`, `/otp/verificar`, `/validaciones`, `/consultas-riesgo`, `/perfil`, `/habilitar` (CAPTACION por el Bus → COREDB).
- **Resultado:** el caso queda HABILITADO y CAPTACION crea el cliente en COREDB (por ejemplo `CLI000000002`), ACTIVO y HABILITADO.
- **Comprobar:** `curl -s "${H[@]}" $BUS/bus/coredb/coredb/clientes/<cod_cliente>` → `estado_cliente: ACTIVO`, `estado_habilitante: HABILITADO`.
- Un cliente creado OBSERVADO (por ejemplo con `POST /coredb/clientes`) no sirve para este flujo: TARJETAS no le emite tarjeta (ERR-TAR-001) y SOL no lo encuentra en CAPTACION.

### 1b. Abrir la cuenta de ahorros

- **Pantalla:** http://localhost:3000/cuenta, pestaña de apertura («Crear cuenta de ahorros»): titular `<cod_cliente>`, PEN, INDIVIDUAL, agencia `AQP01`. La pantalla no genera nada: el empleado escribe el número de cuenta (14 dígitos) y el CCI (20 dígitos). Quién asigna esos números es una pregunta abierta del equipo.
- **Petición:** `POST /api/cuenta/apertura` (CUENTAS → COREDB).
- **Resultado:** cuenta de 14 dígitos, saldo **0.00**.

### 1c. Emitir y activar la tarjeta, asignar el PIN

- **Pantalla:** http://localhost:3000/tarjetas.
  1. «Emitir tarjeta de débito»: cliente `<cod_cliente>` y su cuenta. Queda PENDIENTE_ACTIVACION.
  2. Activarla (ACTIVA).
  3. «Claves de la tarjeta»: PIN_ATM de 4 dígitos.
- **Peticiones:** `POST /api/tarjeta/emision` (con `X-Idempotency-Key`), `POST /api/tarjeta/{id}/estado` `{"estado":"ACTIVA"}`, `PUT /api/tarjeta/{id}/credenciales/PIN_ATM` (TARJETAS → COREDB).
- **Resultado:** tarjeta **ACTIVA** con su PIN. Anote el `id_tarjeta` (UUID): es lo que se escribe en el cajero.

### 2a. Pedir el crédito de 1000.00

- **Pantalla:** http://localhost:3000/solicitud-credito, con el usuario ASESOR.
- **Datos:** buscar al cliente por su DNI; monto **1000.00** (el mínimo de la política de SOL, `backend/SOL/config/politica_demo.json`: 1000.00 a 50000.00, 6 a 60 meses, TEA 22 %, sistema francés), PEN, **6 meses**, destino «Capital de trabajo», fecha base mañana, sin garantías ni fiadores. Guardar el borrador y enviarlo.
- **Peticiones:** `/api/solicitud-credito/auth/login`, `clients/search` (SOL → CAPTACION, CR-INT-01), `applications` (borrador REGISTRADA en COREDB), `applications/{id}/send` (SOL → EVALUACION, CR-INT-02). Todo por el Bus.
- **Resultado:** solicitud **EN_EVALUACION**, con su calendario PRELIMINAR en COREDB.

### 2b. Evaluar la solicitud

- **Pantalla:** http://localhost:3000/evaluacion, con `admin`. Abrir la solicitud y evaluarla: versión 1, ingreso mensual 3500.00, deuda mensual 0.00, riesgo BUENO, verificada.
- **Petición:** `POST /api/evaluacion/solicitudes/{id}/evaluaciones` (EVALUACION → COREDB).
- **Resultado:** **APROBADO** por la regla; la solicitud pasa a APROBADA. En el siguiente ciclo, EVALUACION devuelve el resultado a SOL (CR-INT-03), que lo anota en la bitácora (`RECIBIR_CR_INT_03`).

### 3. Desembolsar

- **Pantalla:** http://localhost:3000/desembolso, con el usuario OPERADOR.
  1. «Verificar identidad» del cliente (DNI, identidad verificada).
  2. Elegir la aprobación y la cuenta de abono (la del paso 1b) y pulsar «Preparar desembolso». La pantalla crea la orden y le registra sola la validación de identidad: la orden queda **VALIDADA**.
  3. En la página de la orden, «Confirmar desembolso».

  El operador hace tres acciones; no hay un paso aparte para validar la orden.
- **Peticiones:** `/api/desembolso/identidad`, `aprobaciones?codCliente=`, `clientes/{cod}/cuentas?moneda=PEN`, `ordenes` (con `X-Idempotency-Key`), `ordenes/{id}/validaciones`, `ordenes/{id}/confirmacion` (DESEMBOLSO → COREDB).
- **Resultado:** orden CONFIRMADA (`DES-2026-…`), crédito `CRE-2026-…` **AL_DIA** con 6 cuotas, solicitud DESEMBOLSADA con calendario OFICIAL. Saldo **1000.00**.
- **Calendario obtenido** (1000.00, 6 meses, TEA 22 %, francés): cuotas de 176.55 (la última 176.54), total 1059.29; capital 159.84, 162.51, 165.23, 167.99, 170.79 y 173.64.
- **Comprobar:** `curl -s "${H[@]}" $BUS/bus/coredb/coredb/creditos/<cod_credito>` (estado, `cuotas`, `eventos` con CREAR_CREDITO).

### 4. Consultar el saldo en el cajero

- **Pantalla:** http://127.0.0.1:8019. El operador abre el cajero con su usuario de COREDB; el cliente escribe su `id_tarjeta` y su PIN y elige «Consultar saldo».
- **Peticiones:** `POST /api/apertura` (200), `POST /api/validar-pin` (200, EXITOSO, abre la sesión de la tarjeta), `GET /api/saldo?id_tarjeta=` con `X-ATM-Sesion` (ATM → TARJETAS y CUENTAS `/consolidada` por el Bus).
- **Resultado:** la pantalla muestra la cuenta de la tarjeta (`****` y los últimos 4 dígitos) con **S/ 1000.00**. Solo aparece la cuenta vinculada a la tarjeta, aunque el cliente tenga otras: es la única que el cajero puede operar.
- **Retiro desde la pantalla:** «Retirar efectivo» usa la misma consulta para elegir la cuenta; luego `POST /api/autorizar` (retiene) y `POST /api/confirmar` (debita), cada uno con su `X-Idempotency-Key`. Este flujo no retira, para que el saldo final siga siendo 1500.00.
- **Antes de #128** esta consulta respondía 500 («SaldoOut() argument after ** must be a mapping, not list») y la pantalla tampoco podía retirar.

### 5. Depositar 1000.00 en ventanilla

- **Pantalla:** http://localhost:3000/cuenta, «Depositar y hacer transferencias», operación Depositar: cuenta del cliente, monto **1000.00**.
- **Petición:** `POST /api/cuenta/deposito` con `X-Channel-ID: VEN` (la pantalla opera como ventanilla), `X-Idempotency-Key` y `X-Request-Timestamp` (CUENTAS → COREDB). Ventanilla no tiene tope diario.
- **Resultado:** depósito registrado; repetirlo con la misma llave devuelve el mismo movimiento (`replay: true`) y no deposita otra vez. Saldo **2000.00**.

### 6a. Afiliar la billetera y registrar el comercio

- **Pantalla:** http://localhost:3000/billetera (#134), con dos pestañas: «Afiliar cliente» (código de cliente, cuenta en soles y PIN de 6 dígitos) y «Registrar comercio» (RUC, razón social y cuenta del comercio).
- **Por curl**, con el token del administrador (es lo que hace `scripts/flujo_demo.py`):

1. Afiliar al cliente, con su cuenta y un PIN de 6 dígitos:
   ```bash
   curl -s "${H[@]}" -X POST $BUS/bus/coredb/coredb/billetera/afiliaciones \
     -d '{"cod_cliente":"<cod_cliente>","num_cuenta":"<num_cuenta>","pin":"<6 dígitos>"}'
   ```
   → 201, `estado: ACTIVA`.
2. El comercio necesita su propia cuenta en soles: su dueño pasa por los pasos 1a y 1b (en la corrida, «Marco Condori Apaza»). Después:
   ```bash
   curl -s "${H[@]}" -X POST $BUS/bus/coredb/coredb/billetera/comercios \
     -d '{"ruc":"20<9 dígitos>","razon_social":"Bodega Demo","num_cuenta":"<cuenta del comercio>"}'
   ```
   → 201, con `id_comercio` y su QR estático.

### 6b. Pagar 500.00 con la billetera

La app Chaski (Flutter, `billetera-chaski/app_movil`) funciona contra la API integrada desde #135: se compila con `--dart-define=SERVIDOR=http://localhost:8020` y, con el celular por USB, `adb reverse tcp:8020 tcp:8020` (ver `billetera-chaski/README.md`). Sin celular, la misma API se usa con curl, por el Bus (`/bus/billetera/api`) o directo en http://127.0.0.1:8020/api.

```bash
SES=$(curl -s -X POST $BUS/bus/billetera/api/login -H "X-Bus-Token: $BT" -H 'Content-Type: application/json' \
  -d '{"celular":"<celular del cliente>","pin":"<PIN de la billetera>"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
curl -s $BUS/bus/billetera/api/comercios -H "X-Bus-Token: $BT" -H "Authorization: Bearer $SES"   # id_qr del comercio
curl -s -X POST $BUS/bus/billetera/api/qr/<id_qr>/pagar -H "X-Bus-Token: $BT" -H "Authorization: Bearer $SES" \
  -H 'Content-Type: application/json' -H "Idempotency-Key: $(python3 -c 'import uuid;print(uuid.uuid4())')" -d '{"monto":500}'
```

- **Resultado:** pago registrado (canal BD). Repetirlo con la misma `Idempotency-Key` devuelve el mismo pago (`repetida: true`). Saldo del cliente **1500.00**; cuenta del comercio 500.00.
- **Topes:** 500.00 es a la vez el máximo por operación de la billetera (`MAX_OPERACION` en `billetera-chaski/backend/server.js`) y el tope diario del canal BD (`core.limite_canal`). Comprobado: 501.00 se rechaza («El límite por operación es S/ 500»), 500.00 pasa y 1.00 más el mismo día se rechaza («Superaste el tope diario de S/ 500 de la billetera», RN-TOP-001).

### 7. Bloquear la tarjeta

- **Pantalla:** http://localhost:3000/homebanking/index.html, con el usuario del banco y el código del cliente; en «Cuentas por tarjeta», «Mis tarjetas», botón **«Bloquear»** de la tarjeta ACTIVA. La pantalla pide confirmación («¿Bloquear la tarjeta terminada en …?») y, al aceptar, muestra «Tarjeta terminada en … bloqueada. Ya no se acepta en el cajero.».
- **Petición:** `POST /api/tarjeta/{id}/bloqueo` `{"motivo":"Bloqueo solicitado por el cliente en Home Banking"}` (puente del frontend → Bus → TARJETAS → COREDB). El personal también puede hacerlo en http://localhost:3000/tarjetas, «Bloquear o cambiar el estado».
- **Resultado:** tarjeta **BLOQUEADA**. El cajero ya no la acepta: `POST /api/validar-pin` responde 400 `ERR-ATM-TARJETA-NO-OPERATIVA`. El desbloqueo no se hace en TARJETAS ni en el Home Banking (403): lo hace Seguridad.
- **Quién entra al Home Banking:** un usuario del banco con su clave de COREDB, que escribe el código del cliente que atiende (decisión 14 de [`decisiones-del-equipo.md`](decisiones-del-equipo.md)). Que entre el propio cliente sigue siendo una pregunta del equipo.

### 8. Comprobar en COREDB

Con curl (los ejemplos de arriba) o con el script, que lo comprueba todo:

| Qué | Petición | Esperado |
|---|---|---|
| Saldo del cliente | `GET /coredb/cuentas/<num_cuenta>` | `saldo_disponible: 1500.00` |
| Movimientos | `GET /coredb/movimientos/cuenta/<num_cuenta>` | DESEMBOLSO C 1000.00 (VEN), DEPOSITO C 1000.00 (VEN), TRANSFERENCIA_ENVIADA D 500.00 (BD) |
| Crédito | `GET /coredb/creditos/<cod_credito>` | AL_DIA, `montoDesembolsado` 1000.00, 6 cuotas PENDIENTE cuyo capital suma 1000.00, evento CREAR_CREDITO |
| Solicitud | `GET /coredb/creditos/solicitudes/<id>` | DESEMBOLSADA, calendario OFICIAL |
| Tarjeta | `GET /api/tarjeta/<id_tarjeta>` (frontend) | BLOQUEADA |
| Bitácora | `GET /coredb/auditoria?id_entidad=<id>` | ver abajo |

Eventos que deja el flujo en la bitácora (`core.evento_auditoria`), con quién los hizo:

| Entidad | Acción | Actor |
|---|---|---|
| cliente | REGISTRAR_CLIENTE | `svc-captacion` |
| cuenta | ABRIR_CUENTA | `admin` |
| tarjeta | EMITIR_TARJETA, CAMBIAR_ESTADO_TARJETA (activación y bloqueo), REGISTRAR_CREDENCIAL | `admin` |
| solicitud | CREAR_BORRADOR, ENVIAR_CR_INT_02 | la asesora |
| solicitud | REGISTRAR_SOLICITUD | `svc-evaluacion` |
| evaluación | EVALUAR_SOLICITUD | `admin` |
| solicitud | RECIBIR_CR_INT_03 | `servicio:EVALUACION` (llega hasta un minuto después) |
| movimiento del abono | DESEMBOLSO | el operador |
| movimiento del depósito | DEPOSITO | `admin` |
| afiliación | AFILIAR | `admin` |
| operación de la billetera | OPERACION_QR | `cliente:<cod_cliente>` |

## El script

```bash
python3 scripts/flujo_demo.py            # el flujo entero, con un cliente nuevo
python3 scripts/flujo_demo.py -v         # además, cada petición con su estado
python3 scripts/flujo_demo.py --json r.json   # guarda cada paso (sin claves) en un JSON
```

Hace las mismas peticiones que las pantallas, por los puentes del frontend (`http://localhost:3000/api/...`), y va al Bus donde no hay pantalla (afiliación, comercio, billetera, cajero). Lee las claves de `.env` y no imprime ninguna (ni el DNI, el celular o los PIN, que genera al azar). Cada corrida crea su propio cliente, su comercio y sus usuarios, así que se puede repetir sobre la misma base. Otras direcciones: `BNA_FRONTEND` y `BNA_BUS`.

Por cada paso imprime dónde (pantalla y ruta), con qué usuario, el resultado y el saldo o estado después, y al final la comprobación en COREDB. Sale con:

- **0** y «Flujo de demostración completo.»: todo pasó.
- **1**: un paso falló; imprime cuál y la respuesta.

Corrido dos veces seguidas el 2026-11-19 sobre la misma base (`main` `aa500a6`, con #128 y #129): las dos terminaron con 0 («Flujo de demostración completo.»), saldo final 1500.00.

## Errores frecuentes

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `Falta BNA_ADMIN_PASSWORD` o `BUS_TOKEN_PRUEBAS` | No hay `.env` | `./bna up` lo crea |
| 401 `BUS_CREDENCIAL_INVALIDA` en un curl | Falta `X-Bus-Token` | Agregar `-H "X-Bus-Token: $BT"` |
| TARJETAS responde ERR-TAR-001 al emitir | El cliente no está ACTIVO (por ejemplo, creado OBSERVADO) | Crear el cliente por `/captacion` |
| SOL no encuentra al cliente | El cliente no viene de CAPTACION, o su verificación venció | Crear el cliente por `/captacion` |
| SOL rechaza el monto (422 «Monto permitido…») | Fuera de 1000.00–50000.00 o de 6–60 meses | Ajustar a la política |
| La evaluación queda OBSERVADO | Zona gris de la regla (cuota alta respecto del ingreso) | Subir el ingreso o decidir con un usuario ANALISTA registrado como analista |
| La billetera rechaza el pago con «límite por operación» o RN-TOP-001 | Más de 500.00 en una operación o en el día | Pagar 500.00 o menos; el tope se renueva al día siguiente |
| El celular de la billetera da 401 | La billetera no está afiliada o el PIN no es el de la afiliación | Repetir la afiliación (cambia el PIN) |
| `./bna down -v` deja volúmenes | Ocurrió en versiones anteriores | `docker compose -p bna down -v` y `docker volume ls` |

## Lo que sigue sin pantalla

Ningún paso está bloqueado y todos tienen pantalla: afiliar la billetera y registrar comercios en `/billetera` (#134) y el pago en la app Chaski (#135, `billetera-chaski/README.md`). Queda por curl, sin pantalla, lo que el script hace por el Bus (por ejemplo, crear usuarios internos con `POST /coredb/usuarios`).

Ningún paso falló por un dato de referencia que falte: la agencia `AQP01`, los terminales `DEV-*`, el BIN `004499`, los periodos contables y los topes por canal los carga `database/sql/bna_datos_dev.sql` al crear el volumen.

## Kubernetes

Hay dos despliegues en Kubernetes, con los mismos manifiestos de `k8s/base`:

- **kind, local:** `./bna k8s-up` (`k8s/overlays/local`, detalles en [`k8s/README.md`](../k8s/README.md)). Publica el frontend en http://localhost:13000 y el Bus en http://127.0.0.1:18018; el script se corre con `BNA_FRONTEND=http://localhost:13000 BNA_BUS=http://127.0.0.1:18018 python3 scripts/flujo_demo.py`, con el mismo `.env` con el que se creó el Secret. El cajero y la billetera no tienen NodePort: el script llega a ellos por el Bus.
- **Clúster de Infraestructura (k3s):** `k8s/overlays/infraestructura` y `scripts/k8s-infra.sh`, guía en [`despliegue-infraestructura.md`](despliegue-infraestructura.md). Publica por Ingress el portal (http://bna.172.16.10.31.sslip.io, también `/homebanking/index.html`), el cajero (http://bna-cajero.172.16.10.31.sslip.io), la API de la billetera (http://bna-billetera.172.16.10.31.sslip.io) y el Bus (http://bna-bus.172.16.10.31.sslip.io). Allí no hay Secrets ni `.env` local: `scripts/k8s-infra.sh flujo` corre este script, que lee sus tres claves de los pods con `kubectl exec`. Los datos de referencia (agencia, terminales, BIN, periodos) los carga la imagen de la base y los completa `scripts/k8s-infra.sh datos`.

En el clúster de Infraestructura `kubectl port-forward` no sirve: la API lo rechaza («cannot create resource pods/portforward»), aunque `kubectl auth can-i create pods/portforward` diga que sí (comprobado el 2026-11-20 con kubectl 1.37, por WebSocket y por SPDY). Se llega a los servicios por los hosts de los Ingress de arriba.

Para la demostración en el clúster, en la tabla de pasos cambian las direcciones: el portal es http://bna.172.16.10.31.sslip.io en vez de http://localhost:3000, el cajero http://bna-cajero.172.16.10.31.sslip.io en vez de http://127.0.0.1:8019 y el Bus http://bna-bus.172.16.10.31.sslip.io en vez de http://127.0.0.1:8018. La clave del administrador se lee como dice la guía (sección «Flujo de demostración»).

En kind (donde `kubectl port-forward` funciona) lo comprueba `scripts/prueba_k8s_infra_kind.sh` (kind v0.30.0, Kubernetes 1.34) con el overlay de Infraestructura: corre este script por `kubectl port-forward` al frontend y al Bus y exige que termine con 0. La CI lo corre en cada PR que toca el despliegue (flujo «Kubernetes»).
