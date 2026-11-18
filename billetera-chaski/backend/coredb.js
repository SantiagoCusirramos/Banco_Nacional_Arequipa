'use strict';
// Cliente de COREDB a través del Bus de Servicios.
//
// Chaski no tiene base propia: cada operación es una llamada a /coredb/billetera/* por el
// Bus (COREDB_URL = http://bus:8018/bus/coredb), con:
//   - X-Bus-Token: la credencial de Chaski ante el Bus (BUS_TOKEN);
//   - Authorization: el token del usuario de servicio svc-billetera (rol SERVICIO, módulo
//     BILLETERA), que se pide con CHASKI_COREDB_USUARIO y CHASKI_COREDB_SECRETO;
//   - X-Cliente-Token: el token del cliente, que COREDB entregó al validar su celular y PIN.
// COREDB identifica al cliente por ese token, nunca por lo que diga Chaski.

class ErrorCoreDb extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// Un token de servicio vencido o revocado se renueva una vez; repetir es seguro porque las
// operaciones de dinero llevan su llave de idempotencia.
const RENOVAR_SERVICIO = new Set(['TOKEN_EXPIRADO', 'TOKEN_INVALIDO', 'USUARIO_NO_VIGENTE', 'TOKEN_REQUERIDO']);

function crearCliente({ url, busToken, usuario, secreto, timeoutMs = 10000, fetchImpl = fetch }) {
  const base = String(url || '').replace(/\/+$/, '');
  let sesion = null; // { token, vence }

  async function pedir(metodo, ruta, { cuerpo, cabeceras = {} } = {}) {
    let res;
    try {
      res = await fetchImpl(base + ruta, {
        method: metodo,
        headers: { Accept: 'application/json', 'X-Bus-Token': busToken,
          ...(cuerpo === undefined ? {} : { 'Content-Type': 'application/json' }), ...cabeceras },
        body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch {
      throw new ErrorCoreDb(503, 'COREDB_NO_DISPONIBLE', 'COREDB no respondió a través del Bus');
    }
    const texto = await res.text();
    let datos = null;
    try {
      datos = texto ? JSON.parse(texto) : null;
    } catch {
      datos = null;
    }
    return { status: res.status, datos };
  }

  async function tokenServicio(renovar) {
    if (!renovar && sesion && sesion.vence > Date.now()) return sesion.token;
    const r = await pedir('POST', '/coredb/auth/login', { cuerpo: { username: usuario, password: secreto } });
    if (r.status !== 200 || !r.datos || !r.datos.access_token) {
      sesion = null;
      throw new ErrorCoreDb(502, 'COREDB_SERVICIO', 'Chaski no pudo iniciar sesión en COREDB');
    }
    const segundos = Math.max(30, Number(r.datos.expires_in) || 0);
    sesion = { token: r.datos.access_token, vence: Date.now() + (segundos - 30) * 1000 };
    return sesion.token;
  }

  async function llamar(metodo, ruta, { cuerpo, tokenCliente, llave } = {}) {
    for (let intento = 0; ; intento++) {
      const cabeceras = { Authorization: `Bearer ${await tokenServicio(intento > 0)}` };
      if (tokenCliente) cabeceras['X-Cliente-Token'] = tokenCliente;
      if (llave) cabeceras['X-Idempotency-Key'] = llave;
      const r = await pedir(metodo, ruta, { cuerpo, cabeceras });
      if (r.status >= 200 && r.status < 300) return r.datos;
      const error = (r.datos && r.datos.error) || {};
      if (r.status === 401 && intento === 0 && RENOVAR_SERVICIO.has(error.code)) continue;
      throw new ErrorCoreDb(r.status, error.code || `HTTP_${r.status}`, error.message || 'Error de COREDB');
    }
  }

  async function salud() {
    try {
      return (await pedir('GET', '/coredb/salud')).status === 200;
    } catch {
      return false;
    }
  }

  return { llamar, salud };
}

module.exports = { crearCliente, ErrorCoreDb };
