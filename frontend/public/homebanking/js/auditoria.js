/* Registro de actividad: las acciones de la bitácora del banco (COREDB), para administradores y
   auditores. Todo lo que llega del servidor se muestra como texto (textContent), nunca como HTML. */

(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();

  const msg = document.getElementById("msgAuditoria");
  const contenido = document.getElementById("contenidoAuditoria");
  const tabla = document.getElementById("tablaAuditoria");
  const resumen = document.getElementById("resumenAuditoria");
  const filtroModulo = document.getElementById("filtroModulo");
  const filtroAccion = document.getElementById("filtroTipo");
  const btnActualizar = document.getElementById("btnActualizar");
  const btnCsv = document.getElementById("btnCsv");

  const SIN_PERMISO = "Esta sección es solo para administradores y auditores del banco. Tu usuario no tiene " +
    "permiso para ver el registro de actividad.";
  const MODULOS = {
    CORE: "Núcleo del banco", "SOLICITUD DE CREDITO": "Solicitud de crédito", CAPTACION: "Captación",
    EVALUACION: "Evaluación", DESEMBOLSO: "Desembolso", COBRANZA: "Cobranza", SEGURIDAD: "Seguridad",
    BILLETERA: "Billetera", CLIENTES: "Clientes", CUENTAS: "Cuentas", TARJETAS: "Tarjetas"
  };
  const legible = codigo => {
    const t = String(codigo || "").replace(/_/g, " ").toLowerCase();
    return t.charAt(0).toUpperCase() + t.slice(1);
  };
  const nombreModulo = m => MODULOS[m] || legible(m);
  const nombreAccion = legible;
  const ID_LARGO = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const sobreQue = e => {
    const id = String(e.idEntidad || "");
    return `${legible(e.entidad)} ${ID_LARGO.test(id) ? id.slice(0, 8) + "…" : id}`.trim();
  };
  // Hora de Arequipa (UTC−5): dd/mm/aaaa hh:mm:ss.
  function fecha(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return "";
    const p = new Intl.DateTimeFormat("es-PE", {
      timeZone: "America/Lima", day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
    }).formatToParts(d);
    const v = t => (p.find(x => x.type === t) || {}).value || "";
    return `${v("day")}/${v("month")}/${v("year")} ${v("hour")}:${v("minute")}:${v("second")}`;
  }

  let eventosActuales = [];

  function opciones(select, valores, etiquetaTodos, nombre) {
    const actual = select.value;
    select.replaceChildren(new Option(etiquetaTodos, ""), ...valores.map(v => new Option(nombre(v), v)));
    if (valores.includes(actual)) select.value = actual;
  }

  function celda(texto) {
    const td = document.createElement("td");
    td.textContent = texto;
    return td;
  }

  function pintarTabla(eventos) {
    eventosActuales = eventos;
    if (!eventos.length) {
      const td = celda("No hay acciones para los filtros elegidos.");
      td.colSpan = 5;
      td.className = "vacio";
      const tr = document.createElement("tr");
      tr.append(td);
      tabla.replaceChildren(tr);
    } else {
      tabla.replaceChildren(...eventos.map(e => {
        const tr = document.createElement("tr");
        tr.append(celda(fecha(e.fechaHora)), celda(nombreAccion(e.accion)), celda(nombreModulo(e.modulo)),
          celda(e.usuario || ""), celda(sobreQue(e)));
        return tr;
      }));
    }
    resumen.textContent = eventos.length === 1 ? "Se muestra 1 acción." : `Se muestran ${eventos.length} acciones.`;
  }

  function mostrarError(e) {
    if (e.codigo === "SESION_EXPIRADA" || e.codigo === "SESION_INVALIDA" || e.status === 401) {
      Sesion.cerrar();
      window.location.href = "index.html";
      return;
    }
    if (e.status === 403) {
      contenido.hidden = true;
      mostrarMensaje(msg, "warn", SIN_PERMISO);
    } else if (e.status === 0) {
      mostrarMensaje(msg, "error", "No hubo respuesta del servidor. Revisa tu conexión e intenta de nuevo.");
    } else {
      mostrarMensaje(msg, "error", "El registro de actividad no está disponible en este momento. Intenta de nuevo más tarde.");
    }
  }

  async function cargar() {
    ocultarMensaje(msg);
    try {
      const todos = await Bus.consultarAuditoria(200);
      opciones(filtroModulo, todos.modulos || [], "Todos", nombreModulo);
      opciones(filtroAccion, todos.acciones || [], "Todas", nombreAccion);
      const elegidos = filtroModulo.value || filtroAccion.value
        ? await Bus.consultarAuditoria(200, { modulo: filtroModulo.value, tipo: filtroAccion.value })
        : todos;
      pintarTabla(elegidos.eventos || []);
      if (!todos.total) mostrarMensaje(msg, "info", "Todavía no hay acciones registradas.");
    } catch (e) {
      mostrarError(e);
    }
  }

  function descargarCsv() {
    if (!eventosActuales.length) {
      mostrarMensaje(msg, "warn", "No hay acciones para descargar con los filtros elegidos.");
      return;
    }
    const cabecera = ["Fecha y hora", "Acción", "Módulo", "Usuario", "Entidad", "Identificador", "N.º de registro"];
    const esc = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
    const filas = [cabecera.map(esc).join(",")].concat(eventosActuales.map(e => [
      fecha(e.fechaHora), nombreAccion(e.accion), nombreModulo(e.modulo), e.usuario, legible(e.entidad), e.idEntidad,
      e.idEvento
    ].map(esc).join(",")));
    const blob = new Blob(["﻿" + filas.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `registro_actividad_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    mostrarMensaje(msg, "ok", `Se descargaron ${eventosActuales.length} acciones.`);
  }

  async function iniciar() {
    try {
      const permisos = await Bus.misPermisos();
      if (!permisos.includes("VER_AUDITORIA")) {
        mostrarMensaje(msg, "warn", SIN_PERMISO);
        return;
      }
    } catch (e) {
      mostrarError(e);
      return;
    }
    contenido.hidden = false;
    btnActualizar.addEventListener("click", cargar);
    filtroModulo.addEventListener("change", cargar);
    filtroAccion.addEventListener("change", cargar);
    btnCsv.addEventListener("click", descargarCsv);
    await cargar();
  }

  iniciar();
})();
