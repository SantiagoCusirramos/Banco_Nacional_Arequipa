"""Acceso a base de datos. MySQL en produccion; SQLite solo para pruebas automaticas."""
import os
import sqlite3
from decimal import Decimal
from urllib.parse import urlparse, unquote

sqlite3.register_adapter(Decimal, str)


def cargar_env(ruta=".env"):
    """Lee un archivo .env sencillo (CLAVE=valor) sin dependencias externas."""
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())


class DB:
    def __init__(self, conn, dialecto):
        self.conn = conn
        self.dialecto = dialecto

    def _sql(self, sql):
        return sql.replace("%s", "?") if self.dialecto == "sqlite" else sql

    def _ejecutar(self, sql, params):
        cur = self.conn.cursor()
        if self.dialecto == "sqlite":
            cur.execute(self._sql(sql), tuple(params))
        else:
            cur.execute(sql, tuple(params) if params else None)
        return cur

    @staticmethod
    def _fila(fila):
        if fila is None:
            return None
        return fila if isinstance(fila, dict) else dict(fila)

    def uno(self, sql, params=()):
        cur = self._ejecutar(sql, params)
        fila = cur.fetchone()
        cur.close()
        return self._fila(fila)

    def todos(self, sql, params=()):
        cur = self._ejecutar(sql, params)
        filas = cur.fetchall()
        cur.close()
        return [self._fila(f) for f in filas]

    def ejecutar(self, sql, params=()):
        cur = self._ejecutar(sql, params)
        cur.close()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def cerrar(self):
        self.conn.close()


def conectar(url=None):
    url = url or os.environ.get("DATABASE_URL", "sqlite:///cobranza_demo.db")
    if url.startswith("sqlite"):
        ruta = url.replace("sqlite:///", "", 1) or ":memory:"
        conn = sqlite3.connect(ruta, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return DB(conn, "sqlite")
    import pymysql
    u = urlparse(url)
    conn = pymysql.connect(
        host=u.hostname, port=u.port or 3306,
        user=unquote(u.username or ""), password=unquote(u.password or ""),
        database=u.path.lstrip("/"), charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=False,
    )
    return DB(conn, "mysql")


DDL = [
    """CREATE TABLE IF NOT EXISTS CREDITO (
        codCredito VARCHAR(20) NOT NULL PRIMARY KEY,
        idCliente VARCHAR(20) NOT NULL,
        idSolicitud VARCHAR(20) NOT NULL,
        montoAprobado DECIMAL(14,2) NOT NULL CHECK (montoAprobado > 0),
        moneda CHAR(3) NOT NULL DEFAULT 'PEN' CHECK (moneda IN ('PEN','USD')),
        fechaDesembolso DATETIME NOT NULL,
        estadoCredito VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'
    )""",
    """CREATE TABLE IF NOT EXISTS CUOTA (
        idCuota VARCHAR(20) NOT NULL PRIMARY KEY,
        codCredito VARCHAR(20) NOT NULL,
        numeroCuota INT NOT NULL CHECK (numeroCuota > 0),
        fechaVencimiento DATE NOT NULL,
        montoCuota DECIMAL(14,2) NOT NULL CHECK (montoCuota > 0),
        saldoPendiente DECIMAL(14,2) NOT NULL CHECK (saldoPendiente >= 0),
        moraPendiente DECIMAL(14,2) NOT NULL DEFAULT 0.00 CHECK (moraPendiente >= 0),
        estadoCuota VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
        UNIQUE (codCredito, numeroCuota),
        FOREIGN KEY (codCredito) REFERENCES CREDITO(codCredito)
    )""",
    """CREATE TABLE IF NOT EXISTS CANAL_PAGO (
        idCanal VARCHAR(10) NOT NULL PRIMARY KEY,
        nombreCanal VARCHAR(50) NOT NULL UNIQUE,
        tipoIntegracion VARCHAR(30) NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS PAGO (
        idPago VARCHAR(20) NOT NULL PRIMARY KEY,
        codCredito VARCHAR(20) NOT NULL,
        idCanal VARCHAR(10) NOT NULL,
        fechaHora DATETIME NOT NULL,
        montoPago DECIMAL(14,2) NOT NULL CHECK (montoPago > 0),
        montoMora DECIMAL(14,2) NOT NULL DEFAULT 0.00 CHECK (montoMora >= 0),
        montoCapital DECIMAL(14,2) NOT NULL DEFAULT 0.00 CHECK (montoCapital >= 0),
        referenciaTransaccion VARCHAR(40) NOT NULL UNIQUE,
        estadoConfirmacion VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
        cuentaOrigen VARCHAR(30) NULL,
        FOREIGN KEY (codCredito) REFERENCES CREDITO(codCredito),
        FOREIGN KEY (idCanal) REFERENCES CANAL_PAGO(idCanal)
    )""",
    """CREATE TABLE IF NOT EXISTS APLICACION_PAGO (
        idAplicacion VARCHAR(20) NOT NULL PRIMARY KEY,
        idPago VARCHAR(20) NOT NULL,
        idCuota VARCHAR(20) NOT NULL,
        montoAplicado DECIMAL(14,2) NOT NULL CHECK (montoAplicado > 0),
        FOREIGN KEY (idPago) REFERENCES PAGO(idPago),
        FOREIGN KEY (idCuota) REFERENCES CUOTA(idCuota)
    )""",
    """CREATE TABLE IF NOT EXISTS MORA (
        idMora VARCHAR(20) NOT NULL PRIMARY KEY,
        idCuota VARCHAR(20) NOT NULL,
        diasAtraso INT NOT NULL CHECK (diasAtraso >= 0),
        montoCalculado DECIMAL(14,2) NOT NULL CHECK (montoCalculado >= 0),
        fechaCalculo DATETIME NOT NULL,
        vigente BOOLEAN NOT NULL DEFAULT TRUE,
        FOREIGN KEY (idCuota) REFERENCES CUOTA(idCuota)
    )""",
    """CREATE TABLE IF NOT EXISTS EVENTO_AUDITORIA (
        idEvento VARCHAR(20) NOT NULL PRIMARY KEY,
        idEntidad VARCHAR(20) NOT NULL,
        tipoEvento VARCHAR(30) NOT NULL,
        `timestamp` DATETIME NOT NULL,
        moduloEmisor VARCHAR(30) NOT NULL,
        usuarioOperador VARCHAR(30) NOT NULL,
        resultado VARCHAR(20) NOT NULL DEFAULT 'EXITOSO'
    )""",
]


# Columnas agregadas despues de la creacion inicial del esquema. CREATE TABLE IF NOT EXISTS no las
# agrega a una tabla que ya existia sin ellas, asi que en MySQL se migran aparte en crear_esquema().
COLUMNAS_NUEVAS = [
    ("CUOTA", "moraPendiente", "DECIMAL(14,2) NOT NULL DEFAULT 0.00"),
    ("PAGO", "montoMora", "DECIMAL(14,2) NOT NULL DEFAULT 0.00"),
    ("PAGO", "montoCapital", "DECIMAL(14,2) NOT NULL DEFAULT 0.00"),
    ("EVENTO_AUDITORIA", "resultado", "VARCHAR(20) NOT NULL DEFAULT 'EXITOSO'"),
    # Integracion con CUENTAS del producto BNA: la cuenta debitada (campo cuentaOrigen de CR-INT-08),
    # necesaria para consultar despues el cargo de un pago PENDIENTE (RF-COB-011) y para RN-COB-012.
    ("PAGO", "cuentaOrigen", "VARCHAR(30) NULL"),
]


def migrar_esquema(db):
    """Migracion simple e idempotente para MySQL: agrega COLUMNAS_NUEVAS si faltan, consultando
    information_schema. No hace nada en SQLite (las pruebas siempre parten de un esquema nuevo)."""
    if db.dialecto != "mysql":
        return
    for tabla, columna, definicion in COLUMNAS_NUEVAS:
        existe = db.uno(
            "SELECT COLUMN_NAME FROM information_schema.columns WHERE TABLE_SCHEMA = DATABASE() "
            "AND LOWER(TABLE_NAME) = LOWER(%s) AND LOWER(COLUMN_NAME) = LOWER(%s)",
            (tabla, columna))
        if not existe:
            db.ejecutar(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
            db.commit()


def crear_esquema(db):
    sufijo = " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4" if db.dialecto == "mysql" else ""
    for ddl in DDL:
        db.ejecutar(ddl + sufijo)
    db.commit()
    migrar_esquema(db)
    if not db.uno("SELECT idCanal FROM CANAL_PAGO WHERE idCanal = %s", ("HB",)):
        db.ejecutar(
            "INSERT INTO CANAL_PAGO (idCanal, nombreCanal, tipoIntegracion) VALUES (%s, %s, %s)",
            ("HB", "Home Banking", "API REST via Bus de Servicios"),
        )
        db.commit()
