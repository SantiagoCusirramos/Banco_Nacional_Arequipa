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

  // Llave de idempotencia. crypto.randomUUID no existe por HTTP fuera de localhost (el clúster
  // se sirve por HTTP); crypto.getRandomValues sí.
  const uuid = () => {
    const b = crypto.getRandomValues(new Uint8Array(16));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    const h = [...b].map(x => x.toString(16).padStart(2, "0")).join("");
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
  };

  function cabeceras(idempotencyKey) {
    const h = { "Content-Type": "application/json" };
    // Token de COREDB para autenticación en los puentes
    const token = localStorage.getItem("bna_access_token");
    if (token) h.Authorization = `Bearer ${token}`;
    if (idempotencyKey) h["X-Idempotency-Key"] = idempotencyKey;
    return h;
  }

  /* ---------------- Invocación a puentes del frontend ---------------- */
  async function invocarAPI(ruta, cuerpo, interfaz, opciones = {}) {
    const metodo = opciones.method || "POST";
    const idem = opciones.idempotencyKey || uuid();
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opciones.timeoutMs || 10000);
    try {
      const resp = await fetch(ruta, {
        method: metodo,
        headers: { ...cabeceras(idem), ...(opciones.headers || {}) },
        body: metodo !== "GET" ? JSON.stringify(cuerpo || {}) : undefined,
        signal: ctrl.signal
      });
      const json = await resp.json();
      if (!resp.ok || json.ok === false) {
        const err = (typeof json.error === "object" && json.error) || {};
        const texto = err.message || json.message || (typeof json.detail === "string" ? json.detail : "") ||
          json.detalle || "No se pudo procesar la solicitud.";
        // Con la contraseña inicial o renovada, COREDB no deja operar hasta cambiarla.
        if (err.code === "CAMBIO_CLAVE_OBLIGATORIO") window.location.href = "/cambiar-clave";
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
          mensaje: "El servicio no respondió a tiempo: la operación queda sin confirmar.",
          status: 504
        });
      }
      if (e.codigo) throw e;
      // Sin respuesta (red caída) o respuesta que no es JSON (un proxy intermedio): no se sabe
      // si la operación llegó.
      throw Object.assign(new Error("sin conexión"), {
        codigo: "BUS_NO_DISPONIBLE",
        mensaje: "No hubo respuesta del servidor. Revisa tu conexión.",
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
    // Quien entra no hereda ninguna sesión anterior (portal, Solicitud, otro cliente atendido).
    Sesion.cerrarTodo();
    const r = await invocarAPI("/api/core/coredb/auth/login", { username: usuario, password: clave }, "COREDB · login");
    if (!r.access_token) fallo(401, "LOGIN", "COREDB no devolvió un token.");
    localStorage.setItem("bna_access_token", r.access_token);
    const yo = await invocarAPI("/api/core/coredb/auth/me", null, "COREDB · perfil", { method: "GET" });
    // La misma sesión que el portal (lib/auth.ts): su token y su usuario.
    localStorage.setItem("bna_usuario", JSON.stringify({
      id_usuario: yo.id_usuario, username: yo.username || usuario,
      nombre: yo.nombre_completo || yo.username || usuario, rol: yo.rol, acciones: yo.acciones || []
    }));
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

  // La cuenta de destino antes de confirmar: moneda, estado y titular enmascarado (CUENTAS no
  // devuelve su saldo ni los datos del titular).
  async function verDestino(numCuenta) {
    const d = await invocarAPI(`/api/cuenta/${encodeURIComponent(numCuenta)}/destino`, null, "CUENTAS · destino", { method: "GET" });
    return { numCuenta: d.num_cuenta, moneda: d.moneda, estado: d.estado_cuenta, titular: d.titular };
  }

  // La llave la pone quien llama: la misma en cada reintento de la misma transferencia
  // (COREDB devuelve la original) y otra cuando cambian los datos, se registró o se rechazó.
  // Canal WEB = Home Banking (HB) en COREDB, que aplica su tope diario. Devuelve lo que contestó
  // CUENTAS, leído de COREDB tras transferir; la pantalla comprueba que esté completo y no rellena nada.
  async function transferencia(p, idempotencyKey) {
    const cuerpo = { num_cuenta_origen: p.cuentaOrigen, num_cuenta_destino: p.cuentaDestino, monto: num(p.monto).toFixed(2) };
    if (p.glosa) cuerpo.glosa = p.glosa;
    const r = await invocarAPI("/api/cuenta/transferencia", cuerpo, "CUENTAS · transferencia", {
      idempotencyKey,
      headers: { "X-Channel-ID": "WEB", "X-Request-Timestamp": new Date().toISOString() }
    });
    return {
      idTransferencia: r.uuid_debito,
      uuidAbono: r.uuid_abono,
      idempotente: r.replay === true,
      cuentaOrigen: r.num_cuenta_origen,
      cuentaDestino: r.num_cuenta_destino,
      monto: r.monto,
      moneda: r.moneda,
      fechaHora: r.fecha_hora,
      estado: r.estado,
      saldoDisponibleOrigen: r.saldo_disponible_origen,
      titularDestino: r.titular_destino
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
          // La cuota más antigua con saldo: COREDB aplica el pago desde ella.
          proximaCuota: pendientes.length
            ? { numero: pendientes[0].numeroCuota, vence: pendientes[0].fechaVencimiento }
            : null,
          estado: c.estadoCredito
        };
      })
    };
  }

  async function obtenerMontoAPagar(codCredito) {
    return invocarAPI(`/api/cobranza/creditos/${encodeURIComponent(codCredito)}/monto-a-pagar`, null, "COBRANZA · monto a pagar", { method: "GET" });
  }

  // CR-INT-08: referenciaTransaccion es la llave; la misma en un reintento no cobra dos veces.
  // Devuelve la respuesta de COBRANZA tal cual (estado, saldo del crédito, cuotas pendientes...):
  // la pantalla comprueba que esté completa y no rellena nada.
  async function pagarCuota(codCredito, p, idempotencyKey) {
    const s = sesion();
    return invocarAPI("/api/cobranza/cr-int-08/pagos", {
      codCliente: s.codCliente, codCredito, montoPago: num(p.montoPago).toFixed(2),
      cuentaOrigen: p.numCuentaOrigen, referenciaTransaccion: idempotencyKey
    }, "COBRANZA · CR-INT-08", { idempotencyKey });
  }

  // Bitácora de COREDB (VER_AUDITORIA: administrador y auditor). Solo lo que COREDB guarda: fecha,
  // módulo, acción, quién y sobre qué. No hay canal, IP ni «resultado»: cada evento es una acción hecha.
  async function consultarAuditoria(limit, filtros = {}) {
    const params = new URLSearchParams({ limite: String(Math.min(limit, 200)) });
    if (filtros.modulo) params.set("modulo", filtros.modulo);
    if (filtros.tipo) params.set("accion", filtros.tipo);
    const lista = await invocarAPI(`/api/core/coredb/auditoria?${params.toString()}`, null, "COREDB · auditoría", { method: "GET" }) || [];
    const eventos = lista.map(e => ({
      idEvento: e.id_evento, fechaHora: e.fecha_hora, modulo: e.modulo, accion: e.accion,
      usuario: e.actor, entidad: e.entidad, idEntidad: e.id_entidad
    }));
    return {
      total: eventos.length,
      eventos,
      modulos: [...new Set(eventos.map(e => e.modulo))],
      acciones: [...new Set(eventos.map(e => e.accion))]
    };
  }

  // Acciones del usuario que inició sesión (COREDB /auth/me).
  async function misPermisos() {
    const yo = await invocarAPI("/api/core/coredb/auth/me", null, "COREDB · perfil", { method: "GET" });
    return (yo && yo.acciones) || [];
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
    verDestino,
    transferencia,
    obtenerCreditosCliente,
    obtenerMontoAPagar,
    pagarCuota,
    consultarAuditoria,
    misPermisos,
    constanciaUrl,
    nuevoIdempotencyKey: uuid
  };
})();