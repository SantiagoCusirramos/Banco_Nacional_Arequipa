# database/

Esta carpeta es una copia de [bna-core-db](https://github.com/miguelpro324/bna-core-db),
rama `mysql`, en la etiqueta **`bd-v1.0-mysql`**.

**No se edita aquí.** Un cambio directo se perdería o chocaría con la siguiente
actualización. Todo cambio de la base va primero a bna-core-db: rama nueva desde
`mysql`, pruebas y etiqueta nueva. Esta nota es el único archivo propio de esta copia.

## Actualizar

Con la etiqueta ya publicada en bna-core-db, sobre la rama `mysql`, y el árbol limpio:

```bash
git subtree pull --prefix=database --squash https://github.com/miguelpro324/bna-core-db.git <nueva etiqueta>
```

- Usar siempre `--squash`: la historia de bna-core-db contiene la de este repositorio, y
  sin él se duplicarían sus commits.
- Hace falta un clon completo. En un clon superficial (`--depth`), `git subtree` no
  encuentra la importación anterior.
- La nueva etiqueta debe descender de la anterior. Por eso una etiqueta publicada no se
  mueve.
- Después de actualizar, cambiar la etiqueta de este archivo.

Nunca se abre un PR desde una rama de bna-core-db hacia este repositorio: su historia
borra todo este árbol.

## Usuarios

| Usuario | Rol | Para qué |
|---|---|---|
| `bna_app_user` | `bna_api` | API de `backend/COREDB`: ejecuta procedimientos y lee solo las tablas que usa; no lee credenciales ni datos biométricos |
| `bna_admin_user` | `bna_admin` | Datos de referencia y administración |
| `bna_seguridad_user` | `bna_seguridad` | Módulo de Seguridad: solo `tarjetas.desbloquear_tarjeta` |

**El desbloqueo de tarjetas está pendiente de un cliente de Seguridad.** La API de
`backend/COREDB` lo rechaza con 403 `BNA-DESBLOQUEO`, sea cual sea el origen, y
ningún cliente usa aún `bna_seguridad_user`. La restricción no cubre a `bna_admin`, ni
a `bna_app` si escribe el historial directamente; ninguna cuenta desplegada tiene `bna_app`.

## Levantar la base

Copiar `backend/COREDB/.env.example` a `backend/COREDB/.env` y completar las claves.

**En desarrollo**, con datos de referencia (periodo abierto del mes en curso, BIN 004499,
una agencia, un terminal por canal y el cliente `DEV001`), para que una base nueva pueda
hacer un depósito:

```bash
docker compose -f docker-compose.coredb.yml -f docker-compose.coredb.dev.yml \
  --env-file backend/COREDB/.env up -d --wait
```

**Sin datos de desarrollo**, sin el segundo archivo. En ese caso todo movimiento se
rechaza hasta que `bna_admin` cargue un periodo contable:

```bash
docker compose -f docker-compose.coredb.yml --env-file backend/COREDB/.env up -d --wait
```

Los scripts de inicio solo corren con un volumen vacío. Si una etiqueta nueva cambia el
esquema, o cambia el mes en desarrollo, hay que recrear el volumen, lo que borra sus datos:

```bash
docker compose -f docker-compose.coredb.yml --env-file backend/COREDB/.env down -v
```
