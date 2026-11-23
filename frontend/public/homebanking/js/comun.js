/* =========================================================
   Utilidades compartidas: sesión, formato, mensajes y botones
   ========================================================= */

const Sesion = {
  clave: "hb_sesion_bna",
  memoria: {},
  leer() {
    try {
      const raw = window.sessionStorage ? sessionStorage.getItem(this.clave) : this.memoria[this.clave];
      return JSON.parse(raw || "null");
    } catch (e) { return null; }
  },
  guardar(datos) {
    const raw = JSON.stringify(datos);
    try { sessionStorage.setItem(this.clave, raw); }
    catch (e) { this.memoria[this.clave] = raw; }
  },
  cerrar() {
    try { sessionStorage.removeItem(this.clave); sessionStorage.removeItem("hb_ultima_tarjeta"); }
    catch (e) { delete this.memoria[this.clave]; }
  },
  // Una sola sesión en el navegador: cerrar aquí cierra también el portal (su token en
  // localStorage) y Solicitud de crédito (cookie HttpOnly: la borra el servidor), y avisa a las
  // otras pestañas con la hora en 'bna_cierre_sesion'. Lo mismo hace cerrarSesion() de lib/auth.ts.
  cerrarTodo() {
    this.cerrar();
    try {
      localStorage.removeItem("bna_access_token");
      localStorage.removeItem("bna_usuario");
      localStorage.setItem("bna_cierre_sesion", String(Date.now()));
    } catch (e) { /* sin localStorage */ }
    try {
      fetch("/api/solicitud-credito/auth/logout", {
        method: "POST", keepalive: true, credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: "{}"
      }).catch(() => {});
    } catch (e) { /* sin red */ }
  },
  // El cliente atendido solo se muestra con la sesión del banco abierta (el token del portal).
  exigir() {
    const s = this.leer();
    let token = null;
    try { token = localStorage.getItem("bna_access_token"); } catch (e) { /* sin localStorage */ }
    if (!s || !token) {
      this.cerrar();
      window.location.href = "index.html";
      return null;
    }
    return s;
  }
};

// Si otra pestaña cierra la sesión, esta deja de mostrar al cliente.
window.addEventListener("storage", e => {
  const cerro = e.key === "bna_cierre_sesion" || e.key === null || (e.key === "bna_access_token" && e.newValue === null);
  if (cerro && Sesion.leer()) {
    Sesion.cerrar();
    window.location.replace("index.html");
  }
});
// «Atrás» tras salir: el navegador puede mostrar la página guardada en memoria sin volver a
// ejecutarla; se comprueba de nuevo la sesión.
window.addEventListener("pageshow", e => {
  if (!e.persisted || /(?:\/|index\.html)$/.test(window.location.pathname)) return;
  let token = null;
  try { token = localStorage.getItem("bna_access_token"); } catch (err) { /* sin localStorage */ }
  if (!Sesion.leer() || !token) {
    Sesion.cerrar();
    window.location.replace("index.html");
  }
});

/* ---------- Formato ---------- */
const fmt = {
  moneda(valor, moneda) {
    const s = new Intl.NumberFormat("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(valor);
    return moneda === "USD" ? `USD ${s}` : `S/ ${s}`;
  },
  hora(ts = new Date()) {
    return ts.toLocaleTimeString("es-PE", { hour12: false });
  },
  fechaHora(ts = new Date()) {
    return ts.toLocaleString("es-PE", { hour12: false });
  }
};

/* ---------- Mensajes en pantalla ---------- */
function mostrarMensaje(idOEl, tipo, texto) {
  const el = typeof idOEl === "string" ? document.getElementById(idOEl) : idOEl;
  if (!el) return;
  el.className = `msg visible ${tipo}`;
  el.textContent = texto;
}
function ocultarMensaje(idOEl) {
  const el = typeof idOEl === "string" ? document.getElementById(idOEl) : idOEl;
  if (el) el.className = "msg";
}

// Los errores del bus pueden traer códigos internos, la ruta llamada y la correlación del
// servidor. Al cliente solo se le explica qué pasó y qué puede hacer, nunca ese detalle técnico.
function mensajeError(err) {
  const e = err || {};
  const codigo = e.codigo || "";
  if (codigo === "PERMISO_DENEGADO" || e.status === 403) return "Tu rol no puede hacer esta operación.";
  if (codigo === "CAMBIO_CLAVE_OBLIGATORIO") return "Debes cambiar tu clave antes de continuar.";
  if (codigo === "BUS_TIMEOUT") return "El servicio no respondió a tiempo. Intenta de nuevo.";
  if (codigo === "BUS_NO_DISPONIBLE") return "No se pudo conectar con el servicio. Revisa tu conexión.";
  if (e.status === 401) return "Tu sesión venció. Vuelve a iniciar sesión.";
  const texto = typeof e.mensaje === "string" ? e.mensaje : "";
  if (/\/(api|core)\//i.test(texto) || /correlaci[oó]n/i.test(texto) || /\b(?:int|rf|rn|cr)[- ]?\d+/i.test(texto)) {
    return "No se pudo completar la operación. Intenta de nuevo.";
  }
  return texto || "No se pudo completar la operación. Intenta de nuevo.";
}

/* ---------- Encabezado de sesión ---------- */
function pintarCabecera() {
  const s = Sesion.leer();
  const n = document.getElementById("sesionNombre");
  const c = document.getElementById("sesionCliente");
  if (n && s) n.textContent = s.nombres;
  if (c && s) c.textContent = `${s.codCliente} · ${s.dni}`;
  const sal = document.getElementById("btnSalir");
  if (sal) sal.addEventListener("click", () => { Sesion.cerrarTodo(); window.location.href = "index.html"; });
}

/* ---------- Botones en carga ---------- */
function cargando(btn, activo, texto) {
  if (!btn) return;
  if (activo) {
    btn.dataset.texto = btn.textContent;
    btn.disabled = true;
    btn.classList.add("cargando");
    btn.textContent = texto || "Procesando";
  } else {
    btn.disabled = false;
    btn.classList.remove("cargando");
    btn.textContent = btn.dataset.texto || btn.textContent;
  }
}

