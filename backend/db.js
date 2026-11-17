const { Pool, Client, types } = require('pg');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// numeric y bigint llegan como texto desde PostgreSQL: los convertimos a número para el JSON
types.setTypeParser(1700, (v) => (v === null ? null : parseFloat(v)));
types.setTypeParser(20, (v) => (v === null ? null : Number(v)));

// La conexión se configura con las variables estándar PGHOST, PGPORT, PGUSER, PGPASSWORD y PGDATABASE (ver .env.example)
const DB_NAME = process.env.PGDATABASE || 'chaski';
const pool = new Pool({ database: DB_NAME, max: 10 });

class AppError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const r2 = (n) => Math.round(n * 100) / 100;
const one = async (c, sql, p = []) => (await c.query(sql, p)).rows[0];
const all = async (c, sql, p = []) => (await c.query(sql, p)).rows;

// Ejecuta fn dentro de una transacción ACID (BEGIN/COMMIT, ROLLBACK si algo falla)
async function tx(fn) {
  const c = await pool.connect();
  try {
    await c.query('BEGIN');
    const r = await fn(c);
    await c.query('COMMIT');
    return r;
  } catch (e) {
    await c.query('ROLLBACK').catch(() => {});
    throw e;
  } finally {
    c.release();
  }
}

// ---- PIN ----
function hashPin(pin) {
  const salt = crypto.randomBytes(16);
  return `${salt.toString('hex')}:${crypto.scryptSync(pin, salt, 32).toString('hex')}`;
}
function checkPin(pin, stored) {
  const [s, h] = stored.split(':');
  const t = crypto.scryptSync(pin, Buffer.from(s, 'hex'), 32);
  return crypto.timingSafeEqual(t, Buffer.from(h, 'hex'));
}

async function nuevaCuentaVirtual(c) {
  for (;;) {
    const n = 'CHK-' + String(crypto.randomInt(0, 1e12)).padStart(12, '0');
    if (!(await one(c, 'SELECT 1 FROM cuenta WHERE numero_cuenta_virtual=$1', [n]))) return n;
  }
}

async function notificar(c, id_cliente, tipo, mensaje) {
  await c.query("INSERT INTO notificacion (id_cliente,tipo,mensaje,estado_envio) VALUES ($1,$2,$3,'enviado')", [id_cliente, tipo, mensaje.slice(0, 300)]);
}

async function crearCliente(c, d, saldoInicial = 0) {
  const { id_cliente } = await one(c,
    'INSERT INTO cliente (tipo_documento,numero_documento,nombres,apellidos,celular,email) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id_cliente',
    [d.tipo_documento, d.numero_documento, d.nombres, d.apellidos, d.celular, d.email || null]);
  await c.query('INSERT INTO credencial (id_cliente,pin_hash) VALUES ($1,$2)', [id_cliente, hashPin(d.pin)]);
  const { id_cuenta } = await one(c,
    'INSERT INTO cuenta (id_cliente,numero_cuenta_virtual,saldo_actual) VALUES ($1,$2,$3) RETURNING id_cuenta',
    [id_cliente, await nuevaCuentaVirtual(c), saldoInicial]);
  if (saldoInicial > 0) {
    await c.query("INSERT INTO movimiento (id_cuenta,tipo_movimiento,monto,saldo_resultante,descripcion) VALUES ($1,'recarga',$2,$2,'Saldo de bienvenida (demo)')",
      [id_cuenta, saldoInicial]);
  }
  await notificar(c, id_cliente, 'bienvenida', '¡Bienvenido a Chaski! Ya puedes enviar y recibir dinero al instante.');
  return { id_cliente, id_cuenta };
}

const cuentaDeCliente = (c, id_cliente) => one(c, 'SELECT * FROM cuenta WHERE id_cliente=$1', [id_cliente]);

// Débitos del día (hora de Lima) de una cuenta: base del tope diario RN-TOP-001
async function consumidoHoy(c, id_cuenta) {
  const r = await one(c, `SELECT COALESCE(SUM(-monto),0) AS n FROM movimiento
    WHERE id_cuenta=$1 AND monto < 0
      AND fecha_hora >= (date_trunc('day', now() AT TIME ZONE 'America/Lima') AT TIME ZONE 'America/Lima')`, [id_cuenta]);
  return r2(r.n);
}

// Mueve dinero entre dos cuentas. Debe llamarse dentro de tx().
// Bloquea ambas filas (en orden de id para evitar deadlocks) y valida estado, saldo y tope diario.
async function moverSaldo(c, id_origen, id_destino, monto, topeDiario) {
  const rows = await all(c, 'SELECT id_cuenta, saldo_actual, estado FROM cuenta WHERE id_cuenta = ANY($1) ORDER BY id_cuenta FOR UPDATE',
    [[id_origen, id_destino]]);
  const o = rows.find((x) => x.id_cuenta === id_origen);
  const d = rows.find((x) => x.id_cuenta === id_destino);
  if (!o || !d) throw new AppError(404, 'Cuenta no encontrada');
  if (o.estado !== 'activo') throw new AppError(403, 'Tu cuenta no está activa');
  if (d.estado !== 'activo') throw new AppError(403, 'La cuenta destino no está activa');
  if (o.saldo_actual < monto) throw new AppError(400, 'Saldo insuficiente');
  if (topeDiario) {
    const usado = await consumidoHoy(c, id_origen);
    if (r2(usado + monto) > topeDiario)
      throw new AppError(400, `Superas tu tope diario de S/ ${topeDiario.toFixed(2)}. Hoy te quedan S/ ${Math.max(0, topeDiario - usado).toFixed(2)}`);
  }
  const so = await one(c, 'UPDATE cuenta SET saldo_actual = saldo_actual - $1 WHERE id_cuenta=$2 RETURNING saldo_actual', [monto, id_origen]);
  const sd = await one(c, 'UPDATE cuenta SET saldo_actual = saldo_actual + $1 WHERE id_cuenta=$2 RETURNING saldo_actual', [monto, id_destino]);
  return { saldoOrigen: so.saldo_actual, saldoDestino: sd.saldo_actual };
}

// ---- creación de la base, esquema y datos de demostración ----
async function asegurarBase() {
  try {
    const c = new Client({ database: DB_NAME });
    await c.connect();
    await c.end();
  } catch (e) {
    if (e.code !== '3D000') throw e; // 3D000 = la base no existe
    const adm = new Client({ database: 'postgres' });
    await adm.connect();
    await adm.query(`CREATE DATABASE "${DB_NAME.replace(/"/g, '')}"`);
    await adm.end();
    console.log(`Base de datos "${DB_NAME}" creada`);
  }
}

const diasDesdeAhora = (d) => new Date(Date.now() + d * 86400000).toISOString();

async function ensureComercio(c, rs, ruc, cel, conQR) {
  const ex = await one(c, 'SELECT id_comercio FROM comercio WHERE ruc=$1', [ruc]);
  if (ex) return ex.id_comercio;
  const { id_cuenta } = await crearCliente(c,
    { tipo_documento: 'RUC', numero_documento: ruc, nombres: rs, apellidos: '(comercio)', celular: cel, pin: crypto.randomBytes(8).toString('hex') }, 0);
  const { id_comercio } = await one(c, 'INSERT INTO comercio (id_cuenta,razon_social,ruc) VALUES ($1,$2,$3) RETURNING id_comercio', [id_cuenta, rs, ruc]);
  if (conQR) await c.query("INSERT INTO codigo_qr (id_comercio,id_cuenta,tipo) VALUES ($1,$2,'estatico')", [id_comercio, id_cuenta]);
  return id_comercio;
}

async function seed(c) {
  if ((await one(c, 'SELECT COUNT(*)::int n FROM cliente')).n > 0) return;
  const demo = [
    ['DNI', '70000001', 'Lucía', 'Quispe Mamani', '900000001'],
    ['DNI', '70000002', 'Carlos', 'Huamán Ccori', '900000002'],
    ['DNI', '70000003', 'Ana', 'Valdivia Pinto', '900000003'],
  ];
  for (const [td, nd, n, a, cel] of demo) {
    await crearCliente(c, { tipo_documento: td, numero_documento: nd, nombres: n, apellidos: a, celular: cel, pin: '123456' }, 250);
  }
  await ensureComercio(c, 'Bodega Don Lucho', '20100000011', '910000001', true);
  await ensureComercio(c, 'Café Misti', '20100000022', '910000002', true);
  await ensureComercio(c, 'Farmacia Sillar', '20100000033', '910000003', true);
}

async function seedTienda(c) {
  await ensureComercio(c, 'Chaski Servicios', '20100000099', '910000009', false); // recibe recargas y pagos de servicios
  if ((await one(c, 'SELECT COUNT(*)::int n FROM producto')).n > 0) return;
  const rosita = await ensureComercio(c, 'Pollería Rosita', '20100000044', '910000004', true);
  const tecno = await ensureComercio(c, 'Tecno Express', '20100000055', '910000005', true);
  const id = async (ruc) => (await one(c, 'SELECT id_comercio FROM comercio WHERE ruc=$1', [ruc])).id_comercio;
  const catalogo = [
    [await id('20100000011'), [
      ['Arroz Costeño 5 kg', 'Abarrotes', '🍚', 24.9, 40], ['Aceite Primor 1 L', 'Abarrotes', '🫒', 9.5, 60],
      ['Leche Gloria (pack x6)', 'Lácteos', '🥛', 27, 30, 21.9], ['Atún Florida (x3)', 'Abarrotes', '🐟', 14, 50],
      ['Inca Kola 3 L', 'Bebidas', '🥤', 12.5, 45, 9.9], ['Galletas Field (x6)', 'Snacks', '🍪', 6, 80]]],
    [await id('20100000022'), [
      ['Café americano', 'Café', '☕', 7, 99], ['Capuchino', 'Café', '☕', 9, 99], ['Sándwich de pavo', 'Comida', '🥪', 14, 40],
      ['Cheesecake de maracuyá', 'Postres', '🍰', 12, 20, 8.9], ['Jugo de naranja', 'Bebidas', '🍊', 8, 50],
      ['Combo desayuno', 'Comida', '🥐', 18, 25, 14.9]]],
    [await id('20100000033'), [
      ['Paracetamol 500 mg (x10)', 'Salud', '💊', 4.5, 100], ['Alcohol en gel 250 ml', 'Cuidado', '🧴', 8, 70],
      ['Vitamina C (x30)', 'Salud', '🍋', 22, 35, 17.5], ['Mascarillas (x20)', 'Cuidado', '😷', 9, 60],
      ['Protector solar FPS 50', 'Cuidado', '☀️', 39.9, 25, 31.9], ['Termómetro digital', 'Salud', '🌡️', 25, 20]]],
    [rosita, [
      ['1/4 de pollo a la brasa', 'Pollos', '🍗', 21, 40, 17.9], ['Porción de papas fritas', 'Extras', '🍟', 6, 80],
      ['Chicha morada 1 L', 'Bebidas', '🍇', 8, 50], ['Mazamorra morada', 'Postres', '🍮', 5, 40]]],
    [tecno, [
      ['Cargador USB-C 20 W', 'Accesorios', '🔌', 29.9, 30, 24.9], ['Audífonos con cable', 'Audio', '🎧', 45, 25],
      ['Power bank 10 000 mAh', 'Accesorios', '🔋', 69, 15, 54], ['Cable USB-C 1 m', 'Accesorios', '🔗', 12, 60]]],
  ];
  for (const [idc, prods] of catalogo) {
    for (const [i, [n, cat, em, pr, st, of]] of prods.entries()) {
      const { id_producto } = await one(c,
        'INSERT INTO producto (id_comercio,nombre,categoria,emoji,precio,stock) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id_producto', [idc, n, cat, em, pr, st]);
      if (of) await c.query('INSERT INTO oferta (id_producto,precio_oferta,stock_oferta,fecha_fin) VALUES ($1,$2,$3,$4)',
        [id_producto, of, Math.min(st, 12), diasDesdeAhora(1 + (i % 4))]);
    }
  }
  const ini = diasDesdeAhora(-1), fin = diasDesdeAhora(60);
  const promos = [
    [await id('20100000022'), '15% de descuento en tu café', 'Paga con Chaski y ahorra en toda tu cuenta. Tope de S/ 10 por compra.', 15, 10],
    [await id('20100000033'), '10% de descuento en salud y cuidado', 'Válido en compras con Chaski, en tienda o con QR. Tope de S/ 15.', 10, 15],
    [await id('20100000011'), '5% menos en tu compra de la semana', 'Descuento en productos sin oferta. Tope de S/ 8.', 5, 8],
    [rosita, '10% en tu pollo a la brasa', 'Paga con Chaski y llévate el descuento. Tope de S/ 8.', 10, 8],
    [tecno, '8% en accesorios', 'Descuento en productos sin oferta. Tope de S/ 12.', 8, 12],
  ];
  for (const [idc, t, d, p, tope] of promos) {
    await c.query('INSERT INTO promocion (id_comercio,titulo,descripcion,porcentaje,tope_descuento,fecha_inicio,fecha_fin) VALUES ($1,$2,$3,$4,$5,$6,$7)',
      [idc, t, d, p, tope, ini, fin]);
  }
}

// Demo: mantiene vigentes las ofertas y promos de ejemplo
async function renovarDemo(c) {
  const ofs = await all(c, 'SELECT id_oferta FROM oferta WHERE fecha_fin < $1 ORDER BY id_oferta', [diasDesdeAhora(0.5)]);
  for (const [i, o] of ofs.entries()) {
    await c.query('UPDATE oferta SET fecha_fin=$1, stock_oferta=GREATEST(stock_oferta,8) WHERE id_oferta=$2', [diasDesdeAhora(1 + (i % 4)), o.id_oferta]);
  }
  await c.query('UPDATE promocion SET fecha_fin=$1 WHERE fecha_fin < $2', [diasDesdeAhora(60), diasDesdeAhora(7)]);
}

async function init() {
  await asegurarBase();
  await pool.query(fs.readFileSync(path.join(__dirname, 'sql', 'schema.sql'), 'utf8'));
  await tx(async (c) => {
    await seed(c);
    await seedTienda(c);
    await renovarDemo(c);
  });
}

module.exports = { pool, tx, one, all, r2, AppError, hashPin, checkPin, crearCliente, cuentaDeCliente, consumidoHoy, moverSaldo, notificar, init };
