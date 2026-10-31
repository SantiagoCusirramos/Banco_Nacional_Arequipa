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
`/core/usuarios`, `/core/permisos`, `/core/auditoria` y `/core/reportes` exigen token y permiso, y toman el actor del token: el campo `actor` del cuerpo se ignora.

Pendiente: `/core/clientes`, `/core/cuentas`, `/core/movimientos`, `/core/tarjetas`, `/core/creditos` y `/core/catalogos` siguen sin token y con el actor del cuerpo, porque `backend/CUENTAS` y `frontend/` las llaman sin token. Hay que migrarlas junto con esos clientes.

## Configuración (.env)
```
SECRET_KEY=<openssl rand -hex 32>   # >= 32 caracteres en todo entorno
ALGORITHM=HS256                     # HS256 | HS384 | HS512
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Con una clave débil el backend no arranca (`CORE/config.py`), y `CORE/utils/tokens.py`
vuelve a comprobarla al emitir y validar cada token. Nunca reutilice los valores del
antiguo `backend/.env` versionado: están comprometidos.

## Decisiones
- El token solo lleva identidad (`sub`, `username`, `rol`, `iss`, `iat`, `exp`, `jti`, `type`); los permisos se consultan en cada petición, y el usuario se relee de BD (desactivar o cambiar de rol surte efecto inmediato).
- El algoritmo lo fija el servidor; `alg=none` y firmas ajenas se rechazan.
- Todo fallo de login responde el mismo 401, también el usuario inactivo. Cada login exitoso queda en `auditoria_evento` (acción `LOGIN`).
- Con los datos sembrados, el primer administrador entra con su usuario de la carga inicial; ya no se pueden crear usuarios sin token.
- Errores: 401 `TOKEN_REQUERIDO | TOKEN_INVALIDO | TOKEN_EXPIRADO | USUARIO_NO_VIGENTE | CREDENCIALES_INVALIDAS`; 403 `PERMISO_DENEGADO`.
