const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { pool, tx, one, all, r2, AppError, checkPin, crearCliente, cuentaDeCliente, consumidoHoy, moverSaldo, notificar, init } = require('./db');

const PORT = process.env.PORT || 3000;
const MAX_OPERACION = 500; // límite por operación (S/)
const TOPE_DIARIO = 500; // tope acumulado diario por cliente (RN-TOP-001)
const HORAS_SOLICITUD = 48; // una solicitud de cobro sin respuesta expira (CUS-BD-002 FA-02)
const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '20kb' }));
app.use((req, res, next) => {
  res.set({ 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store' });
  next();
});

// ---- token firmado (HMAC) ----
const secretFile = path.join(__dirname, '.secret');
if (!process.env.CHASKI_SECRET && !fs.existsSync(secretFile)) fs.writeFileSync(secretFile, crypto.randomBytes(32).toString('hex'), { mode: 0o600 });
const SECRET = process.env.CHASKI_SECRET || fs.readFileSync(secretFile, 'utf8');
const b64 = (b) => Buffer.from(b).toString('base64url');
function firmar(id) {
  const body = b64(JSON.stringify({ id, exp: Date.now() + 1000 * 60 * 60 * 12 }));
  return body + '.' + crypto.createHmac('sha256', SECRET).update(body).digest('base64url');
}
function verificar(t) {
  const [body, sig] = (t || '').split('.');
  if (!body || !sig) return null;
  const esperado = crypto.createHmac('sha256', SECRET).update(body).digest();
  const dado = Buffer.from(sig, 'base64url');
  if (dado.length !== esperado.length || !crypto.timingSafeEqual(dado, esperado)) return null;
  const p = JSON.parse(Buffer.from(body, 'base64url').toString());
  return p.exp > Date.now() ? p.id : null;
}

const wrap = (fn) => (req, res, next) => {
  Promise.resolve()
    .then(() => fn(req, res))
    .then((out) => { if (out !== undefined) res.json(out); })
    .catch(next);
};
function auth(req, res, next) {
  (async () => {
    const id = verificar((req.headers.authorization || '').replace('Bearer ', ''));
    if (!id) throw new AppError(401, 'Sesión vencida. Inicia sesión otra vez.');
    const c = await one(pool, 'SELECT * FROM cliente WHERE id_cliente=$1', [id]);
    if (!c || c.estado !== 'activo') throw new AppError(403, 'Cuenta no disponible');
    req.cliente = c;
    req.cuenta = await cuentaDeCliente(pool, id);
  })().then(() => next(), next);
}

// ---- bloqueo por intentos fallidos ----
const intentos = new Map();
function chequearBloqueo(k) {
  const i = intentos.get(k);
  if (i && i.n >= 5 && Date.now() < i.hasta) throw new AppError(429, 'Demasiados intentos. Espera 5 minutos.');
}
function falla(k) {
  const i = intentos.get(k) || { n: 0 };
  i.n++;
  i.hasta = Date.now() + 5 * 60 * 1000;
  intentos.set(k, i);
}

const str = (v, max = 100) => (typeof v === 'string' ? v.trim().slice(0, max) : '');
function montoValido(m) {
  const n = Number(m);
  if (!Number.isFinite(n) || n <= 0) throw new AppError(400, 'Ingresa un monto válido');
  if (n > MAX_OPERACION) throw new AppError(400, `El límite por operación es S/ ${MAX_OPERACION}`);
  return r2(n);
}
const nombreCorto = (c) => `${c.nombres.split(' ')[0]} ${c.apellidos.split(' ')[0][0]}.`;
const nombreCompleto = (c) => `${c.nombres} ${c.apellidos}`;
const soles = (n) => 'S/ ' + Number(n).toFixed(2);
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// ---- auditoría (INT-13): log de toda operación de dinero, exitosa o rechazada ----
function auditar(id_cliente, operacion, resultado, detalle, uuid) {
  pool.query('INSERT INTO auditoria (id_cliente,operacion,resultado,detalle,uuid_transaccion) VALUES ($1,$2,$3,$4,$5)',
    [id_cliente, operacion, resultado, String(detalle || '').slice(0, 300), uuid || null]).catch((e) => console.error('auditoría:', e.message));
}

// Operación de dinero: transacción ACID + idempotencia por uuidTransaccion (RN-BUS-002) + auditoría.
// Si la app reintenta con el mismo uuid (p. ej. por una caída de red), se devuelve la respuesta original sin volver a cobrar.
async function operacionDinero(req, operacion, fn) {
  const uuid = str(req.get('Idempotency-Key') || req.body.uuid_transaccion, 36) || null;
  if (uuid && !UUID_RE.test(uuid)) throw new AppError(400, 'uuid_transaccion inválido');
  const idc = req.cliente.id_cliente;
  try {
    if (uuid) {
      const prev = await one(pool, 'SELECT id_cliente, respuesta FROM operacion_idempotente WHERE uuid_transaccion=$1', [uuid]);
      if (prev) {
        if (prev.id_cliente !== idc) throw new AppError(409, 'Operación duplicada');
        return { ...prev.respuesta, repetida: true };
      }
    }
    const r = await tx(async (c) => {
      const out = await fn(c);
      if (uuid) await c.query('INSERT INTO operacion_idempotente (uuid_transaccion,id_cliente,operacion,respuesta) VALUES ($1,$2,$3,$4)', [uuid, idc, operacion, out]);
      return out;
    });
    auditar(idc, operacion, 'exitosa', `${soles(r.monto || 0)} · ${r.destinatario || ''}`, uuid);
    return r;
  } catch (e) {
    if (uuid && e.code === '23505' && e.constraint === 'operacion_idempotente_pkey') {
      const prev = await one(pool, 'SELECT respuesta FROM operacion_idempotente WHERE uuid_transaccion=$1', [uuid]);
      if (prev) return { ...prev.respuesta, repetida: true };
    }
    auditar(idc, operacion, 'rechazada', e instanceof AppError ? e.message : 'error interno', uuid);
    throw e;
  }
}

async function expirarSolicitudes() {
  await pool.query(`UPDATE solicitud_cobro SET estado='expirada', fecha_respuesta=now()
    WHERE estado='pendiente' AND fecha_solicitud < now() - make_interval(hours => $1)`, [HORAS_SOLICITUD]);
}

// ================= SALUD =================
app.get('/api/salud', wrap(async () => {
  await pool.query('SELECT 1');
  return { ok: true, servicio: 'chaski-api', hora: new Date().toISOString() };
}));

// ================= AUTH / ENROLAMIENTO (RF-BD-005) =================
app.post('/api/registro', wrap(async (req) => {
  const b = req.body;
  const d = {
    tipo_documento: str(b.tipo_documento, 20) || 'DNI',
    numero_documento: str(b.numero_documento, 20),
    nombres: str(b.nombres),
    apellidos: str(b.apellidos),
    celular: str(b.celular, 20),
    email: str(b.email, 150),
    pin: str(b.pin, 6),
  };
  if (d.tipo_documento !== 'DNI') throw new AppError(400, 'Solo se permite DNI');
  if (!/^\d{8}$/.test(d.numero_documento)) throw new AppError(400, 'El DNI debe tener 8 dígitos');
  if (!d.nombres || !d.apellidos) throw new AppError(400, 'Ingresa tus nombres y apellidos');
  if (!/^9\d{8}$/.test(d.celular)) throw new AppError(400, 'El celular debe tener 9 dígitos y empezar con 9');
  if (d.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email)) throw new AppError(400, 'El correo no es válido');
  if (!/^\d{6}$/.test(d.pin)) throw new AppError(400, 'El PIN debe tener 6 dígitos');
  if (b.acepta_terminos !== true) throw new AppError(400, 'Debes aceptar los términos y condiciones');
  if (await one(pool, 'SELECT 1 FROM cliente WHERE celular=$1', [d.celular])) throw new AppError(409, 'Ese celular ya está registrado');
  if (await one(pool, 'SELECT 1 FROM cliente WHERE tipo_documento=$1 AND numero_documento=$2', [d.tipo_documento, d.numero_documento]))
    throw new AppError(409, 'Ese documento ya está registrado');
  const { id_cliente } = await tx((c) => crearCliente(c, d, 100)); // S/ 100 de saldo demo
  auditar(id_cliente, 'enrolamiento', 'exitosa', `Celular ${d.celular} vinculado`);
  return { token: firmar(id_cliente) };
}));

app.post('/api/login', wrap(async (req) => {
  const cel = str(req.body.celular, 20);
  const pin = str(req.body.pin, 6);
  chequearBloqueo(cel);
  const c = await one(pool, 'SELECT * FROM cliente WHERE celular=$1', [cel]);
  const cred = c && (await one(pool, 'SELECT pin_hash FROM credencial WHERE id_cliente=$1', [c.id_cliente]));
  if (!c || !cred || !/^\d{6}$/.test(pin) || !checkPin(pin, cred.pin_hash)) {
    falla(cel);
    throw new AppError(401, 'Celular o PIN incorrecto');
  }
  if (c.estado !== 'activo') throw new AppError(403, 'Tu cuenta está bloqueada');
  intentos.delete(cel);
  return { token: firmar(c.id_cliente) };
}));

// Verifica el PIN para autorizar una operación cuando el celular no tiene biometría
app.post('/api/pin/verificar', auth, wrap(async (req) => {
  const k = 'op:' + req.cliente.id_cliente;
  chequearBloqueo(k);
  const cred = await one(pool, 'SELECT pin_hash FROM credencial WHERE id_cliente=$1', [req.cliente.id_cliente]);
  const pin = str(req.body.pin, 6);
  if (!/^\d{6}$/.test(pin) || !checkPin(pin, cred.pin_hash)) { falla(k); throw new AppError(401, 'PIN incorrecto'); }
  intentos.delete(k);
  return { ok: true };
}));

// ================= SALDO E HISTORIAL (RF-BD-004) =================
app.get('/api/me', auth, wrap(async (req) => {
  await expirarSolicitudes();
  const idc = req.cliente.id_cliente;
  const usado = await consumidoHoy(pool, req.cuenta.id_cuenta);
  return {
    cliente: { id_cliente: idc, nombres: req.cliente.nombres, apellidos: req.cliente.apellidos, celular: req.cliente.celular, email: req.cliente.email, numero_documento: req.cliente.numero_documento, tipo_documento: req.cliente.tipo_documento },
    cuenta: { id_cuenta: req.cuenta.id_cuenta, numero_cuenta_virtual: req.cuenta.numero_cuenta_virtual, saldo_actual: req.cuenta.saldo_actual, moneda: req.cuenta.moneda, fecha_apertura: req.cuenta.fecha_apertura },
    no_leidas: (await one(pool, "SELECT COUNT(*)::int n FROM notificacion WHERE id_cliente=$1 AND estado_envio<>'leido'", [idc])).n,
    pendientes: (await one(pool, "SELECT COUNT(*)::int n FROM solicitud_cobro WHERE id_cliente_solicitado=$1 AND estado='pendiente'", [idc])).n,
    limite: MAX_OPERACION,
    tope_diario: TOPE_DIARIO,
    disponible_hoy: r2(Math.max(0, TOPE_DIARIO - usado)),
  };
}));

app.get('/api/movimientos', auth, wrap((req) =>
  all(pool, `SELECT id_movimiento,tipo_movimiento,monto,saldo_resultante,fecha_hora,descripcion,id_transferencia,id_pago,id_solicitud,id_orden,id_pago_servicio
    FROM movimiento WHERE id_cuenta=$1 ORDER BY id_movimiento DESC LIMIT 60`, [req.cuenta.id_cuenta])
));

// ================= CONTACTOS (INT-10) =================
app.get('/api/clientes/buscar', auth, wrap(async (req) => {
  const cel = str(req.query.celular, 20);
  const c = await one(pool, "SELECT * FROM cliente WHERE celular=$1 AND estado='activo'", [cel]);
  if (!c) throw new AppError(404, 'El número ingresado no está registrado en Chaski');
  if (c.id_cliente === req.cliente.id_cliente) throw new AppError(400, 'No puedes usar tu propio número');
  return { celular: c.celular, nombre: nombreCorto(c) };
}));

app.get('/api/recientes', auth, wrap(async (req) => {
  const rows = await all(pool, `
    SELECT c.celular, c.nombres, c.apellidos, MAX(t.id_transferencia) AS ult FROM transferencia t
    JOIN cuenta co ON co.id_cuenta = CASE WHEN t.id_cuenta_origen=$1 THEN t.id_cuenta_destino ELSE t.id_cuenta_origen END
    JOIN cliente c ON c.id_cliente = co.id_cliente
    WHERE (t.id_cuenta_origen=$1 OR t.id_cuenta_destino=$1) AND c.tipo_documento<>'RUC'
    GROUP BY c.celular, c.nombres, c.apellidos ORDER BY ult DESC LIMIT 8`, [req.cuenta.id_cuenta]);
  return rows.map((c) => ({ celular: c.celular, nombre: nombreCorto(c) }));
}));

// ================= TRANSFERENCIAS P2P (RF-BD-001) =================
async function ejecutarTransferencia(c, { origen, destino, monto, referencia, id_solicitud = null }) {
  const { saldoOrigen, saldoDestino } = await moverSaldo(c, origen.cuenta.id_cuenta, destino.cuenta.id_cuenta, monto, TOPE_DIARIO);
  const t = await one(c, "INSERT INTO transferencia (id_cuenta_origen,id_cuenta_destino,monto,estado,referencia) VALUES ($1,$2,$3,'completada',$4) RETURNING id_transferencia, fecha_hora",
    [origen.cuenta.id_cuenta, destino.cuenta.id_cuenta, monto, referencia || null]);
  const ins = 'INSERT INTO movimiento (id_cuenta,tipo_movimiento,id_transferencia,id_solicitud,monto,saldo_resultante,descripcion) VALUES ($1,$2,$3,$4,$5,$6,$7)';
  await c.query(ins, [origen.cuenta.id_cuenta, 'transferencia_enviada', t.id_transferencia, id_solicitud, -monto, saldoOrigen, `Enviaste a ${nombreCorto(destino.cliente)}`]);
  await c.query(ins, [destino.cuenta.id_cuenta, 'transferencia_recibida', t.id_transferencia, id_solicitud, monto, saldoDestino, `${nombreCorto(origen.cliente)} te envió dinero`]);
  await notificar(c, destino.cliente.id_cliente, 'transferencia_recibida', `${nombreCorto(origen.cliente)} te envió ${soles(monto)}${referencia ? ' · ' + referencia : ''}`);
  await notificar(c, origen.cliente.id_cliente, 'transferencia_enviada', `Enviaste ${soles(monto)} a ${nombreCorto(destino.cliente)}`);
  return { id_transferencia: t.id_transferencia, fecha_hora: t.fecha_hora, saldo: saldoOrigen };
}
const partes = async (c, cliente) => ({ cliente, cuenta: await cuentaDeCliente(c, cliente.id_cliente) });

app.post('/api/transferencias', auth, wrap(async (req) => {
  const monto = montoValido(req.body.monto);
  const dest = await one(pool, "SELECT * FROM cliente WHERE celular=$1 AND estado='activo'", [str(req.body.celular_destino, 20)]);
  if (!dest) throw new AppError(404, 'El número ingresado no está registrado en Chaski');
  if (dest.id_cliente === req.cliente.id_cliente) throw new AppError(400, 'No puedes enviarte dinero a ti mismo');
  const referencia = str(req.body.referencia, 100);
  return operacionDinero(req, 'transferencia', async (c) => {
    const r = await ejecutarTransferencia(c, { origen: await partes(c, req.cliente), destino: await partes(c, dest), monto, referencia });
    return { ...r, monto, destinatario: nombreCompleto(dest), referencia };
  });
}));

// ================= SOLICITUDES DE COBRO (RF-BD-002) =================
app.post('/api/solicitudes', auth, wrap(async (req) => {
  const monto = montoValido(req.body.monto);
  const dest = await one(pool, "SELECT * FROM cliente WHERE celular=$1 AND estado='activo'", [str(req.body.celular, 20)]);
  if (!dest) throw new AppError(404, 'El número ingresado no está registrado en Chaski');
  if (dest.id_cliente === req.cliente.id_cliente) throw new AppError(400, 'No puedes cobrarte a ti mismo');
  const concepto = str(req.body.concepto, 150);
  return tx(async (c) => {
    const s = await one(c, 'INSERT INTO solicitud_cobro (id_cliente_solicitante,id_cliente_solicitado,monto,concepto) VALUES ($1,$2,$3,$4) RETURNING id_solicitud, fecha_solicitud',
      [req.cliente.id_cliente, dest.id_cliente, monto, concepto || null]);
    await notificar(c, dest.id_cliente, 'solicitud_cobro', `${nombreCorto(req.cliente)} te pide ${soles(monto)}${concepto ? ' · ' + concepto : ''}`);
    return { id_solicitud: s.id_solicitud, monto, destinatario: nombreCompleto(dest), fecha_hora: s.fecha_solicitud, referencia: concepto };
  });
}));

app.get('/api/solicitudes', auth, wrap(async (req) => {
  await expirarSolicitudes();
  const q = (col, me) => `SELECT s.*, c.nombres, c.apellidos, c.celular FROM solicitud_cobro s JOIN cliente c ON c.id_cliente = s.${col}
    WHERE s.${me}=$1 ORDER BY s.id_solicitud DESC LIMIT 30`;
  const recibidas = await all(pool, q('id_cliente_solicitante', 'id_cliente_solicitado'), [req.cliente.id_cliente]);
  const enviadas = await all(pool, q('id_cliente_solicitado', 'id_cliente_solicitante'), [req.cliente.id_cliente]);
  const f = (s) => ({ id_solicitud: s.id_solicitud, monto: s.monto, concepto: s.concepto, estado: s.estado, fecha: s.fecha_solicitud, nombre: nombreCorto(s), celular: s.celular });
  return { recibidas: recibidas.map(f), enviadas: enviadas.map(f) };
}));

app.post('/api/solicitudes/:id/responder', auth, wrap(async (req) => {
  const accion = req.body.accion;
  if (!['aceptar', 'rechazar', 'cancelar'].includes(accion)) throw new AppError(400, 'Acción inválida');
  await expirarSolicitudes();
  const run = async (c) => {
    const s = await one(c, 'SELECT * FROM solicitud_cobro WHERE id_solicitud=$1 FOR UPDATE', [Number(req.params.id) || 0]);
    if (!s || s.estado !== 'pendiente') throw new AppError(404, 'La solicitud ya no está disponible');
    if (accion === 'cancelar') {
      if (s.id_cliente_solicitante !== req.cliente.id_cliente) throw new AppError(403, 'No permitido');
      await c.query("UPDATE solicitud_cobro SET estado='cancelada', fecha_respuesta=now() WHERE id_solicitud=$1", [s.id_solicitud]);
      return { ok: true };
    }
    if (s.id_cliente_solicitado !== req.cliente.id_cliente) throw new AppError(403, 'No permitido');
    const solicitante = await one(c, 'SELECT * FROM cliente WHERE id_cliente=$1', [s.id_cliente_solicitante]);
    if (accion === 'rechazar') {
      await c.query("UPDATE solicitud_cobro SET estado='rechazada', fecha_respuesta=now() WHERE id_solicitud=$1", [s.id_solicitud]);
      await notificar(c, solicitante.id_cliente, 'solicitud_respondida', `${nombreCorto(req.cliente)} rechazó tu solicitud de ${soles(s.monto)}`);
      return { ok: true };
    }
    const r = await ejecutarTransferencia(c, { origen: await partes(c, req.cliente), destino: await partes(c, solicitante), monto: s.monto, referencia: s.concepto, id_solicitud: s.id_solicitud });
    await c.query("UPDATE solicitud_cobro SET estado='aceptada', fecha_respuesta=now(), id_transferencia=$1 WHERE id_solicitud=$2", [r.id_transferencia, s.id_solicitud]);
    await notificar(c, solicitante.id_cliente, 'solicitud_respondida', `${nombreCorto(req.cliente)} pagó tu solicitud de ${soles(s.monto)}`);
    return { ok: true, ...r, monto: s.monto, destinatario: nombreCompleto(solicitante), referencia: s.concepto };
  };
  return accion === 'aceptar' ? operacionDinero(req, 'pago_solicitud', run) : tx(run);
}));

// ================= QR (RF-BD-003) =================
async function promoDeComercio(c, id_comercio) {
  return (await one(c, `SELECT id_promocion, titulo, porcentaje, tope_descuento FROM promocion
    WHERE id_comercio=$1 AND estado='activo' AND fecha_inicio<=now() AND fecha_fin>now() ORDER BY porcentaje DESC LIMIT 1`, [id_comercio])) || null;
}
const calcDescuento = (base, promo) => (promo ? r2(Math.min((base * promo.porcentaje) / 100, promo.tope_descuento ?? Infinity)) : 0);

async function infoQR(c, qr) {
  let nombre, esComercio = false;
  if (qr.id_comercio) {
    nombre = (await one(c, 'SELECT razon_social FROM comercio WHERE id_comercio=$1', [qr.id_comercio])).razon_social;
    esComercio = true;
  } else {
    nombre = nombreCompleto(await one(c, 'SELECT c.* FROM cliente c JOIN cuenta u ON u.id_cliente=c.id_cliente WHERE u.id_cuenta=$1', [qr.id_cuenta]));
  }
  const p = qr.id_comercio ? await promoDeComercio(c, qr.id_comercio) : null;
  return { id_qr: qr.id_qr, tipo: qr.tipo, monto: qr.monto, nombre, es_comercio: esComercio, fecha_expiracion: qr.fecha_expiracion,
    promo: p ? { titulo: p.titulo, porcentaje: p.porcentaje, tope: p.tope_descuento } : null };
}
async function qrVigente(c, id) {
  const qr = await one(c, "SELECT * FROM codigo_qr WHERE id_qr=$1 AND estado='activo'", [Number(id) || 0]);
  if (!qr) throw new AppError(404, 'Código QR no reconocido o no válido');
  if (qr.fecha_expiracion && new Date(qr.fecha_expiracion) < new Date()) throw new AppError(410, 'Este código QR venció');
  return qr;
}

app.post('/api/qr', auth, wrap(async (req) => {
  if (req.body.monto) {
    const monto = montoValido(req.body.monto);
    const r = await one(pool, "INSERT INTO codigo_qr (id_cuenta,tipo,monto,fecha_expiracion) VALUES ($1,'dinamico',$2, now() + interval '15 minutes') RETURNING id_qr, fecha_expiracion",
      [req.cuenta.id_cuenta, monto]);
    return { id_qr: r.id_qr, tipo: 'dinamico', monto, expira: r.fecha_expiracion };
  }
  let qr = await one(pool, "SELECT * FROM codigo_qr WHERE id_cuenta=$1 AND tipo='estatico' AND id_comercio IS NULL AND estado='activo'", [req.cuenta.id_cuenta]);
  if (!qr) qr = await one(pool, "INSERT INTO codigo_qr (id_cuenta,tipo) VALUES ($1,'estatico') RETURNING *", [req.cuenta.id_cuenta]);
  return { id_qr: qr.id_qr, tipo: 'estatico', monto: null };
}));

app.get('/api/qr/:id', auth, wrap(async (req) => infoQR(pool, await qrVigente(pool, req.params.id))));

app.get('/api/comercios', auth, wrap(() =>
  all(pool, "SELECT c.id_comercio, c.razon_social AS nombre, q.id_qr FROM comercio c JOIN codigo_qr q ON q.id_comercio=c.id_comercio WHERE c.estado='activo' AND q.tipo='estatico' AND q.estado='activo' ORDER BY c.razon_social")
));

app.post('/api/qr/:id/pagar', auth, wrap(async (req) => {
  const qr0 = await qrVigente(pool, req.params.id);
  const montoBase = qr0.tipo === 'dinamico' ? qr0.monto : montoValido(req.body.monto);
  return operacionDinero(req, 'pago_qr', async (c) => {
    const qr = await one(c, 'SELECT * FROM codigo_qr WHERE id_qr=$1 FOR UPDATE', [qr0.id_qr]);
    const idDestino = qr.id_comercio ? (await one(c, 'SELECT id_cuenta FROM comercio WHERE id_comercio=$1', [qr.id_comercio])).id_cuenta : qr.id_cuenta;
    if (idDestino === req.cuenta.id_cuenta) throw new AppError(400, 'No puedes pagar a tu propio QR');
    if (qr.tipo === 'dinamico' && (await one(c, "SELECT 1 FROM pago_qr WHERE id_qr=$1 AND estado='completado'", [qr.id_qr])))
      throw new AppError(409, 'Este QR ya fue pagado');
    const info = await infoQR(c, qr);
    const promo = qr.id_comercio ? await promoDeComercio(c, qr.id_comercio) : null;
    const descuento = calcDescuento(montoBase, promo);
    const pagar = r2(montoBase - descuento);
    if (pagar <= 0) throw new AppError(400, 'Ingresa un monto válido');
    const { saldoOrigen, saldoDestino } = await moverSaldo(c, req.cuenta.id_cuenta, idDestino, pagar, TOPE_DIARIO);
    const p = await one(c, "INSERT INTO pago_qr (id_qr,id_cuenta_origen,monto,estado) VALUES ($1,$2,$3,'completado') RETURNING id_pago, fecha_hora",
      [qr.id_qr, req.cuenta.id_cuenta, pagar]);
    const ins = 'INSERT INTO movimiento (id_cuenta,tipo_movimiento,id_pago,monto,saldo_resultante,descripcion) VALUES ($1,$2,$3,$4,$5,$6)';
    await c.query(ins, [req.cuenta.id_cuenta, 'pago_qr', p.id_pago, -pagar, saldoOrigen, `Pagaste a ${info.nombre}${descuento ? ` (promo −${soles(descuento)})` : ''}`]);
    await c.query(ins, [idDestino, 'cobro_qr', p.id_pago, pagar, saldoDestino, `Cobro QR de ${nombreCorto(req.cliente)}`]);
    const dueno = (await one(c, 'SELECT id_cliente FROM cuenta WHERE id_cuenta=$1', [idDestino])).id_cliente;
    await notificar(c, dueno, 'pago_qr_recibido', `${nombreCorto(req.cliente)} te pagó ${soles(pagar)} con QR`);
    await notificar(c, req.cliente.id_cliente, 'pago_qr', `Pagaste ${soles(pagar)} a ${info.nombre}`);
    return { id_pago: p.id_pago, monto: pagar, ahorro: descuento, destinatario: info.nombre, fecha_hora: p.fecha_hora, saldo: saldoOrigen };
  });
}));

// ================= NOTIFICACIONES (RF-BD-009) =================
app.get('/api/notificaciones', auth, wrap((req) =>
  all(pool, 'SELECT id_notificacion,tipo,mensaje,estado_envio,fecha_hora FROM notificacion WHERE id_cliente=$1 ORDER BY id_notificacion DESC LIMIT 40', [req.cliente.id_cliente])
));
app.post('/api/notificaciones/leidas', auth, wrap(async (req) => {
  await pool.query("UPDATE notificacion SET estado_envio='leido' WHERE id_cliente=$1 AND estado_envio<>'leido'", [req.cliente.id_cliente]);
  return { ok: true };
}));

// ================= PROMOS Y CUPONES (RF-BD-007) =================
app.get('/api/promos', auth, wrap((req) =>
  all(pool, `SELECT pr.id_promocion, pr.titulo, pr.descripcion, pr.porcentaje, pr.tope_descuento AS tope, pr.fecha_fin, c.id_comercio, c.razon_social AS tienda,
      (SELECT id_qr FROM codigo_qr WHERE id_comercio = c.id_comercio AND tipo = 'estatico' AND estado = 'activo' LIMIT 1) AS id_qr,
      (SELECT emoji FROM producto WHERE id_comercio = c.id_comercio ORDER BY id_producto LIMIT 1) AS emoji,
      EXISTS (SELECT 1 FROM producto WHERE id_comercio = c.id_comercio AND estado = 'activo' AND stock > 0) AS tiene_tienda,
      (SELECT codigo FROM cupon WHERE id_promocion = pr.id_promocion AND id_cliente = $1 AND estado = 'vigente') AS cupon
    FROM promocion pr JOIN comercio c ON c.id_comercio = pr.id_comercio AND c.estado = 'activo'
    WHERE pr.estado = 'activo' AND pr.fecha_inicio <= now() AND pr.fecha_fin > now() ORDER BY pr.porcentaje DESC`, [req.cliente.id_cliente])
));

const codigoAleatorio = (n) => Array.from({ length: n }, () => 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'[crypto.randomInt(0, 32)]).join('');

app.post('/api/promos/:id/cupon', auth, wrap(async (req) => {
  const p = await one(pool, `SELECT pr.id_promocion, pr.titulo, pr.porcentaje, pr.fecha_fin, c.razon_social AS tienda FROM promocion pr JOIN comercio c ON c.id_comercio=pr.id_comercio
    WHERE pr.id_promocion=$1 AND pr.estado='activo' AND pr.fecha_inicio<=now() AND pr.fecha_fin>now()`, [Number(req.params.id) || 0]);
  if (!p) throw new AppError(404, 'No hay promociones disponibles por el momento');
  const ex = await one(pool, 'SELECT codigo, fecha_generacion FROM cupon WHERE id_promocion=$1 AND id_cliente=$2', [p.id_promocion, req.cliente.id_cliente]);
  if (ex) return { ...p, codigo: ex.codigo, fecha_generacion: ex.fecha_generacion };
  for (let i = 0; i < 5; i++) {
    try {
      const r = await one(pool, 'INSERT INTO cupon (id_promocion,id_cliente,codigo) VALUES ($1,$2,$3) RETURNING codigo, fecha_generacion',
        [p.id_promocion, req.cliente.id_cliente, 'CHK-' + codigoAleatorio(6)]);
      return { ...p, codigo: r.codigo, fecha_generacion: r.fecha_generacion };
    } catch (e) {
      if (e.code !== '23505') throw e;
      const otra = await one(pool, 'SELECT codigo, fecha_generacion FROM cupon WHERE id_promocion=$1 AND id_cliente=$2', [p.id_promocion, req.cliente.id_cliente]);
      if (otra) return { ...p, codigo: otra.codigo, fecha_generacion: otra.fecha_generacion };
    }
  }
  throw new AppError(500, 'No pudimos generar el cupón');
}));

// ================= OFERTAS Y TIENDA (RF-BD-008) =================
const VISTA_PROD = `SELECT p.*, c.razon_social AS tienda,
    o.id_oferta, o.precio_oferta, o.stock_oferta, o.fecha_fin AS oferta_fin,
    pr.titulo AS promo_titulo, pr.porcentaje AS promo_pct, pr.tope_descuento AS promo_tope
  FROM producto p
  JOIN comercio c ON c.id_comercio = p.id_comercio AND c.estado = 'activo'
  LEFT JOIN oferta o ON o.id_oferta = (SELECT id_oferta FROM oferta WHERE id_producto = p.id_producto AND estado = 'activo' AND fecha_fin > now() AND stock_oferta > 0 ORDER BY precio_oferta LIMIT 1)
  LEFT JOIN promocion pr ON pr.id_promocion = (SELECT id_promocion FROM promocion WHERE id_comercio = p.id_comercio AND estado = 'activo' AND fecha_inicio <= now() AND fecha_fin > now() ORDER BY porcentaje DESC LIMIT 1)
  WHERE p.estado = 'activo' AND p.stock > 0`;
const mapProd = (x) => ({
  id_producto: x.id_producto, id_comercio: x.id_comercio, tienda: x.tienda, nombre: x.nombre, categoria: x.categoria, emoji: x.emoji,
  precio: x.precio, stock: x.stock,
  oferta: x.id_oferta ? { id: x.id_oferta, precio: x.precio_oferta, stock: Math.min(x.stock_oferta, x.stock), fin: x.oferta_fin, pct: Math.round((1 - x.precio_oferta / x.precio) * 100) } : null,
  promo: x.promo_pct ? { titulo: x.promo_titulo, porcentaje: x.promo_pct, tope: x.promo_tope } : null,
});
const productos = async (c, extra = '', params = []) => (await all(c, `${VISTA_PROD} ${extra}`, params)).map(mapProd);

app.get('/api/ofertas', auth, wrap(() =>
  productos(pool, 'AND o.id_oferta IS NOT NULL ORDER BY (1 - o.precio_oferta / p.precio) DESC')
));

app.get('/api/tienda', auth, wrap(async (req) => {
  const q = str(req.query.q, 40).replace(/[%_\\]/g, '');
  const idc = Number(req.query.comercio) || 0;
  let extra = '';
  const params = [];
  if (idc) { params.push(idc); extra += ` AND p.id_comercio = $${params.length}`; }
  if (q) { params.push(`%${q}%`); extra += ` AND (p.nombre ILIKE $${params.length} OR p.categoria ILIKE $${params.length} OR c.razon_social ILIKE $${params.length})`; }
  const tiendas = await all(pool, `SELECT c.id_comercio, c.razon_social AS nombre,
      (SELECT emoji FROM producto WHERE id_comercio = c.id_comercio ORDER BY id_producto LIMIT 1) AS emoji
    FROM comercio c WHERE c.estado = 'activo' AND EXISTS (SELECT 1 FROM producto WHERE id_comercio = c.id_comercio AND estado = 'activo' AND stock > 0) ORDER BY c.razon_social`);
  return { tiendas, productos: await productos(pool, extra + ' ORDER BY p.id_comercio, p.id_producto', params) };
}));

app.post('/api/tienda/comprar', auth, wrap(async (req) => {
  const items = Array.isArray(req.body.items) ? req.body.items : [];
  if (!items.length || items.length > 30) throw new AppError(400, 'Tu carrito está vacío');
  // Se ignoran precios del cliente: todo se recalcula aquí
  const pedido = new Map();
  for (const it of items) {
    const id = Number(it.id_producto), n = Math.floor(Number(it.cantidad));
    if (!id || !(n >= 1 && n <= 10)) throw new AppError(400, 'Cantidad inválida');
    pedido.set(id, Math.min(10, (pedido.get(id) || 0) + n));
  }
  return operacionDinero(req, 'compra_tienda', async (c) => {
    const porTienda = new Map();
    for (const [id, cant] of [...pedido].sort((a, b) => a[0] - b[0])) {
      await c.query('SELECT 1 FROM producto WHERE id_producto=$1 FOR UPDATE', [id]);
      const p = (await productos(c, 'AND p.id_producto = $1', [id]))[0];
      if (!p) throw new AppError(409, 'Un producto de tu carrito ya no está disponible');
      if (p.stock < cant) throw new AppError(409, `Solo quedan ${p.stock} de ${p.nombre}`);
      const uOferta = p.oferta ? Math.min(cant, p.oferta.stock) : 0;
      const lineas = [];
      if (uOferta) lineas.push({ id_producto: id, nombre: p.nombre, cantidad: uOferta, precio: p.oferta.precio, original: p.precio, oferta: true });
      if (cant - uOferta) lineas.push({ id_producto: id, nombre: p.nombre, cantidad: cant - uOferta, precio: p.precio, original: p.precio, oferta: false });
      const g = porTienda.get(p.id_comercio) || { id_comercio: p.id_comercio, tienda: p.tienda, lineas: [] };
      g.lineas.push(...lineas);
      porTienda.set(p.id_comercio, g);
      if (!(await c.query('UPDATE producto SET stock = stock - $1 WHERE id_producto = $2 AND stock >= $1', [cant, id])).rowCount)
        throw new AppError(409, `Solo quedan ${p.stock} de ${p.nombre}`);
      if (uOferta && !(await c.query('UPDATE oferta SET stock_oferta = stock_oferta - $1 WHERE id_oferta = $2 AND stock_oferta >= $1', [uOferta, p.oferta.id])).rowCount)
        throw new AppError(409, `La oferta de ${p.nombre} se agotó`);
    }
    let totalGeneral = 0, ahorroGeneral = 0, saldo = req.cuenta.saldo_actual;
    for (const g of porTienda.values()) {
      const subtotal = r2(g.lineas.reduce((a, l) => a + l.cantidad * l.precio, 0));
      const base = g.lineas.filter((l) => !l.oferta).reduce((a, l) => a + l.cantidad * l.precio, 0);
      const ahorroOferta = r2(g.lineas.filter((l) => l.oferta).reduce((a, l) => a + l.cantidad * (l.original - l.precio), 0));
      const descuento = calcDescuento(base, await promoDeComercio(c, g.id_comercio));
      g.subtotal = subtotal; g.descuento = descuento; g.total = r2(subtotal - descuento);
      totalGeneral = r2(totalGeneral + g.total);
      ahorroGeneral = r2(ahorroGeneral + descuento + ahorroOferta);
    }
    montoValido(totalGeneral);
    const ordenes = [];
    for (const g of porTienda.values()) {
      const cuentaTienda = (await one(c, 'SELECT id_cuenta FROM comercio WHERE id_comercio=$1', [g.id_comercio])).id_cuenta;
      const mv = await moverSaldo(c, req.cuenta.id_cuenta, cuentaTienda, g.total, TOPE_DIARIO);
      saldo = mv.saldoOrigen;
      const codigo = codigoAleatorio(6);
      const o = await one(c, 'INSERT INTO orden (id_cliente,id_comercio,subtotal,descuento,total,codigo_recojo) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id_orden',
        [req.cliente.id_cliente, g.id_comercio, g.subtotal, g.descuento, g.total, codigo]);
      for (const l of g.lineas) {
        await c.query('INSERT INTO orden_item (id_orden,id_producto,nombre,cantidad,precio_unitario) VALUES ($1,$2,$3,$4,$5)', [o.id_orden, l.id_producto, l.nombre, l.cantidad, l.precio]);
      }
      const ins = 'INSERT INTO movimiento (id_cuenta,tipo_movimiento,id_orden,monto,saldo_resultante,descripcion) VALUES ($1,$2,$3,$4,$5,$6)';
      await c.query(ins, [req.cuenta.id_cuenta, 'compra_tienda', o.id_orden, -g.total, mv.saldoOrigen, `Compra en ${g.tienda}`]);
      await c.query(ins, [cuentaTienda, 'venta_tienda', o.id_orden, g.total, mv.saldoDestino, `Pedido #${o.id_orden} de ${nombreCorto(req.cliente)}`]);
      const dueno = (await one(c, 'SELECT id_cliente FROM cuenta WHERE id_cuenta=$1', [cuentaTienda])).id_cliente;
      await notificar(c, dueno, 'venta_tienda', `${nombreCorto(req.cliente)} compró ${soles(g.total)} en tu tienda (pedido #${o.id_orden}, retiro ${codigo})`);
      ordenes.push({ id_orden: o.id_orden, tienda: g.tienda, total: g.total, descuento: g.descuento, codigo_recojo: codigo });
    }
    await notificar(c, req.cliente.id_cliente, 'compra_tienda', `Tu compra por ${soles(totalGeneral)} fue exitosa. Recoge tu pedido con el código ${ordenes.map((o) => o.codigo_recojo).join(', ')}`);
    return { ordenes, id_op: ordenes[0].id_orden, monto: totalGeneral, ahorro: ahorroGeneral, saldo, destinatario: ordenes.map((o) => o.tienda).join(' y '), fecha_hora: new Date().toISOString() };
  });
}));

app.get('/api/ordenes', auth, wrap(async (req) => {
  const os = await all(pool, 'SELECT o.*, c.razon_social AS tienda FROM orden o JOIN comercio c ON c.id_comercio=o.id_comercio WHERE o.id_cliente=$1 ORDER BY o.id_orden DESC LIMIT 30', [req.cliente.id_cliente]);
  const items = os.length ? await all(pool, 'SELECT id_orden,nombre,cantidad,precio_unitario FROM orden_item WHERE id_orden = ANY($1) ORDER BY id_item', [os.map((o) => o.id_orden)]) : [];
  return os.map((o) => ({ id_orden: o.id_orden, tienda: o.tienda, total: o.total, descuento: o.descuento, estado: o.estado, codigo_recojo: o.codigo_recojo, fecha_hora: o.fecha_hora,
    items: items.filter((i) => i.id_orden === o.id_orden).map(({ id_orden, ...i }) => i) }));
}));

// ================= RECARGAS Y SERVICIOS (RF-BD-006) =================
const OPERADORES = ['Claro', 'Movistar', 'Entel', 'Bitel'];
const MONTOS_RECARGA = [5, 10, 20, 30, 50];
const SERVICIOS = [
  { id: 'luz-del-sur', nombre: 'Luz del Sur', cat: 'Luz', emoji: '💡' }, { id: 'enel', nombre: 'Enel', cat: 'Luz', emoji: '💡' },
  { id: 'seal', nombre: 'SEAL', cat: 'Luz', emoji: '💡' }, { id: 'sedapal', nombre: 'Sedapal', cat: 'Agua', emoji: '💧' },
  { id: 'sedapar', nombre: 'Sedapar', cat: 'Agua', emoji: '💧' }, { id: 'calidda', nombre: 'Cálidda', cat: 'Gas', emoji: '🔥' },
  { id: 'movistar-hogar', nombre: 'Movistar Hogar', cat: 'Internet y cable', emoji: '🌐' }, { id: 'claro-hogar', nombre: 'Claro Hogar', cat: 'Internet y cable', emoji: '🌐' },
];
const cuentaServicios = (c) => one(c, "SELECT u.id_cuenta, u.id_cliente FROM comercio m JOIN cuenta u ON u.id_cuenta=m.id_cuenta WHERE m.ruc='20100000099'");

app.get('/api/servicios/catalogo', auth, wrap(() => ({ operadores: OPERADORES, montos: MONTOS_RECARGA, servicios: SERVICIOS })));

app.post('/api/recargas', auth, wrap(async (req) => {
  const operador = str(req.body.operador, 20), celular = str(req.body.celular, 9), monto = Number(req.body.monto);
  if (!OPERADORES.includes(operador)) throw new AppError(400, 'Elige un operador');
  if (!/^9\d{8}$/.test(celular)) throw new AppError(400, 'El celular debe tener 9 dígitos y empezar con 9');
  if (!MONTOS_RECARGA.includes(monto)) throw new AppError(400, 'Elige un monto de recarga');
  return operacionDinero(req, 'recarga_celular', async (c) => {
    const dest = await cuentaServicios(c);
    const mv = await moverSaldo(c, req.cuenta.id_cuenta, dest.id_cuenta, monto, TOPE_DIARIO);
    const r = await one(c, "INSERT INTO servicio_pago (id_cliente,tipo,proveedor,referencia,monto,estado) VALUES ($1,'recarga',$2,$3,$4,'completado') RETURNING id_pago_servicio, fecha_hora",
      [req.cliente.id_cliente, operador, celular, monto]);
    const ins = 'INSERT INTO movimiento (id_cuenta,tipo_movimiento,id_pago_servicio,monto,saldo_resultante,descripcion) VALUES ($1,$2,$3,$4,$5,$6)';
    await c.query(ins, [req.cuenta.id_cuenta, 'recarga_celular', r.id_pago_servicio, -monto, mv.saldoOrigen, `Recarga ${operador} · ${celular}`]);
    await c.query(ins, [dest.id_cuenta, 'recarga_celular', r.id_pago_servicio, monto, mv.saldoDestino, `Recarga ${operador} de ${nombreCorto(req.cliente)}`]);
    await notificar(c, req.cliente.id_cliente, 'recarga_celular', `Recargaste ${soles(monto)} a ${operador} ${celular}`);
    return { id_pago_servicio: r.id_pago_servicio, monto, destinatario: `Recarga ${operador} · ${celular}`, fecha_hora: r.fecha_hora, saldo: mv.saldoOrigen };
  });
}));

// Consulta de deuda SIMULADA (determinística por proveedor + código) para la demostración
async function deudaSimulada(c, proveedorId, codigo) {
  const prov = SERVICIOS.find((s) => s.id === proveedorId);
  if (!prov) throw new AppError(400, 'Elige un servicio');
  if (!/^\d{6,12}$/.test(codigo)) throw new AppError(400, 'El código debe tener entre 6 y 12 dígitos');
  const h = crypto.createHash('sha256').update(prov.id + ':' + codigo).digest();
  const n = h.readUInt32BE(0);
  const monto = n % 7 === 0 ? 0 : r2(25 + (n % 15600) / 100);
  const hoy = new Date();
  const venc = new Date(hoy.getTime() + ((n >>> 8) % 12) * 86400000);
  const periodo = hoy.toISOString().slice(0, 7);
  const titular = ['M. Quispe', 'R. Flores', 'J. Ramírez', 'N. Gonzales', 'F. Romero', 'P. Mamani'][n % 6];
  const pagado = !!(await one(c, "SELECT 1 FROM servicio_pago WHERE tipo='servicio' AND proveedor=$1 AND referencia=$2 AND periodo=$3 AND estado='completado'", [prov.nombre, codigo, periodo]));
  return { prov, codigo, monto, titular, vencimiento: venc.toISOString().slice(0, 10), periodo, pagado };
}
app.post('/api/servicios/consultar', auth, wrap(async (req) => {
  const d = await deudaSimulada(pool, str(req.body.proveedor, 30), str(req.body.codigo, 12));
  return { proveedor: d.prov.nombre, codigo: d.codigo, titular: d.titular, monto: d.monto, vencimiento: d.vencimiento, pagado: d.pagado };
}));
app.post('/api/servicios/pagar', auth, wrap(async (req) => {
  const proveedor = str(req.body.proveedor, 30), codigo = str(req.body.codigo, 12);
  return operacionDinero(req, 'pago_servicio', async (c) => {
    const d = await deudaSimulada(c, proveedor, codigo);
    if (d.monto === 0) throw new AppError(400, 'Este código no tiene deudas pendientes');
    if (d.pagado) throw new AppError(409, 'Este recibo ya fue pagado');
    montoValido(d.monto);
    const dest = await cuentaServicios(c);
    const mv = await moverSaldo(c, req.cuenta.id_cuenta, dest.id_cuenta, d.monto, TOPE_DIARIO);
    const r = await one(c, "INSERT INTO servicio_pago (id_cliente,tipo,proveedor,referencia,periodo,monto,estado) VALUES ($1,'servicio',$2,$3,$4,$5,'completado') RETURNING id_pago_servicio, fecha_hora",
      [req.cliente.id_cliente, d.prov.nombre, d.codigo, d.periodo, d.monto]);
    const ins = 'INSERT INTO movimiento (id_cuenta,tipo_movimiento,id_pago_servicio,monto,saldo_resultante,descripcion) VALUES ($1,$2,$3,$4,$5,$6)';
    await c.query(ins, [req.cuenta.id_cuenta, 'pago_servicio', r.id_pago_servicio, -d.monto, mv.saldoOrigen, `Pago de ${d.prov.nombre} · ${d.codigo}`]);
    await c.query(ins, [dest.id_cuenta, 'pago_servicio', r.id_pago_servicio, d.monto, mv.saldoDestino, `Pago ${d.prov.nombre} de ${nombreCorto(req.cliente)}`]);
    await notificar(c, req.cliente.id_cliente, 'pago_servicio', `Pagaste ${soles(d.monto)} de ${d.prov.nombre} (código ${d.codigo})`);
    return { id_pago_servicio: r.id_pago_servicio, monto: d.monto, destinatario: `${d.prov.nombre} · ${d.codigo}`, fecha_hora: r.fecha_hora, saldo: mv.saldoOrigen };
  });
}));

app.use('/api', (req, res) => res.status(404).json({ error: 'No encontrado' }));
app.get('/', (req, res) => res.type('text').send('API Chaski en línea. La app móvil (Flutter) consume /api/*'));
app.use((err, req, res, next) => {
  if (err instanceof AppError) return res.status(err.status).json({ error: err.message });
  if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'JSON inválido' });
  console.error(err);
  res.status(500).json({ error: 'Ocurrió un error. Inténtalo de nuevo.' });
});

init()
  .then(() => {
    setInterval(() => expirarSolicitudes().catch(() => {}), 10 * 60 * 1000).unref();
    app.listen(PORT, '0.0.0.0', () => {
      const nets = Object.values(require('os').networkInterfaces()).flat().filter((n) => n.family === 'IPv4' && !n.internal);
      console.log(`\nAPI Chaski lista (PostgreSQL: ${process.env.PGDATABASE || 'chaski'}):\n  PC:        http://localhost:${PORT}`);
      console.log(`  Emulador:  http://10.0.2.2:${PORT}`);
      nets.forEach((n) => console.log(`  Celular:   http://${n.address}:${PORT}   (mismo Wi-Fi)`));
      console.log('\nUsuarios demo (PIN 123456): 900000001, 900000002, 900000003\n');
    });
  })
  .catch((e) => {
    console.error('No se pudo iniciar la base de datos:', e.message);
    console.error('Revisa PGHOST, PGPORT, PGUSER y PGPASSWORD en backend/.env');
    process.exit(1);
  });
