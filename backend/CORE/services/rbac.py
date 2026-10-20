"""GESTIONAR_PERMISOS — catálogo de acciones y asignaciones rol→acciones.

El esquema unificado `bna` no tiene tablas de permisos (el módulo
BNA_CONTROL_ACCESO solo cubre permisos de comités). Mientras se
incorporan al modelo, CORE administra el catálogo en
`CORE/data/rbac.json`, versionado en el repositorio.
"""

import json
from pathlib import Path

from CORE.exceptions import NotFoundError, ValidationError

RBAC_FILE = Path(__file__).resolve().parent.parent / "data" / "rbac.json"

ACCIONES_CORE = (
    "VER_CLIENTE",
    "CREAR_CLIENTE",
    "MODIFICAR_CLIENTE",
    "VER_CUENTA",
    "CREAR_CUENTA",
    "MODIFICAR_CUENTA",
    "REGISTRAR_MOVIMIENTO",
    "VER_TARJETA",
    "CREAR_TARJETA",
    "BLOQUEAR_TARJETA",
    "CREAR_SOLICITUD_CREDITO",
    "EVALUAR_CREDITO",
    "APROBAR_CREDITO",
    "VER_CREDITO",
    "REGISTRAR_PAGO",
    "CONSULTAR_DEUDA",
    "CREAR_USUARIO",
    "ASIGNAR_ROLES",
    "GESTIONAR_PERMISOS",
    "VER_AUDITORIA",
    "GENERAR_REPORTES",
)


def _leer() -> dict:
    if not RBAC_FILE.exists():
        return {"acciones": list(ACCIONES_CORE), "permisos": {}}
    with RBAC_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _escribir(data: dict) -> None:
    RBAC_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RBAC_FILE.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)


def obtener_catalogo() -> dict:
    data = _leer()
    return {
        "acciones": data.get("acciones", list(ACCIONES_CORE)),
        "permisos": data.get("permisos", {}),
    }


def acciones_de_rol(rol: str) -> list[str]:
    data = _leer()
    return list(data.get("permisos", {}).get(rol, []))


def rol_puede(rol: str, accion: str) -> bool:
    return accion in acciones_de_rol(rol)


def asignar_accion(
    rol: str, accion: str, *, actor: str = "sistema"
) -> dict:
    if accion not in ACCIONES_CORE:
        raise ValidationError(
            "ACCION_NO_RECONOCIDA",
            f"La acción {accion} no existe en el catálogo de CORE.",
        )
    data = _leer()
    permisos = data.setdefault("permisos", {})
    lista = permisos.setdefault(rol, [])
    if accion in lista:
        raise ValidationError(
            "PERMISO_DUPLICADO",
            f"El rol {rol} ya tiene la acción {accion}.",
        )
    lista.append(accion)
    lista.sort()
    data.setdefault("auditoria", []).append(
        {"accion": "ASIGNAR_ACCION", "rol": rol, "asignada": accion, "actor": actor}
    )
    _escribir(data)
    return {"rol": rol, "accion": accion, "asignada": True}


def revocar_accion(
    rol: str, accion: str, *, actor: str = "sistema"
) -> dict:
    data = _leer()
    permisos = data.get("permisos", {})
    lista = permisos.get(rol)
    if lista is None or accion not in lista:
        raise NotFoundError(
            "PERMISO_NO_ENCONTRADO",
            f"El rol {rol} no tiene la acción {accion}.",
        )
    lista.remove(accion)
    data.setdefault("auditoria", []).append(
        {"accion": "REVOCAR_ACCION", "rol": rol, "revocada": accion, "actor": actor}
    )
    _escribir(data)
    return {"rol": rol, "accion": accion, "asignada": False}
