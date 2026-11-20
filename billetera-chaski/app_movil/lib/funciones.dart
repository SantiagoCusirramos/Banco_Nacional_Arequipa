/// Funciones de la app que la API integrada no ofrece en esta versión (decisión pendiente del
/// equipo, ver billetera-chaski/README.md). En false, la app no las muestra ni llama a sus rutas.
class Funciones {
  /// La billetera la activa el banco (punto R-01): POST /api/registro responde 403.
  static const registro = false;

  /// Promociones, ofertas y cupones (pantallas de tienda_screens.dart): la API da listas vacías y 501.
  static const promociones = false;

  /// Tienda y carrito: 501.
  static const tienda = false;

  /// Órdenes («Mis pedidos»): 501.
  static const ordenes = false;

  /// Recargas y pago de servicios (servicios_screen.dart): 501.
  static const servicios = false;
}
