/* =========================================================
   Utilidades compartidas: sesión, mensajes, consola del Bus
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
    try { sessionStorage.removeItem(this.clave); }
    catch (e) { delete this.memoria[this.clave]; }
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

/* ---------- Encabezado de sesión ---------- */
function pintarCabecera() {
  const s = Sesion.leer();
  const n = document.getElementById("sesionNombre");
  const c = document.getElementById("sesionCliente");
  if (n && s) n.textContent = s.nombres;
  if (c && s) c.textContent = `${s.codCliente} · ${s.dni}`;
  const sal = document.getElementById("btnSalir");
  if (sal) sal.addEventListener("click", () => { Sesion.cerrar(); window.location.href = "index.html"; });
}

/* =========================================================
   Consola del Bus de Servicios (evidencia de integración)
   Oculta por defecto; se puede mostrar cuando se necesite
   y la preferencia queda guardada.
   ========================================================= */
const PREF_CONSOLA = "hb_consola_abierta";

function leerPref(clave, porDefecto) {
  try { const v = localStorage.getItem(clave); return v === null ? porDefecto : v === "1"; }
  catch (e) { return porDefecto; }
}
function guardarPref(clave, valor) {
  try { localStorage.setItem(clave, valor ? "1" : "0"); }
  catch (e) { /* almacenamiento no disponible */ }
}

let consolaAbierta = leerPref(PREF_CONSOLA, false);

function crearConsola() {
  const box = document.createElement("div");
  box.className = consolaAbierta ? "consola" : "consola consola-oculta";
  box.id = "consolaBus";
  box.innerHTML = `
    <div class="consola-cab">
      <b>BUS DE SERVICIOS</b>
      <span class="etq ocultable" id="consolaModo">${Bus.modo === "API" ? "Bus local REST/JSON" : "MOCK local"}</span>
      <button type="button" id="btnConsolaToggle">${consolaAbierta ? "Ocultar" : "Mostrar"}</button>
      <button type="button" id="btnConsolaLimpiar" class="ocultable">Limpiar</button>
      <button type="button" id="btnReiniciarDemo" class="ocultable">Reiniciar demo</button>
      <label class="ocultable"><input type="checkbox" id="chkTimeout"> Simular timeout del Bus</label>
      <label class="ocultable"><input type="checkbox" id="chkMostrarReq" checked> Ver solicitudes</label>
      <span class="etq ocultable" id="consolaContador">0 intercambios</span>
    </div>
    <div class="consola-cuerpo" id="consolaCuerpo">
      <div class="consola-vacia">Sin intercambios todavía. Cada llamada del canal al Bus aparecerá aquí. Modo: ${Bus.modo}.</div>
    </div>`;
  document.body.appendChild(box);

  document.getElementById("btnConsolaToggle").addEventListener("click", e => {
    consolaAbierta = !consolaAbierta;
    box.classList.toggle("consola-oculta", !consolaAbierta);
    e.target.textContent = consolaAbierta ? "Ocultar" : "Mostrar";
    guardarPref(PREF_CONSOLA, consolaAbierta);
    ajustarEspacioConsola();
    if (consolaAbierta) pintarConsola();
  });
  document.getElementById("btnConsolaLimpiar").addEventListener("click", () => {
    Bus.consola.length = 0;
    pintarConsola();
  });
  document.getElementById("btnReiniciarDemo").addEventListener("click", async () => {
    await Bus.reiniciarDemo();
    Sesion.cerrar();
    window.location.href = "index.html";
  });
  document.getElementById("chkTimeout").addEventListener("change", e => {
    Bus.timeout = e.target.checked;
    avisoBus(e.target.checked);
  });
  document.getElementById("chkMostrarReq").addEventListener("change", pintarConsola);
  window.addEventListener("resize", ajustarEspacioConsola);
  ajustarEspacioConsola();
}

/* Deja libre el espacio que ocupa la consola para que ningún
   elemento de la página quede tapado por el panel fijo. */
function ajustarEspacioConsola() {
  const panel = document.getElementById("consolaBus");
  const alto = panel ? panel.offsetHeight : 70;
  document.body.style.paddingBottom = (alto + 24) + "px";
}

function avisoBus(activo) {
  let el = document.getElementById("avisoBus");
  if (!el) {
    el = document.createElement("div");
    el.id = "avisoBus";
    el.style.cssText = "position:fixed;top:74px;right:20px;z-index:70;max-width:340px;";
    document.body.appendChild(el);
  }
  mostrarMensaje(el, activo ? "warn" : "info", activo
    ? "Modo timeout activado: el Bus no responderá y la operación quedará PENDIENTE / NO CONFIRMADA (RN-BUS-002)."
    : "Modo timeout desactivado: el Bus responde con normalidad.");
  setTimeout(() => { el.className = "msg"; }, 5000);
}

function pintarConsola() {
  const cuerpo = document.getElementById("consolaCuerpo");
  if (!cuerpo) return;
  const contador = document.getElementById("consolaContador");
  const verReq = document.getElementById("chkMostrarReq");
  const mostrarReq = verReq ? verReq.checked : true;
  const items = Bus.consola.slice(-40);

  if (contador) contador.textContent = `${Bus.consola.length} intercambio(s)`;
  if (!items.length) {
    cuerpo.innerHTML = `<div class="consola-vacia">Sin intercambios todavía. Cada llamada del canal al Bus aparecerá aquí. Modo: ${Bus.modo}.</div>`;
    return;
  }

  cuerpo.innerHTML = items.map(r => `
    <div class="consola-item">
      <div class="linea1">
        <span class="hora">${fmt.hora(new Date(r.fechaHora))}</span>
        <span class="metodo">${r.metodo}</span>
        <span class="ruta">${r.ruta}</span>
        <span class="interfaz">${r.interfaz || "-"}</span>
        <span class="lat">${r.ms} ms</span>
        <span class="${r.status === 200 ? "estado-ok" : "estado-err"}">${r.status} ${r.estado}</span>
        <span class="lat">uuid ${r.uuidTransaccion.slice(0, 13)}…</span>
      </div>
      ${mostrarReq ? `<pre class="req">${JSON.stringify(r.payload, null, 2)}</pre>` : ""}
      <pre class="res">${JSON.stringify(r.respuesta, null, 2)}</pre>
    </div>`).join("");

  cuerpo.scrollTop = cuerpo.scrollHeight;
  ajustarEspacioConsola();
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


/* ---------- Aviso de modo local y utilidades de Fase III ---------- */
function avisoModoLocal(contenedor) {
  if (Bus.modo === "API") return;
  const el = typeof contenedor === "string" ? document.getElementById(contenedor) : contenedor;
  if (el) {
    mostrarMensaje(el, "warn",
      "Modo local limitado: para transferencias, Token Matriz, pago de créditos y auditoría ejecute ./iniciar.sh y abra http://127.0.0.1:8080/.");
  }
}

function tokenSesionActual() {
  const s = Sesion.leer();
  return s ? s.tokenSesion : null;
}
