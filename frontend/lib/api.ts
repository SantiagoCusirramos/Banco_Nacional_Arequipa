import axios from "axios";

// Instancia para el CORE (Puerto 8000)
export const apiCore = axios.create({
  baseURL: "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
});

// Instancia para CUENTAS (Puerto 8001)
export const apiCuentas = axios.create({
  baseURL: "http://localhost:8001",
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
});

export function mensajeError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (data?.error?.message) return data.error.message;
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d: { msg: string }) => d.msg).join(", "); 
    }
    if (err.code === "ERR_NETWORK") return "No se pudo conectar con el servidor";
    return err.message;
  }
  return "Error inesperado";
}
