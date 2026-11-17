/* =========================================================
   BUS DE SERVICIOS DEL PROTOTIPO
   - En modo API (servidor local de pruebas) invoca los servicios simulados.
   - En modo MOCK (archivo abierto directamente) conserva las
     consultas de Fase I/II para demostración sin servidor.
   - Genera UUID, controla timeout, idempotencia y auditoría.
   ========================================================= */

const Bus = (() => {

  let nSecuencia = 0;
  let simulacionTimeout = false;
  const consola = [];

  const modo = (typeof window !== "undefined" &&
    (window.location.protocol === "http:" || window.location.protocol === "https:")) ? "API" : "MOCK";

  const uuid = () =>
    "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : ((r & 0x3) | 0x8);
      return v.toString(16);
    });

  const espera = ms => new Promise(r => setTimeout(r, ms));

  function registrar(reg) {
    consola.push(reg);
    if (typeof window !== "undefined" && typeof pintarConsola === "function") pintarConsola();
  }

  function uuidTransaccion() {
    nSecuencia += 1;
    return { uuid: uuid(), correlacion: `HB-${String(nSecuencia).padStart(4, "0")}` };
  }

  function cabeceras(idempotencyKey) {
    const s = Sesion.leer();
    const h = {
      "Content-Type": "application/json",
      "X-Canal": DATOS_BNA.parametros.canal,
      "X-UUID": idempotencyKey
    };
    if (s && s.tokenSesion) h.Authorization = `Bearer ${s.tokenSesion}`;
    if (simulacionTimeout) h["X-Simulate-Timeout"] = "1";
    if (idempotencyKey) h["X-Idempotency-Key"] = idempotencyKey;
    return h;
  }

  /* ---------------- Modo Bus local (REST/JSON simulado) ---------------- */
  async function invocarAPI(ruta, cuerpo, interfaz, opciones = {}) {
    const tr = uuidTransaccion();
    const idem = opciones.idempotencyKey || tr.uuid;
    const inicio = performance.now();
    const solicitud = {
      metodo: "POST",
      ruta,
      interfaz,
      canal: DATOS_BNA.parametros.canal,
      uuidTransaccion: idem,
      correlacion: tr.correlacion,
      fechaHora: new Date().toISOString(),
      payload: cuerpo
    };

    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opciones.timeoutMs || 10000);
    try {
      const resp = await fetch(ruta, {
        method: "POST",
        headers: cabeceras(idem),
        body: JSON.stringify(cuerpo || {}),
        signal: ctrl.signal
      });
      const json = await resp.json();
      const ms = Math.round(performance.now() - inicio);
      registrar({
        ...solicitud,
        status: resp.status,
        estado: resp.ok && json.ok !== false ? "OK" : "ERROR",
        respuesta: json,
        ms
      });
      if (!resp.ok || json.ok === false) {
        const err = json.error || {};
        throw Object.assign(new Error(err.mensaje || "Error del Bus de Servicios"), {
          codigo: err.codigo || "ERR_API",
          mensaje: err.mensaje || "No se pudo procesar la solicitud.",
          status: resp.status
        });
      }
      return json.data !== undefined ? json.data : json;
    } catch (e) {
      const ms = Math.round(performance.now() - inicio);
      if (e.name === "AbortError") {
        const reg = {
          ...solicitud,
          status: 504,
          estado: "TIMEOUT",
          respuesta: {
            ok: false,
            error: {
              codigo: "BUS_TIMEOUT",
              mensaje: "El servicio no respondió en el tiempo esperado. La operación queda PENDIENTE / NO CONFIRMADA (RN-BUS-002)."
            }
          },
          ms
        };
        registrar(reg);
        throw Object.assign(new Error("timeout"), {
          codigo: "BUS_TIMEOUT",
          mensaje: reg.respuesta.error.mensaje,
          status: 504
        });
      }
      if (e.codigo) throw e;
      const reg = {
        ...solicitud,
        status: 0,
        estado: "SIN_CONEXION",
        respuesta: { ok: false, error: { codigo: "BUS_NO_DISPONIBLE", mensaje: "No se pudo conectar con el Bus de Servicios local." } },
        ms
      };
      registrar(reg);
      throw Object.assign(new Error("sin conexión"), {
        codigo: "BUS_NO_DISPONIBLE",
        mensaje: "No se pudo conectar con el Bus de Servicios. Verifique que el servidor local esté iniciado.",
        status: 0
      });
    } finally {
      clearTimeout(timer);
    }
  }

  /* ---------------- Modo MOCK (sin servidor) ---------------- */
  async function invocarMock(ruta, cuerpo, interfaz) {
    const tr = uuidTransaccion();
    const solicitud = {
      metodo: "POST",
      ruta,
      interfaz,
      canal: DATOS_BNA.parametros.canal,
      uuidTransaccion: tr.uuid,
      correlacion: tr.correlacion,
      fechaHora: new Date().toISOString(),
      payload: cuerpo
    };

    const retardo = 250 + Math.floor(Math.random() * 450);
    await espera(retardo);

    if (simulacionTimeout) {
      const reg = {
        ...solicitud,
        status: 504,
        estado: "TIMEOUT",
        respuesta: {
          ok: false,
          error: {
            codigo: "BUS_TIMEOUT",
            mensaje: "El servicio no respondió en el tiempo esperado. La operación queda PENDIENTE / NO CONFIRMADA (RN-BUS-002)."
          }
        },
        ms: retardo
      };
      registrar(reg);
      throw Object.assign(new Error("timeout"), { codigo: "BUS_TIMEOUT", mensaje: reg.respuesta.error.mensaje, status: 504 });
    }

    let status = 200;
    let respuesta;
    try {
      respuesta = { ok: true, data: procesar(ruta, cuerpo) };
    } catch (e) {
      status = e.status || 400;
      respuesta = { ok: false, error: { codigo: e.codigo || "ERR_GENERICO", mensaje: e.mensaje || "No se pudo procesar la solicitud." } };
    }

    registrar({ ...solicitud, status, estado: status === 200 ? "OK" : "ERROR", respuesta, ms: retardo });

    if (status !== 200) {
      throw Object.assign(new Error(respuesta.error.codigo), {
        codigo: respuesta.error.codigo,
        mensaje: respuesta.error.mensaje,
        status
      });
    }
    return respuesta.data;
  }

  function fallo(status, codigo, mensaje) {
    const e = new Error(codigo);
    Object.assign(e, { status, codigo, mensaje });
    throw e;
  }

  function procesar(ruta, p) {
    switch (ruta) {
      case "/bus/v1/seguridad/autenticar": {
        const cli = DATOS_BNA.clientes.find(c => c.codCliente === p.codCliente);
        if (!cli) fallo(404, "CLI_NO_ENCONTRADO", "La identificación ingresada no existe. Verifíquela e intente nuevamente.");
        if (cli.estado === "BLOQUEADO")
          fallo(423, "CUENTA_BLOQUEADA", "Su acceso está bloqueado. Acuda a una agencia del BNA para realizar la reactivación.");
        if (cli.claveWeb !== p.claveWeb) {
          cli.intentosFallidos += 1;
          const agotados = cli.intentosFallidos >= DATOS_BNA.parametros.maxIntentos;
          if (agotados) {
            cli.estado = "BLOQUEADO";
            fallo(423, "BLOQUEO_INTENTOS", "Superó el máximo de intentos permitidos. Su acceso ha sido bloqueado por seguridad.");
          }
          fallo(401, "CLAVE_INVALIDA", `Clave incorrecta. Le quedan ${DATOS_BNA.parametros.maxIntentos - cli.intentosFallidos} intento(s).`);
        }
        cli.intentosFallidos = 0;
        return {
          estadoAutenticacion: "AUTENTICADO",
          mensajeAcceso: "Acceso autorizado",
          datosSesion: {
            tokenSesion: uuid(),
            expiraEnMin: 15,
            cliente: { codCliente: cli.codCliente, nombres: cli.nombres, dni: cli.dni }
          }
        };
      }

      case "/bus/v1/tarjetas/asociadas": {
        const cli = DATOS_BNA.clientes.find(c => c.codCliente === p.codCliente);
        if (!cli) fallo(404, "CLI_NO_ENCONTRADO", "No se pudo identificar al cliente.");
        return {
          codCliente: cli.codCliente,
          tarjetas: DATOS_BNA.tarjetas
            .filter(t => t.codCliente === p.codCliente)
            .map(t => ({ numTarjeta: t.presentacion, marca: t.marca, tipo: t.tipo, vencimiento: t.vencimiento, estado: t.estado }))
        };
      }

      case "/bus/v1/tarjetas/verificar-titularidad": {
        const tar = DATOS_BNA.tarjetas.find(t => t.numTarjeta === String(p.numTarjeta).replace(/\s/g, ""));
        if (!tar) fallo(404, "TARJETA_NO_ENCONTRADA", "La tarjeta ingresada no fue reconocida. Verifique los datos.");
        if (tar.codCliente !== p.codCliente)
          fallo(403, "TARJETA_NO_ASOCIADA", "La tarjeta ingresada no está asociada a su titularidad.");
        if (tar.estado === "BLOQUEADA")
          fallo(409, "TARJETA_BLOQUEADA", "La tarjeta se encuentra bloqueada. No es posible consultar las cuentas asociadas.");
        if (tar.estado === "VENCIDA")
          fallo(409, "TARJETA_VENCIDA", "La tarjeta está vencida. Actualícela en una agencia para continuar.");
        return {
          tarjeta: {
            numTarjeta: tar.presentacion,
            marca: tar.marca,
            tipo: tar.tipo,
            vencimiento: tar.vencimiento,
            estado: tar.estado,
            codCliente: tar.codCliente
          }
        };
      }

      case "/bus/v1/cuentas/posicion": {
        const cli = DATOS_BNA.clientes.find(c => c.codCliente === p.codCliente);
        if (!cli) fallo(404, "CLI_NO_ENCONTRADO", "No se pudo identificar al cliente para la consulta.");
        const todas = DATOS_BNA.cuentas.filter(c => c.codCliente === p.codCliente);
        const activas = todas.filter(c => c.estado === "ACTIVA");
        if (activas.length === 0)
          fallo(409, "SIN_CUENTAS_ACTIVAS", "No se encontraron cuentas activas asociadas a su titularidad.");
        const totales = {};
        activas.forEach(c => { totales[c.moneda] = (totales[c.moneda] || 0) + c.saldoDisponible; });
        return {
          codCliente: cli.codCliente,
          titular: cli.nombres,
          filtroMes: p.filtroMes || null,
          totalCuentasActivas: activas.length,
          cuentasIgnoradas: todas.length - activas.length,
          cuentas: activas.map(c => ({
            numCuenta: c.numCuenta,
            tipoCuenta: c.tipoCuenta,
            moneda: c.moneda,
            saldoContable: c.saldoContable,
            saldoDisponible: c.saldoDisponible,
            titularidad: c.titularidad,
            estado: c.estado
          })),
          posicionConsolidada: totales
        };
      }

      case "/bus/v1/cuentas/movimientos": {
        const cli = DATOS_BNA.clientes.find(c => c.codCliente === p.codCliente);
        if (!cli) fallo(404, "CLI_NO_ENCONTRADO", "No se pudo identificar al cliente para la consulta.");
        const cta = DATOS_BNA.cuentas.find(c => c.numCuenta === p.numCuenta);
        if (!cta) fallo(404, "CUENTA_NO_ENCONTRADA", "La cuenta solicitada no existe.");
        if (cta.codCliente !== p.codCliente)
          fallo(403, "CUENTA_NO_ASOCIADA", "La cuenta consultada no pertenece a su titularidad.");
        const todos = DATOS_BNA.movimientos[p.numCuenta] || [];
        const filtrados = p.filtroMes
          ? todos.filter(m => m.fecha.slice(3, 5) === p.filtroMes.slice(5, 7) && m.fecha.slice(6) === p.filtroMes.slice(0, 4))
          : todos;
        return {
          numCuenta: cta.numCuenta,
          tipoCuenta: cta.tipoCuenta,
          moneda: cta.moneda,
          saldoContable: cta.saldoContable,
          saldoDisponible: cta.saldoDisponible,
          filtroMes: p.filtroMes || "SIN_FILTRO",
          totalMovimientos: filtrados.length,
          movimientos: filtrados
        };
      }

      default:
        fallo(409, "MODO_LOCAL_LIMITADO",
          "Esta operación requiere el Bus de Servicios local. Ejecute iniciar.sh y abra el canal desde http://127.0.0.1:8080.");
    }
  }

  async function invocar(ruta, cuerpo, interfaz, opciones = {}) {
    if (modo === "API") return invocarAPI(ruta, cuerpo, interfaz, opciones);
    return invocarMock(ruta, cuerpo, interfaz);
  }

  async function reiniciarDemo() {
    if (modo === "API") {
      try {
        await fetch("/bus/v1/demo/reiniciar", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      } catch (e) { /* el servidor puede no estar disponible */ }
    }
    DATOS_BNA.clientes.forEach(c => {
      c.intentosFallidos = 0;
      c.estado = c.codCliente === "CL-0007712" ? "BLOQUEADO" : "ACTIVO";
    });
    consola.length = 0;
    if (typeof pintarConsola === "function") pintarConsola();
  }

  function constanciaUrl(ruta) {
    const s = Sesion.leer();
    if (!ruta) return "#";
    if (modo !== "API" || !s || !s.tokenSesion) return ruta;
    return `${ruta}?token=${encodeURIComponent(s.tokenSesion)}`;
  }

  return {
    invocar,
    reiniciarDemo,
    constanciaUrl,
    nuevoIdempotencyKey: uuid,
    get consola() { return consola; },
    get timeout() { return simulacionTimeout; },
    set timeout(v) { simulacionTimeout = !!v; },
    get modo() { return modo; },
    get esApi() { return modo === "API"; }
  };
})();
