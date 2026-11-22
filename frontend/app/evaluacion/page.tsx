"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { isAxiosError } from "axios";
import { cerrarSesion, obtenerMiPerfil, type Usuario } from "@/lib/auth";
import { AvisoPermiso } from "@/app/components/AvisoPermiso";
import { BarraNavegacion } from "@/app/components/BarraNavegacion";
import { etiquetaSolicitud } from "@/lib/continuidad";
import { pantallaPorHref, puedeVerPantalla } from "@/lib/pantallas";
import {
  ESTADOS, RIESGOS, bandeja, conMoneda, decidir, evaluar, fecha, fechaHora, mensajeDeError, porcentaje,
  resultadosSol, revocar, sumar, verSolicitud,
  type Decision, type DetalleSolicitud, type MensajeSol, type Riesgo, type Solicitud,
} from "@/lib/evaluacion";

// Pantalla del analista. Todo vive en COREDB: Evaluación reenvía el token de esta sesión,
// así que COREDB vuelve a comprobar el permiso y su historial registra a la persona.

// Evaluación se consulta con VER_CREDITO ( auditoría ), se evalúa y decide con las acciones del mapa.
// El menú del portal no ofrece la pantalla a quien solo tiene VER_CREDITO (MR-02).
const puedeConsultarEvaluacion = (acciones?: string[] | null) =>
  puedeVerPantalla(acciones, "/evaluacion") || Boolean(acciones?.includes("VER_CREDITO"));

type Vista = "bandeja" | "resultados";
type Aviso = { text: string; error: boolean };
type Ejecutar = (accion: () => Promise<void>) => Promise<void>;

const ETIQUETA: Record<string, string> = {
  REGISTRADA: "Registrada", EN_EVALUACION: "En evaluación", APROBADA: "Aprobada", RECHAZADA: "Rechazada",
  DESEMBOLSADA: "Desembolsada", APROBADO: "Aprobado", OBSERVADO: "Observado", RECHAZADO: "Rechazado",
};
// Insignias de sol.css: verde favorable, rojo cerrado, ámbar en espera.
const TONO: Record<string, string> = {
  REGISTRADA: "en_evaluacion", EN_EVALUACION: "en_evaluacion", APROBADA: "aprobada", RECHAZADA: "rechazada",
  DESEMBOLSADA: "simulado", APROBADO: "aprobada", OBSERVADO: "observada", RECHAZADO: "rechazada",
};

function Icono({ nombre, tamano = 18 }: { nombre: string; tamano?: number }) {
  const trazos: Record<string, ReactNode> = {
    bandeja: <path d="M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6H3v-6Z" />,
    enviar: <path d="m4 12 16-8-6 16-2-7Z" />,
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
  const [cargandoPerfil, setCargandoPerfil] = useState(true);
  const [sinSesion, setSinSesion] = useState(false);
  const [vista, setVista] = useState<Vista>("bandeja");
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [cargando, setCargando] = useState(false);

  const [items, setItems] = useState<Solicitud[] | null>(null);
  const [filtroEstado, setFiltroEstado] = useState("");
  const [codCliente, setCodCliente] = useState("");
  const [detalle, setDetalle] = useState<DetalleSolicitud | null>(null);
  const [resultados, setResultados] = useState<{ configurado: boolean; ventanaDias: number; items: MensajeSol[] } | null>(null);

  const acciones = usuario?.acciones ?? [];
  const puedeEvaluar = acciones.includes("EVALUAR_CREDITO");
  const puedeDecidir = acciones.includes("APROBAR_CREDITO");

  function fallo(err: unknown) {
    if (esSesionInvalida(err)) setSinSesion(true);
    else setAviso({ text: mensajeDeError(err), error: true });
  }

  // La sesión es la de COREDB; con ella se carga la bandeja.
  useEffect(() => {
    obtenerMiPerfil()
      .then((perfil) => {
        setUsuario(perfil);
        return puedeConsultarEvaluacion(perfil.acciones) ? bandeja() : null;
      })
      .then((lista) => { if (lista) setItems(lista); })
      .catch((err) => {
        if (esSesionInvalida(err)) setSinSesion(true);
        else setAviso({ text: mensajeDeError(err), error: true });
      })
      .finally(() => setCargandoPerfil(false));
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

  const filtros = () => ({ estado: filtroEstado, codCliente: codCliente.trim() });

  function filtrar(e: FormEvent) {
    e.preventDefault();
    void ejecutar(async () => setItems(await bandeja(filtros())));
  }

  function abrir(id: string) {
    void ejecutar(async () => setDetalle(await verSolicitud(id)));
  }

  function irA(destino: Vista) {
    setVista(destino);
    setDetalle(null);
    setAviso(null);
    if (destino === "bandeja") void ejecutar(async () => setItems(await bandeja(filtros())));
    if (destino === "resultados") void ejecutar(async () => setResultados(await resultadosSol()));
  }

  // Tras evaluar, decidir o revocar: el detalle y la bandeja vuelven a leerse de COREDB.
  async function actualizado(id: string, texto: string) {
    setDetalle(await verSolicitud(id));
    setItems(await bandeja(filtros()));
    setAviso({ text: texto, error: false });
  }

  const navegacion: { id: Vista; etiqueta: string; icono: string }[] = [
    { id: "bandeja", etiqueta: "Bandeja de solicitudes", icono: "bandeja" },
    { id: "resultados", etiqueta: "Resultados para Solicitud", icono: "enviar" },
  ];
  const titulo = detalle ? etiquetaSolicitud(detalle) : navegacion.find((n) => n.id === vista)?.etiqueta;
  const conteo = (estado: string) => (items ?? []).filter((s) => s.estado === estado).length;

  if (cargandoPerfil) return <main className="sol-main"><p>Cargando…</p></main>;
  const pantalla = pantallaPorHref("/evaluacion");
  const permitido = puedeConsultarEvaluacion(usuario?.acciones);
  if (usuario && !permitido) {
    return (
      <main className="sol-main">
        <BarraNavegacion titulo="Evaluación" usuario={usuario} />
        <AvisoPermiso mensaje={`Tu rol no tiene permiso para usar esta pantalla. Esta pantalla es para ${pantalla?.rolesPermitidos ?? "personal autorizado"}.`} detalle="Si necesitas evaluar solicitudes, pide a un administrador que revise tus permisos en COREDB." />
      </main>
    );
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
        <nav aria-label="Navegación Evaluación" style={{ marginTop: "32px" }}>
          <p>EVALUACIÓN CREDITICIA</p>
          {navegacion.map((n) => (
            <button key={n.id} className={vista === n.id && !detalle ? "active" : ""} onClick={() => irA(n.id)}>
              <Icono nombre={n.icono} />
              {n.etiqueta}
            </button>
          ))}
        </nav>
        {usuario && (
          <div className="sol-sidebar-bottom">
            <div className="sol-profile">
              <span className="sol-avatar">{(usuario.nombre || usuario.username).trim()[0]?.toUpperCase()}</span>
              <div>
                <strong>{usuario.nombre || usuario.username}</strong>
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
        <BarraNavegacion titulo="Evaluación" subtitulo={String(titulo ?? "")} usuario={usuario} />

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
              puedeEvaluar={puedeEvaluar} puedeDecidir={puedeDecidir} />
          ) : vista === "bandeja" ? (
            <>
              {items && (
                <div className="sol-stats" style={{ marginBottom: "24px" }}>
                  {[
                    { etiqueta: "En evaluación", valor: conteo("EN_EVALUACION"), tono: "gold" },
                    { etiqueta: "Aprobadas", valor: conteo("APROBADA"), tono: "green" },
                    { etiqueta: "Rechazadas", valor: conteo("RECHAZADA"), tono: "red" },
                    { etiqueta: "Desembolsadas", valor: conteo("DESEMBOLSADA"), tono: "blue" },
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
                    <h2>Solicitudes recibidas de Solicitud</h2>
                    <p>Cada versión enviada por SOL es una ronda de evaluación. Sin datos personales del cliente: solo su código.</p>
                  </div>
                </div>
                <form onSubmit={filtrar} className="sol-toolbar">
                  <select aria-label="Estado" value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}>
                    <option value="">Todos los estados</option>
                    {ESTADOS.map((e) => <option key={e} value={e}>{ETIQUETA[e]}</option>)}
                  </select>
                  <input aria-label="Código del cliente" placeholder="Código del cliente" value={codCliente}
                    onChange={(e) => setCodCliente(e.target.value)} maxLength={12} pattern="[A-Za-z0-9]*" style={{ flex: 1 }} />
                  <button className="sol-button primary" type="submit" disabled={cargando}>
                    <Icono nombre="buscar" />
                    Buscar
                  </button>
                </form>
                {items && items.length === 0 ? (
                  <div className="sol-empty" role="status">
                    <span><Icono nombre="bandeja" tamano={26} /></span>
                    <h3>No hay solicitudes con ese filtro.</h3>
                    <p>Las solicitudes llegan cuando Solicitud envía el expediente.</p>
                  </div>
                ) : (
                  <div className="sol-tablewrap">
                    <table aria-label="Solicitudes">
                      <thead>
                        <tr>
                          <th>Solicitud</th>
                          <th>Cliente</th>
                          <th className="num">Monto solicitado</th>
                          <th>Plazo</th>
                          <th>Recibida</th>
                          <th>Estado</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {items?.map((s) => (
                          <tr key={s.idSolicitud}>
                            <td>
                              <span className="sol-record">
                                <strong>{etiquetaSolicitud(s)}</strong>
                                <small>Ronda {s.ronda ?? "—"} · versión {s.versionSolicitud}</small>
                              </span>
                            </td>
                            <td>{s.codCliente}</td>
                            <td className="num emphasis">{conMoneda(s.montoSolicitado, s.moneda)}</td>
                            <td>{s.plazoMeses} meses</td>
                            <td>{fechaHora(s.fechaCreacion)}</td>
                            <td><Estado valor={s.estado} /></td>
                            <td>
                              <button className="sol-button secondary" onClick={() => abrir(s.idSolicitud)}
                                aria-label={`Abrir ${s.idSolicitud}`}>
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
          ) : (
            <Resultados resultados={resultados} />
          )}
        </main>
      </div>
    </div>
  );
}

type PropsDetalle = {
  detalle: DetalleSolicitud;
  cargando: boolean;
  ejecutar: Ejecutar;
  onActualizado: (id: string, texto: string) => Promise<void>;
  puedeEvaluar: boolean;
  puedeDecidir: boolean;
};

function Detalle({ detalle: d, cargando, ejecutar, onActualizado, puedeEvaluar, puedeDecidir }: PropsDetalle) {
  const cal = d.calendario;
  const ultima = d.evaluaciones.find((e) => e.esUltima) ?? null;
  const porEvaluar = d.estado === "EN_EVALUACION" && (!ultima || ultima.ronda !== d.ronda);
  const porDecidir = d.estado === "EN_EVALUACION" && ultima?.resultado === "OBSERVADO" && !ultima.decision;
  return (
    <div className="ev-grid">
      <div>
        <Tarjeta titulo="Solicitud" detalle={`Versión ${d.versionSolicitud} · ronda ${d.ronda ?? "—"}`}>
          <div style={{ marginBottom: "18px" }}><Estado valor={d.estado} /></div>
          <dl className="ev-dl">
            <div><dt>Código del cliente</dt><dd>{d.codCliente}</dd></div>
            <div><dt>Monto solicitado</dt><dd>{conMoneda(d.montoSolicitado, d.moneda)}</dd></div>
            <div><dt>Plazo</dt><dd>{d.plazoMeses} meses</dd></div>
            <div><dt>Tasa del calendario</dt><dd>{porcentaje(cal?.tasa)}</dd></div>
            <div><dt>Método</dt><dd>{cal?.metodo ?? "—"}</dd></div>
            <div><dt>Recibida</dt><dd>{fechaHora(d.fechaCreacion)}</dd></div>
          </dl>
        </Tarjeta>

        {cal && (
          <Tarjeta titulo="Calendario de pagos de Solicitud"
            detalle={`Lo arma SOL (RN-SOL-006) y pasa sin cambios a Desembolso y Cobranza. Tipo: ${cal.tipo}.`}>
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
                      <td className="num">{conMoneda(q.capital, d.moneda)}</td>
                      <td className="num">{conMoneda(q.interes, d.moneda)}</td>
                      <td className="num emphasis">{conMoneda(q.cuotaTotal, d.moneda)}</td>
                      <td className="num">{conMoneda(q.saldoCapital, d.moneda)}</td>
                    </tr>
                  ))}
                  <tr className="ev-total">
                    <td colSpan={3}>Total a pagar</td>
                    <td className="num">{conMoneda(sumar(cal.cuotas.map((q) => q.interes)), d.moneda)}</td>
                    <td className="num">{conMoneda(sumar(cal.cuotas.map((q) => q.cuotaTotal)), d.moneda)}</td>
                    <td />
                  </tr>
                </tbody>
              </table>
            </div>
          </Tarjeta>
        )}
      </div>

      <div>
        {porEvaluar && (puedeEvaluar ? (
          <FormSituacion detalle={d} cargando={cargando} ejecutar={ejecutar} onActualizado={onActualizado} />
        ) : (
          <Tarjeta titulo="Situación financiera">
            <div className="sol-mutedbox">Pendiente: un analista debe registrar la situación financiera del cliente.</div>
          </Tarjeta>
        ))}

        {ultima && (
          <Tarjeta titulo="Resultado de la regla" detalle={`Regla ${ultima.regla} · ronda ${ultima.ronda}`}>
            <div style={{ marginBottom: "12px" }}><Estado valor={ultima.resultadoRegla} /></div>
            <div className="sol-metrics">
              <div><small>Score</small><strong>{ultima.score}</strong></div>
              <div><small>Límite</small><strong>{conMoneda(ultima.limite, d.moneda)}</strong></div>
            </div>
            <p>
              Ingreso mensual {conMoneda(ultima.ingresoMensual)}, deuda mensual {conMoneda(ultima.deudaMensual)}.
              Evaluada el {fechaHora(ultima.fechaEvaluacion)}.
            </p>
          </Tarjeta>
        )}

        {porDecidir && ultima && (puedeDecidir ? (
          <FormDecision idEvaluacion={ultima.idEvaluacion} idSolicitud={d.idSolicitud} cargando={cargando}
            ejecutar={ejecutar} onActualizado={onActualizado} />
        ) : (
          <Tarjeta titulo="Decisión del analista">
            <div className="sol-mutedbox">El caso está en la zona gris de la regla: lo decide un analista.</div>
          </Tarjeta>
        ))}

        {ultima?.decision && (
          <Tarjeta titulo="Decisión del analista" detalle={fechaHora(ultima.fechaDecision)}>
            <div style={{ marginBottom: "12px" }}><Estado valor={ultima.decision} /></div>
            <p>{ultima.comentario}</p>
          </Tarjeta>
        )}

        {d.estado === "APROBADA" && puedeDecidir && (
          <Revocacion idSolicitud={d.idSolicitud} cargando={cargando} ejecutar={ejecutar} onActualizado={onActualizado} />
        )}

        <Tarjeta titulo="Historial">
          <Linea historial={d.historial} />
        </Tarjeta>
      </div>
    </div>
  );
}

type PropsAccion = {
  cargando: boolean;
  ejecutar: Ejecutar;
  onActualizado: (id: string, texto: string) => Promise<void>;
};

function FormSituacion({ detalle, cargando, ejecutar, onActualizado }: PropsAccion & { detalle: DetalleSolicitud }) {
  const [ingreso, setIngreso] = useState("");
  const [deuda, setDeuda] = useState("0.00");
  const [riesgo, setRiesgo] = useState<Riesgo>("BUENO");
  const [verificada, setVerificada] = useState(false);

  function enviar(e: FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const r = await evaluar(detalle.idSolicitud, {
        versionSolicitud: detalle.versionSolicitud, ingresoMensual: ingreso.trim(), deudaMensual: deuda.trim(),
        riesgo, verificada,
      });
      const texto = r.resultado === "OBSERVADO"
        ? `queda en revisión del analista (${porcentaje(r.ratio)})`
        : `resultó ${ETIQUETA[r.resultado]} (${porcentaje(r.ratio)})`;
      await onActualizado(detalle.idSolicitud, `Situación financiera registrada: la regla ${texto}.`);
    });
  }

  return (
    <Tarjeta titulo="Situación financiera" detalle="Con estos datos COREDB corre la regla de evaluación.">
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

function FormDecision({ idEvaluacion, idSolicitud, cargando, ejecutar, onActualizado }:
  PropsAccion & { idEvaluacion: string; idSolicitud: string }) {
  const [decision, setDecision] = useState<Decision>("APROBADO");
  const [comentario, setComentario] = useState("");
  const opciones: { valor: Decision; etiqueta: string }[] = [
    { valor: "APROBADO", etiqueta: "Aprobar" },
    { valor: "RECHAZADO", etiqueta: "Rechazar" },
  ];

  function enviar(e: FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const r = await decidir(idEvaluacion, { decision, comentario: comentario.trim() });
      await onActualizado(idSolicitud, `Solicitud ${ETIQUETA[r.estadoSolicitud].toLowerCase()}. El resultado vuelve a Solicitud.`);
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
          <label htmlFor="ev-comentario">Comentario</label>
          <textarea id="ev-comentario" value={comentario} onChange={(e) => setComentario(e.target.value)}
            minLength={10} maxLength={500} rows={4} required />
          <small>Solicitud lo recibe con el resultado.</small>
        </div>
        <button className="sol-button primary" type="submit" disabled={cargando}>
          {cargando ? "Guardando..." : "Registrar decisión"}
        </button>
      </form>
    </Tarjeta>
  );
}

function Revocacion({ idSolicitud, cargando, ejecutar, onActualizado }: PropsAccion & { idSolicitud: string }) {
  const [motivo, setMotivo] = useState("");

  function enviar(e: FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      await revocar(idSolicitud, { motivo: motivo.trim() });
      await onActualizado(idSolicitud, "Aprobación revocada: Desembolso ya no podrá usarla.");
    });
  }

  return (
    <Tarjeta titulo="Aprobación para Desembolso" detalle="Vigente 30 días mientras no se desembolse.">
      <form onSubmit={enviar}>
        <div className="sol-field">
          <label htmlFor="ev-motivo">Motivo de la revocación</label>
          <input id="ev-motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} minLength={10}
            maxLength={255} required />
        </div>
        <button className="sol-button secondary" type="submit" disabled={cargando}>Revocar aprobación</button>
      </form>
    </Tarjeta>
  );
}

function Resultados({ resultados }: { resultados: { configurado: boolean; ventanaDias: number; items: MensajeSol[] } | null }) {
  return (
    <section className="sol-card">
      <div className="sol-card-title">
        <div>
          <h2>Resultados para Solicitud (CR-INT-03)</h2>
          <p>
            Los resultados finales de los últimos {resultados?.ventanaDias ?? 7} días. Se reenvían en cada ciclo con
            el mismo identificador y SOL reconoce un reintento sin duplicarlo.
          </p>
        </div>
      </div>
      {resultados && !resultados.configurado && (
        <div className="ev-body">
          <div className="sol-alert neutral" role="status">
            Solicitud sigue en modo simulado: los resultados se enviarán cuando SOL active su modo real.
          </div>
        </div>
      )}
      <div className="sol-tablewrap">
        <table aria-label="Resultados para Solicitud">
          <thead>
            <tr>
              <th>Solicitud</th>
              <th>Ronda</th>
              <th>Decisión</th>
              <th>Observaciones</th>
            </tr>
          </thead>
          <tbody>
            {resultados?.items.map((m) => (
              <tr key={m.idOperacion}>
                <td>{etiquetaSolicitud(m)}</td>
                <td>{m.ronda}</td>
                <td><Estado valor={m.decision} /></td>
                <td>{m.observaciones}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Linea({ historial }: { historial: DetalleSolicitud["historial"] }) {
  if (historial.length === 0) return <div className="sol-mutedbox">Sin eventos.</div>;
  return (
    <div className="sol-timeline">
      {[...historial].reverse().map((h, i) => (
        <div key={`${h.fechaHora}-${i}`}>
          <span><Icono nombre="activa" tamano={13} /></span>
          <div>
            <strong>{ETIQUETA[h.estado] ?? h.estado}</strong>
            <p>{h.actor}{h.motivo ? ` · ${h.motivo}` : ""}</p>
            <small>{fechaHora(h.fechaHora)}</small>
          </div>
        </div>
      ))}
    </div>
  );
}
