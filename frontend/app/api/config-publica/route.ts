import { NextResponse } from "next/server";

// Configuración pública: la pantalla Billetera la lee para el enlace de descarga del APK y el
// QR de configuración de Chaski (y el portal, para el cajero). Se resuelve en cada petición: la misma imagen
// sirve para varios despliegues.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function urlPublica(valor: string | undefined): string | null {
  if (!valor || valor !== valor.trim()) return null;
  try {
    const url = new URL(valor);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    if (url.username || url.password) return null;
    return valor;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  void request; // La ruta no depende de la petición; Next.js exige la firma.
  return NextResponse.json(
    {
      urlBilletera: urlPublica(process.env.BNA_URL_BILLETERA),
      urlCajero: urlPublica(process.env.BNA_URL_CAJERO),
      urlApk: urlPublica(process.env.BNA_URL_APK),
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
