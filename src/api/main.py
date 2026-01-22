"""
FastAPI application for regulatory intelligence system.
Provides REST API for document ingestion, classification, and gap analysis.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config.settings import settings, get_log_config
from src.database.connection import init_database, close_database
from src.database.client import get_supabase_client, SupabaseClient
from src.models.document import (
    RegulationResponse, RegulationCreate,
    ClassificationResponse, ClassificationCreate,
    GapAnalysisResponse, GapAnalysisCreate,
    PriorityRegulation
)

# Configure logging
logging.config.dictConfig(get_log_config())
logger = logging.getLogger(__name__)

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Regulatory Intelligence Agent")
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Regulatory Intelligence Agent")
    await close_database()


app = FastAPI(
    title="Regulatory Intelligence Agent",
    description="Agentic system for BSA/AML compliance monitoring",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Regulatory Intelligence Agent is running!",
        "status": "healthy",
        "environment": settings.env,
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    """Detailed health check with database connectivity."""
    try:
        client = get_supabase_client()
        result = client.client.table("regulations").select("id").limit(1).execute()
        db_status = f"connected ({len(result.data)} row returned)"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        db_status = f"error: {str(e)[:100]}"

    return {
        "status": "ok",
        "service": "reg-agent",
        "version": "0.1.0",
        "environment": settings.env,
        "database": db_status
    }


# Regulation endpoints

@app.post("/api/regulations", response_model=RegulationResponse)
async def create_regulation(
    regulation: RegulationCreate,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Create a new regulation document."""
    try:
        # Check for duplicates
        exists = client.regulation_exists(regulation.source, regulation.document_id)
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Regulation with this source and document_id already exists"
            )

        data = client.create_regulation(regulation)
        return RegulationResponse(**data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating regulation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/regulations", response_model=List[RegulationResponse])
async def get_regulations(
    source: str = None,
    limit: int = 50,
    offset: int = 0,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Get regulations with optional filtering."""
    try:
        data = client.get_regulations(source=source, limit=limit, offset=offset)
        return [RegulationResponse(**item) for item in data]

    except Exception as e:
        logger.error(f"Error fetching regulations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/regulations/recent", response_model=List[dict])
async def get_recent_regulations(
    days: int = 90,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Get recent regulations with classification data."""
    try:
        data = client.get_recent_regulations(days=days)
        return data

    except Exception as e:
        logger.error(f"Error fetching recent regulations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/regulations/priority", response_model=List[PriorityRegulation])
async def get_priority_regulations(
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Get high-priority regulations requiring attention."""
    try:
        data = client.get_priority_regulations()
        return [PriorityRegulation(**item) for item in data]

    except Exception as e:
        logger.error(f"Error fetching priority regulations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Classification endpoints

@app.post("/api/classifications", response_model=ClassificationResponse)
async def create_classification(
    classification: ClassificationCreate,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Create a new classification for a regulation."""
    try:
        data = client.create_classification(classification)
        return ClassificationResponse(**data)

    except Exception as e:
        logger.error(f"Error creating classification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Gap Analysis endpoints

@app.post("/api/gap-analyses", response_model=GapAnalysisResponse)
async def create_gap_analysis(
    gap_analysis: GapAnalysisCreate,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Create a new gap analysis for a regulation."""
    try:
        data = client.create_gap_analysis(gap_analysis)
        return GapAnalysisResponse(**data)

    except Exception as e:
        logger.error(f"Error creating gap analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Dashboard

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    source: str = None,
    limit: int = 50,
    offset: int = 0,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Render the document dashboard."""
    try:
        regulations = client.get_regulations(source=source, limit=limit + 1, offset=offset)
        has_more = len(regulations) > limit
        regulations = regulations[:limit]

        all_regs = client.get_regulations(limit=1000)
        total_count = len(all_regs)
        source_counts = {}
        available_sources = set()
        for reg in all_regs:
            src = reg.get("source", "unknown")
            available_sources.add(src)
            source_counts[src] = source_counts.get(src, 0) + 1

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "regulations": regulations,
            "total_count": total_count,
            "source_counts": source_counts,
            "available_sources": sorted(available_sources),
            "current_source": source,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        })

    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")