"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import type { Usuario } from "@/lib/auth";
import { CrearCuenta } from "./CrearCuenta";
import { ModificarCuenta } from "./ModificarCuenta";
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

// Las pantallas reales del producto. Cada una exige la sesión y comprueba los permisos del rol.
export const PANTALLAS: { href: string; label: string; icon: string; descripcion: string }[] = [
  { href: "/cuenta", label: "Cuentas", icon: "▤", descripcion: "Abrir y consultar cuentas, depósitos, retiros, transferencias y movimientos" },
  { href: "/tarjetas", label: "Tarjetas", icon: "▭", descripcion: "Emitir, activar, bloquear tarjetas y autorizar débitos" },
  { href: "/tarjetas/desbloqueo", label: "Desbloqueo de tarjetas", icon: "🔓", descripcion: "Operadores y administradores: desbloquear una tarjeta tras verificar al titular" },
  { href: "/billetera", label: "Billetera Chaski", icon: "◎", descripcion: "Afiliar clientes y comercios a la billetera digital" },
  { href: "/captacion", label: "Captación", icon: "📋", descripcion: "Registrar solicitantes y habilitarlos como clientes" },
  { href: "/solicitud-credito", label: "Solicitud de crédito", icon: "📝", descripcion: "El asesor arma y envía la solicitud (SOL)" },
  { href: "/evaluacion", label: "Evaluación", icon: "⚖", descripcion: "El analista evalúa y decide las solicitudes" },
  { href: "/desembolso", label: "Desembolso", icon: "⇣", descripcion: "Órdenes de desembolso, confirmación y conciliación" },
  { href: "/pagar-cuota", label: "Pagar cuota", icon: "⎘", descripcion: "Pago de cuotas de un crédito (Cobranza, CR-INT-08)" },
  { href: "/homebanking/index.html", label: "Home Banking", icon: "⌂", descripcion: "Prototipo de Home Banking sobre las mismas rutas" },
];

// Solo para quien puede crear usuarios (administradores): la gestión del personal.
const USUARIOS = { href: "/usuarios", label: "Usuarios", icon: "👤", descripcion: "Altas del personal, roles y contraseñas" };

const iniciales = (nombre: string) => nombre.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

export function BancaPersonal({ usuario, onSalir }: Props) {
  const fechaHoy = useSyncExternalStore(sinSuscripcion, fechaDeHoy, () => "");
  const [tab, setTab] = useState<Tab>("inicio");
  const [notice, setNotice] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [cuentaParaModificar, setCuentaParaModificar] = useState<Cuenta | null>(null);
  const titulo = pestanas.find((item) => item.id === tab)?.label;
  const pantallas = usuario.acciones?.includes("CREAR_USUARIO") ? [...PANTALLAS, USUARIOS] : PANTALLAS;

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
          <div className="profile"><div className="avatar">{iniciales(usuario.nombre)}</div><div className="profile-text"><strong>{usuario.nombre}</strong><span>{usuario.rol}</span></div><button aria-label="Cerrar sesión" title="Cerrar sesión" className="more-button" onClick={onSalir}>↪</button></div>
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
          </>}

          {tab === "crear-cuenta" && <CrearCuenta onNotice={setNotice} onModificar={(cuenta) => { setCuentaParaModificar(cuenta); setTab("modificar-cuenta"); setNotice(""); }} />}

          {tab === "modificar-cuenta" && <ModificarCuenta cuentaInicial={cuentaParaModificar} onNotice={setNotice} />}

          <footer className="footer"><span>© 2026 Banco Nacional de Arequipa · Proyecto académico</span></footer>
        </div>
      </section>
    </main>
  );
}
