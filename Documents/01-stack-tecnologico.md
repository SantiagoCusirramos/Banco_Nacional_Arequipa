# Stack Tecnológico — Banco Nacional de Arequipa (BNA)

Este documento define el stack oficial del proyecto. Todo el equipo debe respetar estas decisiones. Cualquier cambio requiere aprobación del Comité de Tecnología.

---

## Backend

| Componente | Tecnología | Versión mínima | Uso |
|---|---|---|---|
| Lenguaje | Python | 3.11+ | Todos los módulos y el Bus de Servicios |
| Framework API | FastAPI | 0.110+ | Exposición de APIs REST/JSON |
| ORM | SQLAlchemy | 2.0+ | Acceso a base de datos |
| Migraciones | Alembic | 1.13+ | Versionado del esquema de BD |
| Validación | Pydantic | 2.x | Validación de contratos y schemas |
| Cliente HTTP | httpx | 0.27+ | Comunicación entre módulos vía Bus |
| Testing | pytest + pytest-asyncio | últimas | Pruebas unitarias e integración |

---

## Base de Datos

| Componente | Tecnología | Versión | Uso |
|---|---|---|---|
| Motor | MySQL | 8.0+ | Persistencia transaccional ACID |
| Engine | InnoDB | — | Transacciones, foreign keys, row locking |
| Charset | utf8mb4 | — | Soporte completo de caracteres |
| Colación | utf8mb4_0900_ai_ci | — | Comparación estándar |

**Reglas de datos obligatorias:**
- Montos: `DECIMAL(15,2)` — nunca `FLOAT` ni `DOUBLE`.
- Monedas: `CHAR(3)` con ISO 4217 (PEN, USD).
- Fechas: `DATETIME` para negocio, `TIMESTAMP` UTC para auditoría.
- Identificadores: UUID v4 (CHAR(36)) para transacciones.

---

## Frontend

| Componente | Tecnología | Versión | Uso |
|---|---|---|---|
| Framework | Next.js | 15+ (App Router) | Home Banking, Billetera Digital, Agencias |
| Lenguaje | TypeScript | 5.x | Tipado estricto en todo el frontend |
| Estilos | Tailwind CSS | 3.x | Diseño utilitario y responsive |
| Componentes | shadcn/ui | últimas | Componentes accesibles (basados en Radix) |
| Formularios | React Hook Form + Zod | últimas | Validación tipada en cliente |
| Estado global | Zustand | última | Estado de sesión y datos de usuario |
| HTTP Client | Axios | última | Con interceptores para tokens |

**Regla crítica de seguridad:**
El frontend **nunca** llama directamente al CORE ni a los módulos. Todas las llamadas pasan por el **Bus de Servicios**. Las URLs internas del Bus se manejan del lado del servidor de Next.js (Route Handlers), nunca en el cliente.

---

## Infraestructura y Contenedores

| Componente | Tecnología | Uso |
|---|---|---|
| Contenedores | Docker + Docker Compose | Desarrollo local y despliegue |
| Servidor | Kybernet | Hosting de contenedores en producción |
| Base de datos | MySQL 8.0 | Instancia dedicada por módulo o esquema lógico |
| Proxy inverso | Nginx (por definir) | Exposición de servicios |

---

## Comunicación entre componentes

| Origen | Destino | Protocolo |
|---|---|---|
| ATM / Cajero | Bus de Servicios | ISO 8583 |
| Home Banking | Bus de Servicios | HTTPS / REST |
| Billetera Digital | Bus de Servicios | HTTPS / REST |
| Agencias / Ventanilla | Bus de Servicios | REST |
| Servicio de Seguridad | Bus de Servicios | OAuth2 + Antifraude |
| Bus de Servicios | Módulos de negocio | REST interno |
| Módulos de negocio | CORE | REST interno vía Bus |

**Regla de oro:** Ningún módulo se conecta directo a la base de datos de otro módulo. Toda comunicación transita por el Bus de Servicios.

---

## Estándares de integración

| Aspecto | Estándar |
|---|---|
| Protocolo | HTTPS con TLS 1.2+ |
| Formato | JSON UTF-8 |
| Contratos | OpenAPI 3.0 (publicados antes de implementar) |
| Trazabilidad | `X-Correlation-ID` en toda petición |
| Idempotencia | `X-Idempotency-Key` en toda operación que afecte saldo |
| Timeouts | 3 s canales digitales / 5 s ATM |
| Reintentos | Máximo 2, con backoff exponencial |

---

## Referencias

- Documento 1 — Arquitectura Empresarial del BNA (TOGAF 10)
- Documento 2 — Requerimientos y Especificaciones Generales
- Documento 3 — Arquitectura e Interfaces entre Módulos
- Anexo C — Estándares de integración y seguridad
