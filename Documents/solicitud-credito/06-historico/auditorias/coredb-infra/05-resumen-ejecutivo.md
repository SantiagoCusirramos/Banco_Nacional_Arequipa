> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# 05 — Resumen ejecutivo

Fecha: 2026-11-16 (America/Lima). Rama analizada: `feature/sol-integracion-cap-eva`. HEAD: `988dc0776da282fbef306632fc86426b6e372376`. Auditoría estática, sin arranque, SQL, migraciones, cambios de rama ni consultas remotas. Las referencias `origin/*` son copias locales; su nombre no acredita el estado actual de un PR.

**COREDB no contiene todas las APIs necesarias para el circuito CAP → SOL → EVA.** Sí tiene las de clientes y verificaciones que utiliza CAP. No expone recepción de expedientes, evaluación, decisiones ni retorno a SOL; esas operaciones ya están implementadas en el módulo EVA de una referencia Git local separada.

**No se puede ejecutar el circuito completo con la configuración actual sin ajustes.** Sí existe una base para demostrarlo sin desarrollar nuevos servicios bancarios: reutilizar CAP de `origin/pr-cap-74`, EVA de `origin/pr-eva-70`, SOL actual y el laboratorio aislado existente. Esto requiere composición/configuración y una prueba conjunta pendiente; no equivale a integración institucional aprobada.

Los bloqueos inmediatos son CAP/EVA ausentes del árbol y Compose principal, configuración de auditoría vacía que impide arrancar SOL REAL, y EVALUACION_SOL_URL vacía que impide el retorno. No hay una espera de confirmación de auditoría central que condicione cada envío: SOL conserva eventos y outbox independientes. El laboratorio ya prevé un simulador de auditoría opcional con gate explícito; permite evitar la dependencia institucional en la futura demo sin eliminar controles. Si se exige no ejecutar ningún proceso de auditoría, el modo REAL con auditoría exclusivamente local requeriría un cambio de SOL aún no implementado.

El transporte HTTP CAP/EVA es compatible por inspección, pero CAP rotula verificaciones simuladas. EVA usa COREDB para validar usuarios, mientras persiste evaluaciones en su propia MySQL. No debe conectarse SOL a tablas COREDB ni usar endpoints CORE legado como sustituto de EVA. El despachador de resultados EVA acepta cualquier2xx como entrega; debe validar el acuse o, en una demo supervisada, comprobar también la recepción efectiva en SOL y declarar esa limitación.

No se inició ningún servicio ni se ejecutó SQL. Comprobación nueva: sintaxis AST correcta en108 fuentes (salida0). Suites bancarias no ejecutadas: Python sin pytest, venv histórico ausente y fixtures de integración que alteran bases. Los tests y antecedentes HTTP documentados previamente no se presentan como E2E nuevo. Estado: **listo para preparar integración académica con limitaciones; no integrado_real**.

Solo se crean los cinco informes autorizados; cambios previos preservados. No hay commit/push ni modificación de código, configuración, changelog o BD. Esta excepción documental sigue la autorización específica de esta tarea.

- [Inventario de infraestructura y Git](01-inventario-infraestructura.md).
- [Matriz de APIs COREDB y límites](02-apis-coredb.md).
- [Compatibilidad, tokens y recorrido completo](03-matriz-integracion-cap-sol-eva.md).
- [Diez respuestas y plan P0/P1/P2](04-bloqueos-y-plan-p0.md).

Decisión recomendada: reutilizar el laboratorio y sus fuentes fijadas, autorizar en otra fase el arranque efímero con auditoría académica explícita, configurar callback y demostrar un expediente completo por HTTP. Reservar homologación institucional, fiadores y política financiera para sus contratos/actas; no reescribir APIs que CAP/EVA ya contienen.
