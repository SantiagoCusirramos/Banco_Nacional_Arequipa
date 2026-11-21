/* Pago de cuota de crédito (CR-INT-08)
   Puentes: /api/cobranza/clientes/{codCliente}/creditos, /api/cobranza/cr-int-08/pagos y
   /api/cuenta/consolidada/{codCliente}.
   1. «Revisar y pagar» solo abre la confirmación (monto, cuota, crédito, cuenta de origen) con un
      código SIMULADO (ver confirmacion.js); sin confirmar no se envía nada.
   2. Una llave (referenciaTransaccion) por intento: la misma en cada reintento, así una respuesta
      perdida no cobra dos veces. Cambia al registrarse el pago, al ser rechazado o al editar datos.
   3. El comprobante muestra solo lo que devuelve COBRANZA; si falta un dato, error claro.
*/

(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();

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
  let enCurso = false;

  // Motivos de rechazo del débito (COREDB).
  const MOTIVOS = {
    SALDO_INSUFICIENTE: "saldo insuficiente en la cuenta de origen",
    CUENTA_NO_OPERATIVA: "la cuenta de origen no está operativa",
    TOPE_DIARIO_SUPERADO: "se superó el tope diario del canal",
    CANAL_NO_ADMITIDO: "el canal no admite esta operación",
  };

  const fecha = iso => {
    const [a, m, d] = String(iso).slice(0, 10).split("-");
    return d && m && a ? `${d}/${m}/${a}` : String(iso);
  };

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
      `<option value="${c.codCredito}">${c.codCredito}</option>`
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
      `<option value="${c.numCuenta}">${c.numCuenta} · ${fmt.moneda(c.saldoDisponible, c.moneda)}</option>`
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
    const proxima = creditoActual.proximaCuota;
    detalle.textContent =
      `Saldo del crédito: ${fmt.moneda(creditoActual.saldo, creditoActual.moneda)} · ` +
      `Cuota: ${fmt.moneda(creditoActual.cuota, creditoActual.moneda)} · ` +
      `Cuotas pendientes: ${creditoActual.cuotasPendientes}` +
      (proxima ? ` · Próxima: cuota ${proxima.numero}, vence el ${fecha(proxima.vence)}.` : ".");
    pintarCreditos();
    idemActual = null;
    ocultarMensaje(msg);
  }

  // Devuelve true si leyó créditos y cuentas. silencioso: no muestra el error (lo dice quien llama).
  async function cargar(silencioso = false) {
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
      return true;
    } catch (e) {
      if (!silencioso) mostrarMensaje(msg, "error", e.mensaje || "No se pudieron recuperar los créditos.");
      return false;
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
    return { credito: creditoActual, cuenta, monto: (Math.round(valor * 100) / 100).toFixed(2) };
  }

  function resumen(v) {
    const proxima = v.credito.proximaCuota;
    const masDeUna = Number(v.monto) > v.credito.cuota + 1e-9;
    const aplicacion = proxima
      ? `Cuota ${proxima.numero} (vence el ${fecha(proxima.vence)})` + (masDeUna ? " y las siguientes" : "")
      : "La cuota más antigua con saldo";
    return {
      titulo: "Confirma el pago de tu cuota",
      filas: [
        ["Monto a pagar", fmt.moneda(Number(v.monto), v.credito.moneda)],
        ["Se aplica a", aplicacion],
        ["Crédito", v.credito.codCredito],
        ["Cuenta de origen", `${v.cuenta.numCuenta} · disponible ${fmt.moneda(v.cuenta.saldoDisponible, v.cuenta.moneda)}`],
      ],
      accion: `Pagar ${fmt.moneda(Number(v.monto), v.credito.moneda)}`,
    };
  }

  // Lo que el comprobante necesita del servidor. Devuelve los datos que faltan y los que no
  // coinciden con lo pedido (nunca se rellenan).
  function revisar(r, v) {
    const faltan = [];
    const presente = x => x !== undefined && x !== null && x !== "";
    if (!presente(r.idPago)) faltan.push("número de operación");
    if (!presente(r.fechaHora)) faltan.push("fecha");
    if (!presente(r.montoPago) || !Number.isFinite(Number(r.montoPago))) faltan.push("monto pagado");
    if (!presente(r.numCuenta)) faltan.push("cuenta de origen");
    if (!presente(r.saldoCredito) || !Number.isFinite(Number(r.saldoCredito))) faltan.push("saldo del crédito");
    if (!Number.isInteger(r.cuotasPendientes) || r.cuotasPendientes < 0) faltan.push("cuotas pendientes");
    if (!Array.isArray(r.cuotasPagadas) || !r.cuotasPagadas.length) faltan.push("cuota pagada");
    if (!presente(r.moneda)) faltan.push("moneda");
    const distintos = [];
    if (presente(r.montoPago) && Number(r.montoPago).toFixed(2) !== v.monto) {
      distintos.push(`el monto registrado (${fmt.moneda(Number(r.montoPago), v.credito.moneda)}) no es el que pediste ` +
        `(${fmt.moneda(Number(v.monto), v.credito.moneda)})`);
    }
    if (presente(r.numCuenta) && r.numCuenta !== v.cuenta.numCuenta) distintos.push(`la cuenta debitada es ${r.numCuenta}`);
    if (presente(r.codCredito) && r.codCredito !== v.credito.codCredito) distintos.push(`el crédito es ${r.codCredito}`);
    return { faltan, distintos };
  }

  function fila(lista, etiqueta, valor) {
    const div = document.createElement("div");
    const span = document.createElement("span");
    span.textContent = etiqueta;
    const b = document.createElement("b");
    b.textContent = valor;
    div.append(span, b);
    lista.appendChild(div);
    return b;
  }

  function pintarResultado(r) {
    resultado.hidden = false;
    resultado.innerHTML = "";
    const cuando = new Date(r.fechaHora);
    const cuandoTexto = Number.isNaN(cuando.getTime()) ? String(r.fechaHora) : fmt.fechaHora(cuando);
    subResultado.textContent = `Pago confirmado · ${cuandoTexto}`;

    const caja = document.createElement("div");
    caja.className = "resumen-operacion";
    const h3 = document.createElement("h3");
    h3.textContent = "Pago de cuota confirmado";
    caja.appendChild(h3);
    if (r.idempotente) {
      const aviso = document.createElement("span");
      aviso.className = "badge warn";
      aviso.textContent = "Este pago ya estaba registrado: no se cobró otra vez.";
      caja.appendChild(aviso);
    }
    const lista = document.createElement("div");
    lista.className = "detalle-lista";
    const pagadas = r.cuotasPagadas;
    fila(lista, "Crédito", r.codCredito);
    fila(lista, "Monto pagado", fmt.moneda(Number(r.montoPago), r.moneda));
    fila(lista, pagadas.length === 1 ? "Cuota pagada" : "Cuotas pagadas", pagadas.join(", "));
    fila(lista, "Cuenta de origen", r.numCuenta);
    fila(lista, "Saldo del crédito", fmt.moneda(Number(r.saldoCredito), r.moneda));
    fila(lista, "Cuotas pendientes", String(r.cuotasPendientes));
    const saldoCuenta = fila(lista, "Saldo disponible de la cuenta", "Consultando…");
    fila(lista, "Fecha", cuandoTexto);
    fila(lista, "N.º de operación", r.idPago);
    caja.appendChild(lista);

    const acciones = document.createElement("div");
    acciones.className = "constancia-acciones";
    const nuevo = document.createElement("button");
    nuevo.type = "button";
    nuevo.className = "btn btn-sec";
    nuevo.id = "btnNuevoPago";
    nuevo.textContent = "Nuevo pago";
    nuevo.addEventListener("click", () => {
      resultado.hidden = true;
      resultado.innerHTML = "";
      subResultado.textContent = "Aún no se ha procesado ningún pago.";
      idemActual = null;
      cargar();
    });
    acciones.appendChild(nuevo);
    caja.appendChild(acciones);
    resultado.appendChild(caja);
    return saldoCuenta;
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    if (enCurso) return;
    ocultarMensaje(msg);
    const v = validar();
    if (!v) return;
    enCurso = true;
    btn.disabled = true;
    let aviso = null;
    try {
      const decision = await ConfirmacionPago.pedir(resumen(v));
      if (!decision.confirmado) {
        aviso = ["info", decision.motivo === "CODIGO_AGOTADO"
          ? "Código incorrecto tres veces: el pago se canceló. No se cobró nada."
          : "Pago cancelado. No se cobró nada."];
        return;
      }
      if (!idemActual) idemActual = Bus.nuevoIdempotencyKey();
      cargando(btn, true, "Procesando");

      const r = await Bus.pagarCuota(v.credito.codCredito, {
        numCuentaOrigen: v.cuenta.numCuenta,
        montoPago: v.monto
      }, idemActual);

      if (r.estado === "RECHAZADO") {
        // Respuesta definitiva: COREDB repetiría el rechazo con la misma referencia, así que el
        // próximo intento (p. ej. tras depositar) lleva otra.
        idemActual = null;
        aviso = ["error", `El pago fue rechazado: ${MOTIVOS[r.motivo] || r.motivo || "sin motivo informado"}. No se cobró nada.`];
        return;
      }
      if (r.estado !== "CONFIRMADO") {
        aviso = ["warn", `El pago ${r.idPago || ""} quedó en estado ${r.estado || "desconocido"}. ` +
          "Revisa el crédito antes de volver a pagar."];
        return;
      }
      const { faltan, distintos } = revisar(r, v);
      if (faltan.length || distintos.length) {
        // La llave se conserva: repetir con los mismos datos devuelve el mismo pago, no cobra otro.
        const partes = [];
        if (faltan.length) partes.push(`el servidor no devolvió: ${faltan.join(", ")}`);
        partes.push(...distintos);
        aviso = ["error", `El pago ${r.idPago || "(sin número de operación)"} se registró, pero ${partes.join("; ")}. ` +
          "No lo repitas: revisa el crédito y la cuenta, o comunícate con el banco."];
        return;
      }

      idemActual = null;  // registrado: el próximo pago es otro intento
      const saldoCuenta = pintarResultado(r);
      const releido = await cargar(true);
      const cuenta = releido && cuentas.find(c => c.numCuenta === r.numCuenta);
      saldoCuenta.textContent = cuenta
        ? fmt.moneda(cuenta.saldoDisponible, cuenta.moneda)
        : "No se pudo consultar; revísalo en Cuentas";
      aviso = ["ok", `Pago de ${fmt.moneda(Number(r.montoPago), r.moneda)} registrado (operación ${r.idPago}).`];
    } catch (err) {
      if (err.codigo === "BUS_TIMEOUT" || err.codigo === "BUS_NO_DISPONIBLE" || err.status >= 500) {
        aviso = ["warn", "No llegó la respuesta del servidor: no sabemos si el pago se registró. " +
          "Vuelve a pulsar «Revisar y pagar» sin cambiar los datos: se usa la misma operación y " +
          "no se cobrará dos veces. Si cambias el monto o la cuenta, revisa antes tus movimientos."];
      } else {
        aviso = ["error", err.mensaje || "El pago no pudo procesarse."];
      }
      // La llave (referenciaTransaccion) se conserva: reintentar el mismo pago no cobra dos
      // veces. Cambia al editar el monto o la cuenta.
    } finally {
      enCurso = false;
      cargando(btn, false);
      btn.disabled = false;
      if (aviso) mostrarMensaje(msg, aviso[0], aviso[1]);
    }
  });

  cargar();
})();
