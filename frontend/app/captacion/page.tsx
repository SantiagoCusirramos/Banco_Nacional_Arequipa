"use client";

import { Suspense, useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { isAxiosError } from "axios";
import { cerrarSesion, obtenerMiPerfil, type Usuario } from "@/lib/auth";
import { rutaActual, urlLoginConVolver } from "@/lib/continuidad";
import { AvisoPermiso } from "@/app/components/AvisoPermiso";
import { BarraNavegacion } from "@/app/components/BarraNavegacion";
import { pantallaPorHref, puedeVerPantalla } from "@/lib/pantallas";
import {
  CANALES, CENTRALES, CONSENTIMIENTOS, TIPOS_DOCUMENTO, VALIDACIONES,
  abrirCaso, bandeja, calcularPerfil, cambiarEstado, consultarCentral, enviarOtp, expediente,
  faltantesDelError, habilitar, mensajeDeError, referencia, registrarConsentimientos, registrarSolicitante,
  validacionManual, validar, verificarOtp,
  type CasoEnBandeja, type Expediente, type NuevoSolicitante, type OtpEnviado, type Referencia,
} from "@/lib/captacion";

type Vista = "bandeja" | "nuevo" | "caso";
type Aviso = { text: string; error: boolean; faltantes?: string[] };

// Insignias de sol.css: verde aprobada, rojo rechazada, ámbar en evaluación, naranja observada.
const TONO: Record<string, string> = {
  INICIADO: "", EN_VALIDACION: "en_evaluacion", OBSERVADO: "observada", APROBADO: "aprobada",
  HABILITADO: "aprobada", RECHAZADO: "rechazada", REVOCADO: "rechazada",
  NORMAL: "aprobada", CPP: "observada", DEFICIENTE: "rechazada", DUDOSO: "rechazada", PERDIDA: "rechazada",
  BAJO: "aprobada", MEDIO: "en_evaluacion", ALTO: "observada", MUY_ALTO: "rechazada",
};
const ESTADOS_BANDEJA = ["EN_VALIDACION", "OBSERVADO", "APROBADO", "HABILITADO", "RECHAZADO"];

function Insignia({ valor, texto }: { valor: string; texto?: string }) {
  return <span className={`sol-badge ${TONO[valor] ?? ""}`}><span />{texto ?? valor.replaceAll("_", " ")}</span>;
}

function Icono({ nombre, tamano = 18 }: { nombre: string; tamano?: number }) {
  const trazos: Record<string, ReactNode> = {
    bandeja: <><path d="M3 13h5l2 3h4l2-3h5" /><path d="M5 5h14l2 8v6H3v-6Z" /></>,
    persona: <><circle cx="12" cy="8" r="4" /><path d="M4 21c1-4 4-6 8-6s7 2 8 6" /></>,
    escudo: <><path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z" /><path d="m8 12 3 3 5-6" /></>,
    salir: <path d="M9 3H3v18h6M12 12h9m-4-4 4 4-4 4" />,
    cerrar: <path d="M18 6 6 18M6 6l12 12" />,
  };
  return (
    <svg width={tamano} height={tamano} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{trazos[nombre]}</svg>
  );
}

const fecha = (iso: string | null) => {
  if (!iso) return "—";
  // COREDB serializa con offset (+00:00); los mocks, sin zona. Añadir «Z» a un offset parte la fecha.
  const valor = /[+-]\d{2}:\d{2}$/.test(iso) || iso.endsWith("Z") ? iso : `${iso}Z`;
  const instante = new Date(valor);
  if (Number.isNaN(instante.getTime())) return "—";
  return instante.toLocaleString("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
};
const soles = (v: string | number) => new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(Number(v));
const nombre = (s: { nombres: string; apellido_paterno: string; apellido_materno: string | null }) =>
  `${s.nombres} ${s.apellido_paterno}${s.apellido_materno ? ` ${s.apellido_materno}` : ""}`;
const ultimos = <T extends { tipo: string }>(items: T[]) => {
  const m = new Map<string, T>();
  for (const i of items) m.set(i.tipo, i);
  return m;
};
const azar = (n: number) => Math.floor(Math.random() * n);

// Documentos del simulador de CAPTACION (backend/CAPTACION/proveedores.py).
const DEMOS = [
  { etiqueta: "Perfil normal", final: "1" },
  { etiqueta: "Riesgo muy alto", final: "9" },
  { etiqueta: "Lista restrictiva", doc: "99999999" },
  { etiqueta: "PEP", doc: "88888880" },
];

function datosDemo(d: { final?: string; doc?: string }): NuevoSolicitante {
  const doc = d.doc ?? `4${String(azar(1_000_000)).padStart(6, "0")}${d.final}`;
  return {
    tipo_documento: "DNI", numero_documento: doc, nombres: "Rosa", apellido_paterno: "Huamán", apellido_materno: "Ccori",
    celular: `9${String(azar(1e8)).padStart(8, "0")}`, correo: `rosa.${doc}.${azar(1e6)}@example.com`,
  };
}

function CaptacionPageInner() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [sinSesion, setSinSesion] = useState(false);
  const [vista, setVista] = useState<Vista>("bandeja");
  const [casos, setCasos] = useState<CasoEnBandeja[]>([]);
  const [filtro, setFiltro] = useState("");
  const [exp, setExp] = useState<Expediente | null>(null);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const fallo = useCallback((err: unknown) => {
    if (isAxiosError(err) && err.response?.status === 401) setSinSesion(true);
    setAviso({ text: mensajeDeError(err), error: true, faltantes: faltantesDelError(err) });
  }, []);

  const acciones = usuario?.acciones ?? [];
  const permitido = puedeVerPantalla(acciones, "/captacion");

  useEffect(() => {
    if (!permitido) return;
    bandeja(filtro || undefined).then(setCasos).catch(fallo);
  }, [fallo, filtro, permitido]);

  const cargarBandeja = useCallback(async (estado = filtro) => {
    if (!permitido) return;
    try { setCasos(await bandeja(estado || undefined)); } catch (err) { fallo(err); }
  }, [filtro, fallo, permitido]);

  const abrir = useCallback(async (idCaso: string) => {
    try {
      setExp(await expediente(idCaso));
      setVista("caso");
    } catch (err) { fallo(err); }
  }, [fallo]);

  useEffect(() => {
    obtenerMiPerfil().then(setUsuario).catch(() => setSinSesion(true));
  }, [fallo]);

  /** Ejecuta un paso del expediente y vuelve a leerlo: el estado lo decide el backend. */
  const paso = async (nombrePaso: string, accion: () => Promise<unknown>, exito?: string) => {
    if (!exp) return;
    setOcupado(nombrePaso);
    setAviso(null);
    try {
      await accion();
      if (exito) setAviso({ text: exito, error: false });
    } catch (err) {
      fallo(err);
    } finally {
      setOcupado(null);
      try { setExp(await expediente(exp.id_caso)); } catch { /* el aviso ya explica */ }
    }
  };

  const conteo = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of casos) m[c.estado] = (m[c.estado] ?? 0) + 1;
    return m;
  }, [casos]);

  const irA = (v: Vista) => {
    setVista(v);
    setAviso(null);
    if (v === "bandeja") void cargarBandeja();
  };

  const pantalla = pantallaPorHref("/captacion");
  if (usuario && !permitido) {
    return (
      <main id="contenido" className="sol-main">
        <BarraNavegacion titulo="Captación" usuario={usuario} />
        <AvisoPermiso mensaje={`Tu rol no tiene permiso para usar esta pantalla. Esta pantalla es para ${pantalla?.rolesPermitidos ?? "personal autorizado"}.`} detalle="Si necesitas trabajar con captación de clientes, pide a un administrador que revise tus permisos en COREDB." />
      </main>
    );
  }

  return (
    <div className="sol-shell">
      <aside className="sol-sidebar">
        <div className="sol-brand light"><div><strong>BNA<span>®</span></strong><small>Banco Nacional de Arequipa</small></div></div>
        <nav aria-label="Navegación Captación" style={{ marginTop: "32px" }}>
          <p>CAPTACIÓN DE CLIENTES</p>
          <button className={vista !== "nuevo" ? "active" : ""} onClick={() => irA("bandeja")}><Icono nombre="bandeja" />Bandeja de casos</button>
          <button className={vista === "nuevo" ? "active" : ""} onClick={() => irA("nuevo")}><Icono nombre="persona" />Nuevo solicitante</button>
        </nav>
        {usuario && (
          <div className="sol-sidebar-bottom">
            <div className="sol-profile">
              <span className="sol-avatar">{usuario.nombre.trim()[0]?.toUpperCase()}</span>
              <div><strong>{usuario.nombre}</strong><small>{usuario.rol}</small></div>
            </div>
          </div>
        )}
      </aside>

      <div className="sol-work">
        <BarraNavegacion titulo="Captación" subtitulo={vista === "nuevo" ? "Nuevo solicitante" : vista === "caso" ? "Expediente" : "Bandeja"} usuario={usuario} />

        <main id="contenido" className="sol-main">
          {sinSesion && (
            <div role="alert" className="sol-alert error">
              Tu sesión no está iniciada o ya venció.
              <Link href={urlLoginConVolver(rutaActual())} onClick={cerrarSesion} style={{ marginLeft: "auto", fontWeight: 600, color: "inherit" }}>Iniciar sesión</Link>
            </div>
          )}
          {aviso && (
            <div role={aviso.error ? "alert" : "status"} className={`sol-alert ${aviso.error ? "error" : "success"}`}>
              <div>
                {aviso.text}
                {aviso.faltantes && aviso.faltantes.length > 0 && <ul className="cap-lista">{aviso.faltantes.map((f) => <li key={f}>{f}</li>)}</ul>}
              </div>
              <button onClick={() => setAviso(null)} aria-label="Cerrar aviso"><Icono nombre="cerrar" tamano={14} /></button>
            </div>
          )}

          {vista === "bandeja" && (
            <Bandeja casos={casos} conteo={conteo} filtro={filtro}
              onFiltro={(e) => { setFiltro(e); void cargarBandeja(e); }}
              onAbrir={abrir} onNuevo={() => irA("nuevo")} />
          )}
          {vista === "nuevo" && <Registro onAbierto={abrir} onError={fallo} />}
          {vista === "caso" && exp && <ExpedienteVista key={exp.id_caso} exp={exp} ocupado={ocupado} paso={paso} acciones={usuario?.acciones ?? []} />}
        </main>
      </div>
    </div>
  );
}

// ── Bandeja ──────────────────────────────────────────────────────────────────
function Bandeja({ casos, conteo, filtro, onFiltro, onAbrir, onNuevo }: {
  casos: CasoEnBandeja[]; conteo: Record<string, number>; filtro: string;
  onFiltro: (e: string) => void; onAbrir: (id: string) => void; onNuevo: () => void;
}) {
  return (
    <>
      <div className="sol-heading">
        <div><h1>Captación de clientes</h1><p className="cap-sub">Del prospecto al cliente habilitado para Solicitud de Crédito.</p></div>
        <button className="sol-button primary" onClick={onNuevo}><Icono nombre="persona" />Nuevo solicitante</button>
      </div>
      <div className="sol-tabs cap-filtros" role="group" aria-label="Filtrar por estado">
        {["", ...ESTADOS_BANDEJA].map((e) => (
          <button key={e || "todos"} className={filtro === e ? "active" : ""} onClick={() => onFiltro(e)}>
            {e ? e.replace("_", " ").toLowerCase() : "todos"}{e && conteo[e] ? ` (${conteo[e]})` : ""}
          </button>
        ))}
      </div>
      <section className="sol-card">
        <div className="sol-tablewrap">
          <table>
            <thead><tr><th>Solicitante</th><th>Documento</th><th>Canal</th><th>Estado</th><th>Cliente</th><th>Abierto</th><th /></tr></thead>
            <tbody>
              {casos.length === 0 && <tr><td colSpan={7} className="sol-empty">No hay casos.</td></tr>}
              {casos.map((c) => (
                <tr key={c.id_caso}>
                  <td><strong>{nombre(c.solicitante)}</strong></td>
                  <td>{c.solicitante.tipo_documento} {c.solicitante.numero_documento}</td>
                  <td>{c.canal.toLowerCase()}</td>
                  <td><Insignia valor={c.estado} /></td>
                  <td>{c.cod_cliente ?? "—"}</td>
                  <td>{fecha(c.creado_en)}</td>
                  <td><button className="sol-button secondary" onClick={() => onAbrir(c.id_caso)}>Abrir</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

// ── Paso 1: registro ─────────────────────────────────────────────────────────
function Registro({ onAbierto, onError }: { onAbierto: (id: string) => void; onError: (e: unknown) => void }) {
  const [f, setF] = useState<NuevoSolicitante>({ tipo_documento: "DNI", numero_documento: "", nombres: "", apellido_paterno: "", apellido_materno: "", celular: "", correo: "" });
  const [canal, setCanal] = useState("AGENCIA");
  const [agencia, setAgencia] = useState("AQP01");
  const [producto, setProducto] = useState("Crédito personal");
  const [enviando, setEnviando] = useState(false);
  const campo = (k: keyof NuevoSolicitante) => ({
    value: f[k], onChange: (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value }),
  });

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    try {
      const { solicitante } = await registrarSolicitante(f);
      try {
        const caso = await abrirCaso(solicitante.id_solicitante, canal, agencia, producto);
        onAbierto(caso.id_caso);
      } catch (err) {
        // Ya tenía un caso abierto: se abre ese.
        const id = isAxiosError(err) ? err.response?.data?.details?.id_caso : undefined;
        if (typeof id === "string") onAbierto(id);
        else throw err;
      }
    } catch (err) {
      onError(err);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <div className="sol-heading"><div><h1>Nuevo solicitante</h1><p className="cap-sub">Si el documento ya es cliente del banco, al habilitarlo se reutiliza el cliente de COREDB.</p></div></div>
      <section className="sol-card">
        <div className="sol-card-title"><div><h2>Datos del solicitante</h2><p>Con las mismas reglas que el maestro de clientes de COREDB.</p></div></div>
        <div className="cap-demo">
          <span>Datos de prueba:</span>
          {DEMOS.map((d) => <button key={d.etiqueta} type="button" className="sol-button ghost" onClick={() => setF(datosDemo(d))}>{d.etiqueta}</button>)}
        </div>
        <form onSubmit={enviar} className="sol-form-grid cap-form">
          <div className="sol-field"><label htmlFor="cap-tipo">Tipo de documento</label>
            <select id="cap-tipo" {...campo("tipo_documento")}>{TIPOS_DOCUMENTO.map((t) => <option key={t}>{t}</option>)}</select></div>
          <div className="sol-field"><label htmlFor="cap-doc">Número de documento</label><input id="cap-doc" required maxLength={12} {...campo("numero_documento")} /></div>
          <div className="sol-field"><label htmlFor="cap-nombres">Nombres</label><input id="cap-nombres" required maxLength={100} {...campo("nombres")} /></div>
          <div className="sol-field"><label htmlFor="cap-paterno">Apellido paterno</label><input id="cap-paterno" required maxLength={100} {...campo("apellido_paterno")} /></div>
          <div className="sol-field"><label htmlFor="cap-materno">Apellido materno</label><input id="cap-materno" maxLength={100} {...campo("apellido_materno")} /></div>
          <div className="sol-field"><label htmlFor="cap-celular">Celular</label><input id="cap-celular" required pattern="9\d{8}" title="Nueve dígitos que empiezan con 9" {...campo("celular")} /></div>
          <div className="sol-field"><label htmlFor="cap-correo">Correo</label><input id="cap-correo" type="email" required maxLength={150} {...campo("correo")} /></div>
          <div className="sol-field"><label htmlFor="cap-canal">Canal</label>
            <select id="cap-canal" value={canal} onChange={(e) => setCanal(e.target.value)}>{CANALES.map((c) => <option key={c}>{c}</option>)}</select></div>
          <div className="sol-field"><label htmlFor="cap-agencia">Agencia</label><input id="cap-agencia" maxLength={10} value={agencia} onChange={(e) => setAgencia(e.target.value)} /></div>
          <div className="sol-field"><label htmlFor="cap-producto">Producto de interés</label><input id="cap-producto" maxLength={60} value={producto} onChange={(e) => setProducto(e.target.value)} /></div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button className="sol-button primary" type="submit" disabled={enviando}>{enviando ? "Registrando..." : "Registrar y abrir caso"}</button>
          </div>
        </form>
      </section>
    </>
  );
}

// ── Expediente: pasos 2 a 5 ──────────────────────────────────────────────────
type Paso = (nombre: string, accion: () => Promise<unknown>, exito?: string) => Promise<void>;

function ExpedienteVista({ exp, ocupado, paso, acciones }: { exp: Expediente; ocupado: string | null; paso: Paso; acciones: string[] }) {
  const consent = ultimos(exp.consentimientos);
  const vals = ultimos(exp.validaciones);
  const cerrado = ["HABILITADO", "RECHAZADO", "REVOCADO"].includes(exp.estado);
  const ok = (t: string) => consent.get(t)?.aceptado === true;
  const aprobada = (t: string) => vals.get(t)?.resultado === "APROBADO";
  const etapas = [
    { t: "Registro", hecho: true },
    { t: "Consentimientos", hecho: ok("TRATAMIENTO_DATOS") && ok("CONSULTA_BUROS") && ok("TERMINOS") },
    { t: "Verificación", hecho: aprobada("CELULAR") && aprobada("RENIEC") && aprobada("LISTAS_NEGRAS") },
    { t: "Riesgo", hecho: exp.perfil !== null },
    { t: "Habilitación", hecho: exp.estado === "HABILITADO" },
  ];
  const actual = etapas.findIndex((e) => !e.hecho);

  return (
    <>
      <div className="sol-heading">
        <div>
          <span className="sol-eyebrow">Caso {exp.id_caso.slice(0, 8)} · {exp.canal.toLowerCase()}{exp.id_agencia ? ` · ${exp.id_agencia}` : ""}</span>
          <h1>{nombre(exp.solicitante)}</h1>
          <p className="cap-sub">{exp.solicitante.tipo_documento} {exp.solicitante.numero_documento} · {exp.solicitante.celular} · {exp.solicitante.correo}</p>
        </div>
        <div className="cap-estado"><Insignia valor={exp.estado} />{exp.creado_en && <small>Abierto {fecha(exp.creado_en)} por {exp.creado_por}</small>}</div>
      </div>

      <ol className="sol-steps">
        {etapas.map((e, i) => <li key={e.t} className={e.hecho ? "done" : i === actual ? "current" : ""}><span>{e.hecho ? "✓" : i + 1}</span>{e.t}</li>)}
      </ol>

      {exp.motivo_cierre && <div className="sol-alert error">Cerrado: {exp.motivo_cierre}</div>}
      {exp.observacion && <div className="sol-alert warning">Observación: {exp.observacion}</div>}

      <Consentimientos exp={exp} cerrado={cerrado} ocupado={ocupado} paso={paso} />
      <Verificacion exp={exp} cerrado={cerrado} ocupado={ocupado} paso={paso} />
      <Riesgo exp={exp} cerrado={cerrado} ocupado={ocupado} paso={paso} />
      <Habilitacion exp={exp} ocupado={ocupado} paso={paso} acciones={acciones} />
      <Decisiones exp={exp} ocupado={ocupado} paso={paso} />
    </>
  );
}

function Seccion({ n, titulo, texto, hecho, children }: { n: number; titulo: string; texto: string; hecho: boolean; children: ReactNode }) {
  return (
    <section className={`sol-card cap-seccion ${hecho ? "hecho" : ""}`}>
      <div className="sol-card-title"><div><h2><span className="cap-num">{hecho ? "✓" : n}</span>{titulo}</h2><p>{texto}</p></div></div>
      <div className="cap-cuerpo">{children}</div>
    </section>
  );
}

type PropsPaso = { exp: Expediente; cerrado: boolean; ocupado: string | null; paso: Paso };

function Consentimientos({ exp, cerrado, ocupado, paso }: PropsPaso) {
  const actuales = ultimos(exp.consentimientos);
  const [marcas, setMarcas] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(CONSENTIMIENTOS.map((c) => [c.tipo, actuales.get(c.tipo)?.aceptado ?? c.requerido])));
  const [medio, setMedio] = useState("DIGITAL");
  const hecho = ["TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS"].every((t) => actuales.get(t)?.aceptado);
  return (
    <Seccion n={2} titulo="Consentimientos" texto="Sin tratamiento de datos no se verifica; sin consulta a burós no se consulta riesgo." hecho={hecho}>
      {CONSENTIMIENTOS.map((c) => {
        const a = actuales.get(c.tipo);
        return (
          <label key={c.tipo} className="sol-checkrow">
            <input type="checkbox" checked={!!marcas[c.tipo]} disabled={cerrado} onChange={(e) => setMarcas({ ...marcas, [c.tipo]: e.target.checked })} />
            <div><strong>{c.etiqueta}</strong><small>{c.requerido ? "Requerido" : "Opcional"}{a?.version ? ` · versión ${a.version}` : ""}</small></div>
            <span style={{ marginLeft: "auto" }}>{a ? <Insignia valor={a.aceptado ? "APROBADO" : "RECHAZADO"} texto={a.aceptado ? `Aceptado (${a.medio.toLowerCase()})` : "No aceptado"} /> : <Insignia valor="" texto="Sin registrar" />}</span>
          </label>
        );
      })}
      {!cerrado && (
        <div className="cap-fila">
          <select aria-label="Medio" value={medio} onChange={(e) => setMedio(e.target.value)}><option value="DIGITAL">Digital</option><option value="FISICO">Físico</option><option value="BIOMETRICO">Biométrico</option></select>
          <button className="sol-button primary" disabled={!!ocupado} onClick={() => paso("consent", () => registrarConsentimientos(exp.id_caso, marcas, medio))}>
            {ocupado === "consent" ? "Guardando..." : "Registrar consentimientos"}
          </button>
        </div>
      )}
    </Seccion>
  );
}

function Verificacion({ exp, cerrado, ocupado, paso }: PropsPaso) {
  const vals = ultimos(exp.validaciones);
  const [otp, setOtp] = useState<OtpEnviado | null>(null);
  const [canal, setCanal] = useState("SMS");
  const [codigo, setCodigo] = useState("");
  const [intento, setIntento] = useState<string | null>(null);
  const [tipos, setTipos] = useState<string[]>(["RENIEC", "LISTAS_NEGRAS", "PEP"]);
  const [manual, setManual] = useState({ tipo: "PEP", resultado: "APROBADO", detalle: "" });
  const contactoOk = (t: string) => vals.get(t)?.resultado === "APROBADO";
  const hecho = contactoOk("CELULAR") && contactoOk("RENIEC") && contactoOk("LISTAS_NEGRAS");

  return (
    <Seccion n={3} titulo="Verificación de datos" texto="Código OTP al contacto del solicitante y validación de su identidad." hecho={hecho}>
      <div className="cap-dos">
        <div className="cap-caja">
          <h3>Código OTP</h3>
          <p className="cap-sub">
            Celular {contactoOk("CELULAR") ? <Insignia valor="APROBADO" texto="verificado" /> : <Insignia valor="" texto="pendiente" />}{" "}
            Correo {contactoOk("CORREO") ? <Insignia valor="APROBADO" texto="verificado" /> : <Insignia valor="" texto="opcional" />}
          </p>
          {!cerrado && (
            <>
              <div className="cap-fila">
                <select aria-label="Enviar por" value={canal} onChange={(e) => { setCanal(e.target.value); setOtp(null); }}>
                  <option value="SMS">SMS al celular</option><option value="EMAIL">Correo</option>
                </select>
                <button className="sol-button secondary" disabled={!!ocupado}
                  onClick={() => paso("otp", async () => { setOtp(await enviarOtp(exp.id_caso, canal)); setCodigo(""); setIntento(null); })}>
                  {otp ? "Reenviar código" : "Enviar código"}
                </button>
              </div>
              {otp && (
                <div className="cap-otp">
                  <p>Enviado a <b>{otp.destino_enmascarado}</b>; vence a las {new Date(otp.expira_en).toLocaleTimeString("es-PE")}.</p>
                  {otp.codigo_simulado && (
                    <p className="cap-simulado">Mensaje simulado: <code>{otp.codigo_simulado}</code>
                      <button className="sol-link" onClick={() => setCodigo(otp.codigo_simulado ?? "")}>usar</button></p>
                  )}
                  <div className="cap-fila">
                    <input aria-label="Código OTP" className="cap-codigo" inputMode="numeric" maxLength={6} placeholder="000000"
                      value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))} />
                    <button className="sol-button primary" disabled={codigo.length !== 6 || !!ocupado}
                      onClick={() => paso("verificar", async () => {
                        const r = await verificarOtp(exp.id_caso, canal, codigo);
                        if (r.verificado) setOtp(null);
                        setIntento(r.verificado ? null : `Código incorrecto (${r.estado_codigo.toLowerCase()}); intentos restantes: ${r.intentos_restantes}.`);
                      })}>Verificar</button>
                  </div>
                  {intento && <p className="cap-mal">{intento}</p>}
                </div>
              )}
            </>
          )}
        </div>

        <div className="cap-caja">
          <h3>Identidad</h3>
          {!cerrado && (
            <>
              <div className="cap-tipos">
                {VALIDACIONES.map((v) => (
                  <label key={v.tipo}><input type="checkbox" checked={tipos.includes(v.tipo)}
                    onChange={(e) => setTipos(e.target.checked ? [...tipos, v.tipo] : tipos.filter((t) => t !== v.tipo))} /> {v.etiqueta}</label>
                ))}
              </div>
              <button className="sol-button primary" disabled={!tipos.length || !!ocupado} onClick={() => paso("validar", () => validar(exp.id_caso, tipos))}>
                {ocupado === "validar" ? "Validando..." : "Ejecutar validaciones"}
              </button>
            </>
          )}
          <div className="sol-tablewrap">
          <table className="cap-tabla">
            <tbody>
              {VALIDACIONES.map((v) => {
                const r = vals.get(v.tipo);
                return (
                  <tr key={v.tipo}>
                    <td>{v.etiqueta}{v.requerido && <em className="cap-req"> *</em>}</td>
                    <td>{r ? <Insignia valor={r.resultado === "OBSERVADO" ? "OBSERVADO" : r.resultado} /> : "—"}</td>
                    <td className="cap-sub">{r ? `${r.detalle ?? ""}${r.proveedor === "MANUAL" ? " (manual)" : ""}` : ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
          {!cerrado && (
            <details className="cap-manual">
              <summary>Registrar una validación manual (debida diligencia, verificación presencial)</summary>
              <div className="cap-fila">
                <select aria-label="Tipo" value={manual.tipo} onChange={(e) => setManual({ ...manual, tipo: e.target.value })}>
                  {VALIDACIONES.map((v) => <option key={v.tipo} value={v.tipo}>{v.etiqueta}</option>)}
                </select>
                <select aria-label="Resultado" value={manual.resultado} onChange={(e) => setManual({ ...manual, resultado: e.target.value })}>
                  <option>APROBADO</option><option>OBSERVADO</option><option>RECHAZADO</option>
                </select>
                <input aria-label="Detalle" placeholder="Detalle (obligatorio)" value={manual.detalle} onChange={(e) => setManual({ ...manual, detalle: e.target.value })} />
                <button className="sol-button secondary" disabled={manual.detalle.trim().length < 3 || !!ocupado}
                  onClick={() => paso("manual", () => validacionManual(exp.id_caso, manual.tipo, manual.resultado, manual.detalle))}>Registrar</button>
              </div>
            </details>
          )}
        </div>
      </div>
    </Seccion>
  );
}

function Riesgo({ exp, cerrado, ocupado, paso }: PropsPaso) {
  const [central, setCentral] = useState("SBS");
  const p = exp.perfil;
  return (
    <Seccion n={4} titulo="Centrales de riesgo y perfil" texto="Consulta a burós y puntaje de 0 a 1000 (más alto, menos riesgo)." hecho={p !== null}>
      {!cerrado && (
        <div className="cap-fila">
          <select aria-label="Central" value={central} onChange={(e) => setCentral(e.target.value)}>{CENTRALES.map((c) => <option key={c}>{c}</option>)}</select>
          <button className="sol-button secondary" disabled={!!ocupado} onClick={() => paso("central", () => consultarCentral(exp.id_caso, central))}>Consultar central</button>
          <button className="sol-button primary" disabled={!!ocupado || exp.consultas.length === 0} onClick={() => paso("perfil", () => calcularPerfil(exp.id_caso))}>Calcular perfil</button>
        </div>
      )}
      <div className="cap-dos">
        <div className="sol-tablewrap">
        <table className="cap-tabla">
          <thead><tr><th>Central</th><th>Calificación</th><th>Deuda</th><th>Entidades</th><th>Mora</th></tr></thead>
          <tbody>
            {exp.consultas.length === 0 && <tr><td colSpan={5} className="cap-sub">Sin consultas.</td></tr>}
            {exp.consultas.map((c, i) => (
              <tr key={i}><td>{c.central}</td><td><Insignia valor={c.calificacion} /></td><td>{soles(c.deuda_total)}</td><td>{c.entidades}</td><td>{c.dias_mora} d</td></tr>
            ))}
          </tbody>
        </table>
        </div>
        <div className="cap-caja">
          {p ? (
            <>
              <div className="cap-fila"><span className="cap-puntaje">{p.puntaje}</span><Insignia valor={p.calificacion} texto={`Riesgo ${p.calificacion.replace("_", " ").toLowerCase()}`} /></div>
              <div className="cap-barra" role="img" aria-label={`Puntaje ${p.puntaje} de 1000`}><i style={{ left: `${p.puntaje / 10}%` }} /></div>
              <div className="cap-eje"><span>0</span><span>350</span><span>550</span><span>750</span><span>1000</span></div>
              <p className="cap-sub">{p.observacion}</p>
            </>
          ) : <p className="cap-sub">Riesgo muy alto rechaza el caso.</p>}
        </div>
      </div>
    </Seccion>
  );
}

function Habilitacion({ exp, ocupado, paso, acciones }: { exp: Expediente; ocupado: string | null; paso: Paso; acciones: string[] }) {
  const [ref, setRef] = useState<Referencia | null>(null);
  const habilitado = exp.estado === "HABILITADO" || exp.estado === "REVOCADO";
  return (
    <Seccion n={5} titulo="Habilitación y envío a Solicitud de Crédito" hecho={exp.estado === "HABILITADO"}
      texto="Registra al cliente en COREDB (o reutiliza el que ya existe) y deja la referencia que consulta Solicitud de Crédito.">
      {!habilitado && exp.estado !== "RECHAZADO" && (
        <>
          {exp.faltantes.length > 0
            ? <div className="sol-alert warning"><div>Falta para habilitar:<ul className="cap-lista">{exp.faltantes.map((f) => <li key={f}>{f}</li>)}</ul></div></div>
            : <div className="sol-alert success">El caso cumple todos los requisitos.</div>}
          <button className="sol-button primary" disabled={!exp.listo_para_habilitar || !!ocupado}
            onClick={() => paso("habilitar", () => habilitar(exp.id_caso), "Cliente habilitado en COREDB.")}>
            <Icono nombre="escudo" />{ocupado === "habilitar" ? "Habilitando..." : "Habilitar cliente"}
          </button>
        </>
      )}
      {habilitado && (
        <>
          <dl className="cap-datos">
            <dt>Código de cliente (COREDB)</dt><dd><strong>{exp.cod_cliente}</strong> {exp.cliente_nuevo ? "· cliente nuevo" : "· cliente que ya existía"}</dd>
            <dt>Verificación de captación</dt><dd className="cap-mono">{exp.id_verificacion_captacion}</dd>
            <dt>Vigencia</dt><dd>{exp.fecha_verificacion} al {exp.vigente_hasta}</dd>
          </dl>
          <div className="cap-fila">
            <button className="sol-button secondary" disabled={!!ocupado} onClick={() => paso("ref", async () => setRef(await referencia(exp.id_caso)))}>
              Ver lo que recibe Solicitud de Crédito
            </button>
            <Link className="sol-link" href="/solicitud-credito">Ir a Solicitud de Crédito</Link>
          </div>
          {puedeVerPantalla(acciones, "/cuenta") && (
            <div className="sol-alert success" role="status" style={{ marginTop: 12 }}>
              Siguiente paso: <Link href={`/cuenta?codCliente=${encodeURIComponent(exp.cod_cliente ?? "")}&tab=apertura`} style={{ fontWeight: 700, color: "inherit" }}>Abrir cuenta</Link> (lo hace un operador).
            </div>
          )}
          {ref && (
            <div className="cap-caja">
              <h3>Referencia CR-INT-01 <Insignia valor={ref.estado_habilitante === "HABILITADO" ? "APROBADO" : "RECHAZADO"} texto={ref.estado_habilitante} /></h3>
              <p className="cap-sub">Es la respuesta de <code>GET /cap/references/{ref.id_cliente}</code>; el estado del cliente se lee en vivo de COREDB.</p>
              <pre className="cap-json">{JSON.stringify(ref, null, 2)}</pre>
            </div>
          )}
        </>
      )}
    </Seccion>
  );
}

function Decisiones({ exp, ocupado, paso }: { exp: Expediente; ocupado: string | null; paso: Paso }) {
  const [motivo, setMotivo] = useState("");
  const abiertos = ["INICIADO", "EN_VALIDACION", "OBSERVADO", "APROBADO"].includes(exp.estado);
  const acciones = exp.estado === "HABILITADO" ? [["REVOCAR", "Revocar habilitación"]]
    : abiertos ? [exp.observacion ? ["LEVANTAR_OBSERVACION", "Levantar observación"] : ["OBSERVAR", "Observar"], ["RECHAZAR", "Rechazar caso"]] : [];
  if (!acciones.length) return null;
  return (
    <section className="sol-card cap-seccion">
      <div className="sol-card-title"><div><h2>Decisión del asesor</h2><p>Queda en la bitácora del caso con su motivo.</p></div></div>
      <div className="cap-cuerpo cap-fila">
        <input aria-label="Motivo" placeholder="Motivo" value={motivo} maxLength={255} onChange={(e) => setMotivo(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
        {acciones.map(([accion, texto]) => (
          <button key={accion} className={`sol-button ${accion === "OBSERVAR" || accion === "LEVANTAR_OBSERVACION" ? "secondary" : "ghost"}`}
            disabled={motivo.trim().length < 3 || !!ocupado}
            onClick={() => paso("estado", async () => { await cambiarEstado(exp.id_caso, accion, motivo); setMotivo(""); })}>{texto}</button>
        ))}
      </div>
    </section>
  );
}


export default function CaptacionPage() {
  return <Suspense fallback={<main id="contenido" className="sol-main"><p>Cargando…</p></main>}><CaptacionPageInner /></Suspense>;
}
