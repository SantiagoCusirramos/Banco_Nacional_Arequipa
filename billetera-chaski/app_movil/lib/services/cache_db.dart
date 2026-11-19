import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import '../models.dart';

/// Persistencia local en SQLite: guarda el último saldo e historial para el
/// "Modo fuera de línea" (CUS-BD-004, FA-01). Las columnas numéricas son REAL → double.
class CacheDb {
  Database? _db;

  Future<Database> get db async => _db ??= await openDatabase(
        p.join(await getDatabasesPath(), 'chaski_cache.db'),
        // v2: los ids del CORE son texto (CLI…, UUID de movimientos) y no hay saldo resultante.
        version: 2,
        onUpgrade: (db, antes, ahora) async {
          await db.execute("DROP TABLE IF EXISTS cuenta_cache");
          await db.execute("DROP TABLE IF EXISTS movimiento_cache");
          await _crear(db);
        },
        onCreate: (db, v) => _crear(db),
      );

  static Future<void> _crear(Database db) async {
          await db.execute('''
            CREATE TABLE cuenta_cache (
              id_cliente TEXT PRIMARY KEY,
              numero_cuenta_virtual TEXT NOT NULL,
              saldo_actual REAL NOT NULL,
              datos TEXT NOT NULL,
              actualizado TEXT NOT NULL
            )''');
          await db.execute('''
            CREATE TABLE movimiento_cache (
              id_movimiento TEXT PRIMARY KEY,
              id_cliente TEXT NOT NULL,
              tipo_movimiento TEXT NOT NULL,
              monto REAL NOT NULL,
              saldo_resultante REAL,
              fecha_hora TEXT NOT NULL,
              descripcion TEXT
            )''');
          await db.execute('CREATE INDEX ix_movc_cliente ON movimiento_cache (id_cliente, fecha_hora DESC)');
  }

  Future<void> guardar(Me me, List<Movimiento> movs) async {
    final d = await db;
    final id = me.cliente.idCliente;
    await d.transaction((t) async {
      await t.insert(
        'cuenta_cache',
        {
          'id_cliente': id,
          'numero_cuenta_virtual': me.cuenta.numeroCuentaVirtual,
          'saldo_actual': me.cuenta.saldoActual,
          'datos': jsonEncode(me.toJson()),
          'actualizado': DateTime.now().toUtc().toIso8601String(),
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
      await t.delete('movimiento_cache', where: 'id_cliente = ?', whereArgs: [id]);
      final b = t.batch();
      for (final m in movs) {
        b.insert('movimiento_cache', m.toRow(id), conflictAlgorithm: ConflictAlgorithm.replace);
      }
      await b.commit(noResult: true);
    });
  }

  Future<({Me me, List<Movimiento> movs, DateTime actualizado})?> leer(String idCliente) async {
    final d = await db;
    final c = await d.query('cuenta_cache', where: 'id_cliente = ?', whereArgs: [idCliente]);
    if (c.isEmpty) return null;
    final movs = await d.query('movimiento_cache', where: 'id_cliente = ?', whereArgs: [idCliente], orderBy: 'fecha_hora DESC');
    return (
      me: Me.fromJson(jsonDecode(c.first['datos'] as String)),
      movs: movs.map(Movimiento.fromRow).toList(),
      actualizado: DateTime.parse(c.first['actualizado'] as String),
    );
  }

  Future<void> limpiar() async {
    final d = await db;
    await d.delete('cuenta_cache');
    await d.delete('movimiento_cache');
  }
}
