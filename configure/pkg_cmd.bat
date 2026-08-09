@echo off
setlocal enabledelayedexpansion
cd /d %~dp0
call ../env/Scripts/activate.bat

set "bat_dir=%~dp0"
set "version_file="
set "py="

for /f "delims=" %%i in ('dir /b "%bat_dir%version.txt" 2^>nul') do (
    set "version_file=%%i"
    echo version_file: !version_file!
    goto got_version_file
)
:got_version_file

for /f "delims=" %%i in ('dir /b "%bat_dir%*.py" 2^>nul') do (
    set "py=%%i"
    echo py: !py!
    goto start
)
:start

pyinstaller -w --onefile --version-file %version_file% --icon=../res/icons/logo.ico --paths=../ %py%

set "exe_name=!py:.py=.exe!"
copy /Y "dist\%exe_name%" "../%exe_name%"

timeout /t 3 /nobreak