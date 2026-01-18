#!/bin/bash
set -e

echo "🚀 Starting CAPP Developer Setup..."

# 1. Install System Dependencies (if brew available)
if command -v brew &> /dev/null; then
    echo "📦 Checking system deps..."
    # brew install postgresql redis
else
    echo "⚠️  Homebrew not found, skipping system deps."
fi

# 2. Python Setup
echo "🐍 Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "📦 Installing Python Dependencies..."
pip install -r apps/api/requirements.txt
# If there are other requirements, add them here
# pip install -r packages/core/requirements.txt

# 3. Node.js Setup
echo "📦 Installing Node.js Dependencies..."
# Root package.json (Husky)
if [ -f "package.json" ]; then
    npm install
fi

# Frontend
if [ -f "apps/web/package.json" ]; then
    cd apps/web
    npm install
    cd ../..
fi

# 4. Environment Variables
echo "🔑 Configuring Environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env from template."
else
    echo "ℹ️  .env already exists."
fi

# 5. Git Hooks (Husky)
echo "🐶 Setting up Husky Git Hooks..."
# We assume husky is installed via npm in root or web, but if not, we try to init
# npm install husky --save-dev
# npx husky install
# For this script, we'll just echo the instruction as we don't want to enforce npm init in root if not there.
echo "   (Skipping Husky auto-install to avoid modifying package.json without permission)"

echo "✅ Setup Complete!"
echo "RUN: ./start-capp.sh"
