import 'package:flutter/material.dart';

import '../models.dart';
import '../theme.dart';
import '../util/format.dart';

void toast(BuildContext context, String msg) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg), duration: const Duration(milliseconds: 2600)));
}

/// Tarjeta blanca redondeada que agrupa filas (como `.lista` en la web).
class Lista extends StatelessWidget {
  final List<Widget> children;
  final EdgeInsets margin;
  const Lista({super.key, required this.children, this.margin = const EdgeInsets.symmetric(horizontal: 16)});

  @override
  Widget build(BuildContext context) {
    final items = <Widget>[];
    for (var i = 0; i < children.length; i++) {
      items.add(children[i]);
      if (i < children.length - 1) items.add(const Divider(height: 1, thickness: 1, color: C.line));
    }
    // Material (no un Container con color): los ListTile pintan su fondo y sus toques en él.
    return Padding(
      padding: margin,
      child: Material(
        color: Colors.white,
        clipBehavior: Clip.antiAlias,
        borderRadius: BorderRadius.circular(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: items),
      ),
    );
  }
}

class Seccion extends StatelessWidget {
  final String titulo;
  final String? accion;
  final VoidCallback? onAccion;
  final EdgeInsets padding;
  const Seccion(this.titulo, {super.key, this.accion, this.onAccion, this.padding = const EdgeInsets.fromLTRB(20, 22, 20, 8)});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Row(
        children: [
          Expanded(child: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 17))),
          if (accion != null)
            GestureDetector(onTap: onAccion, child: Text(accion!, style: const TextStyle(fontSize: 14, color: C.ink2, fontWeight: FontWeight.w600))),
        ],
      ),
    );
  }
}

class Vacio extends StatelessWidget {
  final String titulo, texto;
  const Vacio(this.titulo, this.texto, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 36),
      child: Column(children: [
        Text(titulo, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 4),
        Text(texto, textAlign: TextAlign.center, style: const TextStyle(color: C.muted, fontSize: 15)),
      ]),
    );
  }
}

class Avatar extends StatelessWidget {
  final String texto;
  final Color? fondo;
  final double size;
  const Avatar(this.texto, {super.key, this.fondo, this.size = 42});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: fondo ?? C.mist, shape: BoxShape.circle),
      child: Text(texto, style: TextStyle(fontWeight: FontWeight.w800, color: C.ink, fontSize: size * .42)),
    );
  }
}

class FilaMovimiento extends StatelessWidget {
  final Movimiento m;
  final VoidCallback? onTap;
  const FilaMovimiento(this.m, {super.key, this.onTap});

  @override
  Widget build(BuildContext context) {
    final pos = m.monto > 0;
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(children: [
          Avatar(m.emoji),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m.descripcion, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
              Text(fechaCorta(m.fechaHora), style: const TextStyle(fontSize: 13, color: C.muted)),
            ]),
          ),
          Text('${pos ? '+' : '−'} ${soles(m.monto.abs())}', style: TextStyle(fontWeight: FontWeight.w800, color: pos ? C.ok : C.text)),
        ]),
      ),
    );
  }
}

/// Lista de movimientos con detalle (comprobante) al tocar.
class ListaMovimientos extends StatelessWidget {
  final List<Movimiento> movs;
  const ListaMovimientos(this.movs, {super.key});

  @override
  Widget build(BuildContext context) {
    if (movs.isEmpty) return const Lista(children: [Vacio('Aún no tienes movimientos', 'Envía dinero o paga con QR para empezar.')]);
    return Lista(children: [for (final m in movs) FilaMovimiento(m, onTap: () => detalleMovimiento(context, m))]);
  }
}

void detalleMovimiento(BuildContext context, Movimiento m) {
  showModalBottomSheet(
    context: context,
    backgroundColor: C.mist,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
    builder: (_) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text('${m.monto > 0 ? '+' : '−'} ${soles(m.monto.abs())}',
              style: TextStyle(fontSize: 40, fontWeight: FontWeight.w800, color: m.monto > 0 ? C.ok : C.ink)),
          const SizedBox(height: 4),
          Text(m.descripcion, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          Resumen(lineas: [
            ('Tipo', m.tipoLegible),
            ('Fecha y hora', fecha(m.fechaHora)),
            if (m.idOperacion != null) ('N.º de operación', nroOperacion(m.idOperacion)),
            if (m.saldoResultante != null) ('Saldo resultante', soles(m.saldoResultante!)),
          ], margin: EdgeInsets.zero),
        ]),
      ),
    ),
  );
}

/// Tabla de resumen clave → valor.
class Resumen extends StatelessWidget {
  final List<(String, String)> lineas;
  final Map<String, Color> colores;
  final EdgeInsets margin;
  const Resumen({super.key, required this.lineas, this.colores = const {}, this.margin = const EdgeInsets.symmetric(horizontal: 16, vertical: 8)});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
      child: Column(children: [
        for (var i = 0; i < lineas.length; i++)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 14),
            decoration: BoxDecoration(border: i < lineas.length - 1 ? const Border(bottom: BorderSide(color: C.line)) : null),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(lineas[i].$1, style: const TextStyle(color: C.muted)),
              const SizedBox(width: 16),
              Expanded(
                child: Text(lineas[i].$2, textAlign: TextAlign.right, style: TextStyle(fontWeight: FontWeight.w700, color: colores[lineas[i].$1] ?? C.text)),
              ),
            ]),
          ),
      ]),
    );
  }
}

/// Chip seleccionable (`.ch` en la web).
class Opcion extends StatelessWidget {
  final String texto;
  final bool on;
  final VoidCallback onTap;
  const Opcion(this.texto, {super.key, required this.on, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: on ? C.ink : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: on ? C.ink : C.line, width: 2),
        ),
        child: Text(texto, style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: on ? Colors.white : C.text)),
      ),
    );
  }
}

/// Selector de dos pestañas (`.tabs` en la web).
class DosTabs extends StatelessWidget {
  final String a, b;
  final bool enA;
  final ValueChanged<bool> onChange;
  const DosTabs({super.key, required this.a, required this.b, required this.enA, required this.onChange});

  @override
  Widget build(BuildContext context) {
    Widget tab(String t, bool on, bool valor) => Expanded(
          child: GestureDetector(
            onTap: () => onChange(valor),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              padding: const EdgeInsets.symmetric(vertical: 10),
              alignment: Alignment.center,
              decoration: BoxDecoration(color: on ? C.ink : Colors.transparent, borderRadius: BorderRadius.circular(11)),
              child: Text(t, style: TextStyle(fontWeight: FontWeight.w600, color: on ? Colors.white : C.muted)),
            ),
          ),
        );
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
      child: Row(children: [tab(a, enA, true), tab(b, !enA, false)]),
    );
  }
}

/// Teclado numérico para montos.
class TecladoMonto extends StatelessWidget {
  final ValueChanged<String> onKey;
  const TecladoMonto({super.key, required this.onKey});

  @override
  Widget build(BuildContext context) {
    const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '⌫'];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
      child: GridView.count(
        crossAxisCount: 3,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        childAspectRatio: 2.1,
        mainAxisSpacing: 6,
        crossAxisSpacing: 6,
        children: [
          for (final k in keys)
            Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(16),
                onTap: () => onKey(k),
                child: Center(
                  child: k == '⌫'
                      ? const Icon(Icons.backspace_outlined, semanticLabel: 'Borrar')
                      : Text(k, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w600)),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Monto grande "S/ 0.00".
class MontoGrande extends StatelessWidget {
  final String valor;
  final Color color;
  const MontoGrande(this.valor, {super.key, this.color = C.ink});

  @override
  Widget build(BuildContext context) {
    return FittedBox(
      fit: BoxFit.scaleDown,
      child: Text.rich(TextSpan(children: [
        const TextSpan(text: 'S/ ', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w600, color: C.muted)),
        TextSpan(text: valor, style: TextStyle(fontSize: 60, fontWeight: FontWeight.w800, letterSpacing: -1.5, color: color)),
      ])),
    );
  }
}

/// Logo de Chaski dibujado (flecha amarilla + punto turquesa sobre morado).
class LogoChaski extends StatelessWidget {
  final double size;
  const LogoChaski({super.key, this.size = 56});

  @override
  Widget build(BuildContext context) => CustomPaint(size: Size.square(size), painter: _LogoPainter());
}

class _LogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 512;
    canvas.scale(s);
    canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(0, 0, 512, 512), const Radius.circular(110)), Paint()..color = C.ink2);
    final trazo = Paint()
      ..color = C.sun
      ..style = PaintingStyle.stroke
      ..strokeWidth = 44
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final curva = Path()
      ..moveTo(150, 330)
      ..cubicTo(150, 260, 200, 210, 270, 210)
      ..lineTo(362, 210);
    canvas.drawPath(curva, trazo);
    canvas.drawPath(
        Path()
          ..moveTo(312, 150)
          ..lineTo(372, 210)
          ..lineTo(312, 270),
        trazo);
    canvas.drawCircle(const Offset(150, 345), 26, Paint()..color = C.teal);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
