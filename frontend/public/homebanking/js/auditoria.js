/* INT-13 – Consulta de auditoría centralizada y exportación de evidencia */

(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();
  crearConsola();

  const msg = document.getElementById("msgAuditoria");
  const tabla = document.getElementById("tablaAuditoria");
  const filtroModulo = document.getElementById("filtroModulo");
  const filtroTipo = document.getElementById("filtroTipo");
  const filtroResultado = document.getElementById("filtroResultado");
  const btnActualizar = document.getElementById("btnActualizar");
  const btnCsv = document.getElementById("btnCsv");

  let eventosActuales = [];

  if (!Bus.esApi) {
    avisoModoLocal(msg);
    btnActualizar.disabled = true;
    btnCsv.disabled = true;
  }

  async function consultar(limit, filtros = {}) {
    return Bus.consultarAuditoria(limit, filtros);
  }

  function opciones(select, valores, etiquetaTodos) {
    const actual = select.value;
    select.innerHTML = `<option value="">${etiquetaTodos}</option>` +
      valores.map(v => `<option value="${v}">${v}</option>`).join("");
    if (valores.includes(actual)) select.value = actual;
  }

  function pintarKpis(eventos, total) {
    const ok = eventos.filter(e => e.resultado === "OK").length;
    const error = eventos.filter(e => e.resultado === "ERROR").length;
    const pend = eventos.filter(e => e.resultado === "PENDIENTE").length;
    const trans = eventos.filter(e => e.tipoEvento === "TRANSFERENCIA").length;
    const pagos = eventos.filter(e => e.tipoEvento === "PAGO_CREDITO").length;
    document.getElementById("kpiTotal").textContent = total;
    document.getElementById("kpiOk").textContent = ok;
    document.getElementById("kpiError").textContent = error;
    document.getElementById("kpiPendiente").textContent = pend;
    document.getElementById("kpiTrans").textContent = trans;
    document.getElementById("kpiPagos").textContent = pagos;
  }

  function claseResultado(r) {
    if (r === "OK") return "ok";
    if (r === "PENDIENTE") return "pendiente";
    return "error";
  }

  function pintarTabla(eventos) {
    eventosActuales = eventos;
    if (!eventos.length) {
      tabla.innerHTML = `<tr><td colspan="10" class="vacio">Sin eventos para los filtros seleccionados.</td></tr>`;
      return;
    }
    tabla.innerHTML = eventos.map(e => `
      <tr>
        <td class="num">${e.fechaHora}</td>
        <td class="num">${e.idEvento}</td>
        <td>${e.modulo}</td>
        <td>${e.tipoEvento}</td>
        <td class="num">${e.usuario}</td>
        <td>${e.canal}</td>
        <td class="num">${e.ip}</td>
        <td class="num">${(e.uuid || "").slice(0, 18)}${(e.uuid || "").length > 18 ? "…" : ""}</td>
        <td><span class="badge ${claseResultado(e.resultado)}">${e.resultado}</span></td>
        <td class="detalle">${e.detalle || ""}</td>
      </tr>`).join("");
  }

  async function cargar() {
    ocultarMensaje(msg);
    if (!Bus.esApi) { avisoModoLocal(msg); return; }
    try {
      const todos = await consultar(500);
      opciones(filtroModulo, todos.modulos || [], "Todos");
      opciones(filtroTipo, todos.tipos || [], "Todos");
      const filtrados = await consultar(250, {
        modulo: filtroModulo.value,
        tipo: filtroTipo.value,
        resultado: filtroResultado.value
      });
      pintarKpis(todos.eventos || [], todos.total || 0);
      pintarTabla(filtrados.eventos || []);
      if (!todos.total) mostrarMensaje(msg, "info", "Aún no hay eventos. Realice una operación para generar trazabilidad.");
    } catch (e) {
      if (e.codigo === "SESION_EXPIRADA" || e.codigo === "SESION_INVALIDA") {
        Sesion.cerrar();
        window.location.href = "index.html";
        return;
      }
      if (e.codigo === "NO_DISPONIBLE") {
        mostrarMensaje(msg, "error", "Auditoría: No disponible en esta versión (requiere endpoint /api/core/coredb/auditoria).");
      } else {
        mostrarMensaje(msg, "error", e.mensaje || "No se pudo consultar la auditoría.");
      }
    }
  }

  function descargarCsv() {
    if (!eventosActuales.length) {
      mostrarMensaje(msg, "warn", "No hay eventos para exportar con los filtros actuales.");
      return;
    }
    const cols = ["idEvento", "fechaHora", "modulo", "tipoEvento", "usuario", "canal", "ip", "uuid", "resultado", "detalle"];
    const esc = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
    const filas = [cols.join(",")].concat(eventosActuales.map(e => cols.map(c => esc(e[c])).join(",")));
    const blob = new Blob(["\uFEFF" + filas.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `auditoria_homebanking_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    mostrarMensaje(msg, "ok", `Se exportaron ${eventosActuales.length} evento(s) de auditoría.`);
  }

  btnActualizar.addEventListener("click", cargar);
  filtroModulo.addEventListener("change", cargar);
  filtroTipo.addEventListener("change", cargar);
  filtroResultado.addEventListener("change", cargar);
  btnCsv.addEventListener("click", descargarCsv);
  cargar();
})();