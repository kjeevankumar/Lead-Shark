import os
import re
import logging
from urllib.parse import quote_plus, unquote
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

db_url = (settings.DATABASE_URL or "").strip().strip('"').strip("'")

# Normalize PostgreSQL protocol and force psycopg2 driver (Option B)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql+psycopg://"):
    db_url = db_url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Guard against accidental HTTP/HTTPS URL (e.g. user pasted Supabase Project/REST URL instead of DB URI)
if db_url.startswith("http://") or db_url.startswith("https://"):
    raise RuntimeError(
        "FATAL DATABASE CONFIGURATION: DATABASE_URL was set to an HTTP/HTTPS URL ("
        f"'{db_url[:24]}...'), which is the Supabase Project/REST API URL, not a PostgreSQL database connection string.\n\n"
        "SQLAlchemy requires a database URI starting with 'postgresql://'.\n\n"
        "HOW TO FIX IN SUPABASE & RENDER:\n"
        "1. Open your Supabase Dashboard -> Select your Project.\n"
        "2. Click 'Project Settings' (gear icon on the left sidebar) -> 'Database'.\n"
        "3. Scroll down to the 'Connection string' section and select the 'URI' tab.\n"
        "4. Copy the connection string, which looks like:\n"
        "   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres\n"
        "5. Replace [YOUR-PASSWORD] with the password you set when creating the Supabase project.\n"
        "6. In Render Dashboard -> Click 'lead-shark-backend' -> 'Environment' -> Update DATABASE_URL and Save Changes."
    )

def _sanitize_postgres_url(url: str) -> str:
    """
    Sanitize PostgreSQL database URLs:
    - Strips literal square brackets [ ... ] if user copied the Supabase placeholder [YOUR-PASSWORD] literally
    - URL-encodes special characters like '@', ':', '#' in passwords to prevent hostname truncation/malformed host errors
    """
    m = re.match(r'^(?P<scheme>[a-zA-Z0-9+_-]+://)(?P<user>[^:]+):(?P<password>.+)@(?P<host>[^/@]+(?::\d+)?(?:/.*)?)$', url)
    if not m:
        return url
    scheme = m.group('scheme')
    user = m.group('user')
    raw_password = m.group('password')
    host_part = m.group('host')

    clean_password = raw_password.strip()
    if clean_password.startswith('[') and clean_password.endswith(']'):
        clean_password = clean_password[1:-1]
    clean_password = clean_password.strip('[]')

    encoded_password = quote_plus(unquote(clean_password))
    return f"{scheme}{user}:{encoded_password}@{host_part}"

if "postgresql" in db_url:
    db_url = _sanitize_postgres_url(db_url)

# Enforce PostgreSQL in production - prevent silent SQLite fallback
if settings.ENVIRONMENT == "production" and db_url.startswith("sqlite"):
    raise RuntimeError(
        "FATAL PRODUCTION CONFIGURATION: DATABASE_URL must be configured with a production "
        "PostgreSQL database (e.g. Supabase), not SQLite. Please set DATABASE_URL in Render environment settings."
    )

engine_kwargs = {}
if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Supabase PostgreSQL connection pooler optimizations
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
