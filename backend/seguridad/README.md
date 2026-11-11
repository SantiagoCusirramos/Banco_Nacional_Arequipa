# Módulo 9 · Seguridad · Prototipo local v0.2.0

Prototipo de laboratorio independiente de MySQL y del Bus. Corre como servicio aparte; no está montado en `main:app`. No autentica ni protege automáticamente los endpoints preexistentes `/core`. No sustituye la base de identidades del CORE. No mueve dinero.

## Instalación reproducible

Desde la raíz del repositorio (Python 3.11+):

```bash
python3 -m venv .venv-seguridad
.venv-seguridad/bin/pip install -r backend/requirements-seguridad.txt
cd backend
cp seguridad/.env.example .env.seguridad.local
# Editar .env.seguridad.local: asignar SEGURIDAD_SECRET_KEY aleatoria.
# Para generar el valor: openssl rand -hex 32
set -a
source .env.seguridad.local
set +a
../.venv-seguridad/bin/python -m seguridad.manage create-user admin.local --role ADMINISTRADOR
../.venv-seguridad/bin/python -m seguridad.manage create-user cliente.local --role CLIENTE
cd ..
backend/seguridad/run_local.sh
```

Consola: http://127.0.0.1:8013 · API: http://127.0.0.1:8013/docs.
El puerto 8013 evita interferir con el CORE (8000), CUENTAS (8001), SOL (8011) y COREDB (8012). No se necesita frontend Next.js para la consola técnica. El servidor escucha exclusivamente en loopback.

En este equipo ya se crearon `admin.demo`, `cliente.demo` y `auditor.demo`. La contraseña aleatoria está en `backend/.env.seguridad.local`, campo `DEMO_PASSWORD`, solo para la demostración local; no se incluye en informes, capturas ni control de versiones. No es una cuenta del banco.

## Contratos

Todas las rutas `/seguridad/*` requieren `X-Correlation-ID` (1–100 caracteres alfanuméricos, `_ . : -`). Las protegidas requieren `Authorization: Bearer <token>`.

| Ruta | Método | Permiso |
|---|---|---|
| `/seguridad/estado` | GET | Público, solo estado de laboratorio |
| `/seguridad/auth/login` | POST | Credenciales locales |
| `/seguridad/auth/me` | GET | Usuario autenticado |
| `/seguridad/auth/logout` | POST | Revoca todas las sesiones del usuario |
| `/seguridad/operaciones/evaluar` | POST | CLIENTE, ADMINISTRADOR |
| `/seguridad/auditoria` | GET | AUDITOR, ADMINISTRADOR; últimos 100 eventos |
| `/seguridad/auditoria/verificar` | GET | AUDITOR, ADMINISTRADOR |
| `/seguridad/incidentes` | GET | AUDITOR, OPERADOR, ADMINISTRADOR |
| `/seguridad/incidentes` | POST | OPERADOR, ADMINISTRADOR |
| `/seguridad/incidentes/{id}` | PATCH | OPERADOR, ADMINISTRADOR |

Login JSON: `{"username":"cliente.local","password":"<contraseña-local>"}`. No incluir credenciales en URLs.
JWT HS256, emisor `bna-seguridad`, audiencia `bna-modulos`, expiración 15 minutos. El rol y estado se consultan en servidor. Argon2id: 64 MiB, 3 iteraciones, paralelismo 4. Al tercer fallo se bloquea 15 minutos e invalida sesiones anteriores. Rechazos genéricos con 401. El bloqueo afecta la identidad sintética, **no la tarjeta ni el ATM físico**.

Evaluación JSON:
```json
{"operation_id":"prueba-00001","amount":"850.00","currency":"PEN","channel":"ATM"}
```
Topes locales por usuario/canal/moneda/día de Lima: ATM 1000, HOME_BANKING 5000, BILLETERA 500. Decimal exacto; moneda PEN/USD sin conversión. El servidor calcula el acumulado de decisiones autorizadas; **no es saldo ni consumo bancario confirmado**. La autorización queda contabilizada localmente aunque el canal no ejecute una transacción; no hay confirmación/cancelación con M3.

Más de 80% requiere desafío simulado de 120 s; respuesta incluye `challenge_id` y `demo_otp`. Reenviar ambos como `challenge_id` y `otp`, conservando los demás campos. Tres fallos agotan ese desafío; está ligado a usuario, operación, monto, canal y moneda. **El código se muestra por el mismo canal: no demuestra segundo factor real.**

La operación usa `operation_id` como clave idempotente global de demostración: repetir datos devuelve el resultado original; cambiar datos devuelve 409. No se usa `X-Idempotency-Key` porque no hay operación que afecte saldo. El Bus debe homologar la correlación de ambas claves antes de operar con M3.

Auditoría HMAC encadenada: detecta alteraciones intermedias; sin anclaje externo no detecta truncado final, borrado total o reescritura con acceso a la clave. No es SIEM ni almacenamiento inmutable. Solo registra datos permitidos, sin contraseñas ni JWT ni OTP. La clave local firma JWT y usa separación de dominio para la auditoría; separar llaves y custodia HSM antes de producción.

Incidente: ABIERTO → EN_PROGRESO → RESUELTO (requiere descripción) → CERRADO. SLA son objetivos propuestos, no resultados medidos ni calendario hábil institucional. Registro y seguimiento manual; no hay avisos ni escalamiento automático.

## Pruebas

```bash
cd backend
../.venv-seguridad/bin/python -m pytest seguridad/tests
```

19 casos. Incluye tokens inválidos/vencidos, bloqueo, roles, topes, desafío, idempotencia concurrente, manipulación de auditoría, incidentes y backup/restauración. Las pruebas del CORE no acreditan disponibilidad de MySQL ni integración bancaria.

## Copia y restauración

```bash
cd backend
set -a; source .env.seguridad.local; set +a
../.venv-seguridad/bin/python -m seguridad.manage backup
```

Copia consistente mediante SQLite Backup API. Conservar la clave por separado. Para restaurar: detener el servidor, copiar el respaldo a otra ruta, configurar `SEGURIDAD_DB` hacia esa ruta conservando la clave y verificar `/auditoria/verificar`. No sobrescribir datos sin copia previa. No se midieron RTO/RPO institucionales.

## Pendientes para interoperabilidad / producción

1. Comité de Tecnología: aprobar contrato e identidad del servicio, ubicación de datos y responsabilidad de topes.
2. CORE: exponer autenticación, ampliar esquema para hash robusto (actual CHAR(64)), migrar SHA256/bcrypt con pruebas y proteger rutas existentes con catálogo RBAC. Las identidades locales NO se migraron ni vincularon.
3. M8: Bus real, propagación de identidad/correlación, autenticación entre servicios, TLS/mTLS y políticas de reintentos.
4. M3/M4/M5/M6/M7: homologar topes, reservas/confirmación, Token Matriz, bloqueo de tarjeta, extorno y flujos por canal.
5. Integrar segundo factor por canal independiente, RENIEC/biometría, SMS, HSM y SIEM.
6. Protección contra tráfico abusivo por IP/usuario, gestión de claves, retención, control de acceso a respaldos, monitoreo, carga y revisión de seguridad.
7. Infraestructura/Calidad: Testing institucional, despliegue, redundancia, recuperación y pruebas de integración con evidencias.

El almacenamiento SQLite es una decisión temporal de laboratorio, no un cambio aprobado al estándar MySQL. No se afirma cumplimiento SBS/PCI ni disponibilidad bancaria.
