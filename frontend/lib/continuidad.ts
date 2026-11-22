/** Muestra solo el final del documento o de la cuenta; el operador no necesita el resto. */
function ultimosCuatro(valor: string | null | undefined): string {
  const texto = (valor ?? "").trim();
  return texto ? `••••${texto.slice(-4)}` : "—";
}

export const enmascararDocumento = ultimosCuatro;
export const enmascararCuenta = ultimosCuatro;

/**
 * Solo se vuelve a una ruta interna de esta aplicación. `//` y las barras invertidas
 * permiten a un navegador interpretar la dirección como un sitio distinto.
 */
export function rutaSeguraVolver(ruta: string | null | undefined): string | null {
  if (!ruta || !ruta.startsWith("/") || ruta.startsWith("//") || ruta.includes("\\")) return null;
  if (/[\u0000-\u001f]/.test(ruta)) return null;
  return ruta;
}

/** Arma el destino del login. La ruta raíz no necesita parámetro. */
export function urlLoginConVolver(ruta: string | null | undefined): string {
  const destino = rutaSeguraVolver(ruta);
  if (!destino || destino === "/") return "/login";
  return `/login?volver=${encodeURIComponent(destino)}`;
}

type DatosEtiqueta = {
  idSolicitud?: string;
  codigo?: string;
  codCliente?: string;
  montoSolicitado?: string;
  monto?: string;
  moneda?: string;
  nombre?: string;
};

/** Etiqueta legible de una solicitud: su código SOL, o cliente e importe si no lo hay. */
export function etiquetaSolicitud(datos: DatosEtiqueta): string {
  if (datos.codigo) return datos.codigo;
  const importe = datos.montoSolicitado ?? datos.monto;
  const partes = [datos.nombre ?? datos.codCliente].filter(Boolean) as string[];
  if (importe) {
    const valor = Number(importe);
    if (Number.isFinite(valor)) {
      const numero = valor.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      partes.push(`${datos.moneda === "USD" ? "$" : "S/"} ${numero}`);
    }
  }
  return partes.join(" · ") || "Solicitud";
}

export const CLAVE_BORRADOR_SOLICITUD = "bna_borrador_solicitud";

export type BorradorSolicitud<T> = { form: T; step: number; view: string };

export function guardarBorradorSolicitud<T>(borrador: BorradorSolicitud<T>) {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(CLAVE_BORRADOR_SOLICITUD, JSON.stringify(borrador));
  } catch { /* sin sessionStorage */ }
}

export function leerBorradorSolicitud<T>(): BorradorSolicitud<T> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(CLAVE_BORRADOR_SOLICITUD);
    if (!raw) return null;
    return JSON.parse(raw) as BorradorSolicitud<T>;
  } catch { return null; }
}

export function borrarBorradorSolicitud() {
  if (typeof window === "undefined") return;
  try { sessionStorage.removeItem(CLAVE_BORRADOR_SOLICITUD); } catch { /* sin sessionStorage */ }
}
