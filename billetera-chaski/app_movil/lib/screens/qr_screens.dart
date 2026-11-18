import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../models.dart';
import '../services/api.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/comunes.dart';
import 'operacion.dart';

/// Abre el flujo de pago de un QR por su id (escaneado, digitado o elegido de la lista).
Future<void> abrirPagoQr(BuildContext context, int idQr, {bool reemplazar = false}) async {
  final st = context.read<AppState>();
  try {
    final q = QrInfo.fromJson(Map<String, dynamic>.from(await st.api.get('/qr/$idQr')));
    if (!context.mounted) return;
    final destino = q.dinamico ? ConfirmScreen(operacionQr(q, q.monto!)) : MontoQrScreen(qr: q);
    final ruta = MaterialPageRoute(builder: (_) => destino);
    reemplazar ? Navigator.pushReplacement(context, ruta) : Navigator.push(context, ruta);
  } on ApiException catch (e) {
    if (context.mounted) toast(context, e.message);
  }
}

Operacion operacionQr(QrInfo q, double monto) {
  final desc = q.promo?.descuento(monto) ?? 0;
  final pagar = r2(monto - desc);
  return Operacion(
    modo: Modo.qr,
    para: q.nombre,
    monto: pagar,
    boton: 'Pagar',
    lineas: [
      ('Para', q.nombre),
      if (desc > 0) ('Monto', soles(monto)),
      if (desc > 0) ('Promo −${q.promo!.pct}%', '−${soles(desc)}'),
      ('Tipo de QR', q.dinamico ? 'Con monto (se paga una vez)' : 'Fijo'),
    ],
    ejecutar: (api, uuid) async => Map<String, dynamic>.from(await api.post('/qr/${q.idQr}/pagar', {'monto': monto}, uuid)),
  );
}

/// Escanear un QR para pagar o mostrar "Mi QR" para cobrar.
class QrScreen extends StatefulWidget {
  final bool mio;
  const QrScreen({super.key, this.mio = false});

  @override
  State<QrScreen> createState() => _QrScreenState();
}

class _QrScreenState extends State<QrScreen> {
  late bool _mio = widget.mio;
  final _codigo = TextEditingController();
  final _montoQr = TextEditingController();
  List<Map<String, dynamic>> _comercios = [];
  Map<String, dynamic>? _miQr;
  String? _errorQr;
  bool _procesando = false;

  @override
  void initState() {
    super.initState();
    final api = context.read<AppState>().api;
    api.get('/comercios').then((r) {
      if (mounted) setState(() => _comercios = List<Map<String, dynamic>>.from(r));
    }).catchError((_) {});
    _generar();
  }

  Future<void> _generar([double? monto]) async {
    setState(() {
      _miQr = null;
      _errorQr = null;
    });
    try {
      final q = await context.read<AppState>().api.post('/qr', monto != null ? {'monto': monto} : {});
      if (mounted) setState(() => _miQr = Map<String, dynamic>.from(q));
    } on ApiException catch (e) {
      if (mounted) setState(() => _errorQr = e.message);
    }
  }

  Future<void> _detectado(BarcodeCapture cap) async {
    if (_procesando) return;
    for (final b in cap.barcodes) {
      final raw = b.rawValue ?? '';
      final m = qrRe.firstMatch(raw);
      if (m != null) {
        _procesando = true;
        HapticFeedback.mediumImpact();
        await abrirPagoQr(context, int.parse(m.group(1)!), reemplazar: true);
        _procesando = false;
        return;
      }
      if (raw.isNotEmpty) {
        _procesando = true;
        toast(context, 'Código QR no reconocido o no válido');
        await Future.delayed(const Duration(seconds: 2));
        _procesando = false;
        return;
      }
    }
  }

  Widget _escanear() {
    return ListView(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(20, 8, 20, 8),
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(24)),
        child: AspectRatio(
          aspectRatio: 1,
          child: Stack(fit: StackFit.expand, children: [
            MobileScanner(
              onDetect: _detectado,
              errorBuilder: (ctx, err) => const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('No pudimos usar la cámara. Revisa el permiso o ingresa el código.',
                      textAlign: TextAlign.center, style: TextStyle(color: Colors.white)),
                ),
              ),
            ),
            IgnorePointer(
              child: Container(
                margin: const EdgeInsets.all(56),
                decoration: BoxDecoration(border: Border.all(color: C.sun, width: 4), borderRadius: BorderRadius.circular(22)),
              ),
            ),
          ]),
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('¿Sin cámara? Ingresa el código', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          TextField(
              controller: _codigo,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: const InputDecoration(hintText: 'Código del QR')),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () {
              final c = int.tryParse(_codigo.text.trim());
              if (c == null) return toast(context, 'Ingresa el código numérico');
              abrirPagoQr(context, c, reemplazar: true);
            },
            child: const Text('Continuar'),
          ),
        ]),
      ),
      if (_comercios.isNotEmpty) ...[
        const Seccion('Comercios afiliados', padding: EdgeInsets.fromLTRB(20, 0, 20, 8)),
        Lista(children: [
          for (final c in _comercios)
            ListTile(
              leading: Avatar(inicial(c['nombre'])),
              title: Text(c['nombre'], style: const TextStyle(fontWeight: FontWeight.w600)),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => abrirPagoQr(context, c['id_qr'], reemplazar: true),
            ),
        ]),
        const SizedBox(height: 30),
      ],
    ]);
  }

  Widget _miCodigo() {
    final me = context.watch<AppState>().me!;
    final q = _miQr;
    return ListView(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(20, 8, 20, 8),
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)),
        child: q == null
            ? SizedBox(height: 260, child: Center(child: _errorQr != null ? Text(_errorQr!, textAlign: TextAlign.center) : const CircularProgressIndicator()))
            : Column(children: [
                QrImageView(
                    data: tramaQr(q['id_qr']),
                    size: 240,
                    eyeStyle: const QrEyeStyle(eyeShape: QrEyeShape.square, color: C.ink),
                    dataModuleStyle: const QrDataModuleStyle(dataModuleShape: QrDataModuleShape.square, color: C.ink)),
                const SizedBox(height: 10),
                Text(me.cliente.nombreCompleto, style: const TextStyle(fontWeight: FontWeight.w600)),
                Text(q['monto'] != null ? 'Cobro de ${soles(toD(q['monto']))} · vence en 15 min' : 'Pídeles que lo escaneen para pagarte',
                    style: const TextStyle(color: C.muted, fontSize: 14)),
                const SizedBox(height: 6),
                Text.rich(TextSpan(
                    text: 'Código: ',
                    style: const TextStyle(color: C.muted, fontSize: 13),
                    children: [TextSpan(text: '${q['id_qr']}', style: const TextStyle(fontWeight: FontWeight.w700, color: C.text))])),
              ]),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Cobrar un monto exacto (opcional)', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          TextField(
              controller: _montoQr, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(hintText: 'S/ 0.00')),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () {
              final v = double.tryParse(_montoQr.text.replaceAll(',', '.'));
              if (v == null || v <= 0) return toast(context, 'Ingresa un monto válido');
              FocusScope.of(context).unfocus();
              _generar(r2(v));
            },
            child: const Text('Generar QR con monto'),
          ),
          if (q?['monto'] != null) TextButton(onPressed: () => _generar(), child: const Text('Volver a mi QR fijo')),
        ]),
      ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(leading: const CloseButton(), title: const Text('Código QR')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 4),
          child: DosTabs(a: 'Escanear', b: 'Mi QR', enA: !_mio, onChange: (a) => setState(() => _mio = !a)),
        ),
        Expanded(child: _mio ? _miCodigo() : _escanear()),
      ]),
    );
  }
}

/// Monto para un QR fijo (de comercio o persona).
class MontoQrScreen extends StatefulWidget {
  final QrInfo qr;
  const MontoQrScreen({super.key, required this.qr});

  @override
  State<MontoQrScreen> createState() => _MontoQrScreenState();
}

class _MontoQrScreenState extends State<MontoQrScreen> {
  String _monto = '';

  @override
  Widget build(BuildContext context) {
    final me = context.watch<AppState>().me!;
    final q = widget.qr;
    final n = double.tryParse(_monto) ?? 0;
    final pagar = n - (q.promo?.descuento(n) ?? 0);
    var ok = n > 0;
    String hint;
    if (n > me.limite) {
      hint = 'El límite por operación es ${soles(me.limite)}';
      ok = false;
    } else if (pagar > me.cuenta.saldoActual) {
      hint = 'No tienes saldo suficiente';
      ok = false;
    } else if (pagar > me.disponibleHoy) {
      hint = 'Tu tope diario restante es ${soles(me.disponibleHoy)}';
      ok = false;
    } else if (q.promo != null && n > 0) {
      hint = 'Con tu promo −${q.promo!.pct}% pagas ${soles(pagar)}';
    } else if (q.promo != null) {
      hint = 'Promo −${q.promo!.pct}%: se descuenta al pagar';
    } else {
      hint = 'Saldo ${soles(me.cuenta.saldoActual)}';
    }
    return Scaffold(
      appBar: AppBar(title: Text('Pagar a ${q.nombre}')),
      body: SafeArea(
        child: Column(children: [
          const SizedBox(height: 10),
          if (q.esComercio)
            const Chip(
                avatar: Icon(Icons.verified, color: C.teal, size: 18), label: Text('Comercio afiliado'), backgroundColor: Colors.white, side: BorderSide.none),
          MontoGrande(_monto.isEmpty ? '0' : _monto),
          Text(hint, style: TextStyle(color: ok || n == 0 ? (q.promo != null ? C.ok : C.muted) : C.danger, fontSize: 14, fontWeight: FontWeight.w600)),
          const Spacer(),
          TecladoMonto(onKey: (k) => setState(() => _monto = teclear(_monto, k))),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 16),
            child: FilledButton(
              style: sunButton(),
              onPressed: ok ? () => Navigator.push(context, MaterialPageRoute(builder: (_) => ConfirmScreen(operacionQr(q, r2(n))))) : null,
              child: const Text('Continuar'),
            ),
          ),
        ]),
      ),
    );
  }
}
