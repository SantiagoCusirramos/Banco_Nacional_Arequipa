"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cerrarSesion } from "@/lib/auth";
import { PERFIL } from "@/lib/desembolso/formato";
import { useSesion } from "@/lib/desembolso/sesion";

export function Marco({ children }: { children: React.ReactNode }) {
  const sesion = useSesion();
  const ruta = usePathname();
  const router = useRouter();
  const enlaces = [
    { href: "/desembolso", texto: "Desembolsar" },
    { href: "/desembolso/ordenes", texto: "Órdenes" },
    ...(sesion.puedeConciliar ? [{ href: "/desembolso/conciliacion", texto: "Conciliación" }] : []),
  ];

  function salir() {
    cerrarSesion();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen">
      <header className="no-imprimir bg-marca-800 text-white shadow">
        <div className="mx-auto flex max-w-7xl items-center gap-8 px-6 py-3">
          <Link href="/desembolso" className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-white text-sm font-black text-marca-800">BNA</span>
            <span className="leading-tight">
              <span className="block text-sm font-semibold">Banco Nacional de Arequipa</span>
              <span className="block text-xs text-marca-100">Desembolso de Créditos · Módulo 13</span>
            </span>
          </Link>
          <nav className="flex flex-1 gap-1" aria-label="Navegación Desembolso">
            {enlaces.map((e) => {
              const activo = e.href === "/desembolso" ? ruta === e.href : ruta === e.href || ruta.startsWith(`${e.href}/`);
              return (
                <Link
                  key={e.href}
                  href={e.href}
                  className={`rounded-md px-3 py-2 text-sm font-medium transition ${
                    activo ? "bg-white/15 text-white" : "text-marca-100 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {e.texto}
                </Link>
              );
            })}
          </nav>
          <div className="text-right leading-tight">
            <p className="text-sm font-semibold">{sesion.usuario}</p>
            <p className="text-xs text-marca-100">{PERFIL[sesion.perfil] ?? sesion.perfil}</p>
          </div>
          <button
            onClick={salir}
            className="rounded-md px-3 py-2 text-sm text-marca-100 ring-1 ring-white/20 hover:bg-white/10 hover:text-white"
          >
            Salir
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
    </div>
  );
}
