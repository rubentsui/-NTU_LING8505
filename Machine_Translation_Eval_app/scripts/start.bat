@echo off
echo Starting MT Evaluation App...

cd /d "%~dp0.."

:: Start Backend
start "MT Backend" cmd /k "cd backend && python -m pip install -r requirements.txt && python -m uvicorn main:app --reload"

:: Start Frontend (Checks if node is available)
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js is not installed. Please install Node.js to run the frontend.
    pause
    exit /b
)

start "MT Frontend" cmd /k "cd frontend && npm install && npm run dev"
