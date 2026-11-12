# Frontend

Banca personal del BNA en [Next.js](https://nextjs.org) 16 (App Router) con React 19 y TypeScript.

## Pantallas

| Ruta | Qué es | De dónde salen los datos |
|---|---|---|
| `/login` | Inicio de sesión. El formulario de registro de usuarios solo funciona con una sesión que tenga el permiso `CREAR_USUARIO` | COREDB (`/coredb/auth/login`, `/coredb/usuarios`) |
| `/` | Banca personal. Exige una sesión vigente | "Abrir una cuenta" y "Modificar cuenta" usan CUENTAS y COREDB. El resumen, las transferencias, los movimientos y las tarjetas de esta pantalla son datos de demostración, sin conexión con el banco |
| `/cuenta` | Módulo de cuentas: abrir, consultar, depositar, retirar, transferir y ver movimientos | CUENTAS |
| `/solicitud-credito` | Solicitud de crédito | SOL, con sus propias cuentas (ver [`EMPEZAR_AQUI_SOL.md`](../EMPEZAR_AQUI_SOL.md)) |

El cambio de estado de una cuenta se muestra deshabilitado: COREDB todavía no ofrece esa operación (issue #41).

## Cómo llega a los servicios

El navegador solo llama a rutas de este mismo servidor, que las reenvía desde el lado servidor (`lib/proxy.ts`). Así el navegador nunca conoce la dirección de un servicio.

| Ruta del frontend | Reenvía a | Variable |
|---|---|---|
| `/api/core/coredb/*` | COREDB, `/coredb/*` | `COREDB_URL` |
| `/api/cuenta/*` | CUENTAS, `/api/v1/cuentas/*` | `CUENTAS_GATEWAY_URL` |
| `/api/solicitud-credito/*` | SOL, `/gateway/sol/*` | `SOL_GATEWAY_URL` |

Las variables se leen al ejecutar, no al construir. De cada petición se reenvían `Authorization`, `X-Idempotency-Key`, `X-Channel-ID` y `X-Request-Timestamp`; si falta `X-Correlation-ID`, se genera uno. La sesión de COREDB (el token) se guarda en `localStorage`; la de SOL, en una cookie que maneja su propio puente.

## Ejecutar

Con todo el producto, desde la raíz del repositorio: `./bna up`. El frontend queda en http://localhost:3000 y se entra con `admin` y la contraseña de `BNA_ADMIN_PASSWORD` en `.env`.

Para desarrollar con recarga en vivo hace falta Node.js 20.9 o superior (la imagen usa Node 22) y los servicios levantados:

```bash
./bna up                          # en la raíz: deja COREDB, CUENTAS y SOL en sus puertos
cd frontend
cat .env.example .env.sol.example > .env.local
npm ci
npm run dev -- --port 3001        # el 3000 lo ocupa el frontend del producto
```

`.env.local` no se versiona. Sus valores por omisión ya apuntan a los puertos de `./bna up`.

## Pruebas

```bash
npm run lint
npm test          # Vitest con Testing Library
npm run build
```

Sin Node en la máquina, `./bna test` desde la raíz corre el lint y las pruebas en un contenedor.

## Notas

- `AGENTS.md` y `CLAUDE.md` los genera `next dev`. Piden leer la documentación incluida en `node_modules/next/dist/docs/` antes de escribir código, porque esta versión de Next.js cambia API y convenciones.
- La imagen del producto se construye con [`docker/frontend/Dockerfile`](../docker/frontend/Dockerfile).
