"use client";

/**
 * Módulo de Cuentas (linea Ahorros).
 * Todas las llamadas pasan por el puente de Next /api/cuenta, que reenvía el JWT
 * y las cabeceras de operación a CUENTAS (/api/v1/cuentas, puerto 8001).
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

const TOKEN_KEY = "bna_access_token";
const USER_KEY = "bna_usuario";
const CLIENTE_INICIAL = "DEV001";
const AGENCIA_INICIAL = "AQP01";
const CANAL = "VEN"; // Ventanilla: canal con tope diario definido en el CORE.

type Cuenta = {
  num_cuenta: string;
  cci: string;
  moneda: string;
  regimen: string;
  estado_cuenta: string;
  saldo_contable: string | number;
  saldo_disponible: string | number;
  id_agencia?: string | null;
  titulares?: string[];
};

type Movimiento = {
  uuid_transaccion?: string;
  tipo_operacion?: string;
  naturaleza?: string;
  monto?: string | number;
  moneda?: string;
  glosa?: string;
  id_canal?: string;
  estado_transaccion?: string;
  fecha_hora?: string;
  [clave: string]: unknown;
};

type Usuario = {
  username?: string;
  nombre?: string;
  rol?: string;
};

type Vista = "resumen" | "apertura" | "operaciones" | "movimientos";
type ModoOperacion = "deposito" | "retiro" | "transferencia";

const NAV: { id: Vista; label: string }[] = [
  { id: "resumen", label: "Resumen de cuentas" },
  { id: "apertura", label: "Abrir cuenta" },
  { id: "operaciones", label: "Depósitos y retiros" },
  { id: "movimientos", label: "Movimientos" },
];

const TITULO_VISTA: Record<Vista, string> = {
  resumen: "Resumen de cuentas",
  apertura: "Apertura de cuenta",
  operaciones: "Operaciones",
  movimientos: "Movimientos",
};

const NOMBRE_OPERACION: Record<ModoOperacion, string> = {
  deposito: "Depósito",
  retiro: "Retiro",
  transferencia: "Transferencia",
};

function numero(valor: unknown): number {
  const n = Number(valor ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function dinero(valor: unknown, moneda = "PEN"): string {
  const simbolo = moneda.toUpperCase() === "USD" ? "US$" : "S/";
  return `${simbolo} ${new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numero(valor))}`;
}

function fechaHora(valor?: string): string {
  if (!valor) return "—";
  const fecha = new Date(valor);
  if (Number.isNaN(fecha.getTime())) return valor;
  return fecha.toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short" });
}

function mensajeDeError(cuerpo: unknown, status: number): string {
  if (cuerpo && typeof cuerpo === "object") {
    const datos = cuerpo as Record<string, unknown>;
    const error = datos.error as Record<string, unknown> | undefined;
    const detalles = datos.details ?? datos.detail;
    const base =
      datos.message ??
      error?.message ??
      (typeof datos.detail === "string" ? datos.detail : undefined);
    if (typeof base === "string" && base) {
      const header =
        detalles && !Array.isArray(detalles) && typeof detalles === "object" && "header" in detalles
          ? ` (header: ${String((detalles as Record<string, unknown>).header)})`
          : "";
      const codigo = datos.error_code ? ` [${String(datos.error_code)}]` : "";
      return `${base}${header}${codigo}`;
    }
    if (Array.isArray(detalles)) {
      return detalles
        .map((d: unknown) => {
          if (!d || typeof d !== "object") return String(d);
          const item = d as Record<string, unknown>;
          const loc = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
          return `${loc}: ${String(item.msg ?? "")}`.trim();
        })
        .join(" · ");
    }
  }
  if (status === 401) return "Sesión no válida o vencida. Vuelve a iniciar sesión.";
  if (status === 403) return "Tu usuario no tiene permisos para esta operación.";
  if (status === 503) return "No se pudo contactar al servicio CUENTAS.";
  return `Error HTTP ${status}.`;
}

/** Llama al puente /api/cuenta y devuelve el campo `data` del sobre ITIL-02. */
async function pedir<T>(ruta: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const respuesta = await fetch(`/api/cuenta/${ruta}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const texto = await respuesta.text();
  let cuerpo: unknown = null;
  try {
    cuerpo = texto ? JSON.parse(texto) : null;
  } catch {
    cuerpo = null;
  }

  if (!respuesta.ok) throw new Error(mensajeDeError(cuerpo, respuesta.status));

  if (cuerpo && typeof cuerpo === "object" && "data" in cuerpo) {
    return (cuerpo as { data: T }).data;
  }
  return cuerpo as T;
}

function normalizarMovimientos(valor: unknown): Movimiento[] {
  if (Array.isArray(valor)) return valor as Movimiento[];
  if (valor && typeof valor === "object") {
    const objeto = valor as Record<string, unknown>;
    for (const clave of ["movimientos", "items", "data"]) {
      if (Array.isArray(objeto[clave])) return objeto[clave] as Movimiento[];
    }
  }
  return [];
}

/** CUENTAS exige estas cabeceras en toda operación que mueve dinero. */
function cabecerasDeOperacion(): Record<string, string> {
  return {
    "X-Idempotency-Key": crypto.randomUUID(),
    "X-Channel-ID": CANAL,
    "X-Request-Timestamp": new Date().toISOString(),
  };
}

function textoError(error: unknown): string {
  return error instanceof Error ? error.message : "Ocurrió un error inesperado.";
}

export default function CuentaPage() {
  const router = useRouter();

  // Sesión
  const [token, setToken] = useState<string | null | undefined>(undefined);
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  // Navegación
  const [vista, setVista] = useState<Vista>("resumen");

  // Cuentas
  const [cliente, setCliente] = useState(CLIENTE_INICIAL);
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);
  const [seleccionada, setSeleccionada] = useState<Cuenta | null>(null);
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [detalleMovimiento, setDetalleMovimiento] = useState<Movimiento | null>(null);
  const [uuidBusqueda, setUuidBusqueda] = useState("");

  // Apertura
  const [numCuenta, setNumCuenta] = useState("");
  const [cci, setCci] = useState("");
  const [moneda, setMoneda] = useState("PEN");
  const [regimen, setRegimen] = useState("INDIVIDUAL");
  const [agencia, setAgencia] = useState(AGENCIA_INICIAL);
  const [titulares, setTitulares] = useState(CLIENTE_INICIAL);

  // Operaciones
  const [modo, setModo] = useState<ModoOperacion>("deposito");
  const [numOperacion, setNumOperacion] = useState("");
  const [origen, setOrigen] = useState("");
  const [destino, setDestino] = useState("");
  const [monto, setMonto] = useState("");
  const [glosa, setGlosa] = useState("");

  // Estado de interfaz
  const [cargando, setCargando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; error: boolean } | null>(null);

  useEffect(() => {
    let activo = true;

    // La sesión vive en localStorage: se lee en un callback asíncrono para no
    // encadenar renders dentro del cuerpo del efecto.
    (async () => {
      const guardado = localStorage.getItem(TOKEN_KEY);
      if (!activo) return;
      setToken(guardado);

      try {
        const crudo = localStorage.getItem(USER_KEY);
        if (activo) setUsuario(crudo ? (JSON.parse(crudo) as Usuario) : null);
      } catch {
        if (activo) setUsuario(null);
      }

      if (!guardado) return;

      setCargando(true);
      try {
        const lista = await pedir<Cuenta[]>(
          `consolidada/${encodeURIComponent(CLIENTE_INICIAL)}`,
          guardado,
        );
        if (!activo) return;
        const arreglo = Array.isArray(lista) ? lista : [];
        setCuentas(arreglo);

        const primera = arreglo[0];
        if (primera) {
          const detalle = await pedir<Cuenta>(
            encodeURIComponent(primera.num_cuenta),
            guardado,
          );
          if (!activo) return;
          setSeleccionada(detalle);

          const movs = await pedir<unknown>(
            `${encodeURIComponent(primera.num_cuenta)}/movimientos`,
            guardado,
          );
          if (activo) setMovimientos(normalizarMovimientos(movs));
        }
      } catch (error) {
        if (activo) setAviso({ texto: textoError(error), error: true });
      } finally {
        if (activo) setCargando(false);
      }
    })();

    return () => {
      activo = false;
    };
  }, []);

  const saldos = cuentas.reduce<Record<string, number>>((acumulado, cuenta) => {
    const codigo = (cuenta.moneda || "PEN").toUpperCase();
    acumulado[codigo] = (acumulado[codigo] || 0) + numero(cuenta.saldo_disponible);
    return acumulado;
  }, {});

  function cerrarSesion() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    router.push("/login");
  }

  async function traerMovimientos(numCuentaConsultada: string): Promise<Movimiento[]> {
    const datos = await pedir<unknown>(
      `${encodeURIComponent(numCuentaConsultada)}/movimientos`,
      token ?? null,
    );
    return normalizarMovimientos(datos);
  }

  async function cargarCuentas(codigo = cliente) {
    if (!token) return;
    const limpio = codigo.trim();
    if (!limpio) {
      setAviso({ texto: "Indica el código del cliente (por ejemplo DEV001).", error: true });
      return;
    }

    setCargando(true);
    setAviso(null);
    setDetalleMovimiento(null);
    try {
      const lista = await pedir<Cuenta[]>(
        `consolidada/${encodeURIComponent(limpio)}`,
        token,
      );
      const arreglo = Array.isArray(lista) ? lista : [];
      setCuentas(arreglo);

      if (!arreglo.length) {
        setSeleccionada(null);
        setMovimientos([]);
        setAviso({ texto: `El cliente ${limpio} no tiene cuentas registradas.`, error: false });
        return;
      }

      const detalle = await pedir<Cuenta>(
        encodeURIComponent(arreglo[0].num_cuenta),
        token,
      );
      setSeleccionada(detalle);
      setMovimientos(await traerMovimientos(arreglo[0].num_cuenta));
    } catch (error) {
      setCuentas([]);
      setSeleccionada(null);
      setMovimientos([]);
      setAviso({ texto: textoError(error), error: true });
    } finally {
      setCargando(false);
    }
  }

  async function verCuenta(numCuentaConsultada: string) {
    if (!token) return;
    setCargando(true);
    setAviso(null);
    setDetalleMovimiento(null);
    try {
      const detalle = await pedir<Cuenta>(
        encodeURIComponent(numCuentaConsultada),
        token,
      );
      setSeleccionada(detalle);
      setCuentas((actuales) =>
        actuales.map((cuenta) =>
          cuenta.num_cuenta === detalle.num_cuenta ? detalle : cuenta,
        ),
      );
      setMovimientos(await traerMovimientos(numCuentaConsultada));
    } catch (error) {
      setAviso({ texto: textoError(error), error: true });
    } finally {
      setCargando(false);
    }
  }

  async function abrirCuenta(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!token) return;

    const ids = titulares
      .split(/[,\s;]+/)
      .map((valor) => valor.trim())
      .filter(Boolean);

    if (!numCuenta.trim()) {
      setAviso({ texto: "El número de cuenta es obligatorio.", error: true });
      return;
    }
    if (!/^\d{20}$/.test(cci.trim())) {
      setAviso({ texto: "El CCI debe tener exactamente 20 dígitos.", error: true });
      return;
    }
    if (!ids.length) {
      setAviso({ texto: "Indica al menos un código de cliente titular.", error: true });
      return;
    }
    if (new Set(ids).size !== ids.length) {
      setAviso({ texto: "Un titular está repetido.", error: true });
      return;
    }
    if (regimen === "INDIVIDUAL" && ids.length !== 1) {
      setAviso({ texto: "Una cuenta INDIVIDUAL tiene un solo titular.", error: true });
      return;
    }
    if (regimen.startsWith("MANCOMUNADA") && ids.length < 2) {
      setAviso({ texto: "Una cuenta mancomunada requiere al menos 2 titulares.", error: true });
      return;
    }

    setCargando(true);
    setAviso(null);
    try {
      const creada = await pedir<Cuenta>("apertura", token, {
        method: "POST",
        body: JSON.stringify({
          num_cuenta: numCuenta.trim(),
          cci: cci.trim(),
          moneda,
          regimen,
          id_agencia: agencia.trim() || null,
          titulares: ids.map((id) => ({ id_cliente: id })),
        }),
      });

      setAviso({
        texto: `Cuenta ${creada.num_cuenta} creada correctamente en CUENTAS.`,
        error: false,
      });
      setCliente(ids[0]);
      setSeleccionada(creada);
      setMovimientos([]);
      setDetalleMovimiento(null);
      setVista("resumen");

      const lista = await pedir<Cuenta[]>(
        `consolidada/${encodeURIComponent(ids[0])}`,
        token,
      );
      setCuentas(Array.isArray(lista) ? lista : []);

      setNumCuenta("");
      setCci("");
      setTitulares("");
    } catch (error) {
      setAviso({ texto: textoError(error), error: true });
    } finally {
      setCargando(false);
    }
  }

  async function operar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!token) return;

    const montoLimpio = monto.trim();
    if (!/^\d+(\.\d{1,2})?$/.test(montoLimpio) || Number(montoLimpio) <= 0) {
      setAviso({ texto: "El monto debe ser mayor que 0 y tener hasta 2 decimales.", error: true });
      return;
    }

    const cuentaOrigen = modo === "transferencia" ? origen.trim() : numOperacion.trim();
    if (!cuentaOrigen) {
      setAviso({ texto: "Indica la cuenta de origen.", error: true });
      return;
    }
    if (modo === "transferencia") {
      if (!destino.trim()) {
        setAviso({ texto: "Indica la cuenta de destino.", error: true });
        return;
      }
      if (destino.trim() === cuentaOrigen) {
        setAviso({ texto: "La cuenta origen y destino no pueden ser la misma.", error: true });
        return;
      }
    }

    setCargando(true);
    setAviso(null);
    try {
      if (modo === "transferencia") {
        const resultado = await pedir<{
          uuid_debito: string;
          uuid_abono: string;
          replay?: boolean;
        }>("transferencia", token, {
          method: "POST",
          headers: cabecerasDeOperacion(),
          body: JSON.stringify({
            num_cuenta_origen: cuentaOrigen,
            num_cuenta_destino: destino.trim(),
            monto: montoLimpio,
            glosa: glosa.trim() || undefined,
          }),
        });
        setAviso({
          texto: `Transferencia registrada. Débito ${resultado.uuid_debito}, abono ${
            resultado.uuid_abono
          }${resultado.replay ? " (replay)" : ""}.`,
          error: false,
        });
      } else {
        const resultado = await pedir<{ uuid_transaccion: string; replay?: boolean }>(
          modo,
          token,
          {
            method: "POST",
            headers: cabecerasDeOperacion(),
            body: JSON.stringify({
              num_cuenta: cuentaOrigen,
              monto: montoLimpio,
              glosa: glosa.trim() || undefined,
            }),
          },
        );
        setAviso({
          texto: `${NOMBRE_OPERACION[modo]} registrado. UUID ${resultado.uuid_transaccion}${
            resultado.replay ? " (replay)" : ""
          }.`,
          error: false,
        });
      }

      setMonto("");
      setGlosa("");

      const detalle = await pedir<Cuenta>(encodeURIComponent(cuentaOrigen), token);
      setSeleccionada(detalle);
      setCuentas((actuales) =>
        actuales.map((cuenta) =>
          cuenta.num_cuenta === detalle.num_cuenta ? detalle : cuenta,
        ),
      );
      setMovimientos(await traerMovimientos(cuentaOrigen));
    } catch (error) {
      setAviso({ texto: textoError(error), error: true });
    } finally {
      setCargando(false);
    }
  }

  async function consultarMovimiento(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!token) return;
    const uuid = uuidBusqueda.trim();
    if (!uuid) {
      setAviso({ texto: "Indica el uuid_transaccion del movimiento.", error: true });
      return;
    }

    setCargando(true);
    setAviso(null);
    try {
      const detalle = await pedir<Movimiento>(
        `movimiento/${encodeURIComponent(uuid)}`,
        token,
      );
      setDetalleMovimiento(detalle);
    } catch (error) {
      setDetalleMovimiento(null);
      setAviso({ texto: textoError(error), error: true });
    } finally {
      setCargando(false);
    }
  }

  if (token === undefined) {
    return (
      <main className="sol-main">
        <div className="sol-empty">
          <h3>Comprobando sesión…</h3>
          <p>Validando el token guardado en este navegador.</p>
        </div>
      </main>
    );
  }

  if (token === null) {
    return (
      <main className="sol-main">
        <div className="sol-card" style={{ maxWidth: 560, margin: "60px auto" }}>
          <div className="sol-empty">
            <h3>Necesitas iniciar sesión</h3>
            <p>
              El módulo de cuentas usa el JWT de COREDB. Sin token, las rutas responden
              401.
            </p>
            <Link className="sol-button primary" href="/login">
              Ir a /login
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const inicial = (usuario?.nombre || usuario?.username || "BNA").trim().charAt(0).toUpperCase();

  return (
    <div className="sol-shell">
      <aside className="sol-sidebar">
        <div className="sol-brand light">
          <div>
            <strong>
              BNA<span>●</span>
            </strong>
            <small>Banco Nacional de Arequipa</small>
          </div>
        </div>

        <div className="sol-workspace">
          <span className="sol-workspace-dot" />
          Cuentas · Arequipa Centro
          <small>MÓDULO DE AHORROS</small>
        </div>

        <nav aria-label="Navegación de Cuentas">
          <p>GESTIÓN DE CUENTAS</p>
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className={vista === item.id ? "active" : ""}
              onClick={() => {
                setVista(item.id);
                setAviso(null);
              }}
            >
              {item.label}
              {item.id === "resumen" && <span>{cuentas.length}</span>}
            </button>
          ))}
        </nav>

        <div className="sol-sidebar-bottom">
          <div className="sol-lab">
            <div>
              <strong>API CUENTAS</strong>
              <small>/api/cuenta → puerto 8001</small>
            </div>
          </div>
          <div className="sol-profile">
            <span className="sol-avatar">{inicial}</span>
            <div>
              <strong>{usuario?.nombre || usuario?.username || "Sesión activa"}</strong>
              <small>{usuario?.rol || "USUARIO"}</small>
            </div>
            <button type="button" title="Cerrar sesión" aria-label="Cerrar sesión" onClick={cerrarSesion}>
              ⏻
            </button>
          </div>
        </div>
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div>
            <span>Cuentas</span>
            <b>/</b>
            {TITULO_VISTA[vista]}
          </div>
          <div className="sol-topbar-right">
            <span className="sol-demo-pill">DEMO ACADÉMICA</span>
            <span className="sol-date">
              {new Date().toLocaleDateString("es-PE", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
          </div>
        </header>

        <main className="sol-main">
          {aviso && (
            <div
              role={aviso.error ? "alert" : "status"}
              className={`sol-alert ${aviso.error ? "error" : "success"}`}
            >
              <span>{aviso.error ? "⚠" : "✓"}</span>
              <p>{aviso.texto}</p>
              <button type="button" aria-label="Cerrar aviso" onClick={() => setAviso(null)}>
                ×
              </button>
            </div>
          )}

          <div className="sol-heading">
            <div>
              <p className="sol-kicker">MÓDULO DE CUENTAS</p>
              <h1>Tus cuentas, en un solo lugar.</h1>
              <p>
                Consulta saldos, abre cuentas y registra depósitos, retiros y
                transferencias usando la API de CUENTAS y el JWT de COREDB.
              </p>
            </div>
            <div className="sol-action-group">
              <button
                type="button"
                className="sol-button secondary"
                disabled={cargando}
                onClick={() => void cargarCuentas()}
              >
                {cargando ? "Consultando…" : "Actualizar"}
              </button>
            </div>
          </div>

          {vista === "resumen" && (
            <>
              <div className="sol-stats">
                <div className="sol-stat">
                  <div>
                    <small>Cuentas del cliente</small>
                    <strong>{String(cuentas.length).padStart(2, "0")}</strong>
                  </div>
                  <span className="sol-stat-icon blue">▤</span>
                </div>
                <div className="sol-stat">
                  <div>
                    <small>Saldo disponible PEN</small>
                    <strong>{dinero(saldos.PEN ?? 0, "PEN")}</strong>
                  </div>
                  <span className="sol-stat-icon green">S/</span>
                </div>
                <div className="sol-stat">
                  <div>
                    <small>Saldo disponible USD</small>
                    <strong>{dinero(saldos.USD ?? 0, "USD")}</strong>
                  </div>
                  <span className="sol-stat-icon gold">US$</span>
                </div>
                <div className="sol-stat">
                  <div>
                    <small>Movimientos cargados</small>
                    <strong>{String(movimientos.length).padStart(2, "0")}</strong>
                  </div>
                  <span className="sol-stat-icon red">↕</span>
                </div>
              </div>

              <section className="sol-card" style={{ marginBottom: 20 }}>
                <div className="sol-card-title">
                  <div>
                    <h2>Cuentas del cliente</h2>
                    <p>GET /api/cuenta/consolidada/{"{id_cliente}"}</p>
                  </div>
                  <span className="sol-badge">{cliente || "sin código"}</span>
                </div>
                <div className="sol-toolbar">
                  <div className="sol-search">
                    <span>⌕</span>
                    <input
                      value={cliente}
                      onChange={(evento) => setCliente(evento.target.value)}
                      placeholder="Código de cliente (DEV001)"
                      aria-label="Código de cliente"
                    />
                  </div>
                  <button
                    type="button"
                    className="sol-button primary"
                    disabled={cargando || !cliente.trim()}
                    onClick={() => void cargarCuentas()}
                  >
                    Buscar cuentas
                  </button>
                </div>

                {cuentas.length === 0 ? (
                  <div className="sol-empty">
                    <h3>Sin cuentas para mostrar</h3>
                    <p>Busca un cliente existente o abre su primera cuenta.</p>
                    <button
                      type="button"
                      className="sol-button secondary"
                      onClick={() => setVista("apertura")}
                    >
                      Abrir una cuenta
                    </button>
                  </div>
                ) : (
                  <div className="sol-tablewrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Número</th>
                          <th>CCI</th>
                          <th>Régimen</th>
                          <th>Moneda</th>
                          <th>Estado</th>
                          <th className="num">Saldo disponible</th>
                          <th>Titulares</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {cuentas.map((cuenta) => (
                          <tr key={cuenta.num_cuenta}>
                            <td className="emphasis">{cuenta.num_cuenta}</td>
                            <td className="muted">{cuenta.cci}</td>
                            <td>{cuenta.regimen}</td>
                            <td>{cuenta.moneda}</td>
                            <td>
                              <span className="sol-badge">
                                <span />
                                {cuenta.estado_cuenta}
                              </span>
                            </td>
                            <td className="num emphasis">
                              {dinero(cuenta.saldo_disponible, cuenta.moneda)}
                            </td>
                            <td className="muted">
                              {(cuenta.titulares || []).join(", ") || "—"}
                            </td>
                            <td className="num">
                              <button
                                type="button"
                                className="sol-link"
                                disabled={cargando}
                                onClick={() => void verCuenta(cuenta.num_cuenta)}
                              >
                                Ver detalle
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {seleccionada && (
                <section className="sol-card">
                  <div className="sol-card-title">
                    <div>
                      <h2>
                        Cuenta {seleccionada.num_cuenta} <span>{seleccionada.estado_cuenta}</span>
                      </h2>
                      <p>
                        GET /api/cuenta/{seleccionada.num_cuenta} ·{" "}
                        {seleccionada.regimen} · {seleccionada.moneda}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="sol-link"
                      disabled={cargando}
                      onClick={() => void verCuenta(seleccionada.num_cuenta)}
                    >
                      Actualizar detalle
                    </button>
                  </div>

                  <div className="sol-detail-body">
                    <div className="sol-metrics">
                      <div>
                        <small>Saldo contable</small>
                        <strong>{dinero(seleccionada.saldo_contable, seleccionada.moneda)}</strong>
                      </div>
                      <div>
                        <small>Saldo disponible</small>
                        <strong>{dinero(seleccionada.saldo_disponible, seleccionada.moneda)}</strong>
                      </div>
                      <div>
                        <small>Agencia</small>
                        <strong>{seleccionada.id_agencia || "—"}</strong>
                      </div>
                    </div>

                    <div className="sol-review detail">
                      <div>
                        <small>CCI</small>
                        <strong>{seleccionada.cci}</strong>
                      </div>
                      <div>
                        <small>Régimen</small>
                        <strong>{seleccionada.regimen}</strong>
                      </div>
                      <div>
                        <small>Titulares</small>
                        <strong>{(seleccionada.titulares || []).join(", ") || "—"}</strong>
                      </div>
                    </div>

                    <div className="sol-subheading">
                      <h2>Movimientos de la cuenta</h2>
                      <span>{movimientos.length} registros</span>
                    </div>

                    {movimientos.length === 0 ? (
                      <div className="sol-mutedbox">
                        La cuenta aún no tiene movimientos o no se pudieron cargar.
                      </div>
                    ) : (
                      <div className="sol-tablewrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Fecha</th>
                              <th>Tipo</th>
                              <th>Glosa</th>
                              <th className="num">Monto</th>
                              <th>Canal</th>
                              <th>Estado</th>
                            </tr>
                          </thead>
                          <tbody>
                            {movimientos.map((movimiento, indice) => {
                              const esDebito =
                                String(movimiento.naturaleza || "").toUpperCase() === "D";
                              return (
                                <tr key={movimiento.uuid_transaccion || indice}>
                                  <td className="muted">{fechaHora(movimiento.fecha_hora)}</td>
                                  <td>{movimiento.tipo_operacion || "—"}</td>
                                  <td>{movimiento.glosa || "—"}</td>
                                  <td className="num emphasis">
                                    {esDebito ? "− " : "+ "}
                                    {dinero(movimiento.monto, movimiento.moneda || seleccionada.moneda)}
                                  </td>
                                  <td className="muted">{movimiento.id_canal || "—"}</td>
                                  <td>
                                    <span className="sol-badge">
                                      <span />
                                      {movimiento.estado_transaccion || "—"}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </section>
              )}
            </>
          )}

          {vista === "apertura" && (
            <section className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Abrir cuenta de ahorros</h2>
                  <p>POST /api/cuenta/apertura</p>
                </div>
                <span className="sol-badge">CUENTAS :8001</span>
              </div>

              <div className="sol-detail-body">
                <div className="sol-info-strip">
                  <span>ⓘ</span>
                  <div>
                    <strong>Reglas de titulares</strong>
                    <p>
                      INDIVIDUAL exige 1 titular. MANCOMUNADA_INDISTINTA y
                      MANCOMUNADA_CONJUNTA exigen al menos 2. El CCI debe tener 20
                      dígitos y los clientes deben existir y poder operar en COREDB.
                    </p>
                  </div>
                </div>

                <form onSubmit={abrirCuenta}>
                  <div className="sol-form-grid">
                    <div className="sol-field">
                      <label htmlFor="num-cuenta">Número de cuenta</label>
                      <input
                        id="num-cuenta"
                        value={numCuenta}
                        onChange={(evento) => setNumCuenta(evento.target.value)}
                        placeholder="1234567890"
                        maxLength={20}
                        required
                      />
                      <small>Máximo 20 caracteres. Lo define el CORE.</small>
                    </div>

                    <div className="sol-field">
                      <label htmlFor="cci">CCI</label>
                      <input
                        id="cci"
                        value={cci}
                        onChange={(evento) => setCci(evento.target.value)}
                        placeholder="00212345678901234567"
                        inputMode="numeric"
                        maxLength={20}
                        pattern="[0-9]{20}"
                        required
                      />
                      <small>Exactamente 20 dígitos.</small>
                    </div>

                    <div className="sol-field">
                      <label htmlFor="moneda">Moneda</label>
                      <select
                        id="moneda"
                        value={moneda}
                        onChange={(evento) => setMoneda(evento.target.value)}
                      >
                        <option value="PEN">PEN · Sol</option>
                        <option value="USD">USD · Dólar</option>
                      </select>
                    </div>

                    <div className="sol-field">
                      <label htmlFor="regimen">Régimen</label>
                      <select
                        id="regimen"
                        value={regimen}
                        onChange={(evento) => setRegimen(evento.target.value)}
                      >
                        <option value="INDIVIDUAL">INDIVIDUAL</option>
                        <option value="MANCOMUNADA_INDISTINTA">MANCOMUNADA_INDISTINTA</option>
                        <option value="MANCOMUNADA_CONJUNTA">MANCOMUNADA_CONJUNTA</option>
                      </select>
                    </div>

                    <div className="sol-field">
                      <label htmlFor="agencia">Agencia (opcional)</label>
                      <input
                        id="agencia"
                        value={agencia}
                        onChange={(evento) => setAgencia(evento.target.value)}
                        placeholder="AQP01"
                        maxLength={10}
                      />
                    </div>

                    <div className="sol-field">
                      <label htmlFor="titulares">Clientes titulares</label>
                      <input
                        id="titulares"
                        value={titulares}
                        onChange={(evento) => setTitulares(evento.target.value)}
                        placeholder="DEV001, CLI000000123"
                        required
                      />
                      <small>Separa varios códigos con coma o espacio.</small>
                    </div>
                  </div>

                  <div className="sol-form-actions">
                    <span className="sol-caption">
                      El JWT debe tener el permiso CREAR_CUENTA (ADMINISTRADOR u OPERADOR).
                    </span>
                    <button className="sol-button primary" type="submit" disabled={cargando}>
                      {cargando ? "Abriendo cuenta…" : "Abrir cuenta"}
                    </button>
                  </div>
                </form>
              </div>
            </section>
          )}

          {vista === "operaciones" && (
            <section className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Registrar una operación</h2>
                  <p>POST /api/cuenta/deposito · /retiro · /transferencia</p>
                </div>
                <span className="sol-badge">Canal {CANAL}</span>
              </div>

              <div className="sol-tabs">
                {(["deposito", "retiro", "transferencia"] as ModoOperacion[]).map((opcion) => (
                  <button
                    key={opcion}
                    type="button"
                    className={modo === opcion ? "active" : ""}
                    onClick={() => {
                      setModo(opcion);
                      setAviso(null);
                    }}
                  >
                    {NOMBRE_OPERACION[opcion]}
                  </button>
                ))}
              </div>

              <div className="sol-detail-body">
                <div className="sol-info-strip">
                  <span>ⓘ</span>
                  <div>
                    <strong>Cabeceras automáticas</strong>
                    <p>
                      Cada solicitud envía X-Idempotency-Key (UUIDv4), X-Channel-ID
                      ({CANAL}) y X-Request-Timestamp (ISO-8601). Reintentar con la misma
                      llave devuelve el resultado original (replay).
                    </p>
                  </div>
                </div>

                <form onSubmit={operar}>
                  <div className="sol-form-grid">
                    {modo === "transferencia" ? (
                      <>
                        <div className="sol-field">
                          <label htmlFor="origen">Cuenta de origen</label>
                          <input
                            id="origen"
                            value={origen}
                            onChange={(evento) => setOrigen(evento.target.value)}
                            placeholder={seleccionada?.num_cuenta || "1234567890"}
                            maxLength={20}
                            required
                          />
                        </div>
                        <div className="sol-field">
                          <label htmlFor="destino">Cuenta de destino</label>
                          <input
                            id="destino"
                            value={destino}
                            onChange={(evento) => setDestino(evento.target.value)}
                            placeholder="0987654321"
                            maxLength={20}
                            required
                          />
                        </div>
                      </>
                    ) : (
                      <div className="sol-field">
                        <label htmlFor="num-operacion">Número de cuenta</label>
                        <input
                          id="num-operacion"
                          value={numOperacion}
                          onChange={(evento) => setNumOperacion(evento.target.value)}
                          placeholder={seleccionada?.num_cuenta || "1234567890"}
                          maxLength={20}
                          required
                        />
                      </div>
                    )}

                    <div className="sol-field">
                      <label htmlFor="monto">Monto</label>
                      <input
                        id="monto"
                        value={monto}
                        onChange={(evento) => setMonto(evento.target.value)}
                        placeholder="100.00"
                        inputMode="decimal"
                        required
                      />
                      <small>Mayor que 0 y con hasta 2 decimales.</small>
                    </div>

                    <div className="sol-field" style={{ gridColumn: "1 / -1" }}>
                      <label htmlFor="glosa">Glosa (opcional)</label>
                      <input
                        id="glosa"
                        value={glosa}
                        onChange={(evento) => setGlosa(evento.target.value)}
                        placeholder={`${NOMBRE_OPERACION[modo]} por ventanilla`}
                        maxLength={200}
                      />
                    </div>
                  </div>

                  <div className="sol-form-actions">
                    <span className="sol-caption">
                      El JWT debe tener REGISTRAR_MOVIMIENTO o CREAR_CUENTA según el CORE.
                    </span>
                    <button className="sol-button primary" type="submit" disabled={cargando}>
                      {cargando ? "Registrando…" : `Registrar ${NOMBRE_OPERACION[modo].toLowerCase()}`}
                    </button>
                  </div>
                </form>
              </div>
            </section>
          )}

          {vista === "movimientos" && (
            <>
              <section className="sol-card" style={{ marginBottom: 20 }}>
                <div className="sol-card-title">
                  <div>
                    <h2>Consultar un movimiento</h2>
                    <p>GET /api/cuenta/movimiento/{"{uuid_transaccion}"}</p>
                  </div>
                  <span className="sol-badge">UUID</span>
                </div>
                <form className="sol-toolbar" onSubmit={consultarMovimiento}>
                  <div className="sol-search">
                    <span>⌕</span>
                    <input
                      value={uuidBusqueda}
                      onChange={(evento) => setUuidBusqueda(evento.target.value)}
                      placeholder="uuid_transaccion"
                      aria-label="UUID de la transacción"
                    />
                  </div>
                  <button
                    className="sol-button secondary"
                    type="submit"
                    disabled={cargando || !uuidBusqueda.trim()}
                  >
                    Consultar
                  </button>
                </form>

                {detalleMovimiento && (
                  <div className="sol-detail-body" style={{ paddingTop: 0 }}>
                    <div className="sol-review detail">
                      <div>
                        <small>UUID</small>
                        <strong>{String(detalleMovimiento.uuid_transaccion ?? "—")}</strong>
                      </div>
                      <div>
                        <small>Tipo</small>
                        <strong>{String(detalleMovimiento.tipo_operacion ?? "—")}</strong>
                      </div>
                      <div>
                        <small>Estado</small>
                        <strong>{String(detalleMovimiento.estado_transaccion ?? "—")}</strong>
                      </div>
                    </div>
                    <pre
                      style={{
                        background: "#f6f9fa",
                        border: "1px solid #e5edf1",
                        borderRadius: 7,
                        padding: 16,
                        fontSize: 11,
                        overflowX: "auto",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
                      {JSON.stringify(detalleMovimiento, null, 2)}
                    </pre>
                  </div>
                )}
              </section>

              <section className="sol-card">
                <div className="sol-card-title">
                  <div>
                    <h2>Historial de la cuenta seleccionada</h2>
                    <p>
                      {seleccionada
                        ? `GET /api/cuenta/${seleccionada.num_cuenta}/movimientos`
                        : "Selecciona una cuenta en el resumen"}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="sol-link"
                    disabled={cargando || !seleccionada}
                    onClick={() => {
                      if (!seleccionada) return;
                      setCargando(true);
                      setAviso(null);
                      traerMovimientos(seleccionada.num_cuenta)
                        .then(setMovimientos)
                        .catch((error: unknown) =>
                          setAviso({ texto: textoError(error), error: true }),
                        )
                        .finally(() => setCargando(false));
                    }}
                  >
                    Recargar
                  </button>
                </div>

                {movimientos.length === 0 ? (
                  <div className="sol-empty">
                    <h3>Sin movimientos</h3>
                    <p>
                      Selecciona una cuenta con saldo o registra un depósito para ver
                      actividad.
                    </p>
                    <button
                      type="button"
                      className="sol-button secondary"
                      onClick={() => setVista("operaciones")}
                    >
                      Registrar operación
                    </button>
                  </div>
                ) : (
                  <div className="sol-tablewrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Fecha</th>
                          <th>Tipo</th>
                          <th>Glosa</th>
                          <th className="num">Monto</th>
                          <th>Canal</th>
                          <th>Estado</th>
                          <th>UUID</th>
                        </tr>
                      </thead>
                      <tbody>
                        {movimientos.map((movimiento, indice) => {
                          const esDebito =
                            String(movimiento.naturaleza || "").toUpperCase() === "D";
                          return (
                            <tr key={movimiento.uuid_transaccion || indice}>
                              <td className="muted">{fechaHora(movimiento.fecha_hora)}</td>
                              <td>{movimiento.tipo_operacion || "—"}</td>
                              <td>{movimiento.glosa || "—"}</td>
                              <td className="num emphasis">
                                {esDebito ? "− " : "+ "}
                                {dinero(
                                  movimiento.monto,
                                  movimiento.moneda || seleccionada?.moneda || "PEN",
                                )}
                              </td>
                              <td className="muted">{movimiento.id_canal || "—"}</td>
                              <td>
                                <span className="sol-badge">
                                  <span />
                                  {movimiento.estado_transaccion || "—"}
                                </span>
                              </td>
                              <td className="muted">
                                {movimiento.uuid_transaccion ? (
                                  <button
                                    type="button"
                                    className="sol-link"
                                    onClick={() => {
                                      setUuidBusqueda(String(movimiento.uuid_transaccion));
                                      setDetalleMovimiento(movimiento);
                                    }}
                                  >
                                    {String(movimiento.uuid_transaccion).slice(0, 8)}…
                                  </button>
                                ) : (
                                  "—"
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          )}

          <footer className="sol-footer">
            <span>Banco Nacional de Arequipa · Proyecto académico</span>
            <span>Frontend → /api/cuenta → CUENTAS :8001 → COREDB :8012</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
