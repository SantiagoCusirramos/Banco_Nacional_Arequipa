/* =========================================================
   Confirmación de un pago del Home Banking
   Muestra lo que se va a cobrar y pide un código de 6 dígitos antes de enviar nada.
   El código es una SIMULACIÓN: se genera y se muestra en esta misma pantalla y el servidor
   no lo verifica (todavía no hay proveedor de segundo factor ni acceso propio del cliente).
   Aun así bloquea: si no coincide, el pago no se envía; al tercer error se cancela.
   ========================================================= */

const ConfirmacionPago = (() => {
  const INTENTOS = 3;

  function codigoAlAzar() {
    const n = crypto.getRandomValues(new Uint32Array(1))[0];
    return String(n % 1000000).padStart(6, "0");
  }

  function nodo(etiqueta, clase, texto) {
    const el = document.createElement(etiqueta);
    if (clase) el.className = clase;
    if (texto !== undefined) el.textContent = texto;
    return el;
  }

  // filas: [[etiqueta, valor], ...]. Resuelve { confirmado: true } solo con el código correcto;
  // { confirmado: false, motivo: "CANCELADO" | "CODIGO_AGOTADO" } en otro caso.
  function pedir({ titulo, filas, accion }) {
    return new Promise(resolver => {
      const codigo = codigoAlAzar();
      let fallidos = 0;
      let cerrado = false;

      const overlay = nodo("div", "token-overlay");
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.setAttribute("aria-labelledby", "confirmacionTitulo");

      const caja = nodo("form", "token-caja");
      caja.noValidate = true;
      const cab = nodo("div", "token-cab");
      const h3 = nodo("h3", "", titulo);
      h3.id = "confirmacionTitulo";
      cab.append(h3, nodo("p", "", "Revisa los datos. No se cobra nada hasta que confirmes."));

      const cuerpo = nodo("div", "token-cuerpo");
      const resumen = nodo("dl", "confirmacion-resumen");
      resumen.id = "confirmacionResumen";
      filas.forEach(([etiqueta, valor]) => resumen.append(nodo("dt", "", etiqueta), nodo("dd", "", valor)));

      const simulado = nodo("div", "token-coordenada");
      simulado.append(
        nodo("span", "badge warn", "SIMULACIÓN"),
        nodo("p", "confirmacion-aviso",
          "Este código no es un segundo factor real: se muestra aquí mismo y el servidor no lo verifica. " +
          "Escríbelo para confirmar el pago."),
      );
      const muestra = nodo("b", "", codigo);
      muestra.id = "codigoSimulado";
      simulado.append(muestra);

      const campo = nodo("div", "campo");
      const label = nodo("label", "", "Código de confirmación (6 dígitos)");
      label.htmlFor = "codigoIngresado";
      const input = nodo("input");
      Object.assign(input, { id: "codigoIngresado", inputMode: "numeric", maxLength: 6, autocomplete: "off" });
      campo.append(label, input);

      const error = nodo("div", "msg token-error");
      error.id = "confirmacionError";
      error.setAttribute("role", "alert");

      const acciones = nodo("div", "token-acciones");
      const cancelar = nodo("button", "btn btn-sec", "Cancelar");
      cancelar.type = "button";
      cancelar.id = "btnCancelarPago";
      const confirmar = nodo("button", "btn", accion);
      confirmar.type = "submit";
      confirmar.id = "btnConfirmarPago";
      acciones.append(cancelar, confirmar);

      cuerpo.append(resumen, simulado, campo, error, acciones);
      caja.append(cab, cuerpo);
      overlay.appendChild(caja);
      document.body.appendChild(overlay);
      input.focus();

      function cerrar(resultado) {
        if (cerrado) return;
        cerrado = true;
        confirmar.disabled = true;
        cancelar.disabled = true;
        overlay.remove();
        resolver(resultado);
      }

      function fallar(texto) {
        error.className = "msg visible error token-error";
        error.textContent = texto;
        input.select();
      }

      caja.addEventListener("submit", e => {
        e.preventDefault();
        if (cerrado) return;
        const escrito = input.value.trim();
        if (!/^\d{6}$/.test(escrito)) { fallar("Escribe el código de 6 dígitos."); return; }
        if (escrito !== codigo) {
          fallidos += 1;
          if (fallidos >= INTENTOS) { cerrar({ confirmado: false, motivo: "CODIGO_AGOTADO" }); return; }
          const quedan = INTENTOS - fallidos;
          fallar(`Código incorrecto. Te ${quedan === 1 ? "queda 1 intento" : `quedan ${quedan} intentos`}.`);
          return;
        }
        cerrar({ confirmado: true });
      });
      cancelar.addEventListener("click", () => cerrar({ confirmado: false, motivo: "CANCELADO" }));
      overlay.addEventListener("keydown", e => {
        if (e.key === "Escape") cerrar({ confirmado: false, motivo: "CANCELADO" });
      });
    });
  }

  return { pedir };
})();
