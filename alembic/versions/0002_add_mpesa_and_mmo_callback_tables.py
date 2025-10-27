"""add mpesa and mmo callback tables

Revision ID: 0002
Revises: 0001
Create Date: 2025-10-27

Adds M-Pesa transaction tracking and MMO callback tables for production-ready
mobile money integration:

- mpesa_transactions: Complete M-Pesa transaction lifecycle tracking
- mpesa_callbacks: M-Pesa webhook callback audit trail
- mmo_callbacks: Universal MMO provider callback storage

These tables support:
- STK Push, B2C, C2B, reversal, and query transactions
- Webhook callback processing and verification
- Transaction reconciliation and reporting
- Audit trail for regulatory compliance

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create M-Pesa and MMO callback tables.
    """

    # =========================================================================
    # Create mpesa_transactions table
    # =========================================================================
    op.create_table(
        'mpesa_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),

        # M-Pesa transaction identifiers
        sa.Column('checkout_request_id', sa.String(length=255), nullable=True),
        sa.Column('merchant_request_id', sa.String(length=255), nullable=True),
        sa.Column('conversation_id', sa.String(length=255), nullable=True),
        sa.Column('originator_conversation_id', sa.String(length=255), nullable=True),
        sa.Column('mpesa_receipt_number', sa.String(length=255), nullable=True),

        # Transaction type
        sa.Column('transaction_type', sa.String(length=50), nullable=False,
                  comment='stk_push, b2c, c2b, reversal, query'),

        # Transaction details
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('account_reference', sa.String(length=100), nullable=True),
        sa.Column('transaction_desc', sa.Text(), nullable=True),

        # Status tracking
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending',
                  comment='pending, processing, completed, failed, cancelled, timeout'),
        sa.Column('result_code', sa.Integer(), nullable=True),
        sa.Column('result_description', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # M-Pesa response data
        sa.Column('transaction_date', sa.DateTime(), nullable=True),
        sa.Column('mpesa_balance', sa.Numeric(precision=15, scale=2), nullable=True),

        # Request/Response metadata
        sa.Column('request_payload', sa.Text(), nullable=True,
                  comment='JSON request sent to M-Pesa'),
        sa.Column('response_payload', sa.Text(), nullable=True,
                  comment='JSON response from M-Pesa'),

        # Circuit breaker tracking
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_retry_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('initiated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('callback_received_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name='fk_mpesa_tx_payment'),

        # Unique constraints
        sa.UniqueConstraint('checkout_request_id', name='uq_mpesa_checkout_request_id'),
        sa.UniqueConstraint('mpesa_receipt_number', name='uq_mpesa_receipt_number'),

        # Check constraints
        sa.CheckConstraint('amount > 0', name='check_mpesa_positive_amount'),

        comment='M-Pesa transaction tracking with complete lifecycle management'
    )

    # Create indexes for mpesa_transactions
    op.create_index('idx_mpesa_tx_status_created', 'mpesa_transactions', ['status', 'created_at'])
    op.create_index('idx_mpesa_tx_phone', 'mpesa_transactions', ['phone_number', 'created_at'])
    op.create_index('idx_mpesa_tx_type', 'mpesa_transactions', ['transaction_type', 'status'])
    op.create_index('idx_mpesa_tx_payment', 'mpesa_transactions', ['payment_id'])
    op.create_index('idx_mpesa_tx_merchant_request', 'mpesa_transactions', ['merchant_request_id'])
    op.create_index('idx_mpesa_tx_conversation', 'mpesa_transactions', ['conversation_id'])
    op.create_index('idx_mpesa_tx_originator_conversation', 'mpesa_transactions', ['originator_conversation_id'])

    # =========================================================================
    # Create mpesa_callbacks table
    # =========================================================================
    op.create_table(
        'mpesa_callbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mpesa_transaction_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Callback identifiers
        sa.Column('checkout_request_id', sa.String(length=255), nullable=True),
        sa.Column('merchant_request_id', sa.String(length=255), nullable=True),

        # Callback type
        sa.Column('callback_type', sa.String(length=50), nullable=False,
                  comment='stk_callback, c2b_confirmation, c2b_validation, timeout, b2c_result'),

        # Raw callback data
        sa.Column('callback_data', sa.Text(), nullable=False,
                  comment='JSON payload from M-Pesa'),
        sa.Column('callback_metadata', sa.Text(), nullable=True,
                  comment='Additional metadata'),

        # Signature verification
        sa.Column('signature', sa.String(length=500), nullable=True),
        sa.Column('signature_verified', sa.Boolean(), nullable=False, server_default='false'),

        # Processing status
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('processing_attempts', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(['mpesa_transaction_id'], ['mpesa_transactions.id'],
                                name='fk_mpesa_callback_transaction'),

        comment='M-Pesa webhook callback audit trail and processing tracking'
    )

    # Create indexes for mpesa_callbacks
    op.create_index('idx_mpesa_callback_processed', 'mpesa_callbacks', ['processed', 'received_at'])
    op.create_index('idx_mpesa_callback_type', 'mpesa_callbacks', ['callback_type', 'received_at'])
    op.create_index('idx_mpesa_callback_checkout', 'mpesa_callbacks', ['checkout_request_id'])
    op.create_index('idx_mpesa_callback_transaction', 'mpesa_callbacks', ['mpesa_transaction_id'])

    # =========================================================================
    # Create mmo_callbacks table (universal MMO provider callbacks)
    # =========================================================================
    op.create_table(
        'mmo_callbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Provider information
        sa.Column('provider', sa.String(length=50), nullable=False,
                  comment='mtn_momo, airtel_money, orange_money, etc.'),
        sa.Column('provider_transaction_id', sa.String(length=255), nullable=False),
        sa.Column('external_reference_id', sa.String(length=255), nullable=True),

        # Callback details
        sa.Column('callback_type', sa.String(length=50), nullable=False,
                  comment='collection, disbursement, status, timeout'),
        sa.Column('callback_data', sa.Text(), nullable=False,
                  comment='JSON payload'),
        sa.Column('callback_metadata', sa.Text(), nullable=True),

        # Security
        sa.Column('signature', sa.String(length=500), nullable=True),
        sa.Column('signature_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ip_address', sa.String(length=45), nullable=True,
                  comment='IPv6 compatible'),

        # Processing
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('processing_attempts', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name='fk_mmo_callback_payment'),

        comment='Universal mobile money operator callback storage for all providers'
    )

    # Create indexes for mmo_callbacks
    op.create_index('idx_mmo_callback_provider_tx', 'mmo_callbacks',
                    ['provider', 'provider_transaction_id'])
    op.create_index('idx_mmo_callback_processed', 'mmo_callbacks', ['processed', 'received_at'])
    op.create_index('idx_mmo_callback_provider_type', 'mmo_callbacks',
                    ['provider', 'callback_type'])
    op.create_index('idx_mmo_callback_payment', 'mmo_callbacks', ['payment_id'])
    op.create_index('idx_mmo_callback_external_ref', 'mmo_callbacks', ['external_reference_id'])


def downgrade() -> None:
    """
    Drop M-Pesa and MMO callback tables.
    """

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('mmo_callbacks')
    op.drop_table('mpesa_callbacks')
    op.drop_table('mpesa_transactions')
