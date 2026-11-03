"use strict";
const $ = (s) => document.querySelector(s);
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
  try { datos = await r.json(); } catch (_) { /* sin cuerpo JSON */ }
  if (!r.ok) {
    let msg = (datos && datos.mensaje) || "Error " + r.status;
    if (datos && datos.detalle && datos.detalle.length) msg += ": " + datos.detalle.map((d) => d.campo + " — " + d.mensaje).join("; ");
    throw new Error(msg);
  }
  return datos;
}

const marca = (si) => (si ? '<span class="badge ok">Registrada</span>' : '<span class="badge">Sin plantilla</span>');
let temporizador = null;
let objetivo = null; // { dni, tipo } del archivo que se va a subir

async function cargar() {
  const q = encodeURIComponent($("#busqueda").value.trim());
  try {
    const d = await api("/admin/api/ciudadanos?q=" + q);
    $("#total").textContent = d.total;
    $("#filas").innerHTML = d.ciudadanos.length
      ? d.ciudadanos.map((c) => `<tr>
          <td class="mono">${esc(c.numero_documento)}</td><td>${esc(c.nombres)}</td><td>${esc(c.apellidos)}</td>
          <td>${esc(c.fecha_nacimiento)}</td><td>${esc(c.genero)}</td><td>${marca(c.tiene_facial)}</td><td>${marca(c.tiene_huella)}</td>
          <td><div style="display:flex;gap:.35rem;flex-wrap:wrap">
            <button class="btn btn-ghost btn-sm" data-subir="facial" data-dni="${esc(c.numero_documento)}">${c.tiene_facial ? "Reemplazar" : "Subir"} rostro</button>
            <button class="btn btn-ghost btn-sm" data-subir="huella" data-dni="${esc(c.numero_documento)}">${c.tiene_huella ? "Reemplazar" : "Subir"} huella</button>
            <button class="btn btn-danger btn-sm" data-borrar="${esc(c.numero_documento)}">Eliminar</button>
          </div></td></tr>`).join("")
      : '<tr><td colspan="8" class="vacio">No hay ciudadanos que coincidan.</td></tr>';
  } catch (e) { aviso(e.message, "err"); }
}

$("#form-ciudadano").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target;
  const cuerpo = Object.fromEntries(new FormData(f).entries());
  try {
    await api("/admin/api/ciudadanos", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    aviso("Ciudadano " + cuerpo.numero_documento + " registrado");
    f.reset();
    cargar();
  } catch (e) { aviso(e.message, "err"); }
});

$("#busqueda").addEventListener("input", () => { clearTimeout(temporizador); temporizador = setTimeout(cargar, 250); });
$("#btn-recargar").addEventListener("click", cargar);

$("#filas").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button");
  if (!b) return;
  if (b.dataset.subir) {
    objetivo = { dni: b.dataset.dni, tipo: b.dataset.subir };
    $("#archivo").value = "";
    $("#archivo").click();
  } else if (b.dataset.borrar) {
    if (!confirm("¿Eliminar al ciudadano " + b.dataset.borrar + " y sus plantillas?")) return;
    try { await api("/admin/api/ciudadanos/" + b.dataset.borrar, { method: "DELETE" }); aviso("Ciudadano eliminado"); cargar(); }
    catch (e) { aviso(e.message, "err"); }
  }
});

$("#archivo").addEventListener("change", async (ev) => {
  const archivo = ev.target.files[0];
  if (!archivo || !objetivo) return;
  const { dni, tipo } = objetivo;
  const fd = new FormData();
  fd.append("archivo", archivo);
  aviso("Procesando imagen " + (tipo === "facial" ? "facial (la primera vez carga el modelo y puede tardar)" : "de huella") + "…");
  try {
    const r = await api(`/admin/api/ciudadanos/${dni}/biometria/${tipo}`, { method: "POST", body: fd });
    aviso(r.tipo === "FACIAL" ? `Plantilla facial guardada (${r.dimensiones} dimensiones)` : `Plantilla de huella guardada (${r.minucias} minucias, calidad NFIQ2 ${r.calidad_nfiq2})`);
    cargar();
  } catch (e) { aviso(e.message, "err"); }
  objetivo = null;
});

cargar();
