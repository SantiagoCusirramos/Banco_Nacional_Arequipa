> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Registro de ejecución P20. Evidencia válida para aquella ejecución; no certifica disponibilidad actual ni homologación.

# Pruebas y evidencias reales

Fecha: 2026-11-16 (America/Lima). Rama `feature/sol-integracion-cap-eva`; HEAD `988dc0776da282fbef306632fc86426b6e372376`. CAP `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; EVA `57b0e2a34fd55fb96fd6245acc06a86536d220f8`. Sin merge, cherry-pick, cambio de rama, commit ni push.

## Circuito TCP y persistencia

Ejecución completa del launcher: salida0, **150 controles principales y2 de caída/recuperación**. [Evidencia JSON saneada](evidencias.json) contiene ruta/método/código/expectativa por petición, identificadores y checks SQL, sin tokens, contraseñas, documentos, OTP ni contactos.

| Solicitud | Versión | Operación envío | Evaluación | Ronda | Operación resultado | Estado recibido SOL |
|---|---|---|---|---|---|---|
| e194d697-173f-450e-9ce3-efb2c024c9c7 | 1 | 1bc9f15e-55b6-4813-8dbe-5b9379349efc | EVA-2026-000001 | 1 | 989221b4-6b93-4f55-b36a-96d5e4100779 | APROBADA |
| 91938063-1e9f-4626-b074-d76e25b26107 | 1 | 87f648f4-b8d9-41b3-ab54-d905c040e838 | EVA-2026-000002 | 1 | 5e71d4c0-fe8f-4ade-afba-771e9a92e2bb | OBSERVADA |
| 91938063-1e9f-4626-b074-d76e25b26107 | 2 | cf3f28ad-9fff-4c9e-97ab-2c12c4afa323 | EVA-2026-000003 | 2 | c1f32e6d-75b3-4b6e-888c-c19f6f6a4b3b | APROBADA |
| b50ca3a8-638b-4b67-8ed7-2effdf211800 | 1 | ca1cf8ad-eb08-4e39-904d-a1f7490b3f58 | EVA-2026-000004 | 1 | 381fac96-662f-439c-be65-ae96031763c9 | RECHAZADA |

Cada caso partió de cliente registrado/habilitado en CAP mediante COREDB real. El asesor consultó CAP desde SOL, calculó preview, creó/editó BORRADOR y envió202. EVA recibió sobre HTTP, persistió y emitió acuse; analista autenticado con JWT COREDB registró situación y decisión. Su worker llamó SOL y recibió acuse semántico200; se verificaron estado/versión/Outcome únicos en MySQL. La observación creó versión2 y ronda2, sin alterar snapshotv1.

Para forzar decisión humana sin cambiar reglas se usaron monto15000/plazo12/ingreso4200/deuda0/BUENO: motor académico existente devuelve EN_REVISION. Luego se invocó API real /decision. No hubo demo-result ni SQL insertando decisiones.

Consultas SQL de lectura realizadas por runner con usuarios propios: mvp_sol_envio.payload; mvp_sol_resultado por operation; mvp_sol_expediente.state/current_version; eva_expediente por operación; eva_envio.contenido por evaluación; mvp_sol_evento y auditoría outbox. COREDB confirmó cod_cliente/ACTIVO por GET real que consulta SQL integrado. Excepción de escritura de prueba: cambiar/restaurar vigente_hasta de un caso CAP sintético propio para negativo de vencimiento; no se usó SQL para aprobar solicitudes.

## Negativos reales

- Token CAP incorrecto401, credencial CAP usada en EVA401, COREDB sin token401.
- Cliente inexistente SOL422, referencia vencida422, revocación por API CAP y rechazo SOL422.
- Versión congelada no editable409; operación EVA reutilizada con otro contenido409; sobre idéntico200 y un solo expediente SQL.
- Callback repetido200/reintento_reconocido y un solo Outcome; mismo ID con contenido distinto409; versión999409; Bearer incorrecto401.
- API EVA realmente detenida: SOL responde202 y conserva PENDIENTE/intento1/error. Restaurar solo esa API: mismo ID pasa CONFIRMADO/intento2 con acuse de EVA. MySQL no se paró en esa prueba.
- JSON inválido, recibido:false, operación errónea,401,409 y timeout del receptor: tests complementarios del dispatcher con transporte de fallos (unitario y TCP en proceso separado). El servidor de fallos no reemplaza SOL en los escenarios exitosos.

## Regresiones nuevas

| Ejecución | Resultado actual | Alcance |
|---|---|---|
| SOL/tests |219 passed,1 warning,45,20s, salida0 |SQLite/mocks y pruebas de recuperación a archivo; no se presentan como MySQL E2E. Incluye modo SIMULADO original. |
| COREDB unidad/auth |57 passed,3 warnings,0,85s, salida0 |Imagen propia, sin red/BD. |
| CAP suite |35 passed,1 skipped,1 warning,1,34s, salida0 |SQLite/COREDB falso. Módulo contrato SOL omitido por tzdata en imagen providers. |
| CAP contrato SOL adicional |4 passed,1 warning,0,31s, salida0 |Imagen SOL con tzdata; cubre lo omitido. |
| EVA completa |65 passed,3 warnings,3,78s, salida0 |Tercer MySQL exclusivo. COREDB/SOL falsos en suite original; complementa el E2E TCP real. |
| EVA motor aislado |12 passed, salida0 |Subconjunto, no sumar otra vez a65. |
| Acuse EVA nuevo |9 unitarios +7 TCP aprobados, salida0 |Incluye timeoutTCP real,7 passed0,77s. |
| Frontend |114 passed,2 expected fail,5,86s; lint/tsc/build salida0 |Copia saneada original, sin credenciales; no resultados históricos. |
| Next.js host |login/proxy/política REAL/bandeja/cookie HttpOnly correctos, salida0 |Sin cambio visual ni frontend bancario editado. |

Los warnings son deprecaciones de dependencias; el warning de JWT proviene de test negativo de algoritmo, no de clave real expuesta.

## Comandos ejecutados

Desde raíz: `python3 Documents/solicitud-credito/laboratorio/demo_integracion.py`, acciones `test`, `regressions`, `eva-regressions`, `frontend`, `frontend-regressions`, `refresh-tools` durante depuración. `--suite` permite repetir solo pendientes. El launcher ejecutó builds y Compose up de proyecto exclusivo, inicializadores propios, HTTP TCP, lectura SQL propia y stop/up únicamente API EVA para recuperación.

No se ejecutó ./bna test/smoke porque usa la infraestructura global; se ejecutaron sus módulos pertinentes dentro de entornos aislados. No se hicieron reset,down-v,migraciones globales, cambios de rama ni push. La suite EVA destructiva fue revisada antes y apuntó únicamente a mysql-tests en red test-data, no al MySQL de expedientes.

## Fallos observados y resueltos

Primeros intentos: carrera sonda socket/TCP, scripts0600, PYTHONPATH, helper UPDATE, espera DNS corta. Se corrigieron solo recetas/runners del laboratorio. SOL primera regresión217/2 por imponer sqlite:// al reinicio; al respetar fixtures219/0. COREDB primera recolección falló sin PyJWT en providers; imagen propia57/0. Acuse tests inicial9 errores por fixture sin correlación; corregida fixture. EVA inicial62/3 porque SolFalso omitía operación; parche de fixture al contrato real y posterior65/0. Se conserva historia en changelog; estos fallos no se ocultan ni se cuentan como pruebas pasadas.

La reproducción desde un proyecto completamente nuevo y controles de infraestructura/privacidad se consignan en el cierre agregado a este informe.

## Cierre y reproducción limpia comprobados

El comando `python3 Documents/solicitud-credito/laboratorio/demo_integracion.py --state /tmp/bna-integracion-final-clean.json --port 18130` arrancó desde cero otro proyecto/fuentes/bases/secretos y terminó salida0 con150+2 checks, cuatro Swagger y Next.js REAL. Los IDs de la tabla son de esa instancia limpia, que permanece activa. No se copiaron clientes/resultados SQL del ensayo anterior.

`dependency-checks --state /tmp/bna-integracion-final-clean.json` salió0: supervisor sin facultad403, callback inválido422, caída solo API COREDB→CAPready503 y SOLpreview503; restauración garantizada. `verify-running` salió0: labels propios, MySQL tmpfs sin puertos, APIs loopback, permisos privados y cero secretos del entorno/JWT en logs examinados en memoria; consulta SQL integrada confirmó2 clientes sintéticos. No se publicaron logs brutos.

Validador original sobre una nueva preparación con gates cerrados:97 hashes/AST/configuración correctos, salida0; nueve negativos de infraestructura aprobados0,827s. Enlaces/AST6 nuevas fuentes y git diff --check salida0. No se repitieron suites bancarias ya aprobadas tras cambios exclusivamente de documentación/herramientas de verificación.

Revisión final: seis informes, enlaces y AST de seis scripts correctos; hashes de ambas capturas verificados;622 archivos inspeccionados contra secretos generados sin coincidencias. Backend/frontend/infra compartida e índice Git intactos. El proyecto inicial de depuración fue detenido con salida0, sin down-v; la instancia limpia permanece activa. `git diff --check` salida0. El diff seguido incluye el changelog previo del usuario y la navegación README; los seis scripts, seis informes y JSON nuevos permanecen sin staging.
