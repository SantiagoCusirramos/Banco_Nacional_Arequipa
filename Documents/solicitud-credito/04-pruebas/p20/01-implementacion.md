> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Registro de ejecución P20. Evidencia válida para aquella ejecución; no certifica disponibilidad actual ni homologación.

# Implementación final CAP → COREDB → CAP → SOL → EVA → SOL

Fecha: 2026-11-16 (America/Lima). Rama `feature/sol-integracion-cap-eva`; HEAD `988dc0776da282fbef306632fc86426b6e372376`. CAP `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; EVA `57b0e2a34fd55fb96fd6245acc06a86536d220f8`. Sin merge, cherry-pick, cambio de rama, commit ni push.

## Resultado

Flujo académico implementado y ejecutado por HTTP entre aplicaciones originales independientes. SOL trabaja REAL contra CAP/EVA y guarda en MySQL propio; EVA persiste y devuelve decisiones por callback. Se comprobaron APROBADA, OBSERVADA→subsanaciónv2→APROBADA y RECHAZADA. No se usó demo-result ni se escribieron tablas COREDB desde SOL.

## Archivos incorporados

Todos bajo Documents/solicitud-credito/laboratorio/:

| Archivo | Función |
|---|---|
| demo_integracion.py | Comando de arranque, estado, pruebas, parada y regresiones. Exporta fuentes/secretos fuera de Git y configura overlays exclusivamente para este laboratorio. |
| patch_eva.py | Parche contextual estricto de envios.py original y fixture de pruebas ayudas.py, con hash previo/posterior. |
| flow_http.py | Circuito TCP completo, cuatro evaluaciones, persistencia SQL propia y negativos/idempotencia. |
| failure_http.py | Prueba de API EVA detenida y recuperación con la misma operación; MySQL permanece activa. |
| test_callback_ack.py | Nueve pruebas unitarias del acuse: éxito, recibido:false, operación errónea, JSON inválido,401,409,timeout,202 y booleano no estricto. |
| test_ack_tcp.py | Pruebas con servidor de fallos HTTP en proceso independiente; no sustituye aplicaciones bancarias. |

Nuevos informes y evidencia saneada en esta carpeta. `../change-log.md` registra cada lote, incluidos fallos reales y correcciones. No se editaron backend/SOL, COREDB, CAP original, EVA original, Seguridad, frontend, bases globales, CI ni Compose compartido. Se preservan los cambios previos del usuario y los cinco informes de auditoría.

## Reutilización y composición

Se reutilizan prepare.py, guard.py, bootstrap_sol.py, Dockerfile.api/core, Compose base y overlay audit-sim existentes. Se exportan COREDB/SOL de HEAD/workspace y CAP/EVA de SHA fijos. No se importan PR completos. La copia privada contiene los módulos FastAPI originales y requisitos originales; pruebas también proceden de esos SHA. El launcher exige rama correcta para preparar y verifica hashes antes de actuar.

Dos MySQL8.4 tmpfs: mysql-core aloja los schemas integrados y mysql-modulos aloja tres bases propias con usuarios distintos (CAP/SOL/EVA). El servidor MySQL puede compartirse dentro de este laboratorio; las bases, usuarios y persistencia lógica están separados. Ninguno publica3306. Inicializadores solo contra destinos generados del proyecto. API COREDB conecta core-data; APIs de módulos solo module-data/integration; nombres Docker coredb:8012/captacion:8014/sol:8011/evaluacion:8015.

El overlay flow.json se genera fuera del repo. Publica Swagger en loopback y añade red web propia con egreso: no se promete bloqueo total de salida de las APIs. Frontend solo red web; MySQL nunca red web. Todas las redes y cap-secrets pertenecen al proyecto aleatorio; no hay bind mounts ni volúmenes externos. Fuentes sin dotenv/node_modules/caches, raíz0700, runtime/secrets0600. API y runner no reciben credenciales SQL root. Se rechaza Docker remoto.

## Parche EVA

Antes: cualquier2xx terminaba en ENTREGADO. Ahora: HTTP200, JSON objeto, recibido es True e idOperacion exactamente igual al resultado. Respuesta semánticamente inválida pasa a ERROR/ACUSE_SOL_INVALIDO, conservando contenido y operación; reintento manual disponible.401 es ERROR;409/timeout siguen pendientes y conservan backoff original. No se modifica motor, permisos ni decisiones. El doble SOL de tests ahora incluye idOperacion, igual que el callback real; ninguna aserción original se eliminó.

Los hashes previos/posteriores están en el manifiesto privado y la evidencia saneada. La fuente Git original permanece intacta; para reproducir el parche basta ejecutar el launcher. Las fuentes exportadas nuevas aplican el mismo reemplazo contextual y fallan explícitamente si cambia la referencia.

## Auditoría académica

Se activa solo en este launcher el gate LAB_AUDIT_SIM_AUTHORIZATION=AUTHORIZED_ACADEMIC_ONLY y el overlay existente SOL.simulator. Sirve exclusivamente /security/events en el canal usado; los adaptadores CAP/EVA apuntan a sus aplicaciones originales, no al simulador. Los eventos/outbox locales SOL son reales y persistidos. Los acuses del receptor académico son simulados, aunque la columna de entrega de transporte pueda decir CONFIRMADO; no acreditan Seguridad institucional.

## Problemas depurados

- Sonda socket MySQL aceptaba servidor temporal antes de TCP: overlay cambia a sonda TCP y core.verificar_configuracion.
- Umask privado dejó scripts0600 no legibles por UID10001: fuentes0644/directorios0755 dentro de raíz0700; secretos siguen0600.
- Script bajo /app/lab no encontraba SOL: PYTHONPATH=/app solo en runner.
- Helper SQL leía filas de UPDATE: comprueba returns_rows; fixture vencida solo afecta caso sintético CAP y restaura fecha en finally.
- Prueba de caída esperaba error DNS a los8s: ahora espera condición persistida hasta60s y siempre restaura EVA.
- Regresión forzaba SQLite en memoria a pruebas de reinicio: se respeta elección original de fixtures.
- COREDB requiere PyJWT: tests en imagen COREDB; CAP_SOL requiere tzdata: tests en imagen SOL.
- Tres tests EVA usaban acuse falso incompleto: parche aislado de fixture, validación de producción conservada.

Se mantienen restricciones de fiadores REAL, pago doble y política académica propuesta. La integración institucional sigue pendiente.

Acciones adicionales del launcher: `dependency-checks` comprueba403/422/503 con restauración de COREDB; `verify-running` valida recursos Docker efectivos y privacidad de logs; `eva-regressions` aísla fixtures destructivas en tercer MySQL y `frontend-regressions` ejecuta lint/tsc/tests/build sin credenciales. README de laboratorio existente enlaza esta guía y conserva íntegro su registro histórico. Estas adiciones no cambian los defaults productivos.
