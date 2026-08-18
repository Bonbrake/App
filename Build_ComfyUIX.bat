@echo off
title ComfyUIX - Build & Package System
cd /d "c:\Users\jakeb\Documents\antigravity\silly-tesla"
echo ========================================================
echo               ComfyUIX Automatic Builder
echo ========================================================
echo.
echo Building PyInstaller binary and Inno Setup installer...
echo.
python build_exe.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed! Check the output above.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo ========================================================
echo [SUCCESS] Build & Packaging complete!
echo Installer created at: dist\ComfyUIX_Setup.exe
echo ========================================================
echo.
pause
