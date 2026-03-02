from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
import io
import csv

from .. import database, models

router = APIRouter(
    prefix="/compliance/reports",
    tags=["compliance_reports"]
)

@router.get("/csv")
def generate_csv_report(
    organization_id: str = Query(..., description="Organization UUID to generate report for"),
    db: Session = Depends(database.get_db)
):
    """
    Generate a CSV export of all payment executions for an organization.
    This simulates joining an organization's Agent pool against the PaymentMemory logs.
    """
    # 1. In a real app we'd query db.query(models.AgentCredential).filter(org_id=...)
    # and then filter the PaymentMemoryRecord by those exact agent tx_hashes.
    # For this sandbox, we simply stream all recent payment memory records, simulating an org subset.
    
    records = db.query(models.PaymentMemoryRecord).order_by(models.PaymentMemoryRecord.timestamp.desc()).limit(1000).all()
    
    if not records:
         raise HTTPException(status_code=404, detail="No transaction records found for this organization.")

    # 2. Build the CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write Headers
    writer.writerow(["Timestamp_UTC", "Transaction_Hash", "Corridor", "Target_Chain", "Amount_USD", "Execution_Time_ms", "Success", "Error_Reason"])
    
    # Write Rows
    for r in records:
        writer.writerow([
            r.timestamp.isoformat() if r.timestamp else "",
            r.tx_hash,
            r.corridor,
            r.target_chain,
            f"{r.amount_usd:.2f}" if r.amount_usd else "0.00",
            r.execution_time_ms,
            r.success,
            r.error_reason or ""
        ])
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="capp_compliance_report_{organization_id}.csv"'
    }
    
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers=headers
    )
