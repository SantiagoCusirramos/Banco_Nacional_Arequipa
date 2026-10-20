# =====================================================================
# iniciar_mysql.ps1
# Arranca el servidor MySQL 8.4 en Windows (sin servicio registrado).
# Uso:  .\iniciar_mysql.ps1
# =====================================================================
param(
  [string]$MysqlBin  = "C:\Program Files\MySQL\MySQL Server 8.4\bin",
  [string]$DataDir   = "C:\ProgramData\MySQL\MySQL Server 8.4\Data",
  [int]   $Port      = 3306
)

$ErrorActionPreference = "Stop"

$mysqld = Join-Path $MysqlBin "mysqld.exe"
if (-not (Test-Path -LiteralPath $mysqld)) { throw "No se encontro mysqld.exe en: $mysqld" }
if (-not (Test-Path -LiteralPath $DataDir)) { throw "No se encontro el datadir en: $DataDir" }

$yaCorriendo = Get-Process mysqld -ErrorAction SilentlyContinue
if ($yaCorriendo) {
  Write-Host "MySQL ya esta en ejecucion (PID: $($yaCorriendo.Id -join ', '))." -ForegroundColor Yellow
  return
}

# El datadir se pasa entre comillas por los espacios en la ruta.
$args = "--datadir=`"$DataDir`"", "--port=$Port"
Start-Process -FilePath $mysqld -ArgumentList $args -WindowStyle Hidden

Start-Sleep -Seconds 4
$proc = Get-Process mysqld -ErrorAction SilentlyContinue
if ($proc) {
  Write-Host "MySQL iniciado correctamente en el puerto $Port (PID: $($proc.Id -join ', '))." -ForegroundColor Green
} else {
  Write-Host "No se pudo confirmar el arranque de MySQL. Revisa si el puerto $Port esta ocupado." -ForegroundColor Red
}
