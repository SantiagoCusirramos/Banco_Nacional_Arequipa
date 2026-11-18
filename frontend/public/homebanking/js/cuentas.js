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

  /* ---------- Tarjetas del cliente ---------- */
  (async function cargarTarjetas() {
    try {
      const r = await Bus.obtenerTarjetasAsociadas(sesion.codCliente);
      chips.innerHTML = "";
      r.tarjetas.forEach(t => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "chip";
        b.dataset.num = t.numTarjeta.replace(/\s/g, "");
        b.dataset.venc = t.vencimiento;
        b.dataset.titular = sesion.nombres;
        b.innerHTML = `${t.numTarjeta} <span class="tipo">${t.tipo} · ${t.estado}</span>`;
        if (t.estado !== "ACTIVA") b.style.opacity = ".6";
        b.addEventListener("click", () => {
          [...chips.children].forEach(c => c.classList.remove("sel"));
          b.classList.add("sel");
          inp.value = formatear(b.dataset.num);
          pintarPlastico();
        });
        chips.appendChild(b);
      });
    } catch (e) {
      chips.innerHTML = `<span class="tono-suave">No fue posible recuperar sus tarjetas: ${e.mensaje || "servicio no disponible"}.</span>`;
    }
  })();

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