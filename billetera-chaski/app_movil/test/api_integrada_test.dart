// La app frente a la API integrada de Chaski (billetera-chaski/backend/server.js), con HTTP simulado.
// Los celulares y nombres son de prueba.
import 'dart:convert';

import 'package:chaski_app/funciones.dart';
import 'package:chaski_app/models.dart';
import 'package:chaski_app/screens/home_shell.dart';
import 'package:chaski_app/screens/login_screen.dart';
import 'package:chaski_app/screens/qr_screens.dart';
import 'package:chaski_app/services/api.dart';
import 'package:chaski_app/services/operaciones.dart';
import 'package:chaski_app/state/app_state.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

const celularPrueba = '900000001';
const idQr = 'a5db6a6f-6de7-4e6f-9c7b-af6e43a06fcc';
const idSolicitud = '6c1f0c1e-5a0b-4f8e-9a63-0f6a9c1b2d3e';

final meJson = {
  'cliente': {'id_cliente': 'CLI000000016', 'nombres': 'Rosa H.', 'apellidos': '', 'nombre_corto': 'Rosa H.'},
  'cuenta': {'id_cuenta': 'CTA-0000000000000001', 'numero_cuenta_virtual': 'CTA-0000000000000001', 'saldo_actual': 1000, 'moneda': 'PEN'},
  'no_leidas': 0,
  'pendientes': 0,
  'limite': 500,
  'tope_diario': 500,
  'disponible_hoy': 500,
};

http.Response json(Object cuerpo, [int status = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(cuerpo)), status, headers: {'content-type': 'application/json'});

/// Api con un cliente HTTP simulado que guarda cada petición.
(Api, List<http.Request>) apiSimulada(Future<http.Response> Function(http.Request r) responder) {
  final peticiones = <http.Request>[];
  final api = Api('http://localhost:8020', cliente: MockClient((r) {
    peticiones.add(r);
    return responder(r);
  }))
    ..token = 'token-de-prueba';
  return (api, peticiones);
}

void main() {
  setUpAll(() => initializeDateFormatting('es'));

  group('peticiones a la API', () {
    test('buscar contacto: POST con el celular en el cuerpo, nunca en la URL', () async {
      final (api, peticiones) = apiSimulada((_) async => json({'celular': celularPrueba, 'nombre': 'Alberto Q.'}));
      final r = await buscarContacto(api, celularPrueba);
      expect(r['nombre'], 'Alberto Q.');
      final p = peticiones.single;
      expect(p.method, 'POST');
      expect(p.url.path, '/api/clientes/buscar');
      expect(p.url.toString(), isNot(contains(celularPrueba)));
      expect(jsonDecode(p.body), {'celular': celularPrueba});
      expect(p.headers['Authorization'], 'Bearer token-de-prueba');
    });

    test('un rechazo de la API muestra su mensaje (monto mayor a S/ 500)', () async {
      final (api, _) = apiSimulada((_) async => json({'error': 'El límite por operación es S/ 500'}, 400));
      final op = operacionQr(QrInfo.fromJson({'id_qr': idQr, 'tipo': 'dinamico', 'nombre': 'Bodega', 'monto': 600, 'es_comercio': true}), 600);
      await expectLater(op.ejecutar(api, '11111111-1111-4111-8111-111111111111'),
          throwsA(isA<ApiException>().having((e) => e.message, 'message', 'El límite por operación es S/ 500').having((e) => e.red, 'red', isFalse)));
    });

    test('pago con QR: la misma Idempotency-Key en el reintento tras un corte de red', () async {
      var n = 0;
      final (api, peticiones) = apiSimulada((_) async {
        if (n++ == 0) throw http.ClientException('sin red');
        return json({'id_pago': 'x', 'monto': 20, 'repetida': true});
      });
      final q = QrInfo.fromJson({'id_qr': idQr, 'tipo': 'estatico', 'nombre': 'Bodega', 'monto': null, 'es_comercio': true});
      final intento = IntentoOperacion(espera: Duration.zero);
      final r = await intento.ejecutar((llave) => operacionQr(q, 20).ejecutar(api, llave));
      expect(r['repetida'], isTrue);
      expect(peticiones, hasLength(2));
      expect(peticiones.map((p) => p.url.path).toSet(), {'/api/qr/$idQr/pagar'});
      final llaves = peticiones.map((p) => p.headers['Idempotency-Key']).toSet();
      expect(llaves, hasLength(1));
      expect(uuidRe.hasMatch(llaves.single!), isTrue);
      expect(jsonDecode(peticiones.first.body), {'monto': 20});
    });

    test('si el usuario reintenta la misma operación tras dos cortes, se repite la llave', () async {
      var cortes = 2;
      final (api, peticiones) = apiSimulada((_) async {
        if (cortes-- > 0) throw http.ClientException('sin red');
        return json({'ok': true});
      });
      final intento = IntentoOperacion(espera: Duration.zero);
      Future<dynamic> pagar() => intento.ejecutar((llave) => api.post('/qr/$idQr/pagar', {'monto': 20}, llave));
      await expectLater(pagar(), throwsA(isA<ApiException>().having((e) => e.red, 'red', isTrue)));
      await pagar();
      expect(peticiones, hasLength(3));
      expect(peticiones.map((p) => p.headers['Idempotency-Key']).toSet(), {intento.llave});
    });

    test('rechazar una solicitud manda Idempotency-Key y la repite en el reintento', () async {
      var n = 0;
      final (api, peticiones) = apiSimulada((_) async {
        if (n++ == 0) throw http.ClientException('sin red');
        return json({'ok': true, 'estado': 'rechazada'});
      });
      final st = AppState(api: api);
      await responderSolicitud(st, idSolicitud, 'rechazar', espera: Duration.zero);
      expect(peticiones, hasLength(2));
      for (final p in peticiones) {
        expect(p.url.path, '/api/solicitudes/$idSolicitud/responder');
        expect(jsonDecode(p.body), {'accion': 'rechazar'});
      }
      final llaves = peticiones.map((p) => p.headers['Idempotency-Key']).toSet();
      expect(llaves, hasLength(1));
      expect(uuidRe.hasMatch(llaves.single!), isTrue);
    });

    test('la llave de un rechazo fallido se conserva para el siguiente toque y se descarta al terminar', () async {
      var cortes = 2;
      final (api, peticiones) = apiSimulada((_) async {
        if (cortes-- > 0) throw http.ClientException('sin red');
        return json({'ok': true, 'estado': 'rechazada'});
      });
      final st = AppState(api: api);
      await expectLater(responderSolicitud(st, idSolicitud, 'rechazar', espera: Duration.zero), throwsA(isA<ApiException>()));
      await responderSolicitud(st, idSolicitud, 'rechazar', espera: Duration.zero);
      expect(peticiones.map((p) => p.headers['Idempotency-Key']).toSet(), hasLength(1));
      // Terminada, una respuesta nueva lleva otra llave.
      await responderSolicitud(st, idSolicitud, 'rechazar', espera: Duration.zero);
      expect(peticiones.map((p) => p.headers['Idempotency-Key']).toSet(), hasLength(2));
    });
  });

  group('al iniciar', () {
    test('no pide /api/promos ni /api/recientes', () async {
      SharedPreferences.setMockInitialValues({'token': 'token-de-prueba'});
      final (api, peticiones) = apiSimulada((r) async => switch (r.url.path) {
            '/api/me' => json(meJson),
            '/api/solicitudes' => json({'recibidas': [], 'enviadas': []}),
            _ => json([]),
          });
      final st = AppState(api: api);
      await st.init();
      st.dispose();
      expect(st.me?.cliente.idCliente, 'CLI000000016');
      final rutas = peticiones.map((p) => p.url.path).toSet();
      expect(rutas, containsAll(['/api/me', '/api/movimientos', '/api/solicitudes', '/api/notificaciones']));
      expect(rutas, isNot(contains('/api/promos')));
      expect(rutas, isNot(contains('/api/recientes')));
    });

    test('la caché local no guarda el celular', () {
      final me = Me.fromJson({
        ...meJson,
        'cliente': {...(meJson['cliente'] as Map<String, dynamic>), 'celular': celularPrueba},
      });
      expect(jsonEncode(me.toJson()), isNot(contains(celularPrueba)));
    });
  });

  group('pantallas', () {
    Widget conEstado(AppState st, Widget w) => ChangeNotifierProvider.value(value: st, child: MaterialApp(home: w));

    testWidgets('inicio y perfil sin tienda, ofertas, promociones, servicios ni pedidos', (t) async {
      final (api, peticiones) = apiSimulada((_) async => json([]));
      final st = AppState(api: api)..me = Me.fromJson(meJson);
      await t.pumpWidget(conEstado(st, const HomeShell()));
      expect(find.text('Enviar'), findsOneWidget);
      expect(find.text('Pagar QR'), findsOneWidget);
      for (final oculto in ['Promos', 'Ofertas', 'Tienda', 'Servicios', 'Promos para ti', 'Mis pedidos']) {
        expect(find.text(oculto, skipOffstage: false), findsNothing, reason: oculto);
      }
      // El perfil no muestra un celular ni un documento que la API no entrega.
      expect(find.text('Celular', skipOffstage: false), findsNothing);
      expect(peticiones, isEmpty);
      expect(Funciones.tienda || Funciones.promociones || Funciones.servicios || Funciones.ordenes, isFalse);
    });

    testWidgets('ingreso sin «Crear cuenta»: la billetera se activa en una agencia', (t) async {
      // Pantalla de un celular (360 × 800).
      t.view.physicalSize = const Size(1080, 2400);
      t.view.devicePixelRatio = 3;
      addTearDown(t.view.reset);
      final (api, peticiones) = apiSimulada((_) async => json({}));
      await t.pumpWidget(conEstado(AppState(api: api), const LoginScreen()));
      expect(find.text('Crear cuenta'), findsNothing);
      expect(find.text('Ingresar'), findsWidgets);
      expect(find.textContaining('agencia del BNA'), findsOneWidget);
      expect(peticiones, isEmpty);
    });
  });
}
