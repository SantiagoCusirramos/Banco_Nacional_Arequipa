# Integración académica CAP→SOL→EVA→SOL y documentación consolidada

> Estado: PROPUESTO (descripción del PR final). Verificación documental2026-11-16. Principal: [README SOL](../../README.md). Base de código analizada988dc0776da282fbef306632fc86426b6e372376; rama feature/sol-integracion-cap-eva.

SOL ya puede demostrar el recorrido completo con aplicaciones originales CAP/COREDB/EVA, HTTP y MySQL aislados. El launcher configura callbacks y auditoría académica explícita; el parche EVA valida el contenido del acuse antes de marcar un resultado entregado. Se preservan políticas, restricciones de fiadores/pago doble y módulos institucionales.

La documentación se reorganiza alrededor de un README vigente, arquitectura, diezRF, contratos, pruebas y despliegue. Se trasladan173 archivos, se inventarían213 originales y se conservan evidencias/históricos; scripts y rutas fijadas permanecen compatibles. Cuatro artefactos locales originales (dos caches y dos JSON generados) quedan inventariados como opcionales, fuera del commit.

Validación funcional previa P20:150 controles HTTP principales+2 recuperación EVA; APROBADA,OBSERVADA→v2→APROBADA yRECHAZADA; SOL219,COREDB57,CAP35+4,EVA65,frontend114/2 expected fail,lint/tsc/build0. Los mocks/unitarios se distinguen del circuito HTTP original. No son pruebas ejecutadas durante la reorganización.

Validación documental actual:enlaces Markdown/recursos HTML,JSON/XML,AST y hashes correctos; Compose config E06/demo/laboratorio/overlay salida0 sin arranque ni escrituras BD. Backend/frontend/configuración institucional intactos en este cierre. Sin merge/rebase.

Límites:verificadores externos CAP y auditoría académica SIMULADOS; TLS/SSO,auditoría institucional,RF005/008 y ratificación financiera pendientes. No se declara producción ni homologación institucional. MySQL del laboratorio es efímero.

Reproducción:`python3 Documents/solicitud-credito/laboratorio/demo_integracion.py`. Guía y evidencia:[README SOL](../../README.md),[pruebas](../../04-pruebas/README.md),[reorganización](../REORGANIZACION_DOCUMENTAL.md).
