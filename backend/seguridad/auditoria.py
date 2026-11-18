"""Sellos HMAC encadenados de la bitácora general de COREDB (core.evento_auditoria).

Antes, Seguridad firmaba su propia bitácora en SQLite. Ahora la bitácora es la de la base
integrada, que escriben los procedimientos de todos los módulos, y Seguridad la sella por tramos:
el HMAC de cada evento encadena el anterior, y el primero de un tramo encadena el sello
previo. El sello se guarda en COREDB (`POST /coredb/auditoria/sellos`); la clave queda aquí.

Verificar recalcula todos los sellos con los eventos que COREDB devuelve: un evento sellado
cambiado, borrado o agregado, o un sello cambiado, rompen la cadena. Lo no sellado no queda
protegido, y quien tenga la clave puede rehacer los sellos. No es un SIEM ni almacenamiento
inmutable.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .coredb import ClienteCoreDb

INICIO = "0" * 64
DOMINIO = "auditoria-v1:"
CAMPOS = ("id_evento", "modulo", "entidad", "id_entidad", "accion", "actor", "correlation_id", "detalle",
          "fecha_hora")
PAGINA = 200            # el máximo de GET /coredb/auditoria
MAXIMO_POR_SELLO = 1000
LIMITACION = ("Lo no sellado no queda protegido, y quien tenga la clave de Seguridad puede rehacer los sellos. "
              "No es un SIEM ni almacenamiento inmutable.")


def canonico(evento: dict[str, Any]) -> str:
    return json.dumps({c: evento.get(c) for c in CAMPOS}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def encadenar(clave: str, previo: str, eventos: list[dict[str, Any]]) -> str:
    actual = previo
    for evento in eventos:
        actual = hmac.new(clave.encode(), (DOMINIO + actual + canonico(evento)).encode(), hashlib.sha256).hexdigest()
    return actual


def _fecha(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def sellos(coredb: ClienteCoreDb) -> list[dict[str, Any]]:
    todos: list[dict[str, Any]] = []
    while True:
        pagina = coredb.como_servicio("GET", "/coredb/auditoria/sellos",
                                      params={"despues_de_id": todos[-1]["id_sello"] if todos else 0, "limite": 1000})
        todos.extend(pagina)
        if len(pagina) < 1000:
            return todos


def eventos_tras(coredb: ClienteCoreDb, desde: int, hasta: int | None = None,
                 maximo: int | None = None) -> list[dict[str, Any]]:
    """Los eventos con id en (desde, hasta], del más antiguo al más reciente."""
    leidos: list[dict[str, Any]] = []
    ultimo = desde
    while maximo is None or len(leidos) < maximo:
        pagina = coredb.como_servicio("GET", "/coredb/auditoria", params={"despues_de_id": ultimo, "limite": PAGINA})
        for evento in pagina:
            if hasta is not None and evento["id_evento"] > hasta:
                return leidos
            leidos.append(evento)
            if maximo is not None and len(leidos) >= maximo:
                return leidos
        if len(pagina) < PAGINA:
            return leidos
        ultimo = pagina[-1]["id_evento"]
    return leidos


def sellar(coredb: ClienteCoreDb, clave: str, antiguedad_seg: float,
           ahora: datetime | None = None) -> dict[str, Any] | None:
    """Sella los eventos que siguen al último sello y tienen al menos `antiguedad_seg`. Devuelve
    el sello, o None si no hay eventos que sellar."""
    previos = sellos(coredb)
    desde = previos[-1]["hasta_evento"] if previos else 0
    previo = previos[-1]["hmac"] if previos else INICIO
    corte = (ahora or datetime.now(timezone.utc)) - timedelta(seconds=antiguedad_seg)
    tramo = []
    for evento in eventos_tras(coredb, desde, maximo=MAXIMO_POR_SELLO):
        if _fecha(evento["fecha_hora"]) > corte:
            break
        tramo.append(evento)
    if not tramo:
        return None
    return coredb.como_servicio("POST", "/coredb/auditoria/sellos", json={
        "hasta_evento": tramo[-1]["id_evento"], "eventos": len(tramo), "hmac": encadenar(clave, previo, tramo)})


def verificar(coredb: ClienteCoreDb, clave: str) -> dict[str, Any]:
    previo, esperado, total = INICIO, 0, 0
    todos = sellos(coredb)
    for sello in todos:
        eventos = eventos_tras(coredb, sello["desde_evento"], sello["hasta_evento"])
        motivo = None
        if sello["desde_evento"] != esperado:
            motivo = "el sello no empieza donde acabó el anterior"
        elif len(eventos) != sello["eventos"] or not eventos or eventos[-1]["id_evento"] != sello["hasta_evento"]:
            motivo = "faltan o sobran eventos en el tramo"
        elif not hmac.compare_digest(encadenar(clave, previo, eventos), sello["hmac"]):
            motivo = "un evento o el sello cambió"
        if motivo:
            return {"valida": False, "sellos_verificados": total, "roto_en_sello": sello["id_sello"],
                    "motivo": motivo, "limitacion": LIMITACION}
        previo, esperado, total = sello["hmac"], sello["hasta_evento"], total + 1
    sin_sellar = len(eventos_tras(coredb, esperado, maximo=PAGINA))
    return {"valida": True, "sellos_verificados": total, "ultimo_evento_sellado": esperado,
            "eventos_sin_sellar": sin_sellar if sin_sellar < PAGINA else f"{PAGINA} o más",
            "limitacion": LIMITACION}
