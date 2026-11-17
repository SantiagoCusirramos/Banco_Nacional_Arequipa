> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Registro de ejecución P20. Evidencia válida para aquella ejecución; no certifica disponibilidad actual ni homologación.

# Resumen final de integración

Fecha: 2026-11-16 (America/Lima). Rama `feature/sol-integracion-cap-eva`; HEAD `988dc0776da282fbef306632fc86426b6e372376`. CAP `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; EVA `57b0e2a34fd55fb96fd6245acc06a86536d220f8`. Sin merge, cherry-pick, cambio de rama, commit ni push.

| Pregunta | Respuesta basada en ejecución |
|---|---|
| CAP conectado a COREDB | SÍ. Alta/consulta/habilitación por APIs originales con JWT y código generado. |
| SOL conectado a CAP | SÍ. Referencias consultadas por HTTP REAL; detalle revalidado y negativos vencida/revocada/inexistente rechazados. |
| SOL conectado a EVA | SÍ. Reserva202, recepción/acuse por HTTP y expediente único en MySQL EVA. |
| EVA devuelve resultados a SOL | SÍ. Decisión de analista, outbox, worker y callback real; acuse semántico validado y resultado único SQL. |
| Persistencia real | COREDB integrado, CAP, SOL y EVA usan MySQL8.4. Bases/usuarios separados; laboratorio efímero. |
| Simulaciones | Solo verificadores externos originales de CAP y receptor de auditoría académica, por dependencias institucionales pendientes. |
| Pruebas completas |APROBADA, OBSERVADA→v2→APROBADA y RECHAZADA;150 checks principales+2 caída/recuperación, además de suites aisladas. |
| Pendientes |Homologación institucional, TLS/SSO, fiadores RF008, pago doble RF005, política aprobada, durabilidad/operación productiva. |
| Bloqueos resueltos |Fuentes CAP/EVA exportadas, composición aislada, auditoría académica explícita, callback configurado, parche de acuse EVA y receta reproducible. |
| Flujo de extremo a extremo funcional |**SÍ, en laboratorio académico con transporte HTTP real y persistencia MySQL verificada.** No equivale a integración institucional homologada. |

SOL219, COREDB57, CAP35 más4 de contrato en imagen SOL, EVA65 y frontend114/2 expected fail se ejecutaron en esta tarea. Las pruebas unitarias/mocks son complementarias y se distinguen del recorrido TCP real. La matriz y el informe de evidencias detallan límites y fallos depurados.

Comando: `python3 Documents/solicitud-credito/laboratorio/demo_integracion.py`. Guía: [05-guia-demostracion.md](05-guia-demostracion.md). No commits/push, cambios de rama, escrituras institucionales ni modificaciones de módulos compartidos.

Reproducción limpia final aprobada, con150+2 checks y complementos403/422/503. MySQL COREDB confirmado por SQL (2 clientes sintéticos), cuatro APIs y Next.js en ejecución. Infraestructura estática9 negativos y acuse7 testsTCP (más9 unitarios) aprobados. Los Swagger activos están en18130–18133 y Next en18134; usar --state de la instancia limpia según la guía.
