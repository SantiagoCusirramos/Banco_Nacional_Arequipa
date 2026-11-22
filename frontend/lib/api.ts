import axios, { type InternalAxiosRequestConfig } from "axios";

const TOKEN_KEY = "bna_access_token";

// Canal con el que el personal registra depósitos, retiros y transferencias. CUENTAS
// lo recibe en X-Channel-ID. Ventanilla (VEN) tiene tope definido en el CORE para las
// dos monedas; agencia (AGE) todavía no, y sus débitos se rechazan.
export const CANAL = "VEN";

function conToken(config: InternalAxiosRequestConfig) {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

// COREDB por el puente de Next (/api/core): sesión, usuarios, clientes y catálogos.
// El navegador nunca llama directamente al CORE.
export const apiCore = axios.create({
  baseURL: "/api/core",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});
apiCore.interceptors.request.use(conToken);
export const api = apiCore;

// CUENTAS por el puente de Next (/api/cuenta), que reenvía el token y las cabeceras.
export const apiCuentas = axios.create({
  baseURL: "/api/cuenta",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

// TARJETAS por el puente de Next (/api/tarjeta), que reenvía el token.
export const apiTarjetas = axios.create({
  baseURL: "/api/tarjeta",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});
apiTarjetas.interceptors.request.use(conToken);

// EVALUACIÓN por el puente de Next (/api/evaluacion), que reenvía el token de COREDB.
export const apiEvaluacion = axios.create({
  baseURL: "/api/evaluacion",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});
apiEvaluacion.interceptors.request.use(conToken);

// CAPTACION por el puente de Next (/api/captacion), que reenvía el token.
export const apiCaptacion = axios.create({
  baseURL: "/api/captacion",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});
apiCaptacion.interceptors.request.use(conToken);

// COBRANZA por el puente de Next (/api/cobranza), que reenvía el token de COREDB.
export const apiCobranza = axios.create({
  baseURL: "/api/cobranza",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});
apiCobranza.interceptors.request.use(conToken);

// SEGURIDAD por el puente de Next (/api/seguridad), que solo deja pasar las rutas de la
// pantalla de desbloqueo de tarjetas.
export const apiSeguridad = axios.create({
  baseURL: "/api/seguridad",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});
apiSeguridad.interceptors.request.use(conToken);

/**
 * Cabeceras que CUENTAS exige en toda operación que mueve dinero. La llave la pone quien
 * llama: la misma para cada reintento de la misma operación (si no, CUENTAS movería el
 * dinero otra vez) y una nueva cuando cambian los datos o la operación ya se registró.
 */
export function cabecerasDeOperacion(llave: string): Record<string, string> {
  return {
    "X-Idempotency-Key": llave,
    "X-Channel-ID": CANAL,
    "X-Request-Timestamp": new Date().toISOString(),
  };
}

apiCuentas.interceptors.request.use(conToken);

/**
 * Con la contraseña inicial o renovada, COREDB responde 403 CAMBIO_CLAVE_OBLIGATORIO a todo lo
 * demás: cualquier pantalla lleva entonces a cambiarla. El error sigue su curso.
 */
export function alExigirCambioDeClave(err: unknown): never {
  if (axios.isAxiosError(err) && err.response?.status === 403
      && err.response.data?.error?.code === "CAMBIO_CLAVE_OBLIGATORIO"
      && typeof window !== "undefined" && window.location.pathname !== "/cambiar-clave") {
    window.location.assign("/cambiar-clave");
  }
  throw err;
}
for (const cliente of [apiCore, apiCuentas, apiTarjetas, apiEvaluacion, apiCaptacion, apiCobranza, apiSeguridad]) {
  cliente.interceptors.response.use(undefined, alExigirCambioDeClave);
}

export function mensajeError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (data?.error?.message) return data.error.message; // COREDB
    if (typeof data?.message === "string" && data.message) return data.message; // CUENTAS, TARJETAS, CAPTACION
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) return "Revisa los datos enviados: algún campo no es válido.";
    if (err.response?.status === 401) return "Credenciales incorrectas o sesión vencida.";
    if (err.response?.status === 403) return "Tu usuario no tiene permisos para realizar esta operación.";
    if (err.code === "ERR_NETWORK") return "No se pudo conectar con el servidor.";
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Error inesperado";
}
