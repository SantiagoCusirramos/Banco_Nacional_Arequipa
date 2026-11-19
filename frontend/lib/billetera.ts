import { isAxiosError } from "axios";
import { apiCore as api } from "@/lib/api";

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
    const cuerpo = err.response?.data as
      | { error?: { code?: string; message?: string }; detail?: unknown; message?: string }
      | undefined;
    if (cuerpo?.error?.message) return `${cuerpo.error.message}${cuerpo.error.code ? ` (${cuerpo.error.code})` : ""}`;
    if (Array.isArray(cuerpo?.detail)) return "Revise los datos: el PIN debe tener 6 dígitos y el RUC 11.";
    if (typeof cuerpo?.detail === "string") return cuerpo.detail;
    if (cuerpo?.message) return cuerpo.message;
    if (err.response?.status === 401) return "La sesión venció: vuelva a iniciar sesión.";
    if (err.response?.status === 403) return "Su rol no puede afiliar clientes a la billetera.";
    return err.message;
  }
  return err instanceof Error ? err.message : "Error inesperado";
}
