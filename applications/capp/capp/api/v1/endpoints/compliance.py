from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from applications.capp.capp.core.database import get_db
from applications.capp.capp.services.compliance import ComplianceService
from applications.capp.capp.api.dependencies.auth import get_current_user
from applications.capp.capp.models.user import User

router = APIRouter()
compliance_service = ComplianceService()

@router.get("/reports/download")
async def download_compliance_report(
    report_type: Literal["CSV", "PDF"] = Query(..., description="Format of the report"),
    year: int = Query(..., description="Year for the report"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Generate and download a compliance report.
    """
    user_id = current_user.id
    
    try:
        report = await compliance_service.generate_report(user_id, report_type, year, session)
        
        media_type = "text/csv" if report_type == "CSV" else "text/plain"
        
        return Response(
            content=report["content"],
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={report['filename']}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
