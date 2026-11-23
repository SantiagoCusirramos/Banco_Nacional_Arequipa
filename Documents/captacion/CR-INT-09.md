# CR-INT-09 · CAPTACION ↔ Clientes: identificador maestro del cliente

Contrato con la plantilla de la *Guía práctica de integración de APIs* del Comité de Créditos (22/11/2026).

> **Quién es «Clientes» en `main`.** No hay un módulo Clientes aparte: su PR (#25) se cerró sin
> fusionar el 17/11/2026 y el dominio de clientes vive en la base integrada, detrás de **COREDB**
> (`backend/COREDB/CONTRATO_CLIENTES.md`). Por eso la contraparte de CR-INT-09 es la API de
> clientes de COREDB. Si el Comité designa otro responsable, el contrato no cambia de forma.

| Campo | Contenido |
|---|---|
| **CR-INT / objetivo** | CR-INT-09. Validar si una persona ya es cliente y, al habilitarla, darle de alta (o reutilizar su cliente activo) con **un solo identificador maestro**, `cod_cliente`, que generan COREDB y la base. Ningún otro módulo crea clientes (punto R-01). |
| **Equipos responsables** | Consumidor: Captación de Clientes (enlace Piero Ponce). Proveedor: COREDB / dominio Clientes de la base integrada (coordinación del proyecto). |
| **Versión comprobable** | `main` en `7db6fec` (22/11/2026). CAPTACION: `backend/CAPTACION/core_client.py`, `services/captacion.py`. COREDB: `routers/clientes.py`, `routers/captacion.py`. Base integrada `bd-v1.7+` (`clientes.*_captacion`). |
| **Ruta y método** | Por el Bus, `http://bus:8018/bus/coredb` (ver tabla). COREDB escucha en `:8012`. |
| **JSON** | Ver abajo. |
| **Autenticación / errores** | Lecturas y pasos del expediente: **JWT de COREDB del asesor** (permisos `VER_CLIENTE` y `CREAR_CLIENTE`). Alta del cliente y vínculo con el caso: **usuario de servicio `svc-captacion`** (rol SERVICIO, módulo CLIENTES), creado por `coredb-init` con `CAPTACION_COREDB_SECRETO`. Siempre con `X-Bus-Token` de CAPTACION. |
| **Estado real** | **Implementado y probado entre servicios reales** (CAPTACION → Bus → COREDB → MySQL). |
| **Prueba y evidencia** | 22/11/2026: 6 casos PR-CAP-09-01 a 09-06, todos PASAN, más la consulta de solo lectura en MySQL. Evidencia: [`evidencias/`](evidencias/). Acta PR-CAP-001. |
| **Decisiones por cerrar** | Confirmar el punto R-01 (solo el usuario de servicio del módulo CLIENTES crea clientes HABILITADOS) y que el Comité registre a COREDB como contraparte de CR-INT-09. |

## Llamadas

| Paso | Método y ruta en COREDB | Credencial | Resultado |
|---|---|---|---|
| ¿Ya es cliente? | `POST /coredb/clientes/validaciones/documento` | `svc-captacion` | Cliente existente o ninguno |
| Alta | `POST /coredb/clientes` | `svc-captacion` | `201` con `cod_cliente` (`CLI` + 9 dígitos), `ACTIVO`, `HABILITADO` |
| Vínculo | `POST /coredb/captacion/casos/{id}/cliente` | `svc-captacion` | El caso queda ligado al `cod_cliente` |
| Habilitación | `POST /coredb/captacion/casos/{id}/habilitacion` (`{"vigencia_dias": 30}`) | JWT del asesor | Caso `HABILITADO`, `fecha_verificacion`, `vigente_hasta` |
| Lectura | `GET /coredb/clientes/{cod_cliente}` | JWT del asesor o `svc-captacion` | Identidad, estado y `id_verificacion_captacion` |

Lo que CAPTACION expone al asesor: `POST /api/v1/captacion/casos/{id}/habilitar` → `200`.

```json
{
  "id_caso": "d7156af4-927c-4344-afab-e8875be505fc",
  "estado": "HABILITADO",
  "cod_cliente": "CLI000000004",
  "cliente_nuevo": true,
  "id_verificacion_captacion": "ed74334a-c7ba-4845-adfa-72e7ed19b0ba",
  "fecha_verificacion": "2026-11-22",
  "vigente_hasta": "2026-12-22"
}
```

## Reglas

- **Un documento, un cliente.** Si el documento ya es cliente activo, se reutiliza su `cod_cliente` (`cliente_nuevo: false`).
- **Repetir es seguro.** Volver a habilitar el mismo caso devuelve el mismo `cod_cliente` y no crea otro (PR-CAP-09-03). Registrar otra vez al mismo solicitante devuelve `200` con `duplicado: true` (PR-CAP-09-04).
- **Sin requisitos no hay cliente.** Habilitar sin consentimientos, OTP, validaciones y perfil responde `400 ERR-CAP-CASO-NO-LISTO` con la lista de faltantes (PR-CAP-09-05). Lista restrictiva o riesgo `MUY_ALTO`: caso `RECHAZADO` (PR-CAP-09-06).
- **Sin acceso directo a la base.** CAPTACION no tiene base propia; todo pasa por COREDB a través del Bus.

## Errores

| HTTP | Cuándo |
|---|---|
| 400 `ERR-CAP-CASO-NO-LISTO` | Faltan requisitos para habilitar |
| 400 `ERR-VALIDACION-ESQUEMA` | Cuerpo inválido |
| 401 | Sin token o token inválido |
| 403 | El rol no tiene `CREAR_CLIENTE` (p. ej. ANALISTA) |
| 404 | Caso o cliente inexistente |
| 409 `ERR-CAP-CASO-ABIERTO` | El solicitante ya tiene un caso abierto |
| 503 | COREDB no disponible |
