# Fuentes de las afirmaciones que prueban las pruebas (rama mysql) y cómo se
# cumple cada regla en PostgreSQL (rama main) y en MySQL.
# Es la única parte de la trazabilidad escrita a mano: matriz.py la cruza con
# las salidas de las ejecuciones (resultados/ de esta rama y de main) y genera
# la matriz, las comparaciones del informe y sus estadísticas. Una prueba sin
# fuente aquí detiene la generación. Los experimentos de la comparación de
# gestores, la reproducción de la línea base y el control quedan en main.
#
# Una fuente es (clave, localizador):
#   - clave de bibliography.bib del informe (documentos de los módulos y
#     documentación oficial) y su página o sección, p. ej.
#     ("BNA2026Tarjetas", "p.~34");
#   - las fallas de la línea base MySQL no van aquí: salen de
#     referencias_mysql.csv (commit:archivo:línea, verificadas al generar);
#   - las decisiones del informe (códigos BNA-*) se toman del resultado
#     esperado de cada prueba.

# --- Objetos programados (cuadro «Triggers, funciones, vistas e índices de
# consulta» del informe). Cada objeto lista las pruebas que lo ejercitan.
OBJETOS = [
    dict(grupo="CORE y Cuentas"),
    dict(
        objeto=r"\nm{fn\_asiento\_cuadra} (trigger de restricción diferido)",
        regla=r"Un asiento tiene al menos una línea en el debe y otra en el haber, y sus sumas coinciden; se verifica al confirmar la transacción.",
        etiqueta="CORE y Cuentas (RN-COR-002)",
        fuentes=[("BNA2026Core", ""), ("BNA2026Cuentas", "p.~16")],
        origen="Nuevo",
        pg="Trigger de restricción diferido",
        my="Procedimiento y privilegio",
        my_objetos="\\nm{core.registrar\\_asiento}; \\nm{core.v\\_asientos\\_descuadrados}",
        vale="solo bna\\_app (G04)",
        pruebas=["M20a", "M20b", "F24"],
    ),
    dict(
        objeto=r"\nm{fn\_solo\_insercion} (triggers por fila y por sentencia)",
        regla=r"Asientos, historiales, intentos, auditoría y aplicaciones de pago no admiten \texttt{UPDATE}, \texttt{DELETE} ni \texttt{TRUNCATE}; las autorizaciones no se borran.",
        etiqueta="CORE, Tarjetas (RN-SEG-002, RN-ATM-003) y Desembolso; \\texttt{TRUNCATE}, aplicaciones de pago e historial de la solicitud, decisión de este informe",
        fuentes=[
            ("BNA2026Core", ""),
            ("BNA2026Tarjetas", "p.~23"),
            ("BNA2026Desembolso", "p.~13"),
        ],
        origen="Modelo",
        pg="Trigger por fila y por sentencia",
        my="Privilegio y trigger por fila",
        my_objetos="\\nm{core.rechazar\\_cambio}, con un trigger por tabla y operación",
        vale="UPDATE y DELETE: todos; TRUNCATE: solo bna\\_app (G03)",
        pruebas=["F11a", "F11b", "F11c", "F11d", "F11e", "F11f", "F13", "F20"],
    ),
    dict(
        objeto=r"\nm{fn\_fecha\_negocio}",
        regla=r"El día de negocio se corta a las 00:00 de Arequipa.",
        etiqueta="Tarjetas, RN-TOP-001, y Desembolso",
        fuentes=[("BNA2026Tarjetas", "p.~15"), ("BNA2026Desembolso", "p.~4")],
        origen="Nuevo",
        pg="Función",
        my="Función",
        my_objetos="\\nm{core.fn\\_fecha\\_negocio}; \\nm{core.verificar\\_configuracion}",
        vale="todos",
        pruebas=["F12l", "F12m", "F12n"],
    ),
    dict(
        objeto=r"\nm{fn\_movimiento\_validar}, \nm{fn\_movimiento\_aplicar}, \nm{fn\_consumo\_sumar}",
        regla=r"La cuenta admite débitos o créditos según su estado; el asiento está en la moneda de la cuenta; un débito sin autorización no supera el saldo ni el tope del canal. Bloquea la cuenta, actualiza los saldos y el consumo del día, y vincula el movimiento a su autorización; el extorno devuelve el consumo al día en que se comprometió.",
        etiqueta="Cuentas, CORE y Tarjetas (RN-TOP-001, RN-BD-002, C07)",
        fuentes=[
            ("BNA2026Cuentas", "pp.~16, 17, 25 y~32"),
            ("BNA2026Core", ""),
            ("BNA2026Tarjetas", "pp.~15 y~28"),
        ],
        origen="Modelo",
        pg="Trigger",
        my="Trigger",
        my_objetos="\\nm{tg\\_movimiento\\_validar}, \\nm{tg\\_movimiento\\_aplicar\\_ai/au}, \\nm{core.consumo\\_sumar}",
        vale="todos",
        pruebas=[
            "M04",
            "M10a",
            "M10b",
            "M22",
            "M24a",
            "F21a",
            "F21b",
            "F22",
            "F12m",
            "C01",
            "C02",
        ],
    ),
    dict(
        objeto=r"\nm{fn\_movimiento\_inmutable}",
        regla=r"Un movimiento solo cambia de APROBADO a EXTORNADO.",
        etiqueta="CORE",
        fuentes=[("BNA2026Core", "")],
        origen="Nuevo",
        pg="Trigger",
        my="Privilegio y trigger",
        my_objetos="\\nm{tg\\_movimiento\\_inmutable\\_bu/bd}",
        vale="todos",
        pruebas=["F23"],
    ),
    dict(grupo="Tarjetas"),
    dict(
        objeto=r"\nm{fn\_tarjeta\_emitir}",
        regla=r"Solo se emite tarjeta a un cliente ACTIVO (RF-TAR-005).",
        etiqueta=r"Tarjetas, \nm{trg\_tarjeta\_bi}",
        fuentes=[("BNA2026Tarjetas", "pp.~23 y~31")],
        origen="Portado",
        pg="Trigger",
        my="Trigger",
        my_objetos="\\nm{tg\\_tarjeta\\_emitir}",
        vale="todos",
        pruebas=["F01"],
    ),
    dict(
        objeto=r"\nm{fn\_tarjeta\_emitida}",
        regla=r"La emisión queda en el historial y en la bandeja hacia Seguridad (RN-SEG-002).",
        etiqueta=r"Tarjetas, \nm{trg\_tarjeta\_ai}",
        fuentes=[("BNA2026Tarjetas", "pp.~22 y~23")],
        origen="Portado",
        pg="Trigger",
        my="Trigger",
        my_objetos="\\nm{tg\\_tarjeta\\_emitida}",
        vale="todos",
        pruebas=["F02"],
    ),
    dict(
        objeto=r"\nm{fn\_historial\_validar}, \nm{fn\_historial\_aplicar}, \nm{fn\_tarjeta\_estado\_via\_historial}",
        regla=r"La cancelada no cambia y la vencida solo se cancela (RN-TAR-003); solo un operador o Seguridad desbloquean, y al desbloquear los intentos vuelven a cero (RN-TAR-004). El estado de la tarjeta sigue a su historial y cada cambio se avisa a Seguridad.",
        etiqueta=r"Tarjetas, \nm{trg\_tarjeta\_bu} y \nm{trg\_tarjeta\_au}; el cambio solo por el historial, decisión de este informe",
        fuentes=[("BNA2026Tarjetas", "pp.~23 y~29")],
        origen="Portado",
        pg="Trigger",
        my="Trigger; el estado, privilegio y trigger",
        my_objetos="\\nm{tg\\_historial\\_validar}, \\nm{tg\\_historial\\_aplicar}, \\nm{tg\\_tarjeta\\_estado\\_via\\_historial}",
        vale="todos",
        pruebas=["F03", "F04", "F05", "F06", "F07"],
    ),
    dict(
        objeto=r"\nm{fn\_intento\_contar}",
        regla=r"El tercer intento fallido de la credencial o de la matriz bloquea la tarjeta; un intento exitoso reinicia el contador (RN-TAR-004).",
        etiqueta=r"Tarjetas, \nm{trg\_intento\_ai}",
        fuentes=[("BNA2026Tarjetas", "pp.~19 y~23")],
        origen="Portado",
        pg="Trigger",
        my="Trigger",
        my_objetos="\\nm{tg\\_intento\\_contar}",
        vale="todos",
        pruebas=["F08", "F09", "F10"],
    ),
    dict(
        objeto=r"\nm{fn\_autorizacion\_validar}, \nm{fn\_validar\_reglas\_autorizacion}, \nm{fn\_autorizacion\_aplicar}",
        regla=r"Para autorizar, la tarjeta está operativa y vigente, la terminal y el canal están activos, el cajero no opera cuentas mancomunadas conjuntas (RN-ATM-005), el canal opera en la moneda (RN-BD-002) y el débito no supera el tope (RN-TOP-001) ni el saldo, con la cuenta bloqueada. Al autorizar, compromete el tope y retiene el saldo; al extornar sin movimiento, los libera. Controla la secuencia de estados (RN-ATM-007).",
        etiqueta=r"Tarjetas, \nm{trg\_autorizacion\_bi/bu} y \nm{sp\_validar\_reglas\_autorizacion}",
        fuentes=[("BNA2026Tarjetas", "pp.~15, 21, 23, 26 y~27")],
        origen="Portado",
        pg="Trigger",
        my="Trigger; el vínculo con el movimiento, privilegio y CHECK",
        my_objetos="\\nm{tg\\_autorizacion\\_validar\\_bi/bu}, \\nm{validar\\_reglas\\_autorizacion}, \\nm{tg\\_autorizacion\\_aplicar\\_ai/au}",
        vale="todos",
        pruebas=[
            "M23",
            "M24b",
            "M24c",
            "F12a",
            "F12b",
            "F12c",
            "F12d",
            "F12e",
            "F12f",
            "F12g",
            "F12h",
            "F12i",
            "F12j",
            "F12k",
            "F12l",
            "F12n",
            "C03",
        ],
    ),
    dict(
        objeto=r"\nm{fn\_cliente\_estado\_tarjetas}",
        regla=r"Si Clientes bloquea o suspende al cliente, se bloquean sus tarjetas; si lo da de baja, se cancelan (INT-T07).",
        etiqueta=r"Tarjetas, \nm{trg\_cliente\_ref\_au}, y Clientes",
        fuentes=[("BNA2026Tarjetas", "pp.~23 y~31"), ("BNA2026Clientes", "p.~8")],
        origen="Portado",
        pg="Trigger",
        my="Trigger (con cursor)",
        my_objetos="\\nm{tg\\_cliente\\_estado\\_tarjetas}",
        vale="todos",
        pruebas=["F14a", "F14b"],
    ),
    dict(
        objeto=r"\nm{bloquear\_tarjeta()}",
        regla=r"Bloquea la tarjeta registrando su motivo y su origen en el historial.",
        etiqueta="Tarjetas, RN-SEG-002",
        fuentes=[("BNA2026Tarjetas", "pp.~18 y~22")],
        origen="Portado",
        pg="Función",
        my="Procedimiento",
        my_objetos="\\nm{tarjetas.bloquear\\_tarjeta}",
        vale="todos",
        pruebas=["M26"],
    ),
    dict(
        objeto=r"\nm{marcar\_tarjetas\_vencidas()}",
        regla=r"Marca como VENCIDA cada tarjeta cuya fecha ya pasó (RN-TAR-003).",
        etiqueta=r"Tarjetas, \nm{ev\_marcar\_tarjetas\_vencidas}",
        fuentes=[("BNA2026Tarjetas", "pp.~23 y~32")],
        origen="Portado",
        pg="Función, programada fuera de la base",
        my="Procedimiento y evento diario",
        my_objetos="\\nm{tarjetas.marcar\\_tarjetas\\_vencidas}; \\nm{ev\\_marcar\\_tarjetas\\_vencidas}",
        vale="todos",
        pruebas=["F15"],
    ),
    dict(
        objeto=r"\nm{v\_tarjeta\_resumen}, \nm{v\_consumo\_diario}, \nm{v\_tope\_restante\_hoy}, \nm{v\_credenciales\_en\_riesgo}",
        regla=r"Número enmascarado y vencimiento MM/AA (PCI-DSS); consumo por tarjeta, canal, moneda y día; tope disponible por tarjeta y canal (RN-TOP-001); intentos acumulados y restantes (RN-TAR-004).",
        etiqueta="Tarjetas, objetos programados y consultas C05 y C08",
        fuentes=[("BNA2026Tarjetas", "pp.~23, 24, 27 y~28")],
        origen="Portado",
        pg="Vista",
        my="Vista",
        my_objetos="Las mismas cuatro",
        vale="todos",
        pruebas=["M25", "F25", "F26", "F27"],
    ),
    dict(grupo="Solicitud, Evaluación, Desembolso y Cobranza"),
    dict(
        objeto=r"\nm{fn\_orden\_validar}",
        regla=r"La cuenta destino pertenece al cliente de la solicitud y tiene su moneda; el importe no supera el límite aprobado (decisión de este informe); hay una sola orden CONFIRMADA por solicitud, en todas sus rondas.",
        etiqueta="Desembolso y Evaluación",
        fuentes=[("BNA2026Desembolso", "pp.~11 y~12"), ("BNA2026Evaluacion", "p.~8")],
        origen="Modelo",
        pg="Trigger",
        my="Trigger",
        my_objetos="\\nm{tg\\_orden\\_validar\\_bi/bu}, \\nm{validar\\_orden}",
        vale="todos",
        pruebas=["M09a", "M09b", "M09c", "M14b"],
    ),
    dict(
        objeto=r"\nm{v\_ordenes\_inciertas}, \nm{v\_entregas\_pendientes}, \nm{v\_conciliacion\_diaria}",
        regla=r"Órdenes con resultado incierto en el CORE; entregas a Cobranza que superan dos reintentos; importes ordenados frente a abonados, por fecha y moneda.",
        etiqueta="Desembolso, vistas de apoyo operativo; reintentos, documento de tecnologías",
        fuentes=[("BNA2026Desembolso", "p.~12"), ("BNA2026Stack", "línea~92")],
        origen="Portado",
        pg="Vista",
        my="Vista",
        my_objetos="Las mismas tres",
        vale="todos",
        pruebas=["F28", "F29", "F30"],
    ),
    dict(
        objeto=r"\nm{fn\_credito\_validar}",
        regla=r"El crédito nace de una orden CONFIRMADA (decisión I15) y su calendario pertenece a la solicitud de la orden y es OFICIAL (decisión de este informe).",
        etiqueta="Cobranza (RF-COB-015) y Solicitud",
        fuentes=[("BNA2026Cobranza", "p.~2"), ("BNA2026Solicitud", "p.~4")],
        origen="Modelo",
        pg="Trigger",
        my="Trigger",
        my_objetos="\\nm{tg\\_credito\\_validar\\_bi/bu}, \\nm{validar\\_credito}",
        vale="todos",
        pruebas=["M14a", "F16a", "F16b", "F16c"],
    ),
    dict(
        objeto=r"\nm{fn\_aplicacion\_validar}, \nm{fn\_aplicacion\_aplicar}",
        regla=r"Solo se aplica un pago CONFIRMADO, a cuotas de su crédito, sin superar el saldo de la cuota ni el monto del pago. Actualiza el saldo y el estado de la cuota y cancela el crédito cuando todas sus cuotas quedan pagadas.",
        etiqueta="Cobranza",
        fuentes=[("BNA2026Cobranza", "pp.~3 y~8")],
        origen="Modelo",
        pg="Trigger",
        my="Trigger; la inmutabilidad, privilegio y trigger",
        my_objetos="\\nm{tg\\_aplicacion\\_validar}, \\nm{tg\\_aplicacion\\_aplicar}",
        vale="todos",
        pruebas=["M05", "M13a", "M13b", "F17a", "F17b", "F19"],
    ),
    dict(
        objeto=r"\nm{aplicar\_pago()}",
        regla=r"Reparte el saldo libre de un pago de la cuota más antigua a la siguiente.",
        etiqueta="Cobranza",
        fuentes=[("BNA2026Cobranza", "p.~3")],
        origen="Portado",
        pg="Función",
        my="Procedimiento",
        my_objetos="\\nm{creditos.aplicar\\_pago}",
        vale="todos",
        pruebas=["F18"],
    ),
    dict(grupo="Índices"),
    dict(
        objeto=r"\stat{consultas} índices de consulta",
        regla=r"Movimientos, autorizaciones, intentos e historial por fecha; órdenes por estado y fecha; eventos por enviar; auditoría por \nm{correlation\_id}.",
        etiqueta="Tarjetas y Desembolso",
        fuentes=[("BNA2026Tarjetas", "p.~30"), ("BNA2026Desembolso", "p.~12")],
        origen="Portado",
        pg="Índice",
        my="Índice; los dos parciales, compuestos",
        my_objetos="Los mismos ocho",
        vale="todos",
        pruebas=["F31"],
    ),
]

# --- Pruebas cuya fuente no es un objeto programado (restricciones
# declarativas del modelo, carga y concurrencia). Las pruebas M toman además
# la falla de la línea base MySQL de referencias_mysql.csv.
PRUEBAS = {
    "L01": dict(fuentes=[]),
    "M08": dict(fuentes=[("BNA2026Core", "")]),
    "M12": dict(fuentes=[("BNA2026Cobranza", "p.~2")]),
    "M15a": dict(fuentes=[("BNA2026Tarjetas", "p.~17")]),
    "M16": dict(fuentes=[("BNA2026Tarjetas", "p.~18")]),
    "M17": dict(fuentes=[("BNA2026Tarjetas", "p.~20")]),
    "M18": dict(fuentes=[("BNA2026Solicitud", "p.~3")]),
    "R2": dict(fuentes=[("BNA2026Tarjetas", "p.~20")]),
    "R4": dict(fuentes=[("BNA2026Tarjetas", "p.~18")]),
    "R5": dict(fuentes=[("BNA2026Tarjetas", "p.~21")]),
    "R6": dict(fuentes=[("BNA2026Clientes", "p.~9")]),
    "R7": dict(fuentes=[("BNA2026Desembolso", "p.~12")]),
    "R8": dict(fuentes=[("BNA2026Stack", "línea~32")]),
    "C01": dict(fuentes=[("BNA2026Cuentas", "p.~31"), ("BNA2026Core", "")]),
}

# --- Reglas que ninguna fuente enuncia, o que la fuente resuelve de otro
# modo: son decisiones de este informe y la matriz las presenta así.
DECISIONES = {
    "L01": "el script DDL se genera del modelo integrado",
    "F07": "el estado de la tarjeta cambia solo por su historial (en Tarjetas, p. 23, el historial se escribe después del cambio)",
    "F11c": "el historial tampoco se vacía con TRUNCATE",
    "F11f": "el historial de la solicitud es de solo inserción",
    "F20": "una aplicación de pago no se modifica",
    "F12e": "solo autoriza una terminal activa",
    "F12l": "el compromiso del tope pertenece al día de la autorización",
    "F12m": "el compromiso del tope pertenece al día de la autorización",
    "F12n": "el compromiso del tope pertenece al día de la autorización",
    "F21b": "una cuenta BLOQUEADA_PREVENTIVA admite créditos (Cuentas, p. 25, solo inhabilita débitos)",
    "F16a": "decisión I15: el crédito nace de la orden confirmada",
    "F16b": "decisión I15: el crédito nace de la orden confirmada",
    "F16c": "el crédito usa el calendario OFICIAL (supuesto S13)",
    "M09c": "el importe de la orden no supera el límite aprobado (supuesto S12)",
    "M11": "el saldo disponible no supera al contable",
    "M13a": "una aplicación no supera el monto del pago",
    "M13b": "una aplicación no supera el saldo de la cuota",
    "F18": "el pago se aplica de la cuota más antigua a la siguiente",
    "M12": "el total de la cuota se deriva de sus partes (normalización)",
    "M15b": "la tarjeta vence después de emitirse",
    "M19": "la entidad auditada es un catálogo (en Cobranza, p. 4, la referencia es libre)",
    "R1": "la entidad auditada es un catálogo (en Cobranza, p. 4, la referencia es libre)",
    "R3": "arco exclusivo entre terminal y canal (Tarjetas, p. 20, admite ambos)",
    "R8": "los catálogos en uso no se borran",
}

# --- Reglas declarativas (rama mysql): cómo se cumplen en cada gestor. Las
# programadas salen de OBJETOS.
DECLARATIVAS = [
    dict(
        regla=r"Claves primarias, únicas y foráneas (ON DELETE RESTRICT; ninguna en cascada)",
        pg="Declarativo",
        my="Declarativo",
        vale="todos, salvo una sesión con \\nm{foreign\\_key\\_checks} = 0 (G02)",
        pruebas=["M14a", "M18", "M19", "R1", "R5", "R6", "R8", "G02"],
    ),
    dict(
        regla=r"Dominios cerrados y reglas de fila (CHECK)",
        pg="Declarativo",
        my="Declarativo, con collation que distingue mayúsculas",
        vale="todos",
        pruebas=["M11", "M15a", "M15b", "M16", "M17", "R2", "R3", "R4"],
    ),
    dict(
        regla=r"Unicidad parcial: una matriz activa, una orden confirmada, una cuenta principal, una plantilla vigente",
        pg="Índice único parcial",
        my="Índice único funcional (CASE \\ldots{} END)",
        vale="todos",
        pruebas=["R7"],
    ),
    dict(
        regla=r"Identificadores UUID válidos",
        pg="Tipo UUID",
        my="BINARY(16) con CHECK de versión y variante",
        vale="todos",
        pruebas=["M08"],
    ),
    dict(
        regla=r"Booleanos solo verdadero o falso; direcciones IP válidas",
        pg="Tipos BOOLEAN e INET",
        my="TINYINT(1) y VARCHAR(45) con CHECK",
        vale="todos",
        pruebas=["L01"],
    ),
    dict(
        regla=r"Marcas de tiempo en UTC",
        pg="Tipo TIMESTAMPTZ",
        my="DATETIME(6) en UTC por convención; valores por omisión con UTC\\_TIMESTAMP",
        vale="los valores por omisión; no los que da una sesión con otra zona (G05)",
        pruebas=["F12l", "G05"],
    ),
    dict(
        regla=r"El identificador de una bitácora lo asigna la base",
        pg="IDENTITY GENERATED ALWAYS",
        my="Privilegio y trigger",
        vale="todos",
        pruebas=["F32"],
    ),
    dict(
        regla=r"Un valor inválido es un error, no un valor ajustado",
        pg="Siempre",
        my="Modo estricto del servidor; los triggers y procedimientos, con el modo de su creación",
        vale="sesiones que no cambian \\nm{sql\\_mode} (G01)",
        pruebas=["L02", "G01"],
    ),
]

# --- Pruebas solo de MySQL y sus fuentes.
PRUEBAS.update(
    {
        "L02": dict(fuentes=[("MySQL2024Manual", "sec.~7.1.11")]),
        "M20c": dict(fuentes=[("BNA2026Core", "")]),
        "G01": dict(fuentes=[("MySQL2024Manual", "sec.~7.1.11")]),
        "G02": dict(fuentes=[("MySQL2024Manual", "sec.~15.1.20.5")]),
        "G03": dict(fuentes=[("MySQL2024Manual", "sec.~15.1.37")]),
        "G04": dict(fuentes=[("BNA2026Core", "")]),
        "G05": dict(fuentes=[("MySQL2024Manual", "sec.~13.2.2")]),
    }
)
DECISIONES.update(
    {
        "L02": "la configuración del servidor se comprueba al cargar y al probar",
        "M20c": "el asiento se registra completo o no se registra",
        "F32": "el identificador de una bitácora lo asigna la base",
    }
)

# --- Brechas conocidas de MySQL: lo que queda sin proteger y cómo se mitiga.
BRECHAS = [
    dict(
        id="G01",
        que=r"Una sesión puede quitar el modo estricto (\nm{SET SESSION sql\_mode}) sin privilegios; sus INSERT y UPDATE directos guardan valores truncados o ajustados, con advertencias, antes de que los vean los CHECK y los triggers.",
        mitigacion=r"Modo estricto en el servidor; CHECK en los dominios y montos; triggers y procedimientos con el modo de su creación; la aplicación no debe cambiar el modo.",
    ),
    dict(
        id="G02",
        que=r"Una sesión puede apagar \nm{foreign\_key\_checks} sin privilegios y guardar referencias a filas inexistentes.",
        mitigacion=r"Ninguna en la base; revisar la configuración de las conexiones de la aplicación.",
    ),
    dict(
        id="G03",
        que=r"bna\_admin tiene DROP y puede vaciar una bitácora con TRUNCATE, que no dispara triggers.",
        mitigacion=r"bna\_app no tiene DROP; reservar bna\_admin al mantenimiento y auditarlo.",
    ),
    dict(
        id="G04",
        que=r"Una cuenta con INSERT directo sobre los asientos (bna\_admin) puede saltarse \nm{core.registrar\_asiento} y registrar un asiento descuadrado.",
        mitigacion=r"bna\_app solo inserta por el procedimiento; \nm{core.v\_asientos\_descuadrados} los muestra.",
    ),
    dict(
        id="G05",
        que=r"DATETIME no guarda zona: la base no puede comprobar que una marca de tiempo que da la aplicación esté en UTC.",
        mitigacion=r"Valores por omisión con UTC\_TIMESTAMP; zona del servidor +00:00; la aplicación no debe cambiar la zona de la sesión.",
    ),
]

# Commit de la rama main cuyas salidas de PostgreSQL se comparan y cuyo
# modelo debe ser idéntico al de esta rama.
import os, subprocess

MAIN_COMMIT = subprocess.run(
    [
        "git",
        "-C",
        os.path.dirname(os.path.abspath(__file__)),
        "rev-parse",
        "--short",
        "informe-pg^{commit}",
    ],
    capture_output=True,
    text=True,
    check=True,
).stdout.strip()
