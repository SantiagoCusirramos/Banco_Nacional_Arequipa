/**
 * Frontera del navegador: la URL del gateway y el token quedan en servidor.
 * La sesión usa una cookie HttpOnly; el cliente nunca recibe el bearer token.
 * En esta entrega el gateway es SIMULADO y ejecuta SOL sobre su BD local.
 */
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const COOKIE = "bna_sol_session";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  // Codificar segmentos evita que una URL suministrada por el cliente cambie el host destino.
  const route = path.map(encodeURIComponent).join("/");
  // Los callbacks EVA requieren credencial de servicio y no pasan por el navegador.
  if (path[0] === "integrations")
    return NextResponse.json({ detail: "Ruta no disponible en este canal." }, { status: 404 });
  const trace = crypto.randomUUID();
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    if (origin && new URL(origin).host !== request.headers.get("host")) {
      return NextResponse.json(
        { detail: "Origen de la petición no permitido." },
        { status: 403 },
      );
    }
  }
  const base = process.env.SOL_GATEWAY_URL;
  if (!base)
    return NextResponse.json(
      { detail: "Configura SOL_GATEWAY_URL en frontend/.env.local." },
      { status: 503 },
    );
  const token = request.cookies.get(COOKIE)?.value;
  if (route !== "auth/login" && !token) {
    return NextResponse.json(
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
      const response = NextResponse.json({ usuario: data.usuario });
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
    const response = NextResponse.json(data, { status: upstream.status });
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
    return NextResponse.json(
      {
        detail:
          "No se pudo contactar al servicio SOL. Comprueba que el backend esté iniciado en el puerto 8011.",
      },
      { status: 503, headers: { "X-Correlation-ID": trace } },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
