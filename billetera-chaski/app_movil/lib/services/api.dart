import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final int status;
  final String message;

  /// true cuando no hubo respuesta del servidor (sin red, timeout).
  final bool red;

  ApiException(this.status, this.message, {this.red = false});

  @override
  String toString() => message;
}

/// Cliente REST/JSON de la API de Chaski.
class Api {
  /// Ante un timeout mayor a 15 s la operación se anula (estándar del BNA).
  static const timeout = Duration(seconds: 15);

  String baseUrl;
  String? token;
  void Function()? onUnauthorized;
  final http.Client _http;

  /// [cliente] permite simular el HTTP en las pruebas.
  Api(this.baseUrl, {http.Client? cliente}) : _http = cliente ?? http.Client();

  Uri _uri(String path) => Uri.parse('${baseUrl.replaceAll(RegExp(r'/+$'), '')}/api$path');

  Future<dynamic> get(String path) => _send('GET', path);

  /// [uuid] es el uuidTransaccion de idempotencia: si se reintenta con el mismo valor, el servidor no cobra dos veces.
  Future<dynamic> post(String path, [Map<String, dynamic>? body, String? uuid]) => _send('POST', path, body: body ?? {}, uuid: uuid);

  Future<dynamic> _send(String method, String path, {Map<String, dynamic>? body, String? uuid}) async {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
      if (uuid != null) 'Idempotency-Key': uuid,
    };
    http.Response res;
    try {
      final req = method == 'GET' ? _http.get(_uri(path), headers: headers) : _http.post(_uri(path), headers: headers, body: jsonEncode(body));
      res = await req.timeout(timeout);
    } on TimeoutException {
      throw ApiException(0, 'El servidor tardó demasiado en responder. Inténtalo de nuevo.', red: true);
    } on SocketException {
      throw ApiException(0, 'Sin conexión con el servidor de Chaski', red: true);
    } on http.ClientException {
      throw ApiException(0, 'Sin conexión con el servidor de Chaski', red: true);
    } on FormatException {
      throw ApiException(0, 'La dirección del servidor no es válida', red: true);
    } on ArgumentError {
      throw ApiException(0, 'La dirección del servidor no es válida', red: true);
    }
    dynamic data;
    try {
      data = res.body.isEmpty ? {} : jsonDecode(utf8.decode(res.bodyBytes));
    } catch (_) {
      data = {};
    }
    if (res.statusCode == 401 && token != null && path != '/login' && path != '/pin/verificar') {
      onUnauthorized?.call();
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      final msg = data is Map && data['error'] is String ? data['error'] as String : 'Ocurrió un error (${res.statusCode})';
      throw ApiException(res.statusCode, msg);
    }
    return data;
  }
}
