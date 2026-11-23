# CR-INT-01 · CAPTACION → SOL: cliente habilitado

Contrato con la plantilla de la *Guía práctica de integración de APIs* del Comité de Créditos (22/11/2026).

| Campo | Contenido |
|---|---|
| **CR-INT / objetivo** | CR-INT-01. SOL obtiene de CAPTACION la referencia de un cliente **habilitado** antes de armar, guardar, editar o enviar una solicitud. Modalidad acordada: **consulta** (SOL pregunta; CAPTACION no envía). |
| **Equipos responsables** | Proveedor: Captación de Clientes (líder Sebastián Chávez; enlace del Comité Piero Ponce). Consumidor: Solicitud de Crédito (enlace del Comité Ángel Cruz). |
| **Versión comprobable** | `main` en `7db6fec` (22/11/2026). Proveedor: `backend/CAPTACION/routers/referencias.py` y `services/captacion.py` (`_referencia`). Consumidor: `backend/SOL/integrations.py` (`CAP_SEARCH_PATH`, `CAP_REFERENCE_PATH`, `CLIENT_FIELDS`). |
| **Ruta y método** | Por el Bus: `POST /bus/captacion/cap/references/search` y `GET /bus/captacion/cap/references/{idCliente}`. En Docker, SOL usa `http://bus:8018/bus`; desde la máquina, `http://127.0.0.1:8018/bus/captacion/...`. CAPTACION escucha en `:8017` (Swagger en `/docs`). |
| **JSON** | Ver abajo. |
| **Autenticación / errores** | `Authorization: Bearer <CAP_SOL_TOKEN>` (token de servicio de SOL, ≥ 32 caracteres, se entrega por `.env`, nunca por chat) y `X-Bus-Token` de SOL ante el Bus. Errores en la tabla de abajo. |
| **Estado real** | **Implementado y probado entre servicios reales** (CAPTACION, SOL, Bus y COREDB corriendo; SOL con su adaptador real, sin simulador). Los proveedores externos de Captación (RENIEC, centrales, SMS) siguen **simulados** y la referencia lo declara con `simulado: true`. |
| **Prueba y evidencia** | 22/11/2026: 9 casos PR-CAP-01-01 a 01-09, todos PASAN. Evidencia: [`evidencias/evidencias-2026-11-22.json`](evidencias/evidencias-2026-11-22.json). Acta PR-CAP-002. |
| **Decisiones por cerrar** | Fijar el nombre final de `version_contrato` (hoy `CR-INT-01-PROPUESTA-v2`). Ver [bloqueos y decisiones](bloqueos-y-decisiones.md). |

## Búsqueda

`POST /cap/references/search` — el texto va en el **cuerpo** (un documento no debe quedar en la URL ni en los registros del Bus).

```json
{ "search": "4XXXXXX1", "limit": 50 }
```

- `search`: 0 a 100 caracteres (documento, nombre o apellido). Vacío lista las referencias más recientes.
- `limit`: 1 a 50.
- Respuesta 200: **lista directa** (sin sobre) de 0 a 50 referencias. Puede incluir clientes `REVOCADO`: aparecer en la lista **no** habilita; SOL vuelve a pedir la referencia individual antes de guardar y antes de enviar.

## Referencia individual

`GET /cap/references/{idCliente}` — `idCliente` es el `cod_cliente` de COREDB (`CLI` + 9 dígitos).

```json
{
  "id_cliente": "CLI000000004",
  "cod_tipo_documento": "DNI",
  "numero_documento": "4XXXXXX1",
  "nombres": "Rosa",
  "apellido_paterno": "Huamán",
  "apellido_materno": "Ccori",
  "estado_cliente": "ACTIVO",
  "id_caso": "d7156af4-927c-4344-afab-e8875be505fc",
  "id_verificacion": "ed74334a-c7ba-4845-adfa-72e7ed19b0ba",
  "fecha_verificacion": "2026-11-22",
  "vigente_hasta": "2026-12-22",
  "estado_habilitante": "HABILITADO",
  "version_contrato": "CR-INT-01-PROPUESTA-v2",
  "simulado": true
}
```

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `id_cliente` | texto ≤ 36 | Sí | `cod_cliente` de COREDB; igual al pedido |
| `numero_documento` | texto ≤ 20 | Sí | |
| `nombres`, `apellido_paterno` | texto | Sí (no vacíos) | Identidad vigente en COREDB |
| `apellido_materno` | texto | Sí (puede ser `""`) | Vacío si la persona no tiene segundo apellido; SOL lo acepta (PR-CAP-01-08) |
| `estado_cliente` | texto | Sí | `ACTIVO` para operar |
| `id_caso` | UUID | Sí | Caso de Captación que habilitó |
| `id_verificacion` | UUID | Sí | = `id_verificacion_captacion` del cliente en COREDB |
| `fecha_verificacion`, `vigente_hasta` | `YYYY-MM-DD` | Sí | Vigencia de 30 días (`CAP_VIGENCIA_DIAS`) |
| `estado_habilitante` | texto | Sí | `HABILITADO` o `REVOCADO` |
| `version_contrato` | texto | Sí | |
| `cod_tipo_documento` | texto | No | |
| `simulado` | booleano | No | `true` mientras los proveedores externos sean simulados |

**SOL acepta la referencia** solo si `id_cliente` coincide, `estado_cliente = ACTIVO`, `estado_habilitante = HABILITADO` y `fecha_verificacion ≤ hoy (Lima) ≤ vigente_hasta`. La referencia **no** lleva celular ni correo.

## Errores

| HTTP | Cuándo | Qué hace SOL |
|---|---|---|
| 200 | Referencia o lista | Valida las reglas de arriba |
| 400 `ERR-VALIDACION-ESQUEMA` | Cuerpo inválido (p. ej. `limit` 51). Convención ITIL-02 del proyecto | Lo trata como rechazo de contrato (503) |
| 401 | Sin token, token de una persona o token incorrecto | 503, sin reintento |
| 404 | El cliente no tiene referencia | 422 al asesor: «cliente no habilitado» |
| 503 | COREDB no disponible | Reintenta dentro de su presupuesto; luego 503 |
| 401 / 403 / 404 / 503 / 504 del Bus | Credencial del Bus, módulo desconocido, servicio caído o lento | Igual que el 503 |

Idempotencia: las dos rutas son **de solo lectura**; repetirlas no cambia nada (PR-CAP-01-04).
