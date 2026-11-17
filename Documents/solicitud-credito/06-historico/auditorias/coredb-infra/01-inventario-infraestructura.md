> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../../README.md). Antecedente histórico; sus pendientes/conclusiones corresponden a la etapa original, no al estado vigente.

# 01 — Inventario e infraestructura

Fecha: 2026-11-16 (America/Lima). Rama analizada: `feature/sol-integracion-cap-eva`. HEAD: `988dc0776da282fbef306632fc86426b6e372376`. Auditoría estática, sin arranque, SQL, migraciones, cambios de rama ni consultas remotas. Las referencias `origin/*` son copias locales; su nombre no acredita el estado actual de un PR.

## Alcance y estado inicial

El árbol contiene COREDB, CORE legado, SOL, CUENTAS, TARJETAS, seguridad, frontend Next.js, `database/`, `docker/`, `k8s/`, scripts y documentación. CAPTACION y EVALUACION no existen como paquetes en HEAD; se inspeccionaron con `git show` desde referencias locales independientes. No se cambió a la rama sugerida por AGENTS (`feature/integracion-sol`): la rama efectiva ya contiene adaptadores posteriores.

Cambios previos preservados: `change-log.md` modificado; AGENTS.md, README-INICIO.md y dos JSON de laboratorio sin seguimiento. Esta tarea autoriza exclusivamente cinco informes; por esa instrucción específica no se modifica el changelog ni se atribuyen sus cambios previos a esta auditoría.

## Referencias Git verificadas

```text
feature/integracion-sol | de4ace61f9fce7befb79828ea56133a6667eb914 | 2026-11-14 22:07:55 -0500
feature/sol-integracion-cap-eva | 988dc0776da282fbef306632fc86426b6e372376 | 2026-11-16 19:10:30 -0500
main | 86904edd8dc866c1d4260a996748a1cda3770007 | 2026-11-13 17:46:39 -0500
origin | 86904edd8dc866c1d4260a996748a1cda3770007 | 2026-11-13 17:46:39 -0500
origin/billetera_digital | 8befd60d1ba464a81cc56e337dbcfeb891b2e08a | 2026-10-20 12:27:57 -0500
origin/clientes | fdf8f82e2c7ec8f8b53fa9a2a6c3ae61c1a83f6c | 2026-11-01 23:04:17 -0500
origin/docs/monteagudo-ronda3-v2 | c93bcf288b9fdd7b90a1bc0ce32b0f557763c42e | 2026-11-01 22:38:58 -0500
origin/docs/monteagudo-validacion-ronda3 | caea4958dd324ef5cfd6eafe412fb8b12b6b1fee | 2026-11-01 22:15:03 -0500
origin/feature/integracion-sol | de4ace61f9fce7befb79828ea56133a6667eb914 | 2026-11-14 22:07:55 -0500
origin/feature/sol-integracion-cap-eva | 988dc0776da282fbef306632fc86426b6e372376 | 2026-11-16 19:10:30 -0500
origin/infra/despliegue-k8s | 6e69588eea10de1f4c2f5f2608a20e9591338134 | 2026-10-21 17:53:07 -0500
origin/main | 86904edd8dc866c1d4260a996748a1cda3770007 | 2026-11-13 17:46:39 -0500
origin/pr-cap-74 | 4ea5014bddb1a69289402f03b3fbc47c28cc9413 | 2026-11-15 21:18:53 -0500
origin/pr-eva-70 | 57b0e2a34fd55fb96fd6245acc06a86536d220f8 | 2026-11-15 16:22:36 -0500
origin/qa/pruebas-documentacion | a7394aad89bfb23a806cc0a50ac64ff6b26367f7 | 2026-10-22 16:26:55 -0500
origin/tarjetas/servicio | 35ac26d712e79b4457e9db2078fbccc876aef33c | 2026-11-11 23:05:09 -0500

```

`origin/pr-cap-74` = `4ea5014bddb1a69289402f03b3fbc47c28cc9413` incorpora CAP y cambios de Compose/frontend/Kubernetes/scripts (59 archivos respecto de main local). `origin/pr-eva-70` = `57b0e2a34fd55fb96fd6245acc06a86536d220f8` incorpora EVA y su configuración (39 archivos respecto de main). No están incorporados funcionalmente en HEAD: faltan sus paquetes y servicios en Compose principal. No se verificó estado abierto/cerrado, mergeability ni actualidad remota. La rama de infraestructura Kubernetes es anterior al main local por fecha; no se asume superioridad por nombre. Los informes históricos que citan otros SHA remotos no sustituyen estas referencias.

## Servicios y puertos declarados

Los valores siguientes son defaults de configuración, no listeners comprobados.

| Archivo / servicio | Proceso / puerto interno | Publicación host por defecto | Datos / dependencia |
|---|---|---|---|
| compose.yaml:50 db | MySQL 8.4 /3306 | 127.0.0.1:3307 | core-db-datos; SQL integrado |
| :75 coredb | COREDB.main:app /8012 | 127.0.0.1:8012 | db healthy |
| :96 coredb-init | crear_administrador --si-falta | ninguna | escribe usuarios; no ejecutar en auditoría |
| :115 cuentas | CUENTAS.main:app /8001 | 127.0.0.1:8001 | CORE_BASE_URL=http://coredb:8012 |
| :139 tarjetas | TARJETAS.main:app /8002 | 127.0.0.1:8002 | mismo COREDB |
| :158 sol | SOL.app:app /8011 | 127.0.0.1:8011 | db-aux, SOL_INTEGRATION_MODE=SIMULADO |
| :179 sol-init | SOL.manage init | ninguna | DDL/semilla propia SOL |
| :190 seguridad | seguridad.app:app /8013 | 127.0.0.1:8013 | volumen seguridad-datos |
| :213 frontend | Next.js /3000 | 127.0.0.1:3000 | URLs internas a APIs |
| :244 core-legado | main:app /8000 | 127.0.0.1:8000 | bna sobre db-aux; separado de COREDB |
| :270 db-aux | MySQL /3306 | ninguna declarada | db-aux-datos, SOL y legado |
| CAP ref :173 captacion | CAPTACION.main:app /8014 | 127.0.0.1:8014 | captacion-init, COREDB y base bna_captacion |
| EVA ref :194 evaluacion | EVALUACION.main:app /8015 | 127.0.0.1:8015 | evaluacion-init, COREDB y bna_evaluacion |

Compose principal no declara redes explícitas: usa red default del proyecto `bna`, donde los nombres de servicio resuelven por DNS Docker. No se probó DNS en ejecución. `localhost` dentro de un contenedor apunta al mismo contenedor: CAP default localhost:8012 y EVA default 127.0.0.1:8012 requieren sustituirse por `http://coredb:8012`. Sus Compose de referencia ya lo hacen. Los puertos host no deben usarse entre contenedores.

COREDB puede ejecutarse independientemente con Uvicorn y MySQL integrado; SOL con su propia base y configuración; CAP y EVA con fuentes de sus refs y dependencias específicas. Independencia de proceso no implica independencia de COREDB para autenticar personal. No existe un Compose principal único que reúna CAP y EVA en este HEAD.

## Inicialización, persistencia y variantes

- `docker/python/Dockerfile`: Python 3.11 fijado por digest, requisitos parametrizados, usuario no root, excluye .env mediante .dockerignore. No garantiza que los requisitos actuales incluyan los de EVA; su ref modifica requirements.txt y agrega tzdata.
- `docker/core-db/Dockerfile`: copia bna_core.sql, bna_extension.sql, crear_usuarios.sh y datos de desarrollo opcionales (DATOS_DEV=1 default). Init solo sobre datadir vacío. No es una migración de volumen existente.
- `docker/db-aux/02_usuarios.sh`: crea bna_user y sol_user; no crea por sí solo CAP/EVA en HEAD. Sus inicializadores de refs usan privilegios administrativos para bases/usuarios propios.
- `docker-compose.coredb.yml`: solo MySQL `bna-core-db`, volumen core-db-data, puerto 3307; no arranca API COREDB. Overlay dev añade datos de desarrollo. Puede colisionar con `compose.yaml` por puerto 3307 y usar otro volumen: no combinarlos suponiendo una misma BD.
- Healthchecks: MySQL integrado llama core.verificar_configuracion; COREDB consulta /coredb/salud; SOL /ready consulta su BD. Salud no certifica contratos, vecinos ni circuito completo. depends_on expresa orden y salud inicial, no recuperación integral.
- `backend/Infraestructura - BD/Trabajo_hecho/BD/` conserva SQL de módulos y esquema histórico; la imagen real utiliza `database/sql/`. La existencia de tablas en cualquiera no publica HTTP.
- Kubernetes (`k8s/`) es otro despliegue, no evidencia de ejecución ni sustituto de unir los servicios de las refs.

## Laboratorios existentes

`Documents/solicitud-credito/laboratorio/prepare.py:15–17,111–150` fija SHA CAP/EVA, exporta fuentes fuera del repositorio, genera secretos privados y configura HTTP por DNS: captacion:8014, evaluacion:8015 y coredb:8012. No crea nuevos servicios bancarios. `compose.yaml` del laboratorio tiene dos MySQL tmpfs, redes internas core-data/module-data/integration, inicializadores y APIs, sin puertos host; tmpfs pierde datos al parar MySQL. Volumen cap-secrets conserva credencial de CAP; no confundirlo con persistencia de expedientes.

Base de laboratorio: DDL bloqueado por LAB_ALLOW_DDL, SOL REAL con auditoría incompleta (no arranca), EVALUACION_SOL_URL vacía (sin retorno). Overlay `compose.audit-sim.yaml` reutiliza SOL.simulator:app en audit-lab:8020, exige LAB_AUDIT_SIM_AUTHORIZATION y configura /security/events. Es alternativa académica prevista, no aprobación institucional ni activación autorizada en esta tarea. Incluso con ese overlay falta configurar retorno EVA→SOL.

`demo/compose.yaml` ofrece demostración SIMULADA de SOL, frontend y MySQL; no contiene CAP/EVA reales. No usar sus seis escenarios como prueba de integración solicitada. `compose-e06.yaml` también debe clasificarse por simuladores, no por nombre REAL.

## Verificación no destructiva

Se analizaron por AST 59 archivos COREDB/SOL y 49 archivos CAP/EVA de refs: salida 0, sintaxis correcta; no demuestra comportamiento. Sondeo de dependencias `python3 -c "import pytest,fastapi,sqlalchemy"`: salida 1, ModuleNotFoundError: pytest. El venv histórico /tmp/bna-sol-p01-venv ya no existe (ls salida 2). No se instalaron dependencias ni ejecutaron suites bancarias, ./bna test, ./bna smoke, Compose up, Docker ni HTTP. Las fixtures EVA eliminan/recrean BD y truncan tablas (ref tests/conftest.py:25–51): excluidas.

Comandos futuros, solo con entorno de pruebas aislado y revisión previa de fixtures: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider backend/COREDB/tests/test_unidad.py backend/COREDB/tests/test_autenticacion.py`; `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider backend/SOL/tests/test_providers.py`. Requieren dependencias, PYTHONPATH=backend y configuración sintética; no acreditan TCP conjunto. Para E2E futuro usar laboratorio existente con gates deliberados, sin scripts globales sobre volúmenes compartidos.

Fuentes documentales consultadas: EMPEZAR_AQUI_SOL, plan-integracion-sol, change-log, CONTRATOS_HTTP_V2, sol-apis-disponibles y auditorías/adaptadores previos. Son antecedentes; este diagnóstico se funda en fuentes actuales y refs fijadas. No se usa el PDF histórico como estado vivo.
