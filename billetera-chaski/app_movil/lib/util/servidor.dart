/// Configuración del servidor de Chaski: la trama que el banco muestra en su pantalla Billetera
/// (`CHASKI-SERVIDOR|<url>`) y la dirección que escribe la persona.
final _tramaServidor = RegExp(r'^CHASKI-SERVIDOR\s*\|\s*(.*)$');
final _urlConEsquema = RegExp(r'^([A-Za-z][A-Za-z0-9+.-]*)://(\S+)$');

/// Devuelve la URL normalizada, o null si la trama no es de configuración o la dirección no es
/// http(s) sin credenciales. El esquema y el host se normalizan y se quita la barra final.
String? parsearServidor(String entrada) {
  final texto = entrada.trim();
  final valor = _tramaServidor.firstMatch(texto)?.group(1)?.trim() ?? texto;
  final m = _urlConEsquema.firstMatch(valor);
  if (m == null) return null;
  final esquema = m.group(1)!.toLowerCase();
  if (esquema != 'http' && esquema != 'https') return null;
  final uri = Uri.tryParse('$esquema://${m.group(2)}');
  if (uri == null || uri.host.isEmpty || uri.userInfo.isNotEmpty) return null;
  if (uri.path.isNotEmpty && uri.path != '/' || uri.query.isNotEmpty || uri.fragment.isNotEmpty) return null;
  return uri.toString().replaceAll(RegExp(r'/+$'), '');
}
