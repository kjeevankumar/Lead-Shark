from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.entities import User, Company, Lead, Campaign, CampaignStep, SuppressionList, AuditLog
from app.core.security import get_password_hash

def seed_database(db: Session):
    # 1. Seed Users (Admin, Reviewer, Sales)
    if db.query(User).count() == 0:
        admin = User(
            email="admin@leadshark.io",
            hashed_password=get_password_hash("LeadShark2026!"),
            full_name="Chief Compliance Officer",
            role="admin"
        )
        reviewer = User(
            email="reviewer@leadshark.io",
            hashed_password=get_password_hash("LeadShark2026!"),
            full_name="Lead & Campaign Reviewer",
            role="reviewer"
        )
        sales = User(
            email="sales@leadshark.io",
            hashed_password=get_password_hash("LeadShark2026!"),
            full_name="Outreach Representative",
            role="sales"
        )
        db.add_all([admin, reviewer, sales])
        db.commit()
        
    # 2. Seed Initial Companies & Leads
    if db.query(Lead).count() == 0:
        c1 = Company(
            name="Apex Cloud Systems",
            domain="apexcloud.io",
            website="https://apexcloud.io",
            phone="+1-415-555-0199",
            address="100 Pine St, San Francisco, CA 94111",
            sector="Information Technology",
            description="Enterprise Kubernetes orchestration and cloud cost optimization platform."
        )
        c2 = Company(
            name="Quantum Nexus Robotics",
            domain="quantumnex.com",
            website="https://quantumnex.com",
            phone="+1-312-555-0142",
            address="400 N Michigan Ave, Chicago, IL 60611",
            sector="Manufacturing & Industrial",
            description="Autonomous automated guided vehicles (AGVs) for high-density logistics warehouses."
        )
        c3 = Company(
            name="Aurora BioPharma EU",
            domain="aurorabiopharma.eu",
            website="https://aurorabiopharma.eu",
            phone="+44-20-7946-0192",
            address="250 Euston Rd, London NW1 2PG, UK",
            sector="Healthcare & Life Sciences",
            description="Novel immunotherapies and clinical oncology research data platforms."
        )
        c4 = Company(
            name="SilverPeak Capital",
            domain="silverpeakcapital.com",
            website="https://silverpeakcapital.com",
            phone="+1-212-555-0821",
            address="375 Park Ave, New York, NY 10152",
            sector="Financial Services",
            description="Growth equity investment firm partnering with high-margin enterprise B2B SaaS companies."
        )
        c5 = Company(
            name="Lumière Modern Goods",
            domain="lumierestore.fr",
            website="https://lumierestore.fr",
            phone="+33-1-42-68-55-00",
            address="15 Rue de la Paix, 75002 Paris, France",
            sector="Retail & E-Commerce",
            description="Direct-to-consumer luxury apparel and eco-conscious lifestyle retail chain."
        )
        
        db.add_all([c1, c2, c3, c4, c5])
        db.commit()
        
        l1 = Lead(
            company_id=c1.id,
            name="Sarah Jenkins",
            title="VP of Engineering",
            email="s.jenkins@apexcloud.io",
            email_status="valid",
            region="North America",
            industry="Information Technology",
            sector="Information Technology",
            sector_confidence=0.96,
            sector_reason="Classified: Cloud infrastructure and container orchestration software",
            source_type="demo",
            source_url="https://apexcloud.io/leadership",
            lawful_basis_note="Legitimate B2B Interest under GDPR Art. 6(1)(f) / CAN-SPAM compliant inquiry",
            status="approved"
        )
        l2 = Lead(
            company_id=c1.id,
            name="David Miller",
            title="Head of Cloud Architecture",
            email="d.miller@apexcloud.io",
            email_status="valid",
            region="North America",
            industry="Information Technology",
            sector="Information Technology",
            sector_confidence=0.94,
            sector_reason="Classified: Cloud architecture and DevOps systems",
            source_type="demo",
            source_url="https://apexcloud.io/team",
            lawful_basis_note="Legitimate B2B Interest / Public Executive Listing",
            status="approved"
        )
        l3 = Lead(
            company_id=c2.id,
            name="Marcus Vance",
            title="Director of Supply Chain",
            email="m.vance@quantumnex.com",
            email_status="valid",
            region="North America",
            industry="Manufacturing & Industrial",
            sector="Manufacturing & Industrial",
            sector_confidence=0.91,
            sector_reason="Classified: Industrial robotics & automated warehouse equipment",
            source_type="demo",
            source_url="https://quantumnex.com/contact",
            lawful_basis_note="Legitimate B2B Interest",
            status="verified"
        )
        l4 = Lead(
            company_id=c3.id,
            name="Dr. Elena Rostova",
            title="Chief Medical Officer",
            email="elena.rostova@aurorabiopharma.eu",
            email_status="valid",
            region="Europe (UK/EU)",
            industry="Healthcare & Life Sciences",
            sector="Healthcare & Life Sciences",
            sector_confidence=0.95,
            sector_reason="Classified: Clinical oncology therapeutics and biotech research",
            source_type="demo",
            source_url="https://aurorabiopharma.eu/team",
            lawful_basis_note="Legitimate B2B Interest under GDPR Art. 6(1)(f) / PECR Regulation",
            status="approved"
        )
        l5 = Lead(
            company_id=c4.id,
            name="Robert Sterling",
            title="Managing Director",
            email="r.sterling@silverpeakcapital.com",
            email_status="valid",
            region="North America",
            industry="Financial Services",
            sector="Financial Services",
            sector_confidence=0.89,
            sector_reason="Classified: Private equity and enterprise software growth capital",
            source_type="demo",
            source_url="https://silverpeakcapital.com/partners",
            lawful_basis_note="Legitimate B2B Inquiry",
            status="new"
        )
        l6 = Lead(
            company_id=c5.id,
            name="Chloe Dupont",
            title="VP of E-Commerce",
            email="chloe.dupont@lumierestore.fr",
            email_status="risky",
            region="Europe (UK/EU)",
            industry="Retail & E-Commerce",
            sector="Retail & E-Commerce",
            sector_confidence=0.72,
            sector_reason="Needs human review: E-commerce retail brand with mixed corporate presence",
            source_type="demo",
            source_url="https://lumierestore.fr/about",
            lawful_basis_note="Legitimate B2B Interest",
            status="new"
        )
        l7 = Lead(
            name="Anonymous Contact",
            title="Freelance Consultant",
            email="alex992@gmail.com",
            email_status="risky",
            region="North America",
            industry="Consulting",
            sector="Professional & Legal Services",
            sector_confidence=0.60,
            sector_reason="Consumer freemail domain flagged as non-business address",
            source_type="demo",
            source_url="https://leadshark.io/demo",
            lawful_basis_note="Excluded from cold outreach by policy",
            status="new"
        )
        
        db.add_all([l1, l2, l3, l4, l5, l6, l7])
        db.commit()

    # 3. Seed Campaigns
    admin_user = db.query(User).filter(User.role == "admin").first()
    reviewer_user = db.query(User).filter(User.role == "reviewer").first()
    sales_user = db.query(User).filter(User.role == "sales").first()
    
    if db.query(Campaign).count() == 0 and admin_user:
        camp1 = Campaign(
            name="Q4 Enterprise Cloud Infrastructure Outreach",
            target_sector="Information Technology",
            target_region="North America",
            subject="Scaling container infrastructure for {{company}}",
            body="Hi {{first_name}},\n\nI noticed {{company}}'s recent expansion in enterprise cloud workloads. Many engineering teams in the {{sector}} space struggle with multi-cluster cost transparency.\n\nWe built an automated telemetry engine that cuts compute spend by 28% without sacrificing latency. Would you be open to a brief 10-minute briefing next Tuesday?\n\nBest regards,\nDevin Cole\nLead Shark Enterprise Solutions",
            status="approved",
            daily_limit=50,
            created_by=sales_user.id if sales_user else admin_user.id,
            approved_by=reviewer_user.id if reviewer_user else admin_user.id
        )
        db.add(camp1)
        db.commit()
        db.refresh(camp1)
        
        step1 = CampaignStep(
            campaign_id=camp1.id,
            step_no=1,
            delay_days=0,
            subject="Scaling container infrastructure for {{company}}",
            body=camp1.body
        )
        step2 = CampaignStep(
            campaign_id=camp1.id,
            step_no=2,
            delay_days=4,
            subject="Re: Scaling container infrastructure for {{company}}",
            body="Hi {{first_name}},\n\nFollowing up on my note below regarding {{company}}'s cloud infrastructure. Happy to share a quick benchmark report for {{sector}} if that's more useful.\n\nBest,\nDevin"
        )
        db.add_all([step1, step2])
        db.commit()

    # 4. Seed Global Suppression List
    if db.query(SuppressionList).count() == 0:
        s1 = SuppressionList(
            email="optout@competitor.com",
            reason="unsubscribed",
            added_at=datetime.utcnow() - timedelta(days=5)
        )
        s2 = SuppressionList(
            domain="spamtrapsite.org",
            reason="hard_bounce",
            added_at=datetime.utcnow() - timedelta(days=12)
        )
        s3 = SuppressionList(
            email="legal-inquiries@donotcontact.com",
            reason="gdpr_request",
            added_at=datetime.utcnow() - timedelta(days=20)
        )
        db.add_all([s1, s2, s3])
        db.commit()
        
    # 5. Seed Audit Log
    if db.query(AuditLog).count() == 0:
        a1 = AuditLog(
            actor="system",
            action="database_initialized",
            object="system",
            details='{"version": "1.0.0", "framework": "Lead Shark Engine"}',
            timestamp=datetime.utcnow() - timedelta(days=1)
        )
        a2 = AuditLog(
            actor="reviewer@leadshark.io",
            action="campaign_approved",
            object="campaign:Q4 Enterprise Cloud Infrastructure Outreach",
            details='{"approved_by": "reviewer@leadshark.io", "compliance_checked": true}',
            timestamp=datetime.utcnow() - timedelta(hours=3)
        )
        db.add_all([a1, a2])
        db.commit()
