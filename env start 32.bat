@echo off
chcp 65001 >nul
title Python Venv Auto Launcher - 虚拟环境一键启动
cd /d %~dp0

set "venv_dir=env32"
set "req_file=requirements.txt"

:: 判断虚拟环境是否存在，不存在自动创建
if not exist "%venv_dir%\Scripts\activate.bat" (
    echo Virtual env not found, creating env folder
    python3-32 -m venv %venv_dir%
    echo Virtual environment created successfully
    echo.

    :: 激活虚拟环境
    call %venv_dir%\Scripts\activate.bat

    :: 判断依赖文件并安装
    if exist "%req_file%" (
        echo Found requirements.txt, start installing dependencies
        pip install -r %req_file%
        echo.
        echo All dependencies installed completely
    ) else (
        echo Warning: requirements.txt not found, skip dependency install
        echo.
    )
) else (
    :: 激活虚拟环境
    call %venv_dir%\Scripts\activate.bat
)

echo Virtual environment ready, input deactivate to exit venv
echo.

cmd /k