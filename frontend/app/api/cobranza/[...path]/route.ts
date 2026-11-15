/**
 * Puente hacia el módulo Cobranza, solo para la pantalla "Pagar cuota". A diferencia de
 * /api/cuenta y /api/tarjeta (que reenvían el bearer token de COREDB), Cobranza se autentica
 * con X-API-Key (ver backend/COBRANZA/auth.py): esa clave vive solo aquí, en el servidor, y
 * nunca llega al navegador. El bearer token que sí llega del navegador solo prueba que hay
 * una sesión de COREDB iniciada (RUTAS exige Authorization); Cobranza ni lo ve ni lo necesita.
 *
 * Solo se exponen las 4 rutas que usa esta pantalla; cualquier otra devuelve 404.
 *
 * X-Token-Seguridad (RF-COB-004): el módulo Seguridad todavía no publica el validador real
 * (ver backend/COBRANZA/seguridad.py), así que el servidor envía este valor fijo como
 * validación SIMULADA. Cuando Seguridad ofrezca el servicio real, este valor se reemplaza
 * por el token que entregue.
 */
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const TOKEN_SEGURIDAD_SIMULADO = "SIMULADO-SEGURIDAD-HOME-BANKING";

type Clave = "leer" | "integracion";

const RUTAS: { metodo: string; clave: Clave; coincide: (ruta: string[]) => boolean }[] = [
  { metodo: "GET", clave: "leer", coincide: (r) => r.length === 3 && r[0] === "clientes" && r[2] === "creditos" },
  { metodo: "GET", clave: "leer", coincide: (r) => r.length === 3 && r[0] === "creditos" && r[2] === "monto-a-pagar" },
  { metodo: "GET", clave: "leer", coincide: (r) => r.length === 3 && r[0] === "pagos" && r[2] === "comprobante" },
  { metodo: "POST", clave: "integracion", coincide: (r) => r.length === 2 && r[0] === "cr-int-08" && r[1] === "pagos" },
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

  const base = process.env.COBRANZA_URL || "http://127.0.0.1:8014";
  const clave = regla.clave === "leer"
    ? process.env.COBRANZA_API_KEY_LEER
    : process.env.COBRANZA_API_KEY_INTEGRACION;
  if (!clave) {
    return NextResponse.json(
      { detalle: "Configura COBRANZA_API_KEY_LEER y COBRANZA_API_KEY_INTEGRACION en el servidor." },
      { status: 503 },
    );
  }

  const correlacion = request.headers.get("x-correlation-id") || crypto.randomUUID();
  const headers = new Headers({
    "Content-Type": "application/json",
    "X-API-Key": clave,
    "X-Correlation-ID": correlacion,
  });
  if (regla.metodo === "POST") headers.set("X-Token-Seguridad", TOKEN_SEGURIDAD_SIMULADO);

  const destino = `${base.replace(/\/$/, "")}/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;

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
      { detalle: "No se pudo contactar al servicio Cobranza." },
      { status: 503, headers: { "X-Correlation-ID": correlacion } },
    );
  }

  const texto = await respuesta.text();
  let cuerpo: unknown;
  try {
    cuerpo = texto ? JSON.parse(texto) : null;
  } catch {
    cuerpo = { detalle: "El servicio Cobranza respondió con un formato inesperado." };
  }
  return NextResponse.json(cuerpo, {
    status: respuesta.status,
    headers: { "X-Correlation-ID": respuesta.headers.get("X-Correlation-ID") || correlacion },
  });
}

export const GET = proxy;
export const POST = proxy;
