import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Paleta de Chaski (la misma de la versión web).
class C {
  static const ink = Color(0xFF4A1568);
  static const ink2 = Color(0xFF6A2A8E);
  static const teal = Color(0xFF18C2B4);
  static const sun = Color(0xFFFFB020);
  static const mist = Color(0xFFF4EFF8);
  static const line = Color(0xFFE3D9EC);
  static const text = Color(0xFF22102E);
  static const muted = Color(0xFF6F5F7D);
  static const danger = Color(0xFFD64545);
  static const ok = Color(0xFF12A150);
  static const sunDark = Color(0xFFB26B00);

  /// Fondo suave por comercio, para tarjetas de productos y promos.
  static Color tono(int id) => const [
        Color(0xFFEFE4F7),
        Color(0xFFFFF1D6),
        Color(0xFFDFF3F0),
        Color(0xFFFBE7EC),
        Color(0xFFE7EEFB),
      ][id % 5];
}

ThemeData chaskiTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: C.ink,
      primary: C.ink,
      secondary: C.sun,
      tertiary: C.teal,
      surface: C.mist,
      error: C.danger,
    ),
    scaffoldBackgroundColor: C.mist,
  );
  return base.copyWith(
    textTheme: base.textTheme.apply(bodyColor: C.text, displayColor: C.text),
    appBarTheme: const AppBarTheme(
      backgroundColor: C.mist,
      foregroundColor: C.text,
      elevation: 0,
      scrolledUnderElevation: 0,
      systemOverlayStyle:
          SystemUiOverlayStyle(statusBarColor: Colors.transparent, statusBarIconBrightness: Brightness.dark, statusBarBrightness: Brightness.light),
      centerTitle: false,
      titleTextStyle: TextStyle(fontSize: 19, fontWeight: FontWeight.w600, color: C.text),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.line, width: 2)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.line, width: 2)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.teal, width: 2)),
      counterStyle: const TextStyle(fontSize: 0, height: 0),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: C.ink,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: C.ink,
        minimumSize: const Size.fromHeight(54),
        side: const BorderSide(color: C.line, width: 2),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: C.text,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
  );
}

/// Íconos claros de la barra de estado para pantallas con fondo morado.
const barraClara = SystemUiOverlayStyle(statusBarColor: Colors.transparent, statusBarIconBrightness: Brightness.light, statusBarBrightness: Brightness.dark);

/// Botón amarillo principal ("sun").
ButtonStyle sunButton() => FilledButton.styleFrom(backgroundColor: C.sun, foregroundColor: C.ink, disabledBackgroundColor: C.sun.withValues(alpha: .4));

/// Botón pequeño.
ButtonStyle smallButton({bool ghost = false}) => ghost
    ? OutlinedButton.styleFrom(
        minimumSize: const Size(0, 40),
        padding: const EdgeInsets.symmetric(horizontal: 16),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)))
    : FilledButton.styleFrom(
        minimumSize: const Size(0, 40),
        padding: const EdgeInsets.symmetric(horizontal: 16),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)));
