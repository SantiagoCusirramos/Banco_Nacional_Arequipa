import axios from "axios";
import { api } from "@/lib/api";

// Valores admitidos por el backend (CORE/services/cuentassvc.py)
export const REGIMENES = ["LIBRE", "PROGRAMADO", "INFANTIL", "CTS", "A_PLAZO"] as const;
export const ROLES_TITULAR = ["TITULAR", "MANCOMUNADO", "APODERADO", "TUTOR", "BENEFICIARIO"] as const;
export const ESTADOS_CUENTA = ["ACTIVA", "INACTIVA", "BLOQUEADA", "EMBARGO"] as const;

export type Regimen = (typeof REGIMENES)[number];
export type RolTitular = (typeof ROLES_TITULAR)[number];
export type EstadoCuenta = (typeof ESTADOS_CUENTA)[number];

export type Titular = { id_cliente: string; rol_titular: string };

// Respuesta del backend (CuentaRespuesta). Los Decimal llegan como string.
export type Cuenta = {
  num_cuenta: string;
  moneda: string;
  regimen: string;
  estado_cuenta: string;
  saldo_contable: string | number;
  saldo_disponible: string | number;
  saldo_retenido: string | number;
  fecha_apertura: string;
  id_agencia: string;
  id_producto_ahorro: string;
  titulares: Titular[];
};

export type NuevaCuenta = {
  id_cliente: string;
  id_producto_ahorro: string;
  id_agencia: string;
  regimen: Regimen;
  titulares?: { id_cliente: string; rol_titular: RolTitular }[];
};

// Identifica al canal en la auditoría del backend (campo `actor`).
const ACTOR = "portal-web";

function nuevoCorrelationId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `web-${Date.now()}`;
}

function conTrazabilidad() {
  const correlation_id = nuevoCorrelationId();
  return { correlation_id, config: { headers: { "x-correlation-id": correlation_id } } };
}

/** POST /core/cuentas — Crear cuenta */
export async function crearCuenta(datos: NuevaCuenta): Promise<Cuenta> {
  const { correlation_id, config } = conTrazabilidad();
  const { data } = await api.post<Cuenta>("/core/cuentas", { ...datos, actor: ACTOR, correlation_id }, config);
  return data;
}

/** GET /core/cuentas/{num_cuenta} — Ver cuenta */
export async function verCuenta(numCuenta: string): Promise<Cuenta> {
  const { data } = await api.get<Cuenta>(`/core/cuentas/${encodeURIComponent(numCuenta)}`);
  return data;
}

/** PATCH /core/cuentas/{num_cuenta} — Modificar cuenta (estado) */
export async function modificarCuenta(numCuenta: string, estado: EstadoCuenta): Promise<Cuenta> {
  const { correlation_id, config } = conTrazabilidad();
  const { data } = await api.patch<Cuenta>(
    `/core/cuentas/${encodeURIComponent(numCuenta)}`,
    { estado_cuenta: estado, actor: ACTOR, correlation_id },
    config,
  );
  return data;
}

/**
 * Convierte cualquier error de las llamadas anteriores en un texto para el usuario.
 * El backend responde { error: { code, message } } para errores de negocio
 * y { detail: [...] } (FastAPI) para errores de validación (422).
 */
export function mensajeDeError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (!err.response) {
      return `No se pudo conectar con el servidor (${api.defaults.baseURL ?? "URL no configurada"}). Verifica que el backend esté en ejecución.`;
    }
    const data = err.response.data as
      | { error?: { code?: string; message?: string }; detail?: unknown }
      | undefined;
    if (data?.error?.message) {
      return data.error.code ? `${data.error.message} (${data.error.code})` : data.error.message;
    }
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      const primero = data.detail[0] as { loc?: unknown[]; msg?: string };
      const campo = Array.isArray(primero.loc) ? primero.loc.filter((p) => p !== "body").join(".") : "";
      return `Datos inválidos${campo ? ` en «${campo}»` : ""}: ${primero.msg ?? "revisa el formulario"}.`;
    }
    return `El servidor respondió con un error (${err.response.status}). Inténtalo nuevamente.`;
  }
  return "Ocurrió un error inesperado. Inténtalo nuevamente.";
}

export function formatoMoneda(valor: string | number, moneda: string): string {
  const numero = Number(valor);
  try {
    return new Intl.NumberFormat("es-PE", { style: "currency", currency: moneda }).format(numero);
  } catch {
    return `${moneda} ${numero.toFixed(2)}`;
  }
}

export function formatoFecha(iso: string): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" }).format(fecha);
}
