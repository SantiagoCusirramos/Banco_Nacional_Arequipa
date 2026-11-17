import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/comunes.dart';
import 'operacion.dart';

/// Paso 1: número de celular del destinatario (enviar o solicitar).
class DestinoScreen extends StatefulWidget {
  final bool enviar;
  const DestinoScreen({super.key, required this.enviar});

  @override
  State<DestinoScreen> createState() => _DestinoScreenState();
}

class _DestinoScreenState extends State<DestinoScreen> {
  final _cel = TextEditingController();
  String _error = '';
  bool _buscando = false;
  List<Map<String, dynamic>> _recientes = [];

  @override
  void initState() {
    super.initState();
    context.read<AppState>().api.get('/recientes').then((r) {
      if (mounted) setState(() => _recientes = List<Map<String, dynamic>>.from(r));
    }).catchError((_) {});
  }

  Future<void> _buscar() async {
    final cel = _cel.text.trim();
    setState(() => _error = '');
    if (!celularRe.hasMatch(cel)) return setState(() => _error = 'Ingresa un celular de 9 dígitos que empiece con 9');
    setState(() => _buscando = true);
    try {
      final r = await context.read<AppState>().api.get('/clientes/buscar?celular=$cel');
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(builder: (_) => MontoScreen(enviar: widget.enviar, celular: r['celular'], nombre: r['nombre'])));
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _buscando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.enviar ? 'Enviar dinero' : 'Solicitar dinero')),
      body: ListView(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(widget.enviar ? 'Número de celular de quien recibe' : 'Número de celular de quien te paga',
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            TextField(
              controller: _cel,
              autofocus: true,
              maxLength: 9,
              keyboardType: TextInputType.phone,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              style: const TextStyle(fontSize: 17),
              decoration: const InputDecoration(hintText: '9XXXXXXXX', prefixIcon: Icon(Icons.phone_android)),
              onSubmitted: (_) => _buscar(),
            ),
            SizedBox(
                height: 26,
                child:
                    Padding(padding: const EdgeInsets.only(top: 6), child: Text(_error, style: const TextStyle(color: C.danger, fontWeight: FontWeight.w600)))),
            FilledButton(onPressed: _buscando ? null : _buscar, child: Text(_buscando ? 'Buscando…' : 'Continuar')),
          ]),
        ),
        if (_recientes.isNotEmpty) ...[
          const Seccion('Recientes', padding: EdgeInsets.fromLTRB(20, 6, 20, 8)),
          SizedBox(
            height: 90,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                for (final r in _recientes)
                  GestureDetector(
                    onTap: () {
                      _cel.text = r['celular'];
                      _buscar();
                    },
                    child: SizedBox(
                      width: 76,
                      child: Column(children: [
                        Avatar(inicial(r['nombre']), size: 52, fondo: Colors.white),
                        const SizedBox(height: 6),
                        Text(r['nombre'], maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                      ]),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ]),
    );
  }
}

/// Paso 2: monto con teclado numérico + mensaje.
class MontoScreen extends StatefulWidget {
  final bool enviar;
  final String celular, nombre;
  const MontoScreen({super.key, required this.enviar, required this.celular, required this.nombre});

  @override
  State<MontoScreen> createState() => _MontoScreenState();
}

class _MontoScreenState extends State<MontoScreen> {
  String _monto = '';
  final _ref = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final me = context.watch<AppState>().me!;
    final n = double.tryParse(_monto) ?? 0;
    String hint;
    var ok = n > 0;
    if (n > me.limite) {
      hint = 'El límite por operación es ${soles(me.limite)}';
      ok = false;
    } else if (widget.enviar && n > me.cuenta.saldoActual) {
      hint = 'No tienes saldo suficiente';
      ok = false;
    } else if (widget.enviar && n > me.disponibleHoy) {
      hint = 'Tu tope diario restante es ${soles(me.disponibleHoy)}';
      ok = false;
    } else {
      hint =
          widget.enviar ? 'Saldo ${soles(me.cuenta.saldoActual)} · Hoy puedes enviar ${soles(me.disponibleHoy)}' : 'Máximo ${soles(me.limite)} por operación';
    }
    return Scaffold(
      appBar: AppBar(title: Text('${widget.enviar ? 'Enviar a' : 'Solicitar a'} ${widget.nombre}')),
      body: SafeArea(
        child: Column(children: [
          const SizedBox(height: 10),
          MontoGrande(_monto.isEmpty ? '0' : _monto),
          Text(hint, style: TextStyle(color: ok || n == 0 ? C.muted : C.danger, fontSize: 14)),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
            child: TextField(
              controller: _ref,
              maxLength: 100,
              textAlign: TextAlign.center,
              decoration: InputDecoration(
                hintText: widget.enviar ? 'Añade un mensaje (opcional)' : 'Concepto (opcional)',
                filled: false,
                border: const UnderlineInputBorder(borderSide: BorderSide(color: C.line, width: 2)),
                enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: C.line, width: 2)),
                focusedBorder: const UnderlineInputBorder(borderSide: BorderSide(color: C.teal, width: 2)),
              ),
            ),
          ),
          const Spacer(),
          TecladoMonto(onKey: (k) => setState(() => _monto = teclear(_monto, k))),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 16),
            child: FilledButton(
              style: sunButton(),
              onPressed: ok
                  ? () {
                      final ref = _ref.text.trim();
                      final monto = r2(n);
                      final op = Operacion(
                        modo: widget.enviar ? Modo.enviar : Modo.solicitar,
                        para: widget.nombre,
                        monto: monto,
                        boton: widget.enviar ? 'Enviar' : 'Solicitar',
                        lineas: [
                          (widget.enviar ? 'Para' : 'A quien cobras', widget.nombre),
                          ('Celular', widget.celular),
                          if (ref.isNotEmpty) (widget.enviar ? 'Mensaje' : 'Concepto', ref),
                        ],
                        ejecutar: (api, uuid) async => Map<String, dynamic>.from(widget.enviar
                            ? await api.post('/transferencias', {'celular_destino': widget.celular, 'monto': monto, 'referencia': ref}, uuid)
                            : await api.post('/solicitudes', {'celular': widget.celular, 'monto': monto, 'concepto': ref})),
                      );
                      Navigator.push(context, MaterialPageRoute(builder: (_) => ConfirmScreen(op)));
                    }
                  : null,
              child: const Text('Continuar'),
            ),
          ),
        ]),
      ),
    );
  }
}
