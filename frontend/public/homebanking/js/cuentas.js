/* RF-HB-002 – Consultar saldos de cuentas a partir de la tarjeta (INT-08) */

(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();
  crearConsola();

  const form = document.getElementById("formTarjeta");
  const inp = document.getElementById("numTarjeta");
  const btn = document.getElementById("btnObtener");
  const msg = document.getElementById("msgCuentas");
  const chips = document.getElementById("chipsTarjetas");
  const pNum = document.getElementById("plasticoNumero");
  const pTit = document.getElementById("plasticoTitular");
  const pVen = document.getElementById("plasticoVenc");
  const panelVerif = document.getElementById("verifBloqueo");
  const btnVerificar = document.getElementById("btnVerificarBloqueo");
  let idVerificacion = null;

  /* ---------- Tarjetas del cliente ---------- */
  (async function cargarTarjetas() {
    try {
      const r = await Bus.obtenerTarjetasAsociadas(sesion.codCliente);
      chips.innerHTML = "";
      r.tarjetas.forEach(t => {
        const grupo = document.createElement("span");
        grupo.className = "chip-grupo";
        const b = document.createElement("button");
        b.type = "button";
        b.className = "chip";
        b.dataset.num = t.numTarjeta.replace(/\s/g, "");
        b.dataset.venc = t.vencimiento;
        b.dataset.titular = sesion.nombres;
        b.innerHTML = `${t.numTarjeta} <span class="tipo">${t.tipo} · ${t.estado}</span>`;
        if (t.estado !== "ACTIVA") b.style.opacity = ".6";
        b.addEventListener("click", () => {
          chips.querySelectorAll(".chip").forEach(c => c.classList.remove("sel"));
          b.classList.add("sel");
          inp.value = formatear(b.dataset.num);
          pintarPlastico();
        });
        grupo.appendChild(b);
        if (t.estado === "ACTIVA" && t.idTarjeta) {
          const bloq = document.createElement("button");
          bloq.type = "button";
          bloq.className = "btn btn-sec btn-sm";
          bloq.dataset.bloquear = t.idTarjeta;
          bloq.textContent = "Bloquear";
          bloq.setAttribute("aria-label", `Bloquear la tarjeta terminada en ${t.numTarjeta.slice(-4)}`);
          bloq.addEventListener("click", () => bloquear(t, b, bloq));
          grupo.appendChild(bloq);
        }
        chips.appendChild(grupo);
      });
    } catch (e) {
      chips.innerHTML = `<span class="tono-suave">No fue posible recuperar sus tarjetas: ${e.mensaje || "servicio no disponible"}.</span>`;
    }
  })();

  /* ---------- Bloqueo de una tarjeta ---------- */
  async function bloquear(t, chip, boton) {
    const fin = t.numTarjeta.slice(-4);
    const pregunta = `¿Bloquear la tarjeta terminada en ${fin}?\n\n` +
      "Dejará de aceptarse en el cajero. El desbloqueo no se hace en el Home Banking: lo hace el banco.";
    if (!window.confirm(pregunta)) return;
    ocultarMensaje("msgBloqueo");
    cargando(boton, true, "Bloqueando");
    try {
      const r = await Bus.bloquearTarjeta(t.idTarjeta, "Bloqueo solicitado por el cliente en Home Banking");
      t.estado = (r && r.estado_tarjeta) || "BLOQUEADA";
      chip.querySelector(".tipo").textContent = `${t.tipo} · ${t.estado}`;
      chip.style.opacity = ".6";
      boton.remove();
      mostrarMensaje("msgBloqueo", "ok", `Tarjeta terminada en ${fin} bloqueada. Ya no se acepta en el cajero.`);
      idVerificacion = t.idTarjeta;
      ocultarMensaje("msgVerificacion");
      if (panelVerif) panelVerif.hidden = false;
    } catch (err) {
      cargando(boton, false);
      mostrarMensaje("msgBloqueo", "error",
        `No se pudo bloquear la tarjeta terminada en ${fin}: ${err.mensaje || "servicio no disponible"}.`);
    }
  }

  /* ---------- Verificación del bloqueo contra TARJETAS ---------- */
  async function verificarBloqueo() {
    if (!idVerificacion) return;
    ocultarMensaje("msgVerificacion");
    cargando(btnVerificar, true, "Consultando");
    try {
      const r = await Bus.obtenerTarjetasAsociadas(sesion.codCliente);
      const tarjeta = (r.tarjetas || []).find(t => t.idTarjeta === idVerificacion);
      if (!tarjeta) {
        mostrarMensaje("msgVerificacion", "error", "La tarjeta ya no aparece en la lista del cliente.");
        return;
      }
      const fin = tarjeta.numTarjeta.slice(-4);
      if (tarjeta.estado === "BLOQUEADA") {
        mostrarMensaje("msgVerificacion", "ok",
          `TARJETAS confirma BLOQUEADA la tarjeta terminada en ${fin}. Falta la comprobación en el cajero.`);
      } else {
        mostrarMensaje("msgVerificacion", "warn",
          `TARJETAS todavía reporta ${tarjeta.estado} la tarjeta terminada en ${fin}. Repita el bloqueo o avise al equipo de Tarjetas.`);
      }
    } catch (err) {
      mostrarMensaje("msgVerificacion", "error",
        `No se pudo consultar el estado: ${err.mensaje || "servicio no disponible"}.`);
    } finally {
      cargando(btnVerificar, false);
    }
  }

  if (btnVerificar) btnVerificar.addEventListener("click", verificarBloqueo);

  /* ---------- Utilidades de interfaz ---------- */
  const formatear = v => (v.match(/.{1,4}/g) || []).join(" ");

  function soloDigitos() {
    return inp.value.replace(/\D/g, "").slice(0, 16);
  }

  function pintarPlastico() {
    const d = soloDigitos();
    pNum.textContent = formatear(d) || "•••• •••• •••• ••••";
    const sel = chips.querySelector(".chip.sel");
    pTit.textContent = sel ? (sel.dataset.titular || "TITULAR").toUpperCase() : (sesion.nombres || "TITULAR").toUpperCase();
    pVen.textContent = sel ? sel.dataset.venc : "--/--";
  }

  inp.addEventListener("input", () => {
    inp.value = formatear(soloDigitos());
    const sel = chips.querySelector(".chip.sel");
    if (sel && sel.dataset.num !== soloDigitos()) sel.classList.remove("sel");
    pintarPlastico();
  });

  pintarPlastico();

  /* ---------- Indicador de pasos ---------- */
  function pintarPasos(consultada) {
    document.getElementById("pasoTarjeta").className = `paso ${consultada ? "listo" : "activo"}`;
    document.getElementById("pasoCuentas").className = `paso ${consultada ? "activo" : ""}`;
  }

  /* Recuerda la última tarjeta consultada (al volver desde movimientos) */
  try {
    const ultima = sessionStorage.getItem("hb_ultima_tarjeta");
    if (ultima) inp.value = formatear(ultima);
    pintarPlastico();
  } catch (e) { /* almacenamiento no disponible */ }

  /* ---------- Consulta ---------- */
  form.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarMensaje(msg);
    ocultarMensaje("msgOmitidas");

    const num = soloDigitos();
    if (num.length !== 16) {
      mostrarMensaje(msg, "error", "Ingrese los 16 dígitos de su tarjeta.");
      return;
    }

    cargando(btn, true, "Consultando");
    try {
      /* 1. Módulo Tarjetas: verificar titularidad - NO DISPONIBLE EN ESTA VERSIÓN */
      try {
        await Bus.verificarTitularidad(sesion.codCliente, num);
      } catch (err) {
        if (err.codigo === "NO_DISPONIBLE") {
          mostrarMensaje(msg, "warn", "Verificar titularidad: No disponible en esta versión. Se omite esta validación.");
        } else {
          throw err;
        }
      }

      /* 2. Módulo Cuentas: posición consolidada (INT-08) */
      const pos = await Bus.consultarPosicion(sesion.codCliente, null);

      // Crear objeto tarjeta simulado para pintarResultado (sin verificar titularidad)
      const tarjeta = {
        numTarjeta: num,
        marca: "Tarjeta",
        vencimiento: "--/--",
        estado: "DESCONOCIDA"
      };
      pintarResultado(tarjeta, pos);
      pintarPasos(true);
      try { sessionStorage.setItem("hb_ultima_tarjeta", num); } catch (e) { /* no disponible */ }
      mostrarMensaje(msg, "ok", `Se obtuvieron ${pos.totalCuentasActivas} cuenta(s) activa(s).`);
    } catch (err) {
      pintarPasos(false);
      if (err.codigo === "BUS_TIMEOUT") {
        mostrarMensaje(msg, "warn",
          "El Bus de Servicios no respondió. La consulta queda PENDIENTE / NO CONFIRMADA; no se muestra información parcial. Intente nuevamente.");
      } else {
        mostrarMensaje(msg, "error", err.mensaje || "La consulta no pudo procesarse. Intente nuevamente.");
      }
      limpiarResultado();
    } finally {
      cargando(btn, false);
    }
  });

  /* ---------- Pintado ---------- */
  function limpiarResultado() {
    document.getElementById("resumen").hidden = true;
    document.getElementById("envTabla").hidden = true;
    document.getElementById("tablaCuentas").innerHTML = "";
    document.getElementById("subResultado").textContent = "Aún no se ha consultado ninguna tarjeta.";
  }

  function pintarResultado(tarjeta, pos) {
    document.getElementById("subResultado").textContent =
      `${tarjeta.marca} · venc. ${tarjeta.vencimiento} · estado ${tarjeta.estado} · cliente ${pos.codCliente}`;

    document.getElementById("resumen").hidden = false;
    document.getElementById("resTarjeta").textContent = tarjeta.numTarjeta;
    document.getElementById("resTarjetaDet").textContent = `${tarjeta.marca} · VEN ${tarjeta.vencimiento}`;
    document.getElementById("resCantidad").textContent = pos.totalCuentasActivas;

    const pen = pos.posicionConsolidada.PEN || 0;
    const usd = pos.posicionConsolidada.USD || 0;
    document.getElementById("resPen").textContent = fmt.moneda(pen, "PEN");
    document.getElementById("resUsd").textContent = fmt.moneda(usd, "USD");
    document.getElementById("resPenDet").textContent = pos.cuentas.some(c => c.moneda === "PEN") ? "saldo disponible" : "sin cuentas en soles";
    document.getElementById("resUsdDet").textContent = pos.cuentas.some(c => c.moneda === "USD") ? "saldo disponible" : "sin cuentas en dólares";

    const tb = document.getElementById("tablaCuentas");
    tb.innerHTML = "";
    pos.cuentas.forEach(c => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="num">${c.numCuenta}</td>
        <td>${c.tipoCuenta}</td>
        <td class="tono-suave">${c.titularidad}</td>
        <td><span class="badge info">${c.moneda}</span></td>
        <td class="der num">${fmt.moneda(c.saldoContable, c.moneda)}</td>
        <td class="der num pos">${fmt.moneda(c.saldoDisponible, c.moneda)}</td>
        <td><span class="badge ok">${c.estado}</span></td>
        <td class="der" style="white-space:nowrap">
          <button class="btn btn-sec btn-sm" data-cuenta="${c.numCuenta}">Movimientos</button>
          <button class="btn btn-sm" data-transferir="${c.numCuenta}">Transferir</button>
        </td>`;
      tb.appendChild(tr);
    });
    tb.querySelectorAll("button[data-cuenta]").forEach(b => {
      b.addEventListener("click", () => {
        window.location.href = `movimientos.html?cuenta=${encodeURIComponent(b.dataset.cuenta)}`;
      });
    });
    tb.querySelectorAll("button[data-transferir]").forEach(b => {
      b.addEventListener("click", () => {
        window.location.href = `transferencias.html?origen=${encodeURIComponent(b.dataset.transferir)}`;
      });
    });

    document.getElementById("envTabla").hidden = false;

    const omitidas = pos.cuentasIgnoradas;
    if (omitidas > 0) {
      mostrarMensaje("msgOmitidas", "info",
        `Se omitieron ${omitidas} cuenta(s) que no se encuentran activas. RF-HB-002: el canal muestra únicamente cuentas ACTIVAS.`);
    }
  }
})();