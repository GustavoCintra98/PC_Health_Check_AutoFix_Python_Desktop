@echo off
:: Batch script para executar o PC Health Check & Auto-Fix com elevação de Administrador direta
title PC Health Check & Auto-Fix Launcher

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Privilégios de Administrador detectados!
) else (
    echo [!] Solicitando permissão de Administrador via UAC...
    powershell -Command "Start-Process cmd -ArgumentList '/c ""%~dp0run_admin.bat""' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo [*] Verificando dependencias Python...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check

echo [*] Inicializando PC Health Check & Auto-Fix...
python main.py
if %errorLevel% neq 0 (
    echo.
    echo [-] O aplicativo encerrou com erro.
    pause
)
