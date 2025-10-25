"""Initial database schema

Revision ID: 0001
Revises:
Create Date: 2025-10-25 00:00:00.000000

Creates all initial tables for CAPP:
- users (authentication + KYC)
- payments (transaction data)
- payment_routes (optimized routing)
- liquidity_pools (liquidity management)
- liquidity_reservations (liquidity tracking)
- agent_activities (audit trail)
- exchange_rates (rate history)
- compliance_records (KYC/AML records)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=3), nullable=True),
        sa.Column('kyc_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('kyc_verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('phone_number')
    )

    # Create indexes for users
    op.create_index('idx_users_country_kyc', 'users', ['country', 'kyc_status'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    op.create_index('idx_users_role_status', 'users', ['role', 'status'])
    op.create_index(op.f('ix_users_email'), 'users', ['email'])
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'])
    op.create_index(op.f('ix_users_country'), 'users', ['country'])

    # Create payment_routes table
    op.create_table(
        'payment_routes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_country', sa.String(length=3), nullable=False),
        sa.Column('to_country', sa.String(length=3), nullable=False),
        sa.Column('from_currency', sa.String(length=3), nullable=False),
        sa.Column('to_currency', sa.String(length=3), nullable=False),
        sa.Column('mmo_provider', sa.String(length=50), nullable=False),
        sa.Column('mmo_provider_code', sa.String(length=20), nullable=False),
        sa.Column('estimated_fees', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('max_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('min_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_country', 'to_country', 'mmo_provider_code', name='uq_route_provider')
    )

    # Create indexes for payment_routes
    op.create_index('idx_routes_countries', 'payment_routes', ['from_country', 'to_country'])
    op.create_index('idx_routes_active', 'payment_routes', ['is_active', 'success_rate'])
    op.create_index(op.f('ix_payment_routes_from_country'), 'payment_routes', ['from_country'])
    op.create_index(op.f('ix_payment_routes_to_country'), 'payment_routes', ['to_country'])

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reference_id', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('from_currency', sa.String(length=3), nullable=False),
        sa.Column('to_currency', sa.String(length=3), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column('converted_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('fees', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_name', sa.String(length=200), nullable=False),
        sa.Column('sender_phone', sa.String(length=20), nullable=False),
        sa.Column('sender_country', sa.String(length=3), nullable=False),
        sa.Column('recipient_name', sa.String(length=200), nullable=False),
        sa.Column('recipient_phone', sa.String(length=20), nullable=False),
        sa.Column('recipient_country', sa.String(length=3), nullable=False),
        sa.Column('payment_type', sa.String(length=50), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('route_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mmo_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('blockchain_tx_hash', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('settled_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('amount > 0', name='check_positive_amount'),
        sa.CheckConstraint('total_cost > 0', name='check_positive_total'),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['route_id'], ['payment_routes.id'], ),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_id')
    )

    # Create indexes for payments
    op.create_index('idx_payments_status_created', 'payments', ['status', 'created_at'])
    op.create_index('idx_payments_currencies', 'payments', ['from_currency', 'to_currency'])
    op.create_index('idx_payments_sender_country', 'payments', ['sender_country'])
    op.create_index('idx_payments_recipient_country', 'payments', ['recipient_country'])
    op.create_index('idx_payments_sender_id', 'payments', ['sender_id'])
    op.create_index('idx_payments_recipient_id', 'payments', ['recipient_id'])
    op.create_index(op.f('ix_payments_reference_id'), 'payments', ['reference_id'])
    op.create_index(op.f('ix_payments_from_currency'), 'payments', ['from_currency'])
    op.create_index(op.f('ix_payments_to_currency'), 'payments', ['to_currency'])
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'])
    op.create_index(op.f('ix_payments_blockchain_tx_hash'), 'payments', ['blockchain_tx_hash'])

    # Create liquidity_pools table
    op.create_table(
        'liquidity_pools',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('country', sa.String(length=3), nullable=False),
        sa.Column('total_liquidity', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('available_liquidity', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('reserved_liquidity', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('min_balance', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('max_balance', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('rebalance_threshold', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_rebalanced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('total_liquidity >= 0', name='check_positive_total_liquidity'),
        sa.CheckConstraint('available_liquidity >= 0', name='check_positive_available_liquidity'),
        sa.CheckConstraint('reserved_liquidity >= 0', name='check_positive_reserved_liquidity'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('currency')
    )

    # Create indexes for liquidity_pools
    op.create_index('idx_pools_currency_country', 'liquidity_pools', ['currency', 'country'])
    op.create_index('idx_pools_available', 'liquidity_pools', ['is_active', 'available_liquidity'])
    op.create_index(op.f('ix_liquidity_pools_currency'), 'liquidity_pools', ['currency'])
    op.create_index(op.f('ix_liquidity_pools_country'), 'liquidity_pools', ['country'])

    # Create liquidity_reservations table
    op.create_table(
        'liquidity_reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pool_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='reserved'),
        sa.Column('reserved_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('released_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('amount > 0', name='check_positive_reservation_amount'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
        sa.ForeignKeyConstraint(['pool_id'], ['liquidity_pools.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for liquidity_reservations
    op.create_index('idx_reservations_status_expires', 'liquidity_reservations', ['status', 'expires_at'])
    op.create_index('idx_reservations_payment', 'liquidity_reservations', ['payment_id'])
    op.create_index(op.f('ix_liquidity_reservations_pool_id'), 'liquidity_reservations', ['pool_id'])
    op.create_index(op.f('ix_liquidity_reservations_payment_id'), 'liquidity_reservations', ['payment_id'])

    # Create agent_activities table
    op.create_table(
        'agent_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for agent_activities
    op.create_index('idx_agent_activities_payment_agent', 'agent_activities', ['payment_id', 'agent_type'])
    op.create_index('idx_agent_activities_status', 'agent_activities', ['status', 'started_at'])
    op.create_index('idx_agent_activities_agent_type', 'agent_activities', ['agent_type', 'started_at'])
    op.create_index(op.f('ix_agent_activities_payment_id'), 'agent_activities', ['payment_id'])
    op.create_index(op.f('ix_agent_activities_agent_type'), 'agent_activities', ['agent_type'])

    # Create exchange_rates table
    op.create_table(
        'exchange_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_currency', sa.String(length=3), nullable=False),
        sa.Column('to_currency', sa.String(length=3), nullable=False),
        sa.Column('rate', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('lock_expires_at', sa.DateTime(), nullable=True),
        sa.Column('effective_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('rate > 0', name='check_positive_rate'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_currency', 'to_currency', 'effective_at', name='uq_rate_currency_time')
    )

    # Create indexes for exchange_rates
    op.create_index('idx_exchange_rates_currencies', 'exchange_rates', ['from_currency', 'to_currency'])
    op.create_index('idx_exchange_rates_effective', 'exchange_rates', ['effective_at'])
    op.create_index(op.f('ix_exchange_rates_from_currency'), 'exchange_rates', ['from_currency'])
    op.create_index(op.f('ix_exchange_rates_to_currency'), 'exchange_rates', ['to_currency'])

    # Create compliance_records table
    op.create_table(
        'compliance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('check_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('checked_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for compliance_records
    op.create_index('idx_compliance_user_type', 'compliance_records', ['user_id', 'check_type'])
    op.create_index('idx_compliance_status', 'compliance_records', ['status', 'checked_at'])
    op.create_index('idx_compliance_expires', 'compliance_records', ['expires_at'])
    op.create_index(op.f('ix_compliance_records_user_id'), 'compliance_records', ['user_id'])
    op.create_index(op.f('ix_compliance_records_payment_id'), 'compliance_records', ['payment_id'])


def downgrade() -> None:
    # Drop all tables in reverse order (respecting foreign keys)
    op.drop_table('compliance_records')
    op.drop_table('exchange_rates')
    op.drop_table('agent_activities')
    op.drop_table('liquidity_reservations')
    op.drop_table('liquidity_pools')
    op.drop_table('payments')
    op.drop_table('payment_routes')
    op.drop_table('users')
