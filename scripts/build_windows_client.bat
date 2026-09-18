@echo off
REM scripts/build_windows_client.bat
REM Unotusk MVP Employee Client — Windows x64 Build & Packaging Script
REM Target: Windows 10 / 11 64-bit

setlocal enabledelayedexpansion

echo ================================================================
echo  UNOTUSK EMPLOYEE CLIENT — WINDOWS x64 RELEASE BUILD
echo ================================================================

REM 1. Verify Flutter SDK
where flutter >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Flutter SDK not found in PATH.
    echo Please install Flutter 3.x and ensure it is in your system PATH.
    exit /b 1
)

REM 2. Verify Visual Studio C++ Toolchain
set VS_FOUND=0
if exist "%ProgramFiles%\Microsoft Visual Studio\Installer\vswhere.exe" (
    for /f "usebackq tokens=*" %%i in (`"%ProgramFiles%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
        set "VS_PATH=%%i"
        set VS_FOUND=1
    )
)
if %VS_FOUND% neq 1 (
    where cl.exe >nul 2>&1
    if %ERRORLEVEL% equ 0 set VS_FOUND=1
)

if %VS_FOUND% neq 1 (
    echo [WARNING] Visual Studio 2022 C++ Desktop development workload not detected.
    echo If the build fails, install Visual Studio with "Desktop development with C++".
)

REM 3. Navigate to app root
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%\app"

echo [1/4] Running flutter pub get...
call flutter pub get
if %ERRORLEVEL% neq 0 (
    echo [ERROR] flutter pub get failed.
    exit /b %ERRORLEVEL%
)

echo [2/4] Building Windows release binary (x64)...
call flutter build windows --release
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Flutter Windows build failed.
    exit /b %ERRORLEVEL%
)

set "RELEASE_DIR=%ROOT_DIR%\app\build\windows\x64\runner\Release"
if not exist "%RELEASE_DIR%" (
    echo [ERROR] Release folder not found at %RELEASE_DIR%
    exit /b 1
)

echo [3/4] Packaging release distribution into dist\...
set "DIST_DIR=%ROOT_DIR%\dist"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

set "ZIP_OUT=%DIST_DIR%\unotusk-employee-windows-x64.zip"
if exist "%ZIP_OUT%" del /f /q "%ZIP_OUT%"

powershell -NoProfile -Command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath '%ZIP_OUT%' -Force"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PowerShell archive compression failed.
    exit /b %ERRORLEVEL%
)

echo [4/4] Computing SHA256 checksum...
set "CHECKSUM_FILE=%ZIP_OUT%.sha256"
powershell -NoProfile -Command "(Get-FileHash -Path '%ZIP_OUT%' -Algorithm SHA256).Hash | Out-File -FilePath '%CHECKSUM_FILE%' -Encoding ascii"

echo ================================================================
echo  BUILD SUCCESSFUL: Windows Employee Client
echo ================================================================
echo  Package:  %ZIP_OUT%
echo  Checksum: %CHECKSUM_FILE%
echo.
echo  PILOT RUNTIME NOTES:
echo  1. Copy %ZIP_OUT% to the employee Windows laptop.
echo  2. Extract the ZIP completely into a folder (e.g. C:\Unotusk).
echo  3. Run app.exe.
echo  4. If Windows SmartScreen appears ("Windows protected your PC"):
echo     Click "More info" -^> "Run anyway" (expected for unsigned pilot binaries).
echo  5. In the app, enter the Linux Server LAN address: http://^<SERVER_LAN_IP^>:8000
echo ================================================================
exit /b 0
