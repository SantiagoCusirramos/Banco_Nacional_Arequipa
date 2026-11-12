# Autenticación JWT en CORE

## Endpoints
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/core/auth/login` | Body `{"username","password"}` → `{access_token, token_type:"bearer", expires_in, usuario}` |
| GET | `/core/auth/me` | Requiere `Authorization: Bearer <token>` → perfil + acciones del rol |

## Proteger una ruta
```python
from fastapi import Depends
from CORE.dependencies import usuario_actual, requiere_permiso

# Solo autenticado
@router.get("/x")
def x(usuario = Depends(usuario_actual)): ...

# Autenticado + permiso del catálogo rbac.json
@router.get("", dependencies=[Depends(requiere_permiso("VER_AUDITORIA"))])
def ver_auditoria(...): ...
```

## Rutas protegidas
Todas las rutas de `/core` exigen `Authorization: Bearer <token>`, salvo `POST /core/auth/login`. El actor de cada escritura sale del token: el campo `actor` del cuerpo se ignora.

| Rutas | Qué exigen |
|---|---|
| `/core/auth/me`, `/core/catalogos/*` | Un token vigente (los catálogos no tienen acción en `rbac.json`) |
| `/core/clientes` | `VER_CLIENTE` (GET), `CREAR_CLIENTE` (POST), `MODIFICAR_CLIENTE` (PATCH) |
| `/core/cuentas` | `VER_CUENTA` (GET), `CREAR_CUENTA` (POST), `MODIFICAR_CUENTA` (PATCH) |
| `/core/movimientos` | `REGISTRAR_MOVIMIENTO` |
| `/core/tarjetas` | `VER_TARJETA` (GET), `CREAR_TARJETA` (POST), `BLOQUEAR_TARJETA` (`cambiar-estado`) |
| `/core/creditos` | `CREAR_SOLICITUD_CREDITO` (POST `solicitudes`), `VER_CREDITO` (GET `solicitudes/{id}`), `EVALUAR_CREDITO` (`evaluar`), `APROBAR_CREDITO` (`decision`), `CONSULTAR_DEUDA` (GET `deuda`), `REGISTRAR_PAGO` (POST `pagos`) |
| `/core/usuarios` | `CREAR_USUARIO`; `ASIGNAR_ROLES` en `{id}/rol` |
| `/core/permisos` | `GESTIONAR_PERMISOS` |
| `/core/auditoria` | `VER_AUDITORIA` |
| `/core/reportes` | `GENERAR_REPORTES` |

En `POST /core/creditos/solicitudes/{id}/decision` también se ignora el `id_analista` del cuerpo: se registra el empleado del usuario que decide (`usuario_sistema.id_empleado`), o ninguno si ese usuario no tiene empleado.

`CORE/tests/test_rutas_protegidas.py` falla si una ruta de `/core` distinta del login queda sin token.

## Configuración (.env)
```
SECRET_KEY=<openssl rand -hex 32>   # >= 32 caracteres en todo entorno
ALGORITHM=HS256                     # HS256 | HS384 | HS512
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Con una clave débil el backend no arranca (`CORE/config.py`), y `CORE/utils/tokens.py`
vuelve a comprobarla al emitir y validar cada token.

## Decisiones
- El token solo lleva identidad (`sub`, `username`, `rol`, `iss`, `iat`, `exp`, `jti`, `type`); los permisos se consultan en cada petición, y el usuario se relee de BD (desactivar o cambiar de rol surte efecto inmediato).
- El algoritmo lo fija el servidor; `alg=none` y firmas ajenas se rechazan.
- Todo fallo de login responde el mismo 401, también el usuario inactivo. Cada login exitoso queda en `auditoria_evento` (acción `LOGIN`).
- Con los datos sembrados, el primer administrador entra con su usuario de la carga inicial; crear usuarios exige token.
- Errores: 401 `TOKEN_REQUERIDO | TOKEN_INVALIDO | TOKEN_EXPIRADO | USUARIO_NO_VIGENTE | CREDENCIALES_INVALIDAS`; 403 `PERMISO_DENEGADO`.
