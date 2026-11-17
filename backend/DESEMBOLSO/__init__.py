"""Módulo 13 Desembolso (Línea de Créditos).

Convierte una aprobación en un abono en la cuenta de ahorros del titular: el operador verifica
el documento, prepara la orden, registra la identidad y confirma. No tiene base propia: los
datos viven en `creditos.*` de la base integrada y se escriben solo por COREDB, que en la
confirmación abona, crea el crédito con su calendario oficial y deja la solicitud DESEMBOLSADA.
"""
