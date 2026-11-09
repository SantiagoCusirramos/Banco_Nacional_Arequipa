"""Autenticación: POST /core/auth/login y GET /core/auth/me."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from CORE.dependencies import db_session, usuario_actual
from CORE.schemas.auth import LoginRequest, PerfilRespuesta, TokenRespuesta
from CORE.schemas.usuarios import UsuarioRespuesta
from CORE.services import authsvc, rbac, usuariossvc

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenRespuesta)
def login(payload: LoginRequest, request: Request, db: Session = Depends(db_session)):
    token, expires_in, usuario = authsvc.iniciar_sesion(
        db,
        username=payload.username,
        password=payload.password,
        correlation_id=request.headers.get("x-correlation-id"),
    )
    return TokenRespuesta(
        access_token=token,
        expires_in=expires_in,
        usuario=UsuarioRespuesta(**usuariossvc.vista_publica(usuario)),
    )


@router.get("/me", response_model=PerfilRespuesta)
def me(usuario=Depends(usuario_actual)):
    return PerfilRespuesta(
        **usuariossvc.vista_publica(usuario),
        acciones=rbac.acciones_de_rol(usuario.rol),
    )
