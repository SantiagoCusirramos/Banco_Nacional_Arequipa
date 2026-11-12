import { NextRequest } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Puente hacia el módulo TARJETAS: /api/tarjeta/<ruta> → TARJETAS /api/v1/tarjetas/<ruta>.
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const base = process.env.TARJETAS_GATEWAY_URL || "http://127.0.0.1:8002/api/v1/tarjetas";
  return reenviar(request, base, path, "TARJETAS");
}

export const GET = proxy;
export const POST = proxy;
