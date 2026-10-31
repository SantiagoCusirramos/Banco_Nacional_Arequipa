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

## Configuración (.env)
```
SECRET_KEY=<openssl rand -hex 32>   # >= 32 caracteres en todo entorno
ALGORITHM=HS256                     # HS256 | HS384 | HS512
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

El `backend/.env` versionado no cumple esta regla y su clave ya es pública: quien
la conozca puede firmar tokens. Hasta que se rote, el login y las rutas protegidas
fallan con 500 en vez de emitir o aceptar tokens con esa clave.

## Decisiones
- El token solo lleva identidad (`sub`, `username`, `rol`, `iss`, `iat`, `exp`, `jti`, `type`); los permisos se consultan en cada petición, y el usuario se relee de BD (desactivar o cambiar de rol surte efecto inmediato).
- El algoritmo lo fija el servidor; `alg=none` y firmas ajenas se rechazan.
- Todo fallo de login responde el mismo 401, también el usuario inactivo. Cada login exitoso queda en `auditoria_evento` (acción `LOGIN`).
- Errores: 401 `TOKEN_REQUERIDO | TOKEN_INVALIDO | TOKEN_EXPIRADO | USUARIO_NO_VIGENTE | CREDENCIALES_INVALIDAS`; 403 `PERMISO_DENEGADO`.
