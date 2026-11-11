from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Event, Send, Lead, Campaign
from app.schemas.schemas import EmailEventPayload
from app.services.compliance.checker import add_to_suppression, log_audit
from app.services.sending.sender import check_auto_pause_triggers
from app.services.deduplication.dedup import normalize_email

router = APIRouter(prefix="/webhooks", tags=["Inbound & Webhooks"])

@router.post("/email-events")
def process_email_event(payload: EmailEventPayload, db: Session = Depends(get_db)):
    """
    Handles outbound delivery tracking and inbound events:
    Delivered, Opened, Clicked, Replied, Hard Bounce, Soft Bounce, Complaint, Unsubscribe
    """
    event_type = payload.type.lower()
    send = None
    lead = None
    campaign = None
    
    if payload.send_id:
        send = db.query(Send).filter(Send.id == payload.send_id).first()
        if send:
            lead = send.lead
            campaign = send.campaign
            
    if not lead and payload.email:
        norm_email = normalize_email(payload.email)
        lead = db.query(Lead).filter(Lead.email == norm_email).first()
        
    if not campaign and payload.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == payload.campaign_id).first()
        
    # Create persistent Event record
    event = Event(
        send_id=send.id if send else None,
        lead_id=lead.id if lead else None,
        campaign_id=campaign.id if campaign else (send.campaign_id if send else None),
        type=event_type,
        details=payload.details or f"Event {event_type} received",
        occurred_at=datetime.utcnow()
    )
    db.add(event)
    
    email_for_action = lead.email if lead else payload.email
    
    # Process event business logic
    if event_type == "hard_bounce":
        # Hard bounce -> Permanent suppression
        if email_for_action:
            add_to_suppression(db, email=email_for_action, reason="hard_bounce", actor="webhook_event")
        if lead:
            lead.status = "bounced"
            lead.email_status = "invalid"
            
    elif event_type == "soft_bounce":
        # Soft bounce: check retry count
        if lead:
            lead.email_status = "risky"
            
    elif event_type == "complaint":
        # Complaint -> Immediate suppression and campaign review
        if email_for_action:
            add_to_suppression(db, email=email_for_action, reason="complaint", actor="webhook_event")
        if lead:
            lead.status = "suppressed"
            
    elif event_type == "reply" or event_type == "replied":
        # Reply -> Mark lead replied and halt sequence
        if lead:
            lead.status = "replied"
            
    elif event_type == "unsubscribe":
        # Unsubscribe -> Immediate permanent suppression
        if email_for_action:
            add_to_suppression(db, email=email_for_action, reason="unsubscribed", actor="webhook_event")
        if lead:
            lead.status = "suppressed"
            
    db.commit()
    
    # Check if campaign should be auto-paused (bounce > 3% or complaint > 0.1%)
    camp_id_to_check = campaign.id if campaign else (send.campaign_id if send else None)
    if camp_id_to_check:
        check_auto_pause_triggers(db, camp_id_to_check)
        
    log_audit(
        db,
        actor="webhook_receiver",
        action=f"event_{event_type}",
        object_name=f"email:{email_for_action or 'unknown'}",
        details={"event_type": event_type, "campaign_id": camp_id_to_check}
    )
    
    return {
        "status": "processed",
        "event_type": event_type,
        "email": email_for_action,
        "timestamp": datetime.utcnow().isoformat()
    }
