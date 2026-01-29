from typing import List
from pydantic import BaseModel, Field


SYSTEM_PROMPT = """You are a BSA/AML compliance gap analyst at a major cryptocurrency exchange. Your job is to analyze regulatory documents and determine whether they create compliance gaps in the company's existing control framework.

A "gap" exists when a regulation requires something that current controls do not fully address. You must assess each relevant control and determine:
1. Whether the regulation affects that control
2. If affected, the severity of the gap (how much work is needed to comply)
3. Specific remediation actions required

CONTROL FRAMEWORK:
The company has 20 BSA/AML controls organized by FinCEN's Five Pillars:

INTERNAL CONTROLS:
- IC-01: Transaction Monitoring Program - Automated/manual systems to detect suspicious transactions
- IC-02: Suspicious Activity Escalation Procedures - Procedures for escalating suspicious activity to BSA/AML team
- IC-03: Sanctions Screening Program - Real-time/batch screening against OFAC and restricted party lists
- IC-04: Risk Assessment Methodology - Enterprise-wide BSA/AML risk assessment

BSA OFFICER:
- BSA-01: BSA Officer Designation & Authority - Formal designation of qualified BSA Officer
- BSA-02: Board Reporting & Oversight - Regular BSA reporting to Board/committee
- BSA-03: Regulatory Examination Management - Processes for exam preparation and remediation
- BSA-04: Program Documentation & Updates - Maintenance of BSA policies and procedures

TRAINING:
- TR-01: New Employee BSA Training - Mandatory training within 30 days of hire
- TR-02: Role-Based AML Training - Specialized training for high-risk roles
- TR-03: Annual Refresher Training - Annual BSA/AML refresher for all employees
- TR-04: Training Records & Tracking - System for tracking training completion

INDEPENDENT TESTING:
- IT-01: Annual Independent Audit - Annual independent audit of BSA program
- IT-02: Transaction Testing Sampling - Statistical sampling to test monitoring effectiveness
- IT-03: Finding Remediation Tracking - Tracking audit/exam findings through remediation
- IT-04: Model Validation - Independent validation of TM and sanctions models

CUSTOMER DUE DILIGENCE:
- CDD-01: Customer Identification Program (CIP) - Identity collection and verification at onboarding
- CDD-02: Beneficial Ownership Identification - BO collection for legal entity customers
- CDD-03: Enhanced Due Diligence (EDD) - Additional diligence for high-risk customers
- CDD-04: Ongoing Customer Monitoring - Continuous monitoring against expected behavior

GAP SEVERITY LEVELS:
- low: Minor policy/procedure language updates. <8 hours effort.
- medium: Process changes, some retraining, minor system configuration. 8-40 hours effort.
- high: Significant system changes, major process redesign, extensive retraining. 40-160 hours effort.
- critical: Fundamental program gaps, potential current non-compliance, immediate action required. >160 hours effort.

ANALYSIS GUIDELINES:
1. Only flag controls that are ACTUALLY affected by this specific regulation
2. Be conservative - if a regulation doesn't clearly require changes, don't flag a gap
3. Consider whether the regulation introduces NEW requirements vs. clarifies EXISTING ones
4. For each affected control, provide specific, actionable remediation steps
5. Estimate effort realistically based on typical enterprise compliance programs"""


class ControlGap(BaseModel):
    control_id: str = Field(description="Control ID (e.g., IC-01, CDD-02)")
    gap_description: str = Field(description="Specific gap between regulation requirement and current control")
    remediation_action: str = Field(description="Specific action needed to close the gap")
    effort_level: str = Field(description="Effort level: low, medium, high")


class GapAnalysisResult(BaseModel):
    reasoning: str = Field(description="Step-by-step analysis of regulation requirements vs. controls")
    affected_controls: List[ControlGap] = Field(description="List of controls with identified gaps")
    overall_severity: str = Field(description="Overall gap severity: low, medium, high, critical")
    total_effort_hours: int = Field(description="Estimated total remediation hours")
    summary: str = Field(description="Executive summary of gaps and recommended actions (2-3 sentences)")


def build_gap_analysis_prompt(
    title: str,
    source: str,
    published_date: str,
    content: str,
    classification_reasoning: str,
    relevance_score: int,
    bsa_pillars: List[str],
    categories: List[str],
) -> str:
    max_content_length = 4000
    content = content or title
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n[TRUNCATED]"

    pillars_str = ", ".join(bsa_pillars) if bsa_pillars else "None identified"
    categories_str = ", ".join(categories) if categories else "None identified"

    return f"""Analyze the following regulation for compliance gaps against our 20-control BSA/AML framework.

REGULATION:
Title: {title}
Source: {source}
Published: {published_date}

Content:
{content}

PRIOR CLASSIFICATION:
Relevance Score: {relevance_score}/5
BSA Pillars Affected: {pillars_str}
Categories: {categories_str}
Classification Reasoning: {classification_reasoning}

TASK:
Based on the affected BSA pillars ({pillars_str}), analyze the relevant controls and identify any gaps. Focus on controls within those pillars, but also check adjacent controls if the regulation has cross-cutting implications.

For each gap found, specify:
1. Which control is affected (use control IDs: IC-01 through IC-04, BSA-01 through BSA-04, TR-01 through TR-04, IT-01 through IT-04, CDD-01 through CDD-04)
2. What specific gap exists
3. What remediation action is needed
4. Effort level (low/medium/high)

If no gaps exist (regulation is already addressed by current controls), return an empty affected_controls list with overall_severity "low" and explain why in the summary."""
