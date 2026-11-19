/* =========================================================
   Utilidades compartidas: sesión y mensajes
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
    try {
      sessionStorage.removeItem(this.clave);
      localStorage.removeItem("bna_access_token");
    } catch (e) { delete this.memoria[this.clave]; }
  },
  exigir() {
    const s = this.leer();
    if (!s) { window.location.href = "index.html"; return null; }
    return s;
  }
};

/* ---------- Formato ---------- */
const fmt = {
  moneda(valor, moneda) {
    const s = new Intl.NumberFormat("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(valor);
    return moneda === "USD" ? `USD ${s}` : `S/ ${s}`;
  },
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

/* ---------- Encabezado de sesión ---------- */
function pintarCabecera() {
  const s = Sesion.leer();
  const n = document.getElementById("sesionNombre");
  const c = document.getElementById("sesionCliente");
  if (n && s) n.textContent = s.nombres;
  if (c && s) c.textContent = `Cliente ${s.codCliente}`;
  const sal = document.getElementById("btnSalir");
  if (sal) sal.addEventListener("click", () => { Sesion.cerrar(); window.location.href = "index.html"; });
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
