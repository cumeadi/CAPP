"""Add fee_schedules and risk_rules tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-05 00:00:00.000000

Externalises hardcoded configuration from Python source files into the DB:

fee_schedules
-------------
Replaces the flat-fee constants in financial_base.py (lines 289-308).
Each row describes the fee structure for a given transaction_type ×
compliance_level combination.

risk_rules
----------
Replaces the hardcoded risk-score thresholds in financial_base.py
(lines 260-270). Each row defines the risk increment associated with a
specific condition (amount threshold, compliance level, etc.).

Seed rows mirror the original hardcoded values so that existing behaviour
is preserved exactly after the migration runs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── fee_schedules ─────────────────────────────────────────────────────────
    op.create_table(
        'fee_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('compliance_level', sa.String(length=20), nullable=False),
        # base_fee is a flat additive fee applied to every transaction that
        # matches this row (e.g. 0.01 = 1 cent / 1% depending on currency).
        sa.Column('base_fee', sa.Numeric(precision=15, scale=6), nullable=False,
                  server_default='0'),
        # amount_fee_pct: percentage of transaction amount added as fee
        # (stored as a fraction, e.g. 0.005 = 0.5 %).
        sa.Column('amount_fee_pct', sa.Numeric(precision=10, scale=6), nullable=False,
                  server_default='0'),
        # compliance_surcharge: flat fee added when the compliance_level matches.
        sa.Column('compliance_surcharge', sa.Numeric(precision=15, scale=2), nullable=False,
                  server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_type', 'compliance_level',
                            name='uq_fee_schedule_type_level'),
    )
    op.create_index('idx_fee_schedules_active',
                    'fee_schedules', ['is_active', 'transaction_type'])
    op.create_index(op.f('ix_fee_schedules_transaction_type'),
                    'fee_schedules', ['transaction_type'])
    op.create_index(op.f('ix_fee_schedules_compliance_level'),
                    'fee_schedules', ['compliance_level'])

    # ── risk_rules ────────────────────────────────────────────────────────────
    op.create_table(
        'risk_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        # rule_name: human-readable identifier, e.g. "high_amount", "critical_compliance"
        sa.Column('rule_name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        # condition_value: the threshold or enum value that triggers the rule.
        # Stored as text to accommodate both numeric thresholds and string enum values.
        sa.Column('condition_value', sa.String(length=100), nullable=True),
        # risk_increment: how much this rule adds to the base_risk score (0-1).
        sa.Column('risk_increment', sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_risk_rules_active',
                    'risk_rules', ['is_active', 'rule_type'])
    op.create_index(op.f('ix_risk_rules_rule_type'),
                    'risk_rules', ['rule_type'])

    # ── Seed data: mirror the original hardcoded values ───────────────────────
    # These INSERT statements preserve existing behaviour after migration.
    op.execute("""
        INSERT INTO fee_schedules
            (transaction_type, compliance_level, base_fee, amount_fee_pct, compliance_surcharge, description)
        VALUES
            -- Default row: catches all transaction types not matched by a specific row.
            ('default',   'low',      0.01, 0.005, 0.00,
             'Default fee: 1% base + 0.5% of amount, no surcharge'),
            ('default',   'medium',   0.01, 0.005, 0.00,
             'Default fee: 1% base + 0.5% of amount'),
            ('default',   'high',     0.01, 0.005, 2.00,
             'Default fee: 1% base + 0.5% of amount + $2 compliance surcharge'),
            ('default',   'critical', 0.01, 0.005, 5.00,
             'Default fee: 1% base + 0.5% of amount + $5 compliance surcharge')
        ON CONFLICT (transaction_type, compliance_level) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO risk_rules
            (rule_name, rule_type, condition_value, risk_increment, description)
        VALUES
            ('base_risk',            'base',               NULL,    0.100,
             'Base risk applied to every transaction'),
            ('amount_very_high',     'amount_threshold',   '10000', 0.200,
             'Amount > 10,000: high-value transaction'),
            ('amount_high',          'amount_threshold',   '1000',  0.100,
             'Amount > 1,000 (and <= 10,000)'),
            ('compliance_critical',  'compliance_level',   'critical', 0.300,
             'CRITICAL compliance level'),
            ('compliance_high',      'compliance_level',   'high',  0.200,
             'HIGH compliance level')
        ON CONFLICT (rule_name) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('risk_rules')
    op.drop_table('fee_schedules')
