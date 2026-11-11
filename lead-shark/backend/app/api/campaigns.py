from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Campaign, CampaignStep, Lead, Send, User
from app.schemas.schemas import (
    CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignPreviewRequest, CampaignPreviewResponse
)
from app.core.security import get_current_user, require_roles
from app.services.sending.sender import preview_campaign_email, send_simulated_email
from app.services.compliance.checker import log_audit, check_pre_send_compliance

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.get("", response_model=List[CampaignResponse])
def list_campaigns(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()
    return campaigns

@router.post("", response_model=CampaignResponse)
def create_campaign(
    camp_in: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    campaign = Campaign(
        name=camp_in.name,
        target_sector=camp_in.target_sector,
        target_region=camp_in.target_region,
        subject=camp_in.subject,
        body=camp_in.body,
        daily_limit=camp_in.daily_limit,
        status="draft", # New campaigns start in Draft
        created_by=current_user.id
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Add sequences if provided, or default step 1
    if camp_in.steps:
        for s in camp_in.steps:
            step = CampaignStep(
                campaign_id=campaign.id,
                step_no=s.step_no,
                delay_days=s.delay_days,
                subject=s.subject,
                body=s.body
            )
            db.add(step)
    else:
        # Initial step 1
        step1 = CampaignStep(
            campaign_id=campaign.id,
            step_no=1,
            delay_days=0,
            subject=camp_in.subject,
            body=camp_in.body
        )
        db.add(step1)
        
    db.commit()
    db.refresh(campaign)
    
    log_audit(db, actor=current_user.email, action="campaign_created", object_name=f"campaign:{campaign.id}")
    return campaign

@router.get("/{id}", response_model=CampaignResponse)
def get_campaign(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp

@router.put("/{id}", response_model=CampaignResponse)
def update_campaign(
    id: str,
    camp_in: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Any template edit must reset approval back to Draft!
    template_changed = False
    
    if camp_in.name is not None:
        camp.name = camp_in.name
    if camp_in.target_sector is not None:
        camp.target_sector = camp_in.target_sector
    if camp_in.target_region is not None:
        camp.target_region = camp_in.target_region
    if camp_in.daily_limit is not None:
        camp.daily_limit = camp_in.daily_limit
        
    if camp_in.subject is not None and camp_in.subject != camp.subject:
        camp.subject = camp_in.subject
        template_changed = True
    if camp_in.body is not None and camp_in.body != camp.body:
        camp.body = camp_in.body
        template_changed = True
        
    if template_changed:
        camp.status = "draft"
        camp.approved_by = None
        
    camp.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(camp)
    
    log_audit(
        db, 
        actor=current_user.email, 
        action="campaign_updated", 
        object_name=f"campaign:{camp.id}",
        details={"template_reset_to_draft": template_changed}
    )
    return camp

@router.post("/{id}/submit-for-approval")
def submit_for_approval(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    camp.status = "pending_approval"
    db.commit()
    log_audit(db, actor=current_user.email, action="campaign_submitted_for_approval", object_name=f"campaign:{camp.id}")
    return {"message": "Campaign submitted for reviewer approval", "status": camp.status}

@router.post("/{id}/approve")
def approve_campaign(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "reviewer"]))
):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Strict rule: The campaign creator cannot approve their own campaign!
    # (Unless test bypass if only 1 user exists, but we maintain the separation)
    if camp.created_by == current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Separation of duties violation: The campaign creator cannot approve their own campaign. A designated Reviewer or Admin must approve."
        )
        
    camp.status = "approved"
    camp.approved_by = current_user.id
    camp.updated_at = datetime.utcnow()
    db.commit()
    
    log_audit(db, actor=current_user.email, action="campaign_approved", object_name=f"campaign:{camp.id}")
    return {"message": "Campaign approved for outbound scheduling", "status": camp.status, "approved_by": current_user.email}

@router.post("/{id}/pause")
def pause_campaign(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    camp.status = "paused"
    db.commit()
    log_audit(db, actor=current_user.email, action="campaign_paused", object_name=f"campaign:{camp.id}")
    return {"message": "Campaign paused", "status": camp.status}

@router.post("/{id}/resume")
def resume_campaign(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    camp.status = "sending"
    db.commit()
    log_audit(db, actor=current_user.email, action="campaign_resumed", object_name=f"campaign:{camp.id}")
    return {"message": "Campaign resumed", "status": camp.status}

@router.post("/{id}/preview", response_model=CampaignPreviewResponse)
def preview_campaign(
    id: str,
    req: Optional[CampaignPreviewRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Get a sample lead from matching sector if available
    sample_lead = None
    if req and req.sample_lead_id:
        sample_lead = db.query(Lead).filter(Lead.id == req.sample_lead_id).first()
    else:
        sample_lead = db.query(Lead).filter(Lead.sector == camp.target_sector).first()
        
    preview_data = preview_campaign_email(camp, sample_lead)
    return preview_data

@router.post("/{id}/send-batch")
def send_campaign_batch(
    id: str,
    batch_size: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes a compliant simulated batch send:
    Enforces Pre-Send Checklist (Valid email, not suppressed, approved lead, approved campaign).
    """
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if camp.status not in ["approved", "sending"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send campaign with status '{camp.status}'. Reviewer approval is mandatory."
        )
        
    # Find candidate leads: approved leads in target sector with valid email
    candidates = db.query(Lead).filter(
        Lead.sector == camp.target_sector,
        Lead.status == "approved",
        Lead.email_status == "valid"
    ).limit(batch_size).all()
    
    if not candidates:
        return {
            "sent_count": 0,
            "failed_count": 0,
            "message": "No eligible approved leads found matching target sector."
        }
        
    sent_count = 0
    failed_count = 0
    results = []
    
    for lead in candidates:
        success, message, send = send_simulated_email(
            db=db,
            campaign=camp,
            lead=lead,
            step_no=1,
            actor=current_user.email
        )
        if success:
            sent_count += 1
            results.append({"email": lead.email, "status": "sent", "detail": message})
        else:
            failed_count += 1
            results.append({"email": lead.email, "status": "blocked", "detail": message})
            
    camp.status = "sending"
    db.commit()
    
    return {
        "campaign_id": camp.id,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "results": results
    }
