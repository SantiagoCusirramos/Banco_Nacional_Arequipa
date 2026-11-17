"""Formato de respuestas ITIL-02 para el módulo ATM."""

import time
import uuid
from datetime import datetime
from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


def _metadata(request: Request, inicio: float, modulo_emisor: str = "ATM") -> dict:
    return {
        "uuid_transaccion": request.headers.get("X-Correlation-ID") or str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "modulo_emisor": modulo_emisor,
        "tiempo_ejecucion_ms": round((time.perf_counter() - inicio) * 1000, 1),
    }


def _serializar(data: Any) -> Any:
    """Serializa modelos Pydantic y otros objetos a JSON."""
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_serializar(item) for item in data]
    if isinstance(data, dict):
        return {k: _serializar(v) for k, v in data.items()}
    return data


def exito(request: Request, data: Any | None, status_code: int = 200,
          message: str = "Operacion ejecutada satisfactoriamente", inicio: float | None = None) -> JSONResponse:
    if inicio is None:
        inicio = time.perf_counter()
    cuerpo = {
        "success": True,
        "status_code": status_code,
        "message": message,
        "data": _serializar(data),
        "metadata": _metadata(request, inicio),
    }
    return JSONResponse(cuerpo, status_code=status_code)


def error(request: Request, status_code: int, error_code: str, message: str,
          details: dict | None = None, inicio: float | None = None) -> JSONResponse:
    if inicio is None:
        inicio = time.perf_counter()
    cuerpo = {
        "success": False,
        "status_code": status_code,
        "error_code": error_code,
        "message": message,
        "details": details or {},
        "metadata": _metadata(request, inicio),
    }
    return JSONResponse(cuerpo, status_code=status_code)