# =====================================================================
# verificar_bna.ps1
# Verifica que la base bna tenga todos los objetos esperados.
# Uso:  .\verificar_bna.ps1
#       .\verificar_bna.ps1 -Usuario root -Password "miclave"
# =====================================================================
param(
  [string]$MysqlBin = "C:\Program Files\MySQL\MySQL Server 8.4\bin",
  [string]$Usuario  = "root",
  [string]$Password = ""
)

$mysql = Join-Path $MysqlBin "mysql.exe"
if (-not (Test-Path -LiteralPath $mysql)) { throw "No se encontro mysql.exe en: $mysql" }
if (-not (Get-Process mysqld -ErrorAction SilentlyContinue)) {
  throw "MySQL no esta en ejecucion. Ejecuta primero: .\iniciar_mysql.ps1"
}

$cred = if ($Password -ne "") { "-p$Password" } else { "" }
$query = @"
USE bna;
SELECT 'tablas'  AS objeto, COUNT(*) AS cantidad FROM information_schema.tables   WHERE table_schema='bna' AND table_type='BASE TABLE'
UNION ALL SELECT 'vistas',   COUNT(*) FROM information_schema.views    WHERE table_schema='bna'
UNION ALL SELECT 'triggers', COUNT(*) FROM information_schema.triggers WHERE trigger_schema='bna'
UNION ALL SELECT 'routines', COUNT(*) FROM information_schema.routines WHERE routine_schema='bna'
UNION ALL SELECT 'eventos',  COUNT(*) FROM information_schema.events   WHERE event_schema='bna'
UNION ALL SELECT 'agencias', COUNT(*) FROM bna.agencia;
"@

cmd /c "`"$mysql`" -u $Usuario $cred -e `"$query`""

Write-Host ""
Write-Host "Esperado -> tablas: 66 | vistas: 9 | triggers: 7 | routines: 3 | eventos: 1 | agencias: 4" -ForegroundColor Cyan
