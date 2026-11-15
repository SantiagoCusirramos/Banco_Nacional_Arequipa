import { apiEvaluacion as api, mensajeError } from "@/lib/api";

// Contratos de EVALUACIÓN (backend/EVALUACION). Los montos llegan como texto decimal ("15000.00").

export type EstadoEvaluacion = "PENDIENTE" | "EN_REVISION" | "APROBADO" | "OBSERVADO" | "RECHAZADO";
export type Riesgo = "BUENO" | "REGULAR" | "ALTO";
export type Decision = "APROBADO" | "OBSERVADO" | "RECHAZADO";

export const ESTADOS: EstadoEvaluacion[] = ["PENDIENTE", "EN_REVISION", "APROBADO", "OBSERVADO", "RECHAZADO"];
export const RIESGOS: Riesgo[] = ["BUENO", "REGULAR", "ALTO"];

export interface Evaluacion {
  idEvaluacion: string;
  idSolicitud: string;
  versionSolicitud: number;
  ronda: number;
  estado: EstadoEvaluacion;
  version: number;
  cliente: { idCliente: string; nombre: string; tipoDocumento: string; numeroDocumento: string };
  producto: string;
  destino: string | null;
  montoSolicitado: string;
  moneda: string;
  plazoMeses: number;
  tasaTea: string;
  motor: { resultado: string; score: number; limite: string; ratio: string | null; regla: string } | null;
  motivo: string | null;
  decididoPor: string | null;
  decididoEn: string | null;
  recibidoEn: string;
  actualizadoEn: string;
}

export interface Cuota {
  numeroCuota: number;
  fechaVencimiento: string;
  amortizacion: string;
  interes: string;
  cuotaTotal: string;
  saldoFinal: string;
}

export interface Aprobacion {
  idAprobacion: string;
  version: number;
  codCredito: string;
  estado: "VIGENTE" | "VENCIDA" | "DESEMBOLSADA" | "REVOCADA";
  montoAprobado: string;
  moneda: string;
  plazoMeses: number;
  tasaTea: string;
  vigenteHasta: string;
  aprobadaPor: string;
  aprobadaEn: string;
  desembolso: { codigoOrden: string; fechaDesembolso: string; registradoPor: string } | null;
  revocacion: { motivo: string; revocadaPor: string; fecha: string } | null;
}

export interface Envio {
  idOperacion: string;
  idEvaluacion: string;
  interfaz: string;
  decision: string;
  estado: "PENDIENTE" | "ENTREGADO" | "ERROR";
  intentos: number;
  siguienteIntento: string;
  ultimoError: string | null;
  creadoEn: string;
  entregadoEn: string | null;
}

export interface Evento {
  id: number;
  fecha: string;
  evento: string;
  actor: string;
  idEvaluacion: string | null;
  idAprobacion: string | null;
  idCorrelacion: string | null;
  detalle: Record<string, unknown> | null;
}

export interface DetalleEvaluacion extends Evaluacion {
  expediente: {
    idOperacion: string;
    acuse: string;
    versionContrato: string;
    actorEnvio: string | null;
    simulado: boolean;
    recibidoEn: string;
    fechaBase: string | null;
    garantias: { tipo: string; descripcion: string; valorTasacion: string }[];
    fiadores: number;
    politica: { version: string | null; estadoAprobacion: string | null };
    calendario: {
      estado: string | null;
      cuotaReferencial: string | null;
      interesesTotales: string | null;
      totalPagar: string | null;
      cuotas: Cuota[];
    };
  };
  situacionFinanciera: {
    ingresoMensual: string;
    deudaMensual: string;
    riesgo: Riesgo;
    verificada: boolean;
    registradoPor: string;
    registradoEn: string;
  } | null;
  aprobacion: Aprobacion | null;
  envioSol: Envio | null;
  historial: Evento[];
}

export interface Bandeja {
  items: Evaluacion[];
  conteos: Partial<Record<EstadoEvaluacion, number>>;
}

export const mensajeDeError = mensajeError;

export async function bandeja(filtros: { estado?: string; buscar?: string } = {}): Promise<Bandeja> {
  const params: Record<string, string> = {};
  if (filtros.estado) params.estado = filtros.estado;
  if (filtros.buscar) params.buscar = filtros.buscar;
  const { data } = await api.get<Bandeja>("/evaluaciones", { params });
  return data;
}

export async function verEvaluacion(id: string): Promise<DetalleEvaluacion> {
  const { data } = await api.get<DetalleEvaluacion>(`/evaluaciones/${encodeURIComponent(id)}`);
  return data;
}

export async function registrarSituacion(
  id: string,
  datos: { ingresoMensual: string; deudaMensual: string; riesgo: Riesgo; verificada: boolean; version: number },
): Promise<DetalleEvaluacion> {
  const { data } = await api.post<DetalleEvaluacion>(`/evaluaciones/${encodeURIComponent(id)}/situacion-financiera`, datos);
  return data;
}

export async function decidir(
  id: string,
  datos: { decision: Decision; observaciones: string; version: number },
): Promise<DetalleEvaluacion> {
  const { data } = await api.post<DetalleEvaluacion>(`/evaluaciones/${encodeURIComponent(id)}/decision`, datos);
  return data;
}

export async function revocar(idAprobacion: string, datos: { motivo: string; version: number }): Promise<Aprobacion> {
  const { data } = await api.post<Aprobacion>(`/aprobaciones/${encodeURIComponent(idAprobacion)}/revocacion`, datos);
  return data;
}

export async function listarEnvios(estado?: string): Promise<{ items: Envio[]; configurado: boolean }> {
  const { data } = await api.get<{ items: Envio[]; configurado: boolean }>("/envios", {
    params: estado ? { estado } : {},
  });
  return data;
}

export async function reintentarEnvio(idOperacion: string): Promise<Envio> {
  const { data } = await api.post<Envio>(`/envios/${encodeURIComponent(idOperacion)}/reintento`);
  return data;
}

export async function historial(): Promise<Evento[]> {
  const { data } = await api.get<{ items: Evento[] }>("/historial");
  return data.items;
}

/** "15000.00" → "15,000.00", sin pasar por float. */
export function formatoMonto(texto: string | null | undefined): string {
  if (texto == null || texto === "") return "—";
  const [entero, decimales = "00"] = texto.split(".");
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
