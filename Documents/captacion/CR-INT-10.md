# CR-INT-10 · Seguridad (parte de Captación)

CR-INT-10 es transversal (todos los módulos → Seguridad). Aquí se registra lo que Captación ya
cumple y demuestra, para que el Comité lo compare con el estándar común que se acuerde.

| Campo | Contenido |
|---|---|
| **CR-INT / objetivo** | Autenticación, autorización por rol y auditoría de cada operación de Captación. |
| **Equipos responsables** | Captación de Clientes (enlace Piero Ponce); Seguridad; Comité (Mathias Cabrera) para el estándar común. |
| **Versión comprobable** | `main` en `7db6fec` (22/11/2026). `backend/CAPTACION/dependencies.py`, `BUS_SERVICIOS/`, `COREDB/permisos.py`, `COREDB/routers/auditoria.py`. |
| **Ruta y método** | Todas las rutas de CAPTACION por `/bus/captacion/...`; bitácora en `GET /bus/coredb/coredb/auditoria` (permiso `VER_AUDITORIA`). |
| **Autenticación / errores** | Tres credenciales, ninguna en el repositorio: (1) **JWT de COREDB** de la persona (asesor o administrador); (2) **`X-Bus-Token`** por módulo ante el Bus; (3) **token de servicio de SOL** solo para CR-INT-01. Errores: 401 sin credencial o inválida; 403 rol sin permiso. |
| **Estado real** | **Implementado y probado** en Captación. **Pendiente**: estándar común con el módulo Seguridad (hoy Seguridad no emite las credenciales de Captación). |
| **Prueba y evidencia** | 22/11/2026: PR-CAP-10-01 a 10-04, todos PASAN. Además PR-CAP-01-07 (referencias solo con el token de SOL). Acta PR-CAP-003. |
| **Decisiones por cerrar** | Qué credencial común adopta la Línea de Créditos (JWT de COREDB, emitido por Seguridad u otro) y la rotación de los tokens de servicio. |

## Controles demostrados

| Control | Cómo | Evidencia |
|---|---|---|
| Autenticación | Sin token o con token inválido → 401 | PR-CAP-10-01 |
| Autorización por rol | ANALISTA (sin `CREAR_CLIENTE`) no registra ni habilita → 403. Leer exige `VER_CLIENTE`; trabajar un caso, `CREAR_CLIENTE` (ASESOR, ADMINISTRADOR) | PR-CAP-10-02 |
| Puerta del Bus | Sin `X-Bus-Token` o con uno desconocido → 401 | PR-CAP-10-03 |
| Bitácora | Cada paso queda en COREDB a nombre del asesor, con `correlation_id` y sin datos personales | PR-CAP-10-04 |
| Servicio a servicio | `/cap/references/*` solo con el token de SOL; un JWT de persona → 401 | PR-CAP-01-07 |
| OTP | CAPTACION calcula el HMAC con `CAP_OTP_CLAVE`; COREDB guarda solo el HMAC. SMS 5 min, correo 10 min, 3 intentos | Pruebas de la suite |
| Datos sensibles | Búsquedas por documento en el cuerpo (no en la URL); la referencia no lleva celular ni correo | PR-CAP-01-01 |
