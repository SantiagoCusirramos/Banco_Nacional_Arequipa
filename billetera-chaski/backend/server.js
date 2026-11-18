'use strict';
// API de Chaski (Billetera Digital BNA) para la app móvil, integrada al producto.
//
// Sin base propia: los clientes, cuentas, saldos, QR, cobros y avisos están en la base
// integrada, y Chaski los opera por COREDB a través del Bus (ver coredb.js). Los clientes los
// registra el módulo Clientes (punto R-01) y el banco los afilia a la billetera; Chaski no
// crea clientes. El token de sesión que recibe la app es el token de cliente que emite
// COREDB: Chaski no firma ni guarda nada. Chaski no registra cuerpos ni celulares.
//
// Fuera de esta versión (decisión pendiente del equipo): tienda, promociones, cupones,
// ofertas, órdenes, recargas y pago de servicios.
const crypto = require('node:crypto');
const express = require('express');
const { crearCliente, ErrorCoreDb } = require('./coredb');

const MAX_OPERACION = 500; // S/ por operación; el tope diario lo aplica la base (canal BD)
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SESION_VENCIDA = 'Sesión vencida. Inicia sesión otra vez.';
const B = '/coredb/billetera';

class AppError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Rechazos de COREDB → lo que ve la app. Nada de esto repite el celular.
const TRADUCCION = {
  CREDENCIALES_INVALIDAS: [401, 'Celular o PIN incorrecto'],
  PIN_INCORRECTO: [401, 'PIN incorrecto'],
  BILLETERA_BLOQUEADA: [403, 'Tu billetera está bloqueada. Acércate al banco.'],
  BILLETERA_NO_DISPONIBLE: [403, 'Cuenta no disponible'],
  'BNA-BILLETERA': [403, 'Cuenta no disponible'],
  CLIENTE_TOKEN_REQUERIDO: [401, SESION_VENCIDA],
  TOKEN_CLIENTE_INVALIDO: [401, SESION_VENCIDA],
  TOKEN_CLIENTE_EXPIRADO: [401, SESION_VENCIDA],
  CLIENTE_NO_VIGENTE: [401, SESION_VENCIDA],
  'BNA-SALDO': [400, 'Saldo insuficiente'],
  'RN-TOP-001': [400, `Superaste el tope diario de S/ ${MAX_OPERACION} de la billetera`],
  'BNA-BILLETERA-MONTO': [400, 'Ingresa un monto válido'],
  'BNA-BILLETERA-PROPIA': [400, 'No puedes usar tu propio número'],
  'BNA-BILLETERA-DESTINO': [404, 'El número ingresado no está registrado en Chaski'],
  CONTACTO_NO_ENCONTRADO: [404, 'El número ingresado no está registrado en Chaski'],
  'BNA-QR': [404, 'Código QR no reconocido o no válido'],
  QR_NO_ENCONTRADO: [404, 'Código QR no reconocido o no válido'],
  'BNA-QR-NO-VIGENTE': [410, 'Este código QR ya no está vigente'],
  'BNA-QR-PROPIO': [400, 'No puedes pagar tu propio QR'],
  'BNA-QR-MONTO': [400, 'El monto no es el del código QR'],
  'BNA-IDEMPOTENCIA': [409, 'Operación duplicada'],
  'BNA-SOLICITUD': [404, 'La solicitud ya no está disponible'],
  SOLICITUD_NO_ENCONTRADA: [404, 'La solicitud ya no está disponible'],
  'BNA-SOLICITUD-NO-PENDIENTE': [404, 'La solicitud ya no está disponible'],
  'BNA-SOLICITUD-PERMISO': [403, 'No permitido'],
};

function traducir(error) {
  if (error instanceof AppError) return [error.status, error.message];
  if (error instanceof ErrorCoreDb) {
    if (TRADUCCION[error.code]) return TRADUCCION[error.code];
    if (error.status === 422 || error.status === 400) return [400, 'Datos inválidos'];
    if (error.status === 404) return [404, 'No encontrado'];
    // 401/403 del token de servicio, 5xx de COREDB o del Bus: problema del servicio, no del cliente.
    return [503, 'Servicio no disponible. Intenta más tarde.'];
  }
  return [500, 'Error interno'];
}

// ---- validación de entradas ----
const texto = (v, max = 100) => (typeof v === 'string' ? v.trim().slice(0, max) : '');
function celular(v) {
  const c = texto(v, 20);
  if (!/^9\d{8}$/.test(c)) throw new AppError(400, 'El celular debe tener 9 dígitos y empezar con 9');
  return c;
}
function pin(v) {
  const p = texto(v, 6);
  if (!/^\d{6}$/.test(p)) throw new AppError(400, 'El PIN debe tener 6 dígitos');
  return p;
}
function monto(v) {
  const n = Math.round(Number(v) * 100) / 100;
  if (!Number.isFinite(n) || n <= 0) throw new AppError(400, 'Ingresa un monto válido');
  if (n > MAX_OPERACION) throw new AppError(400, `El límite por operación es S/ ${MAX_OPERACION}`);
  return n.toFixed(2);
}
function uuidRuta(v) {
  if (!UUID_RE.test(String(v))) throw new AppError(404, 'No encontrado');
  return String(v).toLowerCase();
}
// RN-BUS-002: la app genera el uuid de la operación y lo repite si reintenta. Sin uuid, uno
// nuevo (la operación no se podrá repetir sin cobrar otra vez).
function llave(req) {
  const dada = texto(req.get('Idempotency-Key') || (req.body && req.body.uuid_transaccion), 36);
  if (!dada) return crypto.randomUUID();
  if (!UUID_RE.test(dada)) throw new AppError(400, 'uuid_transaccion inválido');
  return dada.toLowerCase();
}

// ---- de COREDB a la forma que usa la app ----
const num = (v) => (v === null || v === undefined ? null : Number(v));
function operacion(o) {
  return {
    id_operacion: o.id_operacion,
    id_transferencia: o.id_operacion,
    id_pago: o.id_operacion,
    tipo: o.tipo.toLowerCase(),
    monto: num(o.monto),
    destinatario: o.nombre_destino,
    remitente: o.nombre_origen,
    referencia: o.referencia,
    fecha_hora: o.fecha_hora,
    repetida: Boolean(o.repetido),
  };
}
const ESTADO_SOLICITUD = { PENDIENTE: 'pendiente', PAGADA: 'aceptada', RECHAZADA: 'rechazada',
  CANCELADA: 'cancelada', VENCIDA: 'expirada' };
function solicitud(s, nombre) {
  return { id_solicitud: s.id_solicitud, monto: num(s.monto), concepto: s.concepto,
    estado: ESTADO_SOLICITUD[s.estado] || s.estado.toLowerCase(), fecha: s.fecha_solicitud,
    vence: s.fecha_vencimiento, nombre };
}
function qr(q) {
  return { id_qr: q.id_qr, tipo: q.tipo.toLowerCase(), monto: num(q.monto), nombre: q.beneficiario,
    es_comercio: q.es_comercio, estado: q.estado.toLowerCase(), fecha_expiracion: q.fecha_expiracion,
    expira: q.fecha_expiracion, promo: null };
}

function crearApp({ coredb }) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '20kb' }));
  app.use((req, res, next) => {
    res.set({ 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store' });
    next();
  });

  const wrap = (fn) => (req, res, next) => {
    Promise.resolve().then(() => fn(req, res)).then((out) => {
      if (out !== undefined && !res.headersSent) res.json(out);
    }).catch(next);
  };
  // El token de la app es el token de cliente de COREDB; COREDB lo valida en cada llamada.
  function sesion(req, res, next) {
    const token = (req.get('Authorization') || '').replace(/^Bearer\s+/i, '').trim();
    if (!token) return next(new AppError(401, SESION_VENCIDA));
    req.tokenCliente = token;
    return next();
  }
  const cliente = (req, metodo, ruta, opciones = {}) =>
    coredb.llamar(metodo, B + ruta, { ...opciones, tokenCliente: req.tokenCliente });

  // ================= SALUD =================
  app.get('/api/salud', wrap(async () => ({ ok: true, servicio: 'chaski-api', hora: new Date().toISOString(),
    coredb: await coredb.salud() })));
  // Lista para recibir tráfico solo si llega a COREDB por el Bus.
  app.get('/api/listo', wrap(async (req, res) => {
    const ok = await coredb.salud();
    res.status(ok ? 200 : 503);
    return { ok };
  }));

  // ================= ACCESO =================
  // Punto R-01: el cliente lo registra el módulo Clientes y lo afilia el banco.
  app.post('/api/registro', wrap(async () => {
    throw new AppError(403, 'La billetera se activa en una agencia del BNA con tu DNI: ahí registran tu celular y tu PIN.');
  }));

  app.post('/api/login', wrap(async (req) => {
    const r = await coredb.llamar('POST', `${B}/acceso`, { cuerpo: { celular: celular(req.body.celular), pin: pin(req.body.pin) } });
    return { token: r.access_token, expira_en: r.expires_in, cliente: r.cliente };
  }));

  // Confirma el PIN antes de una operación cuando el celular no tiene biometría.
  app.post('/api/pin/verificar', sesion, wrap(async (req) => {
    await cliente(req, 'POST', '/pin/verificacion', { cuerpo: { pin: pin(req.body.pin) } });
    return { ok: true };
  }));

  // ================= SALDO E HISTORIAL =================
  app.get('/api/me', sesion, wrap(async (req) => {
    const yo = await cliente(req, 'GET', '/yo');
    return {
      cliente: { id_cliente: yo.cod_cliente, nombres: yo.nombre_corto, apellidos: '', nombre_corto: yo.nombre_corto },
      cuenta: { id_cuenta: yo.num_cuenta, numero_cuenta_virtual: yo.num_cuenta, saldo_actual: num(yo.saldo_disponible),
        moneda: 'PEN' },
      no_leidas: yo.notificaciones_sin_leer,
      pendientes: yo.solicitudes_pendientes,
      limite: MAX_OPERACION,
      tope_diario: num(yo.tope_diario),
      disponible_hoy: num(yo.disponible_hoy),
    };
  }));

  app.get('/api/movimientos', sesion, wrap(async (req) =>
    (await cliente(req, 'GET', '/movimientos?limite=60')).map((m) => ({
      id_movimiento: m.uuid_transaccion,
      tipo_movimiento: m.tipo_operacion.toLowerCase(),
      monto: (m.naturaleza === 'D' ? -1 : 1) * Number(m.monto),
      fecha_hora: m.fecha_hora,
      descripcion: m.glosa,
      canal: m.id_canal,
    }))));

  app.get('/api/operaciones', sesion, wrap(async (req) =>
    (await cliente(req, 'GET', '/operaciones?limite=60')).map((o) => ({ ...operacion(o), sentido: o.sentido.toLowerCase() }))));

  // ================= CONTACTOS =================
  // El celular va en el cuerpo, nunca en la ruta ni en la consulta: el Bus y los servidores
  // registran las rutas con su consulta.
  app.post('/api/clientes/buscar', sesion, wrap(async (req) => {
    const c = celular(req.body && req.body.celular);
    const r = await cliente(req, 'POST', '/contactos', { cuerpo: { celular: c } });
    return { celular: c, nombre: r.nombre };
  }));
  // COREDB no devuelve celulares de otros clientes: los contactos recientes quedan en la app.
  app.get('/api/recientes', sesion, wrap(async () => []));

  // ================= TRANSFERENCIAS P2P =================
  app.post('/api/transferencias', sesion, wrap(async (req) => {
    const cuerpo = { celular_destino: celular(req.body.celular_destino), monto: monto(req.body.monto) };
    const referencia = texto(req.body.referencia, 100);
    if (referencia) cuerpo.referencia = referencia;
    return operacion(await cliente(req, 'POST', '/transferencias', { cuerpo, llave: llave(req) }));
  }));

  // ================= SOLICITUDES DE COBRO =================
  app.post('/api/solicitudes', sesion, wrap(async (req) => {
    const cuerpo = { celular: celular(req.body.celular), monto: monto(req.body.monto) };
    const concepto = texto(req.body.concepto, 100);
    if (concepto) cuerpo.concepto = concepto;
    const s = await cliente(req, 'POST', '/solicitudes', { cuerpo });
    return { id_solicitud: s.id_solicitud, monto: num(s.monto), destinatario: s.nombre_pagador,
      fecha_hora: s.fecha_solicitud, referencia: s.concepto };
  }));

  app.get('/api/solicitudes', sesion, wrap(async (req) => {
    const r = await cliente(req, 'GET', '/solicitudes');
    return { recibidas: r.recibidas.map((s) => solicitud(s, s.nombre_solicitante)),
      enviadas: r.enviadas.map((s) => solicitud(s, s.nombre_pagador)) };
  }));

  app.post('/api/solicitudes/:id/responder', sesion, wrap(async (req) => {
    const accion = { aceptar: 'ACEPTAR', rechazar: 'RECHAZAR', cancelar: 'CANCELAR' }[req.body.accion];
    if (!accion) throw new AppError(400, 'Acción inválida');
    const r = await cliente(req, 'POST', `/solicitudes/${uuidRuta(req.params.id)}/respuesta`,
      { cuerpo: { accion }, llave: accion === 'ACEPTAR' ? llave(req) : undefined });
    return { ok: true, estado: ESTADO_SOLICITUD[r.estado] || r.estado.toLowerCase(),
      ...(r.operacion ? operacion(r.operacion) : {}) };
  }));

  // ================= QR =================
  app.post('/api/qr', sesion, wrap(async (req) => {
    const cuerpo = req.body && req.body.monto ? { monto: monto(req.body.monto) } : {};
    return qr(await cliente(req, 'POST', '/qr', { cuerpo }));
  }));

  app.get('/api/qr/:id', sesion, wrap(async (req) => {
    const q = await cliente(req, 'GET', `/qr/${uuidRuta(req.params.id)}`);
    if (q.estado === 'VENCIDO') throw new AppError(410, 'Este código QR venció');
    if (q.estado !== 'ACTIVO') throw new AppError(410, 'Este código QR ya no está vigente');
    return qr(q);
  }));

  app.get('/api/comercios', sesion, wrap(async (req) =>
    (await cliente(req, 'GET', '/comercios')).map((c) => ({ id_comercio: c.id_comercio, nombre: c.razon_social, id_qr: c.id_qr }))));

  app.post('/api/qr/:id/pagar', sesion, wrap(async (req) => {
    const cuerpo = req.body && req.body.monto !== undefined && req.body.monto !== null ? { monto: monto(req.body.monto) } : {};
    const o = await cliente(req, 'POST', `/qr/${uuidRuta(req.params.id)}/pagos`, { cuerpo, llave: llave(req) });
    return { ...operacion(o), ahorro: 0 };
  }));

  // ================= NOTIFICACIONES =================
  app.get('/api/notificaciones', sesion, wrap(async (req) =>
    (await cliente(req, 'GET', '/notificaciones')).map((n) => ({ id_notificacion: n.id_notificacion, tipo: n.tipo.toLowerCase(),
      mensaje: n.mensaje, estado_envio: n.leida ? 'leido' : 'pendiente', fecha_hora: n.fecha_hora }))));

  app.post('/api/notificaciones/leidas', sesion, wrap(async (req) => {
    await cliente(req, 'POST', '/notificaciones/leidas');
    return { ok: true };
  }));

  // ================= FUERA DE ESTA VERSIÓN =================
  // Listas vacías para que la app cargue; las acciones responden 501.
  app.get('/api/promos', sesion, wrap(async () => []));
  app.get('/api/ofertas', sesion, wrap(async () => []));
  app.get('/api/servicios/catalogo', sesion, wrap(async () => ({ operadores: [], montos: [], servicios: [] })));
  const noDisponible = wrap(async () => {
    throw new AppError(501, 'No disponible en esta versión de la billetera');
  });
  app.post('/api/promos/:id/cupon', sesion, noDisponible);
  app.get('/api/tienda', sesion, noDisponible);
  app.post('/api/tienda/comprar', sesion, noDisponible);
  app.get('/api/ordenes', sesion, noDisponible);
  app.post('/api/recargas', sesion, noDisponible);
  app.post('/api/servicios/consultar', sesion, noDisponible);
  app.post('/api/servicios/pagar', sesion, noDisponible);

  app.get('/', (req, res) => res.type('text').send('API Chaski en línea. La app móvil (Flutter) consume /api/*'));
  app.use('/api', (req, res) => res.status(404).json({ error: 'Ruta no encontrada' }));

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    if (err && err.type === 'entity.parse.failed') return res.status(400).json({ error: 'JSON inválido' });
    const [status, mensaje] = traducir(err);
    // Solo el código: nunca el cuerpo, la consulta ni el token.
    if (status >= 500) console.error(`chaski: ${req.method} ${req.route ? req.route.path : '-'} -> ${status} ${err.code || err.name}`);
    return res.status(status).json({ error: mensaje });
  });
  return app;
}

function configuracion(entorno = process.env) {
  const faltan = ['COREDB_URL', 'BUS_TOKEN', 'CHASKI_COREDB_USUARIO', 'CHASKI_COREDB_SECRETO'].filter((n) => !entorno[n]);
  if (faltan.length) throw new Error(`Faltan variables de entorno: ${faltan.join(', ')}`);
  return { url: entorno.COREDB_URL, busToken: entorno.BUS_TOKEN, usuario: entorno.CHASKI_COREDB_USUARIO,
    secreto: entorno.CHASKI_COREDB_SECRETO, puerto: Number(entorno.PORT || 3000) };
}

if (require.main === module) {
  const c = configuracion();
  crearApp({ coredb: crearCliente(c) }).listen(c.puerto, '0.0.0.0', () => {
    console.log(`API Chaski en el puerto ${c.puerto}, COREDB por el Bus`);
  });
}

module.exports = { crearApp, configuracion, MAX_OPERACION };
