 "use client";

import { useMemo, useState } from "react";

type Tab = "inicio" | "cuentas" | "transferencias" | "movimientos" | "tarjetas";

const initialMovements = [
  { id: "OP-20481", title: "Compra en Plaza Vea", detail: "Hoy · 10:42 a. m.", amount: -128.5, category: "Compra" },
  { id: "OP-20480", title: "Transferencia recibida", detail: "Ayer · 4:18 p. m.", amount: 850, category: "Transferencia" },
  { id: "OP-20479", title: "Pago de internet", detail: "18 oct. · 8:05 a. m.", amount: -89.9, category: "Servicios" },
  { id: "OP-20478", title: "Depósito en cuenta", detail: "17 oct. · 1:31 p. m.", amount: 1200, category: "Depósito" },
];

const money = (amount: number) =>
  new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(amount);

export default function Home() {
  const [tab, setTab] = useState<Tab>("inicio");
  const [showBalance, setShowBalance] = useState(true);
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState("");
  const [destination, setDestination] = useState("");
  const [amount, setAmount] = useState("");
  const [movements, setMovements] = useState(initialMovements);
  const [mobileMenu, setMobileMenu] = useState(false);

  const balance = 12480.75;
  const filteredMovements = useMemo(
    () => movements.filter((m) => `${m.title} ${m.id} ${m.category}`.toLowerCase().includes(search.toLowerCase())),
    [movements, search]
  );

  function submitTransfer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = Number(amount);
    if (!destination.trim() || !Number.isFinite(value) || value <= 0) {
      setNotice("Completa el número de cuenta y un monto válido.");
      return;
    }
    if (value > balance) {
      setNotice("El monto supera el saldo disponible de demostración.");
      return;
    }
    setMovements((current) => [
      { id: `DEMO-${Date.now().toString().slice(-5)}`, title: `Transferencia a ${destination}`, detail: "Ahora · Operación de demostración", amount: -value, category: "Transferencia" },
      ...current,
    ]);
    setNotice("Transferencia simulada correctamente. No se movió dinero real ni se llamó al backend.");
    setDestination("");
    setAmount("");
    setTab("movimientos");
  }

  const navItems: { id: Tab; label: string; icon: string }[] = [
    { id: "inicio", label: "Resumen", icon: "⌂" },
    { id: "cuentas", label: "Mis cuentas", icon: "▤" },
    { id: "transferencias", label: "Transferencias", icon: "⇄" },
    { id: "movimientos", label: "Movimientos", icon: "↕" },
    { id: "tarjetas", label: "Tarjetas", icon: "▰" },
  ];

  return (
    <main className="app-shell">
      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <a className="brand" href="#" onClick={(e) => { e.preventDefault(); setTab("inicio"); }}>
          <span className="brand-mark">B</span>
          <span><strong>BAN</strong><small>Banco Nacional de Arequipa</small></span>
        </a>
        <div className="side-caption">BANCA PERSONAL</div>
        <nav className="navigation" aria-label="Navegación principal">
          {navItems.map((item) => (
            <button key={item.id} className={`nav-item ${tab === item.id ? "active" : ""}`} onClick={() => { setTab(item.id); setNotice(""); setMobileMenu(false); }}>
              <span className="nav-icon">{item.icon}</span>{item.label}
              {item.id === "movimientos" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card"><span className="help-icon">?</span><strong>¿Necesitas ayuda?</strong><p>Estamos aquí para ayudarte con tus operaciones.</p><button onClick={() => setNotice("Centro de ayuda: esta vista es una demostración académica.")}>Ir al centro de ayuda <span>↗</span></button></div>
          <div className="profile"><div className="avatar">DV</div><div className="profile-text"><strong>Diego Vargas</strong><span>Cliente personal</span></div><button aria-label="Opciones de perfil" className="more-button" onClick={() => setNotice("Sesión de demostración activa.")}>•••</button></div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <button className="mobile-toggle" onClick={() => setMobileMenu(!mobileMenu)} aria-label="Abrir menú">☰</button>
          <div className="breadcrumb">Banca personal <span>/</span> <strong>{navItems.find((item) => item.id === tab)?.label}</strong></div>
          <div className="top-actions"><span className="secure"><span className="secure-dot" /> Conexión segura</span><button className="icon-button" aria-label="Notificaciones" onClick={() => setNotice("No tienes notificaciones nuevas.")}>♧<i /></button><div className="top-avatar">DV</div></div>
        </header>

        <div className="content">
          <div className="welcome-row"><div><p className="eyebrow">MIÉRCOLES, 21 DE OCTUBRE DE 2026</p><h1>{tab === "inicio" ? "¡Hola, Diego!" : navItems.find((item) => item.id === tab)?.label}</h1><p className="subtitle">{tab === "inicio" ? "Este es el resumen de tus finanzas de hoy." : "Administra tus productos bancarios de forma sencilla y segura."}</p></div><button className="outline-button" onClick={() => setNotice("Reporte de demostración: no hay datos reales conectados.")}><span>↧</span> Descargar reporte</button></div>

          {notice && <div className="notice" role="status"><span>ⓘ</span><p>{notice}</p><button onClick={() => setNotice("")} aria-label="Cerrar aviso">×</button></div>}

          {tab === "inicio" && <>
            <div className="summary-grid">
              <article className="balance-card"><div className="balance-top"><span className="card-label">SALDO TOTAL DISPONIBLE</span><span className="balance-symbol">↗</span></div><div className="balance-value">{showBalance ? money(balance) : "S/ ••••••"}</div><button className="visibility-button" onClick={() => setShowBalance(!showBalance)}>{showBalance ? "◉ Ocultar saldo" : "◎ Mostrar saldo"}</button><div className="balance-divider" /><div className="balance-footer"><span><i className="green-dot" /> Tus cuentas están activas</span><span>Actualizado ahora</span></div><div className="decor-circle circle-one" /><div className="decor-circle circle-two" /></article>
              <article className="mini-card"><div className="mini-card-head"><span className="mini-icon purple">▤</span><span className="trend positive">+2.4%</span></div><p className="mini-label">Ingresos del mes</p><strong>{money(4850)}</strong><div className="mini-foot"><span className="tiny-bars"><i/><i/><i/><i/><i/><i/><i/><i/></span><span>vs. mes anterior</span></div></article>
              <article className="mini-card"><div className="mini-card-head"><span className="mini-icon orange">↗</span><span className="trend neutral">Este mes</span></div><p className="mini-label">Gastos del mes</p><strong>{money(1720.4)}</strong><div className="mini-foot"><span className="expense-line"><i /></span><span>Control de gastos</span></div></article>
            </div>

            <div className="section-heading"><div><h2>Accesos rápidos</h2><p>¿Qué operación quieres realizar?</p></div></div>
            <div className="quick-grid">
              <button className="quick-action" onClick={() => { setTab("transferencias"); setNotice(""); }}><span className="quick-icon blue">⇄</span><span><strong>Transferir dinero</strong><small>Envía dinero a otra cuenta</small></span><b>→</b></button>
              <button className="quick-action" onClick={() => { setTab("cuentas"); setNotice(""); }}><span className="quick-icon green">＋</span><span><strong>Ver mis cuentas</strong><small>Consulta saldos y detalles</small></span><b>→</b></button>
              <button className="quick-action" onClick={() => { setTab("tarjetas"); setNotice(""); }}><span className="quick-icon violet">▰</span><span><strong>Mis tarjetas</strong><small>Revisa tus tarjetas</small></span><b>→</b></button>
            </div>

            <div className="section-heading movement-heading"><div><h2>Movimientos recientes</h2><p>Revisa la actividad de tus cuentas</p></div><button className="text-button" onClick={() => setTab("movimientos")}>Ver todos <span>→</span></button></div>
            <MovementTable movements={movements.slice(0, 4)} />
          </>}

          {tab === "cuentas" && <div className="product-grid"><article className="account-card"><div className="account-card-top"><span className="product-icon">▤</span><span className="status-pill"><i/> Activa</span></div><p className="mini-label">CUENTA DE AHORROS · PEN</p><h2>Cuenta principal</h2><p className="account-number">•••• •••• •••• 4821</p><div className="account-balance-label">Saldo disponible</div><div className="account-balance">{showBalance ? money(balance) : "S/ ••••••"}</div><div className="account-bottom"><span>Saldo contable <strong>{showBalance ? money(balance) : "••••••"}</strong></span><button onClick={() => setShowBalance(!showBalance)}>{showBalance ? "Ocultar" : "Mostrar"}</button></div></article><article className="add-account"><span className="add-circle">＋</span><h3>¿Necesitas otra cuenta?</h3><p>Solicita información sobre nuestros productos de ahorro.</p><button className="outline-button" onClick={() => setNotice("La apertura de cuentas estará disponible cuando se integre el backend.")}>Consultar productos</button></article></div>}

          {tab === "transferencias" && <div className="form-card"><div className="form-intro"><span className="form-icon">⇄</span><div><h2>Nueva transferencia</h2><p>Completa los datos para simular una operación entre cuentas.</p></div></div><div className="demo-warning">Modo demostración: esta operación solo modifica la lista local de movimientos. No se conecta al banco ni transfiere dinero real.</div><form className="transfer-form" onSubmit={submitTransfer}><label>Cuenta de origen</label><div className="select-like"><span className="account-small-icon">▤</span><span><strong>Cuenta principal</strong><small>•••• 4821 · Saldo: {money(balance)}</small></span><span className="select-arrow">⌄</span></div><label htmlFor="destination">Cuenta de destino</label><input id="destination" value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="Ingresa el número de cuenta" minLength={4} required/><label htmlFor="amount">Monto a transferir (PEN)</label><div className="amount-input"><span>S/</span><input id="amount" type="number" min="0.01" max={balance} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" required/></div><div className="transfer-summary"><span>Monto de la operación</span><strong>{money(Number(amount) || 0)}</strong><span>Comisión</span><strong>{money(0)}</strong></div><button className="primary-button" type="submit">Continuar transferencia <span>→</span></button></form></div>}

          {tab === "movimientos" && <div className="table-card"><div className="table-toolbar"><div><h2>Historial de movimientos</h2><p>Consulta las operaciones registradas en esta demostración.</p></div><div className="search-box"><span>⌕</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar movimiento..." aria-label="Buscar movimiento"/></div></div><MovementTable movements={filteredMovements}/></div>}

          {tab === "tarjetas" && <div className="product-grid"><article className="bank-card"><div className="bank-card-top"><span className="bank-card-brand">BNA<span>●</span></span><span className="chip">▦</span></div><p className="bank-card-type">VISA · DÉBITO</p><div className="bank-card-number">•••• &nbsp; •••• &nbsp; •••• &nbsp; 4821</div><div className="bank-card-bottom"><span><small>TITULAR</small><strong>DIEGO VARGAS</strong></span><span className="visa">VISA</span></div></article><article className="card-details"><div className="account-card-top"><h2>Tarjeta de débito</h2><span className="status-pill"><i/> Activa</span></div><p className="subtitle">Vinculada a tu cuenta principal.</p><div className="detail-row"><span>Tipo de tarjeta</span><strong>Débito</strong></div><div className="detail-row"><span>Número</span><strong>•••• 4821</strong></div><div className="detail-row"><span>Compras por internet</span><strong className="detail-green">Habilitadas</strong></div><button className="outline-button full-button" onClick={() => setNotice("El bloqueo de tarjeta requiere conexión con el backend.")}>Administrar tarjeta</button></article></div>}

          <footer className="footer"><span>© 2026 Banco Nacional de Arequipa · Proyecto académico</span><span><span className="footer-lock">♧</span> Tus datos merecen seguridad</span></footer>
        </div>
      </section>
    </main>
  );
}

function MovementTable({ movements }: { movements: { id: string; title: string; detail: string; amount: number; category: string }[] }) {
  if (!movements.length) return <div className="empty-state">No se encontraron movimientos con esa búsqueda.</div>;
  return <div className="movement-table"><div className="table-header"><span>DESCRIPCIÓN</span><span>FECHA</span><span>MONTO</span></div>{movements.map((movement) => <div className="movement-row" key={movement.id}><div className="movement-title"><span className={`movement-icon ${movement.amount > 0 ? "incoming" : "outgoing"}`}>{movement.amount > 0 ? "↙" : "↗"}</span><span><strong>{movement.title}</strong><small>{movement.id} · {movement.category}</small></span></div><span className="movement-date">{movement.detail}</span><strong className={`movement-amount ${movement.amount > 0 ? "positive-amount" : ""}`}>{movement.amount > 0 ? "+" : "−"}{new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(Math.abs(movement.amount))}</strong></div>)}</div>;
}
