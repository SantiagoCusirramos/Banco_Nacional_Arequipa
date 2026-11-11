import { NextRequest } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Puente hacia el módulo CUENTAS: /api/cuenta/<ruta> → CUENTAS /api/v1/cuentas/<ruta>.
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const base = process.env.CUENTAS_GATEWAY_URL || "http://127.0.0.1:8001/api/v1/cuentas";
  return reenviar(request, base, path, "CUENTAS");
}

export const GET = proxy;
export const POST = proxy;
