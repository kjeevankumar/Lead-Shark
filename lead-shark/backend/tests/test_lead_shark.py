import pytest
import asyncio
from app.main import app, health_check
from app.database import SessionLocal
from app.models.entities import Lead, Campaign, User, SuppressionList
from app.schemas.schemas import (
    UserLogin, DiscoveryJobCreate, CampaignCreate, CampaignUpdate,
    CampaignPreviewRequest, DeleteByEmailRequest, EmailEventPayload
)
from app.api.auth import login, switch_demo_role
from app.api.discovery import create_discovery_job, list_discovery_jobs
from app.api.leads import list_leads, verify_leads, classify_lead_sector, approve_lead, reject_lead, delete_lead_by_email
from app.api.campaigns import create_campaign, update_campaign, approve_campaign, preview_campaign, send_campaign_batch
from app.api.compliance import get_suppression_list, public_unsubscribe_action
from app.api.webhooks import process_email_event
from app.api.analytics import read_overview
from app.services.verification.verifier import verify_email_address
from app.services.deduplication.dedup import is_duplicate_lead

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def admin_user(db):
    return db.query(User).filter(User.role == "admin").first()

@pytest.fixture
def reviewer_user(db):
    return db.query(User).filter(User.role == "reviewer").first()

@pytest.fixture
def sales_user(db):
    return db.query(User).filter(User.role == "sales").first()

def test_health_check(db):
    res = health_check(db)
    assert res["status"] == "healthy"
    assert res["database"] == "connected"

def test_auth_login(db):
    res = login(UserLogin(email="admin@leadshark.io", password="LeadShark2026!"), db)
    assert res["access_token"] is not None
    assert res["user"].email == "admin@leadshark.io"
    assert res["user"].role == "admin"

def test_email_verification_logic():
    # Valid domain
    res_valid = verify_email_address("test@apexcloud.io")
    assert res_valid["status"] == "valid"
    assert res_valid["mx_found"] is True
    
    # Freemail is classified as risky for B2B cold outreach
    res_free = verify_email_address("alex@gmail.com")
    assert res_free["status"] == "risky"
    assert res_free["is_freemail"] is True
    
    # Invalid syntax
    res_invalid = verify_email_address("invalid-email")
    assert res_invalid["status"] == "invalid"

def test_deduplication(db):
    # Existing lead
    is_dup, reason = is_duplicate_lead(db, "s.jenkins@apexcloud.io")
    assert is_dup is True
    
    # Brand new lead
    is_dup_new, _ = is_duplicate_lead(db, "unique_brand_new_lead_test@nowhere.com")
    assert is_dup_new is False

def test_discovery_job(db, sales_user):
    job_in = DiscoveryJobCreate(
        job_name="Pytest IT Discovery",
        source="demo",
        query="cloud systems",
        region="North America",
        max_results=3
    )
    job = create_discovery_job(job_in, db, sales_user)
    assert job.status == "completed"
    assert job.total_found > 0

def test_rag_classification(db, reviewer_user):
    res = classify_lead_sector(lead_id=None, classify_all_unclassified=False, db=db, current_user=reviewer_user)
    assert res["classified_count"] > 0

def test_campaign_lifecycle_and_approval_separation(db, sales_user, reviewer_user):
    # 1. Sales creates draft campaign
    camp_in = CampaignCreate(
        name="Automated Test Campaign",
        target_sector="Information Technology",
        target_region="North America",
        subject="Optimizing compute for {{company}}",
        body="Hi {{first_name}},\n\nReaching out to {{company}} about {{sector}} telemetry."
    )
    camp = create_campaign(camp_in, db, sales_user)
    assert camp.status == "draft"
    
    # 2. Preview email
    prev = preview_campaign(camp.id, None, db, sales_user)
    assert "rendered_subject" in prev
    assert "compliance_footer" in prev
    
    # 3. Separation of duties: Sales cannot approve their own campaign
    with pytest.raises(Exception):
        approve_campaign(camp.id, db, sales_user)
        
    # 4. Reviewer approves
    res = approve_campaign(camp.id, db, reviewer_user)
    assert res["status"] == "approved"
    
    # 5. Template edit resets back to draft
    updated = update_campaign(camp.id, CampaignUpdate(subject="Updated subject {{company}}"), db, sales_user)
    assert updated.status == "draft"

def test_pre_send_checklist_and_batch_send(db, reviewer_user):
    # Ensure campaign is approved
    camp = db.query(Campaign).filter(Campaign.target_sector == "Information Technology").first()
    approve_campaign(camp.id, db, reviewer_user)
    
    # Create a fresh, eligible test lead not in cooldown and not suppressed
    fresh_email = "fresh_it_contact_qa@apexcloud.io"
    # Ensure not suppressed
    db.query(SuppressionList).filter(SuppressionList.email == fresh_email).delete()
    lead = db.query(Lead).filter(Lead.email == fresh_email).first()
    if not lead:
        lead = Lead(
            name="Apex Engineering Lead",
            email=fresh_email,
            email_status="valid",
            status="approved",
            region="North America",
            sector="Information Technology",
            sector_confidence=0.95,
            lawful_basis_note="Legitimate B2B Interest under GDPR Art. 6(1)(f)"
        )
        db.add(lead)
    else:
        lead.email_status = "valid"
        lead.status = "approved"
        lead.sector = "Information Technology"
        lead.sector_confidence = 0.95
    db.commit()
        
    # Send simulated batch
    batch_res = send_campaign_batch(camp.id, batch_size=2, db=db, current_user=reviewer_user)
    assert batch_res["campaign_id"] == camp.id
    assert batch_res["sent_count"] > 0

def test_public_one_click_unsubscribe(db):
    lead = db.query(Lead).first()
    token = lead.unsubscribe_token
    
    res = public_unsubscribe_action(token, db)
    assert res["status"] == "success"
    
    supp_list = get_suppression_list(0, 100, db, lead)
    supp_emails = [s.email for s in supp_list if s.email]
    assert lead.email in supp_emails

def test_analytics_and_audit(db, admin_user):
    stats = read_overview(db, admin_user)
    assert stats["total_leads"] > 0
    assert stats["emails_sent"] > 0
    assert "delivery_rate" in stats
