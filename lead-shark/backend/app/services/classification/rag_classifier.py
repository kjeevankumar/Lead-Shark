import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Sector classification keyword dictionary for transparent fallback
SECTOR_KEYWORDS = {
    "Information Technology": [
        "software", "cloud", "saas", "api", "ai", "machine learning", "devops",
        "cybersecurity", "analytics", "it services", "web development", "mobile app"
    ],
    "Financial Services": [
        "fintech", "banking", "investment", "wealth", "lending", "insurance",
        "capital", "payment", "crypto", "trading", "equity", "accounting"
    ],
    "Healthcare & Life Sciences": [
        "biotech", "medical", "hospital", "pharma", "clinical", "health",
        "telemedicine", "diagnostic", "therapeutics", "care", "wellness"
    ],
    "Manufacturing & Industrial": [
        "manufacturing", "factory", "machinery", "automotive", "assembly",
        "logistics", "supply chain", "warehousing", "hardware", "aerospace"
    ],
    "Retail & E-Commerce": [
        "ecommerce", "e-commerce", "retail", "consumer", "apparel", "store",
        "marketplace", "dtc", "b2c", "wholesale", "merchandise"
    ],
    "Professional & Legal Services": [
        "consulting", "legal", "law", "advisory", "staffing", "recruitment",
        "compliance", "audit", "management consulting", "pr", "marketing agency"
    ],
    "CleanTech & Energy": [
        "solar", "renewable", "energy", "cleantech", "sustainability", "battery",
        "carbon", "green", "power", "grid"
    ]
}

def classify_lead_with_rag(
    company_name: str,
    website: Optional[str] = None,
    description: Optional[str] = None,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify a lead into an industry sector using the external RAG Lead Segregation Agent,
    or a transparent local classification engine when the external agent is not configured or fails.
    """
    payload = {
        "company_name": company_name or "",
        "website": website or "",
        "description": description or "",
        "email": email or ""
    }
    
    # Try calling the external RAG agent if configured
    if settings.RAG_AGENT_URL:
        target_url = settings.RAG_AGENT_URL.rstrip("/")
        if not target_url.endswith("/classify"):
            target_url = f"{target_url}/api/leads/classify"
            
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.post(target_url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "sector": data.get("sector", "General Business"),
                        "confidence": float(data.get("confidence", 0.90)),
                        "reason": data.get("reason", "Classified by external RAG Lead Segregation Agent"),
                        "source": "rag_agent",
                        "needs_review": float(data.get("confidence", 0.90)) < 0.75
                    }
        except Exception as e:
            logger.warning(f"RAG Lead Segregation Agent call failed, using demo fallback: {e}")
            
    # Transparent Fallback Classifier
    text_corpus = f"{company_name} {website or ''} {description or ''}".lower()
    
    best_sector = "General Business"
    highest_score = 0
    matched_keywords = []
    
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = 0
        matches = []
        for kw in keywords:
            if kw in text_corpus:
                score += 1
                matches.append(kw)
        if score > highest_score:
            highest_score = score
            best_sector = sector
            matched_keywords = matches
            
    if highest_score >= 3:
        confidence = 0.92
        reason = f"High-confidence match on keywords: {', '.join(matched_keywords[:3])}"
        needs_review = False
    elif highest_score >= 1:
        confidence = 0.78
        reason = f"Identified sector keywords: {', '.join(matched_keywords)}"
        needs_review = False
    else:
        confidence = 0.55
        best_sector = "Needs Review"
        reason = "Insufficient company description context for automated classification"
        needs_review = True
        
    return {
        "sector": best_sector,
        "confidence": confidence,
        "reason": f"[Demo Fallback Engine] {reason}",
        "source": "demo_classification",
        "needs_review": needs_review
    }
