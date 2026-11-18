"""Configuración del Bus de Servicios. Sin valores por omisión para direcciones ni claves:
si falta algo, el servicio no arranca y el error nombra cada variable que falta."""

import math
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

# Una ruta por módulo del producto: /bus/<módulo en minúsculas>/<ruta del módulo>.
MODULOS = ("COREDB", "CUENTAS", "TARJETAS", "CAPTACION", "SOL", "EVALUACION", "DESEMBOLSO", "COBRANZA", "SEGURIDAD", "ATM", "BILLETERA")

# Nunca públicos: COREDB es el núcleo, y a él solo llegan módulos con su credencial.
NUNCA_PUBLICOS = ("COREDB",)
# Nombre del consumidor de un módulo público (sin X-Bus-Token); no se puede declarar.
PUBLICO = "PUBLICO"

LARGO_MINIMO_TOKEN = 32
_NOMBRE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ConfiguracionInvalida(RuntimeError):
    pass


@dataclass(frozen=True)
class Configuracion:
    modulos: dict          # NOMBRE -> URL base, sin "/" final
    consumidores: dict     # token -> NOMBRE del consumidor
    timeout: float         # segundos que espera la respuesta de un módulo
    timeout_conexion: float
    permitidos: dict = None            # NOMBRE del módulo -> consumidores que pueden usarlo
    publicos: frozenset = frozenset()  # módulos a los que se llega sin X-Bus-Token (PUBLICO)


def _url(nombre, valor, errores):
    try:
        partes = urlsplit(valor)
        valida = (partes.scheme in ("http", "https") and partes.hostname
                  and partes.username is None and partes.password is None
                  and not partes.query and not partes.fragment and not any(c.isspace() for c in valor))
        partes.port  # también rechaza un puerto inválido
    except ValueError:
        valida = False
    if not valida:
        errores.append(f"{nombre}: URL http(s) con host, sin credenciales, consulta ni fragmento")
    return valor.rstrip("/")


def _segundos(entorno, nombre, omision, errores):
    texto = entorno.get(nombre, "").strip() or omision
    try:
        valor = float(texto)
    except ValueError:
        valor = math.nan
    if not (0 < valor <= 300):
        errores.append(f"{nombre}: segundos entre 0 y 300")
    return valor


def cargar(entorno):
    faltan, errores = [], []

    modulos = {}
    for modulo in MODULOS:
        nombre = f"BUS_URL_{modulo}"
        valor = entorno.get(nombre, "").strip()
        if not valor:
            faltan.append(nombre)
        else:
            modulos[modulo] = _url(nombre, valor, errores)

    consumidores = {}
    lista = [c.strip() for c in entorno.get("BUS_CONSUMIDORES", "").split(",") if c.strip()]
    if not lista:
        faltan.append("BUS_CONSUMIDORES")
    for consumidor in lista:
        if consumidor == PUBLICO:
            errores.append("BUS_CONSUMIDORES: PUBLICO está reservado para el canal sin credencial")
            continue
        if not _NOMBRE.match(consumidor):
            errores.append(f"BUS_CONSUMIDORES: nombre inválido {consumidor!r} (mayúsculas, dígitos y _)")
            continue
        nombre = f"BUS_TOKEN_{consumidor}"
        token = entorno.get(nombre, "")
        if not token:
            faltan.append(nombre)
        elif len(token) < LARGO_MINIMO_TOKEN or any(c.isspace() for c in token):
            errores.append(f"{nombre}: al menos {LARGO_MINIMO_TOKEN} caracteres, sin espacios")
        elif token in consumidores:
            errores.append(f"{nombre}: repite el token de {consumidores[token]}")
        else:
            consumidores[token] = consumidor

    # BUS_PERMITIDOS_<MÓDULO>: solo esos consumidores usan el módulo; los demás, 403.
    permitidos = {}
    for modulo in MODULOS:
        nombre = f"BUS_PERMITIDOS_{modulo}"
        lista = [c.strip() for c in entorno.get(nombre, "").split(",") if c.strip()]
        if lista:
            desconocidos = [c for c in lista if c not in consumidores.values()]
            if desconocidos:
                errores.append(f"{nombre}: no están en BUS_CONSUMIDORES: {', '.join(desconocidos)}")
            else:
                permitidos[modulo] = frozenset(lista)

    # BUS_MODULOS_PUBLICOS: módulos con autenticación propia de usuario a los que un canal
    # sin credencial del Bus (la app móvil: un token dentro de la app no sería secreto)
    # llega como PUBLICO.
    publicos = set()
    for modulo in [m.strip().upper() for m in entorno.get("BUS_MODULOS_PUBLICOS", "").split(",") if m.strip()]:
        if modulo not in MODULOS:
            errores.append(f"BUS_MODULOS_PUBLICOS: el módulo {modulo} no está en el Bus")
        elif modulo in NUNCA_PUBLICOS:
            errores.append(f"BUS_MODULOS_PUBLICOS: {modulo} no puede ser público")
        elif modulo in permitidos:
            errores.append(f"BUS_MODULOS_PUBLICOS: {modulo} tiene BUS_PERMITIDOS_{modulo}; no puede ser público")
        else:
            publicos.add(modulo)

    timeout = _segundos(entorno, "BUS_TIMEOUT_SEG", "9", errores)
    timeout_conexion = _segundos(entorno, "BUS_TIMEOUT_CONEXION_SEG", "2", errores)

    if faltan:
        errores.insert(0, "faltan " + ", ".join(faltan))
    if errores:
        raise ConfiguracionInvalida("Configuración del Bus inválida: " + "; ".join(errores))
    return Configuracion(modulos, consumidores, timeout, timeout_conexion, permitidos, frozenset(publicos))
