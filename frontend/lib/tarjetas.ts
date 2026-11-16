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
  /** La cuenta principal, la de su emisión. */
  num_cuenta: string | null;
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

/** Una autorización de TARJETAS: el débito aprobado o rechazado antes de contabilizarse. */
export interface Autorizacion {
  uuid_autorizacion: string;
  id_tarjeta: string;
  num_cuenta: string;
  id_canal: string | null;
  id_terminal: string | null;
  tipo_operacion: string;
  monto: string;
  estado_autorizacion: string;
  codigo_respuesta: string | null;
  motivo_rechazo: string | null;
  aprobada: boolean;
}

export const OPERACIONES = ["RETIRO", "PAGO", "FONDEO_BILLETERA"] as const;
export type Operacion = (typeof OPERACIONES)[number];
export const CANALES = ["ATM", "VEN", "HB", "AGE", "BD"] as const;
export type Canal = (typeof CANALES)[number];
export const TIPOS_CLAVE = ["PIN_ATM", "CLAVE_WEB"] as const;
export type TipoClave = (typeof TIPOS_CLAVE)[number];
// RN-TAR-001
export const DIGITOS_CLAVE: Record<TipoClave, number> = { PIN_ATM: 4, CLAVE_WEB: 6 };

// Códigos de respuesta ISO 8583 que devuelve la base.
export const CODIGOS_RESPUESTA: Record<string, string> = {
  "00": "Aprobada",
  "51": "Fondos insuficientes",
  "54": "Tarjeta vencida",
  "57": "No permitida para la tarjeta o la cuenta",
  "61": "Excede el tope diario del canal",
  "62": "Tarjeta no operativa",
  EXT: "Extornada",
};

export interface Autorizar {
  num_cuenta: string;
  tipo_operacion: Operacion;
  monto: string;
  id_canal: Canal;
}

// Con la misma llave, repetir la autorización devuelve la ya registrada y no retiene dos veces.
export async function autorizarOperacion(idTarjeta: string, datos: Autorizar, llave: string): Promise<Autorizacion> {
  const { data } = await api.post<Sobre<Autorizacion>>(`/${encodeURIComponent(idTarjeta)}/autorizaciones`, datos, {
    headers: { "X-Idempotency-Key": llave },
  });
  return data.data;
}

export async function extornarAutorizacion(uuid: string, motivo: string): Promise<Autorizacion> {
  const { data } = await api.post<Sobre<Autorizacion>>(`/autorizaciones/${encodeURIComponent(uuid)}/extorno`, { motivo });
  return data.data;
}

// La clave solo viaja en el cuerpo de la petición: no se guarda ni se muestra.
export async function registrarClave(idTarjeta: string, tipo: TipoClave, valor: string): Promise<void> {
  await api.put(`/${encodeURIComponent(idTarjeta)}/credenciales/${tipo}`, { valor });
}

export interface Validacion {
  resultado: "EXITOSO" | "FALLIDO";
  intentos_restantes: number;
}

export async function validarClave(idTarjeta: string, tipo: TipoClave, valor: string, canal: Canal): Promise<Validacion> {
  const { data } = await api.post<Sobre<Validacion>>(
    `/${encodeURIComponent(idTarjeta)}/credenciales/${tipo}/validacion`, { valor, id_canal: canal },
  );
  return data.data;
}
