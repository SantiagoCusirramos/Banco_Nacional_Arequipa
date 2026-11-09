# COREDB: API de la base integrada

API FastAPI sobre la base de `database/`, aparte de la API de `CORE`, que no reemplaza.

> **Exige un JWT propio en toda ruta salvo `/coredb/salud` y el login.** No tiene TLS:
> no exponer fuera de la máquina sin un proxy con TLS delante.

## Clonar y levantar

Python 3.11. Desde la raíz del repositorio:

```bash
cp backend/COREDB/.env.example backend/COREDB/.env      # completar las claves y CORE_DB_JWT_CLAVE
docker compose -f docker-compose.coredb.yml -f docker-compose.coredb.dev.yml \
  --env-file backend/COREDB/.env up -d --wait
pip install -r backend/requirements-coredb.txt
cd backend
python -m COREDB.scripts.crear_administrador --username admin --nombre "Su nombre"   # una vez
uvicorn COREDB.main:app --host 127.0.0.1 --port 8012
```

El arranque falla si `CORE_DB_JWT_CLAVE` tiene menos de 32 caracteres o es el valor de
ejemplo (`openssl rand -hex 32`). Es otra clave que el `SECRET_KEY` de CORE.

## Autenticación

Portada del JWT de CORE (Nicolas Ayerve) y de `autenticar()` (Nino Flores), sobre la base
integrada y con PyJWT:

- `POST /coredb/auth/login` con `{"username", "password"}` entrega
  `{access_token, token_type, expires_in, usuario}`. Usuario inexistente, clave incorrecta,
  usuario inactivo y contraseña no admitida responden el mismo 401
  `CREDENCIALES_INVALIDAS`, y el tiempo se iguala con una verificación bcrypt simulada.
  Cada login exitoso queda en la bitácora (`LOGIN`), con el `X-Correlation-ID` si es un
  UUID. Los intentos fallidos no se registran ni bloquean la cuenta, como en CORE.
- Las demás rutas exigen `Authorization: Bearer <token>`. El token lleva `sub`,
  `username`, `rol`, `modulo`, `type`, `iss` (`bna-coredb`), `aud` (`coredb`), `iat`, `exp`
  y `jti`, todos obligatorios. El algoritmo lo fija el servidor (`CORE_DB_JWT_ALGORITMO`,
  HS256 por omisión). El usuario se relee en cada petición: desactivarlo o cambiarle el
  rol surte efecto de inmediato. Un token de CORE no sirve aquí.
- `GET /coredb/auth/me` devuelve el perfil y sus acciones.
- Errores: 401 `TOKEN_REQUERIDO | TOKEN_INVALIDO | TOKEN_EXPIRADO | USUARIO_NO_VIGENTE |
  CREDENCIALES_INVALIDAS`, con `WWW-Authenticate: Bearer`; 403 `PERMISO_DENEGADO`.

**Permisos:** `permisos.py` es un mapa versionado de rol a acciones. Los cinco roles de
personas son los de `CORE/data/rbac.json` en `a9bd70f`, y la API nunca lo escribe. La
acción propia `VALIDAR_IDENTIDAD` la tienen ASESOR y el usuario de servicio de Clientes.
Cada ruta declara su permiso con `requiere_permiso`; una prueba falla si una escritura no
lo declara o si una ruta, salvo las públicas, no exige token.

**Usuarios de servicio:** un módulo se autentica con su propio usuario (rol `SERVICIO` y
su módulo), nunca con una cuenta de persona:

1. Un administrador lo crea con `POST /coredb/usuarios/servicios`
   `{"modulo": "CLIENTES", "username": "svc-clientes", "nombre": "Módulo Clientes"}`. La
   respuesta trae el secreto **una sola vez** (`Cache-Control: no-store`); la base guarda su
   hash bcrypt.
2. Quien despliega el módulo guarda el usuario y el secreto en su almacén de secretos.
3. El módulo inicia sesión con ellos y repite el login ante un 401 `TOKEN_EXPIRADO`.
4. `POST /coredb/usuarios/{id}/credencial` entrega un secreto nuevo y anula el anterior;
   `POST /coredb/usuarios/{id}/estado {"activo": false}` corta el acceso en la siguiente
   petición.

**Primer administrador:** `python -m COREDB.scripts.crear_administrador` lo crea con las
credenciales de la base y pide la contraseña en la terminal. Se niega si ya hay un
administrador activo.

**Pendiente:** ningún límite de intentos de login ni de frecuencia.

El segundo archivo carga datos solo de desarrollo; ver `database/README-UPSTREAM.md`.

Documentación interactiva: `http://127.0.0.1:8012/docs`. Especificación publicada:
`openapi.json`, que se regenera desde `backend/` con
`python -m COREDB.scripts.exporta_openapi`.

## Reglas

- **Conexión:** `bna_app_user`, con el rol `bna_api`: ejecuta procedimientos y lee solo las
  tablas que usa; un endpoint que lea otra necesita su `GRANT` en la base. La tarjeta se lee
  por `tarjetas.v_tarjeta_api`, sin `pan_token`. No lee credenciales ni datos biométricos.
  En UTC y modo estricto. El arranque falla si `core.verificar_configuracion()` no pasa.
- **Desbloqueo de tarjetas:** no disponible, pendiente de un cliente de Seguridad. La API
  responde 403 `BNA-DESBLOQUEO`, porque solo el rol `bna_seguridad` puede desbloquear.
- **Actor:** sale del token. Una cabecera `X-Actor` se ignora.
- **Origen de un cambio de estado de tarjeta:** no lo envía el cliente; sale del token:
  `OPERADOR` para personas, `MODULO_CLIENTES` para el usuario de servicio de Clientes y
  `SISTEMA` para otro módulo. Un cuerpo con `origen` se rechaza con 422.
- **Canal:** lo envía el cliente, y debe tener fila en
  `core.limite_canal` para debitar (ver `database/README.md`): por `AGE`, y por `HB` en USD,
  un débito se rechaza con `BNA-CANAL`; por `BD` en USD, con `RN-BD-002`.
- **Periodos:** sin un periodo contable para la fecha de negocio, todo movimiento se
  rechaza y esta API no puede crearlo. `docker-compose.coredb.dev.yml` carga el del mes
  en curso; en otro entorno lo carga `bna_admin`.
- **Escrituras:** siempre con `CALL` a un procedimiento (`database.llamar`). Una prueba
  rechaza `INSERT`, `UPDATE` o `DELETE` en este paquete.
- **Identificadores:** `BINARY(16)` en la base y `uuid.UUID` en Python (`UuidBinario`).
- **Cambios en la base:** primero en bna-core-db, nunca en `database/` (ver
  `database/README-UPSTREAM.md`).

## Pruebas

```bash
cd backend/COREDB && python -m pytest -q         # unitarias; integración omitida
backend/COREDB/scripts/pruebas_integracion.sh    # contra un contenedor nuevo
```
