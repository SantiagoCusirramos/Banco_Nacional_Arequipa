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

export const REGIMENES = ["INDIVIDUAL", "MANCOMUNADA_INDISTINTA", "MANCOMUNADA_CONJUNTA"];
export const ROLES_TITULAR = ["TITULAR", "MANCOMUNADO", "APODERADO", "TUTOR", "BENEFICIARIO", "CO-TITULAR"];
export const ESTADOS_CUENTA = ["ACTIVA", "BLOQUEADA", "CERRADA", "INACTIVA"];

// Ajustados para soportar un segundo argumento (ej. la moneda) que le estabas pasando en los componentes
export const formatoFecha = (fecha: string, extraInfo?: any) => new Date(fecha).toLocaleDateString("es-PE");
export const formatoMoneda = (monto: number, moneda?: string) => `${moneda === 'USD' ? '$' : 'S/'} ${Number(monto).toFixed(2)}`;

export const mensajeDeError = mensajeError; 

function digitos(n: number) {
  return Array.from({ length: n }, () => Math.floor(Math.random() * 10)).join("");
}

// COREDB exige num_cuenta y cci; si el formulario no los trae se generan (PROPUESTA)
function armarApertura(p: any) {
  const titulares = (p.titulares ?? [{ id_cliente: p.id_cliente }]).map((t: any) => ({ id_cliente: t.id_cliente }));
  return {
    num_cuenta: p.num_cuenta ?? digitos(14),
    cci: p.cci ?? digitos(20),
    moneda: p.moneda ?? "PEN",
    regimen: p.regimen ?? "INDIVIDUAL",
    id_agencia: p.id_agencia,
    titulares,
  };
}

export async function abrirCuenta(payload: any) {
  const { data } = await api.post("/apertura", armarApertura(payload));
  return data;
}

export async function crearCuenta(payload: any) {
  return abrirCuenta(payload);
}

export async function obtenerCuenta(numCuenta: string) {
  const { data } = await api.get(`/${numCuenta}`);
  return data;
}

export async function verCuenta(numCuenta: string) {
  return obtenerCuenta(numCuenta);
}

export async function modificarCuenta(numCuenta: string, payload: any) {
  const { data } = await api.put(`/${numCuenta}`, payload);
  return data;
}

export async function obtenerCuentasCliente(idCliente: string) {
  const { data } = await api.get(`/consolidada/${idCliente}`);
  return data;
}

export async function realizarDeposito(payload: { num_cuenta: string; monto: number; moneda?: string; id_terminal?: string }) {
  const { data } = await api.post("/deposito", payload);
  return data;
}

export async function realizarRetiro(payload: { num_cuenta: string; monto: number; moneda?: string; id_terminal?: string }) {
  const { data } = await api.post("/retiro", payload);
  return data;
}

export async function realizarTransferencia(payload: { num_cuenta_origen: string; num_cuenta_destino: string; monto: number; moneda?: string; id_terminal?: string }) {
  const { data } = await api.post("/transferencia", payload);
  return data;
}