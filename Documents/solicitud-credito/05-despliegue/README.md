# Ejecución, Swagger y operación académica

> Estado: **VIGENTE**. Última verificación documental: **2026-11-16** (código y evidencias existentes; sin repetir pruebas funcionales). Rama: `feature/sol-integracion-cap-eva`; SHA: `988dc0776da282fbef306632fc86426b6e372376`. Principal: [README SOL](../README.md).

## Dos demostraciones distintas

| Modalidad | Comando desde raíz | Alcance |
|---|---|---|
| Circuito intermodular | `python3 Documents/solicitud-credito/laboratorio/demo_integracion.py` |CAP/COREDB/SOL/EVA originales por HTTP, MySQL efímero, auditoría/verificadores externos simulados. |
| Demo SOL independiente | `python3 Documents/solicitud-credito/demo/demo.py` |SOL SIMULADO con frontend y datos de presentación; no prueba CAP/EVA originales. |

Prerrequisitos del circuito: Python3 estándar, Git con refs fijadas, Docker/Compose local, permiso del socket, imágenes/dependencias disponibles o red para build. No hace falta pytest en host. Fuentes/secretos se generan fuera de Git. API/runner sin SQL root; bases propias, MySQL tmpfs sin puertos. La red web propia tiene egreso; no es un entorno institucional sin salida.

## Comandos del launcher contrastados con argparse

```bash
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py status
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py test
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py regressions
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py eva-regressions
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py frontend-regressions
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py stop
```

`up` es acción por defecto; `test` repite el flujo y agrega datos; regresiones no son sondas de salud. `eva-regressions` usa tercer MySQL exclusivo. `dependency-checks` detiene/restaura COREDB para negativos, no ejecutarlo en revisión solo documental. `verify-running` es comprobación operacional sin escrituras de negocio y guarda evidencia privada; `refresh-tools` reconstruye captura de tests y no es un comando de estado.

Para instancia distinta: `--state /tmp/bna-integracion-final-clean.json --port 18130` en up; repetir el mismo --state en acciones posteriores. Estado privado no contiene claves. No se garantiza que /tmp ni contenedores de una ejecución anterior sigan disponibles. El último registro P20 usó esa ruta y18130–18134; es evidencia de aquella ejecución, no una URL institucional permanente.

## Acceso y Swagger

Default generado: COREDB18120,CAP18121,SOL18122,EVA18123,Next18124, todos127.0.0.1; APIs en /docs y /openapi.json, frontend en /solicitud-credito. Con --port18130 se desplazan a18130..18134. El launcher imprime valores efectivos. DNS interno: coredb:8012,captacion:8014,sol:8011,evaluacion:8015; no usar localhost entre contenedores.

Usuario SOL/Next `asesor.bna`; contraseña generada en runtime/sol-init.env (SOL_INITIAL_PASSWORD). Usuario COREDB `admin-lab`; contraseña en runtime/coredb-init.env (CORE_DB_ADMIN_INICIAL_PASSWORD). Leer solo el valor necesario en terminal/editor privado, no mostrar archivos completos en capturas. JWT de persona se obtiene por POST /coredb/auth/login y permite CAP/EVA según permisos; callback usa token de servicio separado. No publicar credenciales ni docker compose config interpolado.

## Guion de demostración

Mostrar código de cliente creado en CAP/COREDB, referencia vigente consultada por SOL, preview y BORRADOR, envío202 local, acuse EVA200 con IDs, decisión de analista y callback recibido en SOL con estado APROBADA. Comparar operación de envío y de resultado (distintas), evaluación/ronda/versión iguales. Mostrar OBSERVADA→v2→APROBADA y v1 congelada. Evidencia P20 tiene IDs y checks SQL, no contraseñas. No usar demo-result para demostrar retorno EVA real.

El runner revoca un cliente para probar negativo y deja otro habilitado para recuperación; no usar el primero para nuevos expedientes. En Next consultar bandeja/historial/estados; CAP/EVA no tienen UI integrada en HEAD, usar Swagger. Auth y política REAL del proxy fueron comprobadas por HTTP, no navegación visual automatizada P20.

## Parada y problemas frecuentes

stop solo detiene su proyecto, sin down-v. MySQL tmpfs pierde datos al parar; el siguiente up prepara proyecto nuevo y conserva captura anterior. No reiniciar MySQL para demostrar durabilidad; caída/restauración de API es otra prueba. No resetear recursos de otras tareas.

Si falta ref Git: detener preparación y verificar SHA local; no crear proveedor falso. Si faltan URL/token REAL: arranque falla sin fallback. Si no llega resultado: comprobar EVALUACION_SOL_URL=http://sol:8011, pareja de token callback y acuse conciliado;409 antes de acuse puede reintentarse. Si EVA marca ERROR/ACUSE_SOL_INVALIDO: corregir contrato y reintentar, no relajar recibido/idOperacion. Si hay puertos ocupados elegir --state nuevo y --port libre, sin detener proyectos ajenos.

## Procedencia y recursos estables

Consolida [guía P20 original](../04-pruebas/p20/05-guia-demostracion.md), [laboratorio](../laboratorio/README.md), [demo independiente](../demo/README.md) y código de launchers. P20 prueba laboratorio; [Compose principal](../../../compose.yaml) sigue distinto y SIMULADO para SOL. TLS/SSO/auditoría homologada, backup/retención y despliegue institucional no se incorporan por esta reorganización.

Scripts E06/Compose/OpenAPI permanecen en raíz por build contexts y Path(__file__); son recursos históricos y no comandos recomendados del circuito actual.
