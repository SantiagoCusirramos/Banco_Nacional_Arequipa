import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/comunes.dart';
import 'operacion.dart';

/// Recargas de celular y pago de servicios (RF-BD-006).
class ServiciosScreen extends StatefulWidget {
  const ServiciosScreen({super.key});

  @override
  State<ServiciosScreen> createState() => _ServiciosScreenState();
}

class _ServiciosScreenState extends State<ServiciosScreen> {
  bool _recarga = true;
  Map<String, dynamic>? _cat;
  String? _error;
  // recarga
  String? _op;
  int? _m;
  late final _rcel = TextEditingController(text: context.read<AppState>().me?.cliente.celular ?? '');
  // servicio
  String? _prov;
  final _cod = TextEditingController();
  Map<String, dynamic>? _deuda;
  bool _consultando = false;

  @override
  void initState() {
    super.initState();
    context.read<AppState>().api.get('/servicios/catalogo').then((r) {
      if (mounted) setState(() => _cat = Map<String, dynamic>.from(r));
    }).catchError((e) {
      if (mounted) setState(() => _error = '$e');
    });
  }

  void _recargar() {
    final cel = _rcel.text.trim();
    if (_op == null) return toast(context, 'Elige un operador');
    if (!celularRe.hasMatch(cel)) return toast(context, 'Ingresa un celular de 9 dígitos que empiece con 9');
    if (_m == null) return toast(context, 'Elige un monto');
    final op = _op!, monto = _m!;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ConfirmScreen(Operacion(
          modo: Modo.recarga,
          para: 'Recarga $op · $cel',
          monto: monto.toDouble(),
          boton: 'Recargar',
          lineas: [('Operador', op), ('Número', cel)],
          ejecutar: (api, uuid) async => Map<String, dynamic>.from(await api.post('/recargas', {'operador': op, 'celular': cel, 'monto': monto}, uuid)),
        )),
      ),
    );
  }

  Future<void> _consultar() async {
    setState(() {
      _consultando = true;
      _deuda = null;
    });
    try {
      final d = await context.read<AppState>().api.post('/servicios/consultar', {'proveedor': _prov, 'codigo': _cod.text.trim()});
      if (mounted) setState(() => _deuda = Map<String, dynamic>.from(d));
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => _consultando = false);
    }
  }

  void _pagar() {
    final d = _deuda!;
    final prov = _prov!;
    final venc = DateTime.parse('${d['vencimiento']}T12:00:00');
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ConfirmScreen(Operacion(
          modo: Modo.servicio,
          para: '${d['proveedor']} · ${d['codigo']}',
          monto: toD(d['monto']),
          boton: 'Pagar',
          lineas: [('Servicio', '${d['proveedor']}'), ('Código', '${d['codigo']}'), ('Titular', '${d['titular'] ?? '-'}'), ('Vence', diaLargo(venc))],
          ejecutar: (api, uuid) async => Map<String, dynamic>.from(await api.post('/servicios/pagar', {'proveedor': prov, 'codigo': d['codigo']}, uuid)),
        )),
      ),
    );
  }

  Widget _label(String t) =>
      Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(t, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)));

  Widget _recargas(Map<String, dynamic> cat) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _label('Operador'),
      Wrap(spacing: 8, runSpacing: 8, children: [for (final o in cat['operadores']) Opcion('$o', on: _op == o, onTap: () => setState(() => _op = '$o'))]),
      const SizedBox(height: 14),
      _label('Número a recargar'),
      TextField(
          controller: _rcel,
          maxLength: 9,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(hintText: '9XXXXXXXX')),
      const SizedBox(height: 14),
      _label('Monto'),
      Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [for (final m in cat['montos']) Opcion('S/ $m', on: _m == m, onTap: () => setState(() => _m = (m as num).toInt()))]),
      const SizedBox(height: 20),
      FilledButton(style: sunButton(), onPressed: _recargar, child: const Text('Continuar')),
    ]);
  }

  Widget _servicios(Map<String, dynamic> cat) {
    final servicios = List<Map<String, dynamic>>.from(cat['servicios']);
    final cats = <String>{for (final s in servicios) s['cat']};
    final sel = servicios.where((s) => s['id'] == _prov).firstOrNull;
    final d = _deuda;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      for (final c in cats) ...[
        _label(c),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final s in servicios.where((s) => s['cat'] == c))
            Opcion('${s['emoji']} ${s['nombre']}',
                on: _prov == s['id'],
                onTap: () => setState(() {
                      _prov = s['id'];
                      _deuda = null;
                      _cod.clear();
                    })),
        ]),
        const SizedBox(height: 14),
      ],
      if (sel != null) ...[
        _label('Código de suministro o cliente de ${sel['nombre']}'),
        TextField(
            controller: _cod,
            maxLength: 12,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: const InputDecoration(hintText: 'Entre 6 y 12 dígitos')),
        const SizedBox(height: 12),
        FilledButton(onPressed: _consultando ? null : _consultar, child: Text(_consultando ? 'Consultando…' : 'Consultar deuda')),
      ],
      if (d != null) ...[
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${d['proveedor']} · ${d['codigo']}', style: const TextStyle(color: C.muted)),
            if (d['titular'] != null) Text('Titular: ${d['titular']}', style: const TextStyle(color: C.muted)),
            const SizedBox(height: 4),
            if (toD(d['monto']) == 0)
              const Text('Sin deudas pendientes', style: TextStyle(fontWeight: FontWeight.w700))
            else if (d['pagado'] == true)
              const Text('Recibo del mes ya pagado', style: TextStyle(fontWeight: FontWeight.w700))
            else ...[
              Text(soles(toD(d['monto'])), style: const TextStyle(fontSize: 34, fontWeight: FontWeight.w800, color: C.ink)),
              Text('Vence el ${diaLargo(DateTime.parse('${d['vencimiento']}T12:00:00'))}', style: const TextStyle(color: C.muted)),
            ],
          ]),
        ),
        if (toD(d['monto']) > 0 && d['pagado'] != true) ...[
          const SizedBox(height: 12),
          FilledButton(style: sunButton(), onPressed: _pagar, child: Text('Pagar ${soles(toD(d['monto']))}')),
        ],
      ],
      const SizedBox(height: 14),
      const Text('Las deudas son de demostración: se calculan a partir del código y no consultan a la empresa real.',
          style: TextStyle(color: C.muted, fontSize: 13)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final cat = _cat;
    return Scaffold(
      appBar: AppBar(title: const Text('Recargas y servicios')),
      body: ListView(padding: const EdgeInsets.fromLTRB(20, 4, 20, 30), children: [
        DosTabs(a: 'Recargas', b: 'Pagar servicios', enA: _recarga, onChange: (a) => setState(() => _recarga = a)),
        const SizedBox(height: 16),
        if (cat == null)
          Padding(padding: const EdgeInsets.all(40), child: Center(child: _error != null ? Text(_error!) : const CircularProgressIndicator()))
        else
          _recarga ? _recargas(cat) : _servicios(cat),
      ]),
    );
  }
}
