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

def find_duplicate_lead(
    db: Session,
    email: str,
    domain: Optional[str] = None,
    company_name: Optional[str] = None
) -> Tuple[bool, str, Optional[Lead]]:
    """
    Checks if a lead or company already exists in the database.
    Returns (is_duplicate: bool, reason: str, existing_lead: Optional[Lead])
    """
    norm_email = normalize_email(email)
    if not norm_email:
        return True, "Empty or invalid email", None
        
    # 1. Check normalized email in leads table
    existing_lead = db.query(Lead).filter(Lead.email == norm_email).first()
    if existing_lead:
        return True, f"Lead with email {norm_email} already exists (Lead ID: {existing_lead.id})", existing_lead
        
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
                    return True, f"Lead with email {norm_email} exists for domain {norm_dom} (Lead ID: {lead_in_company.id})", lead_in_company
                    
    return False, "", None

def is_duplicate_lead(
    db: Session,
    email: str,
    domain: Optional[str] = None,
    company_name: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Backward-compatible wrapper returning (is_duplicate: bool, reason: str).
    """
    is_dup, reason, _ = find_duplicate_lead(db, email, domain, company_name)
    return is_dup, reason


def find_duplicate_company(
    db: Session,
    domain: Optional[str] = None,
    company_name: Optional[str] = None,
) -> Tuple[bool, str, Optional[Company]]:
    """
    Checks if a company already exists in the companies registry by canonical domain or name.
    Returns (is_duplicate: bool, reason: str, existing_company: Optional[Company]).
    """
    norm_dom = normalize_domain(domain or "")
    if norm_dom and "." in norm_dom:
        existing = db.query(Company).filter(Company.domain == norm_dom).first()
        if existing:
            return True, f"Company domain '{norm_dom}' already in directory (Company ID: {existing.id})", existing

    norm_cname = normalize_name(company_name or "")
    if norm_cname:
        for candidate in db.query(Company).filter(Company.name.ilike(f"%{company_name.strip()}%")).limit(10).all():
            if normalize_name(candidate.name) == norm_cname:
                return True, f"Company '{candidate.name}' already in directory (Company ID: {candidate.id})", candidate

    return False, "", None
