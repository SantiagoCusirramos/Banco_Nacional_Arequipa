"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { cerrarSesion, obtenerToken, obtenerMiPerfil, type Usuario } from "@/lib/auth";
import { BancaPersonal } from "./components/BancaPersonal";

// Exige una sesión vigente en COREDB antes de mostrar la banca personal.
export default function Home() {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  useEffect(() => {
    if (!obtenerToken()) {
      router.replace("/login");
      return;
    }
    obtenerMiPerfil()
      .then(setUsuario)
      .catch(() => {
        cerrarSesion();
        router.replace("/login");
      });
  }, [router]);

  function salir() {
    cerrarSesion();
    router.replace("/login");
  }

  if (!usuario) {
    return <main className="auth-page"><div className="auth-loading">Cargando tu banca personal...</div></main>;
  }
  return <BancaPersonal usuario={usuario} onSalir={salir} />;
}
