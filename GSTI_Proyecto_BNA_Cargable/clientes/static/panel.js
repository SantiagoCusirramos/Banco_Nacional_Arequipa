"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function aviso(texto, tipo = "ok") {
  const el = document.createElement("div");
  el.className = "toast " + tipo;
  el.textContent = texto;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), tipo === "err" ? 7000 : 3500);
}

async function api(url, opciones) {
  const r = await fetch(url, opciones);
  let datos = null;
  try { datos = await r.json(); } catch (_) { /* sin JSON */ }
  if (!r.ok) throw new Error((datos && datos.mensaje) || "Error " + r.status);
  return datos;
}

/* ------------------------------------------------------------ estado de servicios */
async function estado() {
  try {
    const e = await api("/panel/api/estado");
    for (const k of ["bus", "core", "reniec"]) $("#st-" + k).className = "punto " + (e[k] === "ok" ? "ok" : e[k] === "caido" ? "caido" : e[k] === "error" ? "error" : "");
  } catch (_) { for (const k of ["bus", "core", "reniec"]) $("#st-" + k).className = "punto caido"; }
}
estado();
setInterval(estado, 15000);

/* ------------------------------------------------------------ pestañas */
$$(".tab").forEach((b) => b.addEventListener("click", () => {
  $$(".tab").forEach((x) => x.classList.toggle("activa", x === b));
  for (const id of ["registro", "validacion", "lab"]) $("#tab-" + id).classList.toggle("panel-oculto", id !== b.dataset.tab);
  if (b.dataset.tab !== "lab") cargarTabla(b.dataset.tab);
}));

/* ------------------------------------------------------------ tablas de solicitudes */
const claseResultado = (r) => {
  if (/^RECHAZADO|RENIEC_NO_DISPONIBLE|^ERROR_|NO_COINCIDE|DNI_NO_ENCONTRADO|DATOS_NO_COINCIDEN/.test(r)) return "err";
  if (/SIN_RENIEC|NO_CONSULTADO|NO_REGISTRADO|FECHA_NO_COINCIDE|SIN_PLANTILLA/.test(r)) return "warn";
  return "ok";
};
const fechaLocal = (iso) => new Date(iso).toLocaleString("es-PE", { dateStyle: "short", timeStyle: "medium" });

async function cargarTabla(cual) {
  const orden = $(`.orden[data-orden="${cual}"]`).value;
  const cuerpo = $("#filas-" + cual);
  const columnas = cual === "registro" ? 5 : 6;
  try {
    const filas = await api(`/panel/api/solicitudes-${cual}?limite=200&orden=${orden}`);
    $("#n-" + cual).textContent = filas.length;
    cuerpo.innerHTML = filas.length ? filas.map((s) => {
      const res = `<span class="badge ${claseResultado(s.resultado)}">${esc(s.resultado.replaceAll("|", " · "))}</span>`;
      const comunes = `<td>${esc(s.modulo_origen)}</td><td>${esc(s.tipo_documento)}</td><td class="mono">${esc(s.numero_documento)}</td>`;
      const tipo = cual === "validacion" ? `<td><span class="badge info">${esc(s.tipo_validacion)}</span></td>` : "";
      return `<tr>${comunes}${tipo}<td title="${esc(s.fecha_solicitud)} (UTC)">${esc(fechaLocal(s.fecha_solicitud))}</td><td>${res}</td></tr>`;
    }).join("") : `<tr><td colspan="${columnas}" class="vacio">Todavía no hay solicitudes.</td></tr>`;
  } catch (e) { cuerpo.innerHTML = `<tr><td colspan="${columnas}" class="vacio">No se pudo leer del Core: ${esc(e.message)}</td></tr>`; }
}
$$("[data-recargar]").forEach((b) => b.addEventListener("click", () => cargarTabla(b.dataset.recargar)));
$$(".orden").forEach((s) => s.addEventListener("change", () => cargarTabla(s.dataset.orden)));
const timers = {};
$$(".auto").forEach((c) => c.addEventListener("change", () => {
  clearInterval(timers[c.dataset.auto]);
  if (c.checked) timers[c.dataset.auto] = setInterval(() => cargarTabla(c.dataset.auto), 5000);
}));
cargarTabla("registro");
cargarTabla("validacion");

/* ------------------------------------------------------------ consola JSON */
function resaltar(obj) {
  const json = esc(JSON.stringify(obj, null, 2));
  return json.replace(/(&quot;(?:\\.|[^&\\]|&(?!quot;))*?&quot;)(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g, (m, cad, dos, bool) => {
    if (cad) return dos ? `<span class="j-k">${cad}</span>${dos}` : `<span class="j-s">${cad}</span>`;
    if (bool) return `<span class="j-b">${m}</span>`;
    if (m === "null") return `<span class="j-z">${m}</span>`;
    return `<span class="j-n">${m}</span>`;
  });
}

function mostrarConsola(r) {
  $("#c-ruta").textContent = r.ruta;
  const http = $("#c-http"); http.textContent = "HTTP " + r.http; http.className = "badge " + (r.ok ? "ok" : "err");
  const est = $("#c-estado"); est.textContent = r.ok ? "Éxito" : "Error"; est.className = "badge " + (r.ok ? "ok" : "err");
  $("#c-ms").textContent = r.ms + " ms";
  $("#c-peticion").innerHTML = resaltar(r.peticion);
  $("#c-respuesta").innerHTML = resaltar(r.respuesta);
}

async function ejecutar(operacion, cuerpo, boton) {
  boton.disabled = true;
  try {
    const r = await api("/panel/api/lab/" + operacion, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    mostrarConsola(r);
    cargarTabla("registro"); cargarTabla("validacion");
    estado();
  } catch (e) { aviso(e.message, "err"); }
  boton.disabled = false;
}

const valoresForm = (f) => Object.fromEntries(new FormData(f).entries());

/* ------------------------------------------------------------ casos de prueba (datos ficticios, ver scripts/cargar_datos_prueba.py) */
const CASOS = {
  registrar: {
    "DNI válido (existe en RENIEC)": { tipo_documento: "DNI", numero_documento: "70000002", nombres: "María Elena", apellidos: "Mamani Condori", fecha_nacimiento: "1995-11-02", ingreso_mensual: "2800.00", direccion: "Calle Mercaderes 123, Arequipa", correo: "maria.mamani@example.com", telefono: "954000002" },
    "DNI con apellido incorrecto (RENIEC lo rechaza)": { tipo_documento: "DNI", numero_documento: "70000002", nombres: "María Elena", apellidos: "Torres Vega", fecha_nacimiento: "1995-11-02", ingreso_mensual: "2800.00", direccion: "Calle Mercaderes 123, Arequipa", correo: "maria@example.com", telefono: "954000002" },
    "DNI inexistente": { tipo_documento: "DNI", numero_documento: "70000099", nombres: "Pedro", apellidos: "Inexistente Nadie", fecha_nacimiento: "1990-01-01", ingreso_mensual: "1500", direccion: "Av. Ejército 456, Arequipa", correo: "pedro@example.com", telefono: "954000099" },
    "Pasaporte (sin verificación RENIEC)": { tipo_documento: "PASAPORTE", numero_documento: "XP7654321", nombres: "Sofía", apellidos: "Duarte Lima", fecha_nacimiento: "1991-04-18", ingreso_mensual: "3200", direccion: "Calle Bolívar 77, Arequipa", correo: "sofia.duarte@example.com", telefono: "+51954000010" },
    "PTP (sin verificación RENIEC)": { tipo_documento: "PTP", numero_documento: "PTP2024777", nombres: "Luis", apellidos: "Barrios Vera", fecha_nacimiento: "1987-09-30", ingreso_mensual: "2100", direccion: "Calle Puente Bolognesi 9, Arequipa", correo: "luis.barrios@example.com", telefono: "954000011" },
    "Ingreso negativo (datos inválidos)": { tipo_documento: "PASAPORTE", numero_documento: "XP1111111", nombres: "Ana", apellidos: "Prueba", fecha_nacimiento: "1990-01-01", ingreso_mensual: "-5", direccion: "Calle Falsa 123", correo: "ana@example.com", telefono: "954000012" },
  },
  documento: {
    "DNI válido y cliente del banco": { tipo_documento: "DNI", numero_documento: "70000001", fecha_nacimiento: "1990-05-14" },
    "DNI válido, NO cliente del banco": { tipo_documento: "DNI", numero_documento: "70000003", fecha_nacimiento: "1988-03-21" },
    "DNI inexistente": { tipo_documento: "DNI", numero_documento: "70000099", fecha_nacimiento: "1990-01-01" },
    "DNI con fecha de nacimiento incorrecta": { tipo_documento: "DNI", numero_documento: "70000001", fecha_nacimiento: "1991-05-14" },
    "Pasaporte registrado": { tipo_documento: "PASAPORTE", numero_documento: "AB123456", fecha_nacimiento: "1985-07-09" },
    "PTP registrado": { tipo_documento: "PTP", numero_documento: "PTP2024001", fecha_nacimiento: "1992-01-30" },
  },
  biometria: {
    "Huella (suba huella_A_variante.png del DNI 70000001)": { numero_documento: "70000001", tipo_biometria: "HUELLA" },
    "Huella (suba huella_B.png contra el DNI 70000001)": { numero_documento: "70000001", tipo_biometria: "HUELLA" },
    "Rostro (suba una foto del DNI cuyo rostro cargó en RENIEC)": { numero_documento: "70000001", tipo_biometria: "FACIAL" },
  },
};
for (const [forma, casos] of Object.entries(CASOS)) {
  const sel = $(`[data-caso="${forma}"]`);
  Object.keys(casos).forEach((nombre) => sel.add(new Option(nombre, nombre)));
  sel.addEventListener("change", () => {
    const caso = casos[sel.value];
    if (!caso) return;
    const f = $("#f-" + forma);
    for (const [k, v] of Object.entries(caso)) { const campo = f.elements[k]; if (campo) campo.value = v; }
    if (forma === "biometria") actualizarFormato();
  });
}

/* ------------------------------------------------------------ prueba 1 y 2 */
$("#f-registrar").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const v = valoresForm(ev.target);
  v.ingreso_mensual = v.ingreso_mensual === "" ? "" : Number(v.ingreso_mensual);
  ejecutar("registrar", v, ev.submitter);
});
$("#f-documento").addEventListener("submit", (ev) => { ev.preventDefault(); ejecutar("validar-documento", valoresForm(ev.target), ev.submitter); });

/* ------------------------------------------------------------ prueba 3: biometría */
let plantillaImagen = null; // plantilla generada desde una imagen (no se muestra ni se guarda)
const FORMATOS = { FACIAL: "ARCFACE_EMBEDDING", HUELLA: "ISO_19794_2_2005" };

function actualizarFormato() {
  $("#bio-formato").value = FORMATOS[$("#bio-tipo").value];
  limpiarPlantilla();
}
function limpiarPlantilla() {
  plantillaImagen = null;
  $("#bio-archivo").value = "";
  $("#bio-template").value = "";
  $("#bio-estado").textContent = "Sin imagen convertida.";
}
$("#bio-tipo").addEventListener("change", actualizarFormato);
$("#bio-limpiar").addEventListener("click", limpiarPlantilla);
actualizarFormato();

$("#bio-archivo").addEventListener("change", async (ev) => {
  const archivo = ev.target.files[0];
  if (!archivo) return;
  const tipo = $("#bio-tipo").value;
  const fd = new FormData();
  fd.append("tipo", tipo);
  fd.append("archivo", archivo);
  $("#bio-estado").textContent = tipo === "FACIAL" ? "Convirtiendo imagen (la primera vez carga el modelo y puede tardar)…" : "Convirtiendo imagen…";
  try {
    const r = await api("/panel/api/lab/extraer-plantilla", { method: "POST", body: fd });
    plantillaImagen = r.template;
    $("#bio-template").value = "";
    $("#bio-estado").textContent = tipo === "FACIAL"
      ? `✓ Plantilla generada desde la imagen: ${r.formato}, ${r.longitud} valores (se enviará al validar).`
      : `✓ Plantilla generada desde la imagen: ${r.formato}, ${r.minucias} minucias, calidad NFIQ2 ${r.calidad_nfiq2}, ${r.longitud} caracteres Base64 (se enviará al validar).`;
  } catch (e) {
    plantillaImagen = null;
    $("#bio-estado").textContent = "✗ " + e.message;
    aviso(e.message, "err");
  }
});

$("#f-biometria").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const v = valoresForm(ev.target);
  const cuerpo = { modulo_origen: v.modulo_origen, tipo_documento: "DNI", numero_documento: v.numero_documento, tipo_biometria: v.tipo_biometria, formato: v.formato };
  if (v.tipo_biometria === "HUELLA") cuerpo.codificacion = "base64";
  let plantilla = plantillaImagen;
  if (plantilla === null) {
    const texto = $("#bio-template").value.trim();
    if (!texto) { aviso("Ingrese una plantilla JSON o suba una imagen", "err"); return; }
    try { plantilla = JSON.parse(texto); } catch (_) { plantilla = texto; } // Base64 sin comillas también se acepta
  }
  cuerpo.template = plantilla;
  ejecutar("validar-biometria", cuerpo, ev.submitter);
});
