# EVALUACIÓN: evaluación crediticia (módulo 12, Línea de Créditos)

Módulo del equipo de Evaluación (Rodrigoss06, #70), integrado sobre COREDB. Recibe el expediente de
Solicitud (CR-INT-02) y lo registra en COREDB, ofrece al analista la bandeja, la evaluación con la regla
provisional RN-EVA-002-P y la decisión, y devuelve el resultado a Solicitud (CR-INT-03). Puerto 8015.

**No tiene base propia.** Los datos viven en las tablas `creditos.*` de la base integrada y solo COREDB
los escribe, por sus procedimientos (`backend/COREDB/CONTRATO_CREDITOS.md` §3). Desembolso lee las
aprobaciones directamente de COREDB (`GET /coredb/creditos/aprobaciones`), así que CR-INT-04 ya no pasa
por aquí.

## Flujo

1. SOL envía el expediente de una versión: `POST /eva/applications`, con su token de servicio. Evaluación
   comprueba el sobre, lo traduce y lo registra con `POST /coredb/creditos/solicitudes` usando su usuario
   de servicio (`svc-evaluacion`). Responde el acuse que SOL valida: `idEvaluacion` (el UUID que tendrá la
   evaluación de esa ronda en COREDB), `ronda` y `acuse` (`ACK-<idEvaluacion>`). Repetir el mismo envío
   devuelve el mismo acuse; la misma versión con otro contenido, 409 `IDEMPOTENCIA_CONFLICTO`.
2. El analista registra la situación financiera (ingreso, deuda, riesgo, verificada) con su token de
   COREDB. COREDB corre la regla: hasta 80 % del límite aprueba, por encima de 100 % rechaza y en medio
   queda **OBSERVADO** para el analista.
3. Un caso OBSERVADO lo decide un analista registrado: **APROBADO o RECHAZADO**. Por omisión del equipo
   (pregunta T1 del contrato), el analista no devuelve la solicitud a SOL para que la corrija.
4. Aprobada, la solicitud queda disponible para Desembolso por 30 días con el calendario de SOL sin
   cambios (RN-SOL-006). Se puede revocar antes del desembolso, con motivo.
5. El resultado final (APROBADO o RECHAZADO) vuelve a SOL (CR-INT-03). Evaluación no guarda nada: cada
   ciclo lee de COREDB las solicitudes de los últimos `EVALUACION_ENVIO_VENTANA_DIAS` días con resultado
   final y se lo envía; el `idOperacion` sale del resultado (uuid5), así que repetirlo manda el mismo
   mensaje y SOL lo reconoce sin duplicarlo. Un OBSERVADO sin decisión no se envía. Mientras SOL siga en
   modo SIMULADO (`EVALUACION_SOL_URL` vacía) el ciclo no corre.

## Rutas

| Ruta | Quién | En COREDB |
|---|---|---|
| `POST /eva/applications` | SOL, token `EVALUACION_TOKEN_SOL` (su `SOL_BUS_TOKEN`) | `POST /coredb/creditos/solicitudes` (`svc-evaluacion`) |
| `GET /eva/operations/{id}` | SOL | Siempre 404: Evaluación no guarda operaciones y SOL reenvía, sin duplicar |
| `GET /eva/v1/solicitudes`, `GET /eva/v1/solicitudes/{id}` | `VER_CREDITO` | Bandeja y detalle |
| `POST /eva/v1/solicitudes/{id}/evaluaciones` | `EVALUAR_CREDITO` | Evaluación (regla) |
| `POST /eva/v1/evaluaciones/{id}/decision` | `APROBAR_CREDITO`, analista registrado | Decisión |
| `POST /eva/v1/solicitudes/{id}/revocacion` | `APROBAR_CREDITO` | Revocación |
| `GET /eva/v1/aprobaciones`, `GET /eva/v1/catalogo` | `VER_CREDITO` | Aprobaciones y catálogo |
| `GET /eva/v1/resultados-sol` | `VER_CREDITO` | Lo que CR-INT-03 envía a SOL |

Las rutas del personal reenvían a COREDB **el token de la persona**: COREDB vuelve a comprobar el permiso
y su auditoría registra al analista. Un usuario de servicio no entra en ellas. Errores como COREDB:
`{"error": {"code", "message"}}`, con los códigos de COREDB (`SOLICITUD_NO_ADMITIDA`,
`ANALISTA_REQUERIDO`, …). Especificación: `openapi.json` (`python -m EVALUACION.scripts.exporta_openapi`).

**Analistas:** decidir exige un usuario de COREDB ligado a un empleado activo y registrado con
`POST /coredb/creditos/analistas` (CONTRATO_CREDITOS.md §3.4). Un administrador da de alta todo por
la API: usuario ANALISTA (`POST /coredb/usuarios`), empleado ligado a él (`POST /coredb/empleados`) y
analista. Evaluar solo exige `EVALUAR_CREDITO`.

## Configuración

| Variable | Qué es |
|---|---|
| `EVALUACION_COREDB_SECRETO` | Secreto de `svc-evaluacion`. En el producto lo crea `coredb-init` con `COREDB.scripts.crear_servicio` |
| `EVALUACION_COREDB_USUARIO` | `svc-evaluacion` por omisión |
| `COREDB_URL` | COREDB, a través del Bus: `http://bus:8018/bus/coredb` en compose y k8s |
| `BUS_TOKEN` | Credencial del módulo ante el Bus (`X-Bus-Token`; en el producto, `BUS_TOKEN_EVALUACION`) |
| `EVALUACION_TOKEN_SOL` | Token de SOL para CR-INT-02 |
| `EVALUACION_SOL_URL`, `EVALUACION_SOL_TOKEN_RESULTADOS` | CR-INT-03; la URL queda vacía mientras SOL sea SIMULADO |
| `EVALUACION_ENVIO_INTERVALO_SEG`, `EVALUACION_ENVIO_VENTANA_DIAS` | Cada cuánto y hasta cuántos días atrás se reenvían resultados (30 s, 7 días) |

## Ejecutar y probar

Con el producto: `./bna up` (pantalla en http://localhost:3000/evaluacion, API en http://127.0.0.1:8015/docs).
Para enviar un expediente con el formato exacto de SOL: `python -m EVALUACION.scripts.enviar_expediente_demo`
(el `--cliente` debe ser un `cod_cliente` de COREDB).

```bash
backend/EVALUACION/scripts/pruebas_integracion.sh      # en contenedores: bna-core-db y COREDB nuevos
```

Las pruebas usan la base integrada y COREDB reales (no dobles) y validan el acuse y el resultado con el
código de SOL (`validate_receipt`, `EvaluationResult` y su cliente `Integrations.deliver` en modo REAL).
Al terminar no quedan contenedores ni volúmenes.

## Pendiente

Que SOL permita configurar la URL de Evaluación aparte del Bus; ratificar en el Comité que SOL arma el
calendario y el `cod_cliente` de COREDB como identificador común; la pregunta T1 (si el analista puede
observar y devolver a SOL) sigue abierta con el valor por omisión "no".
