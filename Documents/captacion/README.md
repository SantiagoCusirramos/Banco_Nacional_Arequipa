# Captación de Clientes · entrega al Comité de Créditos

Respuesta a la *Guía práctica de integración de APIs* (Comité de Créditos, 22/11/2026). Corte:
**22/11/2026**, `main` en `7db6fec`. Líder: Sebastián Chávez. Enlace del Comité: Piero Ponce.

## Resumen

| Interfaz | Con quién | Estado | Prueba |
|---|---|---|---|
| **CR-INT-09** | COREDB (dominio Clientes) | **Demostrado**: alta, reutilización y lectura del `cod_cliente` entre servicios reales | 6 de 6 PASAN · acta PR-CAP-001 |
| **CR-INT-01** | SOL | **Demostrado**: SOL, con su adaptador real, busca y usa al cliente habilitado; rechaza al revocado | 9 de 9 PASAN · acta PR-CAP-002 |
| **CR-INT-10** | Seguridad | **Demostrado** en Captación (401, 403, Bus, bitácora). **Pendiente** el estándar común | 4 de 4 PASAN · acta PR-CAP-003 |
| Proveedores externos (RENIEC, listas, PEP, centrales, SMS) | Terceros | **Simulado** (la referencia lo declara con `simulado: true`) | — |

«Demostrado» en el sentido de la guía: dos módulos ejecutándose, petición y respuesta reales por el
Bus, resultado guardado en la base integrada y evidencia reproducible.

## Contenido

| Archivo | Qué es |
|---|---|
| [`CR-INT-09.md`](CR-INT-09.md) | Contrato CAPTACION ↔ Clientes (identificador maestro) |
| [`CR-INT-01.md`](CR-INT-01.md) | Contrato CAPTACION → SOL (cliente habilitado) |
| [`CR-INT-10.md`](CR-INT-10.md) | Controles de seguridad de Captación |
| [`bloqueos-y-decisiones.md`](bloqueos-y-decisiones.md) | Qué falta, quién lo atiende y fecha propuesta |
| [`evidencias/evidencias-2026-11-22.json`](evidencias/evidencias-2026-11-22.json) | Los 19 casos: petición, HTTP, respuesta, X-Correlation-ID y resultado |
| [`evidencias/persistencia-mysql-2026-11-22.txt`](evidencias/persistencia-mysql-2026-11-22.txt) | Consulta de solo lectura en MySQL del cliente creado |
| [`evidencias/resumen-corrida-2026-11-22.txt`](evidencias/resumen-corrida-2026-11-22.txt) | Salida de la corrida (19 de 19) |
| `actas/` | Actas de prueba PR-CAP-001 a 003 y ficha de cierre del módulo (plantillas del Comité) |

Las evidencias usan datos ficticios creados en la corrida; documentos y contactos van enmascarados
y no hay tokens, claves ni contenido de `.env`.

## Cómo repetir la prueba

```bash
./bna up
backend/CAPTACION/scripts/evidencias_cr_int.sh
```

El script corre en el contenedor del Bus (como `./bna smoke`), llega a CAPTACION, SOL y COREDB solo
por el Bus y deja un JSON nuevo en `Documents/captacion/evidencias/`. Termina con código distinto de
cero si algún caso falla. Además, la suite del módulo: `backend/CAPTACION/scripts/pruebas_integracion.sh`.

Ambiente de la corrida del 22/11/2026: los servicios de `main` (Bus, COREDB, CAPTACION, SOL y
Evaluación) como procesos en un mismo equipo Linux, comunicados por HTTP a través del Bus, con la
base integrada en MySQL 8.0 cargada con los scripts de `database/` (las imágenes de Docker no
pudieron descargarse en ese equipo). La suite del módulo dio 43 pruebas aprobadas contra ese COREDB.
