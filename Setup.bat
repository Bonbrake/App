@echo off
setlocal EnableDelayedExpansion
::============================================================================
:: ComfyUI Uncensored - Setup / Uninstall
::
:: Usage:
::   Setup.bat                 Install (link the engine, no large copy)
::   Setup.bat /copyengine     Install and physically COPY the engine (~90 GB)
::   Setup.bat /uninstall      Reverse everything this script created
::
:: No hardcoded user paths: every location derives from %LOCALAPPDATA%,
:: %USERPROFILE%, %APPDATA% or this script's own directory.
::============================================================================

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "APP_NAME=ComfyUI Uncensored"
set "EXE_NAME=ComfyUI_Uncensored.exe"
set "INSTALL_ROOT=%LOCALAPPDATA%\ComfyUIUncensored"
set "ENGINE_LINK=%INSTALL_ROOT%\ComfyUI_windows_portable"
set "DESKTOP_LNK=%USERPROFILE%\Desktop\%APP_NAME%.lnk"
set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "STARTMENU_LNK=%STARTMENU_DIR%\%APP_NAME%.lnk"

if /I "%~1"=="/uninstall" goto :UNINSTALL
if /I "%~1"=="--uninstall" goto :UNINSTALL

set "COPY_ENGINE=0"
if /I "%~1"=="/copyengine" set "COPY_ENGINE=1"

::============================================================================
:: INSTALL
::============================================================================
echo ============================================================
echo  %APP_NAME% - Setup
echo ============================================================
echo.

:: ---------------------------------------------------------------- [1] Python
:: Only required to RUN FROM SOURCE. A frozen EXE needs no Python at all.
set "HAVE_SOURCE=0"
if exist "%SCRIPT_DIR%\ComfyUI_App.py" set "HAVE_SOURCE=1"

set "PY_CMD="
if "%HAVE_SOURCE%"=="1" (
    echo [1/5] Checking for Python 3.11 ...
    py -3.11 -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3.11"
    ) else (
        python --version 2>nul | findstr /C:"Python 3.11" >nul
        if not errorlevel 1 set "PY_CMD=python"
    )
    if not defined PY_CMD (
        echo.
        echo   ERROR: Python 3.11 was not found on this system.
        echo   It is required to run this app from source.
        echo.
        echo   Download Python 3.11 ^(Windows installer^):
        echo     https://www.python.org/downloads/release/python-3119/
        echo.
        echo   Tick "Add python.exe to PATH" during installation, then re-run Setup.bat.
        echo.
        exit /b 1
    )
    echo       Found: !PY_CMD!
) else (
    echo [1/5] Frozen EXE install detected - Python is not required. Skipping.
)
echo.

:: ------------------------------------------------------------------- [2] venv
if "%HAVE_SOURCE%"=="1" (
    echo [2/5] Creating virtual environment and installing pinned dependencies ...
    if not exist "%SCRIPT_DIR%\requirements.lock.txt" (
        echo   ERROR: requirements.lock.txt not found next to Setup.bat.
        exit /b 1
    )
    if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%" >nul 2>&1
    !PY_CMD! -m venv "%INSTALL_ROOT%\.venv"
    if errorlevel 1 (
        echo   ERROR: virtual environment creation failed.
        exit /b 1
    )
    "%INSTALL_ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    "%INSTALL_ROOT%\.venv\Scripts\python.exe" -m pip install -r "%SCRIPT_DIR%\requirements.lock.txt" --quiet
    if errorlevel 1 (
        echo   ERROR: dependency installation failed.
        exit /b 1
    )
    echo       Dependencies installed from requirements.lock.txt
) else (
    echo [2/5] No source tree here - skipping virtual environment.
)
echo.

:: ------------------------------------------------------- [3] Copy app payload
echo [3/5] Installing application files to:
echo       %INSTALL_ROOT%
if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%" >nul 2>&1

set "EXE_SRC="
if exist "%SCRIPT_DIR%\%EXE_NAME%" set "EXE_SRC=%SCRIPT_DIR%\%EXE_NAME%"
if not defined EXE_SRC if exist "%SCRIPT_DIR%\dist\%EXE_NAME%" set "EXE_SRC=%SCRIPT_DIR%\dist\%EXE_NAME%"

if not defined EXE_SRC (
    echo.
    echo   ERROR: %EXE_NAME% not found next to Setup.bat or in .\dist\.
    echo   Build it first:  py -3.11 build_exe.py
    echo.
    exit /b 1
)

copy /Y "!EXE_SRC!" "%INSTALL_ROOT%\%EXE_NAME%" >nul
if errorlevel 1 (
    echo   ERROR: could not copy the executable.
    exit /b 1
)
echo       %EXE_NAME%

if exist "%SCRIPT_DIR%\assets" (
    if not exist "%INSTALL_ROOT%\assets" mkdir "%INSTALL_ROOT%\assets" >nul 2>&1
    xcopy /E /I /Y /Q "%SCRIPT_DIR%\assets" "%INSTALL_ROOT%\assets" >nul
    echo       assets\
)

:: Never overwrite an existing user configuration.
if exist "%SCRIPT_DIR%\config.json" (
    if exist "%INSTALL_ROOT%\config.json" (
        echo       config.json already present - keeping your settings
    ) else (
        copy /Y "%SCRIPT_DIR%\config.json" "%INSTALL_ROOT%\config.json" >nul
        echo       config.json
    )
)
echo.

:: ----------------------------------------------------------- [4] Engine setup
echo [4/5] Locating the ComfyUI portable engine ...

set "ENGINE_SRC="
call :CHECK_ENGINE "%COMFYUI_PORTABLE_DIR%"
if defined ENGINE_SRC goto :ENGINE_FOUND
call :CHECK_ENGINE "%SCRIPT_DIR%\ComfyUI_windows_portable"
if defined ENGINE_SRC goto :ENGINE_FOUND
call :CHECK_ENGINE "%SCRIPT_DIR%\..\ComfyUI_windows_portable"
if defined ENGINE_SRC goto :ENGINE_FOUND
call :CHECK_ENGINE "C:\ComfyUI-Desktop\ComfyUI_windows_portable"
if defined ENGINE_SRC goto :ENGINE_FOUND

echo.
echo       No existing engine found. MANUAL STEP REQUIRED:
echo.
echo         1. Download the ComfyUI Windows portable build:
echo              https://github.com/comfyanonymous/ComfyUI/releases
echo            ^(file: ComfyUI_windows_portable_nvidia.7z^)
echo         2. Extract it so this path exists:
echo              %ENGINE_LINK%\ComfyUI\main.py
echo         3. Put your .safetensors checkpoints in:
echo              %ENGINE_LINK%\ComfyUI\models\checkpoints\
echo.
echo       Alternatively, point the app at an engine you already have:
echo         setx COMFYUI_PORTABLE_DIR "D:\path\to\ComfyUI_windows_portable"
echo.
goto :SHORTCUTS

:ENGINE_FOUND
echo       Found engine: !ENGINE_SRC!

if exist "%ENGINE_LINK%\" (
    echo       Engine already present in the install folder - leaving it alone.
    goto :SHORTCUTS
)

if "%COPY_ENGINE%"=="1" (
    echo       Copying the engine ^(this is very large and may take a long time^) ...
    robocopy "!ENGINE_SRC!" "%ENGINE_LINK%" /E /NFL /NDL /NJH /NJS /NP >nul
    if exist "%ENGINE_LINK%\ComfyUI\main.py" (
        echo       Engine copied next to the executable.
    ) else (
        echo       ERROR: engine copy did not complete.
        exit /b 1
    )
    goto :SHORTCUTS
)

:: Default: directory junction - instant, uses no extra disk, needs no admin.
mklink /J "%ENGINE_LINK%" "!ENGINE_SRC!" >nul 2>&1
if exist "%ENGINE_LINK%\ComfyUI\main.py" (
    echo       Linked the engine into place ^(no disk space used^).
    echo       Use "Setup.bat /copyengine" if you want a real copy instead.
    goto :SHORTCUTS
)

:: Junction unavailable: fall back to the environment override, which the
:: application honours unconditionally ahead of all path probing.
setx COMFYUI_PORTABLE_DIR "!ENGINE_SRC!" >nul
echo       Could not create a link; set COMFYUI_PORTABLE_DIR instead.
echo       Sign out and back in ^(or reopen your shell^) for it to apply.

:SHORTCUTS
echo.

:: -------------------------------------------------------------- [5] Shortcuts
echo [5/5] Creating shortcuts ...
set "ICON_PATH=%INSTALL_ROOT%\%EXE_NAME%"
if exist "%INSTALL_ROOT%\assets\app_icon.ico" set "ICON_PATH=%INSTALL_ROOT%\assets\app_icon.ico"

call :MAKE_LNK "%DESKTOP_LNK%"
if exist "%DESKTOP_LNK%" (echo       Desktop shortcut) else (echo       WARNING: desktop shortcut failed)

if not exist "%STARTMENU_DIR%" mkdir "%STARTMENU_DIR%" >nul 2>&1
call :MAKE_LNK "%STARTMENU_LNK%"
if exist "%STARTMENU_LNK%" (echo       Start Menu entry) else (echo       WARNING: Start Menu entry failed)

echo.
echo ============================================================
echo  Setup complete.
echo    Installed to : %INSTALL_ROOT%
echo    Launch via   : the "%APP_NAME%" shortcut, or run the EXE directly
echo    To remove    : Setup.bat /uninstall
echo ============================================================
echo.
echo  Note: the EXE is unsigned, so Windows SmartScreen may warn on
echo  first launch. Choose "More info" then "Run anyway".
echo.
exit /b 0

::============================================================================
:: Helpers
::============================================================================
:CHECK_ENGINE
:: %~1 = candidate dir. Sets ENGINE_SRC only for a directory holding a real engine.
set "_CAND=%~1"
if "%_CAND%"=="" exit /b 0
if not exist "%_CAND%\" exit /b 0
for %%I in ("%_CAND%") do set "_CAND=%%~fI"
if exist "%_CAND%\ComfyUI\main.py" set "ENGINE_SRC=%_CAND%" & exit /b 0
if exist "%_CAND%\python_embeded\python.exe" set "ENGINE_SRC=%_CAND%" & exit /b 0
exit /b 0

:MAKE_LNK
:: %~1 = full .lnk path to create
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ^
 "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%~1');" ^
 "$s.TargetPath='%INSTALL_ROOT%\%EXE_NAME%';" ^
 "$s.WorkingDirectory='%INSTALL_ROOT%';" ^
 "$s.IconLocation='%ICON_PATH%';" ^
 "$s.Description='%APP_NAME%';" ^
 "$s.Save()" >nul 2>&1
exit /b 0

::============================================================================
:: UNINSTALL
::============================================================================
:UNINSTALL
echo ============================================================
echo  %APP_NAME% - Uninstall
echo ============================================================
echo.

echo Removing shortcuts ...
if exist "%DESKTOP_LNK%" (del /F /Q "%DESKTOP_LNK%" >nul 2>&1 & echo       Desktop shortcut removed)
if exist "%STARTMENU_LNK%" (del /F /Q "%STARTMENU_LNK%" >nul 2>&1 & echo       Start Menu entry removed)

echo Detaching the engine ...
if exist "%ENGINE_LINK%\" (
    :: A junction must be unlinked with rmdir so the real engine is untouched.
    dir /AL "%INSTALL_ROOT%" 2>nul | findstr /I "ComfyUI_windows_portable" >nul
    if not errorlevel 1 (
        rmdir "%ENGINE_LINK%" >nul 2>&1
        echo       Engine link removed ^(the real engine was NOT deleted^)
    ) else (
        echo       A real engine copy lives at:
        echo         %ENGINE_LINK%
        echo       It is left in place deliberately - it is very large and may
        echo       hold your models. Delete it by hand if you truly want it gone.
    )
)

echo Removing the environment override, if this installer set one ...
reg delete "HKCU\Environment" /F /V COMFYUI_PORTABLE_DIR >nul 2>&1
if not errorlevel 1 (echo       COMFYUI_PORTABLE_DIR cleared) else (echo       none set)

echo Removing application files ...
if exist "%INSTALL_ROOT%\%EXE_NAME%" del /F /Q "%INSTALL_ROOT%\%EXE_NAME%" >nul 2>&1
if exist "%INSTALL_ROOT%\assets" rmdir /S /Q "%INSTALL_ROOT%\assets" >nul 2>&1
if exist "%INSTALL_ROOT%\.venv" rmdir /S /Q "%INSTALL_ROOT%\.venv" >nul 2>&1
if exist "%INSTALL_ROOT%\config.json" del /F /Q "%INSTALL_ROOT%\config.json" >nul 2>&1
echo       Executable, assets, config and venv removed

:: Only remove the install root if nothing of the user's is left behind.
rmdir "%INSTALL_ROOT%" >nul 2>&1
if exist "%INSTALL_ROOT%\" (
    echo.
    echo Kept %INSTALL_ROOT%
    echo   ^(it still contains files this installer did not create^)
) else (
    echo.
    echo Install folder fully removed.
)

echo.
echo ============================================================
echo  Uninstall complete. Generated images in your Pictures folder
echo  were left untouched.
echo ============================================================
echo.
exit /b 0
