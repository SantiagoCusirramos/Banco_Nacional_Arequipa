import { apiEvaluacion as api, mensajeError } from "@/lib/api";

// Contratos de EVALUACIÓN (backend/EVALUACION), que devuelve lo que responde COREDB
// (backend/COREDB/CONTRATO_CREDITOS.md §3). Los montos llegan como texto decimal ("15000.00").

export type EstadoSolicitud = "REGISTRADA" | "EN_EVALUACION" | "APROBADA" | "RECHAZADA" | "DESEMBOLSADA";
export type Riesgo = "BUENO" | "REGULAR" | "ALTO";
// Por omisión del equipo (T1) el analista aprueba o rechaza: no devuelve la solicitud a SOL.
export type Decision = "APROBADO" | "RECHAZADO";

export const ESTADOS: EstadoSolicitud[] = ["EN_EVALUACION", "APROBADA", "RECHAZADA", "DESEMBOLSADA"];
export const RIESGOS: Riesgo[] = ["BUENO", "REGULAR", "ALTO"];

export interface Solicitud {
  idSolicitud: string;
  versionSolicitud: number;
  ronda: number | null;
  codCliente: string;
  montoSolicitado: string;
  moneda: string;
  plazoMeses: number;
  condicionPagoDoble: boolean;
  estado: EstadoSolicitud;
  fechaCreacion: string;
  numeroCuotas: number | null;
  totalCuotas: string | null;
  primerVencimiento: string | null;
}

export interface Cuota {
  numeroCuota: number;
  fechaVencimiento: string;
  capital: string;
  interes: string;
  cuotaTotal: string;
  saldoCapital: string;
}

export interface Evaluacion {
  idEvaluacion: string;
  ronda: number;
  fechaEvaluacion: string;
  score: string;
  limite: string;
  regla: string;
  resultadoRegla: string;
  ingresoMensual: string;
  deudaMensual: string;
  decision: string | null;
  comentario: string | null;
  fechaDecision: string | null;
  resultado: string;
  esUltima: boolean;
}

export interface Estado {
  estado: string;
  fechaHora: string;
  actor: string;
  motivo: string | null;
}

export interface DetalleSolicitud extends Solicitud {
  calendario: { tipo: "PRELIMINAR" | "OFICIAL"; metodo: string; tasa: string; cuotas: Cuota[] } | null;
  evaluaciones: Evaluacion[];
  historial: Estado[];
}

export interface ResultadoEvaluacion {
  idEvaluacion: string;
  resultado: "APROBADO" | "OBSERVADO" | "RECHAZADO";
  regla: string;
  score: number;
  limite: string;
  ratio: string | null;
  estadoSolicitud: EstadoSolicitud;
}

export interface MensajeSol {
  idSolicitud: string;
  idEvaluacion: string;
  ronda: number;
  idOperacion: string;
  decision: string;
  observaciones: string;
}

export const mensajeDeError = mensajeError;

export async function bandeja(filtros: { estado?: string; codCliente?: string } = {}): Promise<Solicitud[]> {
  const params: Record<string, string> = {};
  if (filtros.estado) params.estado = filtros.estado;
  if (filtros.codCliente) params.codCliente = filtros.codCliente;
  const { data } = await api.get<Solicitud[]>("/solicitudes", { params });
  return data;
}

export async function verSolicitud(id: string): Promise<DetalleSolicitud> {
  const { data } = await api.get<DetalleSolicitud>(`/solicitudes/${encodeURIComponent(id)}`);
  return data;
}

export async function evaluar(
  id: string,
  datos: { versionSolicitud: number; ingresoMensual: string; deudaMensual: string; riesgo: Riesgo; verificada: boolean },
): Promise<ResultadoEvaluacion> {
  const { data } = await api.post<ResultadoEvaluacion>(`/solicitudes/${encodeURIComponent(id)}/evaluaciones`, datos);
  return data;
}

export async function decidir(idEvaluacion: string, datos: { decision: Decision; comentario: string }) {
  const { data } = await api.post<{ estadoSolicitud: EstadoSolicitud }>(
    `/evaluaciones/${encodeURIComponent(idEvaluacion)}/decision`, datos);
  return data;
}

export async function revocar(id: string, datos: { motivo: string }) {
  const { data } = await api.post<{ estadoSolicitud: EstadoSolicitud }>(
    `/solicitudes/${encodeURIComponent(id)}/revocacion`, datos);
  return data;
}

export async function resultadosSol(): Promise<{ configurado: boolean; ventanaDias: number; items: MensajeSol[] }> {
  const { data } = await api.get<{ configurado: boolean; ventanaDias: number; items: MensajeSol[] }>("/resultados-sol");
  return data;
}

/** "15000.00" → "15,000.00", sin pasar por float. */
export function formatoMonto(texto: string | null | undefined): string {
  if (texto == null || texto === "") return "—";
  const [entero, decimales = "00"] = String(texto).split(".");
  return `${entero.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${decimales.padEnd(2, "0")}`;
}

export function conMoneda(texto: string | null | undefined, moneda = "PEN"): string {
  return `${moneda === "USD" ? "US$" : "S/"} ${formatoMonto(texto)}`;
}

/** Fracción "0.2200" → "22.00 %"; ratio "0.7143" → "71.43 %". */
export function porcentaje(fraccion: string | null | undefined): string {
  if (fraccion == null) return "—";
  return `${(Number(fraccion) * 100).toFixed(2)} %`;
}

export function fechaHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-PE", { dateStyle: "medium", timeStyle: "short" });
}

/** "2026-12-15" → "15/12/2026", sin zona horaria de por medio. */
export function fecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [anio, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${anio}`;
}

/** La suma de montos en texto, en céntimos enteros (sin errores de coma flotante). */
export function sumar(montos: string[]): string {
  const centimos = montos.reduce((total, m) => total + Math.round(Number(m) * 100), 0);
  return (centimos / 100).toFixed(2);
}
