$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 run_theremin.py
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python run_theremin.py
    exit $LASTEXITCODE
}

Write-Host 'Error: no se encontro Python en PATH.' -ForegroundColor Red
Write-Host 'Instala Python 3 desde https://www.python.org/downloads/' -ForegroundColor Yellow
Read-Host 'Presiona Enter para cerrar'
exit 1
