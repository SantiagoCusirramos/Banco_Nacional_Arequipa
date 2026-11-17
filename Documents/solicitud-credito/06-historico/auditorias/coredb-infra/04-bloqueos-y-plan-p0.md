> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# 04 — Bloqueos y plan priorizado

Fecha: 2026-11-16 (America/Lima). Rama analizada: `feature/sol-integracion-cap-eva`. HEAD: `988dc0776da282fbef306632fc86426b6e372376`. Auditoría estática, sin arranque, SQL, migraciones, cambios de rama ni consultas remotas. Las referencias `origin/*` son copias locales; su nombre no acredita el estado actual de un PR.

## Respuestas a las diez preguntas

| Pregunta | Clasificación | Conclusión verificable |
|---|---|---|
| 1 COREDB tiene APIs para CAP | SÍ, PERO NO PROBADO EN EJECUCIÓN | Alta, consulta, documento, validaciones y estado. No reemplaza expediente/CR01 de CAP. |
| 2 COREDB tiene APIs para EVA | NO | Hay tablas crediticias y catálogo productos, no recepción/decisión/consulta CR02/03. EVA ref ya implementa sus propias APIs. |
| 3 CAP está conectado correctamente a COREDB | SÍ, PERO NO PROBADO EN EJECUCIÓN | Código de ref CAP usa cliente HTTP, JWT servicio CLIENTES y rutas reales. En HEAD CAP no está incorporado. |
| 4 EVA está conectado correctamente a COREDB | PARCIAL | Ref EVA valida sesiones por /coredb/auth/me; persiste expedientes en BD EVA propia, no por API COREDB. HTTP nuevo no ensayado. |
| 5 SOL puede consultar realmente CAP | SÍ, PERO NO PROBADO EN EJECUCIÓN | Adaptador y CR01 ref compatibles; faltan composición activa y configuración REAL completa. |
| 6 SOL puede enviar realmente EVA | SÍ, PERO NO PROBADO EN EJECUCIÓN | Adaptador/worker y receptor CR02 existen en fuentes separadas; sin E2E nuevo. |
| 7 EVA puede devolver resultados SOL | PARCIAL | Callback, auth y outbox existen; URL retorno vacía por defecto y acuse EVA validado solo por 2xx. |
| 8 Dependencia Seguridad/Auditoría | PARCIAL | JWT personal COREDB; auth local SOL; auditoría externa requerida al validar REAL, entrega asíncrona independiente. |
| 9 Puede completarse sin auditoría institucional tal como está | NO | Base REAL no arranca con auditoría vacía. Sí hay alternativa de laboratorio con simulador existente y gate, todavía sin activar ni homologar. |
| 10 Conjunto mínimo disponible | PARCIAL | Reutilizar fuentes CAP/EVA, laboratorio aislado, configurar tokens/retorno/auditoría académica y ejecutar prueba conjunta; no necesita un nuevo servicio bancario ni APIs crediticias COREDB. |

## Bloqueos concretos

1. CAP/EVA están en refs locales, fuera de HEAD/Compose principal. Su existencia en Git no los arranca. No está autorizado integrarlos en este turno.
2. `prepare.py:123–137` deja SOL_AUDIT_* vacío mientras SOL está REAL; Settings.validate falla. Overlay existente evita ese fallo configurando un simulador explícito, no desactivando controles.
3. `prepare.py:137` deja EVALUACION_SOL_URL vacía: DespachadorResultados.configurado=False y los resultados permanecen PENDIENTE. Tener token callback no basta.
4. Datos de CAP provienen de proveedores simulados (`simulado:true`). HTTP real no homologa identidad ni habilitación institucional; demostrar únicamente cliente sintético.
5. Fiadores REAL sin contrato y pago doble condicionado son límites funcionales vigentes. No incluirlos como requisito del expediente mínimo ni activarlos artificialmente.
6. Evidencia actual no acredita TCP conjunto, callbacks, reintentos ni persistencia conjunta. Los reportes anteriores separan pruebas locales y HTTP independientes; no elevan el estado a integrado_real.
7. EVA puede marcar resultado ENTREGADO con cualquier 2xx; necesita validar semántica del acuse para afirmar entrega robusta. Reintenta409 hasta20 conflictos; no todos los409 son transitorios, revisar tratamiento permanente.

## P0 — Imprescindible

Propuestas solamente; ningún archivo indicado se modificó.

| Tarea / componente | Modificación propuesta o reutilización | Dependencias | Prueba de aceptación | Riesgo |
|---|---|---|---|---|
| P0-01 fuentes/dependencias; laboratorio/prepare.py | Reutilizar exportación de SHA fijados CAP/EVA y SOL actual fuera de Git; no fusionar por nombre de PR. Revisar pin y requisitos antes de preparar | refs locales exactas, Docker, imágenes | manifiesto hashes y arranque aislado de APIs con sus bases; sin hostnames institucionales | cambios posteriores de ref, permisos init; cero BD compartida |
| P0-02 configuración privada laboratorio | Usar URLs DNS y tokens pareados de matriz03; conservar secretos fuera del repo. Habilitar solo DDL del proyecto efímero en etapa autorizada | esquemas propios, usuarios mínimos, tmpfs | health/ready y auth negativo401/403 sin revelar secreto | confundir puertos host con internos; perder tmpfs al parar MySQL |
| P0-03 laboratorio/compose.audit-sim.yaml y entorno | Reutilizar overlay existente con gate académico explícito; no nuevo servicio de dominio ni cambio de Seguridad | autorización futura de ejecución; auditoría simulada rotulada | SOL REAL arranca; evento queda local y acuse solo del simulador; no se atribuye confirmación institucional | etiqueta CONFIRMADO de transporte no debe presentarse como homologación CR10 |
| P0-04 entorno EVA de laboratorio | Configurar EVALUACION_SOL_URL=http://sol:8011 y callback token pareado; mantener token de recepción distinto | SOL REAL y callback accesible | resultado pendiente pasa a entregado y solicitud SOL al estado esperado con mismo idEvaluacion/ronda | callback antes de acuse409; URL incorrecta fuga de token |
| P0-05 runner/evidencia en Documents/solicitud-credito/laboratorio | Extender runner existente con CAP sintético completo → referencia HTTP → solicitud SOL sin fiadores/pago doble → envío worker → analista EVA → resultado SOL. Usar datos financieros sintéticos coherentes y sesión permitida, no resultado.demo | P0-01..04 y reglas académicas existentes | IDs coincidentes, acuse real EVA, Outcome único y estado final por HTTP, SQL de lectura en esquemas propios y eventos correlacionados | asumir202=acuse o confundir callbacks con resultado simulado |
| P0-06 ref EVA envios.py:_entregar | Validar JSON recibido:true e idOperacion correspondiente antes de ENTREGADO; coordinar cambio con equipo EVA | contrato de respuesta SOL; no tocar COREDB | casos200 correcto,200 recibido:false/ID distinto/JSON inválido; solo correcto termina entregado | pérdida de eventos por falso éxito; para demo actual verificar recepción también en SOL |

Para una demostración supervisada del camino feliz P0-06 puede mitigarse comprobando explícitamente Outcome/estado SOL y documentando el defecto; para afirmar entrega fiable es imprescindible corregirlo. No se necesita crear nuevas APIs COREDB, usar CORE legado ni copiar solicitudes a creditos.*. Si se prohíbe todo simulador de auditoría, sustituir P0-03 por propuesta de modo local explícito en SOL, con revisión y tests: hoy no existe, no se trata como configuración ya disponible.

## P1 — Importante

| Tarea / componente | Cambio propuesto | Dependencias | Prueba demostrativa | Riesgo |
|---|---|---|---|---|
| P1-01 SOL integrations/operations + pruebas HTTP | Ensayar timeout/acuse perdido, recuperación de lease y reinicio con misma operación; cambiar solo si prueba detecta fallo | laboratorio P0 | GET encuentra recepción y evita segundo expediente; versión congelada única | duplicación, estados divergentes |
| P1-02 EVA envios/servicio y SOL callback | Ensayar duplicado idéntico/distinto, versión vieja, ronda errónea, callback anticipado y409 permanente frente a transitorio | acuses pareados | un Outcome/evento; rechazo esperado; recuperación sin nueva operación | conflicto permanente reenviado20 veces |
| P1-03 CAP servicios/core_client | Revisar recuperación parcial de habilitación, duplicados de validación, cliente bloqueado/revocado/vencido y búsqueda con snapshot viejo | COREDB sintético | detalle fresco impide crear/enviar; caída COREDB da503 | altas parciales, búsquedas desactualizadas |
| P1-04 runner y despliegue laboratorio | Robustez multiworker/MySQL, conservación tras reinicio solo APIs y privacidad de logs | no reiniciar MySQL tmpfs para prueba de persistencia | mismos IDs/estados, sin tokens/PII en logs, roles negativos | confundir reinicio API con durabilidad de BD tmpfs |
| P1-05 contratos/OpenAPI | Comparar DTO de SHA fijos, extras/nulos/fechas/Decimal y tres decisiones reales de EVA | dependencias puras aisladas | tests positivos/negativos más captura HTTP completa | TestClient no demuestra red real |

## P2 — Pendiente de homologación

| Componente | Propuesta | Dependencia | Evidencia futura | Riesgo |
|---|---|---|---|---|
| Seguridad CR-INT-10 / SSO | Homologar receptor, acuse/deduplicación, roles, TLS, revocación/retención y observabilidad | equipo Seguridad/Infra y contrato aprobado | eventos recibidos una vez lógicamente y revocación efectiva | laboratorio no equivale a control central |
| CAP identidad y fiadores RF001/008 | Sustituir verificadores simulados por proveedores acordados y contrato separado fiador | equipos CAP/identidad y aprobación | referencia vigente institucional verificable sin PII excesiva | falso habilitado, tratamiento de datos |
| Política RF005 y reglas financieras | Acta para pago doble, montos/plazos/TEA/moneda y decisiones de evaluación | comité, DA-SOL aplicables | política versionada y regresiones de cálculo | no ampliar reglas académicas por capacidad del DTO |
| COREDB modelo integrado / despliegue común | Decidir fuente de verdad de expedientes/evaluaciones si se exige consolidación institucional; evitar doble escritura | COREDB/CAP/EVA/SOL y contratos de persistencia | coherencia/inmutabilidad y reconciliación | tablas existentes no autorizan writes directos |

## Comandos y prerrequisitos pendientes

No ejecutar `./bna test`, `./bna smoke` ni scripts de integración de EVA sobre entorno compartido. Para futuras pruebas puras preparar venv externo con requisitos verificados y ejecutar los comandos indicados en01 sin caches. Para HTTP conjunto preparar laboratorio mediante su README, revisar manifiesto, cerrar gates por defecto, autorizar expresamente inicialización efímera/overlay y configurar retorno EVA. Evitar `down -v`, reset, migraciones globales y credenciales reales. No se entrega un comando up automático como si su autorización ya existiera.

Trazabilidad: CR-INT-01 (referencias),02 (expediente/acuse),03 (resultado),10 (eventos); RF-SOL-001,002–004,006–010 según alcance; RF005/008 conservan bloqueos. Ninguna decisión institucional pendiente queda completada por esta auditoría.

Siguiente prompt recomendado: «Preparar y ejecutar, con autorización explícita para DDL efímero y auditoría simulada del laboratorio existente, un expediente sintético CAP→SOL→EVA→SOL; fijar SHA, activar retorno EVA y comprobar acuses/duplicados por HTTP, sin modificar Seguridad ni las bases compartidas». Si se desea cero simulador, solicitar antes diseño e implementación revisada de auditoría local independiente de CAP/EVA REAL.
