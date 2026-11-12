"use client";

import { useState } from "react";
import Link from "next/link";
import {
  BINES, ESTADOS_PEDIBLES, cambiarEstado, emitirTarjeta, mensajeDeError, tarjetasDeCliente, verTarjeta,
  type EstadoPedible, type Tarjeta,
} from "@/lib/tarjetas";

type Pestana = "cliente" | "consulta" | "emision" | "estado";
type Aviso = { text: string; error: boolean };

const enCuatroAnios = () => {
  const fecha = new Date();
  fecha.setFullYear(fecha.getFullYear() + 4);
  return fecha.toISOString().slice(0, 10);
};

function IconoCerrar() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  );
}

function DetalleTarjeta({ tarjeta }: { tarjeta: Tarjeta }) {
  return (
    <div style={{ marginTop: "30px", background: "#f8fafc", padding: "20px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
      <h3>Tarjeta {tarjeta.numero_enmascarado}</h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginTop: "15px" }}>
        <div><small>Identificador:</small> <strong style={{ fontFamily: "monospace", fontSize: "12px" }}>{tarjeta.id_tarjeta}</strong></div>
        <div><small>Cliente:</small> <strong>{tarjeta.cod_cliente}</strong></div>
        <div><small>Estado:</small> <strong style={{ color: "#0f766e" }}>{tarjeta.estado_tarjeta}</strong></div>
        <div><small>Vencimiento:</small> <strong>{tarjeta.vencimiento_mm_aa}</strong></div>
        <div><small>Emisión:</small> <strong>{tarjeta.fecha_emision}</strong></div>
        <div><small>BIN:</small> <strong>{tarjeta.bin}</strong></div>
      </div>
    </div>
  );
}

export default function TarjetasPage() {
  const [tab, setTab] = useState<Pestana>("cliente");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<Aviso | null>(null);

  // Tarjetas de un cliente
  const [codCliente, setCodCliente] = useState("");
  const [tarjetas, setTarjetas] = useState<Tarjeta[] | null>(null);

  // Una tarjeta
  const [idConsulta, setIdConsulta] = useState("");
  const [tarjetaActual, setTarjetaActual] = useState<Tarjeta | null>(null);

  // Emisión
  const [clienteEmision, setClienteEmision] = useState("");
  const [cuentaEmision, setCuentaEmision] = useState("");
  const [bin, setBin] = useState(BINES[0]);
  const [vencimiento, setVencimiento] = useState(enCuatroAnios);

  // Cambio de estado
  const [idEstado, setIdEstado] = useState("");
  const [estado, setEstado] = useState<EstadoPedible>("BLOQUEADA");
  const [motivo, setMotivo] = useState("");

  // Ejecuta una llamada mostrando el avance y, si falla, el mensaje del servicio.
  async function ejecutar(accion: () => Promise<void>, alFallar?: () => void) {
    setLoading(true);
    setNotice(null);
    try {
      await accion();
    } catch (err) {
      alFallar?.();
      setNotice({ text: mensajeDeError(err), error: true });
    } finally {
      setLoading(false);
    }
  }

  function mostrar(tarjeta: Tarjeta) {
    setTarjetaActual(tarjeta);
    setIdConsulta(tarjeta.id_tarjeta);
    setTab("consulta");
  }

  function prepararCambio(tarjeta: Tarjeta) {
    setIdEstado(tarjeta.id_tarjeta);
    setTab("estado");
  }

  function buscarDeCliente(e: React.FormEvent) {
    e.preventDefault();
    const codigo = codCliente.trim().toUpperCase();
    if (!codigo) return;
    void ejecutar(async () => setTarjetas(await tarjetasDeCliente(codigo)), () => setTarjetas(null));
  }

  function consultar(e: React.FormEvent) {
    e.preventDefault();
    const id = idConsulta.trim();
    if (!id) return;
    void ejecutar(async () => setTarjetaActual(await verTarjeta(id)), () => setTarjetaActual(null));
  }

  function emitir(e: React.FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const tarjeta = await emitirTarjeta({
        cod_cliente: clienteEmision.trim().toUpperCase(),
        num_cuenta: cuentaEmision.trim(),
        bin,
        fecha_vencimiento: vencimiento,
      });
      setNotice({ text: `Tarjeta ${tarjeta.numero_enmascarado} emitida (${tarjeta.estado_tarjeta}).`, error: false });
      mostrar(tarjeta);
    });
  }

  function cambiar(e: React.FormEvent) {
    e.preventDefault();
    const id = idEstado.trim();
    if (!id) return;
    void ejecutar(async () => {
      const tarjeta = await cambiarEstado(id, estado, motivo.trim());
      setNotice({ text: `La tarjeta ${tarjeta.numero_enmascarado} quedó ${tarjeta.estado_tarjeta}.`, error: false });
      setMotivo("");
      mostrar(tarjeta);
    });
  }

  return (
    <div className="sol-shell">
      <aside className="sol-sidebar">
        <div className="sol-brand light">
          <div>
            <strong>BNA<span>®</span></strong>
            <small>Banco Nacional de Arequipa</small>
          </div>
        </div>
        <div className="sol-workspace">
          <span className="sol-workspace-dot" />
          Módulo Tarjetas <small>sobre el CORE</small>
        </div>
        <nav aria-label="Navegación Tarjetas">
          <p>GESTIÓN DE TARJETAS</p>
          <button className={tab === "cliente" ? "active" : ""} onClick={() => setTab("cliente")}>
            1. Tarjetas de un cliente
          </button>
          <button className={tab === "consulta" ? "active" : ""} onClick={() => setTab("consulta")}>
            2. Ver tarjeta específica
          </button>
          <button className={tab === "emision" ? "active" : ""} onClick={() => setTab("emision")}>
            3. Emitir tarjeta
          </button>
          <button className={tab === "estado" ? "active" : ""} onClick={() => setTab("estado")}>
            4. Bloquear o cambiar estado
          </button>
        </nav>
        <div className="sol-sidebar-bottom">
          <div className="sol-lab">
            <div>
              <strong>TARJETAS</strong>
              <small>Sobre la API del CORE</small>
            </div>
          </div>
        </div>
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div>
            <span>Tarjetas</span>
            <b>/</b>Módulo de Tarjetas de Débito
          </div>
          <div className="sol-topbar-right">
            <span className="sol-demo-pill">Requiere sesión iniciada</span>
            <Link href="/" style={{ color: "#15324f", fontWeight: 600, textDecoration: "none", fontSize: "13px" }}>Volver al Home Banking</Link>
          </div>
        </header>

        <main className="sol-main">
          {notice && (
            <div role={notice.error ? "alert" : "status"} className={`sol-alert ${notice.error ? "error" : "success"}`}>
              {notice.text}
              <button onClick={() => setNotice(null)} aria-label="Cerrar aviso"><IconoCerrar /></button>
            </div>
          )}

          {tab === "cliente" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Tarjetas de un cliente</h2>
                  <p>Lista las tarjetas emitidas a un cliente, de la más reciente a la más antigua.</p>
                </div>
              </div>
              <form onSubmit={buscarDeCliente} className="sol-toolbar" style={{ marginTop: "20px" }}>
                <input
                  aria-label="Código del cliente"
                  placeholder="Código del cliente, por ejemplo CLI000000001"
                  value={codCliente}
                  onChange={(e) => setCodCliente(e.target.value)}
                  maxLength={12}
                  required
                />
                <button className="sol-button primary" type="submit" disabled={loading}>
                  {loading ? "Buscando..." : "Ver tarjetas"}
                </button>
              </form>

              {tarjetas && tarjetas.length === 0 && (
                <p role="status" style={{ marginTop: "20px" }}>El cliente no tiene tarjetas.</p>
              )}
              {tarjetas && tarjetas.length > 0 && (
                <div className="sol-tablewrap" style={{ marginTop: "20px" }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Tarjeta</th>
                        <th>Estado</th>
                        <th>Vence</th>
                        <th>Emisión</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tarjetas.map((t) => (
                        <tr key={t.id_tarjeta}>
                          <td style={{ fontFamily: "monospace" }}>{t.numero_enmascarado}</td>
                          <td>{t.estado_tarjeta}</td>
                          <td>{t.vencimiento_mm_aa}</td>
                          <td>{t.fecha_emision}</td>
                          <td style={{ display: "flex", gap: "8px" }}>
                            <button className="sol-button" type="button" onClick={() => mostrar(t)}>Ver</button>
                            <button className="sol-button" type="button" onClick={() => prepararCambio(t)}>Cambiar estado</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {tab === "consulta" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Ver una tarjeta en específico</h2>
                  <p>Consulta el estado y las fechas de una tarjeta por su identificador.</p>
                </div>
              </div>
              <form onSubmit={consultar} className="sol-toolbar" style={{ marginTop: "20px" }}>
                <input
                  aria-label="Identificador de la tarjeta"
                  placeholder="Identificador de la tarjeta (UUID)"
                  value={idConsulta}
                  onChange={(e) => setIdConsulta(e.target.value)}
                  required
                />
                <button className="sol-button primary" type="submit" disabled={loading}>
                  {loading ? "Buscando..." : "Ver tarjeta"}
                </button>
              </form>
              {tarjetaActual && <DetalleTarjeta tarjeta={tarjetaActual} />}
            </div>
          )}

          {tab === "emision" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Emitir tarjeta de débito</h2>
                  <p>La tarjeta queda pendiente de activación y vinculada a una cuenta del cliente.</p>
                </div>
              </div>
              <form onSubmit={emitir} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label htmlFor="emision-cliente">Código del cliente</label>
                  <input id="emision-cliente" value={clienteEmision} onChange={(e) => setClienteEmision(e.target.value)} required maxLength={12} />
                </div>
                <div className="sol-field">
                  <label htmlFor="emision-cuenta">Cuenta a vincular</label>
                  <input id="emision-cuenta" value={cuentaEmision} onChange={(e) => setCuentaEmision(e.target.value)} required maxLength={20} placeholder="Una cuenta en la que el cliente es titular" />
                </div>
                <div className="sol-field">
                  <label htmlFor="emision-bin">BIN</label>
                  <select id="emision-bin" value={bin} onChange={(e) => setBin(e.target.value)}>
                    {BINES.map((opcion) => <option key={opcion} value={opcion}>{opcion}</option>)}
                  </select>
                </div>
                <div className="sol-field">
                  <label htmlFor="emision-vencimiento">Fecha de vencimiento</label>
                  <input id="emision-vencimiento" type="date" value={vencimiento} onChange={(e) => setVencimiento(e.target.value)} required />
                </div>
                <div style={{ gridColumn: "1 / -1", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Emitiendo..." : "Emitir tarjeta"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {tab === "estado" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Bloquear o cambiar el estado</h2>
                  <p>Cada cambio queda en el historial de la tarjeta. El desbloqueo lo hace Seguridad.</p>
                </div>
              </div>
              <form onSubmit={cambiar} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label htmlFor="estado-id">Identificador de la tarjeta</label>
                  <input id="estado-id" value={idEstado} onChange={(e) => setIdEstado(e.target.value)} required />
                </div>
                <div className="sol-field">
                  <label htmlFor="estado-nuevo">Nuevo estado</label>
                  <select id="estado-nuevo" value={estado} onChange={(e) => setEstado(e.target.value as EstadoPedible)}>
                    {ESTADOS_PEDIBLES.map((opcion) => <option key={opcion} value={opcion}>{opcion}</option>)}
                  </select>
                </div>
                <div className="sol-field" style={{ gridColumn: "1 / -1" }}>
                  <label htmlFor="estado-motivo">Motivo</label>
                  <input id="estado-motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={255} placeholder="Por ejemplo: robo reportado por el cliente" />
                </div>
                <div style={{ gridColumn: "1 / -1", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Aplicando..." : "Aplicar cambio"}
                  </button>
                </div>
              </form>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
