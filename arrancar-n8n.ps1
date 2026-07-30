# Arranca n8n local para este proyecto.
# Uso: parado en la carpeta del proyecto, en PowerShell:
#     .\arrancar-n8n.ps1
# Despues abrir http://localhost:5678
#
# La variable N8N_RESTRICT_FILE_ACCESS_TO NO es opcional. Desde n8n 2.x los
# nodos que tocan el disco solo pueden leer/escribir dentro de ~/.n8n-files.
# Sin ella, cualquier fase que lea el CSV falla con:
#     Access to the file is not allowed
# y parece un bug del workflow cuando es una restriccion de seguridad de n8n.

$ErrorActionPreference = "Stop"

# La carpeta donde vive este script = raiz del proyecto. Asi la ruta no queda
# hardcodeada: el script funciona aunque muevas la carpeta.
$raiz = $PSScriptRoot

$env:N8N_RESTRICT_FILE_ACCESS_TO = $raiz
$env:N8N_DIAGNOSTICS_ENABLED = "false"   # sin telemetria
$env:N8N_SECURE_COOKIE = "false"         # permite http://localhost sin HTTPS

Write-Host "Carpeta permitida para archivos: $raiz" -ForegroundColor Cyan
Write-Host "Arrancando n8n... la primera vez npx lo descarga (tarda unos minutos)." -ForegroundColor Cyan
Write-Host "Cuando diga 'Editor is now accessible', abri http://localhost:5678" -ForegroundColor Cyan
Write-Host ""

npx --yes n8n
