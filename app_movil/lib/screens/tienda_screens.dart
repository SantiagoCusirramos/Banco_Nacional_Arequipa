import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../models.dart';
import '../services/api.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/comunes.dart';
import 'operacion.dart';
import 'qr_screens.dart';

// ======================= PROMOS Y CUPONES (RF-BD-007) =======================
class PromosScreen extends StatefulWidget {
  const PromosScreen({super.key});

  @override
  State<PromosScreen> createState() => _PromosScreenState();
}

class _PromosScreenState extends State<PromosScreen> {
  int _comercio = 0;

  @override
  void initState() {
    super.initState();
    context.read<AppState>().refrescar();
  }

  Future<void> _cupon(Promo p) async {
    final st = context.read<AppState>();
    try {
      final c = await st.api.post('/promos/${p.idPromocion}/cupon');
      if (!mounted) return;
      unawaited(st.refrescar());
      showModalBottomSheet(
        context: context,
        backgroundColor: C.mist,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
        builder: (_) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(22),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(p.tienda, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
              Text(p.titulo, textAlign: TextAlign.center, style: const TextStyle(color: C.muted)),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                child: QrImageView(data: 'CHASKI-CUPON|${c['codigo']}', size: 200),
              ),
              const SizedBox(height: 12),
              SelectableText('${c['codigo']}', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800, letterSpacing: 3, color: C.ink)),
              const SizedBox(height: 6),
              Text('Muéstralo en caja para canjearlo · vence el ${dia(p.fechaFin)}',
                  textAlign: TextAlign.center, style: const TextStyle(color: C.muted, fontSize: 13)),
            ]),
          ),
        ),
      );
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final tiendas = {for (final p in st.promos) p.idComercio: p.tienda};
    final ps = st.promos.where((p) => _comercio == 0 || p.idComercio == _comercio).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Promos y cupones')),
      body: RefreshIndicator(
        onRefresh: st.refrescar,
        child: ListView(padding: const EdgeInsets.only(bottom: 30), children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 4, 20, 12),
            child: Text('Paga con Chaski en estos comercios y el descuento se aplica solo. También puedes obtener un cupón para canjear en caja.',
                style: TextStyle(color: C.muted, fontSize: 14)),
          ),
          if (tiendas.length > 1)
            SizedBox(
              height: 46,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 20), children: [
                Opcion('Todas', on: _comercio == 0, onTap: () => setState(() => _comercio = 0)),
                for (final e in tiendas.entries)
                  Padding(
                      padding: const EdgeInsets.only(left: 8), child: Opcion(e.value, on: _comercio == e.key, onTap: () => setState(() => _comercio = e.key))),
              ]),
            ),
          const SizedBox(height: 8),
          if (ps.isEmpty) const Vacio('No hay promociones disponibles por el momento', 'Vuelve pronto.'),
          for (final p in ps)
            Container(
              margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 54,
                  height: 54,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: C.tono(p.idComercio), borderRadius: BorderRadius.circular(16)),
                  child: Text(p.emoji ?? '🎁', style: const TextStyle(fontSize: 28)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(p.tienda, style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(p.titulo, style: const TextStyle(fontWeight: FontWeight.w600)),
                    if ((p.descripcion ?? '').isNotEmpty) Text(p.descripcion!, style: const TextStyle(color: C.muted, fontSize: 13)),
                    Text('Vigente hasta ${dia(p.fechaFin)}', style: const TextStyle(color: C.muted, fontSize: 13)),
                    const SizedBox(height: 10),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      FilledButton(style: smallButton(), onPressed: () => _cupon(p), child: Text(p.cupon != null ? 'Ver cupón' : 'Obtener cupón')),
                      if (p.tieneTienda)
                        OutlinedButton(
                            style: smallButton(ghost: true),
                            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => TiendaScreen(comercio: p.idComercio))),
                            child: const Text('Ver tienda')),
                      if (p.idQr != null)
                        OutlinedButton(style: smallButton(ghost: true), onPressed: () => abrirPagoQr(context, p.idQr!), child: const Text('Pagar con QR')),
                    ]),
                  ]),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(color: C.sun, borderRadius: BorderRadius.circular(12)),
                  child: Text('−${p.pct}%', style: const TextStyle(fontWeight: FontWeight.w800, color: C.ink, fontSize: 16)),
                ),
              ]),
            ),
        ]),
      ),
    );
  }
}

// ======================= PRODUCTOS =======================
class TarjetaProducto extends StatelessWidget {
  final Producto p;
  const TarjetaProducto(this.p, {super.key});

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final q = st.cantidad(p.idProducto);
    final of = p.oferta;
    void cambiar(int d) {
      final err = st.cambiarCarrito(p, d);
      if (err != null) toast(context, err);
    }

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Stack(children: [
          Container(
            height: 84,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: C.tono(p.idComercio), borderRadius: BorderRadius.circular(14)),
            child: Text(p.emoji ?? '🛍️', style: const TextStyle(fontSize: 42)),
          ),
          if (of != null)
            Positioned(
              top: 6,
              left: 6,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(color: C.danger, borderRadius: BorderRadius.circular(9)),
                child: Text('−${of.pct}%', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12)),
              ),
            ),
        ]),
        const SizedBox(height: 6),
        Text(p.nombre, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, height: 1.2)),
        Text(p.tienda, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: C.muted)),
        const Spacer(),
        Text.rich(TextSpan(children: [
          TextSpan(text: soles(of?.precio ?? p.precio), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          if (of != null) TextSpan(text: '  ${soles(p.precio)}', style: const TextStyle(color: C.muted, fontSize: 12, decoration: TextDecoration.lineThrough)),
        ])),
        Text(
          of != null
              ? 'Quedan ${of.stock} · ${restante(of.fin)}'
              : p.promo != null
                  ? '−${p.promo!.pct}% al pagar'
                  : '',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: of != null ? C.sunDark : C.ok),
        ),
        const SizedBox(height: 6),
        q > 0
            ? Container(
                height: 40,
                decoration: BoxDecoration(color: C.ink, borderRadius: BorderRadius.circular(12)),
                child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  IconButton(onPressed: () => cambiar(-1), icon: const Icon(Icons.remove, color: Colors.white, size: 20), tooltip: 'Quitar uno'),
                  Text('$q', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
                  IconButton(onPressed: () => cambiar(1), icon: const Icon(Icons.add, color: Colors.white, size: 20), tooltip: 'Agregar uno'),
                ]),
              )
            : SizedBox(
                height: 40,
                width: double.infinity,
                child: TextButton(
                  style: TextButton.styleFrom(
                      backgroundColor: C.mist, foregroundColor: C.ink, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: () => cambiar(1),
                  child: const Text('Agregar', style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ),
      ]),
    );
  }
}

class GrillaProductos extends StatelessWidget {
  final List<Producto> ps;
  const GrillaProductos(this.ps, {super.key});

  @override
  Widget build(BuildContext context) {
    if (ps.isEmpty) return const SliverToBoxAdapter(child: Vacio('No encontramos productos', 'Prueba con otra búsqueda.'));
    return SliverPadding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      sliver: SliverGrid(
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, mainAxisSpacing: 12, crossAxisSpacing: 12, mainAxisExtent: 268),
        delegate: SliverChildBuilderDelegate((_, i) => TarjetaProducto(ps[i]), childCount: ps.length),
      ),
    );
  }
}

class BarraCarrito extends StatelessWidget {
  const BarraCarrito({super.key});

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final n = st.carritoN;
    if (n == 0) return const SizedBox.shrink();
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
        child: Material(
          color: C.ink,
          elevation: 8,
          shadowColor: C.ink.withValues(alpha: .4),
          borderRadius: BorderRadius.circular(18),
          child: InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CarritoScreen())),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(children: [
                const Icon(Icons.shopping_cart_outlined, color: Colors.white),
                const SizedBox(width: 10),
                Expanded(
                    child: Text('Ver carrito · $n ${n == 1 ? 'producto' : 'productos'}',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600))),
                Text(soles(st.calcCarrito().total), style: const TextStyle(color: C.sun, fontWeight: FontWeight.w800, fontSize: 17)),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

// ======================= OFERTAS =======================
class OfertasScreen extends StatefulWidget {
  const OfertasScreen({super.key});

  @override
  State<OfertasScreen> createState() => _OfertasScreenState();
}

class _OfertasScreenState extends State<OfertasScreen> {
  List<Producto>? _ps;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final st = context.read<AppState>();
    try {
      final r = (await st.api.get('/ofertas') as List).map((e) => Producto.fromJson(e)).toList();
      st.indexar(r);
      if (mounted) setState(() => _ps = r);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ofertas Chaski')),
      bottomNavigationBar: const BarraCarrito(),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: CustomScrollView(slivers: [
          const SliverToBoxAdapter(
            child: Padding(
                padding: EdgeInsets.fromLTRB(20, 4, 20, 12),
                child: Text('Precios rebajados por tiempo limitado y hasta agotar stock.', style: TextStyle(color: C.muted, fontSize: 14))),
          ),
          if (_ps == null)
            SliverToBoxAdapter(
                child: Padding(padding: const EdgeInsets.all(40), child: Center(child: _error != null ? Text(_error!) : const CircularProgressIndicator())))
          else
            GrillaProductos(_ps!),
          const SliverToBoxAdapter(child: SizedBox(height: 30)),
        ]),
      ),
    );
  }
}

// ======================= TIENDA (RF-BD-008) =======================
class TiendaScreen extends StatefulWidget {
  final int comercio;
  const TiendaScreen({super.key, this.comercio = 0});

  @override
  State<TiendaScreen> createState() => _TiendaScreenState();
}

class _TiendaScreenState extends State<TiendaScreen> {
  late int _comercio = widget.comercio;
  String _q = '';
  List<Tienda> _tiendas = [];
  List<Producto>? _ps;
  String? _error;
  Timer? _deb;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _deb?.cancel();
    super.dispose();
  }

  Future<void> _cargar() async {
    final st = context.read<AppState>();
    try {
      final r = await st.api.get('/tienda?comercio=$_comercio&q=${Uri.encodeQueryComponent(_q)}');
      final ps = (r['productos'] as List).map((e) => Producto.fromJson(e)).toList();
      st.indexar(ps);
      if (mounted) {
        setState(() {
          _tiendas = (r['tiendas'] as List).map((e) => Tienda.fromJson(e)).toList();
          _ps = ps;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tienda Chaski'), actions: [
        IconButton(
          tooltip: 'Mis pedidos',
          onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PedidosScreen())),
          icon: const Icon(Icons.shopping_bag_outlined),
        ),
      ]),
      bottomNavigationBar: const BarraCarrito(),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: CustomScrollView(slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: TextField(
                decoration: const InputDecoration(hintText: 'Busca productos o tiendas', prefixIcon: Icon(Icons.search)),
                onChanged: (v) {
                  _q = v;
                  _deb?.cancel();
                  _deb = Timer(const Duration(milliseconds: 300), _cargar);
                },
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: SizedBox(
              height: 46,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 20), children: [
                Opcion('Todas', on: _comercio == 0, onTap: () {
                  setState(() => _comercio = 0);
                  _cargar();
                }),
                for (final t in _tiendas)
                  Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: Opcion('${t.emoji ?? ''} ${t.nombre}', on: _comercio == t.idComercio, onTap: () {
                      setState(() => _comercio = t.idComercio);
                      _cargar();
                    }),
                  ),
              ]),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 8)),
          if (_ps == null)
            SliverToBoxAdapter(
                child: Padding(padding: const EdgeInsets.all(40), child: Center(child: _error != null ? Text(_error!) : const CircularProgressIndicator())))
          else
            GrillaProductos(_ps!),
          const SliverToBoxAdapter(child: SizedBox(height: 30)),
        ]),
      ),
    );
  }
}

class CarritoScreen extends StatelessWidget {
  const CarritoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final c = st.calcCarrito();
    if (c.grupos.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Tu carrito')),
        body: const Vacio('Tu carrito está vacío', 'Agrega productos desde la tienda o las ofertas.'),
      );
    }
    final me = st.me!;
    final falta = c.total > me.cuenta.saldoActual
        ? 'No tienes saldo suficiente'
        : c.total > me.limite
            ? 'El límite por operación es ${soles(me.limite)}'
            : c.total > me.disponibleHoy
                ? 'Tu tope diario restante es ${soles(me.disponibleHoy)}'
                : '';
    return Scaffold(
      appBar: AppBar(title: const Text('Tu carrito')),
      body: ListView(padding: const EdgeInsets.only(bottom: 20), children: [
        for (final g in c.grupos) ...[
          Seccion(g.tienda, padding: const EdgeInsets.fromLTRB(20, 12, 20, 8)),
          Lista(children: [
            for (final l in g.lineas)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(children: [
                  Avatar(l.p.emoji ?? '🛍️', fondo: C.tono(l.p.idComercio)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(l.p.nombre, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
                      Text('${soles(l.p.oferta?.precio ?? l.p.precio)} c/u${l.p.oferta != null ? ' · oferta' : ''}',
                          style: const TextStyle(fontSize: 13, color: C.muted)),
                    ]),
                  ),
                  IconButton(onPressed: () => st.cambiarCarrito(l.p, -1), icon: const Icon(Icons.remove_circle_outline), tooltip: 'Quitar uno'),
                  Text('${l.n}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  IconButton(
                    onPressed: () {
                      final e = st.cambiarCarrito(l.p, 1);
                      if (e != null) toast(context, e);
                    },
                    icon: const Icon(Icons.add_circle_outline),
                    tooltip: 'Agregar uno',
                  ),
                ]),
              ),
            if (g.desc > 0)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(children: [
                  Expanded(child: Text('Promo −${g.promo!.pct}% · ${g.promo!.titulo}', style: const TextStyle(fontWeight: FontWeight.w600))),
                  Text('−${soles(g.desc)}', style: const TextStyle(color: C.ok, fontWeight: FontWeight.w800)),
                ]),
              ),
          ]),
        ],
        const SizedBox(height: 14),
        Resumen(colores: const {
          'Estás ahorrando': C.ok
        }, lineas: [
          ('Total', soles(c.total)),
          if (c.ahorro > 0) ('Estás ahorrando', soles(c.ahorro)),
          ('Saldo después', soles(me.cuenta.saldoActual - c.total)),
        ]),
        const Padding(
            padding: EdgeInsets.fromLTRB(20, 6, 20, 0),
            child: Text('Recoges tu pedido en cada tienda con un código de retiro.', style: TextStyle(color: C.muted, fontSize: 14))),
      ]),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            if (falta.isNotEmpty)
              Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(falta, style: const TextStyle(color: C.danger, fontWeight: FontWeight.w600))),
            FilledButton(
              style: sunButton(),
              onPressed: falta.isNotEmpty
                  ? null
                  : () {
                      final items = [
                        for (final l in st.carrito.values) {'id_producto': l.p.idProducto, 'cantidad': l.n}
                      ];
                      final op = Operacion(
                        modo: Modo.compra,
                        para: c.grupos.map((g) => g.tienda).join(' y '),
                        monto: c.total,
                        boton: 'Pagar',
                        lineas: [
                          for (final g in c.grupos) (g.tienda, soles(g.total)),
                          if (c.ahorro > 0) ('Ahorras', soles(c.ahorro)),
                        ],
                        ejecutar: (api, uuid) async => Map<String, dynamic>.from(await api.post('/tienda/comprar', {'items': items}, uuid)),
                        alTerminar: (st) => st.vaciarCarrito(),
                      );
                      Navigator.push(context, MaterialPageRoute(builder: (_) => ConfirmScreen(op)));
                    },
              child: Text('Pagar ${soles(c.total)}'),
            ),
          ]),
        ),
      ),
    );
  }
}

class PedidosScreen extends StatefulWidget {
  const PedidosScreen({super.key});

  @override
  State<PedidosScreen> createState() => _PedidosScreenState();
}

class _PedidosScreenState extends State<PedidosScreen> {
  List<Orden>? _os;
  String? _error;

  @override
  void initState() {
    super.initState();
    context.read<AppState>().api.get('/ordenes').then((r) {
      if (mounted) setState(() => _os = (r as List).map((e) => Orden.fromJson(e)).toList());
    }).catchError((e) {
      if (mounted) setState(() => _error = '$e');
    });
  }

  @override
  Widget build(BuildContext context) {
    final os = _os;
    return Scaffold(
      appBar: AppBar(title: const Text('Mis pedidos')),
      body: os == null
          ? Center(child: _error != null ? Text(_error!) : const CircularProgressIndicator())
          : os.isEmpty
              ? const Vacio('Aún no tienes pedidos', 'Tus compras de la tienda aparecerán aquí.')
              : ListView(padding: const EdgeInsets.only(bottom: 30), children: [
                  for (final o in os)
                    Container(
                      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        Row(children: [
                          Expanded(child: Text(o.tienda, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16))),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                            decoration: BoxDecoration(color: C.mist, borderRadius: BorderRadius.circular(20)),
                            child: Text(o.estado == 'pagada' ? 'Listo para retirar' : o.estado,
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: C.muted)),
                          ),
                        ]),
                        Padding(
                            padding: const EdgeInsets.only(top: 4, bottom: 8),
                            child: Text('Pedido #${o.idOrden} · ${fechaCorta(o.fechaHora)}', style: const TextStyle(color: C.muted, fontSize: 13))),
                        for (final i in o.items)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 2),
                            child: Row(children: [
                              Expanded(child: Text('${i.cantidad} × ${i.nombre}', style: const TextStyle(fontSize: 14))),
                              Text(soles(i.cantidad * i.precioUnitario), style: const TextStyle(fontSize: 14))
                            ]),
                          ),
                        if (o.descuento > 0)
                          Row(children: [
                            const Expanded(child: Text('Promo', style: TextStyle(color: C.ok, fontSize: 14))),
                            Text('−${soles(o.descuento)}', style: const TextStyle(color: C.ok, fontSize: 14))
                          ]),
                        const SizedBox(height: 8),
                        Row(children: [
                          const Expanded(child: Text('Total', style: TextStyle(fontWeight: FontWeight.w800))),
                          Text(soles(o.total), style: const TextStyle(fontWeight: FontWeight.w800))
                        ]),
                        Container(
                          margin: const EdgeInsets.only(top: 10),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          decoration: BoxDecoration(color: C.mist, borderRadius: BorderRadius.circular(12)),
                          child: Row(children: [
                            const Expanded(child: Text('Código de retiro', style: TextStyle(fontSize: 14))),
                            Text(o.codigoRecojo, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: 2.5)),
                          ]),
                        ),
                      ]),
                    ),
                ]),
    );
  }
}
