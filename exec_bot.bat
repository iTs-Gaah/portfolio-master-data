@echo off
cd /d "C:\Users\usuario_1\VS Code\Dashboard"

if exist "C:\Users\usuario_1\VS Code\.venv\Scripts\python.exe" (
    "C:\Users\usuario_1\VS Code\.venv\Scripts\python.exe" "C:\Users\usuario_1\VS Code\Dashboard\Bot.py"
) else (
    echo Ambiente virtual .venv nao encontrado!
)