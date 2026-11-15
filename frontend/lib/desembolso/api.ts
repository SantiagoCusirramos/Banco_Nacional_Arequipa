import axios, { AxiosError } from "axios";

// El navegador solo habla con el frontend: /api/desembolso reenvía a la API de Desembolso con el token de
// COREDB de la sesión (el mismo del inicio de sesión del producto).
export const api = axios.create({ baseURL: "/api/desembolso", headers: { "Content-Type": "application/json" }, timeout: 20000 });

export class ErrorApi extends Error {
  constructor(
    mensaje: string,
    public codigo: string,
    public estado: number,
    public detalle?: unknown,
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

api.interceptors.response.use(
  (respuesta) => respuesta,
  (error: AxiosError<{ codigo?: string; mensaje?: string; detalle?: unknown; correlation_id?: string; detail?: string }>) => {
    const datos = error.response?.data;
    return Promise.reject(
      new ErrorApi(
        datos?.mensaje ?? datos?.detail ?? "No se pudo comunicar con el servidor",
        datos?.codigo ?? (error.response?.status === 401 ? "NO_AUTENTICADO" : "ERROR_DE_RED"),
        error.response?.status ?? 0,
        datos?.detalle,
        datos?.correlation_id ?? error.response?.headers?.["x-correlation-id"],
      ),
    );
  },
);

export function nuevaClave(): string {
  return crypto.randomUUID();
}
