import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional
from dataclasses import dataclass

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


@dataclass
class DocumentInput:
    id: str
    title: str
    source: str
    published_date: str
    content: str


@dataclass
class BatchResult:
    id: str
    result: Optional[ClassificationResult]
    error: Optional[str]


def classify_documents_batch(
    documents: List[DocumentInput],
    max_workers: int = 10,
) -> List[BatchResult]:
    results: List[BatchResult] = [None] * len(documents)

    def classify_one(idx: int, doc: DocumentInput) -> Tuple[int, BatchResult]:
        try:
            result = classify_document(
                title=doc.title,
                source=doc.source,
                published_date=doc.published_date,
                content=doc.content,
            )
            return idx, BatchResult(id=doc.id, result=result, error=None)
        except Exception as e:
            logger.error(f"Error classifying {doc.id}: {e}")
            return idx, BatchResult(id=doc.id, result=None, error=str(e))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(classify_one, i, doc): i
            for i, doc in enumerate(documents)
        }

        for future in as_completed(futures):
            idx, batch_result = future.result()
            results[idx] = batch_result
            logger.info(f"[{sum(1 for r in results if r is not None)}/{len(documents)}] Completed: {batch_result.id}")

    return results
