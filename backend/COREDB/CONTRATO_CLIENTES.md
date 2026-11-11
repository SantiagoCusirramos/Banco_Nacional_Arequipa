# Contrato de COREDB para el módulo Clientes

**Estado:** implementado en `backend/COREDB`. Pendiente de la revisión del equipo de Clientes (Eddu Valeriano): los cambios que pidan se hacen sobre estas rutas.
**Qué es:** las operaciones que el CORE ofrece a Clientes en `backend/COREDB`, la API sobre la base integrada (`database/`). La especificación exacta está en `openapi.json` y en `/docs`.
**Qué no es:** el contrato público de Clientes hacia los canales (`/api/v1/kyc/...`). Ese es del módulo Clientes. Este documento cubre solo el tramo Clientes → CORE.

## 1. Convenciones

- **URL base:** configurable, por ejemplo `CORE_BASE_URL=http://127.0.0.1:8012`. Cuando exista el Bus de Servicios apuntará al Bus. Todas las rutas empiezan con `/coredb`.
- **Autenticación:** `Authorization: Bearer <token>` en todas las rutas salvo `/coredb/auth/login` y `/coredb/salud` (sección 2).
- **Correlación:** cabecera `X-Correlation-ID` con un UUID. Es opcional: si falta, o no es un UUID, COREDB genera uno. Siempre vuelve en la respuesta, también en las de error, y queda en la bitácora y en `clientes.validacion_identidad`. Conviene enviar el mismo identificador que recibió Clientes del canal.
- **Cuerpos JSON estrictos:** un campo desconocido se rechaza con 422, y los textos deben ser cadenas JSON (`"70000001"`, no `70000001`).
- **Error de negocio:** `{"error": {"code": "CODIGO", "message": "texto"}}`.
- **Error de validación (422):** `{"detail": [{"loc": [...], "type": "..."}]}`. **No devuelve los valores recibidos.**
- **Datos personales:** ningún mensaje de error repite documentos, correos ni celulares.
- **Errores comunes a todas las rutas:**

| Estado | `code` | Cuándo |
|---|---|---|
| 401 | `TOKEN_REQUERIDO`, `TOKEN_INVALIDO`, `TOKEN_EXPIRADO`, `USUARIO_NO_VIGENTE` | Sin token, token malo o vencido, o usuario desactivado |
| 403 | `PERMISO_DENEGADO` | El rol no tiene el permiso de la ruta |
| 503 | `CONFLICTO_CONCURRENCIA` | La base no pudo completar por concurrencia; se puede reintentar |

## 2. Credenciales del módulo

Clientes se autentica con un **usuario de servicio** (rol `SERVICIO`, módulo `CLIENTES`). No usa una cuenta de persona ni un token compartido.

1. Un administrador del CORE lo crea con `POST /coredb/usuarios/servicios`, enviando `{"modulo": "CLIENTES", "username": "svc-clientes", "nombre": "Módulo Clientes"}`.
   - La respuesta trae el **secreto una sola vez**. El CORE solo guarda su hash bcrypt y no puede volver a mostrarlo.
2. Quien despliega Clientes pone el usuario y el secreto en su almacén de secretos, por ejemplo `CORE_USUARIO` y `CORE_SECRETO` en el `.env` (nunca en el repositorio).
3. Clientes inicia sesión:

   ```http
   POST /coredb/auth/login
   {"username": "svc-clientes", "password": "<secreto>"}
   ```

   ```json
   200 {"access_token": "…", "token_type": "bearer", "expires_in": 1800,
        "usuario": {"id_usuario": "…", "username": "svc-clientes", "rol": "SERVICIO", "modulo": "CLIENTES", "activo": true, …}}
   ```

   - Todo fallo de login responde **el mismo 401 `CREDENCIALES_INVALIDAS`**.
4. Clientes guarda el token y lo envía en cada llamada. Ante un 401 `TOKEN_EXPIRADO`, inicia sesión otra vez y repite la llamada una sola vez.
5. **Rotación:** `POST /coredb/usuarios/{id}/credencial` entrega un secreto nuevo, también una sola vez, y el anterior deja de servir.
6. **Revocación:** `POST /coredb/usuarios/{id}/estado {"activo": false}` corta el acceso en la siguiente llamada, aunque el token aún no venza.

El token de COREDB no sirve en la API `CORE` ni al revés: tienen claves y emisores distintos.

## 3. Permisos

| Ruta | Permiso | `SERVICIO:CLIENTES` | ASESOR | ADMINISTRADOR | Otros roles |
|---|---|---|---|---|---|
| `POST /coredb/clientes` | `CREAR_CLIENTE` | Sí (HABILITADO u OBSERVADO) | Sí (solo OBSERVADO) | Sí (solo OBSERVADO) | No |
| `POST /coredb/clientes/validaciones/documento` | `VALIDAR_IDENTIDAD` | Sí | Sí | No | No |
| `POST /coredb/clientes/{cod_cliente}/validaciones` | `VALIDAR_IDENTIDAD` | Sí | Sí | No | No |
| `GET /coredb/clientes/{cod_cliente}` | `VER_CLIENTE` | Sí | Sí | Sí | ANALISTA, OPERADOR, AUDITOR |
| `POST /coredb/clientes/{cod_cliente}/estado` | `MODIFICAR_CLIENTE` | Sí, **salvo BAJA** | Sí | Sí | No |
| `GET /coredb/catalogos/clientes` | autenticado | Sí | Sí | Sí | Sí |

- **Registro HABILITADO (punto R-01, por confirmar con Eddu y Santiago):** solo el usuario de servicio de Clientes puede registrar un cliente `HABILITADO`, porque es quien verificó la identidad contra RENIEC. El personal del banco registra solo `OBSERVADO`. Si se decide otra cosa, cambia en un solo lugar de COREDB.
- **BAJA:** es final y cancela todas las tarjetas del cliente, por eso solo la fija una persona con `MODIFICAR_CLIENTE`. El servicio puede fijar ACTIVO, OBSERVADO, BLOQUEADO y SUSPENDIDO.

## 4. Rutas

### 4.1 Registrar un cliente: `POST /coredb/clientes`

```json
{
  "tipo_documento": "DNI",
  "numero_documento": "70000001",
  "nombres": "Juan Carlos",
  "apellido_paterno": "Pérez",
  "apellido_materno": "Quispe",
  "correo": "juan@example.com",
  "celular": "954000002",
  "version_contrato": "v1",
  "estado_habilitante": "HABILITADO"
}
```

| Campo | Regla |
|---|---|
| `tipo_documento` | `DNI`, `CE`, `PTP` o `PASAPORTE` (ver `GET /coredb/catalogos/clientes`) |
| `numero_documento` | Hasta 12 caracteres. Se pasa a mayúsculas. DNI: 8 dígitos. CE: 9 a 12 letras o dígitos. **PTP: 9 dígitos.** Pasaporte: 6 a 12 letras o dígitos |
| `nombres`, `apellido_paterno` | Obligatorios, hasta 100. **Dos apellidos separados**, no un solo `apellidos` |
| `apellido_materno` | Opcional, hasta 100, o `null` |
| `correo` | Obligatorio, hasta 150. Se guarda en minúsculas y es **único** |
| `celular` | Exactamente 9 dígitos y empieza con 9 (`^9\d{8}$`), sin `+51` ni espacios. Es **único**. Normalizarlo es tarea de Clientes |
| `version_contrato` | Obligatorio, hasta 10: la versión del contrato que aceptó el cliente |
| `estado_habilitante` | `HABILITADO` (identidad verificada) u `OBSERVADO` |

- **Respuesta:** `201 {"cod_cliente": "CLI000000001", "estado_cliente": "ACTIVO", "estado_habilitante": "HABILITADO", "id_verificacion_captacion": "…"}`.
  - **El `cod_cliente` lo genera el CORE** (`CLI` y nueve dígitos).
  - HABILITADO da un cliente ACTIVO y OBSERVADO da un cliente OBSERVADO.
- **Errores:**

| Estado | `code` | Cuándo |
|---|---|---|
| 409 | `CLIENTE_DUPLICADO`, `CORREO_DUPLICADO`, `CELULAR_DUPLICADO` | El documento, el correo o el celular ya están registrados |
| 422 | `BNA-DOCUMENTO` | El número no cumple la regla de su tipo, o el tipo no existe |
| 422 | `DATOS_INVALIDOS` | Otra regla de la base |
| 422 | validación | Formato, como el celular o un campo vacío |
| 403 | `HABILITACION_NO_PERMITIDA` | Alguien que no es el servicio de Clientes pidió HABILITADO |

> **Importante: los 409 son información del CORE para Clientes.** Revelan que un documento, correo o celular ya pertenece a un cliente. Clientes **no debe reenviarlos tal cual al usuario final** antes de verificar su identidad.

Fuera de este contrato quedan `fecha_nacimiento`, `ingreso_mensual` y `direccion`, que no están en el maestro de clientes.

### 4.2 Verificar un documento: `POST /coredb/clientes/validaciones/documento`

La consulta por documento (RF-CLI-001). Clientes primero verifica la identidad (RENIEC, biometría, etc.) y luego pregunta al CORE.

```json
{"tipo_documento": "DNI", "numero_documento": "70000001", "identidad_verificada": true, "motivo": null}
```

- `motivo`: opcional, hasta 60. Es el motivo de Clientes cuando no pudo verificar, por ejemplo `RENIEC_NO_COINCIDE` o `RENIEC_NO_DISPONIBLE`. Queda en la bitácora.
- **Respuesta: siempre `201`**, con `{"id_validacion": 123, "resultado": "...", "motivo": "...", "cliente": {...} | null}`. **Nunca 404.**

| `identidad_verificada` | Situación en el CORE | `resultado` | `motivo` | `cliente` |
|---|---|---|---|---|
| `false` | cualquiera | `RECHAZADO` | `IDENTIDAD_NO_VERIFICADA` | `null` |
| `true` | no es cliente | `RECHAZADO` | `NO_ES_CLIENTE` | `null` |
| `true` | cliente que no está ACTIVO | `RECHAZADO` | `CLIENTE_NO_ACTIVO` | el cliente (con su estado) |
| `true` | cliente ACTIVO | `APROBADO` | `null` | el cliente |

- **Sin identidad verificada, la respuesta es la misma para un cliente y para quien no lo es**, salvo `id_validacion`. Así el CORE no revela si alguien es cliente del banco (hallazgo 4 de la revisión del PR #25).
- Cada llamada queda en `clientes.validacion_identidad` (tipo DOCUMENTO) y en la bitácora, con el usuario que la hizo y el `X-Correlation-ID`.
- El documento va en el cuerpo, nunca en la URL, para que no quede en registros de acceso.
- **Errores:** 422 si falta un campo o el formato es inválido.

### 4.3 Registrar otra validación: `POST /coredb/clientes/{cod_cliente}/validaciones`

Para los veredictos de huella, rostro, celular y correo que produce Clientes.

```json
{"tipo_validacion": "HUELLA", "resultado": "RECHAZADO", "motivo": "SIMILITUD_BAJA"}
```

- `tipo_validacion`: `HUELLA`, `FACIAL`, `CELULAR` o `CORREO`. `DOCUMENTO` se registra por la ruta 4.2.
- `resultado`: `APROBADO` o `RECHAZADO`.
- **Respuesta:** `201 {"id_validacion": 124}`.
- **Errores:** 404 `CLIENTE_NO_ENCONTRADO` (quien llama ya tiene el código, así que no revela nada nuevo); 422.

### 4.4 Consultar un cliente: `GET /coredb/clientes/{cod_cliente}`

```json
200 {"cod_cliente": "CLI000000001", "tipo_documento": "DNI", "numero_documento": "70000001",
     "nombres": "Juan Carlos", "apellido_paterno": "Pérez", "apellido_materno": "Quispe",
     "correo": "juan@example.com", "celular": "954000002", "estado_cliente": "ACTIVO",
     "permite_operar": true, "version_contrato": "v1", "id_verificacion_captacion": "…",
     "estado_habilitante": "HABILITADO", "fecha_verificacion": "2026-11-02T15:04:05.000000Z"}
```

Es la misma vista que devuelven las rutas 4.2 y 4.5. **Nunca incluye datos biométricos.** Si el código no existe, responde 404 `CLIENTE_NO_ENCONTRADO`.

No hay rutas para listar clientes ni para buscarlos por nombre, correo o celular.

### 4.5 Cambiar el estado: `POST /coredb/clientes/{cod_cliente}/estado`

```json
{"estado": "BLOQUEADO", "motivo": "Investigación de fraude"}
```

- `estado`: `ACTIVO`, `OBSERVADO`, `BLOQUEADO`, `SUSPENDIDO` o `BAJA` (`BAJA`, solo personas; ver la sección 3).
- `motivo`: obligatorio, de 1 a 255 caracteres. Queda en la bitácora.
- **Respuesta:** `200`, con la vista del cliente más `"estado_anterior"`.
- **Reglas:**
  - BLOQUEADO o SUSPENDIDO bloquean las tarjetas activas y por activar del cliente; BAJA las cancela todas.
  - **Reactivar al cliente no desbloquea sus tarjetas.** Eso lo hace el módulo de Seguridad.
  - **BAJA es final.**
  - Pedir el estado que ya tiene no cambia nada: responde 200 con `estado_anterior` igual al actual, sin nuevo evento.
- **Errores:**

| Estado | `code` | Cuándo |
|---|---|---|
| 404 | `CLIENTE_NO_ENCONTRADO` | El código no existe |
| 422 | `BNA-ESTADO` | Se intentó cambiar un cliente dado de baja, o el estado no existe |
| 422 | `BNA-MOTIVO` o validación | Falta el motivo |
| 403 | `PERMISO_DENEGADO` | El servicio pidió BAJA |

### 4.6 Catálogos: `GET /coredb/catalogos/clientes`

```json
200 {"tipos_documento": [{"codigo": "DNI", "descripcion": "Documento Nacional de Identidad",
                          "longitud_min": 8, "longitud_max": 8, "es_alfanumerico": false}, …],
     "estados_cliente": [{"codigo": "ACTIVO", "descripcion": "Cliente activo", "permite_operar": true}, …]}
```

Conviene que Clientes lea las reglas de documento de aquí en lugar de fijarlas en su código.

## 5. Cambios respecto al PR #25

| PR #25 | Este contrato |
|---|---|
| `id` entero que genera el Core simulado | `cod_cliente` texto (`CLI` y nueve dígitos), generado por el CORE |
| `apellidos` en un solo campo | `apellido_paterno` obligatorio y `apellido_materno` opcional |
| `telefono` de 7 a 15 caracteres, no único | `celular` de 9 dígitos que empieza con 9, único |
| `correo` hasta 120, no único | `correo` hasta 150, único |
| PTP de 6 a 15 alfanumérico; sin CE | PTP de 9 dígitos; CE de 9 a 12 alfanumérico |
| `verificado_reniec: true` en el cuerpo, aceptado de cualquiera | `estado_habilitante: HABILITADO`, aceptado solo del usuario de servicio de Clientes |
| `registrado_bna` aunque RENIEC rechace | Sin identidad verificada, la misma respuesta para cliente y no cliente |
| Sin estado del cliente | Estado del cliente; APROBADO solo si está ACTIVO |
| `BUS_TOKEN` compartido | Usuario de servicio propio y token con vencimiento |
| `fecha_nacimiento`, `ingreso_mensual`, `direccion` | Fuera del maestro de clientes |
| `X-Request-ID` por salto | `X-Correlation-ID` de extremo a extremo |

## 6. Pendiente (fuera de esta versión)

- **Límite de intentos:** no hay límite de intentos ni de frecuencia en la verificación por documento. El CORE confía en `identidad_verificada` del llamador autenticado y deja cada consulta con quien la hizo (en el espíritu de RF-CLI-005).
- **Login:** los intentos fallidos no se registran ni bloquean la cuenta, como en CORE (punto M2).
- **Más adelante:** códigos OTP (`codigo_verificacion`), cambio de correo o celular y enrolamiento biométrico en el CORE (decisiones D2 y D4).
- **Por confirmar:** quién puede registrar HABILITADO (R-01).

Dudas o cambios: comentarios sobre este documento o al equipo del CORE.
