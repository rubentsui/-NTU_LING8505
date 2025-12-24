#!/bin/bash
echo "Starting MT Evaluation App..."

# Start Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload &
BACKEND_PID=$!

# Start Frontend
cd ../frontend
if command -v npm &> /dev/null; then
    npm install
    npm run dev &
    FRONTEND_PID=$!
else
    echo "Node.js is not installed. Please install Node.js to run the frontend."
fi

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

wait
