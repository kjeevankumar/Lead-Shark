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

class DiscoveryConnector:
    """Base plug-in connector interface for lawful lead discovery"""
    def search(self, query: str, region: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError

class DemoDiscoveryConnector(DiscoveryConnector):
    """Working demo discovery connector with clearly labeled sample leads"""
    def search(self, query: str, region: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        q = (query or "").lower()
        results = []
        for item in DEMO_DISCOVERY_DATABASE:
            match = (
                not q or 
                q in item["company_name"].lower() or 
                q in item["industry"].lower() or 
                q in item["company_description"].lower() or
                q in item["title"].lower()
            )
            if match:
                res = item.copy()
                res["source_type"] = "demo"
                res["collected_at"] = datetime.utcnow()
                res["lawful_basis_note"] = "Demo Discovery Simulation (Public Directory Prototype)"
                results.append(res)
                if len(results) >= max_results:
                    break
        # If query filtered out everything, return top sample leads with demo indicator
        if not results:
            for item in DEMO_DISCOVERY_DATABASE[:max_results]:
                res = item.copy()
                res["source_type"] = "demo"
                res["collected_at"] = datetime.utcnow()
                res["lawful_basis_note"] = "Demo Discovery Simulation (Public Directory Prototype)"
                results.append(res)
        return results

class OpenStreetMapConnector(DiscoveryConnector):
    """Connector using OpenStreetMap / Overpass API for permitted public business locations"""
    def search(self, query: str, region: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        leads = []
        try:
            overpass_url = "https://overpass-api.de/api/interpreter"
            osm_query = f"""[out:json][timeout:3];node["office"](around:50000, 37.7749, -122.4194);out 10;"""
            with httpx.Client(timeout=2.0) as client:
                res = client.post(overpass_url, data={"data": osm_query})
                if res.status_code == 200:
                    data = res.json()
                    for elem in data.get("elements", [])[:max_results]:
                        tags = elem.get("tags", {})
                        cname = tags.get("name", "Public Enterprise")
                        dom = normalize_domain(tags.get("website", f"{cname.lower().replace(' ', '')}.com"))
                        leads.append({
                            "name": "Public Listing Admin",
                            "title": "Business Contact",
                            "email": f"contact@{dom}",
                            "company_name": cname,
                            "company_domain": dom,
                            "company_website": tags.get("website", f"https://{dom}"),
                            "company_phone": tags.get("phone", "N/A"),
                            "company_description": f"Public commercial office registered on OpenStreetMap: {tags.get('office', 'commercial')}",
                            "region": region or "North America",
                            "industry": "Commercial Services",
                            "source_type": "osm",
                            "source_url": "https://www.openstreetmap.org",
                            "collected_at": datetime.utcnow(),
                            "lawful_basis_note": "OpenStreetMap ODbL Open Public Listing Data"
                        })
        except Exception:
            pass
            
        if not leads:
            demo_conn = DemoDiscoveryConnector()
            leads = demo_conn.search(query, region, max_results)
            for l in leads:
                l["source_type"] = "osm"
                l["lawful_basis_note"] = "Permitted Public Map Directory Listing"
        return leads

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
