// Bloque 6b de usabilidad: conectar con el banco, PIN y hora de Lima.
// Los nombres de servidor y los PIN son de prueba.
import 'dart:convert';

import 'package:chaski_app/main.dart';
import 'package:chaski_app/screens/conectar_screen.dart';
import 'package:chaski_app/services/api.dart';
import 'package:chaski_app/services/autorizacion.dart';
import 'package:chaski_app/state/app_state.dart';
import 'package:chaski_app/util/format.dart';
import 'package:chaski_app/util/servidor.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

final meJson = {
  'cliente': {'id_cliente': 'CLI000000016', 'nombres': 'Rosa H.', 'apellidos': '', 'nombre_corto': 'Rosa H.'},
  'cuenta': {'id_cuenta': 'CTA-0000000000000001', 'numero_cuenta_virtual': 'CTA-0000000000000001', 'saldo_actual': 1000, 'moneda': 'PEN'},
  'no_leidas': 0,
  'pendientes': 0,
  'limite': 500,
  'tope_diario': 500,
  'disponible_hoy': 500,
};

http.Response jsonResp(Object cuerpo, [int status = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(cuerpo)), status, headers: {'content-type': 'application/json'});

(Api, List<http.Request>) apiSimulada(Future<http.Response> Function(http.Request r) responder) {
  final peticiones = <http.Request>[];
  final api = Api('http://localhost:8020', cliente: MockClient((r) {
    peticiones.add(r);
    return responder(r);
  }));
  return (api, peticiones);
}

Widget conEstado(AppState st, Widget w) => ChangeNotifierProvider.value(value: st, child: MaterialApp(home: w));

void main() {
  setUpAll(() => initializeDateFormatting('es'));

  group('trama de configuración del banco', () {
    test('una trama válida da la URL sin barra final', () {
      expect(parsearServidor('CHASKI-SERVIDOR|https://banco.ejemplo.com:8020/'), 'https://banco.ejemplo.com:8020');
    });

    test('acepta espacios y normaliza el esquema en mayúsculas', () {
      expect(parsearServidor('  CHASKI-SERVIDOR | Https://Banco.Ejemplo:8020/  '), 'https://banco.ejemplo:8020');
    });

    test('rechaza URL sin esquema, ftp y credenciales', () {
      expect(parsearServidor('CHASKI-SERVIDOR|banco.ejemplo:8020'), isNull);
      expect(parsearServidor('CHASKI-SERVIDOR|ftp://banco.ejemplo:8020'), isNull);
      expect(parsearServidor('CHASKI-SERVIDOR|https://usuario:clave@banco.ejemplo:8020'), isNull);
    });

    test('otra trama no configura el servidor', () {
      expect(parsearServidor('CHASKI|a5db6a6f-6de7-4e6f-9c7b-af6e43a06fcc'), isNull);
      expect(parsearServidor('CHASKI-SERVIDOR'), isNull);
    });

    test('también normaliza una dirección escrita a mano', () {
      expect(parsearServidor('HTTP://Banco.Ejemplo:8020'), 'http://banco.ejemplo:8020');
    });
  });

  group('conectar con mi banco', () {
    testWidgets('primer uso sin servidor guardado muestra la pantalla de conexión', (t) async {
      SharedPreferences.setMockInitialValues({});
      final (api, peticiones) = apiSimulada((_) async => jsonResp({}));
      final st = AppState(api: api);
      await st.init();
      await t.pumpWidget(conEstado(st, const ChaskiApp()));
      await t.pumpAndSettle();
      expect(find.text('Conectar con mi banco'), findsOneWidget);
      expect(find.text('Escanear el código del banco'), findsOneWidget);
      expect(find.text('Escribir la dirección'), findsOneWidget);
      expect(peticiones, isEmpty);
      st.dispose();
    });

    testWidgets('probando una dirección no se guarda hasta que responde', (t) async {
      SharedPreferences.setMockInitialValues({});
      final (api, peticiones) = apiSimulada((r) async {
        expect(r.url.path, '/api/salud');
        return jsonResp({});
      });
      final st = AppState(api: api);
      await st.init();
      await t.pumpWidget(conEstado(st, const ConectarScreen()));
      await t.pumpAndSettle();
      await t.enterText(find.byType(TextField), 'Https://Banco.Ejemplo:8020/');
      await t.tap(find.text('Conectar'));
      await t.pumpAndSettle();
      expect(peticiones.single.url.toString(), 'https://banco.ejemplo:8020/api/salud');
      expect(find.text('✓ Conectado'), findsOneWidget);
      await t.tap(find.text('Continuar'));
      await t.pumpAndSettle();
      expect(st.servidor, 'https://banco.ejemplo:8020');
      st.dispose();
    });

    testWidgets('sin conexión ofrece Reintentar y Cambiar de banco', (t) async {
      SharedPreferences.setMockInitialValues({'servidor': 'http://banco.ejemplo:8020'});
      var fallos = 1;
      final (api, peticiones) = apiSimulada((r) async {
        if (r.url.path == '/api/salud') {
          if (fallos-- > 0) throw http.ClientException('sin red');
          return jsonResp({});
        }
        return switch (r.url.path) {
          '/api/me' => jsonResp(meJson),
          '/api/solicitudes' => jsonResp({'recibidas': [], 'enviadas': []}),
          _ => jsonResp([]),
        };
      });
      final st = AppState(api: api);
      await st.init();
      await t.pumpWidget(conEstado(st, const ChaskiApp()));
      await t.pumpAndSettle();
      expect(find.text('No pudimos conectar con el banco.'), findsOneWidget);
      expect(find.text('Cambiar de banco'), findsOneWidget);
      final antes = peticiones.where((p) => p.url.path == '/api/salud').length;
      await t.tap(find.text('Reintentar'));
      await t.pumpAndSettle();
      expect(peticiones.where((p) => p.url.path == '/api/salud').length, antes + 1);
      expect(find.text('No pudimos conectar con el banco.'), findsNothing);
      expect(find.text('Ingresar'), findsWidgets);
      st.dispose();
    });

    testWidgets('Cambiar de banco abre la pantalla de conexión', (t) async {
      SharedPreferences.setMockInitialValues({'servidor': 'http://banco.ejemplo:8020'});
      final (api, _) = apiSimulada((_) async => throw http.ClientException('sin red'));
      final st = AppState(api: api);
      await st.init();
      await t.pumpWidget(conEstado(st, const ChaskiApp()));
      await t.pumpAndSettle();
      await t.tap(find.text('Cambiar de banco'));
      await t.pumpAndSettle();
      expect(find.text('Conectar con mi banco'), findsOneWidget);
      st.dispose();
    });
  });

  testWidgets('el PIN solo se envía al tocar Autorizar', (t) async {
    final (api, peticiones) = apiSimulada((_) async => jsonResp({}));
    final st = AppState(api: api);
    await t.pumpWidget(conEstado(
        st,
        Scaffold(
            body: Builder(
                builder: (ctx) => FilledButton(onPressed: () => Autorizacion.pedirPin(ctx, st), child: const Text('Abrir PIN'))))));
    await t.tap(find.text('Abrir PIN'));
    await t.pumpAndSettle();
    final autorizar = find.widgetWithText(FilledButton, 'Autorizar');
    expect(t.widget<FilledButton>(autorizar).onPressed, isNull);
    await t.enterText(find.byType(TextField).last, '246810');
    await t.pump();
    expect(peticiones, isEmpty, reason: 'no se envía al escribir el sexto dígito');
    expect(t.widget<FilledButton>(autorizar).onPressed, isNotNull);
    await t.tap(autorizar);
    await t.pumpAndSettle();
    expect(peticiones.single.url.path, '/api/pin/verificar');
    expect(jsonDecode(peticiones.single.body), {'pin': '246810'});
  });

  test('una fecha UTC se muestra en hora de Lima (UTC−5, sin verano)', () {
    expect(fecha(DateTime.utc(2026, 11, 22, 14, 57)), contains('09:57'));
    expect(fechaCorta(DateTime.utc(2026, 11, 22, 14, 57)), contains('09:57'));
    expect(dia(DateTime.utc(2026, 11, 22, 5, 30)), '22 nov');
    expect(fecha(DateTime.utc(2026, 1, 15, 3, 0)), contains('14 ene 2026'));
    expect(fecha(parseFecha('2026-11-22T14:57:00')), contains('09:57'));
  });
}
