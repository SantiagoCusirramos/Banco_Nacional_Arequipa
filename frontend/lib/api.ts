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

const OPERACIONES = ["/deposito", "/retiro", "/transferencia"];

/** Cabeceras que CUENTAS exige en toda operación que mueve dinero. */
export function cabecerasDeOperacion(): Record<string, string> {
  return {
    "X-Idempotency-Key": crypto.randomUUID(),
    "X-Channel-ID": CANAL,
    "X-Request-Timestamp": new Date().toISOString(),
  };
}

apiCuentas.interceptors.request.use((config) => {
  conToken(config);
  if (config.method === "post" && OPERACIONES.includes(config.url || "")) {
    for (const [nombre, valor] of Object.entries(cabecerasDeOperacion())) {
      config.headers[nombre] = valor;
    }
  }
  return config;
});

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
