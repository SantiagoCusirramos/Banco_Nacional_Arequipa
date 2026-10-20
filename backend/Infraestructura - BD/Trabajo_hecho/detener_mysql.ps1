# =====================================================================
# detener_mysql.ps1
# Detiene el servidor MySQL en Windows.
# Uso:  .\detener_mysql.ps1
# =====================================================================
$proc = Get-Process mysqld -ErrorAction SilentlyContinue
if ($proc) {
  $proc | Stop-Process -Force
  Start-Sleep -Milliseconds 800
  $rest = Get-Process mysqld -ErrorAction SilentlyContinue
  if ($rest) {
    Write-Host "Algunos procesos mysqld siguen activos. Reintenta como Administrador." -ForegroundColor Red
  } else {
    Write-Host "MySQL detenido correctamente." -ForegroundColor Green
  }
} else {
  Write-Host "MySQL no estaba en ejecucion." -ForegroundColor Yellow
}
