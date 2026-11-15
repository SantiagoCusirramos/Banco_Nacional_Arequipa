"use client";

import { createContext, useContext } from "react";
import type { Sesion } from "./tipos";

const ContextoSesion = createContext<Sesion | null>(null);

export function ProveedorSesion({ sesion, children }: { sesion: Sesion; children: React.ReactNode }) {
  return <ContextoSesion.Provider value={sesion}>{children}</ContextoSesion.Provider>;
}

export function useSesion(): Sesion {
  const sesion = useContext(ContextoSesion);
  if (!sesion) throw new Error("useSesion debe usarse dentro de ProveedorSesion");
  return sesion;
}

export function puede(sesion: Sesion, permiso: string): boolean {
  return sesion.permisos.includes(permiso);
}

export function esSupervision(sesion: Sesion): boolean {
  return sesion.rol === "SUPERVISOR" || sesion.rol === "AUDITOR";
}
