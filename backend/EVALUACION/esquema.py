"""Esquema de la base de Evaluación (MySQL 8.4): tablas, triggers y permisos.

Es la única fuente del esquema: la usan el contenedor de arranque (scripts/preparar_base.py) y
las pruebas. Montos en DECIMAL(15,2) y fechas en UTC. Lo recibido de SOL, la situación
financiera registrada, el calendario y el historial no se modifican; una aprobación solo cambia
de estado, una vez, y cada cambio aumenta su versión. El usuario de la aplicación no tiene
DELETE en ninguna tabla.
"""
from __future__ import annotations

import re

BASE = "bna_evaluacion"
USUARIO = "evaluacion_user"

TABLAS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS eva_correlativo (
      tipo   CHAR(3)  NOT NULL COMMENT 'EVA evaluación, APR aprobación, CRE crédito',
      anio   SMALLINT NOT NULL,
      ultimo INT      NOT NULL,
      PRIMARY KEY (tipo, anio),
      CONSTRAINT ck_correlativo_tipo CHECK (tipo IN ('EVA', 'APR', 'CRE'))
    ) ENGINE = InnoDB COMMENT = 'Último número emitido de cada código por año'
    """,
    """
    CREATE TABLE IF NOT EXISTS eva_expediente (
      id_operacion      VARCHAR(80)  NOT NULL COMMENT 'idOperacion de SOL, igual a su X-Idempotency-Key',
      id_solicitud      VARCHAR(36)  NOT NULL,
      version_solicitud INT          NOT NULL,
      id_correlacion    VARCHAR(100) NOT NULL,
      version_contrato  VARCHAR(40)  NOT NULL,
      actor_envio       VARCHAR(60)  NULL,
      simulado          TINYINT(1)   NOT NULL,
      huella            CHAR(64)     NOT NULL COMMENT 'SHA-256 del sobre: una repetición idéntica no crea otro',
      contenido         JSON         NOT NULL COMMENT 'Sobre CR-INT-02 tal como llegó de SOL',
      recibido_en       DATETIME(6)  NOT NULL,
      PRIMARY KEY (id_operacion),
      UNIQUE KEY uk_expediente_version (id_solicitud, version_solicitud),
      CONSTRAINT ck_expediente_version CHECK (version_solicitud >= 1)
    ) ENGINE = InnoDB COMMENT = 'Expedientes recibidos de Solicitud (CR-INT-02); no se modifican'
    """,
    """
    CREATE TABLE IF NOT EXISTS eva_evaluacion (
      id_evaluacion     VARCHAR(20)   NOT NULL COMMENT 'EVA-AAAA-NNNNNN',
      id_operacion      VARCHAR(80)   NOT NULL,
      id_solicitud      VARCHAR(36)   NOT NULL,
      version_solicitud INT           NOT NULL,
      ronda             INT           NOT NULL COMMENT 'La numera Evaluación: 1, 2... por solicitud',
      acuse             VARCHAR(60)   NOT NULL,
      id_cliente        VARCHAR(36)   NOT NULL,
      cliente_nombre    VARCHAR(200)  NOT NULL,
      tipo_documento    VARCHAR(10)   NOT NULL,
      numero_documento  VARCHAR(20)   NOT NULL,
      producto          VARCHAR(100)  NOT NULL,
      destino           VARCHAR(120)  NULL,
      monto_solicitado  DECIMAL(15,2) NOT NULL,
      moneda            CHAR(3)       NOT NULL,
      plazo_meses       INT           NOT NULL,
      tasa_tea          DECIMAL(7,6)  NOT NULL COMMENT 'Fracción: 0.220000 es 22 %',
      estado            VARCHAR(12)   NOT NULL,
      resultado_motor   VARCHAR(10)   NULL,
      score             SMALLINT      NULL,
      limite            DECIMAL(15,2) NULL,
      ratio             DECIMAL(9,4)  NULL,
      regla             VARCHAR(40)   NULL,
      motivo            VARCHAR(1000) NULL COMMENT 'Explicación u observaciones que recibe SOL',
      decidido_por      VARCHAR(60)   NULL COMMENT 'Usuario de COREDB, o MOTOR',
      decidido_en       DATETIME(6)   NULL,
      version           INT           NOT NULL DEFAULT 1,
      recibido_en       DATETIME(6)   NOT NULL,
      actualizado_en    DATETIME(6)   NOT NULL,
      PRIMARY KEY (id_evaluacion),
      UNIQUE KEY uk_evaluacion_operacion (id_operacion),
      UNIQUE KEY uk_evaluacion_ronda (id_solicitud, ronda),
      KEY ix_evaluacion_estado (estado, recibido_en),
      KEY ix_evaluacion_documento (numero_documento),
      CONSTRAINT fk_evaluacion_expediente FOREIGN KEY (id_operacion) REFERENCES eva_expediente (id_operacion),
      CONSTRAINT ck_evaluacion_estado CHECK (estado IN ('PENDIENTE', 'EN_REVISION', 'APROBADO', 'OBSERVADO', 'RECHAZADO')),
      CONSTRAINT ck_evaluacion_motor CHECK (resultado_motor IS NULL OR resultado_motor IN ('APROBADO', 'OBSERVADO', 'RECHAZADO')),
      CONSTRAINT ck_evaluacion_monto CHECK (monto_solicitado > 0),
      CONSTRAINT ck_evaluacion_moneda CHECK (moneda IN ('PEN', 'USD')),
      CONSTRAINT ck_evaluacion_plazo CHECK (plazo_meses >= 1)
    ) ENGINE = InnoDB COMMENT = 'Una evaluación por ronda de una solicitud'
    """,
    """
    CREATE TABLE IF NOT EXISTS eva_situacion_financiera (
      id              BIGINT        NOT NULL AUTO_INCREMENT,
      id_evaluacion   VARCHAR(20)   NOT NULL,
      id_cliente      VARCHAR(36)   NOT NULL,
      ingreso_mensual DECIMAL(15,2) NOT NULL,
      deuda_mensual   DECIMAL(15,2) NOT NULL,
      riesgo          VARCHAR(10)   NOT NULL,
      verificada      TINYINT(1)    NOT NULL,
      registrado_por  VARCHAR(60)   NOT NULL,
      registrado_en   DATETIME(6)   NOT NULL,
      PRIMARY KEY (id),
      UNIQUE KEY uk_situacion_evaluacion (id_evaluacion),
      CONSTRAINT fk_situacion_evaluacion FOREIGN KEY (id_evaluacion) REFERENCES eva_evaluacion (id_evaluacion),
      CONSTRAINT ck_situacion_montos CHECK (ingreso_mensual > 0 AND deuda_mensual >= 0),
      CONSTRAINT ck_situacion_riesgo CHECK (riesgo IN ('BUENO', 'REGULAR', 'ALTO'))
    ) ENGINE = InnoDB COMMENT = 'Situación financiera que sustenta la evaluación; no se modifica'
    """,
    """
    CREATE TABLE IF NOT EXISTS eva_aprobacion (
      id_aprobacion       VARCHAR(20)   NOT NULL COMMENT 'APR-AAAA-NNNNNN',
      id_evaluacion       VARCHAR(20)   NOT NULL,
      id_solicitud        VARCHAR(36)   NOT NULL,
      version_solicitud   INT           NOT NULL,
      cod_credito         VARCHAR(20)   NOT NULL COMMENT 'CRE-AAAA-NNNNNN',
      id_cliente          VARCHAR(36)   NOT NULL,
      cliente_nombre      VARCHAR(200)  NOT NULL,
      tipo_documento      VARCHAR(10)   NOT NULL,
      numero_documento    VARCHAR(20)   NOT NULL,
      producto            VARCHAR(100)  NOT NULL,
      monto_aprobado      DECIMAL(15,2) NOT NULL,
      moneda              CHAR(3)       NOT NULL,
      plazo_meses         INT           NOT NULL,
      tasa_tea            DECIMAL(7,6)  NOT NULL,
      calendario_estado   VARCHAR(20)   NOT NULL COMMENT 'Como lo envió SOL, p. ej. PRELIMINAR',
      calendario_politica VARCHAR(40)   NOT NULL COMMENT 'Versión de la política de SOL',
      cuota_referencial   DECIMAL(15,2) NOT NULL,
      intereses_totales   DECIMAL(15,2) NOT NULL,
      total_pagar         DECIMAL(15,2) NOT NULL,
      estado              VARCHAR(12)   NOT NULL,
      version             INT           NOT NULL DEFAULT 1,
      vigente_hasta       DATETIME(6)   NOT NULL,
      aprobada_por        VARCHAR(60)   NOT NULL,
      aprobada_en         DATETIME(6)   NOT NULL,
      codigo_orden        VARCHAR(30)   NULL COMMENT 'Orden de Desembolso que la usó',
      fecha_desembolso    DATETIME(6)   NULL,
      desembolso_registrado_por VARCHAR(60) NULL,
      revocada_por        VARCHAR(60)   NULL,
      motivo_revocacion   VARCHAR(500)  NULL,
      cambiado_en         DATETIME(6)   NULL,
      PRIMARY KEY (id_aprobacion),
      UNIQUE KEY uk_aprobacion_evaluacion (id_evaluacion),
      UNIQUE KEY uk_aprobacion_credito (cod_credito),
      KEY ix_aprobacion_documento (numero_documento),
      CONSTRAINT fk_aprobacion_evaluacion FOREIGN KEY (id_evaluacion) REFERENCES eva_evaluacion (id_evaluacion),
      CONSTRAINT ck_aprobacion_estado CHECK (estado IN ('VIGENTE', 'DESEMBOLSADA', 'REVOCADA')),
      CONSTRAINT ck_aprobacion_monto CHECK (monto_aprobado > 0),
      CONSTRAINT ck_aprobacion_moneda CHECK (moneda IN ('PEN', 'USD'))
    ) ENGINE = InnoDB COMMENT = 'Aprobación que Desembolso consulta (CR-INT-04)'
    """,
    """
    CREATE TABLE IF NOT EXISTS eva_cuota (
      id_aprobacion     VARCHAR(20)   NOT NULL,
      numero_cuota      INT           NOT NULL,
      fecha_vencimiento DATE          NOT NULL,
      saldo_inicial     DECIMAL(15,2) NOT NULL,
      amortizacion      DECIMAL(15,2) NOT NULL,
      interes           DECIMAL(15,2) NOT NULL,
      cuota_total       DECIMAL(15,2) NOT NULL,
      saldo_final       DECIMAL(15,2) NOT NULL,
      PRIMARY KEY (id_aprobacion, numero_cuota),
      CONSTRAINT fk_cuota_aprobacion FOREIGN KEY (id_aprobacion) REFERENCES eva_aprobacion (id_aprobacion),
      CONSTRAINT ck_cuota_numero CHECK (numero_cuota >= 1),
      CONSTRAINT ck_cuota_total CHECK (cuota_total > 0)
    ) ENGINE = InnoDB COMMENT = 'Calendario de SOL (RN-SOL-006) copiado sin cambios; no se modifica'
    """,
    """
    CREATE TABLE IF NOT EXISTS eva_envio (
      id_operacion      VARCHAR(80)  NOT NULL COMMENT 'idOperacion del resultado, igual a su X-Idempotency-Key',
      id_evaluacion     VARCHAR(20)  NOT NULL,
      interfaz          VARCHAR(10)  NOT NULL,
      contenido         JSON         NOT NULL,
      estado            VARCHAR(12)  NOT NULL,
      intentos          INT          NOT NULL DEFAULT 0,
      siguiente_intento DATETIME(6)  NOT NULL,
      ultimo_error      VARCHAR(200) NULL,
      creado_en         DATETIME(6)  NOT NULL,
      entregado_en      DATETIME(6)  NULL,
      PRIMARY KEY (id_operacion),
      UNIQUE KEY uk_envio_evaluacion (id_evaluacion, interfaz),
      KEY ix_envio_pendiente (estado, siguiente_intento),
      CONSTRAINT fk_envio_evaluacion FOREIGN KEY (id_evaluacion) REFERENCES eva_evaluacion (id_evaluacion),
      CONSTRAINT ck_envio_estado CHECK (estado IN ('PENDIENTE', 'ENTREGADO', 'ERROR')),
      CONSTRAINT ck_envio_interfaz CHECK (interfaz IN ('CR-INT-03'))
    ) ENGINE = InnoDB COMMENT = 'Resultados por entregar a Solicitud (CR-INT-03), al menos una vez'
    """,
    """
    CREATE TABLE IF NOT EXISTS eva_historial (
      id             BIGINT       NOT NULL AUTO_INCREMENT,
      fecha          DATETIME(6)  NOT NULL,
      evento         VARCHAR(40)  NOT NULL,
      actor          VARCHAR(60)  NOT NULL,
      id_evaluacion  VARCHAR(20)  NULL,
      id_aprobacion  VARCHAR(20)  NULL,
      id_correlacion VARCHAR(100) NULL,
      detalle        JSON         NULL,
      PRIMARY KEY (id),
      KEY ix_historial_evaluacion (id_evaluacion, id),
      KEY ix_historial_aprobacion (id_aprobacion, id)
    ) ENGINE = InnoDB COMMENT = 'Trazabilidad de cada cambio; solo se agregan filas'
    """,
]


def _inmutable(tabla: str, operacion: str, mensaje: str) -> tuple[str, str]:
    nombre = f"trg_{tabla}_{'bu' if operacion == 'UPDATE' else 'bd'}"
    return nombre, (f"CREATE TRIGGER {nombre} BEFORE {operacion} ON {tabla} FOR EACH ROW "
                    f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{mensaje}'")


TRIGGERS: list[tuple[str, str]] = [
    _inmutable("eva_expediente", "UPDATE", "EVA-EXPEDIENTE: un expediente recibido no se modifica"),
    _inmutable("eva_expediente", "DELETE", "EVA-EXPEDIENTE: un expediente recibido no se borra"),
    _inmutable("eva_situacion_financiera", "UPDATE", "EVA-SITUACION: la situación registrada no se modifica"),
    _inmutable("eva_situacion_financiera", "DELETE", "EVA-SITUACION: la situación registrada no se borra"),
    _inmutable("eva_cuota", "UPDATE", "EVA-CALENDARIO: el calendario de SOL no se modifica"),
    _inmutable("eva_cuota", "DELETE", "EVA-CALENDARIO: el calendario de SOL no se borra"),
    _inmutable("eva_historial", "UPDATE", "EVA-HISTORIAL: el historial no se modifica"),
    _inmutable("eva_historial", "DELETE", "EVA-HISTORIAL: el historial no se borra"),
    ("trg_eva_evaluacion_bu", """
CREATE TRIGGER trg_eva_evaluacion_bu BEFORE UPDATE ON eva_evaluacion FOR EACH ROW
BEGIN
  IF OLD.estado IN ('APROBADO', 'OBSERVADO', 'RECHAZADO') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'EVA-EVALUACION: una evaluación decidida no se modifica';
  END IF;
  IF NEW.id_operacion <> OLD.id_operacion OR NEW.id_solicitud <> OLD.id_solicitud
     OR NEW.version_solicitud <> OLD.version_solicitud OR NEW.ronda <> OLD.ronda
     OR NEW.id_cliente <> OLD.id_cliente OR NEW.monto_solicitado <> OLD.monto_solicitado
     OR NEW.moneda <> OLD.moneda OR NEW.plazo_meses <> OLD.plazo_meses OR NEW.tasa_tea <> OLD.tasa_tea THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'EVA-EVALUACION: los datos recibidos de SOL no se modifican';
  END IF;
  IF NOT ((OLD.estado = 'PENDIENTE' AND NEW.estado IN ('PENDIENTE', 'EN_REVISION', 'APROBADO', 'RECHAZADO'))
       OR (OLD.estado = 'EN_REVISION' AND NEW.estado IN ('EN_REVISION', 'APROBADO', 'OBSERVADO', 'RECHAZADO'))) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'EVA-EVALUACION: transición de estado no permitida';
  END IF;
END
"""),
    ("trg_eva_aprobacion_bu", """
CREATE TRIGGER trg_eva_aprobacion_bu BEFORE UPDATE ON eva_aprobacion FOR EACH ROW
BEGIN
  IF NEW.id_evaluacion <> OLD.id_evaluacion OR NEW.cod_credito <> OLD.cod_credito
     OR NEW.id_cliente <> OLD.id_cliente OR NEW.monto_aprobado <> OLD.monto_aprobado
     OR NEW.moneda <> OLD.moneda OR NEW.plazo_meses <> OLD.plazo_meses OR NEW.tasa_tea <> OLD.tasa_tea
     OR NEW.total_pagar <> OLD.total_pagar OR NEW.vigente_hasta <> OLD.vigente_hasta THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'EVA-APROBACION: las condiciones aprobadas no se modifican';
  END IF;
  IF NEW.estado <> OLD.estado THEN
    IF OLD.estado <> 'VIGENTE' THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'EVA-APROBACION: DESEMBOLSADA y REVOCADA son estados finales';
    END IF;
    IF NEW.version <> OLD.version + 1 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'EVA-APROBACION: cada cambio de estado aumenta la versión en uno';
    END IF;
  END IF;
END
"""),
]

# Permisos mínimos del usuario de la aplicación: ningún DELETE; lo que no se modifica, sin UPDATE.
PERMISOS: list[tuple[str, str]] = [
    ("SELECT, INSERT, UPDATE", "eva_correlativo"),
    ("SELECT, INSERT", "eva_expediente"),
    ("SELECT, INSERT, UPDATE", "eva_evaluacion"),
    ("SELECT, INSERT", "eva_situacion_financiera"),
    ("SELECT, INSERT, UPDATE", "eva_aprobacion"),
    ("SELECT, INSERT", "eva_cuota"),
    ("SELECT, INSERT, UPDATE", "eva_envio"),
    ("SELECT, INSERT", "eva_historial"),
]

_NOMBRE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def _validar(nombre: str) -> str:
    if not _NOMBRE.fullmatch(nombre):
        raise ValueError(f"Nombre no permitido: {nombre!r}")
    return nombre


def sentencias(base: str = BASE, usuario: str = USUARIO, host: str = "%") -> list[str]:
    """El SQL completo, para revisarlo o aplicarlo a mano. La contraseña se pone aparte."""
    base, usuario = _validar(base), _validar(usuario)
    salida = [f"CREATE DATABASE IF NOT EXISTS `{base}` CHARACTER SET utf8mb4", f"USE `{base}`"]
    salida += [ddl.strip() for ddl in TABLAS]
    for nombre, ddl in TRIGGERS:
        salida += [f"DROP TRIGGER IF EXISTS `{nombre}`", ddl.strip()]
    salida.append(f"CREATE USER IF NOT EXISTS '{usuario}'@'{host}' IDENTIFIED BY '<EVALUACION_DB_PASSWORD>'")
    salida.append(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{usuario}'@'{host}'")
    salida += [f"GRANT {privilegios} ON `{base}`.`{tabla}` TO '{usuario}'@'{host}'" for privilegios, tabla in PERMISOS]
    return salida


def instalar(cursor, base: str = BASE, usuario: str = USUARIO, clave: str | None = None, host: str = "%") -> None:
    """Crea o completa la base con un cursor administrativo (PyMySQL). No borra datos.

    Con `clave`, crea o actualiza el usuario de la aplicación y deja solo sus permisos."""
    base, usuario = _validar(base), _validar(usuario)
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{base}` CHARACTER SET utf8mb4")
    cursor.execute(f"USE `{base}`")
    for ddl in TABLAS:
        cursor.execute(ddl)
    for nombre, ddl in TRIGGERS:
        cursor.execute(f"DROP TRIGGER IF EXISTS `{nombre}`")
        cursor.execute(ddl)
    if clave is None:
        return
    cuenta = f"'{usuario}'@'{host}'"
    # Con parámetros, PyMySQL interpreta el % del host como formato: se duplica.
    con_parametros = cuenta.replace("%", "%%")
    cursor.execute(f"CREATE USER IF NOT EXISTS {con_parametros} IDENTIFIED BY %s", (clave,))
    # Si la clave cambió en .env, se alinea: el usuario solo existe para Evaluación.
    cursor.execute(f"ALTER USER {con_parametros} IDENTIFIED BY %s", (clave,))
    cursor.execute(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM {cuenta}")
    for privilegios, tabla in PERMISOS:
        cursor.execute(f"GRANT {privilegios} ON `{base}`.`{tabla}` TO {cuenta}")
