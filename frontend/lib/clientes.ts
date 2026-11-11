import { apiCore as api } from "@/lib/api";

/** El cliente como lo devuelve COREDB (GET /coredb/clientes/{cod_cliente}). */
export interface Cliente {
  cod_cliente: string;
  tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  estado_cliente: string;
  permite_operar: boolean;
}

// El CORE no ofrece búsqueda por documento ni por nombre: un cliente se consulta por su código.
export async function obtenerCliente(codCliente: string): Promise<Cliente> {
  const { data } = await api.get<Cliente>(`/coredb/clientes/${encodeURIComponent(codCliente)}`);
  return data;
}

export function nombreCompleto(cliente: Cliente) {
  return [cliente.nombres, cliente.apellido_paterno, cliente.apellido_materno].filter(Boolean).join(" ");
}
