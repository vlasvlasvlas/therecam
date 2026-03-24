@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run_theremin.py
  goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
  python run_theremin.py
  goto :eof
)

echo Error: no se encontro Python en PATH.
echo Instala Python 3 desde https://www.python.org/downloads/
pause
exit /b 1
