import { api } from "@/lib/api";

export type Usuario = {
  id_usuario: string;
  username: string;
  nombre: string;
  rol: string;
  id_empleado: string | null;
  activo: boolean;
  creado_en: string;
  acciones?: string[];
};

export type LoginRespuesta = {
  access_token: string;
  token_type: string;
  expires_in: number;
  usuario: Usuario;
};

const TOKEN_KEY = "bna_access_token";
const USER_KEY = "bna_usuario";

export function guardarSesion(token: string, usuario: Usuario) {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(usuario));
}

export function obtenerToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function obtenerUsuarioGuardado(): Usuario | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as Usuario; } catch { return null; }
}

export function cerrarSesion() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function iniciarSesion(username: string, password: string) {
  const { data } = await api.post<LoginRespuesta>("/core/auth/login", { username, password });
  guardarSesion(data.access_token, data.usuario);
  return data;
}

export async function obtenerMiPerfil() {
  const { data } = await api.get<Usuario>("/core/auth/me");
  if (obtenerToken()) guardarSesion(obtenerToken()!, data);
  return data;
}

export async function registrarUsuario(datos: {
  username: string;
  nombre: string;
  password: string;
  rol: string;
  id_empleado?: string | null;
}) {
  const { data } = await api.post<Usuario>("/core/usuarios", {
    ...datos,
    activo: true,
  });
  return data;
}
