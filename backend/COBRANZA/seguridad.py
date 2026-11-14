"""Validador de Seguridad para CR-INT-08 (RF-COB-004). PROPUESTA pendiente del Comite de Creditos:
Cobranza no implementa antifraude real, solo simula el token de Seguridad (clase aparte, igual que
app/cuentas.py), tal como se documenta en CLAUDE.md."""
import os
import time


class SeguridadSimulada:
    """Rechaza el token "TOKEN-INVALIDO" (o un token vacio). Tras `limite_rechazos` rechazos
    CONSECUTIVOS para el mismo idCliente, bloquea temporalmente sus pagos por `bloqueo_segundos`
    (duracion configurable). Un token valido reinicia el contador de rechazos."""

    def __init__(self, bloqueo_segundos=300, limite_rechazos=3):
        self.bloqueo_segundos = bloqueo_segundos
        self.limite_rechazos = limite_rechazos
        self._rechazos = {}         # idCliente -> rechazos consecutivos
        self._bloqueado_hasta = {}  # idCliente -> timestamp epoch hasta el que esta bloqueado

    def bloqueado(self, id_cliente):
        hasta = self._bloqueado_hasta.get(id_cliente)
        if hasta and time.time() < hasta:
            return True, hasta
        return False, None

    def validar(self, id_cliente, token):
        """Devuelve (ok: bool, motivo: str)."""
        esta_bloqueado, hasta = self.bloqueado(id_cliente)
        if esta_bloqueado:
            restante = int(hasta - time.time())
            return False, f"Cliente bloqueado temporalmente por Seguridad ({restante}s restantes)"
        if not token or token == "TOKEN-INVALIDO":
            self._rechazos[id_cliente] = self._rechazos.get(id_cliente, 0) + 1
            if self._rechazos[id_cliente] >= self.limite_rechazos:
                self._bloqueado_hasta[id_cliente] = time.time() + self.bloqueo_segundos
                self._rechazos[id_cliente] = 0
                return False, (f"Token de Seguridad invalido. Cliente bloqueado por {self.bloqueo_segundos}s "
                                f"tras {self.limite_rechazos} rechazos")
            return False, "Token de Seguridad invalido"
        self._rechazos[id_cliente] = 0
        return True, "Token valido (Seguridad simulado)"


def crear_validador_seguridad():
    segundos = int(os.environ.get("SEGURIDAD_BLOQUEO_SEGUNDOS", "300"))
    limite = int(os.environ.get("SEGURIDAD_LIMITE_RECHAZOS", "3"))
    return SeguridadSimulada(bloqueo_segundos=segundos, limite_rechazos=limite)
