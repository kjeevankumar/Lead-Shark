import re
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.entities import Lead, Campaign, Send, Event
from app.core.config import settings
from app.services.compliance.checker import check_pre_send_compliance, log_audit

def render_template(content: str, lead: Lead) -> str:
    """Replaces {{first_name}}, {{company}}, {{sector}} merge tags"""
    first_name = lead.name.split()[0] if (lead.name and lead.name.strip()) else "there"
    company_name = lead.company.name if lead.company else "your company"
    sector_name = lead.sector or "Business"
    
    text = content.replace("{{first_name}}", first_name)
    text = text.replace("{{company}}", company_name)
    text = text.replace("{{sector}}", sector_name)
    return text

def build_compliance_footer(lead: Lead) -> Dict[str, str]:
    """Generates mandatory compliance footer with one-click unsubscribe URL and postal address"""
    token = lead.unsubscribe_token or "demo-token"
    # Unsubscribe link target
    unsubscribe_url = f"/unsubscribe/{token}"
    
    text_footer = (
        f"\n\n---\n"
        f"You are receiving this communication regarding {lead.sector or 'business services'} "
        f"under legitimate B2B interest.\n"
        f"Lead Shark Outreach Services | {settings.COMPANY_POSTAL_ADDRESS}\n"
        f"To permanently opt out of all communications: {unsubscribe_url}\n"
    )
    
    html_footer = f"""
    <div style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #E2E8F0; font-size: 12px; color: #64748B; font-family: sans-serif; line-height: 1.5;">
        <p style="margin: 0 0 6px 0;">
            You received this communication because your business contact is listed for legitimate B2B inquiries regarding <strong>{lead.sector or 'your industry'}</strong>.
        </p>
        <p style="margin: 0 0 6px 0;">
            <strong>Lead Shark Inc.</strong> &bull; {settings.COMPANY_POSTAL_ADDRESS}
        </p>
        <p style="margin: 0;">
            <a href="{unsubscribe_url}" style="color: #2563EB; text-decoration: underline;">Click here to permanently unsubscribe</a>
            from all future business communications.
        </p>
    </div>
    """
    
    return {
        "text": text_footer,
        "html": html_footer,
        "unsubscribe_url": unsubscribe_url
    }

def preview_campaign_email(campaign: Campaign, lead: Optional[Lead] = None) -> Dict[str, Any]:
    """Renders a fully merged email preview with compliance headers and footer"""
    mock_lead = lead
    if not mock_lead:
        # Create a mock lead representation for preview
        mock_lead = Lead(
            name="Alex Mercer",
            email="alex.mercer@enterprise-saas.com",
            region="North America",
            sector=campaign.target_sector or "Information Technology"
        )
        
    subject = render_template(campaign.subject, mock_lead)
    body_text = render_template(campaign.body, mock_lead)
    footer = build_compliance_footer(mock_lead)
    
    full_text = body_text + footer["text"]
    full_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1E293B; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="white-space: pre-wrap;">{body_text}</div>
        {footer["html"]}
    </div>
    """
    
    return {
        "rendered_subject": subject,
        "rendered_body_html": full_html,
        "rendered_body_text": full_text,
        "sample_lead": {
            "name": mock_lead.name,
            "email": mock_lead.email,
            "company": mock_lead.company.name if mock_lead.company else "Enterprise Systems Inc",
            "sector": mock_lead.sector
        },
        "sender_info": {
            "from_name": "Outreach Team via Lead Shark",
            "from_address": f"no-reply@{settings.SENDING_DOMAIN}",
            "reply_to": f"connect@{settings.SENDING_DOMAIN}"
        },
        "compliance_footer": {
            "postal_address": settings.COMPANY_POSTAL_ADDRESS,
            "unsubscribe_link": footer["unsubscribe_url"],
            "list_unsubscribe_header": f"<{footer['unsubscribe_url']}>"
        }
    }

def check_auto_pause_triggers(db: Session, campaign_id: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if campaign bounce rate > 3% or complaint rate > 0.1%.
    If so, immediately pauses the campaign to protect domain reputation.
    """
    total_sends = db.query(Send).filter(Send.campaign_id == campaign_id).count()
    if total_sends < 5:
        # Minimum statistical sample size
        return False, None
        
    bounces = db.query(Event).filter(
        Event.campaign_id == campaign_id,
        Event.type.in_(["hard_bounce", "soft_bounce"])
    ).count()
    
    complaints = db.query(Event).filter(
        Event.campaign_id == campaign_id,
        Event.type == "complaint"
    ).count()
    
    bounce_rate = (bounces / total_sends) * 100.0
    complaint_rate = (complaints / total_sends) * 100.0
    
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return False, None
        
    if bounce_rate > settings.MAX_BOUNCE_RATE_PERCENT:
        campaign.status = "paused"
        db.commit()
        reason = f"Auto-paused: Bounce rate {bounce_rate:.1f}% exceeded safety threshold ({settings.MAX_BOUNCE_RATE_PERCENT}%)"
        log_audit(db, actor="safety_monitor", action="campaign_auto_paused", object_name=f"campaign:{campaign_id}", details={"bounce_rate": bounce_rate})
        return True, reason
        
    if complaint_rate > settings.MAX_COMPLAINT_RATE_PERCENT:
        campaign.status = "paused"
        db.commit()
        reason = f"Auto-paused: Complaint rate {complaint_rate:.2f}% exceeded safety threshold ({settings.MAX_COMPLAINT_RATE_PERCENT}%)"
        log_audit(db, actor="safety_monitor", action="campaign_auto_paused", object_name=f"campaign:{campaign_id}", details={"complaint_rate": complaint_rate})
        return True, reason
        
    return False, None

def send_simulated_email(
    db: Session,
    campaign: Campaign,
    lead: Lead,
    step_no: int = 1,
    actor: str = "system"
) -> Tuple[bool, str, Optional[Send]]:
    """
    Safe demo provider send execution:
    Validates pre-send compliance, creates Send record, records mock delivered event,
    and updates campaign counts.
    """
    is_eligible, violations = check_pre_send_compliance(db, lead, campaign)
    if not is_eligible:
        return False, f"Pre-send checklist failed: {'; '.join(violations)}", None
        
    # Check auto-pause triggers
    is_paused, pause_reason = check_auto_pause_triggers(db, campaign.id)
    if is_paused:
        return False, f"Campaign was paused: {pause_reason}", None
        
    # Safe demo send
    msg_id = f"demo_msg_{uuid.uuid4().hex[:12]}"
    send = Send(
        campaign_id=campaign.id,
        lead_id=lead.id,
        step_no=step_no,
        provider_message_id=msg_id,
        sent_at=datetime.utcnow(),
        status="sent"
    )
    db.add(send)
    
    # Update lead status to 'contacted'
    lead.status = "contacted"
    campaign.total_sends += 1
    
    # Auto register a 'delivered' event in demo mode
    db.commit()
    db.refresh(send)
    
    event = Event(
        send_id=send.id,
        lead_id=lead.id,
        campaign_id=campaign.id,
        type="delivered",
        details="Simulated Safe Demo Delivery via Virtual Outbound Queue",
        occurred_at=datetime.utcnow()
    )
    db.add(event)
    db.commit()
    
    log_audit(
        db,
        actor=actor,
        action="email_sent",
        object_name=f"lead:{lead.id}",
        details={
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "email": lead.email,
            "provider_message_id": msg_id,
            "sending_mode": settings.SENDING_MODE
        }
    )
    
    return True, f"Compliant email successfully simulated to {lead.email}", send
