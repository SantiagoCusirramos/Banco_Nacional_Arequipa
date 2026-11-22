import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../services/api.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/servidor.dart';
import '../widgets/comunes.dart';

enum _Paso { elegir, probando, conectado, sinConexion }

/// Primer uso o cambio de banco: escanear la trama `CHASKI-SERVIDOR|<url>` que muestra el banco o
/// escribir la dirección. Nada se guarda hasta que el servidor responde a `/api/salud`.
class ConectarScreen extends StatefulWidget {
  const ConectarScreen({super.key});

  @override
  State<ConectarScreen> createState() => _ConectarScreenState();
}

class _ConectarScreenState extends State<ConectarScreen> {
  final _url = TextEditingController();
  _Paso _paso = _Paso.elegir;
  String? _destino;
  String _detalle = '';

  Future<void> _probar(String texto) async {
    final normalizada = parsearServidor(texto);
    if (normalizada == null) {
      setState(() {
        _paso = _Paso.elegir;
        _detalle = 'Usa una dirección http:// o https://, sin usuario ni clave';
      });
      return;
    }
    setState(() {
      _paso = _Paso.probando;
      _destino = normalizada;
      _detalle = '';
    });
    try {
      await context.read<AppState>().probarServidor(normalizada);
      if (mounted) setState(() => _paso = _Paso.conectado);
    } on ApiException catch (e) {
      if (mounted) setState(() {
        _paso = _Paso.sinConexion;
        _detalle = e.message;
      });
    }
  }

  Future<void> _escanear() async {
    final url = await Navigator.of(context).push<String>(MaterialPageRoute(builder: (_) => const _EscanearServidor()));
    if (url != null && mounted) await _probar(url);
  }

  Future<void> _continuar() async {
    final destino = _destino;
    if (destino == null) return;
    await context.read<AppState>().setServidor(destino);
    if (mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
  }

  void _cambiar() => setState(() {
        _paso = _Paso.elegir;
        _destino = null;
        _detalle = '';
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.mist,
      appBar: AppBar(title: const Text('Billetera Chaski')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
          children: [
            const Icon(Icons.account_balance_outlined, size: 60, color: C.ink2),
            const SizedBox(height: 14),
            const Text('Conectar con mi banco', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            const Text('Escanea el código que muestra la pantalla Billetera de tu banco o escribe su dirección.',
                style: TextStyle(color: C.muted)),
            const SizedBox(height: 22),
            FilledButton.icon(
              style: sunButton(),
              onPressed: _paso == _Paso.probando ? null : _escanear,
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('Escanear el código del banco'),
            ),
            const SizedBox(height: 24),
            const Text('Escribir la dirección', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            TextField(
              controller: _url,
              keyboardType: TextInputType.url,
              autocorrect: false,
              textCapitalization: TextCapitalization.none,
              decoration: const InputDecoration(hintText: 'https://servidor-del-banco:8020'),
            ),
            const SizedBox(height: 12),
            FilledButton(
              style: sunButton(),
              onPressed: _paso == _Paso.probando ? null : () => _probar(_url.text),
              child: const Text('Conectar'),
            ),
            const SizedBox(height: 20),
            if (_paso == _Paso.probando) const Center(child: CircularProgressIndicator()),
            if (_paso == _Paso.conectado) ...[
              const Text('✓ Conectado', style: TextStyle(color: C.ok, fontWeight: FontWeight.w700, fontSize: 16)),
              const SizedBox(height: 12),
              FilledButton(onPressed: _continuar, child: const Text('Continuar')),
            ],
            if (_detalle.isNotEmpty && _paso != _Paso.sinConexion)
              Text(_detalle, style: const TextStyle(color: C.danger, fontWeight: FontWeight.w600)),
            if (_paso == _Paso.sinConexion) ...[
              const Text('No pudimos conectar con el banco.', style: TextStyle(color: C.danger, fontWeight: FontWeight.w700, fontSize: 16)),
              if (_detalle.isNotEmpty) Text(_detalle, style: const TextStyle(color: C.muted)),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                    child: OutlinedButton(
                        onPressed: () => _probar(_destino ?? _url.text), child: const Text('Reintentar'))),
                const SizedBox(width: 10),
                Expanded(child: TextButton(onPressed: _cambiar, child: const Text('Cambiar de banco'))),
              ]),
            ],
          ],
        ),
      ),
    );
  }
}

class _EscanearServidor extends StatefulWidget {
  const _EscanearServidor();

  @override
  State<_EscanearServidor> createState() => _EscanearServidorState();
}

class _EscanearServidorState extends State<_EscanearServidor> {
  bool _procesando = false;

  Future<void> _detectado(BarcodeCapture cap) async {
    if (_procesando) return;
    for (final b in cap.barcodes) {
      final raw = b.rawValue ?? '';
      if (raw.isEmpty) continue;
      final url = parsearServidor(raw);
      _procesando = true;
      if (url == null) {
        toast(context, 'Código QR no reconocido o no válido');
        await Future.delayed(const Duration(seconds: 2));
        if (mounted) setState(() => _procesando = false);
      } else {
        HapticFeedback.mediumImpact();
        if (mounted) Navigator.of(context).pop(url);
      }
      return;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Escanear código del banco')),
      body: MobileScanner(
        onDetect: _detectado,
        errorBuilder: (_, __) => const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text('No pudimos usar la cámara. Revisa el permiso o escribe la dirección.', textAlign: TextAlign.center),
          ),
        ),
      ),
    );
  }
}
