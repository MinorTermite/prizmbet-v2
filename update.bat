@echo off
chcp 65001 >nul
title PRIZMBET - Update Matches

echo.
echo ====================================================================
echo PRIZMBET - Updating match lineup
echo ====================================================================
echo.

cd /d "%~dp0"
python winline_parser.py

echo.
echo ====================================================================
echo Update complete!
echo ====================================================================
echo.
echo Press any key to exit...
pause >nul
