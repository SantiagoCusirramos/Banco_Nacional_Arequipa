# Demo SOL con un comando

Desde la raíz del repositorio:

```bash
python3 Documents/solicitud-credito/demo/demo.py
```

Requisitos: Python3.9 o posterior, Git y Docker Engine/Desktop con `docker compose` y acceso al daemon local. No necesitas instalar Node, MySQL ni paquetes Python en tu equipo. La primera construcción necesita Internet para imágenes/dependencias y puede tardar varios minutos.

En la primera ejecución interactiva, elige una clave de12–128 caracteres para las cuatro cuentas académicas. No aparece en pantalla. En ejecuciones no interactivas se genera aleatoriamente. El comando muestra la ubicación de `acceso.txt`, fuera del repositorio, permisos0600; no imprime contraseñas ni tokens. No compartas ese archivo ni lo añadas a Git.

Cuando termine, abre **http://127.0.0.1:13017/solicitud-credito** y entra con **asesor.bna** y la clave elegida. Usa esa URL exacta (127.0.0.1, no localhost) para coincidir con la protección de origen del proxy. Swagger: http://127.0.0.1:18017/docs.

## Qué queda listo

El comando captura el código actual de SOL y el frontend registrado en Git (incluyendo sus modificaciones locales), excluye .env/caches/bases, construye imágenes propias, arranca MySQL8.4/API/Next.js, inicializa únicamente su base y carga por HTTP seis expedientes:

| Ejemplo | Estado y finalidad |
|---|---|
| Borrador | Editar monto/plazo y revisar calendario, garantía y fiador |
| En evaluación | Enseñar congelación y devolución de resultado con evaluador.demo |
| Observada | Explicar observaciones y preparar una subsanación |
| Aprobada | Mostrar resultado de Evaluación SIMULADA, sin aprobación institucional/desembolso |
| Rechazada | Mostrar decisión simulada e historial |
| Subsanación v2 | Borrador versión2 y versión1 enviada inmutable |

Todos usan datos sintéticos existentes del módulo, perfil académico versionado y pago doble desactivado. No se inventan políticas bancarias ni verificaciones reales. Pago doble y validación institucional de fiadores siguen pendientes de decisión. Garantías/fiadores son declaraciones de demostración, no validación institucional.

Perfiles (misma clave inicial, cuentas sintéticas):

- `asesor.bna`: creación, edición, envío y subsanación.
- `supervisor.bna`: consulta/funciones de supervisión permitidas; no crea solicitudes.
- `auditor.bna`: consulta de trazabilidad y eventos permitidos.
- `evaluador.demo`: devoluciones exclusivamente SIMULADAS, nunca habilitado en REAL.

## Guion de exposición — 5 a 8 minutos

1. Entrar como asesor. Explicar que SOL registra/versiona solicitudes y **no evalúa riesgo, desembolsa ni cobra**. Señalar el indicador DEMO ACADÉMICA/servicios simulados.
2. Abrir el borrador precargado. Mostrar cliente/referencia, monto/plazo/moneda, calendario preliminar con saldo final cero, garantía vehicular y fiador sintético. Editar y guardar; explicar revisión y política propuesta.
3. Mostrar el expediente en evaluación: versión enviada congelada y trazabilidad. Cerrar sesión y entrar como evaluador.demo para enviar OBSERVADO con un comentario sintético. La operación usa el endpoint demo existente, no EVA real.
4. Volver como asesor. Abrir la observada y crear nueva versión/subsanación usando los controles de la interfaz. Comparar v1 inmutable con v2 editable; enviar nuevamente si quieres completar el recorrido.
5. Con evaluador.demo, devolver APROBADO sobre la versión actual. Mostrar historial y aclarar que es resultado simulado; SOL no realiza desembolso.
6. Mostrar los ejemplos aprobado/rechazado y la subsanaciónv2 ya precargada si prefieres una exposición sin esperas.
7. Entrar como supervisor/auditor para explicar permisos de servidor y auditoría SIMULADA. Un perfil de consulta no puede crear solicitudes aunque se invoque la API directamente.
8. Cerrar aclarando pendientes: receptor institucional CR10, ensayo conjunto CAP/EVA, políticas de pago doble e identidad institucional de fiadores. No presentar esta demo como integración institucional.

Para iniciar desde cero dentro de la propia demo, puedes crear otra solicitud desde la interfaz; no es necesario tocar las bases ni ejecutar scripts SQL. Las referencias observadas/vencidas ya existentes permiten enseñar los rechazos sin cambiar fechas por SQL.

## Relanzar, estado y detener

El mismo comando de inicio reutiliza su instancia activa y conserva las ediciones del expositor. No vuelve a crear los seis expedientes mientras sea la misma instancia MySQL. La carga inicial también reanuda sus casos si un arranque se interrumpe.

```bash
python3 Documents/solicitud-credito/demo/demo.py status
python3 Documents/solicitud-credito/demo/demo.py stop
```

**Los datos son temporales:** MySQL usa tmpfs; al detener/reiniciar su contenedor se pierden los expedientes de esa demo. El siguiente inicio prepara seis ejemplos de nuevo. `stop` únicamente detiene el proyecto propio; no borra volúmenes ni ejecuta `down -v`. Si tu sistema limpia /tmp, el estado/clave pueden desaparecer: elige un nuevo directorio externo con --state-dir; no borres recursos compartidos.

Si los puertos están ocupados, el launcher aborta sin detener al ocupante. Puedes elegir otra instancia:

```bash
python3 Documents/solicitud-credito/demo/demo.py --state-dir /tmp/mi-demo-sol --port 13027 --api-port 18027
```

Usa después ese mismo --state-dir también en status/stop. Un directorio ya configurado conserva sus puertos y clave. `check` verifica fuentes/configuración y colisiones sin arrancar servicios; puede crear su estado/clave externa si es una instancia nueva.

## Aislamiento y credenciales

- Proyecto e imágenes `bna-sol-demo-<id>` exclusivos por workspace/directorio de estado; etiquetas de propietario comprobadas.
- MySQL sin puertos, usuario `sol_demo` limitado a `bna_sol_mvp_demo`; sin bases/volúmenes E06, CAP/EVA o institucionales.
- Red de datos interna para MySQL/init/SOL; puente web propio para SOL/frontend/preparador. Frontend no accede a la red de datos. Puertos publicados solo127.0.0.1.
- El puente web permite publicación y puede tener egreso: **no es una red sin salida a Internet**. Se fija SIMULADO y no se proporcionan URLs/tokens institucionales. Docker no publicó puertos efectivos cuando todos los servicios estaban únicamente en una red internal; por eso existe el puente web separado.
- API/frontend no-root y filesystem de solo lectura; claves fuera del repositorio, raíz externa0700 y archivos0600. Solo init/preparador reciben la clave inicial; API no la recibe. No se monta socket Docker en contenedores.
- No se modifica compose.yaml general, código bancario, políticas, autenticación, frontend ni el índice Git. Contextos/manifiestos/credenciales son salidas externas; no se deben versionar.
- **SIMULADO de SOL** utiliza las referencias/resultados/eventos demo existentes. No arranca el simulador HTTP de Auditoría, no configura SOL REAL ni sustituye CR10 por un acuse institucional ficticio.

## Archivos y comprobaciones de esta tarea

`demo.py` es el launcher; `compose.yaml` y los dos Dockerfiles describen solo la demo; `seed_demo.py` prepara casos por el proxy Next y verifica cookie HttpOnly/calendario/versiones; `test_demo.py` valida las guardias sin iniciar servicios.

Resultados de verificación SOL-DEMO (2026-11-16):

- 13 controles estáticos aprobados (0,045s en la última ejecución de cierre).
- Build de backend y frontend Next/TypeScript completado; MySQL/API/frontend saludables.
- Seis escenarios creados por HTTP, con saldo final cero y subsanación preservando v1. Relanzamiento conserva seis casos, sin duplicarlos.
- Acceso efectivo desde host HTTP200, cookie HttpOnly, conteos2 BORRADOR/1 EN_EVALUACION/1 OBSERVADA/1 APROBADA/1 RECHAZADA, v2 con v1 congelada y escritura supervisor rechazada403.
- La primera carga esperaba202 donde SIMULADO devuelve200; corregida expectativa del preparador. El primer diseño de red no publicó localhost; detectado por prueba host y corregido con puente web. Normalización Compose omite internal:false; validador adaptado y negativos repetidos. Ninguna corrección cambió SOL.

Estas son pruebas de la demo SIMULADA; no se vuelve a contabilizar la regresión219 anterior ni se certifica interacción de navegador con ratón, proveedores reales o homologación institucional. El arranque de verificación usa un --state-dir distinto del predeterminado para que tu primera ejecución pueda elegir su propia clave.
