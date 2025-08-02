#!/bin/bash

# CAPP Startup Script
# This script starts both the CAPP backend and frontend

echo "🚀 Starting CAPP (Canza Autonomous Payment Protocol)"
echo "=================================================="

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $1 is already in use"
        return 1
    else
        echo "✅ Port $1 is available"
        return 0
    fi
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r applications/capp/requirements.txt

# Check ports
echo "🔍 Checking port availability..."
check_port 8000 || exit 1
check_port 3000 || exit 1

# Start backend in background
echo "🔧 Starting CAPP Backend (FastAPI) on port 8000..."
cd /Users/chikau/Desktop/CAPP
source venv/bin/activate
python -m uvicorn applications.capp.capp.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend started successfully"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend in background
echo "🎨 Starting CAPP Frontend (React) on port 3000..."
cd /Users/chikau/Desktop/CAPP/applications/capp/capp-frontend
npm start &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 5

# Check if frontend started successfully
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend started successfully"
else
    echo "❌ Frontend failed to start"
    kill $FRONTEND_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🎉 CAPP is now running!"
echo "=================================================="
echo "📊 Backend API: http://localhost:8000"
echo "🎨 Frontend:    http://localhost:3000"
echo "📚 API Docs:    http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping CAPP services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Keep script running
wait 