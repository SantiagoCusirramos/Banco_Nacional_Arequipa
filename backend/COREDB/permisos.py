"""Permisos por rol de COREDB: un mapa versionado y de solo lectura.

Los cinco roles de personas se copiaron de CORE/data/rbac.json en a9bd70f (el CORE
legado, eliminado en #125). A diferencia de aquel, la API nunca escribe este mapa:
un cambio de permisos es un cambio de código, revisado en un PR. Los usuarios de
servicio se identifican por `SERVICIO:<módulo>`.
"""

from COREDB.auth_tipos import Actor

ACCIONES_CORE = frozenset({
    "VER_CLIENTE", "CREAR_CLIENTE", "MODIFICAR_CLIENTE",
    "VER_CUENTA", "CREAR_CUENTA", "MODIFICAR_CUENTA",
    "REGISTRAR_MOVIMIENTO",
    "VER_TARJETA", "CREAR_TARJETA", "BLOQUEAR_TARJETA",
    "CREAR_SOLICITUD_CREDITO", "EVALUAR_CREDITO", "APROBAR_CREDITO", "VER_CREDITO",
    "REGISTRAR_PAGO", "CONSULTAR_DEUDA",
    "CREAR_USUARIO", "ASIGNAR_ROLES", "GESTIONAR_PERMISOS",
    "VER_AUDITORIA", "GENERAR_REPORTES",
})
# Propia de COREDB: registrar el resultado de una validación de identidad de Clientes.
VALIDAR_IDENTIDAD = "VALIDAR_IDENTIDAD"
# Propias de COREDB para créditos (CONTRATO_CREDITOS.md): preparar, validar y confirmar un
# desembolso, y registrar la mora y los vencimientos.
DESEMBOLSAR_CREDITO = "DESEMBOLSAR_CREDITO"
REGISTRAR_MORA = "REGISTRAR_MORA"
# Propia de COREDB: registrar empleados y ligarlos a su usuario (solo ADMINISTRADOR).
REGISTRAR_EMPLEADO = "REGISTRAR_EMPLEADO"
# Propias de COREDB para la Billetera Digital (bd-v1.9): afiliar a un cliente (le fija su PIN),
# afiliar un comercio y operar por un cliente. Operar exige además el token del cliente
# (X-Cliente-Token), así que quien la tiene no actúa por un cliente sin su PIN.
AFILIAR_BILLETERA = "AFILIAR_BILLETERA"
REGISTRAR_COMERCIO = "REGISTRAR_COMERCIO"
OPERAR_BILLETERA = "OPERAR_BILLETERA"
ACCIONES_BILLETERA = frozenset({AFILIAR_BILLETERA, REGISTRAR_COMERCIO, OPERAR_BILLETERA})
# Propias de COREDB para el módulo Seguridad (bd-v1.13). OPERAR_SEGURIDAD la tiene solo su
# usuario de servicio: las rutas /coredb/seguridad/* y el desbloqueo de tarjetas exigen además
# el token de la persona por la que actúa (X-Persona-Token), con su propio permiso, y la
# registran a ella en la bitácora. GESTIONAR_INCIDENTES abre y avanza incidentes.
OPERAR_SEGURIDAD = "OPERAR_SEGURIDAD"
GESTIONAR_INCIDENTES = "GESTIONAR_INCIDENTES"
# Propia de COREDB (bd-v1.14): un módulo sin base propia reporta sus eventos de auditoría a la
# bitácora (POST /coredb/auditoria/eventos). El módulo de la bitácora es el del token (el
# módulo de un usuario de servicio es un nombre de core.modulo).
REGISTRAR_EVENTO_MODULO = "REGISTRAR_EVENTO_MODULO"
ACCIONES = (ACCIONES_CORE | {VALIDAR_IDENTIDAD, DESEMBOLSAR_CREDITO, REGISTRAR_MORA, REGISTRAR_EMPLEADO}
            | ACCIONES_BILLETERA | {OPERAR_SEGURIDAD, GESTIONAR_INCIDENTES, REGISTRAR_EVENTO_MODULO})


PERMISOS: dict[str, frozenset[str]] = {
    "ADMINISTRADOR": (ACCIONES_CORE | {DESEMBOLSAR_CREDITO, REGISTRAR_MORA, REGISTRAR_EMPLEADO} | ACCIONES_BILLETERA
                      | {GESTIONAR_INCIDENTES}),
    "ANALISTA": frozenset({
        "APROBAR_CREDITO", "CONSULTAR_DEUDA", "EVALUAR_CREDITO", "VER_CLIENTE", "VER_CREDITO",
        "VER_CUENTA",
    }),
    "ASESOR": frozenset({
        "CONSULTAR_DEUDA", "CREAR_CLIENTE", "CREAR_SOLICITUD_CREDITO", "MODIFICAR_CLIENTE",
        "VER_CLIENTE", "VER_CREDITO", "VER_CUENTA", VALIDAR_IDENTIDAD, AFILIAR_BILLETERA,
    }),
    "AUDITOR": frozenset({
        "CONSULTAR_DEUDA", "GENERAR_REPORTES", "VER_AUDITORIA", "VER_CLIENTE", "VER_CREDITO",
        "VER_CUENTA", "VER_TARJETA",
    }),
    "OPERADOR": frozenset({
        "CONSULTAR_DEUDA", "CREAR_CUENTA", "CREAR_TARJETA", "BLOQUEAR_TARJETA",
        "MODIFICAR_CUENTA", "REGISTRAR_MOVIMIENTO", "REGISTRAR_PAGO", "VER_CLIENTE",
        "VER_CREDITO", "VER_CUENTA", "VER_TARJETA", DESEMBOLSAR_CREDITO,
        # La verificación del documento en ventanilla es la evidencia IDENTIDAD del desembolso.
        VALIDAR_IDENTIDAD, AFILIAR_BILLETERA, REGISTRAR_COMERCIO, GESTIONAR_INCIDENTES,
    }),
    "SERVICIO:CLIENTES": frozenset({
        "VER_CLIENTE", "CREAR_CLIENTE", "MODIFICAR_CLIENTE", VALIDAR_IDENTIDAD,
    }),
    # Los módulos de créditos: lo que hace una persona (evaluar, decidir, desembolsar,
    # cobrar) va con el token de esa persona, que el módulo reenvía.
    "SERVICIO:EVALUACION": frozenset({"CREAR_SOLICITUD_CREDITO", "VER_CREDITO"}),
    "SERVICIO:DESEMBOLSO": frozenset({"VER_CREDITO", "VER_CUENTA"}),
    "SERVICIO:COBRANZA": frozenset({"VER_CREDITO", "CONSULTAR_DEUDA", REGISTRAR_MORA}),
    # La billetera (Chaski) solo opera por el cliente que le dio su token.
    "SERVICIO:BILLETERA": frozenset({OPERAR_BILLETERA}),
    # Seguridad sella la bitácora con su clave (por eso la lee) y actúa por personas.
    "SERVICIO:SEGURIDAD": frozenset({OPERAR_SEGURIDAD, "VER_AUDITORIA"}),
    # SOL (bd-v1.14): el borrador lo guarda el asesor con su token, que SOL reenvía; con el suyo,
    # SOL lee las solicitudes (para el resultado de Evaluación) y reporta sus eventos.
    "SERVICIO:SOLICITUD DE CREDITO": frozenset({"VER_CREDITO", REGISTRAR_EVENTO_MODULO}),
}


def puede_registrar_habilitado(actor: Actor) -> bool:
    """Punto R-01: solo el módulo Clientes, que verificó la identidad, registra un cliente
    HABILITADO. Los demás registran OBSERVADO. Si el equipo decide otra cosa, cambia aquí."""
    return actor.clave_permisos == "SERVICIO:CLIENTES"


def puede_dar_de_baja(actor: Actor) -> bool:
    """La baja es final y cancela las tarjetas del cliente: la fija una persona."""
    return not actor.es_servicio


def acciones_de(actor: Actor) -> frozenset[str]:
    return PERMISOS.get(actor.clave_permisos, frozenset())


def puede(actor: Actor, accion: str) -> bool:
    return accion in acciones_de(actor)
