"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import type { Usuario } from "@/lib/auth";
import { pantallasParaUsuario } from "@/lib/pantallas";
import { CrearCuenta } from "./CrearCuenta";
import { ModificarCuenta } from "./ModificarCuenta";
import { CanalesExternos } from "./CanalesExternos";
import type { Cuenta } from "@/lib/cuentas";

// Pestañas que viven en la portada; el resto son pantallas propias, enlazadas abajo.
type Tab = "inicio" | "crear-cuenta" | "modificar-cuenta";

const sinSuscripcion = () => () => {};
const fechaDeHoy = () =>
  new Date()
    .toLocaleDateString("es-PE", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
    .toUpperCase();

type Props = {
  usuario: Usuario;
  onSalir: () => void;
};

const pestanas: { id: Tab; label: string; icon: string }[] = [
  { id: "inicio", label: "Resumen", icon: "⌂" },
  { id: "crear-cuenta", label: "Crear cuenta", icon: "＋" },
  { id: "modificar-cuenta", label: "Modificar cuenta", icon: "✎" },
];

// Las pantallas reales del producto. La visibilidad sale del mapa central (lib/pantallas.ts)
// y de las acciones que COREDB entrega en /coredb/auth/me.

const iniciales = (nombre: string) => nombre.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

export function BancaPersonal({ usuario, onSalir }: Props) {
  const fechaHoy = useSyncExternalStore(sinSuscripcion, fechaDeHoy, () => "");
  const [tab, setTab] = useState<Tab>("inicio");
  const [notice, setNotice] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [cuentaParaModificar, setCuentaParaModificar] = useState<Cuenta | null>(null);
  const titulo = pestanas.find((item) => item.id === tab)?.label;
  const pantallas = pantallasParaUsuario(usuario);

  return (
    <main className="app-shell">
      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <a className="brand" href="#" onClick={(e) => { e.preventDefault(); setTab("inicio"); }}>
          <span className="brand-mark">B</span>
          <span><strong>BAN</strong><small>Banco Nacional de Arequipa</small></span>
        </a>
        <div className="side-caption">BANCA PERSONAL</div>
        <nav className="navigation" aria-label="Navegación principal">
          {pestanas.map((item) => (
            <button key={item.id} className={`nav-item ${tab === item.id ? "active" : ""}`} onClick={() => { setTab(item.id); setNotice(""); setCuentaParaModificar(null); setMobileMenu(false); }}>
              <span className="nav-icon">{item.icon}</span>{item.label}
            </button>
          ))}
          {pantallas.map((item) => (
            <Link key={item.href} className="nav-item" href={item.href}>
              <span className="nav-icon">{item.icon}</span>{item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <Link href="/" className="nav-item" onClick={() => setMobileMenu(false)}><span className="nav-icon">↩</span>Volver al portal</Link>
          <div className="profile"><div className="avatar">{iniciales(usuario.nombre)}</div><div className="profile-text"><strong>{usuario.nombre}</strong><span>{usuario.rol}</span></div></div>
          <button type="button" aria-label="Cerrar sesión" className="nav-item" onClick={onSalir} style={{ width: "100%", marginTop: 8 }}><span className="nav-icon">⎋</span>Cerrar sesión</button>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <button className="mobile-toggle" onClick={() => setMobileMenu(!mobileMenu)} aria-label="Abrir menú">☰</button>
          <div className="breadcrumb">Banca personal <span>/</span> <strong>{titulo}</strong></div>
          <div className="top-actions"><span className="secure"><span className="secure-dot" /> Conexión segura</span><div className="top-avatar">{iniciales(usuario.nombre)}</div></div>
        </header>

        <div className="content">
          <div className="welcome-row"><div><p className="eyebrow">{fechaHoy}</p><h1>{tab === "inicio" ? `¡Hola, ${usuario.nombre}!` : titulo}</h1><p className="subtitle">{tab === "inicio" ? "Elige la pantalla con la que quieres trabajar." : "Opera sobre el CORE del banco."}</p></div></div>

          {notice && <div className="notice" role="status"><span>ⓘ</span><p>{notice}</p><button onClick={() => setNotice("")} aria-label="Cerrar aviso">×</button></div>}

          {tab === "inicio" && <>
            <div className="section-heading"><div><h2>Pantallas del banco</h2><p>Cada una pide los permisos de tu rol ({usuario.rol}).</p></div></div>
            <div className="quick-grid">
              {pantallas.map((item) => (
                <Link key={item.href} href={item.href} className="quick-action">
                  <span className="quick-icon blue">{item.icon}</span>
                  <span><strong>{item.label}</strong><small>{item.descripcion}</small></span>
                  <b>→</b>
                </Link>
              ))}
            </div>
            <CanalesExternos />
          </>}

          {tab === "crear-cuenta" && <CrearCuenta onNotice={setNotice} onModificar={(cuenta) => { setCuentaParaModificar(cuenta); setTab("modificar-cuenta"); setNotice(""); }} />}

          {tab === "modificar-cuenta" && <ModificarCuenta cuentaInicial={cuentaParaModificar} onNotice={setNotice} />}

          <footer className="footer"><span>© 2026 Banco Nacional de Arequipa · Proyecto académico</span></footer>
        </div>
      </section>
    </main>
  );
}
