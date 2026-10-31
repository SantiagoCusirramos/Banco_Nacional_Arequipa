# Contratos de simulación

Para el transporte HTTP, callbacks, cola y configuración consulta [CONTRATOS_HTTP_V2.md](CONTRATOS_HTTP_V2.md). Ese documento es el contrato técnico propuesto vigente.

## Separación de responsabilidades

| Participante | Autoridad prevista |
|---|---|
| Clientes / Captación | Identidad, referencia y evidencia de habilitación. |
| SOL | Expediente, condiciones solicitadas, versiones y calendario preliminar. |
| EVA | Dictamen, observaciones y condiciones resultantes; autorización hacia Desembolso. |
| Seguridad | Identidad autenticada, permisos y auditoría transversal. |
| Bus | Enrutamiento y políticas comunes de transporte. |

El laboratorio guarda datos sintéticos en `bna_sol_mvp` porque la persistencia definitiva está pendiente. La API no conecta directamente el navegador al CORE.

## Rutas de la demo

El backend expone `/sol/*` como módulo interno y `/gateway/sol/*` como despacho SIMULADO al mismo módulo. No existe un Bus desplegado aparte ni se afirma que el gateway esté conectado a otros equipos.

El Route Handler de Next.js usa `SOL_GATEWAY_URL`. Cambiar únicamente esa URL no completa una integración institucional: deben coincidir autenticación, rutas, esquemas, estados, semántica e idempotencia. El modo `REAL` usa adaptadores HTTP configurables; requiere homologar el contrato propuesto y probar contra los servicios institucionales.

| Método y ruta relativa | Función | Perfil |
|---|---|---|
| POST `auth/login` | Sesión local de laboratorio | Cuenta registrada |
| POST `auth/logout` | Invalidar token | Autenticado |
| GET `auth/me` | Identidad y rol de la sesión | Autenticado |
| GET `policy` | Política vigente | Autenticado |
| GET `clients?search=` | Referencias de Captación simulada | Autenticado |
| POST `preview` | Validar y recalcular calendario | ASESOR |
| GET / POST `applications` | Listar / crear | Autenticado / ASESOR |
| GET / PUT `applications/{id}` | Consultar / editar borrador | Autenticado / ASESOR |
| POST `applications/{id}/send` | Congelar y enviar | ASESOR |
| POST `applications/{id}/revise` | Crear versión para subsanar | ASESOR |
| POST `applications/{id}/demo-result` | Retorno de resultado simulado | EVALUADOR |

## CR-INT-01: datos de prueba

`id_cliente`, datos de identidad con nombres existentes en los schemas del repositorio, `id_caso`, `id_verificacion`, `fecha_verificacion`, `vigente_hasta`, `estado_habilitante`, `version_contrato` y `simulado`.

En esta demo el estado habilitante se llama `HABILITADO`. No debe confundirse con aprobación de crédito. Captación real debe definir el estado exacto y su vigencia; SOL no interpreta puntuaciones de riesgo.

## CR-INT-02: mensaje persistido

```json
{
  "versionContrato": "CR-INT-02-DEMO-v1",
  "idSolicitud": "UUID de la solicitud",
  "versionSolicitud": 1,
  "idOperacion": "UUID estable del envío",
  "idCorrelacion": "UUID de la petición",
  "expediente": {
    "cliente": {},
    "condiciones": {},
    "fiadores": [],
    "politica": {},
    "calendario": {}
  },
  "simulado": true
}
```

Envío: body `{ "revision": 1 }`, cabecera `X-Idempotency-Key` de 8–80 caracteres y sesión ASESOR. La operación persiste un acuse `EVA-DEMO-*`; no calcula riesgo. El mismo identificador con el mismo envío se reconoce como reintento. Reutilizarlo para otra solicitud/revisión se rechaza. La restricción única solicitud/versión impide dos entregas de una misma versión.

## CR-INT-03: retorno simulado

POST `applications/{id}/demo-result`, cabecera `X-Idempotency-Key`, cuenta `evaluador.demo`:

```json
{
  "version": 1,
  "decision": "OBSERVADO",
  "observaciones": "Precisar destino del crédito."
}
```

La demo admite APROBADO, OBSERVADO y RECHAZADO. Internamente se traducen a APROBADA, OBSERVADA y RECHAZADA. Se valida versión pendiente y no se acepta el resultado de una versión antigua. Un resultado repetido con la misma operación y contenido no duplica eventos.

El callback HTTP exige `idEvaluacion` y `ronda` del acuse, junto con un token de servicio. Su homologación, la autenticación central, la aceptación del cliente y `condicionesResultantes` siguen pendientes. Los campos extra se rechazan; esta entrega no interpreta cambios de monto/plazo propuestos por EVA.

## CR-INT-10

Se registran localmente actor autenticado, solicitud, versión, evento, estado anterior/nuevo, fecha UTC y correlación. SOL incluye outbox transaccional, worker de reenvío y adaptador HTTP hacia la ruta configurada de Seguridad. El acuse demo se etiqueta SIMULADO. No se ha demostrado conexión al servicio institucional ni se presenta el historial local como almacenamiento central inviolable.

## Integración real: acuerdos concretos

1. Tecnología/CORE/Créditos decide la autoridad de persistencia antes de agregar escrituras sobre `sol_*`.
2. CAP/SOL define campos, estado habilitante, vigencia y errores.
3. SOL/EVA homologa estados, recepción, resultados y versiones.
4. Bus define rutas, autenticación, timeouts, reintentos, correlación e idempotencia común.
5. Seguridad reemplaza sesiones locales y recibe eventos.
6. Infraestructura acuerda migraciones incrementales revisadas. No ejecutar `create_all` contra la BD compartida como estrategia de migración.
7. Calidad prueba contratos, timeouts, mensajes repetidos, resultados fuera de orden y recuperación.
