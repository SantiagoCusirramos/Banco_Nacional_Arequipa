"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { isAxiosError } from "axios";
import { cerrarSesion, obtenerMiPerfil, type Usuario } from "@/lib/auth";
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

// Íconos de trazo, con la misma forma que los de Solicitud de Crédito.
function Icono({ nombre, tamano = 18 }: { nombre: string; tamano?: number }) {
  const trazos: Record<string, ReactNode> = {
    tarjeta: (
      <>
        <rect x="2" y="5" width="20" height="14" rx="2" />
        <path d="M2 10h20M6 15h4" />
      </>
    ),
    buscar: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="m15 15 6 6" />
      </>
    ),
    mas: <path d="M12 5v14M5 12h14" />,
    candado: (
      <>
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </>
    ),
    activa: <path d="m5 12 4 4L19 6" />,
    reloj: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    escudo: (
      <>
        <path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z" />
        <path d="M12 8v5m0 3h.01" />
      </>
    ),
    ojo: (
      <>
        <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
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

// Color de cada estado con las insignias de sol.css: verde operativa, rojo fuera de uso,
// ámbar en espera y naranja vencida.
const TONO_ESTADO: Record<string, string> = {
  ACTIVA: "aprobada",
  BLOQUEADA: "rechazada",
  CANCELADA: "rechazada",
  PENDIENTE_ACTIVACION: "en_evaluacion",
  RETENIDA: "en_evaluacion",
  VENCIDA: "observada",
};
const FUERA_DE_USO = new Set(["BLOQUEADA", "CANCELADA", "VENCIDA"]);

function EstadoTarjeta({ estado }: { estado: string }) {
  return (
    <span className={`sol-badge ${TONO_ESTADO[estado] ?? ""}`}>
      <span />
      {estado.replace("_", " ")}
    </span>
  );
}

function Chip() {
  return (
    <svg className="tj-chip" width="38" height="28" viewBox="0 0 38 28" aria-hidden="true">
      <rect x="0.5" y="0.5" width="37" height="27" rx="5" fill="#d9b765" stroke="#b8963f" />
      <path d="M0 10h12m14 0h12M0 18h12m14 0h12M12 0v28m14-28v28M12 14h14" stroke="#a5843a" strokeWidth="1" fill="none" />
    </svg>
  );
}

/** La tarjeta como se ve impresa: número enmascarado, titular y vencimiento MM/AA. */
function Plastico({ numero, titular, vence, estado, grande = false }:
  { numero: string; titular: string; vence: string; estado?: string; grande?: boolean }) {
  const apagada = estado !== undefined && FUERA_DE_USO.has(estado);
  return (
    <div className={`tj-plastico ${apagada ? "apagada" : ""} ${grande ? "grande" : ""}`}>
      {estado && <div className="tj-estado"><EstadoTarjeta estado={estado} /></div>}
      <div className="tj-plastico-top">
        <div className="tj-marca">BNA<small>DÉBITO</small></div>
      </div>
      <Chip />
      <div className="tj-numero">{numero}</div>
      <div className="tj-plastico-bottom">
        <div className="tj-dato"><small>TITULAR</small><strong>{titular || "CÓDIGO DEL CLIENTE"}</strong></div>
        <div className="tj-dato"><small>VENCE</small><strong>{vence}</strong></div>
      </div>
    </div>
  );
}

function Resumen({ tarjetas }: { tarjetas: Tarjeta[] }) {
  const contar = (...estados: string[]) => tarjetas.filter((t) => estados.includes(t.estado_tarjeta)).length;
  const cifras = [
    { etiqueta: "Total de tarjetas", valor: tarjetas.length, icono: "tarjeta", tono: "blue" },
    { etiqueta: "Activas", valor: contar("ACTIVA"), icono: "activa", tono: "green" },
    { etiqueta: "En espera", valor: contar("PENDIENTE_ACTIVACION", "RETENIDA"), icono: "reloj", tono: "gold" },
    { etiqueta: "Fuera de uso", valor: contar("BLOQUEADA", "CANCELADA", "VENCIDA"), icono: "candado", tono: "red" },
  ];
  return (
    <div className="sol-stats" style={{ marginBottom: "24px" }}>
      {cifras.map((c) => (
        <div className="sol-stat" key={c.etiqueta}>
          <div>
            <small>{c.etiqueta}</small>
            <strong>{c.valor}</strong>
          </div>
          <span className={`sol-stat-icon ${c.tono}`}><Icono nombre={c.icono} /></span>
        </div>
      ))}
    </div>
  );
}

const esSesionInvalida = (err: unknown) => isAxiosError(err) && err.response?.status === 401;

export default function TarjetasPage() {
  const [tab, setTab] = useState<Pestana>("cliente");
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  // Sin sesión o con la sesión vencida se pide iniciarla, en vez de mostrar el error técnico.
  const [sinSesion, setSinSesion] = useState(false);
  const [loading, setLoading] = useState(false);

  // Quién trabaja en la pantalla; sin sesión, el pie del menú queda vacío.
  useEffect(() => {
    obtenerMiPerfil().then(setUsuario).catch((err) => {
      setUsuario(null);
      if (esSesionInvalida(err)) setSinSesion(true);
    });
  }, []);
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
  // Llave de idempotencia de esta emisión: se mantiene si se repite el mismo envío (doble
  // clic, reintento tras un error) y cambia al editar un dato o al emitir con éxito.
  const [llaveEmision, setLlaveEmision] = useState(() => crypto.randomUUID());
  const editarEmision = (cambiar: (valor: string) => void) => (valor: string) => {
    cambiar(valor);
    setLlaveEmision(crypto.randomUUID());
  };

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
      if (esSesionInvalida(err)) setSinSesion(true);
      else setNotice({ text: mensajeDeError(err), error: true });
    } finally {
      setLoading(false);
    }
  }

  function irA(pestana: Pestana) {
    setTab(pestana);
    setNotice(null);
  }

  function mostrar(tarjeta: Tarjeta) {
    setTarjetaActual(tarjeta);
    setIdConsulta(tarjeta.id_tarjeta);
    setTab("consulta");
  }

  function prepararCambio(tarjeta: Tarjeta, nuevo: EstadoPedible = "BLOQUEADA") {
    setIdEstado(tarjeta.id_tarjeta);
    setEstado(nuevo);
    irA("estado");
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
      }, llaveEmision);
      setLlaveEmision(crypto.randomUUID());
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

  const navegacion: { id: Pestana; etiqueta: string; icono: string }[] = [
    { id: "cliente", etiqueta: "Tarjetas del cliente", icono: "tarjeta" },
    { id: "consulta", etiqueta: "Consultar tarjeta", icono: "buscar" },
    { id: "emision", etiqueta: "Emitir tarjeta", icono: "mas" },
    { id: "estado", etiqueta: "Bloqueos y estados", icono: "candado" },
  ];
  const vencePrevia = vencimiento ? `${vencimiento.slice(5, 7)}/${vencimiento.slice(2, 4)}` : "MM/AA";

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
          {navegacion.map((n) => (
            <button key={n.id} className={tab === n.id ? "active" : ""} onClick={() => irA(n.id)}>
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
            <span>Tarjetas</span>
            <b>/</b>{navegacion.find((n) => n.id === tab)?.etiqueta}
          </div>
          <div className="sol-topbar-right">
            <span className="sol-demo-pill">Requiere sesión iniciada</span>
            <Link href="/" style={{ color: "#15324f", fontWeight: 600, textDecoration: "none", fontSize: "13px" }}>Volver al Home Banking</Link>
          </div>
        </header>

        <main className="sol-main">
          <div className="sol-heading">
            <div>
              <h1>Tarjetas de débito</h1>
            </div>
            {tab !== "emision" && (
              <button className="sol-button primary" onClick={() => irA("emision")}>
                <Icono nombre="mas" />
                Nueva tarjeta
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

          {notice && (
            <div role={notice.error ? "alert" : "status"} className={`sol-alert ${notice.error ? "error" : "success"}`}>
              {notice.text}
              <button onClick={() => setNotice(null)} aria-label="Cerrar aviso"><Icono nombre="cerrar" tamano={14} /></button>
            </div>
          )}

          {tab === "cliente" && (
            <>
              <section className="sol-card" style={{ marginBottom: "24px" }}>
                <div className="sol-card-title">
                  <div>
                    <h2>Tarjetas de un cliente</h2>
                    <p>Las tarjetas emitidas al cliente, de la más reciente a la más antigua.</p>
                  </div>
                </div>
                <form onSubmit={buscarDeCliente} className="sol-toolbar">
                  <input
                    aria-label="Código del cliente"
                    placeholder="Código del cliente"
                    value={codCliente}
                    onChange={(e) => setCodCliente(e.target.value)}
                    maxLength={12}
                    required
                    style={{ flex: 1 }}
                  />
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    <Icono nombre="buscar" />
                    {loading ? "Buscando..." : "Ver tarjetas"}
                  </button>
                </form>
              </section>

              {tarjetas && tarjetas.length === 0 && (
                <section className="sol-card">
                  <div className="sol-empty" role="status">
                    <span><Icono nombre="tarjeta" tamano={26} /></span>
                    <h3>El cliente no tiene tarjetas.</h3>
                    <p>Puedes emitirle una vinculada a una de sus cuentas.</p>
                    <button className="sol-button secondary" onClick={() => { editarEmision(setClienteEmision)(codCliente.trim().toUpperCase()); irA("emision"); }}>
                      <Icono nombre="mas" />
                      Emitir tarjeta
                    </button>
                  </div>
                </section>
              )}

              {tarjetas && tarjetas.length > 0 && (
                <>
                  <Resumen tarjetas={tarjetas} />
                  <ul className="tj-grid" aria-label="Tarjetas del cliente" style={{ listStyle: "none", padding: 0, margin: 0 }}>
                    {tarjetas.map((t) => (
                      <li key={t.id_tarjeta} className="tj-item">
                        <Plastico numero={t.numero_enmascarado} titular={t.cod_cliente} vence={t.vencimiento_mm_aa} estado={t.estado_tarjeta} />
                        <div className="tj-item-actions">
                          <button className="sol-button secondary" type="button" onClick={() => mostrar(t)}>
                            <Icono nombre="ojo" tamano={16} />
                            Ver detalle
                          </button>
                          <button className="sol-button secondary" type="button" onClick={() => prepararCambio(t)}>
                            <Icono nombre="candado" tamano={16} />
                            Cambiar estado
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}

          {tab === "consulta" && (
            <section className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Ver una tarjeta en específico</h2>
                  <p>Consulta el estado y las fechas de una tarjeta por su identificador.</p>
                </div>
              </div>
              <form onSubmit={consultar} className="sol-toolbar">
                <input
                  aria-label="Identificador de la tarjeta"
                  placeholder="Identificador de la tarjeta (UUID)"
                  value={idConsulta}
                  onChange={(e) => setIdConsulta(e.target.value)}
                  required
                  style={{ flex: 1 }}
                />
                <button className="sol-button primary" type="submit" disabled={loading}>
                  <Icono nombre="buscar" />
                  {loading ? "Buscando..." : "Ver tarjeta"}
                </button>
              </form>
              {tarjetaActual && (
                <div className="tj-detalle">
                  <Plastico grande numero={tarjetaActual.numero_enmascarado} titular={tarjetaActual.cod_cliente}
                    vence={tarjetaActual.vencimiento_mm_aa} estado={tarjetaActual.estado_tarjeta} />
                  <div>
                    <h3 style={{ marginTop: 0 }}>Tarjeta {tarjetaActual.numero_enmascarado}</h3>
                    <dl className="tj-datos">
                      <div><dt>Estado</dt><dd><EstadoTarjeta estado={tarjetaActual.estado_tarjeta} /></dd></div>
                      <div><dt>Cliente</dt><dd>{tarjetaActual.cod_cliente}</dd></div>
                      <div><dt>Emisión</dt><dd>{tarjetaActual.fecha_emision}</dd></div>
                      <div><dt>Vencimiento</dt><dd>{tarjetaActual.vencimiento_mm_aa} ({tarjetaActual.fecha_vencimiento})</dd></div>
                      <div><dt>BIN</dt><dd>{tarjetaActual.bin}</dd></div>
                      <div><dt>Identificador</dt><dd style={{ fontSize: "12px" }}>{tarjetaActual.id_tarjeta}</dd></div>
                    </dl>
                    <div className="tj-item-actions" style={{ marginTop: "24px", maxWidth: "420px" }}>
                      {tarjetaActual.estado_tarjeta === "PENDIENTE_ACTIVACION" && (
                        <button className="sol-button primary" type="button" onClick={() => prepararCambio(tarjetaActual, "ACTIVA")}>
                          <Icono nombre="activa" tamano={16} />
                          Activar
                        </button>
                      )}
                      {tarjetaActual.estado_tarjeta === "ACTIVA" && (
                        <button className="sol-button secondary" type="button" onClick={() => prepararCambio(tarjetaActual)}>
                          <Icono nombre="candado" tamano={16} />
                          Bloquear
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

          {tab === "emision" && (
            <section className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Emitir tarjeta de débito</h2>
                  <p>La tarjeta queda pendiente de activación y vinculada a una cuenta del cliente.</p>
                </div>
              </div>
              <div className="tj-emision">
                <form onSubmit={emitir} className="sol-form-grid">
                  <div className="sol-field">
                    <label htmlFor="emision-cliente">Código del cliente</label>
                    <input id="emision-cliente" value={clienteEmision} onChange={(e) => editarEmision(setClienteEmision)(e.target.value)} required maxLength={12} />
                  </div>
                  <div className="sol-field">
                    <label htmlFor="emision-cuenta">Cuenta a vincular</label>
                    <input id="emision-cuenta" value={cuentaEmision} onChange={(e) => editarEmision(setCuentaEmision)(e.target.value)} required maxLength={20} placeholder="Número de cuenta" />
                  </div>
                  <div className="sol-field">
                    <label htmlFor="emision-bin">BIN</label>
                    <select id="emision-bin" value={bin} onChange={(e) => editarEmision(setBin)(e.target.value)}>
                      {BINES.map((opcion) => <option key={opcion} value={opcion}>{opcion}</option>)}
                    </select>
                  </div>
                  <div className="sol-field">
                    <label htmlFor="emision-vencimiento">Fecha de vencimiento</label>
                    <input id="emision-vencimiento" type="date" value={vencimiento} onChange={(e) => editarEmision(setVencimiento)(e.target.value)} required />
                  </div>
                  <div style={{ gridColumn: "1 / -1" }}>
                    <button className="sol-button primary" type="submit" disabled={loading}>
                      <Icono nombre="tarjeta" />
                      {loading ? "Emitiendo..." : "Emitir tarjeta"}
                    </button>
                  </div>
                </form>
                <div className="tj-vista-previa" aria-hidden="true">
                  <p>Vista previa</p>
                  <Plastico numero={`${bin.slice(0, 4)} ${bin.slice(4)}** **** ••••`} titular={clienteEmision.trim().toUpperCase()} vence={vencePrevia} />
                </div>
              </div>
              <div className="tj-nota">
                <Icono nombre="escudo" />
                <span>El número completo de la tarjeta nunca pasa por esta pantalla: el módulo envía un token en su lugar y solo se conservan el BIN y los últimos cuatro dígitos.</span>
              </div>
            </section>
          )}

          {tab === "estado" && (
            <section className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Bloquear o cambiar el estado</h2>
                  <p>Cada cambio queda en el historial de la tarjeta, con su motivo.</p>
                </div>
              </div>
              <form onSubmit={cambiar} className="sol-form-grid" style={{ padding: "0 24px 24px" }}>
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
                <div style={{ gridColumn: "1 / -1" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    <Icono nombre="candado" />
                    {loading ? "Aplicando..." : "Aplicar cambio"}
                  </button>
                </div>
              </form>
              <div className="tj-nota">
                <Icono nombre="escudo" />
                <span>El desbloqueo (de BLOQUEADA a ACTIVA) lo hace el módulo de Seguridad y aquí se rechaza. ANULADA cancela la tarjeta de forma definitiva.</span>
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
