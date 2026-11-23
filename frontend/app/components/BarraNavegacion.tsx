"use client";

import Link from "next/link";
import { cerrarSesion } from "@/lib/auth";

type Props = {
  titulo: string;
  subtitulo?: string;
  usuario?: { nombre: string; rol?: string } | null;
};

export function BarraNavegacion({ titulo, subtitulo, usuario }: Props) {
  return (
    <header className="topbar" style={{ gap: 12 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <div className="breadcrumb">Banca personal <span>/</span> <strong>{titulo}</strong></div>
        {subtitulo ? <small style={{ color: "#64748b" }}>{subtitulo}</small> : null}
      </div>
      <div className="top-actions" style={{ gap: 10 }}>
        <Link href="/" className="sol-btn sol-btn-ghost" style={{ textDecoration: "none" }}>Volver al portal</Link>
        {usuario ? <span className="secure"><span className="secure-dot" /> {usuario.nombre}{usuario.rol ? ` · ${usuario.rol}` : ""}</span> : null}
        <Link href="/login" className="sol-btn sol-btn-ghost" style={{ textDecoration: "none" }}
          aria-label="Cerrar sesión" onClick={() => void cerrarSesion()}>Cerrar sesión</Link>
      </div>
    </header>
  );
}
