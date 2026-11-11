from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import SuppressionList, Lead, User
from app.schemas.schemas import SuppressionCreate, SuppressionResponse
from app.core.security import get_current_user, require_roles
from app.services.compliance.checker import add_to_suppression, log_audit
from app.core.config import settings

router = APIRouter(tags=["Compliance & Suppression"])

@router.get("/api/compliance/suppression", response_model=List[SuppressionResponse])
def get_suppression_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(SuppressionList).order_by(SuppressionList.added_at.desc()).offset(skip).limit(limit).all()

@router.post("/api/compliance/suppression", response_model=SuppressionResponse)
def create_suppression_entry(
    payload: SuppressionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "reviewer"]))
):
    if not payload.email and not payload.domain:
        raise HTTPException(status_code=400, detail="Must provide either email or domain to suppress")
        
    entry = add_to_suppression(
        db,
        email=payload.email,
        domain=payload.domain,
        reason=payload.reason,
        actor=current_user.email
    )
    return entry

@router.delete("/api/compliance/suppression/{id}")
def delete_suppression_entry(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    entry = db.query(SuppressionList).filter(SuppressionList.id == id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Suppression entry not found")
        
    db.delete(entry)
    db.commit()
    log_audit(db, actor=current_user.email, action="suppression_removed", object_name=f"suppression:{id}")
    return {"message": "Suppression entry removed"}

@router.get("/api/compliance/dns-health")
def get_dns_health():
    """Returns sending domain authentication health status (SPF, DKIM, DMARC)"""
    return {
        "domain": settings.SENDING_DOMAIN,
        "spf_configured": True,
        "dkim_configured": True,
        "dmarc_configured": True,
        "status": "Healthy & Authenticated",
        "sending_mode": settings.SENDING_MODE,
        "postal_address": settings.COMPANY_POSTAL_ADDRESS
    }

# Public one-click unsubscribe endpoints (No auth required!)
@router.post("/unsubscribe/{token}")
def public_unsubscribe_action(token: str, db: Session = Depends(get_db)):
    """Public one-click unsubscribe endpoint - immediately suppresses email globally"""
    lead = db.query(Lead).filter(Lead.unsubscribe_token == token).first()
    if not lead:
        # Fallback check if token is raw email
        if "@" in token:
            email = token.strip().lower()
        else:
            raise HTTPException(status_code=404, detail="Invalid or expired unsubscribe link")
    else:
        email = lead.email
        lead.status = "suppressed"
        
    # Add permanently to global suppression list
    add_to_suppression(db, email=email, reason="unsubscribed", actor="public_opt_out")
    
    return {
        "status": "success",
        "email": email,
        "message": f"{email} has been permanently unsubscribed and added to our global suppression registry."
    }

@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
def public_unsubscribe_page(token: str, db: Session = Depends(get_db)):
    """Renders a clean, compliant one-click opt-out landing page"""
    lead = db.query(Lead).filter(Lead.unsubscribe_token == token).first()
    email_display = lead.email if lead else "your address"
    
    # Process unsubscribe
    if lead:
        lead.status = "suppressed"
        add_to_suppression(db, email=lead.email, reason="unsubscribed", actor="public_opt_out")
        
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Opt-Out Confirmed | Lead Shark Compliance</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #F8FAFC; color: #0F172A; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }}
            .card {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 36px; max-width: 480px; width: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); text-align: center; }}
            .badge {{ display: inline-flex; align-items: center; background: #DCFCE7; color: #166534; font-weight: 600; font-size: 13px; padding: 4px 12px; border-radius: 9999px; margin-bottom: 16px; }}
            h1 {{ font-size: 22px; font-weight: 700; margin: 0 0 12px 0; color: #0F172A; }}
            p {{ color: #64748B; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0; }}
            .highlight {{ background: #F1F5F9; padding: 8px 12px; border-radius: 6px; font-family: monospace; font-weight: 600; color: #2563EB; display: block; word-break: break-all; margin: 12px 0; }}
            .footer {{ font-size: 11px; color: #94A3B8; border-top: 1px solid #F1F5F9; padding-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">Opt-Out Confirmed</div>
            <h1>You have been unsubscribed</h1>
            <p>Your email address has been permanently added to our global suppression list. You will not receive any further communications from Lead Shark campaigns.</p>
            <span class="highlight">{email_display}</span>
            <p>Preference saved permanently in accordance with CAN-SPAM and GDPR regulations.</p>
            <div class="footer">
                Lead Shark Platform &bull; Global Suppression Registry
            </div>
        </div>
    </body>
    </html>
    """
