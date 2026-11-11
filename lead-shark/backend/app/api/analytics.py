import io
import csv
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Lead, User
from app.core.security import get_current_user
from app.services.analytics.stats import get_overview_statistics, get_campaign_analytics_list

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
def read_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_overview_statistics(db)

@router.get("/campaigns")
def read_campaign_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_campaign_analytics_list(db)

@router.get("/export-csv")
def export_leads_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Exports all lead records into compliant CSV format"""
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "Lead ID", "Contact Name", "Job Title", "Email", "Company Name",
        "Company Website", "Region", "Industry", "Sector (RAG)", 
        "Verification Status", "Lead Status", "Lawful Basis Note", "Source URL"
    ])
    
    for l in leads:
        writer.writerow([
            l.id,
            l.name or "",
            l.title or "",
            l.email,
            l.company.name if l.company else "",
            l.company.website if l.company else "",
            l.region or "",
            l.industry or "",
            l.sector or "",
            l.email_status,
            l.status,
            l.lawful_basis_note or "",
            l.source_url or ""
        ])
        
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leadshark_leads_export.csv"}
    )
