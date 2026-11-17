/* RF-HB-001 – Autenticación del cliente en Home Banking */

(function () {
  crearConsola();

  const form = document.getElementById("formLogin");
  const btn = document.getElementById("btnIngresar");
  const msg = document.getElementById("msgLogin");
  const cod = document.getElementById("codCliente");
  const clave = document.getElementById("claveWeb");

  (async function verificarCanal() {
    const etiqueta = document.getElementById("estadoCanal");
    if (!Bus.esApi) {
      if (etiqueta) etiqueta.textContent = "MOCK local · sin servidor";
      mostrarMensaje(msg, "warn", "Modo local limitado. Ejecute ./iniciar.sh para habilitar transferencias, Token Matriz, créditos y auditoría.");
      return;
    }
    try {
      const r = await fetch("/bus/v1/salud");
      const j = await r.json();
      if (etiqueta && j.ok) etiqueta.textContent = `Bus local REST/JSON · ${j.data.estado}`;
    } catch (e) {
      if (etiqueta) etiqueta.textContent = "Bus local no disponible";
      mostrarMensaje(msg, "warn", "El Bus de Servicios local no responde. Verifique que ./iniciar.sh esté en ejecución.");
    }
  })();

  if (Sesion.leer()) {
    window.location.href = "cuentas.html";
    return;
  }

  clave.addEventListener("input", () => {
    clave.value = clave.value.replace(/\D/g, "").slice(0, 6);
  });

  form.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarMensaje(msg);

    const codCliente = cod.value.trim().toUpperCase();
    const claveWeb = clave.value.trim();

    if (!codCliente) {
      mostrarMensaje(msg, "error", "Ingrese su código de cliente.");
      return;
    }
    if (!/^\d{6}$/.test(claveWeb)) {
      mostrarMensaje(msg, "error", "La clave debe contener exactamente 6 dígitos numéricos.");
      return;
    }

    cargando(btn, true, "Validando");
    try {
      const r = await Bus.invocar(
        "/bus/v1/seguridad/autenticar",
        { codCliente, claveWeb, canal: DATOS_BNA.parametros.canal, ipOrigen: "190.12.44.107" },
        "RF-HB-001"
      );

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
      const texto = err.mensaje || "No fue posible iniciar sesión. Intente nuevamente.";
      mostrarMensaje(msg, err.codigo === "BUS_TIMEOUT" ? "warn" : "error", texto);
      clave.value = "";
      clave.focus();
    } finally {
      cargando(btn, false);
    }
  });
})();
