import { isAxiosError } from "axios";
import { apiCore as api, mensajeError } from "@/lib/api";

// Afiliación a la billetera Chaski y registro de comercios. Son rutas del banco en COREDB
// (/coredb/billetera/*), por el puente /api/core: exigen el token del personal con los
// permisos AFILIAR_BILLETERA y REGISTRAR_COMERCIO (ADMINISTRADOR, ASESOR u OPERADOR).

export interface Afiliacion {
  cod_cliente: string;
  num_cuenta: string;
  estado: string;
  /** false si ya estaba afiliado: cambió el PIN o la cuenta y quedó ACTIVA. */
  nueva: boolean;
}

export interface Comercio {
  id_comercio: string;
  ruc: string;
  razon_social: string;
  num_cuenta: string;
  estado: string;
  id_qr: string | null;
}

export async function afiliar(datos: { cod_cliente: string; num_cuenta: string; pin: string }): Promise<Afiliacion> {
  const { data } = await api.post<Afiliacion>("/coredb/billetera/afiliaciones", datos);
  return data;
}

export async function registrarComercio(datos: { ruc: string; razon_social: string; num_cuenta: string }): Promise<Comercio> {
  const { data } = await api.post<Comercio>("/coredb/billetera/comercios", datos);
  return data;
}

/** El mensaje que devuelve COREDB ({"error": {"code", "message"}} o el 422 de validación). */
export function mensajeDeError(err: unknown): string {
  if (isAxiosError(err)) {
    const cuerpo = err.response?.data as { detail?: unknown } | undefined;
    if (Array.isArray(cuerpo?.detail)) return "Revise los datos: el PIN debe tener 6 dígitos y el RUC 11.";
  }
  return mensajeError(err);
}
