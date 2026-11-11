import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Lead, Company, User
from app.schemas.schemas import (
    LeadResponse, LeadCreate, LeadBulkAction, LeadImportResponse, DeleteByEmailRequest
)
from app.core.security import get_current_user, require_roles
from app.services.verification.verifier import verify_email_address
from app.services.deduplication.dedup import is_duplicate_lead, normalize_domain, normalize_email
from app.services.classification.rag_classifier import classify_lead_with_rag
from app.services.discovery.connectors import parse_csv_leads
from app.services.compliance.checker import log_audit, execute_data_deletion_by_email

router = APIRouter(prefix="/leads", tags=["Lead Management"])

@router.get("", response_model=List[LeadResponse])
def list_leads(
    search: Optional[str] = None,
    sector: Optional[str] = None,
    region: Optional[str] = None,
    verification_status: Optional[str] = None,
    source_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Lead)
    
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (Lead.name.ilike(search_pattern)) | 
            (Lead.email.ilike(search_pattern)) |
            (Lead.title.ilike(search_pattern))
        )
        
    if sector and sector != "All":
        query = query.filter(Lead.sector == sector)
        
    if region and region != "All":
        query = query.filter(Lead.region == region)
        
    if verification_status and verification_status != "All":
        query = query.filter(Lead.email_status == verification_status)
        
    if source_type and source_type != "All":
        query = query.filter(Lead.source_type == source_type)
        
    if status_filter and status_filter != "All":
        query = query.filter(Lead.status == status_filter)
        
    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return leads

@router.get("/{id}", response_model=LeadResponse)
def get_lead(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.post("/import", response_model=LeadImportResponse)
async def import_leads_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
        
    content = await file.read()
    raw_leads = parse_csv_leads(content)
    
    total_processed = len(raw_leads)
    new_leads = 0
    duplicates_skipped = 0
    
    for item in raw_leads:
        email = normalize_email(item.get("email", ""))
        domain = item.get("company_domain", "")
        
        is_dup, _ = is_duplicate_lead(db, email, domain, item.get("company_name"))
        if is_dup:
            duplicates_skipped += 1
            continue
            
        company = None
        if item.get("company_name"):
            company = db.query(Company).filter(Company.domain == domain).first()
            if not company:
                company = Company(
                    name=item.get("company_name"),
                    domain=domain,
                    website=item.get("company_website"),
                    phone=item.get("company_phone"),
                    description=item.get("company_description"),
                    sector=item.get("industry")
                )
                db.add(company)
                db.commit()
                db.refresh(company)
                
        lead = Lead(
            company_id=company.id if company else None,
            name=item.get("name"),
            title=item.get("title"),
            email=email,
            region=item.get("region", "North America"),
            industry=item.get("industry"),
            sector=item.get("industry"),
            source_type="csv",
            source_url=f"CSV: {file.filename}",
            collected_at=datetime.utcnow(),
            lawful_basis_note=item.get("lawful_basis_note", "CSV Business Contact Import"),
            status="new",
            email_status="unknown"
        )
        db.add(lead)
        new_leads += 1
        
    db.commit()
    log_audit(
        db, 
        actor=current_user.email, 
        action="csv_imported", 
        object_name=f"file:{file.filename}",
        details={"processed": total_processed, "new": new_leads, "duplicates": duplicates_skipped}
    )
    
    return {
        "total_processed": total_processed,
        "new_leads": new_leads,
        "duplicates_skipped": duplicates_skipped,
        "message": f"Successfully imported {new_leads} leads ({duplicates_skipped} duplicates skipped)"
    }

@router.post("/verify")
def verify_leads(
    lead_id: Optional[str] = None,
    verify_all_unverified: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify single lead or all unverified leads via DNS/MX and syntax validation"""
    if lead_id:
        leads_to_verify = db.query(Lead).filter(Lead.id == lead_id).all()
    elif verify_all_unverified:
        leads_to_verify = db.query(Lead).filter(Lead.email_status.in_(["unknown", "new"])).all()
    else:
        leads_to_verify = db.query(Lead).filter(Lead.email_status == "unknown").limit(20).all()
        
    verified_count = 0
    valid_count = 0
    risky_count = 0
    invalid_count = 0
    
    for lead in leads_to_verify:
        result = verify_email_address(lead.email)
        lead.email_status = result["status"]
        lead.email_details = json.dumps(result)
        
        # If valid and currently 'new', update status to 'verified'
        if result["status"] == "valid" and lead.status == "new":
            lead.status = "verified"
            valid_count += 1
        elif result["status"] == "risky":
            risky_count += 1
        elif result["status"] == "invalid":
            invalid_count += 1
            lead.status = "bounced"
            
        verified_count += 1
        
    db.commit()
    log_audit(
        db,
        actor=current_user.email,
        action="leads_verified",
        object_name=f"{verified_count} leads",
        details={"valid": valid_count, "risky": risky_count, "invalid": invalid_count}
    )
    
    return {
        "verified_count": verified_count,
        "valid_count": valid_count,
        "risky_count": risky_count,
        "invalid_count": invalid_count
    }

@router.post("/classify")
def classify_lead_sector(
    lead_id: Optional[str] = None,
    classify_all_unclassified: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Integrates with RAG Lead Segregation Agent (or fallback) for sector classification"""
    if lead_id:
        targets = db.query(Lead).filter(Lead.id == lead_id).all()
    elif classify_all_unclassified:
        targets = db.query(Lead).filter((Lead.sector == None) | (Lead.sector == "") | (Lead.sector == "General Business")).all()
    else:
        targets = db.query(Lead).limit(10).all()
        
    classified_count = 0
    needs_review_count = 0
    
    for lead in targets:
        company_name = lead.company.name if lead.company else (lead.name or "Company")
        website = lead.company.website if lead.company else ""
        desc = lead.company.description if lead.company else ""
        
        res = classify_lead_with_rag(
            company_name=company_name,
            website=website,
            description=desc,
            email=lead.email
        )
        
        lead.sector = res["sector"]
        lead.sector_confidence = res["confidence"]
        lead.sector_reason = f"[{res['source']}] {res['reason']}"
        
        if res.get("needs_review") or res["confidence"] < 0.75:
            needs_review_count += 1
            # Keep in Needs Review state
            if lead.status == "new":
                lead.status = "new"
        classified_count += 1
        
    db.commit()
    log_audit(
        db,
        actor=current_user.email,
        action="leads_classified_rag",
        object_name=f"{classified_count} leads",
        details={"classified": classified_count, "needs_review": needs_review_count}
    )
    
    return {
        "classified_count": classified_count,
        "needs_review_count": needs_review_count,
        "message": f"Classified {classified_count} leads ({needs_review_count} held for human review)"
    }

@router.post("/{id}/approve")
def approve_lead(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "reviewer"]))
):
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    lead.status = "approved"
    db.commit()
    log_audit(db, actor=current_user.email, action="lead_approved", object_name=f"lead:{lead.id}")
    return {"message": "Lead approved for campaign outreach", "lead_id": lead.id, "status": lead.status}

@router.post("/{id}/reject")
def reject_lead(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "reviewer"]))
):
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    lead.status = "rejected"
    db.commit()
    log_audit(db, actor=current_user.email, action="lead_rejected", object_name=f"lead:{lead.id}")
    return {"message": "Lead rejected", "lead_id": lead.id, "status": lead.status}

@router.post("/bulk-action")
def bulk_lead_action(
    payload: LeadBulkAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    action = payload.action.lower()
    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    affected = 0
    
    if action == "approve":
        if current_user.role not in ["admin", "reviewer"]:
            raise HTTPException(status_code=403, detail="Approver or Admin role required")
        for l in leads:
            l.status = "approved"
            affected += 1
    elif action == "reject":
        if current_user.role not in ["admin", "reviewer"]:
            raise HTTPException(status_code=403, detail="Approver or Admin role required")
        for l in leads:
            l.status = "rejected"
            affected += 1
    elif action == "verify":
        for l in leads:
            res = verify_email_address(l.email)
            l.email_status = res["status"]
            l.email_details = json.dumps(res)
            if res["status"] == "valid" and l.status == "new":
                l.status = "verified"
            affected += 1
    elif action == "delete":
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required for bulk deletion")
        for l in leads:
            db.delete(l)
            affected += 1
            
    db.commit()
    log_audit(
        db, 
        actor=current_user.email, 
        action=f"bulk_{action}", 
        object_name=f"{affected} leads"
    )
    return {"action": action, "affected_records": affected}

@router.delete("/by-email")
def delete_lead_by_email(
    req: DeleteByEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """GDPR Article 17 / Data Subject Right to Erasure"""
    count, message = execute_data_deletion_by_email(db, req.email, actor=current_user.email)
    return {"status": "success", "deleted_records": count, "message": message}
