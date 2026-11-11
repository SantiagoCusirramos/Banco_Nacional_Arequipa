import { apiCore as api } from "@/lib/api";

export interface Agencia {
  id_agencia: string;
  nombre: string;
}

export async function listarAgencias(): Promise<Agencia[]> {
  const { data } = await api.get<Agencia[]>("/coredb/catalogos/agencias");
  return data;
}
