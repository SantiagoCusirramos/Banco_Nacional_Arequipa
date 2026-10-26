import { api } from "./api";

export type Agencia = {
  id_agencia: string;
  nombre: string;
  direccion: string;
};

export type ProductoAhorro = {
  id_producto_ahorro: string;
  nombre: string;
  moneda: string;
  tasa_tea: string | number;
};

export async function listarAgencias(): Promise<Agencia[]> {
  const { data } = await api.get<Agencia[]>("/core/catalogos/agencias");
  return data;
}

export async function listarProductosAhorro(): Promise<ProductoAhorro[]> {
  const { data } = await api.get<ProductoAhorro[]>("/core/catalogos/productos-ahorro");
  return data;
}
