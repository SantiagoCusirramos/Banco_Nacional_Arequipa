import type { EstadoOrden } from "./tipos";

// Los importes llegan como cadena ("10000.00") y se formatean sin convertir a float.
export function dinero(importe: string | null | undefined, moneda: string): string {
  if (!importe) return "—";
  const [entero, decimales = "00"] = importe.split(".");
  const miles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${moneda === "USD" ? "US$" : "S/"} ${miles}.${decimales.padEnd(2, "0").slice(0, 2)}`;
}

// Fechas de la API en hora de Arequipa (sin zona): se formatean como texto.
export function fecha(iso: string | null | undefined, conHora = true): string {
  if (!iso) return "—";
  let texto = iso;
  // Con zona (las marcas técnicas vienen en UTC): se lleva a la hora de Arequipa, UTC-5 todo el año.
  if (/(?:[zZ]|[+-]\d{2}:\d{2})$/.test(iso)) {
    const instante = Date.parse(iso);
    if (!Number.isNaN(instante)) texto = new Date(instante - 5 * 3600 * 1000).toISOString();
  }
  const m = texto.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (!m) return iso;
  const base = `${m[3]}/${m[2]}/${m[1]}`;
  return conHora && m[4] ? `${base} ${m[4]}:${m[5]}` : base;
}

export function hoyLima(): string {
  const ahora = new Date(Date.now() - 5 * 3600 * 1000);
  return ahora.toISOString().slice(0, 10);
}

export const ETIQUETA_ESTADO: Record<EstadoOrden, string> = {
  PREPARADA: "Preparada",
  VALIDADA: "Validada",
  EN_PROCESO: "En proceso",
  POR_VERIFICAR: "Por verificar",
  CONFIRMADA: "Confirmada",
  RECHAZADA: "Rechazada",
  REVERTIDA: "Revertida",
};

export const TONO_ESTADO: Record<string, Tono> = {
  PREPARADA: "neutro",
  VALIDADA: "info",
  EN_PROCESO: "aviso",
  POR_VERIFICAR: "aviso",
  CONFIRMADA: "exito",
  RECHAZADA: "error",
  REVERTIDA: "especial",
  PENDIENTE: "aviso",
  ENVIADO: "info",
  CONFIRMADO: "exito",
  FALLIDO: "error",
  APROBADA: "exito",
  HABILITADA: "exito",
  VIGENTE: "exito",
  DESEMBOLSADA: "especial",
  VENCIDA: "error",
  REVOCADA: "error",
  SOLICITADA: "aviso",
};

export type Tono = "neutro" | "info" | "exito" | "aviso" | "error" | "especial";

export const MOTIVOS_CUENTA: Record<string, string> = {
  MONEDA_DISTINTA: "Moneda distinta a la del crédito",
  CUENTA_BLOQUEADA: "Cuenta bloqueada",
  CUENTA_MANCOMUNADA: "Cuenta mancomunada",
  TITULAR_DISTINTO: "Titular distinto",
  CUENTA_INEXISTENTE: "Cuenta inexistente",
};
