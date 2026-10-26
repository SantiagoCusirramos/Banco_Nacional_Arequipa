# Banco Nacional de Arequipa — ERP Monolítico Modular

Sistema ERP bancario desarrollado como proyecto académico en la UCSM. Arquitectura modular con Bus de Servicios central, backend en FastAPI y frontend en Next.js.

---

## Estructura del repositorio

```
Banco_Nacional_Arequipa/
├── backend/          # API REST (FastAPI + Python)
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/         # Home Banking / UI (Next.js + TypeScript)
│   ├── app/
│   ├── package.json
│   └── ...
└── Documents/        # Stack tecnológico y guías
```

---

## Requisitos previos

Verifica que tengas instalado:

| Herramienta     | Versión mínima | Verificación               |
|-----------------|----------------|----------------------------|
| Git             | 2.40+          | `git --version`            |
| Python          | 3.11+          | `python3 --version`        |
| Node.js         | 20.x LTS       | `node --version`           |
| npm             | 10.x           | `npm --version`            |
| Docker          | 24.x           | `docker --version`         |
| Docker Compose  | 2.20+          | `docker compose version`   |

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone git@github.com:SantiagoCusirramos/Banco_Nacional_Arequipa.git
cd Banco_Nacional_Arequipa
```

---

### 2. Backend (FastAPI)

#### 2.1 Crear y activar el entorno virtual

```bash
cd backend
python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

#### 2.2 Instalar dependencias

```bash
pip install -r requirements.txt
```

#### 2.3 Configurar variables de entorno

```bash
cp .env.example .env
```

Edita el archivo `.env` y completa los valores reales (base de datos, claves secretas, etc.).

#### 2.4 Ejecutar el servidor de desarrollo

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El backend quedará disponible en `http://localhost:8000`.  
Documentación automática: `http://localhost:8000/docs`

---

### 3. Frontend (Next.js)

#### 3.1 Instalar dependencias

```bash
cd frontend
npm install
```

#### 3.2 Ejecutar el servidor de desarrollo

```bash
npm run dev
```

El frontend quedará disponible en `http://localhost:3000`.

---

## Resumen de puertos

| Servicio   | URL                        |
|------------|----------------------------|
| Backend    | http://localhost:8000      |
| API Docs   | http://localhost:8000/docs |
| Frontend   | http://localhost:3000      |
| MySQL      | localhost:3306             |
| Bus de Servicios | http://localhost:9000 |

---

## Variables de entorno

Cada componente tiene su propio `.env.example`:

| Archivo                  | Descripción                        |
|--------------------------|------------------------------------|
| `backend/.env.example`   | Configuración de la API y base de datos |

Copia cada archivo como `.env` en la misma carpeta y completa los valores. **Nunca subas el `.env` al repositorio.**

---

## Autenticación

> 🚧 **Pendiente de implementación.** Hoy el backend (módulo CORE) no
> autentica peticiones: la función `autenticar()` existe en
> `backend/CORE/services/usuariossvc.py`, pero no está expuesta por ningún
> router, y el `actor` de la auditoría se recibe en el cuerpo de cada
> petición. Esta sección se completará cuando se integre el sistema JWT.

Contenido previsto:

- Endpoint `POST /core/auth/login` (credenciales inválidas → `401` con mensaje genérico).
- Formato del token JWT y expiración (`ACCESS_TOKEN_EXPIRE_MINUTES`, firma con `SECRET_KEY`).
- Uso del header `Authorization: Bearer <token>`.
- Dependencias `get_current_user` y `require_action(accion)` (validan contra el catálogo RBAC).
- El `actor` de trazabilidad se obtiene del token, nunca del body.
- Migración de hashes SHA256 a bcrypt en el primer login exitoso.

Más detalle: [`backend/CORE/README.md`](backend/CORE/README.md),
[`Documents/05-checklist-validacion.md`](Documents/05-checklist-validacion.md) y
[`Documents/06-revision-arquitectura-schemas.md`](Documents/06-revision-arquitectura-schemas.md).

---

## Stack tecnológico

Consulta [`Documents/01-stack-tecnologico.md`](Documents/01-stack-tecnologico.md) para el detalle completo del stack y las decisiones de arquitectura.

---

## Convenciones del proyecto

- Los montos siempre se manejan como `DECIMAL(15,2)`. Nunca `float`.
- Las monedas siguen ISO 4217: `PEN`, `USD`.
- El frontend **nunca** llama directamente al Core ni a los módulos. Toda petición pasa por el Bus de Servicios.
- Toda petición debe incluir el header `X-Correlation-ID` para trazabilidad.

---

<<<<<<< HEAD
=======
## Equipo

Proyecto académico — Universidad Católica de Santa María (UCSM), 2026.
>>>>>>> origin/main
