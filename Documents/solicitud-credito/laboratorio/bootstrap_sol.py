"""Minimal SOL schema/user provisioning. SQL only when explicitly run in isolated lab."""
import os
import re


def main():
    if os.getenv('LAB_ALLOW_DDL') != 'YES_ISOLATED_LAB':
        raise SystemExit('DDL no autorizado.')
    if os.environ['SOL_DB_HOST'] != 'mysql-modulos' or os.environ['SOL_DB_USER'] != 'sol_lab':
        raise SystemExit('Destino ajeno al laboratorio.')
    name = os.environ['SOL_DB_NAME']
    if not re.fullmatch(r'bna_sol_mvp_[a-z0-9]{8,24}', name):
        raise SystemExit('Esquema de laboratorio inválido.')
    import pymysql
    connection = pymysql.connect(host='mysql-modulos', port=3306, user='root',
                                 password=os.environ['AUX_DB_ROOT_PASSWORD'], autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4')
            cursor.execute("CREATE USER IF NOT EXISTS 'sol_lab'@'%%' IDENTIFIED BY %s", (os.environ['SOL_DB_PASSWORD'],))
            cursor.execute("ALTER USER 'sol_lab'@'%%' IDENTIFIED BY %s", (os.environ['SOL_DB_PASSWORD'],))
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{name}`.* TO 'sol_lab'@'%'")
    finally:
        connection.close()
    print('Bootstrap SOL de laboratorio completado; sin datos bancarios.')


if __name__ == '__main__':
    main()
