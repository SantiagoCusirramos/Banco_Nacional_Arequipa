"""Módulo CORE — Núcleo transaccional y contable del BNA.

Único punto de acceso de la plataforma a la base de datos `bna`.
Ningún canal ni módulo toca la BD directamente; todo pasa por aquí
(vía Bus de Servicios en producción).

Acciones implementadas (ver Contexto_BNA/Acciones CORE.md):
VER/CREAR/MODIFICAR_CLIENTE, VER/CREAR/MODIFICAR_CUENTA,
REGISTRAR_MOVIMIENTO, VER/CREAR/BLOQUEAR_TARJETA,
CREAR_SOLICITUD_CREDITO, EVALUAR_CREDITO, APROBAR_CREDITO, VER_CREDITO,
REGISTRAR_PAGO, CONSULTAR_DEUDA, CREAR_USUARIO, ASIGNAR_ROLES,
GESTIONAR_PERMISOS, VER_AUDITORIA, GENERAR_REPORTES.
"""

__version__ = "0.1.0"
