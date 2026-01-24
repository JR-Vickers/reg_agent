"""Run classifier against labeled test cases and produce evaluation metrics."""

import logging
import time
from typing import List, Tuple

from src.database.client import get_supabase_client
from src.agents.classify.client import classify_document
from src.evaluation.loader import load_test_data, TestCase
from src.evaluation.metrics import (
    PredictedClassification,
    evaluate_classification,
    generate_report,
    generate_error_analysis,
    EvaluationReport,
)

logger = logging.getLogger(__name__)


def run_evaluation() -> Tuple[EvaluationReport, List[dict]]:
    db = get_supabase_client()
    dataset = load_test_data()

    predictions: List[PredictedClassification] = []
    skipped: List[dict] = []
    valid_cases: List[TestCase] = []

    total = len(dataset.test_cases)
    start_time = time.time()

    for i, tc in enumerate(dataset.test_cases, 1):
        regulation = db.get_regulation_by_document_id(tc.document_id)
        if not regulation:
            logger.warning(f"Skipping {tc.document_id}: not found in DB")
            skipped.append({"document_id": tc.document_id, "reason": "not_in_db"})
            continue

        logger.info(f"[{i}/{total}] Classifying: {tc.document_id}")

        try:
            result = classify_document(
                title=regulation["title"],
                source=regulation.get("source", "unknown"),
                published_date=str(regulation.get("published_date", "")),
                content=regulation.get("content", regulation["title"]),
            )

            predictions.append(PredictedClassification(
                relevance_score=result.relevance_score,
                confidence=result.confidence,
                bsa_pillars=result.bsa_pillars,
                categories=result.categories,
                requires_human_review=result.requires_human_review,
            ))
            valid_cases.append(tc)

        except Exception as e:
            logger.error(f"Error classifying {tc.document_id}: {e}")
            skipped.append({"document_id": tc.document_id, "reason": str(e)})

    elapsed = time.time() - start_time

    if not valid_cases:
        raise RuntimeError("No test cases could be evaluated — check DB contents")

    report = evaluate_classification(valid_cases, predictions)

    logger.info(
        f"Evaluation complete: {len(valid_cases)} cases in {elapsed:.1f}s "
        f"({len(skipped)} skipped)"
    )

    return report, skipped


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    report, skipped = run_evaluation()

    print(generate_report(report))
    print()
    print(generate_error_analysis(report))

    if skipped:
        print(f"\nSkipped {len(skipped)} cases:")
        for s in skipped:
            print(f"  {s['document_id']}: {s['reason']}")
