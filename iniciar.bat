@echo off
title Bela Odontologia — Sistema de Gestao
color 0A
echo.
echo  =====================================================
echo   BELA ODONTOLOGIA  -  Sistema de Gestao da Clinica
echo  =====================================================
echo.
echo  Banco de dados: MySQL (bela_odontologia)
echo  Servidor web  : http://localhost:5000
echo.
echo  Login padrao:
echo    E-mail : admin@clinica.com
echo    Senha  : admin123
echo.
echo  Pressione Ctrl+C para encerrar.
echo  =====================================================
echo.

set PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.6-windows-x86_64-none\python.exe

if not exist "%PYTHON%" (
    echo [ERRO] Python nao encontrado em: %PYTHON%
    echo Verifique a instalacao do Python e edite este arquivo.
    pause
    exit /b 1
)

:: Abre o navegador apos 2 segundos
start /b cmd /c "timeout /t 2 >nul && start http://localhost:5000"

"%PYTHON%" app.py
pause
