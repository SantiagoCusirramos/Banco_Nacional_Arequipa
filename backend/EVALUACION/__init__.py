"""Módulo 12 Evaluación Crediticia (Línea de Créditos).

Recibe el expediente de Solicitud (CR-INT-02) y lo registra en COREDB, ofrece al analista la
bandeja, la evaluación con la regla RN-EVA-002-P y la decisión, y devuelve el resultado a
Solicitud (CR-INT-03). No tiene base propia: los datos viven en `creditos.*` de la base
integrada y se escriben solo por COREDB.
"""
