"""Administración local explícita. No hay usuarios ni passwords preinstalados."""
import argparse
import getpass
import json
from uuid import uuid4
from .config import Settings
from .store import Store
from .security import HASHER


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create-user')
    create.add_argument('username')
    create.add_argument('--role', choices=['ADMINISTRADOR', 'AUDITOR', 'OPERADOR', 'CLIENTE'], required=True)
    sub.add_parser('backup')
    args = p.parse_args()
    state = Store(Settings.from_env())
    if args.command == 'create-user':
        password = getpass.getpass('Contraseña local (mínimo 12 caracteres): ')
        if len(password) < 12 or len(password) > 128:
            p.error('Contraseña: entre 12 y 128 caracteres')
        with state.transaction() as db:
            uid = str(uuid4())
            db.execute('INSERT INTO users(id,username,password_hash,role) VALUES(?,?,?,?)',
                       (uid, args.username, HASHER.hash(password), args.role))
            state.audit(db, 'USUARIO_LOCAL_CREADO', 'administracion-local', 'cli', {'id': uid, 'role': args.role})
        print('Usuario creado. No corresponde a una identidad del CORE.')
    else:
        import sqlite3
        from datetime import datetime, timezone
        path = state.settings.database + '.' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '.backup'
        with sqlite3.connect(state.settings.database) as source, sqlite3.connect(path) as target:
            source.backup(target)
        print(json.dumps({'backup': path, 'note': 'Custodiar también SEGURIDAD_SECRET_KEY por separado'}))


if __name__ == '__main__':
    main()
