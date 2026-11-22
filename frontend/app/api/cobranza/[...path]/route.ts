/**
 * Puente hacia el módulo Cobranza, solo para la pantalla "Pagar cuota". Al igual que
 * /api/cuenta y /api/tarjeta, reenvía el bearer token de COREDB (y la credencial del
 * frontend ante el Bus) sin añadir X-API-Key ni X-Token-Seguridad. El módulo Cobranza
 * valida la sesión con COREDB y comprueba los permisos.
 *
 * Solo se exponen las 4 rutas que usa esta pantalla; cualquier otra devuelve 404.
 */
import { NextRequest, NextResponse } from "next/server";
import { reenviar } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const RUTAS: { metodo: string; coincide: (ruta: string[]) => boolean }[] = [
  { metodo: "GET", coincide: (r) => r.length === 3 && r[0] === "clientes" && r[2] === "creditos" },
  { metodo: "GET", coincide: (r) => r.length === 3 && r[0] === "creditos" && r[2] === "monto-a-pagar" },
  { metodo: "GET", coincide: (r) => r.length === 3 && r[0] === "pagos" && r[2] === "comprobante" },
  { metodo: "POST", coincide: (r) => r.length === 2 && r[0] === "cr-int-08" && r[1] === "pagos" },
  // Rutas nuevas de la API v1 (CR-INT-07): consulta de créditos y cobro
  { metodo: "GET", coincide: (r) => r.length >= 2 && r[0] === "api" && r[1] === "v1" },
  { metodo: "POST", coincide: (r) => r.length >= 2 && r[0] === "api" && r[1] === "v1" },
];

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const regla = RUTAS.find((r) => r.metodo === request.method && r.coincide(path));
  if (!regla) {
    return NextResponse.json({ detalle: "Ruta no disponible en este canal." }, { status: 404 });
  }
  if (!request.headers.get("authorization")) {
    return NextResponse.json({ detalle: "Inicia sesión para continuar." }, { status: 401 });
  }
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    if (origin && new URL(origin).host !== request.headers.get("host")) {
      return NextResponse.json({ detalle: "Origen de la petición no permitido." }, { status: 403 });
    }
  }

  const base = process.env.COBRANZA_GATEWAY_URL || "http://127.0.0.1:8014";
  return reenviar(request, base, path, "COBRANZA");
}

export const GET = proxy;
export const POST = proxy;
