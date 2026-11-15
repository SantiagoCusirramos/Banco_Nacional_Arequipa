# EVALUACIÓN: evaluación crediticia (módulo 12, Línea de Créditos)

Módulo del equipo de Evaluación, adaptado por el equipo de Desembolso para integrarlo al producto.
Recibe el expediente de Solicitud (CR-INT-02), registra la situación financiera del cliente, aplica la
regla provisional RN-EVA-002-P, devuelve el resultado a Solicitud (CR-INT-03) y ofrece la aprobación
vigente a Desembolso (CR-INT-04). Puerto 8015; base propia `bna_evaluacion` en `db-aux`.

## Flujo

1. SOL envía el expediente de una versión: `POST /eva/applications`, con su token de servicio. Evaluación
   responde el acuse que SOL valida (`idEvaluacion`, `ronda`, `acuse`). Repetir el mismo envío devuelve el
   mismo acuse; `GET /eva/operations/{idOperacion}` responde 404 si no se recibió.
2. El analista registra la situación financiera (ingreso, deuda, riesgo, verificada) y corre la regla:
   hasta 80 % del límite aprueba, por encima de 100 % rechaza y en medio queda **EN_REVISION**.
3. En revisión, el analista aprueba, rechaza u **observa** (SOL corrige en una versión nueva, que es otra ronda).
4. Al aprobar se crea la aprobación: código de crédito `CRE-AAAA-NNNNNN`, vigencia de 30 días
   (`EVALUACION_VIGENCIA_DIAS`) y el **calendario de SOL copiado sin cambios** (RN-SOL-006).
5. Desembolso consulta la aprobación y, al confirmar la orden, la marca DESEMBOLSADA; repetirlo con la misma
   orden devuelve lo mismo.
6. El resultado final va a SOL por una cola con reintentos. Mientras SOL siga en modo SIMULADO
   (`EVALUACION_SOL_URL` vacía) los resultados esperan.

## Rutas

| Ruta | Quién |
|---|---|
| `POST /eva/applications`, `GET /eva/operations/{id}` | SOL, token `EVALUACION_TOKEN_SOL` (su `SOL_BUS_TOKEN`) |
| `GET /eva/v1/aprobaciones?numeroDocumento=&codCredito=`, `GET /eva/v1/aprobaciones/{id}` | Desembolso (usuario de servicio de COREDB) o personal con lectura |
| `POST /eva/v1/aprobaciones/{id}/desembolso` | Solo Desembolso |
| `/eva/v1/evaluaciones…`, `/eva/v1/envios…`, `/eva/v1/historial` | Personal con su token de COREDB |

Permisos, con las acciones de `COREDB/permisos.py`: `EVALUAR_CREDITO` registra la situación,
`APROBAR_CREDITO` decide y revoca, `VER_AUDITORIA` consulta. El token lo valida COREDB
(`GET /coredb/auth/me`); Evaluación no conoce su clave. Errores como COREDB: `{"error": {"code", "message"}}`.
Especificación: `openapi.json` (`python -m EVALUACION.scripts.exporta_openapi`).

## Base de datos

`esquema.py` es la única fuente: tablas `eva_*`, montos `DECIMAL(15,2)`, fechas UTC. Triggers impiden
modificar lo recibido de SOL, la situación registrada, el calendario y el historial, y reabrir una
aprobación DESEMBOLSADA o REVOCADA. El usuario `evaluacion_user` no tiene DELETE.
`python -m EVALUACION.scripts.preparar_base --sql` imprime el SQL.

## Ejecutar y probar

Con el producto: `./bna up` (pantalla en http://localhost:3000/evaluacion, API en http://127.0.0.1:8015/docs).
Para enviar un expediente con el formato exacto de SOL: `python -m EVALUACION.scripts.enviar_expediente_demo`.

```bash
backend/EVALUACION/scripts/pruebas_integracion.sh      # en contenedores, contra un MySQL 8.4 nuevo
EVALUACION_TEST_MYSQL=mysql+pymysql://root:clave@127.0.0.1:3306 python -m pytest EVALUACION/tests   # desde backend/
```

Las pruebas validan el acuse y el resultado con el código de SOL (`validate_receipt`, `EvaluationResult`,
y su cliente `Integrations.deliver` en modo REAL contra un servidor real).

## Pendiente

Kubernetes (`k8s/`); que SOL permita configurar la URL de Evaluación aparte del Bus; ratificar en el
Comité que SOL arma el calendario y el `cod_cliente` de COREDB como identificador común.
