# Cómo explicar el código de Solicitud de Crédito

La aplicación tiene tres partes: Next.js presenta pantallas en el puerto 3000; Python/FastAPI valida y procesa en 8011; MySQL guarda los datos en 3306. Cerrar una pantalla no borra una solicitud porque vive en la base de datos.

## Backend

| Archivo | Responsabilidad | Qué puedes explicar |
|---|---|---|
| `SOL/app.py` | Endpoints, autenticación, permisos y transacciones del recorrido. | El servidor controla quién puede crear, enviar y simular resultados. No basta ocultar botones. |
| `SOL/schemas.py` | Forma y tipos de las entradas. | Un monto con más de dos decimales o un plazo fraccionario se rechaza. |
| `SOL/config/politica_demo.json` | Parámetros de negocio en un único archivo. | Aquí cambian montos, plazo y tasa cuando el comité lo acuerde. |
| `SOL/policy.py` | Verifica coherencia de la política. | Un límite invertido o fórmula no soportada bloquea operaciones en lugar de inventar un resultado. |
| `SOL/finance.py` | Conversión de tasa y calendario con Decimal. | La tasa mensual equivalente es `(1 + TEA)^(1/12) - 1` para periodos de 30 días. El último pago ajusta el saldo residual. |
| `SOL/models.py` | Tablas del laboratorio y restricciones únicas. | Un expediente tiene varias versiones; cada una guarda condiciones, política y calendario. |
| `SOL/database.py` | Motor SQLAlchemy y sesiones de BD. | Los cambios de estado y su historial se confirman en una transacción. |
| `SOL/service.py` | Validaciones, snapshots, revisión y serialización. | Se vuelve a calcular en el backend; no se confía en una cuota enviada desde la interfaz. |
| `SOL/integrations.py` | Adaptadores simulados y HTTP vía Bus. | Cambiar este borde permite incorporar las APIs del Bus sin reescribir las pantallas. Todavía deben ratificarse los contratos reales. |
| `SOL/security.py` | Hash de contraseñas y tokens. | No se guarda la clave en texto y el rol se obtiene de la sesión del servidor. |
| `SOL/seed.py` | Cuentas y referencias sintéticas para probar. | Un cliente activo no equivale automáticamente a Captación habilitada. |
| `SOL/manage.py` | Creación explícita y comprobación de la BD local. | No se ejecuta automáticamente el SQL de todo el banco. |
| `SOL/tests/` | Pruebas de límites, permisos y flujo. | Se verifica que reintentar no duplique expedientes y que subsanar no altere la versión enviada. |

## Frontend

| Archivo | Responsabilidad |
|---|---|
| `app/solicitud-credito/page.tsx` | Acceso, bandeja, formulario por pasos, detalle, calendario, historial y consola separada de pruebas EVA. Tipos TypeScript documentan lo que muestra la interfaz. |
| `app/solicitud-credito/sol.css` | Variables de color y diseño responsive. Los estilos están limitados al módulo para no modificar otros equipos. |
| `app/solicitud-credito/layout.tsx` | Título, descripción y ámbito visual del módulo. |
| `app/api/solicitud-credito/[...path]/route.ts` | Puente del lado servidor entre navegador y gateway. Mantiene el token en cookie HttpOnly y no expone la URL interna en el navegador. |

## Archivos añadidos en v2

| Archivo | Para explicarlo sin tecnicismos |
|---|---|
| `SOL/clock.py` | Todos los cálculos de fecha consultan el mismo reloj de Lima. Las evidencias conservan instantes UTC. |
| `SOL/operations.py` | Guarda los envíos y eventos pendientes, consulta si EVA recibió un envío y recupera el trabajo tras una caída. |
| `SOL/observability.py` | Registra identificadores y duración de cada operación sin claves ni datos de cliente. Calcula p95 con muestras reales del proceso. |
| `SOL/migrations.py` | Añade las columnas/tablas de la actualización conservando los expedientes anteriores. |
| `SOL/simulator.py` | Servidor HTTP de práctica, no conectado al banco. Permite verificar las rutas propuestas. |
| `SOL/tests/test_integration_v2.py` | Pruebas del horario nocturno, adaptadores, callbacks, cola, sesiones, privacidad, monitoreo y migración. |

## Ejemplo de envío

1. El asesor revisa el expediente y pulsa enviar.
2. Next.js recibe la petición y adjunta el token de la sesión.
3. El gateway SIMULADO despacha al módulo SOL del mismo proceso; no es el Bus del proyecto.
4. SOL valida rol, revisión vigente, estado, política y verificación de Captación.
5. SOL reserva y congela la versión antes de contactar a EVA. En SIMULADO confirma el acuse local; en REAL responde 202 pendiente y el worker consulta/envía por HTTP. Solo con acuse válido pasa a EN_EVALUACION. El historial y su evento pendiente de auditoría se confirman juntos.
6. El navegador muestra el resultado confirmado. Si la base de datos falla, no informa éxito.

## Qué significa versionar

Supón una solicitud v1 de S/ 15 000. Se envía y EVA la observa. SOL crea v2, el asesor modifica el destino o el monto y vuelve a enviarla. V1 sigue mostrando su monto, destino, política y calendario originales. El resultado de v1 no puede aplicarse como si fuera de v2.

`revision` y `version` cumplen funciones distintas: la versión identifica el expediente; la revisión aumenta con cada modificación para detectar pestañas antiguas y evitar sobrescrituras.

## Datos y autoridad

Las referencias locales son sintéticas. No convierten a SOL en propietario de Clientes, Captación o Evaluación. La persistencia definitiva debe acordarse con Tecnología/CORE, porque el código base centraliza datos y el informe propone propiedad por módulo.

La sesión local y las cuatro cuentas son para la demostración. La conexión con Seguridad central debe reemplazar la autenticación local mediante un contrato homologado, sin aceptar roles o identidades desde el formulario.
