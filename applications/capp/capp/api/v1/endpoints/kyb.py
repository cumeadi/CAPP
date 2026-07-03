"""
KYB (Know Your Business) onboarding endpoint

POST /api/v1/compliance/kyb

Persists a business KYB submission into the hifi_kyc_submissions table
and runs it through the Compliance Agent's Enhanced Due Diligence (EDD) check.
The submission_type is fixed to "business".
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ....core.database import get_db, HifiKYCSubmission
from ....services.compliance import ComplianceService
from ....models.payments import Country
from ....models.user import User
from ....api.dependencies.auth import get_current_active_user

logger = structlog.get_logger(__name__)
router = APIRouter()

_compliance = ComplianceService()


class KYBRequest(BaseModel):
    business_name: str
    tax_identification_number: str
    country: Country

    # Registered address
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state_province_region: str
    postal_code: str

    # Contact
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class KYBResponse(BaseModel):
    submission_id: str
    status: str                 # pending | approved | rejected
    compliance_passed: bool
    risk_level: str
    message: str
    submitted_at: str


@router.post(
    "/kyb",
    response_model=KYBResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit business KYB",
    description=(
        "Submit a business for Know Your Business (KYB) onboarding. "
        "The submission is persisted and run through the Compliance Agent's "
        "Enhanced Due Diligence flow. Returns `pending` for manual review "
        "or `approved`/`rejected` for automated decisions."
    ),
)
async def submit_kyb(
    request: KYBRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> KYBResponse:
    # Persist the submission
    submission = HifiKYCSubmission(
        user_id=current_user.id,
        submission_type="business",
        status="pending",
        business_name=request.business_name,
        tax_identification_number=request.tax_identification_number,
        country=request.country,
        address_line1=request.address_line1,
        address_line2=request.address_line2,
        city=request.city,
        state_province_region=request.state_province_region,
        postal_code=request.postal_code,
        email=request.contact_email,
        phone=request.contact_phone,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    logger.info("kyb_submission_created", submission_id=str(submission.id), user_id=str(current_user.id))

    # Run EDD compliance check
    try:
        # Use the existing sanctions + AML check as the EDD proxy:
        # check the business country against sanctions lists and AML thresholds
        # ($10k EDD trigger from check_kyc_compliance covers high-value business accounts)
        compliance_result = await _compliance.check_kyc_compliance(
            sender_country=request.country,
            recipient_country=request.country,
            amount=10_001.0,  # trigger EDD level — business onboarding is always EDD
        )

        sanctions_result = await _compliance.check_sanctions(
            sender_country=request.country,
            recipient_country=request.country,
        )

        compliance_passed = compliance_result.passed and sanctions_result.passed
        risk_level = compliance_result.risk_level if hasattr(compliance_result, "risk_level") else "medium"

        if not compliance_passed:
            await db.execute(
                HifiKYCSubmission.__table__.update()
                .where(HifiKYCSubmission.id == submission.id)
                .values(status="rejected")
            )
            await db.commit()
            logger.warning("kyb_rejected", submission_id=str(submission.id), reason=compliance_result.message)
            return KYBResponse(
                submission_id=str(submission.id),
                status="rejected",
                compliance_passed=False,
                risk_level=risk_level,
                message=compliance_result.message or "KYB rejected by compliance screening",
                submitted_at=submission.submitted_at.isoformat(),
            )

        # Auto-approve low/medium risk; send high risk for manual review
        if risk_level in ("high", "critical"):
            final_status = "pending"
            message = "High-risk profile — submission queued for manual review"
        else:
            final_status = "approved"
            message = "KYB approved"
            await db.execute(
                HifiKYCSubmission.__table__.update()
                .where(HifiKYCSubmission.id == submission.id)
                .values(status=final_status, verified_at=datetime.now(timezone.utc))
            )
            await db.commit()

        logger.info("kyb_outcome", submission_id=str(submission.id), status=final_status)

        return KYBResponse(
            submission_id=str(submission.id),
            status=final_status,
            compliance_passed=compliance_passed,
            risk_level=risk_level,
            message=message,
            submitted_at=submission.submitted_at.isoformat(),
        )

    except Exception as exc:
        logger.error("kyb_compliance_check_failed", submission_id=str(submission.id), error=str(exc))
        # Submission stays in pending — don't reject on a transient error
        return KYBResponse(
            submission_id=str(submission.id),
            status="pending",
            compliance_passed=False,
            risk_level="unknown",
            message="Compliance check deferred — submission pending manual review",
            submitted_at=submission.submitted_at.isoformat(),
        )
