import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="sales") # admin, reviewer, sales
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), index=True, nullable=False)
    domain = Column(String(255), index=True, nullable=False)
    website = Column(String(500), nullable=True)
    phone = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    sector = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    leads = relationship("Lead", back_populates="company")

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    name = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    email = Column(String(255), index=True, nullable=False)
    email_status = Column(String(50), default="unknown") # valid, risky, invalid, unknown
    email_details = Column(Text, nullable=True) # JSON string: mx_found, is_role_based, is_freemail
    region = Column(String(100), default="North America")
    industry = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)
    sector_confidence = Column(Float, default=0.0)
    sector_reason = Column(Text, nullable=True)
    source_type = Column(String(50), default="demo") # csv, osm, google_places, website, demo
    source_url = Column(String(500), nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)
    lawful_basis_note = Column(String(500), default="Legitimate B2B Interest under GDPR Art. 6(1)(f) / Lawful Business Inquiry")
    status = Column(String(50), default="new") # new, verified, approved, contacted, replied, bounced, suppressed, rejected
    unsubscribe_token = Column(String(64), unique=True, index=True, default=gen_uuid)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="leads")
    sends = relationship("Send", back_populates="lead")

class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    job_name = Column(String(255), nullable=False)
    source = Column(String(50), nullable=False) # csv, osm, google_places, website, demo
    query = Column(String(255), nullable=False)
    region = Column(String(100), nullable=True)
    filters = Column(Text, nullable=True)
    max_results = Column(Integer, default=50)
    schedule = Column(String(50), default="once")
    status = Column(String(50), default="completed") # pending, running, completed, failed
    total_found = Column(Integer, default=0)
    new_leads_count = Column(Integer, default=0)
    duplicates_skipped = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    last_run = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    target_sector = Column(String(100), nullable=False)
    target_region = Column(String(100), nullable=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), default="draft") # draft, pending_approval, approved, scheduled, sending, paused, completed
    daily_limit = Column(Integer, default=50)
    total_sends = Column(Integer, default=0)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    steps = relationship("CampaignStep", back_populates="campaign", cascade="all, delete-orphan")
    sends = relationship("Send", back_populates="campaign")

class CampaignStep(Base):
    __tablename__ = "campaign_steps"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    step_no = Column(Integer, default=1)
    delay_days = Column(Integer, default=0)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    
    campaign = relationship("Campaign", back_populates="steps")

class Send(Base):
    __tablename__ = "sends"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False)
    step_no = Column(Integer, default=1)
    provider_message_id = Column(String(255), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="sent") # queued, sent, delivered, bounced, failed
    
    campaign = relationship("Campaign", back_populates="sends")
    lead = relationship("Lead", back_populates="sends")
    events = relationship("Event", back_populates="send")

class Event(Base):
    __tablename__ = "events"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    send_id = Column(String(36), ForeignKey("sends.id"), nullable=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True)
    type = Column(String(50), nullable=False) # delivered, opened, clicked, replied, hard_bounce, soft_bounce, complaint, unsubscribe
    details = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow)
    
    send = relationship("Send", back_populates="events")

class SuppressionList(Base):
    __tablename__ = "suppression_list"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), index=True, nullable=True)
    domain = Column(String(255), index=True, nullable=True)
    reason = Column(String(100), default="unsubscribed") # unsubscribed, hard_bounce, complaint, manual, gdpr_request
    added_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    actor = Column(String(255), nullable=False) # user email or "system"
    action = Column(String(100), nullable=False) # e.g. "campaign_approved", "lead_verified", etc.
    object = Column(String(255), nullable=False) # e.g. "campaign:...", "lead:..."
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
