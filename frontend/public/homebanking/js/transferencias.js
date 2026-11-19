(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();

  const form = document.getElementById("formTrans");
  const msg = document.getElementById("msgTrans");
  const tabs = document.getElementById("tabsTipo");
  const selOrigen = document.getElementById("selOrigen");
  const selDestino = document.getElementById("selDestinoPropia");
  const ctaTercero = document.getElementById("ctaTercero");
  const titularTercero = document.getElementById("titularTercero");
  const monto = document.getElementById("monto");
  const txtMoneda = document.getElementById("txtMoneda");
  const txtDisponible = document.getElementById("txtDisponible");
  const glosa = document.getElementById("glosa");
  const btn = document.getElementById("btnTransferir");
  const resultado = document.getElementById("resultado");
  const subResultado = document.getElementById("subResultado");

  let cuentas = [];
  let tipo = "PROPIA";
  let idemActual = null;

  const cuentaActual = () => cuentas.find(c => c.numCuenta === selOrigen.value);
  const monedaActual = () => cuentaActual() ? cuentaActual().moneda : "PEN";

  function pintarDisponible() {
    const c = cuentaActual();
    if (!c) {
      txtDisponible.value = "—";
      txtMoneda.value = "—";
      return;
    }
    txtDisponible.value = fmt.moneda(c.saldoDisponible, c.moneda);
    txtMoneda.value = c.moneda;
    monto.max = c.saldoDisponible;
  }

  function llenarDestinosPropios() {
    const c = cuentaActual();
    if (!c) {
      selDestino.innerHTML = "";
      return;
    }
    const destinos = cuentas.filter(d => d.numCuenta !== c.numCuenta && d.moneda === c.moneda);
    selDestino.innerHTML = destinos.length
      ? destinos.map(d => `<option value="${d.numCuenta}">${d.numCuenta} · ${d.tipoCuenta}</option>`).join("")
      : `<option value="">Sin cuentas propias en ${c.moneda}</option>`;
  }

  async function cargarCuentas(conservarOrigen = true) {
    try {
      const pos = await Bus.consultarPosicion(sesion.codCliente);
      cuentas = pos.cuentas || [];
      const anterior = conservarOrigen ? selOrigen.value : null;
      selOrigen.innerHTML = cuentas.map(c =>
        `<option value="${c.numCuenta}">${c.numCuenta} · ${c.tipoCuenta} · ${c.moneda}</option>`
      ).join("");
      const params = new URLSearchParams(window.location.search);
      const solicitada = anterior || params.get("origen");
      if (solicitada && cuentas.some(c => c.numCuenta === solicitada)) {
        selOrigen.value = solicitada;
      }
      llenarDestinosPropios();
      pintarDisponible();
      if (!cuentas.length) mostrarMensaje(msg, "warn", "No se encontraron cuentas activas.");
    } catch (e) {
      mostrarMensaje(msg, "error", e.mensaje || "No se pudieron recuperar sus cuentas.");
    }
  }

  function cambiarTipo(nuevo) {
    tipo = nuevo;
    [...tabs.querySelectorAll(".tab")].forEach(b => b.classList.toggle("activo", b.dataset.tipo === tipo));
    document.getElementById("bloquePropia").hidden = tipo !== "PROPIA";
    document.getElementById("bloqueTercero").hidden = tipo !== "TERCERO";
    idemActual = null;
    ocultarMensaje(msg);
  }

  tabs.addEventListener("click", e => {
    const b = e.target.closest(".tab");
    if (b) cambiarTipo(b.dataset.tipo);
  });

  selOrigen.addEventListener("change", () => {
    llenarDestinosPropios();
    pintarDisponible();
    idemActual = null;
  });

  [monto, ctaTercero, titularTercero, glosa, selDestino].forEach(el => {
    if (el) el.addEventListener("input", () => { idemActual = null; });
  });

  function validar() {
    const c = cuentaActual();
    if (!c) { mostrarMensaje(msg, "error", "Seleccione una cuenta de origen."); return null; }
    const valor = Number(monto.value);
    if (!Number.isFinite(valor) || valor <= 0) {
      mostrarMensaje(msg, "error", "Ingrese un monto mayor a cero.");
      return null;
    }
    if (valor > c.saldoDisponible + 1e-9) {
      mostrarMensaje(msg, "error", "El monto supera el saldo disponible de la cuenta de origen.");
      return null;
    }
    if (tipo === "PROPIA") {
      if (!selDestino.value) { mostrarMensaje(msg, "error", "Seleccione una cuenta de destino propia."); return null; }
      if (selDestino.value === c.numCuenta) { mostrarMensaje(msg, "error", "La cuenta de origen y destino no pueden ser la misma."); return null; }
    }
    if (tipo === "TERCERO") {
      if (!ctaTercero.value.trim()) { mostrarMensaje(msg, "error", "Ingrese la cuenta destino BNA."); return null; }
      if (ctaTercero.value.trim() === c.numCuenta) { mostrarMensaje(msg, "error", "La cuenta de destino no puede ser la cuenta de origen."); return null; }
    }
    return { cuenta: c, monto: Math.round(valor * 100) / 100 };
  }

  function construirPayload(v) {
    const p = {
      tipo,
      cuentaOrigen: v.cuenta.numCuenta,
      monto: v.monto,
      moneda: v.cuenta.moneda,
      descripcion: glosa.value.trim()
    };
    if (tipo === "PROPIA") {
      p.cuentaDestino = selDestino.value;
    } else {
      p.cuentaDestino = ctaTercero.value.trim();
      p.titularDestino = titularTercero.value.trim();
    }
    return p;
  }

  function pintarResultado(r) {
    resultado.hidden = false;
    subResultado.textContent = `Operación ${r.estado} · ${r.fechaHora}`;
    const constancia = Bus.constanciaUrl(r.constanciaPDF);
    resultado.innerHTML = `
      <div class="resumen-operacion">
        <h3>Transferencia procesada</h3>
        <div class="operacion-id">${r.idTransferencia}</div>
        ${r.idempotente ? '<span class="badge warn">Operación ya registrada</span>' : ""}
        <div class="detalle-lista">
          <div><span>Tipo</span><b>${r.tipo}</b></div>
          <div><span>Monto</span><b>${fmt.moneda(r.monto, r.moneda)}</b></div>
          <div><span>Cuenta origen</span><b class="num">${r.cuentaOrigen}</b></div>
          <div><span>Cuenta destino</span><b class="num">${r.cuentaDestino}</b></div>
          <div><span>Entidad destino</span><b>${r.entidadDestino}</b></div>
          <div><span>Titular destino</span><b>${r.titularDestino || "—"}</b></div>
          <div><span>Estado</span><b>${r.estado}</b></div>
          <div><span>Saldo disponible</span><b>${fmt.moneda(r.saldoActualizado?.saldoDisponible || 0, r.moneda)}</b></div>
          <div><span>Comprobante</span><b class="num">${r.idAsientoCore || "N/D"}</b></div>
          <div><span>Identificador de operación</span><b class="num">${r.uuidTransaccion || "N/D"}</b></div>
        </div>
        <div class="constancia-acciones">
          ${constancia ? `<a class="btn" href="${constancia}" target="_blank" rel="noopener">Descargar constancia PDF</a>` : ""}
          <button type="button" class="btn btn-sec" id="btnNuevaTrans">Nueva transferencia</button>
        </div>
      </div>`;
    const btnNueva = document.getElementById("btnNuevaTrans");
    if (btnNueva) {
      btnNueva.addEventListener("click", () => {
        resultado.hidden = true;
        subResultado.textContent = "Aún no se ha procesado ninguna transferencia.";
        form.reset();
        idemActual = null;
        cargarCuentas(true);
      });
    }
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarMensaje(msg);
    const v = validar();
    if (!v) return;
    if (!idemActual) idemActual = Bus.nuevoIdempotencyKey();
    const payload = construirPayload(v);
    cargando(btn, true, "Procesando");
    try {
      const r = await Bus.transferencia({
        ...payload,
        uuidTransaccion: idemActual,
        idempotencyKey: idemActual
      }, idemActual);

      mostrarMensaje(msg, "ok", `Transferencia ${r.idTransferencia} procesada correctamente.`);
      pintarResultado(r);
      idemActual = null;  // confirmada: la próxima operación lleva otra llave
      await cargarCuentas(true);
    } catch (err) {
      if (err.codigo === "TOKEN_CANCELADO") {
        mostrarMensaje(msg, "info", err.mensaje);
      } else if (err.codigo === "BUS_TIMEOUT") {
        mostrarMensaje(msg, "warn",
          "El servicio no respondió. No se reintentó automáticamente; conserve el identificador y verifique antes de repetir.");
      } else {
        mostrarMensaje(msg, "error", err.mensaje || "La transferencia no pudo procesarse.");
      }
      // Conservar la llave evita duplicar la operación si la respuesta se perdió.
    } finally {
      cargando(btn, false);
    }
  });

  cargarCuentas(false);
})();