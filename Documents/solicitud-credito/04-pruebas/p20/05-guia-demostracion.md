> **Estado: HISTÓRICO.** Revisión documental: 2026-11-16. Rama/SHA de la fuente: conservar los declarados en el texto original.
> Documento principal: [README SOL](../../README.md). Registro de ejecución P20. Evidencia válida para aquella ejecución; no certifica disponibilidad actual ni homologación.

# Guía reproducible para demostración

Fecha: 2026-11-16 (America/Lima). Rama `feature/sol-integracion-cap-eva`; HEAD `988dc0776da282fbef306632fc86426b6e372376`. CAP `4ea5014bddb1a69289402f03b3fbc47c28cc9413`; EVA `57b0e2a34fd55fb96fd6245acc06a86536d220f8`. Sin merge, cherry-pick, cambio de rama, commit ni push.

## Inicio desde raíz

Requisitos: Python3 con biblioteca estándar, Git con los SHA CAP/EVA fijados, Docker/Compose local y permisos del socket, imágenes/dependencias descargables o en caché. No requiere pytest instalado en host. El launcher verifica configuración y genera todo lo privado fuera del repo.

```bash
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py
```

El comando construye aplicaciones originales, inicia solo el proyecto aleatorio exclusivo, configura auditoría académica SIMULADA, crea clientes por CAP, ejecuta decisiones EVA/callbacks, comprueba MySQL/negativos/recuperación y arranca frontend. No fusiona ramas. Si falla devuelve salida1 y conserva diagnóstico privado externo; no hace fallback. La primera construcción puede tardar varios minutos.

Para otro proyecto completamente limpio (puertos distintos):

```bash
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py --state /tmp/bna-integracion-final-clean.json --port 18130
```

El archivo --state solo referencia directorio privado, no contiene contraseñas. Las URLs efectivas se imprimen al finalizar. Default: COREDB18120,CAP18121,SOL18122,EVA18123,Next18124; con ejemplo limpio18130..18134. Cada proyecto tiene sus propias bases/secretos/redes. MySQL sin puertos host. APIs publicadas solo127.0.0.1.

## Credenciales seguras y Swagger

No existen claves compartidas versionadas. El launcher imprime la ruta externa privada; dentro de runtime/:

- COREDB/CAP/EVA: usuario académico `admin-lab`; clave en coredb-init.env, campo CORE_DB_ADMIN_INICIAL_PASSWORD. Solo el propietario puede abrir ese archivo; copiar valor a Swagger sin guardarlo en capturas/informes.
- SOL/Next.js: `asesor.bna`; clave en sol-init.env, SOL_INITIAL_PASSWORD. Supervisor/auditor locales usan la misma semilla académica de esta instancia; no son cuentas institucionales.
- El runner crea además una persona ANALISTA mediante API COREDB y usa su JWT real; su contraseña transitoria no se exporta. Para una demostración manual se puede autenticar admin-lab con permisos de analista o crear una persona nueva en POST /coredb/usuarios y conservar su clave privadamente.
- Tokens de servicio son distintos y están en archivos runtime de cada módulo. No pegar esos archivos completos en terminal compartida ni grabar Authorize de Swagger. No ejecutar docker compose config con salida pública.

Abrir `/docs` de los cuatro puertos. COREDB login devuelve JWT para Authorize de COREDB/CAP/EVA. SOL login devuelve sesión para Authorize de SOL. Callback requiere exclusivamente token de servicio propio, no sesión del asesor. Sus rutas están en OpenAPI, comprobadas por HTTP; no se automatizó interacción visual del navegador.

## Guion de 5–10 minutos

1. Mostrar consola: REAL HTTP entre COREDB/CAP/SOL/EVA; SIMULADO verificadores externos CAP y auditoría académica. Mostrar rama/SHA de manifiesto, sin runtime secreto.
2. CAP Swagger: el runner ya registró prospecto, caso, consentimientos, OTP de laboratorio, validaciones y habilitación. Mostrar ID caso/código cliente de evidencia. COREDB GET /coredb/clientes/{código} confirma ACTIVO; no exponer contactos/DNI en captura pública.
3. SOL Swagger o Next `/solicitud-credito`: iniciar asesor, mostrar política REAL, bandeja y una solicitud creada desde referencia CAP. Mostrar calendario PRELIMINAR, garantía sintética y versión1.
4. Explicar /send:202 es solo reserva local. En evidencia, mostrar GET de operación EVA200 con idSolicitud/version/idOperacion/idEvaluacion/ronda/acuse. EVA Swagger muestra expediente y situación financiera.
5. Mostrar API /decision de EVA y su envioSol ENTREGADO. SOL detalle muestra APROBADA. La evidencia contiene operación de resultado distinta, mismo expediente/evaluación/ronda y Outcome SQL único. No se usó demo-result.
6. Mostrar caso OBSERVADA→v2→APROBADA con v1 congelada y ronda2. Mostrar también RECHAZADA. Desde Next se pueden consultar esos estados sin rediseño de UI.
7. Mostrar duplicado callback200 reconocido y versión errónea409. Mostrar caída EVA: pendiente/intento1, restauración de API y confirmado/intento2 con misma operación, sin reiniciar MySQL.
8. Aclarar pendientes institucionales: política académica, fiadores/pago doble restringidos, SSO/TLS/auditoría central no homologados y datos tmpfs.

El runner revoca uno de sus clientes al final para comprobar el negativo; ese cliente no sirve para una solicitud manual nueva. El cliente de recuperación permanece habilitado y puede buscarse por nombre sintético en CAP/SOL; revalidar detalle siempre. Identificadores concretos están en evidencia. Los escenarios ya finalizados no admiten reedición; crear un borrador nuevo para una demostración manual.

## Evidencia y repetición

Dentro de la raíz privada: manifest.json (SHA/hashes/parches/puertos), evidence.json (sin secretos), regressions.json. La copia saneada versionable está en [evidencias.json](evidencias.json). Nunca versionar runtime/, credenciales, logs brutos ni fuentes exportadas. Repetir el comando en instancia activa añade escenarios sintéticos nuevos con operaciones únicas; cada reintento de operación se prueba sin duplicación. No limpia ni reinicia bases ajenas.

```bash
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py status
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py regressions
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py eva-regressions
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py frontend-regressions
```

Con instancia alternativa añadir el mismo --state a cada comando. EVA completa usa un tercer MySQL desechable, aislado de las bases del flujo; sus fixtures son destructivas solo ahí y el launcher lo detiene al terminar. No ejecutar manualmente esas fixtures contra otra URL.

## Parada segura

```bash
python3 Documents/solicitud-credito/laboratorio/demo_integracion.py stop
```

Con --state alternativo, repetirlo también en stop. Solo detiene ese proyecto, sin down-v ni eliminación de volúmenes. Se pierden datos de MySQL tmpfs; informes/manifiesto privados se conservan. El siguiente up crea una instancia nueva y conserva referencia a la anterior. La demo SOL SIMULADA original sigue disponible en `../demo/README.md`; no se modificó ni se fusionaron los dos laboratorios.

## Instancia actualmente verificada

Permanece activa la instancia limpia `/tmp/bna-integracion-final-clean.json`:

- COREDB: http://127.0.0.1:18130/docs
- CAP: http://127.0.0.1:18131/docs
- SOL: http://127.0.0.1:18132/docs
- EVA: http://127.0.0.1:18133/docs
- Next.js: http://127.0.0.1:18134/solicitud-credito

Para consultar/parar esta instancia añadir `--state /tmp/bna-integracion-final-clean.json`. El laboratorio inicial de depuración se detiene por separado y conserva sus evidencias privadas. Las rutas /tmp pueden desaparecer al reiniciar el equipo; el comando de inicio las reproduce con secretos nuevos.

Complementos ejecutados: acciones `dependency-checks` y `verify-running` con ese mismo --state. El primero ensaya403/422/503 y restaura COREDB en finally; el segundo verifica recursos y privacidad sin mostrar secretos. `refresh-tools` se utiliza solo al cambiar deliberadamente runners/tests y renueva su manifiesto; no modifica las fuentes bancarias exportadas.
