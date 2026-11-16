import { NextRequest } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Puente hacia CAPTACION: /api/captacion/<ruta> → CAPTACION /api/v1/captacion/<ruta>.
// Las referencias para Solicitud de Crédito (/cap/references) no pasan por aquí: son de
// servicio a servicio y usan un token que el navegador nunca ve.
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const base = process.env.CAPTACION_GATEWAY_URL || "http://127.0.0.1:8014/api/v1/captacion";
  return reenviar(request, base, path, "CAPTACION");
}

export const GET = proxy;
export const POST = proxy;
