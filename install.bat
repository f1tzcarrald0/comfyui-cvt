@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ============================================
echo   SoraUtils Installer for ComfyUI
echo ============================================
echo.
echo A folder picker will open. Select:
echo   1) Your ComfyUI folder (contains custom_nodes), or
echo   2) Your portable root folder (contains ComfyUI\custom_nodes).
echo.

set "SELECTED_DIR="
for /f "delims=" %%I in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.FolderBrowserDialog; $f.Description = 'Select ComfyUI folder or portable root'; $f.ShowNewFolderButton = $false; if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath } else { '' }"') do set "SELECTED_DIR=%%I"

if "!SELECTED_DIR!"=="" (
    echo.
    echo Cancelled by user.
    goto :fail
)
if "!SELECTED_DIR:~-1!"=="\" set "SELECTED_DIR=!SELECTED_DIR:~0,-1!"

set "COMFY_DIR="
if exist "!SELECTED_DIR!\custom_nodes" set "COMFY_DIR=!SELECTED_DIR!"
if not defined COMFY_DIR if exist "!SELECTED_DIR!\ComfyUI\custom_nodes" set "COMFY_DIR=!SELECTED_DIR!\ComfyUI"

if not defined COMFY_DIR (
    echo.
    echo ERROR: Could not find custom_nodes in the selected location.
    echo        Selected: !SELECTED_DIR!
    echo.
    echo Select a ComfyUI folder or portable root folder.
    goto :fail
)
if "!COMFY_DIR:~-1!"=="\" set "COMFY_DIR=!COMFY_DIR:~0,-1!"

for %%A in ("!COMFY_DIR!\..") do set "COMFY_PARENT=%%~fA"
if "!COMFY_PARENT:~-1!"=="\" set "COMFY_PARENT=!COMFY_PARENT:~0,-1!"

echo.
echo Found ComfyUI at: !COMFY_DIR!

set "PYTHON_EXE="
set "PIP_EXE="
set "ENV_NOTE="
call :detect_python "!COMFY_DIR!" "!COMFY_PARENT!"
if defined ENV_NOTE echo !ENV_NOTE!

if not defined PYTHON_EXE if not defined PIP_EXE (
    echo.
    echo WARNING: Could not find ComfyUI's Python environment automatically.
    echo Looked for:
    echo   !COMFY_DIR!\venv\Scripts\python.exe
    echo   !COMFY_DIR!\.venv\Scripts\python.exe
    echo   !COMFY_DIR!\python_embeded\python.exe
    echo   !COMFY_DIR!\python_embedded\python.exe
    echo   !COMFY_DIR!\venv\Scripts\pip.exe
    echo   !COMFY_DIR!\.venv\Scripts\pip.exe
    echo   !COMFY_PARENT!\venv\Scripts\python.exe
    echo   !COMFY_PARENT!\.venv\Scripts\python.exe
    echo   !COMFY_PARENT!\python_embeded\python.exe
    echo   !COMFY_PARENT!\python_embedded\python.exe
    echo   !COMFY_PARENT!\venv\Scripts\pip.exe
    echo   !COMFY_PARENT!\.venv\Scripts\pip.exe
    call :manual_python_pick
)

set "SOURCE_DIR=%~dp0"
if "!SOURCE_DIR:~-1!"=="\" set "SOURCE_DIR=!SOURCE_DIR:~0,-1!"
set "DEST_DIR=!COMFY_DIR!\custom_nodes\SoraUtils"

echo.
echo Copying SoraUtils to: !DEST_DIR!
if exist "!DEST_DIR!" (
    echo Removing existing SoraUtils installation...
    rmdir /s /q "!DEST_DIR!"
)

robocopy "!SOURCE_DIR!" "!DEST_DIR!" /e /xd __pycache__ .git build dist installer .claude /xf install.bat install_macos.command build_installer.ps1 build_macos_pkg.sh *.spec >nul 2>&1

if exist "!SOURCE_DIR!\example_workflows" if not exist "!DEST_DIR!\example_workflows\" (
    echo example_workflows was missing after copy. Copying it explicitly...
    robocopy "!SOURCE_DIR!\example_workflows" "!DEST_DIR!\example_workflows" /e >nul 2>&1
)

if not exist "!DEST_DIR!\__init__.py" (
    echo.
    echo ERROR: Copy failed. Check folder permissions.
    goto :fail
)
if exist "!SOURCE_DIR!\example_workflows" if not exist "!DEST_DIR!\example_workflows\" (
    echo.
    echo WARNING: example_workflows could not be copied automatically.
)
echo Files copied successfully.

if defined PYTHON_EXE (
    echo.
    echo Installing Python dependencies with: !PYTHON_EXE!
    "!PYTHON_EXE!" -m pip install -r "!DEST_DIR!\requirements.txt"
    if !errorlevel! neq 0 (
        echo.
        echo WARNING: pip install had errors. You may need to install dependencies manually.
    ) else (
        echo Dependencies installed successfully.
    )
) else if defined PIP_EXE (
    echo.
    echo Installing Python dependencies with: !PIP_EXE!
    "!PIP_EXE!" install -r "!DEST_DIR!\requirements.txt"
    if !errorlevel! neq 0 (
        echo.
        echo WARNING: pip install had errors. You may need to install dependencies manually.
    ) else (
        echo Dependencies installed successfully.
    )
) else (
    echo.
    echo Dependencies were NOT installed automatically.
    echo Run this in your ComfyUI Python environment:
    echo   pip install -r "!DEST_DIR!\requirements.txt"
)

echo.
echo ============================================
echo   SoraUtils installed successfully!
echo   Restart ComfyUI to load the new nodes.
echo ============================================
echo.
pause
exit /b 0

:detect_python
set "CHECK_DIR=%~1"
set "CHECK_PARENT=%~2"

call :set_python_if_exists "%CHECK_DIR%\venv\Scripts\python.exe" "Found venv Python at:"
if defined PYTHON_EXE goto :eof
call :set_python_if_exists "%CHECK_DIR%\.venv\Scripts\python.exe" "Found .venv Python at:"
if defined PYTHON_EXE goto :eof
call :set_python_if_exists "%CHECK_DIR%\python_embeded\python.exe" "Found embedded Python at:"
if defined PYTHON_EXE goto :eof
call :set_python_if_exists "%CHECK_DIR%\python_embedded\python.exe" "Found embedded Python at:"
if defined PYTHON_EXE goto :eof

call :set_python_if_exists "%CHECK_PARENT%\venv\Scripts\python.exe" "Found parent venv Python at:"
if defined PYTHON_EXE goto :eof
call :set_python_if_exists "%CHECK_PARENT%\.venv\Scripts\python.exe" "Found parent .venv Python at:"
if defined PYTHON_EXE goto :eof
call :set_python_if_exists "%CHECK_PARENT%\python_embeded\python.exe" "Found parent embedded Python at:"
if defined PYTHON_EXE goto :eof
call :set_python_if_exists "%CHECK_PARENT%\python_embedded\python.exe" "Found parent embedded Python at:"
if defined PYTHON_EXE goto :eof

call :set_pip_if_exists "%CHECK_DIR%\venv\Scripts\pip.exe" "Found venv pip at:"
if defined PIP_EXE goto :eof
call :set_pip_if_exists "%CHECK_DIR%\.venv\Scripts\pip.exe" "Found .venv pip at:"
if defined PIP_EXE goto :eof
call :set_pip_if_exists "%CHECK_PARENT%\venv\Scripts\pip.exe" "Found parent venv pip at:"
if defined PIP_EXE goto :eof
call :set_pip_if_exists "%CHECK_PARENT%\.venv\Scripts\pip.exe" "Found parent .venv pip at:"
if defined PIP_EXE goto :eof
goto :eof

:set_python_if_exists
if exist "%~1" (
    set "PYTHON_EXE=%~1"
    set "ENV_NOTE=%~2 %~1"
)
goto :eof

:set_pip_if_exists
if exist "%~1" (
    set "PIP_EXE=%~1"
    set "ENV_NOTE=%~2 %~1"
)
goto :eof

:manual_python_pick
echo.
choice /c YN /n /m "Select ComfyUI python.exe manually now? [Y/N]: "
if errorlevel 2 goto :eof

set "MANUAL_PY="
for /f "delims=" %%I in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.OpenFileDialog; $f.Title = 'Select ComfyUI python.exe'; $f.Filter = 'Python executable (python.exe)|python.exe|Executable files (*.exe)|*.exe|All files (*.*)|*.*'; if ($f.ShowDialog() -eq 'OK') { $f.FileName } else { '' }"') do set "MANUAL_PY=%%I"

if "!MANUAL_PY!"=="" (
    echo Manual python selection cancelled.
    goto :eof
)

for %%P in ("!MANUAL_PY!") do set "MANUAL_NAME=%%~nxP"
if /i not "!MANUAL_NAME!"=="python.exe" (
    echo Selected file is not python.exe: !MANUAL_PY!
    goto :eof
)

set "PYTHON_EXE=!MANUAL_PY!"
set "PIP_EXE="
set "ENV_NOTE=Using manually selected Python at: !MANUAL_PY!"
echo !ENV_NOTE!
goto :eof

:fail
echo.
echo Installation failed.
echo.
pause
exit /b 1
