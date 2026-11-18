'use strict';
// Pruebas de la API de Chaski contra un COREDB falso (un servidor HTTP en este proceso que
// registra lo que recibe). Lo que Chaski hace con COREDB y la base real lo prueba el flujo
// de extremo a extremo del producto (scripts/flujo_e2e.py, tramo de la billetera).
// Uso: npm test
const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const { crearApp, configuracion } = require('../server');
const { crearCliente } = require('../coredb');

const BUS_TOKEN = 'b'.repeat(40);
const TOKEN_CLIENTE = 'token-de-cliente-emitido-por-coredb';
const LLAVE = '6f1c2a5e-7d4b-4c3a-9e8f-0a1b2c3d4e5f';

// COREDB falso: responde según `respuestas[ruta]` y guarda cada petición en `peticiones`.
function falsoCoreDb() {
  const estado = { peticiones: [], respuestas: {}, logins: 0, vencerServicio: false };
  const servidor = http.createServer((req, res) => {
    let cuerpo = '';
    req.on('data', (c) => { cuerpo += c; });
    req.on('end', () => {
      const ruta = `${req.method} ${req.url}`;
      estado.peticiones.push({ ruta, cabeceras: req.headers, cuerpo: cuerpo ? JSON.parse(cuerpo) : undefined });
      const responder = (status, datos) => {
        res.writeHead(status, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(datos));
      };
      if (req.headers['x-bus-token'] !== BUS_TOKEN) return responder(401, { error: { code: 'BUS_CREDENCIAL_INVALIDA' } });
      if (ruta === 'POST /bus/coredb/coredb/auth/login') {
        estado.logins += 1;
        return responder(200, { access_token: `svc-${estado.logins}`, expires_in: 1800 });
      }
      if (ruta === 'GET /bus/coredb/coredb/salud') return responder(200, { estado: 'ok' });
      if (estado.vencerServicio && req.headers.authorization === 'Bearer svc-1') {
        return responder(401, { error: { code: 'TOKEN_EXPIRADO', message: 'La sesión expiró.' } });
      }
      const [status, datos] = estado.respuestas[ruta] || [404, { error: { code: 'NO_ESTA', message: ruta } }];
      return responder(status, datos);
    });
  });
  return { estado, servidor };
}

const OPERACION = { id_operacion: '11111111-1111-4111-8111-111111111111', tipo: 'P2P', sentido: 'ENVIADA',
  nombre_origen: 'Ana D.', nombre_destino: 'Luis R.', monto: '45.50', referencia: 'Almuerzo', id_qr: null,
  id_solicitud: null, uuid_debito: '22222222-2222-4222-8222-222222222222', fecha_hora: '2026-11-17T10:00:00Z',
  repetido: false };

async function preparar(t) {
  const { estado, servidor } = falsoCoreDb();
  await new Promise((ok) => servidor.listen(0, '127.0.0.1', ok));
  const coredb = crearCliente({ url: `http://127.0.0.1:${servidor.address().port}/bus/coredb`, busToken: BUS_TOKEN,
    usuario: 'svc-billetera', secreto: 's'.repeat(40) });
  const chaski = crearApp({ coredb }).listen(0, '127.0.0.1');
  await new Promise((ok) => chaski.once('listening', ok));
  t.after(() => { chaski.close(); servidor.close(); });
  const base = `http://127.0.0.1:${chaski.address().port}/api`;
  async function api(metodo, ruta, { cuerpo, token = TOKEN_CLIENTE, cabeceras = {} } = {}) {
    const res = await fetch(base + ruta, {
      method: metodo,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...cabeceras },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
    return { status: res.status, datos: await res.json() };
  }
  const ultima = (ruta) => [...estado.peticiones].reverse().find((p) => p.ruta === ruta);
  return { estado, api, ultima };
}

test('el login valida celular y PIN en COREDB y entrega el token de cliente', async (t) => {
  const { estado, api, ultima } = await preparar(t);
  estado.respuestas['POST /bus/coredb/coredb/billetera/acceso'] = [200, {
    access_token: TOKEN_CLIENTE, token_type: 'bearer', expires_in: 1800, cliente: { cod_cliente: 'C9', nombre_corto: 'Ana D.' } }];
  const r = await api('POST', '/login', { token: null, cuerpo: { celular: '959000001', pin: '123456' } });
  assert.equal(r.status, 200, JSON.stringify(r.datos));
  assert.equal(r.datos.token, TOKEN_CLIENTE);
  const p = ultima('POST /bus/coredb/coredb/billetera/acceso');
  assert.deepEqual(p.cuerpo, { celular: '959000001', pin: '123456' });
  assert.equal(p.cabeceras.authorization, 'Bearer svc-1', 'con el token de servicio de Chaski');
  assert.equal(p.cabeceras['x-bus-token'], BUS_TOKEN, 'con la credencial de Chaski ante el Bus');
  assert.equal(p.cabeceras['x-cliente-token'], undefined);
});

test('un PIN equivocado y una billetera bloqueada se explican sin datos del cliente', async (t) => {
  const { estado, api } = await preparar(t);
  estado.respuestas['POST /bus/coredb/coredb/billetera/acceso'] = [401, { error: { code: 'CREDENCIALES_INVALIDAS' } }];
  const r = await api('POST', '/login', { token: null, cuerpo: { celular: '959000001', pin: '000000' } });
  assert.deepEqual(r, { status: 401, datos: { error: 'Celular o PIN incorrecto' } });
  estado.respuestas['POST /bus/coredb/coredb/billetera/acceso'] = [403, { error: { code: 'BILLETERA_BLOQUEADA' } }];
  const b = await api('POST', '/login', { token: null, cuerpo: { celular: '959000001', pin: '123456' } });
  assert.equal(b.status, 403);
  assert.doesNotMatch(JSON.stringify(b.datos), /959000001/);
});

test('el registro no crea clientes: la billetera la activa el banco (punto R-01)', async (t) => {
  const { estado, api } = await preparar(t);
  const r = await api('POST', '/registro', { token: null, cuerpo: { celular: '959000001', pin: '123456', numero_documento: '12345678' } });
  assert.equal(r.status, 403);
  assert.match(r.datos.error, /agencia/);
  assert.equal(estado.peticiones.length, 0, 'no llama a COREDB');
});

test('cada operación del cliente lleva el token de servicio y el del cliente', async (t) => {
  const { estado, api, ultima } = await preparar(t);
  estado.respuestas['GET /bus/coredb/coredb/billetera/yo'] = [200, { cod_cliente: 'C9', nombre_corto: 'Ana D.',
    num_cuenta: 'CTA-1', estado: 'ACTIVA', saldo_disponible: '254.50', tope_diario: '500.00', consumido_hoy: '45.50',
    disponible_hoy: '454.50', notificaciones_sin_leer: 2, solicitudes_pendientes: 1 }];
  const r = await api('GET', '/me');
  assert.equal(r.status, 200, JSON.stringify(r.datos));
  assert.equal(r.datos.cuenta.saldo_actual, 254.5);
  assert.equal(r.datos.disponible_hoy, 454.5);
  assert.equal(r.datos.no_leidas, 2);
  const p = ultima('GET /bus/coredb/coredb/billetera/yo');
  assert.equal(p.cabeceras.authorization, 'Bearer svc-1');
  assert.equal(p.cabeceras['x-cliente-token'], TOKEN_CLIENTE);
});

test('sin sesión no llama a COREDB, y una sesión vencida en COREDB es 401 para la app', async (t) => {
  const { estado, api } = await preparar(t);
  const sin = await api('GET', '/me', { token: null });
  assert.equal(sin.status, 401);
  assert.equal(estado.peticiones.length, 0);
  estado.respuestas['GET /bus/coredb/coredb/billetera/yo'] = [401, { error: { code: 'TOKEN_CLIENTE_EXPIRADO' } }];
  const vencida = await api('GET', '/me');
  assert.deepEqual(vencida, { status: 401, datos: { error: 'Sesión vencida. Inicia sesión otra vez.' } });
});

test('una transferencia reenvía la llave de la app como X-Idempotency-Key', async (t) => {
  const { estado, api, ultima } = await preparar(t);
  estado.respuestas['POST /bus/coredb/coredb/billetera/transferencias'] = [201, OPERACION];
  const r = await api('POST', '/transferencias', { cabeceras: { 'Idempotency-Key': LLAVE },
    cuerpo: { celular_destino: '959000002', monto: 45.5, referencia: 'Almuerzo' } });
  assert.equal(r.status, 200, JSON.stringify(r.datos));
  assert.equal(r.datos.id_transferencia, OPERACION.id_operacion);
  assert.equal(r.datos.destinatario, 'Luis R.');
  assert.equal(r.datos.repetida, false);
  const p = ultima('POST /bus/coredb/coredb/billetera/transferencias');
  assert.equal(p.cabeceras['x-idempotency-key'], LLAVE);
  assert.deepEqual(p.cuerpo, { celular_destino: '959000002', monto: '45.50', referencia: 'Almuerzo' });
  // El uuid también puede venir en el cuerpo (uuid_transaccion), como en la app.
  await api('POST', '/transferencias', { cuerpo: { celular_destino: '959000002', monto: 1, uuid_transaccion: LLAVE } });
  assert.equal(ultima('POST /bus/coredb/coredb/billetera/transferencias').cabeceras['x-idempotency-key'], LLAVE);
});

test('una transferencia sin uuid lleva una llave nueva y una mal formada se rechaza', async (t) => {
  const { estado, api, ultima } = await preparar(t);
  estado.respuestas['POST /bus/coredb/coredb/billetera/transferencias'] = [201, OPERACION];
  await api('POST', '/transferencias', { cuerpo: { celular_destino: '959000002', monto: 1 } });
  assert.match(ultima('POST /bus/coredb/coredb/billetera/transferencias').cabeceras['x-idempotency-key'],
    /^[0-9a-f-]{36}$/);
  const n = estado.peticiones.length;
  const mala = await api('POST', '/transferencias', { cabeceras: { 'Idempotency-Key': 'no-es-uuid' },
    cuerpo: { celular_destino: '959000002', monto: 1 } });
  assert.equal(mala.status, 400);
  assert.equal(estado.peticiones.length, n, 'no llega a COREDB');
});

test('Chaski valida celular y monto antes de llamar a COREDB', async (t) => {
  const { estado, api } = await preparar(t);
  for (const cuerpo of [{ celular_destino: '12345', monto: 1 }, { celular_destino: '959000002', monto: 0 },
    { celular_destino: '959000002', monto: 501 }, { celular_destino: '959000002', monto: 'x' }]) {
    const r = await api('POST', '/transferencias', { cuerpo });
    assert.equal(r.status, 400, JSON.stringify(cuerpo));
  }
  assert.equal(estado.peticiones.length, 0);
});

test('los rechazos de la base llegan a la app como mensajes', async (t) => {
  const { estado, api } = await preparar(t);
  const casos = [
    ['BNA-SALDO', 422, 400, /Saldo insuficiente/],
    ['RN-TOP-001', 422, 400, /tope diario/],
    ['BNA-BILLETERA-DESTINO', 404, 404, /no está registrado/],
    ['BNA-IDEMPOTENCIA', 409, 409, /duplicada/],
  ];
  for (const [code, deCoreDb, esperado, mensaje] of casos) {
    estado.respuestas['POST /bus/coredb/coredb/billetera/transferencias'] = [deCoreDb, { error: { code, message: 'x' } }];
    const r = await api('POST', '/transferencias', { cuerpo: { celular_destino: '959000002', monto: 10 } });
    assert.equal(r.status, esperado, code);
    assert.match(r.datos.error, mensaje, code);
  }
});

test('un token de servicio vencido se renueva y la operación se repite con la misma llave', async (t) => {
  const { estado, api } = await preparar(t);
  estado.respuestas['POST /bus/coredb/coredb/billetera/transferencias'] = [201, OPERACION];
  await api('GET', '/promos'); // no llama a COREDB
  estado.respuestas['GET /bus/coredb/coredb/billetera/notificaciones'] = [200, []];
  await api('GET', '/notificaciones'); // primer login: svc-1
  estado.vencerServicio = true;
  const r = await api('POST', '/transferencias', { cabeceras: { 'Idempotency-Key': LLAVE },
    cuerpo: { celular_destino: '959000002', monto: 5 } });
  assert.equal(r.status, 200, JSON.stringify(r.datos));
  assert.equal(estado.logins, 2);
  const envios = estado.peticiones.filter((p) => p.ruta === 'POST /bus/coredb/coredb/billetera/transferencias');
  assert.deepEqual(envios.map((p) => p.cabeceras.authorization), ['Bearer svc-1', 'Bearer svc-2']);
  assert.deepEqual(envios.map((p) => p.cabeceras['x-idempotency-key']), [LLAVE, LLAVE]);
});

test('buscar un contacto manda el celular a COREDB en el cuerpo, no en la ruta', async (t) => {
  const { estado, api, ultima } = await preparar(t);
  estado.respuestas['POST /bus/coredb/coredb/billetera/contactos'] = [200, { nombre: 'Luis R.' }];
  const r = await api('GET', '/clientes/buscar?celular=959000002');
  assert.deepEqual(r.datos, { celular: '959000002', nombre: 'Luis R.' });
  assert.deepEqual(ultima('POST /bus/coredb/coredb/billetera/contactos').cuerpo, { celular: '959000002' });
  assert.ok(estado.peticiones.every((p) => !p.ruta.includes('959000002')));
});

test('pagar un QR usa su id, el monto si es estático y la llave', async (t) => {
  const { estado, api, ultima } = await preparar(t);
  const id = '33333333-3333-4333-8333-333333333333';
  estado.respuestas[`GET /bus/coredb/coredb/billetera/qr/${id}`] = [200, { id_qr: id, tipo: 'DINAMICO', monto: '30.00',
    estado: 'ACTIVO', beneficiario: 'Marta L.', es_comercio: false, fecha_expiracion: '2026-11-17T10:15:00Z' }];
  const visto = await api('GET', `/qr/${id}`);
  assert.equal(visto.datos.nombre, 'Marta L.');
  assert.equal(visto.datos.monto, 30);
  estado.respuestas[`POST /bus/coredb/coredb/billetera/qr/${id}/pagos`] = [201, { ...OPERACION, tipo: 'QR', id_qr: id }];
  const pago = await api('POST', `/qr/${id}/pagar`, { cabeceras: { 'Idempotency-Key': LLAVE }, cuerpo: {} });
  assert.equal(pago.status, 200, JSON.stringify(pago.datos));
  assert.equal(pago.datos.id_pago, OPERACION.id_operacion);
  const p = ultima(`POST /bus/coredb/coredb/billetera/qr/${id}/pagos`);
  assert.deepEqual(p.cuerpo, {});
  assert.equal(p.cabeceras['x-idempotency-key'], LLAVE);
  estado.respuestas[`GET /bus/coredb/coredb/billetera/qr/${id}`][1].estado = 'PAGADO';
  assert.equal((await api('GET', `/qr/${id}`)).status, 410);
  assert.equal((await api('GET', '/qr/no-es-un-uuid')).status, 404);
});

test('aceptar una solicitud exige llave; rechazarla no', async (t) => {
  const { estado, api, ultima } = await preparar(t);
  const id = '44444444-4444-4444-8444-444444444444';
  const ruta = `POST /bus/coredb/coredb/billetera/solicitudes/${id}/respuesta`;
  estado.respuestas[ruta] = [200, { estado: 'PAGADA', operacion: { ...OPERACION, tipo: 'SOLICITUD' } }];
  const aceptada = await api('POST', `/solicitudes/${id}/responder`, { cuerpo: { accion: 'aceptar' } });
  assert.equal(aceptada.datos.estado, 'aceptada');
  assert.deepEqual(ultima(ruta).cuerpo, { accion: 'ACEPTAR' });
  assert.match(ultima(ruta).cabeceras['x-idempotency-key'], /^[0-9a-f-]{36}$/);
  estado.respuestas[ruta] = [200, { estado: 'RECHAZADA', operacion: null }];
  const rechazada = await api('POST', `/solicitudes/${id}/responder`, { cuerpo: { accion: 'rechazar' } });
  assert.equal(rechazada.datos.estado, 'rechazada');
  assert.equal(ultima(ruta).cabeceras['x-idempotency-key'], undefined);
  assert.equal((await api('POST', `/solicitudes/${id}/responder`, { cuerpo: { accion: 'otra' } })).status, 400);
});

test('tienda, promociones, cupones, recargas y servicios quedan fuera de esta versión', async (t) => {
  const { estado, api } = await preparar(t);
  assert.deepEqual((await api('GET', '/promos')).datos, []);
  assert.deepEqual((await api('GET', '/ofertas')).datos, []);
  for (const [metodo, ruta] of [['POST', '/promos/1/cupon'], ['GET', '/tienda'], ['POST', '/tienda/comprar'],
    ['GET', '/ordenes'], ['POST', '/recargas'], ['POST', '/servicios/pagar']]) {
    assert.equal((await api(metodo, ruta, { cuerpo: metodo === 'POST' ? {} : undefined })).status, 501, ruta);
  }
  assert.equal(estado.peticiones.length, 0);
});

test('la salud dice si COREDB responde por el Bus', async (t) => {
  const { api } = await preparar(t);
  const salud = await api('GET', '/salud', { token: null });
  assert.equal(salud.status, 200);
  assert.equal(salud.datos.coredb, true);
  assert.equal((await api('GET', '/listo', { token: null })).status, 200);
});

test('sin su configuración Chaski no arranca y nombra lo que falta', () => {
  assert.throws(() => configuracion({ COREDB_URL: 'http://bus:8018/bus/coredb' }),
    /BUS_TOKEN, CHASKI_COREDB_USUARIO, CHASKI_COREDB_SECRETO/);
});
