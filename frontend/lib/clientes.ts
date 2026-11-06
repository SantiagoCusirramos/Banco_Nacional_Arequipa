import { apiCore as api } from "@/lib/api";

export interface Cliente {
  id_cliente: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno?: string;
  numero_documento: string;
  cod_tipo_documento: string;
}

export type NuevoCliente = {
  cod_tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  numero_celular: string;
};

export async function crearCliente(datos: NuevoCliente) {
  const { data } = await api.post("/core/clientes", datos);
  return data;
}

export async function obtenerCliente(idCliente: string) {
  const { data } = await api.get(`/core/clientes/${idCliente}`);
  return data;
}

export async function buscarClientesPorDocumento(doc: string) {
  const { data } = await api.get(`/core/clientes/buscar?documento=${doc}`);
  return data;
}

export function nombreCompleto(cliente: Cliente) {
  return `${cliente.nombres} ${cliente.apellido_paterno}`;
}