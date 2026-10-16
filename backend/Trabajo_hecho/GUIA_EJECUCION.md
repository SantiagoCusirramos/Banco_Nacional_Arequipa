# Guía de ejecución — Base de datos BNA (MySQL 8.4)

Esta guía permite a **cualquier integrante del equipo** crear y cargar la base
de datos `bna` desde cero en su equipo con Windows.

- **Base de datos:** `bna`
- **Motor:** MySQL 8.0 / 8.4 · InnoDB · utf8mb4
- **Claves:** `id_*` como **UUID v7** (`CHAR(36)`); la app los genera.
- **Contenido:** 66 tablas, 9 vistas, 7 triggers, 2 procedimientos, 1 función y 1 evento
- **Carpeta del proyecto:** `Trabajo_hecho`

> `99_bna_unificado.sql` ya **elimina y recrea** la base, por lo que cada
> ejecución deja el esquema limpio y completo. No necesitas borrar nada a mano.

---

## 0. Requisitos

1. **MySQL Server 8.4** instalado (esta guía usa la ruta por defecto):
   `C:\Program Files\MySQL\MySQL Server 8.4`
2. Carpeta con los scripts: `C:\Users\Lenovo\Downloads\Trabajo de bubu\Trabajo_hecho`
   (o la ruta donde copies el proyecto).
3. PowerShell (incluido en Windows).
4. El datadir de MySQL inicializado en:
   `C:\ProgramData\MySQL\MySQL Server 8.4\Data`

> Ajusta las rutas de los scripts si guardas el proyecto en otra ubicación.

---

## 1. Arrancar el servidor MySQL

El servidor no está registrado como servicio, así que se levanta manualmente.
**Elige una opción.**

### Opción A — Script automático (recomendado)

Abre PowerShell **en la carpeta del proyecto** y ejecuta:

```powershell
.\iniciar_mysql.ps1
```

### Opción B — Comando manual

```powershell
Start-Process -FilePath "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" `
  -ArgumentList "--datadir=`"C:\ProgramData\MySQL\MySQL Server 8.4\Data`"","--port=3306" `
  -WindowStyle Hidden
```

> **IMPORTANTE:** el valor de `--datadir` debe ir con comillas porque la carpeta
> tiene espacios ("MySQL Server 8.4"). Si no, el servidor no arranca con el error
> `Failed to set datadir`.

### Comprobar que arrancó

```powershell
Get-Process mysqld
```

Debe listar uno o más procesos `mysqld`. También puedes probar la conexión:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -e "SELECT VERSION();"
```

---

## 2. Cargar la base de datos

### Opción A — Script automático (recomendado)

```powershell
.\cargar_bna.ps1
```

### Opción B — Comando manual (método confiable)

Desde PowerShell, usando `cmd`:

```powershell
cmd /c '"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root < "C:\Users\Lenovo\Downloads\Trabajo de bubu\Trabajo_hecho\99_bna_unificado.sql"'
```

Si `root` tiene contraseña, agrega `-p` (te la pedirá):

```powershell
cmd /c '"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p < "C:\Users\Lenovo\Downloads\Trabajo de bubu\Trabajo_hecho\99_bna_unificado.sql"'
```

### Opción C — Desde MySQL Shell (mysqlsh)

> **Advertencia:** en MySQL Shell el comando `\source` **no ejecutó bien el
> `DROP DATABASE`** durante las pruebas. Si usas esta vía, **borra la base a
> mano primero**:

```
\connect root@localhost:3306
DROP DATABASE IF EXISTS bna;
\source "C:/Users/Lenovo/Downloads/Trabajo de bubu/Trabajo_hecho/99_bna_unificado.sql"
```

---

## 3. Verificar que todo cargó

Ejecuta (o usa el script `verificar_bna.ps1`):

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -e "
USE bna;
SELECT COUNT(*) AS tablas FROM information_schema.tables   WHERE table_schema='bna' AND table_type='BASE TABLE';
SELECT COUNT(*) AS vistas  FROM information_schema.views    WHERE table_schema='bna';
SELECT COUNT(*) AS triggers FROM information_schema.triggers WHERE trigger_schema='bna';
SELECT COUNT(*) AS routines FROM information_schema.routines WHERE routine_schema='bna';
SELECT COUNT(*) AS eventos  FROM information_schema.events   WHERE event_schema='bna';
SELECT * FROM agencia;"
```

**Resultado esperado:**

| Objeto | Cantidad |
|---|---|
| Tablas | 66 |
| Vistas | 9 |
| Triggers | 7 |
| Procedimientos (routines) | 3 |
| Eventos | 1 |
| Agencias (seed) | 4 |

Si obtienes esas cifras, la carga fue correcta.

---

## 4. Detener el servidor

```powershell
Stop-Process -Name mysqld -Force
```

O usa el script:

```powershell
.\detener_mysql.ps1
```

---

## 5. Estructura de archivos

| Archivo | Descripción |
|---|---|
| `01_catalogos_comunes.sql` | Catálogos y tablas compartidas (agencia, empleado, canal, moneda, contabilidad, auditoría…) |
| `02_clientes_kyc.sql` | Cliente, biometría, OTP, auditoría de validación |
| `03_cuentas.sql` | Cuentas de ahorro, titulares, transacciones, retenciones, topes, intereses |
| `04_tarjetas.sql` | Tarjetas, credenciales, matriz, tokens, intentos, autorizaciones, historial, outbox |
| `05_captacion.sql` | Solicitante, caso, consentimiento, validaciones, consultas/reportes, perfil |
| `06_solicitud.sql` | Solicitud, fiador, garantía, historial, calendario y cuotas |
| `07_evaluacion.sql` | Reglas, situación financiera, evaluación y decisión del analista |
| `08_desembolso.sql` | Orden, validación, evento de entrega, auditoría y reversión |
| `09_cobranza.sql` | Crédito, cuotas, pagos, aplicación de pago, mora y auditoría |
| `10_seed_catalogos.sql` | Carga inicial de catálogos y datos de prueba |
| `11_vistas.sql` | Vistas de negocio |
| `12_triggers_eventos.sql` | Triggers, evento de vencimiento y procedimientos |
| `13_consultas.sql` | Consultas C01–C11 de Tarjetas y CRUD por módulo |
| `99_bna_unificado.sql` | **Todo en uno** (borra y recrea `bna`; úsalo para cargar) |
| `diccionario_datos.md` | Diccionario de datos (66 tablas) |
| `mer_bna.mermaid` | Diagrama entidad-relación (Mermaid) |
| `iniciar_mysql.ps1` | Arranca el servidor MySQL |
| `cargar_bna.ps1` | Carga el script unificado |
| `verificar_bna.ps1` | Verifica conteos de objetos |
| `detener_mysql.ps1` | Detiene el servidor |
| `README.md` | Resumen del proyecto |

---

## 6. Carga individual por módulo (opcional)

Si prefieres cargar por partes (por ejemplo para depurar), el orden de
dependencias es:

```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13
```

Cada archivo hace `USE bna;`, pero **solo `01` crea la base**. Para cargar
individualmente:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root bna < "01_catalogos_comunes.sql"
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root bna < "02_clientes_kyc.sql"
# ... y así sucesivamente
```

---

## 7. Solución de problemas

| Síntoma | Causa / Solución |
|---|---|
| `Can't connect to MySQL server ... (10061)` | El servidor está apagado. Ejecuta `iniciar_mysql.ps1` (paso 1). |
| `Failed to set datadir to 'C:\ProgramData\MySQL\MySQL\'` | Falta comillas en `--datadir`. Usa el comando del paso 1 (Opción B) con comillas. |
| `ERROR 1007 ... Can't create database 'bna'; database exists` | El `DROP DATABASE` del script no corrió (típico en mysqlsh). Ejecuta la carga con `mysql.exe` (paso 2, Opción B) o borra la base antes. |
| `ERROR 1050 (42S01): Table '...' already exists` | La base tenía tablas previas. Vuelve a ejecutar `99_bna_unificado.sql`: empieza con `DROP DATABASE IF EXISTS bna`. |
| `Unknown column '...'` / vistas que no se crean | Estás usando una base antigua. Recarga con `99_bna_unificado.sql` (borra y recrea). |
| Warning `Data truncated for column 'regla_negocio'` | Ya corregido (columna ampliada a `VARCHAR(40)`). Usa la versión actual del archivo. |
| Warning `Integer display width is deprecated` | Aviso informativo de MySQL 8.4 por `TINYINT(1)`; es inofensivo. |
| `ERROR 1452 ... foreign key constraint fails` al final del script | Corregido en `13_consultas.sql` (se crea la cuota antes de aplicar el pago). Usa la versión actual. |

---

## 8. Notas de seguridad

- Los usuarios y contraseñas de `10_seed_catalogos.sql` (`admin123`, etc.) son
  **de ejemplo/prueba**. Cámbialos antes de cualquier uso real:
  `UPDATE usuario_sistema SET hash_password=SHA2('NUEVA_CLAVE',256) WHERE username='admin.bna';`
- El script asume `root` sin contraseña (entorno de desarrollo). En producción,
  configura un usuario dedicado con contraseña y permisos mínimos.
- La base creada es de **desarrollo/pruebas**.

---

## 9. Restablecer todo (borrón y cuenta nueva)

No hace falta borrar nada: `99_bna_unificado.sql` **elimina y recrea** `bna`.
Simplemente repite el paso 2 y el paso 3.
