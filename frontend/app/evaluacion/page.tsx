"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { isAxiosError } from "axios";
import { cerrarSesion, obtenerMiPerfil, type Usuario } from "@/lib/auth";
import {
  ESTADOS, RIESGOS, bandeja, conMoneda, decidir, fecha, fechaHora, historial, listarEnvios, mensajeDeError, porcentaje,
  reintentarEnvio, registrarSituacion, revocar, verEvaluacion,
  type Bandeja, type Decision, type DetalleEvaluacion, type Envio, type Evento, type Riesgo,
} from "@/lib/evaluacion";

type Vista = "bandeja" | "envios" | "historial";
type Aviso = { text: string; error: boolean };
type Ejecutar = (accion: () => Promise<void>) => Promise<void>;

const ETIQUETA: Record<string, string> = {
  PENDIENTE: "Pendiente", EN_REVISION: "En revisión", APROBADO: "Aprobado", OBSERVADO: "Observado",
  RECHAZADO: "Rechazado", VIGENTE: "Vigente", VENCIDA: "Vencida", DESEMBOLSADA: "Desembolsada", REVOCADA: "Revocada",
  ENTREGADO: "Entregado", ERROR: "Error",
};
// Insignias de sol.css: verde favorable, rojo cerrado, ámbar en espera.
const TONO: Record<string, string> = {
  PENDIENTE: "en_evaluacion", EN_REVISION: "observada", APROBADO: "aprobada", OBSERVADO: "observada",
  RECHAZADO: "rechazada", VIGENTE: "aprobada", VENCIDA: "observada", DESEMBOLSADA: "simulado", REVOCADA: "rechazada",
  ENTREGADO: "aprobada", ERROR: "rechazada",
};

function Icono({ nombre, tamano = 18 }: { nombre: string; tamano?: number }) {
  const trazos: Record<string, ReactNode> = {
    bandeja: <path d="M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6H3v-6Z" />,
    enviar: <path d="m4 12 16-8-6 16-2-7Z" />,
    reloj: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    buscar: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="m15 15 6 6" />
      </>
    ),
    volver: <path d="M15 6 9 12l6 6" />,
    activa: <path d="m5 12 4 4L19 6" />,
    cerrar: <path d="M18 6 6 18M6 6l12 12" />,
    salir: <path d="M9 3H3v18h6M12 12h9m-4-4 4 4-4 4" />,
    escudo: (
      <>
        <path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z" />
        <path d="M12 8v5m0 3h.01" />
      </>
    ),
  };
  return (
    <svg width={tamano} height={tamano} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {trazos[nombre]}
    </svg>
  );
}

function Estado({ valor }: { valor: string }) {
  return (
    <span className={`sol-badge ${TONO[valor] ?? ""}`}>
      <span />
      {ETIQUETA[valor] ?? valor}
    </span>
  );
}

function Tarjeta({ titulo, detalle, children }: { titulo: string; detalle?: string; children: ReactNode }) {
  return (
    <section className="sol-card">
      <div className="sol-card-title">
        <div>
          <h2>{titulo}</h2>
          {detalle && <p>{detalle}</p>}
        </div>
      </div>
      <div className="ev-body">{children}</div>
    </section>
  );
}

const esSesionInvalida = (err: unknown) => isAxiosError(err) && err.response?.status === 401;
const MONTO = "^\\d{1,13}(\\.\\d{1,2})?$";

export default function EvaluacionPage() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [sinSesion, setSinSesion] = useState(false);
  const [vista, setVista] = useState<Vista>("bandeja");
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [cargando, setCargando] = useState(false);

  const [datos, setDatos] = useState<Bandeja | null>(null);
  const [filtroEstado, setFiltroEstado] = useState("");
  const [buscar, setBuscar] = useState("");
  const [detalle, setDetalle] = useState<DetalleEvaluacion | null>(null);
  const [envios, setEnvios] = useState<{ items: Envio[]; configurado: boolean } | null>(null);
  const [eventos, setEventos] = useState<Evento[] | null>(null);

  const acciones = usuario?.acciones ?? [];
  const puedeEvaluar = acciones.includes("EVALUAR_CREDITO");
  const puedeDecidir = acciones.includes("APROBAR_CREDITO");
  const puedeAuditar = acciones.includes("VER_AUDITORIA");

  function fallo(err: unknown) {
    if (esSesionInvalida(err)) setSinSesion(true);
    else setAviso({ text: mensajeDeError(err), error: true });
  }

  // La sesión es la de COREDB; con ella se carga la bandeja.
  useEffect(() => {
    obtenerMiPerfil()
      .then((perfil) => {
        setUsuario(perfil);
        return bandeja();
      })
      .then(setDatos)
      .catch((err) => {
        if (esSesionInvalida(err)) setSinSesion(true);
        else setAviso({ text: mensajeDeError(err), error: true });
      });
  }, []);

  const ejecutar: Ejecutar = async (accion) => {
    setCargando(true);
    setAviso(null);
    try {
      await accion();
    } catch (err) {
      fallo(err);
    } finally {
      setCargando(false);
    }
  };

  const filtros = () => ({ estado: filtroEstado, buscar: buscar.trim() });

  function filtrar(e: FormEvent) {
    e.preventDefault();
    void ejecutar(async () => setDatos(await bandeja(filtros())));
  }

  function abrir(id: string) {
    void ejecutar(async () => setDetalle(await verEvaluacion(id)));
  }

  function irA(destino: Vista) {
    setVista(destino);
    setDetalle(null);
    setAviso(null);
    if (destino === "bandeja") void ejecutar(async () => setDatos(await bandeja(filtros())));
    if (destino === "envios") void ejecutar(async () => setEnvios(await listarEnvios()));
    if (destino === "historial") void ejecutar(async () => setEventos(await historial()));
  }

  // Tras registrar o decidir: el detalle nuevo y la bandeja con sus conteos al día.
  async function actualizado(nuevo: DetalleEvaluacion, texto: string) {
    setDetalle(nuevo);
    setDatos(await bandeja(filtros()));
    setAviso({ text: texto, error: false });
  }

  function reintentar(envio: Envio) {
    void ejecutar(async () => {
      await reintentarEnvio(envio.idOperacion);
      if (detalle) setDetalle(await verEvaluacion(detalle.idEvaluacion));
      if (vista === "envios") setEnvios(await listarEnvios());
      setAviso({ text: "El resultado volvió a la cola de envío a Solicitud.", error: false });
    });
  }

  const navegacion: { id: Vista; etiqueta: string; icono: string; visible: boolean }[] = [
    { id: "bandeja", etiqueta: "Bandeja de evaluaciones", icono: "bandeja", visible: true },
    { id: "envios", etiqueta: "Resultados para Solicitud", icono: "enviar", visible: true },
    { id: "historial", etiqueta: "Historial", icono: "reloj", visible: puedeAuditar || puedeDecidir },
  ];
  const titulo = detalle ? `Evaluación ${detalle.idEvaluacion}` : navegacion.find((n) => n.id === vista)?.etiqueta;

  return (
    <div className="sol-shell">
      <aside className="sol-sidebar">
        <div className="sol-brand light">
          <div>
            <strong>BNA<span>®</span></strong>
            <small>Banco Nacional de Arequipa</small>
          </div>
        </div>
        <nav aria-label="Navegación Evaluación" style={{ marginTop: "32px" }}>
          <p>EVALUACIÓN CREDITICIA</p>
          {navegacion.filter((n) => n.visible).map((n) => (
            <button key={n.id} className={vista === n.id && !detalle ? "active" : ""} onClick={() => irA(n.id)}>
              <Icono nombre={n.icono} />
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
                style={{ marginLeft: "auto", color: "#b2c6d6", display: "flex" }}>
                <Icono nombre="salir" tamano={16} />
              </Link>
            </div>
          </div>
        )}
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div>
            <span>Evaluación</span>
            <b>/</b>{titulo}
          </div>
          <div className="sol-topbar-right">
            <span className="sol-demo-pill">Regla provisional RN-EVA-002-P</span>
            <Link href="/" style={{ color: "#15324f", fontWeight: 600, textDecoration: "none", fontSize: "13px" }}>
              Volver al inicio
            </Link>
          </div>
        </header>

        <main className="sol-main">
          <div className="sol-heading">
            <div>
              <h1>{titulo}</h1>
            </div>
            {detalle && (
              <button className="sol-button secondary" onClick={() => setDetalle(null)}>
                <Icono nombre="volver" />
                Volver a la bandeja
              </button>
            )}
          </div>

          {sinSesion && (
            <div role="alert" className="sol-alert error">
              Tu sesión no está iniciada o ya venció.
              <Link href="/login" onClick={cerrarSesion} style={{ marginLeft: "auto", fontWeight: 600, color: "inherit" }}>
                Iniciar sesión
              </Link>
            </div>
          )}

          {aviso && (
            <div role={aviso.error ? "alert" : "status"} className={`sol-alert ${aviso.error ? "error" : "success"}`}>
              {aviso.text}
              <button onClick={() => setAviso(null)} aria-label="Cerrar aviso"><Icono nombre="cerrar" tamano={14} /></button>
            </div>
          )}

          {detalle ? (
            <Detalle detalle={detalle} cargando={cargando} ejecutar={ejecutar} onActualizado={actualizado}
              onReintentar={reintentar} puedeEvaluar={puedeEvaluar} puedeDecidir={puedeDecidir} />
          ) : vista === "bandeja" ? (
            <>
              {datos && (
                <div className="sol-stats" style={{ marginBottom: "24px" }}>
                  {[
                    { etiqueta: "Por evaluar", valor: datos.conteos.PENDIENTE ?? 0, tono: "blue" },
                    { etiqueta: "En revisión del analista", valor: datos.conteos.EN_REVISION ?? 0, tono: "gold" },
                    { etiqueta: "Aprobadas", valor: datos.conteos.APROBADO ?? 0, tono: "green" },
                    { etiqueta: "Observadas o rechazadas",
                      valor: (datos.conteos.OBSERVADO ?? 0) + (datos.conteos.RECHAZADO ?? 0), tono: "red" },
                  ].map((c) => (
                    <div className="sol-stat" key={c.etiqueta}>
                      <div>
                        <small>{c.etiqueta}</small>
                        <strong>{c.valor}</strong>
                      </div>
                      <span className={`sol-stat-icon ${c.tono}`}><Icono nombre="bandeja" /></span>
                    </div>
                  ))}
                </div>
              )}
              <section className="sol-card">
                <div className="sol-card-title">
                  <div>
                    <h2>Expedientes recibidos de Solicitud</h2>
                    <p>Cada versión enviada por SOL es una ronda de evaluación.</p>
                  </div>
                </div>
                <form onSubmit={filtrar} className="sol-toolbar">
                  <select aria-label="Estado" value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}>
                    <option value="">Todos los estados</option>
                    {ESTADOS.map((e) => <option key={e} value={e}>{ETIQUETA[e]}</option>)}
                  </select>
                  <input aria-label="Buscar" placeholder="Cliente, documento, solicitud o evaluación" value={buscar}
                    onChange={(e) => setBuscar(e.target.value)} maxLength={80} style={{ flex: 1 }} />
                  <button className="sol-button primary" type="submit" disabled={cargando}>
                    <Icono nombre="buscar" />
                    Buscar
                  </button>
                </form>
                {datos && datos.items.length === 0 ? (
                  <div className="sol-empty" role="status">
                    <span><Icono nombre="bandeja" tamano={26} /></span>
                    <h3>No hay evaluaciones con ese filtro.</h3>
                    <p>Los expedientes llegan cuando Solicitud los envía.</p>
                  </div>
                ) : (
                  <div className="sol-tablewrap">
                    <table aria-label="Evaluaciones">
                      <thead>
                        <tr>
                          <th>Evaluación</th>
                          <th>Cliente</th>
                          <th className="num">Monto solicitado</th>
                          <th>Plazo</th>
                          <th>Recibida</th>
                          <th>Estado</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {datos?.items.map((e) => (
                          <tr key={e.idEvaluacion}>
                            <td>
                              <span className="sol-record">
                                <strong>{e.idEvaluacion}</strong>
                                <small>Ronda {e.ronda} · versión {e.versionSolicitud}</small>
                              </span>
                            </td>
                            <td>
                              {e.cliente.nombre}
                              <span className="sol-cell-small">{e.cliente.tipoDocumento} {e.cliente.numeroDocumento}</span>
                            </td>
                            <td className="num emphasis">{conMoneda(e.montoSolicitado, e.moneda)}</td>
                            <td>{e.plazoMeses} meses</td>
                            <td>{fechaHora(e.recibidoEn)}</td>
                            <td><Estado valor={e.estado} /></td>
                            <td>
                              <button className="sol-button secondary" onClick={() => abrir(e.idEvaluacion)}
                                aria-label={`Abrir ${e.idEvaluacion}`}>
                                Abrir
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          ) : vista === "envios" ? (
            <Envios envios={envios} puedeDecidir={puedeDecidir} onReintentar={reintentar} />
          ) : (
            <Tarjeta titulo="Historial del módulo" detalle="Los últimos eventos, del más reciente al más antiguo.">
              <Linea eventos={eventos ?? []} />
            </Tarjeta>
          )}
        </main>
      </div>
    </div>
  );
}

type PropsDetalle = {
  detalle: DetalleEvaluacion;
  cargando: boolean;
  ejecutar: Ejecutar;
  onActualizado: (nuevo: DetalleEvaluacion, texto: string) => Promise<void>;
  onReintentar: (envio: Envio) => void;
  puedeEvaluar: boolean;
  puedeDecidir: boolean;
};

function Detalle({ detalle: d, cargando, ejecutar, onActualizado, onReintentar, puedeEvaluar, puedeDecidir }: PropsDetalle) {
  const exp = d.expediente;
  const cal = exp.calendario;
  return (
    <div className="ev-grid">
      <div>
        <Tarjeta titulo="Expediente recibido de Solicitud"
          detalle={`Solicitud ${d.idSolicitud} · versión ${d.versionSolicitud} · ronda ${d.ronda}`}>
          <div style={{ marginBottom: "18px" }}><Estado valor={d.estado} /></div>
          <dl className="ev-dl">
            <div><dt>Cliente</dt><dd>{d.cliente.nombre}</dd></div>
            <div><dt>Documento</dt><dd>{d.cliente.tipoDocumento} {d.cliente.numeroDocumento}</dd></div>
            <div><dt>Código del cliente</dt><dd>{d.cliente.idCliente}</dd></div>
            <div><dt>Producto</dt><dd>{d.producto}</dd></div>
            <div><dt>Monto solicitado</dt><dd>{conMoneda(d.montoSolicitado, d.moneda)}</dd></div>
            <div><dt>Plazo</dt><dd>{d.plazoMeses} meses</dd></div>
            <div><dt>TEA de la política</dt><dd>{porcentaje(d.tasaTea)}</dd></div>
            <div><dt>Destino</dt><dd>{d.destino ?? "—"}</dd></div>
            <div><dt>Fecha base del calendario</dt><dd>{fecha(exp.fechaBase)}</dd></div>
            <div><dt>Enviado por</dt><dd>{exp.actorEnvio ?? "—"} · {fechaHora(exp.recibidoEn)}</dd></div>
            <div><dt>Política de SOL</dt><dd>{exp.politica.version ?? "—"}</dd></div>
            <div><dt>Acuse entregado a SOL</dt><dd>{exp.acuse}</dd></div>
          </dl>
          <p>
            Garantías declaradas: {exp.garantias.length === 0 ? "ninguna" : exp.garantias.map(
              (g) => `${g.tipo} (${conMoneda(g.valorTasacion)})`).join(", ")}. Fiadores: {exp.fiadores}.
            {exp.simulado && " Enviado en modo simulado."}
          </p>
        </Tarjeta>

        <Tarjeta titulo="Calendario de pagos de Solicitud"
          detalle={`Lo arma SOL (RN-SOL-006) y pasa sin cambios a Desembolso y Cobranza. Estado: ${cal.estado ?? "—"}.`}>
          <div className="sol-tablewrap">
            <table aria-label="Calendario de pagos">
              <thead>
                <tr>
                  <th>N.°</th>
                  <th>Vencimiento</th>
                  <th className="num">Amortización</th>
                  <th className="num">Interés</th>
                  <th className="num">Cuota</th>
                  <th className="num">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {cal.cuotas.map((q) => (
                  <tr key={q.numeroCuota}>
                    <td>{q.numeroCuota}</td>
                    <td>{fecha(q.fechaVencimiento)}</td>
                    <td className="num">{conMoneda(q.amortizacion, d.moneda)}</td>
                    <td className="num">{conMoneda(q.interes, d.moneda)}</td>
                    <td className="num emphasis">{conMoneda(q.cuotaTotal, d.moneda)}</td>
                    <td className="num">{conMoneda(q.saldoFinal, d.moneda)}</td>
                  </tr>
                ))}
                <tr className="ev-total">
                  <td colSpan={3}>Total a pagar</td>
                  <td className="num">{conMoneda(cal.interesesTotales, d.moneda)}</td>
                  <td className="num">{conMoneda(cal.totalPagar, d.moneda)}</td>
                  <td />
                </tr>
              </tbody>
            </table>
          </div>
        </Tarjeta>
      </div>

      <div>
        {d.estado === "PENDIENTE" && (puedeEvaluar ? (
          <FormSituacion detalle={d} cargando={cargando} ejecutar={ejecutar} onActualizado={onActualizado} />
        ) : (
          <Tarjeta titulo="Situación financiera">
            <div className="sol-mutedbox">Pendiente: un analista debe registrar la situación financiera del cliente.</div>
          </Tarjeta>
        ))}

        {d.motor && (
          <Tarjeta titulo="Resultado de la regla" detalle={d.motor.regla}>
            <div className="sol-metrics">
              <div><small>Score</small><strong>{d.motor.score}</strong></div>
              <div><small>Límite</small><strong>{conMoneda(d.motor.limite, d.moneda)}</strong></div>
              <div><small>Monto / límite</small><strong>{porcentaje(d.motor.ratio)}</strong></div>
            </div>
            {d.situacionFinanciera && (
              <p>
                Ingreso mensual {conMoneda(d.situacionFinanciera.ingresoMensual)}, deuda mensual{" "}
                {conMoneda(d.situacionFinanciera.deudaMensual)}, riesgo {d.situacionFinanciera.riesgo.toLowerCase()}.
                Registró {d.situacionFinanciera.registradoPor} el {fechaHora(d.situacionFinanciera.registradoEn)}.
              </p>
            )}
          </Tarjeta>
        )}

        {d.estado === "EN_REVISION" && (puedeDecidir ? (
          <FormDecision detalle={d} cargando={cargando} ejecutar={ejecutar} onActualizado={onActualizado} />
        ) : (
          <Tarjeta titulo="Decisión del analista">
            <div className="sol-mutedbox">El caso está en la zona gris de la regla: lo decide un analista.</div>
          </Tarjeta>
        ))}

        {d.decididoPor && (
          <Tarjeta titulo="Resultado" detalle={`Decidió ${d.decididoPor} · ${fechaHora(d.decididoEn)}`}>
            <div style={{ marginBottom: "12px" }}><Estado valor={d.estado} /></div>
            <p>{d.motivo}</p>
          </Tarjeta>
        )}

        {d.aprobacion && (
          <Aprobacion detalle={d} cargando={cargando} ejecutar={ejecutar} onActualizado={onActualizado}
            puedeDecidir={puedeDecidir} />
        )}

        {d.envioSol && (
          <Tarjeta titulo="Resultado para Solicitud (CR-INT-03)" detalle={`Operación ${d.envioSol.idOperacion}`}>
            <dl className="ev-dl">
              <div><dt>Estado</dt><dd><Estado valor={d.envioSol.estado} /></dd></div>
              <div><dt>Intentos</dt><dd>{d.envioSol.intentos}</dd></div>
              <div><dt>Entregado</dt><dd>{fechaHora(d.envioSol.entregadoEn)}</dd></div>
              <div><dt>Último error</dt><dd>{d.envioSol.ultimoError ?? "—"}</dd></div>
            </dl>
            {d.envioSol.estado === "ERROR" && puedeDecidir && (
              <button className="sol-button secondary" style={{ marginTop: "18px" }} disabled={cargando}
                onClick={() => d.envioSol && onReintentar(d.envioSol)}>
                Reintentar envío
              </button>
            )}
          </Tarjeta>
        )}

        <Tarjeta titulo="Historial">
          <Linea eventos={d.historial} />
        </Tarjeta>
      </div>
    </div>
  );
}

type PropsAccion = {
  detalle: DetalleEvaluacion;
  cargando: boolean;
  ejecutar: Ejecutar;
  onActualizado: (nuevo: DetalleEvaluacion, texto: string) => Promise<void>;
};

function FormSituacion({ detalle, cargando, ejecutar, onActualizado }: PropsAccion) {
  const [ingreso, setIngreso] = useState("");
  const [deuda, setDeuda] = useState("0.00");
  const [riesgo, setRiesgo] = useState<Riesgo>("BUENO");
  const [verificada, setVerificada] = useState(false);

  function enviar(e: FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const nuevo = await registrarSituacion(detalle.idEvaluacion, {
        ingresoMensual: ingreso.trim(), deudaMensual: deuda.trim(), riesgo, verificada, version: detalle.version,
      });
      const resultado = nuevo.estado === "EN_REVISION" ? "queda en revisión del analista" : `resultó ${ETIQUETA[nuevo.estado]}`;
      await onActualizado(nuevo, `Situación financiera registrada: la evaluación ${resultado}.`);
    });
  }

  return (
    <Tarjeta titulo="Situación financiera" detalle="Con estos datos corre la regla de evaluación.">
      <form onSubmit={enviar}>
        <div className="sol-form-grid">
          <div className="sol-field">
            <label htmlFor="ev-ingreso">Ingreso mensual (S/)</label>
            <input id="ev-ingreso" inputMode="decimal" pattern={MONTO} value={ingreso} required
              onChange={(e) => setIngreso(e.target.value)} placeholder="0.00" />
          </div>
          <div className="sol-field">
            <label htmlFor="ev-deuda">Deuda mensual (S/)</label>
            <input id="ev-deuda" inputMode="decimal" pattern={MONTO} value={deuda} required
              onChange={(e) => setDeuda(e.target.value)} />
          </div>
          <div className="sol-field">
            <label htmlFor="ev-riesgo">Riesgo</label>
            <select id="ev-riesgo" value={riesgo} onChange={(e) => setRiesgo(e.target.value as Riesgo)}>
              {RIESGOS.map((r) => <option key={r} value={r}>{r.charAt(0) + r.slice(1).toLowerCase()}</option>)}
            </select>
          </div>
        </div>
        <label className="ev-check">
          <input type="checkbox" checked={verificada} onChange={(e) => setVerificada(e.target.checked)} />
          Verifiqué la situación financiera con el sustento del cliente
        </label>
        <button className="sol-button primary" type="submit" disabled={cargando}>
          <Icono nombre="activa" />
          {cargando ? "Evaluando..." : "Registrar y evaluar"}
        </button>
      </form>
    </Tarjeta>
  );
}

function FormDecision({ detalle, cargando, ejecutar, onActualizado }: PropsAccion) {
  const [decision, setDecision] = useState<Decision>("APROBADO");
  const [observaciones, setObservaciones] = useState("");
  const opciones: { valor: Decision; etiqueta: string }[] = [
    { valor: "APROBADO", etiqueta: "Aprobar" },
    { valor: "OBSERVADO", etiqueta: "Observar: Solicitud corrige" },
    { valor: "RECHAZADO", etiqueta: "Rechazar" },
  ];

  function enviar(e: FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const nuevo = await decidir(detalle.idEvaluacion, {
        decision, observaciones: observaciones.trim(), version: detalle.version,
      });
      await onActualizado(nuevo, `Evaluación ${ETIQUETA[nuevo.estado].toLowerCase()}. El resultado se enviará a Solicitud.`);
    });
  }

  return (
    <Tarjeta titulo="Decisión del analista" detalle="El monto está entre el 80 % y el 100 % del límite.">
      <form onSubmit={enviar}>
        <div className="ev-opciones" role="radiogroup" aria-label="Decisión">
          {opciones.map((o) => (
            <label key={o.valor}>
              <input type="radio" name="decision" value={o.valor} checked={decision === o.valor}
                onChange={() => setDecision(o.valor)} />
              {o.etiqueta}
            </label>
          ))}
        </div>
        <div className="sol-field">
          <label htmlFor="ev-observaciones">Observaciones para Solicitud</label>
          <textarea id="ev-observaciones" value={observaciones} onChange={(e) => setObservaciones(e.target.value)}
            minLength={10} maxLength={1000} rows={4} required />
          <small>Solicitud las recibe con el resultado. Al observar, el asesor corrige en una versión nueva.</small>
        </div>
        <button className="sol-button primary" type="submit" disabled={cargando}>
          {cargando ? "Guardando..." : "Registrar decisión"}
        </button>
      </form>
    </Tarjeta>
  );
}

function Aprobacion({ detalle, cargando, ejecutar, onActualizado, puedeDecidir }: PropsAccion & { puedeDecidir: boolean }) {
  const a = detalle.aprobacion;
  const [motivo, setMotivo] = useState("");
  if (!a) return null;

  function revocarAprobacion(e: FormEvent) {
    e.preventDefault();
    if (!a) return;
    void ejecutar(async () => {
      await revocar(a.idAprobacion, { motivo: motivo.trim(), version: a.version });
      await onActualizado(await verEvaluacion(detalle.idEvaluacion), "Aprobación revocada: Desembolso ya no podrá usarla.");
    });
  }

  return (
    <Tarjeta titulo="Aprobación para Desembolso (CR-INT-04)" detalle={`${a.idAprobacion} · versión ${a.version}`}>
      <dl className="ev-dl">
        <div><dt>Crédito</dt><dd>{a.codCredito}</dd></div>
        <div><dt>Estado</dt><dd><Estado valor={a.estado} /></dd></div>
        <div><dt>Monto aprobado</dt><dd>{conMoneda(a.montoAprobado, a.moneda)}</dd></div>
        <div><dt>Vigente hasta</dt><dd>{fechaHora(a.vigenteHasta)}</dd></div>
        <div><dt>Aprobó</dt><dd>{a.aprobadaPor}</dd></div>
        <div><dt>Plazo y TEA</dt><dd>{a.plazoMeses} meses · {porcentaje(a.tasaTea)}</dd></div>
        {a.desembolso && (
          <div><dt>Desembolsada</dt><dd>Orden {a.desembolso.codigoOrden} · {fechaHora(a.desembolso.fechaDesembolso)}</dd></div>
        )}
        {a.revocacion && (
          <div><dt>Revocada por {a.revocacion.revocadaPor}</dt><dd>{a.revocacion.motivo}</dd></div>
        )}
      </dl>
      {a.estado === "VIGENTE" && puedeDecidir && (
        <form onSubmit={revocarAprobacion} style={{ marginTop: "20px" }}>
          <div className="sol-field">
            <label htmlFor="ev-motivo">Motivo de la revocación</label>
            <input id="ev-motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} minLength={10}
              maxLength={500} required />
          </div>
          <button className="sol-button secondary" type="submit" disabled={cargando}>Revocar aprobación</button>
        </form>
      )}
    </Tarjeta>
  );
}

function Envios({ envios, puedeDecidir, onReintentar }:
  { envios: { items: Envio[]; configurado: boolean } | null; puedeDecidir: boolean; onReintentar: (e: Envio) => void }) {
  return (
    <section className="sol-card">
      <div className="sol-card-title">
        <div>
          <h2>Resultados para Solicitud (CR-INT-03)</h2>
          <p>Se entregan al menos una vez; SOL reconoce un reintento sin duplicarlo.</p>
        </div>
      </div>
      {envios && !envios.configurado && (
        <div className="ev-body">
          <div className="sol-alert neutral" role="status">
            Solicitud sigue en modo simulado: los resultados esperan aquí hasta que SOL active su modo real.
          </div>
        </div>
      )}
      <div className="sol-tablewrap">
        <table aria-label="Resultados para Solicitud">
          <thead>
            <tr>
              <th>Evaluación</th>
              <th>Decisión</th>
              <th>Estado</th>
              <th>Intentos</th>
              <th>Último error</th>
              <th>Creado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {envios?.items.map((e) => (
              <tr key={e.idOperacion}>
                <td>{e.idEvaluacion}</td>
                <td><Estado valor={e.decision} /></td>
                <td><Estado valor={e.estado} /></td>
                <td>{e.intentos}</td>
                <td>{e.ultimoError ?? "—"}</td>
                <td>{fechaHora(e.creadoEn)}</td>
                <td>
                  {e.estado === "ERROR" && puedeDecidir && (
                    <button className="sol-button secondary" onClick={() => onReintentar(e)}>Reintentar</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Linea({ eventos }: { eventos: Evento[] }) {
  if (eventos.length === 0) return <div className="sol-mutedbox">Sin eventos.</div>;
  return (
    <div className="sol-timeline">
      {eventos.map((h) => (
        <div key={h.id}>
          <span><Icono nombre="activa" tamano={13} /></span>
          <div>
            <strong>{h.evento.replaceAll("_", " ").toLowerCase()}</strong>
            <p>{h.actor}{h.idEvaluacion ? ` · ${h.idEvaluacion}` : ""}</p>
            <small>{fechaHora(h.fecha)}</small>
          </div>
        </div>
      ))}
    </div>
  );
}
