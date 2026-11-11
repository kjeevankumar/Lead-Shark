import json
from datetime import datetime, timedelta
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import Lead, Campaign, Send, SuppressionList, AuditLog, Company
from app.core.config import settings
from app.services.deduplication.dedup import normalize_email, normalize_domain

def log_audit(db: Session, actor: str, action: str, object_name: str, details: Optional[dict] = None):
    """Create a persistent immutable compliance audit log entry"""
    log_entry = AuditLog(
        actor=actor,
        action=action,
        object=object_name,
        details=json.dumps(details or {}),
        timestamp=datetime.utcnow()
    )
    db.add(log_entry)
    db.commit()

def is_suppressed(db: Session, email: str, domain: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if an email address or its domain is on the global suppression list.
    """
    norm_email = normalize_email(email)
    
    # 1. Check exact email
    supp_email = db.query(SuppressionList).filter(SuppressionList.email == norm_email).first()
    if supp_email:
        return True, f"Email suppressed: {supp_email.reason} (Added: {supp_email.added_at})"
        
    # 2. Check domain suppression
    target_domain = domain
    if not target_domain and "@" in norm_email:
        target_domain = norm_email.split("@")[1]
        
    if target_domain:
        norm_dom = normalize_domain(target_domain)
        supp_domain = db.query(SuppressionList).filter(SuppressionList.domain == norm_dom).first()
        if supp_domain:
            return True, f"Domain '@{norm_dom}' globally suppressed: {supp_domain.reason}"
            
    return False, None

def add_to_suppression(
    db: Session, 
    email: Optional[str] = None, 
    domain: Optional[str] = None, 
    reason: str = "unsubscribed",
    actor: str = "system"
) -> SuppressionList:
    """
    Permanently add an email or domain to global suppression list.
    """
    norm_email = normalize_email(email) if email else None
    norm_domain = normalize_domain(domain) if domain else None
    
    # Check if already exists
    existing = None
    if norm_email:
        existing = db.query(SuppressionList).filter(SuppressionList.email == norm_email).first()
    elif norm_domain:
        existing = db.query(SuppressionList).filter(SuppressionList.domain == norm_domain).first()
        
    if existing:
        return existing
        
    supp = SuppressionList(
        email=norm_email,
        domain=norm_domain,
        reason=reason,
        added_at=datetime.utcnow()
    )
    db.add(supp)
    
    # Update lead status if matching
    if norm_email:
        matching_leads = db.query(Lead).filter(Lead.email == norm_email).all()
        for lead in matching_leads:
            lead.status = "suppressed"
            
    db.commit()
    db.refresh(supp)
    
    log_audit(
        db, 
        actor=actor, 
        action="suppression_added", 
        object_name=f"suppression:{norm_email or norm_domain}",
        details={"reason": reason, "type": "email" if norm_email else "domain"}
    )
    return supp

def check_pre_send_compliance(
    db: Session, 
    lead: Lead, 
    campaign: Campaign
) -> Tuple[bool, List[str]]:
    """
    Enforces the strict 8-point Pre-Send Checklist in code:
    1. Lead email status is 'valid'
    2. Email is not on global suppression list
    3. Domain is not on global suppression list
    4. Lead not contacted within cooldown window (30 days)
    5. Region rules satisfied (legitimate interest note for EU/UK)
    6. Campaign has reviewer approval
    7. Campaign within daily sending limit
    8. Mandatory compliance footer present
    """
    violations = []
    
    # 1. Email verification status must be valid
    if lead.email_status != "valid":
        violations.append(f"Email verification status is '{lead.email_status}'. Only 'valid' emails are campaign-eligible.")
        
    # 2 & 3. Global suppression check (Email & Domain)
    domain = None
    if lead.company and lead.company.domain:
        domain = lead.company.domain
    elif "@" in lead.email:
        domain = lead.email.split("@")[1]
        
    suppressed, supp_reason = is_suppressed(db, lead.email, domain)
    if suppressed:
        violations.append(f"Suppression Rule: {supp_reason}")
        
    # 4. Cooldown window (e.g. 30 days)
    cooldown_cutoff = datetime.utcnow() - timedelta(days=settings.COOLDOWN_DAYS)
    recent_send = db.query(Send).filter(
        Send.lead_id == lead.id,
        Send.sent_at >= cooldown_cutoff,
        Send.status.in_(["sent", "delivered"])
    ).first()
    if recent_send:
        violations.append(f"Cooldown active: Contacted on {recent_send.sent_at.strftime('%Y-%m-%d')} (30-day quiet period)")
        
    # 5. Region compliance checks
    if lead.region and "europe" in lead.region.lower():
        if not lead.lawful_basis_note or "legitimate" not in lead.lawful_basis_note.lower():
            violations.append("GDPR/PECR Compliance: Missing legitimate-interest documentation for EU/UK recipient")
            
    # 6. Campaign Approval Check
    if campaign.status not in ["approved", "scheduled", "sending"]:
        violations.append(f"Campaign status is '{campaign.status}'. Mandatory Reviewer Approval is required before sending.")
        
    # 7. Daily limit check
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sends_count = db.query(Send).filter(
        Send.campaign_id == campaign.id,
        Send.sent_at >= today_start
    ).count()
    if today_sends_count >= campaign.daily_limit:
        violations.append(f"Daily volume limit reached ({today_sends_count}/{campaign.daily_limit})")
        
    # 8. Mandatory postal address check
    if not settings.COMPANY_POSTAL_ADDRESS or len(settings.COMPANY_POSTAL_ADDRESS.strip()) < 10:
        violations.append("CAN-SPAM: Physical postal address must be configured before outbound sending")
        
    is_eligible = len(violations) == 0
    return is_eligible, violations

def execute_data_deletion_by_email(db: Session, email: str, actor: str = "admin") -> Tuple[int, str]:
    """
    Executes GDPR Article 17 / DPDP Right to Erasure:
    Deletes all lead and personal contact records, but retains email in permanent suppression
    to prevent future re-import.
    """
    norm_email = normalize_email(email)
    leads = db.query(Lead).filter(Lead.email == norm_email).all()
    count = len(leads)
    
    for l in leads:
        db.delete(l)
        
    # Add to permanent suppression with 'gdpr_request' reason
    add_to_suppression(db, email=norm_email, reason="gdpr_request", actor=actor)
    
    db.commit()
    log_audit(
        db, 
        actor=actor, 
        action="gdpr_data_erasure", 
        object_name=f"email:{norm_email}", 
        details={"deleted_records_count": count}
    )
    return count, f"Erased {count} records associated with {norm_email}. Email permanently suppressed."
