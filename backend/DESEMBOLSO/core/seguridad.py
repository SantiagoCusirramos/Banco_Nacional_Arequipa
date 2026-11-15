"""Usuario autenticado y permisos del módulo.

El token es el de COREDB. Desembolso no conoce la clave que lo firma: lo valida COREDB en
`GET /coredb/auth/me` (integraciones/coredb.py). Los roles de COREDB se traducen a los perfiles
del módulo: OPERADOR es el operador de agencia; ADMINISTRADOR hace de supervisor, porque COREDB
no tiene un rol de supervisor (decisión pendiente del Comité de Créditos); AUDITOR solo consulta.
"""
from __future__ import annotations

from dataclasses import dataclass

LEER = "DESEMBOLSO_LEER"
EJECUTAR = "DESEMBOLSO_EJECUTAR"
OPERADOR = "OPERADOR"
SUPERVISOR = "SUPERVISOR"
AUDITOR = "AUDITOR"

# Rol de COREDB -> (perfil en Desembolso, permisos). Otro rol entra sin permisos (403).
PERFILES: dict[str, tuple[str, frozenset[str]]] = {
    "OPERADOR": (OPERADOR, frozenset({LEER, EJECUTAR})),
    "ADMINISTRADOR": (SUPERVISOR, frozenset({LEER, EJECUTAR})),
    "AUDITOR": (AUDITOR, frozenset({LEER})),
}


@dataclass(frozen=True)
class Usuario:
    id: str
    nombre: str
    rol: str
    permisos: frozenset[str]
    agencia_id: str | None
    agencia_nombre: str | None
    jti: str

    def tiene(self, permiso: str) -> bool:
        return permiso in self.permisos


def perfil_de(rol_coredb: str) -> tuple[str, frozenset[str]]:
    return PERFILES.get(rol_coredb, (rol_coredb, frozenset()))
