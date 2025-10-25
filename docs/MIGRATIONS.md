# Database Migrations Guide

This document describes how to manage database migrations for the CAPP (Canza Autonomous Payment Protocol) application using Alembic.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Common Migration Commands](#common-migration-commands)
- [Creating Migrations](#creating-migrations)
- [Applying Migrations](#applying-migrations)
- [Rolling Back Migrations](#rolling-back-migrations)
- [Migration Best Practices](#migration-best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

CAPP uses **Alembic** for database schema management and migrations. Alembic is a lightweight database migration tool for SQLAlchemy that provides:

- Automatic migration generation from model changes
- Version control for database schemas
- Safe upgrade and downgrade capabilities
- Support for multiple database environments

## Prerequisites

Before working with migrations, ensure you have:

1. **PostgreSQL** installed and running
2. **Python dependencies** installed:
   ```bash
   pip install -r applications/capp/requirements.txt
   ```
3. **Database created** and accessible
4. **Environment variables** configured (see `.env` file)

## Initial Setup

### 1. Configure Database Connection

The database URL is configured in two places:

**For the application** (`applications/capp/capp/config/settings.py`):
```python
DATABASE_URL = "postgresql+asyncpg://capp_user:capp_password@localhost/capp_db"
```

**For Alembic** (`alembic.ini`):
```ini
sqlalchemy.url = postgresql://capp_user:capp_password@localhost/capp_db
```

Note: Alembic uses the synchronous `postgresql://` driver, while the application uses the async `postgresql+asyncpg://` driver.

### 2. Verify Alembic Configuration

Check that Alembic is properly configured:

```bash
alembic current
```

This should show the current database migration version (or no version if migrations haven't been applied).

## Common Migration Commands

### Check Current Migration Status

```bash
alembic current
```

Shows the current migration revision applied to the database.

### View Migration History

```bash
alembic history
```

Shows all available migrations in chronological order.

### View Pending Migrations

```bash
alembic heads
```

Shows the latest migration(s) available.

### Show Detailed Migration Info

```bash
alembic show <revision>
```

Replace `<revision>` with a migration revision ID (e.g., `0001`).

## Creating Migrations

### Automatic Migration Generation

The recommended way to create migrations is using Alembic's autogenerate feature:

```bash
# Using the helper script
./scripts/create_migration.sh "description of changes"

# Or directly with Alembic
alembic revision --autogenerate -m "description of changes"
```

**Example:**
```bash
./scripts/create_migration.sh "add user preferences table"
```

This will:
1. Compare your SQLAlchemy models with the current database schema
2. Generate a migration file in `alembic/versions/`
3. Include upgrade and downgrade operations

### Manual Migration Creation

For complex migrations that can't be auto-generated:

```bash
alembic revision -m "description of changes"
```

This creates a blank migration file that you can edit manually.

### Review Generated Migrations

**IMPORTANT:** Always review auto-generated migrations before applying them!

Generated migrations are in `alembic/versions/`. Check:

- Column types are correct
- Indexes are created appropriately
- Foreign keys are handled properly
- Default values are set correctly
- No data loss will occur

## Applying Migrations

### Upgrade to Latest Version

Apply all pending migrations:

```bash
alembic upgrade head
```

### Upgrade to Specific Version

```bash
alembic upgrade <revision>
```

**Example:**
```bash
alembic upgrade 0002
```

### Upgrade by Steps

Upgrade by a specific number of revisions:

```bash
alembic upgrade +2  # Upgrade 2 revisions forward
```

## Rolling Back Migrations

### Downgrade One Revision

```bash
alembic downgrade -1
```

### Downgrade to Specific Version

```bash
alembic downgrade <revision>
```

**Example:**
```bash
alembic downgrade 0001
```

### Downgrade by Steps

```bash
alembic downgrade -2  # Downgrade 2 revisions
```

### Downgrade to Base (Remove All Migrations)

**WARNING:** This will drop all tables!

```bash
alembic downgrade base
```

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations

Auto-generation is smart but not perfect. Review all generated migrations to ensure:

- No accidental table drops
- Renamed columns are detected correctly (not dropped and re-created)
- Indexes are created efficiently
- Data migrations are handled properly

### 2. Test Migrations Before Production

Always test migrations in a staging environment:

```bash
# Backup your database first
pg_dump capp_db > backup.sql

# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Re-upgrade
alembic upgrade head
```

### 3. Keep Migrations Small

Create focused migrations for specific changes:

- ✅ Good: "add email index to users table"
- ❌ Bad: "update database schema for Q4 features"

### 4. Never Edit Applied Migrations

Once a migration is applied to production, never edit it. Instead:

1. Create a new migration to fix issues
2. Keep migration history linear and traceable

### 5. Use Descriptive Messages

```bash
# Good
./scripts/create_migration.sh "add kyc_verified_at timestamp to users"

# Bad
./scripts/create_migration.sh "update users"
```

### 6. Handle Data Migrations Carefully

For data migrations, use Alembic's `op.execute()`:

```python
def upgrade():
    # Schema change
    op.add_column('users', sa.Column('status', sa.String(50)))

    # Data migration
    op.execute("UPDATE users SET status = 'active' WHERE is_active = true")

def downgrade():
    op.drop_column('users', 'status')
```

## Database Schema Overview

The current database schema includes these tables:

1. **users** - User accounts with authentication and KYC information
2. **payments** - Payment transactions and their details
3. **payment_routes** - Available payment corridors and routes
4. **liquidity_pools** - Liquidity pools for currency pairs
5. **liquidity_reservations** - Reserved liquidity for pending payments
6. **agent_activities** - Agent interaction logs and performance metrics
7. **exchange_rates** - Historical exchange rate data
8. **compliance_records** - AML/KYC compliance and audit logs

See `applications/capp/capp/core/database.py` for detailed model definitions.

## Troubleshooting

### "No module named 'applications.capp'"

Ensure you're running Alembic from the project root:

```bash
cd /path/to/CAPP
alembic current
```

The `prepend_sys_path = .` setting in `alembic.ini` should handle this automatically.

### "Can't locate revision identified by 'head'"

This means no migrations have been created yet. Create the initial migration:

```bash
./scripts/create_migration.sh "initial schema"
```

### Database Connection Errors

Check your database connection settings:

1. Verify PostgreSQL is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Test connection manually:
   ```bash
   psql -h localhost -U capp_user -d capp_db
   ```

3. Check environment variables in `.env` file

### "Table already exists" Errors

If you're migrating an existing database, you may need to stamp it with the current revision:

```bash
# Mark database as being at a specific revision without running migrations
alembic stamp <revision>

# Or stamp as head (latest)
alembic stamp head
```

### Migration Conflicts

If you have multiple migration heads (branched history):

```bash
# View heads
alembic heads

# Merge heads
alembic merge heads -m "merge migration branches"
```

## Environment-Specific Migrations

### Development

```bash
# Use local database
export DATABASE_URL="postgresql://capp_user:capp_password@localhost/capp_dev"
alembic upgrade head
```

### Testing

```bash
# Use test database
export DATABASE_URL="postgresql://capp_user:capp_password@localhost/capp_test"
alembic upgrade head
```

### Production

```bash
# Use production database (with proper credentials)
export DATABASE_URL="postgresql://user:pass@prod-db-host/capp_prod"

# Backup first!
pg_dump capp_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Apply migrations
alembic upgrade head
```

## Helpful Scripts

### Test Migration Script

Run the full migration test suite:

```bash
./scripts/test_migration.sh
```

This script will:
1. Check database connectivity
2. Show current migration status
3. Apply all migrations
4. Test rollback
5. Re-apply migrations

### Create Migration Script

Quickly create a new migration:

```bash
./scripts/create_migration.sh "your migration description"
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [CAPP Database Models](../applications/capp/capp/core/database.py)

## Support

For migration issues or questions:

1. Check this documentation
2. Review the Alembic logs
3. Consult the team's development channel
4. Open an issue in the project repository

---

**Last Updated:** 2025-10-25
**Alembic Version:** 1.13.0+
**Database:** PostgreSQL 13+
