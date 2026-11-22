"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import * as QRCode from "qrcode";
import { AvisoPermiso } from "@/app/components/AvisoPermiso";
import { BarraNavegacion } from "@/app/components/BarraNavegacion";
import { obtenerMiPerfil, type Usuario } from "@/lib/auth";
import { pantallaPorHref, puedeVerPantalla } from "@/lib/pantallas";
import { ClaveNueva } from "../components/ClaveNueva";
import { afiliar, mensajeDeError, registrarComercio, type Afiliacion, type Comercio } from "@/lib/billetera";

type Pestana = "afiliacion" | "comercio";
type Aviso = { text: string; error: boolean };
type ConfigPublica = { urlBilletera: string | null; urlCajero: string | null; urlApk: string | null };

const filaDato = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginTop: "15px" } as const;
const recuadro = { marginTop: "30px", background: "#f8fafc", padding: "20px", borderRadius: "8px", border: "1px solid #e2e8f0" } as const;
const opcionesQr = { type: "image/png", width: 220, margin: 1 } as const;

function useQr(trama: string | null) {
  // Se guarda también la trama: si cambia, la imagen anterior deja de mostrarse hasta que
  // termine el nuevo QR, sin necesitar un setState síncrono dentro del efecto.
  const [resultado, setResultado] = useState<{ trama: string; imagen: string } | null>(null);
  useEffect(() => {
    let vigente = true;
    if (!trama) return;
    void QRCode.toDataURL(trama, opcionesQr).then(
      (imagen) => { if (vigente) setResultado({ trama, imagen }); },
      () => { if (vigente) setResultado(null); },
    );
    return () => { vigente = false; };
  }, [trama]);
  return resultado?.trama === trama ? resultado.imagen : null;
}

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
  const [afiliado, setAfiliado] = useState<Afiliacion | null>(null);

  // Comercio: recibe pagos con QR en su cuenta en soles.
  const [ruc, setRuc] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [cuentaComercio, setCuentaComercio] = useState("");
  const [comercio, setComercio] = useState<Comercio | null>(null);
  const [config, setConfig] = useState<ConfigPublica | null>(null);

  // La configuración se lee del servidor en cada carga: las URL no se incrustan en la imagen.
  useEffect(() => {
    let vigente = true;
    fetch("/api/config-publica")
      .then((respuesta) => (respuesta.ok ? respuesta.json() : null))
      .then((datos: ConfigPublica | null) => {
        if (!vigente) return;
        setConfig(datos ?? { urlBilletera: null, urlCajero: null, urlApk: null });
      })
      .catch(() => {
        if (vigente) setConfig({ urlBilletera: null, urlCajero: null, urlApk: null });
      });
    return () => { vigente = false; };
  }, []);

  const tramaQrComercio = comercio?.id_qr ? `CHASKI|${comercio.id_qr}` : null;
  const imagenQrComercio = useQr(tramaQrComercio);
  const tramaQrServidor = config?.urlBilletera ? `CHASKI-SERVIDOR|${config.urlBilletera}` : null;
  const imagenQrServidor = useQr(tramaQrServidor);

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

  // El PIN lo genera el sistema o lo escribe la clienta (ClaveNueva), nunca el operador.
  async function afiliarConPin(pin: string) {
    const cod = codCliente.trim().toUpperCase(), cuenta = numCuenta.trim();
    if (!cod || !cuenta) throw new Error("Escribe el código del cliente y la cuenta antes de afiliar.");
    setNotice(null);
    let r: Afiliacion;
    try {
      r = await afiliar({ cod_cliente: cod, num_cuenta: cuenta, pin });
    } catch (err) {
      throw new Error(mensajeDeError(err));
    }
    setAfiliado(r);
    setNotice({
      text: r.nueva
        ? `Cliente ${r.cod_cliente} afiliado a Chaski. Ya puede entrar a la app con su celular y el PIN.`
        : `El cliente ${r.cod_cliente} ya estaba afiliado: se actualizó su PIN o su cuenta y la billetera quedó ${r.estado}.`,
      error: false,
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
              <div className="sol-form-grid" style={{ marginTop: "20px" }}>
                <div className="sol-field">
                  <label htmlFor="af-cliente">Código del cliente</label>
                  <input id="af-cliente" value={codCliente} onChange={(e) => setCodCliente(e.target.value)} required maxLength={12} placeholder="CLI000000001" />
                </div>
                <div className="sol-field">
                  <label htmlFor="af-cuenta">Número de cuenta en soles</label>
                  <input id="af-cuenta" value={numCuenta} onChange={(e) => setNumCuenta(e.target.value)} required maxLength={20} placeholder="Cuenta del cliente" />
                </div>
              </div>
              <div style={{ marginTop: "16px" }}>
                <ClaveNueva digitos={6} nombre="PIN de Chaski" asignar={afiliarConPin}
                  textoGenerar="Generar PIN y afiliar" textoAsignar="Afiliar a Chaski" />
              </div>
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
                  {tramaQrComercio && imagenQrComercio && (
                    <div data-impresion-qr className="qr-impresion" style={{ marginTop: "20px" }}>
                      <figure style={{ margin: 0, textAlign: "center" }}>
                        <img src={imagenQrComercio} alt={`QR de pago de ${comercio.razon_social}`} width={220} height={220}
                          style={{ imageRendering: "pixelated", maxWidth: "100%" }} />
                        <figcaption style={{ marginTop: "8px", fontWeight: 700 }}>{comercio.razon_social}</figcaption>
                      </figure>
                      <div className="qr-no-impresion" style={{ display: "flex", gap: "10px", justifyContent: "center", marginTop: "12px" }}>
                        <a className="sol-button primary" href={imagenQrComercio} download={`qr-${comercio.ruc}.png`}>Descargar QR</a>
                        <button type="button" className="sol-button" onClick={() => window.print()}>Imprimir</button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <section className="sol-card" aria-labelledby="instalar-chaski-titulo" style={{ marginTop: "20px" }}>
            <div className="sol-card-title">
              <div>
                <h2 id="instalar-chaski-titulo">Instalar Chaski en el celular de la clienta</h2>
                <p>Descargue la app y conéctela con este banco desde el celular; no hace falta configurar nada en la app.</p>
              </div>
            </div>
            {config === null ? (
              <p>Consultando la configuración pública…</p>
            ) : (
              <>
                {config.urlApk ? (
                  <p><a className="sol-button primary" href={config.urlApk}>Descargar Chaski (APK)</a></p>
                ) : (
                  <p>Falta la URL del APK: pida al administrador del despliegue que configure BNA_URL_APK.</p>
                )}
                {config.urlBilletera ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "20px", flexWrap: "wrap", marginTop: "15px" }}>
                    {imagenQrServidor && (
                      <img src={imagenQrServidor} alt="QR de configuración de Chaski" width={180} height={180}
                        style={{ imageRendering: "pixelated", maxWidth: "100%" }} />
                    )}
                    <p>En la app, toca &quot;Conectar con mi banco&quot; y escanea este código</p>
                  </div>
                ) : (
                  <p>Falta la URL de la billetera: pida al administrador del despliegue que configure BNA_URL_BILLETERA.</p>
                )}
              </>
            )}
          </section>
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
