import 'package:uuid/uuid.dart';

import '../state/app_state.dart';
import 'api.dart';

/// Busca a un cliente de Chaski por su celular. El celular va en el cuerpo, nunca en la URL: el Bus y
/// los servidores registran las rutas con su consulta.
Future<Map<String, dynamic>> buscarContacto(Api api, String celular) async =>
    Map<String, dynamic>.from(await api.post('/clientes/buscar', {'celular': celular}));

/// Una operación con su uuid de idempotencia (RN-BUS-002), que se repite en cada reintento: si el
/// servidor ya la hizo, devuelve la misma (`repetida: true`) sin cobrar dos veces.
class IntentoOperacion {
  final String llave;
  final Duration espera;

  IntentoOperacion({String? llave, this.espera = const Duration(seconds: 1)}) : llave = llave ?? const Uuid().v4();

  /// Ejecuta [f] con la llave; ante un corte de red (sin respuesta) espera y reintenta una vez con la
  /// misma llave. Si vuelve a fallar, quien llama puede llamar otra vez a [ejecutar]: la llave no cambia.
  Future<T> ejecutar<T>(Future<T> Function(String llave) f) async {
    try {
      return await f(llave);
    } on ApiException catch (e) {
      if (!e.red) rethrow;
      await Future.delayed(espera);
      return await f(llave);
    }
  }
}

/// Rechaza o cancela una solicitud de cobro con su Idempotency-Key. La llave se guarda en el estado
/// mientras no se sepa el resultado (corte de red o error del servidor), así un segundo toque usa la
/// misma; se descarta cuando la API responde o rechaza la acción (4xx).
Future<dynamic> responderSolicitud(AppState st, String id, String accion, {Duration espera = const Duration(seconds: 1)}) async {
  final clave = '$id:$accion';
  final intento = st.intentos.putIfAbsent(clave, () => IntentoOperacion(espera: espera));
  try {
    final r = await intento.ejecutar((llave) => st.api.post('/solicitudes/$id/responder', {'accion': accion}, llave));
    st.intentos.remove(clave);
    return r;
  } on ApiException catch (e) {
    if (e.status >= 400 && e.status < 500) st.intentos.remove(clave);
    rethrow;
  }
}
