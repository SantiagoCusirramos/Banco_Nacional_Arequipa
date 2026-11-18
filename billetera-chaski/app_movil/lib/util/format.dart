import 'dart:math' as math;

import 'package:intl/intl.dart';

String soles(num n) => 'S/ ${n.toStringAsFixed(2)}';

double r2(num n) => (n * 100).roundToDouble() / 100;

double toD(dynamic v) => v == null ? 0 : (v is num ? v.toDouble() : double.tryParse('$v') ?? 0);

final _fecha = DateFormat('dd MMM yyyy, HH:mm', 'es');
final _fechaCorta = DateFormat('dd MMM, HH:mm', 'es');
final _dia = DateFormat('dd MMM', 'es');
final _diaLargo = DateFormat("d 'de' MMMM", 'es');

String fecha(DateTime d) => _fecha.format(d.toLocal());
String fechaCorta(DateTime d) => _fechaCorta.format(d.toLocal());
String dia(DateTime d) => _dia.format(d.toLocal());
String diaLargo(DateTime d) => _diaLargo.format(d.toLocal());

DateTime parseFecha(dynamic v) => v == null ? DateTime.now() : DateTime.tryParse('$v') ?? DateTime.now();

String inicial(String n) {
  final t = n.trim();
  return t.isEmpty ? '?' : t[0].toUpperCase();
}

String nroOperacion(dynamic id) => '${id ?? 0}'.padLeft(8, '0');

/// Tiempo restante de una oferta, igual que en la web.
String restante(DateTime fin) {
  final ms = math.max(0, fin.difference(DateTime.now()).inMilliseconds);
  final h = ms ~/ 3600000;
  if (h >= 24) return 'termina en ${h ~/ 24} d ${h % 24} h';
  if (h >= 1) return 'termina en $h h ${(ms % 3600000) ~/ 60000} min';
  return 'termina en ${math.max(1, ms ~/ 60000)} min';
}

final celularRe = RegExp(r'^9\d{8}$');

/// Lógica del teclado numérico de montos (máx. 3 enteros y 2 decimales).
String teclear(String v, String k) {
  if (k == '⌫') return v.isEmpty ? v : v.substring(0, v.length - 1);
  if (k == '.') return v.contains('.') ? v : '${v.isEmpty ? '0' : v}.';
  if (v == '0') v = '';
  final partes = v.split('.');
  if (partes.length == 2 ? partes[1].length < 2 : partes[0].length < 3) return v + k;
  return v;
}
