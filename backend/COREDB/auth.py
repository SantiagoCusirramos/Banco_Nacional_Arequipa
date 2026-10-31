"""Autenticación enchufable.

Hoy NO hay autenticación: `actor_actual` confía en la cabecera X-Actor y solo
sirve para registrar quién actúa en la auditoría. Cuando exista el JWT, se
reemplaza esta dependencia sin tocar los routers:

    app.dependency_overrides[actor_actual] = dependencia_jwt
"""

from dataclasses import dataclass

from fastapi import Header


@dataclass(frozen=True)
class Actor:
    usuario: str
    # Sin JWT no se sabe quién llama: todo cambio de la API se registra como del banco.
    # La dependencia del JWT lo derivará del usuario autenticado.
    origen: str = "OPERADOR"


def actor_actual(
    x_actor: str = Header(default="local", min_length=1, max_length=40, pattern=r"\S"),
) -> Actor:
    return Actor(usuario=x_actor.strip())
