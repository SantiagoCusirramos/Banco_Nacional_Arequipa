# =====================================================================
# cargar_bna.ps1
# Carga (borra y recrea) la base de datos bna usando el script unificado.
# Uso:  .\cargar_bna.ps1
#       .\cargar_bna.ps1 -Usuario root -Password "miclave"
# =====================================================================
param(
  [string]$MysqlBin = "C:\Program Files\MySQL\MySQL Server 8.4\bin",
  [string]$Usuario  = "root",
  [string]$Password = "",
  [string]$Script   = "99_bna_unificado.sql"
)

$ErrorActionPreference = "Stop"

$mysql  = Join-Path $MysqlBin "mysql.exe"
$raiz   = Split-Path -Parent $MyInvocation.MyCommand.Path
$sqlFile = Join-Path $raiz $Script

if (-not (Test-Path -LiteralPath $mysql))   { throw "No se encontro mysql.exe en: $mysql" }
if (-not (Test-Path -LiteralPath $sqlFile)) { throw "No se encontro el script: $sqlFile" }

if (-not (Get-Process mysqld -ErrorAction SilentlyContinue)) {
  throw "MySQL no esta en ejecucion. Ejecuta primero: .\iniciar_mysql.ps1"
}

$cred = if ($Password -ne "") { "-p$Password" } else { "" }
$cmdLine = "`"$mysql`" -u $Usuario $cred < `"$sqlFile`""

Write-Host "Cargando $Script en la base bna ..." -ForegroundColor Cyan
$salida = cmd /c $cmdLine 2>&1
$errores = $salida | Select-String -Pattern '^ERROR'

if ($errores) {
  Write-Host "Se produjeron errores durante la carga:" -ForegroundColor Red
  $errores | ForEach-Object { Write-Host $_ -ForegroundColor Red }
  exit 1
} else {
  Write-Host "Carga completada SIN errores." -ForegroundColor Green
  Write-Host "Ejecuta .\verificar_bna.ps1 para comprobar los conteos." -ForegroundColor Green
}
