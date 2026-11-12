import { apiCore as api, mensajeError } from "@/lib/api";

/** La tarjeta como la devuelve COREDB, sin el token del PAN. */
export interface Tarjeta {
  id_tarjeta: string;
  bin: string;
  ultimos4: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  estado_tarjeta: string;
  cod_cliente: string;
}

export interface Emision {
  cod_cliente: string;
  num_cuenta: string;
  bin: string;
  fecha_vencimiento: string;
  fecha_emision?: string;
  ultimos4?: string;
}

// Estados que se pueden pedir. ANULADA llega a la base como CANCELADA. El desbloqueo
// (de BLOQUEADA a ACTIVA) lo rechaza COREDB: es de Seguridad.
export const ESTADOS_PEDIBLES = ["ACTIVA", "BLOQUEADA", "RETENIDA", "ANULADA"] as const;
export type EstadoPedible = (typeof ESTADOS_PEDIBLES)[number];

// Único BIN del catálogo de la base integrada (tarjetas.bin_tarjeta).
export const BINES = ["004499"];

export const mensajeDeError = mensajeError;

const RUTA = "/coredb/tarjetas";

/** «MM/AA», como se imprime en la tarjeta (RN-TAR-003). */
export const vencimientoMmAa = (fecha: string) => `${fecha.slice(5, 7)}/${fecha.slice(2, 4)}`;

export const enmascarada = (tarjeta: Pick<Tarjeta, "bin" | "ultimos4">) =>
  `${tarjeta.bin.slice(0, 4)} ${tarjeta.bin.slice(4)}•• •••• ${tarjeta.ultimos4}`;

const hoy = () => new Date().toISOString().slice(0, 10);

function digitos(n: number) {
  return Array.from({ length: n }, () => Math.floor(Math.random() * 10)).join("");
}

export async function tarjetasDeCliente(codCliente: string): Promise<Tarjeta[]> {
  const { data } = await api.get<Tarjeta[]>(RUTA, { params: { cod_cliente: codCliente } });
  return data;
}

export async function verTarjeta(idTarjeta: string): Promise<Tarjeta> {
  const { data } = await api.get<Tarjeta>(`${RUTA}/${encodeURIComponent(idTarjeta)}`);
  return data;
}

// El PAN nunca pasa por el frontend: se envía un token aleatorio en su lugar y, si el
// formulario no los trae, los últimos cuatro dígitos.
export async function emitirTarjeta(emision: Emision): Promise<Tarjeta> {
  const { data } = await api.post<Tarjeta>(RUTA, {
    pan_token: crypto.randomUUID().replaceAll("-", ""),
    bin: emision.bin,
    ultimos4: emision.ultimos4 ?? digitos(4),
    fecha_emision: emision.fecha_emision ?? hoy(),
    fecha_vencimiento: emision.fecha_vencimiento,
    cod_cliente: emision.cod_cliente,
    num_cuenta: emision.num_cuenta,
  });
  return data;
}

export async function cambiarEstado(idTarjeta: string, estado: EstadoPedible, motivo: string): Promise<Tarjeta> {
  const { data } = await api.post<Tarjeta>(`${RUTA}/${encodeURIComponent(idTarjeta)}/estado`, {
    estado,
    ...(motivo ? { motivo } : {}),
  });
  return data;
}
