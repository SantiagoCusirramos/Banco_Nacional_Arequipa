import { NextRequest, NextResponse } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Puente hacia Seguridad, solo para la pantalla de desbloqueo de tarjetas:
//   GET  /api/seguridad/auth/me
//   GET  /api/seguridad/tarjetas?cod_cliente=…
//   GET  /api/seguridad/tarjetas/<id>
//   POST /api/seguridad/tarjetas/<id>/desbloqueo
// Lo demás de Seguridad (bitácora, incidentes, evaluación, login) no pasa por aquí.
const ID = /^[0-9a-fA-F-]{36}$/;

function permitida(metodo: string, ruta: string[]): boolean {
  if (metodo === "GET") {
    if (ruta.length === 2 && ruta[0] === "auth" && ruta[1] === "me") return true;
    if (ruta.length === 1 && ruta[0] === "tarjetas") return true;
    return ruta.length === 2 && ruta[0] === "tarjetas" && ID.test(ruta[1]);
  }
  return metodo === "POST" && ruta.length === 3 && ruta[0] === "tarjetas" && ID.test(ruta[1])
    && ruta[2] === "desbloqueo";
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (!permitida(request.method, path)) {
    return NextResponse.json({ detail: "Ruta no disponible." }, { status: 404 });
  }
  const base = process.env.SEGURIDAD_GATEWAY_URL || "http://127.0.0.1:8013/seguridad";
  return reenviar(request, base, path, "SEGURIDAD");
}

export const GET = proxy;
export const POST = proxy;
