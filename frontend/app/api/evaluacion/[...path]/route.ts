import { NextRequest } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Puente hacia el módulo EVALUACIÓN: /api/evaluacion/<ruta> → EVALUACIÓN /eva/v1/<ruta>.
// Las rutas de SOL (CR-INT-02) quedan fuera: no están bajo /eva/v1.
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const base = process.env.EVALUACION_GATEWAY_URL || "http://127.0.0.1:8015/eva/v1";
  return reenviar(request, base, path, "Evaluación");
}

export const GET = proxy;
export const POST = proxy;
