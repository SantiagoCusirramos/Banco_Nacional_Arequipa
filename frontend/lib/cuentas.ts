import { apiCuentas as api, mensajeError } from "@/lib/api";

// Agregamos "INACTIVA" para satisfacer a ModificarCuenta.tsx
export type EstadoCuenta = "ACTIVA" | "BLOQUEADA" | "CERRADA" | "INACTIVA" | "EMBARGO";

export interface Titular {
  id_cliente: string;
  rol_titular: string;
}

export interface Cuenta {
  id_cuenta?: string; // opcional por si acaso
  num_cuenta: string;
  saldo_disponible: number;
  saldo_contable: number;
  saldo_retenido: number;
  estado_cuenta: EstadoCuenta;
  moneda: string;
  regimen: string;
  fecha_apertura: string;
  id_agencia: string;
  id_producto_ahorro: string;
  titulares: Titular[];
}

export const REGIMENES = ["LIBRE", "PROGRAMADO", "INFANTIL", "CTS", "A_PLAZO", "MANCOMUNADO"];
export const ROLES_TITULAR = ["TITULAR", "MANCOMUNADO", "APODERADO", "TUTOR", "BENEFICIARIO", "CO-TITULAR"];
export const ESTADOS_CUENTA = ["ACTIVA", "BLOQUEADA", "CERRADA", "INACTIVA"];

// Ajustados para soportar un segundo argumento (ej. la moneda) que le estabas pasando en los componentes
export const formatoFecha = (fecha: string, extraInfo?: any) => new Date(fecha).toLocaleDateString("es-PE");
export const formatoMoneda = (monto: number, moneda?: string) => `${moneda === 'USD' ? '$' : 'S/'} ${Number(monto).toFixed(2)}`;

export const mensajeDeError = mensajeError; 

export async function abrirCuenta(payload: any) {
  const { data } = await api.post("/api/v1/cuentas/apertura", payload);
  return data;
}

export async function crearCuenta(payload: any) {
  return abrirCuenta(payload);
}

export async function obtenerCuenta(numCuenta: string) {
  const { data } = await api.get(`/api/v1/cuentas/${numCuenta}`);
  return data;
}

export async function verCuenta(numCuenta: string) {
  return obtenerCuenta(numCuenta);
}

export async function modificarCuenta(numCuenta: string, payload: any) {
  const { data } = await api.put(`/api/v1/cuentas/${numCuenta}`, payload);
  return data;
}

export async function obtenerCuentasCliente(idCliente: string) {
  const { data } = await api.get(`/api/v1/cuentas/consolidada/${idCliente}`);
  return data;
}

export async function realizarDeposito(payload: { num_cuenta: string; monto: number; moneda?: string; id_terminal?: string }) {
  const { data } = await api.post("/api/v1/cuentas/deposito", payload);
  return data;
}

export async function realizarRetiro(payload: { num_cuenta: string; monto: number; moneda?: string; id_terminal?: string }) {
  const { data } = await api.post("/api/v1/cuentas/retiro", payload);
  return data;
}

export async function realizarTransferencia(payload: { num_cuenta_origen: string; num_cuenta_destino: string; monto: number; moneda?: string; id_terminal?: string }) {
  const { data } = await api.post("/api/v1/cuentas/transferencia", payload);
  return data;
}