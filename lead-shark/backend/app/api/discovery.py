import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import DiscoveryJob, Lead, Company, User
from app.schemas.schemas import DiscoveryJobCreate, DiscoveryJobResponse
from app.core.security import get_current_user
from app.services.discovery.connectors import DemoDiscoveryConnector, OpenStreetMapConnector
from app.services.deduplication.dedup import is_duplicate_lead, normalize_domain, normalize_email
from app.services.compliance.checker import log_audit

router = APIRouter(prefix="/discovery", tags=["Lead Discovery"])

@router.post("/jobs", response_model=DiscoveryJobResponse)
def create_discovery_job(
    job_in: DiscoveryJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create Job record
    job = DiscoveryJob(
        job_name=job_in.job_name,
        source=job_in.source,
        query=job_in.query,
        region=job_in.region,
        filters=json.dumps(job_in.filters or {}),
        max_results=job_in.max_results,
        schedule=job_in.schedule,
        status="running",
        last_run=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Execute connector
    try:
        if job_in.source == "osm":
            connector = OpenStreetMapConnector()
        else:
            # Default to Demo Discovery Connector (safely labeled sample data)
            connector = DemoDiscoveryConnector()
            
        raw_leads = connector.search(
            query=job_in.query,
            region=job_in.region,
            max_results=job_in.max_results
        )
        
        total_found = len(raw_leads)
        new_leads_count = 0
        duplicates_skipped = 0
        
        for item in raw_leads:
            norm_email = normalize_email(item.get("email", ""))
            domain = normalize_domain(item.get("company_domain", "") or norm_email.split("@")[1])
            
            # Check duplication
            is_dup, _ = is_duplicate_lead(db, norm_email, domain, item.get("company_name"))
            if is_dup:
                duplicates_skipped += 1
                continue
                
            # Create or find company
            company = None
            if item.get("company_name"):
                company = db.query(Company).filter(Company.domain == domain).first()
                if not company:
                    company = Company(
                        name=item.get("company_name"),
                        domain=domain,
                        website=item.get("company_website"),
                        phone=item.get("company_phone"),
                        description=item.get("company_description"),
                        sector=item.get("industry")
                    )
                    db.add(company)
                    db.commit()
                    db.refresh(company)
                    
            lead = Lead(
                company_id=company.id if company else None,
                name=item.get("name"),
                title=item.get("title"),
                email=norm_email,
                region=item.get("region", "North America"),
                industry=item.get("industry"),
                sector=item.get("industry"),
                source_type=item.get("source_type", job_in.source),
                source_url=item.get("source_url", "https://leadshark.io/demo"),
                collected_at=datetime.utcnow(),
                lawful_basis_note=item.get("lawful_basis_note", "Public Directory / Business Inquiry"),
                status="new",
                email_status="unknown"
            )
            db.add(lead)
            new_leads_count += 1
            
        db.commit()
        
        job.status = "completed"
        job.total_found = total_found
        job.new_leads_count = new_leads_count
        job.duplicates_skipped = duplicates_skipped
        db.commit()
        db.refresh(job)
        
        log_audit(
            db,
            actor=current_user.email,
            action="discovery_job_completed",
            object_name=f"job:{job.id}",
            details={"found": total_found, "new": new_leads_count, "duplicates": duplicates_skipped}
        )
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        db.refresh(job)
        
    return job

@router.get("/jobs", response_model=List[DiscoveryJobResponse])
def list_discovery_jobs(
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/jobs/{id}", response_model=DiscoveryJobResponse)
def get_discovery_job(
    id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")
    return job
