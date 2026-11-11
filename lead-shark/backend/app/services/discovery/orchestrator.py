import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.deduplication.dedup import normalize_domain, normalize_name
from app.services.discovery.adapters import (
    AdapterOutcome,
    BaseSourceAdapter,
    CompanyDirectoryAdapter,
    ExternalSearchAPIAdapter,
    GooglePlacesAdapter,
    OpenStreetMapAdapter,
    WebsiteEnrichmentAdapter,
    WikidataKnowledgeAdapter,
)
from app.services.discovery.query_parser import ParsedQuery, infer_region_and_country, parse_universal_query
from app.services.discovery.resilience import get_discovery_cache
from app.services.verification.verifier import check_mx_records, verify_email_address


@dataclass
class DiscoveryExecutionResult:
    query: str
    parsed_query: ParsedQuery
    data_mode: str  # "live" | "demo"
    records: List[Dict[str, Any]]
    sources_searched: List[Dict[str, Any]]
    total_raw_found: int
    cross_provider_merged: int
    no_results_reason: Optional[str] = None
    cached: bool = False
    duration_ms: int = 0


LIVE_ADAPTER_REGISTRY: Dict[str, BaseSourceAdapter] = {
    "wikidata": WikidataKnowledgeAdapter(),
    "openstreetmap": OpenStreetMapAdapter(),
    "osm": OpenStreetMapAdapter(),
    "company_directory": CompanyDirectoryAdapter(),
    "external_search": ExternalSearchAPIAdapter(),
    "google_places": GooglePlacesAdapter(),
    "website": WebsiteEnrichmentAdapter(),
}


def _deduplicate_across_providers(raw_records: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    """
    Deduplicates and merges complementary fields across multiple providers
    using canonical domain + normalized company name + optional city.
    """
    merged: List[Dict[str, Any]] = []
    index_by_key: Dict[str, int] = {}
    merged_count = 0

    for rec in raw_records:
        dom = normalize_domain(rec.get("company_domain") or rec.get("company_website") or "")
        cname_norm = normalize_name(rec.get("company_name") or "")
        city_norm = normalize_name(rec.get("city") or "")

        # Primary key: domain if present and not an empty generic string; else name+city
        dedup_key = f"dom:{dom}" if dom and "." in dom else f"name:{cname_norm}:{city_norm}"
        alt_name_key = f"name_only:{cname_norm}" if cname_norm else None

        existing_idx = index_by_key.get(dedup_key)
        if existing_idx is None and alt_name_key and not dom:
            existing_idx = index_by_key.get(alt_name_key)

        if existing_idx is not None:
            merged_count += 1
            target = merged[existing_idx]
            # Merge complementary missing fields cleanly (never overwrite valid fields with None)
            for fld in ("company_website", "company_domain", "email", "company_phone", "country", "city"):
                if not target.get(fld) and rec.get(fld):
                    target[fld] = rec[fld]

            # Upgrade generic placeholder fields when another provider provides richer structured classification
            if target.get("business_category") in (None, "Verified Corporate Domain", "Business Enterprise") and rec.get("business_category") not in (None, "Verified Corporate Domain", "Business Enterprise"):
                target["business_category"] = rec["business_category"]
            if target.get("industry") in (None, "Commercial Enterprise", "Commercial Business") and rec.get("industry") not in (None, "Commercial Enterprise", "Commercial Business"):
                target["industry"] = rec["industry"]
            if target.get("region") in (None, "Global") and rec.get("region") not in (None, "Global"):
                target["region"] = rec["region"]
            if (not target.get("company_description") or "Official business domain resolved via" in target.get("company_description", "")) and rec.get("company_description"):
                target["company_description"] = rec["company_description"]
            if rec.get("raw_industry") and not target.get("raw_industry"):
                target["raw_industry"] = rec["raw_industry"]

            # Prefer canonical Wikidata attribution URL if target was a bare domain
            if target.get("source_provider") == "company_directory" and "wikidata.org" in (rec.get("source_url") or ""):
                target["source_url"] = rec["source_url"]

            # Preserve attribution from secondary provider
            p1 = target.get("source_provider") or ""
            p2 = rec.get("source_provider") or ""
            if p2 and p2 not in p1:
                target["source_provider"] = f"{p1}, {p2}" if p1 else p2
            continue

        idx = len(merged)
        merged.append(rec)
        index_by_key[dedup_key] = idx
        if alt_name_key and alt_name_key not in index_by_key:
            index_by_key[alt_name_key] = idx

    return merged, merged_count


def _score_relevance(rec: Dict[str, Any], parsed: ParsedQuery) -> int:
    """Computes relevance score to order multi-provider results cleanly."""
    score = 0
    cname = (rec.get("company_name") or "").lower()
    dom = (rec.get("company_domain") or "").lower()
    desc = (rec.get("company_description") or "").lower()
    raw_ind = (rec.get("raw_industry") or "").lower()
    std_ind = (rec.get("industry") or "").lower()
    cat = (rec.get("business_category") or "").lower()
    city = (rec.get("city") or "").lower()
    country = (rec.get("country") or "").lower()

    full_text = f"{cname} {dom} {desc} {raw_ind} {std_ind} {cat}"
    topic_low = parsed.cleaned_topic.lower()

    if parsed.intent in ("specific_company", "domain_url"):
        if cname == topic_low or cname.startswith(f"{topic_low} "):
            score += 50
        elif topic_low in cname:
            score += 30
        if topic_low in dom:
            score += 25
    else:
        # Category search
        for kw in parsed.expanded_keywords:
            if kw.lower() in full_text:
                score += 18
        if parsed.inferred_industry and parsed.inferred_industry.lower() in std_ind:
            score += 15

    # Location match bonus
    if parsed.location_aliases:
        geo_haystack = f"{city} {country} {desc}"
        if any(a.lower() in geo_haystack for a in parsed.location_aliases):
            score += 20

    # Completeness & primary domain preference
    if rec.get("company_website"):
        score += 10
    if dom == f"{topic_low}.com":
        score += 12
    elif dom.endswith(".com"):
        score += 3
    if rec.get("email"):
        score += 8
    if rec.get("company_phone"):
        score += 4
    if rec.get("city") or rec.get("country"):
        score += 3

    return score


def _matches_topic_or_filter(
    rec: Dict[str, Any],
    parsed: ParsedQuery,
    region_filter: Optional[str],
    industry_filter: Optional[str],
    country_filter: Optional[str],
) -> bool:
    # 1. Explicit country filter if provided
    if country_filter and country_filter not in ("All", "Global"):
        c_val = (rec.get("country") or "").lower()
        if c_val and country_filter.lower() not in c_val:
            return False

    # 2. Explicit region filter (only enforce if entity has a known non-Global region and differs)
    if region_filter and region_filter not in ("All", "All Regions", "Global"):
        rec_reg = rec.get("region") or "Global"
        rec_ctry = rec.get("country") or ""
        inferred_reg, _ = infer_region_and_country(rec_ctry)
        effective_reg = rec_reg if rec_reg != "Global" else (inferred_reg or "Global")
        if effective_reg != "Global" and effective_reg.lower() != region_filter.lower():
            return False

    # 3. Topic coherence check for category searches with strong industry focus
    if parsed.intent in ("category_location", "category_global"):
        topic_low = parsed.cleaned_topic.lower()
        full_text = f"{rec.get('company_name', '')} {rec.get('raw_industry', '')} {rec.get('industry', '')} {rec.get('business_category', '')} {rec.get('company_description', '')}".lower()

        if any(k in topic_low for k in ["it", "software", "cloud", "tech", "ai", "cyber", "startup"]):
            # Exclude obvious off-sector results (media, newspapers, pharma, transport) unless explicitly IT/tech
            if any(bad in full_text for bad in ["pharmaceutical", "biotechnology", "hospital", "space industry", "rail transport", "newspaper", "television", "broadcast", "magazine", "cinema"]):
                if not any(good in full_text for good in ["software", "information technology", "it service", "cloud", "computing", "computer", "saas", "fintech", "e-commerce"]):
                    return False
            # Also exclude bare entities that lack any tech/startup/business indicator when topic is narrow ("IT" / "cloud")
            if topic_low in ("it", "cloud", "cloud computing") and not any(good in full_text for good in ["software", "information technology", "it ", "cloud", "tech", "computing", "computer", "digital", "consulting", "saas", "data"]):
                return False

        if any(k in topic_low for k in ["manufactur", "industrial", "factory"]):
            if any(bad in full_text for bad in ["newspaper", "television", "university", "bank"]):
                return False

        if any(k in topic_low for k in ["health", "hospital", "pharma", "biotech", "medical"]):
            if not any(good in full_text for good in ["health", "hospital", "medical", "pharma", "biotech", "clinic", "care"]):
                return False

    return True


def _verify_record_integrity(rec: Dict[str, Any]) -> None:
    """Assigns deterministic, truthful verification_status based on email DNS/MX or domain MX resolution."""
    if rec.get("is_demo"):
        rec["verification_status"] = "demo_sample"
        return

    email = rec.get("email")
    if email:
        res = verify_email_address(email)
        if res["status"] == "valid":
            rec["verification_status"] = "verified_email"
        elif res["status"] == "risky":
            rec["verification_status"] = "risky_email"
        else:
            rec["verification_status"] = "invalid_email"
        return

    domain = rec.get("company_domain")
    if domain and "." in domain:
        mx_ok, _ = check_mx_records(domain)
        rec["verification_status"] = "verified_domain" if mx_ok else "unverified"
        return

    rec["verification_status"] = "unverified"


def execute_universal_discovery(
    *,
    query: str,
    source: str = "all",
    region: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    max_results: int = 25,
    force_refresh: bool = False,
) -> DiscoveryExecutionResult:
    """
    Universal dynamic search orchestrator:
    - Strictly isolates DEMO vs LIVE data
    - Runs multi-provider live adapters concurrently
    - Deduplicates & merges records across providers
    - Enriches public contacts safely via robots.txt
    - Caches live results briefly to guard against rate limits
    """
    t0 = time.monotonic()
    src_norm = (source or "all").strip().lower()
    parsed = parse_universal_query(query, region=region, industry=industry, country=country)

    # 1. Explicit Demo path — strictly separated from live records
    if src_norm == "demo":
        from app.services.discovery.connectors import DemoDiscoveryConnector

        demo_conn = DemoDiscoveryConnector()
        demo_records = demo_conn.search(query=query, region=region, max_results=max_results, industry=industry)
        for rec in demo_records:
            rec["is_demo"] = True
            rec["source_provider"] = "demo"
            rec["verification_status"] = "demo_sample"
            if not rec.get("business_category"):
                rec["business_category"] = "Demo Sample Record"

        duration_ms = int((time.monotonic() - t0) * 1000)
        return DiscoveryExecutionResult(
            query=query,
            parsed_query=parsed,
            data_mode="demo",
            records=demo_records[:max_results],
            sources_searched=[{
                "source_id": "demo",
                "source_label": "Demo Sample Dataset (Synthetic Testing Data)",
                "status": "ok" if demo_records else "empty",
                "count": len(demo_records),
                "latency_ms": duration_ms,
                "message": "Synthetic demonstration records loaded by explicit selection.",
            }],
            total_raw_found=len(demo_records),
            cross_provider_merged=0,
            no_results_reason=None if demo_records else "No synthetic sample records matched the demo filters.",
            cached=False,
            duration_ms=duration_ms,
        )

    # 2. Live Discovery Path (NEVER invokes DemoDiscoveryConnector)
    cache = get_discovery_cache()
    cache_key = f"live|{src_norm}|{query.strip().lower()}|{(region or 'Global').lower()}|{(industry or 'All').lower()}|{(country or '').lower()}|{max_results}"
    if not force_refresh:
        cached_result: Optional[DiscoveryExecutionResult] = cache.get(cache_key)
        if cached_result is not None:
            return DiscoveryExecutionResult(
                query=cached_result.query,
                parsed_query=cached_result.parsed_query,
                data_mode="live",
                records=[dict(r) for r in cached_result.records],
                sources_searched=cached_result.sources_searched,
                total_raw_found=cached_result.total_raw_found,
                cross_provider_merged=cached_result.cross_provider_merged,
                no_results_reason=cached_result.no_results_reason,
                cached=True,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

    if src_norm in ("all", "auto", "universal"):
        adapter_keys = ["wikidata", "openstreetmap", "company_directory", "external_search"]
    elif src_norm in LIVE_ADAPTER_REGISTRY:
        adapter_keys = [src_norm]
    else:
        adapter_keys = ["wikidata", "openstreetmap", "external_search"]

    outcomes: List[AdapterOutcome] = []
    raw_records: List[Dict[str, Any]] = []

    pool = ThreadPoolExecutor(max_workers=len(adapter_keys))
    try:
        future_map = {
            pool.submit(LIVE_ADAPTER_REGISTRY[k].search, parsed, max_results): k
            for k in adapter_keys
        }
        try:
            for fut in as_completed(future_map, timeout=16.0):
                key = future_map[fut]
                try:
                    outcome = fut.result(timeout=1.0)
                    outcomes.append(outcome)
                    raw_records.extend(outcome.records)
                except Exception as exc:
                    outcomes.append(
                        AdapterOutcome(
                            source_id=key,
                            source_label=LIVE_ADAPTER_REGISTRY[key].source_label,
                            status="error",
                            records=[],
                            latency_ms=0,
                            message=f"Adapter execution error: {exc}",
                        )
                    )
        except Exception:
            # Handle TimeoutError from as_completed cleanly without dropping completed adapter results
            done_keys = {o.source_id for o in outcomes}
            for fut, key in future_map.items():
                if key not in done_keys:
                    outcomes.append(
                        AdapterOutcome(
                            source_id=key,
                            source_label=LIVE_ADAPTER_REGISTRY[key].source_label,
                            status="timeout",
                            records=[],
                            latency_ms=16000,
                            message="Provider timed out after 16s budget",
                        )
                    )
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    total_raw_found = len(raw_records)

    # Deduplicate across live providers and merge complementary attributes
    deduped_records, cross_merged = _deduplicate_across_providers(raw_records)

    # Filter & rank by relevance
    filtered_records = [
        rec for rec in deduped_records
        if _matches_topic_or_filter(rec, parsed, region, industry, country)
    ]

    # Sort descending by relevance score
    filtered_records.sort(key=lambda r: _score_relevance(r, parsed), reverse=True)
    final_records = filtered_records[:max_results]

    # Public website contact enrichment (robots.txt strict) for top found companies lacking public email/phone
    if final_records and src_norm != "website":
        try:
            enricher = WebsiteEnrichmentAdapter()
            enricher.enrich_batch(final_records, max_sites=4)
        except Exception:
            pass

    # Assign honest DNS/MX/email verification statuses
    for rec in final_records:
        rec["is_demo"] = False
        _verify_record_integrity(rec)

    sources_summary = [o.to_summary() for o in outcomes]
    no_results_reason = None
    if not final_records:
        reasons = []
        for o in outcomes:
            if o.status == "rate_limited":
                reasons.append(f"{o.source_label}: rate-limited ({o.message})")
            elif o.status == "timeout":
                reasons.append(f"{o.source_label}: request timed out")
            elif o.status == "not_configured":
                reasons.append(f"{o.source_label}: optional API keys not set")
            elif o.status == "error":
                reasons.append(f"{o.source_label}: {o.message}")
            elif o.status == "empty":
                reasons.append(f"{o.source_label}: 0 matching live entities")
        if total_raw_found > 0 and not filtered_records:
            no_results_reason = (
                f"External sources returned {total_raw_found} candidate records, but none matched your active "
                f"Region/Country/Industry filters. Try setting Region to 'Global' and Industry to 'All', or load Demo Data for testing."
            )
        else:
            no_results_reason = (
                f"No live public records matched '{query}'. "
                + ("Details: " + "; ".join(reasons) + ". " if reasons else "")
                + "Try a broader industry/location query, verify network connectivity to Wikidata/OSM, or use 'Load Demo Data' for presentation testing."
            )

    result = DiscoveryExecutionResult(
        query=query,
        parsed_query=parsed,
        data_mode="live",
        records=final_records,
        sources_searched=sources_summary,
        total_raw_found=total_raw_found,
        cross_provider_merged=cross_merged,
        no_results_reason=no_results_reason,
        cached=False,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )

    # Cache live responses cleanly for subsequent pagination/re-queries
    cache.set(cache_key, result, ttl_seconds=settings.DISCOVERY_CACHE_TTL_SECONDS)
    return result
