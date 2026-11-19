import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/comunes.dart';

/// Ingreso con celular + PIN y enrolamiento de una cuenta nueva (RF-BD-005).
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _registro = false;
  bool _enviando = false;
  bool _terminos = false;
  String _error = '';
  final _nombres = TextEditingController();
  final _apellidos = TextEditingController();
  final _dni = TextEditingController();
  final _email = TextEditingController();
  final _cel = TextEditingController();
  final _pin = TextEditingController();
  final _pin2 = TextEditingController();

  Future<void> _enviar() async {
    final st = context.read<AppState>();
    setState(() => _error = '');
    if (_registro) {
      if (_pin.text != _pin2.text) return setState(() => _error = 'Los PIN no coinciden');
      if (!_terminos) return setState(() => _error = 'Debes aceptar los términos y condiciones');
    }
    setState(() => _enviando = true);
    try {
      if (_registro) {
        await st.registro({
          'tipo_documento': 'DNI',
          'numero_documento': _dni.text.trim(),
          'nombres': _nombres.text.trim(),
          'apellidos': _apellidos.text.trim(),
          'email': _email.text.trim(),
          'celular': _cel.text.trim(),
          'pin': _pin.text.trim(),
          'acepta_terminos': _terminos,
        });
      } else {
        await st.login(_cel.text.trim(), _pin.text.trim());
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  void _configServidor() {
    final st = context.read<AppState>();
    final ctrl = TextEditingController(text: st.servidor);
    showDialog(
      context: context,
      builder: (ctx) {
        String estado = '';
        return StatefulBuilder(
          builder: (ctx, setD) => AlertDialog(
            title: const Text('Servidor de Chaski'),
            content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Emulador: http://10.0.2.2:8020\nCelular real: http://IP-del-servidor:8020', style: TextStyle(color: C.muted, fontSize: 13)),
              const SizedBox(height: 12),
              TextField(controller: ctrl, keyboardType: TextInputType.url, decoration: const InputDecoration(hintText: 'http://IP-del-servidor:8020')),
              const SizedBox(height: 8),
              Text(estado, style: TextStyle(color: estado.startsWith('✓') ? C.ok : C.danger, fontWeight: FontWeight.w600)),
            ]),
            actions: [
              TextButton(
                onPressed: () async {
                  await st.setServidor(ctrl.text);
                  setD(() => estado = 'Probando…');
                  try {
                    await st.probarServidor();
                    setD(() => estado = '✓ Conectado');
                  } on ApiException catch (e) {
                    setD(() => estado = e.message);
                  }
                },
                child: const Text('Probar'),
              ),
              FilledButton(
                style: smallButton(),
                onPressed: () async {
                  await st.setServidor(ctrl.text);
                  if (ctx.mounted) Navigator.pop(ctx);
                },
                child: const Text('Guardar'),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _campo(String label, TextEditingController c, {int? max, bool numero = false, bool oculto = false, String? hint, TextInputType? teclado}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        TextField(
          controller: c,
          maxLength: max,
          obscureText: oculto,
          keyboardType: teclado ?? (numero ? TextInputType.number : TextInputType.name),
          inputFormatters: numero ? [FilteringTextInputFormatter.digitsOnly] : null,
          textCapitalization: numero ? TextCapitalization.none : TextCapitalization.words,
          decoration: InputDecoration(hintText: hint),
          style: const TextStyle(fontSize: 17),
        ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: barraClara,
      child: Scaffold(
        backgroundColor: C.ink,
        body: SafeArea(
          bottom: false,
          child: Column(children: [
            Align(
              alignment: Alignment.topRight,
              child: IconButton(onPressed: _configServidor, icon: const Icon(Icons.settings_outlined, color: Colors.white70), tooltip: 'Servidor'),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(28, 0, 28, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const LogoChaski(),
                const SizedBox(height: 14),
                const Text('Chaski', style: TextStyle(color: Colors.white, fontSize: 44, fontWeight: FontWeight.w800, letterSpacing: -1.2)),
                const SizedBox(height: 6),
                Text('Envía y recibe dinero al instante, solo con un celular.', style: TextStyle(color: Colors.white.withValues(alpha: .8), fontSize: 16)),
              ]),
            ),
            const SizedBox(height: 14),
            Expanded(
              child: Container(
                width: double.infinity,
                decoration: const BoxDecoration(color: C.mist, borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
                child: ListView(
                  padding: EdgeInsets.fromLTRB(20, 22, 20, MediaQuery.of(context).padding.bottom + 24),
                  children: [
                    DosTabs(
                        a: 'Ingresar',
                        b: 'Crear cuenta',
                        enA: !_registro,
                        onChange: (a) => setState(() {
                              _registro = !a;
                              _error = '';
                            })),
                    const SizedBox(height: 14),
                    if (_registro) ...[
                      Row(children: [
                        Expanded(child: _campo('Nombres', _nombres)),
                        const SizedBox(width: 10),
                        Expanded(child: _campo('Apellidos', _apellidos)),
                      ]),
                      _campo('DNI', _dni, max: 8, numero: true),
                      _campo('Correo (opcional)', _email, teclado: TextInputType.emailAddress),
                    ],
                    _campo('Celular', _cel, max: 9, numero: true, hint: '9XXXXXXXX'),
                    _campo('PIN de 6 dígitos', _pin, max: 6, numero: true, oculto: true),
                    if (_registro) ...[
                      _campo('Repite tu PIN', _pin2, max: 6, numero: true, oculto: true),
                      CheckboxListTile(
                        value: _terminos,
                        onChanged: (v) => setState(() => _terminos = v ?? false),
                        contentPadding: EdgeInsets.zero,
                        controlAffinity: ListTileControlAffinity.leading,
                        title: const Text('Acepto los términos y condiciones y el tratamiento de mis datos personales', style: TextStyle(fontSize: 14)),
                      ),
                    ],
                    SizedBox(height: 22, child: Text(_error, style: const TextStyle(color: C.danger, fontWeight: FontWeight.w600))),
                    FilledButton(
                        style: sunButton(),
                        onPressed: _enviando ? null : _enviar,
                        child: Text(_enviando
                            ? 'Un momento…'
                            : _registro
                                ? 'Crear mi cuenta'
                                : 'Ingresar')),
                    const SizedBox(height: 10),
                    Text(_registro ? 'Recibirás S/ 100 de saldo de prueba.' : 'Demo: 900000001 · PIN 123456',
                        style: const TextStyle(fontSize: 13, color: C.muted)),
                  ],
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}
