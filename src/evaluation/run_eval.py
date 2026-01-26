"""Run classifier against labeled test cases and produce evaluation metrics."""

import logging
import time
from typing import List, Tuple

from src.database.client import get_supabase_client
from src.agents.classify.client import classify_documents_batch, DocumentInput
from src.evaluation.loader import load_test_data, TestCase
from src.evaluation.metrics import (
    PredictedClassification,
    evaluate_classification,
    generate_report,
    generate_error_analysis,
    EvaluationReport,
)

logger = logging.getLogger(__name__)


def run_evaluation(max_workers: int = 10) -> Tuple[EvaluationReport, List[dict]]:
    db = get_supabase_client()
    dataset = load_test_data()

    skipped: List[dict] = []
    documents: List[DocumentInput] = []
    test_case_map: dict[str, TestCase] = {}

    for tc in dataset.test_cases:
        regulation = db.get_regulation_by_document_id(tc.document_id)
        if not regulation:
            logger.warning(f"Skipping {tc.document_id}: not found in DB")
            skipped.append({"document_id": tc.document_id, "reason": "not_in_db"})
            continue

        documents.append(DocumentInput(
            id=tc.document_id,
            title=regulation["title"],
            source=regulation.get("source", "unknown"),
            published_date=str(regulation.get("published_date", "")),
            content=regulation.get("content", regulation["title"]),
        ))
        test_case_map[tc.document_id] = tc

    logger.info(f"Classifying {len(documents)} documents with {max_workers} workers...")
    start_time = time.time()

    batch_results = classify_documents_batch(documents, max_workers=max_workers)

    elapsed = time.time() - start_time

    predictions: List[PredictedClassification] = []
    valid_cases: List[TestCase] = []

    for br in batch_results:
        if br.error:
            skipped.append({"document_id": br.id, "reason": br.error})
            continue

        predictions.append(PredictedClassification(
            relevance_score=br.result.relevance_score,
            confidence=br.result.confidence,
            bsa_pillars=br.result.bsa_pillars,
            categories=br.result.categories,
            requires_human_review=br.result.requires_human_review,
        ))
        valid_cases.append(test_case_map[br.id])

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
