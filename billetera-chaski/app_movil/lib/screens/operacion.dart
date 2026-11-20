import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../services/api.dart';
import '../services/autorizacion.dart';
import '../services/operaciones.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/comunes.dart';

/// Tipos de operación: definen títulos y textos de la constancia.
enum Modo { enviar, solicitar, qr, compra, recarga, servicio, pagoSolicitud }

/// Describe una operación lista para confirmar. [ejecutar] recibe el uuidTransaccion de idempotencia.
class Operacion {
  final Modo modo;
  final String para;
  final double monto;
  final List<(String, String)> lineas;
  final String boton;
  final Future<Map<String, dynamic>> Function(Api api, String uuid) ejecutar;

  /// Se ejecuta tras el éxito (p. ej. vaciar el carrito).
  final void Function(AppState st)? alTerminar;

  Operacion({required this.modo, required this.para, required this.monto, required this.lineas, required this.boton, required this.ejecutar, this.alTerminar});

  bool get mueveDinero => modo != Modo.solicitar;
}

/// Pantalla de confirmación → autorización (biometría o PIN) → procesando → constancia.
class ConfirmScreen extends StatefulWidget {
  final Operacion op;
  const ConfirmScreen(this.op, {super.key});

  @override
  State<ConfirmScreen> createState() => _ConfirmScreenState();
}

class _ConfirmScreenState extends State<ConfirmScreen> {
  bool _procesando = false;

  /// Un uuid de idempotencia por operación: se repite si el usuario vuelve a tocar el botón tras un
  /// fallo, así el servidor no cobra dos veces (RN-BUS-002).
  final _intento = IntentoOperacion();

  Future<void> _ejecutar() async {
    final st = context.read<AppState>();
    final op = widget.op;
    if (op.mueveDinero) {
      final ok = await Autorizacion.autorizar(context, st, 'Autoriza ${op.boton.toLowerCase()} ${soles(op.monto)}');
      if (!ok || !mounted) return;
    }
    setState(() => _procesando = true);
    final t0 = DateTime.now();
    try {
      // Ante un corte de red reintenta una vez con el mismo uuid.
      final res = await _intento.ejecutar((uuid) => op.ejecutar(st.api, uuid));
      final espera = 1400 - DateTime.now().difference(t0).inMilliseconds;
      if (espera > 0) await Future.delayed(Duration(milliseconds: espera));
      op.alTerminar?.call(st);
      await st.refrescar();
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => ExitoScreen(op: op, res: res)), (r) => r.isFirst);
    } on ApiException catch (e) {
      await Future.delayed(const Duration(milliseconds: 500));
      if (!mounted) return;
      setState(() => _procesando = false);
      toast(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_procesando) return const _Procesando();
    final st = context.watch<AppState>();
    final op = widget.op;
    final saldo = st.me?.cuenta.saldoActual ?? 0;
    final corto = op.mueveDinero && op.monto > saldo;
    final excede = op.mueveDinero && st.me != null && op.monto > st.me!.disponibleHoy;
    final error = corto
        ? 'No tienes saldo suficiente'
        : excede
            ? 'Superas tu tope diario. Hoy te quedan ${soles(st.me!.disponibleHoy)}'
            : '';
    return Scaffold(
      appBar: AppBar(title: const Text('Confirma la operación')),
      body: SafeArea(
        child: Column(children: [
          Padding(padding: const EdgeInsets.fromLTRB(20, 14, 20, 4), child: MontoGrande(op.monto.toStringAsFixed(2))),
          Expanded(
            child: ListView(children: [
              Resumen(
                lineas: [
                  ...op.lineas,
                  if (op.mueveDinero) ('Saldo después', soles(saldo - op.monto)),
                ],
                colores: {
                  for (final l in op.lineas)
                    if (l.$1.startsWith('Promo') || l.$1 == 'Ahorras') l.$1: C.ok
                },
              ),
              if (op.mueveDinero)
                const Padding(
                  padding: EdgeInsets.fromLTRB(24, 6, 24, 0),
                  child:
                      Text('Se te pedirá tu huella, rostro o PIN para autorizar.', textAlign: TextAlign.center, style: TextStyle(color: C.muted, fontSize: 13)),
                ),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 16),
            child: Column(children: [
              if (error.isNotEmpty)
                Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(error, style: const TextStyle(color: C.danger, fontWeight: FontWeight.w600))),
              FilledButton(style: sunButton(), onPressed: error.isEmpty ? _ejecutar : null, child: Text('${op.boton} ${soles(op.monto)}')),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _Procesando extends StatelessWidget {
  const _Procesando();

  @override
  Widget build(BuildContext context) {
    return const AnnotatedRegion<SystemUiOverlayStyle>(
      value: barraClara,
      child: PopScope(
        canPop: false,
        child: Scaffold(
          backgroundColor: C.ink,
          body: Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              SizedBox(width: 96, height: 96, child: CircularProgressIndicator(strokeWidth: 8, color: C.sun, backgroundColor: Color(0x2EFFFFFF))),
              SizedBox(height: 22),
              Text('Procesando…', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 18)),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Constancia animada de la operación.
class ExitoScreen extends StatefulWidget {
  final Operacion op;
  final Map<String, dynamic> res;
  const ExitoScreen({super.key, required this.op, required this.res});

  @override
  State<ExitoScreen> createState() => _ExitoScreenState();
}

class _ExitoScreenState extends State<ExitoScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: const Duration(milliseconds: 1700))..forward();

  @override
  void dispose() {
    _a.dispose();
    super.dispose();
  }

  String get _titulo => switch (widget.op.modo) {
        Modo.solicitar => 'Solicitud enviada',
        Modo.qr => '¡Pago exitoso!',
        Modo.compra => '¡Compra exitosa!',
        Modo.recarga => '¡Recarga exitosa!',
        Modo.servicio => '¡Pago exitoso!',
        _ => '¡Enviaste!',
      };

  String get _nroOp {
    final r = widget.res;
    return nroOperacion(r['id_op'] ?? r['id_transferencia'] ?? r['id_pago'] ?? r['id_pago_servicio'] ?? r['id_solicitud']);
  }

  void _compartir() {
    final r = widget.res;
    final texto = 'Constancia Chaski\n${_titulo.replaceAll('¡', '').replaceAll('!', '')}: ${soles(toD(r['monto']))}\n'
        'Para: ${r['destinatario'] ?? widget.op.para}\nOperación: $_nroOp\nFecha: ${fecha(parseFecha(r['fecha_hora']))}';
    SharePlus.instance.share(ShareParams(text: texto, subject: 'Constancia Chaski'));
  }

  Widget _aparece(double desde, Widget child) {
    final anim = CurvedAnimation(parent: _a, curve: Interval(desde, math.min(1.0, desde + .25), curve: Curves.easeOut));
    return FadeTransition(opacity: anim, child: SlideTransition(position: Tween(begin: const Offset(0, .15), end: Offset.zero).animate(anim), child: child));
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.res;
    final sol = widget.op.modo == Modo.solicitar;
    final ahorro = toD(r['ahorro']);
    final ordenes = (r['ordenes'] as List?) ?? [];
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: barraClara,
      child: PopScope(
        canPop: false,
        onPopInvokedWithResult: (didPop, _) {
          if (!didPop) Navigator.of(context).popUntil((r) => r.isFirst);
        },
        child: Scaffold(
          backgroundColor: C.ink,
          body: SafeArea(
            child: Column(children: [
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 30),
                  child: Column(children: [
                    AnimatedBuilder(animation: _a, builder: (_, __) => CustomPaint(size: const Size.square(120), painter: _CheckPainter(_a.value))),
                    const SizedBox(height: 22),
                    _aparece(.55, Text(_titulo, style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700))),
                    _aparece(
                        .6,
                        Text(soles(toD(r['monto'])),
                            style: const TextStyle(color: Colors.white, fontSize: 52, fontWeight: FontWeight.w800, letterSpacing: -1.5))),
                    _aparece(
                        .65,
                        Text('${sol ? 'Le pediste a' : 'Para'} ${r['destinatario'] ?? widget.op.para}',
                            textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70, fontSize: 16))),
                    const SizedBox(height: 26),
                    _aparece(
                      .72,
                      Resumen(margin: EdgeInsets.zero, colores: const {
                        'Ahorraste': C.ok
                      }, lineas: [
                        ('Fecha y hora', fecha(parseFecha(r['fecha_hora']))),
                        ('N.º de operación', _nroOp),
                        for (final o in ordenes) ('Retiro en ${o['tienda']}', '${o['codigo_recojo']}'),
                        if (ordenes.isEmpty && (r['referencia'] ?? '').toString().isNotEmpty) ('Mensaje', '${r['referencia']}'),
                        if (ahorro > 0) ('Ahorraste', soles(ahorro)),
                      ]),
                    ),
                  ]),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                child: Column(children: [
                  FilledButton(style: sunButton(), onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst), child: const Text('Listo')),
                  if (!sol) ...[
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(foregroundColor: Colors.white, side: const BorderSide(color: Colors.white30, width: 2)),
                      onPressed: _compartir,
                      icon: const Icon(Icons.share_outlined),
                      label: const Text('Compartir constancia'),
                    ),
                  ],
                ]),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _CheckPainter extends CustomPainter {
  final double t;
  _CheckPainter(this.t);

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final circulo = (t / .35).clamp(0.0, 1.0);
    final check = ((t - .32) / .2).clamp(0.0, 1.0);
    final rayos = ((t - .47) / .3).clamp(0.0, 1.0);
    canvas.drawArc(
        Rect.fromCircle(center: c, radius: 54),
        -math.pi / 2,
        2 * math.pi * circulo,
        false,
        Paint()
          ..color = C.sun
          ..style = PaintingStyle.stroke
          ..strokeWidth = 6);
    if (check > 0) {
      final path = Path()
        ..moveTo(36, 62)
        ..lineTo(52, 78)
        ..lineTo(84, 44);
      final metric = path.computeMetrics().first;
      canvas.drawPath(
          metric.extractPath(0, metric.length * check),
          Paint()
            ..color = Colors.white
            ..style = PaintingStyle.stroke
            ..strokeWidth = 9
            ..strokeCap = StrokeCap.round
            ..strokeJoin = StrokeJoin.round);
    }
    if (rayos > 0 && rayos < 1) {
      final op = rayos < .4 ? rayos / .4 : 1 - (rayos - .4) / .6;
      final p = Paint()
        ..color = C.sun.withValues(alpha: op)
        ..strokeWidth = 5
        ..strokeCap = StrokeCap.round;
      final escala = .6 + .65 * rayos;
      for (var i = 0; i < 8; i++) {
        final a = i * math.pi / 4 - math.pi / 2;
        final d1 = 70 * escala, d2 = 84 * escala;
        canvas.drawLine(c + Offset(math.cos(a) * d1, math.sin(a) * d1), c + Offset(math.cos(a) * d2, math.sin(a) * d2), p);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _CheckPainter old) => old.t != t;
}
