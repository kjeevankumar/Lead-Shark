from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "sales"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Lead & Company Schemas ---
class CompanyBase(BaseModel):
    name: str
    domain: str
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: str
    created_at: datetime
    class Config:
        from_attributes = True

class LeadBase(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    email: str
    region: Optional[str] = "North America"
    industry: Optional[str] = None
    source_type: Optional[str] = "demo"
    source_url: Optional[str] = None
    lawful_basis_note: Optional[str] = "Legitimate B2B Interest under GDPR Art. 6(1)(f)"

class LeadCreate(LeadBase):
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_phone: Optional[str] = None
    company_description: Optional[str] = None

class LeadResponse(LeadBase):
    id: str
    company_id: Optional[str] = None
    company: Optional[CompanyResponse] = None
    email_status: str
    email_details: Optional[str] = None
    sector: Optional[str] = None
    sector_confidence: float
    sector_reason: Optional[str] = None
    status: str
    collected_at: datetime
    created_at: datetime
    updated_at: datetime
    unsubscribe_token: Optional[str] = None
    
    class Config:
        from_attributes = True

class LeadBulkAction(BaseModel):
    lead_ids: List[str]
    action: str # approve, reject, verify, delete, classify

class LeadImportResponse(BaseModel):
    total_processed: int
    new_leads: int
    duplicates_skipped: int
    message: str

# --- Discovery Schemas ---
class DiscoveryJobCreate(BaseModel):
    job_name: str
    source: str = "demo" # csv, osm, google_places, website, demo
    query: str
    region: Optional[str] = "Global"
    filters: Optional[Dict[str, Any]] = None
    max_results: int = 50
    schedule: str = "once"

class DiscoveryJobResponse(BaseModel):
    id: str
    job_name: str
    source: str
    query: str
    region: Optional[str]
    max_results: int
    schedule: str
    status: str
    total_found: int
    new_leads_count: int
    duplicates_skipped: int
    error_message: Optional[str]
    last_run: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Campaign Schemas ---
class CampaignStepSchema(BaseModel):
    step_no: int
    delay_days: int
    subject: str
    body: str

class CampaignCreate(BaseModel):
    name: str
    target_sector: str
    target_region: Optional[str] = None
    subject: str
    body: str
    daily_limit: int = 50
    steps: Optional[List[CampaignStepSchema]] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    target_sector: Optional[str] = None
    target_region: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    daily_limit: Optional[int] = None
    steps: Optional[List[CampaignStepSchema]] = None

class CampaignResponse(BaseModel):
    id: str
    name: str
    target_sector: str
    target_region: Optional[str]
    subject: str
    body: str
    status: str
    daily_limit: int
    total_sends: int
    created_by: str
    approved_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    steps: List[CampaignStepSchema] = []
    
    class Config:
        from_attributes = True

class CampaignPreviewRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    sample_lead_id: Optional[str] = None

class CampaignPreviewResponse(BaseModel):
    rendered_subject: str
    rendered_body_html: str
    rendered_body_text: str
    sample_lead: Optional[Dict[str, Any]]
    sender_info: Dict[str, str]
    compliance_footer: Dict[str, str]

# --- Compliance & Suppression Schemas ---
class SuppressionCreate(BaseModel):
    email: Optional[str] = None
    domain: Optional[str] = None
    reason: str = "manual" # unsubscribed, hard_bounce, complaint, manual, gdpr_request

class SuppressionResponse(BaseModel):
    id: str
    email: Optional[str]
    domain: Optional[str]
    reason: str
    added_at: datetime
    
    class Config:
        from_attributes = True

class DeleteByEmailRequest(BaseModel):
    email: str
    reason: Optional[str] = "GDPR Article 17 Data Erasure Request"

class PreSendCheckResult(BaseModel):
    is_eligible: bool
    reasons: List[str]
    lead_id: str
    email: str

# --- Webhooks & Events Schemas ---
class EmailEventPayload(BaseModel):
    send_id: Optional[str] = None
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    email: Optional[str] = None
    type: str # delivered, opened, clicked, replied, hard_bounce, soft_bounce, complaint, unsubscribe
    details: Optional[str] = None

# --- Analytics Schemas ---
class OverviewStats(BaseModel):
    total_leads: int
    verified_emails: int
    approved_leads: int
    active_campaigns: int
    emails_sent: int
    delivery_rate: float
    reply_rate: float
    bounce_rate: float
    complaint_rate: float
    unsubscribed_count: int

class SectorStatItem(BaseModel):
    sector: str
    count: int
    verified_count: int

class CampaignStatItem(BaseModel):
    id: str
    name: str
    sector: str
    status: str
    sends: int
    opens: int
    replies: int
    bounces: int
    unsubscribes: int

# --- Audit Log Schemas ---
class AuditLogResponse(BaseModel):
    id: str
    actor: str
    action: str
    object: str
    details: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True
