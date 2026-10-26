import { api } from "./api";

export type Cliente = {
  id_cliente: string;
  cod_tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  fecha_nacimiento: string | null;
  numero_celular: string;
  correo_electronico: string | null;
  estado_cliente: string;
  fecha_registro: string | null;
};

export async function buscarClientesPorDocumento(documento: string): Promise<Cliente[]> {
  const { data } = await api.get<Cliente[]>("/core/clientes", {
    params: { documento: documento.trim() },
  });
  return data;
}

export async function verCliente(idCliente: string): Promise<Cliente> {
  const { data } = await api.get<Cliente>(`/core/clientes/${encodeURIComponent(idCliente)}`);
  return data;
}

export async function clienteConDocumento(documento: string): Promise<Cliente | null> {
  const lista = await buscarClientesPorDocumento(documento);
  return lista.find((c) => c.numero_documento === documento.trim()) ?? null;
}

export function nombreCompleto(c: Cliente): string {
  return [c.nombres, c.apellido_paterno, c.apellido_materno].filter(Boolean).join(" ");
}
