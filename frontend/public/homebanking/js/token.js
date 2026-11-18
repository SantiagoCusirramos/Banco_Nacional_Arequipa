/* =========================================================
   Token Matriz (INT-03) - NO DISPONIBLE EN ESTA VERSIÓN
   Esta versión del Home Banking no incluye endpoint para Token Matriz.
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
    p.textContent = "Token Matriz: NO DISPONIBLE EN ESTA VERSIÓN. No hay endpoint /api/tarjeta/token/...";
    cab.append(h3, p);

    const cuerpo = document.createElement("div");
    cuerpo.className = "token-cuerpo";

    const coord = document.createElement("div");
    coord.className = "token-coordenada";
    coord.innerHTML = `<b>Token Matriz no disponible</b><br>
      <span class="tono-suave">Esta versión del Home Banking no incluye el endpoint para Token Matriz (INT-03).</span>`;

    cuerpo.append(coord);

    const msg = document.createElement("div");
    msg.className = "msg token-error";

    const acciones = document.createElement("div");
    acciones.className = "token-acciones";
    const btnCerrar = document.createElement("button");
    btnCerrar.type = "button";
    btnCerrar.className = "btn";
    btnCerrar.textContent = "Cerrar";
    acciones.append(btnCerrar);

    cuerpo.append(msg, acciones);
    caja.append(cab, cuerpo);
    overlay.appendChild(caja);
    document.body.appendChild(overlay);

    const cerrar = () => overlay.remove();

    btnCerrar.addEventListener("click", () => {
      cerrar();
      rechazar(Object.assign(new Error("cancelado"), {
        codigo: "TOKEN_CANCELADO",
        mensaje: "Token Matriz no disponible en esta versión."
      }));
    });

    overlay.addEventListener("keydown", e => { if (e.key === "Escape") btnCerrar.click(); });
  }

  async function pedirYValidar(opciones = {}) {
    // Token Matriz NO DISPONIBLE EN ESTA VERSIÓN
    throw Object.assign(new Error("NO_DISPONIBLE"), {
      codigo: "NO_DISPONIBLE",
      mensaje: "Token Matriz (INT-03): No disponible en esta versión. Requiere endpoint /api/tarjeta/token/...",
      status: 501
    });
  }

  return { pedirYValidar };
})();