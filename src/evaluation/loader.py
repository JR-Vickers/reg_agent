"""Test data loader and validator for evaluation framework."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator

VALID_BSA_PILLARS = {
    "internal_controls", "bsa_officer", "training",
    "independent_testing", "customer_due_diligence"
}


class ExpectedClassification(BaseModel):
    """Expected classification output for a test case."""
    relevance_score: int = Field(..., ge=0, le=5)
    confidence: float = Field(..., ge=0.0, le=1.0)
    bsa_pillars: List[str]
    categories: List[str]
    requires_human_review: bool

    @model_validator(mode="after")
    def validate_pillars(self):
        for pillar in self.bsa_pillars:
            if pillar not in VALID_BSA_PILLARS:
                raise ValueError(f"Invalid BSA pillar: {pillar}")
        return self


class TestCase(BaseModel):
    """A single test case with document and expected classification."""
    document_id: str
    title: str
    expected: ExpectedClassification
    rationale: str


class TestDataset(BaseModel):
    """Complete test dataset with metadata."""
    metadata: Dict[str, Any]
    test_cases: List[TestCase]


def load_test_data(path: Optional[Path] = None) -> TestDataset:
    """Load and validate test dataset from JSON file."""
    if path is None:
        path = Path(__file__).parent / "test_data.json"

    with open(path) as f:
        data = json.load(f)

    return TestDataset(**data)


def get_test_cases_by_relevance(
    dataset: TestDataset,
    min_score: int = 0,
    max_score: int = 5
) -> List[TestCase]:
    """Filter test cases by relevance score range."""
    return [
        tc for tc in dataset.test_cases
        if min_score <= tc.expected.relevance_score <= max_score
    ]


def get_test_cases_by_category(
    dataset: TestDataset,
    category: str
) -> List[TestCase]:
    """Filter test cases containing a specific category."""
    return [
        tc for tc in dataset.test_cases
        if category in tc.expected.categories
    ]


def summarize_dataset(dataset: TestDataset) -> Dict[str, Any]:
    """Generate summary statistics for the test dataset."""
    scores = [tc.expected.relevance_score for tc in dataset.test_cases]
    categories_flat = [
        cat for tc in dataset.test_cases
        for cat in tc.expected.categories
    ]
    pillars_flat = [
        p for tc in dataset.test_cases
        for p in tc.expected.bsa_pillars
    ]

    from collections import Counter

    return {
        "total_cases": len(dataset.test_cases),
        "score_distribution": dict(Counter(scores)),
        "category_distribution": dict(Counter(categories_flat)),
        "pillar_distribution": dict(Counter(pillars_flat)),
        "human_review_required": sum(
            1 for tc in dataset.test_cases
            if tc.expected.requires_human_review
        ),
        "avg_confidence": sum(
            tc.expected.confidence for tc in dataset.test_cases
        ) / len(dataset.test_cases) if dataset.test_cases else 0
    }


if __name__ == "__main__":
    dataset = load_test_data()
    summary = summarize_dataset(dataset)

    print(f"Test Dataset Summary")
    print(f"=" * 40)
    print(f"Total cases: {summary['total_cases']}")
    print(f"\nRelevance score distribution:")
    for score in range(6):
        count = summary['score_distribution'].get(score, 0)
        print(f"  {score}: {'█' * count} ({count})")

    print(f"\nCategory distribution:")
    for cat, count in sorted(summary['category_distribution'].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    print(f"\nBSA Pillar distribution:")
    for pillar, count in sorted(summary['pillar_distribution'].items(), key=lambda x: -x[1]):
        print(f"  {pillar}: {count}")

    print(f"\nHuman review required: {summary['human_review_required']}")
    print(f"Average confidence: {summary['avg_confidence']:.2f}")
