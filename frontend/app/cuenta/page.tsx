"use client";

import { useState } from "react";

type CuentaInfo = {
  num_cuenta: string;
  cci: string;
  moneda: string;
  regimen: string;
  saldo_contable: number;
  saldo_disponible: number;
  saldo_retenido: number;
  fecha_apertura: string;
  estado_cuenta: string;
  id_agencia: string;
  id_producto_ahorro: string;
  titulares: { id_cliente: string; rol_titular: string }[];
};

type MovimientoInfo = {
  id_transaccion: string;
  uuid_transaccion: string;
  num_cuenta: string;
  num_cuenta_contraparte: string | null;
  tipo_operacion: string;
  tipo_movimiento: string;
  monto: number;
  moneda: string;
  id_canal: string;
  saldo_posterior: number;
  estado_transaccion: string;
  fecha_hora: string;
};

function cabeceraAuth(): Record<string, string> {
  try {
    const token = localStorage.getItem("bna_access_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

export default function CuentaPage() {
  const [tab, setTab] = useState<"apertura" | "consulta" | "operaciones" | "movimientos" | "detalleMovimiento">("apertura");
  const [numCuentaConsulta, setNumCuentaConsulta] = useState("");
  const [cuentaActual, setCuentaActual] = useState<CuentaInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(null);

  // Formulario de apertura
  const [idCliente, setIdCliente] = useState("CLI-001");
  const [idAgencia, setIdAgencia] = useState("AG1");
  const [regimen, setRegimen] = useState("INDIVIDUAL");
  const [cci, setCci] = useState("19100000000000000101");
  const [numCuentaNueva, setNumCuentaNueva] = useState("1010000001");

  // Formulario operaciones
  const [cuentaOrigen, setCuentaOrigen] = useState("");
  const [cuentaDestino, setCuentaDestino] = useState("");
  const [montoOp, setMontoOp] = useState("");
  const [tipoOp, setTipoOp] = useState<"deposito" | "retiro" | "transferencia">("deposito");

  // Movimientos
  const [cuentaMovs, setCuentaMovs] = useState("");
  const [movimientosList, setMovimientosList] = useState<MovimientoInfo[]>([]);
  const [uuidMovimiento, setUuidMovimiento] = useState("");
  const [movimientoDetalle, setMovimientoDetalle] = useState<MovimientoInfo | null>(null);

  async function consultarCuenta(e: React.FormEvent) {
    e.preventDefault();
    if (!numCuentaConsulta.trim()) return;
    setLoading(true);
    setNotice(null);
    try {
      const res = await fetch(`/api/cuenta/${numCuentaConsulta.trim()}`, { headers: cabeceraAuth() });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || (typeof json.detail === "string" ? json.detail : null) || "No se pudo consultar la cuenta.");
      }
      setCuentaActual(json.data || json);
    } catch (err: any) {
      setCuentaActual(null);
      setNotice({ text: err.message, error: true });
    } finally {
      setLoading(false);
    }
  }

  async function abrirCuenta(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setNotice(null);
    try {
      const payload = {
        num_cuenta: numCuentaNueva,
        cci,
        moneda: "PEN",
        regimen,
        id_agencia: idAgencia,
        titulares: [{ id_cliente: idCliente }],
      };
      const res = await fetch(`/api/cuenta/apertura`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...cabeceraAuth() },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || (typeof json.detail === "string" ? json.detail : null) || "No se pudo abrir la cuenta.");
      }
      const cta = json.data || json;
      setCuentaActual(cta);
      setNotice({ text: `Cuenta ${cta.num_cuenta || numCuentaNueva} abierta exitosamente en COREDB (8012).`, error: false });
      setTab("consulta");
      setNumCuentaConsulta(cta.num_cuenta || numCuentaNueva);
    } catch (err: any) {
      setNotice({ text: err.message, error: true });
    } finally {
      setLoading(false);
    }
  }

  async function ejecutarOperacion(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setNotice(null);
    try {
      let endpoint = tipoOp === "transferencia" ? "/transferencia" : `/${tipoOp}`;
      let body: any = {
        monto: Number(montoOp),
        moneda: "PEN",
        id_terminal: "ATM-01",
      };
      if (tipoOp === "transferencia") {
        body.num_cuenta_origen = cuentaOrigen;
        body.num_cuenta_destino = cuentaDestino;
      } else {
        body.num_cuenta = cuentaOrigen;
      }

      const res = await fetch(`/api/cuenta${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...cabeceraAuth(),
          "X-Idempotency-Key": crypto.randomUUID(),
          "X-Channel-ID": "AGE",
          "X-Request-Timestamp": new Date().toISOString(),
        },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || (typeof json.detail === "string" ? json.detail : null) || "No se pudo completar la operación.");
      }
      setNotice({ text: `Operación ${tipoOp} ejecutada correctamente en COREDB (8012). Transacción registrada.`, error: false });
    } catch (err: any) {
      setNotice({ text: err.message, error: true });
    } finally {
      setLoading(false);
    }
  }

  async function revisarMovimientos(e: React.FormEvent) {
    e.preventDefault();
    if (!cuentaMovs.trim()) return;
    setLoading(true);
    setNotice(null);
    try {
      const res = await fetch(`/api/cuenta/${cuentaMovs.trim()}/movimientos`, { headers: cabeceraAuth() });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || (typeof json.detail === "string" ? json.detail : null) || "No se pudieron obtener los movimientos.");
      }
      setMovimientosList(json.data || json || []);
    } catch (err: any) {
      setMovimientosList([]);
      setNotice({ text: err.message, error: true });
    } finally {
      setLoading(false);
    }
  }

  async function buscarMovimientoEspecifico(e: React.FormEvent) {
    e.preventDefault();
    if (!uuidMovimiento.trim()) return;
    setLoading(true);
    setNotice(null);
    try {
      const res = await fetch(`/api/cuenta/movimiento/${uuidMovimiento.trim()}`, { headers: cabeceraAuth() });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.message || (typeof json.detail === "string" ? json.detail : null) || "No se encontró el movimiento específico.");
      }
      setMovimientoDetalle(json.data || json);
    } catch (err: any) {
      setMovimientoDetalle(null);
      setNotice({ text: err.message, error: true });
    } finally {
      setLoading(false);
    }
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
          Módulo Cuentas <small>COREDB (Puerto 8012)</small>
        </div>
        <nav aria-label="Navegación Cuentas">
          <p>GESTIÓN DE CUENTAS</p>
          <button className={tab === "apertura" ? "active" : ""} onClick={() => setTab("apertura")}>
            1. Crear cuenta
          </button>
          <button className={tab === "consulta" ? "active" : ""} onClick={() => setTab("consulta")}>
            2. Ver cuenta específica
          </button>
          <button className={tab === "operaciones" ? "active" : ""} onClick={() => setTab("operaciones")}>
            3. Depositar / Transferir
          </button>
          <button className={tab === "movimientos" ? "active" : ""} onClick={() => setTab("movimientos")}>
            4. Revisar movimientos
          </button>
          <button className={tab === "detalleMovimiento" ? "active" : ""} onClick={() => setTab("detalleMovimiento")}>
            5. Ver movimiento específico
          </button>
        </nav>
        <div className="sol-sidebar-bottom">
          <div className="sol-lab">
            <div>
              <strong>COREDB Backend</strong>
              <small>Puerto 8012 · Procedimientos SQL</small>
            </div>
          </div>
        </div>
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div>
            <span>Cuentas</span>
            <b>/</b>Módulo de Ahorros y Operaciones (COREDB)
          </div>
          <div className="sol-topbar-right">
            <span className="sol-demo-pill">COREDB (8012)</span>
            <a href="/" style={{ color: "#15324f", fontWeight: 600, textDecoration: "none", fontSize: "13px" }}>Volver al Home Banking</a>
          </div>
        </header>

        <main className="sol-main">
          {notice && (
            <div role={notice.error ? "alert" : "status"} className={`sol-alert ${notice.error ? "error" : "success"}`}>
              {notice.text}
              <button onClick={() => setNotice(null)}>×</button>
            </div>
          )}

          {tab === "apertura" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Crear cuenta de ahorros</h2>
                  <p>Registra una nueva cuenta usando COREDB en el puerto 8012.</p>
                </div>
              </div>
              <form onSubmit={abrirCuenta} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label>Número de cuenta (10-20 dígitos)</label>
                  <input value={numCuentaNueva} onChange={(e) => setNumCuentaNueva(e.target.value)} required maxLength={20} />
                </div>
                <div className="sol-field">
                  <label>Código de Cuenta Interbancario (CCI - 20 dígitos)</label>
                  <input value={cci} onChange={(e) => setCci(e.target.value)} required minLength={20} maxLength={20} />
                </div>
                <div className="sol-field">
                  <label>ID del Cliente Titular</label>
                  <input value={idCliente} onChange={(e) => setIdCliente(e.target.value)} required />
                </div>
                <div className="sol-field">
                  <label>Agencia</label>
                  <input value={idAgencia} onChange={(e) => setIdAgencia(e.target.value)} required />
                </div>
                <div className="sol-field">
                  <label>Régimen</label>
                  <select value={regimen} onChange={(e) => setRegimen(e.target.value)}>
                    <option value="INDIVIDUAL">INDIVIDUAL</option>
                    <option value="MANCOMUNADA_INDISTINTA">MANCOMUNADA_INDISTINTA</option>
                    <option value="MANCOMUNADA_CONJUNTA">MANCOMUNADA_CONJUNTA</option>
                  </select>
                </div>
                <div style={{ gridColumn: "1 / -2", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Creando..." : "Crear cuenta en COREDB (8012)"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {tab === "consulta" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Ver una cuenta en específico</h2>
                  <p>Consulta los saldos y detalles de una cuenta ingresando su número.</p>
                </div>
              </div>
              <form onSubmit={consultarCuenta} className="sol-toolbar" style={{ marginTop: "20px" }}>
                <input
                  placeholder="Número de cuenta..."
                  value={numCuentaConsulta}
                  onChange={(e) => setNumCuentaConsulta(e.target.value)}
                  required
                />
                <button className="sol-button primary" type="submit" disabled={loading}>
                  {loading ? "Buscando..." : "Ver cuenta"}
                </button>
              </form>

              {cuentaActual && (
                <div style={{ marginTop: "30px", background: "#f8fafc", padding: "20px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <h3>Detalle de Cuenta: {cuentaActual.num_cuenta}</h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginTop: "15px" }}>
                    <div><small>CCI:</small> <strong>{cuentaActual.cci}</strong></div>
                    <div><small>Moneda:</small> <strong>{cuentaActual.moneda}</strong></div>
                    <div><small>Régimen:</small> <strong>{cuentaActual.regimen}</strong></div>
                    <div><small>Estado:</small> <strong style={{ color: "#0f766e" }}>{cuentaActual.estado_cuenta}</strong></div>
                    <div><small>Saldo Disponible:</small> <strong style={{ fontSize: "18px", color: "#15324f" }}>S/ {Number(cuentaActual.saldo_disponible || 0).toFixed(2)}</strong></div>
                    <div><small>Saldo Contable:</small> <strong>S/ {Number(cuentaActual.saldo_contable || 0).toFixed(2)}</strong></div>
                    <div><small>Agencia:</small> <strong>{cuentaActual.id_agencia}</strong></div>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === "operaciones" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Depositar y hacer transferencias</h2>
                  <p>Ejecuta operaciones transaccionales seguras conectadas a COREDB (8012).</p>
                </div>
              </div>
              <form onSubmit={ejecutarOperacion} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label>Tipo de Operación</label>
                  <select value={tipoOp} onChange={(e) => setTipoOp(e.target.value as any)}>
                    <option value="deposito">Depositar (Depósito)</option>
                    <option value="retiro">Retiro</option>
                    <option value="transferencia">Hacer Transferencia</option>
                  </select>
                </div>
                <div className="sol-field">
                  <label>{tipoOp === "transferencia" ? "Cuenta de Origen" : "Número de Cuenta"}</label>
                  <input value={cuentaOrigen} onChange={(e) => setCuentaOrigen(e.target.value)} required placeholder="Ej. 1010000001" />
                </div>
                {tipoOp === "transferencia" && (
                  <div className="sol-field">
                    <label>Cuenta de Destino</label>
                    <input value={cuentaDestino} onChange={(e) => setCuentaDestino(e.target.value)} required placeholder="Ej. 1010000002" />
                  </div>
                )}
                <div className="sol-field">
                  <label>Monto</label>
                  <input type="number" step="0.01" min="0.01" value={montoOp} onChange={(e) => setMontoOp(e.target.value)} required placeholder="0.00" />
                </div>
                <div style={{ gridColumn: "1 / -1", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Procesando..." : `Ejecutar ${tipoOp.toUpperCase()}`}
                  </button>
                </div>
              </form>
            </div>
          )}

          {tab === "movimientos" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Revisar movimientos</h2>
                  <p>Consulta el historial de transacciones de una cuenta específica.</p>
                </div>
              </div>
              <form onSubmit={revisarMovimientos} className="sol-toolbar" style={{ marginTop: "20px" }}>
                <input
                  placeholder="Número de cuenta para revisar movimientos..."
                  value={cuentaMovs}
                  onChange={(e) => setCuentaMovs(e.target.value)}
                  required
                />
                <button className="sol-button primary" type="submit" disabled={loading}>
                  {loading ? "Cargando..." : "Revisar movimientos"}
                </button>
              </form>

              {movimientosList.length > 0 && (
                <div className="sol-tablewrap" style={{ marginTop: "20px" }}>
                  <table>
                    <thead>
                      <tr>
                        <th>UUID Transacción</th>
                        <th>Tipo</th>
                        <th>Mov.</th>
                        <th className="num">Monto</th>
                        <th className="num">Saldo Post.</th>
                        <th>Fecha</th>
                      </tr>
                    </thead>
                    <tbody>
                      {movimientosList.map((m) => (
                        <tr key={m.uuid_transaccion}>
                          <td style={{ fontFamily: "monospace", fontSize: "11px" }}>{m.uuid_transaccion}</td>
                          <td>{m.tipo_operacion}</td>
                          <td>{m.tipo_movimiento}</td>
                          <td className="num">S/ {Number(m.monto).toFixed(2)}</td>
                          <td className="num">S/ {Number(m.saldo_posterior).toFixed(2)}</td>
                          <td>{new Date(m.fecha_hora).toLocaleString("es-PE")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {tab === "detalleMovimiento" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Ver un movimiento en específico</h2>
                  <p>Consulta la información detallada de una transacción ingresando su UUID único.</p>
                </div>
              </div>
              <form onSubmit={buscarMovimientoEspecifico} className="sol-toolbar" style={{ marginTop: "20px" }}>
                <input
                  placeholder="UUID de la transacción (ej. 123e4567-e89b...)"
                  value={uuidMovimiento}
                  onChange={(e) => setUuidMovimiento(e.target.value)}
                  required
                />
                <button className="sol-button primary" type="submit" disabled={loading}>
                  {loading ? "Buscando..." : "Ver movimiento"}
                </button>
              </form>

              {movimientoDetalle && (
                <div style={{ marginTop: "30px", background: "#f8fafc", padding: "20px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <h3>Detalle del Movimiento: {movimientoDetalle.uuid_transaccion}</h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginTop: "15px" }}>
                    <div><small>Cuenta:</small> <strong>{movimientoDetalle.num_cuenta}</strong></div>
                    <div><small>Contraparte:</small> <strong>{movimientoDetalle.num_cuenta_contraparte || "N/A"}</strong></div>
                    <div><small>Tipo Operación:</small> <strong>{movimientoDetalle.tipo_operacion}</strong></div>
                    <div><small>Tipo Movimiento (D/C):</small> <strong>{movimientoDetalle.tipo_movimiento}</strong></div>
                    <div><small>Monto:</small> <strong style={{ color: "#15324f" }}>S/ {Number(movimientoDetalle.monto).toFixed(2)}</strong></div>
                    <div><small>Saldo Posterior:</small> <strong>S/ {Number(movimientoDetalle.saldo_posterior).toFixed(2)}</strong></div>
                    <div><small>Canal:</small> <strong>{movimientoDetalle.id_canal}</strong></div>
                    <div><small>Estado:</small> <strong>{movimientoDetalle.estado_transaccion}</strong></div>
                    <div><small>Fecha/Hora:</small> <strong>{new Date(movimientoDetalle.fecha_hora).toLocaleString("es-PE")}</strong></div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
