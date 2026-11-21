/* Transferencias entre cuentas BNA (propias o de terceros)
   Puentes: /api/cuenta/consolidada/{codCliente}, /api/cuenta/{num}/destino y /api/cuenta/transferencia.
   1. «Revisar y transferir» consulta la cuenta de destino (titular enmascarado, moneda, estado) y
      abre la confirmación (monto, origen, destino, titular) con un código SIMULADO (ver
      confirmacion.js); sin confirmar no se envía nada.
   2. Una llave por intento: la misma en cada reintento, así una respuesta perdida no transfiere dos
      veces. Cambia al registrarse la transferencia, al ser rechazada o al editar datos.
   3. El comprobante muestra solo lo que devuelve CUENTAS (leído de COREDB); si falta un dato o no
      coincide con lo pedido, error con el número de operación y sin comprobante.
   El tope diario lo aplica COREDB al canal Home Banking; esta pantalla no lo repite.
*/

(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();

  const form = document.getElementById("formTrans");
  const msg = document.getElementById("msgTrans");
  const tabs = document.getElementById("tabsTipo");
  const selOrigen = document.getElementById("selOrigen");
  const selDestino = document.getElementById("selDestinoPropia");
  const pistaPropia = document.getElementById("pistaPropia");
  const ctaTercero = document.getElementById("ctaTercero");
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
  let enCurso = false;

  // Rechazos de CUENTAS/COREDB que el cliente puede entender. Ninguno movió dinero.
  const MOTIVOS = {
    "ERR-CTA-FONDOS-INSUFICIENTES": "saldo insuficiente en la cuenta de origen",
    "ERR-CTA-TOPE-EXCEDIDO": "se superó el tope diario del Home Banking para esta cuenta",
    "ERR-CTA-BLOQUEADA": "una de las cuentas no está operativa",
    "ERR-CTA-CANAL-INVALIDO": "el Home Banking no opera en la moneda de esta cuenta",
    "ERR-CTA-NO-ENCONTRADA": "la cuenta de destino no existe",
    "ERR-CTA-CUENTAS-IGUALES": "la cuenta de origen y la de destino son la misma",
    "ERR-COR-BNA-MONEDA": "las cuentas son de monedas distintas",
  };

  const cuentaActual = () => cuentas.find(c => c.numCuenta === selOrigen.value);
  const nuevoIntento = () => { idemActual = null; };

  function pintarDisponible() {
    const c = cuentaActual();
    txtDisponible.value = c ? fmt.moneda(c.saldoDisponible, c.moneda) : "—";
    txtMoneda.value = c ? c.moneda : "—";
    if (c) monto.max = c.saldoDisponible;
  }

  function llenarDestinosPropios() {
    const c = cuentaActual();
    if (!c) {
      selDestino.innerHTML = "";
      return;
    }
    const destinos = cuentas.filter(d => d.numCuenta !== c.numCuenta && d.moneda === c.moneda);
    selDestino.innerHTML = destinos.length
      ? destinos.map(d => `<option value="${d.numCuenta}">${d.numCuenta} · ${fmt.moneda(d.saldoDisponible, d.moneda)}</option>`).join("")
      : `<option value="">Sin otras cuentas propias en ${c.moneda}</option>`;
    pistaPropia.textContent = destinos.length
      ? "Solo se muestran cuentas activas de su titularidad con la misma moneda."
      : "Para enviar dinero a otra persona, use «Terceros BNA».";
  }

  // Devuelve true si leyó las cuentas. silencioso: no muestra el error (lo dice quien llama).
  async function cargarCuentas(conservarOrigen = true, silencioso = false) {
    try {
      const pos = await Bus.consultarPosicion(sesion.codCliente, null);
      cuentas = pos.cuentas || [];
      const anterior = conservarOrigen ? selOrigen.value : null;
      selOrigen.innerHTML = cuentas.map(c =>
        `<option value="${c.numCuenta}">${c.numCuenta} · ${c.moneda}</option>`
      ).join("");
      const params = new URLSearchParams(window.location.search);
      const solicitada = anterior || params.get("origen");
      if (solicitada && cuentas.some(c => c.numCuenta === solicitada)) {
        selOrigen.value = solicitada;
      }
      llenarDestinosPropios();
      pintarDisponible();
      if (!cuentas.length && !silencioso) mostrarMensaje(msg, "warn", "No se encontraron cuentas activas.");
      return true;
    } catch (e) {
      if (!silencioso) mostrarMensaje(msg, "error", e.mensaje || "No se pudieron recuperar sus cuentas.");
      return false;
    }
  }

  function cambiarTipo(nuevo) {
    tipo = nuevo;
    [...tabs.querySelectorAll(".tab")].forEach(b => b.classList.toggle("activo", b.dataset.tipo === tipo));
    document.getElementById("bloquePropia").hidden = tipo !== "PROPIA";
    document.getElementById("bloqueTercero").hidden = tipo !== "TERCERO";
    nuevoIntento();
    ocultarMensaje(msg);
  }

  tabs.addEventListener("click", e => {
    const b = e.target.closest(".tab");
    if (b && !enCurso) cambiarTipo(b.dataset.tipo);
  });

  selOrigen.addEventListener("change", () => {
    llenarDestinosPropios();
    pintarDisponible();
    nuevoIntento();
  });
  [monto, ctaTercero, glosa].forEach(el => el.addEventListener("input", nuevoIntento));
  selDestino.addEventListener("change", nuevoIntento);

  function validar() {
    const c = cuentaActual();
    if (!c) { mostrarMensaje(msg, "error", "Seleccione una cuenta de origen."); return null; }
    const valor = Number(monto.value);
    if (!Number.isFinite(valor) || valor <= 0) { mostrarMensaje(msg, "error", "Ingrese un monto mayor a cero."); return null; }
    if (valor > c.saldoDisponible + 1e-9) {
      mostrarMensaje(msg, "error", "El monto supera el saldo disponible de la cuenta de origen.");
      return null;
    }
    const destino = tipo === "PROPIA" ? selDestino.value : ctaTercero.value.trim();
    if (!destino) {
      mostrarMensaje(msg, "error", tipo === "PROPIA" ? "Seleccione una cuenta de destino propia." : "Ingrese la cuenta de destino BNA.");
      return null;
    }
    if (destino === c.numCuenta) { mostrarMensaje(msg, "error", "La cuenta de destino no puede ser la de origen."); return null; }
    return { cuenta: c, destino, monto: (Math.round(valor * 100) / 100).toFixed(2), glosa: glosa.value.trim() };
  }

  // La cuenta de destino según el banco. Devuelve null (y deja el mensaje) si no se puede usar.
  async function comprobarDestino(v) {
    let d;
    try {
      d = await Bus.verDestino(v.destino);
    } catch (err) {
      mostrarMensaje(msg, "error", err.codigo === "ERR-CTA-NO-ENCONTRADA"
        ? `La cuenta de destino ${v.destino} no existe. Revise el número.`
        : `No se pudo comprobar la cuenta de destino: ${err.mensaje || "intente de nuevo"}. No se movió dinero.`);
      return null;
    }
    if (!d.titular || !d.moneda || !d.estado) {
      mostrarMensaje(msg, "error", "El banco no devolvió el titular de la cuenta de destino. No se movió dinero.");
      return null;
    }
    if (d.estado !== "ACTIVA") {
      mostrarMensaje(msg, "error", `La cuenta de destino ${v.destino} no está activa. No se movió dinero.`);
      return null;
    }
    if (d.moneda !== v.cuenta.moneda) {
      mostrarMensaje(msg, "error", `La cuenta de destino es en ${d.moneda} y la de origen en ${v.cuenta.moneda}: ` +
        "solo se transfiere entre cuentas de la misma moneda.");
      return null;
    }
    return d;
  }

  function resumen(v, d) {
    const importe = fmt.moneda(Number(v.monto), v.cuenta.moneda);
    const filas = [
      ["Monto", importe],
      ["Tipo", tipo === "PROPIA" ? "Entre mis cuentas" : "A otra cuenta BNA"],
      ["Cuenta de origen", `${v.cuenta.numCuenta} · disponible ${fmt.moneda(v.cuenta.saldoDisponible, v.cuenta.moneda)}`],
      ["Cuenta de destino", v.destino],
      ["Titular de destino", d.titular],
    ];
    if (v.glosa) filas.push(["Glosa", v.glosa]);
    return {
      titulo: "Confirma tu transferencia",
      nota: "Revisa los datos, sobre todo el titular de destino. No se mueve dinero hasta que confirmes.",
      objeto: "la transferencia",
      filas,
      accion: `Transferir ${importe}`,
    };
  }

  // Lo que el comprobante necesita del servidor. Devuelve los datos que faltan y los que no
  // coinciden con lo pedido (nunca se rellenan).
  function revisar(r, v) {
    const presente = x => x !== undefined && x !== null && x !== "";
    const numero = x => presente(x) && Number.isFinite(Number(x));
    const faltan = [];
    if (!presente(r.idTransferencia)) faltan.push("número de operación");
    if (!presente(r.fechaHora)) faltan.push("fecha");
    if (!numero(r.monto)) faltan.push("monto transferido");
    if (!presente(r.moneda)) faltan.push("moneda");
    if (!presente(r.cuentaOrigen)) faltan.push("cuenta de origen");
    if (!presente(r.cuentaDestino)) faltan.push("cuenta de destino");
    if (!presente(r.titularDestino)) faltan.push("titular de destino");
    if (!numero(r.saldoDisponibleOrigen)) faltan.push("saldo de la cuenta de origen");
    if (!presente(r.estado)) faltan.push("estado");
    const distintos = [];
    if (numero(r.monto) && Number(r.monto).toFixed(2) !== v.monto) {
      distintos.push(`el monto registrado (${fmt.moneda(Number(r.monto), v.cuenta.moneda)}) no es el que pediste ` +
        `(${fmt.moneda(Number(v.monto), v.cuenta.moneda)})`);
    }
    if (presente(r.cuentaOrigen) && r.cuentaOrigen !== v.cuenta.numCuenta) distintos.push(`la cuenta debitada es ${r.cuentaOrigen}`);
    if (presente(r.cuentaDestino) && r.cuentaDestino !== v.destino) distintos.push(`la cuenta abonada es ${r.cuentaDestino}`);
    if (presente(r.moneda) && r.moneda !== v.cuenta.moneda) distintos.push(`la moneda es ${r.moneda}`);
    if (presente(r.estado) && r.estado !== "APROBADO") distintos.push(`la operación figura como ${r.estado}`);
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

  // Devuelve el campo del saldo de la cuenta de destino si es propia (se completa al releer).
  function pintarResultado(r, propia) {
    resultado.hidden = false;
    resultado.innerHTML = "";
    const cuando = new Date(r.fechaHora);
    const cuandoTexto = Number.isNaN(cuando.getTime()) ? String(r.fechaHora) : fmt.fechaHora(cuando);
    subResultado.textContent = `Transferencia registrada · ${cuandoTexto}`;

    const caja = document.createElement("div");
    caja.className = "resumen-operacion";
    const h3 = document.createElement("h3");
    h3.textContent = "Transferencia registrada";
    caja.appendChild(h3);
    if (r.idempotente) {
      const aviso = document.createElement("span");
      aviso.className = "badge warn";
      aviso.textContent = "Esta transferencia ya estaba registrada: no se transfirió otra vez.";
      caja.appendChild(aviso);
    }
    const lista = document.createElement("div");
    lista.className = "detalle-lista";
    fila(lista, "Monto", fmt.moneda(Number(r.monto), r.moneda));
    fila(lista, "Cuenta de origen", r.cuentaOrigen);
    fila(lista, "Cuenta de destino", r.cuentaDestino);
    fila(lista, "Titular de destino", r.titularDestino);
    fila(lista, "Saldo disponible de la cuenta de origen", fmt.moneda(Number(r.saldoDisponibleOrigen), r.moneda));
    const saldoDestino = propia ? fila(lista, "Saldo disponible de la cuenta de destino", "Consultando…") : null;
    fila(lista, "Fecha", cuandoTexto);
    fila(lista, "N.º de operación", r.idTransferencia);
    caja.appendChild(lista);

    const acciones = document.createElement("div");
    acciones.className = "constancia-acciones";
    const nueva = document.createElement("button");
    nueva.type = "button";
    nueva.className = "btn btn-sec";
    nueva.id = "btnNuevaTrans";
    nueva.textContent = "Nueva transferencia";
    nueva.addEventListener("click", () => {
      resultado.hidden = true;
      resultado.innerHTML = "";
      subResultado.textContent = "Aún no se ha procesado ninguna transferencia.";
      form.reset();
      nuevoIntento();
      cargarCuentas(true);
    });
    acciones.appendChild(nueva);
    caja.appendChild(acciones);
    resultado.appendChild(caja);
    return saldoDestino;
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
      const destino = await comprobarDestino(v);
      if (!destino) return;
      const decision = await ConfirmacionPago.pedir(resumen(v, destino));
      if (!decision.confirmado) {
        aviso = ["info", decision.motivo === "CODIGO_AGOTADO"
          ? "Código incorrecto tres veces: la transferencia se canceló. No se movió dinero."
          : "Transferencia cancelada. No se movió dinero."];
        return;
      }
      if (!idemActual) idemActual = Bus.nuevoIdempotencyKey();
      cargando(btn, true, "Procesando");

      const r = await Bus.transferencia({
        cuentaOrigen: v.cuenta.numCuenta, cuentaDestino: v.destino, monto: v.monto, glosa: v.glosa
      }, idemActual);

      const { faltan, distintos } = revisar(r, v);
      if (faltan.length || distintos.length) {
        // La llave se conserva: repetir con los mismos datos devuelve la misma transferencia.
        const partes = [];
        if (faltan.length) partes.push(`el servidor no devolvió: ${faltan.join(", ")}`);
        partes.push(...distintos);
        aviso = ["error", `La transferencia ${r.idTransferencia || "(sin número de operación)"} se registró, pero ` +
          `${partes.join("; ")}. No la repitas: revisa tus movimientos o comunícate con el banco.`];
        return;
      }

      nuevoIntento();  // registrada: la próxima transferencia es otro intento
      const saldoDestino = pintarResultado(r, tipo === "PROPIA");
      const releido = await cargarCuentas(true, true);
      if (saldoDestino) {
        const cuenta = releido && cuentas.find(c => c.numCuenta === r.cuentaDestino);
        saldoDestino.textContent = cuenta
          ? fmt.moneda(cuenta.saldoDisponible, cuenta.moneda)
          : "No se pudo consultar; revísalo en Cuentas";
      }
      aviso = ["ok", `Transferencia de ${fmt.moneda(Number(r.monto), r.moneda)} registrada (operación ${r.idTransferencia}).`];
    } catch (err) {
      if (err.codigo === "BUS_TIMEOUT" || err.codigo === "BUS_NO_DISPONIBLE" || !err.status || err.status >= 500) {
        // No se sabe si llegó: la llave se conserva para que el reintento no transfiera dos veces.
        aviso = ["warn", "No llegó la respuesta del servidor: no sabemos si la transferencia se registró. " +
          "Vuelve a pulsar «Revisar y transferir» sin cambiar los datos: se usa la misma operación y " +
          "no se transferirá dos veces. Si cambias el monto o la cuenta, revisa antes tus movimientos."];
      } else if (err.codigo === "ERR-CTA-IDEMPOTENCIA") {
        nuevoIntento();
        aviso = ["error", "Esta operación ya figura registrada con otros datos. Revisa tus movimientos antes de repetirla."];
      } else {
        // Respuesta definitiva del banco: el próximo intento (p. ej. tras depositar) lleva otra llave.
        nuevoIntento();
        aviso = ["error", `La transferencia fue rechazada: ${MOTIVOS[err.codigo] || err.mensaje || "sin motivo informado"}. ` +
          "No se movió dinero."];
      }
    } finally {
      enCurso = false;
      cargando(btn, false);
      btn.disabled = false;
      if (aviso) mostrarMensaje(msg, aviso[0], aviso[1]);
    }
  });

  cargarCuentas(false);
})();
