#!/bin/bash
# Script to create Alembic migrations for CAPP

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create migration
if [ -z "$1" ]; then
    echo "Usage: $0 <migration_message>"
    echo "Example: $0 'add user table'"
    exit 1
fi

MESSAGE="$1"

echo "Creating migration: $MESSAGE"
alembic revision --autogenerate -m "$MESSAGE"

echo ""
echo "Migration created successfully!"
echo "Review the migration file in alembic/versions/"
echo ""
echo "To apply the migration, run:"
echo "  alembic upgrade head"
