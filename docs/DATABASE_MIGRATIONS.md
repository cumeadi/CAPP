# CAPP Database Migrations Guide

This guide explains how to manage database schema migrations for the CAPP platform using Alembic.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Migration Files](#migration-files)
- [Common Commands](#common-commands)
- [Creating Migrations](#creating-migrations)
- [Applying Migrations](#applying-migrations)
- [Rolling Back](#rolling-back)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Overview

CAPP uses **Alembic** for database schema version control and migrations. Alembic provides:

- Version-controlled database schemas
- Forward migrations (upgrade)
- Backward migrations (downgrade)
- Automatic migration generation from model changes
- Production-safe schema updates

### Migration Strategy

- **Development**: Create and test migrations locally
- **Staging**: Test migrations in staging environment
- **Production**: Apply migrations during deployment with zero-downtime strategy

---

## Prerequisites

### 1. PostgreSQL Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Docker:**
```bash
docker run --name capp-postgres \
  -e POSTGRES_USER=capp_user \
  -e POSTGRES_PASSWORD=capp_password \
  -e POSTGRES_DB=capp_db \
  -p 5432:5432 \
  -d postgres:15
```

### 2. Database Setup

Create the database and user:

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE capp_db;
CREATE USER capp_user WITH ENCRYPTED PASSWORD 'capp_password';
GRANT ALL PRIVILEGES ON DATABASE capp_db TO capp_user;
\q
```

### 3. Python Dependencies

```bash
pip install alembic psycopg2-binary sqlalchemy
```

### 4. Environment Configuration

Create `.env` file with database URL:

```bash
DATABASE_URL=postgresql+asyncpg://capp_user:capp_password@localhost:5432/capp_db
```

---

## Migration Files

### Directory Structure

```
CAPP/
├── alembic/
│   ├── versions/          # Migration files
│   │   ├── 0001_initial_schema.py
│   │   └── 0002_add_mpesa_and_mmo_callback_tables.py
│   ├── env.py             # Alembic environment configuration
│   └── script.py.mako     # Migration template
├── alembic.ini            # Alembic configuration
└── docs/
    └── DATABASE_MIGRATIONS.md  # This file
```

### Current Migrations

#### Migration 0001: Initial Schema
**File**: `alembic/versions/0001_initial_schema.py`
**Creates**:
- users
- payments
- payment_routes
- liquidity_pools
- liquidity_reservations
- agent_activities
- exchange_rates
- compliance_records

#### Migration 0002: M-Pesa and MMO Callbacks
**File**: `alembic/versions/0002_add_mpesa_and_mmo_callback_tables.py`
**Creates**:
- mpesa_transactions (M-Pesa transaction tracking)
- mpesa_callbacks (M-Pesa webhook audit trail)
- mmo_callbacks (Universal MMO provider callbacks)

---

## Common Commands

### Check Current Version

```bash
alembic current
```

**Expected output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
0002 (head)
```

### View Migration History

```bash
alembic history
```

**Output**:
```
0001 -> 0002 (head), add mpesa and mmo callback tables
<base> -> 0001, initial schema
```

### View Migration Details

```bash
alembic show 0002
```

### Check for Pending Migrations

```bash
alembic current
alembic heads
```

If current != heads, you have pending migrations.

---

## Creating Migrations

### Method 1: Auto-Generate from Model Changes

**Recommended for most changes**

1. Update your SQLAlchemy models in `applications/capp/capp/core/database.py`

2. Import new models in `alembic/env.py`:
   ```python
   from applications.capp.capp.core.database import (
       Base,
       User,
       Payment,
       # ... add your new model here
   )
   ```

3. Generate migration:
   ```bash
   alembic revision --autogenerate -m "add_user_profile_table"
   ```

4. Review and edit the generated file in `alembic/versions/`

5. Test the migration:
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```

### Method 2: Manual Migration

**For complex changes or when database is unavailable**

1. Create empty migration:
   ```bash
   alembic revision -m "add_custom_index"
   ```

2. Edit the generated file:
   ```python
   def upgrade() -> None:
       op.create_index(
           'idx_payments_custom',
           'payments',
           ['status', 'created_at']
       )

   def downgrade() -> None:
       op.drop_index('idx_payments_custom', 'payments')
   ```

3. Test the migration

---

## Applying Migrations

### Upgrade to Latest Version

```bash
alembic upgrade head
```

**Output**:
```
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, add mpesa and mmo callback tables
```

### Upgrade to Specific Version

```bash
alembic upgrade 0002
```

### Upgrade One Step

```bash
alembic upgrade +1
```

### Dry Run (Show SQL)

```bash
alembic upgrade head --sql
```

This shows the SQL that would be executed without actually running it.

---

## Rolling Back

### Downgrade One Version

```bash
alembic downgrade -1
```

### Downgrade to Specific Version

```bash
alembic downgrade 0001
```

### Downgrade All (Reset Database)

```bash
alembic downgrade base
```

**Warning**: This drops all tables! Only use in development.

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Backup production database
- [ ] Test migration in staging environment
- [ ] Review migration SQL (`alembic upgrade head --sql`)
- [ ] Check for breaking changes
- [ ] Plan rollback strategy
- [ ] Schedule maintenance window if needed

### Zero-Downtime Deployment Strategy

For production deployments with minimal downtime:

#### Phase 1: Additive Changes (No Downtime)

1. Deploy migration with only **additive** changes:
   - Add new columns (nullable or with defaults)
   - Add new tables
   - Add new indexes (use CONCURRENT if needed)

2. Deploy application code that works with both old and new schema

3. Monitor for issues

#### Phase 2: Cleanup (Scheduled Maintenance)

1. Remove deprecated columns/tables
2. Add NOT NULL constraints
3. Remove old indexes

### PostgreSQL-Specific Optimizations

For large tables, use PostgreSQL concurrent operations:

```python
def upgrade():
    # Create index concurrently (doesn't lock table)
    op.create_index(
        'idx_payments_status',
        'payments',
        ['status'],
        postgresql_concurrently=True
    )

def downgrade():
    op.drop_index('idx_payments_status', 'payments')
```

**Note**: Concurrent operations must run outside transactions. Set:
```python
from alembic import op

def upgrade():
    connection = op.get_bind()
    connection.execute('COMMIT')  # End transaction
    connection.execute('CREATE INDEX CONCURRENTLY ...')
```

### Production Deployment Commands

```bash
# 1. Backup database
pg_dump -U capp_user -d capp_db -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# 2. Check current version
alembic current

# 3. Review pending migrations
alembic history

# 4. Dry run (review SQL)
alembic upgrade head --sql > migration.sql
cat migration.sql  # Review changes

# 5. Apply migration
alembic upgrade head

# 6. Verify
alembic current
psql -U capp_user -d capp_db -c "\dt"  # List tables
```

---

## Troubleshooting

### Issue: "Can't locate revision identified by 'xxxx'"

**Cause**: Migration file missing or database out of sync

**Solution**:
```bash
# Check migration files exist
ls alembic/versions/

# Check database state
alembic current

# Stamp database to specific version (if you know it)
alembic stamp 0001
```

### Issue: "Target database is not up to date"

**Cause**: Database has uncommitted changes

**Solution**:
```bash
# Check for pending migrations
alembic current
alembic heads

# Apply pending migrations
alembic upgrade head
```

### Issue: Migration fails mid-way

**Cause**: Error in migration SQL or data issues

**Solution**:
```bash
# Alembic automatically rolls back failed migrations
# Fix the migration file and retry

# Or manually fix database and stamp version
alembic stamp head
```

### Issue: "psycopg2.OperationalError: could not connect"

**Cause**: PostgreSQL not running or wrong credentials

**Solution**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start if needed
sudo systemctl start postgresql

# Verify credentials
psql -U capp_user -d capp_db

# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

### Issue: "Table already exists"

**Cause**: Running migration on database that already has tables

**Solution**:
```bash
# Stamp database to current state without running migrations
alembic stamp head

# Or drop and recreate
alembic downgrade base
alembic upgrade head
```

---

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations

Alembic's autogenerate is helpful but not perfect. Always review:
- Column type changes
- Index definitions
- Foreign key constraints
- Data migrations

### 2. Test Migrations Both Ways

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Test upgrade again
alembic upgrade head
```

### 3. Use Descriptive Migration Messages

**Good**:
```bash
alembic revision -m "add_email_verification_to_users"
```

**Bad**:
```bash
alembic revision -m "update"
```

### 4. Keep Migrations Small

One logical change per migration:
- Add one table
- Add indexes for one feature
- Modify related columns together

### 5. Document Complex Migrations

Add comments in migration files:
```python
def upgrade():
    """
    Add email verification workflow.

    - Adds email_verified column
    - Adds email_verification_token column
    - Creates index for fast token lookup
    """
    # Migration code...
```

### 6. Handle Data Migrations Carefully

For data transformations:
```python
def upgrade():
    # First: Add new column (nullable)
    op.add_column('users', sa.Column('full_name', sa.String(200)))

    # Second: Migrate data
    connection = op.get_bind()
    connection.execute("""
        UPDATE users
        SET full_name = first_name || ' ' || last_name
        WHERE full_name IS NULL
    """)

    # Third: Make NOT NULL if needed
    op.alter_column('users', 'full_name', nullable=False)
```

### 7. Always Backup Before Production Migrations

```bash
pg_dump -U capp_user -d capp_db -F c -f backup_before_migration.dump
```

Restore if needed:
```bash
pg_restore -U capp_user -d capp_db -c backup_before_migration.dump
```

---

## Environment-Specific Migrations

### Development

```bash
# .env.development
DATABASE_URL=postgresql+asyncpg://capp_user:capp_password@localhost:5432/capp_dev
```

### Staging

```bash
# .env.staging
DATABASE_URL=postgresql+asyncpg://capp_user:capp_password@staging-db:5432/capp_staging
```

### Production

```bash
# .env.production
DATABASE_URL=postgresql+asyncpg://capp_user:capp_password@prod-db:5432/capp_prod
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `alembic current` | Show current version |
| `alembic history` | Show migration history |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic upgrade +1` | Apply next migration |
| `alembic downgrade -1` | Rollback one migration |
| `alembic downgrade base` | Rollback all migrations |
| `alembic revision -m "msg"` | Create empty migration |
| `alembic revision --autogenerate -m "msg"` | Auto-generate migration |
| `alembic upgrade head --sql` | Show SQL without executing |
| `alembic stamp head` | Mark database as up-to-date |

---

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Last Updated**: 2025-10-27
**CAPP Version**: 0.1.0
**Alembic Version**: Latest
