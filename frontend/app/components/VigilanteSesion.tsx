"use client";

import { useEffect } from "react";
import { CLAVE_CIERRE } from "@/lib/auth";

/**
 * En cada pantalla del portal: si otra pestaña cierra la sesión (o borra el token), esta va al
 * login; y si el navegador muestra con «Atrás» una página guardada en memoria, la recarga para
 * que la pantalla vuelva a comprobar la sesión en vez de mostrar datos de una sesión cerrada.
 */
export default function VigilanteSesion() {
  useEffect(() => {
    const enLogin = () => window.location.pathname.startsWith("/login");
    const alCambiar = (e: StorageEvent) => {
      const cerro = e.key === CLAVE_CIERRE || (e.key === "bna_access_token" && e.newValue === null) || e.key === null;
      if (cerro && !enLogin()) window.location.replace("/login");
    };
    const alMostrar = (e: PageTransitionEvent) => {
      if (e.persisted) window.location.reload();
    };
    window.addEventListener("storage", alCambiar);
    window.addEventListener("pageshow", alMostrar);
    return () => {
      window.removeEventListener("storage", alCambiar);
      window.removeEventListener("pageshow", alMostrar);
    };
  }, []);
  return null;
}
