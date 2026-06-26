@echo off
title Bela Odontologia — Sistema de Gestao
color 0A
echo.
echo  =====================================================
echo   BELA ODONTOLOGIA  -  Sistema de Gestao da Clinica
echo  =====================================================
echo.
echo  Servidor  : http://localhost:5000
echo  Login     : admin@clinica.com  /  admin123
echo  Encerrar  : Ctrl+C
echo  =====================================================
echo.

set PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.6-windows-x86_64-none\python.exe

if not exist "%PYTHON%" (
    echo [ERRO] Python nao encontrado: %PYTHON%
    pause & exit /b 1
)

:: Abre o Chrome maximizado apos 2 segundos (em background)
start /b powershell -WindowStyle Hidden -Command ^
  "Start-Sleep 2; $chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'; $edge = 'C:\Program Files\Microsoft\Edge\Application\msedge.exe'; if (Test-Path $chrome) { Start-Process $chrome '--start-maximized http://localhost:5000' } elseif (Test-Path $edge) { Start-Process $edge '--start-maximized http://localhost:5000' } else { Start-Process 'http://localhost:5000' }"

:: Inicia o servidor Flask
"%PYTHON%" app.py
pause
