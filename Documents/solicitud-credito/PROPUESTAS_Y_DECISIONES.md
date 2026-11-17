# Propuestas y decisiones del MVP SOL

Fecha: 21 de octubre de 2026.

El usuario confirmó el uso del perfil de demostración para construir el prototipo y que dispone de MySQL. Esta conformidad autoriza la demo académica; no equivale a aprobación institucional del Comité de Créditos.

| Elemento | Implementación de esta entrega | Fuente / justificación | Estado institucional |
|---|---|---|---|
| Canal y actor | Personal de agencia; asesor registra y envía | Alcance SOL y decisión de trabajo de esta demo | Propuesto |
| Producto | Crédito Personal | Producto existente en el seed del repositorio | Pendiente de ratificación |
| Moneda | PEN | Catálogo común; acota el primer recorrido | Propuesto |
| Montos | S/ 1 000–S/ 50 000 | Alcance académico para probar casos y límites. No hay evidencia para declararlo política de riesgo | Pendiente de aprobación |
| Plazo | 6–60 meses | Seed de Crédito Personal | Pendiente de ratificación |
| TEA | 22 % ilustrativa | Seed de Crédito Personal; se guarda como 0.2200 | Pendiente de ratificación |
| Amortización | Francés, Decimal, ajuste final | Fórmula ya presente en CORE | Pendiente de ratificación |
| Fechas | Cada 30 días desde fecha base | Mantiene el criterio del servicio revisado; no equivale a igual día de cada mes | Pendiente de ratificación |
| Interés periódico | `(1+TEA)^(días/360)-1` | Para 30 días equivale a la conversión mensual del CORE. Otras duraciones usan convención comercial explícita de demo | Pendiente de ratificación |
| Cargos | Sin cargos adicionales en el cálculo | Simplifica comprobación inicial; no es una promesa de gratuidad real ni cálculo de TCEA | Propuesto |
| Pago doble | No se calcula | Mecanismo y meses sin definir | Pendiente |
| Garantías | Tipo, descripción y valor declarado | Datos compatibles con el esquema revisado; no se imponen umbrales nuevos | Obligación pendiente |
| Fiadores | Referencias de identidad sintéticas y snapshot | Evita crear desde SOL otro maestro institucional | Validación real pendiente |
| Identidad visual | Azul #15324F, verde petróleo #0F766E, fondo #F8FAFC, grafito #1F2937, acento #B58A3A | Continuidad con mockup, legibilidad, distinción de acciones y estética sobria | Propuesta, no marca oficial |
| Fuente | Geist Sans | Ya configurada en el proyecto | Propuesta |
| Logo | BNA con silueta geométrica del Misti en SVG | Referencia a Arequipa; escalable y monocromático | Propuesta |
| Persistencia | BD local bna_sol_mvp, tablas mvp_sol_* | Aislamiento de laboratorio mientras se decide la autoridad de escritura | Integración definitiva pendiente |
| Identificadores locales | UUID v4 para transacciones del laboratorio | Alineado con el documento de stack. Las referencias de clientes/producto conservan los IDs de ejemplo | Homologación v4/v7 pendiente |

## Cambios fáciles de regularizar

Límites, plazos, monedas del catálogo, tasa y versión se editan en backend/SOL/config/politica_demo.json. El servidor valida el archivo y la interfaz lee sus valores; no hay topes comerciales duplicados en componentes. Cada versión conserva el snapshot de política.

Cambiar producto, fórmula, pago doble, reglas de obligatoriedad de garantías o interpretación de condicionesResultantes requiere implementar y probar ese comportamiento, además de editar un parámetro. La configuración rechaza funciones declaradas pero no soportadas.

## Brechas detectadas en el código base

1. CORE centraliza operaciones y persistencia; el informe asigna propiedad por módulo. No conectar ambas escrituras hasta ratificar la arquitectura.
2. El ENUM SQL de solicitud no admite OBSERVADO/OBSERVADA, aunque el servicio escribe OBSERVADO.
3. SQL permite calendarios por pareja solicitud/versión; el ORM del CORE declara id_solicitud único en el calendario.
4. La solicitud original no congela una versión completa de expediente como exige el informe.
5. El contrato de creación original permite id_caso opcional y el servicio no comprueba habilitación CAP.
6. No existe pago doble en el contrato/table de solicitud revisado.
7. Las referencias de identidad de fiadores requieren homologación con Clientes/Captación.
8. El ZIP no incorpora una implementación del Bus corporativo.
9. El stack documenta UUID v4; el código/seed del CORE utiliza UUID v7.

Esta entrega implementa el recorrido SOL en el laboratorio y conserva el código compartido. La solución definitiva sobre las tablas del CORE debe prepararse con migraciones revisadas por sus responsables.

## Registro para el comité

| Decisión | Responsable de revisar | Evidencia de aprobación | Estado |
|---|---|---|---|
| Producto, límites, tasa y plazo | Créditos y Tecnología en su ámbito | Por completar | Pendiente |
| Calendario y pago doble | Créditos, SOL, EVA y Cobranza | Por completar | Pendiente |
| Fiadores y garantías | Créditos, Evaluación, Clientes y Seguridad | Por completar | Pendiente |
| Propiedad de persistencia | Tecnología, CORE y Créditos | Por completar | Pendiente |
| Estados y contratos | SOL, CAP, EVA, Bus y Tecnología | Por completar | Pendiente |
| Identidad visual común | Tecnología y dirección del proyecto | Por completar | Pendiente |
| Autenticación y auditoría central | Seguridad | Por completar | Pendiente |

Fuentes: ZIP Banco_Nacional_Arequipa-main(1), Documents/01-stack-tecnologico.md, scripts SQL 06/10/13, schemas y servicios CORE; informe SOL de Fase I y consolidado de Créditos compartidos. La presencia en código no acredita aprobación formal.
