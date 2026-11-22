import { isAxiosError } from "axios";
import { apiSeguridad as api } from "@/lib/api";

/** Un cambio de estado de la tarjeta, como lo guarda la base (historial). */
export interface CambioEstado {
  id_historial: number;
  estado_nuevo: string;
  motivo: string | null;
  origen: string;
  fecha_hora: string;
}

export interface TarjetaSeguridad {
  id_tarjeta: string;
  bin: string;
  ultimos4: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  estado_tarjeta: string;
  cod_cliente: string;
  num_cuenta: string | null;
  numero_enmascarado: string;
}

/** La tarjeta con lo necesario para decidir: si se puede desbloquear y por qué está bloqueada. */
export interface FichaTarjeta extends TarjetaSeguridad {
  desbloqueable: boolean;
  bloqueo: CambioEstado | null;
  historial: CambioEstado[];
}

export interface Desbloqueo extends Omit<TarjetaSeguridad, "numero_enmascarado"> {
  cambio: CambioEstado & { estado_anterior: string; actor: string };
}

export const PERMISO_DESBLOQUEO = "BLOQUEAR_TARJETA";

export async function tarjetasDelCliente(codCliente: string): Promise<TarjetaSeguridad[]> {
  const { data } = await api.get<TarjetaSeguridad[]>("/tarjetas", { params: { cod_cliente: codCliente } });
  return data;
}

export async function fichaDeTarjeta(idTarjeta: string): Promise<FichaTarjeta> {
  const { data } = await api.get<FichaTarjeta>(`/tarjetas/${encodeURIComponent(idTarjeta)}`);
  return data;
}

export async function desbloquearTarjeta(idTarjeta: string, motivo: string): Promise<Desbloqueo> {
  const { data } = await api.post<Desbloqueo>(`/tarjetas/${encodeURIComponent(idTarjeta)}/desbloqueo`, { motivo });
  return data;
}

// Textos para el personal, sin los códigos internos.
const ESTADOS: Record<string, string> = {
  ACTIVA: "Activa", BLOQUEADA: "Bloqueada", RETENIDA: "Retenida", CANCELADA: "Anulada", ANULADA: "Anulada",
  VENCIDA: "Vencida", EMITIDA: "Emitida, sin activar", INACTIVA: "Inactiva",
};
export const nombreEstado = (estado: string) =>
  ESTADOS[estado] ?? estado.charAt(0) + estado.slice(1).toLowerCase().replaceAll("_", " ");

const ORIGENES: Record<string, string> = {
  CLIENTE: "El cliente", OPERADOR: "Personal del banco", SISTEMA: "Proceso automático del banco",
  SEGURIDAD: "Área de Seguridad", MODULO_CLIENTES: "Registro de clientes",
};
export const nombreOrigen = (origen: string) => ORIGENES[origen] ?? "Otro";

/** Fecha y hora de Arequipa (UTC−5), dd/mm/aaaa hh:mm. */
export function fechaHora(iso: string): string {
  const partes = new Intl.DateTimeFormat("es-PE", {
    timeZone: "America/Lima", day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(new Date(iso));
  const p = (tipo: string) => partes.find((x) => x.type === tipo)?.value ?? "";
  return `${p("day")}/${p("month")}/${p("year")} ${p("hour")}:${p("minute")}`;
}

export type TipoError = "sesion" | "permiso" | "no_bloqueada" | "no_encontrada" | "sin_respuesta" | "otro";

export function tipoDeError(err: unknown): TipoError {
  if (!isAxiosError(err)) return "otro";
  const estado = err.response?.status;
  const codigo = (err.response?.data as { error?: { code?: string } } | undefined)?.error?.code;
  if (!err.response || estado === 502 || estado === 503 || estado === 504) return "sin_respuesta";
  if (estado === 401) return "sesion";
  if (estado === 403) return "permiso";
  if (codigo === "TARJETA_NO_BLOQUEADA") return "no_bloqueada";
  if (estado === 404) return "no_encontrada";
  return "otro";
}

export function mensajeParaPersonal(err: unknown, buscando: "cliente" | "tarjeta" | "desbloqueo"): string {
  switch (tipoDeError(err)) {
    case "sesion": return "Tu sesión venció. Vuelve a iniciarla.";
    case "permiso": return "Tu usuario no tiene permiso para desbloquear tarjetas.";
    case "no_bloqueada": return "La tarjeta ya no está bloqueada: otra persona pudo desbloquearla. Revisa su estado actual.";
    case "no_encontrada":
      return buscando === "cliente" ? "No existe un cliente con ese código." : "No existe una tarjeta con ese número de identificación.";
    case "sin_respuesta":
      return buscando === "desbloqueo"
        ? "No sabemos si se desbloqueó: el servidor no respondió. Revisa el estado de la tarjeta antes de intentarlo de nuevo."
        : "El servidor no respondió. Intenta de nuevo en unos segundos.";
    default:
      return buscando === "desbloqueo"
        ? "No se pudo desbloquear la tarjeta. Revisa los datos e intenta de nuevo."
        : "No se pudo completar la búsqueda. Revisa los datos e intenta de nuevo.";
  }
}
