"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cerrarSesion } from "@/lib/auth";
import { rutaActual, urlLoginConVolver } from "@/lib/continuidad";
import { api, ErrorApi } from "@/lib/desembolso/api";
import { ProveedorSesion } from "@/lib/desembolso/sesion";
import type { Sesion } from "@/lib/desembolso/tipos";
import { Marco } from "./Marco";

/** Carga el perfil de Desembolso con la sesión de COREDB; sin sesión pide iniciarla. */
export function ConSesion({ children }: { children: React.ReactNode }) {
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [error, setError] = useState<ErrorApi | null>(null);

  useEffect(() => {
    api
      .get<Sesion>("sesion")
      .then((r) => setSesion(r.data))
      .catch((e: ErrorApi) => setError(e));
  }, []);

  if (error) {
    const sinSesion = error.estado === 401;
    return (
      <main className="mx-auto mt-24 max-w-md rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-slate-200">
        <p className="text-lg font-semibold text-slate-900">
          {sinSesion ? "Tu sesión no está iniciada o ya venció." : "No se pudo abrir Desembolso."}
        </p>
        {!sinSesion && <p className="mt-2 text-sm text-slate-600">{error.message}</p>}
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/" className="inline-flex rounded-lg px-4 py-2 text-sm font-semibold text-marca-700 ring-1 ring-marca-200 hover:bg-marca-50">Volver al portal</Link>
          <Link
            href={urlLoginConVolver(rutaActual())}
            onClick={cerrarSesion}
            className="inline-flex rounded-lg bg-marca-700 px-4 py-2 text-sm font-semibold text-white hover:bg-marca-800"
          >
            Iniciar sesión
          </Link>
        </div>
      </main>
    );
  }
  if (!sesion) {
    return <p className="mt-24 text-center text-sm text-slate-500">Cargando Desembolso…</p>;
  }
  return (
    <ProveedorSesion sesion={sesion}>
      <Marco>{children}</Marco>
    </ProveedorSesion>
  );
}
