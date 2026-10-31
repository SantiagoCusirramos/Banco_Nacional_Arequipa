# COREDB: API de la base integrada

API FastAPI sobre la base de `database/`, aparte de la API de `CORE`, que no reemplaza.

> **Solo para uso local. No tiene autenticación.** No exponer fuera de la máquina ni
> desplegar. `auth.py` es una dependencia enchufable que espera el JWT de Nicolas
> Ayerve; hasta entonces, la cabecera `X-Actor` solo identifica a quien actúa en la
> auditoría y cualquiera puede escribirla.

## Clonar y levantar

Python 3.11. Desde la raíz del repositorio:

```bash
cp backend/COREDB/.env.example backend/COREDB/.env      # completar las claves
docker compose -f docker-compose.coredb.yml -f docker-compose.coredb.dev.yml \
  --env-file backend/COREDB/.env up -d --wait
pip install -r backend/requirements-coredb.txt
cd backend
uvicorn COREDB.main:app --host 127.0.0.1 --port 8012
```

El segundo archivo carga datos solo de desarrollo; ver `database/README-UPSTREAM.md`.

Documentación interactiva: `http://127.0.0.1:8012/docs`. Especificación publicada:
`openapi.json`, que se regenera desde `backend/` con
`python -m COREDB.scripts.exporta_openapi`.

## Reglas

- **Conexión:** `bna_app_user`, con el rol `bna_api`: solo lee y ejecuta procedimientos.
  En UTC y modo estricto. El arranque falla si `core.verificar_configuracion()` no pasa.
- **Desbloqueo de tarjetas:** no disponible, pendiente de un cliente de Seguridad. La API
  responde 403 `BNA-DESBLOQUEO`, porque solo el rol `bna_seguridad` puede desbloquear.
- **Actor:** viene de `X-Actor`, es decir, del cliente, hasta que exista el JWT.
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
