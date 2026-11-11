> **MVP de Solicitud de Crédito:** para ejecutar la entrega local con MySQL, empieza por [EMPEZAR_AQUI_SOL.md](EMPEZAR_AQUI_SOL.md). La interfaz del módulo está en `/solicitud-credito` y usa un backend propio en el puerto 8011.

# Banco Nacional de Arequipa — ERP Monolítico Modular

Sistema ERP bancario desarrollado como proyecto académico en la UCSM. Arquitectura modular con Bus de Servicios central, backend en FastAPI y frontend en Next.js.

---

## Inicio rápido con Docker

Solo hace falta Docker con Compose 2.20 o superior y bash (en Windows, Git Bash o WSL2).

```bash
git clone https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa.git
cd Banco_Nacional_Arequipa
./bna up        # o: make up
./bna smoke     # comprueba el producto de extremo a extremo
```

`./bna up` crea `.env` con claves aleatorias (no se versiona), construye las imágenes, levanta todos los servicios y espera a que estén sanos. La primera vez tarda unos minutos. Al terminar muestra las direcciones:

| Servicio | Dirección |
|---|---|
| Frontend | http://localhost:3000 |
| COREDB, la API del CORE | http://127.0.0.1:8012/docs |
| CUENTAS | http://127.0.0.1:8001/docs |
| SOL | http://127.0.0.1:8011/docs |
| Seguridad | http://127.0.0.1:8013 |
| CORE legado | http://127.0.0.1:8000/docs |
| MySQL de la base integrada | 127.0.0.1:3307 |

El administrador de COREDB es `admin`; su contraseña está en `.env`, en `BNA_ADMIN_PASSWORD`.

| Orden | Qué hace |
|---|---|
| `./bna up` | Levanta todo |
| `./bna down` | Detiene y elimina los contenedores; conserva los datos |
| `./bna reset` | Elimina también los datos y vuelve a levantar desde cero |
| `./bna ps` | Estado de los servicios |
| `./bna logs [servicio]` | Registros en vivo |
| `./bna smoke` | Flujo de extremo a extremo: login, apertura de cuentas, depósito y transferencia |
| `./bna test` | Todas las suites de pruebas, en contenedores |

El resto de este documento describe la instalación manual de cada componente.

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

Cada persona crea su propio `backend/.env`. Ese archivo no se versiona.

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pega el resultado en `SECRET_KEY` y completa `DB_PASSWORD` con un valor propio. Sin una `SECRET_KEY` propia de al menos 32 caracteres, el backend no arranca y el error indica qué hacer.

No reutilices ningún valor del antiguo `backend/.env` versionado: están comprometidos.

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
| CUENTAS    | http://localhost:8001      |
| SOL        | http://127.0.0.1:8011      |
| COREDB     | http://127.0.0.1:8012      |
| Seguridad  | http://127.0.0.1:8013      |
| Frontend   | http://localhost:3000      |
| MySQL      | localhost:3306             |
| Bus de Servicios (previsto, aún no existe) | http://localhost:9000 |

---

## Variables de entorno

Cada componente tiene su propio archivo de ejemplo:

| Archivo                     | Copia                 | Descripción                             |
|-----------------------------|-----------------------|-----------------------------------------|
| `backend/.env.example`      | `backend/.env`        | Configuración de la API y base de datos |
| `backend/.env.sol.example`  | `backend/.env.sol`    | Módulo SOL                              |
| `backend/COREDB/.env.example` | `backend/COREDB/.env` | API COREDB                              |
| `backend/seguridad/.env.example` | `backend/.env.seguridad.local` | Módulo de Seguridad               |
| `.env.example`              | `.env` (lo crea `./bna up`) | Producto completo con Docker      |
| `frontend/.env.example`     | `frontend/.env.local` | URL del backend para el navegador       |
| `frontend/.env.sol.example` | `frontend/.env.local` (agregar) | Puente del frontend hacia SOL |

Copia cada archivo como se indica y completa los valores. **Nunca subas el `.env` al repositorio.**

---

## Autenticación

CORE emite tokens JWT con `POST /core/auth/login` y los valida con el header `Authorization: Bearer <token>`. `/core/usuarios`, `/core/permisos`, `/core/auditoria` y `/core/reportes` exigen token y permiso; las demás rutas de CORE todavía no.

Más detalle: [`backend/CORE/AUTH_JWT.md`](backend/CORE/AUTH_JWT.md) y
[`backend/CORE/AUTENTICACION.md`](backend/CORE/AUTENTICACION.md).

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

## Equipo

Proyecto académico — Universidad Católica de Santa María (UCSM), 2026.
