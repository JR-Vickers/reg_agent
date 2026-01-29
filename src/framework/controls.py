from typing import List, Optional
from pydantic import BaseModel


class Control(BaseModel):
    id: str
    name: str
    pillar: str
    description: str
    evidence_types: List[str]
    typical_owners: List[str]


CONTROLS: List[Control] = [
    # Internal Controls (IC-01 through IC-04)
    Control(
        id="IC-01",
        name="Transaction Monitoring Program",
        pillar="internal_controls",
        description="Automated and manual systems to detect suspicious transactions, including threshold-based alerts, behavioral analytics, and pattern detection for money laundering, structuring, and other illicit activity.",
        evidence_types=["TM system configuration", "Alert rules documentation", "Tuning reports", "Alert disposition logs"],
        typical_owners=["AML Operations", "Risk Management"],
    ),
    Control(
        id="IC-02",
        name="Suspicious Activity Escalation Procedures",
        pillar="internal_controls",
        description="Documented procedures for escalating potentially suspicious activity from front-line staff to the BSA/AML team, including timelines, documentation requirements, and decision authority.",
        evidence_types=["Escalation policy", "Case management records", "SAR referral logs"],
        typical_owners=["AML Operations", "BSA Officer"],
    ),
    Control(
        id="IC-03",
        name="Sanctions Screening Program",
        pillar="internal_controls",
        description="Real-time and batch screening of customers, transactions, and counterparties against OFAC SDN lists, sectoral sanctions, and other restricted party lists.",
        evidence_types=["Screening system configuration", "List update logs", "Hit disposition records", "False positive analysis"],
        typical_owners=["AML Operations", "Compliance Training"],
    ),
    Control(
        id="IC-04",
        name="Risk Assessment Methodology",
        pillar="internal_controls",
        description="Enterprise-wide BSA/AML risk assessment identifying inherent risks by customer type, product, geography, and transaction channel, with controls mapping and residual risk ratings.",
        evidence_types=["Risk assessment document", "Risk rating matrices", "Board approval records"],
        typical_owners=["Risk Management", "BSA Officer"],
    ),
    # BSA Officer (BSA-01 through BSA-04)
    Control(
        id="BSA-01",
        name="BSA Officer Designation & Authority",
        pillar="bsa_officer",
        description="Formal designation of a qualified BSA/AML Officer with sufficient authority, independence, and access to resources to manage the compliance program.",
        evidence_types=["Board resolution", "Job description", "Reporting structure documentation"],
        typical_owners=["BSA Officer", "Legal & Regulatory Affairs"],
    ),
    Control(
        id="BSA-02",
        name="Board Reporting & Oversight",
        pillar="bsa_officer",
        description="Regular reporting to the Board or Board committee on BSA/AML program status, metrics, examination findings, and significant suspicious activity trends.",
        evidence_types=["Board meeting minutes", "BSA reports to Board", "Committee charters"],
        typical_owners=["BSA Officer", "Internal Audit"],
    ),
    Control(
        id="BSA-03",
        name="Regulatory Examination Management",
        pillar="bsa_officer",
        description="Processes for preparing for, responding to, and remediating findings from FinCEN, state, and other regulatory examinations of the BSA/AML program.",
        evidence_types=["Exam response files", "Remediation tracking", "MRA/MRIA status reports"],
        typical_owners=["BSA Officer", "Legal & Regulatory Affairs"],
    ),
    Control(
        id="BSA-04",
        name="Program Documentation & Updates",
        pillar="bsa_officer",
        description="Maintenance of comprehensive BSA/AML policies and procedures with version control, regular review cycles, and updates for regulatory changes.",
        evidence_types=["Policy repository", "Version history", "Annual review sign-offs"],
        typical_owners=["BSA Officer", "Compliance Training"],
    ),
    # Training (TR-01 through TR-04)
    Control(
        id="TR-01",
        name="New Employee BSA Training",
        pillar="training",
        description="Mandatory BSA/AML training for all new employees within 30 days of hire, covering legal requirements, red flags, and escalation procedures.",
        evidence_types=["Training curriculum", "Completion records", "Quiz scores"],
        typical_owners=["Compliance Training", "Human Resources"],
    ),
    Control(
        id="TR-02",
        name="Role-Based AML Training",
        pillar="training",
        description="Specialized training for high-risk roles (customer onboarding, transaction monitoring analysts, customer support) with job-specific scenarios and typologies.",
        evidence_types=["Role-specific curricula", "Completion records by role", "Competency assessments"],
        typical_owners=["Compliance Training", "AML Operations"],
    ),
    Control(
        id="TR-03",
        name="Annual Refresher Training",
        pillar="training",
        description="Annual BSA/AML refresher training for all employees covering regulatory updates, new typologies, and lessons learned from internal cases.",
        evidence_types=["Annual training materials", "Completion tracking", "Acknowledgment records"],
        typical_owners=["Compliance Training"],
    ),
    Control(
        id="TR-04",
        name="Training Records & Tracking",
        pillar="training",
        description="System for tracking training completion, sending reminders for overdue training, and generating compliance reports for examinations.",
        evidence_types=["LMS reports", "Completion dashboards", "Exam-ready training summaries"],
        typical_owners=["Compliance Training", "Human Resources"],
    ),
    # Independent Testing (IT-01 through IT-04)
    Control(
        id="IT-01",
        name="Annual Independent Audit",
        pillar="independent_testing",
        description="Annual independent audit of the BSA/AML program by qualified internal audit staff or external party, covering all Five Pillars.",
        evidence_types=["Audit reports", "Scope documentation", "Auditor qualifications"],
        typical_owners=["Internal Audit"],
    ),
    Control(
        id="IT-02",
        name="Transaction Testing Sampling",
        pillar="independent_testing",
        description="Statistical sampling of transactions to test whether monitoring systems are detecting expected suspicious patterns and whether alerts are appropriately dispositioned.",
        evidence_types=["Sampling methodology", "Test results", "Exception reports"],
        typical_owners=["Internal Audit", "AML Operations"],
    ),
    Control(
        id="IT-03",
        name="Finding Remediation Tracking",
        pillar="independent_testing",
        description="Formal tracking of audit and examination findings through remediation, with status reporting, root cause analysis, and verification of corrective actions.",
        evidence_types=["Finding tracker", "Remediation evidence", "Closure approvals"],
        typical_owners=["Internal Audit", "BSA Officer"],
    ),
    Control(
        id="IT-04",
        name="Model Validation",
        pillar="independent_testing",
        description="Independent validation of transaction monitoring and sanctions screening models, including threshold analysis, above/below-the-line testing, and tuning recommendations.",
        evidence_types=["Validation reports", "Model inventory", "Tuning recommendations"],
        typical_owners=["Internal Audit", "Risk Management"],
    ),
    # Customer Due Diligence (CDD-01 through CDD-04)
    Control(
        id="CDD-01",
        name="Customer Identification Program (CIP)",
        pillar="customer_due_diligence",
        description="Procedures for collecting and verifying customer identity at onboarding, including documentary and non-documentary verification methods for individuals and entities.",
        evidence_types=["CIP procedures", "Verification logs", "Exception handling records"],
        typical_owners=["AML Operations", "Customer Onboarding"],
    ),
    Control(
        id="CDD-02",
        name="Beneficial Ownership Identification",
        pillar="customer_due_diligence",
        description="Collection and verification of beneficial ownership information for legal entity customers, including 25% ownership threshold and control prong requirements.",
        evidence_types=["BO certification forms", "Ownership verification records", "Refresh documentation"],
        typical_owners=["AML Operations", "Customer Onboarding"],
    ),
    Control(
        id="CDD-03",
        name="Enhanced Due Diligence (EDD)",
        pillar="customer_due_diligence",
        description="Additional due diligence procedures for high-risk customers including PEPs, high-risk jurisdictions, and complex entity structures. Includes source of funds/wealth verification.",
        evidence_types=["EDD procedures", "High-risk customer files", "PEP screening results"],
        typical_owners=["AML Operations", "Risk Management"],
    ),
    Control(
        id="CDD-04",
        name="Ongoing Customer Monitoring",
        pillar="customer_due_diligence",
        description="Continuous monitoring of customer activity against expected behavior, periodic refresh of CDD information, and trigger-based reviews for significant changes.",
        evidence_types=["Monitoring rules", "Periodic review schedules", "Trigger event logs"],
        typical_owners=["AML Operations", "Risk Management"],
    ),
]


def get_controls_by_pillar(pillar: str) -> List[Control]:
    return [c for c in CONTROLS if c.pillar == pillar]


def get_control_by_id(control_id: str) -> Optional[Control]:
    for c in CONTROLS:
        if c.id == control_id:
            return c
    return None


def get_all_control_ids() -> List[str]:
    return [c.id for c in CONTROLS]


VALID_CONTROL_IDS = get_all_control_ids()
