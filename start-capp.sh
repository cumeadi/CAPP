#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# CAPP DEMO launcher
#
# This starts the DEMO stack: the demo API (apps/api — App A) paired with the
# demo web frontend (apps/web). It exists to showcase SDK/API capabilities.
#
# This is NOT the production service. The production API is App B:
#   applications/capp/capp/main.py  (served at /api/v1, deployed via Dockerfile)
#
# To run the production API locally instead:
#   python3 -m uvicorn applications.capp.capp.main:app --reload --port 8000
# ─────────────────────────────────────────────────────────────────────────────

# Function to kill processes on exit
cleanup() {
    echo "Stopping demo services..."
    kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT

echo "🚀 Starting CAPP DEMO (App A + web frontend)..."

# Add current directory to PYTHONPATH to ensure packages are found
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Start Demo Backend (App A)
echo "Starting demo API (apps/api, Port 8000)..."
python3 -m uvicorn apps.api.app.main:app --reload --port 8000 &

# Start Demo Frontend
echo "Starting demo frontend (apps/web, Port 3000)..."
cd apps/web
npm run dev

wait
