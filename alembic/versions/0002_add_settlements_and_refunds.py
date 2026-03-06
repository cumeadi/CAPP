"""Add settlements and refunds tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-05 00:00:00.000000

Adds two new tables required for the Payment Refund and Timeout Flows:

settlements
-----------
Records each on-chain settlement transaction linked to a payment.
A payment may have at most one confirmed settlement, but can have
multiple attempts (pending → confirmed / failed).

refunds
-------
Records each refund (compensating transaction) attempt against a
payment.  Linked optionally to the settlement that is being reversed.
The ``rolled_back_steps`` and ``failed_rollbacks`` JSON columns mirror
the RollbackResult from the saga orchestrator.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # settlements table
    # ------------------------------------------------------------------
    op.create_table(
        'settlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),

        # On-chain identity
        sa.Column('blockchain_tx_hash', sa.String(length=255), nullable=False),
        sa.Column('blockchain_network', sa.String(length=50), nullable=False),

        # Financial amounts
        sa.Column('settlement_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('settlement_currency', sa.String(length=3), nullable=False),

        # Lifecycle
        # status: pending | confirmed | failed
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),

        # On-chain confirmation details (nullable until confirmed)
        sa.Column('block_number', sa.BigInteger(), nullable=True),
        sa.Column('gas_used', sa.BigInteger(), nullable=True),

        # Timestamps
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.CheckConstraint('settlement_amount > 0', name='check_positive_settlement_amount'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name='fk_settlements_payment_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blockchain_tx_hash', name='uq_settlements_tx_hash'),
    )

    op.create_index('idx_settlements_payment_id',  'settlements', ['payment_id'])
    op.create_index('idx_settlements_status',       'settlements', ['status', 'settled_at'])
    op.create_index('idx_settlements_network',      'settlements', ['blockchain_network'])
    op.create_index(op.f('ix_settlements_payment_id'),
                    'settlements', ['payment_id'])
    op.create_index(op.f('ix_settlements_blockchain_tx_hash'),
                    'settlements', ['blockchain_tx_hash'])

    # ------------------------------------------------------------------
    # refunds table
    # ------------------------------------------------------------------
    op.create_table(
        'refunds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),

        # The settlement being reversed (nullable — refunds can precede
        # a confirmed settlement, e.g. timeout before confirmation).
        sa.Column('settlement_id', postgresql.UUID(as_uuid=True), nullable=True),

        # On-chain refund transaction (nullable until the refund tx is
        # submitted / confirmed)
        sa.Column('refund_tx_hash', sa.String(length=255), nullable=True),

        # Financial amounts
        sa.Column('refund_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('refund_currency', sa.String(length=3), nullable=False),

        # Why the refund was initiated
        # reason: PAYMENT_TIMEOUT | SETTLEMENT_FAILED | MANUAL_REQUEST | COMPLIANCE_HOLD
        sa.Column('reason', sa.String(length=100), nullable=False),

        # Lifecycle
        # status: pending | processing | completed | failed
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),

        # Who / what triggered the refund
        # initiated_by: watchdog | user | admin
        sa.Column('initiated_by', sa.String(length=50), nullable=False,
                  server_default='watchdog'),

        # Saga rollback details stored as JSON text arrays
        sa.Column('rolled_back_steps', sa.Text(), nullable=True),   # JSON array of step IDs
        sa.Column('failed_rollbacks',  sa.Text(), nullable=True),   # JSON array of step IDs

        # Timestamps
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.CheckConstraint('refund_amount > 0', name='check_positive_refund_amount'),
        sa.ForeignKeyConstraint(['payment_id'],    ['payments.id'],    name='fk_refunds_payment_id'),
        sa.ForeignKeyConstraint(['settlement_id'], ['settlements.id'], name='fk_refunds_settlement_id'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('idx_refunds_payment_id',  'refunds', ['payment_id'])
    op.create_index('idx_refunds_status',       'refunds', ['status', 'initiated_at'])
    op.create_index('idx_refunds_reason',       'refunds', ['reason'])
    op.create_index('idx_refunds_initiated_by', 'refunds', ['initiated_by', 'initiated_at'])
    op.create_index(op.f('ix_refunds_payment_id'),    'refunds', ['payment_id'])
    op.create_index(op.f('ix_refunds_settlement_id'), 'refunds', ['settlement_id'])
    op.create_index(op.f('ix_refunds_refund_tx_hash'), 'refunds', ['refund_tx_hash'])


def downgrade() -> None:
    # Drop in reverse order (refunds references settlements)
    op.drop_table('refunds')
    op.drop_table('settlements')
