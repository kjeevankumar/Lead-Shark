import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import engine, Base, SessionLocal, get_db, ensure_schema_columns
from app.core.seed import seed_database
from app.api import auth, discovery, leads, campaigns, compliance, webhooks, analytics, audit

# Ensure database tables & migrated columns exist immediately upon import
Base.metadata.create_all(bind=engine)
ensure_schema_columns()
_seed_db = SessionLocal()
try:
    seed_database(_seed_db)
except Exception as _e:
    print(f"Seed note: {_e}")
finally:
    _seed_db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Lead Shark — Lead Discovery & Compliant Outreach Intelligence Platform",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensures unhandled errors return structured JSON inside CORSMiddleware with proper headers."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server error: {str(exc)}"},
    )

# Public Render Health Check (Strictly NO AUTH required)
@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        # Verify db session
        db.execute(Base.metadata.tables["users"].select().limit(1))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(discovery.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(compliance.router) # includes /unsubscribe/{token} and /api/compliance/...
app.include_router(webhooks.router)   # includes /webhooks/email-events

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
