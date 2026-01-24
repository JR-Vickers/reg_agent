"""
FastAPI application for regulatory intelligence system.
Provides REST API for document ingestion, classification, and gap analysis.
"""
import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import schedule
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
    PriorityRegulation, RelevanceScore, BSAPillar
)
from src.agents.monitor.fincen import ingest_new_documents

# Configure logging
logging.config.dictConfig(get_log_config())
logger = logging.getLogger(__name__)

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Scheduler state
scheduler_running = False


def run_scheduler():
    """Run the schedule loop in a background thread."""
    global scheduler_running
    while scheduler_running:
        schedule.run_pending()
        time.sleep(60)


def run_fincen_scraper():
    """Wrapper to run the FinCEN scraper with error handling."""
    try:
        logger.info("Running scheduled FinCEN scrape")
        count = ingest_new_documents()
        logger.info(f"Scheduled scrape complete: {count} new documents")
    except Exception as e:
        logger.error(f"Scheduled FinCEN scrape failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global scheduler_running

    # Startup
    logger.info("Starting Regulatory Intelligence Agent")
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

    # Start scheduler
    schedule.every(30).minutes.do(run_fincen_scraper)
    scheduler_running = True
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("FinCEN scraper scheduled to run every 30 minutes")

    yield

    # Shutdown
    logger.info("Shutting down Regulatory Intelligence Agent")
    scheduler_running = False
    schedule.clear()
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


@app.post("/api/scrape/fincen")
def trigger_fincen_scrape():
    """Manually trigger a FinCEN scrape."""
    try:
        count = ingest_new_documents()
        return {"status": "ok", "new_documents": count}
    except Exception as e:
        logger.error(f"Manual FinCEN scrape failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/evaluate")
def run_evaluation_endpoint():
    """Run classifier against labeled test cases and return metrics."""
    from src.evaluation.run_eval import run_evaluation
    from src.evaluation.metrics import generate_report

    try:
        report, skipped = run_evaluation()
        return {
            "status": "ok",
            "total_cases": report.total_cases,
            "skipped": len(skipped),
            "relevance": {
                "mae": round(report.relevance.mae, 3),
                "rmse": round(report.relevance.rmse, 3),
                "tier_accuracy": round(report.relevance.tier_accuracy, 3),
                "exact_accuracy": round(report.relevance.exact_accuracy, 3),
            },
            "pillars": {
                "precision": round(report.pillars.precision, 3),
                "recall": round(report.pillars.recall, 3),
                "f1": round(report.pillars.f1, 3),
            },
            "categories": {
                "precision": round(report.categories.precision, 3),
                "recall": round(report.categories.recall, 3),
                "f1": round(report.categories.f1, 3),
            },
            "calibration": {
                "brier_score": round(report.calibration.brier_score, 3),
                "calibration_error": round(report.calibration.calibration_error, 3),
                "human_review_accuracy": round(report.calibration.human_review_accuracy, 3),
            },
            "details": report.details,
            "skipped_cases": skipped,
            "report_text": generate_report(report),
        }
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/classify/{regulation_id}", response_model=ClassificationResponse)
def classify_regulation(
    regulation_id: str,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Classify a regulation document using GPT-4o-mini."""
    from uuid import UUID as _UUID
    from src.agents.classify.client import classify_document

    try:
        reg_uuid = _UUID(regulation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid regulation ID format")

    regulation = client.get_regulation(reg_uuid)
    if not regulation:
        raise HTTPException(status_code=404, detail="Regulation not found")

    existing = client.get_classification(reg_uuid)
    if existing:
        return ClassificationResponse(**existing)

    result = classify_document(
        title=regulation["title"],
        source=regulation.get("source", "unknown"),
        published_date=str(regulation.get("published_date", "")),
        content=regulation.get("content", regulation["title"]),
    )

    classification = ClassificationCreate(
        regulation_id=reg_uuid,
        relevance_score=RelevanceScore(result.relevance_score),
        confidence=result.confidence,
        bsa_pillars=[BSAPillar(p) for p in result.bsa_pillars],
        categories={"labels": result.categories},
        classification_reasoning=result.reasoning,
        model_used="gpt-4o-mini",
    )

    data = client.create_classification(classification)
    return ClassificationResponse(**data)