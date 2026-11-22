import axios from "axios";
import { apiCobranza as api, mensajeError } from "@/lib/api";

/** Una cuota del cronograma, tal como la devuelve Cobranza (CR-INT-08). */
export interface Cuota {
  idCuota: string;
  numeroCuota: number;
  fechaVencimiento: string;
  montoCuota: string;
  saldoPendiente: string;
  moraPendiente: string;
  totalAdeudado: string;
  estadoCuota: "PENDIENTE" | "PARCIAL" | "PAGADA";
}

/** Un crédito con su cronograma completo. */
export interface Credito {
  codCredito: string;
  idCliente: string;
  montoAprobado: string;
  moneda: string;
  fechaDesembolso: string;
  estadoCredito: string;
  saldoTotalPendiente: string;
  cuotas: Cuota[];
}

/** RF-COB-003: desglose de lo que toca pagar hoy, en capital y mora. */
export interface MontoAPagar {
  codCredito: string;
  idCuota: string;
  numeroCuota: number;
  fechaVencimiento: string;
  saldoCapital: string;
  moraVigente: string;
  totalAPagar: string;
}

export type EstadoPago = "CONFIRMADO" | "RECHAZADO" | "PENDIENTE" | "REQUIERE_REVISION";

export interface AplicacionPago {
  idCuota: string;
  numeroCuota: number;
  montoAplicado: string;
  montoAplicadoMora: string;
  montoAplicadoCapital: string;
  saldoPendienteCuota: string;
  moraPendienteCuota: string;
  estadoCuota: string;
}

/** Resultado de CR-INT-08: el mismo objeto se repite si se reintenta con la misma referencia. */
export interface ResultadoPago {
  idPago: string;
  referenciaTransaccion: string;
  estado: EstadoPago;
  idempotente: boolean;
  motivo: string | null;
  codCredito: string;
  idCanal: string;
  montoPago: string;
  fechaHora: string;
  aplicacion: AplicacionPago | null;
  estadoCredito: string;
}

/** RN-COB-012: comprobante de un pago ya CONFIRMADO. */
export interface Comprobante {
  numeroOperacion: string;
  fechaHora: string;
  canal: string;
  codCredito: string;
  montoPagado: string;
  montoAplicadoMora: string;
  montoAplicadoCapital: string;
  cuotaNumero: number;
  saldoRestanteCuota: string;
  moraRestanteCuota: string;
  saldoRestanteCredito: string;
  estadoCredito: string;
}

export interface PagoCuota {
  codCliente: string;
  codCredito: string;
  montoPago: string;
  cuentaOrigen: string;
  referenciaTransaccion: string;
}

export const formatoMoneda = (monto: string | number, moneda = "PEN") =>
  `${moneda === "USD" ? "$" : "S/"} ${Number(monto).toFixed(2)}`;

/** Cobranza responde sus errores de negocio como COREDB: {"error": {"code", "message"}}. */
export const mensajeDeError = mensajeError;

export const esSesionInvalida = (err: unknown) => axios.isAxiosError(err) && err.response?.status === 401;

/** RF-COB-002 / RF-COB-012: créditos (con su cronograma) de un cliente. */
export async function creditosDeCliente(idCliente: string): Promise<Credito[]> {
  const { data } = await api.get<Credito[]>(`/clientes/${encodeURIComponent(idCliente)}/creditos`);
  return data;
}

export async function montoAPagar(codCredito: string): Promise<MontoAPagar> {
  const { data } = await api.get<MontoAPagar>(`/creditos/${encodeURIComponent(codCredito)}/monto-a-pagar`);
  return data;
}

/** CR-INT-08: la misma referenciaTransaccion en un reintento no cobra dos veces. */
export async function pagarCuota(pago: PagoCuota): Promise<ResultadoPago> {
  const { data } = await api.post<ResultadoPago>("/cr-int-08/pagos", pago);
  return data;
}

export async function comprobante(referenciaTransaccion: string): Promise<Comprobante> {
  const { data } = await api.get<Comprobante>(`/pagos/${encodeURIComponent(referenciaTransaccion)}/comprobante`);
  return data;
}
