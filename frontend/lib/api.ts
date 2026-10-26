import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
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
