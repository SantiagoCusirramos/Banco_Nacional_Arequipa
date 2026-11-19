const Bus = (() => {

  const uuid = () =>
    "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : ((r & 0x3) | 0x8);
      return v.toString(16);
    });

  function fallo(status, codigo, mensaje) {
    const e = new Error(codigo);
    Object.assign(e, { status, codigo, mensaje });
    throw e;
  }

  function leerToken() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("bna_access_token");
  }

  function cabeceras(idempotencyKey) {
    const h = { "Content-Type": "application/json" };
    const token = leerToken();
    if (token) h.Authorization = `Bearer ${token}`;
    if (idempotencyKey) h["X-Idempotency-Key"] = idempotencyKey;
    return h;
  }

  async function invocarAPI(ruta, cuerpo, opciones = {}) {
    const idem = opciones.idempotencyKey || uuid();
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opciones.timeoutMs || 10000);
    try {
      const resp = await fetch(ruta, {
        method: opciones.method || "POST",
        headers: { ...cabeceras(idem), ...(opciones.headers || {}) },
        body: (opciones.method || "POST") !== "GET" ? JSON.stringify(cuerpo || {}) : undefined,
        signal: ctrl.signal
      });
      const json = await resp.json();
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
      if (e.name === "AbortError") {
        throw Object.assign(new Error("timeout"), {
          codigo: "BUS_TIMEOUT",
          mensaje: "El servicio no respondió en el tiempo esperado. Intente nuevamente.",
          status: 504
        });
      }
      if (e.codigo) throw e;
      throw Object.assign(new Error("sin conexión"), {
        codigo: "BUS_NO_DISPONIBLE",
        mensaje: "No se pudo conectar con el servicio. Intente nuevamente.",
        status: 0
      });
    } finally {
      clearTimeout(timer);
    }
  }

  const num = v => Number(v || 0);
  const sesion = () => {
    const s = Sesion.leer();
    if (!s) fallo(401, "NO_SESION", "No hay sesión activa.");
    return s;
  };

  async function autenticar(usuario, clave, codCliente) {
    const r = await invocarAPI("/api/core/coredb/auth/login", { username: usuario, password: clave });
    if (!r.access_token) fallo(401, "LOGIN", "No se pudo completar el ingreso.");
    localStorage.setItem("bna_access_token", r.access_token);
    const yo = await invocarAPI("/api/core/coredb/auth/me", null, { method: "GET" });
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
    const lista = await invocarAPI(`/api/tarjeta/cliente/${encodeURIComponent(codCliente)}`, null, { method: "GET" });
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

  async function bloquearTarjeta(idTarjeta, motivo) {
    return invocarAPI(`/api/tarjeta/${encodeURIComponent(idTarjeta)}/bloqueo`, { motivo });
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

  async function consultarPosicion(codCliente) {
    const lista = await invocarAPI(`/api/cuenta/consolidada/${encodeURIComponent(codCliente)}`, null, { method: "GET" });
    const todas = (lista || []).map(cuentaUi);
    const cuentas = todas.filter(c => c.estado === "ACTIVA");
    const totales = {};
    cuentas.forEach(c => { totales[c.moneda] = (totales[c.moneda] || 0) + c.saldoDisponible; });
    return {
      codCliente,
      titular: codCliente,
      totalCuentasActivas: cuentas.length,
      cuentasIgnoradas: todas.length - cuentas.length,
      cuentas,
      posicionConsolidada: totales
    };
  }

  async function consultarMovimientos(codCliente, numCuenta, filtroMes) {
    const cuenta = cuentaUi(await invocarAPI(`/api/cuenta/${encodeURIComponent(numCuenta)}`, null, { method: "GET" }));
    let movs = await invocarAPI(`/api/cuenta/${encodeURIComponent(numCuenta)}/movimientos`, null, { method: "GET" }) || [];
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

  async function transferencia(p, idempotencyKey) {
    if (p.tipo !== "PROPIA" && p.tipo !== "TERCERO") {
      fallo(501, "NO_DISPONIBLE", "Esta transferencia no está disponible en este momento.");
    }
    const r = await invocarAPI("/api/cuenta/transferencia", {
      num_cuenta_origen: p.cuentaOrigen, num_cuenta_destino: p.cuentaDestino, monto: num(p.monto).toFixed(2)
    }, {
      idempotencyKey,
      headers: { "X-Channel-ID": "VEN", "X-Request-Timestamp": new Date().toISOString() }
    });
    const origen = cuentaUi(await invocarAPI(`/api/cuenta/${encodeURIComponent(p.cuentaOrigen)}`, null, { method: "GET" }));
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
    const lista = await invocarAPI(`/api/cobranza/clientes/${encodeURIComponent(s.codCliente)}/creditos`, null, { method: "GET" });
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
    return invocarAPI(`/api/cobranza/creditos/${encodeURIComponent(codCredito)}/monto-a-pagar`, null, { method: "GET" });
  }

  async function pagarCuota(codCredito, p, idempotencyKey) {
    const s = sesion();
    const r = await invocarAPI("/api/cobranza/cr-int-08/pagos", {
      codCliente: s.codCliente, codCredito, montoPago: num(p.montoPago).toFixed(2),
      cuentaOrigen: p.numCuentaOrigen, referenciaTransaccion: idempotencyKey
    }, { idempotencyKey });
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

  async function consultarAuditoria(limit, filtros = {}) {
    const params = new URLSearchParams({ limite: String(Math.min(limit, 200)) });
    if (filtros.modulo) params.set("modulo", filtros.modulo);
    if (filtros.tipo) params.set("accion", filtros.tipo);
    const lista = await invocarAPI(`/api/core/coredb/auditoria?${params.toString()}`, null, { method: "GET" }) || [];
    const eventos = lista.map(e => ({
      idEvento: e.id_evento, fechaHora: e.fecha_hora, modulo: e.modulo, tipoEvento: e.accion,
      usuario: e.actor,
      resultado: String((e.detalle && e.detalle.resultado) || e.resultado || "OK").toUpperCase(),
      detalle: `${e.entidad} ${e.id_entidad}`,
      canal: (e.detalle && e.detalle.canal) || "-",
      ip: (e.detalle && e.detalle.ip) || "-",
      uuid: e.correlation_id || "-"
    }));
    const aplicables = filtros.resultado ? eventos.filter(e => e.resultado === filtros.resultado) : eventos;
    return {
      total: aplicables.length,
      eventos: aplicables,
      modulos: [...new Set(aplicables.map(e => e.modulo))],
      tipos: [...new Set(aplicables.map(e => e.tipoEvento))]
    };
  }

  function constanciaUrl() {
    return null;
  }

  return {
    invocar: invocarAPI,
    autenticar,
    obtenerTarjetasAsociadas,
    bloquearTarjeta,
    consultarPosicion,
    consultarMovimientos,
    transferencia,
    obtenerCreditosCliente,
    obtenerMontoAPagar,
    pagarCuota,
    consultarAuditoria,
    constanciaUrl,
    nuevoIdempotencyKey: uuid
  };
})();
