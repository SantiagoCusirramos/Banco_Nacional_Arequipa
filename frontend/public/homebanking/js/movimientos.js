/* RF-HB-003 – Consultar movimientos históricos (INT-08) */

(function () {
  const sesion = Sesion.exigir();
  if (!sesion) return;

  pintarCabecera();

  const params = new URLSearchParams(window.location.search);
  const numCuenta = (params.get("cuenta") || "").trim();

  const form = document.getElementById("formMov");
  const inp = document.getElementById("filtroMes");
  const btn = document.getElementById("btnConsultar");
  const msg = document.getElementById("msgMov");
  const titulo = document.getElementById("ctaTitulo");
  const sub = document.getElementById("ctaSub");

  if (!numCuenta) {
    titulo.textContent = "Cuenta no especificada";
    sub.textContent = "Selecciona una cuenta desde la consulta de posición consolidada.";
    mostrarMensaje(msg, "error", "No se recibió el número de cuenta. Vuelve a tus cuentas y vuelve a intentarlo.");
    form.style.display = "none";
    return;
  }

  titulo.textContent = `Movimientos · ${numCuenta}`;

  async function consultar() {
    ocultarMensaje(msg);
    document.getElementById("resumenMov").hidden = true;
    document.getElementById("envMov").hidden = true;

    cargando(btn, true, "Consultando");
    try {
      const r = await Bus.consultarMovimientos(sesion.codCliente, numCuenta, inp.value || null);
      pintar(r);
      if (r.totalMovimientos === 0) {
        mostrarMensaje(msg, "warn", `No existen movimientos para el periodo ${inp.value || "seleccionado"}.`);
      }
    } catch (err) {
      if (err.codigo === "BUS_TIMEOUT") {
        mostrarMensaje(msg, "warn", "El servicio no respondió. La consulta quedó sin confirmar. Intenta de nuevo.");
      } else if (err.status === 403) {
        mostrarMensaje(msg, "error", "La cuenta consultada no pertenece a su titularidad.");
      } else {
        mostrarMensaje(msg, "error", mensajeError(err));
      }
    } finally {
      cargando(btn, false);
    }
  }

  function pintar(r) {
    sub.textContent = `${r.tipoCuenta} · moneda ${r.moneda} · periodo ${r.filtroMes === "SIN_FILTRO" ? "historial completo" : r.filtroMes}`;

    let abonos = 0, cargos = 0;
    r.movimientos.forEach(m => { m.monto >= 0 ? abonos += m.monto : cargos += Math.abs(m.monto); });

    document.getElementById("resumenMov").hidden = false;
    document.getElementById("mvTotal").textContent = r.totalMovimientos;
    document.getElementById("mvAbonos").textContent = fmt.moneda(abonos, r.moneda);
    document.getElementById("mvCargos").textContent = fmt.moneda(cargos, r.moneda);
    document.getElementById("mvSaldo").textContent = fmt.moneda(r.saldoDisponible, r.moneda);
    document.getElementById("mvSaldoDet").textContent = "contable " + fmt.moneda(r.saldoContable, r.moneda);

    const tb = document.getElementById("tablaMov");
    tb.innerHTML = "";
    if (!r.movimientos.length) {
      tb.innerHTML = `<tr><td colspan="5" class="vacio">Sin movimientos para el periodo consultado.</td></tr>`;
    } else {
      r.movimientos.forEach(m => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="num">${m.fecha}</td>
          <td><span class="badge ${m.monto >= 0 ? "ok" : "info"}">${m.operacion}</span></td>
          <td>${m.glosa}</td>
          <td class="der num ${m.monto >= 0 ? "pos" : ""}" style="${m.monto < 0 ? "color:var(--error)" : ""}">${m.monto >= 0 ? "+" : "−"} ${fmt.moneda(Math.abs(m.monto), r.moneda)}</td>
          <td class="der num">${fmt.moneda(m.saldo, r.moneda)}</td>`;
        tb.appendChild(tr);
      });
    }
    document.getElementById("envMov").hidden = false;
  }

  form.addEventListener("submit", e => { e.preventDefault(); consultar(); });
  consultar();
})();