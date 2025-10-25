#!/bin/bash
# Script to test Alembic migrations for CAPP

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Testing CAPP Alembic Migrations ===${NC}"
echo ""

# Check if database is accessible
echo -e "${YELLOW}Checking database connection...${NC}"
python -c "
import asyncio
from applications.capp.capp.config.settings import get_settings
from applications.capp.capp.core.database import engine

async def check_db():
    try:
        async with engine.begin() as conn:
            print('✓ Database connection successful')
        await engine.dispose()
    except Exception as e:
        print(f'✗ Database connection failed: {e}')
        exit(1)

asyncio.run(check_db())
"

echo ""

# Show current migration status
echo -e "${YELLOW}Current migration status:${NC}"
alembic current

echo ""

# Show pending migrations
echo -e "${YELLOW}Pending migrations:${NC}"
alembic heads

echo ""

# Apply migrations
echo -e "${YELLOW}Applying migrations...${NC}"
alembic upgrade head

echo ""

# Show current status after upgrade
echo -e "${YELLOW}Migration status after upgrade:${NC}"
alembic current

echo ""

# Test rollback (downgrade one revision)
echo -e "${YELLOW}Testing rollback (downgrade -1)...${NC}"
alembic downgrade -1

echo ""

# Show status after downgrade
echo -e "${YELLOW}Status after downgrade:${NC}"
alembic current

echo ""

# Re-apply migrations
echo -e "${YELLOW}Re-applying migrations...${NC}"
alembic upgrade head

echo ""

# Final status
echo -e "${YELLOW}Final migration status:${NC}"
alembic current

echo ""
echo -e "${GREEN}=== Migration test completed successfully! ===${NC}"
echo ""
echo "To apply migrations in production:"
echo "  alembic upgrade head"
echo ""
echo "To rollback one migration:"
echo "  alembic downgrade -1"
echo ""
echo "To see migration history:"
echo "  alembic history"
