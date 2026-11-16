"""Explicit lab gates. Never imported by the bank modules."""
import os
import sys


def main(args):
    flags, command = args[:args.index('--')], args[args.index('--')+1:]
    if '--ddl' in flags and os.getenv('LAB_ALLOW_DDL') != 'YES_ISOLATED_LAB':
        raise SystemExit('Bloqueado: falta autorización de escrituras del laboratorio aislado.')
    if '--audit' in flags and os.getenv('LAB_AUDIT_SIM_AUTHORIZATION') != 'AUTHORIZED_ACADEMIC_ONLY':
        raise SystemExit('Bloqueado: falta autorización explícita de auditoría simulada académica.')
    if not command:
        raise SystemExit('Falta comando.')
    os.execvp(command[0], command)


if __name__ == '__main__':
    main(sys.argv[1:])
