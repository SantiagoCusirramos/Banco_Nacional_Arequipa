"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cerrarSesion, obtenerMiPerfil, type Usuario } from "@/lib/auth";
import { cuentasDeCliente, formatoMoneda as formatoMonedaCuenta, type Cuenta } from "@/lib/cuentas";
import {
  comprobante as obtenerComprobante, creditosDeCliente, esSesionInvalida, formatoMoneda, mensajeDeError,
  montoAPagar as obtenerMontoAPagar, pagarCuota, type Comprobante, type Credito, type MontoAPagar, type ResultadoPago,
} from "@/lib/cobranza";

type Pestana = "credito" | "pago";
type Aviso = { text: string; error: boolean };

const ETIQUETA_ESTADO: Record<string, string> = {
  CONFIRMADO: "aprobada", RECHAZADO: "rechazada", PENDIENTE: "en_evaluacion", REQUIERE_REVISION: "observada",
};

const MENSAJE_ESTADO: Record<string, string> = {
  PENDIENTE: "CUENTAS no confirmó el cargo a tiempo. El pago queda pendiente y se revisará: si el cargo se "
    + "realizó, se confirmará; si no, se rechazará. Puedes consultarlo más tarde.",
  REQUIERE_REVISION: "El pago requiere revisión manual del área de Cobranza antes de aplicarse.",
};

export default function PagarCuotaPage() {
  const [tab, setTab] = useState<Pestana>("credito");
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [sinSesion, setSinSesion] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<Aviso | null>(null);

  useEffect(() => {
    obtenerMiPerfil().then(setUsuario).catch((err) => {
      setUsuario(null);
      if (esSesionInvalida(err)) setSinSesion(true);
    });
  }, []);

  // Paso 1: cliente y sus créditos
  const [idCliente, setIdCliente] = useState("");
  const [creditos, setCreditos] = useState<Credito[] | null>(null);

  // Paso 2: crédito elegido, lo que toca pagar hoy, cuentas del cliente y el pago
  const [credito, setCredito] = useState<Credito | null>(null);
  const [monto, setMonto] = useState<MontoAPagar | null>(null);
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [cuentaOrigen, setCuentaOrigen] = useState("");
  const [montoPago, setMontoPago] = useState("");
  // Un intento de pago conserva su referencia mientras no se edite; así un reintento (tras un
  // error de red, por ejemplo) no cobra dos veces (CR-INT-08, idempotencia por referencia).
  const [referencia, setReferencia] = useState(() => crypto.randomUUID());
  const [resultado, setResultado] = useState<ResultadoPago | null>(null);
  const [comprobante, setComprobante] = useState<Comprobante | null>(null);

  async function ejecutar(accion: () => Promise<void>, alFallar?: () => void) {
    setLoading(true);
    setNotice(null);
    try {
      await accion();
    } catch (err) {
      alFallar?.();
      if (esSesionInvalida(err)) setSinSesion(true);
      else setNotice({ text: mensajeDeError(err), error: true });
    } finally {
      setLoading(false);
    }
  }

  function buscarCreditos(e: React.FormEvent) {
    e.preventDefault();
    const codigo = idCliente.trim().toUpperCase();
    if (!codigo) return;
    void ejecutar(async () => setCreditos(await creditosDeCliente(codigo)), () => setCreditos(null));
  }

  function elegirCredito(c: Credito) {
    void ejecutar(async () => {
      const [montoHoy, cuentasCliente] = await Promise.all([
        obtenerMontoAPagar(c.codCredito),
        cuentasDeCliente(c.idCliente).catch(() => [] as Cuenta[]),
      ]);
      setCredito(c);
      setMonto(montoHoy);
      setCuentas(cuentasCliente);
      setCuentaOrigen(cuentasCliente[0]?.num_cuenta ?? "");
      setMontoPago(montoHoy.totalAPagar);
      setReferencia(crypto.randomUUID());
      setResultado(null);
      setComprobante(null);
      setTab("pago");
    });
  }

  // Editar un dato del pago cambia la referencia: ya no es el mismo intento.
  function editarCuenta(valor: string) {
    setCuentaOrigen(valor);
    setReferencia(crypto.randomUUID());
  }
  function editarMonto(valor: string) {
    setMontoPago(valor);
    setReferencia(crypto.randomUUID());
  }

  function pagar(e: React.FormEvent) {
    e.preventDefault();
    if (!credito || !monto || !cuentaOrigen) return;
    const importe = Number(montoPago);
    if (!Number.isFinite(importe) || importe <= 0) {
      setNotice({ text: "Ingresa un monto mayor a cero.", error: true });
      return;
    }
    if (importe > Number(monto.totalAPagar)) {
      setNotice({ text: `El monto no puede superar lo que toca pagar hoy (${formatoMoneda(monto.totalAPagar)}).`, error: true });
      return;
    }
    void ejecutar(async () => {
      const r = await pagarCuota({
        codCliente: credito.idCliente,
        codCredito: credito.codCredito,
        montoPago: importe.toFixed(2),
        cuentaOrigen,
        referenciaTransaccion: referencia,
      });
      setResultado(r);
      setComprobante(null);
      if (r.estado === "CONFIRMADO") {
        try { setComprobante(await obtenerComprobante(r.referenciaTransaccion)); } catch { /* el resultado ya se muestra sin el comprobante */ }
      }
    });
  }

  function pagarOtraCuota() {
    setCredito(null);
    setMonto(null);
    setCuentas([]);
    setCuentaOrigen("");
    setMontoPago("");
    setResultado(null);
    setComprobante(null);
    setTab("credito");
  }

  const navegacion: { id: Pestana; etiqueta: string }[] = [
    { id: "credito", etiqueta: "1. Elegir crédito" },
    { id: "pago", etiqueta: "2. Pagar cuota" },
  ];

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
          Módulo Cobranza <small>cobro real por CUENTAS</small>
        </div>
        <nav aria-label="Navegación Pagar cuota">
          <p>PAGAR CUOTA</p>
          {navegacion.map((n) => (
            <button key={n.id} className={tab === n.id ? "active" : ""} disabled={n.id === "pago" && !credito}
              onClick={() => setTab(n.id)}>
              {n.etiqueta}
            </button>
          ))}
        </nav>
        {usuario && (
          <div className="sol-sidebar-bottom">
            <div className="sol-profile">
              <span className="sol-avatar">{usuario.nombre.trim()[0]?.toUpperCase()}</span>
              <div>
                <strong>{usuario.nombre}</strong>
                <small>{usuario.rol}</small>
              </div>
              <Link href="/login" onClick={cerrarSesion} title="Cerrar sesión" aria-label="Cerrar sesión"
                style={{ marginLeft: "auto", color: "#b2c6d6" }}>×</Link>
            </div>
          </div>
        )}
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div>
            <span>Cobranza</span>
            <b>/</b>{navegacion.find((n) => n.id === tab)?.etiqueta}
          </div>
          <div className="sol-topbar-right">
            <span className="sol-demo-pill">Requiere sesión iniciada</span>
            <Link href="/" style={{ color: "#15324f", fontWeight: 600, textDecoration: "none", fontSize: "13px" }}>Volver al Home Banking</Link>
          </div>
        </header>

        <main className="sol-main">
          {sinSesion && (
            <div role="alert" className="sol-alert error">
              Tu sesión no está iniciada o ya venció.
              <Link href="/login" onClick={cerrarSesion} style={{ marginLeft: "auto", fontWeight: 600, color: "inherit" }}>
                Iniciar sesión
              </Link>
            </div>
          )}

          {notice && (
            <div role={notice.error ? "alert" : "status"} className={`sol-alert ${notice.error ? "error" : "success"}`}>
              {notice.text}
              <button onClick={() => setNotice(null)} aria-label="Cerrar aviso">×</button>
            </div>
          )}

          {tab === "credito" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Créditos del cliente</h2>
                  <p>Ingresa el código del cliente para ver sus créditos y el estado de sus cuotas.</p>
                </div>
              </div>
              <form onSubmit={buscarCreditos} className="sol-toolbar" style={{ marginTop: "20px" }}>
                <input
                  aria-label="Código del cliente"
                  placeholder="Código del cliente (ej. CLI000000001)"
                  value={idCliente}
                  onChange={(e) => setIdCliente(e.target.value)}
                  required
                  style={{ flex: 1 }}
                />
                <button className="sol-button primary" type="submit" disabled={loading}>
                  {loading ? "Buscando..." : "Ver créditos"}
                </button>
              </form>

              {creditos && creditos.length === 0 && (
                <p role="status" style={{ marginTop: "20px" }}>El cliente no tiene créditos en Cobranza.</p>
              )}

              {creditos && creditos.length > 0 && (
                <div style={{ marginTop: "24px", display: "grid", gap: "16px" }}>
                  {creditos.map((c) => (
                    <div key={c.codCredito} style={{ background: "#f8fafc", padding: "18px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "8px" }}>
                        <h3 style={{ margin: 0 }}>Crédito {c.codCredito}</h3>
                        <span className={`sol-badge ${c.estadoCredito === "EN_MORA" ? "rechazada" : "aprobada"}`}>
                          <span />{c.estadoCredito.replace("_", " ")}
                        </span>
                      </div>
                      <p style={{ margin: "6px 0 14px" }}>
                        Monto aprobado {formatoMoneda(c.montoAprobado, c.moneda)} · Saldo pendiente{" "}
                        <strong>{formatoMoneda(c.saldoTotalPendiente, c.moneda)}</strong>
                      </p>
                      <div className="sol-tablewrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Cuota</th><th>Vence</th><th className="num">Monto</th>
                              <th className="num">Capital</th><th className="num">Mora</th><th>Estado</th>
                            </tr>
                          </thead>
                          <tbody>
                            {c.cuotas.map((cuota) => (
                              <tr key={cuota.idCuota}>
                                <td>{cuota.numeroCuota}</td>
                                <td>{cuota.fechaVencimiento}</td>
                                <td className="num">{formatoMoneda(cuota.montoCuota, c.moneda)}</td>
                                <td className="num">{formatoMoneda(cuota.saldoPendiente, c.moneda)}</td>
                                <td className="num">{formatoMoneda(cuota.moraPendiente, c.moneda)}</td>
                                <td>{cuota.estadoCuota}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {Number(c.saldoTotalPendiente) > 0 ? (
                        <button className="sol-button primary" type="button" style={{ marginTop: "14px" }}
                          disabled={loading} onClick={() => elegirCredito(c)}>
                          Pagar una cuota de este crédito
                        </button>
                      ) : (
                        <p style={{ marginTop: "14px", marginBottom: 0 }}><small>Este crédito ya no tiene saldo pendiente.</small></p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "pago" && credito && monto && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Pagar cuota {monto.numeroCuota} del crédito {credito.codCredito}</h2>
                  <p>Vence el {monto.fechaVencimiento}. El monto se descuenta de la cuenta de ahorros elegida.</p>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "15px", marginTop: "10px", marginBottom: "10px" }}>
                <div><small>Capital</small><br /><strong>{formatoMoneda(monto.saldoCapital, credito.moneda)}</strong></div>
                <div><small>Mora</small><br /><strong>{formatoMoneda(monto.moraVigente, credito.moneda)}</strong></div>
                <div><small>Total a pagar hoy</small><br /><strong style={{ fontSize: "18px", color: "#15324f" }}>{formatoMoneda(monto.totalAPagar, credito.moneda)}</strong></div>
              </div>

              <form onSubmit={pagar} className="sol-form-grid" style={{ marginTop: "10px" }}>
                <div className="sol-field">
                  <label htmlFor="pago-cuenta">Cuenta de ahorros con la que paga</label>
                  {cuentas.length > 0 ? (
                    <select id="pago-cuenta" value={cuentaOrigen} onChange={(e) => editarCuenta(e.target.value)} required>
                      {cuentas.map((cta) => (
                        <option key={cta.num_cuenta} value={cta.num_cuenta}>
                          {cta.num_cuenta} · {formatoMonedaCuenta(cta.saldo_disponible, cta.moneda)} disponible
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input id="pago-cuenta" value={cuentaOrigen} onChange={(e) => editarCuenta(e.target.value)} required
                      placeholder="El cliente no tiene cuentas listadas: ingresa el número" />
                  )}
                </div>
                <div className="sol-field">
                  <label htmlFor="pago-monto">Monto a pagar</label>
                  <input id="pago-monto" type="number" step="0.01" min="0.01" max={monto.totalAPagar}
                    value={montoPago} onChange={(e) => editarMonto(e.target.value)} required />
                </div>
                <div style={{ gridColumn: "1 / -1", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Procesando..." : "Confirmar pago"}
                  </button>
                  <button className="sol-button secondary" type="button" style={{ marginLeft: "10px" }} onClick={pagarOtraCuota}>
                    Elegir otro crédito
                  </button>
                </div>
              </form>

              {resultado && (
                <div style={{ marginTop: "30px", background: "#f8fafc", padding: "20px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <h3 style={{ margin: 0 }}>Resultado del pago</h3>
                    <span className={`sol-badge ${ETIQUETA_ESTADO[resultado.estado] ?? ""}`}>
                      <span />{resultado.estado.replace("_", " ")}
                    </span>
                  </div>
                  <p>Referencia: <strong>{resultado.referenciaTransaccion}</strong></p>

                  {resultado.estado === "RECHAZADO" && (
                    <p role="alert">Motivo: {resultado.motivo ?? "No se especificó un motivo."}</p>
                  )}
                  {(resultado.estado === "PENDIENTE" || resultado.estado === "REQUIERE_REVISION") && (
                    <p role="status">{MENSAJE_ESTADO[resultado.estado]}</p>
                  )}
                  {resultado.estado === "CONFIRMADO" && comprobante && (
                    <div role="status" style={{ marginTop: "10px" }}>
                      <h4 style={{ margin: "0 0 8px" }}>Comprobante {comprobante.numeroOperacion}</h4>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                        <div><small>Fecha:</small> <strong>{comprobante.fechaHora}</strong></div>
                        <div><small>Canal:</small> <strong>{comprobante.canal}</strong></div>
                        <div><small>Monto pagado:</small> <strong>{formatoMoneda(comprobante.montoPagado, credito.moneda)}</strong></div>
                        <div><small>Aplicado a capital:</small> <strong>{formatoMoneda(comprobante.montoAplicadoCapital, credito.moneda)}</strong></div>
                        <div><small>Aplicado a mora:</small> <strong>{formatoMoneda(comprobante.montoAplicadoMora, credito.moneda)}</strong></div>
                        <div><small>Saldo restante del crédito:</small> <strong>{formatoMoneda(comprobante.saldoRestanteCredito, credito.moneda)}</strong></div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
