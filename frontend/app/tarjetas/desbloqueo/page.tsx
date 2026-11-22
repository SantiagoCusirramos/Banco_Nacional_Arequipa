"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { isAxiosError } from "axios";
import { cerrarSesion, obtenerMiPerfil, type Usuario } from "@/lib/auth";
import {
  PERMISO_DESBLOQUEO, desbloquearTarjeta, fechaHora, fichaDeTarjeta, mensajeParaPersonal, nombreEstado, nombreOrigen,
  tarjetasDelCliente, tipoDeError,
  type Desbloqueo, type FichaTarjeta, type TarjetaSeguridad,
} from "@/lib/seguridad";

// Desbloqueo de tarjetas para el personal autorizado (OPERADOR y ADMINISTRADOR: quienes tienen
// BLOQUEAR_TARJETA, decisión 22 de Documents/decisiones-del-equipo.md). Lo hace Seguridad: en la
// base solo su cuenta puede desbloquear, y la persona queda como responsable en la bitácora.
// El cliente nunca desbloquea: el Home Banking solo bloquea.

type Aviso = { texto: string; error: boolean };

const MOTIVO_MINIMO = 10;
const ROLES: Record<string, string> = {
  ADMINISTRADOR: "Administrador", OPERADOR: "Operador", ASESOR: "Asesor", ANALISTA: "Analista", AUDITOR: "Auditor",
};
const nombreRol = (rol: string) => ROLES[rol] ?? "Usuario del banco";
const TONO: Record<string, string> = { ACTIVA: "aprobada", BLOQUEADA: "rechazada", RETENIDA: "rechazada" };
const fecha = (iso: string) => iso.slice(0, 10).split("-").reverse().join("/");

function Estado({ estado }: { estado: string }) {
  return <span className={`sol-badge ${TONO[estado] ?? ""}`}><span />{nombreEstado(estado)}</span>;
}

/** Lo que devolvió el servidor es un desbloqueo de esta tarjeta, completo. */
function esDesbloqueoValido(r: Desbloqueo | undefined, idTarjeta: string): r is Desbloqueo {
  const c = r?.cambio;
  return !!r && !!c && r.id_tarjeta === idTarjeta && r.estado_tarjeta === "ACTIVA" && c.estado_nuevo === "ACTIVA"
    && Number.isInteger(c.id_historial) && c.id_historial > 0 && !!c.fecha_hora && !!c.actor && !!c.estado_anterior;
}

export default function DesbloqueoPage() {
  const [usuario, setUsuario] = useState<Usuario | null | undefined>(undefined);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [buscando, setBuscando] = useState(false);

  const [codCliente, setCodCliente] = useState("");
  const [idTarjeta, setIdTarjeta] = useState("");
  const [lista, setLista] = useState<TarjetaSeguridad[] | null>(null);
  const [ficha, setFicha] = useState<FichaTarjeta | null>(null);

  const [motivo, setMotivo] = useState("");
  const [verificado, setVerificado] = useState(false);
  const [errorForm, setErrorForm] = useState("");
  const [confirmando, setConfirmando] = useState(false);
  const [digitos, setDigitos] = useState("");
  const [enviando, setEnviando] = useState(false);
  const enCurso = useRef(false);
  const [comprobante, setComprobante] = useState<Desbloqueo | null>(null);

  useEffect(() => {
    obtenerMiPerfil().then(setUsuario).catch(() => setUsuario(null));
  }, []);

  const puede = !!usuario?.acciones?.includes(PERMISO_DESBLOQUEO);

  function limpiarDecision() {
    setMotivo("");
    setVerificado(false);
    setErrorForm("");
    setConfirmando(false);
    setDigitos("");
  }

  async function abrir(id: string) {
    setBuscando(true);
    setAviso(null);
    setComprobante(null);
    limpiarDecision();
    try {
      setFicha(await fichaDeTarjeta(id));
    } catch (err) {
      setFicha(null);
      setAviso({ texto: mensajeParaPersonal(err, "tarjeta"), error: true });
    } finally {
      setBuscando(false);
    }
  }

  // Vuelve a leer la tarjeta sin borrar el aviso: tras un desbloqueo dudoso o rechazado.
  async function releer(id: string) {
    try {
      setFicha(await fichaDeTarjeta(id));
    } catch {
      setFicha(null);
    }
  }

  async function buscarCliente(e: React.FormEvent) {
    e.preventDefault();
    const codigo = codCliente.trim().toUpperCase();
    if (!codigo) return;
    setBuscando(true);
    setAviso(null);
    setFicha(null);
    setComprobante(null);
    try {
      setLista(await tarjetasDelCliente(codigo));
    } catch (err) {
      setLista(null);
      setAviso({ texto: mensajeParaPersonal(err, "cliente"), error: true });
    } finally {
      setBuscando(false);
    }
  }

  function buscarTarjeta(e: React.FormEvent) {
    e.preventDefault();
    const id = idTarjeta.trim();
    if (!id) return;
    setLista(null);
    void abrir(id);
  }

  function revisar(e: React.FormEvent) {
    e.preventDefault();
    if (motivo.trim().length < MOTIVO_MINIMO) {
      setErrorForm(`Escribe el motivo del desbloqueo (al menos ${MOTIVO_MINIMO} caracteres).`);
      return;
    }
    if (!verificado) {
      setErrorForm("Confirma que verificaste la identidad del titular.");
      return;
    }
    setErrorForm("");
    setDigitos("");
    setConfirmando(true);
  }

  async function desbloquear() {
    if (!ficha || enCurso.current || digitos !== ficha.ultimos4) return;
    enCurso.current = true;
    setEnviando(true);
    setAviso(null);
    const id = ficha.id_tarjeta;
    try {
      const r = await desbloquearTarjeta(id, motivo.trim());
      setConfirmando(false);
      if (!esDesbloqueoValido(r, id)) {
        setAviso({ texto: "No se pudo confirmar el desbloqueo con los datos del servidor. Revisa el estado de la "
          + "tarjeta antes de intentarlo de nuevo.", error: true });
        await releer(id);
        return;
      }
      setComprobante(r);
      setFicha(null);
      setLista(null);
      limpiarDecision();
    } catch (err) {
      setConfirmando(false);
      if (isAxiosError(err) && err.response?.status === 401) setUsuario(null);
      setAviso({ texto: mensajeParaPersonal(err, "desbloqueo"), error: true });
      const tipo = tipoDeError(err);
      if (tipo === "no_bloqueada" || tipo === "sin_respuesta" || tipo === "otro") await releer(id);
    } finally {
      enCurso.current = false;
      setEnviando(false);
    }
  }

  function otraTarjeta() {
    setComprobante(null);
    setFicha(null);
    setLista(null);
    setIdTarjeta("");
    setAviso(null);
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
        <nav aria-label="Navegación Tarjetas" style={{ marginTop: "32px" }}>
          <p>TARJETAS DE DÉBITO</p>
          <Link href="/tarjetas" className="tj-enlace-nav">Tarjetas</Link>
          <span className="tj-enlace-nav active" aria-current="page">Desbloqueo de tarjetas</span>
        </nav>
        {usuario && (
          <div className="sol-sidebar-bottom">
            <div className="sol-profile">
              <span className="sol-avatar">{usuario.nombre.trim()[0]?.toUpperCase()}</span>
              <div>
                <strong>{usuario.nombre}</strong>
                <small>{nombreRol(usuario.rol)}</small>
              </div>
            </div>
          </div>
        )}
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div><span>Tarjetas</span><b>/</b>Desbloqueo</div>
          <div className="sol-topbar-right">
            <Link href="/" style={{ color: "#15324f", fontWeight: 600, textDecoration: "none", fontSize: "13px" }}>Volver al portal</Link>
          </div>
        </header>

        <main className="sol-main">
          <div className="sol-heading">
            <div>
              <h1>Desbloqueo de tarjetas</h1>
              <p className="tj-sub">Devuelve al uso una tarjeta bloqueada o retenida, después de verificar la identidad del titular.</p>
            </div>
          </div>

          {usuario === undefined && <p role="status">Comprobando tu sesión…</p>}

          {usuario === null && (
            <div role="alert" className="sol-alert error">
              Tu sesión no está iniciada o ya venció.
              <Link href="/login" onClick={cerrarSesion} style={{ marginLeft: "auto", fontWeight: 600, color: "inherit" }}>
                Iniciar sesión
              </Link>
            </div>
          )}

          {usuario && !puede && (
            <section className="sol-card">
              <div className="sol-empty" role="status">
                <h3>Esta pantalla es para operadores y administradores.</h3>
                <p>Tu rol ({nombreRol(usuario.rol)}) no puede desbloquear tarjetas. Si el cliente lo necesita, deriva el caso a un operador.</p>
                <Link className="sol-button secondary" href="/">Volver al portal</Link>
              </div>
            </section>
          )}

          {usuario && puede && (
            <>
              {aviso && (
                <div role={aviso.error ? "alert" : "status"} className={`sol-alert ${aviso.error ? "error" : "success"}`}>
                  {aviso.texto}
                </div>
              )}

              {comprobante ? (
                <Comprobante r={comprobante} onOtra={otraTarjeta} />
              ) : (
                <>
                  <section className="sol-card" style={{ marginBottom: "24px" }}>
                    <div className="sol-card-title">
                      <div>
                        <h2>1. Buscar la tarjeta</h2>
                        <p>Por el código del cliente o por el número de identificación de la tarjeta.</p>
                      </div>
                    </div>
                    <div className="tj-busquedas">
                      <form onSubmit={buscarCliente} className="sol-toolbar">
                        <label htmlFor="dt-cliente" className="tj-oculto">Código del cliente</label>
                        <input id="dt-cliente" placeholder="Código del cliente (ej. CLI000000003)" value={codCliente}
                          onChange={(e) => setCodCliente(e.target.value)} maxLength={12} style={{ flex: 1 }} />
                        <button className="sol-button primary" type="submit" disabled={buscando}>Buscar tarjetas</button>
                      </form>
                      <form onSubmit={buscarTarjeta} className="sol-toolbar">
                        <label htmlFor="dt-id" className="tj-oculto">Número de identificación de la tarjeta</label>
                        <input id="dt-id" placeholder="Número de identificación de la tarjeta" value={idTarjeta}
                          onChange={(e) => setIdTarjeta(e.target.value)} maxLength={36} style={{ flex: 1 }} />
                        <button className="sol-button secondary" type="submit" disabled={buscando}>Buscar tarjeta</button>
                      </form>
                    </div>
                  </section>

                  {lista && lista.length === 0 && (
                    <section className="sol-card"><div className="sol-empty" role="status"><h3>El cliente no tiene tarjetas.</h3></div></section>
                  )}

                  {lista && lista.length > 0 && !ficha && (
                    <section className="sol-card" style={{ marginBottom: "24px" }}>
                      <div className="sol-card-title"><div><h2>Tarjetas del cliente {lista[0].cod_cliente}</h2></div></div>
                      <ul className="tj-lista" aria-label="Tarjetas del cliente">
                        {lista.map((t) => (
                          <li key={t.id_tarjeta}>
                            <span className="tj-numero">{t.numero_enmascarado}</span>
                            <Estado estado={t.estado_tarjeta} />
                            <span className="tj-cuenta">Vence {fecha(t.fecha_vencimiento)}</span>
                            <button className="sol-button secondary" type="button" disabled={buscando}
                              aria-label={`Revisar la tarjeta terminada en ${t.ultimos4}`} onClick={() => abrir(t.id_tarjeta)}>
                              Revisar
                            </button>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {ficha && (
                    <section className="sol-card" aria-label={`Tarjeta ${ficha.numero_enmascarado}`}>
                      <div className="sol-card-title">
                        <div>
                          <h2>2. Revisar la tarjeta</h2>
                          <p>Tarjeta {ficha.numero_enmascarado} del cliente {ficha.cod_cliente}.</p>
                        </div>
                        <Estado estado={ficha.estado_tarjeta} />
                      </div>
                      <dl className="tj-datos" style={{ padding: "0 24px 20px" }}>
                        <div><dt>Cliente</dt><dd>{ficha.cod_cliente}</dd></div>
                        <div><dt>Cuenta</dt><dd>{ficha.num_cuenta ?? "Sin cuenta vinculada"}</dd></div>
                        <div><dt>Vence</dt><dd>{fecha(ficha.fecha_vencimiento)}</dd></div>
                        <div><dt>Estado</dt><dd>{nombreEstado(ficha.estado_tarjeta)}</dd></div>
                      </dl>

                      {ficha.desbloqueable && (
                        <section className="tj-bloqueo" aria-label="Bloqueo vigente">
                          <h3>Por qué está {nombreEstado(ficha.estado_tarjeta).toLowerCase()}</h3>
                          {ficha.bloqueo ? (
                            <dl className="tj-datos">
                              <div style={{ gridColumn: "1 / -1" }}><dt>Motivo</dt><dd>{ficha.bloqueo.motivo || "No se registró un motivo"}</dd></div>
                              <div><dt>Quién la bloqueó</dt><dd>{nombreOrigen(ficha.bloqueo.origen)}</dd></div>
                              <div><dt>Fecha y hora</dt><dd>{fechaHora(ficha.bloqueo.fecha_hora)}</dd></div>
                            </dl>
                          ) : <p>No hay un registro del bloqueo en el historial de la tarjeta.</p>}
                        </section>
                      )}

                      {!ficha.desbloqueable && (
                        <div className="tj-nota">
                          <span>
                            Esta tarjeta no está bloqueada (estado: {nombreEstado(ficha.estado_tarjeta)}); no hay nada que desbloquear.
                            {ficha.estado_tarjeta !== "ACTIVA" && " Una tarjeta anulada o vencida no vuelve a activarse: se emite una nueva."}
                          </span>
                        </div>
                      )}

                      {ficha.historial.length > 0 && (
                        <details className="tj-historial">
                          <summary>Últimos cambios de estado</summary>
                          <table>
                            <thead><tr><th>Fecha y hora</th><th>Estado</th><th>Quién</th><th>Motivo</th></tr></thead>
                            <tbody>
                              {ficha.historial.map((h) => (
                                <tr key={h.id_historial}>
                                  <td>{fechaHora(h.fecha_hora)}</td><td>{nombreEstado(h.estado_nuevo)}</td>
                                  <td>{nombreOrigen(h.origen)}</td><td>{h.motivo || "—"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </details>
                      )}

                      {ficha.desbloqueable && (
                        <form onSubmit={revisar} className="sol-form-grid" style={{ padding: "8px 24px 24px" }} noValidate>
                          <h3 style={{ gridColumn: "1 / -1", margin: 0 }}>3. Decidir el desbloqueo</h3>
                          <div className="sol-field" style={{ gridColumn: "1 / -1" }}>
                            <label htmlFor="dt-motivo">Motivo del desbloqueo</label>
                            <input id="dt-motivo" value={motivo} maxLength={255} onChange={(e) => setMotivo(e.target.value)}
                              placeholder="Ej.: el titular se presentó con su DNI y confirmó que recuperó la tarjeta"
                              aria-describedby={errorForm ? "dt-error" : undefined} />
                          </div>
                          <label className="tj-check" style={{ gridColumn: "1 / -1" }}>
                            <input type="checkbox" checked={verificado} onChange={(e) => setVerificado(e.target.checked)} />
                            Verifiqué la identidad del titular con su documento de identidad
                          </label>
                          {errorForm && <p id="dt-error" className="tj-error" style={{ gridColumn: "1 / -1" }}>{errorForm}</p>}
                          <div style={{ gridColumn: "1 / -1" }}>
                            <button className="sol-button primary" type="submit">Revisar desbloqueo</button>
                          </div>
                        </form>
                      )}
                    </section>
                  )}
                </>
              )}
            </>
          )}
        </main>
      </div>

      {confirmando && ficha && (
        <div className="tj-velo" onKeyDown={(e) => { if (e.key === "Escape" && !enviando) setConfirmando(false); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="dt-confirmar-titulo" className="tj-dialogo">
            <h2 id="dt-confirmar-titulo">Confirmar el desbloqueo</h2>
            <p>
              Vas a desbloquear la tarjeta <b>{ficha.numero_enmascarado}</b> del cliente <b>{ficha.cod_cliente}</b>.
              La tarjeta volverá a aceptarse en el cajero y en los pagos. El desbloqueo queda registrado a tu nombre.
            </p>
            <p><b>Motivo:</b> {motivo.trim()}</p>
            <div className="sol-field">
              <label htmlFor="dt-digitos">Últimos 4 dígitos de la tarjeta</label>
              <input id="dt-digitos" inputMode="numeric" maxLength={4} autoFocus value={digitos}
                onChange={(e) => setDigitos(e.target.value.replace(/\D/g, ""))} />
            </div>
            <div className="tj-dialogo-acciones">
              <button className="sol-button secondary" type="button" disabled={enviando} onClick={() => setConfirmando(false)}>Cancelar</button>
              <button className="sol-button primary" type="button" disabled={enviando || digitos !== ficha.ultimos4}
                aria-busy={enviando} onClick={desbloquear}>
                Desbloquear tarjeta
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Comprobante({ r, onOtra }: { r: Desbloqueo; onOtra: () => void }) {
  return (
    <section className="sol-card tj-comprobante" aria-label="Comprobante de desbloqueo">
      <div className="sol-card-title">
        <div>
          <h2>Tarjeta desbloqueada</h2>
          <p>Ya se acepta en el cajero y en los pagos. El desbloqueo quedó registrado en la bitácora del banco.</p>
        </div>
        <Estado estado={r.estado_tarjeta} />
      </div>
      <dl className="tj-datos" style={{ padding: "0 24px 20px" }}>
        <div><dt>Número de operación</dt><dd>{r.cambio.id_historial}</dd></div>
        <div><dt>Fecha y hora</dt><dd>{fechaHora(r.cambio.fecha_hora)}</dd></div>
        <div><dt>Tarjeta</dt><dd>{r.bin}******{r.ultimos4}</dd></div>
        <div><dt>Cliente</dt><dd>{r.cod_cliente}</dd></div>
        <div><dt>Estado anterior</dt><dd>{nombreEstado(r.cambio.estado_anterior)}</dd></div>
        <div><dt>Estado actual</dt><dd>{nombreEstado(r.estado_tarjeta)}</dd></div>
        <div><dt>Desbloqueada por</dt><dd>{r.cambio.actor}</dd></div>
        <div style={{ gridColumn: "1 / -1" }}><dt>Motivo</dt><dd>{r.cambio.motivo}</dd></div>
      </dl>
      <div className="tj-dialogo-acciones" style={{ padding: "0 24px 24px" }}>
        <button className="sol-button secondary" type="button" onClick={() => window.print()}>Imprimir</button>
        <button className="sol-button primary" type="button" onClick={onOtra}>Desbloquear otra tarjeta</button>
      </div>
    </section>
  );
}
