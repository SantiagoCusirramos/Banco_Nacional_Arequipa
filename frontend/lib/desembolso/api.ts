import axios, { AxiosError } from "axios";

// El navegador solo habla con el frontend: /api/desembolso reenvía a la API de Desembolso con el token de
// COREDB de la sesión (el mismo del inicio de sesión del producto). Desembolso devuelve los errores de
// COREDB: {"error": {"code", "message"}}.
export const api = axios.create({ baseURL: "/api/desembolso", headers: { "Content-Type": "application/json" }, timeout: 20000 });

export class ErrorApi extends Error {
  constructor(
    mensaje: string,
    public codigo: string,
    public estado: number,
    public correlationId?: string,
  ) {
    super(mensaje);
  }
}

api.interceptors.request.use((config) => {
  config.headers.set("X-Correlation-ID", crypto.randomUUID());
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("bna_access_token");
    if (token) config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

type Cuerpo = { error?: { code?: string; message?: string }; detail?: unknown };

function mensaje(estado: number, datos: Cuerpo | undefined): string {
  if (datos?.error?.message) return datos.error.message;
  if (typeof datos?.detail === "string") return datos.detail;
  if (Array.isArray(datos?.detail)) return "Revisa los datos enviados: algún campo no es válido.";
  if (estado === 401) return "La sesión no es válida o ya venció.";
  if (estado === 403) return "Tu usuario no tiene permiso para esta operación.";
  return "No se pudo comunicar con el servidor";
}

api.interceptors.response.use(
  (respuesta) => respuesta,
  (error: AxiosError<Cuerpo>) => {
    const estado = error.response?.status ?? 0;
    const datos = error.response?.data;
    const codigo = datos?.error?.code ?? (estado === 401 ? "NO_AUTENTICADO" : estado === 422 ? "DATOS_INVALIDOS" : "ERROR_DE_RED");
    return Promise.reject(new ErrorApi(mensaje(estado, datos), codigo, estado, error.response?.headers?.["x-correlation-id"]));
  },
);

export function nuevaClave(): string {
  return crypto.randomUUID();
}
