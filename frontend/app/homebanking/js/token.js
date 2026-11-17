/* =========================================================
   Token Matriz (INT-03)
   Solicita una coordenada, muestra la matriz de demostración
   y valida el valor contra el Bus de Servicios.
   ========================================================= */

const TokenMatriz = (() => {

  function crearModal(desafio, opciones, resolver, rechazar) {
    const overlay = document.createElement("div");
    overlay.className = "token-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");

    const caja = document.createElement("div");
    caja.className = "token-caja";

    const cab = document.createElement("div");
    cab.className = "token-cab";
    const h3 = document.createElement("h3");
    h3.textContent = opciones.titulo || "Validación Token Matriz";
    const p = document.createElement("p");
    p.textContent = "Segundo factor requerido para operaciones no presenciales (RF-HB-008 / INT-03).";
    cab.append(h3, p);

    const cuerpo = document.createElement("div");
    cuerpo.className = "token-cuerpo";

    const coord = document.createElement("div");
    coord.className = "token-coordenada";
    coord.innerHTML = `Coordenada solicitada: <b>${desafio.coordenada}</b><br>
      <span class="tono-suave">Ingrese el valor de 6 dígitos de esa coordenada. En producción el cliente lo obtiene de su Token Matriz físico; aquí se muestra la matriz de demostración.</span>`;

    const grid = document.createElement("div");
    grid.className = "token-grid";
    const letras = ["A", "B", "C", "D"];
    const columnas = ["1", "2", "3", "4"];

    const esq = document.createElement("div");
    esq.className = "esq";
    esq.textContent = "";
    grid.appendChild(esq);
    columnas.forEach(c => {
      const cabecera = document.createElement("div");
      cabecera.className = "cab";
      cabecera.textContent = c;
      grid.appendChild(cabecera);
    });
    letras.forEach(letra => {
      const etiqueta = document.createElement("div");
      etiqueta.className = "cab";
      etiqueta.textContent = letra;
      grid.appendChild(etiqueta);
      columnas.forEach(col => {
        const clave = letra + col;
        const celda = document.createElement("div");
        celda.className = "token-celda" + (clave === desafio.coordenada ? " pedida" : "");
        celda.textContent = desafio.matriz[clave] || "------";
        grid.appendChild(celda);
      });
    });

    const campo = document.createElement("div");
    campo.className = "campo";
    const label = document.createElement("label");
    label.setAttribute("for", "tokenValor");
    label.textContent = `Valor de la coordenada ${desafio.coordenada}`;
    const input = document.createElement("input");
    input.type = "text";
    input.id = "tokenValor";
    input.className = "mono";
    input.inputMode = "numeric";
    input.maxLength = 6;
    input.placeholder = "6 dígitos";
    input.autocomplete = "one-time-code";
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "").slice(0, 6);
    });
    campo.append(label, input);

    const msg = document.createElement("div");
    msg.className = "msg token-error";

    const acciones = document.createElement("div");
    acciones.className = "token-acciones";
    const btnCancelar = document.createElement("button");
    btnCancelar.type = "button";
    btnCancelar.className = "btn btn-sec";
    btnCancelar.textContent = "Cancelar";
    const btnValidar = document.createElement("button");
    btnValidar.type = "button";
    btnValidar.className = "btn";
    btnValidar.textContent = "Validar Token";
    acciones.append(btnCancelar, btnValidar);

    cuerpo.append(coord, grid, campo, msg, acciones);
    caja.append(cab, cuerpo);
    overlay.appendChild(caja);
    document.body.appendChild(overlay);
    setTimeout(() => input.focus(), 50);

    const cerrar = () => overlay.remove();

    btnCancelar.addEventListener("click", () => {
      cerrar();
      rechazar(Object.assign(new Error("cancelado"), {
        codigo: "TOKEN_CANCELADO",
        mensaje: "Validación del Token Matriz cancelada por el usuario."
      }));
    });

    async function validar() {
      ocultarMensaje(msg);
      if (!/^\d{6}$/.test(input.value.trim())) {
        mostrarMensaje(msg, "error", "Ingrese exactamente 6 dígitos numéricos.");
        input.focus();
        return;
      }
      cargando(btnValidar, true, "Validando");
      try {
        const r = await Bus.invocar("/bus/v1/tarjetas/token/validar", {
          challengeId: desafio.challengeId,
          valorIngresado: input.value.trim()
        }, "INT-03");
        cerrar();
        resolver(r);
      } catch (e) {
        if (e.codigo === "TOKEN_BLOQUEADO" || e.codigo === "DESAFIO_EXPIRADO" || e.codigo === "DESAFIO_YA_UTILIZADO") {
          mostrarMensaje(msg, "error", e.mensaje || "El desafío ya no es válido. Cierre y solicite uno nuevo.");
        } else {
          mostrarMensaje(msg, "error", e.mensaje || "No se pudo validar el Token Matriz.");
        }
        input.value = "";
        input.focus();
      } finally {
        cargando(btnValidar, false);
      }
    }

    btnValidar.addEventListener("click", validar);
    input.addEventListener("keydown", e => { if (e.key === "Enter") validar(); });
    overlay.addEventListener("keydown", e => { if (e.key === "Escape") btnCancelar.click(); });
  }

  async function pedirYValidar(opciones = {}) {
    if (!Bus.esApi) {
      throw Object.assign(new Error("modo local"), {
        codigo: "MODO_LOCAL_LIMITADO",
        mensaje: "El Token Matriz requiere el Bus de Servicios local. Ejecute ./iniciar.sh y abra http://127.0.0.1:8080/."
      });
    }
    const desafio = await Bus.invocar("/bus/v1/tarjetas/token/desafio", {}, "INT-03");
    return new Promise((resolver, rechazar) => {
      crearModal(desafio, opciones, resolver, rechazar);
    });
  }

  return { pedirYValidar };
})();
