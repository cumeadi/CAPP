#!/bin/bash

# CAPP Phase 3 Quick Start Script
# This script sets up and runs the Phase 3 implementation

set -e  # Exit on any error

echo "🚀 CAPP Phase 3: Production Readiness Implementation"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r applications/capp/requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp env.example .env
    echo "📝 Please update .env file with your configuration"
fi

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Make the demo script executable
chmod +x scripts/phase3_implementation.py

echo ""
echo "🎯 Phase 3 Features Available:"
echo "✅ Complete database layer with PostgreSQL"
echo "✅ M-Pesa integration with STK Push"
echo "✅ Repository pattern for data access"
echo "✅ Database migrations with Alembic"
echo "✅ Production-ready async architecture"
echo "✅ Error handling and recovery"
echo "✅ Performance monitoring"
echo ""

echo "🚀 Running Phase 3 Demo..."
echo "=========================="

# Run the Phase 3 implementation demo
python scripts/phase3_implementation.py

echo ""
echo "🎉 Phase 3 Demo Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Review the demo output above"
echo "2. Check the database models in capp/core/database.py"
echo "3. Explore M-Pesa integration in capp/services/mpesa_integration.py"
echo "4. Run 'python -m applications.capp.capp.main' to start the API server"
echo "5. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "📚 Documentation:"
echo "- Phase 3 Plan: PHASE3_PLAN.md"
echo "- Phase 3 Summary: PHASE3_SUMMARY.md"
echo "- Database Schema: capp/core/database.py"
echo "- M-Pesa Integration: capp/services/mpesa_integration.py"
echo ""
echo "🔧 Development Commands:"
echo "- Start API: python -m applications.capp.capp.main"
echo "- Run tests: python test_capp.py"
echo "- Database migrations: alembic upgrade head"
echo "- Format code: black . && isort ."
echo ""
echo "🌟 CAPP Phase 3 is ready for production deployment!" 