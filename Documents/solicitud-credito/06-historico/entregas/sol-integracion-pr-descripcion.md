> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# feat(sol): adaptadores CAP/EVA independientes y laboratorio de integración

SOL usaba una sola URL/credencial de Bus para CAP, EVA y Auditoría y rechazaba referencias CAP sin apellido materno. Este cambio permite configurar cada proveedor por separado y procesar el apellido opcional sin inventar identidad. Conserva Bus legado, SIMULADO, snapshots, idempotencia, reservas y callback existentes; un fallo REAL nunca activa simulación.

**Segundo PR sobre `feature/integracion-sol`, dependiente del [PR75 E01–E06](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/75), todavía abierto al cierre.** Listo con limitaciones documentadas; **no demuestra el circuito CAP→SOL→EVA→SOL ni integración institucional**.

## Cambios técnicos

- SOL_CAP_BASE_URL/TOKEN, SOL_EVA_BASE_URL/TOKEN y SOL_AUDIT_BASE_URL/TOKEN como parejas completas; campos propios ausentes reutilizan configuración Bus, nunca credenciales de otro proveedor tras un error.
- Clientes HTTP con destino/token por proveedor; rechazo de rutas que elijan otro host y redirects deshabilitados. Timeouts/presupuesto/reintentos públicos conservados.
- Materno omitido/null/vacío normalizado a vacío; proyección mínima en listado/detalle/fiadores e historia sobre copia, sin reescribir snapshots. DTO de respuesta opcional.
- Cincuenta pruebas multiproveedor y laboratorio exclusivo, sin modificar Compose general ni CAP/EVA/COREDB. Fuentes por SHA y workspace SOL, dos MySQL con tmpfs, redes internas y secretos externos. Auditoría simulada opcional con autorización separada, no activada.
- Matriz RF, evidencia clasificada y manifiesto exacto de commit. Sin dependencias nuevas ni cambios de frontend, política financiera, workers, reservas, migraciones o callback/auth.

## APIs y contratos

| Contrato | Endpoints preparados | Estado demostrado |
|---|---|---|
|CR-INT-01 | GET /cap/references, GET /cap/references/{idCliente} | CAP/COREDB HTTP independiente probado; gate/adapter SOL con fakes y contratos. CAP→SOL activo no verificado |
|CR-INT-02 | POST /eva/applications, GET /eva/operations/{idOperacion} | DTO/acuse y conciliación SOL probados localmente; sin entrega válida SOL→EVA TCP |
|CR-INT-03 | POST /sol/integrations/evaluation-results | Receptor intacto, auth/IDs/versiones/rondas/decisiones/subsanación probadas con fake/DB; sin worker EVA→SOL TCP |
|CR-INT-10 | Receptor institucional pendiente | Configuración/acuse siguen obligatorios en REAL; no excepción ni autorización implícita del simulador |

CAP[74](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/74) se fija a4ea5014, EVA[70](https://github.com/SantiagoCusirramos/Banco_Nacional_Arequipa/pull/70) a57b0e2a. No se fusionan ni se incorpora su historia de Cuentas/Tarjetas. COREDB del laboratorio es la base de SOL; main posterior requiere revisión propia.

## Validación nueva de cierre

| Ejecución | Resultado |
|---|---|
| SOL SQLite |219 passed,45,45s, salida0 |
| Suite SOL con fixtures MySQL habilitadas |219 passed,51,77s, salida0; casos puros siguen en memoria |
| CAP |33 passed + móduloSOL omitido por tzdata en imagenCOREDB; las4 CAP-SOL pasaron en providers |
| Contratos/OpenAPI/motor EVA |22 passed (10 nuevos +12 motor),1,30s |
| Aislamiento estático |9 passed;97 fuentes verificadas |
| Frontend en copia limpia |114 passed,2 expected fail; TypeScript/lint/build salida0 |

Advertencias heredadas deprecaciones backend/Vite/ESLint documentadas; no errores nuevos. No suites destructivas EVA ni scripts globales. El esquema MySQL de regresión es nuevo y usuario limitado; ninguna base CAP/EVA/COREDB se usa como base de tests SOL.

La evidencia anterior de SOL-LAB-INTEGRATION se identifica separadamente:24 HTTP independientes, captura sin materno, referencia/revocación, errores401/403/404/409/422/503, persistencia MySQL8.4.11 y reinicio solo de APIs. No es una nueva ejecución de este cierre ni una prueba de SOL activo.

## Limitaciones y decisiones

- CR10 bloquea arrancar SOL REAL conjunto: Seguridad debe aportar receptor homologado o autorizar expresamente el simulador académico existente. No se ha hecho ninguna de ambas cosas.
- CAP mantiene verificadores de identidad/riesgo/OTP simulados; EVA regla provisional. RF005 pago doble y RF008 validación de fiadores institucionales conservan bloqueos DA-SOL-005/006.
- Prueba unitaria nueva caracteriza que EVA marca ENTREGADO ante200 con recibido:false/JSON incompatible. Se solicita a su equipo acordar/validar el acuse positivo; no se editó EVA ni se afirma reproducción TCP/MySQL de ese riesgo. Lease/409/respuestas tardías requieren ensayo conjunto.
- Pendientes recepción/acuse real, respuesta perdida tras persistir, callback/duplicados antiguos, subsanación v2 y recuperación con reservas reales. No se declara integración institucional.
- main remoto observado por Git fcc76b1 difiere de API commits/main729c1e5. Comparación fijada a fcc76b1 sin solapamientos de archivos, mergeability desconocida; no certifica ausencia de conflictos semánticos. Actualizar revisión al abrir/cambiar base.

## Reproducción y archivos

Consultar [entrega](sol-integracion-entrega-final.md), [laboratorio](../../laboratorio/README.md), [plan](../planes/sol-plan-laboratorio-cap-eva.md), [BUILD](../planes/sol-laboratorio-build.md) y [manifiesto de commit](sol-integracion-archivos-commit.txt).

`prepare.py --run-id <id-unico>` genera fuentes/secretos fuera del repositorio; validate.py y test_static.py solo inspeccionan configuración. Build/arranque por fases requieren las autorizaciones del plan. SOL REAL no se inicia sin CR10 autorizado. No utilizar fixtures EVA destructivas ni `down -v`; no reutilizar recursos E06. JSON generados, runtime, logs, DB, caches y secretos excluidos del commit; los informes conservan resultados saneados.
