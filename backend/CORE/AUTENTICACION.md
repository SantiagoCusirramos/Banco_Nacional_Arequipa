# Autenticación en CORE

Cómo verifica CORE las credenciales y qué hace la capa HTTP con el
resultado. Cubre `CORE/utils/hashing.py` y `usuariossvc.autenticar()`.

## Almacenamiento de contraseñas

| `algoritmo_hash` | `version_hash` | Uso |
|---|---|---|
| `BCRYPT` | `v2` | Usuarios nuevos y usuarios ya migrados |
| `SHA256` | `v1` | Usuarios existentes y seeds, solo hasta su primer login |

Un hash bcrypt ocupa 60 caracteres y cabe en `hash_password CHAR(64)`, sin
cambiar el modelo. Argon2 no cabe, por eso se eligió bcrypt. Cualquier otro
valor de `algoritmo_hash` se deniega.

`bcrypt` está fijado en `4.0.1` en `requirements.txt` porque `passlib` 1.7.4
falla con bcrypt 5.x al generar el primer hash.

## Contrato de `autenticar()`

```python
usuariossvc.autenticar(db, username=..., password=...) -> UsuarioSistema
```

Retorna el objeto `UsuarioSistema`. `usuariossvc.vista_publica(usuario)` da los
campos que se pueden exponer: `id_usuario`, `username`, `nombre`, `rol`,
`id_empleado`, `activo`, `creado_en`. Los claims del token salen de ahí, nunca
de `hash_password`.

La función hace `commit` cuando migra un hash. Quien la llame no debe mezclarla
con cambios propios pendientes en la misma sesión.

## Estados

`activo` es el único estado. "Bloqueado" no existe en el modelo y equivale a
`activo = False`.

| Caso | Excepción | `code` | Estado HTTP de la excepción |
|---|---|---|---|
| Usuario inexistente | `NotFoundError` | `CREDENCIALES_INVALIDAS` | 404 |
| Clave incorrecta, activo o inactivo | `NotFoundError` | `CREDENCIALES_INVALIDAS` | 404 |
| Clave correcta, inactivo | `ValidationError` | `USUARIO_INACTIVO` | 422 |
| Clave correcta, activo | Ninguna | | |
| Contraseña sin UTF-8 válido | `ValidationError` | `PASSWORD_NO_ADMITIDA` | 422 |

Un hash corrupto se trata como clave incorrecta. La contraseña sin UTF-8 válido
se rechaza antes de consultar la BD, así que no revela nada del usuario.

## Lo que hace el login

`POST /core/auth/login` (`authsvc.iniciar_sesion`, ver `AUTH_JWT.md`):

1. Llama a `autenticar()`. No repite la verificación del hash.
2. Responde un único `401` genérico para `CREDENCIALES_INVALIDAS`,
   `USUARIO_INACTIVO` y `PASSWORD_NO_ADMITIDA`, con el mismo cuerpo. Los estados
   404 y 422 de la tabla son los del servicio y no llegan al cliente en esta ruta.
3. Emite el token con los datos del usuario.

```text
Cliente -> POST /core/auth/login -> usuariossvc.autenticar()
                                      |- usuario y hash verificados
                                      |- migración a bcrypt, si corresponde
                                      `- UsuarioSistema
Cliente <- token JWT <- router
```

## Migración desde SHA-256

Ocurre dentro de `autenticar()`, después de verificar la clave y el estado:

1. Un `UPDATE` condicional guarda el hash bcrypt, `BCRYPT` y `v2` solo si la fila
   sigue en `SHA256`.
2. Si actualizó la fila, se registra `MIGRAR_HASH_PASSWORD` en `auditoria_evento`,
   sin ningún hash. Con logins simultáneos, solo uno lo registra.
3. Se hace `commit`. Si falla, se revierte, el login válido continúa y la
   migración se reintenta en el siguiente login.

## Límites

- bcrypt solo usa los primeros 72 bytes y no admite el carácter nulo. CORE
  rechaza esas contraseñas, y las que tienen un surrogate aislado, al crear
  usuarios con `PASSWORD_NO_ADMITIDA`, en lugar de truncarlas.
- Una contraseña SHA-256 existente que bcrypt no admite sigue funcionando y
  permanece en SHA-256.
- El tiempo de respuesta se iguala en los fallos: el usuario inexistente, la
  clave incorrecta de un usuario SHA-256, la contraseña no admitida y el hash
  bcrypt nulo o malformado gastan una verificación bcrypt.

## Pruebas de integración

`CORE/tests/integracion/test_real_mysql.py` prueba este flujo contra un MySQL real.
Se omite salvo que `BNA_INTEGRACION_MYSQL=1`, porque escribe en la BD y necesita una
carga limpia: las semillas deben seguir en SHA-256. No se debe activar contra una BD
compartida. Desde `backend/`, con Docker, en bash:

```bash
docker run -d --name bna-prueba -e MYSQL_ROOT_PASSWORD=raiz-local \
  -p 127.0.0.1:3318:3306 mysql:8.4

# Esperar a que MySQL acepte conexiones y cargar el esquema base.
until docker exec bna-prueba mysql -uroot -praiz-local -e 'SELECT 1' >/dev/null 2>&1; do
  sleep 2
done
docker exec -i bna-prueba mysql -uroot -praiz-local --default-character-set=utf8mb4 \
  < "Infraestructura - BD/Trabajo_hecho/BD/99_bna_unificado.sql"
docker exec bna-prueba mysql -uroot -praiz-local -e "
  CREATE USER 'bna_user'@'%' IDENTIFIED BY 'app-local';
  GRANT SELECT, INSERT, UPDATE, DELETE ON bna.* TO 'bna_user'@'%';"

BNA_INTEGRACION_MYSQL=1 DB_HOST=127.0.0.1 DB_PORT=3318 DB_NAME=bna \
  DB_USER=bna_user DB_PASSWORD=app-local SECRET_KEY=prueba-local-con-al-menos-32-caracteres \
  python -m pytest CORE/tests/integracion -q

docker rm -f bna-prueba
```
