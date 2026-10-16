# Base de Datos Unificada BNA (MySQL 8.0/8.4)

Banco Nacional de Arequipa (BNA) — modelo relacional unificado, generado desde
los documentos de `Archivos que se tienen` (8 módulos + catálogos compartidos).

- **Motor:** MySQL 8.0 / 8.4 · **InnoDB** · **utf8mb4 / utf8mb4_0900_ai_ci**
- **Base de datos:** `bna`
- **Claves:** todos los `id_*` son **UUID v7** en `CHAR(36)` (ordenables por tiempo).
- **Fecha de generación:** 2026-10-15

## Estructura de archivos

| Archivo | Contenido |
|---|---|
| `01_catalogos_comunes.sql` | Catálogos y tablas compartidas (agencia, empleado, canal, moneda, contabilidad, auditoría, etc.) |
| `02_clientes_kyc.sql` | Cliente, biometría, OTP y auditoría de validación (KYC) |
| `03_cuentas.sql` | Cuentas de ahorro, titulares, transacciones, retenciones, topes, intereses |
| `04_tarjetas.sql` | Tarjetas, credenciales, matriz, tokens, intentos, autorizaciones, historial, outbox |
| `05_captacion.sql` | Solicitante, caso, consentimiento, validaciones, consultas/reportes de riesgo, perfil |
| `06_solicitud.sql` | Solicitud, fiador, garantía, historial de estado, calendario y cuotas |
| `07_evaluacion.sql` | Reglas, situación financiera, evaluación y decisión del analista |
| `08_desembolso.sql` | Orden, validación, evento de entrega, auditoría y reversión |
| `09_cobranza.sql` | Crédito, cuotas, pagos, aplicación de pago, mora y auditoría |
| `10_seed_catalogos.sql` | Carga inicial de catálogos y datos de prueba |
| `11_vistas.sql` | Vistas de negocio |
| `12_triggers_eventos.sql` | Triggers, evento (vencimiento) y procedimientos |
| `13_consultas.sql` | Consultas C01–C11 de Tarjetas y CRUD por módulo |
| `99_bna_unificado.sql` | **Todo en uno** (ejecuta los scripts anteriores en orden) |
| `diccionario_datos.md` | Diccionario de datos |
| `mer_bna.mermaid` | Diagrama entidad-relación (Mermaid) |
| `GUIA_EJECUCION.md` | **Guía paso a paso para el equipo** |
| `iniciar_mysql.ps1` | Arranca el servidor MySQL |
| `cargar_bna.ps1` | Carga (borra y recrea) la base `bna` |
| `verificar_bna.ps1` | Verifica los conteos de objetos |
| `detener_mysql.ps1` | Detiene el servidor MySQL |

## Cómo cargar la base (resumen)

> **Guía completa y solución de problemas en [`GUIA_EJECUCION.md`](GUIA_EJECUCION.md).**

Con los scripts incluidos:

```powershell
.\iniciar_mysql.ps1    # 1. Arranca el servidor MySQL
.\cargar_bna.ps1       # 2. Carga (borra y recrea) la base bna
.\verificar_bna.ps1    # 3. Verifica: 66 tablas, 9 vistas, 7 triggers
.\detener_mysql.ps1    # 4. Detiene el servidor
```

Comando manual equivalente (el `cmd /c` es necesario para que el `<` funcione en PowerShell):

```powershell
cmd /c '"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root < "99_bna_unificado.sql"'
```

> Nota: `99_bna_unificado.sql` empieza con `DROP DATABASE IF EXISTS bna; CREATE DATABASE bna`,
> por lo que **recrea la base desde cero** y garantiza una carga limpia.
> En MySQL Shell (mysqlsh) el `\source` no ejecutó bien el `DROP`; usa el cliente
> `mysql.exe` o borra la base a mano antes (ver `GUIA_EJECUCION.md`, sección 2).


## Mejoras aplicadas (Informe de revisión + Feedback)

- **IDs UUID v7:** todas las claves primarias y foráneas pasaron de
  `BIGINT UNSIGNED AUTO_INCREMENT` a `CHAR(36)` con **UUID v7**. La aplicación
  genera los v7; para las filas que crea la base (triggers y el procedimiento de
  pago) se usa la función `fn_uuid_v7()` definida en `12_triggers_eventos.sql`.
  El seed usa literales v7 fijos para seguir siendo idempotente.
- Enums **con valores** (no vacíos) en todas las tablas.
- `ENGINE=InnoDB` y `utf8mb4` explícitos; `DATETIME(3)` con `DEFAULT CURRENT_TIMESTAMP(3)` sin comillas.
- Eliminados los índices `UNIQUE` duplicados sobre PK.
- **Seguridad:** biometría cifrada (algoritmo/versión/hash), OTP con **HMAC** + propósito + vigencia, credenciales con `algoritmo_hash`/`version_hash`, PAN tokenizado, reversión con **autorizador distinto** y transacción de reposición.
- **Contabilidad multimoneda:** moneda, tipo de cambio e importe en moneda base en `asiento_detalle`; periodos contables.
- **Transacciones de cuenta:** contraparte, saldo posterior, fecha valor, comisión, ITF, retención e idempotencia.
- **Cobranza:** la aplicación de pago separa capital/interés/seguro/mora; una sola mora vigente por cuota (columna generada + UNIQUE).
- **Tablas faltantes añadidas:** `usuario_sistema`, `moneda`, `tipo_cambio`, `terminal`, `producto_ahorro`, `producto_credito`, `periodo_contable`, `cta_retencion_saldo`, `auditoria_evento`.
- **Auditoría centralizada** en `auditoria_evento`; historial de estados inmutable en Tarjetas.
- **Índices de consulta** en las llaves foráneas y campos de filtrado frecuente.

## Decisiones de reconciliación

- Se conservan **todas** las tablas documentadas de los 8 módulos (no se elimina/fusiona ninguna),
  y las mejoras del Feedback se aplican como **adiciones/endurecimiento** de diseño y seguridad.
