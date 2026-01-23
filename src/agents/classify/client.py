import logging
from openai import OpenAI

from src.config.settings import settings
from src.agents.classify.prompts import (
    SYSTEM_PROMPT,
    ClassificationResult,
    build_user_prompt,
)

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"


def _get_strict_schema() -> dict:
    schema = ClassificationResult.model_json_schema()
    schema["additionalProperties"] = False
    if "$defs" in schema:
        del schema["$defs"]
    return schema


def classify_document(
    title: str,
    source: str,
    published_date: str,
    content: str,
) -> ClassificationResult:
    client = OpenAI(api_key=settings.openai_api_key)

    user_prompt = build_user_prompt(title, source, published_date, content)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "classification",
                "strict": True,
                "schema": _get_strict_schema(),
            },
        },
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    result = ClassificationResult.model_validate_json(raw)

    logger.info(
        "Classified '%s': relevance=%d, confidence=%.2f, pillars=%s",
        title[:50],
        result.relevance_score,
        result.confidence,
        result.bsa_pillars,
    )

    return result
