# Validación del MVP SOL v2

Fecha: 23 de octubre de 2026. Esta validación reemplaza el registro de v1 del 21 de octubre para describir el código actualizado. Los resultados proceden de ejecuciones locales; no acreditan integración con los servicios institucionales.

## Resultado

- **52 pruebas aprobadas en SQLite**, incluyendo las 29 verificaciones anteriores y 23 casos nuevos/parametrizados de v2. Regresiones adicionales aprobadas para la normalización del ingreso, la identificación de actor/sujeto en bajas y la recuperación de auditoría.
- **52 pruebas aprobadas en la ejecución con MySQL 8.0.46**, con la base exclusiva bna_sol_mvp_test. Los casos unitarios del calendario/configuración no necesitan base; los ensayos explícitos de migración y reinicio usan archivos SQLite para aislarse. Los casos de API, adaptadores y outbox de esta ejecución sí usan MySQL.
- **Frontend:** build de Next.js 16.3.8/TypeScript y ESLint aprobados.
- **Navegador Chromium + MySQL local:** crear, calcular, enviar, observar, subsanar en v2, reenviar, aprobar y consultar como auditor. Sesión HttpOnly, origen externo rechazado con 403, ausencia de errores JavaScript y vista móvil sin desbordamiento.
- **Procesos HTTP locales separados + MySQL:** FastAPI SOL en modo REAL apuntando al servidor SOL.simulator; CAP habilitado aceptado y observado/vencido rechazados; 202 local y confirmación del worker; callback OBSERVADO, v2, rechazo de resultado viejo y APROBADO. El consumidor confirmó ocho eventos del recorrido en el servicio de auditoría simulado.

Los fallos de timeout después de aceptación, consulta remota caída, agotamiento de reintentos y recuperación de auditoría se inyectan de forma reproducible con `httpx.MockTransport` en los tests. El ensayo de procesos separados comprueba transporte TCP y callback, con simuladores locales. Ninguno se presenta como una prueba con CAP/EVA/Bus/Seguridad del banco.

La corrección de fecha incluye un reloj controlado a las 20:00 en Lima, cuando UTC ya está en el día siguiente. También se prueba el cambio real de fecha de negocio a medianoche de Lima. No se cambió la hora del equipo del usuario.

## Evidencia entregada

Abrir **`evidencias-v2/indice.html`** en el navegador después de extraer el ZIP.

- `pytest-mysql.xml` / `.txt` y `pytest-sqlite.xml` / `.txt`: salida efectiva de las suites.
- `caso-01.html/png` a `caso-52.html/png`: qué se probó, resultado, duración, fecha y ambiente por caso. Las imágenes son **capturas del reporte generado desde el XML**, no fotografías de terminal ni evidencias institucionales. El código contiene las aserciones comprobadas.
- `ui-01-acceso.png`, `ui-02-revision.png`, `ui-03-bandeja-aprobada-v2.png` y `ui-04-movil.png`: capturas reales del navegador con fecha de Lima y rótulo de datos sintéticos.
- `navegador.json`: resultado del recorrido, sesión y controles de interfaz.
- `http-local.json`: resultado del intercambio TCP, confirmación de auditoría y muestras p95 del proceso. Son mediciones locales, sin carga representativa ni meta de servicio aprobada.
- `frontend-build.txt`, `frontend-lint.txt` y `entorno-mysql.json`: compilación y ambiente utilizado.

Los archivos y capturas no incluyen credenciales de servicio, contraseñas ni datos personales reales. Se observó una advertencia de obsolescencia de la dependencia de pruebas de Starlette/AnyIO; no representa un fallo de los casos. Las tablas y las fórmulas de crédito conservan la política de laboratorio, sin nuevas aprobaciones de negocio.

## Reproducir

Desde backend: `python -m pytest SOL/tests -q`. Usa SQLite por defecto.

Para MySQL, crear **solo** `bna_sol_mvp_test` y definir `SOL_TEST_DATABASE_URL` con su URL SQLAlchemy/PyMySQL. Los tests borran/recrean tablas de laboratorio en esa base; el nombre se verifica antes de ejecutar. No usar la base que contiene tus solicitudes de demostración ni la compartida del proyecto.

Desde frontend: `npm run lint` y `npm run build`. Para iniciar la app consultar `EMPEZAR_AQUI_SOL.md`. Para HTTP local y configuración del callback consultar `CONTRATOS_HTTP_V2.md`.

## Pendiente en Testing institucional

1. Rutas/esquemas/versiones y autenticación definitivas con Bus y los propietarios de las cuatro interfaces.
2. Ejecuciones reales de CR-INT-01, 02, 03 y 10, con fecha, versiones, responsables y acuses del ambiente compartido.
3. Dedupe persistente de idOperacion en EVA y de idEvento en Seguridad. La cola local entrega al menos una vez; no puede imponer unicidad en una base ajena.
4. Roles/SSO/MFA centrales, TLS y restricciones de red, retención de logs/eventos y responsable operativo del worker.
5. Validación de migración sobre una copia de la base concreta del equipo. La migración automática probada es incremental y no borra datos, pero no se accedió al MySQL de la computadora del usuario.
6. Reglas financieras, estados oficiales, pago doble, fiadores y obligatoriedad de garantías según aprobación del Comité. No se han inventado esos acuerdos.
