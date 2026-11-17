import { NextRequest, NextResponse } from "next/server";

// Cabeceras del navegador que se reenvían al servicio. Las demás no pasan.
const REENVIADAS = ["authorization", "x-idempotency-key", "x-channel-id", "x-request-timestamp"];

/**
 * Credencial del frontend ante el Bus de Servicios (X-Bus-Token). Sale del entorno del
 * servidor (BUS_TOKEN), nunca del navegador. Sin BUS_TOKEN no se envía: así el frontend
 * también puede apuntar directo a los módulos en desarrollo (`npm run dev`).
 */
export function credencialBus(headers: Headers): void {
  const token = process.env.BUS_TOKEN;
  if (token) headers.set("X-Bus-Token", token);
}

/**
 * Reenvía una petición del navegador a un servicio interno desde el servidor de
 * Next.js, de modo que el navegador nunca conoce la dirección del servicio.
 */
export async function reenviar(
  request: NextRequest,
  base: string,
  ruta: string[],
  servicio: string,
): Promise<NextResponse> {
  const correlacion = request.headers.get("x-correlation-id") || crypto.randomUUID();
  const headers = new Headers({ "Content-Type": "application/json", "X-Correlation-ID": correlacion });
  for (const nombre of REENVIADAS) {
    const valor = request.headers.get(nombre);
    if (valor) headers.set(nombre, valor);
  }
  credencialBus(headers);
  const destino = `${base.replace(/\/$/, "")}/${ruta.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;

  let respuesta: Response;
  try {
    respuesta = await fetch(destino, {
      method: request.method,
      headers,
      cache: "no-store",
      redirect: "error",
      body: request.method === "GET" ? undefined : await request.text(),
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    return NextResponse.json(
      { detail: `No se pudo contactar al servicio ${servicio}.` },
      { status: 503, headers: { "X-Correlation-ID": correlacion } },
    );
  }

  const texto = await respuesta.text();
  let cuerpo: unknown;
  try {
    cuerpo = texto ? JSON.parse(texto) : null;
  } catch {
    cuerpo = { detail: `El servicio ${servicio} respondió con un formato inesperado.` };
  }
  return NextResponse.json(cuerpo, {
    status: respuesta.status,
    headers: { "X-Correlation-ID": respuesta.headers.get("X-Correlation-ID") || correlacion },
  });
}
