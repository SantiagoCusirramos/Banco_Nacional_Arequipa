# Captación · bloqueos técnicos y decisiones por cerrar

Corte: 22/11/2026, `main` en `7db6fec`. Ninguno impide la demo ni las pruebas de CR-INT-01 y CR-INT-09.

| # | Qué falta | Interfaz | Quién lo atiende | Propuesta | Fecha propuesta |
|---|---|---|---|---|---|
| 1 | **Nombre final de la versión del contrato.** Hoy `version_contrato = CR-INT-01-PROPUESTA-v2`. | CR-INT-01 | Comité (Mathias Cabrera) | Aprobar este documento como versión 2 y cambiar el literal a `CR-INT-01-v2` en ambos lados. | 27/11/2026 |
| 2 | **Contraparte de CR-INT-09.** No hay módulo Clientes aparte (PR #25 cerrado); el dominio de clientes está en COREDB. Falta confirmar el punto R-01. | CR-INT-09 | Comité y coordinación del proyecto | Registrar a COREDB como proveedor de CR-INT-09 y confirmar R-01. | 27/11/2026 |
| 3 | **Estándar común de seguridad.** Captación usa JWT de COREDB, `X-Bus-Token` y token de servicio de SOL; el módulo Seguridad no los emite. | CR-INT-10 | Seguridad y Comité | Definir la credencial común y la rotación de tokens de servicio. | Según agenda del Comité |
| 4 | **Proveedores externos simulados.** RENIEC, listas, PEP, centrales y SMS/correo responden con un simulador determinista; la referencia dice `simulado: true`. | CR-INT-01 / 09 | Captación | Sin contratos con terceros en el curso. Se reemplaza `backend/CAPTACION/proveedores.py` sin cambiar los contratos. | Fuera del alcance del curso |
| 5 | **Prueba en red entre computadoras.** La prueba se hizo con los servicios en un mismo equipo, comunicados por HTTP a través del Bus. | Todas | Infraestructura | Si el Comité lo pide, repetir `evidencias_cr_int.sh` con los servicios en equipos distintos. | A pedido |
| 6 | **Tiempo del Bus (9 s) frente a la habilitación**, que hace varias llamadas seguidas a COREDB. Con COREDB lento podría verse un 504. | CR-INT-09 | Captación | Repetir es seguro: la habilitación no duplica (PR-CAP-09-03). Vigilar en la demo. | — |
| 7 | **Corregir celular o correo** de un solicitante antes de habilitarlo. | — | Captación | Siguiente versión. Hoy se abre otro registro. | Siguiente versión |

Cerrado en esta ronda: **`apellido_materno` vacío.** COREDB lo admite vacío y la versión actual de SOL ya no lo exige; PR-CAP-01-08 lo demuestra (cliente sin segundo apellido, borrador 201).

Observación sin acción: los errores de validación de CAPTACION responden **400 `ERR-VALIDACION-ESQUEMA`** (convención ITIL-02 del proyecto, igual que CUENTAS y TARJETAS), no 422. SOL trata cualquier 4xx de su proveedor como rechazo de contrato, así que no hay incompatibilidad.
