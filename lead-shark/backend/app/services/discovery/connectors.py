import csv
import io
import urllib.robotparser
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from app.services.deduplication.dedup import normalize_domain

# Per-source allowlist for responsible scraping
ALLOWED_DOMAINS = [
    "example.com", "publicdirectory.org", "techcrunch.com", 
    "openstreetmap.org", "overpass-api.de"
]

def check_robots_txt(target_url: str, user_agent: str = "LeadSharkBot/1.0 (+https://leadshark.io/compliance)") -> bool:
    """
    Checks robots.txt for a website before any requests.
    Respects disallow directives without evasion.
    """
    try:
        parsed = urlparse(target_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, target_url)
    except Exception:
        # Default to safe / permissive if robots.txt unreachable but do not crawl aggressive paths
        return True

DEMO_DISCOVERY_DATABASE = [
    {
        "name": "Sarah Jenkins",
        "title": "VP of Technology",
        "email": "s.jenkins@apexcloud.io",
        "company_name": "Apex Cloud Systems",
        "company_domain": "apexcloud.io",
        "company_website": "https://apexcloud.io",
        "company_phone": "+1-415-555-0199",
        "company_description": "Enterprise cloud infrastructure, container security, and AI workload scaling platforms.",
        "region": "North America",
        "industry": "Information Technology",
        "source_type": "demo",
        "source_url": "https://apexcloud.io/about"
    },
    {
        "name": "Marcus Vance",
        "title": "Head of Operations",
        "email": "m.vance@quantumnex.com",
        "company_name": "Quantum Nexus Logistics",
        "company_domain": "quantumnex.com",
        "company_website": "https://quantumnex.com",
        "company_phone": "+1-312-555-0142",
        "company_description": "Automated supply chain and industrial robotics fulfillment solutions for global retailers.",
        "region": "North America",
        "industry": "Manufacturing & Industrial",
        "source_type": "demo",
        "source_url": "https://quantumnex.com/team"
    },
    {
        "name": "Dr. Elena Rostova",
        "title": "Chief Scientific Officer",
        "email": "elena.rostova@aurorabiopharma.eu",
        "company_name": "Aurora BioPharma",
        "company_domain": "aurorabiopharma.eu",
        "company_website": "https://aurorabiopharma.eu",
        "company_phone": "+44-20-7946-0192",
        "company_description": "Next-generation targeted oncology therapeutics and clinical trial data analytics.",
        "region": "Europe (UK/EU)",
        "industry": "Healthcare & Life Sciences",
        "source_type": "demo",
        "source_url": "https://aurorabiopharma.eu/leadership"
    },
    {
        "name": "David Chen",
        "title": "Chief Financial Officer",
        "email": "dchen@silverpeakcapital.com",
        "company_name": "SilverPeak Capital Partners",
        "company_domain": "silverpeakcapital.com",
        "company_website": "https://silverpeakcapital.com",
        "company_phone": "+1-212-555-0821",
        "company_description": "Private equity and venture growth investments in B2B software and fintech infrastructure.",
        "region": "North America",
        "industry": "Financial Services",
        "source_type": "demo",
        "source_url": "https://silverpeakcapital.com/contact"
    },
    {
        "name": "Chloe Dupont",
        "title": "Director of Growth",
        "email": "c.dupont@lumierestore.fr",
        "company_name": "Lumière Modern Goods",
        "company_domain": "lumierestore.fr",
        "company_website": "https://lumierestore.fr",
        "company_phone": "+33-1-42-68-55-00",
        "company_description": "Sustainable luxury e-commerce brand operating across direct-to-consumer and wholesale retail channels.",
        "region": "Europe (UK/EU)",
        "industry": "Retail & E-Commerce",
        "source_type": "demo",
        "source_url": "https://lumierestore.fr/legal"
    },
    {
        "name": "Vikram Malhotra",
        "title": "Managing Partner",
        "email": "vmalhotra@veritasadvisory.in",
        "company_name": "Veritas Legal & Strategy Advisory",
        "company_domain": "veritasadvisory.in",
        "company_website": "https://veritasadvisory.in",
        "company_phone": "+91-22-6712-4400",
        "company_description": "Corporate governance, cross-border M&A compliance, and DPDP Act legal advisory services.",
        "region": "Asia-Pacific",
        "industry": "Professional & Legal Services",
        "source_type": "demo",
        "source_url": "https://veritasadvisory.in/partners"
    },
    {
        "name": "Hannah Wright",
        "title": "VP of Engineering",
        "email": "hwright@solarisfusion.energy",
        "company_name": "Solaris Fusion Energy",
        "company_domain": "solarisfusion.energy",
        "company_website": "https://solarisfusion.energy",
        "company_phone": "+1-512-555-0761",
        "company_description": "Utility-scale smart grid battery storage systems and microgrid energy management software.",
        "region": "North America",
        "industry": "CleanTech & Energy",
        "source_type": "demo",
        "source_url": "https://solarisfusion.energy/contact"
    },
    {
        "name": "Rajesh Sharma",
        "title": "CTO",
        "email": "rajesh@innovatetech.io",
        "company_name": "InnovateTech Global",
        "company_domain": "innovatetech.io",
        "company_website": "https://innovatetech.io",
        "company_phone": "+91-80-4567-8900",
        "company_description": "AI-driven customer operations workflows and enterprise generative application builders.",
        "region": "Asia-Pacific",
        "industry": "Information Technology",
        "source_type": "demo",
        "source_url": "https://innovatetech.io/company"
    }
]

AMAZON_SYNTHETIC_DEMO_LEADS = [
    {
        "name": "Cloud Solutions Architecture Desk",
        "title": "Solutions Architecture Desk (Synthetic Demo)",
        "email": "aws-solutions-demo@amazon.com",
        "company_name": "Amazon Web Services (AWS) - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://aws.amazon.com",
        "company_phone": "+1-206-266-1000",
        "company_description": "Synthetic demonstrative record: Cloud infrastructure, serverless compute, and enterprise database services.",
        "region": "North America",
        "industry": "Information Technology",
        "source_type": "demo",
        "source_url": "https://aws.amazon.com/contact-us/",
        "lawful_basis_note": "Synthetic Demo Data — AWS Business Unit Prototype (Public Directory Simulation)"
    },
    {
        "name": "Procurement & B2B Operations",
        "title": "Enterprise Accounts Team (Synthetic Demo)",
        "email": "business-b2b-demo@amazon.com",
        "company_name": "Amazon Business B2B - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://business.amazon.com",
        "company_phone": "+1-888-281-3847",
        "company_description": "Synthetic demonstrative record: B2B wholesale marketplace, commercial purchasing, and enterprise supply chain solutions.",
        "region": "North America",
        "industry": "Retail & E-Commerce",
        "source_type": "demo",
        "source_url": "https://business.amazon.com/en/contact-us",
        "lawful_basis_note": "Synthetic Demo Data — Commercial Marketplace Prototype"
    },
    {
        "name": "Robotics & Logistics Engineering",
        "title": "Fulfillment Systems Desk (Synthetic Demo)",
        "email": "robotics-fulfillment-demo@amazon.com",
        "company_name": "Amazon Robotics & Fulfillment - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://aboutamazon.com",
        "company_phone": "+1-206-266-1000",
        "company_description": "Synthetic demonstrative record: Automated material handling, autonomous mobile robots, and warehouse logistics.",
        "region": "North America",
        "industry": "Manufacturing & Industrial",
        "source_type": "demo",
        "source_url": "https://aboutamazon.com/news/operations",
        "lawful_basis_note": "Synthetic Demo Data — Logistics Automation Prototype"
    },
    {
        "name": "Enterprise Advertising Partnerships",
        "title": "Ad Strategy Group (Synthetic Demo)",
        "email": "advertising-ads-demo@amazon.com",
        "company_name": "Amazon Advertising - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://advertising.amazon.com",
        "company_phone": "+1-206-266-1000",
        "company_description": "Synthetic demonstrative record: Retail media ad exchange, sponsored listings, and campaign measurement telemetry.",
        "region": "North America",
        "industry": "Information Technology",
        "source_type": "demo",
        "source_url": "https://advertising.amazon.com/contact",
        "lawful_basis_note": "Synthetic Demo Data — Ad Network Prototype"
    },
    {
        "name": "EMEA Cloud Infrastructure Team",
        "title": "Regional Cloud Team (Synthetic Demo)",
        "email": "aws-emea-cloud-demo@amazon.com",
        "company_name": "Amazon Web Services EMEA - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://aws.amazon.com/local/uk/",
        "company_phone": "+44-20-7084-7000",
        "company_description": "Synthetic demonstrative record: EMEA sovereign cloud architecture, data residency, and GDPR compliance systems.",
        "region": "Europe (UK/EU)",
        "industry": "Information Technology",
        "source_type": "demo",
        "source_url": "https://aws.amazon.com/contact-us/",
        "lawful_basis_note": "Synthetic Demo Data — EMEA Cloud Prototype"
    },
    {
        "name": "APAC Commercial Operations",
        "title": "Regional Enterprise Desk (Synthetic Demo)",
        "email": "apac-commercial-demo@amazon.com",
        "company_name": "Amazon Commercial Operations APAC - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://aboutamazon.in",
        "company_phone": "+91-80-4000-0000",
        "company_description": "Synthetic demonstrative record: APAC regional cross-border commerce, seller ecosystems, and customer logistics.",
        "region": "Asia-Pacific",
        "industry": "Retail & E-Commerce",
        "source_type": "demo",
        "source_url": "https://aboutamazon.in",
        "lawful_basis_note": "Synthetic Demo Data — APAC Operations Prototype"
    },
    {
        "name": "Devices & Hardware Development Lab",
        "title": "Hardware Development Desk (Synthetic Demo)",
        "email": "lab126-hardware-demo@amazon.com",
        "company_name": "Amazon Devices Lab126 - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://amazon.jobs/lab126",
        "company_phone": "+1-408-863-7000",
        "company_description": "Synthetic demonstrative record: Consumer electronics, smart home automation, and connected edge devices.",
        "region": "North America",
        "industry": "Information Technology",
        "source_type": "demo",
        "source_url": "https://amazon.jobs/lab126",
        "lawful_basis_note": "Synthetic Demo Data — Hardware Engineering Prototype"
    },
    {
        "name": "Clean Energy & Sustainability Procurement",
        "title": "Renewable Power Desk (Synthetic Demo)",
        "email": "sustainability-operations-demo@amazon.com",
        "company_name": "Amazon Sustainability & Clean Energy - Demo Entity",
        "company_domain": "amazon.com",
        "company_website": "https://sustainability.aboutamazon.com",
        "company_phone": "+1-206-266-1000",
        "company_description": "Synthetic demonstrative record: Corporate renewable energy power purchase agreements (PPAs) and net-zero carbon operations.",
        "region": "North America",
        "industry": "CleanTech & Energy",
        "source_type": "demo",
        "source_url": "https://sustainability.aboutamazon.com",
        "lawful_basis_note": "Synthetic Demo Data — Sustainability Prototype"
    }
]

class DiscoveryConnector:
    """Base plug-in connector interface for lawful lead discovery"""
    def search(
        self, 
        query: str, 
        region: Optional[str] = None, 
        max_results: int = 50,
        industry: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

class DemoDiscoveryConnector(DiscoveryConnector):
    """Working demo discovery connector with clearly labeled sample leads"""
    def search(
        self, 
        query: str, 
        region: Optional[str] = None, 
        max_results: int = 50,
        industry: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        q = (query or "").lower().strip()
        results = []
        
        # 1. If query specifically targets Amazon, use dedicated synthetic Amazon business unit leads
        if "amazon" in q or "aws" in q:
            target_pool = AMAZON_SYNTHETIC_DEMO_LEADS
        else:
            target_pool = DEMO_DISCOVERY_DATABASE
            
        for item in target_pool:
            # Region filter if specified
            if region and region not in ["Global", "All", "All Regions"] and item.get("region") != region:
                continue
                
            # Industry filter if specified
            if industry and industry not in ["All", "All Industries"] and item.get("industry") != industry:
                continue
                
            match = (
                not q or 
                q in item["company_name"].lower() or 
                q in item["industry"].lower() or 
                q in item["company_description"].lower() or
                q in item["title"].lower() or
                ("amazon" in q and "amazon" in item["company_name"].lower()) or
                ("aws" in q and "aws" in item["company_name"].lower())
            )
            if match:
                res = item.copy()
                res["collected_at"] = datetime.utcnow()
                results.append(res)
                if len(results) >= max_results:
                    break
                    
        # If query was empty and no restrictive filters were applied, return default sample database
        if not q and not results and (not region or region in ["Global", "All"]) and (not industry or industry in ["All", "All Industries"]):
            for item in DEMO_DISCOVERY_DATABASE[:max_results]:
                res = item.copy()
                res["collected_at"] = datetime.utcnow()
                results.append(res)
                
        return results

class OpenStreetMapConnector(DiscoveryConnector):
    """Connector delegating strictly to live OpenStreetMapAdapter (no demo fallback or fabricated emails)"""
    def search(
        self, 
        query: str, 
        region: Optional[str] = None, 
        max_results: int = 50,
        industry: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        from app.services.discovery.adapters import OpenStreetMapAdapter
        from app.services.discovery.query_parser import parse_universal_query

        parsed = parse_universal_query(query, region=region, industry=industry)
        outcome = OpenStreetMapAdapter().search(parsed, max_results=max_results)
        return outcome.records

def parse_csv_leads(content_bytes: bytes) -> List[Dict[str, Any]]:
    """Parse uploaded CSV into standardized raw lead dictionaries"""
    text = content_bytes.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    leads = []
    
    for row in reader:
        # Standardize headers case-insensitively
        row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
        
        email = row_lower.get("email") or row_lower.get("email_address") or row_lower.get("contact_email")
        if not email:
            continue
            
        company_name = (
            row_lower.get("company_name") or 
            row_lower.get("company") or 
            row_lower.get("organization") or 
            email.split("@")[1].split(".")[0].capitalize()
        )
        
        website = row_lower.get("website") or row_lower.get("url") or f"https://{email.split('@')[1]}"
        domain = normalize_domain(website or email.split("@")[1])
        
        leads.append({
            "name": row_lower.get("name") or row_lower.get("contact_name") or row_lower.get("full_name") or "Business Representative",
            "title": row_lower.get("title") or row_lower.get("job_title") or "Executive",
            "email": email.strip().lower(),
            "company_name": company_name,
            "company_domain": domain,
            "company_website": website,
            "company_phone": row_lower.get("phone") or row_lower.get("business_phone"),
            "company_description": row_lower.get("description") or row_lower.get("company_description") or f"Commercial business operations at {domain}",
            "region": row_lower.get("region") or row_lower.get("country") or "North America",
            "industry": row_lower.get("industry") or row_lower.get("sector") or "General Business",
            "source_type": "csv",
            "source_url": "CSV Upload",
            "collected_at": datetime.utcnow(),
            "lawful_basis_note": "Sales Team CSV Import (Pre-existing Opt-in / B2B Listing)"
        })
    return leads
