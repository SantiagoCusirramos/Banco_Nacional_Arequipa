/* RF-HB-001 – Autenticación del cliente en Home Banking */

(function () {

  const form = document.getElementById("formLogin");
  const btn = document.getElementById("btnIngresar");
  const msg = document.getElementById("msgLogin");
  const cod = document.getElementById("codCliente");
  const clave = document.getElementById("claveWeb");
  const usuario = document.getElementById("usuario");

  (async function verificarCanal() {
    const etiqueta = document.getElementById("estadoCanal");
    try {
      const r = await fetch("/api/core/coredb/salud");
      if (etiqueta && r.ok) etiqueta.textContent = "Servicio disponible";
    } catch (e) {
      if (etiqueta) etiqueta.textContent = "Servicio no disponible";
      mostrarMensaje(msg, "warn", "No se pudo comprobar la conexión. Intenta de nuevo más tarde.");
    }
  })();

  if (Sesion.leer()) {
    window.location.href = "cuentas.html";
    return;
  }


  form.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarMensaje(msg);

    const codCliente = cod.value.trim().toUpperCase();
    const claveWeb = clave.value.trim();

    if (!codCliente) {
      mostrarMensaje(msg, "error", "Ingrese su código de cliente.");
      return;
    }
    if (!usuario.value.trim() || !claveWeb) {
      mostrarMensaje(msg, "error", "Ingrese el usuario y la clave del banco.");
      return;
    }

    cargando(btn, true, "Validando");
    try {
      // Usa Bus.autenticar (POST /api/core/coredb/auth/login)
      const r = await Bus.autenticar(usuario.value.trim(), claveWeb, codCliente);

      Sesion.guardar({
        codCliente: r.datosSesion.cliente.codCliente,
        nombres: r.datosSesion.cliente.nombres,
        dni: r.datosSesion.cliente.dni,
        tokenSesion: r.datosSesion.tokenSesion,
        inicio: Date.now()
      });

      mostrarMensaje(msg, "ok", `${r.mensajeAcceso}. Redirigiendo a sus cuentas…`);
      setTimeout(() => { window.location.href = "cuentas.html"; }, 700);
    } catch (err) {
      const texto = mensajeError(err);
      mostrarMensaje(msg, err.codigo === "BUS_TIMEOUT" ? "warn" : "error", texto);
      clave.value = "";
      clave.focus();
    } finally {
      cargando(btn, false);
    }
  });
})();