import type { EstadoOrden } from "./tipos";

// Los importes llegan como cadena ("10000.00") y se formatean sin convertir a float.
export function dinero(importe: string | null | undefined, moneda: string): string {
  if (!importe) return "—";
  const [entero, decimales = "00"] = importe.split(".");
  const miles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${moneda === "USD" ? "US$" : "S/"} ${miles}.${decimales.padEnd(2, "0").slice(0, 2)}`;
}

// Fechas: "2026-12-15" se muestra tal cual; una marca con zona (UTC) se lleva a la hora de Arequipa,
// UTC-5 todo el año.
export function fecha(iso: string | null | undefined, conHora = true): string {
  if (!iso) return "—";
  let texto = iso;
  if (/(?:[zZ]|[+-]\d{2}:\d{2})$/.test(iso)) {
    const instante = Date.parse(iso);
    if (!Number.isNaN(instante)) texto = new Date(instante - 5 * 3600 * 1000).toISOString();
  }
  const m = texto.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (!m) return iso;
  const base = `${m[3]}/${m[2]}/${m[1]}`;
  return conHora && m[4] ? `${base} ${m[4]}:${m[5]}` : base;
}

/** Fracción "0.1268" → "12.68 %". */
export function porcentaje(fraccion: string | null | undefined): string {
  if (fraccion == null) return "—";
  return `${(Number(fraccion) * 100).toFixed(2)} %`;
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

// Los estados que COREDB usa hoy en una orden: PREPARADA, VALIDADA, CONFIRMADA y RECHAZADA.
export const ESTADOS_EN_USO: EstadoOrden[] = ["PREPARADA", "VALIDADA", "CONFIRMADA", "RECHAZADA"];

export const TONO_ESTADO: Record<string, Tono> = {
  PREPARADA: "neutro",
  VALIDADA: "info",
  EN_PROCESO: "aviso",
  POR_VERIFICAR: "aviso",
  CONFIRMADA: "exito",
  RECHAZADA: "error",
  REVERTIDA: "especial",
  APROBADA: "exito",
  APROBADO: "exito",
  RECHAZADO: "error",
  DESEMBOLSADA: "especial",
  PRELIMINAR: "aviso",
  OFICIAL: "exito",
};

export type Tono = "neutro" | "info" | "exito" | "aviso" | "error" | "especial";

export const MOTIVOS_CUENTA: Record<string, string> = {
  CUENTA_MANCOMUNADA: "Cuenta mancomunada: solo se abona en una cuenta individual",
  TITULAR_DISTINTO: "Titular distinto",
  CUENTA_NO_ACTIVA: "Cuenta no activa",
  MONEDA_DISTINTA: "Moneda distinta a la del crédito",
};

export const PERFIL: Record<string, string> = {
  OPERADOR: "Operador de agencia",
  SUPERVISOR: "Supervisor",
  AUDITOR: "Auditor",
  CONSULTA: "Consulta",
};
