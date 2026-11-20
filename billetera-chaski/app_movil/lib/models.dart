// Modelos de datos. Cada clase refleja una tabla del diagrama (cliente, cuenta, movimiento,
// notificacion, solicitud_cobro, codigo_qr…) tal como la devuelve la API.
import 'dart:math' as math;

import 'util/format.dart';

class Cliente {
  final String idCliente; // código del cliente en el CORE (CLI000000016)
  final String tipoDocumento, numeroDocumento, nombres, apellidos, celular;
  final String? email;

  Cliente(
      {required this.idCliente,
      required this.tipoDocumento,
      required this.numeroDocumento,
      required this.nombres,
      required this.apellidos,
      required this.celular,
      this.email});

  factory Cliente.fromJson(Map<String, dynamic> j) => Cliente(
        idCliente: '${j['id_cliente'] ?? ''}',
        tipoDocumento: j['tipo_documento'] ?? 'DNI',
        numeroDocumento: j['numero_documento'] ?? '',
        nombres: j['nombres'] ?? '',
        apellidos: j['apellidos'] ?? '',
        celular: j['celular'] ?? '',
        email: j['email'],
      );

  /// Lo que se guarda en la caché local: sin el celular (nunca se persiste en claro).
  Map<String, dynamic> toJson() => {
        'id_cliente': idCliente,
        'tipo_documento': tipoDocumento,
        'numero_documento': numeroDocumento,
        'nombres': nombres,
        'apellidos': apellidos,
        'email': email,
      };

  String get primerNombre => nombres.split(' ').first;
  String get nombreCompleto => '$nombres $apellidos';
}

class Cuenta {
  final String idCuenta; // número de cuenta en el CORE (CTA-…)
  final String numeroCuentaVirtual, moneda;
  final double saldoActual;

  Cuenta({required this.idCuenta, required this.numeroCuentaVirtual, required this.saldoActual, required this.moneda});

  factory Cuenta.fromJson(Map<String, dynamic> j) => Cuenta(
      idCuenta: '${j['id_cuenta'] ?? ''}', numeroCuentaVirtual: j['numero_cuenta_virtual'] ?? '', saldoActual: toD(j['saldo_actual']), moneda: j['moneda'] ?? 'PEN');

  Map<String, dynamic> toJson() => {'id_cuenta': idCuenta, 'numero_cuenta_virtual': numeroCuentaVirtual, 'saldo_actual': saldoActual, 'moneda': moneda};
}

/// Respuesta de GET /api/me: cliente + cuenta + contadores y límites.
class Me {
  final Cliente cliente;
  final Cuenta cuenta;
  final int noLeidas, pendientes;
  final double limite, topeDiario, disponibleHoy;

  Me(
      {required this.cliente,
      required this.cuenta,
      required this.noLeidas,
      required this.pendientes,
      required this.limite,
      required this.topeDiario,
      required this.disponibleHoy});

  factory Me.fromJson(Map<String, dynamic> j) => Me(
        cliente: Cliente.fromJson(j['cliente']),
        cuenta: Cuenta.fromJson(j['cuenta']),
        noLeidas: j['no_leidas'] ?? 0,
        pendientes: j['pendientes'] ?? 0,
        limite: toD(j['limite'] ?? 500),
        topeDiario: toD(j['tope_diario'] ?? 500),
        disponibleHoy: toD(j['disponible_hoy'] ?? 500),
      );

  Map<String, dynamic> toJson() => {
        'cliente': cliente.toJson(),
        'cuenta': cuenta.toJson(),
        'no_leidas': noLeidas,
        'pendientes': pendientes,
        'limite': limite,
        'tope_diario': topeDiario,
        'disponible_hoy': disponibleHoy,
      };

  /// Monto máximo que se puede debitar ahora: el menor entre saldo, límite por operación y tope diario restante.
  double get maxDebito => math.min(cuenta.saldoActual, math.min(limite, disponibleHoy));
}

/// Un movimiento de la cuenta como lo da la API sobre COREDB: `id_movimiento` es el UUID de la
/// transacción, `monto` viene con signo (negativo si es un débito) y no trae saldo resultante.
class Movimiento {
  final String idMovimiento;
  final String tipoMovimiento;
  final double monto;
  final double? saldoResultante;
  final DateTime fechaHora;
  final String descripcion;
  final String? idTransferencia, idPago, idOrden, idPagoServicio;

  Movimiento(
      {required this.idMovimiento,
      required this.tipoMovimiento,
      required this.monto,
      this.saldoResultante,
      required this.fechaHora,
      required this.descripcion,
      this.idTransferencia,
      this.idPago,
      this.idOrden,
      this.idPagoServicio});

  factory Movimiento.fromJson(Map<String, dynamic> j) => Movimiento(
        idMovimiento: '${j['id_movimiento']}',
        tipoMovimiento: '${j['tipo_movimiento'] ?? ''}'.toLowerCase(),
        monto: toD(j['monto']),
        saldoResultante: j['saldo_resultante'] == null ? null : toD(j['saldo_resultante']),
        fechaHora: parseFecha(j['fecha_hora']),
        descripcion: j['descripcion'] ?? '',
        idTransferencia: j['id_transferencia']?.toString(),
        idPago: j['id_pago']?.toString(),
        idOrden: j['id_orden']?.toString(),
        idPagoServicio: j['id_pago_servicio']?.toString(),
      );

  /// Fila para la caché local SQLite (columnas REAL ↔ double).
  Map<String, Object?> toRow(String idCliente) => {
        'id_movimiento': idMovimiento,
        'id_cliente': idCliente,
        'tipo_movimiento': tipoMovimiento,
        'monto': monto,
        'saldo_resultante': saldoResultante,
        'fecha_hora': fechaHora.toUtc().toIso8601String(),
        'descripcion': descripcion,
      };

  factory Movimiento.fromRow(Map<String, Object?> r) => Movimiento(
        idMovimiento: '${r['id_movimiento']}',
        tipoMovimiento: r['tipo_movimiento'] as String,
        monto: (r['monto'] as num).toDouble(),
        saldoResultante: (r['saldo_resultante'] as num?)?.toDouble(),
        fechaHora: DateTime.parse(r['fecha_hora'] as String),
        descripcion: (r['descripcion'] as String?) ?? '',
      );

  String? get idOperacion => idTransferencia ?? idPago ?? idOrden ?? idPagoServicio;

  String get emoji =>
      const {
        'compra_tienda': '🛍️',
        'venta_tienda': '🛍️',
        'recarga_celular': '📱',
        'pago_servicio': '🧾',
        'recarga': '💰',
      }[tipoMovimiento] ??
      inicial(descripcion.replaceFirst(RegExp(r'^(Enviaste a|Pagaste a|Cobro QR de)\s'), ''));

  String get tipoLegible =>
      const {
        'deposito': 'Depósito',
        'retiro': 'Retiro',
        'fondeo_billetera': 'Recarga de la billetera',
        'transferencia_enviada': 'Transferencia enviada',
        'transferencia_recibida': 'Transferencia recibida',
        'pago_qr': 'Pago con QR',
        'cobro_qr': 'Cobro con QR',
        'recarga': 'Recarga de saldo',
        'compra_tienda': 'Compra en tienda',
        'venta_tienda': 'Venta en tienda',
        'recarga_celular': 'Recarga de celular',
        'pago_servicio': 'Pago de servicio',
      }[tipoMovimiento] ??
      tipoMovimiento;
}

class Notificacion {
  final int id;
  final String tipo, mensaje, estadoEnvio;
  final DateTime fechaHora;

  Notificacion({required this.id, required this.tipo, required this.mensaje, required this.estadoEnvio, required this.fechaHora});

  factory Notificacion.fromJson(Map<String, dynamic> j) => Notificacion(
      id: j['id_notificacion'],
      tipo: j['tipo'] ?? '',
      mensaje: j['mensaje'] ?? '',
      estadoEnvio: j['estado_envio'] ?? 'enviado',
      fechaHora: parseFecha(j['fecha_hora']));

  bool get leida => estadoEnvio == 'leido';
}

class Solicitud {
  final String id; // UUID de la solicitud en COREDB
  final double monto;
  final String? concepto;
  final String estado, nombre, celular;
  final DateTime fecha;

  Solicitud({required this.id, required this.monto, this.concepto, required this.estado, required this.nombre, required this.celular, required this.fecha});

  factory Solicitud.fromJson(Map<String, dynamic> j) => Solicitud(
        id: '${j['id_solicitud']}',
        monto: toD(j['monto']),
        concepto: j['concepto'],
        estado: j['estado'] ?? 'pendiente',
        nombre: j['nombre'] ?? '',
        celular: j['celular'] ?? '',
        fecha: parseFecha(j['fecha']),
      );

  bool get pendiente => estado == 'pendiente';
}

class Solicitudes {
  final List<Solicitud> recibidas, enviadas;
  Solicitudes(this.recibidas, this.enviadas);
  static Solicitudes vacio() => Solicitudes([], []);
  factory Solicitudes.fromJson(Map<String, dynamic> j) => Solicitudes(
        (j['recibidas'] as List).map((e) => Solicitud.fromJson(e)).toList(),
        (j['enviadas'] as List).map((e) => Solicitud.fromJson(e)).toList(),
      );
}

/// Promoción aplicada a un comercio (porcentaje con tope en soles).
class PromoInfo {
  final String titulo;
  final double porcentaje;
  final double? tope;
  PromoInfo({required this.titulo, required this.porcentaje, this.tope});
  static PromoInfo? fromJson(dynamic j) =>
      j == null ? null : PromoInfo(titulo: j['titulo'] ?? '', porcentaje: toD(j['porcentaje']), tope: j['tope'] == null ? null : toD(j['tope']));

  double descuento(double base) => r2(math.min(base * porcentaje / 100, tope ?? double.infinity));
  String get pct => porcentaje == porcentaje.roundToDouble() ? porcentaje.toStringAsFixed(0) : porcentaje.toString();
}

class Promo {
  final int idPromocion, idComercio;
  final String titulo, tienda;
  final String? descripcion, emoji, cupon;
  final double porcentaje;
  final double? tope;
  final DateTime fechaFin;
  final String? idQr;
  final bool tieneTienda;

  Promo(
      {required this.idPromocion,
      required this.idComercio,
      required this.titulo,
      required this.tienda,
      this.descripcion,
      this.emoji,
      this.cupon,
      required this.porcentaje,
      this.tope,
      required this.fechaFin,
      this.idQr,
      required this.tieneTienda});

  factory Promo.fromJson(Map<String, dynamic> j) => Promo(
        idPromocion: j['id_promocion'],
        idComercio: j['id_comercio'],
        titulo: j['titulo'] ?? '',
        tienda: j['tienda'] ?? '',
        descripcion: j['descripcion'],
        emoji: j['emoji'],
        cupon: j['cupon'],
        porcentaje: toD(j['porcentaje']),
        tope: j['tope'] == null ? null : toD(j['tope']),
        fechaFin: parseFecha(j['fecha_fin']),
        idQr: j['id_qr']?.toString(),
        tieneTienda: j['tiene_tienda'] == true,
      );

  String get pct => PromoInfo(titulo: titulo, porcentaje: porcentaje).pct;
}

class Oferta {
  final int id, stock, pct;
  final double precio;
  final DateTime fin;
  Oferta({required this.id, required this.precio, required this.stock, required this.fin, required this.pct});
  static Oferta? fromJson(dynamic j) =>
      j == null ? null : Oferta(id: j['id'], precio: toD(j['precio']), stock: j['stock'] ?? 0, fin: parseFecha(j['fin']), pct: j['pct'] ?? 0);
}

class Producto {
  final int idProducto, idComercio, stock;
  final String nombre, tienda;
  final String? categoria, emoji;
  final double precio;
  final Oferta? oferta;
  final PromoInfo? promo;

  Producto(
      {required this.idProducto,
      required this.idComercio,
      required this.stock,
      required this.nombre,
      required this.tienda,
      this.categoria,
      this.emoji,
      required this.precio,
      this.oferta,
      this.promo});

  factory Producto.fromJson(Map<String, dynamic> j) => Producto(
        idProducto: j['id_producto'],
        idComercio: j['id_comercio'],
        stock: j['stock'] ?? 0,
        nombre: j['nombre'] ?? '',
        tienda: j['tienda'] ?? '',
        categoria: j['categoria'],
        emoji: j['emoji'],
        precio: toD(j['precio']),
        oferta: Oferta.fromJson(j['oferta']),
        promo: PromoInfo.fromJson(j['promo']),
      );
}

class Tienda {
  final int idComercio;
  final String nombre;
  final String? emoji;
  Tienda(this.idComercio, this.nombre, this.emoji);
  factory Tienda.fromJson(Map<String, dynamic> j) => Tienda(j['id_comercio'], j['nombre'] ?? '', j['emoji']);
}

class OrdenItem {
  final String nombre;
  final int cantidad;
  final double precioUnitario;
  OrdenItem(this.nombre, this.cantidad, this.precioUnitario);
  factory OrdenItem.fromJson(Map<String, dynamic> j) => OrdenItem(j['nombre'] ?? '', j['cantidad'] ?? 0, toD(j['precio_unitario']));
}

class Orden {
  final int idOrden;
  final String tienda, estado, codigoRecojo;
  final double total, descuento;
  final DateTime fechaHora;
  final List<OrdenItem> items;

  Orden(
      {required this.idOrden,
      required this.tienda,
      required this.estado,
      required this.codigoRecojo,
      required this.total,
      required this.descuento,
      required this.fechaHora,
      required this.items});

  factory Orden.fromJson(Map<String, dynamic> j) => Orden(
        idOrden: j['id_orden'],
        tienda: j['tienda'] ?? '',
        estado: j['estado'] ?? 'pagada',
        codigoRecojo: j['codigo_recojo'] ?? '',
        total: toD(j['total']),
        descuento: toD(j['descuento']),
        fechaHora: parseFecha(j['fecha_hora']),
        items: ((j['items'] ?? []) as List).map((e) => OrdenItem.fromJson(e)).toList(),
      );
}

/// Datos de un codigo_qr listo para pagar.
class QrInfo {
  final String idQr; // UUID del QR en COREDB
  final String tipo, nombre;
  final double? monto;
  final bool esComercio;
  final PromoInfo? promo;

  QrInfo({required this.idQr, required this.tipo, required this.nombre, this.monto, required this.esComercio, this.promo});

  factory QrInfo.fromJson(Map<String, dynamic> j) => QrInfo(
        idQr: '${j['id_qr']}',
        tipo: '${j['tipo']}'.toLowerCase(),
        nombre: j['nombre'] ?? '',
        monto: j['monto'] == null ? null : toD(j['monto']),
        esComercio: j['es_comercio'] == true,
        promo: PromoInfo.fromJson(j['promo']),
      );

  bool get dinamico => tipo == 'dinamico';
}

/// Trama del QR de Chaski: `CHASKI|<id_qr>`, con el UUID del QR que da COREDB.
final uuidRe = RegExp(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$');
final qrRe = RegExp(r'^CHASKI\|([0-9a-fA-F-]{36})$');
String tramaQr(String idQr) => 'CHASKI|$idQr';
