import re
import time
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from app.core.config import settings
from app.services.deduplication.dedup import normalize_domain
from app.services.discovery.query_parser import (
    ParsedQuery,
    infer_region_and_country,
    infer_standard_sector,
)
from app.services.discovery.resilience import request_with_retry


ALLOWED_SCRAPE_SCHEMES = ("http://", "https://")
BLOCKED_EMAIL_FRAGMENTS = (
    "example.com", "example.org", "sentry", "wixpress", "wix.com",
    "noreply", "no-reply", "donotreply", "mailer-daemon", "schema.org",
    "w3.org", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js",
)
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,10}")
TEL_PATTERN = re.compile(r'href=["\']tel:([+\d\s\-().]{7,20})["\']', re.IGNORECASE)
MAILTO_PATTERN = re.compile(r'href=["\']mailto:([^"\'?]+)', re.IGNORECASE)
META_DESC_PATTERN = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{15,400})["\']',
    re.IGNORECASE,
)

# Standard Wikidata Q-IDs for valid business/commercial types (class IDs, NOT companies)
VALID_BUSINESS_P31_QIDS = {
    "Q4830453",   # business
    "Q783794",    # company
    "Q891723",    # public company
    "Q6881511",   # enterprise
    "Q16917",     # hospital
    "Q167037",    # corporation
    "Q46970",     # airline
    "Q22687",     # bank
    "Q507619",    # pharmacy / retail
    "Q134161",    # joint venture
    "Q1589009",   # privately held company
    "Q166280",    # conglomerate
    "Q658255",    # subsidiary
    "Q2073580",   # technology company
    "Q1058914",   # software company
    "Q19644607",  # pharmaceutical company
    "Q10912826",  # manufacturing / enterprise
    "Q18388277",  # startup company
    "Q15850590",  # holding company
}

# Wikidata P31 classes that are explicitly NOT B2B target companies
NON_COMPANY_P31_QIDS = {
    "Q515", "Q3957", "Q5119", "Q6256", "Q35657", "Q82794",  # city, town, country, state, region
    "Q1549591", "Q174844", "Q200250", "Q15127012",          # big city, megacity, metropolis, state capital
    "Q1149652", "Q486972", "Q270791", "Q208511",            # Indian district, human settlement, municipality
    "Q4167410", "Q13406463", "Q11266439", "Q4167836",       # disambiguation, Wikimedia list/template/category
    "Q7889", "Q11424", "Q5398426", "Q7725634", "Q482994",   # video game, film, tv, literary work, album
    "Q11032", "Q15265344", "Q1616075", "Q14350",            # newspaper, broadcaster, television station, radio
    "Q4022", "Q23442", "Q8502",                             # river, island, mountain
    "Q618779", "Q11446", "Q5", "Q3918",                     # award, ship, human, university
}

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
]


def check_robots_txt(target_url: str, user_agent: str = "LeadSharkBot/1.0 (+https://leadshark.io)") -> bool:
    """Checks robots.txt before fetching a site. Strictly respects disallow directives."""
    rp = _fetch_robots_parser(target_url)
    if rp is None:
        return True
    return rp.can_fetch(user_agent, target_url)


def _fetch_robots_parser(target_url: str) -> Optional[urllib.robotparser.RobotFileParser]:
    try:
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            return None
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        res = request_with_retry("robots", "GET", robots_url, timeout=2.0, max_retries=0, expect_json=False)
        if not res.ok:
            return None
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(res.text.splitlines())
        return rp
    except Exception:
        return None


def _clean_website_url(raw_url: Optional[str]) -> Optional[str]:
    if not raw_url:
        return None
    u = raw_url.strip()
    if not u:
        return None
    if not u.startswith(ALLOWED_SCRAPE_SCHEMES):
        u = f"https://{u}"
    dom = normalize_domain(u)
    if not dom or "." not in dom:
        return None
    return u


def _make_record(
    *,
    company_name: str,
    website: Optional[str] = None,
    domain: Optional[str] = None,
    business_category: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    region: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    contact_name: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    source_provider: str,
    source_url: str,
    verification_status: str = "unverified",
    is_demo: bool = False,
    lawful_basis_note: str = "Public Business Registry / Open Directory",
) -> Dict[str, Any]:
    clean_web = _clean_website_url(website)
    clean_dom = normalize_domain(domain or clean_web or "")
    inferred_reg = region
    if not inferred_reg or inferred_reg == "Global":
        r_city, c_city = infer_region_and_country(city)
        r_ctry, c_ctry = infer_region_and_country(country)
        inferred_reg = r_city or r_ctry or region or "Global"
        if not country:
            country = c_city or c_ctry

    std_sector = infer_standard_sector(industry or business_category or description or company_name)
    display_industry = std_sector or (industry.title() if industry else "Commercial Business")

    clean_email = email.strip().lower() if email and "@" in email else None
    if clean_email and clean_email.startswith("mailto:"):
        clean_email = clean_email.replace("mailto:", "", 1).strip()

    return {
        "company_name": company_name.strip(),
        "company_website": clean_web,
        "company_domain": clean_dom,
        "business_category": business_category or (industry.title() if industry else "Business Enterprise"),
        "industry": display_industry,
        "raw_industry": industry,
        "country": country,
        "city": city,
        "region": inferred_reg,
        "email": clean_email,
        "company_phone": phone.strip() if phone else None,
        "name": contact_name,
        "title": title,
        "company_description": description,
        "source_provider": source_provider,
        "source_type": source_provider,
        "source_url": source_url,
        "verification_status": verification_status,
        "is_demo": is_demo,
        "lawful_basis_note": lawful_basis_note,
        "collected_at": datetime.utcnow(),
    }


@dataclass
class AdapterOutcome:
    source_id: str
    source_label: str
    status: str  # ok | empty | timeout | rate_limited | not_configured | error
    records: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0
    message: Optional[str] = None

    def to_summary(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_label": self.source_label,
            "status": self.status,
            "count": len(self.records),
            "latency_ms": self.latency_ms,
            "message": self.message,
        }


class BaseSourceAdapter:
    source_id: str = "base"
    source_label: str = "Base Source"

    def search(self, parsed: ParsedQuery, max_results: int = 25) -> AdapterOutcome:
        raise NotImplementedError


# ==============================================================================
# 1. WIKIDATA & WIKIPEDIA DYNAMIC KNOWLEDGE GRAPH ADAPTER
# ==============================================================================
class WikidataKnowledgeAdapter(BaseSourceAdapter):
    """
    Dynamically discovers businesses/companies globally via Wikidata & Wikipedia APIs.
    Supports both named entity lookups ('Amazon', 'Wipro', 'Infosys') and
    category/location discovery ('IT companies in Hyderabad', 'Manufacturing companies in India').
    Zero hardcoded company lists.
    """
    source_id = "wikidata"
    source_label = "Wikidata & Wikipedia Business Graph"

    def _search_wikidata_cirrus(self, search_expr: str, limit: int = 12) -> List[str]:
        res = request_with_retry(
            "wikidata_api",
            "GET",
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": search_expr,
                "srlimit": limit,
                "format": "json",
            },
            timeout=settings.DISCOVERY_HTTP_TIMEOUT,
            max_retries=1,
        )
        if not res.ok or not res.data:
            return []
        return [x["title"] for x in res.data.get("query", {}).get("search", []) if x.get("title", "").startswith("Q")]

    def _search_wb_entities(self, term: str, limit: int = 8) -> List[str]:
        res = request_with_retry(
            "wikidata_api",
            "GET",
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": term,
                "language": "en",
                "limit": limit,
                "format": "json",
            },
            timeout=settings.DISCOVERY_HTTP_TIMEOUT,
            max_retries=1,
        )
        if not res.ok or not res.data:
            return []
        return [x["id"] for x in res.data.get("search", []) if x.get("id")]

    def _discover_qids_via_wikipedia(self, parsed: ParsedQuery, max_titles: int = 35) -> List[str]:
        search_queries = [parsed.raw_query]
        topic = parsed.cleaned_topic
        loc = parsed.location

        if parsed.intent == "category_location" and loc:
            loc_primary = parsed.location_aliases[0] if parsed.location_aliases else loc
            if any(k in topic.lower() for k in ["health", "hospital", "pharma"]):
                search_queries.extend([f"hospitals in {loc_primary}", f"pharmaceutical companies {loc_primary}"])
            elif any(k in topic.lower() for k in ["startup", "startups"]):
                search_queries.extend([f"companies based in {loc_primary}", f"software companies in {loc_primary}"])
            elif any(k in topic.lower() for k in ["it", "software", "tech"]):
                if parsed.location_aliases and len(parsed.location_aliases) > 1:
                    search_queries.append(f"Software industry in {parsed.location_aliases[1]}")
                search_queries.extend([f"software companies in {loc_primary}", f"companies based in {loc_primary}"])
            elif "manufactur" in topic.lower():
                search_queries.extend([f"manufacturing companies {loc_primary}", f"companies of {loc_primary}"])
            else:
                search_queries.extend([f"{topic} companies {loc_primary}", f"companies based in {loc_primary}"])
        elif parsed.intent == "category_global":
            search_queries = [f"{topic} companies", parsed.raw_query]

        titles: List[str] = []
        list_pages: List[str] = []

        # Run top 2 Wikipedia searches cleanly without slow retries
        for sq in search_queries[:2]:
            res = request_with_retry(
                "wikipedia_api",
                "GET",
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": sq, "srlimit": 10, "format": "json"},
                timeout=5.0,
                max_retries=0,
            )
            if res.ok and res.data:
                for hit in res.data.get("query", {}).get("search", []):
                    t = hit.get("title", "")
                    if not t:
                        continue
                    t_low = t.lower()
                    if t_low.startswith("list of") or "industry in" in t_low or "economy of" in t_low:
                        if t not in list_pages:
                            list_pages.append(t)
                    elif t not in titles:
                        titles.append(t)

        # Expand internal links on discovered "List of companies..." / overview pages
        if list_pages:
            res_links = request_with_retry(
                "wikipedia_api",
                "GET",
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": "|".join(list_pages[:2]),
                    "prop": "links",
                    "pllimit": 120,
                    "plnamespace": 0,
                    "format": "json",
                },
                timeout=settings.DISCOVERY_HTTP_TIMEOUT,
                max_retries=1,
            )
            if res_links.ok and res_links.data:
                pages = res_links.data.get("query", {}).get("pages", {})
                for _, pdata in pages.items():
                    for lk in pdata.get("links", []):
                        lt = lk.get("title", "")
                        if lt and lt not in titles and not lt.lower().startswith("list of"):
                            titles.append(lt)

        if not titles:
            return []

        # Batch resolve Wikipedia titles -> Wikidata QIDs
        unique_titles = titles[:max_titles]
        res_qids = request_with_retry(
            "wikipedia_api",
            "GET",
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "titles": "|".join(unique_titles),
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "redirects": 1,
                "format": "json",
            },
            timeout=settings.DISCOVERY_HTTP_TIMEOUT,
            max_retries=1,
        )
        qids: List[str] = []
        if res_qids.ok and res_qids.data:
            pages = res_qids.data.get("query", {}).get("pages", {})
            for _, pdata in pages.items():
                qid = pdata.get("pageprops", {}).get("wikibase_item")
                if qid and qid not in qids:
                    qids.append(qid)
        return qids

    def _extract_claim_values(self, claims: Dict[str, Any], prop: str) -> List[str]:
        vals: List[str] = []
        for stmt in claims.get(prop, []):
            mainsnak = stmt.get("mainsnak", {})
            dv = mainsnak.get("datavalue", {})
            vtype = dv.get("type")
            val = dv.get("value")
            if vtype == "string" and isinstance(val, str):
                vals.append(val)
            elif vtype == "wikibase-entityid" and isinstance(val, dict):
                qid = val.get("id")
                if qid:
                    vals.append(qid)
        return vals

    def _hydrate_qids_rest(self, qids: List[str]) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Optional[str]]:
        if not qids:
            return {}, None

        batch_qids = qids[:45]
        res = request_with_retry(
            "wikidata_api",
            "GET",
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbgetentities",
                "ids": "|".join(batch_qids),
                "props": "labels|descriptions|claims",
                "languages": "en",
                "format": "json",
            },
            timeout=8.0,
            max_retries=1,
        )
        if not res.ok or not res.data:
            return None, res.error

        entities = res.data.get("entities", {})
        grouped: Dict[str, Dict[str, Any]] = {}
        ref_qids_to_resolve = set()

        for qid, ent in entities.items():
            if ent.get("missing"):
                continue
            claims = ent.get("claims", {})
            p31s = set(self._extract_claim_values(claims, "P31"))
            if p31s & NON_COMPANY_P31_QIDS:
                continue

            websites = self._extract_claim_values(claims, "P856")
            industries = self._extract_claim_values(claims, "P452")
            label = ent.get("labels", {}).get("en", {}).get("value", "")
            desc = ent.get("descriptions", {}).get("en", {}).get("value", "")

            is_biz_type = bool(p31s & VALID_BUSINESS_P31_QIDS) or bool(industries)
            if not is_biz_type or not label or not websites:
                continue
            website = websites[0]
            dom_chk = normalize_domain(website)
            if not dom_chk or dom_chk.endswith(".gov") or ".gov." in dom_chk or dom_chk.endswith(".nic.in") or dom_chk.endswith(".edu"):
                continue

            emails = self._extract_claim_values(claims, "P968")
            phones = self._extract_claim_values(claims, "P1329")
            hqs = self._extract_claim_values(claims, "P159")
            countries = self._extract_claim_values(claims, "P17")

            for rq in industries[:2] + hqs[:1] + countries[:1]:
                if rq.startswith("Q"):
                    ref_qids_to_resolve.add(rq)

            grouped[qid] = {
                "qid": qid,
                "label": label,
                "description": desc,
                "website": website,
                "email": emails[0] if emails else None,
                "phone": phones[0] if phones else None,
                "industry_qids": industries[:3],
                "city_qid": hqs[0] if hqs else None,
                "country_qid": countries[0] if countries else None,
                "p31s": p31s,
            }

        # Batch resolve industry/city/country QIDs into English labels (1 single fast REST call)
        label_map: Dict[str, str] = {}
        ref_list = list(ref_qids_to_resolve)[:50]
        if ref_list:
            res_ref = request_with_retry(
                "wikidata_api",
                "GET",
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(ref_list),
                    "props": "labels",
                    "languages": "en",
                    "format": "json",
                },
                timeout=6.0,
                max_retries=1,
            )
            if res_ref.ok and res_ref.data:
                for rqid, rent in res_ref.data.get("entities", {}).items():
                    lbl = rent.get("labels", {}).get("en", {}).get("value")
                    if lbl:
                        label_map[rqid] = lbl

        for item in grouped.values():
            item["industries"] = [label_map[q] for q in item["industry_qids"] if q in label_map]
            item["city"] = label_map.get(item["city_qid"]) if item.get("city_qid") else None
            item["country"] = label_map.get(item["country_qid"]) if item.get("country_qid") else None

        return grouped, None

    def search(self, parsed: ParsedQuery, max_results: int = 25) -> AdapterOutcome:
        t0 = time.monotonic()
        candidate_qids: List[str] = []

        if parsed.intent in ("specific_company", "domain_url"):
            term = parsed.domain_hint.split(".")[0] if parsed.domain_hint else parsed.cleaned_topic
            for qid in self._search_wb_entities(term, limit=6):
                if qid not in candidate_qids:
                    candidate_qids.append(qid)
            for qid in self._search_wikidata_cirrus(f"haswbstatement:P856 {term}", limit=10):
                if qid not in candidate_qids:
                    candidate_qids.append(qid)
        else:
            # Category / location / global query
            for qid in self._discover_qids_via_wikipedia(parsed, max_titles=35):
                if qid not in candidate_qids:
                    candidate_qids.append(qid)
            if len(candidate_qids) < 12:
                cirrus_q = f"haswbstatement:P856 {parsed.cleaned_topic}"
                if parsed.location_aliases:
                    cirrus_q += f" {parsed.location_aliases[0]}"
                for qid in self._search_wikidata_cirrus(cirrus_q, limit=12):
                    if qid not in candidate_qids:
                        candidate_qids.append(qid)

        if not candidate_qids:
            return AdapterOutcome(
                source_id=self.source_id,
                source_label=self.source_label,
                status="empty",
                records=[],
                latency_ms=int((time.monotonic() - t0) * 1000),
                message="No matching Wikidata entities found for query",
            )

        grouped, rest_err = self._hydrate_qids_rest(candidate_qids)
        if grouped is None:
            return AdapterOutcome(
                source_id=self.source_id,
                source_label=self.source_label,
                status="error",
                records=[],
                latency_ms=int((time.monotonic() - t0) * 1000),
                message=rest_err or "Wikidata API request failed",
            )

        records: List[Dict[str, Any]] = []
        loc_aliases_low = [a.lower() for a in parsed.location_aliases]
        topic_low = parsed.cleaned_topic.lower()

        for qid, item in grouped.items():
            # Domain validation check if domain search
            dom = normalize_domain(item["website"])
            if parsed.intent == "domain_url" and parsed.domain_hint:
                if parsed.domain_hint not in dom and parsed.cleaned_topic not in item["label"].lower():
                    continue

            # Relevance filtering for specific company search
            if parsed.intent == "specific_company":
                haystack = f"{item['label']} {item['description']} {dom}".lower()
                if topic_low not in haystack:
                    continue

            # Geographic filtering when user asked "... in <location>"
            if parsed.intent == "category_location" and loc_aliases_low:
                geo_text = f"{item.get('city') or ''} {item.get('country') or ''} {item.get('description') or ''}".lower()
                if not any(alias in geo_text for alias in loc_aliases_low):
                    continue

            # Ensure entity isn't clearly an unrelated sector when industry query has strong focus
            if parsed.intent == "category_location" and any(k in topic_low for k in ["health", "hospital", "pharma"]):
                ind_text = f"{' '.join(item['industries'])} {item['description']} {item['label']}".lower()
                if not any(k in ind_text for k in ["health", "hospital", "medical", "pharma", "biotech", "clinic", "care"]):
                    continue

            raw_ind = item["industries"][0] if item["industries"] else None
            biz_cat = ", ".join(item["industries"][:2]) if item["industries"] else "Public Business Entity"

            rec = _make_record(
                company_name=item["label"],
                website=item["website"],
                domain=dom,
                business_category=biz_cat,
                industry=raw_ind,
                country=item["country"],
                city=item["city"],
                email=item["email"],
                phone=item["phone"],
                description=item["description"] or f"Verified entity on Wikidata ({qid})",
                source_provider=self.source_id,
                source_url=f"https://www.wikidata.org/wiki/{qid}",
                verification_status="verified_email" if item["email"] else "verified_domain",
                is_demo=False,
                lawful_basis_note="Wikidata CC0 Structured Public Business Knowledge Graph",
            )
            records.append(rec)
            if len(records) >= max_results:
                break

        return AdapterOutcome(
            source_id=self.source_id,
            source_label=self.source_label,
            status="ok" if records else "empty",
            records=records,
            latency_ms=int((time.monotonic() - t0) * 1000),
            message=None if records else "Entities retrieved lacked matching business/location metadata",
        )


# ==============================================================================
# 2. OPENSTREETMAP / OVERPASS / PHOTON / NOMINATIM ADAPTER
# ==============================================================================
class OpenStreetMapAdapter(BaseSourceAdapter):
    """
    Live dynamic OpenStreetMap discovery using:
    1. Nominatim Geocoding (resolves any city/state/country into dynamic bounding box)
    2. Photon OSM Search API + Nominatim Lookup (fast structured business tag lookup)
    3. Overpass API with mirror failover inside resolved bounding box
    Never uses hardcoded coordinates and never fabricates emails or phone numbers.
    """
    source_id = "openstreetmap"
    source_label = "OpenStreetMap / Overpass Business Directory"

    def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        res = request_with_retry(
            "nominatim",
            "GET",
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "jsonv2", "limit": 1, "addressdetails": 1},
            timeout=6.0,
            max_retries=1,
            min_interval=0.4,
        )
        if res.ok and isinstance(res.data, list) and res.data:
            return res.data[0]
        return None

    def _photon_search(self, q: str, limit: int = 12, lat: Optional[float] = None, lon: Optional[float] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"q": q, "limit": limit}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        res = request_with_retry(
            "photon",
            "GET",
            "https://photon.komoot.io/api/",
            params=params,
            timeout=6.0,
            max_retries=1,
        )
        if not res.ok or not res.data:
            return []
        return res.data.get("features", [])

    def _nominatim_lookup_batch(self, osm_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not osm_ids:
            return {}
        res = request_with_retry(
            "nominatim",
            "GET",
            "https://nominatim.openstreetmap.org/lookup",
            params={
                "osm_ids": ",".join(osm_ids[:20]),
                "format": "jsonv2",
                "extratags": 1,
                "addressdetails": 1,
            },
            timeout=7.0,
            max_retries=1,
            min_interval=0.5,
        )
        out: Dict[str, Dict[str, Any]] = {}
        if res.ok and isinstance(res.data, list):
            for entry in res.data:
                ot = entry.get("osm_type", "")
                oid = entry.get("osm_id")
                if ot and oid:
                    prefix = ot[0].upper()
                    out[f"{prefix}{oid}"] = entry
        return out

    def _query_overpass(self, lat: float, lon: float, tag_hints: List[Tuple[str, str]], limit: int = 15) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        # Build narrow Overpass union query within 10km around geocoded center
        clauses = []
        for k, v in tag_hints[:2]:
            if v == "*":
                clauses.append(f'nwr["{k}"]["name"](around:10000,{lat},{lon});')
            else:
                clauses.append(f'nwr["{k}"="{v}"]["name"](around:10000,{lat},{lon});')
        ql = f'[out:json][timeout:4];({"".join(clauses)});out center {limit};'

        last_err = None
        for ep in OVERPASS_ENDPOINTS:
            res = request_with_retry(
                "overpass",
                "POST",
                ep,
                data={"data": ql},
                timeout=4.5,
                max_retries=0,
            )
            if res.ok and isinstance(res.data, dict):
                return res.data.get("elements", []), None
            last_err = res.error
        return [], last_err

    def search(self, parsed: ParsedQuery, max_results: int = 25) -> AdapterOutcome:
        t0 = time.monotonic()
        records: List[Dict[str, Any]] = []
        notes: List[str] = []

        geo_lat: Optional[float] = None
        geo_lon: Optional[float] = None
        geo_is_city = False
        if parsed.location:
            geo = self._geocode_location(parsed.location)
            if geo:
                try:
                    geo_lat = float(geo["lat"])
                    geo_lon = float(geo["lon"])
                    geo_is_city = geo.get("addresstype") not in ("country", "state")
                except (KeyError, ValueError, TypeError):
                    pass

        # 1. Overpass structured query when a city-level location is resolved
        if geo_lat is not None and geo_lon is not None and geo_is_city and parsed.intent == "category_location":
            ov_elements, ov_err = self._query_overpass(geo_lat, geo_lon, parsed.osm_tag_hints, limit=min(15, max_results))
            if ov_err:
                notes.append(f"Overpass server note: {ov_err}")
            for el in ov_elements:
                tags = el.get("tags", {})
                cname = tags.get("name")
                if not cname:
                    continue
                el_type = el.get("type", "node")
                el_id = el.get("id")
                web = tags.get("website") or tags.get("contact:website") or tags.get("url")
                email = tags.get("email") or tags.get("contact:email")
                phone = tags.get("phone") or tags.get("contact:phone")
                cat_val = tags.get("office") or tags.get("industrial") or tags.get("amenity") or tags.get("healthcare") or "commercial"
                records.append(_make_record(
                    company_name=cname,
                    website=web,
                    business_category=f"OSM {cat_val.replace('_', ' ').title()}",
                    industry=parsed.inferred_industry or cat_val,
                    country=tags.get("addr:country") or parsed.inferred_country,
                    city=tags.get("addr:city") or parsed.location,
                    region=parsed.inferred_region,
                    email=email,
                    phone=phone,
                    description=f"OpenStreetMap Overpass public business listing ({cat_val})",
                    source_provider=self.source_id,
                    source_url=f"https://www.openstreetmap.org/{el_type}/{el_id}",
                    verification_status="verified_email" if email else ("verified_domain" if web else "verified_domain"),
                    is_demo=False,
                    lawful_basis_note="OpenStreetMap ODbL Public Map Data",
                ))

        # 2. Photon OSM search + Nominatim Lookup enrichment
        photon_q = parsed.raw_query
        if parsed.intent == "category_location" and parsed.location:
            # Make Photon search friendlier by pairing concise topic + location
            topic_word = parsed.expanded_keywords[0] if parsed.expanded_keywords else parsed.cleaned_topic
            if "hospital" in " ".join(parsed.expanded_keywords):
                photon_q = f"Hospital {parsed.location}"
            elif "manufactur" in parsed.cleaned_topic.lower():
                photon_q = f"Manufacturing {parsed.location}"
            else:
                photon_q = f"{parsed.cleaned_topic} {parsed.location}"

        feats = self._photon_search(photon_q, limit=min(15, max_results), lat=geo_lat, lon=geo_lon)
        valid_osm_keys = {"office", "industrial", "amenity", "landuse", "building", "shop", "craft"}
        candidate_feats = []
        osm_lookup_ids = []

        for f in feats:
            p = f.get("properties", {})
            name = p.get("name")
            if not name:
                continue
            osm_key = p.get("osm_key", "")
            osm_val = p.get("osm_value", "")
            if osm_key in ("railway", "highway", "natural", "waterway", "place"):
                continue
            if osm_val in ("apartments", "house", "residential", "educational_institution", "school", "college", "university"):
                continue
            if parsed.intent == "specific_company" and parsed.cleaned_topic.lower() not in name.lower():
                continue
            if osm_key not in valid_osm_keys and osm_val not in ("commercial", "industrial", "office"):
                continue

            otype = p.get("osm_type", "")
            oid = p.get("osm_id")
            if otype and oid:
                full_oid = f"{otype.upper()}{oid}"
                if full_oid not in osm_lookup_ids:
                    osm_lookup_ids.append(full_oid)
                candidate_feats.append((full_oid, p))

        enriched_map = self._nominatim_lookup_batch(osm_lookup_ids)
        seen_oids = set()
        for full_oid, props in candidate_feats:
            if full_oid in seen_oids:
                continue
            seen_oids.add(full_oid)
            nom = enriched_map.get(full_oid, {})
            extra = nom.get("extratags") or {}
            addr = nom.get("address") or {}

            cname = nom.get("name") or props.get("name")
            web = extra.get("website") or extra.get("contact:website") or extra.get("url")
            email = extra.get("email") or extra.get("contact:email")
            phone = extra.get("phone") or extra.get("contact:phone")
            city = addr.get("city") or addr.get("town") or addr.get("state_district") or props.get("city") or parsed.location
            ctry = addr.get("country") or props.get("country") or parsed.inferred_country

            # Guard against fuzzy substring country mismatches (e.g. searching 'India' matching 'Indiana, United States')
            if parsed.inferred_country and ctry and parsed.inferred_country.lower() not in ctry.lower():
                continue

            osm_type_full = {"N": "node", "W": "way", "R": "relation"}.get(props.get("osm_type", "N").upper(), "node")
            osm_url = f"https://www.openstreetmap.org/{osm_type_full}/{props.get('osm_id')}"

            cat_label = f"{props.get('osm_key', 'office')}={props.get('osm_value', 'company')}"
            records.append(_make_record(
                company_name=cname,
                website=web,
                business_category=f"OSM {props.get('osm_value', 'Company').replace('_', ' ').title()}",
                industry=parsed.inferred_industry or props.get("osm_value") or "Commercial Enterprise",
                country=ctry,
                city=city,
                region=parsed.inferred_region,
                email=email,
                phone=phone,
                description=f"OpenStreetMap commercial location ({cat_label})",
                source_provider=self.source_id,
                source_url=osm_url,
                verification_status="verified_email" if email else ("verified_domain" if web else "verified_domain"),
                is_demo=False,
                lawful_basis_note="OpenStreetMap ODbL Public Map Data",
            ))

        status_str = "ok" if records else "empty"
        return AdapterOutcome(
            source_id=self.source_id,
            source_label=self.source_label,
            status=status_str,
            records=records[:max_results],
            latency_ms=int((time.monotonic() - t0) * 1000),
            message="; ".join(notes) if notes else (None if records else "No matching OpenStreetMap commercial listings returned"),
        )


# ==============================================================================
# 3. COMPANY DIRECTORY ADAPTER (CLEARBIT AUTOCOMPLETE API)
# ==============================================================================
class CompanyDirectoryAdapter(BaseSourceAdapter):
    """
    Discovers corporate names and official domains via the public Clearbit Company Suggest API.
    Best suited for brand/company lookups and concise global technology/keyword searches.
    """
    source_id = "company_directory"
    source_label = "Public Company Domain Directory"

    def search(self, parsed: ParsedQuery, max_results: int = 25) -> AdapterOutcome:
        t0 = time.monotonic()
        if parsed.intent == "category_location":
            # Clearbit Autocomplete only matches company prefix names, not natural language geography
            return AdapterOutcome(
                source_id=self.source_id,
                source_label=self.source_label,
                status="empty",
                records=[],
                latency_ms=int((time.monotonic() - t0) * 1000),
                message="Skipped for location-based category query (domain prefix API)",
            )

        term = parsed.domain_hint or parsed.cleaned_topic
        res = request_with_retry(
            "clearbit_suggest",
            "GET",
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": term},
            timeout=6.0,
            max_retries=1,
        )
        if not res.ok:
            return AdapterOutcome(
                source_id=self.source_id,
                source_label=self.source_label,
                status="rate_limited" if res.rate_limited else ("timeout" if res.timed_out else "error"),
                records=[],
                latency_ms=int((time.monotonic() - t0) * 1000),
                message=res.error,
            )

        data = res.data if isinstance(res.data, list) else []
        records: List[Dict[str, Any]] = []
        term_low = parsed.cleaned_topic.lower()

        for entry in data:
            name = (entry.get("name") or "").strip()
            dom = normalize_domain(entry.get("domain") or "")
            if not name or not dom:
                continue
            if len(name) > 85 or name.startswith("@"):
                continue
            if parsed.intent == "specific_company" and term_low not in name.lower() and term_low not in dom:
                continue
            records.append(_make_record(
                company_name=name,
                website=f"https://{dom}",
                domain=dom,
                business_category="Verified Corporate Domain",
                industry=parsed.inferred_industry or "Commercial Enterprise",
                country=parsed.inferred_country,
                region=parsed.inferred_region,
                description=f"Official business domain resolved via Public Company Directory ({dom})",
                source_provider=self.source_id,
                source_url=f"https://{dom}",
                verification_status="verified_domain",
                is_demo=False,
                lawful_basis_note="Public DNS / Corporate Domain Registry",
            ))
            if len(records) >= max_results:
                break

        return AdapterOutcome(
            source_id=self.source_id,
            source_label=self.source_label,
            status="ok" if records else "empty",
            records=records,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


# ==============================================================================
# 4. EXTERNAL SEARCH API ADAPTER (GOOGLE PLACES, SERPER, SERPAPI, BRAVE, DDG IA)
# ==============================================================================
class ExternalSearchAPIAdapter(BaseSourceAdapter):
    """
    Modular external search API adapter.
    Uses configured commercial APIs (Google Places, Serper, SerpAPI, Brave Search) when keys exist,
    plus DuckDuckGo Instant Answer API for public company lookups.
    """
    source_id = "external_search"
    source_label = "External Search APIs (Google Places / Serper / SerpAPI / Brave / DDG)"

    def _search_google_places(self, query_text: str, max_results: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not settings.GOOGLE_PLACES_API_KEY:
            return [], "GOOGLE_PLACES_API_KEY not configured"
        res = request_with_retry(
            "google_places",
            "GET",
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"query": query_text, "key": settings.GOOGLE_PLACES_API_KEY},
            timeout=7.0,
            max_retries=1,
        )
        if not res.ok or not res.data:
            return [], res.error
        records = []
        for place in res.data.get("results", [])[:max_results]:
            name = place.get("name")
            if not name:
                continue
            pid = place.get("place_id")
            web = None
            phone = None
            if pid:
                det = request_with_retry(
                    "google_places",
                    "GET",
                    "https://maps.googleapis.com/maps/api/place/details/json",
                    params={
                        "place_id": pid,
                        "fields": "name,website,formatted_phone_number,url,address_components",
                        "key": settings.GOOGLE_PLACES_API_KEY,
                    },
                    timeout=5.0,
                    max_retries=0,
                )
                if det.ok and det.data:
                    result = det.data.get("result", {})
                    web = result.get("website")
                    phone = result.get("formatted_phone_number")
            records.append(_make_record(
                company_name=name,
                website=web,
                business_category=", ".join(place.get("types", [])[:2]) or "Business",
                phone=phone,
                description=place.get("formatted_address"),
                source_provider="google_places",
                source_url=f"https://www.google.com/maps/place/?q=place_id:{pid}" if pid else "https://maps.google.com",
                verification_status="verified_domain" if web else "unverified",
                lawful_basis_note="Google Places API Authorized Business Data",
            ))
        return records, None

    def _search_serper(self, query_text: str, max_results: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not settings.SERPER_API_KEY:
            return [], "SERPER_API_KEY not configured"
        res = request_with_retry(
            "serper",
            "POST",
            "https://google.serper.dev/search",
            json_body={"q": query_text, "num": min(max_results, 20)},
            headers={"X-API-KEY": settings.SERPER_API_KEY},
            timeout=7.0,
            max_retries=1,
        )
        if not res.ok or not res.data:
            return [], res.error
        records = []
        for org in res.data.get("organic", []):
            link = org.get("link")
            title = org.get("title", "")
            cname = title.split(" - ")[0].split(" | ")[0].strip()
            if not cname or not link:
                continue
            records.append(_make_record(
                company_name=cname,
                website=link,
                description=org.get("snippet"),
                source_provider="external_search",
                source_url=link,
                verification_status="verified_domain",
                lawful_basis_note="Serper Google Search Public Business Index",
            ))
        return records, None

    def _search_brave(self, query_text: str, max_results: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not settings.BRAVE_SEARCH_API_KEY:
            return [], "BRAVE_SEARCH_API_KEY not configured"
        res = request_with_retry(
            "brave_search",
            "GET",
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query_text, "count": min(max_results, 20)},
            headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY},
            timeout=7.0,
            max_retries=1,
        )
        if not res.ok or not res.data:
            return [], res.error
        records = []
        for item in res.data.get("web", {}).get("results", []):
            url = item.get("url")
            title = item.get("title", "")
            cname = title.split(" - ")[0].split(" | ")[0].strip()
            if not cname or not url:
                continue
            records.append(_make_record(
                company_name=cname,
                website=url,
                description=item.get("description"),
                source_provider="external_search",
                source_url=url,
                verification_status="verified_domain",
                lawful_basis_note="Brave Web Search Public Index",
            ))
        return records, None

    def _search_ddg_instant_answer(self, parsed: ParsedQuery) -> List[Dict[str, Any]]:
        if parsed.intent not in ("specific_company", "domain_url"):
            return []
        q_term = parsed.domain_hint or f"{parsed.cleaned_topic} company"
        res = request_with_retry(
            "ddg_ia",
            "GET",
            "https://api.duckduckgo.com/",
            params={"q": q_term, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=5.0,
            max_retries=0,
        )
        if not res.ok or not isinstance(res.data, dict):
            return []
        d = res.data
        heading = (d.get("Heading") or "").strip()
        if not heading:
            return []
        official_url = None
        for r in d.get("Results", []):
            if "official site" in (r.get("Text") or "").lower() or r.get("FirstURL"):
                official_url = r.get("FirstURL")
                break
        if not official_url:
            return []
        clean_name = re.sub(r"\s*\(company\)\s*$", "", heading, flags=re.IGNORECASE).strip()
        return [_make_record(
            company_name=clean_name,
            website=official_url,
            business_category="Official Enterprise Website",
            industry=parsed.inferred_industry,
            country=parsed.inferred_country,
            region=parsed.inferred_region,
            description=d.get("AbstractText") or f"Verified official homepage from DuckDuckGo Knowledge Graph",
            source_provider=self.source_id,
            source_url=d.get("AbstractURL") or official_url,
            verification_status="verified_domain",
            is_demo=False,
            lawful_basis_note="DuckDuckGo Instant Answer Official Website Reference",
        )]

    def search(self, parsed: ParsedQuery, max_results: int = 25) -> AdapterOutcome:
        t0 = time.monotonic()
        records: List[Dict[str, Any]] = []
        notes: List[str] = []

        # Run configured commercial providers if API keys exist
        if settings.GOOGLE_PLACES_API_KEY:
            gp_recs, gp_err = self._search_google_places(parsed.raw_query, max_results)
            records.extend(gp_recs)
            if gp_err:
                notes.append(gp_err)
        if settings.SERPER_API_KEY:
            s_recs, s_err = self._search_serper(parsed.raw_query, max_results)
            records.extend(s_recs)
            if s_err:
                notes.append(s_err)
        if settings.BRAVE_SEARCH_API_KEY:
            b_recs, b_err = self._search_brave(parsed.raw_query, max_results)
            records.extend(b_recs)
            if b_err:
                notes.append(b_err)

        # Always run DuckDuckGo IA for company/domain lookups
        records.extend(self._search_ddg_instant_answer(parsed))

        has_commercial = any([settings.GOOGLE_PLACES_API_KEY, settings.SERPER_API_KEY, settings.BRAVE_SEARCH_API_KEY])
        if not has_commercial and not records:
            return AdapterOutcome(
                source_id=self.source_id,
                source_label=self.source_label,
                status="not_configured" if parsed.intent.startswith("category") else "empty",
                records=[],
                latency_ms=int((time.monotonic() - t0) * 1000),
                message="Optional commercial Search API keys (GOOGLE_PLACES_API_KEY / SERPER_API_KEY / BRAVE_SEARCH_API_KEY) are not configured",
            )

        return AdapterOutcome(
            source_id=self.source_id,
            source_label=self.source_label,
            status="ok" if records else "empty",
            records=records[:max_results],
            latency_ms=int((time.monotonic() - t0) * 1000),
            message="; ".join(notes) if notes else None,
        )


# ==============================================================================
# 5. GOOGLE PLACES EXPLICIT ADAPTER (BACKWARD COMPATIBLE OPTION)
# ==============================================================================
class GooglePlacesAdapter(BaseSourceAdapter):
    source_id = "google_places"
    source_label = "Google Places Business API"

    def search(self, parsed: ParsedQuery, max_results: int = 25) -> AdapterOutcome:
        t0 = time.monotonic()
        if not settings.GOOGLE_PLACES_API_KEY:
            return AdapterOutcome(
                source_id=self.source_id,
                source_label=self.source_label,
                status="not_configured",
                records=[],
                latency_ms=int((time.monotonic() - t0) * 1000),
                message="GOOGLE_PLACES_API_KEY is not configured in backend environment settings.",
            )
        ext = ExternalSearchAPIAdapter()
        recs, err = ext._search_google_places(parsed.raw_query, max_results)
        return AdapterOutcome(
            source_id=self.source_id,
            source_label=self.source_label,
            status="ok" if recs else ("error" if err else "empty"),
            records=recs,
            latency_ms=int((time.monotonic() - t0) * 1000),
            message=err,
        )


# ==============================================================================
# 6. WEBSITE PUBLIC CONTACT ENRICHMENT ADAPTER (ROBOTS.TXT STRICT)
# ==============================================================================
class WebsiteEnrichmentAdapter(BaseSourceAdapter):
    """
    Robots.txt-strict public corporate website reader.
    Extracts genuinely listed business emails (mailto: / visible business addresses) and phone numbers.
    Never invents or fabricates contact information.
    """
    source_id = "website"
    source_label = "Official Company Website (robots.txt compliant)"

    def extract_public_contacts(self, website_url: str, domain: str) -> Dict[str, Optional[str]]:
        out: Dict[str, Optional[str]] = {"email": None, "phone": None, "description": None}
        if not website_url or not website_url.startswith(ALLOWED_SCRAPE_SCHEMES):
            return out

        rp = _fetch_robots_parser(website_url)
        user_agent = "LeadSharkBot/1.0 (+https://leadshark.io)"
        if rp is not None and not rp.can_fetch(user_agent, website_url):
            return out

        parsed_u = urlparse(website_url)
        base_root = f"{parsed_u.scheme}://{parsed_u.netloc}"
        candidate_urls = [website_url, urljoin(base_root, "/contact")]

        for idx, url in enumerate(candidate_urls):
            if idx > 0 and (out["email"] or out["phone"]):
                break
            if idx > 0 and rp is not None and not rp.can_fetch(user_agent, url):
                continue
            res = request_with_retry(
                "website_fetch",
                "GET",
                url,
                timeout=2.5,
                max_retries=0,
                expect_json=False,
                headers={"User-Agent": "Mozilla/5.0 (compatible; LeadSharkBot/1.0; +https://leadshark.io)"},
            )
            if not res.ok or not res.text:
                # Don't probe /contact if landing page blocked (e.g. WAF 403/429) or timed out
                if idx == 0 and res.status_code in (403, 429, 0):
                    break
                continue

            html = res.text[:200000]
            if not out["description"]:
                dm = META_DESC_PATTERN.search(html)
                if dm:
                    out["description"] = dm.group(1).strip()

            if not out["email"]:
                raw_emails = MAILTO_PATTERN.findall(html) + EMAIL_PATTERN.findall(html)
                for candidate in raw_emails:
                    em = candidate.strip().lower()
                    if any(bad in em for bad in BLOCKED_EMAIL_FRAGMENTS):
                        continue
                    if "@" not in em or len(em) > 80:
                        continue
                    if domain and domain in em.split("@", 1)[1]:
                        out["email"] = em
                        break
                    if not out["email"]:
                        out["email"] = em

            if not out["phone"]:
                tels = TEL_PATTERN.findall(html)
                for t in tels:
                    clean_t = re.sub(r"\s+", " ", t).strip()
                    if 7 <= sum(ch.isdigit() for ch in clean_t) <= 15:
                        out["phone"] = clean_t
                        break

        return out

    def enrich_batch(self, records: List[Dict[str, Any]], max_sites: int = 4) -> None:
        seen_domains = set()
        targets = []
        for rec in records:
            dom = rec.get("company_domain") or ""
            if rec.get("company_website") and (not rec.get("email") or not rec.get("company_phone")) and dom not in seen_domains:
                seen_domains.add(dom)
                targets.append(rec)
                if len(targets) >= max_sites:
                    break
        if not targets:
            return

        pool = ThreadPoolExecutor(max_workers=4)
        try:
            future_map = {
                pool.submit(self.extract_public_contacts, rec["company_website"], rec.get("company_domain", "")): rec
                for rec in targets
            }
            for fut in as_completed(future_map, timeout=5.0):
                rec = future_map[fut]
                try:
                    extracted = fut.result(timeout=0.5)
                    if not rec.get("email") and extracted.get("email"):
                        rec["email"] = extracted["email"]
                    if not rec.get("company_phone") and extracted.get("phone"):
                        rec["company_phone"] = extracted["phone"]
                    if not rec.get("company_description") and extracted.get("description"):
                        rec["company_description"] = extracted["description"]
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def search(self, parsed: ParsedQuery, max_results: int = 25) -> AdapterOutcome:
        t0 = time.monotonic()
        target_url = _clean_website_url(parsed.domain_hint or parsed.raw_query)
        if not target_url:
            return AdapterOutcome(
                source_id=self.source_id,
                source_label=self.source_label,
                status="empty",
                records=[],
                latency_ms=int((time.monotonic() - t0) * 1000),
                message="Website adapter requires a valid domain or URL (e.g., wipro.com)",
            )
        dom = normalize_domain(target_url)
        contacts = self.extract_public_contacts(target_url, dom)
        cname = dom.split(".")[0].capitalize()
        rec = _make_record(
            company_name=cname,
            website=target_url,
            domain=dom,
            business_category="Company Website",
            industry=parsed.inferred_industry,
            country=parsed.inferred_country,
            region=parsed.inferred_region,
            email=contacts["email"],
            phone=contacts["phone"],
            description=contacts["description"] or f"Official website analyzed cleanly via robots.txt ({dom})",
            source_provider=self.source_id,
            source_url=target_url,
            verification_status="verified_email" if contacts["email"] else "verified_domain",
            is_demo=False,
            lawful_basis_note="Public Website Business Contact Page (robots.txt permitted)",
        )
        return AdapterOutcome(
            source_id=self.source_id,
            source_label=self.source_label,
            status="ok",
            records=[rec],
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
