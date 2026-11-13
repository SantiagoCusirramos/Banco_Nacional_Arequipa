import { apiTarjetas as api, mensajeError } from "@/lib/api";

/** La tarjeta como la devuelve TARJETAS, que la toma de COREDB sin el token del PAN. */
export interface Tarjeta {
  id_tarjeta: string;
  bin: string;
  ultimos4: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  estado_tarjeta: string;
  cod_cliente: string;
  numero_enmascarado: string;
  vencimiento_mm_aa: string;
}

export interface Emision {
  cod_cliente: string;
  num_cuenta: string;
  bin: string;
  fecha_vencimiento: string;
}

// Estados que se pueden pedir. ANULADA llega a la base como CANCELADA. El desbloqueo
// (de BLOQUEADA a ACTIVA) lo rechaza COREDB: es de Seguridad.
export const ESTADOS_PEDIBLES = ["ACTIVA", "BLOQUEADA", "RETENIDA", "ANULADA"] as const;
export type EstadoPedible = (typeof ESTADOS_PEDIBLES)[number];

// Único BIN del catálogo de la base integrada (tarjetas.bin_tarjeta): de desarrollo y FISICA.
// Los BIN reales son un pendiente del emisor (issue #34, pregunta 7).
export const BINES = ["004499"];

export const mensajeDeError = mensajeError;

// Respuesta de TARJETAS (ITIL-02): los datos van en `data`.
type Sobre<T> = { success: boolean; message?: string; data: T };

export async function tarjetasDeCliente(codCliente: string): Promise<Tarjeta[]> {
  const { data } = await api.get<Sobre<Tarjeta[]>>(`/cliente/${encodeURIComponent(codCliente)}`);
  return data.data;
}

export async function verTarjeta(idTarjeta: string): Promise<Tarjeta> {
  const { data } = await api.get<Sobre<Tarjeta>>(`/${encodeURIComponent(idTarjeta)}`);
  return data.data;
}

// El PAN nunca pasa por el frontend: TARJETAS envía un token en su lugar. Con la misma
// llave, repetir la emisión devuelve la tarjeta ya emitida en vez de emitir otra.
export async function emitirTarjeta(emision: Emision, llave: string): Promise<Tarjeta> {
  const { data } = await api.post<Sobre<Tarjeta>>("/emision", emision, {
    headers: { "X-Idempotency-Key": llave },
  });
  return data.data;
}

export async function cambiarEstado(idTarjeta: string, estado: EstadoPedible, motivo: string): Promise<Tarjeta> {
  const { data } = await api.post<Sobre<Tarjeta>>(`/${encodeURIComponent(idTarjeta)}/estado`, {
    estado,
    ...(motivo ? { motivo } : {}),
  });
  return data.data;
}
