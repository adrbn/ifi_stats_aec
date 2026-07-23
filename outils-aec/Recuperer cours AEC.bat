@echo off
REM Double-clic (Windows) -> ouvre l'outil OSCAR (fenetre + logs en direct).
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" oscar_tool.py
) else (
    py oscar_tool.py
)
pause
