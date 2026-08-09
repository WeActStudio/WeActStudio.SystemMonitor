@echo off
chcp 65001 >nul
cd /d %~dp0

set "venv_dir=env"

if exist "%venv_dir%" (
    rmdir /s /q "%venv_dir%"
    echo already deleted %venv_dir% folder
) else (
    echo %venv_dir% folder not found, no need to delete
)

set "venv_dir=env32"

if exist "%venv_dir%" (
    rmdir /s /q "%venv_dir%"
    echo already deleted %venv_dir% folder
) else (
    echo %venv_dir% folder not found, no need to delete
)

pause