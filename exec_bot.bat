@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "Bot.py"
) else (
    echo Ambiente virtual .venv nao encontrado!
)