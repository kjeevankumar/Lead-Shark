import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


CATEGORY_TRIGGER_WORDS = {
    "company", "companies", "business", "businesses", "enterprise", "enterprises",
    "firm", "firms", "startup", "startups", "organization", "organizations",
    "hospital", "hospitals", "clinic", "clinics", "agency", "agencies",
    "manufacturer", "manufacturers", "manufacturing", "factory", "factories",
    "vendor", "vendors", "provider", "providers", "services", "industry",
    "industries", "corps", "corporations", "consultancy", "consultancies"
}

GENERIC_INDUSTRY_EXPANSIONS = {
    "it": ["information technology", "software", "IT services", "technology"],
    "software": ["software development", "information technology", "SaaS", "technology"],
    "tech": ["technology", "software", "information technology", "electronics"],
    "cloud": ["cloud computing", "cloud services", "SaaS", "cloud infrastructure"],
    "cloud computing": ["cloud computing", "cloud infrastructure", "cloud platform", "SaaS"],
    "startup": ["startup", "technology", "software", "fintech", "e-commerce", "SaaS"],
    "startups": ["startup", "technology", "software", "fintech", "e-commerce", "SaaS"],
    "manufacturing": ["manufacturing", "industrial", "automotive", "engineering", "factory"],
    "industrial": ["industrial", "manufacturing", "engineering", "machinery"],
    "healthcare": ["healthcare", "health care", "hospital", "pharmaceutical", "biotechnology", "medical"],
    "health": ["healthcare", "hospital", "medical", "pharmaceutical"],
    "pharma": ["pharmaceutical", "biotechnology", "healthcare"],
    "biotech": ["biotechnology", "pharmaceutical", "healthcare"],
    "fintech": ["financial services", "fintech", "banking", "payments"],
    "finance": ["financial services", "banking", "investment", "insurance"],
    "retail": ["retail", "e-commerce", "consumer goods"],
    "ecommerce": ["e-commerce", "retail", "online marketplace"],
    "cleantech": ["renewable energy", "clean technology", "solar", "energy"],
    "energy": ["energy", "power", "renewable energy", "oil and gas"],
    "logistics": ["logistics", "supply chain", "freight", "shipping"],
    "telecom": ["telecommunications", "wireless", "networking"],
    "ai": ["artificial intelligence", "machine learning", "software", "data science"],
    "cybersecurity": ["computer security", "cybersecurity", "information security"],
}

INDUSTRY_STANDARD_SECTOR_MAP = {
    "it": "Information Technology",
    "software": "Information Technology",
    "tech": "Information Technology",
    "cloud": "Information Technology",
    "startup": "Information Technology",
    "startups": "Information Technology",
    "ai": "Information Technology",
    "cybersecurity": "Information Technology",
    "telecom": "Information Technology",
    "manufacturing": "Manufacturing & Industrial",
    "industrial": "Manufacturing & Industrial",
    "automotive": "Manufacturing & Industrial",
    "engineering": "Manufacturing & Industrial",
    "logistics": "Manufacturing & Industrial",
    "healthcare": "Healthcare & Life Sciences",
    "health": "Healthcare & Life Sciences",
    "hospital": "Healthcare & Life Sciences",
    "pharma": "Healthcare & Life Sciences",
    "biotech": "Healthcare & Life Sciences",
    "medical": "Healthcare & Life Sciences",
    "finance": "Financial Services",
    "fintech": "Financial Services",
    "banking": "Financial Services",
    "insurance": "Financial Services",
    "retail": "Retail & E-Commerce",
    "ecommerce": "Retail & E-Commerce",
    "e-commerce": "Retail & E-Commerce",
    "consulting": "Professional & Legal Services",
    "legal": "Professional & Legal Services",
    "energy": "CleanTech & Energy",
    "cleantech": "CleanTech & Energy",
    "solar": "CleanTech & Energy",
}

GEO_ALIASES = {
    "bangalore": ["Bangalore", "Bengaluru", "Karnataka", "India"],
    "bengaluru": ["Bengaluru", "Bangalore", "Karnataka", "India"],
    "hyderabad": ["Hyderabad", "Telangana", "India"],
    "telangana": ["Telangana", "Hyderabad", "Warangal", "India"],
    "mumbai": ["Mumbai", "Bombay", "Maharashtra", "India"],
    "delhi": ["Delhi", "New Delhi", "NCR", "India"],
    "chennai": ["Chennai", "Tamil Nadu", "India"],
    "pune": ["Pune", "Maharashtra", "India"],
    "gurgaon": ["Gurgaon", "Gurugram", "India"],
    "noida": ["Noida", "Uttar Pradesh", "India"],
    "india": ["India"],
    "usa": ["United States", "USA", "America"],
    "us": ["United States", "USA"],
    "united states": ["United States", "USA"],
    "uk": ["United Kingdom", "UK", "England", "Britain"],
    "united kingdom": ["United Kingdom", "UK", "Britain"],
    "london": ["London", "United Kingdom"],
    "san francisco": ["San Francisco", "California", "United States"],
    "new york": ["New York", "New York City", "United States"],
    "seattle": ["Seattle", "Washington", "United States"],
    "singapore": ["Singapore"],
    "germany": ["Germany", "Deutschland"],
    "berlin": ["Berlin", "Germany"],
    "france": ["France"],
    "paris": ["Paris", "France"],
    "canada": ["Canada"],
    "toronto": ["Toronto", "Canada"],
    "australia": ["Australia"],
    "sydney": ["Sydney", "Australia"],
    "dubai": ["Dubai", "United Arab Emirates"],
    "uae": ["United Arab Emirates", "UAE", "Dubai"],
}

LOCATION_TO_REGION = {
    "india": ("Asia-Pacific", "India"),
    "hyderabad": ("Asia-Pacific", "India"),
    "telangana": ("Asia-Pacific", "India"),
    "bangalore": ("Asia-Pacific", "India"),
    "bengaluru": ("Asia-Pacific", "India"),
    "mumbai": ("Asia-Pacific", "India"),
    "chennai": ("Asia-Pacific", "India"),
    "delhi": ("Asia-Pacific", "India"),
    "pune": ("Asia-Pacific", "India"),
    "singapore": ("Asia-Pacific", "Singapore"),
    "tokyo": ("Asia-Pacific", "Japan"),
    "japan": ("Asia-Pacific", "Japan"),
    "australia": ("Asia-Pacific", "Australia"),
    "sydney": ("Asia-Pacific", "Australia"),
    "china": ("Asia-Pacific", "China"),
    "usa": ("North America", "United States"),
    "us": ("North America", "United States"),
    "united states": ("North America", "United States"),
    "san francisco": ("North America", "United States"),
    "new york": ("North America", "United States"),
    "seattle": ("North America", "United States"),
    "california": ("North America", "United States"),
    "canada": ("North America", "Canada"),
    "toronto": ("North America", "Canada"),
    "uk": ("Europe (UK/EU)", "United Kingdom"),
    "united kingdom": ("Europe (UK/EU)", "United Kingdom"),
    "london": ("Europe (UK/EU)", "United Kingdom"),
    "germany": ("Europe (UK/EU)", "Germany"),
    "berlin": ("Europe (UK/EU)", "Germany"),
    "france": ("Europe (UK/EU)", "France"),
    "paris": ("Europe (UK/EU)", "France"),
    "sweden": ("Europe (UK/EU)", "Sweden"),
    "netherlands": ("Europe (UK/EU)", "Netherlands"),
    "ireland": ("Europe (UK/EU)", "Ireland"),
    "dubai": ("Middle East & Africa", "United Arab Emirates"),
    "uae": ("Middle East & Africa", "United Arab Emirates"),
}

GLOBAL_MARKERS = {"globally", "global", "worldwide", "international", "world"}


@dataclass
class ParsedQuery:
    raw_query: str
    cleaned_topic: str
    intent: str  # specific_company | category_location | category_global | domain_url
    location: Optional[str] = None
    location_aliases: List[str] = field(default_factory=list)
    inferred_country: Optional[str] = None
    inferred_region: Optional[str] = None
    inferred_industry: Optional[str] = None
    expanded_keywords: List[str] = field(default_factory=list)
    osm_tag_hints: List[Tuple[str, str]] = field(default_factory=list)
    domain_hint: Optional[str] = None


def infer_region_and_country(location_or_country: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not location_or_country:
        return None, None
    key = location_or_country.strip().lower()
    if key in LOCATION_TO_REGION:
        return LOCATION_TO_REGION[key]
    for loc_k, val in LOCATION_TO_REGION.items():
        if loc_k in key:
            return val
    return None, None


def infer_standard_sector(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    low = text.lower()
    for token, sector in INDUSTRY_STANDARD_SECTOR_MAP.items():
        if re.search(rf"\b{re.escape(token)}\b", low):
            return sector
    return None


def _get_osm_hints(topic_low: str) -> List[Tuple[str, str]]:
    if any(k in topic_low for k in ["hospital", "health", "clinic", "pharma", "medical", "biotech"]):
        return [("amenity", "hospital"), ("amenity", "clinic"), ("healthcare", "*"), ("office", "company")]
    if any(k in topic_low for k in ["manufactur", "industrial", "factory", "plant", "automotive", "engineering"]):
        return [("industrial", "*"), ("landuse", "industrial"), ("building", "industrial"), ("office", "company")]
    if any(k in topic_low for k in ["it", "software", "tech", "cloud", "startup", "saas", "ai", "cyber"]):
        return [("office", "it"), ("office", "company"), ("office", "telecommunication")]
    if any(k in topic_low for k in ["finance", "bank", "fintech", "insurance", "investment"]):
        return [("office", "financial"), ("amenity", "bank"), ("office", "company")]
    return [("office", "company"), ("office", "it"), ("industrial", "*")]


def parse_universal_query(
    query: str,
    region: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
) -> ParsedQuery:
    raw = (query or "").strip()
    low = raw.lower()

    # 1. Domain / URL check (e.g. wipro.com or https://stripe.com)
    domain_match = re.match(r"^(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})(?:/.*)?$", raw)
    if domain_match:
        dom = domain_match.group(1).lower()
        return ParsedQuery(
            raw_query=raw,
            cleaned_topic=dom.split(".")[0],
            intent="domain_url",
            domain_hint=dom,
            inferred_region=region if region and region != "Global" else None,
            inferred_country=country,
            inferred_industry=industry if industry and industry != "All" else None,
            expanded_keywords=[dom],
            osm_tag_hints=[("office", "company")],
        )

    # 2. Detect explicit "<topic> in/at/near/from <location>"
    loc = None
    topic = raw
    is_global_phrase = False

    loc_split = re.match(r"^(.*?)\s+(?:in|at|near|across|from|based in)\s+(.+)$", raw, flags=re.IGNORECASE)
    if loc_split:
        topic_part = loc_split.group(1).strip()
        loc_part = loc_split.group(2).strip().rstrip(".,")
        if loc_part.lower() in GLOBAL_MARKERS:
            is_global_phrase = True
            topic = topic_part
        else:
            topic = topic_part
            loc = loc_part
    else:
        # Handle trailing global markers like "Cloud computing companies globally"
        words = raw.split()
        if words and words[-1].lower().rstrip(".,") in GLOBAL_MARKERS:
            is_global_phrase = True
            topic = " ".join(words[:-1]).strip()

    # Clean generic noun words ("companies", "firms", "businesses") to isolate core topic
    topic_tokens = topic.split()
    has_category_trigger = any(t.lower().rstrip(".,") in CATEGORY_TRIGGER_WORDS for t in topic_tokens)

    cleaned_words = [
        w for w in topic_tokens
        if w.lower().rstrip(".,") not in {"companies", "company", "businesses", "business", "firms", "firm", "enterprises", "organizations"}
    ]
    cleaned_topic = " ".join(cleaned_words).strip() or topic.strip() or raw

    # Strip "startups" only when keeping it is useful or keep it as category keyword
    topic_low = cleaned_topic.lower()

    # Determine intent
    if loc:
        intent = "category_location"
    elif is_global_phrase or has_category_trigger or topic_low in GENERIC_INDUSTRY_EXPANSIONS:
        intent = "category_global"
    else:
        intent = "specific_company"

    # Resolve location aliases and region/country
    loc_aliases: List[str] = []
    inferred_reg = None
    inferred_country = country.strip() if country and country.strip() not in ("All", "Global") else None

    effective_loc = loc or inferred_country
    if effective_loc:
        eff_low = effective_loc.lower()
        loc_aliases = GEO_ALIASES.get(eff_low, [effective_loc])
        reg, ctry = infer_region_and_country(effective_loc)
        inferred_reg = reg
        if not inferred_country and ctry:
            inferred_country = ctry

    if not inferred_reg and region and region not in ("Global", "All", "All Regions"):
        inferred_reg = region
        if not inferred_country and region in LOCATION_TO_REGION:
            _, inferred_country = LOCATION_TO_REGION[region]

    # Expanded industry keywords
    expanded: List[str] = []
    for k, exps in GENERIC_INDUSTRY_EXPANSIONS.items():
        if re.search(rf"\b{re.escape(k)}\b", topic_low) or re.search(rf"\b{re.escape(k)}\b", low):
            for e in exps:
                if e not in expanded:
                    expanded.append(e)
    if not expanded:
        expanded = [cleaned_topic]

    inferred_sector = (
        industry if industry and industry not in ("All", "All Industries") else infer_standard_sector(topic_low)
    )

    return ParsedQuery(
        raw_query=raw,
        cleaned_topic=cleaned_topic,
        intent=intent,
        location=effective_loc,
        location_aliases=loc_aliases,
        inferred_country=inferred_country,
        inferred_region=inferred_reg or "Global",
        inferred_industry=inferred_sector,
        expanded_keywords=expanded,
        osm_tag_hints=_get_osm_hints(low),
    )
