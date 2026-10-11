@echo off
:: Compila o PC Health Check & Auto-Fix em um executavel autonomo (.exe) com manifesto UAC.
:: Toda a configuracao fica em PC_Health_Check_AutoFix.spec (fonte unica de verdade).
title Compilador PyInstaller - PC Health Check
cd /d "%~dp0"

set "PY=python"
where python >nul 2>&1 || set "PY=py -3"

echo [*] Instalando dependencias de build...
%PY% -m pip install -r requirements-dev.txt --quiet --disable-pip-version-check || goto :erro

echo [*] Executando testes...
%PY% -m pytest -q || goto :erro

echo [*] Compilando executavel...
%PY% -m PyInstaller --clean --noconfirm PC_Health_Check_AutoFix.spec || goto :erro

echo.
echo [OK] Compilacao concluida! Executavel: dist\PC_Health_Check_AutoFix.exe
pause
exit /b 0

:erro
echo.
echo [-] Falha na compilacao.
pause
exit /b 1
