import { apiCore as api } from "@/lib/api";

export interface Agencia {
  id_agencia: string;
  nombre: string;
  direccion: string;
}

export interface ProductoAhorro {
  id_producto: string;
  nombre: string;
  moneda: string;
  tasa_tea: number;
}

export async function listarAgencias() {
  const { data } = await api.get("/core/agencias");
  return data;
}

export async function listarProductosAhorro() {
  const { data } = await api.get("/cuentas/productos");
  return data;
}