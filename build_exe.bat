@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Installing build dependencies...
py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [2/3] Building standalone Windows executable...
py -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name CosmicByteAccentSync --collect-all hid cosmic_byte_accent_sync.py
if errorlevel 1 goto :error

echo.
echo [3/3] Build complete.
echo EXE location: %~dp0dist\CosmicByteAccentSync.exe
echo.
echo To enable automatic startup, right-click install_startup.ps1 and choose
echo "Run with PowerShell", or run it from a PowerShell window.
pause
exit /b 0

:error
echo.
echo BUILD FAILED. Check the error messages above.
pause
exit /b 1
