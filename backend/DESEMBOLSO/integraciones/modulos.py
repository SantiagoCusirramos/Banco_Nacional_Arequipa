"""Contratos de los módulos contraparte en el producto BNA.

- Evaluación (CR-INT-04, backend/EVALUACION): aprobación con el calendario de SOL y aviso DESEMBOLSADA.
- CUENTAS (CR-INT-05, backend/CUENTAS): cuentas del cliente, depósito idempotente y sus movimientos.
- Cobranza (CR-INT-06, PR #68): POST /cr-int-06/obligaciones con el calendario de SOL sin cambios.
- Clientes no está en el producto: la identidad la verifica el operador en ventanilla (ordenes.py).
- Seguridad (laboratorio) no ofrece antifraude ni recibe eventos de otros módulos (CR-INT-10).
Evaluación y CUENTAS se llaman con el usuario de servicio de COREDB; Cobranza, con su X-API-Key.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote

import httpx

from ..config import Config
from ..core.dinero import a_decimal, formatear
from ..core.errores import DependenciaNoDisponible, ErrorNegocio
from ..core.tiempo import ahora_lima, desde_iso
from .coredb import SesionServicio, VerificadorSesiones
from .http import ClienteHttp, Latencias, cuerpo

log = logging.getLogger("desembolso.integraciones")


@dataclass(frozen=True)
class Aprobacion:
    aprobacion_id: str
    version: int
    credito_id: str
    cliente_id: str
    cliente_nombre: str
    cliente_documento: str
    producto: str
    importe: Decimal
    moneda: str
    plazo_meses: int | None
    tasa_tea: str | None
    estado: str
    vigente_hasta: datetime | None
    solicitud_id: str | None = None
    calendario: tuple[dict, ...] = ()

    @property
    def habilitada(self) -> bool:
        return self.estado == "VIGENTE" and (self.vigente_hasta is None or self.vigente_hasta >= ahora_lima())

    @classmethod
    def desde(cls, d: dict) -> Aprobacion:
        """La aprobación de CR-INT-04 tal como la publica Evaluación (backend/EVALUACION)."""
        tasa = d.get("tasaTea")
        porcentaje = None if tasa is None else format(
            (Decimal(str(tasa)) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")
        return cls(
            aprobacion_id=d["idAprobacion"], version=int(d["version"]), credito_id=d["codCredito"],
            cliente_id=d["idCliente"], cliente_nombre=d.get("clienteNombre", ""),
            cliente_documento=d.get("numeroDocumento", ""), producto=d.get("producto", ""),
            importe=a_decimal(d["montoAprobado"]), moneda=d["moneda"], plazo_meses=d.get("plazoMeses"),
            tasa_tea=porcentaje, estado=d["estado"], vigente_hasta=desde_iso(d.get("vigenteHasta")),
            solicitud_id=d.get("idSolicitud"), calendario=tuple((d.get("calendario") or {}).get("cuotas") or ()))


def _mensaje(r: httpx.Response) -> tuple[str | None, str]:
    """Código y mensaje del error, en los formatos de COREDB/Evaluación, CUENTAS y Cobranza."""
    b = cuerpo(r)
    error = b.get("error") if isinstance(b.get("error"), dict) else {}
    codigo = error.get("code") or b.get("error_code") or b.get("regla")
    mensaje = error.get("message") or b.get("message") or b.get("detalle") or f"HTTP {r.status_code}"
    if isinstance(b.get("detail"), list):
        mensaje = "El contrato no aceptó algún campo: " + ", ".join(
            ".".join(str(p) for p in e.get("loc", [])) for e in b["detail"][:5])
    return codigo, str(mensaje)


def _exigir(r: httpx.Response, modulo: str) -> dict:
    if r.status_code in (200, 201):
        return r.json()
    codigo, mensaje = _mensaje(r)
    if r.status_code in (401, 403):
        raise ErrorNegocio(503, "PERMISO_DE_SERVICIO",
                           f"{modulo} no aceptó al usuario de servicio de Desembolso: {mensaje}",
                           {"modulo": modulo, "estado_http": r.status_code, "codigo": codigo})
    raise ErrorNegocio(502, "RESPUESTA_INESPERADA", f"{modulo} respondió con estado {r.status_code}: {mensaje}",
                       {"modulo": modulo, "codigo": codigo})


class Evaluacion:
    """CR-INT-04: aprobaciones vigentes de Evaluación, con el calendario de SOL."""

    def __init__(self, http: ClienteHttp, sesion: SesionServicio, config: Config):
        self._http, self._sesion, self._config = http, sesion, config

    def _get(self, ruta: str, params: dict | None = None) -> httpx.Response:
        return self._sesion.con_token(lambda t: self._http.solicitar(
            "GET", ruta, params=params, cabeceras={"Authorization": f"Bearer {t}"},
            reintentos=self._config.reintentos_consulta))

    def buscar(self, documento: str | None = None, credito_id: str | None = None) -> list[Aprobacion]:
        params = {k: v for k, v in {"numeroDocumento": documento, "codCredito": credito_id}.items() if v}
        return [Aprobacion.desde(a) for a in _exigir(self._get("/eva/v1/aprobaciones", params), "Evaluación")["items"]]

    def obtener(self, aprobacion_id: str) -> Aprobacion | None:
        r = self._get(f"/eva/v1/aprobaciones/{quote(aprobacion_id, safe='')}")
        if r.status_code == 404:
            return None
        return Aprobacion.desde(_exigir(r, "Evaluación"))

    def registrar_desembolso(self, aviso: dict) -> dict:
        """Marca la aprobación DESEMBOLSADA. Evaluación devuelve lo mismo si se repite con la misma orden."""
        r = self._sesion.con_token(lambda t: self._http.solicitar(
            "POST", f"/eva/v1/aprobaciones/{quote(aviso['idAprobacion'], safe='')}/desembolso",
            json={"version": aviso["version"], "codigoOrden": aviso["codigoOrden"],
                  "fechaDesembolso": aviso["fechaDesembolso"]},
            cabeceras={"Authorization": f"Bearer {t}"}))
        if r.status_code == 200:
            datos = r.json()
            return {"confirmacion_id": f"{datos['idAprobacion']}@v{datos['version']}", "duplicado": False}
        codigo, mensaje = _mensaje(r)
        raise ErrorNegocio(409 if r.status_code < 500 else 502, codigo or "RECHAZO_EVALUACION",
                           f"Evaluación no registró el desembolso: {mensaje}",
                           {"estado_http": r.status_code, "permanente": r.status_code < 500})


def clave_abono(orden_id: str) -> str:
    """CUENTAS exige un UUIDv4 en X-Idempotency-Key: se deriva de la orden, siempre el mismo."""
    base = uuid.uuid5(uuid.NAMESPACE_URL, f"bna:desembolso:abono:{orden_id}")
    return str(uuid.UUID(bytes=base.bytes, version=4))


def marca(codigo_orden: str) -> str:
    """Va en la glosa del depósito: con ella se encuentra el movimiento sin volver a abonar."""
    return f"(ref. {codigo_orden})"


def glosa(d: dict) -> str:
    return f"Desembolso del crédito {d['credito_id']} {marca(d['codigo_orden'])}"[:200]


def _fecha_cuentas(texto: str | None) -> str | None:
    """COREDB guarda UTC sin zona; se devuelve con zona para convertirlo a la hora de Lima."""
    if not texto:
        return None
    fecha = datetime.fromisoformat(texto)
    return (fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)).isoformat()


def _enmascarar_cuenta(numero: str) -> str:
    return "****" + numero[-4:]


def elegibilidad(c: dict, cliente_id: str, moneda: str | None) -> tuple[bool, str | None]:
    """Escenario base (RN-03): cuenta de ahorros activa, individual, del titular y en la moneda del crédito."""
    if cliente_id not in (c.get("titulares") or []):
        return False, "TITULAR_DISTINTO"
    if c.get("estado_cuenta") != "ACTIVA":
        return False, f"CUENTA_{c.get('estado_cuenta')}"
    if c.get("regimen") != "INDIVIDUAL":
        return False, "CUENTA_MANCOMUNADA"
    if moneda and c.get("moneda") != moneda:
        return False, "MONEDA_DISTINTA"
    return True, None


class Cuentas:
    """CR-INT-05 sobre el módulo CUENTAS, que registra el movimiento en COREDB."""

    LIMITE_MOVIMIENTOS = 50     # lo que CUENTAS devuelve por consulta
    admite_reversion = False    # CUENTAS no ofrece extorno: requiere un cambio en el CORE

    def __init__(self, http: ClienteHttp, sesion: SesionServicio, config: Config):
        self._http, self._sesion, self._config = http, sesion, config

    def _consultar(self, ruta: str) -> httpx.Response:
        return self._sesion.con_token(lambda t: self._http.solicitar(
            "GET", ruta, cabeceras={"Authorization": f"Bearer {t}"}, reintentos=self._config.reintentos_consulta))

    @staticmethod
    def _datos(r: httpx.Response):
        return (_exigir(r, "Cuentas") or {}).get("data")

    def _cuenta_publica(self, c: dict, cliente_id: str, moneda: str | None) -> dict:
        elegible, motivo = elegibilidad(c, cliente_id, moneda)
        return {"cuenta_id": c["num_cuenta"], "numero_enmascarado": _enmascarar_cuenta(c["num_cuenta"]),
                "producto": f"Cuenta de ahorros {c.get('moneda')}", "moneda": c.get("moneda"),
                "estado": c.get("estado_cuenta"),
                "titularidad": "INDIVIDUAL" if c.get("regimen") == "INDIVIDUAL" else "MANCOMUNADA",
                "elegible": elegible, "motivo": motivo}

    def elegibles(self, cliente_id: str, moneda: str) -> list[dict]:
        r = self._consultar(f"/consolidada/{quote(cliente_id, safe='')}")
        if r.status_code == 404:
            return []
        return [self._cuenta_publica(c, cliente_id, moneda) for c in self._datos(r) or []]

    def elegibilidad(self, cuenta_id: str, cliente_id: str, moneda: str) -> dict:
        r = self._consultar(f"/{quote(cuenta_id, safe='')}")
        if r.status_code == 404:
            return {"cuenta_id": cuenta_id, "elegible": False, "motivo": "CUENTA_INEXISTENTE",
                    "numero_enmascarado": None, "referencia": cuenta_id}
        c = self._datos(r)
        elegible, motivo = elegibilidad(c, cliente_id, moneda)
        return {"cuenta_id": cuenta_id, "elegible": elegible, "motivo": motivo,
                "numero_enmascarado": _enmascarar_cuenta(c["num_cuenta"]), "referencia": f"CUENTAS:{c['num_cuenta']}"}

    def abonar(self, d: dict) -> dict:
        """Depósito en la cuenta destino, un solo intento (RT-04). Sin respuesta, un 5xx o una llave en
        conflicto dejan el resultado incierto; un rechazo de negocio de CUENTAS es definitivo."""
        cuerpo_deposito = {"num_cuenta": d["cuenta_id"], "monto": formatear(d["importe"]), "moneda": d["moneda"],
                           "glosa": glosa(d)}
        cabeceras = {"X-Idempotency-Key": clave_abono(d["id"]), "X-Channel-ID": self._config.canal_cuentas,
                     "X-Request-Timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            r = self._sesion.con_token(lambda t: self._http.solicitar(
                "POST", "/deposito", json=cuerpo_deposito, cabeceras={**cabeceras, "Authorization": f"Bearer {t}"},
                timeout=self._config.timeout_abono_seg))
        except DependenciaNoDisponible:
            raise
        except ErrorNegocio as exc:   # sin credencial de servicio: no se llegó a CUENTAS
            raise DependenciaNoDisponible("Cuentas", incierto=True, causa=exc.codigo) from exc
        if r.status_code in (200, 201):
            datos = r.json().get("data") or {}
            return {"estado": "CONFIRMADO", "operacion_id": datos["uuid_transaccion"], "fecha_efectiva": None,
                    "replay": bool(datos.get("replay"))}
        if r.status_code in (401, 409):
            raise DependenciaNoDisponible("Cuentas", incierto=True, causa=f"HTTP_{r.status_code}")
        codigo, mensaje = _mensaje(r)
        return {"estado": "RECHAZADO", "codigo": codigo or f"HTTP_{r.status_code}", "motivo": mensaje}

    def consultar_abono(self, d: dict) -> dict:
        """RN-07: busca el depósito de la orden entre los movimientos de la cuenta, sin volver a abonar.
        COREDB registra el movimiento en la misma transacción que el saldo: si no aparece, no se abonó."""
        r = self._consultar(f"/{quote(d['cuenta_id'], safe='')}/movimientos")
        if r.status_code == 404:
            return {"estado": "NO_ENCONTRADO"}
        movimientos = self._datos(r) or []
        referencia = marca(d["codigo_orden"])
        for m in movimientos:
            if referencia in str(m.get("glosa", "")):
                return {"estado": "CONFIRMADO", "operacion_id": m.get("uuid_transaccion"),
                        "fecha_efectiva": _fecha_cuentas(m.get("fecha_hora"))}
        if len(movimientos) >= self.LIMITE_MOVIMIENTOS:
            return {"estado": "DESCONOCIDO"}   # puede estar más atrás: no se concluye nada
        return {"estado": "NO_ENCONTRADO"}

    def movimiento(self, uuid_transaccion: str) -> dict | None:
        r = self._consultar(f"/movimiento/{quote(uuid_transaccion, safe='')}")
        if r.status_code == 404:
            return None
        return self._datos(r)

    def movimientos(self, cuenta_id: str) -> list[dict]:
        r = self._consultar(f"/{quote(cuenta_id, safe='')}/movimientos")
        return [] if r.status_code == 404 else (self._datos(r) or [])

    def revertir(self, cuerpo_: dict, clave: str) -> dict:
        raise ErrorNegocio(409, "REVERSION_NO_DISPONIBLE",
                           "CUENTAS no ofrece extorno: la reversión requiere un cambio en el CORE")

    def consultar_reversion(self, clave: str) -> dict:
        return self.revertir({}, clave)


class Cobranza:
    """CR-INT-06: activa la obligación de cobro en Cobranza con el calendario de SOL sin cambios.

    Cobranza identifica la llamada por codCredito: repetirla responde 409 (RN-COB-001) y no
    duplica el crédito, así que ese 409 es un acuse."""

    def __init__(self, http: ClienteHttp, config: Config):
        self._http, self._config = http, config

    @property
    def configurada(self) -> bool:
        return bool(self._config.cobranza_url and self._config.cobranza_api_key)

    def activar_obligacion(self, obligacion: dict) -> dict:
        if not self.configurada:
            raise DependenciaNoDisponible("Cobranza", causa="NO_CONFIGURADA")
        r = self._http.solicitar("POST", "/cr-int-06/obligaciones", json=obligacion,
                                 cabeceras={"X-API-Key": self._config.cobranza_api_key})
        if r.status_code in (200, 201):
            return {"confirmacion_id": obligacion["codCredito"], "duplicado": False}
        codigo, mensaje = _mensaje(r)
        if r.status_code == 409 and codigo == "RN-COB-001":
            return {"confirmacion_id": obligacion["codCredito"], "duplicado": True}
        raise ErrorNegocio(422, codigo or "RECHAZO_COBRANZA", f"Cobranza no activó la obligación: {mensaje}",
                           {"estado_http": r.status_code, "permanente": True})


class Seguridad:
    """El Seguridad del producto es un laboratorio: no ofrece antifraude a los módulos ni recibe sus
    eventos críticos (CR-INT-10). La bitácora des_auditoria es la fuente de verdad mientras tanto."""

    def antifraude(self, datos: dict) -> dict:
        raise ErrorNegocio(503, "ANTIFRAUDE_NO_DISPONIBLE", "Seguridad todavía no ofrece antifraude a los módulos")

    def publicar_evento(self, evento: dict) -> None:
        log.debug("Evento crítico sin receptor en Seguridad: %s", evento.get("accion"))


class Modulos:
    def __init__(self, config: Config, transportes: dict[str, httpx.BaseTransport] | None = None):
        t = transportes or {}
        self.latencias = Latencias()
        espera = config.timeout_dependencia_seg
        self._coredb = ClienteHttp("COREDB", config.coredb_url, espera, self.latencias, t.get("coredb"))
        self._clientes = [
            self._coredb,
            ClienteHttp("Evaluacion", config.evaluacion_url, espera, self.latencias, t.get("evaluacion")),
            ClienteHttp("Cuentas", config.cuentas_url, espera, self.latencias, t.get("cuentas")),
            ClienteHttp("Cobranza", config.cobranza_url, espera, self.latencias, t.get("cobranza")),
        ]
        self.sesion = SesionServicio(self._coredb, config)
        self.sesiones = VerificadorSesiones(self._coredb, config)
        self.evaluacion = Evaluacion(self._clientes[1], self.sesion, config)
        self.cuentas = Cuentas(self._clientes[2], self.sesion, config)
        self.cobranza = Cobranza(self._clientes[3], config)
        self.seguridad = Seguridad()

    def coredb_disponible(self) -> bool:
        try:
            return self._coredb.solicitar("GET", "/coredb/salud", timeout=2).status_code == 200
        except ErrorNegocio:
            return False

    def cerrar(self) -> None:
        for cliente in self._clientes:
            cliente.cerrar()
