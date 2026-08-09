@echo off
chcp 65001 >nul
title Python Venv Auto Launcher
cd /d %~dp0

set "venv_dir=env"
call %venv_dir%\Scripts\activate.bat

python build_release.py -sq -c

set "venv_dir=env32"
call %venv_dir%\Scripts\activate.bat

python build_release.py -s

pause