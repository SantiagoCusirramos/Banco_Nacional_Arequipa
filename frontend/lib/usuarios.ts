import { api } from "@/lib/api";

// Gestión de usuarios del banco (COREDB /coredb/usuarios). Exige CREAR_USUARIO; cambiar el rol,
// ASIGNAR_ROLES. La contraseña inicial y la renovada las genera COREDB y llegan una sola vez.

export const PERMISO_USUARIOS = "CREAR_USUARIO";
export const ROLES = ["ASESOR", "ANALISTA", "OPERADOR", "AUDITOR", "ADMINISTRADOR"] as const;
export const NOMBRE_ROL: Record<string, string> = {
  ADMINISTRADOR: "Administrador", ASESOR: "Asesor", ANALISTA: "Analista", OPERADOR: "Operador", AUDITOR: "Auditor",
  SERVICIO: "Servicio (módulo)",
};

export type UsuarioBanco = {
  id_usuario: string;
  username: string;
  nombre: string;
  rol: string;
  modulo: string | null;
  id_empleado: string | null;
  activo: boolean;
  creado_en: string;
  debe_cambiar_clave?: boolean;
};

export async function listarUsuarios() {
  const { data } = await api.get<UsuarioBanco[]>("/coredb/usuarios?limite=200");
  return data;
}

/** Sin contraseña: COREDB genera la inicial y la devuelve solo en esta respuesta. */
export async function crearUsuario(datos: { username: string; nombre: string; rol: string }) {
  const { data } = await api.post<UsuarioBanco & { clave_inicial: string | null }>("/coredb/usuarios", datos);
  return data;
}

export async function renovarClave(id: string) {
  const { data } = await api.post<{ usuario: UsuarioBanco; clave_inicial: string }>(`/coredb/usuarios/${id}/clave`);
  return data;
}

export async function cambiarRol(id: string, rol: string) {
  const { data } = await api.post<UsuarioBanco>(`/coredb/usuarios/${id}/rol`, { rol });
  return data;
}

export async function cambiarEstado(id: string, activo: boolean) {
  const { data } = await api.post<UsuarioBanco>(`/coredb/usuarios/${id}/estado`, { activo });
  return data;
}

export async function desbloquearIngreso(id: string) {
  const { data } = await api.post<UsuarioBanco>(`/coredb/usuarios/${id}/desbloqueo`);
  return data;
}
