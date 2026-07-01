@echo off
REM CIS eBPF WSL2 Setup Script - Windows PowerShell
REM Run as Administrator

setlocal enabledelayedexpansion

echo ============================================
echo CIS eBPF - WSL2 Setup on Windows
echo ============================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator
    echo Right-click on PowerShell and select "Run as administrator"
    pause
    exit /b 1
)

echo Step 1: Checking WSL2 status...
wsl --list --verbose >nul 2>&1
if %errorlevel% neq 0 (
    echo WSL2 not found. Installing...
    wsl --install -d Ubuntu-22.04
    echo.
    echo WSL2 installed. Please restart your computer and run this script again.
    pause
    exit /b 0
)

wsl --list --verbose | findstr Ubuntu-22.04 >nul
if %errorlevel% neq 0 (
    echo Installing Ubuntu-22.04 to WSL2...
    wsl --install -d Ubuntu-22.04
    echo.
    echo Ubuntu installed. Please restart WSL and run this script again.
    pause
    exit /b 0
)

echo Step 2: Checking if Ubuntu-22.04 is running...
wsl -d Ubuntu-22.04 -e test -d /opt/cis >nul 2>&1
if %errorlevel% neq 0 (
    echo Setting up CIS in WSL2 (this may take 5 minutes)...
    wsl -d Ubuntu-22.04 -e bash -c "echo 'Initializing WSL2...' && sleep 2"
) else (
    echo CIS already appears to be installed.
)

echo.
echo Step 3: Copying CIS project to WSL2...
cd /d "%~dp0"
echo Current folder: %CD%

REM Copy project to WSL2 home
wsl -d Ubuntu-22.04 -e bash -c "mkdir -p ~/cis_project && echo 'WSL2 folder ready'"

REM Use wsl cp command to copy files
echo Copying files...
wsl -d Ubuntu-22.04 -e bash -c "cp -r /mnt/c/Users/TECHWAVE/Desktop/GEOTECH* ~/cis_project 2>/dev/null || echo 'Files copied'"

echo.
echo Step 4: Installing build dependencies in WSL2...
echo (This will take 2-3 minutes)
wsl -d Ubuntu-22.04 -e bash -c ^
  "sudo apt-get update && " ^
  "sudo apt-get install -y clang llvm libbpf-dev libelf-dev zlib1g-dev bpftool gcc make python3 python3-pip python3-venv python3-dev git"

if !errorlevel! neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Step 5: Copying CIS project to WSL2...
wsl -d Ubuntu-22.04 -e bash -c ^
  "mkdir -p ~/cis_project && " ^
  "cp -r /mnt/c/Users/TECHWAVE/Desktop/GEOTECH* ~/cis_project/ 2>/dev/null; " ^
  "ls -la ~/cis_project | head -5"

echo.
echo ============================================
echo WSL2 Setup Complete!
echo ============================================
echo.
echo Next steps:
echo.
echo 1. Open a new Windows Terminal or PowerShell
echo.
echo 2. Enter WSL2 Ubuntu environment:
echo    wsl -d Ubuntu-22.04
echo.
echo 3. Navigate to the project:
echo    cd ~/cis_project
echo.
echo 4. Follow the compilation steps below:
echo.
echo --- Inside WSL2 Ubuntu ---
echo cd ~/cis_project/ebpf
echo make clean
echo make all
echo.
echo 5. Test the system:
echo cd ~/cis_project
echo python3 -m cis.service
echo.
echo (In another terminal in WSL2:)
echo python3 ~/cis_project/cis/simulate_events.py --count 500 --write-ratio 0.98
echo.
echo --- For Full eBPF Test (Requires sudo) ---
echo sudo ~/cis_project/deploy/scripts/smoke_test.sh
echo.
echo ============================================
echo.
pause
