// Prueba de humo de la API. Requiere el servidor corriendo (npm start) con los datos demo.
// Uso: npm test     (API_URL=http://localhost:3000 por defecto)
const test = require('node:test');
const assert = require('node:assert');
const crypto = require('node:crypto');

const BASE = (process.env.API_URL || `http://localhost:${process.env.PORT || 3000}`) + '/api';
async function api(path, { token, body, headers = {} } = {}) {
  const res = await fetch(BASE + path, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}), ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, data: await res.json() };
}
const login = async (celular) => (await api('/login', { body: { celular, pin: '123456' } })).data.token;

test('flujo completo de la billetera', async (t) => {
  const lucia = await login('900000001');
  const carlos = await login('900000002');
  assert.ok(lucia && carlos, 'login demo');

  const me0 = (await api('/me', { token: lucia })).data;
  assert.equal(me0.cliente.celular, '900000001');
  assert.equal(me0.tope_diario, 500);

  await t.test('PIN incorrecto se rechaza', async () => {
    assert.equal((await api('/login', { body: { celular: '900000001', pin: '000000' } })).status, 401);
  });

  await t.test('transferencia P2P con idempotencia', async () => {
    const uuid = crypto.randomUUID();
    const body = { celular_destino: '900000002', monto: 1.5, referencia: 'prueba', uuid_transaccion: uuid };
    const a = await api('/transferencias', { token: lucia, body });
    assert.equal(a.status, 200, JSON.stringify(a.data));
    const b = await api('/transferencias', { token: lucia, body });
    assert.equal(b.data.repetida, true);
    assert.equal(b.data.id_transferencia, a.data.id_transferencia);
    const me1 = (await api('/me', { token: lucia })).data;
    assert.equal(Math.round((me0.cuenta.saldo_actual - me1.cuenta.saldo_actual) * 100), 150, 'se cobra una sola vez');
  });

  await t.test('celular no afiliado', async () => {
    assert.equal((await api('/clientes/buscar?celular=999999999', { token: lucia })).status, 404);
  });

  await t.test('tope diario de S/ 500', async () => {
    const r = await api('/transferencias', { token: lucia, body: { celular_destino: '900000002', monto: 500 } });
    assert.equal(r.status, 400);
    assert.match(r.data.error, /tope diario|Saldo insuficiente/);
  });

  await t.test('solicitud de cobro aceptada', async () => {
    const s = await api('/solicitudes', { token: carlos, body: { celular: '900000001', monto: 2, concepto: 'almuerzo' } });
    assert.equal(s.status, 200, JSON.stringify(s.data));
    const r = await api(`/solicitudes/${s.data.id_solicitud}/responder`, { token: lucia, body: { accion: 'aceptar' } });
    assert.equal(r.status, 200, JSON.stringify(r.data));
    assert.ok(r.data.id_transferencia);
  });

  await t.test('pago QR a comercio con promo', async () => {
    const com = (await api('/comercios', { token: lucia })).data;
    const cafe = com.find((c) => c.nombre === 'Café Misti');
    const info = (await api('/qr/' + cafe.id_qr, { token: lucia })).data;
    assert.ok(info.promo);
    const p = await api(`/qr/${cafe.id_qr}/pagar`, { token: lucia, body: { monto: 10 } });
    assert.equal(p.status, 200, JSON.stringify(p.data));
    assert.equal(p.data.ahorro, 1.5);
    assert.equal(p.data.monto, 8.5);
  });

  await t.test('QR dinámico se paga una sola vez', async () => {
    const q = (await api('/qr', { token: carlos, body: { monto: 1 } })).data;
    assert.equal((await api(`/qr/${q.id_qr}/pagar`, { token: lucia, body: {} })).status, 200);
    assert.equal((await api(`/qr/${q.id_qr}/pagar`, { token: lucia, body: {} })).status, 409);
  });

  await t.test('cupón de promoción', async () => {
    const promos = (await api('/promos', { token: lucia })).data;
    const c1 = await api(`/promos/${promos[0].id_promocion}/cupon`, { token: lucia, body: {} });
    const c2 = await api(`/promos/${promos[0].id_promocion}/cupon`, { token: lucia, body: {} });
    assert.equal(c1.status, 200);
    assert.equal(c1.data.codigo, c2.data.codigo);
  });

  await t.test('compra en tienda', async () => {
    const t1 = (await api('/tienda', { token: carlos })).data;
    const prod = t1.productos.find((p) => p.precio < 10);
    const r = await api('/tienda/comprar', { token: carlos, body: { items: [{ id_producto: prod.id_producto, cantidad: 1 }], uuid_transaccion: crypto.randomUUID() } });
    assert.equal(r.status, 200, JSON.stringify(r.data));
    assert.equal(r.data.ordenes.length, 1);
    assert.ok((await api('/ordenes', { token: carlos })).data[0].items.length);
  });

  await t.test('recarga y pago de servicio', async () => {
    assert.equal((await api('/recargas', { token: carlos, body: { operador: 'Claro', celular: '900000002', monto: 5 } })).status, 200);
    let d, cod;
    for (let i = 100000; i < 100050; i++) {
      d = (await api('/servicios/consultar', { token: carlos, body: { proveedor: 'sedapal', codigo: String(i) } })).data;
      if (d.monto > 0 && d.monto < 60 && !d.pagado) { cod = String(i); break; }
    }
    assert.ok(cod, 'encontrar un recibo de prueba');
    assert.equal((await api('/servicios/pagar', { token: carlos, body: { proveedor: 'sedapal', codigo: cod } })).status, 200);
    assert.equal((await api('/servicios/pagar', { token: carlos, body: { proveedor: 'sedapal', codigo: cod } })).status, 409);
  });

  await t.test('movimientos y notificaciones', async () => {
    const movs = (await api('/movimientos', { token: lucia })).data;
    assert.ok(movs.length >= 3);
    assert.ok((await api('/notificaciones', { token: carlos })).data.length > 0);
  });
});
