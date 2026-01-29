"""Classify-and-store pipeline: classifies a regulation and writes to DB."""

import logging
from uuid import UUID

from src.database.client import get_supabase_client
from src.agents.classify.client import classify_document
from src.models.document import ClassificationCreate, RelevanceScore, BSAPillar

logger = logging.getLogger(__name__)

GAP_ANALYSIS_RELEVANCE_THRESHOLD = 3
GAP_ANALYSIS_CONFIDENCE_THRESHOLD = 0.7


def classify_and_store(regulation_id: UUID, title: str, source: str, published_date: str, content: str) -> bool:
    db = get_supabase_client()

    existing = db.get_classification(regulation_id)
    if existing:
        logger.debug(f"Classification already exists for {regulation_id}, skipping API call")
        return False

    result = classify_document(
        title=title,
        source=source,
        published_date=published_date,
        content=content,
    )

    classification = ClassificationCreate(
        regulation_id=regulation_id,
        relevance_score=RelevanceScore(result.relevance_score),
        confidence=result.confidence,
        bsa_pillars=[BSAPillar(p) for p in result.bsa_pillars],
        categories={"labels": result.categories},
        classification_reasoning=result.reasoning,
        model_used="gpt-4o-mini",
    )

    db.create_classification(classification)
    logger.info(f"Classified '{title[:50]}': relevance={result.relevance_score}")

    if result.relevance_score >= GAP_ANALYSIS_RELEVANCE_THRESHOLD and result.confidence >= GAP_ANALYSIS_CONFIDENCE_THRESHOLD:
        _trigger_gap_analysis(
            regulation_id=regulation_id,
            title=title,
            source=source,
            published_date=published_date,
            content=content,
            classification_reasoning=result.reasoning,
            relevance_score=result.relevance_score,
            bsa_pillars=result.bsa_pillars,
            categories=result.categories,
        )

    return True


def _trigger_gap_analysis(
    regulation_id: UUID,
    title: str,
    source: str,
    published_date: str,
    content: str,
    classification_reasoning: str,
    relevance_score: int,
    bsa_pillars: list,
    categories: list,
) -> bool:
    from src.agents.assess.client import analyze_gaps
    from src.models.document import GapAnalysisCreate, GapSeverity

    db = get_supabase_client()

    existing = db.get_gap_analysis(regulation_id)
    if existing:
        logger.debug(f"Gap analysis already exists for {regulation_id}, skipping")
        return False

    logger.info(f"Auto-triggering gap analysis for '{title[:50]}' (relevance={relevance_score})")

    try:
        result = analyze_gaps(
            title=title,
            source=source,
            published_date=published_date,
            content=content,
            classification_reasoning=classification_reasoning,
            relevance_score=relevance_score,
            bsa_pillars=bsa_pillars,
            categories=categories,
        )

        gap_create = GapAnalysisCreate(
            regulation_id=regulation_id,
            affected_controls={"controls": [g.model_dump() for g in result.affected_controls]},
            gap_severity=GapSeverity(result.overall_severity),
            remediation_effort_hours=result.total_effort_hours if result.total_effort_hours > 0 else None,
            analysis_summary=result.summary,
            recommendations={"reasoning": result.reasoning},
            model_used="gpt-4o",
        )

        data = db.create_gap_analysis(gap_create)
        logger.info(f"Gap analysis complete for '{title[:50]}': severity={result.overall_severity}, controls={len(result.affected_controls)}")

        _trigger_task_generation(
            gap_analysis_id=data["id"],
            regulation_id=regulation_id,
            gap_severity=result.overall_severity,
            affected_controls=[g.model_dump() for g in result.affected_controls],
            regulation_title=title,
        )

        return True

    except Exception as e:
        logger.error(f"Gap analysis failed for {regulation_id}: {e}")
        return False


def _trigger_task_generation(
    gap_analysis_id: str,
    regulation_id: UUID,
    gap_severity: str,
    affected_controls: list,
    regulation_title: str,
) -> bool:
    from src.agents.route import generate_tasks_from_gap_analysis

    db = get_supabase_client()

    existing = db.get_tasks_by_gap_analysis(gap_analysis_id)
    if existing:
        logger.debug(f"Tasks already exist for gap analysis {gap_analysis_id}, skipping")
        return False

    logger.info(f"Auto-generating tasks for '{regulation_title[:50]}'")

    try:
        tasks = generate_tasks_from_gap_analysis(
            regulation_id=regulation_id,
            gap_analysis_id=gap_analysis_id,
            gap_severity=gap_severity,
            affected_controls=affected_controls,
            regulation_title=regulation_title,
        )

        for task in tasks:
            db.create_task(task)

        logger.info(f"Created {len(tasks)} tasks for '{regulation_title[:50]}'")
        return True

    except Exception as e:
        logger.error(f"Task generation failed for gap analysis {gap_analysis_id}: {e}")
        return False
