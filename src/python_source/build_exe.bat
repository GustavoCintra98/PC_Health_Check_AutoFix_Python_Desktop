@echo off
:: Script para compilar o PC Health Check & Auto-Fix em um executável autônomo (.exe) com UAC embutido
title Compilador PyInstaller - PC Health Check

echo [*] Instalando PyInstaller...
pip install pyinstaller

echo [*] Compilando executavel com manifesto de Administrador (uac-admin)...
pyinstaller --noconsole --onefile --uac-admin --name="PC_Health_Check_AutoFix" --hidden-import="wmi" --hidden-import="win32timezone" main.py

echo.
echo [OK] Compilacao concluida! O executavel esta na pasta: dist/PC_Health_Check_AutoFix.exe
pause
