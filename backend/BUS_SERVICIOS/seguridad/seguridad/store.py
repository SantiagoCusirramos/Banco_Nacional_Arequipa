"""Persistencia de laboratorio. BEGIN IMMEDIATE serializa intentos y decisiones."""
import hashlib
import hmac
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class Store:
    def __init__(self, settings):
        self.settings = settings
        Path(settings.database).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
              role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
              failures INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0,
              token_version INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS audit (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL,
              previous TEXT NOT NULL, signature TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS challenges (
              id TEXT PRIMARY KEY, user_id TEXT NOT NULL, operation_id TEXT NOT NULL,
              amount TEXT NOT NULL, currency TEXT NOT NULL, channel TEXT NOT NULL,
              expires REAL NOT NULL, digest TEXT NOT NULL, tries INTEGER NOT NULL DEFAULT 0,
              used INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS decisions (
              operation_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, amount TEXT NOT NULL,
              currency TEXT NOT NULL, channel TEXT NOT NULL, day TEXT NOT NULL,
              result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS incidents (
              id TEXT PRIMARY KEY, priority TEXT NOT NULL, title TEXT NOT NULL,
              status TEXT NOT NULL, actor TEXT NOT NULL, created TEXT NOT NULL,
              updated TEXT NOT NULL, resolution TEXT);
            ''')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.settings.database, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def sign(self, text):
        # Separación de dominio respecto de la firma JWT.
        return hmac.new(self.settings.secret.encode(), ('audit-v1:' + text).encode(), hashlib.sha256).hexdigest()

    def audit(self, db, event, actor, correlation, detail=None):
        last = db.execute('SELECT signature FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
        previous = last['signature'] if last else '0' * 64
        payload = canonical(dict(time=utcnow(), event=event, actor=actor,
                                 correlation_id=correlation, detail=detail or {}))
        db.execute('INSERT INTO audit(payload,previous,signature) VALUES(?,?,?)',
                   (payload, previous, self.sign(previous + payload)))

    def verify(self, db):
        previous = '0' * 64
        count = 0
        for row in db.execute('SELECT * FROM audit ORDER BY seq'):
            if row['seq'] != count + 1 or row['previous'] != previous or not hmac.compare_digest(row['signature'], self.sign(previous + row['payload'])):
                return dict(valid=False, checked=count, broken_at=row['seq'])
            previous = row['signature']
            count += 1
        return dict(valid=True, checked=count, head=previous,
                    limitation='Sin anclaje externo: no detecta truncado de la cola ni reescritura con la clave')
