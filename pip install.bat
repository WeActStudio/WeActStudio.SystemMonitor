@echo off
echo Python Module Install

cd /d %~dp0
@set "PATH=C:\Windows\System32;.\Python\Scripts;.\Python"

:restart
set /p var="python -m pip install "
cls
echo Start install

python -m pip install %var% --target .\Python\Lib\site-packages
REM python -m pip install %var%

goto restart