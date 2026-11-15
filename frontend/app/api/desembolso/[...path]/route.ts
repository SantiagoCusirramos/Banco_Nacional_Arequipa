import { NextRequest } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Puente hacia el módulo DESEMBOLSO: /api/desembolso/<ruta> → DESEMBOLSO /api/v1/<ruta>.
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const base = process.env.DESEMBOLSO_GATEWAY_URL || "http://127.0.0.1:8016/api/v1";
  return reenviar(request, base, path, "Desembolso");
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
