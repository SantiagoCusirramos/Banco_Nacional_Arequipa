# MVP funcional v2 — Solicitud de Crédito BNA

Esta entrega se basa en el ZIP del repositorio compartido. Incluye una interfaz Next.js y un servicio FastAPI para el módulo SOL. Trabaja con tu MySQL local y datos sintéticos. No necesita acceso de escritura a GitHub para ejecutarse.

La interfaz se encuentra en **http://localhost:3000/solicitud-credito**. La portada `/` del repositorio se conserva para no ocupar la pantalla de otro equipo.

## Si ya ejecutabas la v1: actualizar conservando tus datos

1. Respalda tu base `bna_sol_mvp` y conserva tus `.env.sol` y `.env.local` privados. No copies archivos sobre un backend que siga ejecutándose.
2. Lleva los archivos SOL de esta actualización a tu carpeta del proyecto; consulta `CAMBIOS_SOL.md`. No reemplaces cambios de otros equipos.
3. Desde **backend**, ejecuta:

```powershell
.\.venv-sol\Scripts\python.exe -m pip install -r requirements-sol.txt
.\.venv-sol\Scripts\python.exe -m SOL.manage migrate
.\.venv-sol\Scripts\python.exe -m pytest SOL/tests -q
.\.venv-sol\Scripts\python.exe -m uvicorn SOL.app:app --host 127.0.0.1 --port 8011
```

`migrate` añade tablas/columnas sin borrar solicitudes, versiones o claves. No necesitas crear otro entorno virtual ni repetir `init`. Mantén `SOL_INTEGRATION_MODE=SIMULADO` para seguir con la demo; las nuevas variables HTTP pueden quedar vacías. Reinicia `npm run dev` en la terminal del frontend. `/ready` comprueba acceso a MySQL.

**Para practicar el modo HTTP o coordinar la integración:** sigue `Documents/solicitud-credito/CONTRATOS_HTTP_V2.md`. Activar REAL requiere las rutas y tokens; no basta cambiar una URL. Las reglas de negocio y contratos siguen pendientes de homologación.

## Qué hace esta versión

- Acceso de personal con permisos validados en el servidor.
- Selección de cliente habilitado por Captación simulada.
- Registro y edición de condiciones, garantías declaradas y referencias de fiadores.
- Cálculo de calendario preliminar con Decimal y política versionada.
- Guardado persistente de borradores en MySQL.
- Envío con acuse a Evaluación simulada; control de duplicados y versión congelada.
- Recepción de observaciones, creación de otra versión, corrección y reenvío.
- Consulta de resultados, historial, versiones y exportación de expediente JSON.

El asesor del banco completa los datos. El cliente es la persona solicitante y no necesita una cuenta en esta primera interfaz. No se ha aprobado un canal de autoservicio para clientes en este MVP.

## Antes de empezar

Necesitas Git solo si vas a clonar/publicar. Para ejecutar el ZIP son necesarios **Python 3.11+**, **Node.js compatible con Next.js 16 (20.9+; recomendado 22 LTS)** y **MySQL 8.0+ encendido**. Abre la carpeta de este proyecto en Visual Studio Code.

Esta entrega no usa la BD compartida `bna`. Crea `bna_sol_mvp` para probar sin competir con el CORE por sus datos. El cambio a persistencia compartida requiere ratificar propiedad y contratos. No ejecutes `99_bna_unificado.sql` para iniciar este laboratorio.

## 1. Preparar el backend en Windows / PowerShell

Desde la carpeta raíz del proyecto:

```powershell
cd backend
py -3 -m venv .venv-sol
.\.venv-sol\Scripts\python.exe -m pip install -r requirements-sol.txt
Copy-Item .env.sol.example .env.sol
```

Si `py` no está disponible pero `python --version` muestra 3.11+, reemplaza `py -3` por `python` en el comando que crea el entorno.

Abre `backend/.env.sol` y reemplaza `SOL_DB_PASSWORD` por tu contraseña de MySQL. Ajusta usuario y puerto si no utilizas `root` / 3306. Puedes envolver la clave entre comillas si contiene espacios o `#`. No compartas ese archivo.

```dotenv
SOL_DB_HOST=127.0.0.1
SOL_DB_PORT=3306
SOL_DB_USER=root
SOL_DB_PASSWORD="TU_CLAVE_MYSQL"
SOL_DB_NAME=bna_sol_mvp
SOL_INTEGRATION_MODE=SIMULADO
```

Inicializa la base de datos:

```powershell
.\.venv-sol\Scripts\python.exe -m SOL.manage init
```

El comando crea la BD del laboratorio y sus tablas. Necesita que el usuario MySQL pueda crear esa BD y sus tablas. Si tu cuenta no tiene permiso, pide a Infraestructura que prepare una BD local con nombre permitido y permisos sobre ella. El comando solicitará **una clave de acceso al portal de al menos 12 caracteres**, sin mostrarla al escribir. Esta clave es diferente de tu contraseña MySQL. Recuérdala: será la clave inicial de las cuatro cuentas DEMO.

Volver a ejecutar `init` no borra solicitudes ni cambia claves de cuentas ya existentes. Para un laboratorio nuevo se puede usar `SOL_DB_NAME=bna_sol_mvp_otro` e inicializar esa BD.

Levanta el servicio:

```powershell
.\.venv-sol\Scripts\python.exe -m uvicorn SOL.app:app --host 127.0.0.1 --port 8011
```

Deja esta terminal abierta. Puedes comprobar http://127.0.0.1:8011/health y consultar los endpoints en http://127.0.0.1:8011/docs.

## 2. Preparar el frontend

Abre **otra terminal** en la raíz del proyecto:

```powershell
cd frontend
Copy-Item .env.sol.example .env.local
npm ci
npm run dev
```

El comando de copia es para una carpeta nueva. Si ya tienes `.env.local`, conserva su contenido y agrega `SOL_GATEWAY_URL=http://127.0.0.1:8011/gateway/sol` en una línea nueva. Deja `SOL_COOKIE_SECURE=false` mientras uses HTTP en localhost.

Abre **http://localhost:3000/solicitud-credito**. Si Next.js anuncia otro puerto porque 3000 ya está ocupado, usa el puerto que aparezca en la terminal. Mantén un mismo host al navegar; `localhost` y `127.0.0.1` tienen cookies separadas.

## 3. Cuentas de la demostración

Todas usan inicialmente la clave que elegiste en `SOL.manage init`.

| Usuario | Función | Permisos |
|---|---|---|
| `asesor.bna` | Trabajador que prepara la solicitud | Crear, editar borradores, enviar y subsanar. |
| `supervisor.bna` | Supervisión del módulo | Consultar, sin modificar ni decidir. |
| `auditor.bna` | Revisión de trazabilidad | Consultar, sin modificar ni decidir. |
| `evaluador.demo` | Simulador separado de EVA | Emitir resultados de prueba de las versiones enviadas. |

Son cuentas del laboratorio, no identidades del banco conectadas a Seguridad. La pantalla de Evaluación simulada no equivale a desarrollar el módulo EVA ni a un motor de riesgo. El asesor no puede invocar sus acciones aunque intente llamar directamente al backend.

## 4. Primera prueba de extremo a extremo

1. Ingresa como `asesor.bna` y crea una solicitud.
2. Selecciona Juan Perez Quispe o Lucía Torres Mamani. Los demás casos muestran controles de bloqueo, observación o verificación vencida.
3. Registra por ejemplo S/ 15 000, 12 meses y destino «Mejoras en la vivienda».
4. Deja los respaldos vacíos para el caso simple o agrega una garantía y/o fiador de referencia.
5. Calcula, revisa el calendario y pulsa «Guardar y enviar».
6. Consulta el historial: debe aparecer un acuse de EVA simulada y la versión congelada.
7. Cierra sesión; ingresa como `evaluador.demo`, abre la solicitud y envía OBSERVADO con una observación de prueba.
8. Vuelve como asesor. Abre la solicitud y pulsa «Subsanar en nueva versión».
9. Corrige los datos, guarda y reenvía. La versión 1 debe conservar sus condiciones.
10. Desde `evaluador.demo`, envía APROBADO o RECHAZADO para la nueva versión.
11. Consulta el resultado como asesor. No se desembolsa dinero.
12. Reinicia el backend y vuelve a consultar: los expedientes deben seguir guardados en MySQL.

## 5. Cambiar montos, plazos o tasa

Edita **`backend/SOL/config/politica_demo.json`**. Es la fuente central; no necesitas buscar cifras en componentes de interfaz.

- `monto_minimo` / `monto_maximo`: cadenas decimales, por ejemplo `"1000.00"`.
- `plazo_minimo_meses` / `plazo_maximo_meses`: enteros.
- `tea`: fracción anual efectiva; `"0.2200"` significa 22 %, no 0,22 %.
- `version`: aumenta el identificador cada vez que cambies una regla.
- `estado_aprobacion` y textos de origen: registra acuerdo, fuente y vigencia cuando se ratifiquen.

Guarda el archivo y actualiza la pantalla. El servidor lo vuelve a leer. Una política inválida bloquea operaciones nuevas; no vuelve silenciosamente a valores anteriores. Si un borrador se calculó con otra política, debe guardarse otra vez para recalcular antes del envío. Las versiones enviadas conservan su política y calendario originales.

Los importes se almacenan en snapshots como cadenas decimales y se calculan con Decimal. El laboratorio usa documentos JSON para preservar la versión completa; esto no cambia las tablas DECIMAL del CORE ni crea un nuevo estándar institucional.

Cambiar límites, tasa y plazo está soportado. Habilitar una fórmula nueva, pago doble, cargos, moneda fuera del catálogo local o un producto diferente requiere desarrollar y probar su regla; un booleano no implementa una fórmula financiera. En este perfil los respaldos son registrables, pero su obligatoriedad automática no está aprobada.

## 6. Si todavía no tienes acceso de escritura a GitHub

Puedes ejecutar y modificar este ZIP localmente. Para publicar después, envía al propietario tu usuario de GitHub y pídele que te invite desde Settings → Collaborators → Add people. Acepta la invitación. Que puedas descargar/clonar el repositorio no acredita permiso de escritura.

Cuando tengas acceso, clona el repositorio y selecciona la rama existente `solicitud_credito`. Revisa primero el estado de esa rama y contrasta el archivo `CAMBIOS_SOL.md`: copia únicamente esos cambios. Conserva `.git` del clon; no sustituyas toda la carpeta del proyecto compartido con el ZIP.

Si el equipo prefiere trabajar con forks, puedes publicar en un fork de tu cuenta y presentar un Pull Request al repositorio original. No necesitas crear un proyecto nuevo sin relación con el actual.

## 7. Verificación y problemas comunes

Desde `backend`:

```powershell
.\.venv-sol\Scripts\python.exe -m SOL.manage check
.\.venv-sol\Scripts\python.exe -m pytest SOL/tests -q
```

`check` verifica tu conexión MySQL y cuenta solicitudes. Las pruebas usan por defecto una BD SQLite temporal y no modifican tus expedientes. Para la suite sobre MySQL se debe preparar exclusivamente `bna_sol_mvp_test` y pasar `SOL_TEST_DATABASE_URL`; las pruebas borran y recrean solo sus tablas de laboratorio en esa BD. Nunca utilices una BD compartida para pruebas destructivas.

Desde `frontend`, `npm run lint` y `npm run build` verifican la interfaz. La construcción del layout original usa Geist mediante Next/font y puede necesitar acceso a Google Fonts durante la primera compilación.

| Mensaje | Qué revisar |
|---|---|
| «No se pudo acceder a MySQL» | Servicio encendido, puerto, usuario/clave de `.env.sol` y ejecución de `init`. |
| «No se pudo contactar al servicio SOL» | Backend iniciado en 8011; variable SOL_GATEWAY_URL correcta; reiniciar Next tras modificar `.env.local`. |
| «Usuario o contraseña incorrectos» | Cuenta del laboratorio y clave elegida durante `init`, no la clave MySQL. |
| «Demasiados intentos» | Esperar cinco minutos antes de reintentar. |
| «La política cambió» | Editar/guardar el borrador para recalcular antes de enviarlo. |
| «La solicitud cambió en otra sesión» | Actualizar el detalle; no sobrescribir desde una pestaña antigua. |
| Cliente deshabilitado | Es uno de los casos de prueba de Captación; seleccionar un caso habilitado. |

## Límites que deben declararse en la sustentación

Persistencia local en MySQL y lógica de SOL funcionales. Captación y Evaluación se simulan; el Bus corporativo y Seguridad central no están conectados. La auditoría tiene historial local y cola persistente. Incluye adaptador HTTP con acuse central, pendiente de validación contra Seguridad institucional. No es un repositorio certificado como inmutable. Pago doble, documentos adjuntos, cambios de condiciones propuestos por EVA, traspaso final de calendario, desembolso y cobranza no se implementan en esta entrega. La identidad visual y las políticas siguen siendo propuestas para revisión.

Consulta `Documents/solicitud-credito/LECTURA_DEL_CODIGO.md`, `CONTRATOS_DEMO.md`, `PROPUESTAS_Y_DECISIONES.md` y `VALIDACION.md` para explicar y coordinar la siguiente integración.
