import { api as apiBridge, apiCore as api } from "@/lib/api";

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

/** Solicitante devuelto por la búsqueda del CORE; `cod_cliente` existe solo si ya es cliente. */
export interface SolicitanteBuscado {
  id_solicitante: string;
  tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  cod_cliente: string | null;
}

export function nombreSolicitante(s: SolicitanteBuscado) {
  return [s.nombres, s.apellido_paterno, s.apellido_materno].filter(Boolean).join(" ");
}

/**
 * Búsqueda por documento o nombre. El texto va en el cuerpo del POST: en la URL quedaría
 * expuesto en el historial y en los registros del puente.
 */
export async function buscarSolicitantes(texto: string): Promise<SolicitanteBuscado[]> {
  const { data } = await apiBridge.post<SolicitanteBuscado[]>("/coredb/captacion/solicitantes/busqueda", {
    texto, con_cliente: true, limite: 20,
  });
  return data;
}
