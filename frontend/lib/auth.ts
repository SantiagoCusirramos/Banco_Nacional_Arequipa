import { api } from "@/lib/api";

export type Usuario = {
  id_usuario: string;
  username: string;
  nombre: string;
  rol: string;
  modulo?: string | null;
  activo?: boolean;
  acciones?: string[];
  /** Con la contraseña inicial o renovada: debe cambiarla antes de operar (bd-v1.17). */
  debe_cambiar_clave?: boolean;
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
  const { data } = await api.post<LoginRespuesta>("/coredb/auth/login", { username, password });
  guardarSesion(data.access_token, data.usuario);
  return data;
}

/** El perfil vigente en COREDB. Falla con 401 si el token ya no sirve. */
export async function obtenerMiPerfil(): Promise<Usuario> {
  const { data } = await api.get<Omit<Usuario, "nombre">>("/coredb/auth/me");
  // /coredb/auth/me no trae el nombre: se conserva el que dio el login.
  const guardado = obtenerUsuarioGuardado();
  const usuario: Usuario = { ...data, nombre: guardado?.nombre || data.username };
  const token = obtenerToken();
  if (token) guardarSesion(token, usuario);
  return usuario;
}

/** La persona cambia su contraseña (obligatorio tras la inicial o una renovada). */
export async function cambiarClave(actual: string, nueva: string) {
  const { data } = await api.post<{ debe_cambiar_clave: boolean }>("/coredb/auth/clave", { actual, nueva });
  const guardado = obtenerUsuarioGuardado();
  const token = obtenerToken();
  if (guardado && token) guardarSesion(token, { ...guardado, debe_cambiar_clave: data.debe_cambiar_clave });
  return data;
}
