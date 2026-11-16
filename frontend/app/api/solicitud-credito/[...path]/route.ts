/**
 * Frontera del navegador: la URL del gateway y el token quedan en servidor.
 * La sesión usa una cookie HttpOnly; el cliente nunca recibe el bearer token.
 * En esta entrega el gateway es SIMULADO y ejecuta SOL sobre su BD local.
 */
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const COOKIE = "bna_sol_session";

function json(body: unknown, init?: ResponseInit) {
  const response = NextResponse.json(body, init);
  response.headers.set("Cache-Control", "no-store");
  return response;
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (path.some((part) => !part || part === "." || part === ".." || part.includes("/") || part.includes("\\")))
    return json({ detail: "Ruta no permitida." }, { status: 400 });
  // Codificar segmentos evita que una URL suministrada por el cliente cambie el host destino.
  const route = path.map(encodeURIComponent).join("/");
  // Los callbacks EVA requieren credencial de servicio y no pasan por el navegador.
  if (path[0] === "integrations")
    return json({ detail: "Ruta no disponible en este canal." }, { status: 404 });
  const trace = crypto.randomUUID();
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    // Next arma nextUrl con su puerto interno (3000), no con el que publica
    // compose o el NodePort de kind. Por omisión vale el Host que recibió el
    // servidor, que lo fija el navegador y una página ajena no puede cambiar.
    // Detrás de un proxy TLS se configura SOL_PUBLIC_ORIGIN; nunca se toma de
    // X-Forwarded-* del cliente.
    const host = request.headers.get("host");
    let expectedOrigin = host ? `${request.nextUrl.protocol}//${host}` : request.nextUrl.origin;
    const configuredOrigin = process.env.SOL_PUBLIC_ORIGIN;
    if (configuredOrigin) {
      try {
        const publicUrl = new URL(configuredOrigin);
        if (!["http:", "https:"].includes(publicUrl.protocol) || publicUrl.origin !== configuredOrigin)
          throw new Error("Origen inválido");
        expectedOrigin = publicUrl.origin;
      } catch {
        return json({ detail: "Configura SOL_PUBLIC_ORIGIN como origen HTTP(S) sin ruta ni credenciales." }, { status: 503 });
      }
    }
    let sameOrigin = false;
    try { sameOrigin = !!origin && new URL(origin).origin === expectedOrigin; } catch { /* Origen inválido. */ }
    if (!sameOrigin) {
      return json(
        { detail: "Origen de la petición no permitido." },
        { status: 403 },
      );
    }
  }
  const base = process.env.SOL_GATEWAY_URL;
  if (!base)
    return json(
      { detail: "Configura SOL_GATEWAY_URL en frontend/.env.local." },
      { status: 503 },
    );
  const token = request.cookies.get(COOKIE)?.value;
  if (route !== "auth/login" && !token) {
    return json(
      { detail: "Inicia sesión para continuar." },
      { status: 401 },
    );
  }
  const headers = new Headers({
    "Content-Type": "application/json",
    "X-Correlation-ID": trace,
  });
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const operation = request.headers.get("X-Idempotency-Key");
  if (operation) headers.set("X-Idempotency-Key", operation);
  try {
    const upstream = await fetch(
      `${base.replace(/\/$/, "")}/${route}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        cache: "no-store",
        redirect: "error",
        body: request.method === "GET" ? undefined : await request.text(),
        signal: AbortSignal.timeout(3000),
      },
    );
    const data = await upstream.json();
    if (route === "auth/login" && upstream.ok) {
      if (typeof data.token !== "string" || !data.token || !data.usuario)
        return json({ detail: "Respuesta de acceso no válida." }, { status: 503 });
      const response = json({ usuario: data.usuario });
      response.headers.set("X-Correlation-ID", upstream.headers.get("X-Correlation-ID") || trace);
      response.cookies.set(COOKIE, data.token, {
        httpOnly: true,
        sameSite: "lax",
        secure: process.env.SOL_COOKIE_SECURE === "true",
        maxAge: 8 * 60 * 60,
        path: "/api/solicitud-credito",
      });
      return response;
    }
    const response = json(data, { status: upstream.status });
    response.headers.set("X-Correlation-ID", upstream.headers.get("X-Correlation-ID") || trace);
    if (route === "auth/logout" || upstream.status === 401) {
      response.cookies.set(COOKIE, "", {
        maxAge: 0,
        path: "/api/solicitud-credito",
      });
    }
    return response;
  } catch {
    // Una caída de MySQL/Bus no se disfraza como respuesta de demostración exitosa.
    const response = json(
      {
        detail:
          "No se pudo contactar al servicio SOL. Comprueba que el backend esté iniciado en el puerto 8011.",
      },
      { status: 503, headers: { "X-Correlation-ID": trace } },
    );
    if (route === "auth/logout")
      response.cookies.set(COOKIE, "", { maxAge: 0, path: "/api/solicitud-credito" });
    return response;
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
