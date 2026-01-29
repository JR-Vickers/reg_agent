import logging
from typing import List

from openai import OpenAI

from src.config.settings import settings
from src.agents.assess.prompts import (
    SYSTEM_PROMPT,
    GapAnalysisResult,
    build_gap_analysis_prompt,
)

logger = logging.getLogger(__name__)

MODEL = "gpt-4o"


def _get_strict_schema() -> dict:
    schema = GapAnalysisResult.model_json_schema()
    schema["additionalProperties"] = False
    if "properties" in schema:
        for prop in schema["properties"].values():
            if isinstance(prop, dict):
                prop["additionalProperties"] = False
    if "$defs" in schema:
        for def_schema in schema["$defs"].values():
            if isinstance(def_schema, dict):
                def_schema["additionalProperties"] = False
    return schema


def analyze_gaps(
    title: str,
    source: str,
    published_date: str,
    content: str,
    classification_reasoning: str,
    relevance_score: int,
    bsa_pillars: List[str],
    categories: List[str],
) -> GapAnalysisResult:
    client = OpenAI(api_key=settings.openai_api_key)

    user_prompt = build_gap_analysis_prompt(
        title=title,
        source=source,
        published_date=published_date,
        content=content,
        classification_reasoning=classification_reasoning,
        relevance_score=relevance_score,
        bsa_pillars=bsa_pillars,
        categories=categories,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "gap_analysis",
                "strict": True,
                "schema": _get_strict_schema(),
            },
        },
        temperature=0.2,
    )

    raw = response.choices[0].message.content
    result = GapAnalysisResult.model_validate_json(raw)

    logger.info(
        "Gap analysis for '%s': severity=%s, affected_controls=%d, effort=%d hrs",
        title[:50],
        result.overall_severity,
        len(result.affected_controls),
        result.total_effort_hours,
    )

    return result
