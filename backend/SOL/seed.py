"""Datos sintéticos repetibles. No importa ni modifica el maestro del banco."""

from datetime import date, timedelta
from .clock import business_today
from uuid import uuid4
from sqlalchemy import select
from .models import ClientReference, User
from .security import hash_password

DEMO_USERS = [
    ("asesor.bna", "Valeria · Asesora de agencia", "ASESOR"),
    ("supervisor.bna", "Supervisor de Solicitudes", "SUPERVISOR"),
    ("auditor.bna", "Auditor del laboratorio", "AUDITOR"),
    ("evaluador.demo", "Evaluación · Simulador de integración", "EVALUADOR"),
]


def seed(session_factory, password: str):
    """Alta idempotente; volver a ejecutar no reinicia claves ni borra expedientes."""
    if len(password) < 12:
        raise ValueError("Elige una clave de laboratorio de al menos 12 caracteres.")
    with session_factory.begin() as db:
        for username, name, role in DEMO_USERS:
            if db.scalar(select(User).where(User.username == username)) is None:
                db.add(
                    User(
                        id=str(uuid4()),
                        username=username,
                        name=name,
                        role=role,
                        password_hash=hash_password(password),
                    )
                )
        fixtures = [
            (1, "Juan", "Perez", "Quispe", "HABILITADO", "ACTIVO", 60),
            (2, "Lucía", "Torres", "Mamani", "HABILITADO", "ACTIVO", 60),
            (3, "Diego", "Flores", "Vargas", "OBSERVADO", "ACTIVO", 60),
            (4, "Ana", "Ramos", "Salas", "HABILITADO", "BLOQUEADO", 60),
            (5, "Miguel", "Condori", "Paz", "HABILITADO", "ACTIVO", -1),
        ]
        for index, names, paterno, materno, cap, state, days in fixtures:
            identifier = f"0198b000-0000-7009-8000-{index:012d}"
            if db.get(ClientReference, identifier):
                continue
            snapshot = {
                "id_cliente": identifier,
                "cod_tipo_documento": "DNI",
                "numero_documento": f"7000000{index}",
                "nombres": names,
                "apellido_paterno": paterno,
                "apellido_materno": materno,
                "fecha_nacimiento": "1990-05-10",
                "numero_celular": f"95900000{index}",
                "correo_electronico": f"cliente{index}@example.com",
                "estado_cliente": state,
                "id_caso": f"0198b000-0000-7012-8000-{index:012d}",
                "id_verificacion": f"0198b000-0000-7013-8000-{index:012d}",
                "fecha_verificacion": business_today().isoformat(),
                "vigente_hasta": (business_today() + timedelta(days=days)).isoformat(),
                "estado_habilitante": cap,
                "version_contrato": "CR-INT-01-DEMO-v1",
                "simulado": True,
            }
            db.add(
                ClientReference(
                    id=identifier,
                    document=snapshot["numero_documento"],
                    snapshot=snapshot,
                )
            )
