"use client";

import { useState } from "react";
import Link from "next/link";
import {
  abrirCuenta, depositar, formatoMoneda, mensajeDeError, movimientosDeCuenta, retirar, transferir,
  verCuenta, verMovimiento, REGIMENES, type Cuenta, type Movimiento, type Regimen,
} from "@/lib/cuentas";

type Pestana = "apertura" | "consulta" | "operaciones" | "movimientos" | "detalleMovimiento";
type Operacion = "deposito" | "retiro" | "transferencia";
type Aviso = { text: string; error: boolean };

export default function CuentaPage() {
  const [tab, setTab] = useState<Pestana>("apertura");
  const [numCuentaConsulta, setNumCuentaConsulta] = useState("");
  const [cuentaActual, setCuentaActual] = useState<Cuenta | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<Aviso | null>(null);

  // Formulario de apertura
  const [idCliente, setIdCliente] = useState("");
  const [idAgencia, setIdAgencia] = useState("");
  const [regimen, setRegimen] = useState<Regimen>("INDIVIDUAL");
  const [cci, setCci] = useState("");
  const [numCuentaNueva, setNumCuentaNueva] = useState("");

  // Formulario operaciones
  const [cuentaOrigen, setCuentaOrigen] = useState("");
  const [cuentaDestino, setCuentaDestino] = useState("");
  const [montoOp, setMontoOp] = useState("");
  const [tipoOp, setTipoOp] = useState<Operacion>("deposito");

  // Movimientos
  const [cuentaMovs, setCuentaMovs] = useState("");
  const [movimientosList, setMovimientosList] = useState<Movimiento[] | null>(null);
  const [uuidMovimiento, setUuidMovimiento] = useState("");
  const [movimientoDetalle, setMovimientoDetalle] = useState<Movimiento | null>(null);

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

  function consultarCuenta(e: React.FormEvent) {
    e.preventDefault();
    const numero = numCuentaConsulta.trim();
    if (!numero) return;
    void ejecutar(async () => setCuentaActual(await verCuenta(numero)), () => setCuentaActual(null));
  }

  function abrir(e: React.FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const cuenta = await abrirCuenta({
        num_cuenta: numCuentaNueva.trim(),
        cci: cci.trim(),
        moneda: "PEN",
        regimen,
        id_agencia: idAgencia.trim(),
        titulares: idCliente.split(",").map((codigo) => codigo.trim().toUpperCase()).filter(Boolean),
      });
      setCuentaActual(cuenta);
      setNotice({ text: `Cuenta ${cuenta.num_cuenta} abierta.`, error: false });
      setTab("consulta");
      setNumCuentaConsulta(cuenta.num_cuenta);
    });
  }

  function ejecutarOperacion(e: React.FormEvent) {
    e.preventDefault();
    const monto = Number(montoOp).toFixed(2);
    void ejecutar(async () => {
      if (tipoOp === "transferencia") {
        const resultado = await transferir(cuentaOrigen.trim(), cuentaDestino.trim(), monto);
        setNotice({ text: `Transferencia registrada. Débito ${resultado.uuid_debito}, abono ${resultado.uuid_abono}.`, error: false });
      } else {
        const operar = tipoOp === "deposito" ? depositar : retirar;
        const resultado = await operar(cuentaOrigen.trim(), monto);
        setNotice({ text: `Operación registrada: ${resultado.uuid_transaccion}.`, error: false });
      }
    });
  }

  function revisarMovimientos(e: React.FormEvent) {
    e.preventDefault();
    const numero = cuentaMovs.trim();
    if (!numero) return;
    void ejecutar(async () => setMovimientosList(await movimientosDeCuenta(numero)), () => setMovimientosList(null));
  }

  function buscarMovimientoEspecifico(e: React.FormEvent) {
    e.preventDefault();
    const uuid = uuidMovimiento.trim();
    if (!uuid) return;
    void ejecutar(async () => setMovimientoDetalle(await verMovimiento(uuid)), () => setMovimientoDetalle(null));
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
          Módulo Cuentas <small>sobre el CORE</small>
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
              <strong>CUENTAS</strong>
              <small>Sobre la API del CORE</small>
            </div>
          </div>
        </div>
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div>
            <span>Cuentas</span>
            <b>/</b>Módulo de Ahorros y Operaciones
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
              <button onClick={() => setNotice(null)}>×</button>
            </div>
          )}

          {tab === "apertura" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Crear cuenta de ahorros</h2>
                  <p>Registra una nueva cuenta de ahorros en soles.</p>
                </div>
              </div>
              <form onSubmit={abrir} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label htmlFor="apertura-num">Número de cuenta (hasta 20 caracteres)</label>
                  <input id="apertura-num" value={numCuentaNueva} onChange={(e) => setNumCuentaNueva(e.target.value)} required maxLength={20} placeholder="Ej. 10100000000001" />
                </div>
                <div className="sol-field">
                  <label htmlFor="apertura-cci">Código de Cuenta Interbancario (CCI - 20 dígitos)</label>
                  <input id="apertura-cci" value={cci} onChange={(e) => setCci(e.target.value)} required minLength={20} maxLength={20} placeholder="20 dígitos" />
                </div>
                <div className="sol-field">
                  <label htmlFor="apertura-cliente">Código del cliente titular</label>
                  <input id="apertura-cliente" value={idCliente} onChange={(e) => setIdCliente(e.target.value)} required placeholder="CLI000000001 (varios separados por coma si es mancomunada)" />
                </div>
                <div className="sol-field">
                  <label htmlFor="apertura-agencia">Agencia</label>
                  <input id="apertura-agencia" value={idAgencia} onChange={(e) => setIdAgencia(e.target.value)} required maxLength={10} placeholder="Código de la agencia, por ejemplo AQP01" />
                </div>
                <div className="sol-field">
                  <label htmlFor="apertura-regimen">Régimen</label>
                  <select id="apertura-regimen" value={regimen} onChange={(e) => setRegimen(e.target.value as Regimen)}>
                    {REGIMENES.map((opcion) => <option key={opcion} value={opcion}>{opcion}</option>)}
                  </select>
                </div>
                <div style={{ gridColumn: "1 / -2", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Creando..." : "Crear cuenta"}
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
                    <div><small>Saldo Disponible:</small> <strong style={{ fontSize: "18px", color: "#15324f" }}>{formatoMoneda(cuentaActual.saldo_disponible, cuentaActual.moneda)}</strong></div>
                    <div><small>Saldo Contable:</small> <strong>{formatoMoneda(cuentaActual.saldo_contable, cuentaActual.moneda)}</strong></div>
                    <div><small>Agencia:</small> <strong>{cuentaActual.id_agencia}</strong></div>
                    <div><small>Titulares:</small> <strong>{cuentaActual.titulares.join(", ")}</strong></div>
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
                  <p>Registra depósitos, retiros y transferencias entre cuentas de la misma moneda.</p>
                </div>
              </div>
              <form onSubmit={ejecutarOperacion} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label htmlFor="operacion-tipo">Tipo de Operación</label>
                  <select id="operacion-tipo" value={tipoOp} onChange={(e) => setTipoOp(e.target.value as Operacion)}>
                    <option value="deposito">Depositar (Depósito)</option>
                    <option value="retiro">Retiro</option>
                    <option value="transferencia">Hacer Transferencia</option>
                  </select>
                </div>
                <div className="sol-field">
                  <label htmlFor="operacion-cuenta">{tipoOp === "transferencia" ? "Cuenta de Origen" : "Número de Cuenta"}</label>
                  <input id="operacion-cuenta" value={cuentaOrigen} onChange={(e) => setCuentaOrigen(e.target.value)} required placeholder="Ej. 1010000001" />
                </div>
                {tipoOp === "transferencia" && (
                  <div className="sol-field">
                    <label htmlFor="operacion-destino">Cuenta de Destino</label>
                    <input id="operacion-destino" value={cuentaDestino} onChange={(e) => setCuentaDestino(e.target.value)} required placeholder="Ej. 1010000002" />
                  </div>
                )}
                <div className="sol-field">
                  <label htmlFor="operacion-monto">Monto</label>
                  <input id="operacion-monto" type="number" step="0.01" min="0.01" value={montoOp} onChange={(e) => setMontoOp(e.target.value)} required placeholder="0.00" />
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

              {movimientosList && movimientosList.length === 0 && (
                <p role="status" style={{ marginTop: "20px" }}>La cuenta no tiene movimientos.</p>
              )}
              {movimientosList && movimientosList.length > 0 && (
                <div className="sol-tablewrap" style={{ marginTop: "20px" }}>
                  <table>
                    <thead>
                      <tr>
                        <th>UUID Transacción</th>
                        <th>Tipo</th>
                        <th>Mov.</th>
                        <th className="num">Monto</th>
                        <th>Glosa</th>
                        <th>Fecha</th>
                      </tr>
                    </thead>
                    <tbody>
                      {movimientosList.map((m) => (
                        <tr key={m.uuid_transaccion}>
                          <td style={{ fontFamily: "monospace", fontSize: "11px" }}>{m.uuid_transaccion}</td>
                          <td>{m.tipo_operacion}</td>
                          <td>{m.naturaleza === "D" ? "Débito" : "Crédito"}</td>
                          <td className="num">{formatoMoneda(m.monto, m.moneda)}</td>
                          <td>{m.glosa}</td>
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
                    <div><small>Tipo Operación:</small> <strong>{movimientoDetalle.tipo_operacion}</strong></div>
                    <div><small>Naturaleza:</small> <strong>{movimientoDetalle.naturaleza === "D" ? "Débito" : "Crédito"}</strong></div>
                    <div><small>Monto:</small> <strong style={{ color: "#15324f" }}>{formatoMoneda(movimientoDetalle.monto, movimientoDetalle.moneda)}</strong></div>
                    <div><small>Glosa:</small> <strong>{movimientoDetalle.glosa}</strong></div>
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
