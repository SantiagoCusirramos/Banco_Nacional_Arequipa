import 'package:chaski_app/models.dart';
import 'package:chaski_app/state/app_state.dart';
import 'package:chaski_app/util/format.dart';
import 'package:flutter_test/flutter_test.dart';

Producto prod(int id, double precio, {Map<String, dynamic>? oferta, Map<String, dynamic>? promo, int comercio = 1}) => Producto.fromJson({
      'id_producto': id,
      'id_comercio': comercio,
      'tienda': 'Tienda $comercio',
      'nombre': 'Producto $id',
      'precio': precio,
      'stock': 50,
      'oferta': oferta,
      'promo': promo,
    });

void main() {
  test('teclado de montos: máximo 3 enteros y 2 decimales', () {
    var v = '';
    for (final k in ['0', '5', '0', '0', '0', '.', '2', '5', '9']) {
      v = teclear(v, k);
    }
    expect(v, '500.25');
    expect(teclear('12', '⌫'), '1');
    expect(teclear('', '.'), '0.');
    expect(teclear('1.5', '.'), '1.5');
  });

  test('formato de soles y número de operación', () {
    expect(soles(8.5), 'S/ 8.50');
    expect(nroOperacion(42), '00000042');
    expect(celularRe.hasMatch('900000001'), isTrue);
    expect(celularRe.hasMatch('800000001'), isFalse);
  });

  test('promo con tope', () {
    final p = PromoInfo(titulo: 'x', porcentaje: 15, tope: 10);
    expect(p.descuento(10), 1.5);
    expect(p.descuento(100), 10);
    expect(p.pct, '15');
  });

  test('trama QR', () {
    const id = 'a5db6a6f-6de7-4e6f-9c7b-af6e43a06fcc'; // el id del QR es el UUID que da COREDB
    expect(qrRe.firstMatch(tramaQr(id))!.group(1), id);
    expect(uuidRe.hasMatch(id), isTrue);
    expect(qrRe.hasMatch('CHASKI|7'), isFalse);
    expect(qrRe.hasMatch('https://otro.qr'), isFalse);
  });

  test('modelos con la respuesta real de la API sobre COREDB', () {
    final me = Me.fromJson({
      'cliente': {'id_cliente': 'CLI000000016', 'nombres': 'Rosa H.', 'apellidos': '', 'nombre_corto': 'Rosa H.'},
      'cuenta': {'id_cuenta': 'CTA-0017950647181350', 'numero_cuenta_virtual': 'CTA-0017950647181350', 'saldo_actual': 1000, 'moneda': 'PEN'},
      'no_leidas': 0, 'pendientes': 0, 'limite': 500, 'tope_diario': 500, 'disponible_hoy': 500,
    });
    expect(me.cliente.idCliente, 'CLI000000016');
    expect(me.cuenta.saldoActual, 1000);
    final m = Movimiento.fromJson({
      'id_movimiento': 'a1afe391-77cd-4b1d-94e8-37e25a881560', 'tipo_movimiento': 'deposito', 'monto': -25,
      'fecha_hora': '2026-11-19T05:05:18.227835', 'descripcion': 'Pasaje', 'canal': 'BD',
    });
    expect(m.saldoResultante, isNull);
    expect(m.monto, -25);
    expect(m.tipoLegible, 'Depósito');
    expect(Movimiento.fromRow(m.toRow(me.cliente.idCliente)).idMovimiento, m.idMovimiento);
    final s = Solicitud.fromJson({'id_solicitud': '6c1f0c1e-5a0b-4f8e-9a63-0f6a9c1b2d3e', 'monto': 10, 'estado': 'pendiente',
      'nombre': 'Alberto Q.', 'fecha': '2026-11-19T05:05:18'});
    expect(s.id, '6c1f0c1e-5a0b-4f8e-9a63-0f6a9c1b2d3e');
    final q = QrInfo.fromJson({'id_qr': 'a5db6a6f-6de7-4e6f-9c7b-af6e43a06fcc', 'tipo': 'estatico', 'nombre': 'Bodega Don Beto',
      'monto': null, 'es_comercio': true});
    expect(q.dinamico, isFalse);
    expect(q.esComercio, isTrue);
  });

  test('carrito: la oferta gana a la promo y cubre solo sus cupos', () {
    final st = AppState();
    final conOferta = prod(1, 20, oferta: {'id': 1, 'precio': 15, 'stock': 1, 'fin': '2099-01-01T00:00:00Z', 'pct': 25}, promo: {'titulo': 'p', 'porcentaje': 10, 'tope': null});
    st.cambiarCarrito(conOferta, 1);
    st.cambiarCarrito(conOferta, 1); // 1 a precio oferta + 1 a precio normal
    final r = st.calcCarrito();
    // subtotal 15 + 20 = 35; promo 10% sobre lo que no está en oferta (20) = 2
    expect(r.total, 33);
    expect(r.ahorro, 7); // 5 por oferta + 2 por promo
    expect(st.carritoN, 2);
  });

  test('carrito agrupa por tienda y respeta el máximo por producto', () {
    final st = AppState();
    st.cambiarCarrito(prod(1, 10, comercio: 1), 1);
    st.cambiarCarrito(prod(2, 5, comercio: 2), 1);
    expect(st.calcCarrito().grupos.length, 2);
    final p = prod(3, 1);
    for (var i = 0; i < 10; i++) {
      expect(st.cambiarCarrito(p, 1), isNull);
    }
    expect(st.cambiarCarrito(p, 1), 'Máximo 10 por producto');
  });
}
