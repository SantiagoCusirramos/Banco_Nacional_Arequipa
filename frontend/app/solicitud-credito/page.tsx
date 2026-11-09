"use client";

/** Interfaz de agencia del MVP SOL. Todas las validaciones de negocio y los
 * cálculos financieros se ejecutan de nuevo en el servidor con Decimal.
 * Los Number de este archivo solo presentan cifras o convierten el plazo entero.
 */
import {
  cloneElement,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";

type User = {
  username: string;
  nombre: string;
  rol: "ASESOR" | "SUPERVISOR" | "AUDITOR" | "EVALUADOR";
};
type Policy = {
  version: string;
  estado_aprobacion: string;
  producto_nombre: string;
  monedas: string[];
  monto_minimo: string;
  monto_maximo: string;
  plazo_minimo_meses: number;
  plazo_maximo_meses: number;
  tea: string;
  dias_por_periodo: number;
  nota: string;
  integracion: string;
};
type Client = {
  id_cliente: string;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string;
  estado_cliente: string;
  estado_habilitante: string;
  vigente_hasta: string;
  id_caso: string;
  id_verificacion: string;
};
type Guarantee = {
  tipo_garantia: string;
  descripcion: string;
  valor_tasacion: string;
};
type FormData = {
  id_cliente: string;
  monto_solicitado: string;
  moneda: string;
  plazo_meses: number;
  destino_credito: string;
  fecha_base: string;
  pago_doble: boolean;
  garantias: Guarantee[];
  fiadores: string[];
  revision?: number;
};
type Schedule = {
  estado: string;
  cuota_referencial: string;
  intereses_totales: string;
  total_pagar: string;
  cuotas: {
    numero_cuota: number;
    fecha_vencimiento: string;
    saldo_inicial: string;
    amortizacion: string;
    interes: string;
    cuota_total: string;
    saldo_final: string;
  }[];
};
type Snapshot = {
  cliente: Client;
  condiciones: FormData;
  politica: Policy;
  calendario: Schedule;
  fiadores: { id_cliente: string }[];
};
type Summary = {
  id: string;
  codigo: string;
  estado: string;
  version: number;
  revision: number;
  cliente_nombre: string;
  documento: string;
  monto: string;
  moneda: string;
  plazo: number;
  actualizado: string;
};
type ApplicationPage = { items: Summary[]; total: number; offset: number; limit: number; estados: Record<string, number> };
type Detail = Summary & {
  pendiente_envio?: boolean;
  versiones: { numero: number; congelada: boolean; expediente: Snapshot }[];
  resultados: {
    version: number;
    decision: string;
    observaciones: string;
    fecha: string;
  }[];
  eventos: {
    accion: string;
    actor: string;
    version: number;
    estado_anterior: string;
    estado_nuevo: string;
    fecha: string;
    correlacion: string;
  }[];
  envios: {
    version: number;
    id_operacion: string;
    acuse: string;
    estado_transporte: string;
    fecha: string;
  }[];
};
type View = "bandeja" | "editor" | "detalle" | "politicas" | "integraciones";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  operation?: string,
): Promise<T> {
  const response = await fetch(`/api/solicitud-credito/${path}`, {
    method,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(operation ? { "X-Idempotency-Key": operation } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail
          .map(
            (e: { loc: string[]; msg: string }) =>
              `${e.loc.slice(1).join(".")}: ${e.msg}`,
          )
          .join(" · ")
      : data.detail;
    throw new ApiError(
      message || "No se pudo completar la operación.",
      response.status,
    );
  }
  return data;
}

function today() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Lima", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const part = (type: string) => parts.find((p) => p.type === type)!.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}
function freshForm(): FormData {
  return {
    id_cliente: "",
    monto_solicitado: "",
    moneda: "PEN",
    plazo_meses: 12,
    destino_credito: "",
    fecha_base: today(),
    pago_doble: false,
    garantias: [],
    fiadores: [],
  };
}
const amount = (value: string | number, currency = "PEN") =>
  new Intl.NumberFormat("es-PE", { style: "currency", currency }).format(
    Number(value),
  );
const person = (c: Client) =>
  `${c.nombres} ${c.apellido_paterno} ${c.apellido_materno}`;
const eligible = (c: Client) =>
  c.estado_cliente === "ACTIVO" &&
  c.estado_habilitante === "HABILITADO" &&
  c.vigente_hasta >= today();
const dateTime = (d: string) =>
  new Date(d).toLocaleString("es-PE", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Lima",
  });

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    doc: (
      <>
        <path d="M14 2H5v20h14V7Z" />
        <path d="M14 2v6h5M8 12h8M8 16h6" />
      </>
    ),
    shield: (
      <>
        <path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z" />
        <path d="m8 12 3 3 5-6" />
      </>
    ),
    link: (
      <>
        <path d="m9 15 6-6M8 16l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 10a4 4 0 0 0 6 0l4-4a4 4 0 0 0-6-6l-1 1" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
    back: <path d="M19 12H5m6-6-6 6 6 6" />,
    search: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="m15 15 6 6" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    exit: (
      <>
        <path d="M9 3H3v18h6M12 12h9m-4-4 4 4-4 4" />
      </>
    ),
    download: (
      <>
        <path d="M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4" />
      </>
    ),
    alert: (
      <>
        <path d="m12 3 10 18H2Z" />
        <path d="M12 9v5m0 3h.01" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="7" r="4" />
        <path d="M4 22v-3a8 8 0 0 1 16 0v3" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {paths[name] || paths.doc}
    </svg>
  );
}

function Brand({ light = false }: { light?: boolean }) {
  return (
    <div className={`sol-brand ${light ? "light" : ""}`}>
      <svg width="42" height="40" viewBox="0 0 48 44" fill="none" aria-hidden>
        <path
          d="m4 28 17-21 5 4 4-3 14 20M4 34h40M11 40h26"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
        />
        <path d="m17 13 4 5 5-7" stroke="var(--sol-gold)" strokeWidth="2" />
      </svg>
      <div>
        <strong>
          BNA<span>®</span>
        </strong>
        <small>Banco Nacional de Arequipa</small>
      </div>
    </div>
  );
}

function Badge({ state }: { state: string }) {
  return (
    <span className={`sol-badge ${state.toLowerCase()}`}>
      <span />
      {state.replaceAll("_", " ")}
    </span>
  );
}
function Field({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  // Etiqueta y ayuda separadas del control: nombres accesibles estables,
  // incluso en selects con varias opciones y al usar lectores de pantalla.
  const id = useId();
  const control = children as ReactElement<{
    id?: string;
    "aria-describedby"?: string;
  }>;
  return (
    <div className="sol-field">
      <label htmlFor={id}>{title}</label>
      {cloneElement(control, {
        id,
        "aria-describedby": hint ? `${id}-hint` : undefined,
      })}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </div>
  );
}

function CalendarTable({
  data,
  currency,
}: {
  data: Schedule;
  currency: string;
}) {
  const [all, setAll] = useState(false);
  return (
    <>
      <div className="sol-metrics">
        <div>
          <small>Cuota referencial</small>
          <strong>{amount(data.cuota_referencial, currency)}</strong>
        </div>
        <div>
          <small>Interés total</small>
          <strong>{amount(data.intereses_totales, currency)}</strong>
        </div>
        <div>
          <small>Total a pagar</small>
          <strong>{amount(data.total_pagar, currency)}</strong>
        </div>
      </div>
      <div className="sol-tablewrap">
        <table>
          <thead>
            <tr>
              <th>Cuota</th>
              <th>Vencimiento</th>
              <th className="num">Capital</th>
              <th className="num">Interés</th>
              <th className="num">Total</th>
              <th className="num">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {(all ? data.cuotas : data.cuotas.slice(0, 6)).map((q) => (
              <tr key={q.numero_cuota}>
                <td>{String(q.numero_cuota).padStart(2, "0")}</td>
                <td>{q.fecha_vencimiento.split("-").reverse().join("/")}</td>
                <td className="num">{amount(q.amortizacion, currency)}</td>
                <td className="num">{amount(q.interes, currency)}</td>
                <td className="num emphasis">
                  {amount(q.cuota_total, currency)}
                </td>
                <td className="num">{amount(q.saldo_final, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.cuotas.length > 6 && (
        <button className="sol-link" onClick={() => setAll(!all)} type="button">
          {all
            ? "Mostrar primeras 6 cuotas"
            : `Ver las ${data.cuotas.length} cuotas`}
        </button>
      )}
      <p className="sol-caption">
        Calendario preliminar · Periodos de días fijos · Última cuota ajustada
        por redondeo. Sin comisiones ni seguros.
      </p>
    </>
  );
}

export default function SolicitudPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(
    null,
  );
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [pageOffset, setPageOffset] = useState(0);
  const [totalApplications, setTotalApplications] = useState(0);
  const [stateCounts, setStateCounts] = useState<Record<string, number>>({});
  const [clients, setClients] = useState<Client[]>([]);
  const [apps, setApps] = useState<Summary[]>([]);
  const [view, setView] = useState<View>("bandeja");
  const [selected, setSelected] = useState<Detail | null>(null);
  const [tab, setTab] = useState("Resumen");
  const [version, setVersion] = useState(1);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("TODAS");
  const [form, setForm] = useState<FormData>(freshForm);
  const [step, setStep] = useState(0);
  const [preview, setPreview] = useState<Snapshot | null>(null);
  const [username, setUsername] = useState("asesor.bna");
  const [password, setPassword] = useState("");
  const [decision, setDecision] = useState("OBSERVADO");
  const [observation, setObservation] = useState("");
  // Conservar la clave al reintentar tras un timeout reconoce un acuse que
  // pudo confirmarse aunque el navegador no recibiera la primera respuesta.
  const sendKeys = useRef(new Map<string, string>());
  function sendKey(d: Detail) {
    const pending = d.envios.find((e) => e.version === d.version && e.estado_transporte !== "CONFIRMADO");
    if (pending) return pending.id_operacion;
    const id = `${d.id}:${d.revision}`;
    if (!sendKeys.current.has(id))
      sendKeys.current.set(id, crypto.randomUUID());
    return sendKeys.current.get(id)!;
  }

  const fail = useCallback((e: unknown) => {
    setNotice({
      text:
        e instanceof Error ? e.message : "No se pudo completar la operación.",
      error: true,
    });
    if (e instanceof ApiError && e.status === 401) setUser(null);
  }, []);
  const refresh = useCallback(async () => {
    const [p, c, a] = await Promise.all([
      api<Policy>("policy"),
      api<Client[]>("clients"),
      api<ApplicationPage>(`applications?limit=50&offset=${pageOffset}`),
    ]);
    setPolicy(p);
    setClients(c);
    setApps(a.items);
    setTotalApplications(a.total);
    setStateCounts(a.estados);
  }, [pageOffset]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const u = await api<User>("auth/me");
        if (active) {
          setUser(u);
          await refresh();
        }
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 401) && active) fail(e);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [refresh, fail]);

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setNotice(null);
    try {
      await task();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  const update = <K extends keyof FormData>(key: K, value: FormData[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setPreview(null);
  };
  const writable = user?.rol === "ASESOR";
  const editing = selected && view === "editor";
  const current = selected?.versiones.find((v) => v.numero === version);

  function start() {
    setSelected(null);
    setForm({
      ...freshForm(),
      moneda: policy?.monedas[0] || "PEN",
      plazo_meses: Math.min(
        policy?.plazo_maximo_meses || 12,
        Math.max(12, policy?.plazo_minimo_meses || 1),
      ),
    });
    setStep(0);
    setPreview(null);
    setView("editor");
    setNotice(null);
  }
  async function open(id: string) {
    await run(async () => {
      const d = await api<Detail>(`applications/${id}`);
      setSelected(d);
      setVersion(d.version);
      setTab("Resumen");
      setView("detalle");
    });
  }
  function edit(d: Detail) {
    const snapshot = d.versiones.find(
      (v) => v.numero === d.version,
    )!.expediente;
    const c = snapshot.condiciones;
    setForm({
      id_cliente: c.id_cliente,
      monto_solicitado: c.monto_solicitado,
      moneda: c.moneda,
      plazo_meses: c.plazo_meses,
      destino_credito: c.destino_credito,
      fecha_base: c.fecha_base < today() ? today() : c.fecha_base,
      pago_doble: false,
      garantias: c.garantias,
      fiadores: snapshot.fiadores.map((f) => f.id_cliente),
      revision: d.revision,
    });
    setSelected(d);
    setStep(1);
    setPreview(null);
    setView("editor");
  }
  async function calculate() {
    await run(async () => {
      setPreview(await api<Snapshot>("preview", "POST", form));
      setStep(3);
    });
  }
  async function save(send: boolean) {
    await run(async () => {
      const d = editing
        ? await api<Detail>(`applications/${selected!.id}`, "PUT", form)
        : await api<Detail>("applications", "POST", form);
      // Abrir el borrador antes de enviar evita perder el ID si el gateway falla.
      setSelected(d);
      setVersion(d.version);
      setView("detalle");
      setTab("Resumen");
      await refresh();
      let pending = false;
      if (send) {
        const sent = await api<Detail>(
          `applications/${d.id}/send`,
          "POST",
          { revision: d.revision },
          sendKey(d),
        );
        pending = !!sent.pendiente_envio;
        setSelected(sent);
        await refresh();
      }
      setNotice({
        text: pending
          ? "Envío pendiente de confirmación. La versión está reservada; actualiza para consultar el acuse."
          : send
          ? (policy?.integracion === "REAL" ? "Evaluación confirmó la recepción del expediente." : "Expediente enviado a Evaluación simulada. La versión quedó congelada.")
          : "Borrador guardado en la base de datos.",
        error: false,
      });
    });
  }
  async function sendCurrent() {
    if (selected)
      await run(async () => {
        const d = await api<Detail>(
          `applications/${selected.id}/send`,
          "POST",
          { revision: selected.revision },
          sendKey(selected),
        );
        setSelected(d);
        await refresh();
        setNotice({
          text: d.pendiente_envio ? "Envío pendiente de confirmación. Actualiza para consultar el acuse." : (policy?.integracion === "REAL" ? "Envío confirmado por Evaluación. Consulta el acuse." : "Envío recibido por EVA simulada. Consulta el acuse en el historial."),
          error: false,
        });
      });
  }
  async function revise() {
    if (selected)
      await run(async () => {
        const d = await api<Detail>(
          `applications/${selected.id}/revise`,
          "POST",
          { revision: selected.revision },
        );
        await refresh();
        edit(d);
        setNotice({
          text: `Versión ${d.version} creada. La anterior conserva sus condiciones.`,
          error: false,
        });
      });
  }
  function exportJson() {
    if (!selected) return;
    const blob = new Blob([JSON.stringify(selected, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selected.codigo}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading)
    return (
      <div className="sol-loading">
        <Brand />
        <p>Preparando tu espacio de trabajo…</p>
      </div>
    );

  if (!user)
    return (
      <div className="sol-login">
        <section className="sol-login-visual">
          <Brand light />
          <div>
            <p className="sol-eyebrow">CERCA DE TI. CERCA DE TU FUTURO.</p>
            <h1>
              Las buenas decisiones
              <br />
              empiezan con una
              <br />
              <em>solicitud clara.</em>
            </h1>
            <p>
              Un espacio para acompañar cada solicitud,
              <br />
              desde el primer registro hasta su evaluación.
            </p>
          </div>
          <svg
            className="sol-mountain"
            viewBox="0 0 600 240"
            fill="none"
            aria-hidden
          >
            <path
              d="m0 220 130-60 145-150 70 65 35-27 220 172M0 234h600M150 235l125-225m-45 60 45 16 32-40"
              stroke="currentColor"
              strokeWidth="1.2"
            />
          </svg>
          <small>AREQUIPA, PERÚ · BANCA CON IDENTIDAD</small>
        </section>
        <section className="sol-login-form">
          <span className="sol-kicker">PORTAL DEL PERSONAL</span>
          <h2>Bienvenido a BNA</h2>
          <p>Ingresa para gestionar solicitudes de crédito.</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                const result = await api<{ usuario: User }>(
                  "auth/login",
                  "POST",
                  { username, password },
                );
                setUser(result.usuario);
                setPassword("");
                setView("bandeja");
                await refresh();
              });
            }}
          >
            <Field title="Usuario">
              <select
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              >
                <option value="asesor.bna">asesor.bna · Asesor</option>
                <option value="supervisor.bna">
                  supervisor.bna · Solo consulta
                </option>
                <option value="auditor.bna">auditor.bna · Solo consulta</option>
                <option value="evaluador.demo">
                  evaluador.demo · Simulador EVA
                </option>
              </select>
            </Field>
            <Field
              title="Contraseña"
              hint="Usa la clave que elegiste al inicializar el laboratorio."
            >
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                placeholder="Ingresa tu contraseña"
              />
            </Field>
            <button className="sol-button primary" disabled={busy}>
              {busy ? "Ingresando…" : "Ingresar al portal"}
              <Icon name="arrow" />
            </button>
          </form>
          {notice && (
            <p role="alert" className="sol-alert error">
              {notice.text}
            </p>
          )}
          <div className="sol-login-note">
            <Icon name="shield" />
            <p>
              <strong>Entorno académico de demostración</strong>
              <br />
              Datos sintéticos y conexiones con otros módulos simuladas.
              Políticas pendientes de aprobación.
            </p>
          </div>
          <small>Solicitud de Crédito · Plataforma BNA · MVP 1.0</small>
        </section>
      </div>
    );

  const filtered = apps.filter(
    (a) =>
      (filter === "TODAS" || a.estado === filter) &&
      `${a.codigo} ${a.cliente_nombre} ${a.documento}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <div className="sol-shell">
      <aside className="sol-sidebar">
        <Brand light />
        <div className="sol-workspace">
          <span className="sol-workspace-dot" />
          Agencia · Arequipa Centro<small>ESPACIO DEL PERSONAL</small>
        </div>
        <nav aria-label="Navegación de Solicitud">
          <p>GESTIÓN DE CRÉDITOS</p>
          {[
            {
              id: "bandeja",
              icon: "grid",
              label:
                user.rol === "EVALUADOR"
                  ? "Consola EVA simulada"
                  : "Solicitudes",
              count: apps.length,
            },
            { id: "politicas", icon: "shield", label: "Políticas de crédito" },
            { id: "integraciones", icon: "link", label: "Integraciones" },
          ].map((n) => (
            <button
              key={n.id}
              className={
                view === n.id ||
                (n.id === "bandeja" && ["detalle", "editor"].includes(view))
                  ? "active"
                  : ""
              }
              onClick={() => {
                setView(n.id as View);
                setNotice(null);
              }}
            >
              <Icon name={n.icon} />
              {n.label}
              {n.count !== undefined && <span>{n.count}</span>}
            </button>
          ))}
        </nav>
        <div className="sol-sidebar-bottom">
          <div className="sol-lab">
            <Icon name="shield" />
            <div>
              <strong>Laboratorio BNA</strong>
              <small>{policy?.integracion === "REAL" ? "HTTP vía Bus configurado" : "Integración simulada"}</small>
            </div>
            <i />
          </div>
          <div className="sol-profile">
            <span className="sol-avatar">{user.nombre[0]}</span>
            <div>
              <strong>{user.nombre.split(" · ")[0]}</strong>
              <small>
                {user.rol === "EVALUADOR" ? "SIMULADOR EVA" : user.rol}
              </small>
            </div>
            <button
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
              onClick={() =>
                run(async () => {
                  await api("auth/logout", "POST", {});
                  setUser(null);
                  setSelected(null);
                })
              }
            >
              <Icon name="exit" size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="sol-work">
        <header className="sol-topbar">
          <div>
            <span>Créditos</span>
            <b>/</b>Solicitud de crédito
          </div>
          <div className="sol-topbar-right">
            <span className="sol-demo-pill">DEMO ACADÉMICA</span>
            <span className="sol-date">
              {new Date().toLocaleDateString("es-PE", {
                timeZone: "America/Lima",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
          </div>
        </header>
        <main className="sol-main">
          {notice && (
            <div
              role={notice.error ? "alert" : "status"}
              className={`sol-alert ${notice.error ? "error" : "success"}`}
            >
              <Icon name={notice.error ? "alert" : "check"} />
              {notice.text}
              <button aria-label="Cerrar aviso" onClick={() => setNotice(null)}>
                ×
              </button>
            </div>
          )}

          {view === "bandeja" && (
            <>
              <div className="sol-heading">
                <div>
                  <p className="sol-kicker">SOLICITUD DE CRÉDITO</p>
                  <h1>
                    {user.rol === "EVALUADOR"
                      ? "Consola de Evaluación simulada"
                      : "Cada solicitud, un nuevo comienzo."}
                  </h1>
                  <p>
                    {user.rol === "EVALUADOR"
                      ? "Emite respuestas de prueba para verificar el retorno hacia SOL. No representa una evaluación real de riesgo."
                      : "Prepara expedientes completos y acompaña su avance hacia Evaluación."}
                  </p>
                </div>
                {writable && (
                  <button className="sol-button primary" onClick={start}>
                    <Icon name="plus" />
                    Nueva solicitud
                  </button>
                )}
              </div>
              <div className="sol-stats">
                {[
                  {
                    label: "Solicitudes registradas",
                    value: totalApplications,
                    icon: "doc",
                    cls: "blue",
                  },
                  {
                    label: "En evaluación",
                    value: stateCounts.EN_EVALUACION || 0,
                    icon: "clock",
                    cls: "gold",
                  },
                  {
                    label: "Por subsanar",
                    value: stateCounts.OBSERVADA || 0,
                    icon: "alert",
                    cls: "red",
                  },
                  {
                    label: "Aprobadas",
                    value: stateCounts.APROBADA || 0,
                    icon: "check",
                    cls: "green",
                  },
                ].map((s) => (
                  <div className="sol-stat" key={s.label}>
                    <div>
                      <small>{s.label}</small>
                      <strong>{s.value.toString().padStart(2, "0")}</strong>
                    </div>
                    <span className={`sol-stat-icon ${s.cls}`}>
                      <Icon name={s.icon} />
                    </span>
                  </div>
                ))}
              </div>
              <section className="sol-card">
                <div className="sol-card-title">
                  <div>
                    <h2>
                      Bandeja de solicitudes <span>{totalApplications}</span>
                    </h2>
                    <p>
                      Consulta el estado y la última versión de cada expediente.
                    </p>
                  </div>
                  <button
                    className="sol-link"
                    disabled={busy}
                    onClick={() => run(refresh)}
                  >
                    Actualizar
                  </button>
                </div>
                <div className="sol-toolbar">
                  <label className="sol-search">
                    <Icon name="search" />
                    <input
                      aria-label="Buscar solicitudes"
                      placeholder="Buscar en esta página por cliente, DNI o código…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                  <select
                    aria-label="Filtrar por estado"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    {[
                      "TODAS",
                      "BORRADOR",
                      "EN_EVALUACION",
                      "OBSERVADA",
                      "APROBADA",
                      "RECHAZADA",
                    ].map((s) => (
                      <option key={s} value={s}>
                        {s === "TODAS"
                          ? "Todos los estados"
                          : s.replaceAll("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
                {filtered.length ? (
                  <div className="sol-tablewrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Solicitud / cliente</th>
                          <th>Monto solicitado</th>
                          <th>Plazo</th>
                          <th>Estado</th>
                          <th>Última actualización</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map((a) => (
                          <tr key={a.id}>
                            <td>
                              <button
                                className="sol-record"
                                onClick={() => open(a.id)}
                              >
                                <strong>{a.cliente_nombre}</strong>
                                <small>
                                  {a.codigo} · DNI {a.documento}
                                </small>
                              </button>
                            </td>
                            <td className="emphasis">
                              {amount(a.monto, a.moneda)}
                            </td>
                            <td>{a.plazo} meses</td>
                            <td>
                              <Badge state={a.estado} />
                            </td>
                            <td className="muted">
                              {dateTime(a.actualizado)}
                              <small className="sol-cell-small">
                                Versión {a.version}
                              </small>
                            </td>
                            <td>
                              <button
                                className="sol-icon-button"
                                aria-label={`Abrir ${a.codigo}`}
                                onClick={() => open(a.id)}
                              >
                                <Icon name="arrow" size={18} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="sol-empty">
                    <span>
                      <Icon name="doc" size={30} />
                    </span>
                    <h3>
                      {apps.length
                        ? "No hay resultados para esta búsqueda"
                        : "Tu primera solicitud empieza aquí"}
                    </h3>
                    <p>
                      {apps.length
                        ? "Prueba con otro nombre o estado."
                        : "Selecciona un cliente habilitado por Captación y prepara su expediente."}
                    </p>
                    {writable && !apps.length && (
                      <button className="sol-button secondary" onClick={start}>
                        Crear primera solicitud
                        <Icon name="arrow" size={16} />
                      </button>
                    )}
                  </div>
                )}
                <div className="sol-tablefoot">
                  {filtered.length} visibles · {totalApplications} solicitudes en total
                  <span>Página {Math.floor(pageOffset / 50) + 1}</span>
                  <button className="sol-link" disabled={busy || pageOffset === 0}
                    onClick={() => setPageOffset((n) => Math.max(0, n - 50))}>Anterior</button>
                  <button className="sol-link" disabled={busy || pageOffset + 50 >= totalApplications}
                    onClick={() => setPageOffset((n) => n + 50)}>Siguiente</button>
                </div>
              </section>
              <div className="sol-bottom-note">
                <Icon name="shield" />
                <p>
                  <strong>Un expediente trazable, de principio a fin.</strong>{" "}
                  Cada envío conserva condiciones, calendario y versión de
                  política. La decisión corresponde a Evaluación.
                </p>
              </div>
            </>
          )}

          {view === "editor" && policy && (
            <>
              <button
                className="sol-link"
                onClick={() => setView(selected ? "detalle" : "bandeja")}
              >
                <Icon name="back" size={16} />
                Volver a solicitudes
              </button>
              <div className="sol-heading">
                <div>
                  <p className="sol-kicker">
                    {editing
                      ? `${selected!.codigo} · VERSIÓN ${selected!.version}`
                      : "NUEVO EXPEDIENTE"}
                  </p>
                  <h1>
                    {editing ? "Editar solicitud" : "Preparemos la solicitud."}
                  </h1>
                  <p>
                    Completa los datos y revisa las condiciones antes de enviar.
                  </p>
                </div>
                <Badge state="BORRADOR" />
              </div>
              <ol className="sol-steps">
                {["Cliente", "Condiciones", "Respaldos", "Revisión"].map(
                  (s, i) => (
                    <li
                      className={
                        i === step ? "current" : i < step ? "done" : ""
                      }
                      key={s}
                    >
                      <span>
                        {i < step ? <Icon name="check" size={16} /> : i + 1}
                      </span>
                      {s}
                    </li>
                  ),
                )}
              </ol>
              <div className="sol-editor-grid">
                <section className="sol-card sol-editor-card">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (step === 0) {
                        if (!form.id_cliente)
                          return setNotice({
                            text: "Selecciona un cliente habilitado.",
                            error: true,
                          });
                        setStep(1);
                      } else if (step === 1) setStep(2);
                      else if (step === 2) calculate();
                    }}
                  >
                    {step === 0 && (
                      <>
                        <div className="sol-section-head">
                          <span>01</span>
                          <div>
                            <h2>Selecciona al solicitante</h2>
                            <p>
                              Referencias recibidas desde Captación simulada.
                            </p>
                          </div>
                        </div>
                        <div className="sol-client-list">
                          {clients.map((c) => (
                            <label
                              key={c.id_cliente}
                              className={`sol-client-option ${form.id_cliente === c.id_cliente ? "chosen" : ""} ${!eligible(c) ? "disabled" : ""}`}
                            >
                              <input
                                type="radio"
                                name="client"
                                value={c.id_cliente}
                                checked={form.id_cliente === c.id_cliente}
                                disabled={!eligible(c)}
                                onChange={() =>
                                  update("id_cliente", c.id_cliente)
                                }
                              />
                              <span className="sol-avatar">
                                {c.nombres[0]}
                                {c.apellido_paterno[0]}
                              </span>
                              <span>
                                <strong>{person(c)}</strong>
                                <small>
                                  DNI {c.numero_documento} ·{" "}
                                  {c.numero_documento}
                                </small>
                              </span>
                              <span
                                className={`sol-client-status ${eligible(c) ? "ok" : ""}`}
                              >
                                {eligible(c)
                                  ? "Habilitado"
                                  : c.estado_cliente !== "ACTIVO"
                                    ? "Cliente bloqueado"
                                    : c.vigente_hasta < today()
                                      ? "Verificación vencida"
                                      : "Captación observada"}
                              </span>
                            </label>
                          ))}
                        </div>
                      </>
                    )}
                    {step === 1 && (
                      <>
                        <div className="sol-section-head">
                          <span>02</span>
                          <div>
                            <h2>Condiciones solicitadas</h2>
                            <p>
                              Registra lo que solicita el cliente. Evaluación
                              emitirá el dictamen.
                            </p>
                          </div>
                        </div>
                        <div className="sol-form-grid">
                          <Field title="Producto">
                            <input value={policy.producto_nombre} readOnly />
                          </Field>
                          <Field title="Moneda">
                            <select
                              value={form.moneda}
                              onChange={(e) => update("moneda", e.target.value)}
                            >
                              {policy.monedas.map((m) => (
                                <option key={m}>{m}</option>
                              ))}
                            </select>
                          </Field>
                          <Field
                            title="Monto solicitado"
                            hint={`De ${amount(policy.monto_minimo, form.moneda)} a ${amount(policy.monto_maximo, form.moneda)} · Perfil DEMO`}
                          >
                            <input
                              required
                              type="number"
                              step="0.01"
                              min={policy.monto_minimo}
                              max={policy.monto_maximo}
                              value={form.monto_solicitado}
                              onChange={(e) =>
                                update("monto_solicitado", e.target.value)
                              }
                              placeholder="Ej. 15000.00"
                            />
                          </Field>
                          <Field
                            title="Plazo en meses"
                            hint={`Entre ${policy.plazo_minimo_meses} y ${policy.plazo_maximo_meses} meses`}
                          >
                            <input
                              required
                              type="number"
                              step="1"
                              min={policy.plazo_minimo_meses}
                              max={policy.plazo_maximo_meses}
                              value={form.plazo_meses}
                              onChange={(e) =>
                                update("plazo_meses", Number(e.target.value))
                              }
                            />
                          </Field>
                          <Field title="Destino del crédito">
                            <input
                              required
                              minLength={5}
                              maxLength={120}
                              value={form.destino_credito}
                              onChange={(e) =>
                                update("destino_credito", e.target.value)
                              }
                              placeholder="Ej. Mejoras en la vivienda"
                            />
                          </Field>
                          <Field
                            title="Fecha base del calendario"
                            hint={`Primera cuota ${policy.dias_por_periodo} días después.`}
                          >
                            <input
                              required
                              type="date"
                              min={today()}
                              value={form.fecha_base}
                              onChange={(e) =>
                                update("fecha_base", e.target.value)
                              }
                            />
                          </Field>
                        </div>
                        <div className="sol-info-strip">
                          <Icon name="clock" />
                          <div>
                            <strong>Pago doble pendiente de definición</strong>
                            <p>
                              El perfil inicial usa cuotas ordinarias. Los meses
                              y la fórmula se regularizarán con Créditos.
                            </p>
                          </div>
                        </div>
                      </>
                    )}
                    {step === 2 && (
                      <>
                        <div className="sol-section-head">
                          <span>03</span>
                          <div>
                            <h2>Garantías y fiadores</h2>
                            <p>
                              Registra respaldos si corresponde. La
                              obligatoriedad por producto está pendiente de
                              aprobación.
                            </p>
                          </div>
                        </div>
                        <div className="sol-subheading">
                          <h3>Garantías declaradas</h3>
                          <button
                            type="button"
                            className="sol-link"
                            disabled={form.garantias.length >= 10}
                            onClick={() =>
                              update("garantias", [
                                ...form.garantias,
                                {
                                  tipo_garantia: "PERSONAL",
                                  descripcion: "",
                                  valor_tasacion: "",
                                },
                              ])
                            }
                          >
                            <Icon name="plus" size={16} />
                            Agregar
                          </button>
                        </div>
                        {!form.garantias.length && (
                          <p className="sol-mutedbox">
                            No se han registrado garantías para esta solicitud.
                          </p>
                        )}
                        {form.garantias.map((g, i) => (
                          <div className="sol-guarantee" key={i}>
                            <div className="sol-form-grid">
                              <Field title="Tipo">
                                <select
                                  value={g.tipo_garantia}
                                  onChange={(e) =>
                                    update(
                                      "garantias",
                                      form.garantias.map((v, j) =>
                                        j === i
                                          ? {
                                              ...v,
                                              tipo_garantia: e.target.value,
                                            }
                                          : v,
                                      ),
                                    )
                                  }
                                >
                                  {[
                                    "PERSONAL",
                                    "HIPOTECARIA",
                                    "VEHICULAR",
                                    "MOBILIARIA",
                                    "FONDOS",
                                  ].map((t) => (
                                    <option key={t}>{t}</option>
                                  ))}
                                </select>
                              </Field>
                              <Field title="Valor declarado">
                                <input
                                  required
                                  type="number"
                                  min="0.01"
                                  step="0.01"
                                  value={g.valor_tasacion}
                                  onChange={(e) =>
                                    update(
                                      "garantias",
                                      form.garantias.map((v, j) =>
                                        j === i
                                          ? {
                                              ...v,
                                              valor_tasacion: e.target.value,
                                            }
                                          : v,
                                      ),
                                    )
                                  }
                                />
                              </Field>
                            </div>
                            <Field title="Descripción">
                              <input
                                required
                                minLength={5}
                                maxLength={200}
                                value={g.descripcion}
                                onChange={(e) =>
                                  update(
                                    "garantias",
                                    form.garantias.map((v, j) =>
                                      j === i
                                        ? { ...v, descripcion: e.target.value }
                                        : v,
                                    ),
                                  )
                                }
                              />
                            </Field>
                            <button
                              className="sol-link danger"
                              type="button"
                              onClick={() =>
                                update(
                                  "garantias",
                                  form.garantias.filter((_, j) => j !== i),
                                )
                              }
                            >
                              Quitar garantía
                            </button>
                          </div>
                        ))}
                        <div className="sol-subheading">
                          <h3>Fiadores con referencia de identidad</h3>
                          <span>Opcional en la demo</span>
                        </div>
                        {clients
                          .filter(
                            (c) =>
                              c.id_cliente !== form.id_cliente &&
                              c.estado_cliente === "ACTIVO",
                          )
                          .map((c) => (
                            <label className="sol-checkrow" key={c.id_cliente}>
                              <input
                                type="checkbox"
                                checked={form.fiadores.includes(c.id_cliente)}
                                onChange={(e) =>
                                  update(
                                    "fiadores",
                                    e.target.checked
                                      ? [...form.fiadores, c.id_cliente]
                                      : form.fiadores.filter(
                                          (id) => id !== c.id_cliente,
                                        ),
                                  )
                                }
                              />
                              <span>
                                <strong>{person(c)}</strong>
                                <small>
                                  DNI {c.numero_documento} · Referencia
                                  sintética validada para la demo
                                </small>
                              </span>
                            </label>
                          ))}
                        <p className="sol-caption">
                          Se guarda la referencia y su snapshot autorizado. Esta
                          versión no incluye carga de archivos ni verificación
                          externa de documentos.
                        </p>
                      </>
                    )}
                    {step === 3 && preview && (
                      <>
                        <div className="sol-section-head">
                          <span>04</span>
                          <div>
                            <h2>Revisa el expediente</h2>
                            <p>
                              El servidor validó las condiciones y calculó el
                              calendario preliminar.
                            </p>
                          </div>
                        </div>
                        <div className="sol-review">
                          <div>
                            <small>Solicitante</small>
                            <strong>{person(preview.cliente)}</strong>
                          </div>
                          <div>
                            <small>Destino</small>
                            <strong>{form.destino_credito}</strong>
                          </div>
                          <div>
                            <small>Monto / plazo</small>
                            <strong>
                              {amount(form.monto_solicitado, form.moneda)} ·{" "}
                              {form.plazo_meses} meses
                            </strong>
                          </div>
                          <div>
                            <small>Respaldos</small>
                            <strong>
                              {form.garantias.length} garantías ·{" "}
                              {form.fiadores.length} fiadores
                            </strong>
                          </div>
                        </div>
                        <CalendarTable
                          data={preview.calendario}
                          currency={form.moneda}
                        />
                      </>
                    )}
                    <div className="sol-form-actions">
                      {step > 0 ? (
                        <button
                          className="sol-button ghost"
                          type="button"
                          disabled={busy}
                          onClick={() => setStep(step - 1)}
                        >
                          <Icon name="back" size={16} />
                          Anterior
                        </button>
                      ) : (
                        <span />
                      )}
                      {step < 3 ? (
                        <button
                          className="sol-button primary"
                          disabled={busy}
                          type="submit"
                        >
                          {busy
                            ? "Calculando…"
                            : step === 2
                              ? "Calcular y revisar"
                              : "Continuar"}
                          <Icon name="arrow" size={16} />
                        </button>
                      ) : (
                        <div className="sol-action-group">
                          <button
                            type="button"
                            className="sol-button secondary"
                            disabled={busy}
                            onClick={() => save(false)}
                          >
                            Guardar borrador
                          </button>
                          <button
                            type="button"
                            className="sol-button primary"
                            disabled={busy}
                            onClick={() => save(true)}
                          >
                            {busy ? "Guardando…" : "Guardar y enviar"}
                            <Icon name="arrow" size={16} />
                          </button>
                        </div>
                      )}
                    </div>
                  </form>
                </section>
                <aside className="sol-editor-aside">
                  <div className="sol-card sol-product">
                    <span className="sol-product-icon">
                      <Icon name="doc" size={25} />
                    </span>
                    <p className="sol-kicker">PRODUCTO INICIAL</p>
                    <h3>{policy.producto_nombre}</h3>
                    <div>
                      <small>TEA ilustrativa</small>
                      <strong>
                        {(Number(policy.tea) * 100).toLocaleString("es-PE")}%
                      </strong>
                    </div>
                    <hr />
                    <p>
                      Amortización francesa.
                      <br />
                      Cuotas cada {policy.dias_por_periodo} días.
                    </p>
                    <small>Política {policy.version}</small>
                  </div>
                  <div className="sol-aside-note">
                    <Icon name="shield" />
                    <p>
                      Estos parámetros son de demostración y están pendientes de
                      aprobación por el comité.
                    </p>
                  </div>
                </aside>
              </div>
            </>
          )}

          {view === "detalle" && selected && current && (
            <>
              <button className="sol-link" onClick={() => setView("bandeja")}>
                <Icon name="back" size={16} />
                Volver a la bandeja
              </button>
              <div className="sol-heading">
                <div>
                  <p className="sol-kicker">{selected.codigo}</p>
                  <h1>{selected.cliente_nombre}</h1>
                  <p>
                    DNI {selected.documento} ·{" "}
                    {amount(selected.monto, selected.moneda)} · {selected.plazo}{" "}
                    meses
                  </p>
                </div>
                <div className="sol-action-group">
                  <button className="sol-button secondary" onClick={exportJson}>
                    <Icon name="download" size={16} />
                    Expediente JSON
                  </button>
                  <Badge state={selected.estado} />
                </div>
              </div>
              {selected.resultados.length > 0 && (
                <div
                  className={`sol-alert ${selected.estado === "OBSERVADA" ? "warning" : "neutral"}`}
                >
                  <Icon name="doc" />
                  <div>
                    <strong>
                      Último resultado de EVA simulada:{" "}
                      {selected.resultados.at(-1)!.decision}
                    </strong>
                    <p>{selected.resultados.at(-1)!.observaciones}</p>
                  </div>
                </div>
              )}
              <div className="sol-detail-actions">
                <div>
                  Versión{" "}
                  <select
                    aria-label="Versión del expediente"
                    value={version}
                    onChange={(e) => setVersion(Number(e.target.value))}
                  >
                    {selected.versiones.map((v) => (
                      <option key={v.numero} value={v.numero}>
                        v{v.numero} · {v.congelada ? "Congelada" : "Borrador"}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sol-action-group">
                  <button className="sol-link" disabled={busy} onClick={() => open(selected.id)}>Actualizar estado</button>
                  {writable && selected.estado === "BORRADOR" && (
                    <>
                      <button
                        className="sol-button secondary"
                        disabled={busy || selected.versiones.some((v) => v.numero === selected.version && v.congelada)}
                        onClick={() => edit(selected)}
                      >
                        Editar borrador
                      </button>
                      <button
                        className="sol-button primary"
                        disabled={busy}
                        onClick={sendCurrent}
                      >
                        Enviar a Evaluación
                        <Icon name="arrow" size={16} />
                      </button>
                    </>
                  )}
                  {writable && selected.estado === "OBSERVADA" && (
                    <button
                      className="sol-button primary"
                      disabled={busy}
                      onClick={revise}
                    >
                      Subsanar en nueva versión
                      <Icon name="arrow" size={16} />
                    </button>
                  )}
                  <button
                    className="sol-link"
                    onClick={() => open(selected.id)}
                    disabled={busy}
                  >
                    Actualizar
                  </button>
                </div>
              </div>
              <section className="sol-card">
                <div className="sol-tabs">
                  {["Resumen", "Calendario", "Historial", "Versiones"].map(
                    (t) => (
                      <button
                        key={t}
                        className={tab === t ? "active" : ""}
                        onClick={() => setTab(t)}
                      >
                        {t}
                      </button>
                    ),
                  )}
                </div>
                <div className="sol-detail-body">
                  {tab === "Resumen" && (
                    <>
                      <h2>Condiciones de la versión {version}</h2>
                      <div className="sol-review detail">
                        <div>
                          <small>Producto</small>
                          <strong>
                            {current.expediente.politica.producto_nombre}
                          </strong>
                        </div>
                        <div>
                          <small>Monto solicitado</small>
                          <strong>
                            {amount(
                              current.expediente.condiciones.monto_solicitado,
                              current.expediente.condiciones.moneda,
                            )}
                          </strong>
                        </div>
                        <div>
                          <small>Plazo</small>
                          <strong>
                            {current.expediente.condiciones.plazo_meses} meses
                          </strong>
                        </div>
                        <div>
                          <small>TEA ilustrativa</small>
                          <strong>
                            {(
                              Number(current.expediente.politica.tea) * 100
                            ).toLocaleString("es-PE")}
                            %
                          </strong>
                        </div>
                        <div>
                          <small>Destino</small>
                          <strong>
                            {current.expediente.condiciones.destino_credito}
                          </strong>
                        </div>
                        <div>
                          <small>Política conservada</small>
                          <strong>{current.expediente.politica.version}</strong>
                        </div>
                        <div>
                          <small>Garantías</small>
                          <strong>
                            {current.expediente.condiciones.garantias.length}{" "}
                            registradas
                          </strong>
                        </div>
                        <div>
                          <small>Fiadores</small>
                          <strong>
                            {current.expediente.fiadores.length} asociados
                          </strong>
                        </div>
                      </div>
                      <div className="sol-info-strip">
                        <Icon name="shield" />
                        <div>
                          <strong>Referencia de Captación simulada</strong>
                          <p>
                            Caso: {current.expediente.cliente.id_caso}
                            <br />
                            Verificación:{" "}
                            {current.expediente.cliente.id_verificacion}
                          </p>
                        </div>
                      </div>
                      {current.expediente.condiciones.garantias.map((g, i) => (
                        <p key={i} className="sol-mutedbox">
                          {g.tipo_garantia} · {g.descripcion} ·{" "}
                          {amount(
                            g.valor_tasacion,
                            current.expediente.condiciones.moneda,
                          )}
                        </p>
                      ))}
                    </>
                  )}
                  {tab === "Calendario" && (
                    <CalendarTable
                      key={version}
                      data={current.expediente.calendario}
                      currency={current.expediente.condiciones.moneda}
                    />
                  )}{" "}
                  {tab === "Historial" && (
                    <>
                      <h2>Trazabilidad del expediente</h2>
                      <div className="sol-timeline">
                        {selected.eventos.map((e, i) => (
                          <div key={i}>
                            <span>
                              <Icon name="check" size={13} />
                            </span>
                            <div>
                              <strong>{e.accion.replaceAll("_", " ")}</strong>
                              <p>
                                {e.actor} · Versión {e.version} ·{" "}
                                {dateTime(e.fecha)}
                              </p>
                              <small>
                                {e.estado_anterior || "INICIO"} →{" "}
                                {e.estado_nuevo}
                                <br />
                                Correlación: {e.correlacion}
                              </small>
                            </div>
                          </div>
                        ))}
                      </div>
                      {selected.envios.map((e) => (
                        <p className="sol-mutedbox" key={e.id_operacion}>
                          <strong>
                            {e.estado_transporte === "CONFIRMADO" ? (policy?.integracion === "REAL" ? "Acuse de Evaluación" : "Acuse de recepción EVA simulada") : "Envío pendiente de confirmación"} · v{e.version}
                          </strong>
                          <br />
                          {e.acuse || e.estado_transporte}
                          <br />
                          Operación: {e.id_operacion}
                        </p>
                      ))}
                    </>
                  )}
                  {tab === "Versiones" && (
                    <>
                      <h2>Versiones conservadas</h2>
                      <p className="sol-caption">
                        Una corrección crea otra versión. Las condiciones ya
                        enviadas se conservan.
                      </p>
                      {selected.versiones.map((v) => (
                        <div className="sol-version-row" key={v.numero}>
                          <span>v{v.numero}</span>
                          <div>
                            <strong>
                              {amount(
                                v.expediente.condiciones.monto_solicitado,
                                v.expediente.condiciones.moneda,
                              )}{" "}
                              · {v.expediente.condiciones.plazo_meses} meses
                            </strong>
                            <small>
                              {v.expediente.politica.version} ·{" "}
                              {v.congelada
                                ? "Congelada: no editable"
                                : "Borrador editable"}
                            </small>
                          </div>
                          <button
                            className="sol-link"
                            onClick={() => {
                              setVersion(v.numero);
                              setTab("Resumen");
                            }}
                          >
                            Consultar
                            <Icon name="arrow" size={16} />
                          </button>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </section>
              {user.rol === "EVALUADOR" &&
                selected.estado === "EN_EVALUACION" && (
                  <section className="sol-card sol-simulator">
                    <p className="sol-kicker">
                      HERRAMIENTA DE PRUEBA · EVA SIMULADA
                    </p>
                    <h2>Enviar un resultado a Solicitud</h2>
                    <p>
                      Este control verifica CR-INT-03. No calcula scoring ni
                      decide sobre un crédito real.
                    </p>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        run(async () => {
                          const d = await api<Detail>(
                            `applications/${selected.id}/demo-result`,
                            "POST",
                            {
                              version: selected.version,
                              decision,
                              observaciones: observation,
                            },
                            crypto.randomUUID(),
                          );
                          setSelected(d);
                          setObservation("");
                          await refresh();
                          setNotice({
                            text: "Resultado simulado recibido y registrado por SOL.",
                            error: false,
                          });
                        });
                      }}
                    >
                      <div className="sol-form-grid">
                        <Field title="Dictamen de prueba">
                          <select
                            value={decision}
                            onChange={(e) => setDecision(e.target.value)}
                          >
                            {["OBSERVADO", "APROBADO", "RECHAZADO"].map((d) => (
                              <option key={d}>{d}</option>
                            ))}
                          </select>
                        </Field>
                        <Field title="Observación / sustento">
                          <input
                            required
                            minLength={5}
                            maxLength={1000}
                            placeholder="Ej. Precisar el destino del crédito"
                            value={observation}
                            onChange={(e) => setObservation(e.target.value)}
                          />
                        </Field>
                      </div>
                      <button className="sol-button primary" disabled={busy}>
                        Enviar resultado simulado
                        <Icon name="arrow" size={16} />
                      </button>
                    </form>
                  </section>
                )}
            </>
          )}

          {view === "politicas" && policy && (
            <>
              <div className="sol-heading">
                <div>
                  <p className="sol-kicker">REGLAS Y PARÁMETROS</p>
                  <h1>Políticas de crédito</h1>
                  <p>
                    La configuración se consulta desde el servidor y se conserva
                    con cada versión.
                  </p>
                </div>
                <span className="sol-demo-pill">PROPUESTA PARA EL COMITÉ</span>
              </div>
              <section className="sol-card sol-detail-body">
                <h2>{policy.producto_nombre}</h2>
                <div className="sol-review detail">
                  <div>
                    <small>Monto mínimo</small>
                    <strong>{amount(policy.monto_minimo)}</strong>
                  </div>
                  <div>
                    <small>Monto máximo</small>
                    <strong>{amount(policy.monto_maximo)}</strong>
                  </div>
                  <div>
                    <small>Plazo</small>
                    <strong>
                      {policy.plazo_minimo_meses}–{policy.plazo_maximo_meses}{" "}
                      meses
                    </strong>
                  </div>
                  <div>
                    <small>TEA ilustrativa</small>
                    <strong>{Number(policy.tea) * 100}%</strong>
                  </div>
                  <div>
                    <small>Monedas habilitadas</small>
                    <strong>{policy.monedas.join(", ")}</strong>
                  </div>
                  <div>
                    <small>Versión</small>
                    <strong>{policy.version}</strong>
                  </div>
                </div>
                <div className="sol-alert warning">
                  <Icon name="alert" />
                  <div>
                    <strong>Pendiente de aprobación institucional</strong>
                    <p>
                      La tasa y los plazos proceden del catálogo del
                      repositorio. Los montos son una propuesta de alcance
                      académico. {policy.nota}
                    </p>
                  </div>
                </div>
                <p className="sol-caption">
                  Los asesores no modifican políticas desde esta pantalla. Los
                  cambios se gestionan con el comité y quedan versionados.
                </p>
              </section>
            </>
          )}

          {view === "integraciones" && (
            <>
              <div className="sol-heading">
                <div>
                  <p className="sol-kicker">LÍNEA DE CRÉDITOS</p>
                  <h1>Conexiones del módulo</h1>
                  <p>
                    Contratos de demostración preparados para coordinar la
                    integración.
                  </p>
                </div>
                <span className="sol-demo-pill">{policy?.integracion === "REAL" ? "HTTP VÍA BUS · VALIDACIÓN PENDIENTE" : "SERVICIOS SIMULADOS"}</span>
              </div>
              <div className="sol-integration-grid">
                {[
                  {
                    id: "CR-INT-01",
                    name: "Captación → Solicitud",
                    description:
                      "Referencia del cliente, caso y evidencia habilitante. Incluye casos habilitados, observados y vencidos para las pruebas.",
                  },
                  {
                    id: "CR-INT-02",
                    name: "Solicitud → Evaluación",
                    description:
                      "Expediente congelado, versión, correlación y operación. Se consulta la recepción antes de repetir un envío.",
                  },
                  {
                    id: "CR-INT-03",
                    name: "Evaluación → Solicitud",
                    description:
                      "Dictamen y observaciones sobre la versión enviada. En HTTP se valida la evaluación y su ronda; la cuenta demo solo funciona en modo SIMULADO.",
                  },
                  {
                    id: "CR-INT-10",
                    name: "Eventos y auditoría",
                    description:
                      "Eventos persistidos con identificador estable. La cola espera confirmación y recupera pendientes; el acuse demo se distingue de la confirmación central.",
                  },
                ].map((c) => (
                  <section className="sol-card sol-integration" key={c.id}>
                    <span>{c.id}</span>
                    <h2>{c.name}</h2>
                    <p>{c.description}</p>
                    <Badge state={policy?.integracion === "REAL" ? "HTTP CONFIGURADO" : "SIMULADO"} />
                  </section>
                ))}
              </div>
              <div className="sol-bottom-note">
                <Icon name="link" />
                <p>
                  SOL formaliza el expediente y recibe resultados. La
                  autorización hacia Desembolso pertenece a Evaluación. Este MVP
                  no ejecuta movimientos de dinero.
                </p>
              </div>
            </>
          )}

          {!policy && (
            <div className="sol-alert warning">
              <Icon name="alert" />
              No se pudo cargar la configuración.
              <button className="sol-link" onClick={() => run(refresh)}>
                Reintentar
              </button>
            </div>
          )}
        </main>
        <footer className="sol-footer">
          <span>BNA · Solicitud de Crédito</span>
          <span>Prototipo académico · UCSM · 2026</span>
        </footer>
      </div>
    </div>
  );
}
