@echo off
chcp 65001 >nul
title PRIZMBET - Setup Auto Update

echo.
echo ====================================================================
echo PRIZMBET - Setup Automatic Update
echo ====================================================================
echo.
echo This script will create a Windows Task Scheduler task
echo to automatically update matches every day at 00:00
echo.
echo Press any key to continue or close window to cancel...
pause >nul

echo.
echo Creating task...

set "SCRIPT_PATH=%~dp0update.bat"

schtasks /create /tn "PRIZMBET_AutoUpdate" /tr "%SCRIPT_PATH%" /sc daily /st 00:00 /f

if %errorlevel% equ 0 (
    echo.
    echo ====================================================================
    echo SUCCESS!
    echo ====================================================================
    echo.
    echo Task created successfully!
    echo Matches will update automatically every day at 00:00
    echo.
    echo You can:
    echo - Open Windows Task Scheduler to change schedule
    echo - Find task "PRIZMBET_AutoUpdate"
    echo - Change run time
    echo.
) else (
    echo.
    echo ====================================================================
    echo ERROR
    echo ====================================================================
    echo.
    echo Failed to create task.
    echo Possible reasons:
    echo - Insufficient permissions (run as administrator)
    echo - Task Scheduler is disabled
    echo.
)

echo.
echo Press any key to exit...
pause >nul
