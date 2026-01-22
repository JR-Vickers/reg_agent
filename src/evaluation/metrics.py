"""Evaluation metrics for classification performance."""

from dataclasses import dataclass
from typing import List, Dict, Set, Any
import math

from src.evaluation.loader import TestCase


@dataclass
class MultiLabelScores:
    """Precision/recall/F1 for multi-label classification."""
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


@dataclass
class RelevanceScores:
    """Scores for relevance prediction."""
    mae: float
    rmse: float
    tier_accuracy: float
    exact_accuracy: float


@dataclass
class CalibrationScores:
    """Confidence calibration metrics."""
    brier_score: float
    calibration_error: float
    human_review_accuracy: float


@dataclass
class EvaluationReport:
    """Complete evaluation results."""
    relevance: RelevanceScores
    pillars: MultiLabelScores
    categories: MultiLabelScores
    calibration: CalibrationScores
    total_cases: int
    details: List[Dict[str, Any]]


def _relevance_to_tier(score: int) -> str:
    """Convert 0-5 score to tier (low/medium/high)."""
    if score <= 1:
        return "low"
    elif score <= 3:
        return "medium"
    else:
        return "high"


def score_relevance(
    predictions: List[int],
    expected: List[int]
) -> RelevanceScores:
    """Calculate relevance prediction metrics."""
    if len(predictions) != len(expected):
        raise ValueError("Prediction and expected lists must have same length")

    n = len(predictions)
    if n == 0:
        return RelevanceScores(mae=0, rmse=0, tier_accuracy=0, exact_accuracy=0)

    abs_errors = [abs(p - e) for p, e in zip(predictions, expected)]
    squared_errors = [(p - e) ** 2 for p, e in zip(predictions, expected)]

    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(squared_errors) / n)

    exact_matches = sum(1 for p, e in zip(predictions, expected) if p == e)
    exact_accuracy = exact_matches / n

    tier_matches = sum(
        1 for p, e in zip(predictions, expected)
        if _relevance_to_tier(p) == _relevance_to_tier(e)
    )
    tier_accuracy = tier_matches / n

    return RelevanceScores(
        mae=mae,
        rmse=rmse,
        tier_accuracy=tier_accuracy,
        exact_accuracy=exact_accuracy
    )


def score_multilabel(
    predictions: List[Set[str]],
    expected: List[Set[str]]
) -> MultiLabelScores:
    """Calculate precision/recall/F1 for multi-label predictions."""
    if len(predictions) != len(expected):
        raise ValueError("Prediction and expected lists must have same length")

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for pred, exp in zip(predictions, expected):
        pred_set = set(pred)
        exp_set = set(exp)

        tp = len(pred_set & exp_set)
        fp = len(pred_set - exp_set)
        fn = len(exp_set - pred_set)

        total_tp += tp
        total_fp += fp
        total_fn += fn

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return MultiLabelScores(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=total_tp,
        false_positives=total_fp,
        false_negatives=total_fn
    )


def score_calibration(
    confidences: List[float],
    correct: List[bool],
    human_review_pred: List[bool],
    human_review_expected: List[bool]
) -> CalibrationScores:
    """Calculate confidence calibration metrics."""
    n = len(confidences)
    if n == 0:
        return CalibrationScores(brier_score=0, calibration_error=0, human_review_accuracy=0)

    brier_score = sum(
        (conf - (1.0 if corr else 0.0)) ** 2
        for conf, corr in zip(confidences, correct)
    ) / n

    bins = [[] for _ in range(10)]
    for conf, corr in zip(confidences, correct):
        bin_idx = min(int(conf * 10), 9)
        bins[bin_idx].append((conf, corr))

    calibration_errors = []
    for bin_data in bins:
        if bin_data:
            avg_conf = sum(c for c, _ in bin_data) / len(bin_data)
            actual_acc = sum(1 for _, corr in bin_data if corr) / len(bin_data)
            calibration_errors.append(abs(avg_conf - actual_acc) * len(bin_data))

    calibration_error = sum(calibration_errors) / n if calibration_errors else 0

    hr_correct = sum(
        1 for p, e in zip(human_review_pred, human_review_expected) if p == e
    )
    human_review_accuracy = hr_correct / len(human_review_pred) if human_review_pred else 0

    return CalibrationScores(
        brier_score=brier_score,
        calibration_error=calibration_error,
        human_review_accuracy=human_review_accuracy
    )


@dataclass
class PredictedClassification:
    """Classifier output to evaluate against expected."""
    relevance_score: int
    confidence: float
    bsa_pillars: List[str]
    categories: List[str]
    requires_human_review: bool


def evaluate_classification(
    test_cases: List[TestCase],
    predictions: List[PredictedClassification],
    relevance_tolerance: int = 1
) -> EvaluationReport:
    """Run full evaluation comparing predictions to test cases."""
    if len(test_cases) != len(predictions):
        raise ValueError("Must have same number of test cases and predictions")

    pred_relevance = [p.relevance_score for p in predictions]
    exp_relevance = [tc.expected.relevance_score for tc in test_cases]
    relevance_scores = score_relevance(pred_relevance, exp_relevance)

    pred_pillars = [set(p.bsa_pillars) for p in predictions]
    exp_pillars = [set(tc.expected.bsa_pillars) for tc in test_cases]
    pillar_scores = score_multilabel(pred_pillars, exp_pillars)

    pred_categories = [set(p.categories) for p in predictions]
    exp_categories = [set(tc.expected.categories) for tc in test_cases]
    category_scores = score_multilabel(pred_categories, exp_categories)

    correct = [
        abs(p.relevance_score - tc.expected.relevance_score) <= relevance_tolerance
        for p, tc in zip(predictions, test_cases)
    ]
    confidences = [p.confidence for p in predictions]
    human_review_pred = [p.requires_human_review for p in predictions]
    human_review_expected = [tc.expected.requires_human_review for tc in test_cases]

    calibration_scores = score_calibration(
        confidences, correct, human_review_pred, human_review_expected
    )

    details = []
    for tc, pred in zip(test_cases, predictions):
        details.append({
            "document_id": tc.document_id,
            "title": tc.title,
            "expected_relevance": tc.expected.relevance_score,
            "predicted_relevance": pred.relevance_score,
            "relevance_error": abs(pred.relevance_score - tc.expected.relevance_score),
            "expected_pillars": tc.expected.bsa_pillars,
            "predicted_pillars": pred.bsa_pillars,
            "pillar_match": set(pred.bsa_pillars) == set(tc.expected.bsa_pillars),
            "expected_categories": tc.expected.categories,
            "predicted_categories": pred.categories,
            "category_match": set(pred.categories) == set(tc.expected.categories),
            "confidence": pred.confidence,
            "correct_within_tolerance": abs(pred.relevance_score - tc.expected.relevance_score) <= relevance_tolerance
        })

    return EvaluationReport(
        relevance=relevance_scores,
        pillars=pillar_scores,
        categories=category_scores,
        calibration=calibration_scores,
        total_cases=len(test_cases),
        details=details
    )


def generate_report(evaluation: EvaluationReport) -> str:
    """Generate human-readable evaluation report."""
    lines = [
        "=" * 60,
        "CLASSIFICATION EVALUATION REPORT",
        "=" * 60,
        f"Total test cases: {evaluation.total_cases}",
        "",
        "RELEVANCE SCORING",
        "-" * 40,
        f"  Mean Absolute Error: {evaluation.relevance.mae:.3f}",
        f"  Root Mean Squared Error: {evaluation.relevance.rmse:.3f}",
        f"  Exact Match Accuracy: {evaluation.relevance.exact_accuracy:.1%}",
        f"  Tier Accuracy (low/med/high): {evaluation.relevance.tier_accuracy:.1%}",
        "",
        "BSA PILLARS (Multi-Label)",
        "-" * 40,
        f"  Precision: {evaluation.pillars.precision:.1%}",
        f"  Recall: {evaluation.pillars.recall:.1%}",
        f"  F1 Score: {evaluation.pillars.f1:.1%}",
        f"  True Positives: {evaluation.pillars.true_positives}",
        f"  False Positives: {evaluation.pillars.false_positives}",
        f"  False Negatives: {evaluation.pillars.false_negatives}",
        "",
        "CATEGORIES (Multi-Label)",
        "-" * 40,
        f"  Precision: {evaluation.categories.precision:.1%}",
        f"  Recall: {evaluation.categories.recall:.1%}",
        f"  F1 Score: {evaluation.categories.f1:.1%}",
        f"  True Positives: {evaluation.categories.true_positives}",
        f"  False Positives: {evaluation.categories.false_positives}",
        f"  False Negatives: {evaluation.categories.false_negatives}",
        "",
        "CONFIDENCE CALIBRATION",
        "-" * 40,
        f"  Brier Score: {evaluation.calibration.brier_score:.3f} (lower is better)",
        f"  Calibration Error: {evaluation.calibration.calibration_error:.3f}",
        f"  Human Review Prediction Accuracy: {evaluation.calibration.human_review_accuracy:.1%}",
        "",
        "=" * 60,
    ]

    return "\n".join(lines)


def generate_error_analysis(evaluation: EvaluationReport) -> str:
    """Generate breakdown of errors for debugging."""
    lines = [
        "ERROR ANALYSIS",
        "=" * 60,
        "",
        "Cases with relevance error > 1:",
        "-" * 40,
    ]

    errors = [d for d in evaluation.details if d["relevance_error"] > 1]
    if not errors:
        lines.append("  None - all predictions within tolerance!")
    else:
        for d in sorted(errors, key=lambda x: -x["relevance_error"]):
            lines.extend([
                f"  {d['document_id']}",
                f"    Title: {d['title'][:50]}...",
                f"    Expected: {d['expected_relevance']}, Predicted: {d['predicted_relevance']}",
                f"    Error: {d['relevance_error']}",
                ""
            ])

    lines.extend([
        "",
        "Cases with pillar mismatch:",
        "-" * 40,
    ])

    pillar_errors = [d for d in evaluation.details if not d["pillar_match"]]
    if not pillar_errors:
        lines.append("  None - all pillar predictions correct!")
    else:
        for d in pillar_errors[:10]:
            lines.extend([
                f"  {d['document_id']}",
                f"    Expected: {d['expected_pillars']}",
                f"    Predicted: {d['predicted_pillars']}",
                ""
            ])

    return "\n".join(lines)


if __name__ == "__main__":
    from src.evaluation.loader import load_test_data

    dataset = load_test_data()

    mock_predictions = [
        PredictedClassification(
            relevance_score=tc.expected.relevance_score,
            confidence=tc.expected.confidence,
            bsa_pillars=tc.expected.bsa_pillars,
            categories=tc.expected.categories,
            requires_human_review=tc.expected.requires_human_review
        )
        for tc in dataset.test_cases
    ]

    report = evaluate_classification(dataset.test_cases, mock_predictions)
    print(generate_report(report))
    print()
    print(generate_error_analysis(report))
