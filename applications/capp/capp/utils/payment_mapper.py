"""
Payment Model Mappers

Utilities to convert between Pydantic domain models and SQLAlchemy database models.
"""

from typing import Optional
from uuid import UUID

from ..models.payments import (
    CrossBorderPayment,
    PaymentStatus,
    PaymentType,
    PaymentMethod,
)
from ..core.database import Payment as PaymentModel


def crossborder_payment_to_db(payment: CrossBorderPayment, user_id: Optional[UUID] = None) -> PaymentModel:
    """
    Convert CrossBorderPayment (Pydantic) to Payment (SQLAlchemy).

    Args:
        payment: The Pydantic payment model
        user_id: Optional user ID to associate with the payment

    Returns:
        PaymentModel: SQLAlchemy database model
    """
    return PaymentModel(
        id=payment.payment_id,
        user_id=user_id,
        reference=payment.reference_id,

        # Sender information
        sender_name=payment.sender.name,
        sender_phone=payment.sender.phone_number,
        sender_email=payment.sender.email,
        sender_country=payment.sender.country.value,
        sender_address=payment.sender.address,

        # Recipient information
        recipient_name=payment.recipient.name,
        recipient_phone=payment.recipient.phone_number,
        recipient_email=payment.recipient.email,
        recipient_country=payment.recipient.country.value,
        recipient_address=payment.recipient.address,
        recipient_bank_account=payment.recipient.bank_account,
        recipient_bank_name=payment.recipient.bank_name,
        recipient_mmo_account=payment.recipient.mmo_account,
        recipient_mmo_provider=payment.recipient.mmo_provider.value if payment.recipient.mmo_provider else None,

        # Payment details
        payment_type=payment.payment_type.value,
        payment_method=payment.payment_method.value,

        # Amount and currency
        amount=float(payment.amount),
        from_currency=payment.from_currency.value,
        to_currency=payment.to_currency.value,
        exchange_rate=float(payment.exchange_rate) if payment.exchange_rate else None,
        converted_amount=float(payment.converted_amount) if payment.converted_amount else None,
        fees=float(payment.fees),
        total_cost=float(payment.total_cost),

        # Status and timing
        status=payment.status.value,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        completed_at=payment.completed_at,
        expires_at=payment.expires_at,

        # Processing
        route_id=payment.selected_route.route_id if payment.selected_route else None,
        blockchain_tx_hash=payment.blockchain_tx_hash,
        agent_id=payment.agent_id,
        workflow_id=payment.workflow_id,

        # Compliance and security
        compliance_status=payment.compliance_status,
        fraud_score=payment.fraud_score,
        risk_level=payment.risk_level,

        # KYC verification
        sender_kyc_verified=payment.sender.kyc_verified,
        recipient_kyc_verified=payment.recipient.kyc_verified,

        # Metadata
        description=payment.description,
        metadata=payment.metadata,

        # Offline support
        offline_queued=payment.offline_queued,
        sync_attempts=payment.sync_attempts,
        last_sync_attempt=payment.last_sync_attempt,
    )


def db_payment_to_crossborder(db_payment: PaymentModel) -> CrossBorderPayment:
    """
    Convert Payment (SQLAlchemy) to CrossBorderPayment (Pydantic).

    Args:
        db_payment: The SQLAlchemy database model

    Returns:
        CrossBorderPayment: Pydantic domain model
    """
    from ..models.payments import SenderInfo, RecipientInfo, PaymentPreferences, Currency, Country, MMOProvider
    from decimal import Decimal

    # Build sender info
    sender = SenderInfo(
        name=db_payment.sender_name,
        phone_number=db_payment.sender_phone,
        email=db_payment.sender_email,
        country=Country(db_payment.sender_country),
        address=db_payment.sender_address,
        kyc_verified=db_payment.sender_kyc_verified,
    )

    # Build recipient info
    recipient = RecipientInfo(
        name=db_payment.recipient_name,
        phone_number=db_payment.recipient_phone,
        email=db_payment.recipient_email,
        country=Country(db_payment.recipient_country),
        address=db_payment.recipient_address,
        bank_account=db_payment.recipient_bank_account,
        bank_name=db_payment.recipient_bank_name,
        mmo_account=db_payment.recipient_mmo_account,
        mmo_provider=MMOProvider(db_payment.recipient_mmo_provider) if db_payment.recipient_mmo_provider else None,
        kyc_verified=db_payment.recipient_kyc_verified,
    )

    # Build payment
    return CrossBorderPayment(
        payment_id=db_payment.id,
        reference_id=db_payment.reference,
        payment_type=PaymentType(db_payment.payment_type),
        payment_method=PaymentMethod(db_payment.payment_method),

        # Amount and currency
        amount=Decimal(str(db_payment.amount)),
        from_currency=Currency(db_payment.from_currency),
        to_currency=Currency(db_payment.to_currency),
        exchange_rate=Decimal(str(db_payment.exchange_rate)) if db_payment.exchange_rate else None,
        converted_amount=Decimal(str(db_payment.converted_amount)) if db_payment.converted_amount else None,

        # Parties
        sender=sender,
        recipient=recipient,

        # Routing (selected_route and available_routes will need to be loaded separately if needed)
        selected_route=None,  # TODO: Load from payment_routes table if route_id exists
        available_routes=[],
        preferences=PaymentPreferences(),  # Default preferences

        # Status and timing
        status=PaymentStatus(db_payment.status),
        created_at=db_payment.created_at,
        updated_at=db_payment.updated_at,
        expires_at=db_payment.expires_at,
        completed_at=db_payment.completed_at,

        # Fees and costs
        fees=Decimal(str(db_payment.fees)),
        total_cost=Decimal(str(db_payment.total_cost)),

        # Processing
        agent_id=db_payment.agent_id,
        workflow_id=db_payment.workflow_id,
        blockchain_tx_hash=db_payment.blockchain_tx_hash,

        # Compliance and security
        compliance_status=db_payment.compliance_status,
        fraud_score=db_payment.fraud_score,
        risk_level=db_payment.risk_level,

        # Metadata
        description=db_payment.description,
        metadata=db_payment.metadata or {},

        # Offline support
        offline_queued=db_payment.offline_queued,
        sync_attempts=db_payment.sync_attempts,
        last_sync_attempt=db_payment.last_sync_attempt,
    )
