#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Stopping services..."
    kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT

echo "🚀 Starting CAPP System..."

# Add current directory to PYTHONPATH to ensure packages are found
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Start Backend
echo "Starting Backend (Port 8000)..."
python3 -m uvicorn apps.api.app.main:app --reload --port 8000 &

# Start Frontend
echo "Starting Frontend (Port 3000)..."
cd apps/web
npm run dev

wait
