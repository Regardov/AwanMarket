@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\local-site.ps1" -Stop
if errorlevel 1 (
    echo.
    echo AwanMarket could not complete the operation. See the message above.
    pause
    exit /b 1
)
exit /b 0
