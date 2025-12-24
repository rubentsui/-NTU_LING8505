@echo off
cd /d "%~dp0"
echo ========================================
echo Stopping Translation Dashboard (Docker)
echo ========================================
echo.
docker-compose down
echo.
echo Services stopped.
pause
