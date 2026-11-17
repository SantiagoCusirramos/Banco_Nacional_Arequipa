# Pruebas por ejecución y evidencia original

> Estado: **VIGENTE**. Última verificación documental: **2026-11-16** (código y evidencias existentes; sin repetir pruebas funcionales). Rama: `feature/sol-integracion-cap-eva`; SHA: `988dc0776da282fbef306632fc86426b6e372376`. Principal: [README SOL](../README.md).

## Registro más reciente: P20, 2026-11-16

[Informe original](p20/03-pruebas-y-evidencias.md), [JSON original saneado](p20/evidencias.json), [implementación](p20/01-implementacion.md). Sus bytes JSON se conservan; se comprobaron status/exit/contadores y resúmenes contra el propio archivo y scripts. Las cifras son **ejecuciones anteriores verificadas documentalmente ahora**, no suites reejecutadas durante esta reorganización.

| Ejecución independiente | Resultado original | Condiciones / fuente |
|---|---|---|
| Circuito completo TCP |150 checks principales +2 recuperación EVA |Aplicaciones originales independientes, MySQL, tres solicitudes/cuatro evaluaciones, APROBADA/OBSERVADA→v2→APROBADA/RECHAZADA. integration.checks y fault_checks. |
| Complementos TCP |403/422 y503 propagado CAP/SOL |dependency_checks: supervisor sin permiso,callback inválido,caída/restauración COREDB. |
| SOL |219 passed/1 warning45,20s |SQLite y MockTransport; incluye reinicios en archivo. regressions.SOL. |
| COREDB |57 passed/3 warnings0,85s |Unidad/auth en imagen propia, sin BD/red. |
| CAP |35 passed/1 skipped/1 warning1,34s |SQLite/COREDB falso; módulo contrato omitido por tzdata. |
| CAP_SOL |4 passed/1 warning0,31s |Imagen SOL con tzdata; cubre módulo omitido, ejecución separada. |
| EVA completa |65 passed/3 warnings3,78s |Tercer MySQL exclusivo; COREDB/SOL falsos en esa suite. |
| EVA motor |12 passed |Subconjunto de EVA65: no sumar como cobertura adicional. |
| Parche acuse |9 unitarios +7 TCP |Mocks o servidor de fallos por proceso; no reemplazan SOL del circuito completo. |
| Infraestructura estática |9 negativos,97 fuentes verificadas |config/hashes/gates; no E2E. |
| Frontend |114 passed/2 expected fail;lint/tsc/build0 |Copia saneada original, sin credenciales; Node/Next propios. |
| Proxy Next→SOL |login,cookie HttpOnly,política REAL,bandeja |HTTP desde host en launcher; no automatización visual de navegador P20. |

No sumar150 con219 ni65 con12: miden escenarios, casos y subconjuntos distintos. No generalizar la suite SOL SQLite a MySQL; la persistencia MySQL P20 se comprobó con consultas propias durante el circuito. Los warnings no son fallos esperados; los2 expected fail son resultado explícito del frontend.

## Condiciones y reproducción

Ver [guía vigente](../05-despliegue/README.md). `regressions` ejecuta suites locales; `eva-regressions` crea un MySQL exclusivo y sus fixtures destruyen solo sus tablas/base de pruebas. No ejecutar para validar una reorganización documental. `test` y `up` crean datos sintéticos: tampoco son read-only. `status` y configuración Compose son alternativas sin escrituras de BD.

Los resultados incluyen fallos iniciales resueltos; el [changelog](../change-log.md) no se reescribe. P20 requiere parche aislado de envios.py y doble de acuse de tests; el motor y APIs originales no se sustituyen por mocks en el camino principal.

## Ejecuciones históricas

- [v2: HTML/XML/PNG](historicas/v2/indice.html):52 pruebas antiguas y capturas de reporte/navegador; no evidencia institucional ni P20.
- [E06: JSON HTTP/manifiesto/reinicio](historicas/e06/): ensayo SOL con proveedores simulados.
- [cierre E06](../06-historico/entregas/sol-entrega-final.md) y [cierre anterior P20](../06-historico/entregas/sol-integracion-entrega-final.md):169 o219 según ejecución, sin mezclar etapas.
- OpenAPI E01/E05/E06 permanece en raíz documental por compatibilidad de scripts. Son snapshots históricos, no OpenAPI actual garantizado: [E06 REAL](../sol-openapi-e06-real.json), [E06 SIMULADO](../sol-openapi-e06-simulado.json), [E05 de referencia](../sol-openapi-e05-simulado.json).

## Validación documental de esta reorganización

Resultados y comandos en [REORGANIZACION_DOCUMENTAL](../06-historico/REORGANIZACION_DOCUMENTAL.md). Solo análisis estático; ninguna nueva cifra de pruebas bancarias se atribuye a esta tarea. Inventario original y mapa permiten comprobar conservación de evidencias y recursos.
