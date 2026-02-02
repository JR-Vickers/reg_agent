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
    PriorityRegulation,
    TaskResponse, TaskUpdate,
)
from src.agents.monitor.fincen import ingest_new_documents as ingest_fincen
from src.agents.monitor.federal_register import ingest_new_documents as ingest_federal_register
from src.agents.monitor.sec import ingest_new_documents as ingest_sec

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
        count = ingest_fincen()
        logger.info(f"Scheduled scrape complete: {count} new documents")
    except Exception as e:
        logger.error(f"Scheduled FinCEN scrape failed: {e}")


def run_federal_register_scraper():
    """Wrapper to run the Federal Register scraper with error handling."""
    try:
        logger.info("Running scheduled Federal Register scrape")
        count = ingest_federal_register()
        logger.info(f"Scheduled Federal Register scrape complete: {count} new documents")
    except Exception as e:
        logger.error(f"Scheduled Federal Register scrape failed: {e}")


def run_sec_scraper():
    """Wrapper to run the SEC scraper with error handling."""
    try:
        logger.info("Running scheduled SEC scrape")
        count = ingest_sec()
        logger.info(f"Scheduled SEC scrape complete: {count} new documents")
    except Exception as e:
        logger.error(f"Scheduled SEC scrape failed: {e}")


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
    schedule.every(24).hours.do(run_federal_register_scraper)
    schedule.every(24).hours.do(run_sec_scraper)
    scheduler_running = True
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("FinCEN scraper scheduled every 30 minutes, Federal Register and SEC every 24 hours")

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

        counts = client.get_regulation_counts()
        total_count = counts["total"]
        source_counts = counts["by_source"]
        available_sources = set(source_counts.keys())

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
        count = ingest_fincen()
        return {"status": "ok", "new_documents": count}
    except Exception as e:
        logger.error(f"Manual FinCEN scrape failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape/federal-register")
def trigger_federal_register_scrape(backfill_months: int = 0):
    """Manually trigger a Federal Register scrape. Set backfill_months > 0 for historical data."""
    try:
        if backfill_months > 0:
            from src.agents.monitor.federal_register import backfill
            count = backfill(months=backfill_months)
        else:
            count = ingest_federal_register()
        return {"status": "ok", "new_documents": count}
    except Exception as e:
        logger.error(f"Federal Register scrape failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape/sec")
def trigger_sec_scrape(backfill_days: int = 30):
    """Manually trigger an SEC scrape. Set backfill_days for historical data (default 30)."""
    try:
        if backfill_days > 30:
            from src.agents.monitor.sec import backfill
            count = backfill(days=backfill_days)
        else:
            count = ingest_sec(days_back=backfill_days)
        return {"status": "ok", "new_documents": count}
    except Exception as e:
        logger.error(f"SEC scrape failed: {e}")
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
    from src.agents.classify.pipeline import classify_and_store

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

    classify_and_store(
        regulation_id=reg_uuid,
        title=regulation["title"],
        source=regulation.get("source", "unknown"),
        published_date=str(regulation.get("published_date", "")),
        content=regulation.get("content", regulation["title"]),
    )

    data = client.get_classification(reg_uuid)
    return ClassificationResponse(**data)


@app.post("/api/gap-analysis/backfill")
def backfill_gap_analyses(
    limit: int = 10,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Run gap analysis on classified regulations that meet threshold but lack analysis."""
    from src.agents.classify.pipeline import _trigger_gap_analysis

    pending = client.get_classifications_needing_gap_analysis(limit=limit)

    results = {"processed": 0, "succeeded": 0, "failed": 0, "details": []}

    for row in pending:
        reg = row.get("regulations", {})
        if not reg:
            continue

        results["processed"] += 1
        title = reg.get("title", "Unknown")

        success = _trigger_gap_analysis(
            regulation_id=row["regulation_id"],
            title=title,
            source=reg.get("source", "unknown"),
            published_date=str(reg.get("published_date", "")),
            content=reg.get("content", title),
            classification_reasoning=row.get("classification_reasoning", ""),
            relevance_score=row["relevance_score"],
            bsa_pillars=row.get("bsa_pillars", []),
            categories=row.get("categories", {}).get("labels", []),
        )

        if success:
            results["succeeded"] += 1
            results["details"].append({"regulation_id": row["regulation_id"], "title": title[:50], "status": "success"})
        else:
            results["failed"] += 1
            results["details"].append({"regulation_id": row["regulation_id"], "title": title[:50], "status": "failed"})

    return results


@app.post("/api/gap-analysis/{regulation_id}", response_model=GapAnalysisResponse)
def run_gap_analysis(
    regulation_id: str,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Run gap analysis on a classified regulation using GPT-4o."""
    from uuid import UUID as _UUID
    from src.agents.assess.client import analyze_gaps
    from src.models.document import GapAnalysisCreate, GapSeverity

    try:
        reg_uuid = _UUID(regulation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid regulation ID format")

    regulation = client.get_regulation(reg_uuid)
    if not regulation:
        raise HTTPException(status_code=404, detail="Regulation not found")

    classification = client.get_classification(reg_uuid)
    if not classification:
        raise HTTPException(
            status_code=400,
            detail="Regulation must be classified before gap analysis. Call POST /api/classify/{id} first."
        )

    if classification["relevance_score"] < 3 or classification["confidence"] < 0.7:
        raise HTTPException(
            status_code=400,
            detail=f"Regulation does not meet threshold for gap analysis (relevance >= 3 AND confidence >= 0.7). Current: relevance={classification['relevance_score']}, confidence={classification['confidence']}"
        )

    existing = client.get_gap_analysis(reg_uuid)
    if existing:
        return GapAnalysisResponse(**existing)

    result = analyze_gaps(
        title=regulation["title"],
        source=regulation.get("source", "unknown"),
        published_date=str(regulation.get("published_date", "")),
        content=regulation.get("content", regulation["title"]),
        classification_reasoning=classification.get("classification_reasoning", ""),
        relevance_score=classification["relevance_score"],
        bsa_pillars=classification.get("bsa_pillars", []),
        categories=classification.get("categories", []),
    )

    gap_create = GapAnalysisCreate(
        regulation_id=reg_uuid,
        affected_controls={"controls": [g.model_dump() for g in result.affected_controls]},
        gap_severity=GapSeverity(result.overall_severity),
        remediation_effort_hours=result.total_effort_hours if result.total_effort_hours > 0 else None,
        analysis_summary=result.summary,
        recommendations={"reasoning": result.reasoning},
        model_used="gpt-4o",
    )

    data = client.create_gap_analysis(gap_create)
    return GapAnalysisResponse(**data)


# Task endpoints

@app.post("/api/tasks/generate/{gap_analysis_id}")
def generate_tasks_for_gap_analysis(
    gap_analysis_id: str,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Generate tasks from a gap analysis."""
    from uuid import UUID as _UUID
    from src.agents.route import generate_tasks_from_gap_analysis

    try:
        gap_uuid = _UUID(gap_analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gap analysis ID format")

    gap_analysis = client.get_gap_analysis_by_id(gap_uuid)
    if not gap_analysis:
        raise HTTPException(status_code=404, detail="Gap analysis not found")

    existing_tasks = client.get_tasks_by_gap_analysis(gap_uuid)
    if existing_tasks:
        return {
            "status": "already_exists",
            "message": f"Tasks already generated for this gap analysis",
            "task_count": len(existing_tasks),
            "tasks": [TaskResponse(**t) for t in existing_tasks]
        }

    regulation = client.get_regulation(gap_analysis["regulation_id"])
    if not regulation:
        raise HTTPException(status_code=404, detail="Regulation not found")

    affected_controls = gap_analysis.get("affected_controls", {}).get("controls", [])

    tasks = generate_tasks_from_gap_analysis(
        regulation_id=gap_analysis["regulation_id"],
        gap_analysis_id=gap_uuid,
        gap_severity=gap_analysis["gap_severity"],
        affected_controls=affected_controls,
        regulation_title=regulation["title"],
    )

    created_tasks = []
    for task in tasks:
        data = client.create_task(task)
        created_tasks.append(TaskResponse(**data))

    return {
        "status": "created",
        "task_count": len(created_tasks),
        "tasks": created_tasks
    }


@app.get("/api/tasks", response_model=List[TaskResponse])
def get_tasks(
    status: str = None,
    assigned_team: str = None,
    priority: str = None,
    limit: int = 50,
    offset: int = 0,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Get tasks with optional filtering."""
    try:
        data = client.get_tasks(
            status=status,
            assigned_team=assigned_team,
            priority=priority,
            limit=limit,
            offset=offset
        )
        return [TaskResponse(**item) for item in data]

    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/tasks/teams")
def get_teams():
    """Get list of valid teams for task assignment."""
    from src.agents.route import VALID_TEAMS
    return {"teams": VALID_TEAMS}


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Get a single task by ID."""
    from uuid import UUID as _UUID

    try:
        task_uuid = _UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    task = client.get_task(task_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task)


@app.patch("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    update: TaskUpdate,
    client: SupabaseClient = Depends(get_supabase_client)
):
    """Update a task (status, team, priority, due date)."""
    from uuid import UUID as _UUID

    try:
        task_uuid = _UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    existing = client.get_task(task_uuid)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        data = client.update_task(task_uuid, update)
        return TaskResponse(**data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))