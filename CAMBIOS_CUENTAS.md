# Actualización y Conexión del Módulo de Cuentas con COREDB

Este documento detalla la integración del módulo de **Cuentas** (backend y frontend) con la base integrada y API **COREDB** del Banco Nacional de Arequipa.

---

## 1. Arquitectura y Conexión con COREDB

- **Propósito:** El backend de Cuentas (`backend/CUENTAS/`) y el frontend (`frontend/app/cuenta/`) operan utilizando exclusivamente **COREDB** (puerto `8012`) para todas las operaciones sobre cuentas de ahorros y transacciones.
- **Operaciones Integradas:**
  1. **Crear cuenta:** `POST /coredb/cuentas` (vía procedimiento almacenado `cuentas.abrir_cuenta`).
  2. **Ver una cuenta en específico:** `GET /coredb/cuentas/{num_cuenta}`.
  3. **Depositar / Retirar:** `POST /coredb/movimientos`.
  4. **Hacer transferencias:** `POST /coredb/movimientos/transferencias`.
  5. **Revisar movimientos:** `GET /coredb/movimientos/cuenta/{num_cuenta}`.
  6. **Ver un movimiento en específico:** `GET /coredb/movimientos/{uuid_transaccion}`.

---

## 2. Resumen de Puertos

| Servicio | Puerto Local | URL de Acceso | Descripción |
|---|---|---|---|
| **Frontend (Next.js)** | 3000 | `http://localhost:3000` | Interfaz principal y portal de banca |
| **Módulo de Cuentas (UI)** | 3000 | `http://localhost:3000/cuenta` | Interfaz de gestión y operaciones de cuentas |
| **MySQL (COREDB / Base)** | 3307 (3306 int.) | `localhost:3307` | Base de datos MySQL 8.4 con esquemas `core`, `cuentas`, etc. |
| **Backend CUENTAS** | 8001 | `http://localhost:8001` | API intermedia de Cuentas |
| **Backend COREDB** | 8012 | `http://127.0.0.1:8012` | API principal de la base integrada |
| **Backend CORE (Legado)** | 8000 | `http://localhost:8000` | ERP monolítico original |

---

## 3. Claves y Seguridad (JWT)

- **COREDB JWT Key (`CORE_DB_JWT_CLAVE`):** Clave simétrica preconfigurada para firmar y validar tokens JWT propios de COREDB (`iss: bna-coredb`):
  ```env
  CORE_DB_JWT_CLAVE=6b0591c3fb910b956535c59ecc9ccc8c24a23563266c365b8fed87eff4f2ce27
  ```
- **Aislamiento:** Los tokens emitidos por CORE no son válidos en COREDB, garantizando el aislamiento de seguridad por módulo.

---

## 4. Cambios Realizados en COREDB

- Se añadió el modelo SQLAlchemy `CtaTransaccion` apuntando a la tabla `cuentas.cta_transaccion`.
- Se implementaron los endpoints GET en `backend/COREDB/routers/movimientos.py` para listar movimientos por cuenta (`/cuenta/{num_cuenta}`) y consultar un movimiento específico por su UUID (`/{uuid_transaccion}`).
- Se actualizó el cliente HTTP de Cuentas (`backend/CUENTAS/core_client.py`) para apuntar a COREDB (`http://localhost:8012`).

---

## 5. Guía de Ejecución

### A. Despliegue Local (Sin Docker)

1. **Base de Datos:** Asegúrate de tener MySQL 8.4 corriendo en el puerto 3307 con los scripts de `database/`.
2. **Backend COREDB:**
   ```powershell
   cd backend
   pip install -r requirements-coredb.txt
   python -m uvicorn COREDB.main:app --host 127.0.0.1 --port 8012
   ```
3. **Backend CUENTAS:**
   ```powershell
   cd backend
   pip install -r requirements.txt
   python -m uvicorn CUENTAS.main:app --host 127.0.0.1 --port 8001
   ```
4. **Frontend:**
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

### B. Despliegue en Docker (Orquestador)

Para levantar todo el sistema integrado mediante Docker Compose:
```bash
docker compose up -d --build
```
El orquestador levantará secuencialmente la base de datos MySQL con healthchecks (`bna_core_db`), el backend COREDB (`coredb` en puerto 8012), el backend de cuentas (`cuentas` en puerto 8001) y el frontend Next.js (`frontend` en puerto 3000).

---

## 6. Directorio de Enlaces y Documentación

- **Interfaz de Cuentas:** `http://localhost:3000/cuenta`
- **Documentación Interactiva COREDB (Swagger):** `http://127.0.0.1:8012/docs`
- **Home Banking Principal:** `http://localhost:3000`
- **Módulo de Crédito (SOL):** `http://localhost:3000/solicitud-credito`
- **Documentación OpenAPI COREDB:** `backend/COREDB/openapi.json`
