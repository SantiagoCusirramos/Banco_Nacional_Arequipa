import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../funciones.dart';
import '../models.dart';
import '../services/api.dart';
import '../services/operaciones.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/comunes.dart';
import 'enviar_screens.dart';
import 'operacion.dart';
import 'qr_screens.dart';
import 'servicios_screen.dart';
import 'tienda_screens.dart';

/// Contenedor principal: Inicio, Movimientos, Avisos y Perfil + botón central de QR.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> with WidgetsBindingObserver {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) context.read<AppState>().refrescar();
  }

  void _ir(int i) {
    setState(() => _tab = i);
    final st = context.read<AppState>();
    if (i == 2) {
      st.marcarLeidas();
    } else {
      st.refrescar();
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final n = st.me?.noLeidas ?? 0;
    Widget item(int i, IconData ic, IconData icOn, String t, {int badge = 0}) => Expanded(
          child: InkWell(
            onTap: () => _ir(i),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Badge(
                    isLabelVisible: badge > 0,
                    label: Text('$badge'),
                    backgroundColor: C.danger,
                    child: Icon(_tab == i ? icOn : ic, color: _tab == i ? C.ink : C.muted)),
                const SizedBox(height: 3),
                Text(t, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _tab == i ? C.ink : C.muted)),
              ]),
            ),
          ),
        );
    return Scaffold(
      body: IndexedStack(index: _tab, children: [
        _InicioTab(irAMovs: () => _ir(1)),
        const _MovimientosTab(),
        const _AvisosTab(),
        const _PerfilTab(),
      ]),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: SizedBox(
        width: 62,
        height: 62,
        child: FloatingActionButton(
          heroTag: 'qr',
          backgroundColor: C.sun,
          foregroundColor: C.ink,
          elevation: 6,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          tooltip: 'Pagar con QR',
          onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const QrScreen())),
          child: const Icon(Icons.qr_code_scanner, size: 30),
        ),
      ),
      bottomNavigationBar: BottomAppBar(
        color: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 6),
        height: 68,
        shape: const CircularNotchedRectangle(),
        notchMargin: 6,
        child: Row(children: [
          item(0, Icons.home_outlined, Icons.home, 'Inicio'),
          item(1, Icons.receipt_long_outlined, Icons.receipt_long, 'Movimientos'),
          const SizedBox(width: 72),
          item(2, Icons.notifications_outlined, Icons.notifications, 'Avisos', badge: n),
          item(3, Icons.person_outline, Icons.person, 'Perfil'),
        ]),
      ),
    );
  }
}

// ======================= INICIO =======================
class _InicioTab extends StatelessWidget {
  final VoidCallback irAMovs;
  const _InicioTab({required this.irAMovs});

  void _push(BuildContext context, Widget w) => Navigator.push(context, MaterialPageRoute(builder: (_) => w));

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final me = st.me!;
    Widget accion(IconData ic, String t, VoidCallback onTap) => Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5),
            child: Material(
              color: Colors.white,
              elevation: 4,
              shadowColor: C.ink.withValues(alpha: .12),
              borderRadius: BorderRadius.circular(18),
              child: InkWell(
                borderRadius: BorderRadius.circular(18),
                onTap: onTap,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(4, 14, 4, 10),
                  child: Column(children: [
                    Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(color: C.mist, borderRadius: BorderRadius.circular(14)),
                        child: Icon(ic, color: C.ink)),
                    const SizedBox(height: 8),
                    Text(t, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                  ]),
                ),
              ),
            ),
          ),
        );
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: barraClara,
      child: RefreshIndicator(
        onRefresh: st.refrescar,
        child: ListView(padding: const EdgeInsets.only(bottom: 30), children: [
          Container(
            color: C.ink,
            padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 18, 20, 40),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('Hola, ${me.cliente.primerNombre}', style: const TextStyle(color: Colors.white, fontSize: 15))),
                const LogoChaski(size: 30),
              ]),
              const SizedBox(height: 18),
              const Text('Tu saldo', style: TextStyle(color: Colors.white70, fontSize: 14)),
              Row(children: [
                Flexible(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(st.ocultarSaldo ? 'S/ ••••' : soles(me.cuenta.saldoActual),
                        style: const TextStyle(color: Colors.white, fontSize: 44, fontWeight: FontWeight.w800, letterSpacing: -1)),
                  ),
                ),
                IconButton(
                  onPressed: st.toggleOcultar,
                  tooltip: st.ocultarSaldo ? 'Mostrar saldo' : 'Ocultar saldo',
                  icon: Icon(st.ocultarSaldo ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: Colors.white70),
                ),
              ]),
              if (st.offline)
                Container(
                  margin: const EdgeInsets.only(top: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: .15), borderRadius: BorderRadius.circular(10)),
                  child: Text('Modo fuera de línea - Saldo no actualizado${st.cacheFecha != null ? ' (${fechaCorta(st.cacheFecha!)})' : ''}',
                      style: const TextStyle(color: C.sun, fontSize: 13, fontWeight: FontWeight.w600)),
                )
              else
                Text('Hoy puedes mover hasta ${soles(me.disponibleHoy)}', style: const TextStyle(color: Colors.white60, fontSize: 13)),
            ]),
          ),
          Transform.translate(
            offset: const Offset(0, -20),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 11),
              child: Column(children: [
                Row(children: [
                  accion(Icons.send_outlined, 'Enviar', () => _push(context, const DestinoScreen(enviar: true))),
                  accion(Icons.download_outlined, 'Solicitar', () => _push(context, const DestinoScreen(enviar: false))),
                  accion(Icons.qr_code_scanner, 'Pagar QR', () => _push(context, const QrScreen())),
                  accion(Icons.qr_code_2, 'Mi QR', () => _push(context, const QrScreen(mio: true))),
                ]),
                // Promociones, ofertas, tienda y servicios no están en esta versión de la API (ver Funciones).
                if (Funciones.promociones || Funciones.tienda || Funciones.servicios) ...[
                  const SizedBox(height: 10),
                  Row(children: [
                    if (Funciones.promociones) accion(Icons.local_offer_outlined, 'Promos', () => _push(context, const PromosScreen())),
                    if (Funciones.promociones) accion(Icons.flash_on_outlined, 'Ofertas', () => _push(context, const OfertasScreen())),
                    if (Funciones.tienda) accion(Icons.storefront_outlined, 'Tienda', () => _push(context, const TiendaScreen())),
                    if (Funciones.servicios) accion(Icons.receipt_outlined, 'Servicios', () => _push(context, const ServiciosScreen())),
                  ]),
                ],
              ]),
            ),
          ),
          if (Funciones.promociones && st.promos.isNotEmpty) ...[
            Seccion('Promos para ti',
                accion: 'Ver todas', onAccion: () => _push(context, const PromosScreen()), padding: const EdgeInsets.fromLTRB(20, 0, 20, 8)),
            SizedBox(
              height: 112,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16), children: [
                for (final p in st.promos.take(6))
                  GestureDetector(
                    onTap: () => _push(context, const PromosScreen()),
                    child: Container(
                      width: 118,
                      margin: const EdgeInsets.only(right: 10),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(color: C.tono(p.idComercio), borderRadius: BorderRadius.circular(18)),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(p.emoji ?? '🎁', style: const TextStyle(fontSize: 24)),
                        Text('−${p.pct}%', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: C.ink)),
                        Text(p.tienda, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                      ]),
                    ),
                  ),
              ]),
            ),
          ],
          Seccion('Últimos movimientos', accion: 'Ver todo', onAccion: irAMovs),
          ListaMovimientos(st.movs.take(5).toList()),
        ]),
      ),
    );
  }
}

// ======================= MOVIMIENTOS (RF-BD-004) =======================
class _MovimientosTab extends StatelessWidget {
  const _MovimientosTab();

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Movimientos')),
      body: RefreshIndicator(
        onRefresh: st.refrescar,
        child: ListView(padding: const EdgeInsets.only(bottom: 30), children: [
          if (st.offline)
            const Padding(
                padding: EdgeInsets.fromLTRB(20, 0, 20, 10),
                child: Text('Modo fuera de línea - Historial guardado en el celular', style: TextStyle(color: C.sunDark, fontWeight: FontWeight.w600))),
          ListaMovimientos(st.movs),
        ]),
      ),
    );
  }
}

// ======================= AVISOS (RF-BD-002 / RF-BD-009) =======================
class _AvisosTab extends StatelessWidget {
  const _AvisosTab();

  Future<void> _responder(BuildContext context, Solicitud s, String accion) async {
    final st = context.read<AppState>();
    try {
      // Con Idempotency-Key, la misma si se reintenta (como aceptar).
      await responderSolicitud(st, s.id, accion);
      if (context.mounted) toast(context, accion == 'rechazar' ? 'Solicitud rechazada' : 'Solicitud cancelada');
    } on ApiException catch (e) {
      if (context.mounted) toast(context, e.message);
    }
    await st.refrescar();
  }

  void _pagar(BuildContext context, Solicitud s) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ConfirmScreen(Operacion(
          modo: Modo.pagoSolicitud,
          para: s.nombre,
          monto: s.monto,
          boton: 'Pagar',
          lineas: [
            ('Para', s.nombre),
            if (s.celular.isNotEmpty) ('Celular', s.celular),
            if ((s.concepto ?? '').isNotEmpty) ('Concepto', s.concepto!),
          ],
          ejecutar: (api, uuid) async => Map<String, dynamic>.from(await api.post('/solicitudes/${s.id}/responder', {'accion': 'aceptar'}, uuid)),
        )),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final pend = st.sol.recibidas.where((s) => s.pendiente).toList();
    final enviadas = st.sol.enviadas.where((s) => s.pendiente).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Avisos')),
      body: RefreshIndicator(
        onRefresh: st.refrescar,
        child: ListView(padding: const EdgeInsets.only(bottom: 30), children: [
          if (pend.isNotEmpty) ...[
            const Seccion('Te piden dinero', padding: EdgeInsets.fromLTRB(20, 4, 20, 8)),
            Lista(children: [
              for (final s in pend)
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text.rich(TextSpan(children: [
                      TextSpan(text: s.nombre, style: const TextStyle(fontWeight: FontWeight.w700)),
                      const TextSpan(text: ' te pide '),
                      TextSpan(text: soles(s.monto), style: const TextStyle(fontWeight: FontWeight.w700)),
                    ])),
                    if ((s.concepto ?? '').isNotEmpty) Text(s.concepto!, style: const TextStyle(color: C.muted, fontSize: 14)),
                    Text('Expira 48 h después de ${fechaCorta(s.fecha)}', style: const TextStyle(color: C.muted, fontSize: 12)),
                    const SizedBox(height: 10),
                    Row(children: [
                      FilledButton(style: smallButton(), onPressed: () => _pagar(context, s), child: Text('Pagar ${soles(s.monto)}')),
                      const SizedBox(width: 8),
                      OutlinedButton(style: smallButton(ghost: true), onPressed: () => _responder(context, s, 'rechazar'), child: const Text('Rechazar')),
                    ]),
                  ]),
                ),
            ]),
          ],
          const Seccion('Notificaciones'),
          if (st.notifs.isEmpty)
            const Lista(children: [Vacio('Sin notificaciones', 'Aquí verás cuando recibas dinero.')])
          else
            Lista(children: [
              for (final n in st.notifs)
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Container(
                      width: 9,
                      height: 9,
                      margin: const EdgeInsets.only(top: 6, right: 10),
                      decoration: BoxDecoration(color: n.leida ? Colors.transparent : C.teal, shape: BoxShape.circle),
                    ),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(n.mensaje, style: const TextStyle(fontSize: 15)),
                        const SizedBox(height: 3),
                        Text(fechaCorta(n.fechaHora), style: const TextStyle(color: C.muted, fontSize: 13)),
                      ]),
                    ),
                  ]),
                ),
            ]),
          if (enviadas.isNotEmpty) ...[
            const Seccion('Cobros que pediste'),
            Lista(children: [
              for (final s in enviadas)
                ListTile(
                  title: Text('${s.nombre} · ${soles(s.monto)}', style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Pendiente'),
                  trailing: OutlinedButton(style: smallButton(ghost: true), onPressed: () => _responder(context, s, 'cancelar'), child: const Text('Cancelar')),
                ),
            ]),
          ],
        ]),
      ),
    );
  }
}

// ======================= PERFIL =======================
class _PerfilTab extends StatelessWidget {
  const _PerfilTab();

  @override
  Widget build(BuildContext context) {
    final st = context.watch<AppState>();
    final c = st.me!.cliente;
    Widget fila(String k, String v) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(children: [
            Text(k, style: const TextStyle(color: C.muted)),
            const SizedBox(width: 12),
            Expanded(child: Text(v, textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w700))),
          ]),
        );
    return Scaffold(
      appBar: AppBar(title: const Text('Perfil')),
      body: ListView(padding: const EdgeInsets.only(bottom: 30), children: [
        Lista(children: [
          fila('Nombre', c.nombreCompleto.trim()),
          // La API integrada no entrega el documento ni el celular: solo se muestran si llegan.
          if (c.numeroDocumento.isNotEmpty) fila(c.tipoDocumento, c.numeroDocumento),
          if (c.celular.isNotEmpty) fila('Celular', c.celular),
          if ((c.email ?? '').isNotEmpty) fila('Correo', c.email!),
          fila('Cuenta virtual', st.me!.cuenta.numeroCuentaVirtual),
          fila('Límite por operación', soles(st.me!.limite)),
          fila('Tope diario', '${soles(st.me!.topeDiario)} (quedan ${soles(st.me!.disponibleHoy)})'),
        ]),
        const Seccion('Seguridad'),
        Lista(children: [
          SwitchListTile(
            value: st.usarBiometria,
            onChanged: st.setBiometria,
            title: const Text('Autorizar con huella o rostro', style: TextStyle(fontWeight: FontWeight.w600)),
            subtitle: const Text('Si no, se pedirá tu PIN en cada operación'),
          ),
          ListTile(title: const Text('Servidor', style: TextStyle(fontWeight: FontWeight.w600)), subtitle: Text(st.servidor)),
        ]),
        if (Funciones.ordenes)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 0),
            child: OutlinedButton(
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PedidosScreen())), child: const Text('Mis pedidos')),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 20, 16, 20),
          child: OutlinedButton(
            onPressed: () async {
              final ok = await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('¿Cerrar sesión?'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('No')),
                    TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Sí, salir')),
                  ],
                ),
              );
              if (ok == true) st.logout();
            },
            child: const Text('Cerrar sesión'),
          ),
        ),
      ]),
    );
  }
}
