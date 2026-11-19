/* =========================================================
   BUS DE SERVICIOS DEL PROTOTIPO - Versión para frontend Next.js
   Usa SOLO las rutas de puente existentes en el frontend:
   - /api/core/coredb/* → COREDB (auth, me, auditoría)
   - /api/cuenta/* → CUENTAS (cuenta, movimientos, consolidada, transferencia)
   - /api/tarjeta/* → TARJETAS
   - /api/cobranza/* → COBRANZA (créditos, pagos CR-INT-08)
   El token de COREDB se lee de localStorage con clave 'bna_access_token'.
   ========================================================= */

const Bus = (() => {

  let nSecuencia = 0;
  let simulacionTimeout = false;
  const consola = [];

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

  function leerToken() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("bna_access_token");
  }

  function cabeceras(idempotencyKey) {
    const s = Sesion.leer();
    const h = {
      "Content-Type": "application/json",
    };
    // Token de COREDB para autenticación en los puentes
    const token = leerToken();
    if (token) h.Authorization = `Bearer ${token}`;
    if (idempotencyKey) h["X-Idempotency-Key"] = idempotencyKey;
    return h;
  }

  /* ---------------- Invocación a puentes del frontend ---------------- */
  async function invocarAPI(ruta, cuerpo, interfaz, opciones = {}) {
    const tr = uuidTransaccion();
    const idem = opciones.idempotencyKey || tr.uuid;
    const inicio = performance.now();
    const solicitud = {
      metodo: opciones.method || "POST",
      ruta,
      interfaz,
      canal: "HB_WEB",
      uuidTransaccion: idem,
      correlacion: tr.correlacion,
      fechaHora: new Date().toISOString(),
      payload: cuerpo
    };

    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opciones.timeoutMs || 10000);
    try {
      const resp = await fetch(ruta, {
        method: solicitud.metodo,
        headers: { ...cabeceras(idem), ...(opciones.headers || {}) },
        body: solicitud.metodo !== "GET" ? JSON.stringify(cuerpo || {}) : undefined,
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
        const err = (typeof json.error === "object" && json.error) || {};
        const texto = err.message || json.message || (typeof json.detail === "string" ? json.detail : "") ||
          json.detalle || "No se pudo procesar la solicitud.";
        throw Object.assign(new Error(texto), {
          codigo: err.code || json.error_code || "ERR_API",
          mensaje: texto,
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
        respuesta: { ok: false, error: { codigo: "BUS_NO_DISPONIBLE", mensaje: "No se pudo conectar con el frontend." } },
        ms
      };
      registrar(reg);
      throw Object.assign(new Error("sin conexión"), {
        codigo: "BUS_NO_DISPONIBLE",
        mensaje: "No se pudo conectar con el frontend. Verifique que el servidor esté iniciado.",
        status: 0
      });
    } finally {
      clearTimeout(timer);
    }
  }

  /* ---------------- Funciones de error ---------------- */
  function fallo(status, codigo, mensaje) {
    const e = new Error(codigo);
    Object.assign(e, { status, codigo, mensaje });
    throw e;
  }

  /* ---------------- Mapeo de operaciones a rutas de puente ----------------
     Cada función llama a un puente que existe (frontend/app/api/*) y traduce su respuesta
     (CUENTAS, TARJETAS, COBRANZA y COREDB, en snake_case o camelCase según el módulo) a la
     forma que usan las pantallas del prototipo. */

  const num = v => Number(v || 0);
  const sesion = () => {
    const s = Sesion.leer();
    if (!s) fallo(401, "NO_SESION", "No hay sesión activa.");
    return s;
  };

  // El Home Banking no tiene todavía autenticación de clientes (CR-INT-08 sigue sin canal propio):
  // entra un usuario del banco con su clave de COREDB y elige el cliente que atiende.
  async function autenticar(usuario, clave, codCliente) {
    const r = await invocarAPI("/api/core/coredb/auth/login", { username: usuario, password: clave }, "COREDB · login");
    if (!r.access_token) fallo(401, "LOGIN", "COREDB no devolvió un token.");
    localStorage.setItem("bna_access_token", r.access_token);
    const yo = await invocarAPI("/api/core/coredb/auth/me", null, "COREDB · perfil", { method: "GET" });
    return {
      estadoAutenticacion: "AUTENTICADO",
      mensajeAcceso: "Acceso autorizado",
      datosSesion: {
        tokenSesion: r.access_token,
        cliente: { codCliente, nombres: yo.nombre_completo || yo.username || usuario, dni: yo.username || usuario }
      }
    };
  }

  async function obtenerTarjetasAsociadas(codCliente) {
    const lista = await invocarAPI(`/api/tarjeta/cliente/${encodeURIComponent(codCliente)}`, null, "TARJETAS · del cliente", { method: "GET" });
    return {
      codCliente,
      tarjetas: (lista || []).map(t => ({
        idTarjeta: t.id_tarjeta,
        numTarjeta: t.numero_enmascarado || ("•••• " + t.ultimos4),
        marca: "BNA",
        tipo: "DÉBITO",
        vencimiento: t.vencimiento_mm_aa,
        estado: t.estado_tarjeta
      }))
    };
  }

  // Bloqueo de la tarjeta: ruta de bloqueo de TARJETAS (por el Bus). El desbloqueo no se hace aquí:
  // TARJETAS lo rechaza y lo hace Seguridad.
  async function bloquearTarjeta(idTarjeta, motivo) {
    return invocarAPI(`/api/tarjeta/${encodeURIComponent(idTarjeta)}/bloqueo`, { motivo }, "TARJETAS · bloqueo");
  }

  async function verificarTitularidad() {
    // Sin ruta en el producto: no se hace ninguna petición.
    fallo(501, "NO_DISPONIBLE", "Verificar titularidad no está disponible en esta versión.");
  }

  const cuentaUi = c => ({
    numCuenta: c.num_cuenta,
    tipoCuenta: "AHORROS",
    moneda: c.moneda,
    saldoContable: num(c.saldo_contable),
    saldoDisponible: num(c.saldo_disponible),
    titularidad: c.regimen,
    estado: c.estado_cuenta
  });

  async function consultarPosicion(codCliente, filtroMes) {
    const lista = await invocarAPI(`/api/cuenta/consolidada/${encodeURIComponent(codCliente)}`, null, "CUENTAS · consolidada", { method: "GET" });
    const todas = (lista || []).map(cuentaUi);
    const cuentas = todas.filter(c => c.estado === "ACTIVA");
    const totales = {};
    cuentas.forEach(c => { totales[c.moneda] = (totales[c.moneda] || 0) + c.saldoDisponible; });
    return {
      codCliente,
      titular: codCliente,
      filtroMes: filtroMes || null,
      totalCuentasActivas: cuentas.length,
      cuentasIgnoradas: todas.length - cuentas.length,
      cuentas,
      posicionConsolidada: totales
    };
  }

  async function consultarMovimientos(codCliente, numCuenta, filtroMes) {
    const cuenta = cuentaUi(await invocarAPI(`/api/cuenta/${encodeURIComponent(numCuenta)}`, null, "CUENTAS · cuenta", { method: "GET" }));
    let movs = await invocarAPI(`/api/cuenta/${encodeURIComponent(numCuenta)}/movimientos`, null, "CUENTAS · movimientos", { method: "GET" }) || [];
    if (filtroMes) movs = movs.filter(m => String(m.fecha_hora).startsWith(filtroMes));
    return {
      numCuenta,
      tipoCuenta: cuenta.tipoCuenta,
      moneda: cuenta.moneda,
      saldoContable: cuenta.saldoContable,
      saldoDisponible: cuenta.saldoDisponible,
      filtroMes: filtroMes || "SIN_FILTRO",
      totalMovimientos: movs.length,
      movimientos: movs.map(m => ({
        fecha: m.fecha_hora,
        operacion: m.tipo_operacion,
        glosa: m.glosa,
        monto: m.naturaleza === "D" ? -num(m.monto) : num(m.monto),
        saldo: null
      }))
    };
  }

  // La llave la pone quien llama: la misma en cada reintento de la misma transferencia
  // (CUENTAS devuelve la original) y otra cuando cambian los datos o ya se registró.
  async function transferencia(p, idempotencyKey) {
    if (p.tipo !== "PROPIA" && p.tipo !== "TERCERO") {
      fallo(501, "NO_DISPONIBLE", "Las transferencias interbancarias no están disponibles en esta versión.");
    }
    const r = await invocarAPI("/api/cuenta/transferencia", {
      num_cuenta_origen: p.cuentaOrigen, num_cuenta_destino: p.cuentaDestino, monto: num(p.monto).toFixed(2)
    }, "CUENTAS · transferencia", {
      idempotencyKey,
      headers: { "X-Channel-ID": "VEN", "X-Request-Timestamp": new Date().toISOString() }
    });
    const origen = cuentaUi(await invocarAPI(`/api/cuenta/${encodeURIComponent(p.cuentaOrigen)}`, null, "CUENTAS · cuenta", { method: "GET" }));
    return {
      idTransferencia: r.uuid_debito,
      uuidTransaccion: r.uuid_debito,
      idAsientoCore: r.uuid_abono,
      idempotente: !!r.replay,
      estado: "REGISTRADA",
      fechaHora: new Date().toLocaleString("es-PE"),
      tipo: p.tipo,
      monto: num(p.monto),
      moneda: p.moneda,
      cuentaOrigen: p.cuentaOrigen,
      cuentaDestino: p.cuentaDestino,
      entidadDestino: "BNA",
      titularDestino: p.titularDestino || "",
      saldoActualizado: { saldoDisponible: origen.saldoDisponible },
      constanciaPDF: null
    };
  }

  async function obtenerCreditosCliente() {
    const s = sesion();
    const lista = await invocarAPI(`/api/cobranza/clientes/${encodeURIComponent(s.codCliente)}/creditos`, null, "COBRANZA · créditos", { method: "GET" });
    return {
      creditos: (lista || []).map(c => {
        const pendientes = (c.cuotas || []).filter(q => q.estadoCuota !== "PAGADA");
        return {
          codCredito: c.codCredito,
          producto: "Crédito " + c.codCredito,
          moneda: c.moneda,
          saldo: num(c.saldoTotalPendiente),
          cuota: pendientes.length ? num(pendientes[0].totalAdeudado) : 0,
          cuotasPendientes: pendientes.length,
          estado: c.estadoCredito,
          cuentaAsociada: null
        };
      })
    };
  }

  async function obtenerMontoAPagar(codCredito) {
    return invocarAPI(`/api/cobranza/creditos/${encodeURIComponent(codCredito)}/monto-a-pagar`, null, "COBRANZA · monto a pagar", { method: "GET" });
  }

  // CR-INT-08: referenciaTransaccion es la llave; la misma en un reintento no cobra dos veces.
  async function pagarCuota(codCredito, p, idempotencyKey) {
    const s = sesion();
    const r = await invocarAPI("/api/cobranza/cr-int-08/pagos", {
      codCliente: s.codCliente, codCredito, montoPago: num(p.montoPago).toFixed(2),
      cuentaOrigen: p.numCuentaOrigen, referenciaTransaccion: idempotencyKey
    }, "COBRANZA · CR-INT-08", { idempotencyKey });
    if (r.estado && r.estado !== "CONFIRMADO") fallo(422, "PAGO_" + r.estado, r.motivo || "El pago no se confirmó.");
    return {
      idPago: r.idPago,
      uuidTransaccion: r.referenciaTransaccion,
      codCredito: r.codCredito,
      producto: "Crédito " + r.codCredito,
      estadoPago: r.estado,
      idempotente: !!r.idempotente,
      montoPagado: num(p.montoPago),
      moneda: p.moneda,
      fechaHora: new Date().toLocaleString("es-PE"),
      idAsientoCore: r.idPago,
      saldoCredito: null,
      cuotasPendientes: null,
      saldoActualizado: null,
      constanciaPDF: null
    };
  }

  // Bitácora de COREDB (solo el administrador). No hay "resultado": cada evento es una acción hecha.
  async function consultarAuditoria(limit, filtros = {}) {
    const params = new URLSearchParams({ limite: String(Math.min(limit, 200)) });
    if (filtros.modulo) params.set("modulo", filtros.modulo);
    if (filtros.tipo) params.set("accion", filtros.tipo);
    const lista = await invocarAPI(`/api/core/coredb/auditoria?${params.toString()}`, null, "COREDB · auditoría", { method: "GET" }) || [];
    const eventos = lista.map(e => ({
      idEvento: e.id_evento, fechaHora: e.fecha_hora, modulo: e.modulo, tipoEvento: e.accion,
      usuario: e.actor, resultado: "OK", detalle: `${e.entidad} ${e.id_entidad}`,
      canal: "-", ip: "-", uuid: e.correlation_id || "-"
    }));
    return {
      total: eventos.length,
      eventos,
      modulos: [...new Set(eventos.map(e => e.modulo))],
      tipos: [...new Set(eventos.map(e => e.tipoEvento))]
    };
  }

  async function reiniciarDemo() {
    // No hay reinicio de demo en esta versión: solo se limpia la consola local.
    consola.length = 0;
    if (typeof pintarConsola === "function") pintarConsola();
  }

  function constanciaUrl() {
    return null;  // No hay constancia PDF en el producto.
  }

  return {
    invocar: invocarAPI,
    autenticar,
    obtenerTarjetasAsociadas,
    bloquearTarjeta,
    verificarTitularidad,
    consultarPosicion,
    consultarMovimientos,
    transferencia,
    obtenerCreditosCliente,
    obtenerMontoAPagar,
    pagarCuota,
    consultarAuditoria,
    reiniciarDemo,
    constanciaUrl,
    nuevoIdempotencyKey: uuid,
    get consola() { return consola; },
    get timeout() { return simulacionTimeout; },
    set timeout(v) { simulacionTimeout = !!v; },
    get modo() { return "API"; },
    get esApi() { return true; }
  };
})();