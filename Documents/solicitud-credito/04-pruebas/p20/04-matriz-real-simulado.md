> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Registro de ejecución P20. Evidencia válida para aquella ejecución; no certifica disponibilidad actual ni homologación.

# Matriz REAL / SIMULADO / pendiente

Fecha: 2026-11-16 (America/Lima). Rama `feature/sol-integracion-cap-eva`; HEAD `988dc0776da282fbef306632fc86426b6e372376`. CAP `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; EVA `57b0e2a34fd55fb96fd6245acc06a86536d220f8`. Sin merge, cherry-pick, cambio de rama, commit ni push.

| Componente / operación | Clasificación | Evidencia / límite |
|---|---|---|
| COREDB original y MySQL integrado | REAL Y PROBADO POR HTTP |CAP alta/consulta, JWT y código generado. No API evaluación inventada. |
| CAP FastAPI original | REAL Y PROBADO POR HTTP |Registro/caso/consentimientos/habilitación y CR01; MySQL CAP propia. |
| Verificaciones RENIEC/listas/PEP/central/SMS CAP | SIMULADO EXPLÍCITAMENTE |Proveedores externos no disponibles/homologados; referencia declara simulado:true. Se conserva lógica original, no se finge integración nacional. |
| SOL consulta CAP | REAL Y PROBADO POR HTTP |Adaptador REAL, detalle fresco, inexistente/vencida/revocada rechazadas. |
| SOL registro/preview/versiones/garantía | REAL Y PROBADO POR HTTP |MySQL SOL, Decimal y snapshots; sin fiadores/pago doble. |
| SOL envío EVA | REAL Y PROBADO POR HTTP |Reserva durable202, GET+POST a EVA original, acuse y operación única. |
| EVA persistencia y analista | REAL Y PROBADO POR HTTP |BD EVA y JWT persona COREDB; decisión real por API. |
| Regla financiera EVA | REAL E IMPLEMENTADO |Se ejecuta motor original Decimal; política académica provisional, no homologada. |
| EVA retorno SOL | REAL Y PROBADO POR HTTP |Worker real, callback autenticado, acuse semántico y Outcome único. |
| Parche EVA en copia exportada | REAL Y PROBADO POR HTTP |Camino feliz real; rechazos de acuse complementados por tests unitarios/TCP. No se modificó rama del otro equipo. |
| Historial/outbox locales SOL | REAL Y PROBADO POR HTTP |Transacciones originales y comprobación SQL; no se eliminan controles. |
| Auditoría institucional | SIMULADO EXPLÍCITAMENTE |Receptor académico existente en overlay y gate explícito. Entrega transporte no es homologación institucional. |
| Next.js SOL | REAL Y PROBADO POR HTTP |Proxy servidor hacia /sol, cookie HttpOnly, política REAL y bandeja. No UI CAP/EVA en HEAD: usar Swagger. |
| Bus corporativo | NO IMPLEMENTADO |No se crea. /gateway/sol permanece solo para modo SIMULADO original. |
| Fiadores institucionales RF008 | BLOQUEADO |Contrato no homologado; REAL rechaza. No se fuerza para demo. |
| Pago doble RF005 | BLOQUEADO |Regla/acta pendiente; no basta booleano. |
| TLS/SSO/MFA/auditoría homologada | BLOQUEADO |Fuera del laboratorio académico loopback; no se declara producción lista. |
| Desembolso y cobranza | NO IMPLEMENTADO |Fuera del escenario SOL; ningún desembolso ejecutado. |
| Durabilidad ante pérdida de MySQL tmpfs | NO IMPLEMENTADO |Datos efímeros deliberados; reinicio de API sí recupera operación, parar MySQL pierde fixtures. |
| HA/carga institucional/red remota | IMPLEMENTADO SIN PRUEBA |Reservas/bloqueos existen; no se acredita operación institucional ni pruebas de carga. |

REAL de transporte no significa cliente institucional, política aprobada ni riesgo certificado. Las únicas simulaciones del recorrido son verificadores externos de CAP y auditoría académica. Los dobles/servidores de fallos de las suites son pruebas complementarias identificadas y no se cuentan como circuito bancario real.
