import json
import math
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.database import get_db
from app.models.entities import Company, DiscoveryJob, DiscoveryResult, Lead, User
from app.schemas.schemas import (
    DiscoveryJobCreate,
    DiscoveryJobResponse,
    DiscoveryResultResponse,
    DiscoveryResultsPageResponse,
)
from app.services.compliance.checker import log_audit
from app.services.deduplication.dedup import (
    find_duplicate_company,
    find_duplicate_lead,
    normalize_domain,
    normalize_email,
    normalize_name,
)
from app.services.discovery.orchestrator import execute_universal_discovery
from app.services.verification.verifier import verify_email_address

router = APIRouter(prefix="/discovery", tags=["Lead Discovery"])


@router.get("/providers")
def get_discovery_providers(current_user: User = Depends(get_current_user)):
    """Returns active and optional external discovery adapters without exposing credentials."""
    return {
        "providers": [
            {
                "id": "all",
                "name": "All Live Public Sources (Universal Search)",
                "type": "live",
                "configured": True,
                "description": "Searches Wikidata, Wikipedia Business Graph, OpenStreetMap (Nominatim/Photon/Overpass), Public Company Directory, and External APIs concurrently.",
            },
            {
                "id": "wikidata",
                "name": "Wikidata & Wikipedia Business Graph",
                "type": "live",
                "configured": True,
                "description": "Structured knowledge graph retrieving official websites, HQ cities, countries, industries, and public contacts.",
            },
            {
                "id": "osm",
                "name": "OpenStreetMap / Overpass / Photon",
                "type": "live",
                "configured": True,
                "description": "Permitted ODbL open geographic business directory using dynamic location geocoding.",
            },
            {
                "id": "company_directory",
                "name": "Public Company Domain Directory",
                "type": "live",
                "configured": True,
                "description": "Real-time corporate domain resolution by company name or brand.",
            },
            {
                "id": "external_search",
                "name": "External Search APIs",
                "type": "live",
                "configured": True,
                "commercial_keys": {
                    "google_places": bool(settings.GOOGLE_PLACES_API_KEY),
                    "serper": bool(settings.SERPER_API_KEY),
                    "brave_search": bool(settings.BRAVE_SEARCH_API_KEY),
                },
                "description": "Uses configured Search/Places API keys plus DuckDuckGo public company lookup.",
            },
            {
                "id": "google_places",
                "name": "Google Places Business API",
                "type": "live",
                "configured": bool(settings.GOOGLE_PLACES_API_KEY),
                "description": "Requires GOOGLE_PLACES_API_KEY in backend environment.",
            },
            {
                "id": "website",
                "name": "Company Website (robots.txt compliant)",
                "type": "live",
                "configured": True,
                "description": "Extracts publicly listed corporate contact details strictly obeying robots.txt.",
            },
            {
                "id": "demo",
                "name": "Demo Data (Synthetic Sample Dataset)",
                "type": "demo",
                "configured": True,
                "description": "Clearly labeled synthetic data strictly isolated for presentation & QA testing.",
            },
        ]
    }


def _trunc(val: Optional[str], max_len: int) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if len(s) <= max_len:
        return s
    return s[:max_len]


def _persist_company(db: Session, item: Dict, domain: str) -> Optional[Company]:
    company_name = _trunc(item.get("company_name") or "", 250)
    if not company_name:
        return None
    safe_domain = _trunc(domain or normalize_name(company_name), 250) or normalize_name(company_name)[:250]
    existing = None
    if safe_domain and "." in safe_domain:
        existing = db.query(Company).filter(Company.domain == safe_domain).first()
    if not existing:
        existing = Company(
            name=company_name,
            domain=safe_domain,
            website=item.get("company_website"),
            phone=_trunc(item.get("company_phone"), 250),
            sector=_trunc(item.get("industry"), 250),
            industry=_trunc(item.get("industry"), 250),
            business_category=_trunc(item.get("business_category"), 250),
            country=_trunc(item.get("country"), 250),
            city=_trunc(item.get("city"), 250),
            region=_trunc(item.get("region"), 250),
            description=item.get("company_description"),
        )
        db.add(existing)
        db.flush()
    else:
        if not existing.website and item.get("company_website"):
            existing.website = item.get("company_website")
        if not existing.phone and item.get("company_phone"):
            existing.phone = _trunc(item.get("company_phone"), 250)
        if not existing.country and item.get("country"):
            existing.country = _trunc(item.get("country"), 250)
        if not existing.city and item.get("city"):
            existing.city = _trunc(item.get("city"), 250)
        if not existing.region and item.get("region"):
            existing.region = _trunc(item.get("region"), 250)
        if not existing.business_category and item.get("business_category"):
            existing.business_category = _trunc(item.get("business_category"), 250)
        if not existing.industry and item.get("industry"):
            existing.industry = _trunc(item.get("industry"), 250)
    return existing


def _build_discovery_result(
    *,
    job_id: str,
    item: Dict,
    domain: str,
    company_name: str,
    website: Optional[str],
    email: Optional[str],
    contact_name: Optional[str],
    title: Optional[str],
    source_provider: Optional[str],
    source_url: Optional[str],
    verification_status: str,
    is_demo: bool,
    result_status: str,
    raw_json: str,
    lead_id: Optional[str] = None,
    company_id: Optional[str] = None,
    duplicate_reason: Optional[str] = None,
) -> DiscoveryResult:
    return DiscoveryResult(
        discovery_job_id=job_id,
        lead_id=lead_id,
        company_id=company_id,
        company_name=_trunc(company_name, 250),
        domain=_trunc(domain, 250),
        website=website,
        business_category=_trunc(item.get("business_category"), 250),
        industry=_trunc(item.get("industry"), 250),
        country=_trunc(item.get("country"), 250),
        city=_trunc(item.get("city"), 250),
        region=_trunc(item.get("region"), 250),
        email=_trunc(email, 250) if email else None,
        phone=_trunc(item.get("company_phone"), 250),
        contact_name=_trunc(contact_name, 250),
        title=_trunc(title, 250),
        description=item.get("company_description"),
        source_provider=_trunc(source_provider, 250),
        source_url=source_url,
        verification_status=_trunc(verification_status, 48) or "unverified",
        is_demo=is_demo,
        result_status=_trunc(result_status, 48) or "new",
        duplicate_reason=duplicate_reason,
        raw_data=raw_json,
    )


@router.post("/jobs", response_model=DiscoveryJobResponse)
def create_discovery_job(
    job_in: DiscoveryJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_name = (job_in.job_name or "").strip()
    if not effective_name:
        prefix = "[DEMO] " if (job_in.source or "").lower() == "demo" else ""
        effective_name = f"{prefix}{job_in.query.strip()} Search" if job_in.query else "Business Leads Search"

    industry = job_in.industry or (job_in.filters or {}).get("industry")
    country = job_in.country or (job_in.filters or {}).get("country")
    filters_dict = job_in.filters or {}
    if industry:
        filters_dict["industry"] = industry
    if country:
        filters_dict["country"] = country

    job = DiscoveryJob(
        job_name=_trunc(effective_name, 250) or "Business Leads Search",
        source=_trunc(job_in.source or "all", 48) or "all",
        query=_trunc(job_in.query, 250) or "",
        region=_trunc(job_in.region or "Global", 95),
        filters=json.dumps(filters_dict),
        max_results=job_in.max_results,
        schedule=_trunc(job_in.schedule, 48) or "once",
        status="running",
        data_mode="demo" if (job_in.source or "").lower() == "demo" else "live",
        last_run=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        exec_res = execute_universal_discovery(
            query=job_in.query,
            source=job_in.source or "all",
            region=job_in.region,
            industry=industry,
            country=country,
            max_results=job_in.max_results,
            force_refresh=job_in.force_refresh,
        )

        raw_leads = exec_res.records
        total_found = len(raw_leads)
        new_leads_count = 0
        duplicates_skipped = 0

        batch_seen_emails = set()
        batch_seen_domains = set()

        for item in raw_leads:
            norm_email = normalize_email(item.get("email") or "")
            raw_dom = item.get("company_domain") or (norm_email.split("@")[1] if "@" in norm_email else "") or item.get("company_website") or ""
            domain = normalize_domain(raw_dom)
            company_name = (item.get("company_name") or "").strip()
            website = item.get("company_website")
            contact_name = item.get("name")
            title = item.get("title")
            source_url = item.get("source_url") or website or "https://leadshark.io"
            is_demo_row = bool(item.get("is_demo")) or exec_res.data_mode == "demo"
            ver_status = item.get("verification_status") or ("demo_sample" if is_demo_row else "unverified")
            src_provider = "demo" if is_demo_row else (item.get("source_provider") or job_in.source)
            raw_json = json.dumps(item, default=str)

            # Demo pipeline maintains strict historical email requirement
            if is_demo_row:
                if not norm_email or "@" not in norm_email:
                    db.add(_build_discovery_result(
                        job_id=job.id, item=item, domain=domain, company_name=company_name,
                        website=website, email=None, contact_name=contact_name, title=title,
                        source_provider="demo", source_url=source_url, verification_status="demo_sample",
                        is_demo=True, result_status="rejected", raw_json=raw_json,
                        duplicate_reason="Invalid or missing email address",
                    ))
                    continue

                is_dup, reason, existing_lead = find_duplicate_lead(db, norm_email, domain, company_name)
                if is_dup or norm_email in batch_seen_emails:
                    duplicates_skipped += 1
                    db.add(_build_discovery_result(
                        job_id=job.id, item=item, domain=domain, company_name=company_name,
                        website=website, email=norm_email, contact_name=contact_name, title=title,
                        source_provider="demo", source_url=source_url, verification_status="demo_sample",
                        is_demo=True, result_status="duplicate", raw_json=raw_json,
                        lead_id=existing_lead.id if existing_lead else None,
                        company_id=existing_lead.company_id if existing_lead else None,
                        duplicate_reason=reason or "Duplicate email in batch",
                    ))
                    continue

                batch_seen_emails.add(norm_email)
                company = _persist_company(db, item, domain)
                lead = Lead(
                    company_id=company.id if company else None,
                    name=_trunc(contact_name, 250),
                    title=_trunc(title, 250),
                    email=_trunc(norm_email, 250) or norm_email,
                    region=_trunc(item.get("region", "North America"), 250),
                    industry=_trunc(item.get("industry"), 250),
                    sector=_trunc(item.get("industry"), 250),
                    source_type="demo",
                    source_url=source_url,
                    collected_at=datetime.utcnow(),
                    lawful_basis_note=item.get("lawful_basis_note", "Synthetic Demo Sample"),
                    status="new",
                    email_status="unknown",
                )
                db.add(lead)
                db.flush()
                new_leads_count += 1
                db.add(_build_discovery_result(
                    job_id=job.id, item=item, domain=domain, company_name=company_name,
                    website=website, email=norm_email, contact_name=contact_name, title=title,
                    source_provider="demo", source_url=source_url, verification_status="demo_sample",
                    is_demo=True, result_status="new", raw_json=raw_json,
                    lead_id=lead.id, company_id=company.id if company else None,
                ))
                continue

            # LIVE UNIVERSAL SEARCH PATH — persist real discovered companies even when public email is not exposed
            if norm_email and "@" in norm_email:
                is_dup, reason, existing_lead = find_duplicate_lead(db, norm_email, domain, company_name)
                if is_dup or norm_email in batch_seen_emails:
                    duplicates_skipped += 1
                    db.add(_build_discovery_result(
                        job_id=job.id, item=item, domain=domain, company_name=company_name,
                        website=website, email=norm_email, contact_name=contact_name, title=title,
                        source_provider=src_provider, source_url=source_url, verification_status=ver_status,
                        is_demo=False, result_status="duplicate", raw_json=raw_json,
                        lead_id=existing_lead.id if existing_lead else None,
                        company_id=existing_lead.company_id if existing_lead else None,
                        duplicate_reason=reason or "Duplicate email in batch",
                    ))
                    continue

                batch_seen_emails.add(norm_email)
                if domain:
                    batch_seen_domains.add(domain)
                company = _persist_company(db, item, domain)
                em_res = verify_email_address(norm_email)
                lead = Lead(
                    company_id=company.id if company else None,
                    name=_trunc(contact_name or company_name, 250),
                    title=_trunc(title or "Public Business Contact", 250),
                    email=_trunc(norm_email, 250) or norm_email,
                    region=_trunc(item.get("region") or "Global", 250),
                    industry=_trunc(item.get("industry"), 250),
                    sector=_trunc(item.get("industry"), 250),
                    source_type=_trunc(src_provider, 250),
                    source_url=source_url,
                    collected_at=datetime.utcnow(),
                    lawful_basis_note=item.get("lawful_basis_note", "Public Business Directory"),
                    status="verified" if em_res["status"] == "valid" else "new",
                    email_status=em_res["status"],
                    email_details=json.dumps(em_res),
                )
                db.add(lead)
                db.flush()
                new_leads_count += 1
                db.add(_build_discovery_result(
                    job_id=job.id, item=item, domain=domain, company_name=company_name,
                    website=website, email=norm_email, contact_name=contact_name, title=title,
                    source_provider=src_provider, source_url=source_url, verification_status=ver_status,
                    is_demo=False, result_status="new", raw_json=raw_json,
                    lead_id=lead.id, company_id=company.id if company else None,
                ))
            else:
                # Company record discovered without an exposed public email (never invent emails!)
                is_comp_dup, comp_reason, existing_comp = find_duplicate_company(db, domain, company_name)
                if is_comp_dup or (domain and domain in batch_seen_domains):
                    duplicates_skipped += 1
                    db.add(_build_discovery_result(
                        job_id=job.id, item=item, domain=domain, company_name=company_name,
                        website=website, email=None, contact_name=contact_name, title=title,
                        source_provider=src_provider, source_url=source_url, verification_status=ver_status,
                        is_demo=False, result_status="duplicate", raw_json=raw_json,
                        company_id=existing_comp.id if existing_comp else None,
                        duplicate_reason=comp_reason or f"Company domain '{domain}' duplicate in search batch",
                    ))
                    continue

                if domain:
                    batch_seen_domains.add(domain)
                company = _persist_company(db, item, domain)
                new_leads_count += 1
                db.add(_build_discovery_result(
                    job_id=job.id, item=item, domain=domain, company_name=company_name,
                    website=website, email=None, contact_name=contact_name, title=title,
                    source_provider=src_provider, source_url=source_url, verification_status=ver_status,
                    is_demo=False, result_status="new", raw_json=raw_json,
                    company_id=company.id if company else None,
                ))

        db.commit()

        job.status = "completed"
        job.total_found = total_found
        job.new_leads_count = new_leads_count
        job.duplicates_skipped = duplicates_skipped
        job.search_intent = _trunc(exec_res.parsed_query.intent, 48)
        job.data_mode = exec_res.data_mode
        job.sources_searched = json.dumps(exec_res.sources_searched)
        job.no_results_reason = exec_res.no_results_reason
        job.cached = exec_res.cached
        job.duration_ms = exec_res.duration_ms
        db.commit()
        db.refresh(job)

        log_audit(
            db,
            actor=current_user.email,
            action="discovery_job_completed",
            object_name=f"job:{job.id}",
            details={
                "query": job_in.query,
                "mode": exec_res.data_mode,
                "intent": exec_res.parsed_query.intent,
                "found": total_found,
                "new": new_leads_count,
                "duplicates": duplicates_skipped,
                "cached": exec_res.cached,
            },
        )

    except Exception as e:
        db.rollback()
        failed_job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job.id).first()
        if failed_job:
            failed_job.status = "failed"
            failed_job.error_message = str(e)
            db.commit()
            db.refresh(failed_job)
            return failed_job
        raise HTTPException(status_code=500, detail=f"Discovery search error: {e}")

    return job


@router.get("/jobs", response_model=List[DiscoveryJobResponse])
def list_discovery_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/jobs/{id}", response_model=DiscoveryJobResponse)
def get_discovery_job(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")
    return job


@router.get("/jobs/{id}/results", response_model=List[DiscoveryResultResponse])
def get_discovery_job_results(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    industry: Optional[str] = None,
    country: Optional[str] = None,
    region: Optional[str] = None,
    verification_status: Optional[str] = None,
    result_status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
):
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")

    q = db.query(DiscoveryResult).filter(DiscoveryResult.discovery_job_id == id)
    if industry and industry != "All":
        q = q.filter(DiscoveryResult.industry == industry)
    if country and country != "All":
        q = q.filter(DiscoveryResult.country == country)
    if region and region != "All":
        q = q.filter(DiscoveryResult.region == region)
    if verification_status and verification_status != "All":
        q = q.filter(DiscoveryResult.verification_status == verification_status)
    if result_status and result_status != "all":
        q = q.filter(DiscoveryResult.result_status == result_status)
    if search and search.strip():
        pat = f"%{search.strip()}%"
        q = q.filter(
            (DiscoveryResult.company_name.ilike(pat))
            | (DiscoveryResult.domain.ilike(pat))
            | (DiscoveryResult.city.ilike(pat))
            | (DiscoveryResult.country.ilike(pat))
            | (DiscoveryResult.email.ilike(pat))
        )

    return q.order_by(DiscoveryResult.created_at.asc()).offset(skip).limit(limit).all()


@router.get("/jobs/{id}/results/page", response_model=DiscoveryResultsPageResponse)
def get_discovery_job_results_paginated(
    id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    industry: Optional[str] = None,
    country: Optional[str] = None,
    region: Optional[str] = None,
    verification_status: Optional[str] = None,
    result_status: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")

    all_rows = db.query(DiscoveryResult).filter(DiscoveryResult.discovery_job_id == id).all()
    facets = {
        "industries": sorted({r.industry for r in all_rows if r.industry}),
        "countries": sorted({r.country for r in all_rows if r.country}),
        "regions": sorted({r.region for r in all_rows if r.region}),
        "verification_statuses": sorted({r.verification_status for r in all_rows if r.verification_status}),
        "providers": sorted({r.source_provider for r in all_rows if r.source_provider}),
        "result_statuses": sorted({r.result_status for r in all_rows if r.result_status}),
    }

    q = db.query(DiscoveryResult).filter(DiscoveryResult.discovery_job_id == id)
    if industry and industry != "All":
        q = q.filter(DiscoveryResult.industry == industry)
    if country and country != "All":
        q = q.filter(DiscoveryResult.country == country)
    if region and region != "All":
        q = q.filter(DiscoveryResult.region == region)
    if verification_status and verification_status != "All":
        q = q.filter(DiscoveryResult.verification_status == verification_status)
    if result_status and result_status != "all":
        q = q.filter(DiscoveryResult.result_status == result_status)
    if provider and provider != "All":
        q = q.filter(DiscoveryResult.source_provider.ilike(f"%{provider}%"))
    if search and search.strip():
        pat = f"%{search.strip()}%"
        q = q.filter(
            (DiscoveryResult.company_name.ilike(pat))
            | (DiscoveryResult.domain.ilike(pat))
            | (DiscoveryResult.city.ilike(pat))
            | (DiscoveryResult.country.ilike(pat))
            | (DiscoveryResult.email.ilike(pat))
        )

    total = q.count()
    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size
    items = q.order_by(DiscoveryResult.created_at.asc()).offset(offset).limit(page_size).all()

    return DiscoveryResultsPageResponse(
        job=job,
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        facets=facets,
    )
