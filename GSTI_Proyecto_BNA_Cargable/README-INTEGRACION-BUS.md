# Integración con el módulo de Clientes (guía para el Bus de Servicios y los demás módulos)

Este documento explica **cómo conectarse al módulo de Clientes** del BNA. Está pensado sobre todo para el **Bus de Servicios** (que será el intermediario), pero los módulos consumidores —Banca en línea, Cajero automático, Agencias, Billetera digital, Cuentas, Tarjetas, Créditos y Seguridad— también deben conocerlo.

Comité responsable: **Clientes** (línea de negocio Ahorros) · líder: Eddu Germán Valeriano Cuba.

---

## 1. Qué ofrece Clientes

Tres operaciones HTTP/JSON:

| N.° | Operación | Para qué sirve |
|---|---|---|
| 1 | `POST /clientes/registrar` | Registra un cliente nuevo. Con DNI verifica nombres y fecha de nacimiento contra RENIEC |
| 2 | `POST /clientes/validar-documento` | Indica si un documento es válido (DNI contra RENIEC) y si la persona es cliente del banco |
| 3 | `POST /clientes/validar-biometria` | Valida una huella o un rostro (solo DNI) contra RENIEC e indica si la persona es cliente |

Toda solicitud —aceptada o rechazada— queda auditada en el Core.

## 2. Cómo se conectan las piezas

```
Módulos consumidores ──►  BUS  ──►  CLIENTES  ──(directo)──►  RENIEC
                                       │
                                       └──►  BUS  ──►  CORE
```

Hay **dos sentidos** de comunicación con el Bus:

| Sentido | Quién llama | Qué ruta | Credencial |
|---|---|---|---|
| **Entrante** | El Bus llama a Clientes | `/clientes/*` | El Bus presenta el **`CLIENTES_TOKEN`** |
| **Saliente** | Clientes llama al Bus | `/bus/core/*` (para hablar con el Core) | Clientes presenta el **`BUS_TOKEN`** |

Reglas de diseño que el Bus debe respetar:
1. **El Bus no llama a RENIEC.** Clientes consulta a RENIEC directamente; RENIEC se trata como un sistema externo.
2. El Bus solo **enruta**: reenvía el cuerpo JSON y el código HTTP tal cual, sin reglas de negocio ni transformación.
3. **No registrar cuerpos de petición** en los logs del Bus: pueden contener plantillas biométricas (datos sensibles).

Hoy el repositorio incluye un **mini-Bus** (`mini-bus/`) que cumple este papel y sirve de referencia; su tabla de rutas está en `mini-bus/app/main.py`.

## 3. Dónde está Clientes

| Desde | Dirección |
|---|---|
| Fuera del clúster (con la VPN WireGuard activa) | `http://172.16.10.31:31091` |
| Dentro del clúster (otro namespace) | `http://clientes.2022251091.svc.cluster.local:8000` (si el clúster no restringe el tráfico entre namespaces) |
| Dentro del namespace `2022251091` | `http://clientes:8000` |

Comprobación de vida (sin credenciales): `GET /salud` → `{"servicio":"clientes","estado":"ok"}`. Documentación interactiva: `GET /docs`.

## 4. Autenticación

Todas las rutas `/clientes/*` exigen la cabecera:

```
X-Service-Token: <CLIENTES_TOKEN>
```

- Sin cabecera o con un valor incorrecto → `401` `{"correcto":false,"codigo":"NO_AUTORIZADO",...}`.
- El valor **no está en el repositorio**: el comité de Clientes lo entrega por un canal privado. No lo publiques en Git, wikis ni capturas.
- Opcional: la cabecera `X-Request-ID` permite correlacionar logs entre módulos (el mini-Bus la genera y la propaga; Clientes no la exige).

## 5. Lo que debe exponer el Bus

### 5.1 Hacia los módulos consumidores → Clientes

| Método | Ruta pública del Bus | Se reenvía a Clientes |
|---|---|---|
| POST | `/bus/clientes/registrar` | `/clientes/registrar` |
| POST | `/bus/clientes/validar-documento` | `/clientes/validar-documento` |
| POST | `/bus/clientes/validar-biometria` | `/clientes/validar-biometria` |

Al reenviar, el Bus cambia la credencial: acepta la de su consumidor y envía `X-Service-Token: <CLIENTES_TOKEN>` a Clientes. Debe devolver **el mismo código HTTP y el mismo JSON**.

### 5.2 Desde Clientes → Core (a través del Bus)

Clientes **nunca** habla con el Core directamente; siempre entra por el Bus con `X-Service-Token: <BUS_TOKEN>`. Si el Core real/oficial es de otro comité, el Bus debe enrutar estas rutas hacia él:

| Método | Ruta en el Bus | Destino en el Core | Contenido |
|---|---|---|---|
| POST | `/bus/core/registrar-cliente` | `/interno/registrar-cliente` | Datos del cliente + `verificado_reniec`; responde `{"correcto":true,"cliente_id":N}` o `409 CLIENTE_DUPLICADO` |
| POST | `/bus/core/auditar-registro` | `/interno/auditar-registro` | Constancia de un registro rechazado antes de llegar al Core |
| POST | `/bus/core/validar-documento` | `/interno/validar-documento` | Registra la solicitud y, si `consultar` es verdadero, responde `{"registrado":bool,"fecha_coincide":bool\|null,"cliente":{...}\|null}` |
| POST | `/bus/core/validar-biometria` | `/interno/validar-biometria` | Registra la solicitud biométrica; responde `{"registrado":bool,"cliente":{...}\|null}` |
| GET | `/bus/core/solicitudes-registro` | `/interno/solicitudes-registro` | Listado para el panel (`limite`, `orden`) |
| GET | `/bus/core/solicitudes-validacion` | `/interno/solicitudes-validacion` | Listado para el panel (`limite`, `orden`) |

Los cuerpos exactos están en `core-simulado/app/main.py` (clases `RegistroCoreIn`, `AuditoriaRegistroIn`, `ValidarDocumentoCoreIn`, `ValidarBiometriaCoreIn`).

### 5.3 Requisitos técnicos para el Bus

- `Content-Type: application/json` en cuerpos y respuestas.
- **Tiempo de espera de al menos 30 s** hacia Clientes: la validación biométrica puede tardar unos segundos.
- **Tamaño de cuerpo**: una plantilla facial son 512 números (~10 KB); una de huella, hasta 64 KB en Base64. No imponga límites menores.
- Si el destino no responde, el Bus debe devolver `503` con el formato de error uniforme (sección 8). El mini-Bus usa `SERVICIO_NO_DISPONIBLE`.

## 6. Contrato de las operaciones

Valores comunes:

- `modulo_origen` (obligatorio en todas): `BANCA_LINEA`, `CAJERO_AUTOMATICO`, `AGENCIAS`, `BILLETERA_DIGITAL`, `CUENTAS`, `TARJETAS`, `CREDITOS` o `SEGURIDAD`. Identifica quién consulta; queda auditado.
- `tipo_documento`: `DNI`, `PASAPORTE` o `PTP`.
- Formato del número: **DNI** 8 dígitos; **PASAPORTE** 6–12 caracteres alfanuméricos; **PTP** 6–15. Se convierte a mayúsculas.
- `fecha_nacimiento`: `AAAA-MM-DD`, entre 1900-01-01 y hoy.
- Los cuerpos **no admiten campos adicionales**: un campo desconocido produce `422 DATOS_INVALIDOS`.

### 6.1 Registrar cliente — `POST /clientes/registrar`

| Campo | Regla |
|---|---|
| `modulo_origen`, `tipo_documento`, `numero_documento`, `fecha_nacimiento` | Ver arriba |
| `nombres`, `apellidos` | 1–100 caracteres. Con DNI se comparan con RENIEC sin tildes ni mayúsculas |
| `ingreso_mensual` | Número ≥ 0, hasta 2 decimales (se recomienda enviarlo como cadena, p. ej. `"2500.00"`) |
| `direccion` | 5–200 caracteres |
| `correo` | Correo electrónico válido |
| `telefono` | 7–15 dígitos, con `+` opcional |

```json
POST /clientes/registrar
{ "modulo_origen": "AGENCIAS", "tipo_documento": "DNI", "numero_documento": "70000002",
  "nombres": "María Elena", "apellidos": "Mamani Condori", "fecha_nacimiento": "1995-11-02",
  "ingreso_mensual": "2500.00", "telefono": "954123456",
  "direccion": "Av. Ejército 123, Arequipa", "correo": "maria@example.com" }
```
Respuesta `201`: `{"correcto":true,"cliente_id":1,"verificacion_reniec":true}`.
Con PASAPORTE/PTP no hay verificación externa: `verificacion_reniec:false` y un campo `aviso`.

### 6.2 Validar por documento — `POST /clientes/validar-documento`

Campos: `modulo_origen`, `tipo_documento`, `numero_documento`, `fecha_nacimiento`.

```json
{ "modulo_origen": "BANCA_LINEA", "tipo_documento": "DNI", "numero_documento": "70000001", "fecha_nacimiento": "1990-05-14" }
```
Respuesta `200`:
```json
{ "correcto": true, "identidad": "DNI_VALIDO", "registrado_bna": true,
  "cliente": { "id": 1, "nombres": "Juan Carlos", "apellidos": "Pérez Quispe" } }
```
- `identidad`: `DNI_VALIDO`, `DNI_NO_ENCONTRADO`, `DATOS_NO_COINCIDEN` o, para PASAPORTE/PTP, `PASAPORTE_NO_CONSULTADO` / `PTP_NO_CONSULTADO`.
- `cliente` (con nombres) solo aparece si la identidad es `DNI_VALIDO` y la fecha coincide con la registrada. Para pasaporte/PTP solo se devuelve `{"id":N}` y un `aviso`.
- `registrado_bna`: si la persona es cliente del banco.

### 6.3 Validar por biometría — `POST /clientes/validar-biometria`

Solo para **DNI**. Campos: `modulo_origen`, `tipo_documento` (`"DNI"`), `numero_documento`, `tipo_biometria`, `formato`, `codificacion`, `template`.

| Tipo | `formato` | `codificacion` | `template` |
|---|---|---|---|
| `HUELLA` | `ISO_19794_2_2005` | `"base64"` (obligatoria) | Cadena Base64 con la plantilla ISO 19794-2:2005 |
| `FACIAL` | `ARCFACE_EMBEDDING` | no se usa | Lista de **512 números** (embedding ArcFace) |

```json
{ "modulo_origen": "CAJERO_AUTOMATICO", "tipo_documento": "DNI", "numero_documento": "70000001",
  "tipo_biometria": "HUELLA", "formato": "ISO_19794_2_2005", "codificacion": "base64", "template": "<base64>" }
```
Respuestas `200`:
- Coincide: `{"correcto":true,"coincide":true,"registrado_bna":true,"cliente":{"id":1,"nombres":"...","apellidos":"..."}}`
- No coincide: `{"correcto":true,"coincide":false,"motivo":"NO_COINCIDE"}` — sin datos personales. Otros `motivo`: `DNI_NO_ENCONTRADO`, `SIN_PLANTILLA` (el ciudadano no tiene biometría registrada).

Umbrales (los aplica RENIEC): huella con puntaje Bozorth3 ≥ 50, calidad NFIQ2 ≥ 35 y ≥ 15 minucias; rostro con distancia coseno ≤ 0.68. Los módulos consumidores envían la **plantilla**, no la imagen; no hay detección de vida.

## 7. Cómo interpretar las respuestas

- **Un resultado de negocio negativo no es un error HTTP.** «No coincide», «DNI no encontrado» o «no es cliente» llegan como `200` con `correcto:true`. `correcto:false` solo aparece cuando hubo un error (secciones siguientes).
- Los datos personales solo se entregan si la identidad quedó verificada.

## 8. Errores

Formato uniforme: `{"correcto":false,"codigo":"...","mensaje":"..."}` (en `422` con `detalle` por campo).

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 401 | `NO_AUTORIZADO` | Falta o es incorrecto `X-Service-Token` |
| 409 | `CLIENTE_DUPLICADO` | El documento ya está registrado como cliente |
| 422 | `DATOS_INVALIDOS` | Formato o campos inválidos (ver `detalle`) |
| 422 | `DNI_NO_ENCONTRADO` | En el **registro**, el DNI no existe en RENIEC |
| 422 | `DATOS_NO_COINCIDEN` | En el **registro**, nombres o fecha no coinciden con RENIEC |
| 422 | `FORMATO_NO_SOPORTADO` | El formato de la plantilla no corresponde al tipo de biometría |
| 409 | `PLANTILLA_INCOMPATIBLE` | La plantilla registrada en RENIEC se creó con otra configuración y debe volver a registrarse |
| 503 | `RENIEC_NO_DISPONIBLE` | RENIEC no responde; la solicitud igual queda auditada |
| 503 | `BUS_NO_DISPONIBLE` / `SERVICIO_NO_DISPONIBLE` | El Bus no alcanza al Core o a Clientes |
| 500 | `ERROR_INTERNO` | Error no previsto |

Reintentos: son seguros en las validaciones. En `registrar`, tras un `503` verifique con `validar-documento` antes de reintentar; un reintento de un registro ya hecho devuelve `409`.

## 9. Probar la conexión (checklist)

Con la VPN activa y el `CLIENTES_TOKEN` que te entregó el comité:

```bash
# 1) Clientes está vivo
curl http://172.16.10.31:31091/salud

# 2) Operación directa a Clientes (equivale a lo que hará el Bus)
curl -X POST http://172.16.10.31:31091/clientes/validar-documento \
  -H "Content-Type: application/json" -H "X-Service-Token: $CLIENTES_TOKEN" \
  -d '{"modulo_origen":"BANCA_LINEA","tipo_documento":"PASAPORTE","numero_documento":"AB123456","fecha_nacimiento":"1985-07-09"}'
```

Para el Bus oficial, confirme:
- [ ] El Bus acepta las 3 rutas `/bus/clientes/*` y reenvía a `/clientes/*` con el `CLIENTES_TOKEN`.
- [ ] El Bus devuelve el mismo código HTTP y JSON que Clientes (incluidos `409`, `422` y `503`).
- [ ] El Bus expone las 6 rutas `/bus/core/*` y las enruta al Core, aceptando el `BUS_TOKEN` de Clientes.
- [ ] El Bus **no** contacta a RENIEC y **no** registra cuerpos de petición.
- [ ] Tiempo de espera ≥ 30 s y sin límite de cuerpo menor a 64 KB.

### Cambiar Clientes al Bus oficial
En el clúster, editar en `kubernetes/00-config.yaml` el valor `BUS_URL` (p. ej. `http://<servicio-del-bus>.<namespace>.svc.cluster.local:<puerto>`), actualizar `BUS_TOKEN` en el Secret con la credencial que dé el Bus oficial, aplicar con `kubectl apply -f kubernetes/00-config.yaml` y reiniciar: `kubectl -n 2022251091 rollout restart deploy/clientes`. No hace falta tocar código.

## 10. Datos de prueba

Con `scripts/cargar_datos_prueba.py` existen: DNI `70000001` Juan Carlos Pérez Quispe (1990-05-14, cliente, con huella), `70000002` María Elena Mamani Condori (1995-11-02, ciudadana sin ser cliente), `70000003` Luis Alberto Huamán Ccama (sin biometría); el `70000099` no existe. Cliente con pasaporte `AB123456` (1985-07-09) y con PTP `PTP2024001` (1992-01-30). Todos son **ficticios**.

## 11. Cambios y dudas

Cualquier cambio de contrato (campos, rutas, códigos de error) debe coordinarse con el comité de Clientes antes de aplicarse, para mantener esta guía y las pruebas al día.
