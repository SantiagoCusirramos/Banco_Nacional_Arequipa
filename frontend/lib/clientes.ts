import { api } from "@/lib/api";

export type NuevoCliente = {
  cod_tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  numero_celular: string;
};

export async function crearCliente(datos: NuevoCliente) {
  const { data } = await api.post("/core/clientes", datos);
  return data; // { cliente: {...}, duplicado: boolean }
}
