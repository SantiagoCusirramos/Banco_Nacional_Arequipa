import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:local_auth/local_auth.dart';

import '../state/app_state.dart';
import '../theme.dart';
import 'api.dart';

/// Autoriza una operación de dinero con huella / rostro del celular y, si no hay biometría, con el PIN de 6 dígitos.
class Autorizacion {
  static final _auth = LocalAuthentication();

  static Future<bool> autorizar(BuildContext context, AppState st, String motivo) async {
    if (st.usarBiometria) {
      try {
        final soporta = await _auth.isDeviceSupported();
        final inscrita = soporta && (await _auth.getAvailableBiometrics()).isNotEmpty;
        if (inscrita) {
          final ok = await _auth.authenticate(localizedReason: motivo);
          if (ok) return true;
        }
      } on PlatformException catch (_) {
        // sin biometría disponible: seguimos con el PIN
      } on LocalAuthException catch (_) {
        // cancelada o no disponible: seguimos con el PIN
      }
    }
    if (!context.mounted) return false;
    return await pedirPin(context, st) ?? false;
  }

  static Future<bool?> pedirPin(BuildContext context, AppState st) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.mist,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (_) => _PinSheet(st: st),
    );
  }
}

class _PinSheet extends StatefulWidget {
  final AppState st;
  const _PinSheet({required this.st});

  @override
  State<_PinSheet> createState() => _PinSheetState();
}

class _PinSheetState extends State<_PinSheet> {
  final _pin = TextEditingController();
  String? _error;
  bool _enviando = false;

  Future<void> _verificar() async {
    if (!RegExp(r'^\d{6}$').hasMatch(_pin.text)) {
      setState(() => _error = 'Ingresa tu PIN de 6 dígitos');
      return;
    }
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      await widget.st.api.post('/pin/verificar', {'pin': _pin.text});
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() {
        _enviando = false;
        _error = e.message;
        _pin.clear();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 22, 20, MediaQuery.of(context).viewInsets.bottom + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Confirma con tu PIN', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Ingresa tu PIN de 6 dígitos para autorizar la operación.', style: TextStyle(color: C.muted)),
          const SizedBox(height: 16),
          TextField(
            controller: _pin,
            autofocus: true,
            obscureText: true,
            keyboardType: TextInputType.number,
            maxLength: 6,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 26, letterSpacing: 12, fontWeight: FontWeight.w700),
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            onChanged: (_) => setState(() => _error = null),
          ),
          SizedBox(height: 22, child: Text(_error ?? '', style: const TextStyle(color: C.danger, fontWeight: FontWeight.w600))),
          FilledButton(
              style: sunButton(),
              onPressed: _enviando || !RegExp(r'^\d{6}$').hasMatch(_pin.text) ? null : _verificar,
              child: Text(_enviando ? 'Verificando…' : 'Autorizar')),
        ],
      ),
    );
  }
}
