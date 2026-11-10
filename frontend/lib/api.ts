import axios from "axios";

export const api = axios.create({
  // Define NEXT_PUBLIC_API_URL en frontend/.env.local, por ejemplo:
  // NEXT_PUBLIC_API_URL=http://localhost:8000
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

// Añade el JWT automáticamente a las rutas protegidas del CORE.
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("bna_access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function mensajeError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (data?.error?.message) return data.error.message;
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d: { msg: string }) => d.msg).join(", ");
    }
    if (err.response?.status === 401) return "Credenciales incorrectas o sesión vencida.";
    if (err.response?.status === 403) return "Tu usuario no tiene permisos para realizar esta operación.";
    if (err.code === "ERR_NETWORK") return "No se pudo conectar con el servidor. Verifica que el backend esté encendido y que NEXT_PUBLIC_API_URL sea correcto.";
    return err.message;
  }
  return "Error inesperado";
}
