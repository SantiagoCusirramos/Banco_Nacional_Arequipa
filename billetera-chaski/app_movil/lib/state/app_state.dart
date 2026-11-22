import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../funciones.dart';
import '../models.dart';
import '../services/api.dart';
import '../services/cache_db.dart';
import '../services/operaciones.dart';
import '../util/format.dart';
import '../util/servidor.dart';

/// URL fijada al compilar con --dart-define=SERVIDOR=... (por ejemplo http://10.0.2.2:8020 para el
/// emulador). Vacía si no se definió: en ese caso la primera apertura pregunta a qué banco conectarse.
const servidorPorDefecto = String.fromEnvironment('SERVIDOR');

class LineaCarrito {
  Producto p;
  int n;
  LineaCarrito(this.p, this.n);
}

class GrupoCarrito {
  final int idComercio;
  final String tienda;
  final PromoInfo? promo;
  final List<LineaCarrito> lineas = [];
  double subtotal = 0, base = 0, ahorroOferta = 0, desc = 0, total = 0;
  GrupoCarrito(this.idComercio, this.tienda, this.promo);
}

class ResumenCarrito {
  final List<GrupoCarrito> grupos;
  final double total, ahorro;
  ResumenCarrito(this.grupos, this.total, this.ahorro);
}

/// Estado global de la app (sesión, saldo, movimientos, avisos y carrito).
class AppState extends ChangeNotifier {
  late SharedPreferences _prefs;
  Api? _api;
  Api get api => _api!;
  final cache = CacheDb();

  /// [api] permite inyectar un cliente (pruebas); si no, se crea en [init] con el servidor guardado.
  AppState({Api? api}) : _api = api;

  bool iniciando = true;
  String? token;
  Me? me;
  List<Movimiento> movs = [];
  Solicitudes sol = Solicitudes.vacio();
  List<Notificacion> notifs = [];
  List<Promo> promos = [];

  /// true cuando se muestra el último saldo guardado porque el servidor no responde.
  bool offline = false;
  DateTime? cacheFecha;
  bool ocultarSaldo = false;
  bool usarBiometria = true;

  bool _necesitaServidor = false;

  /// Primer uso: no hay servidor guardado ni fijado al compilar.
  bool get necesitaServidor => _necesitaServidor;

  set necesitaServidor(bool v) {
    if (_necesitaServidor == v) return;
    _necesitaServidor = v;
    notifyListeners();
  }

  bool _servidorSinConexion = false;

  /// El servidor guardado no responde: hay que reintentar o cambiar de banco.
  bool get servidorSinConexion => _servidorSinConexion;

  set servidorSinConexion(bool v) {
    if (_servidorSinConexion == v) return;
    _servidorSinConexion = v;
    notifyListeners();
  }

  final Map<int, LineaCarrito> carrito = {};

  /// Operaciones sin terminar (p. ej. rechazar una solicitud), con su uuid de idempotencia.
  final Map<String, IntentoOperacion> intentos = {};
  Timer? _poll;

  String get servidor => api.baseUrl;
  bool get logueado => token != null && me != null;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    final guardado = _prefs.getString('servidor');
    final url = guardado != null
        ? parsearServidor(guardado)
        : (servidorPorDefecto.isEmpty ? null : parsearServidor(servidorPorDefecto));
    if (_api == null) _api = Api(url ?? '');
    if (url == null) {
      necesitaServidor = true;
      api.baseUrl = '';
    } else {
      api.baseUrl = url;
      necesitaServidor = false;
    }
    api.onUnauthorized = () => logout(expirada: true);
    ocultarSaldo = _prefs.getBool('ocultar') ?? false;
    usarBiometria = _prefs.getBool('biometria') ?? true;
    token = _prefs.getString('token');
    api.token = token;
    if (!necesitaServidor) {
      try {
        await probarServidor();
      } on ApiException {
        servidorSinConexion = true;
      }
    }
    if (!necesitaServidor && !servidorSinConexion) {
      if (token != null) await refrescar();
      if (token != null && me != null) _iniciarPoll();
    }
    iniciando = false;
    notifyListeners();
  }

  /// Normaliza y guarda el servidor tras haber comprobado que responde.
  Future<void> setServidor(String url) async {
    final normalizada = parsearServidor(url);
    if (normalizada == null) {
      throw ApiException(0, 'La dirección debe ser http:// o https://, sin usuario ni clave', red: true);
    }
    api.baseUrl = normalizada;
    await _prefs.setString('servidor', normalizada);
    necesitaServidor = false;
    servidorSinConexion = false;
    notifyListeners();
  }

  /// Comprueba [url] (o el servidor actual) con la misma llamada de salud de siempre, sin guardar nada.
  Future<void> probarServidor([String? url]) async {
    String? destino;
    if (url != null) {
      destino = parsearServidor(url);
      if (destino == null) throw ApiException(0, 'Escribe una dirección http:// o https:// válida', red: true);
    }
    final anterior = api.baseUrl;
    if (destino != null) api.baseUrl = destino;
    try {
      await api.get('/salud');
    } finally {
      if (destino != null) api.baseUrl = anterior;
    }
  }

  /// Descarta la sesión y el servidor actual para volver a la pantalla de conexión.
  Future<void> cambiarBanco() async {
    await logout();
    await _prefs.remove('servidor');
    api.baseUrl = '';
    necesitaServidor = true;
    servidorSinConexion = false;
    notifyListeners();
  }

  Future<void> _entrar(String t) async {
    token = t;
    api.token = t;
    try {
      await refrescar(lanzar: true);
    } catch (_) {
      token = null;
      api.token = null;
      me = null;
      rethrow;
    }
    await _prefs.setString('token', t);
    _iniciarPoll();
  }

  Future<void> login(String celular, String pin) async {
    final r = await api.post('/login', {'celular': celular, 'pin': pin});
    await _entrar(r['token']);
  }

  Future<void> registro(Map<String, dynamic> datos) async {
    final r = await api.post('/registro', datos);
    await _entrar(r['token']);
  }

  Future<void> logout({bool expirada = false}) async {
    _poll?.cancel();
    token = null;
    api.token = null;
    me = null;
    movs = [];
    sol = Solicitudes.vacio();
    notifs = [];
    carrito.clear();
    intentos.clear();
    offline = false;
    await _prefs.remove('token');
    await _prefs.remove('id_cliente'); // clave de la versión con ids numéricos
    await _prefs.remove('cliente');
    await cache.limpiar().catchError((_) {});
    notifyListeners();
  }

  void _iniciarPoll() {
    _poll?.cancel();
    _poll = Timer.periodic(const Duration(seconds: 8), (_) {
      if (logueado) refrescar();
    });
  }

  /// Trae saldo, movimientos, solicitudes y avisos (y promos solo si están en esta versión). Si el
  /// servidor no responde, usa la caché local.
  Future<void> refrescar({bool lanzar = false}) async {
    try {
      final r = await Future.wait([
        api.get('/me'),
        api.get('/movimientos'),
        api.get('/solicitudes'),
        api.get('/notificaciones'),
        if (Funciones.promociones) api.get('/promos').catchError((_) => <dynamic>[]),
      ]);
      me = Me.fromJson(r[0]);
      movs = (r[1] as List).map((e) => Movimiento.fromJson(e)).toList();
      sol = Solicitudes.fromJson(r[2]);
      notifs = (r[3] as List).map((e) => Notificacion.fromJson(e)).toList();
      promos = r.length > 4 ? (r[4] as List).map((e) => Promo.fromJson(e)).toList() : [];
      offline = false;
      await _prefs.setString('cliente', me!.cliente.idCliente);
      cache.guardar(me!, movs).catchError((_) {});
    } on ApiException catch (e) {
      if (e.red) {
        await _cargarCache();
        if (lanzar && me == null) rethrow;
      } else if (lanzar) {
        rethrow;
      }
    } finally {
      if (token != null) {
        if (me != null && (_poll == null || !_poll!.isActive)) _iniciarPoll();
        notifyListeners();
      }
    }
  }

  Future<void> _cargarCache() async {
    final id = _prefs.getString('cliente');
    if (id == null) return;
    final c = await cache.leer(id).catchError((_) => null);
    if (c == null) return;
    me ??= c.me;
    if (movs.isEmpty) movs = c.movs;
    cacheFecha = c.actualizado;
    offline = true;
  }

  Future<void> marcarLeidas() async {
    try {
      await api.post('/notificaciones/leidas');
      await refrescar();
    } catch (_) {}
  }

  void toggleOcultar() {
    ocultarSaldo = !ocultarSaldo;
    _prefs.setBool('ocultar', ocultarSaldo);
    notifyListeners();
  }

  void setBiometria(bool v) {
    usarBiometria = v;
    _prefs.setBool('biometria', v);
    notifyListeners();
  }

  // ---------- carrito ----------
  int get carritoN => carrito.values.fold(0, (a, x) => a + x.n);
  int cantidad(int idProducto) => carrito[idProducto]?.n ?? 0;

  /// Devuelve un mensaje de error si no se puede agregar.
  String? cambiarCarrito(Producto p, int delta) {
    final actual = cantidad(p.idProducto);
    final nuevo = actual + delta;
    final max = p.stock < 10 ? p.stock : 10;
    if (nuevo > max) return 'Máximo $max por producto';
    if (nuevo <= 0) {
      carrito.remove(p.idProducto);
    } else {
      carrito[p.idProducto] = LineaCarrito(p, nuevo);
    }
    notifyListeners();
    return null;
  }

  /// Actualiza los productos del carrito con datos recientes (precio, stock, oferta).
  void indexar(List<Producto> ps) {
    for (final p in ps) {
      carrito[p.idProducto]?.p = p;
    }
  }

  void vaciarCarrito() {
    carrito.clear();
    notifyListeners();
  }

  /// Mismo cálculo que el servidor: oferta por unidades con cupo, promo sobre lo que no está en oferta.
  ResumenCarrito calcCarrito() {
    final gs = <int, GrupoCarrito>{};
    for (final l in carrito.values) {
      final p = l.p;
      final uOf = p.oferta != null ? (l.n < p.oferta!.stock ? l.n : p.oferta!.stock) : 0;
      final g = gs.putIfAbsent(p.idComercio, () => GrupoCarrito(p.idComercio, p.tienda, p.promo));
      g.lineas.add(l);
      g.subtotal += uOf * (p.oferta?.precio ?? 0) + (l.n - uOf) * p.precio;
      g.base += (l.n - uOf) * p.precio;
      if (uOf > 0) g.ahorroOferta += uOf * (p.precio - p.oferta!.precio);
    }
    double total = 0, ahorro = 0;
    for (final g in gs.values) {
      g.desc = g.promo?.descuento(g.base) ?? 0;
      g.total = r2(g.subtotal - g.desc);
      total += g.total;
      ahorro += g.desc + g.ahorroOferta;
    }
    return ResumenCarrito(gs.values.toList(), r2(total), r2(ahorro));
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }
}
