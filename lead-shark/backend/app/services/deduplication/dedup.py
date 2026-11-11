import re
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models.entities import Lead, Company

def normalize_email(email: str) -> str:
    if not email:
        return ""
    return email.strip().lower()

def normalize_domain(domain_or_url: str) -> str:
    if not domain_or_url:
        return ""
    d = domain_or_url.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0].split(":")[0]
    return d

def normalize_name(name: str) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())

def is_duplicate_lead(
    db: Session,
    email: str,
    domain: Optional[str] = None,
    company_name: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Checks if a lead or company already exists in the database.
    Returns (is_duplicate: bool, reason: str)
    """
    norm_email = normalize_email(email)
    if not norm_email:
        return True, "Empty or invalid email"
        
    # 1. Check normalized email in leads table
    existing_lead = db.query(Lead).filter(Lead.email == norm_email).first()
    if existing_lead:
        return True, f"Lead with email {norm_email} already exists (ID: {existing_lead.id})"
        
    # 2. Check company domain if given
    if domain:
        norm_dom = normalize_domain(domain)
        if norm_dom:
            existing_company = db.query(Company).filter(Company.domain == norm_dom).first()
            if existing_company:
                # Check if this company already has this email
                lead_in_company = db.query(Lead).filter(
                    Lead.company_id == existing_company.id,
                    Lead.email == norm_email
                ).first()
                if lead_in_company:
                    return True, f"Lead with email {norm_email} exists for domain {norm_dom}"
                    
    return False, ""
