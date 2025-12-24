@echo off
cd /d "%~dp0"
echo ========================================
echo Starting Translation Dashboard (Docker)
echo ========================================
echo.
echo Checking for Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not installed or not in PATH.
    echo Please install Docker Desktop first.
    pause
    exit /b
)

echo Building and starting services...
echo This may take a few minutes for the first time...
docker-compose up --build

pause
