"""Permisos por rol de COREDB: un mapa versionado y de solo lectura.

Los cinco roles de personas se copiaron de CORE/data/rbac.json en a9bd70f. A
diferencia de CORE, la API nunca escribe este mapa: un cambio de permisos es un
cambio de código, revisado en un PR. Los usuarios de servicio se identifican por
`SERVICIO:<módulo>`.
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
ACCIONES = ACCIONES_CORE | {VALIDAR_IDENTIDAD}

PERMISOS: dict[str, frozenset[str]] = {
    "ADMINISTRADOR": ACCIONES_CORE,
    "ANALISTA": frozenset({
        "APROBAR_CREDITO", "CONSULTAR_DEUDA", "EVALUAR_CREDITO", "VER_CLIENTE", "VER_CREDITO",
        "VER_CUENTA",
    }),
    "ASESOR": frozenset({
        "CONSULTAR_DEUDA", "CREAR_CLIENTE", "CREAR_SOLICITUD_CREDITO", "MODIFICAR_CLIENTE",
        "VER_CLIENTE", "VER_CREDITO", "VER_CUENTA", VALIDAR_IDENTIDAD,
    }),
    "AUDITOR": frozenset({
        "CONSULTAR_DEUDA", "GENERAR_REPORTES", "VER_AUDITORIA", "VER_CLIENTE", "VER_CREDITO",
        "VER_CUENTA", "VER_TARJETA",
    }),
    "OPERADOR": frozenset({
        "CONSULTAR_DEUDA", "CREAR_CUENTA", "CREAR_TARJETA", "BLOQUEAR_TARJETA",
        "MODIFICAR_CUENTA", "REGISTRAR_MOVIMIENTO", "REGISTRAR_PAGO", "VER_CLIENTE",
        "VER_CREDITO", "VER_CUENTA", "VER_TARJETA",
    }),
    "SERVICIO:CLIENTES": frozenset({
        "VER_CLIENTE", "CREAR_CLIENTE", "MODIFICAR_CLIENTE", VALIDAR_IDENTIDAD,
    }),
}


def acciones_de(actor: Actor) -> frozenset[str]:
    return PERMISOS.get(actor.clave_permisos, frozenset())


def puede(actor: Actor, accion: str) -> bool:
    return accion in acciones_de(actor)
