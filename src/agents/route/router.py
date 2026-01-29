"""Task routing logic for gap analysis remediation."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from src.framework.controls import get_control_by_id, CONTROLS
from src.models.document import TaskCreate, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)

VALID_TEAMS = [
    "AML Operations",
    "Compliance Training",
    "BSA Officer",
    "Internal Audit",
    "Legal & Regulatory Affairs",
    "Risk Management",
]

PRIORITY_DUE_DAYS = {
    "critical": 7,
    "high": 14,
    "medium": 30,
    "low": 60,
}


def severity_to_priority(severity: str) -> TaskPriority:
    """Map gap severity to task priority."""
    mapping = {
        "critical": TaskPriority.CRITICAL,
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW,
    }
    return mapping.get(severity.lower(), TaskPriority.MEDIUM)


def calculate_due_date(priority: TaskPriority) -> datetime:
    """Calculate due date based on priority."""
    days = PRIORITY_DUE_DAYS.get(priority.value, 30)
    return datetime.utcnow() + timedelta(days=days)


def get_primary_owner(control_id: str) -> str:
    """Get the primary owner team for a control."""
    control = get_control_by_id(control_id)
    if control and control.typical_owners:
        return control.typical_owners[0]
    return "BSA Officer"


def generate_tasks_from_gap_analysis(
    regulation_id: UUID,
    gap_analysis_id: UUID,
    gap_severity: str,
    affected_controls: List[Dict[str, Any]],
    regulation_title: str,
) -> List[TaskCreate]:
    """Generate tasks from gap analysis affected controls.

    Args:
        regulation_id: UUID of the regulation
        gap_analysis_id: UUID of the gap analysis
        gap_severity: Overall gap severity (critical/high/medium/low)
        affected_controls: List of affected control dicts from gap analysis
        regulation_title: Title of the regulation for task context

    Returns:
        List of TaskCreate objects ready to be persisted
    """
    tasks = []
    priority = severity_to_priority(gap_severity)
    due_date = calculate_due_date(priority)

    for control_gap in affected_controls:
        control_id = control_gap.get("control_id")
        if not control_id:
            continue

        control = get_control_by_id(control_id)
        if not control:
            logger.warning(f"Unknown control ID: {control_id}")
            continue

        gap_type = control_gap.get("gap_type", "unknown")
        recommendation = control_gap.get("recommendation", "")

        title = f"[{control_id}] Address {gap_type} gap in {control.name}"

        description_parts = [
            f"Regulation: {regulation_title}",
            f"Control: {control.name}",
            f"Pillar: {control.pillar.replace('_', ' ').title()}",
            f"Gap Type: {gap_type}",
        ]
        if recommendation:
            description_parts.append(f"Recommendation: {recommendation}")

        description = "\n".join(description_parts)

        assigned_team = get_primary_owner(control_id)

        task = TaskCreate(
            regulation_id=regulation_id,
            gap_analysis_id=gap_analysis_id,
            control_id=control_id,
            title=title,
            description=description,
            assigned_team=assigned_team,
            priority=priority,
            status=TaskStatus.PENDING,
            due_date=due_date,
        )
        tasks.append(task)

    return tasks
