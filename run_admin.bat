@echo off
:: Executa o PC Health Check & Auto-Fix com elevacao de Administrador
:: (texto sem acentos: o cmd.exe usa a pagina de codigo OEM e corromperia caracteres UTF-8)
title PC Health Check ^& Auto-Fix Launcher

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Privilegios de Administrador detectados!
) else (
    echo [!] Solicitando permissao de Administrador via UAC...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c ""%~f0""' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: Usa "python" se estiver no PATH; caso contrario, o launcher "py" do instalador oficial
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"

echo [*] Verificando dependencias Python...
%PY% -m pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorLevel% neq 0 (
    echo [-] Falha ao instalar dependencias. Verifique se o Python 3.9+ esta instalado.
    pause
    exit /b 1
)

echo [*] Inicializando PC Health Check ^& Auto-Fix...
%PY% main.py --no-elevate
if %errorLevel% neq 0 (
    echo.
    echo [-] O aplicativo encerrou com erro. Log: %LOCALAPPDATA%\PCHealthCheck\logs\app.log
    pause
)
