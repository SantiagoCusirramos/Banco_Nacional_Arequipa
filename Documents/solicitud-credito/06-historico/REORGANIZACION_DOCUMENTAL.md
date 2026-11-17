# Reorganización documental SOL — P21

> Estado: HISTÓRICO (registro de esta reorganización). Última revisión:2026-11-16. Rama feature/sol-integracion-cap-eva; SHA988dc0776da282fbef306632fc86426b6e372376. Principal: [README SOL](../README.md).

## Inventario y estructura anterior

213 archivos originales:50 Markdown,15 JSON,19 Python,4 YAML/Compose,4 Dockerfiles,53 HTML,56 PNG,8 TXT,2 XML y2 pyc preexistentes ignorados. Lectura de contenido textual y bytes/hashes de todos antes de mover; PNG identificados por firma/colección, sin reinterpretar capturas como nuevas pruebas. Las colecciones HTML/XML describen evidencia histórica, no se regeneraron.

Raíz con informes sucesivos, contratos y planes mezclados; directorios auditoria-coredb-infra,integracion-final,evidencias-v2,prompts,laboratorio,demo. Cambios locales previos (incluidos documentos/scripts nuevos y changelog) preservados; no se descartaron ni se atribuyeron nuevamente.

## Estructura resultante y autoridad

README principal y01-arquitectura,02-funcionalidades,03-contratos,04-pruebas,05-despliegue,06-historico. Laboratorio/demo mantienen estructura ejecutable. Changelog permanece estable. Tres puentes de compatibilidad:plan-integracion-sol.md,CONTRATOS_HTTP_V2.md,sol-laboratorio-build.md. Seis OpenAPI y recursos ejecutables E06 permanecen en raíz por Path(__file__), directorios de referencia y build contexts. No modificar scripts para obtener una organización estética.

173 archivos trasladados (git mv en versionados; rename en no seguidos). Después se retiró del índice únicamente el staging de esos movimientos, sin revertir el árbol; no commits/push/branch/merge/cherry-pick. Cero archivos eliminados. Los2 pyc preexistentes no se incorporan ni se borran.

## Consolidaciones y procedencia

| Grupo original | Síntesis vigente | Decisión |
|---|---|---|
| Auditorías P00/E01/PR y COREDB/infra |[arquitectura](../01-arquitectura/README.md),[contratos](../03-contratos/README.md) |Archivar originales y distinguir fase previa al circuito P20. |
| E01–E06,matriz RF,funcionalidades internas |[RF vigente](../02-funcionalidades/matriz-rf.md) |Conservar detalles históricos; actualizar RF001/009/010 con P20, mantener RF005/008 bloqueados. |
| Contratos demo/v2/E01/E04 y P20 |[contratos utilizados](../03-contratos/README.md) |Consolidar esquemas/rutas sin homologar propuestas. Estructuras completas conservadas en originales. |
| Cierres,entregas,PR y resumen P20 |[README](../README.md) y[pruebas](../04-pruebas/README.md) |Una síntesis ejecutiva actual, registros de ejecución separados. |
| VALIDACION52,capturas v2,E06,P20 |[pruebas por ejecución](../04-pruebas/README.md) |No sumar resultados ni reescribir XML/JSON/PNG/HTML. |
| Guías anteriores,lab/demo y guía P20 |[despliegue](../05-despliegue/README.md) |Conservar comandos ejecutables y distinguir up/test con escrituras frente a status/config. |

Documentos vigentes:README, índices01–05 y matriz-rf; READMEs laboratorio/demo como navegación de recursos. Histórico:todos los informes por fase/tema y registros P20 como evidencia de su ejecución. Propuestas institucionales preservadas, sin acta aprobada inventada.

## Contradicciones resueltas

La matriz/cierres anteriores decían que no existía circuito conjunto: se mantienen como conclusión temporal histórica, superada por150+2 controles P20. La auditoría de COREDB halló bloqueo de auditoría/retorno antes del launcher; P20 configura overlay académico ycallback, no convierte auditoría simulada en institucional. Compose principal permanece SIMULADO y sin CAP/EVA: no confundirlo con laboratorio exportado. P20 tiene219 SOL SQLite;219 de una ejecución anterior con fixtures MySQL no se traslada a P20. EVA12 es subconjunto de65. Roles/TLS/políticas/fiadores/pago doble siguen pendientes.

El test_close_contracts.py caracteriza el defecto EVA original y espera su comportamiento antiguo; se conserva por trazabilidad, no debe ejecutarse como regresión del EVA parcheado. Los tests actuales del parche son test_callback_ack.py ytest_ack_tcp.py. La documentación vigente distingue ambos sin cambiar código.

## Enlaces y compatibilidad

Se recalcularon enlaces desde ubicación original y destino; HTML y sus assets se trasladaron como unidad. Manifiestos/JSON conservan paths/hashes de ejecución originales, explícitamente históricos. Los puntos de entrada README del proyecto,EMPEZAR_AQUI_SOL yREADME-INICIO reciben aviso/enlace al documento vigente; no se modifican backend/frontend/configuración para arreglar referencias.

El [inventario máquina](inventario-documental.json) contiene categoríaA–G,vigencia,hash,bytes,destino,acción,superposición y criterio de referencias de cada uno de213 originales. Tabla siguiente exhaustiva; archivos nuevos de síntesis/validación no se presentan como originales.

## Trazabilidad exhaustiva

| Archivo original | Nueva ubicación | Acción | Justificación |
|---|---|---|---|
| `CONTRATOS_DEMO.md` | `06-historico/contratos/CONTRATOS_DEMO.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `CONTRATOS_HTTP_V2.md` | `06-historico/contratos/CONTRATOS_HTTP_V2.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `CORRECCIONES_V2.md` | `06-historico/etapas/CORRECCIONES_V2.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `LECTURA_DEL_CODIGO.md` | `06-historico/etapas/LECTURA_DEL_CODIGO.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `PROPUESTAS_Y_DECISIONES.md` | `06-historico/coordinacion/PROPUESTAS_Y_DECISIONES.md` | ARCHIVAR/MOVER (G) | Archivar sin transformar propuestas en aprobaciones. |
| `VALIDACION.md` | `06-historico/etapas/VALIDACION.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `auditoria-coredb-infra/01-inventario-infraestructura.md` | `06-historico/auditorias/coredb-infra/01-inventario-infraestructura.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `auditoria-coredb-infra/02-apis-coredb.md` | `06-historico/auditorias/coredb-infra/02-apis-coredb.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `auditoria-coredb-infra/03-matriz-integracion-cap-sol-eva.md` | `06-historico/auditorias/coredb-infra/03-matriz-integracion-cap-sol-eva.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `auditoria-coredb-infra/04-bloqueos-y-plan-p0.md` | `06-historico/auditorias/coredb-infra/04-bloqueos-y-plan-p0.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `auditoria-coredb-infra/05-resumen-ejecutivo.md` | `06-historico/auditorias/coredb-infra/05-resumen-ejecutivo.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `change-log.md` | `change-log.md` | CONSERVAR (A) | Conservar ruta y entradas previas; solo añadir nuevos lotes. |
| `compose-e06.yaml` | `compose-e06.yaml` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `demo/Dockerfile.backend` | `demo/Dockerfile.backend` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `demo/Dockerfile.frontend` | `demo/Dockerfile.frontend` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `demo/README.md` | `demo/README.md` | CONSERVAR (B) | Conservar unidad ejecutable y enlazar guía vigente. |
| `demo/compose.yaml` | `demo/compose.yaml` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `demo/demo.py` | `demo/demo.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `demo/seed_demo.py` | `demo/seed_demo.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `demo/test_demo.py` | `demo/test_demo.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `e06_validar_http.py` | `e06_validar_http.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `e06_validar_mysql.py` | `e06_validar_mysql.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `evidencias-v2/caso-01.html` | `04-pruebas/historicas/v2/caso-01.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-01.png` | `04-pruebas/historicas/v2/caso-01.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-02.html` | `04-pruebas/historicas/v2/caso-02.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-02.png` | `04-pruebas/historicas/v2/caso-02.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-03.html` | `04-pruebas/historicas/v2/caso-03.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-03.png` | `04-pruebas/historicas/v2/caso-03.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-04.html` | `04-pruebas/historicas/v2/caso-04.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-04.png` | `04-pruebas/historicas/v2/caso-04.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-05.html` | `04-pruebas/historicas/v2/caso-05.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-05.png` | `04-pruebas/historicas/v2/caso-05.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-06.html` | `04-pruebas/historicas/v2/caso-06.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-06.png` | `04-pruebas/historicas/v2/caso-06.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-07.html` | `04-pruebas/historicas/v2/caso-07.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-07.png` | `04-pruebas/historicas/v2/caso-07.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-08.html` | `04-pruebas/historicas/v2/caso-08.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-08.png` | `04-pruebas/historicas/v2/caso-08.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-09.html` | `04-pruebas/historicas/v2/caso-09.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-09.png` | `04-pruebas/historicas/v2/caso-09.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-10.html` | `04-pruebas/historicas/v2/caso-10.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-10.png` | `04-pruebas/historicas/v2/caso-10.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-11.html` | `04-pruebas/historicas/v2/caso-11.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-11.png` | `04-pruebas/historicas/v2/caso-11.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-12.html` | `04-pruebas/historicas/v2/caso-12.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-12.png` | `04-pruebas/historicas/v2/caso-12.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-13.html` | `04-pruebas/historicas/v2/caso-13.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-13.png` | `04-pruebas/historicas/v2/caso-13.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-14.html` | `04-pruebas/historicas/v2/caso-14.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-14.png` | `04-pruebas/historicas/v2/caso-14.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-15.html` | `04-pruebas/historicas/v2/caso-15.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-15.png` | `04-pruebas/historicas/v2/caso-15.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-16.html` | `04-pruebas/historicas/v2/caso-16.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-16.png` | `04-pruebas/historicas/v2/caso-16.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-17.html` | `04-pruebas/historicas/v2/caso-17.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-17.png` | `04-pruebas/historicas/v2/caso-17.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-18.html` | `04-pruebas/historicas/v2/caso-18.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-18.png` | `04-pruebas/historicas/v2/caso-18.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-19.html` | `04-pruebas/historicas/v2/caso-19.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-19.png` | `04-pruebas/historicas/v2/caso-19.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-20.html` | `04-pruebas/historicas/v2/caso-20.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-20.png` | `04-pruebas/historicas/v2/caso-20.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-21.html` | `04-pruebas/historicas/v2/caso-21.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-21.png` | `04-pruebas/historicas/v2/caso-21.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-22.html` | `04-pruebas/historicas/v2/caso-22.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-22.png` | `04-pruebas/historicas/v2/caso-22.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-23.html` | `04-pruebas/historicas/v2/caso-23.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-23.png` | `04-pruebas/historicas/v2/caso-23.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-24.html` | `04-pruebas/historicas/v2/caso-24.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-24.png` | `04-pruebas/historicas/v2/caso-24.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-25.html` | `04-pruebas/historicas/v2/caso-25.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-25.png` | `04-pruebas/historicas/v2/caso-25.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-26.html` | `04-pruebas/historicas/v2/caso-26.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-26.png` | `04-pruebas/historicas/v2/caso-26.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-27.html` | `04-pruebas/historicas/v2/caso-27.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-27.png` | `04-pruebas/historicas/v2/caso-27.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-28.html` | `04-pruebas/historicas/v2/caso-28.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-28.png` | `04-pruebas/historicas/v2/caso-28.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-29.html` | `04-pruebas/historicas/v2/caso-29.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-29.png` | `04-pruebas/historicas/v2/caso-29.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-30.html` | `04-pruebas/historicas/v2/caso-30.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-30.png` | `04-pruebas/historicas/v2/caso-30.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-31.html` | `04-pruebas/historicas/v2/caso-31.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-31.png` | `04-pruebas/historicas/v2/caso-31.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-32.html` | `04-pruebas/historicas/v2/caso-32.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-32.png` | `04-pruebas/historicas/v2/caso-32.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-33.html` | `04-pruebas/historicas/v2/caso-33.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-33.png` | `04-pruebas/historicas/v2/caso-33.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-34.html` | `04-pruebas/historicas/v2/caso-34.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-34.png` | `04-pruebas/historicas/v2/caso-34.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-35.html` | `04-pruebas/historicas/v2/caso-35.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-35.png` | `04-pruebas/historicas/v2/caso-35.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-36.html` | `04-pruebas/historicas/v2/caso-36.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-36.png` | `04-pruebas/historicas/v2/caso-36.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-37.html` | `04-pruebas/historicas/v2/caso-37.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-37.png` | `04-pruebas/historicas/v2/caso-37.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-38.html` | `04-pruebas/historicas/v2/caso-38.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-38.png` | `04-pruebas/historicas/v2/caso-38.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-39.html` | `04-pruebas/historicas/v2/caso-39.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-39.png` | `04-pruebas/historicas/v2/caso-39.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-40.html` | `04-pruebas/historicas/v2/caso-40.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-40.png` | `04-pruebas/historicas/v2/caso-40.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-41.html` | `04-pruebas/historicas/v2/caso-41.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-41.png` | `04-pruebas/historicas/v2/caso-41.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-42.html` | `04-pruebas/historicas/v2/caso-42.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-42.png` | `04-pruebas/historicas/v2/caso-42.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-43.html` | `04-pruebas/historicas/v2/caso-43.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-43.png` | `04-pruebas/historicas/v2/caso-43.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-44.html` | `04-pruebas/historicas/v2/caso-44.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-44.png` | `04-pruebas/historicas/v2/caso-44.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-45.html` | `04-pruebas/historicas/v2/caso-45.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-45.png` | `04-pruebas/historicas/v2/caso-45.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-46.html` | `04-pruebas/historicas/v2/caso-46.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-46.png` | `04-pruebas/historicas/v2/caso-46.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-47.html` | `04-pruebas/historicas/v2/caso-47.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-47.png` | `04-pruebas/historicas/v2/caso-47.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-48.html` | `04-pruebas/historicas/v2/caso-48.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-48.png` | `04-pruebas/historicas/v2/caso-48.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-49.html` | `04-pruebas/historicas/v2/caso-49.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-49.png` | `04-pruebas/historicas/v2/caso-49.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-50.html` | `04-pruebas/historicas/v2/caso-50.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-50.png` | `04-pruebas/historicas/v2/caso-50.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-51.html` | `04-pruebas/historicas/v2/caso-51.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-51.png` | `04-pruebas/historicas/v2/caso-51.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-52.html` | `04-pruebas/historicas/v2/caso-52.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/caso-52.png` | `04-pruebas/historicas/v2/caso-52.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/entorno-mysql.json` | `04-pruebas/historicas/v2/entorno-mysql.json` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/frontend-build.txt` | `04-pruebas/historicas/v2/frontend-build.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/frontend-lint.txt` | `04-pruebas/historicas/v2/frontend-lint.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/http-local.json` | `04-pruebas/historicas/v2/http-local.json` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/indice.html` | `04-pruebas/historicas/v2/indice.html` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/login-case-regression.txt` | `04-pruebas/historicas/v2/login-case-regression.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/navegador.json` | `04-pruebas/historicas/v2/navegador.json` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/pytest-mysql.txt` | `04-pruebas/historicas/v2/pytest-mysql.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/pytest-mysql.xml` | `04-pruebas/historicas/v2/pytest-mysql.xml` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/pytest-sqlite.txt` | `04-pruebas/historicas/v2/pytest-sqlite.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/pytest-sqlite.xml` | `04-pruebas/historicas/v2/pytest-sqlite.xml` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/regresiones-seguridad.txt` | `04-pruebas/historicas/v2/regresiones-seguridad.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/ui-01-acceso.png` | `04-pruebas/historicas/v2/ui-01-acceso.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/ui-02-revision.png` | `04-pruebas/historicas/v2/ui-02-revision.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/ui-03-bandeja-aprobada-v2.png` | `04-pruebas/historicas/v2/ui-03-bandeja-aprobada-v2.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `evidencias-v2/ui-04-movil.png` | `04-pruebas/historicas/v2/ui-04-movil.png` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `integracion-final/01-implementacion.md` | `04-pruebas/p20/01-implementacion.md` | ARCHIVAR/MOVER (B) | Conservar registro original y separar evidencia de síntesis actual. |
| `integracion-final/02-endpoints-y-contratos.md` | `04-pruebas/p20/02-endpoints-y-contratos.md` | ARCHIVAR/MOVER (B) | Conservar registro original y separar evidencia de síntesis actual. |
| `integracion-final/03-pruebas-y-evidencias.md` | `04-pruebas/p20/03-pruebas-y-evidencias.md` | ARCHIVAR/MOVER (B) | Conservar registro original y separar evidencia de síntesis actual. |
| `integracion-final/04-matriz-real-simulado.md` | `04-pruebas/p20/04-matriz-real-simulado.md` | ARCHIVAR/MOVER (B) | Conservar registro original y separar evidencia de síntesis actual. |
| `integracion-final/05-guia-demostracion.md` | `04-pruebas/p20/05-guia-demostracion.md` | ARCHIVAR/MOVER (B) | Conservar registro original y separar evidencia de síntesis actual. |
| `integracion-final/06-resumen-final.md` | `04-pruebas/p20/06-resumen-final.md` | ARCHIVAR/MOVER (B) | Conservar registro original y separar evidencia de síntesis actual. |
| `integracion-final/evidencias.json` | `04-pruebas/p20/evidencias.json` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `laboratorio/Dockerfile.api` | `laboratorio/Dockerfile.api` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/Dockerfile.core` | `laboratorio/Dockerfile.core` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/README.md` | `laboratorio/README.md` | CONSERVAR (B) | Conservar unidad ejecutable y enlazar guía vigente. |
| `laboratorio/__pycache__/patch_eva.cpython-313.pyc` | `laboratorio/__pycache__/patch_eva.cpython-313.pyc` | CONSERVAR (F) | Cache preexistente; conservado sin incorporar a entregables. |
| `laboratorio/__pycache__/prepare.cpython-313.pyc` | `laboratorio/__pycache__/prepare.cpython-313.pyc` | CONSERVAR (F) | Cache preexistente; conservado sin incorporar a entregables. |
| `laboratorio/bootstrap_sol.py` | `laboratorio/bootstrap_sol.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/compose.audit-sim.yaml` | `laboratorio/compose.audit-sim.yaml` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/compose.yaml` | `laboratorio/compose.yaml` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/demo_integracion.py` | `laboratorio/demo_integracion.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/evidencias-http-independientes.json` | `laboratorio/evidencias-http-independientes.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `laboratorio/failure_http.py` | `laboratorio/failure_http.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/flow_http.py` | `laboratorio/flow_http.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/guard.py` | `laboratorio/guard.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/http_probe.py` | `laboratorio/http_probe.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/independent_http.py` | `laboratorio/independent_http.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/patch_eva.py` | `laboratorio/patch_eva.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/prepare.py` | `laboratorio/prepare.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/sources-manifest.json` | `laboratorio/sources-manifest.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `laboratorio/test_ack_tcp.py` | `laboratorio/test_ack_tcp.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/test_callback_ack.py` | `laboratorio/test_callback_ack.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/test_close_contracts.py` | `laboratorio/test_close_contracts.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/test_static.py` | `laboratorio/test_static.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `laboratorio/validate.py` | `laboratorio/validate.py` | CONSERVAR (F) | Ruta conservada por imports,Path(__file__),builds/montajes; no alterar lógica. |
| `plan-integracion-sol.md` | `06-historico/planes/plan-integracion-sol.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `prompts/E01-diagnostico-contratos.md` | `06-historico/prompts/E01-diagnostico-contratos.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `prompts/E02-funcionalidades-rf.md` | `06-historico/prompts/E02-funcionalidades-rf.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `prompts/E03-captacion-coredb.md` | `06-historico/prompts/E03-captacion-coredb.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `prompts/E04-evaluacion.md` | `06-historico/prompts/E04-evaluacion.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `prompts/E05-seguridad-frontend.md` | `06-historico/prompts/E05-seguridad-frontend.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `prompts/E06-validacion-entrega.md` | `06-historico/prompts/E06-validacion-entrega.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-adaptadores-cap-eva.md` | `06-historico/etapas/sol-adaptadores-cap-eva.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-apis-disponibles.md` | `06-historico/auditorias/sol-apis-disponibles.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-archivos-commit.txt` | `06-historico/entregas/sol-archivos-commit.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-auditoria-e01.md` | `06-historico/auditorias/sol-auditoria-e01.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-auditoria-pr-cap-eva.md` | `06-historico/auditorias/sol-auditoria-pr-cap-eva.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-auditoria.md` | `06-historico/auditorias/sol-auditoria.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-baseline.md` | `06-historico/auditorias/sol-baseline.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-captacion-coredb.md` | `06-historico/etapas/sol-captacion-coredb.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-cierre-rama.md` | `06-historico/entregas/sol-cierre-rama.md` | ARCHIVAR/MOVER (D) | Consolidar síntesis actual en README; conservar cierres íntegros. |
| `sol-contrato-evaluacion.md` | `06-historico/contratos/sol-contrato-evaluacion.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-contratos-finalizacion.md` | `06-historico/contratos/sol-contratos-finalizacion.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-coordinacion-proveedores.md` | `06-historico/coordinacion/sol-coordinacion-proveedores.md` | ARCHIVAR/MOVER (G) | Archivar sin transformar propuestas en aprobaciones. |
| `sol-e06-http-evidencia.json` | `04-pruebas/historicas/e06/sol-e06-http-evidencia.json` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-e06-manifiesto.json` | `04-pruebas/historicas/e06/sol-e06-manifiesto.json` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-e06-reinicio-privacidad.json` | `04-pruebas/historicas/e06/sol-e06-reinicio-privacidad.json` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-entrega-final.md` | `06-historico/entregas/sol-entrega-final.md` | ARCHIVAR/MOVER (D) | Consolidar síntesis actual en README; conservar cierres íntegros. |
| `sol-evaluacion.md` | `06-historico/etapas/sol-evaluacion.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-evidencias-testing.md` | `06-historico/etapas/sol-evidencias-testing.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-funcionalidades-internas.md` | `06-historico/etapas/sol-funcionalidades-internas.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-integracion-archivos-commit.txt` | `06-historico/entregas/sol-integracion-archivos-commit.txt` | ARCHIVAR/MOVER (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-integracion-entrega-final.md` | `06-historico/entregas/sol-integracion-entrega-final.md` | ARCHIVAR/MOVER (D) | Consolidar síntesis actual en README; conservar cierres íntegros. |
| `sol-integracion-pr-descripcion.md` | `06-historico/entregas/sol-integracion-pr-descripcion.md` | ARCHIVAR/MOVER (G) | Archivar sin transformar propuestas en aprobaciones. |
| `sol-laboratorio-build.md` | `06-historico/planes/sol-laboratorio-build.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-matriz-rf.md` | `06-historico/etapas/sol-matriz-rf.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-openapi-e01-real.json` | `sol-openapi-e01-real.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-openapi-e01-simulado.json` | `sol-openapi-e01-simulado.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-openapi-e05-real.json` | `sol-openapi-e05-real.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-openapi-e05-simulado.json` | `sol-openapi-e05-simulado.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-openapi-e06-real.json` | `sol-openapi-e06-real.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-openapi-e06-simulado.json` | `sol-openapi-e06-simulado.json` | CONSERVAR (E) | Conservar bytes y agrupación de ejecución; no reescribir resultados/manifiestos. |
| `sol-plan-laboratorio-cap-eva.md` | `06-historico/planes/sol-plan-laboratorio-cap-eva.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-pr-descripcion.md` | `06-historico/entregas/sol-pr-descripcion.md` | ARCHIVAR/MOVER (G) | Archivar sin transformar propuestas en aprobaciones. |
| `sol-pruebas-integracion-cap-eva.md` | `06-historico/etapas/sol-pruebas-integracion-cap-eva.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |
| `sol-seguridad-frontend.md` | `06-historico/etapas/sol-seguridad-frontend.md` | ARCHIVAR/MOVER (C) | Separar antecedente de conclusión vigente; conservar detalles únicos. |

## Validaciones y pendientes

En preparación: ejecutar [validador estático](validar_documentacion.py), JSON/AST/enlaces/recursos HTML/PNG, hashes de originales E/F, Compose config sin arranque, diff y comprobación de código intacto. No se reejecutan suites bancarias ni se altera ninguna base para esta tarea. Resultados reales de cierre se añaden al final.

## Cierre de validación documental P21

Validador reproducible: `PYTHONDONTWRITEBYTECODE=1 python3 Documents/solicitud-credito/06-historico/validar_documentacion.py`, salida0:361 enlaces Markdown,109 recursos HTML,16 JSON,20 AST Python,53 HTML,56 PNG,2 XML y213 originales representados sin errores. JSON de evidencias P20 contrastado, sin reejecutar sus pruebas funcionales.

Docker Compose config E06/demo/laboratorio base/overlay salió0 (4/5/12/13 servicios) con variables ficticias en archivos temporales, sin daemon/arranque/bases. Análisis adicional de Markdown versionado fuera de SOL:sin enlaces rotos; referencia de código/config a sol-laboratorio-build.md satisfecha por puente conservado. Prefijo previo del changelog intacto; backend/frontend/infra/CI sin delta. git diff --check salida0.

No archivos eliminados ni evidencias regeneradas. Los manifiestos históricos conservan rutas de la estructura original deliberadamente; no son manifiestos de publicación actuales. Las rutas externas /tmp son específicas de ejecución y no garantizan disponibilidad. No se ha vuelto a certificar servicio institucional ni ejecutar pruebas destructivas.

Entrega final solicitada posteriormente: preparar commit y PR con fuentes documentales/runners autorizados, excluyendo AGENTS.md,README-INICIO.md ajenos y dos JSON locales de laboratorio previamente excluidos. Los movimientos permanecen representados en inventario y evidencias originales conservan hashes. Los resultados de publicación se informan por separado, sin inventar número de PR.
