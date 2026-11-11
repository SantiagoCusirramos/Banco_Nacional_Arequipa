import { NextRequest, NextResponse } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Puente hacia COREDB: /api/core/coredb/<ruta> → COREDB /coredb/<ruta>. Solo sirve
// para lo que todavía no ofrece un módulo propio: sesión, usuarios, clientes y catálogos.
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (path[0] !== "coredb") {
    return NextResponse.json({ detail: "Ruta no disponible." }, { status: 404 });
  }
  const base = process.env.COREDB_URL || "http://127.0.0.1:8012";
  return reenviar(request, base, path, "COREDB");
}

export const GET = proxy;
export const POST = proxy;
