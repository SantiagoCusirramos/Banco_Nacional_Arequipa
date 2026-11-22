"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AvisoPermiso } from "@/app/components/AvisoPermiso";
import { BarraNavegacion } from "@/app/components/BarraNavegacion";
import { obtenerMiPerfil, type Usuario } from "@/lib/auth";
import { pantallaPorHref, puedeVerPantalla } from "@/lib/pantallas";
import { afiliar, mensajeDeError, registrarComercio, type Afiliacion, type Comercio } from "@/lib/billetera";

type Pestana = "afiliacion" | "comercio";
type Aviso = { text: string; error: boolean };

const filaDato = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginTop: "15px" } as const;
const recuadro = { marginTop: "30px", background: "#f8fafc", padding: "20px", borderRadius: "8px", border: "1px solid #e2e8f0" } as const;

function BilleteraPageInner() {
  const params = useSearchParams();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargandoPerfil, setCargandoPerfil] = useState(true);
  const [tab, setTab] = useState<Pestana>("afiliacion");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<Aviso | null>(null);

  // Afiliación: el cliente ya existe (lo registra Captación) y tiene una cuenta individual en soles.
  const [codCliente, setCodCliente] = useState(() => params?.get("codCliente")?.toUpperCase() ?? "");
  const [numCuenta, setNumCuenta] = useState(() => params?.get("numCuenta") ?? "");
  const [pin, setPin] = useState("");
  const [afiliado, setAfiliado] = useState<Afiliacion | null>(null);

  // Comercio: recibe pagos con QR en su cuenta en soles.
  const [ruc, setRuc] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [cuentaComercio, setCuentaComercio] = useState("");
  const [comercio, setComercio] = useState<Comercio | null>(null);

  useEffect(() => { obtenerMiPerfil().then(setUsuario).catch(() => setUsuario(null)).finally(() => setCargandoPerfil(false)); }, []);

  async function ejecutar(accion: () => Promise<void>) {
    setLoading(true);
    setNotice(null);
    try {
      await accion();
    } catch (err) {
      setNotice({ text: mensajeDeError(err), error: true });
    } finally {
      setLoading(false);
    }
  }

  function enviarAfiliacion(e: React.FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const r = await afiliar({ cod_cliente: codCliente.trim().toUpperCase(), num_cuenta: numCuenta.trim(), pin });
      setPin(""); // el PIN solo vive en el campo
      setAfiliado(r);
      setNotice({
        text: r.nueva
          ? `Cliente ${r.cod_cliente} afiliado a Chaski. Ya puede entrar a la app con su celular y el PIN.`
          : `El cliente ${r.cod_cliente} ya estaba afiliado: se actualizó su PIN o su cuenta y la billetera quedó ${r.estado}.`,
        error: false,
      });
    });
  }

  function enviarComercio(e: React.FormEvent) {
    e.preventDefault();
    void ejecutar(async () => {
      const r = await registrarComercio({ ruc: ruc.trim(), razon_social: razonSocial.trim(), num_cuenta: cuentaComercio.trim() });
      setComercio(r);
      setNotice({ text: `Comercio ${r.razon_social} registrado con su QR.`, error: false });
    });
  }

  if (cargandoPerfil) return <main className="sol-main"><p>Cargando…</p></main>;
  const pantalla = pantallaPorHref("/billetera");
  const permitido = puedeVerPantalla(usuario?.acciones, "/billetera");
  if (!permitido) {
    return (
      <main className="sol-main">
        <BarraNavegacion titulo="Billetera Chaski" usuario={usuario} />
        <AvisoPermiso mensaje={`Tu rol no tiene permiso para usar esta pantalla. Esta pantalla es para ${pantalla?.rolesPermitidos ?? "personal autorizado"}.`} detalle="Si necesitas afiliar clientes o comercios, pide a un administrador que revise tus permisos en COREDB." />
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
        <div className="sol-workspace">
          <span className="sol-workspace-dot" />
          Billetera Chaski <small>sobre el CORE</small>
        </div>
        <nav aria-label="Navegación Billetera">
          <p>BILLETERA DIGITAL</p>
          <button className={tab === "afiliacion" ? "active" : ""} onClick={() => setTab("afiliacion")}>
            1. Afiliar cliente
          </button>
          <button className={tab === "comercio" ? "active" : ""} onClick={() => setTab("comercio")}>
            2. Registrar comercio
          </button>
        </nav>
        <div className="sol-sidebar-bottom">
          <div className="sol-lab">
            <div>
              <strong>CHASKI</strong>
              <small>La app móvil entra con celular y PIN</small>
            </div>
          </div>
        </div>
      </aside>

      <div className="sol-work">
        <BarraNavegacion titulo="Billetera Chaski" subtitulo="Afiliación a Chaski" usuario={usuario} />

        <main className="sol-main">
          {notice && (
            <div role={notice.error ? "alert" : "status"} className={`sol-alert ${notice.error ? "error" : "success"}`}>
              {notice.text}
              <button onClick={() => setNotice(null)}>×</button>
            </div>
          )}

          {tab === "afiliacion" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Afiliar un cliente a Chaski</h2>
                  <p>
                    El cliente debe estar ACTIVO (registrado y habilitado en Captación) y la cuenta debe ser suya,
                    individual y en soles. En la app entrará con el celular que dio en Captación y este PIN.
                    Si ya estaba afiliado, se cambia su PIN o su cuenta y se desbloquea.
                  </p>
                </div>
              </div>
              <form onSubmit={enviarAfiliacion} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label htmlFor="af-cliente">Código del cliente</label>
                  <input id="af-cliente" value={codCliente} onChange={(e) => setCodCliente(e.target.value)} required maxLength={12} placeholder="CLI000000001" />
                </div>
                <div className="sol-field">
                  <label htmlFor="af-cuenta">Número de cuenta en soles</label>
                  <input id="af-cuenta" value={numCuenta} onChange={(e) => setNumCuenta(e.target.value)} required maxLength={20} placeholder="Cuenta del cliente" />
                </div>
                <div className="sol-field">
                  <label htmlFor="af-pin">PIN de la billetera (6 dígitos)</label>
                  <input id="af-pin" type="password" inputMode="numeric" autoComplete="new-password" value={pin}
                    onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} required pattern="[0-9]{6}" placeholder="••••••" />
                </div>
                <div style={{ gridColumn: "1 / -2", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Afiliando..." : "Afiliar a Chaski"}
                  </button>
                </div>
              </form>
              {afiliado && (
                <div style={recuadro}>
                  <h3>Billetera de {afiliado.cod_cliente}</h3>
                  <div style={filaDato}>
                    <div><small>Cuenta:</small> <strong>{afiliado.num_cuenta}</strong></div>
                    <div><small>Estado:</small> <strong style={{ color: "#0f766e" }}>{afiliado.estado}</strong></div>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === "comercio" && (
            <div className="sol-card">
              <div className="sol-card-title">
                <div>
                  <h2>Registrar un comercio</h2>
                  <p>
                    El comercio cobra con un QR estático: los clientes de Chaski lo pagan desde la app y el dinero se
                    abona en esta cuenta en soles (puede ser de cualquier cliente del banco).
                  </p>
                </div>
              </div>
              <form onSubmit={enviarComercio} className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label htmlFor="co-ruc">RUC (11 dígitos)</label>
                  <input id="co-ruc" inputMode="numeric" value={ruc} onChange={(e) => setRuc(e.target.value.replace(/\D/g, "").slice(0, 11))}
                    required pattern="(10|15|17|20)[0-9]{9}" placeholder="20123456789" />
                </div>
                <div className="sol-field">
                  <label htmlFor="co-razon">Razón social</label>
                  <input id="co-razon" value={razonSocial} onChange={(e) => setRazonSocial(e.target.value)} required maxLength={150} placeholder="Bodega Doña Rosa" />
                </div>
                <div className="sol-field">
                  <label htmlFor="co-cuenta">Cuenta de abono en soles</label>
                  <input id="co-cuenta" value={cuentaComercio} onChange={(e) => setCuentaComercio(e.target.value)} required maxLength={20} placeholder="Número de cuenta" />
                </div>
                <div style={{ gridColumn: "1 / -2", marginTop: "10px" }}>
                  <button className="sol-button primary" type="submit" disabled={loading}>
                    {loading ? "Registrando..." : "Registrar comercio"}
                  </button>
                </div>
              </form>
              {comercio && (
                <div style={recuadro}>
                  <h3>{comercio.razon_social}</h3>
                  <div style={filaDato}>
                    <div><small>RUC:</small> <strong>{comercio.ruc}</strong></div>
                    <div><small>Estado:</small> <strong style={{ color: "#0f766e" }}>{comercio.estado}</strong></div>
                    <div><small>Cuenta:</small> <strong>{comercio.num_cuenta}</strong></div>
                    <div><small>Id del QR:</small> <strong style={{ fontSize: "12px" }}>{comercio.id_qr ?? "—"}</strong></div>
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


function BilleteraConParametros() {
  const params = useSearchParams();
  return <BilleteraPageInner key={params?.toString() ?? ""} />;
}

export default function BilleteraPage() {
  return <Suspense fallback={<main className="sol-main"><p>Cargando…</p></main>}><BilleteraConParametros /></Suspense>;
}
