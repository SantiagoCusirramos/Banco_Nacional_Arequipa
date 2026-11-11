import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const COOKIE = "bna_cuenta_session";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const route = path.map(encodeURIComponent).join("/");
  const trace = crypto.randomUUID();
  const base = process.env.CUENTAS_GATEWAY_URL || "http://127.0.0.1:8001/api/v1/cuentas";
  
  const headers = new Headers({
    "Content-Type": "application/json",
    "X-Correlation-ID": trace,
  });
  for (const nombre of ["authorization", "x-idempotency-key", "x-channel-id", "x-request-timestamp"]) {
    const valor = request.headers.get(nombre);
    if (valor) headers.set(nombre, valor);
  }

  try {
    const upstream = await fetch(
      `${base.replace(/\/$/, "")}/${route}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        cache: "no-store",
        redirect: "error",
        body: request.method === "GET" ? undefined : await request.text(),
        signal: AbortSignal.timeout(5000),
      },
    );
    const data = await upstream.json();
    const response = NextResponse.json(data, { status: upstream.status });
    response.headers.set("X-Correlation-ID", upstream.headers.get("X-Correlation-ID") || trace);
    return response;
  } catch {
    return NextResponse.json(
      {
        detail:
          "No se pudo contactar al servicio de Cuentas (COREDB / CUENTAS). Comprueba que el backend esté iniciado en el puerto 8001 u 8012.",
      },
      { status: 503, headers: { "X-Correlation-ID": trace } },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
