import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'screens/conectar_screen.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'services/api.dart';
import 'state/app_state.dart';
import 'theme.dart';
import 'widgets/comunes.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('es');
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  final st = AppState();
  runApp(ChangeNotifierProvider.value(value: st, child: const ChaskiApp()));
  await st.init();
}

class ChaskiApp extends StatelessWidget {
  const ChaskiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Chaski',
      debugShowCheckedModeBanner: false,
      theme: chaskiTheme(),
      locale: const Locale('es', 'PE'),
      supportedLocales: const [Locale('es', 'PE'), Locale('es')],
      localizationsDelegates: const [GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate],
      home: const _Raiz(),
    );
  }
}

/// Decide qué mostrar según la sesión: carga → ingreso → billetera.
class _Raiz extends StatelessWidget {
  const _Raiz();

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    if (st.iniciando) {
      return const Scaffold(backgroundColor: C.ink, body: Center(child: LogoChaski(size: 88)));
    }
    if (st.necesitaServidor) return const ConectarScreen();
    if (st.servidorSinConexion || (st.token != null && st.me == null)) return const _SinConexion();
    return st.logueado ? const HomeShell() : const LoginScreen();
  }
}

class _SinConexion extends StatefulWidget {
  const _SinConexion();

  @override
  State<_SinConexion> createState() => _SinConexionState();
}

class _SinConexionState extends State<_SinConexion> {
  bool _cargando = false;

  @override
  Widget build(BuildContext context) {
    final st = context.read<AppState>();
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Icon(Icons.cloud_off, size: 64, color: C.muted),
            const SizedBox(height: 16),
            const Text('No pudimos conectar con el banco.', textAlign: TextAlign.center, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Text('Revisa tu conexión o la dirección del servidor (${st.servidor}).', textAlign: TextAlign.center, style: const TextStyle(color: C.muted)),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _cargando ? null : _reintentar,
              child: Text(_cargando ? 'Reintentando…' : 'Reintentar'),
            ),
            const SizedBox(height: 10),
            OutlinedButton(onPressed: () => st.cambiarBanco(), child: const Text('Cambiar de banco')),
          ]),
        ),
      ),
    );
  }

  Future<void> _reintentar() async {
    setState(() => _cargando = true);
    final st = context.read<AppState>();
    try {
      await st.probarServidor();
      st.servidorSinConexion = false;
      if (st.token != null) await st.refrescar();
    } on ApiException {
      st.servidorSinConexion = true;
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }
}
