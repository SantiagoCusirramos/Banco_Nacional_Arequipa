"""Usuarios del sistema (script 01).

CREAR_USUARIO / ASIGNAR_ROLES operan sobre esta tabla. El catálogo de
acciones (GESTIONAR_PERMISOS) se administra en CORE/data/rbac.json
hasta que el esquema unificado incorpore tablas de permisos.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


class UsuarioSistema(Base):
    __tablename__ = "usuario_sistema"

    id_usuario: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(15))  # ENUM rol_usuario
    hash_password: Mapped[str] = mapped_column(String(64))
    algoritmo_hash: Mapped[str] = mapped_column(String(20), default="SHA256")
    version_hash: Mapped[str] = mapped_column(String(10), default="v1")
    id_empleado: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("empleado.id_empleado"), nullable=True
    )
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(3))
