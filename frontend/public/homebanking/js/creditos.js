/* RF-HB-007 – Pago de cuota de crédito (CR-INT-08)
   Usa puentes: /api/cobranza/clientes/{codCliente}/creditos, /api/cobranza/creditos/{codCredito}/monto-a-pagar,
   /api/cobranza/cr-int-08/pagos
   NOTA: Token Matriz, evaluar-riesgo y validar topes NO DISPONIBLES en esta versión
*/

(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();
  crearConsola();

  const msg = document.getElementById("msgCredito");
  const contenedor = document.getElementById("creditos");
  const form = document.getElementById("formCredito");
  const selCredito = document.getElementById("selCredito");
  const selCuenta = document.getElementById("selCuenta");
  const montoPago = document.getElementById("montoPago");
  const detalle = document.getElementById("detalleCredito");
  const btn = document.getElementById("btnPagar");
  const resultado = document.getElementById("resultadoCredito");
  const subResultado = document.getElementById("subResultadoCredito");

  let creditos = [];
  let cuentas = [];
  let creditoActual = null;
  let idemActual = null;

  if (!Bus.esApi) {
    avisoModoLocal(msg);
    btn.disabled = true;
    btn.title = "Pago de créditos requiere COBRANZA y CUENTAS";
  }

  function pintarCreditos() {
    contenedor.innerHTML = "";
    if (!creditos.length) {
      contenedor.innerHTML = `<div class="nota">No se encontraron créditos asociados al cliente.</div>`;
      return;
    }
    creditos.forEach(c => {
      const card = document.createElement("div");
      card.className = "credito-card" + (creditoActual && creditoActual.codCredito === c.codCredito ? " sel" : "");
      card.innerHTML = `
        <div>
          <div class="cod">${c.codCredito}</div>
          <h3>${c.producto}</h3>
        </div>
        <div class="monto">${fmt.moneda(c.saldo, c.moneda)}</div>
        <div class="fila"><span>Cuota</span><b>${fmt.moneda(c.cuota, c.moneda)}</b></div>
        <div class="fila"><span>Cuotas pendientes</span><b>${c.cuotasPendientes}</b></div>
        <div class="fila"><span>Estado</span><b>${c.estado}</b></div>
        <button type="button" class="btn btn-sec btn-sm" data-credito="${c.codCredito}">Seleccionar</button>`;
      card.querySelector("button").addEventListener("click", () => seleccionarCredito(c.codCredito));
      contenedor.appendChild(card);
    });
  }

  function llenarSelectCredito() {
    selCredito.innerHTML = creditos.map(c =>
      `<option value="${c.codCredito}">${c.codCredito} · ${c.producto}</option>`
    ).join("");
    if (creditoActual) selCredito.value = creditoActual.codCredito;
  }

  function llenarCuentas() {
    if (!creditoActual) {
      selCuenta.innerHTML = "";
      return;
    }
    const disponibles = cuentas.filter(c => c.moneda === creditoActual.moneda);
    selCuenta.innerHTML = disponibles.map(c =>
      `<option value="${c.numCuenta}">${c.numCuenta} · ${c.tipoCuenta} · ${fmt.moneda(c.saldoDisponible, c.moneda)}</option>`
    ).join("");
    if (!disponibles.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = `Sin cuentas activas en ${creditoActual.moneda}`;
      selCuenta.appendChild(opt);
    }
  }

  function seleccionarCredito(codigo) {
    creditoActual = creditos.find(c => c.codCredito === codigo) || null;
    if (!creditoActual) return;
    selCredito.value = codigo;
    llenarCuentas();
    montoPago.value = Math.min(creditoActual.cuota, creditoActual.saldo).toFixed(2);
    montoPago.max = Math.min(creditoActual.saldo, Number(montoPago.value) || creditoActual.saldo).toFixed(2);
    detalle.innerHTML = `
      <b>${creditoActual.producto}</b> · ${creditoActual.codCredito}<br>
      Saldo del crédito: <b>${fmt.moneda(creditoActual.saldo, creditoActual.moneda)}</b> ·
      Cuota: <b>${fmt.moneda(creditoActual.cuota, creditoActual.moneda)}</b> ·
      Cuotas pendientes: <b>${creditoActual.cuotasPendientes}</b> ·
      Cuenta asociada: <b>${creditoActual.cuentaAsociada}</b>.`;
    pintarCreditos();
    idemActual = null;
    ocultarMensaje(msg);
  }

  async function cargar() {
    try {
      const [rc, rp] = await Promise.all([
        Bus.obtenerCreditosCliente(),
        Bus.consultarPosicion(sesion.codCliente, null)
      ]);
      creditos = rc.creditos || [];
      cuentas = rp.cuentas || [];
      const anterior = creditoActual ? creditoActual.codCredito : null;
      pintarCreditos();
      llenarSelectCredito();
      if (anterior && creditos.some(c => c.codCredito === anterior)) {
        seleccionarCredito(anterior);
      } else if (creditos.length) {
        seleccionarCredito(creditos[0].codCredito);
      }
    } catch (e) {
      if (e.codigo === "MODO_LOCAL_LIMITADO") avisoModoLocal(msg);
      else mostrarMensaje(msg, "error", e.mensaje || "No se pudieron recuperar los créditos.");
    }
  }

  selCredito.addEventListener("change", () => seleccionarCredito(selCredito.value));
  montoPago.addEventListener("input", () => { idemActual = null; });
  selCuenta.addEventListener("change", () => { idemActual = null; });

  function validar() {
    if (!creditoActual) { mostrarMensaje(msg, "error", "Seleccione un crédito."); return null; }
    const cuenta = cuentas.find(c => c.numCuenta === selCuenta.value);
    if (!cuenta) { mostrarMensaje(msg, "error", "Seleccione una cuenta de cargo válida."); return null; }
    const valor = Number(montoPago.value);
    if (!Number.isFinite(valor) || valor <= 0) { mostrarMensaje(msg, "error", "Ingrese un monto mayor a cero."); return null; }
    if (valor > cuenta.saldoDisponible + 1e-9) { mostrarMensaje(msg, "error", "El monto supera el saldo disponible de la cuenta de cargo."); return null; }
    if (valor > creditoActual.saldo + 1e-9) { mostrarMensaje(msg, "error", "El monto supera el saldo del crédito."); return null; }
    return { cuenta, monto: Math.round(valor * 100) / 100 };
  }

  function pintarResultado(r) {
    resultado.hidden = false;
    subResultado.textContent = `Pago ${r.estadoPago} · ${r.fechaHora}`;
    const constancia = Bus.constanciaUrl(r.constanciaPDF || r.constancia);
    resultado.innerHTML = `
      <div class="resumen-operacion">
        <h3>Pago de crédito ${r.estadoPago}</h3>
        <div class="operacion-id">${r.idPago}</div>
        ${r.idempotente ? '<span class="badge warn">Reintento idempotente</span>' : ""}
        <div class="detalle-lista">
          <div><span>Crédito</span><b>${r.codCredito} · ${r.producto}</b></div>
          <div><span>Monto pagado</span><b>${fmt.moneda(r.montoPagado, r.moneda)}</b></div>
          <div><span>Saldo del crédito</span><b>${fmt.moneda(r.saldoCredito, r.moneda)}</b></div>
          <div><span>Cuotas pendientes</span><b>${r.cuotasPendientes}</b></div>
          <div><span>Saldo disponible</span><b>${fmt.moneda(r.saldoActualizado?.saldoDisponible || 0, r.moneda)}</b></div>
          <div><span>Asiento Core</span><b class="num">${r.idAsientoCore || "N/D"}</b></div>
          <div><span>UUID</span><b class="num">${r.uuidTransaccion || "N/D"}</b></div>
        </div>
        <div class="constancia-acciones">
          ${constancia ? `<a class="btn" href="${constancia}" target="_blank" rel="noopener">Descargar constancia PDF</a>` : ""}
          <button type="button" class="btn btn-sec" id="btnNuevoPago">Nuevo pago</button>
        </div>
      </div>`;
    const btnNuevo = document.getElementById("btnNuevoPago");
    if (btnNuevo) {
      btnNuevo.addEventListener("click", () => {
        resultado.hidden = true;
        subResultado.textContent = "Aún no se ha procesado ningún pago.";
        idemActual = null;
        cargar();
      });
    }
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarMensaje(msg);
    if (!Bus.esApi) { avisoModoLocal(msg); return; }
    const v = validar();
    if (!v) return;
    if (!idemActual) idemActual = Bus.nuevoIdempotencyKey();

    cargando(btn, true, "Procesando");
    try {
      // Token Matriz, evaluación de riesgo y topes no tienen ruta en el producto: no se piden.

      // Pago CR-INT-08
      const r = await Bus.pagarCuota(creditoActual.codCredito, {
        numCuentaOrigen: v.cuenta.numCuenta,
        montoPago: v.monto,
        moneda: creditoActual.moneda
      }, idemActual);

      mostrarMensaje(msg, "ok", `Pago ${r.idPago || r.uuidTransaccion} procesado correctamente.`);
      pintarResultado(r);
      idemActual = null;
      await cargar();
    } catch (err) {
      if (err.codigo === "TOKEN_CANCELADO") {
        mostrarMensaje(msg, "info", err.mensaje);
      } else if (err.codigo === "BUS_TIMEOUT") {
        mostrarMensaje(msg, "warn",
          "El Bus no respondió. El pago queda PENDIENTE / NO CONFIRMADA. No se reintentó automáticamente; verifique antes de repetir.");
      } else if (err.codigo === "NO_DISPONIBLE") {
        mostrarMensaje(msg, "error", "Pago de crédito: No disponible en esta versión (requiere endpoint /api/cobranza/cr-int-08/pagos).");
      } else {
        mostrarMensaje(msg, "error", err.mensaje || "El pago no pudo procesarse.");
      }
      // La llave (referenciaTransaccion) se conserva: reintentar el mismo pago no cobra dos
      // veces. Cambia al editar el monto o la cuenta.
    } finally {
      cargando(btn, false);
    }
  });

  cargar();
})();