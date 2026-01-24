"""Classify-and-store pipeline: classifies a regulation and writes to DB."""

import logging
from uuid import UUID

from src.database.client import get_supabase_client
from src.agents.classify.client import classify_document
from src.models.document import ClassificationCreate, RelevanceScore, BSAPillar

logger = logging.getLogger(__name__)


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
    return True
