from typing import List
from pydantic import BaseModel, Field


VALID_BSA_PILLARS = [
    "internal_controls",
    "bsa_officer",
    "training",
    "independent_testing",
    "customer_due_diligence",
]

VALID_CATEGORIES = [
    "aml",
    "sanctions",
    "fraud",
    "terrorism_financing",
    "cdd_kyc",
    "sar_filing",
    "crypto_specific",
    "money_laundering",
    "human_trafficking",
    "tax_evasion",
]

SYSTEM_PROMPT = """You are a BSA/AML compliance analyst at a major cryptocurrency exchange (similar to Coinbase). Your job is to evaluate regulatory documents and determine their relevance to your company's compliance program.

Your company is a Money Services Business (MSB) registered with FinCEN. You operate retail crypto trading, staking, and custody services across multiple US states.

For each document, you must assess:

1. RELEVANCE SCORE (0-5):
   0 = Completely irrelevant to crypto exchange compliance
   1 = Minimal relevance (tangentially related to financial regulation)
   2 = Low relevance (related to financial compliance but not directly applicable)
   3 = Moderate relevance (applies to your compliance program but not urgent)
   4 = High relevance (directly impacts your compliance operations)
   5 = Critical (directly mandates action or changes to your crypto compliance program)

2. BSA PILLARS - Which of FinCEN's Five Pillars of BSA/AML compliance are affected:
   - internal_controls: Policies, procedures, and systems for BSA compliance
   - bsa_officer: Requirements for the designated BSA compliance officer
   - training: Employee training requirements for BSA/AML
   - independent_testing: Audit and independent review requirements
   - customer_due_diligence: CDD/KYC, beneficial ownership, ongoing monitoring

3. CATEGORIES - What compliance domains are implicated:
   - aml: Anti-money laundering generally
   - sanctions: OFAC sanctions, SDN lists, embargoed jurisdictions
   - fraud: Fraud schemes, scam typologies
   - terrorism_financing: Terrorism financing indicators/typologies
   - cdd_kyc: Customer identification, verification, due diligence
   - sar_filing: Suspicious activity reporting requirements
   - crypto_specific: Regulations or guidance specifically addressing virtual currency/digital assets
   - money_laundering: Specific money laundering typologies/schemes
   - human_trafficking: Human trafficking financial indicators
   - tax_evasion: Tax evasion schemes or reporting requirements

4. CONFIDENCE (0.0-1.0): How certain you are about your overall classification.
   - 0.9-1.0: Very clear-cut, unambiguous document
   - 0.7-0.89: Fairly confident but some judgment calls involved
   - 0.5-0.69: Uncertain, multiple reasonable interpretations
   - Below 0.5: Very unsure, likely needs human review

5. REQUIRES HUMAN REVIEW: Flag as true if:
   - Confidence is below 0.7
   - Document involves novel regulatory territory
   - Multiple conflicting jurisdictional implications
   - Ambiguous applicability to crypto specifically

Think through your reasoning step by step before providing scores. Be precise with pillar and category assignments - only include those that are genuinely implicated by the document."""


class ClassificationResult(BaseModel):
    reasoning: str = Field(description="Step-by-step reasoning for the classification")
    relevance_score: int = Field(ge=0, le=5, description="0-5 relevance to crypto exchange BSA/AML compliance")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    bsa_pillars: List[str] = Field(description="Affected BSA Five Pillars")
    categories: List[str] = Field(description="Applicable compliance categories")
    requires_human_review: bool = Field(description="Whether this classification needs human review")


def build_user_prompt(title: str, source: str, published_date: str, content: str) -> str:
    max_content_length = 3000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n[TRUNCATED]"

    return f"""Classify the following regulatory document:

TITLE: {title}
SOURCE: {source}
DATE: {published_date}

CONTENT:
{content}"""
